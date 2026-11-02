# 선율이 '짬뽕'인지 재기: 엔진 덤프(evolve_stats … 덤프.txt) 와 실제 곡(학습 자료)을 같은 잣대로
#   단락 안: 마디 리듬 되풀이 · 음정 3-그램 되풀이 (동기로 짜였나)
#   이웃 단락: 리듬 · 윤곽 · 음정+길이 닮음 (이어지나 / 너무 똑같나)
#   python tools/mel_metrics.py 덤프1.txt [덤프2.txt …]
import sys, pickle, collections
import numpy as np

ROOT = "/home/drboom/project/car_bgm"


def chunk_stats(chunks):
    """chunks: [ [ (bar, tick, dur, pitch) … ] … ] (차례대로 이어진 단락들)"""
    def bar_sigs(c):
        d = collections.defaultdict(list)
        for b, t, _, _ in c:
            d[b].append(t // 3)
        return [tuple(v) for _, v in sorted(d.items())]

    def ivs(c):
        p = [x[3] for x in c]
        return [p[i + 1] - p[i] for i in range(len(p) - 1)]

    def grams(seq, n):
        return [tuple(seq[i:i + n]) for i in range(len(seq) - n + 1)]

    def jac(a, b):
        a, b = set(a), set(b)
        return len(a & b) / max(1, len(a | b)) if a or b else 1.0

    R = collections.defaultdict(list)
    for i, c in enumerate(chunks):
        if len(c) < 8:
            continue
        sig = bar_sigs(c)
        cnt = collections.Counter(sig)
        R["안·리듬되풀이"].append(sum(cnt[s] > 1 for s in sig) / len(sig))
        g = grams(ivs(c), 3)
        gc = collections.Counter(g)
        R["안·음정3그램되풀이"].append(sum(gc[x] > 1 for x in g) / max(1, len(g)))
        iv = np.abs(ivs(c))
        R["순차진행%"].append(float((iv <= 2).mean()))
        R["평균도약"].append(float(iv.mean()))
        R["마디당음"].append(len(c) / max(1, len(sig)))
        if i + 1 < len(chunks) and len(chunks[i + 1]) >= 8:
            d = chunks[i + 1]
            R["이웃·리듬"].append(jac(sig, bar_sigs(d)))
            R["이웃·윤곽4"].append(jac(grams(list(np.sign(ivs(c))), 4), grams(list(np.sign(ivs(d))), 4)))
            R["이웃·음정3"].append(jac(grams(ivs(c), 3), grams(ivs(d), 3)))
            R["이웃·똑같은마디%"].append(len(set(map(tuple, bar_notes(c))) & set(map(tuple, bar_notes(d)))) / max(1, len(set(map(tuple, bar_notes(c))))))
    return {k: float(np.mean(v)) for k, v in R.items()}


def bar_notes(c):
    d = collections.defaultdict(list)
    for b, t, du, p in c:
        d[b].append((t, p))
    return [tuple(v) for _, v in sorted(d.items())]


def real(srcs, n_songs=300):
    songs = pickle.load(open(f"{ROOT}/data/score_ai/songs.pkl", "rb"))
    try:
        songs += pickle.load(open(f"{ROOT}/data/score_ai/lmd_songs.pkl", "rb"))
    except FileNotFoundError:
        pass
    out = {}
    for src in srcs:
        ss = [s for s in songs if s["src"] == src][:n_songs]
        acc = collections.defaultdict(list)
        for s in ss:
            chunks = []
            bars = s["bars"]
            for k in range(0, len(bars) - 7, 8):
                c = [(b, t, d, p) for b in range(8) for (t, d, p) in sorted(bars[k + b]["notes"])]
                chunks.append(c)
            for kk, v in chunk_stats(chunks).items():
                acc[kk].append(v)
        out[src] = {k: float(np.nanmean(v)) for k, v in acc.items()}
    return out


def engine(path):
    d = collections.defaultdict(list)
    for line in open(path):
        k, b, t, du, p = map(int, line.split())
        d[k].append((b, t, du, p))
    return chunk_stats([d[k] for k in sorted(d)])


if __name__ == "__main__":
    rows = {f"엔진:{p.split('/')[-1]}": engine(p) for p in sys.argv[1:]}
    rows.update({f"실제:{k}": v for k, v in real(["pop909", "ewld", "lmd_song", "lmd_jazz"]).items()})
    keys = ["안·리듬되풀이", "안·음정3그램되풀이", "이웃·리듬", "이웃·윤곽4", "이웃·음정3", "이웃·똑같은마디%", "순차진행%", "평균도약", "마디당음"]
    print(f"{'':28s}" + "".join(f"{k[:9]:>11s}" for k in keys))
    for name, r in rows.items():
        print(f"{name:28s}" + "".join(f"{r.get(k, float('nan')):11.3f}" for k in keys))
