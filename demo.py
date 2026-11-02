# 끝에서 끝까지: 주변 소리 → (귀) 단어 → (지휘) 음악 지시 → (음악 모델) 연주 → mp3
# 장면 소리는 학습에 안 쓴 시험 데이터(FSD50K 평가셋, CREMA-D 시험 화자)를 섞어 만든다.
import os, sys, json, time
import numpy as np, soundfile as sf, torch
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path += [ROOT, f"{ROOT}/ear", f"{ROOT}/music"]
from labels import GROUP_IDS, EMOTIONS
from listen import Listener
from conduct import conduct
from tokens import TOK, decode
import generate as G

OUT = f"{ROOT}/demo_out"
SR = 16000
ix = np.load(f"{ROOT}/data/ear/index.npz")
W = np.memmap(f"{ROOT}/data/ear/wav.i16", dtype=np.int16, mode="r")
GI = {g: i for i, g in enumerate(GROUP_IDS)}
TEST = np.where(ix["split"] == 2)[0]


def pick(group=None, emo=None, nth=0):
    """시험 데이터에서 그 소리만 또렷한(다른 묶음이 적은) 클립을 순서대로 고른다 (골라 먹기 없음)."""
    if emo is not None:
        c = TEST[(ix["src"][TEST] == 1) & (ix["emo"][TEST] == EMOTIONS.index(emo))]
    else:
        c = TEST[(ix["src"][TEST] == 0) & (ix["y"][TEST, GI[group]] == 1)]
        c = c[np.argsort(ix["y"][c].sum(1), kind="stable")]
    i = c[nth]
    o, L = ix["offset"][i], ix["length"][i]
    return W[o:o + L].astype(np.float32) / 32768


def mix(parts, sec=8.0):
    n = int(sec * SR); out = np.zeros(n, np.float32)
    for x, db in parts:
        x = np.tile(x, int(np.ceil(n / len(x))))[:n] if len(x) < n // 2 else np.pad(x[:n], (0, max(0, n - len(x))))
        out += x / (np.sqrt((x ** 2).mean()) + 1e-6) * 10 ** (db / 20) * 0.05
    return out / max(1.0, np.abs(out).max() / 0.9)


SCENES = [
    ("바닷가 드라이브", [("sea", None, 0), ("gull", None, -3), ("traffic", None, -12)]),
    ("아이 재우기", [("baby_cry", None, 0), ("traffic", None, -15)]),
    ("바닷가에서 아이 재우기", [("sea", None, -6), ("gull", None, -8), ("baby_cry", None, 0)]),
    ("다툼", [(None, "anger", 0), ("shout", None, -2), ("traffic", None, -15)]),
    ("즐거운 대화", [("laughter", None, 0), (None, "happy", -3), ("traffic", None, -15)]),
    ("슬픈 대화", [(None, "sad", 0), ("traffic", None, -18)]),
    ("비 오는 길", [("rain", None, 0), ("traffic", None, -6)]),
    ("전화 옴", [("phone", None, 0), ("speech", None, -6), ("traffic", None, -15)]),
    ("조용한 주행", [("traffic", None, -25)]),
]


def main(bars=16):
    os.makedirs(OUT, exist_ok=True)
    ear = Listener()
    lm = G.load(f"{ROOT}/runs/music/best.pt")
    report = []
    for k, (name, parts) in enumerate(SCENES):
        x = mix([(pick(g, e), db) for g, e, db in parts])
        sf.write(f"{OUT}/{k}_{name}_소리.wav", x, SR)
        torch.cuda.synchronize(); t = time.time()
        r = ear(x, SR)
        torch.cuda.synchronize(); t_ear = time.time() - t
        c = conduct(r["words"])
        t = time.time()
        out = G.generate(lm, c["조건"], bars, seed=k, progs=G.fam_progs(c["조건"]))
        t_gen = time.time() - t
        notes, nb, bl = decode([TOK[s] for s in c["조건"]] + out)
        qpm = G.qpm_of(c["조건"])
        music_sec = nb * bl / 12 * 60 / qpm
        mid = f"{OUT}/{k}_{name}_음악.mid"
        G.to_midi(notes, qpm, mid)
        G.render(mid, mid.replace(".mid", ".wav"), mid.replace(".mid", ".mp3"))
        os.remove(mid.replace(".mid", ".wav"))
        row = {"장면": name, "들은 단어": [w for w, s, _ in r["words"]], "상황": c["상황"], "음악 지시": c["지시"],
               "볼륨dB": c["볼륨dB"], "동작": c["동작"], "조건": c["조건"],
               "귀 시간ms": round(t_ear * 1000), "작곡 시간s": round(t_gen, 2), "음악 길이s": round(music_sec, 1),
               "마디": nb, "음표": len(notes)}
        report.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
    json.dump(report, open(f"{OUT}/report.json", "w"), ensure_ascii=False, indent=1)
    transition(ear, lm)


