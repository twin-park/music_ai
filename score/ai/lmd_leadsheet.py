# Lakh MIDI(정리해 둔 data/music_lmd) → 리드시트(선율 + 코드) — 학습 자료 늘리기
#   ① 선율 트랙 고르기: 단음 위주 · 마디를 고루 채움 · 가운데~높은 음역 · 선율 악기 가산점 (베이스·드럼·패드 제외)
#   ② 코드: 반 마디(3/4 는 한 마디)마다 선율 뺀 반주 음으로 틀 맞추기 (10종 · 베이스음 가산) · 모르면 앞 코드 이어 감
#   ③ 조: Krumhansl · 스윙: 8분 뒷박 자리(6 대 8)
#   ④ 거르기: 코드 모름 25% 미만 · 마디당 선율 0.8음 이상 · 16마디 이상 · 4/4 · 3/4 만
#   python lmd_leadsheet.py   → data/score_ai/lmd_songs.pkl
import os, sys, pickle, time
import numpy as np
sys.path.insert(0, "/home/drboom/project/car_bgm/music")
from tokens import TIMESIGS, GENRES, MOODS

ROOT = "/home/drboom/project/car_bgm"
Q = 12
QUALS = ["maj", "maj7", "min", "m7", "dom", "alt", "sus", "hdim", "dim", "aug", "mM7"]
TPL_IV = {"maj": [0, 4, 7], "maj7": [0, 4, 7, 11], "min": [0, 3, 7], "m7": [0, 3, 7, 10], "dom": [0, 4, 7, 10],
          "sus": [0, 5, 7], "hdim": [0, 3, 6, 10], "dim": [0, 3, 6], "aug": [0, 4, 8], "mM7": [0, 3, 7, 11]}
TQ = list(TPL_IV)
TPL = np.zeros((12 * len(TQ), 12), np.float32)
for r in range(12):
    for qi, q in enumerate(TQ):
        for iv in TPL_IV[q]:
            TPL[r * len(TQ) + qi, (r + iv) % 12] = 1
TPL_N = TPL.sum(1)
KS_MAJ = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
KS_MIN = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
LEAD_PROGS = set(range(0, 8)) | set(range(16, 32)) | set(range(40, 47)) | set(range(56, 88)) | {11, 12, 13}
BAD_PROGS = set(range(32, 40)) | set(range(88, 104)) | set(range(48, 56)) | set(range(112, 128))   # 베이스 · 패드 · 합주 현 · 효과


def key_of(p, w):
    h = np.bincount(p % 12, weights=w, minlength=12)
    best = (-2, 0, False)
    for r in range(12):
        for prof, mi in ((KS_MAJ, False), (KS_MIN, True)):
            c = np.corrcoef(h, np.roll(prof, r))[0, 1]
            if c > best[0]:
                best = (c, r, mi)
    return best[1], best[2], best[0]


