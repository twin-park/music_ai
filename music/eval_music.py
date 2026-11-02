# 음악 모델 채점: ① 문법 ② 조건 따르기(조건 없이 만든 것과 비교) ③ 실제 곡과 통계 비교 ④ 학습 곡 베끼기
import os, sys, json, time, argparse
import numpy as np, torch
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from tokens import TOK, V, SEP, BOS, decode, conditions, estimate_key, TIMESIGS, GENRES, Q
import generate as G
from train import Windows
from conduct import SITUATIONS, DEFAULT

D = "/home/drboom/project/car_bgm/data/music"
ATTR = ["MODE", "DENS", "POLY", "REG", "VEL"]
MAJ = {0, 2, 4, 5, 7, 9, 11}; MIN = {0, 2, 3, 5, 7, 8, 10, 11}


def stats(notes, bar_len, n_bars):
    """음악 통계: 조 안 음 비율, 음계 엔트로피, 마디당 음, 반복 마디 비율"""
    pn = np.array([n for n in notes if n[1] != 128]) if notes else np.zeros((0, 5))
    if len(pn) < 8:
        return None
    r, mode, _ = estimate_key(pn[:, 2].astype(int), pn[:, 3].astype(float))
    sc = MAJ if mode == "major" else MIN
    inkey = np.isin((pn[:, 2] - r) % 12, list(sc)).mean()
    h = np.bincount(pn[:, 2].astype(int) % 12, minlength=12) + 1e-9; h = h / h.sum()
    ent = float(-(h * np.log2(h)).sum())
    bars = {}
    for t, _, p, _, _ in pn:
        bars.setdefault(int(t) // bar_len, []).append((int(t) % bar_len, int(p)))
    keys = [tuple(sorted(v)) for k, v in sorted(bars.items())]
    rep = np.mean([k in keys[:i] for i, k in enumerate(keys)]) if len(keys) > 1 else 0
    return {"조안음": float(inkey), "음계엔트로피": ent, "마디당음": len(pn) / max(1, n_bars), "반복마디": float(rep)}


def cond_of(notes, conds, n_bars):
    a = np.array(notes) if notes else np.zeros((0, 5), int)
    bl = G.bar_len_of(conds)
    ts = next((c[3:] for c in conds if c.startswith("TS_")), "4/4")
    return conditions(a, bl, G.qpm_of(conds), ts, [], max(1, n_bars))


def melody_grams(notes, n=10):
    """윗선율(같은 시각 가장 높은 음)의 (음정, 시차) n개 묶음 해시"""
    a = np.array([x for x in notes if x[1] != 128], np.int64) if len(notes) else np.zeros((0, 5), np.int64)
    if len(a) < n + 1:
        return np.zeros(0, np.int64)
    o = np.lexsort((-a[:, 2], a[:, 0])); a = a[o]
    first = np.r_[True, a[1:, 0] != a[:-1, 0]]
    top = a[first]
    iv = np.clip(np.diff(top[:, 2]), -24, 24) + 24
    dt = np.clip(np.diff(top[:, 0]), 0, 95)
    sym = iv * 96 + dt
    if len(sym) < n:
        return np.zeros(0, np.int64)
    w = np.lib.stride_tricks.sliding_window_view(sym, n)
    h = np.zeros(len(w), np.int64)
    for k in range(n):
        h = h * 4801 + w[:, k]
    return h


def train_gram_set():
    p = f"{D}/train_grams.npy"
    if os.path.exists(p):
        return np.load(p)
    notes = np.load(f"{D}/notes.npy", mmap_mode="r"); P = np.load(f"{D}/pieces.npz", allow_pickle=True)
    out = []
    for i in np.where(P["split"] == 0)[0]:
        out.append(np.unique(melody_grams(np.array(notes[P["note_off"][i]:P["note_off"][i] + P["note_n"][i]]))))
    s = np.unique(np.concatenate(out)); np.save(p, s)
    return s


def copy_stats(grams, tset):
    if len(grams) == 0:
        return None
    hit = np.isin(grams, tset)
    run, best = 0, 0
    for h in hit:
        run = run + 1 if h else 0; best = max(best, run)
    return {"겹침비율": float(hit.mean()), "최장연속겹침": int(best) + 9}   # 음 개수로 환산(10-gram)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", default="/home/drboom/project/car_bgm/runs/music/best.pt")
    ap.add_argument("--k", type=int, default=8); ap.add_argument("--bars", type=int, default=16)
    ap.add_argument("--out", default="/home/drboom/project/car_bgm/runs/music/eval")
    A = ap.parse_args()
    os.makedirs(A.out, exist_ok=True)
    m = G.load(A.ckpt)
    t_set = train_gram_set()
    print(f"학습곡 선율 묶음 {len(t_set):,}개", flush=True)
    sits = [(s[0], s[2]) for s in SITUATIONS] + [(DEFAULT[0], DEFAULT[2])]
    R = {"상황": {}, "조건일치": {}, "무조건일치": {}}
    gen_stats, gen_copy, invm, speed = [], [], [], []
    for name, conds in sits:
        progs = None
        rows = []
        for k in range(A.k):
            t = time.time()
            out = G.generate(m, conds, A.bars, seed=k, progs=G.fam_progs(conds))
            speed.append((len(out), time.time() - t))
            notes, nb, bl = decode([TOK[c] for c in conds] + out)
            got = cond_of(notes, conds, nb)
            rows.append(got)
            s = stats(notes, bl, nb); s and gen_stats.append(s)
            c = copy_stats(melody_grams(notes), t_set); c and gen_copy.append(c)
            if k < 2:
                invm.append(G.invalid_mass(m, [BOS] + [TOK[c] for c in conds] + [SEP] + out))
            if k < 2:
                mid = f"{A.out}/{name}_{k}.mid"
                G.to_midi(notes, G.qpm_of(conds), mid)
                G.render(mid, mid.replace(".mid", ".wav"), mid.replace(".mid", ".mp3"))
                os.remove(mid.replace(".mid", ".wav"))
        # 조건 없이 (박자만) 만든 것
        base = []
        for k in range(A.k):
            ts = [c for c in conds if c.startswith("TS_")]
            out = G.generate(m, ts, A.bars, seed=100 + k)
            notes, nb, _ = decode([TOK[c] for c in ts] + out)
            base.append(cond_of(notes, conds, nb))
        for lab, rr in (("조건일치", rows), ("무조건일치", base)):
            for a in ATTR:
                want = next((c for c in conds if c.startswith(a + "_")), None)
                if want is None:
                    continue
                hits = [want in g for g in rr]
                near = []
                for g in rr:
                    gv = next((c for c in g if c.startswith(a + "_")), None)
                    if a == "MODE" or gv is None:
                        near.append(gv == want)
                    else:
                        near.append(abs(int(gv.split("_")[1]) - int(want.split("_")[1])) <= 1)
                R[lab].setdefault(a, []).append((float(np.mean(hits)), float(np.mean(near))))
            fam_want = {c for c in conds if c.startswith("FAM_")}
            R[lab].setdefault("FAM", []).append(float(np.mean([fam_want == {c for c in g if c.startswith("FAM_")} for g in rr])))
        R["상황"][name] = rows[0]
        print(f"{name}: {rows[0]}", flush=True)
    # 실제 시험 곡과 비교
    ds = Windows(2, 2048, seed=3, fixed=True); ds.setup(); rng = np.random.default_rng(3)
    real_stats, real_copy = [], []
    P = ds.P
    for i in rng.choice(ds.ids, 200, replace=False):
        nt = np.array(ds.notes[P["note_off"][i]:P["note_off"][i] + P["note_n"][i]], np.int64)
        bs = np.array(ds.bars[P["bar_off"][i]:P["bar_off"][i] + P["bar_n"][i]], np.int64)
        sel = nt[nt[:, 0] < bs[min(len(bs) - 1, A.bars)]]
        bl = int(np.median(np.diff(bs))) if len(bs) > 1 else 48
        s = stats([tuple(x) for x in sel], max(1, bl), min(len(bs), A.bars)); s and real_stats.append(s)
        c = copy_stats(melody_grams(sel), t_set); c and real_copy.append(c)
    summ = lambda L: {k: round(float(np.mean([x[k] for x in L])), 3) for k in L[0]}
    res = {
        "문법_막기전_틀린낱말확률": round(float(np.mean(invm)), 5),
        "조건일치(정확,±1칸)": {a: [round(np.mean([v[0] for v in R["조건일치"][a]]), 3), round(np.mean([v[1] for v in R["조건일치"][a]]), 3)] for a in ATTR if a in R["조건일치"]},
        "조건없이_우연일치(정확,±1칸)": {a: [round(np.mean([v[0] for v in R["무조건일치"][a]]), 3), round(np.mean([v[1] for v in R["무조건일치"][a]]), 3)] for a in ATTR if a in R["무조건일치"]},
        "악기정확일치": [round(float(np.mean(R["조건일치"]["FAM"])), 3), round(float(np.mean(R["무조건일치"]["FAM"])), 3)],
        "통계_생성": summ(gen_stats), "통계_실제": summ(real_stats),
        "베끼기_생성": summ(gen_copy), "베끼기_실제시험곡": summ(real_copy),
        "생성속도_낱말per초(GPU)": round(sum(a for a, _ in speed) / sum(b for _, b in speed), 1),
    }
    json.dump(res, open(f"{A.out}/result.json", "w"), ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
