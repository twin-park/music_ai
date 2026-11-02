# 낱말 만들기 — 진행 AI 와 선율 AI 두 개
#  진행: BOS SRC MODE TS | BAR [SEC_x] (BEAT_b DEG_d Q_q)… | … EOS          (조 기준 도수 → 어느 조로도 씀)
#  선율: BOS KIND FEEL TEMPO TS MODE DENS REG | BAR (CPOS CR CQ)… NR NQ (POS P D)… | … EOS
#        코드·앞 마디 낱말은 '주어지는 것'이라 학습 손실에서 뺌, 선율 낱말(POS P D BAR EOS)만 배움
import numpy as np

TPB = 12
DUR_SET = [1, 2, 3, 4, 6, 8, 9, 12, 16, 18, 24, 30, 36, 48, 60, 72, 96]
P_LO, P_HI = 36, 96


def _vocab(groups):
    v = []
    for g in groups:
        v += g
    return v, {t: i for i, t in enumerate(v)}


# ---------------- 진행 AI ----------------
C_VOCAB, C_ID = _vocab([["PAD", "BOS", "EOS", "BAR"], ["SRC_jazz", "SRC_pop", "SRC_song"], ["MODE_maj", "MODE_min"],
                        ["TS_4", "TS_3"], [f"SEC_{x}" for x in "ABCDE"], [f"BEAT_{b}" for b in range(4)],
                        [f"DEG_{d}" for d in range(12)], [f"Q_{q}" for q in range(11)]])
C_SRC = {"irb": "SRC_jazz", "pop909": "SRC_pop", "ewld": "SRC_song", "wjazzd": "SRC_jazz",
         "lmd_jazz": "SRC_jazz", "lmd_pop": "SRC_pop", "lmd_song": "SRC_song"}       # 10-31 밤: Lakh 리드시트 추가


def chord_tokens(s):
    t = ["BOS", C_SRC[s["src"]], "MODE_min" if s["minor"] else "MODE_maj", f"TS_{s['ts']}"]
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
M_VOCAB, M_ID = _vocab([["PAD", "BOS", "EOS", "BAR"], ["KIND_solo", "KIND_head"], ["FEEL_swing", "FEEL_straight", "FEEL_latin"],
                        ["TEMPO_slow", "TEMPO_med", "TEMPO_fast", "TEMPO_unk"], ["TS_4", "TS_3"], ["MODE_maj", "MODE_min"],
                        [f"DENS_{i}" for i in range(4)], [f"REG_{i}" for i in range(3)],
                        [f"CPOS_{b}" for b in range(4)], [f"CR_{r}" for r in range(12)], [f"CQ_{q}" for q in range(11)], ["CNONE"],
                        [f"NR_{r}" for r in range(12)], [f"NQ_{q}" for q in range(11)], ["NNONE"],
                        [f"POS_{p}" for p in range(4 * TPB)], [f"P_{p}" for p in range(P_LO, P_HI + 1)], [f"D_{d}" for d in DUR_SET]])
M_GIVEN = set(i for t, i in M_ID.items() if t.split("_")[0] in ("CPOS", "CR", "CQ", "CNONE", "NR", "NQ", "NNONE", "KIND", "FEEL",
                                                                  "TEMPO", "TS", "MODE", "DENS", "REG", "BOS", "PAD"))
DUR_IDX = np.array([min(range(len(DUR_SET)), key=lambda k: abs(DUR_SET[k] - d)) for d in range(200)])


def tempo_tok(bpm):
    if not bpm:
        return "TEMPO_unk"
    return "TEMPO_slow" if bpm < 95 else "TEMPO_med" if bpm < 160 else "TEMPO_fast"


def dens_of(npb):
    return 0 if npb < 2.5 else 1 if npb < 4.5 else 2 if npb < 7 else 3


def reg_of(mean_p):
    return 0 if mean_p < 62 else 1 if mean_p < 72 else 2


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
    npb = np.mean([len(x) for x in per_bar])
    mp = np.mean([p for x in per_bar for _, _, p in x])
    head = ["BOS", f"KIND_{s['kind']}", f"FEEL_{s['feel']}", tempo_tok(s.get("tempo")), f"TS_{s['ts']}",
            "MODE_min" if s["minor"] else "MODE_maj", f"DENS_{dens_of(npb)}", f"REG_{reg_of(mp)}"]
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