def transition(ear, lm, bars=8):
    """이어 듣기: 바닷가 → (뒷자리에서 아이 울음) → 같은 곡에서 자연스럽게 자장가로 + 볼륨 낮춤"""
    a = mix([(pick("sea"), 0), (pick("gull"), -3), (pick("traffic"), -12)])
    b = mix([(pick("sea"), -6), (pick("baby_cry"), 0)])
    ca, cb = conduct(ear(a)["words"]), conduct(ear(b)["words"])
    ts = [s for s in ca["조건"] if s.startswith("TS_")]
    cb_conds = ts + [s for s in cb["조건"] if not s.startswith("TS_")]      # 박자는 이어지게 유지
    out_a = G.generate(lm, ca["조건"], bars, seed=11, progs=G.fam_progs(ca["조건"]))
    # 앞 곡 마지막 4마디를 이어 쓸 실마리로
    bar_idx = [i for i, t in enumerate(out_a) if t == TOK["BAR"]]
    prompt = out_a[bar_idx[-4]:] if len(bar_idx) >= 4 else out_a
    out_b = G.generate(lm, cb_conds, bars, prompt=prompt, seed=12, progs=G.fam_progs(cb_conds))
    na, nba, bl = decode([TOK[s] for s in ca["조건"]] + out_a)
    nb_, nbb, _ = decode([TOK[s] for s in cb_conds] + out_b)
    qa, qb = G.qpm_of(ca["조건"]), G.qpm_of(cb_conds)
    # 템포가 다르니 각자 렌더해서 오디오로 이어 붙임(2초 겹쳐 넘김), 뒤쪽은 볼륨 낮춤
    G.to_midi(na, qa, f"{OUT}/전환_A.mid"); G.render(f"{OUT}/전환_A.mid", f"{OUT}/전환_A.wav")
    G.to_midi(nb_, qb, f"{OUT}/전환_B.mid"); G.render(f"{OUT}/전환_B.mid", f"{OUT}/전환_B.wav")
    xa, sr = sf.read(f"{OUT}/전환_A.wav"); xb, _ = sf.read(f"{OUT}/전환_B.wav")
    la = int(nba * bl / 12 * 60 / qa * sr)
    xa = xa[:la + 2 * sr]
    xb = xb * 10 ** (cb["볼륨dB"] / 20)
    f = np.linspace(1, 0, 2 * sr)[:, None]
    y = np.concatenate([xa[:la], xa[la:la + 2 * sr] * f + xb[:2 * sr] * (1 - f), xb[2 * sr:]])
    sf.write(f"{OUT}/전환_바닷가→아이재우기.wav", y, sr)
    os.system(f"{G.TOOLS}/ffmpeg -y -loglevel error -i '{OUT}/전환_바닷가→아이재우기.wav' -b:a 192k '{OUT}/전환_바닷가→아이재우기.mp3'")
    for p in ("전환_A.wav", "전환_B.wav", "전환_바닷가→아이재우기.wav"):
        os.remove(f"{OUT}/{p}")
    info = {"앞": ca["상황"], "뒤": cb["상황"], "뒤 지시": cb["지시"], "볼륨dB": cb["볼륨dB"]}
    json.dump(info, open(f"{OUT}/전환.json", "w"), ensure_ascii=False, indent=1)
    print("전환", info)


if __name__ == "__main__":
    main()
