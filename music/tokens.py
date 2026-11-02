# 악보 ↔ 낱말.  시간은 4분음표 = 12칸.
# 한 곡 조각 = [BOS] 조건들 [SEP] (BAR (POS PROG VEL (PITCH DUR)+ ...)*)* [EOS]
import numpy as np

Q = 12                       # 4분음표 한 칸 수
MAX_BAR = 96                 # 한 마디 최대 8분의... 4분음표 8개
DURS = [1, 2, 3, 4, 6, 8, 9, 12, 16, 18, 24, 30, 36, 42, 48, 60, 72, 96, 120, 144, 192]
TEMPO_EDGES = [60, 70, 80, 90, 100, 110, 120, 135, 150, 170]          # 11칸
DENS_EDGES = [0.75, 1.0, 1.25, 1.5, 1.75, 2.1, 3.0]                   # 4분음표당 소리 나는 시점 수(리듬 바쁨), 8칸 — PDMX 분위수
REG_EDGES = [48, 55, 60, 65, 70]                                      # 평균 음높이, 6칸
VEL_EDGES = [60, 66, 80]                                              # 4칸 (악보 대부분 64)
POLY_EDGES = [1.2, 2.5, 3.5, 4.5]                                     # 소리 날 때 동시에 울리는 음 수, 5칸
TIMESIGS = ["2/4", "3/4", "4/4", "6/8", "2/2", "3/8", "9/8", "12/8", "5/4", "other"]
FAMILIES = ["piano", "chrom_perc", "organ", "guitar", "bass", "strings", "ensemble", "brass", "reed",
            "pipe", "synth_lead", "synth_pad", "synth_fx", "ethnic", "percussive", "sfx", "drums"]
GENRES = ["classical", "pop", "rock", "jazz", "folk", "soundtrack", "religious", "electronic", "world",
          "children", "rnb", "latin", "country", "metal", "other", "ambient", "easylistening", "blues", "orchestral"]
# MidiCaps 분위기 꼬리표 중 쓰는 것
MOODS = ["melodic", "happy", "relaxing", "film", "energetic", "meditative", "dark", "epic", "love", "slow",
         "inspiring", "dream", "emotional", "drama", "ballad", "background", "romantic", "positive", "space", "motivational"]
CH_Q = ["maj", "min", "7", "maj7", "m7", "m7b5", "dim", "sus", "aug"]
CH_IV = {"maj": [0, 4, 7], "min": [0, 3, 7], "7": [0, 4, 7, 10], "maj7": [0, 4, 7, 11], "m7": [0, 3, 7, 10],
         "m7b5": [0, 3, 6, 10], "dim": [0, 3, 6], "sus": [0, 5, 7], "aug": [0, 4, 8]}
MODES = ["major", "minor"]

# 낱말 표
V = ["PAD", "BOS", "EOS", "SEP", "BAR"]
V += [f"TS_{t}" for t in TIMESIGS]
V += [f"TEMPO_{i}" for i in range(len(TEMPO_EDGES) + 1)]
V += [f"MODE_{m}" for m in MODES]
V += [f"DENS_{i}" for i in range(len(DENS_EDGES) + 1)]
V += [f"POLY_{i}" for i in range(len(POLY_EDGES) + 1)]
V += [f"REG_{i}" for i in range(len(REG_EDGES) + 1)]
V += [f"VEL_{i}" for i in range(len(VEL_EDGES) + 1)]
V += [f"GENRE_{g}" for g in GENRES]
V += [f"FAM_{f}" for f in FAMILIES]
V += [f"MOOD_{m}" for m in MOODS]
V += [f"SWING_{i}" for i in range(3)]
V += [f"CH_{r}_{q}" for r in range(12) for q in CH_Q] + ["CH_NC"]
V += [f"POS_{i}" for i in range(MAX_BAR)]
V += [f"PROG_{i}" for i in range(129)]           # 128 = 드럼
V += [f"NV_{i}" for i in range(8)]               # 음 세기 8칸
V += [f"P_{i}" for i in range(128)]
V += [f"D_{i}" for i in range(len(DURS))]
TOK = {t: i for i, t in enumerate(V)}
VOCAB = len(V)
PAD, BOS, EOS, SEP, BAR = (TOK[t] for t in ("PAD", "BOS", "EOS", "SEP", "BAR"))


