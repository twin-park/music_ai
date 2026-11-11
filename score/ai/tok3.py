# 낱말 v3 (11-11) — tok.py(v2) 에서 달라진 것:
#   진행: SRC 에 classical 추가
#   선율: 머리에 SRC(재즈·팝·노래·클래식) 와 CT(강박 코드음 비율 = 얼마나 '안쪽'으로 조화롭게 부르나, 0~3) 추가
#  진행: BOS SRC MODE TS | BAR [SEC_x] (BEAT_b DEG_d Q_q)… | … EOS          (조 기준 도수 → 어느 조로도 씀)
#  선율: BOS SRC KIND FEEL TEMPO TS MODE DENS REG CT | BAR (CPOS CR CQ)… NR NQ (POS P D)… | … EOS
#        코드·머리 낱말은 '주어지는 것'이라 학습 손실에서 뺌, 선율 낱말(POS P D BAR EOS)만 배움
import numpy as np

TPB = 12
DUR_SET = [1, 2, 3, 4, 6, 8, 9, 12, 16, 18, 24, 30, 36, 48, 60, 72, 96]
P_LO, P_HI = 36, 96
TONES_Q = [[0, 4, 7], [0, 4, 7, 11], [0, 3, 7], [0, 3, 7, 10], [0, 4, 7, 10], [0, 4, 10], [0, 5, 7, 10], [0, 3, 6, 10], [0, 3, 6, 9], [0, 4, 8], [0, 3, 7, 11]]


def _vocab(groups):
    v = []
    for g in groups:
        v += g
    return v, {t: i for i, t in enumerate(v)}


SRCS = ["jazz", "pop", "song", "classical"]
# 출처 → 갈래 (진행 / 선율). EWLD(옛 스탠더드 노래)는 진행에선 '노래', 선율에선 재즈 머리 선율의 본보기로 씀
C_SRC = {"irb": "jazz", "wjazzd": "jazz", "lmd_jazz": "jazz", "pop909": "pop", "lmd_pop": "pop", "pdmx_pop": "pop", "ewld": "song",
         "lmd_song": "song", "pdmx_misc": "song", "pdmx_folk": "song", "pdmx_jazz": "song", "pdmx_classical": "classical"}
M_SRC = dict(C_SRC, ewld="jazz")

# ---------------- 진행 AI ----------------
C_VOCAB, C_ID = _vocab([["PAD", "BOS", "EOS", "BAR"], [f"SRC_{x}" for x in SRCS], ["MODE_maj", "MODE_min"],
                        ["TS_4", "TS_3"], [f"SEC_{x}" for x in "ABCDE"], [f"BEAT_{b}" for b in range(4)],
                        [f"DEG_{d}" for d in range(12)], [f"Q_{q}" for q in range(11)]])


def chord_tokens(s):
    t = ["BOS", f"SRC_{C_SRC[s['src']]}", "MODE_min" if s["minor"] else "MODE_maj", f"TS_{s['ts']}"]
    for b in s["bars"]:
        t.append("BAR")
        if b.get("sec"):
            t.append(f"SEC_{b['sec']}")
        last = None
        for pos, r, q in b["chords"]:
            beat = min(int(pos), s["ts"] - 1)
            d = (r - s["key"]) % 12
            if (d, q) == last:
                continue
            t += [f"BEAT_{beat}", f"DEG_{d}", f"Q_{q}"]
            last = (d, q)
    t.append("EOS")
    return [C_ID[x] for x in t]


# ---------------- 선율 AI ----------------
M_VOCAB, M_ID = _vocab([["PAD", "BOS", "EOS", "BAR"], [f"SRC_{x}" for x in SRCS], ["KIND_solo", "KIND_head"],
                        ["FEEL_swing", "FEEL_straight", "FEEL_latin"], ["TEMPO_slow", "TEMPO_med", "TEMPO_fast", "TEMPO_unk"],
                        ["TS_4", "TS_3"], ["MODE_maj", "MODE_min"], [f"DENS_{i}" for i in range(4)], [f"REG_{i}" for i in range(3)],
                        [f"CT_{i}" for i in range(4)],
                        [f"CPOS_{b}" for b in range(4)], [f"CR_{r}" for r in range(12)], [f"CQ_{q}" for q in range(11)], ["CNONE"],
                        [f"NR_{r}" for r in range(12)], [f"NQ_{q}" for q in range(11)], ["NNONE"],
                        [f"POS_{p}" for p in range(4 * TPB)], [f"P_{p}" for p in range(P_LO, P_HI + 1)], [f"D_{d}" for d in DUR_SET]])
M_GIVEN = set(i for t, i in M_ID.items() if t.split("_")[0] in ("CPOS", "CR", "CQ", "CNONE", "NR", "NQ", "NNONE", "SRC", "KIND", "FEEL",
                                                                  "TEMPO", "TS", "MODE", "DENS", "REG", "CT", "BOS", "PAD"))
M_HEAD = 10
DUR_IDX = np.array([min(range(len(DUR_SET)), key=lambda k: abs(DUR_SET[k] - d)) for d in range(200)])


def tempo_tok(bpm):
    if not bpm:
        return "TEMPO_unk"
    return "TEMPO_slow" if bpm < 95 else "TEMPO_med" if bpm < 160 else "TEMPO_fast"


