# 귀 모델 채점 · 문턱 다시 정하기 — 앱이 듣는 방식(4초 창 · 2초 간격 · 창들 중 최댓값)으로
#   python -I eval_android.py <출력 폴더> <best.pt> [<best.pt> …]
#   자료: data/fsd50k/data/{validation,test}-*.parquet · data/cremad/*.parquet (말하는 사람으로 검증 1074~1082 · 시험 1083~)
#   결과: <출력>/<이름>_thresholds.json (검증에서 F1 가장 좋은 문턱) · <출력>/<이름>_report.json (시험 점수)
#   옛 채점(10초 가운데 한 조각)도 같이 내서 학습 기록(runs/*/log.txt)의 검증 점수와 맞는지 확인
import os, sys, io, re, glob, json, time
import numpy as np, torch, soundfile as sf, pyarrow.parquet as pq
from sklearn.metrics import average_precision_score
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from model import Ear
from labels import fsd_to_groups, GROUP_IDS, N_GROUPS, EMOTIONS

ROOT = "/home/drboom/project/car_bgm/data"
SR, WIN, HOP, MAXS = 16000, 64000, 32000, 30 * 16000
G = {g: i for i, g in enumerate(GROUP_IDS)}
VOCAL = [G[k] for k in ("speech", "child", "baby_cry", "crying", "laughter", "shout", "whisper", "singing")]


def dec(b):
    x, sr = sf.read(io.BytesIO(b), dtype="int16", always_2d=True)
    assert sr == SR, sr
    return (x.mean(1) if x.shape[1] > 1 else x[:, 0]).astype(np.int16)[:MAXS]


def load_split(name):
    xs, ys, em, src = [], [], [], []
    for p in sorted(glob.glob(f"{ROOT}/fsd50k/data/{name}-*.parquet")):
        for r in pq.read_table(p, columns=["audio", "labels", "title", "tags"]).to_pylist():
            xs.append(dec(r["audio"]["bytes"]))
            ys.append(fsd_to_groups(r["labels"], (r["title"] or "") + " " + " ".join(r["tags"] or []))); em.append(-1); src.append(0)
    want = (lambda a: 1074 <= a <= 1082) if name == "validation" else (lambda a: a >= 1083)
    for p in sorted(glob.glob(f"{ROOT}/cremad/*.parquet")):
        for r in pq.read_table(p, columns=["file", "audio", "emotion"]).to_pylist():
            a = int(re.search(r"(\d{4})_", r["file"]).group(1))
            if not want(a):
                continue
            xs.append(dec(r["audio"]["bytes"]))
            y = [0] * N_GROUPS; y[G["speech"]] = 1
            ys.append(y); em.append(EMOTIONS.index(r["emotion"])); src.append(1)
    return xs, np.array(ys, np.float32), np.array(em), np.array(src)


def windows(x):
    x = x.astype(np.float32) / 32768.0
    if len(x) < WIN:
        x = np.pad(x, (0, WIN - len(x)))
    return np.stack([x[s:s + WIN] for s in range(0, len(x) - WIN + 1, HOP)])


def center10(x):
    n = 10 * SR
    out = np.zeros(n, np.float32)
    L = len(x)
    if L >= n:
        s = (L - n) // 2; out[:] = x[s:s + n]
    else:
        out[:L] = x
    return out / 32768.0


@torch.no_grad()
def run(m, xs, dev, noise=None, mode="win"):
    """mode win: 4초 창 · 2초 간격 · 창 최댓값 (앱 방식) / old: 10초 가운데 한 조각 (학습 때 채점)"""
    P, E = [], []
    rng = np.random.default_rng(123)
    if mode == "old":
        for k in range(0, len(xs), 64):
            x = torch.from_numpy(np.stack([center10(a) for a in xs[k:k + 64]])).to(dev)
            with torch.autocast("cuda", torch.bfloat16):
                c, e, _ = m(m.mel(x))
            P.append(c.float().cpu().numpy()); E.append(torch.softmax(e.float(), 1).cpu().numpy())
        return np.concatenate(P), np.concatenate(E)
    buf, owner = [], []
    def flush():
        if not buf:
            return
        x = torch.from_numpy(np.stack(buf)).to(dev)
        with torch.autocast("cuda", torch.bfloat16):
            c, e, _ = m(m.mel(x))
        res.append((np.array(owner), c.float().cpu().numpy(), torch.softmax(e.float(), 1).cpu().numpy()))
        buf.clear(); owner.clear()
    res = []
    for i, a in enumerate(xs):
        w = windows(a)
        if noise is not None:                                   # 차 소음 SNR 10dB
            nz = windows(noise[rng.integers(len(noise))])
            nz = nz[rng.integers(len(nz), size=len(w))]
            r = lambda v: np.sqrt((v ** 2).mean(1, keepdims=True)) + 1e-5
            w = w + nz * r(w) / r(nz) * 10 ** (-10 / 20)
        for row in w:
            buf.append(row); owner.append(i)
            if len(buf) >= 128:
                flush()
    flush()
    n = len(xs)
    Pm = np.zeros((n, N_GROUPS), np.float32); Es = np.zeros((n, len(EMOTIONS))); Ws = np.zeros(n)
    for o, c, e in res:
        np.maximum.at(Pm, o, c)
        sp = c[:, G["speech"]]
        np.add.at(Es, o, e * sp[:, None]); np.add.at(Ws, o, sp)
    return Pm, Es / np.maximum(Ws, 1e-6)[:, None]