def first(prefix):
    return TOK[prefix + "0"] if prefix + "0" in TOK else min(i for t, i in TOK.items() if t.startswith(prefix))


POS0, PROG0, NV0, P0, D0 = first("POS_"), first("PROG_"), first("NV_"), first("P_"), first("D_")
COND_RANGE = (TOK["TS_2/4"], POS0)               # 조건 낱말 구간
DUR_ARR = np.array(DURS)


def bin_of(v, edges):
    return int(np.searchsorted(edges, v, side="right"))


def family(prog):
    return 16 if prog == 128 else prog // 8


def dur_tok(d):
    return D0 + int(np.abs(DUR_ARR - d).argmin())


KS_MAJ = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
KS_MIN = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


def estimate_key(pitch, dur):
    """Krumhansl 조 추정 → (으뜸음, 'major'|'minor', 상관값)"""
    h = np.bincount(pitch % 12, weights=dur, minlength=12)
    if h.sum() == 0:
        return 0, "major", 0.0
    best = (-2, 0, "major")
    for r in range(12):
        for prof, m in ((KS_MAJ, "major"), (KS_MIN, "minor")):
            c = np.corrcoef(h, np.roll(prof, r))[0, 1]
            if c > best[0]:
                best = (c, r, m)
    return best[1], best[2], best[0]


_TPL = np.zeros((len(CH_Q) * 12, 12), np.float32)
for _ri in range(12):
    for _qi, _q in enumerate(CH_Q):
        for _iv in CH_IV[_q]:
            _TPL[_ri * len(CH_Q) + _qi, (_ri + _iv) % 12] = 1
_TPL_N = _TPL.sum(1)
CH0 = TOK["CH_0_maj"]; CH_NC = TOK["CH_NC"]