def chord_of(seg, s, e):
    """seg (N,5) t,prog,p,d,v — [s,e) 구간 → (근음, 종류번호) 또는 None"""
    if len(seg) == 0:
        return None
    a = np.maximum(seg[:, 0], s); b = np.minimum(seg[:, 0] + seg[:, 3], e)
    w = np.maximum(0, b - a).astype(np.float32)
    if w.sum() <= 0:
        return None
    h = np.bincount(seg[:, 2] % 12, weights=w, minlength=12).astype(np.float32)
    h /= h.sum()
    sc = TPL @ h - 0.45 * ((1 - TPL) @ h) - 0.06 * (TPL_N - 3)
    live = w > 0
    bass = int(seg[live][np.argmin(seg[live][:, 2]), 2] % 12)
    sc += 0.12 * (np.arange(len(sc)) // len(TQ) == bass)
    k = int(np.argmax(sc))
    if sc[k] < 0.25:
        return None
    return k // len(TQ), QUALS.index(TQ[k % len(TQ)])


def pick_melody(nt, bars_start, n_bars):
    """프로그램별로 점수 → 선율 프로그램 (없으면 None)"""
    best, bs = None, -1
    for prog in np.unique(nt[:, 1]):
        if prog == 128 or prog in BAD_PROGS:
            continue
        x = nt[nt[:, 1] == prog]
        if len(x) < 64:
            continue
        mp = x[:, 2].mean()
        if mp < 55 or mp > 86:
            continue
        on, cnt = np.unique(x[:, 0], return_counts=True)
        mono = (cnt == 1).mean()
        if mono < .8:
            continue
        bi = np.searchsorted(bars_start, x[:, 0], side="right") - 1
        cov = len(np.unique(bi[bi >= 0])) / n_bars
        if cov < .4:
            continue
        sc = cov + .5 * mono + .01 * (mp - 60) + (.15 if prog in LEAD_PROGS else 0)
        if sc > bs:
            best, bs = int(prog), sc
    return best


def one(nt, bars, ts_name, qpm, genre, mood, idx):
    L = 4 * Q if ts_name == "4/4" else 3 * Q
    if len(bars) < 16:
        return None
    nt = nt[nt[:, 0] >= bars[0]]
    end = int((nt[:, 0] + nt[:, 3]).max())
    n_bars = len(bars)
    mp = pick_melody(nt, bars, n_bars)
    if mp is None:
        return None
    mel = nt[nt[:, 1] == mp]
    acc = nt[(nt[:, 1] != mp) & (nt[:, 1] != 128)]
    if len(acc) < 50:
        return None
    # 단음으로: 같은 시작은 높은 음만, 다음 음과 겹치면 자름
    mel = mel[np.lexsort((-mel[:, 2], mel[:, 0]))]
    keep = np.ones(len(mel), bool)
    keep[1:] = mel[1:, 0] != mel[:-1, 0]
    mel = mel[keep]
    pn = nt[nt[:, 1] != 128]
    key, minor, kc = key_of(pn[:, 2], pn[:, 3].astype(float))
    if kc < .55:
        return None
    sw_ph = pn[:, 0] % Q
    n6, n8 = int((sw_ph == 6).sum()), int((sw_ph == 8).sum())
    g = [GENRES[i] for i in range(len(GENRES)) if genre >> i & 1]
    feel = "latin" if "latin" in g else "swing" if n6 + n8 >= 16 and n8 / (n6 + n8) > .6 else "straight"
    src = "lmd_jazz" if "jazz" in g else "lmd_song" if any(x in g for x in ("classical", "soundtrack", "folk", "world", "country",
                                                                               "easylistening", "ambient", "orchestral")) and "pop" not in g else "lmd_pop"
    out_bars, nc, prev = [], 0, None
    bs = list(bars) + [bars[-1] + L]
    for k in range(n_bars):
        s, e = bs[k], bs[k + 1]
        if e - s != L:                                         # 박자가 바뀌는 곡은 버림
            return None
        chords = []
        for h in ((0, 2) if L == 4 * Q else (0,)):
            hs, he = s + h * Q, (s + (h + 2) * Q) if L == 4 * Q else e
            sel = acc[(acc[:, 0] < he) & (acc[:, 0] + acc[:, 3] > hs)]
            c = chord_of(sel, hs, he)
            if c is None:
                nc += 1
                c = prev
            if c is not None and (not chords or (chords[-1][1], chords[-1][2]) != c):
                if not (h and prev == c and chords):
                    chords.append((float(h), c[0], c[1]))
            prev = c if c is not None else prev
        m = mel[(mel[:, 0] >= s) & (mel[:, 0] < e)]
        notes = []
        for i, (t, _, p, d, _) in enumerate(m):
            nxt = mel[np.searchsorted(mel[:, 0], t, side="right")][0] if np.searchsorted(mel[:, 0], t, side="right") < len(mel) else t + d
            dd = int(max(1, min(d, nxt - t, 4 * L)))
            notes.append((int(t - s), dd, int(p)))
        out_bars.append(dict(chords=chords, notes=notes, sec=None))
    halves = n_bars * (2 if L == 4 * Q else 1)
    if nc / halves > .25:
        return None
    if sum(len(b["notes"]) for b in out_bars) / n_bars < .8:
        return None
    # 앞뒤 빈 마디 자르기, 길면 앞 160마디만
    while out_bars and not out_bars[0]["notes"]:
        out_bars.pop(0)
    while out_bars and not out_bars[-1]["notes"]:
        out_bars.pop()
    out_bars = out_bars[:160]
    if len(out_bars) < 16:
        return None
    if not out_bars[0]["chords"]:
        first = next((b["chords"][0] for b in out_bars if b["chords"]), None)
        if first is None:
            return None
        out_bars[0]["chords"].insert(0, (0.0, first[1], first[2]))
    cur = None
    for b in out_bars:                                          # 코드 없는 마디는 앞 코드 이어 받음
        if b["chords"] and b["chords"][0][0] > 0 and cur is not None:
            b["chords"].insert(0, (0.0, cur[1], cur[2]))
        if not b["chords"] and cur is not None:
            b["chords"].append((0.0, cur[1], cur[2]))
        if b["chords"]:
            cur = b["chords"][-1]
    mods = [MOODS[i] for i in range(len(MOODS)) if mood >> i & 1]
    return dict(src=src, title=f"lmd{idx}", key=int(key), minor=bool(minor), ts=4 if L == 4 * Q else 3, feel=feel, tempo=float(qpm),
                kind="head", bars=out_bars, genres=g, moods=mods, mel_prog=mp)


if __name__ == "__main__":
    D = f"{ROOT}/data/music_lmd"
    z = np.load(f"{D}/pieces.npz")
    notes = np.load(f"{D}/notes.npy", mmap_mode="r")
    bars = np.load(f"{D}/bars.npy", mmap_mode="r")
    out, t0, why = [], time.time(), 0
    for i in range(len(z["note_n"])):
        tsn = TIMESIGS[z["ts"][i]]
        if tsn not in ("4/4", "3/4"):
            continue
        nt = np.array(notes[z["note_off"][i]: z["note_off"][i] + z["note_n"][i]])
        bb = np.array(bars[z["bar_off"][i]: z["bar_off"][i] + z["bar_n"][i]])
        if z["xmas"][i]:
            continue
        try:
            r = one(nt, bb, tsn, float(z["qpm"][i]), int(z["genre"][i]), int(z["mood"][i]), i)
        except Exception as e:
            r = None
        if r:
            out.append(r)
        if i % 2000 == 0:
            print(f"{i}/{len(z['note_n'])} · 쓸 곡 {len(out)} · {time.time() - t0:.0f}초", flush=True)
    pickle.dump(out, open(f"{ROOT}/data/score_ai/lmd_songs.pkl", "wb"))
    import collections
    print("끝:", len(out), collections.Counter(s["src"] for s in out), collections.Counter(s["feel"] for s in out),
          collections.Counter(s["ts"] for s in out), "단조", sum(s["minor"] for s in out))
