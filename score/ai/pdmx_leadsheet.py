# PDMX(공개 악보 25만, tar.gz 그대로 흘려 읽음) → 리드시트(선율 + 코드) — 클래식 · 찬송 · 민요 자료
#   ① 박자 4/4 · 2/2 · 3/4 만, 마디 길이가 고른 곡 (못갖춘 첫 마디는 버림)
#   ② 선율: 맨 위 보표(트랙 0)의 윗소리 — 더 높은 선율음이 울리는 동안의 아랫음과 선율 음역에서 뚝 떨어진 음은 반주로 넘김
#   ③ 코드: 반 마디(3/4 는 한 마디)마다 반주 음(+선율 0.3 무게)으로 틀 맞추기 (lmd_leadsheet 와 같은 틀)
#   ④ 거르기: 반주 없는 한 줄 악보 · 코드 모름 25% 이상 · 조가 흐린 곡 · 16마디 미만
#   python pdmx_leadsheet.py [앞에서 N곡만]   → data/score_ai/pdmx_songs.pkl
import os, sys, json, pickle, tarfile, time, collections
import numpy as np, pandas as pd
sys.path.insert(0, "/home/drboom/project/car_bgm/music")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lmd_leadsheet import TPL, TPL_N, TQ, QUALS, key_of

ROOT = "/home/drboom/project/car_bgm"
Q = 12
SUS = (np.arange(len(TPL)) % len(TQ) == TQ.index("sus")).astype(np.float32)
MAJ7 = (np.arange(len(TPL)) % len(TQ) == TQ.index("maj7")).astype(np.float32)