def dens_of(npb):
    return 0 if npb < 2.5 else 1 if npb < 4.5 else 2 if npb < 7 else 3


def reg_of(mean_p):
    return 0 if mean_p < 62 else 1 if mean_p < 72 else 2


def ct_ratio(s):
    """강박(4/4 는 1·3박, 3/4 는 1박)에 놓인 선율음 중 코드 구성음 비율 — 곡이 얼마나 '안쪽'인가"""
    hit = tot = 0
    step = 2 if s["ts"] == 4 else 3
    for b in s["bars"]:
        for on, d, p in b["notes"]:
            if on % TPB or (on // TPB) % step:
                continue
            c = None
            for pos, r, q in b["chords"]:
                if pos <= on / TPB + 1e-6:
                    c = (r, q)
            if c is None:
                continue
            tot += 1
            hit += ((p - c[0]) % 12) in TONES_Q[c[1]]
    return hit / tot if tot >= 8 else None


def ct_of(x):
    return 0 if x < .6 else 1 if x < .72 else 2 if x < .84 else 3


def clean_notes(s):
    """학습용 정리: ① 스윙 8분(박 안에 0·8 또는 0·9 두 개만) → 0·6 ② 다음 음과 4틱 이내 틈이면 이어 붙여 레가토 ③ 단음으로(같은 시작은 높은 음만)"""
    ts = s["ts"] * TPB
    flat = []
    for bi, b in enumerate(s["bars"]):
        by_beat = {}
        for on, d, p in b["notes"]:
            by_beat.setdefault(on // TPB, []).append((on, d, p))
        for beat, ns in by_beat.items():
            offs = sorted({on % TPB for on, _, _ in ns})
            if len(ns) <= 2 and offs in ([0, 8], [0, 9], [8], [9], [0, 7], [7]):
                ns = [(on - on % TPB + 6, d, p) if on % TPB in (7, 8, 9) else (on, d, p) for on, d, p in ns]
            for on, d, p in ns:
                flat.append([bi * ts + on, d, p])
    flat.sort(key=lambda x: (x[0], -x[2]))
    mono = []
    for n in flat:
        if mono and mono[-1][0] == n[0]:
            continue
        mono.append(n)
    for a, b in zip(mono, mono[1:]):
        ioi = b[0] - a[0]
        if a[1] > ioi or ioi - a[1] <= 4:
            a[1] = ioi
    return mono


def melody_song(s):
    """곡 → (머리 낱말들, [마디별 낱말 묶음]) — 학습 때 창으로 잘라 씀"""
    ts = s["ts"] * TPB
    notes = clean_notes(s)
    if not notes:
        return None
    nb = len(s["bars"])
    per_bar = [[] for _ in range(nb)]
    for on, d, p in notes:
        k = on // ts
        if k < nb and P_LO <= p <= P_HI:
            per_bar[k].append((on - k * ts, d, p))
    if not any(per_bar):
        return None
    npb = np.mean([len(x) for x in per_bar])
    mp = np.mean([p for x in per_bar for _, _, p in x])
    ct = s.get("ct")
    if ct is None:
        ct = ct_ratio(s)
    head = ["BOS", f"SRC_{M_SRC[s['src']]}", f"KIND_{s['kind']}", f"FEEL_{s['feel']}", tempo_tok(s.get("tempo")), f"TS_{s['ts']}",
            "MODE_min" if s["minor"] else "MODE_maj", f"DENS_{dens_of(npb)}", f"REG_{reg_of(mp)}", f"CT_{ct_of(ct if ct is not None else .7)}"]
    bars = []
    for bi, b in enumerate(s["bars"]):
        t = ["BAR"]
        last = None
        for pos, r, q in b["chords"]:
            beat = min(int(round(pos)), s["ts"] - 1)
            if (r, q) == last:
                continue
            t += [f"CPOS_{beat}", f"CR_{r}", f"CQ_{q}"]
            last = (r, q)
        if not b["chords"]:
            t.append("CNONE")
        nxt = s["bars"][bi + 1]["chords"][0] if bi + 1 < nb and s["bars"][bi + 1]["chords"] else None
        t += [f"NR_{nxt[1]}", f"NQ_{nxt[2]}"] if nxt else ["NNONE"]
        for on, d, p in per_bar[bi]:
            t += [f"POS_{on}", f"P_{p}", f"D_{DUR_SET[DUR_IDX[min(d, 199)]]}"]
        bars.append([M_ID[x] for x in t])
    return [M_ID[x] for x in head], bars


# 조옮김 (학습 때 무작위로): CR/NR 은 근음만 돌리고, P 는 음높이를 올림
CR0, NR0, P0 = M_ID["CR_0"], M_ID["NR_0"], M_ID[f"P_{P_LO}"]


def transpose(arr, k):
    a = np.array(arr, dtype=np.int64)
    m = (a >= CR0) & (a < CR0 + 12)
    a[m] = CR0 + (a[m] - CR0 + k) % 12
    m = (a >= NR0) & (a < NR0 + 12)
    a[m] = NR0 + (a[m] - NR0 + k) % 12
    m = (a >= P0) & (a <= P0 + P_HI - P_LO)
    a[m] = np.clip(a[m] + k, P0, P0 + P_HI - P_LO)
    return a