def score(P, E, y, em, src, skip=()):
    m = src != 1
    aps = {GROUP_IDS[g]: float(average_precision_score(y[m, g], P[m, g])) for g in range(N_GROUPS)
           if GROUP_IDS[g] not in skip and y[m, g].sum() > 0}
    ok = em >= 0
    return float(np.mean(list(aps.values()))), aps, float((E[ok].argmax(1) == em[ok]).mean())


def thresholds(P, y):
    th = {}
    for g in range(N_GROUPS):
        if y[:, g].sum() < 3:
            th[GROUP_IDS[g]] = .5; continue
        cand = np.linspace(.05, .95, 91)
        f1 = [2 * ((P[:, g] > c) & (y[:, g] > 0)).sum() / max(1, (P[:, g] > c).sum() + y[:, g].sum()) for c in cand]
        th[GROUP_IDS[g]] = float(cand[int(np.argmax(f1))])
    return th


def prf(P, y, th, src):
    m = src != 1
    out = {}
    for g in range(N_GROUPS):
        k = GROUP_IDS[g]
        pos = y[m, g] > 0
        if pos.sum() == 0:
            continue
        on = P[m, g] >= th[k]
        tp = (on & pos).sum()
        out[k] = {"정밀도": round(float(tp / max(1, on.sum())), 3), "재현율": round(float(tp / pos.sum()), 3), "시험 양성 수": int(pos.sum())}
    return out


if __name__ == "__main__":
    out = sys.argv[1]; pts = sys.argv[2:]
    os.makedirs(out, exist_ok=True)
    dev = "cuda"
    t0 = time.time()
    V = load_split("validation"); Tt = load_split("test")
    noise = [a for a, yy in zip(V[0], V[1]) if yy[G["traffic"]] == 1 and yy[VOCAL].sum() == 0]
    print(f"검증 {len(V[0])} · 시험 {len(Tt[0])} · 소음 {len(noise)} ({time.time() - t0:.0f}초)", flush=True)
    for pt in pts:
        ck = torch.load(pt, map_location=dev)
        m = Ear(ck["width"], ck["blocks"]).to(dev).eval(); m.load_state_dict(ck["model"])
        name = os.path.basename(os.path.dirname(pt))
        Pv0, Ev0 = run(m, V[0], dev, mode="old")
        mo, _, eo = score(Pv0, Ev0, V[1], V[2], V[3])
        Pv, Ev = run(m, V[0], dev)
        th = thresholds(Pv, V[1])
        mv, _, ev = score(Pv, Ev, V[1], V[2], V[3])
        Pt, Et = run(m, Tt[0], dev)
        mt, at, et = score(Pt, Et, Tt[1], Tt[2], Tt[3])
        Pn, En = run(m, Tt[0], dev, noise=noise)
        mn, an, en = score(Pn, En, Tt[1], Tt[2], Tt[3], skip=("traffic",))
        rep = {"모델": pt, "걸음": ck.get("step"),
               "검증(옛 채점 10초)": {"mAP": round(mo, 4), "감정": round(eo, 4)},
               "검증(앱 방식 4초 창)": {"mAP": round(mv, 4), "감정": round(ev, 4)},
               "시험(앱 방식)": {"mAP": round(mt, 4), "감정": round(et, 4), "AP": {k: round(v, 3) for k, v in at.items()}},
               "시험+차소음10dB": {"mAP": round(mn, 4), "감정": round(en, 4)},
               "문턱에서 정밀도·재현율(시험)": prf(Pt, Tt[1], th, Tt[3])}
        json.dump({k: round(v, 3) for k, v in th.items()}, open(f"{out}/{name}_thresholds.json", "w"), ensure_ascii=False, indent=1)
        json.dump(rep, open(f"{out}/{name}_report.json", "w"), ensure_ascii=False, indent=1)
        print(f"{name}: 옛 채점 검증 mAP {mo:.4f} 감정 {eo:.4f} | 앱 방식 검증 {mv:.4f} · 시험 {mt:.4f} 감정 {et:.4f} · 차소음 {mn:.4f} ({time.time() - t0:.0f}초)", flush=True)