def chord_w(p, a, b, w, s, e):
    """음(p) · 시작(a) · 끝(b) · 무게(w) → [s,e) 구간 코드 (근음, 종류) 또는 None"""
    ov = np.maximum(0, np.minimum(b, e) - np.maximum(a, s)).astype(np.float32) * w
    tot = ov.sum()
    if tot <= 0:
        return None
    h = np.bincount(p % 12, weights=ov, minlength=12).astype(np.float32) / tot
    # 악보는 지나가는 음이 많아 7화음 · sus 로 잘못 읽기 쉬움 → 네 음 틀과 sus 에 벌점을 더 줌 (7음이 12% 넘게 울려야 7화음)
    sc = TPL @ h - 0.45 * ((1 - TPL) @ h) - 0.17 * (TPL_N - 3) - 0.18 * SUS - 0.06 * MAJ7
    live = (ov > 0) & (w >= 1)
    if live.any():
        bass = int(p[live].min() % 12)
        sc += 0.12 * (np.arange(len(sc)) // len(TQ) == bass)
    k = int(np.argmax(sc))
    if sc[k] < 0.25:
        return None
    return k // len(TQ), QUALS.index(TQ[k % len(TQ)])


def skyline(x):
    """x (N,3: t,p,d) 한 보표 → (선율 표시 bool) — 시작마다 가장 높은 음, 단 더 높은 선율음이 아직 울리면 반주"""
    order = np.lexsort((-x[:, 1], x[:, 0]))
    mel = np.zeros(len(x), bool)
    last_t, cur_end, cur_p = -1, -1, -1
    recent = []
    for i in order:
        t, p, d = x[i]
        if t == last_t:
            continue                                   # 같은 시작의 아랫음
        last_t = t
        if t < cur_end and p < cur_p:
            continue                                   # 선율음이 울리는 동안의 속음
        if len(recent) >= 6 and p < np.median(recent[-8:]) - 12:
            continue                                   # 선율 음역에서 한 옥타브 넘게 떨어짐 → 반주가 드러난 것
        mel[i] = True
        cur_end, cur_p = t + d, p
        recent.append(p)
    return mel


def one(j, genres, idx):
    sig = {(t["numerator"], t["denominator"]) for t in (j.get("time_signatures") or [])}
    if len(sig) != 1:
        return None
    sig = sig.pop()
    if sig in ((4, 4), (2, 2)):
        L, ts = 4 * Q, 4
    elif sig == (3, 4):
        L, ts = 3 * Q, 3
    else:
        return None
    r = j["resolution"]
    cv = lambda t: int(round(t * Q / r))
    tracks = []
    for tr in j["tracks"]:
        if str(tr.get("is_drum")) == "True":
            continue
        rows = [(cv(n["time"]), n["pitch"], max(1, cv(n["duration"]))) for n in tr["notes"]
                if not n.get("is_grace") and 21 <= n["pitch"] <= 108 and n["duration"] > 0]
        if len(rows) >= 16:
            tracks.append(np.array(rows, np.int64))
    if not tracks:
        return None
    bl = sorted({cv(b["time"]) for b in j.get("barlines", [])})
    if len(bl) < 17:
        return None
    if bl[1] - bl[0] != L:                                 # 못갖춘 첫 마디
        bl = bl[1:]
    n_ok = 0
    while n_ok + 1 < len(bl) and bl[n_ok + 1] - bl[n_ok] == L:
        n_ok += 1
    if n_ok < 16:
        return None
    bars = np.array(bl[:n_ok], np.int64)
    t0, t1 = bars[0], bars[-1] + L
    tracks = [x[(x[:, 0] >= t0) & (x[:, 0] < t1)] for x in tracks]
    tracks = [x for x in tracks if len(x) >= 16]
    if not tracks:
        return None
    # 선율 보표: 맨 위 보표를 먼저 보고, 너무 낮거나 비면 다음 보표
    mi = None
    for k, x in enumerate(tracks[:3]):
        bi = np.searchsorted(bars, x[:, 0], side="right") - 1
        cov = len(np.unique(bi)) / n_ok
        if x[:, 1].mean() >= 57 and cov >= .5:
            mi = k
            break
    if mi is None:
        return None
    x = tracks[mi]
    m = skyline(x)
    mel = x[m]
    mel = mel[np.argsort(mel[:, 0], kind="stable")]
    acc = [x[~m]] + [y for k, y in enumerate(tracks) if k != mi]
    acc = np.concatenate(acc) if acc else np.zeros((0, 3), np.int64)
    if len(acc) < max(40, n_ok) or len(mel) < n_ok * .8:
        return None                                       # 반주가 없는 한 줄 악보
    allp = np.concatenate(tracks)
    key, minor, kc = key_of(allp[:, 1], allp[:, 2].astype(float))
    if kc < .55:
        return None
    # 코드
    P = np.concatenate([acc[:, 1], mel[:, 1]]); A = np.concatenate([acc[:, 0], mel[:, 0]])
    B = A + np.concatenate([acc[:, 2], mel[:, 2]])
    W = np.concatenate([np.ones(len(acc), np.float32), np.full(len(mel), .3, np.float32)])
    o = np.argsort(A, kind="stable"); P, A, B, W = P[o], A[o], B[o], W[o]
    maxd = int((B - A).max())
    out_bars, nc, prev = [], 0, None
    for k in range(n_ok):
        s = int(bars[k])
        chords = []
        for h in ((0, 2) if ts == 4 else (0,)):
            hs = s + h * Q
            he = hs + 2 * Q if ts == 4 else s + L
            lo, hi = np.searchsorted(A, hs - maxd), np.searchsorted(A, he)
            c = chord_w(P[lo:hi], A[lo:hi], B[lo:hi], W[lo:hi], hs, he)
            if c is None:
                nc += 1
                c = prev
            if c is not None and (not chords or (chords[-1][1], chords[-1][2]) != c):
                if not (h and prev == c and chords):
                    chords.append((float(h), c[0], c[1]))
            prev = c if c is not None else prev
        a, b = np.searchsorted(mel[:, 0], s), np.searchsorted(mel[:, 0], s + L)
        notes = []
        for i in range(a, b):
            t, p, d = mel[i]
            nxt = mel[i + 1, 0] if i + 1 < len(mel) else t + d
            notes.append((int(t - s), int(max(1, min(d, nxt - t, 4 * L))), int(p)))
        out_bars.append(dict(chords=chords, notes=notes, sec=None))
    if nc / (n_ok * (2 if ts == 4 else 1)) > .25:
        return None
    while out_bars and not out_bars[0]["notes"]:
        out_bars.pop(0)
    while out_bars and not out_bars[-1]["notes"]:
        out_bars.pop()
    out_bars = out_bars[:160]
    if len(out_bars) < 16:
        return None
    first = next((b["chords"][0] for b in out_bars if b["chords"]), None)
    if first is None:
        return None
    if not out_bars[0]["chords"]:
        out_bars[0]["chords"].insert(0, (0.0, first[1], first[2]))
    cur = None
    for b in out_bars:
        if b["chords"] and b["chords"][0][0] > 0 and cur is not None:
            b["chords"].insert(0, (0.0, cur[1], cur[2]))
        if not b["chords"] and cur is not None:
            b["chords"].append((0.0, cur[1], cur[2]))
        if b["chords"]:
            cur = b["chords"][-1]
    tp = (j.get("tempos") or [{}])[0]
    qpm = None if not tp or (abs(tp.get("qpm", 120) - 120) < 1e-3 and not tp.get("text")) else float(min(max(tp["qpm"], 30), 250))
    g = [x for x in str(genres).split("-") if x and x != "nan"]
    src = ("pdmx_classical" if ("classical" in g or "religiousmusic" in g) else "pdmx_folk" if any(x in g for x in ("folk", "worldmusic", "country"))
           else "pdmx_jazz" if any(x in g for x in ("jazz", "blues")) else "pdmx_pop" if g else "pdmx_misc")
    return dict(src=src, title=f"pdmx{idx}", key=int(key), minor=bool(minor), ts=ts, feel="straight", tempo=qpm, kind="head",
                bars=out_bars, genres=g, n_tracks=len(tracks), name=(j.get("metadata") or {}).get("title"))


if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    D = f"{ROOT}/data/pdmx"
    df = pd.read_csv(f"{D}/meta/PDMX/PDMX.csv", low_memory=False)
    df = df[df["subset:deduplicated"] & (df["song_length.bars"] >= 17) & (df["n_notes"] >= 150) & (df["n_tracks"] <= 24)]
    want = {"PDMX/" + p[2:]: (g, i) for i, (p, g) in enumerate(zip(df["path"], df["genres"]))}
    print("볼 곡", len(want), flush=True)
    out, t0, seen, why = [], time.time(), 0, collections.Counter()
    with tarfile.open(f"{D}/PDMX.tar.gz", "r|gz") as tar:
        for m in tar:
            if m.name not in want:
                continue
            seen += 1
            g, i = want[m.name]
            try:
                r = one(json.load(tar.extractfile(m)), g, i)
            except Exception as e:
                r = None
                why[type(e).__name__] += 1
            if r:
                out.append(r)
            if seen % 5000 == 0:
                print(f"{seen}/{len(want)} · 쓸 곡 {len(out)} · {time.time() - t0:.0f}초", flush=True)
            if limit and seen >= limit:
                break
    pickle.dump(out, open(f"{ROOT}/data/score_ai/pdmx_songs{'_test' if limit else ''}.pkl", "wb"))
    print("끝:", len(out), collections.Counter(s["src"] for s in out), collections.Counter(s["ts"] for s in out),
          "단조", sum(s["minor"] for s in out), "오류", dict(why), f"{time.time() - t0:.0f}초")