def chord_tok(seg, s, e):
    """구간 [s,e) 에 울리는 음(드럼 빼고) → 코드 낱말. 길이로 무게, 베이스음 덤, 4화음은 7음이 충분할 때만."""
    if len(seg) == 0:
        return CH_NC
    a = np.maximum(seg[:, 0], s); b = np.minimum(seg[:, 0] + seg[:, 3], e)
    w = np.maximum(0, b - a).astype(np.float32)
    if w.sum() <= 0:
        return CH_NC
    h = np.bincount(seg[:, 2] % 12, weights=w, minlength=12).astype(np.float32)
    h /= h.sum()
    sc = _TPL @ h - 0.45 * ((1 - _TPL) @ h) - 0.06 * (_TPL_N - 3)
    bass = seg[np.argmin(seg[:, 2] + (w <= 0) * 200), 2] % 12
    sc += 0.12 * (np.arange(len(sc)) // len(CH_Q) == bass)
    k = int(np.argmax(sc))
    return CH0 + k if sc[k] > 0.25 else CH_NC


def conditions(notes, bar_len, qpm, ts, genres, n_bars, moods=()):
    """notes (N,5): t, prog, pitch, dur, vel (조각 안 상대 시간). 조건 낱말 목록."""
    c = [f"TS_{ts if ts in TIMESIGS else 'other'}", f"TEMPO_{bin_of(qpm, TEMPO_EDGES)}"]
    pn = notes[notes[:, 1] != 128]
    if len(pn):
        _, mode, _ = estimate_key(pn[:, 2], pn[:, 3])
        c.append(f"MODE_{mode}")
    beats = max(1.0, n_bars * bar_len / Q)
    on = np.unique(pn[:, 0]) if len(pn) else np.zeros(0)
    c.append(f"DENS_{bin_of(len(on) / beats, DENS_EDGES)}")
    if len(pn):
        sounding = np.mean([((pn[:, 0] <= t) & (pn[:, 0] + pn[:, 3] > t)).sum() for t in on[:400]])
        c.append(f"POLY_{bin_of(sounding, POLY_EDGES)}")
        c.append(f"REG_{bin_of(pn[:, 2].mean(), REG_EDGES)}")
    if len(notes):
        c.append(f"VEL_{bin_of(notes[:, 4].mean(), VEL_EDGES)}")
    c += [f"GENRE_{g}" for g in genres]
    c += [f"FAM_{FAMILIES[f]}" for f in sorted({family(int(p)) for p in notes[:, 1]})]
    c += [f"MOOD_{m}" for m in moods]
    if len(pn):                                   # 8분 뒷박이 곧은 자리(6)냐 셋잇단 자리(8)냐
        ph = pn[:, 0] % Q
        n6, n8 = int((ph == 6).sum()), int((ph == 8).sum())
        if n6 + n8 >= 8:
            r = n8 / (n6 + n8)
            c.append(f"SWING_{0 if r < 0.3 else (1 if r < 0.7 else 2)}")
    return c


def encode_bars(notes, bar_starts, bar_lens, b0, budget):
    """b0 마디부터 낱말 budget 개 안에 들어가는 마디까지. → (낱말, 들어간 마디 수, 조각 음표(상대시간))"""
    out, used, sel = [], 0, []
    t_order = np.lexsort((notes[:, 2], notes[:, 1], notes[:, 0]))
    notes = notes[t_order]
    starts = notes[:, 0]
    for b in range(b0, len(bar_starts)):
        s, L = bar_starts[b], bar_lens[b]
        lo, hi = np.searchsorted(starts, s), np.searchsorted(starts, s + L)
        nb = notes[lo:hi]
        half = s + L // 2
        live = notes[(notes[:, 0] < s + L) & (notes[:, 0] + notes[:, 3] > s) & (notes[:, 1] != 128)]
        bt = [BAR, chord_tok(live, s, half), chord_tok(live, half, s + L)]
        prev_pos, prev_prog = -1, -1
        i = 0
        while i < len(nb):
            pos = int(nb[i, 0] - s)
            prog = int(nb[i, 1])
            j = i
            while j < len(nb) and nb[j, 0] == nb[i, 0] and nb[j, 1] == prog:
                j += 1
            grp = nb[i:j]
            if pos != prev_pos:
                bt.append(POS0 + min(pos, MAX_BAR - 1)); prev_pos = pos
            bt.append(PROG0 + prog)
            bt.append(NV0 + min(7, int(grp[:, 4].mean()) // 16))
            for n in grp:
                bt.append(P0 + int(n[2])); bt.append(dur_tok(int(n[3])))
            i = j
        if used + len(bt) > budget:
            break
        out += bt; used += len(bt)
        g = nb.copy(); g[:, 0] -= bar_starts[b0]; sel.append(g)
    nsel = np.concatenate(sel) if sel else np.zeros((0, 5), np.int64)
    return out, len(sel), nsel


def decode(ids, bar_len_default=48):
    """낱말 → 음표 목록 [(t, prog, pitch, dur, vel)] 와 마디 수. 문법에 안 맞는 낱말은 건너뜀."""
    notes, t_bar, bar_len, n_bars = [], -1, bar_len_default, 0
    pos, prog, vel, pitch = 0, 0, 64, None
    ts = None
    for i in ids:
        t = V[i]
        if t.startswith("TS_") and t != "TS_other":
            a, b = map(int, t[3:].split("/"))
            bar_len = a * 4 * Q // b
        elif i == BAR:
            t_bar = 0 if t_bar < 0 else t_bar + bar_len
            n_bars += 1; pos = 0
        elif t.startswith("POS_"):
            pos = int(t[4:])
        elif t.startswith("PROG_"):
            prog = int(t[5:])
        elif t.startswith("NV_"):
            vel = int(t[3:]) * 16 + 8
        elif t.startswith("P_"):
            pitch = int(t[2:])
        elif t.startswith("D_") and pitch is not None and t_bar >= 0:
            notes.append((t_bar + pos, prog, pitch, DURS[int(t[2:])], vel)); pitch = None
        elif i == EOS:
            break
    return notes, n_bars, bar_len
