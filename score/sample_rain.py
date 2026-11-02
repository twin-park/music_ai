# 샘플 1곡 — "비 오는 날 재즈 발라드" (Eb장조 ♩=70, 4/4, 가벼운 스윙)
# 나중에 AI 가 써야 할 악보의 목표 모양. 선율·진행은 공식대로 손으로 짰고, 반주·베이스·브러시는 공식 함수로 채움.
#   형식: 도입 4 · A 8 · A' 8 · B 8 · A'' 8 · 끝맺음 4 + 마지막 화음
#   python sample_rain.py  → out/비오는날_재즈.txt (악보 글자)  → play.py 로 소리
import os, re, math, random
from theory import Key, Chord, rootless, guide, stack, near, fit, LETTERS, LETTER_PC
from notation import Sheet

HERE = os.path.dirname(os.path.abspath(__file__))
KEY, BPB, SWING = Key("Eb"), 4, 0.62
rng = random.Random(7)

# ---------------- 진행 (마디마다, 공백 = 2박씩) ----------------
CH = ["Gm7 C7b9", "Fm9 Bb13", "Gm7 Gb7", "Fm9 Bb7sus4",                                   # 도입: 반음 내려가는 3·7음 + 트라이톤(C7→Gb7)
      "Ebmaj9", "Ab13", "Gm7", "C7b9", "Fm9", "Bb13", "Gm7 C7b9", "Fm7 Bb7",                # A
      "Ebmaj9", "Ab13", "Gm7", "Gb7#11", "Fm9", "Bb7sus4 Bb7b9", "Ebmaj9", "Bbm7 Eb9",      # A'  (C7b9 → Gb7#11 대리, 끝은 IV 로 가는 2-5)
      "Abmaj9", "Abm7 Db9", "Ebmaj9", "Cm9", "Fm9", "Bb13", "Gm7 C7b9", "Fm7 Bb7",          # B   (IV → iv 단조 빌려오기)
      "Ebmaj9", "Ab13", "Gm7", "C7alt", "Fm9", "Bb13", "Gm7 Gb7", "Fm9 Bb7b9",              # A'' (C7alt · Gb7 로 색 바꿈)
      "Gm7 C7b9", "Fm9 Bb13", "Gm7 Gb7", "Fm9 Bb7sus4", "Ebmaj9"]                         # 끝맺음 iii-VI-ii-V 두 번 → I
SEC = [("도입", 0, 4), ("A", 4, 12), ("A'", 12, 20), ("B", 20, 28), ("A''", 28, 36), ("끝", 36, 41)]
SP = []
for b, s in enumerate(CH):
    toks = s.split()
    for i, t in enumerate(toks):
        SP.append((b * BPB + i * BPB / len(toks), b * BPB + (i + 1) * BPB / len(toks), Chord.parse(t)))


def span(t):
    for a, b, c in SP:
        if a - 1e-6 <= t < b - 1e-6:
            return a, b, c
    return SP[-1]


def chord(t):
    return span(t)[2]


def N(name):
    m = re.match(r"^([A-G])(bb|b|##|#)?(-?\d)$", name)
    L = LETTERS.index(m.group(1))
    return 12 * (int(m.group(3)) + 1) + LETTER_PC[L] + {"bb": -2, "b": -1, None: 0, "#": 1, "##": 2}[m.group(2)]


def mel(bar_map):
    """{마디: [(박, 길이, '음'), ...]} → [(절대박, 길이, midi)]"""
    return [(b * BPB + on, d, N(nm)) for b, xs in bar_map.items() for on, d, nm in xs]


# ---------------- 선율 (손으로 짠 것) ----------------
# 동기: 마디 1 "7-1-9-3 으로 올라가기" → 마디 2 긴 텐션(13) + 3음 내려오기 → 마디 3·4 한 칸 아래로 같은 꼴(반복진행)
INTRO_TOP = mel({0: [(0, 2, "F5"), (2, 2, "E5")], 1: [(0, 2, "Eb5"), (2, 2, "D5")],     # 7→3→7→3 반음씩 내려가는 가이드톤 줄
                 2: [(0, 2, "F5"), (2, 2, "Fb5")], 3: [(0, 2, "Eb5"), (2, 1, "C5"), (3, .5, "Bb4"), (3.5, .5, "C5")]})
A = {0: [(0, 1.5, "D5"), (1.5, .5, "Eb5"), (2, 1.5, "F5"), (3.5, .5, "G5")],
     1: [(0, 2.5, "F5"), (2.5, .5, "Eb5"), (3, .5, "C5"), (3.5, .5, "Eb5")],
     2: [(0, 1.5, "Bb4"), (1.5, .5, "C5"), (2, 1.5, "D5"), (3.5, .5, "F5")],
     3: [(0, 2.5, "Db5"), (2.5, .5, "C5"), (3, .5, "Bb4"), (3.5, .5, "G4")],
     4: [(0, 1, "Ab4"), (1, .5, "C5"), (1.5, .5, "Eb5"), (2, 1.5, "G5"), (3.5, .5, "Ab5")],
     5: [(0, 2, "G5"), (2, .5, "F5"), (2.5, .5, "Eb5"), (3, .5, "D5"), (3.5, .5, "C5")],
     6: [(0, 1, "Bb4"), (1, .5, "D5"), (1.5, .5, "F5"), (2, 1.5, "E5"), (3.5, .5, "Db5")],
     7: [(0, 2, "C5")]}
PIANO_A = mel({4 + k: v for k, v in A.items()})
# A'' = 같은 선율, 두 군데만 살짝 (마디 1 끝 앞당김, C7alt 에 맞춰 끝음) + 마지막 두 마디 새로
A2 = dict(A)
A2[0] = [(0, 1.5, "D5"), (1.5, .5, "Eb5"), (2, 1, "F5"), (3, .5, "G5"), (3.5, .5, "Ab5")]
A2[3] = [(0, 2.5, "Db5"), (2.5, .5, "C5"), (3, .5, "Bb4"), (3.5, .5, "Ab4")]
A2[6] = [(0, 1, "Bb4"), (1, .5, "D5"), (1.5, .5, "F5"), (2, 1.5, "Fb5"), (3.5, .5, "Db5")]
A2[7] = [(0, 2, "C5"), (2, .5, "D5"), (2.5, .5, "Cb5"), (3, .5, "Bb4"), (3.5, .5, "Ab4")]
PIANO_A2 = mel({28 + k: v for k, v in A2.items()})
# A' 색소폰: 같은 선율을 한 옥타브 아래로, 숨 쉬는 자리·끝을 바꿈 (Gb7#11 위에서도 같은 음이 맞게)
SAX_A1 = mel({11: [(3, .5, "Bb3"), (3.5, .5, "C4")],
              12: [(0, 1.5, "D4"), (1.5, .5, "Eb4"), (2, 1.5, "F4"), (3.5, .5, "G4")],
              13: [(0, 2, "F4"), (2, .5, "Gb4"), (2.5, .5, "F4"), (3, .5, "Eb4"), (3.5, .5, "C4")],
              14: [(0, 1.5, "Bb3"), (1.5, .5, "C4"), (2, 1.5, "D4"), (3.5, .5, "F4")],
              15: [(0, 2.5, "Db4"), (2.5, .5, "C4"), (3, .5, "Bb3"), (3.5, .5, "Ab3")],
              16: [(0, .5, "Ab3"), (.5, .5, "C4"), (1, .5, "Eb4"), (1.5, .5, "F4"), (2, 1.5, "G4"), (3.5, .5, "Ab4")],
              17: [(0, 2, "G4"), (2, .5, "F4"), (2.5, .5, "Eb4"), (3, .5, "D4"), (3.5, .5, "Cb4")],
              18: [(0, 1, "Bb3"), (1, .5, "C4"), (1.5, .5, "D4"), (2, 2, "G4")],
              19: [(0, 1.5, "Db4"), (1.5, .5, "F4"), (2, 1.5, "G4"), (3.5, .5, "F4")]})
# B: 색소폰 2마디 → 피아노 2마디 대답 → 색소폰 2마디 → 둘이 같이(옥타브)
SAX_B = mel({20: [(.5, .5, "Eb4"), (1, 1, "G4"), (2, .5, "Ab4"), (2.5, 1.5, "C5")],
             21: [(0, 1.5, "Cb5"), (1.5, .5, "Bb4"), (2, 1, "Ab4"), (3, .5, "F4"), (3.5, .5, "Eb4")],
             24: [(0, 1.5, "C5"), (1.5, .5, "Bb4"), (2, 1, "Ab4"), (3, 1, "G4")],
             25: [(0, 1.5, "D4"), (1.5, .5, "F4"), (2, 2, "G4")],
             26: [(0, 1, "Bb3"), (1, .5, "D4"), (1.5, .5, "F4"), (2, 1.5, "E4"), (3.5, .5, "Db4")],
             27: [(0, 2, "C4")]})
PIANO_B = mel({22: [(0, 1, "G5"), (1, .5, "F5"), (1.5, .25, "Eb5"), (1.75, .25, "D5"), (2, .5, "C5"), (2.5, .5, "Bb4"), (3, 1, "D5")],
               23: [(0, .5, "Eb5"), (.5, .5, "D5"), (1, .5, "Eb5"), (1.5, .5, "G5"), (2, 1.5, "Bb5"), (3.5, .5, "Ab5")]})
PIANO_B_UNI = [(t, d, p + 12) for t, d, p in SAX_B if 26 * 4 <= t < 27 * 4]
PIANO_FILL = mel({27: [(2, .5, "F4"), (2.5, .5, "Ab4"), (3, .5, "C5"), (3.5, .5, "Bb4")]})
# A'' 색소폰 대선율: 3·7음이 반음씩 내려가는 가이드톤 줄 G→Gb→F→E→Eb→D
SAX_A2 = mel({28: [(0, 4, "G3")], 29: [(0, 4, "Gb3")], 30: [(0, 4, "F3")], 31: [(0, 4, "E3")], 32: [(0, 4, "Eb3")], 33: [(0, 3, "D3")]})
SAX_END = mel({36: [(0, 1.5, "D4"), (1.5, .5, "F4"), (2, 1.5, "E4"), (3.5, .5, "Db4")], 37: [(0, 2, "C4"), (2, 2, "D4")],
               40: [(.25, 5.5, "G3")]})
PIANO_END = mel({38: [(0, 1, "Bb5"), (1, .5, "A5"), (1.5, .5, "F5"), (2, 1.5, "Ab5"), (3.5, .5, "Fb5")],
                 39: [(0, 2, "Eb5"), (2, 1, "F5"), (3, 1, "Eb5")]})

ev = {"피아노 오른손": [], "피아노 왼손": [], "테너색소폰": [], "베이스": [], "브러시": []}
pedal = []


def add(part, t, d, p, v):
    n = [t, d, p, int(max(1, min(127, v)))]
    ev[part].append(n)
    return n


def arc(t, base, amp=7):
    """4마디 숨: 셋째 마디까지 커졌다 넷째 마디에 가라앉음"""
    ph = ((t / BPB) % 4) / 4
    return base + amp * math.sin(math.pi * min(1, ph * 1.25)) - 2


# ---------------- 피아노: 선율 + 아래 화음 (드롭2) ----------------
def block_under(m, c, n=3, lo=50):
    """선율음 m 아래로 화음음 n 개 (가까이 쌓은 뒤 위에서 둘째를 옥타브 내림). 선율 바로 반음 아래는 뺌."""
    pcs = [x for x in dict.fromkeys(rootless(c) + c.tones()) if x != m % 12 and x != (m - 1) % 12]
    if c.q in ("maj7", "maj9", "6", "69") and (m % 12) == c.root:
        pcs = [x for x in pcs if x != (c.root + 11) % 12]                 # 선율이 근음이면 장7음 빼기(반음 부딪힘)
    below = []
    for p in sorted({m - ((m - pc) % 12 or 12) for pc in pcs}, reverse=True):   # 이웃한 두 음이 반음으로 붙지 않게
        if all(abs(p - q) > 1 for q in below) and len(below) < n:
            below.append(p)
    if len(below) >= 3 and below[0] - 12 >= lo:
        below = below[1:] + [below[0] - 12]                               # 드롭2
    return [p for p in below if p >= lo - 2]


def piano_melody(notes, base, octave=False, line=False):
    for t, d, m in notes:
        c = chord(t)
        a, b, _ = span(t)
        v = arc(t, base) + (3 if d >= 1 else 0) + rng.randint(-2, 2)
        add("피아노 오른손", t, d, m, v)
        if octave and d >= .5:
            add("피아노 오른손", t, d, m - 12, v - 12)
        strong = d >= 1 or abs(t - a) < 1e-6 or abs((t % BPB) - 2) < 1e-6
        if line:
            strong = abs(t - a) < 1e-6 and d >= .5
        if strong:
            hs = block_under(m, c, 2 if octave else 3, lo=52 if not octave else 56)
            if octave:
                hs = [h for h in hs if m - 12 < h < m]                    # 옥타브 사이 안쪽 음만
            for h in hs:
                add("피아노 오른손", t + 0.02, d, h, v - 17)
            # 긴 선율음 아래 화음이 바뀌면: 위는 그대로, 안쪽만 바꿈 (같은 위치 · 안쪽 화음만 바뀜)
            if t + d > b + 1e-6:
                c2 = chord(b)
                for h in block_under(m, c2, 2 if octave else 3, lo=52):
                    if not octave or m - 12 < h < m:
                        add("피아노 오른손", b + 0.02, t + d - b, h, v - 19)
        elif not line and d >= .5 and rng.random() < .35:                 # 8분 음에 가끔 3도/6도 아래 한 음
            cands = [m - k for k in (3, 4, 8, 9) if (m - k) % 12 in c.tones() + c.tensions()]
            if cands:
                add("피아노 오른손", t, d, cands[0], v - 18)


def lh_guide(b0, b1, base=46, shell=False):
    """왼손: 베이스가 근음을 맡으니 3·7음 두 개 (그림 1 왼손처럼). 도입은 근음+7음/10도."""
    prev = None
    for a, b, c in SP:
        if not (b0 * BPB - 1e-6 <= a < b1 * BPB - 1e-6):
            continue
        if shell:
            r = fit(c.root, 36, 47)
            top = guide(c)[1 if (len(pedal) % 2) else 0]
            v = [r, fit(top, r + 7, r + 16)]
        else:
            v = stack(guide(c), 46, 62, prev)
        prev = v
        vel = base + rng.randint(-3, 3)
        for p in v:
            add("피아노 왼손", a, b - a, p, vel)
        if b - a >= 4 and rng.random() < .35 and not shell:               # 긴 화음은 2박 뒷박에 살짝 다시
            for p in v:
                add("피아노 왼손", a + 2.5, b - a - 2.5, p, vel - 8)


def pedals(b0, b1):
    for a, b, c in SP:
        if b0 * BPB - 1e-6 <= a < b1 * BPB - 1e-6:
            cuts = [a, a + 2, b] if b - a >= 4 else [a, b]
            for x, y in zip(cuts, cuts[1:]):
                pedal.append((x + 0.04, y - 0.03))


# ---------------- 피아노 반주 (색소폰이 선율일 때): 근음 없는 4음 + 발라드 반주 리듬 ----------------
COMP1 = [[(0, 3.5)], [(0, 1.5), (2.5, 1.5)], [(-.5, 2.5)], [(0, .5), (1.5, 2.5)], [(1, 2.5)]]
COMP2 = [[(0, 2), (2, 2)], [(0, 1.5), (1.5, 2.5)], [(-.5, 2), (2, 2)]]


def comp(bars, base=48, lead=()):
    """lead: 그때 선율(색소폰) 음들 — 선율과 반음·단9도로 부딪히는 반주음은 빼고, 앞당겨 치면 앞 화음은 거기서 끊음"""
    prev, last, ring = None, None, []
    for bar in bars:
        two = len(CH[bar].split()) > 1
        pats = [p for p in (COMP2 if two else COMP1) if p is not last]
        if bar == bars[0] or (bar - 1) not in bars:
            pats = [p for p in pats if p[0][0] >= 0]
        pat = rng.choice(pats)
        last = pat
        for k, (on, d) in enumerate(pat):
            t = bar * BPB + on
            c = chord(t + 0.5 if on < 0 or on % 1 else t)                 # 앞당겨 치면 다음 화음
            v = stack(rootless(c), 50, 68, prev)
            if v[1] - v[0] == 1 and v[0] < 60:                              # 낮은 자리 반음 뭉침은 위로 올림
                v = sorted(v[1:] + [v[0] + 12])
            prev = v
            for n in ring:
                if n[0] + n[1] > t - .03:
                    n[1] = max(.1, t - .03 - n[0])
            ov = [p for lt, ld, p in lead if lt < t + d and lt + ld > t]
            v = [q for q in v if not any((p - q) % 12 == 1 or (q - p) in (1, 13) for p in ov)]
            ring = [add("피아노 오른손" if p >= 60 else "피아노 왼손", t + 0.01 * rng.random(), d, p,
                        base + (4 if k == 0 else 0) + rng.randint(-3, 3)) for p in v]


# ---------------- 베이스 ----------------
def two_feel(b0, b1, base=74, push=.3):
    p = 39
    for bar in range(b0, b1):
        for half in (0, 2):
            t = bar * BPB + half
            a, b, c = span(t)
            if abs(t - a) < 1e-6:
                q = min([x for x in range(29, 47) if x % 12 == c.root], key=lambda x: abs(x - p))
            else:
                fifth = (c.root + 7) % 12
                q = min([x for x in range(29, 47) if x % 12 in (fifth, c.iv(3))], key=lambda x: abs(x - p) + (0 if x % 12 == fifth else 2))
            nxt = chord(t + 2)
            if rng.random() < push and bar * BPB + half + 2 < b1 * BPB:   # 8분 접근음으로 다음 근음 밀어주기
                tgt = min([x for x in range(29, 47) if x % 12 == nxt.root], key=lambda x: abs(x - q))
                add("베이스", t, 1.45, q, base + rng.randint(-4, 4))
                add("베이스", t + 1.5, .45, tgt + rng.choice([-1, 1]), base - 8)
            else:
                add("베이스", t, 1.9, q, base + rng.randint(-4, 4))
            p = q


def walking(b0, b1, base=76):
    p = 39
    for beat in range(b0 * BPB, b1 * BPB):
        a, b, c = span(beat)
        if abs(beat - a) < 1e-6:
            pcs = [c.root] if (rng.random() < .85 or b - a < 4) else [c.iv(3)]
            q = min([x for x in range(28, 49) if x % 12 in pcs], key=lambda x: abs(x - p) + (3 if x == p else 0))
        elif beat + 1 >= b - 1e-6:                                         # 다음 화음 바로 앞: 반음 / 5도 접근
            nr = min([x for x in range(28, 49) if x % 12 == chord(b).root], key=lambda x: abs(x - p))
            opts = [nr + 1, nr - 1, nr + 7 if nr + 7 <= 48 else nr - 5]
            q = rng.choices(opts, weights=[3, 3, 2])[0]
            if q == p:
                q = opts[1] if opts[0] == p else opts[0]
        else:
            nr = min([x for x in range(28, 49) if x % 12 == chord(b).root], key=lambda x: abs(x - p))
            way = 1 if nr > p else -1
            sc = [x for x in range(28, 49) if x % 12 in c.scale(KEY)]
            ct = [x for x in sc if x % 12 in c.tones()]
            pool = [x for x in (ct if rng.random() < .6 else sc) if 1 <= (x - p) * way <= 4]
            q = rng.choice(pool) if pool else min(sc, key=lambda x: abs(x - (p + way * 2)))
        q = fit(q, 28, 48)
        add("베이스", beat, .92, q, base + (5 if beat % 2 else 0) + rng.randint(-5, 4))
        p = q


# ---------------- 브러시 ----------------
def brush(bar, kind, lvl=0, fill=False):
    t0 = bar * BPB
    if kind == "ballad":
        add("브러시", t0, 2, 40, 36 + lvl * 4 + rng.randint(-3, 3))       # 휘젓기
        add("브러시", t0 + 2, 2, 40, 33 + lvl * 4 + rng.randint(-3, 3))
        for on in (1, 3):
            add("브러시", t0 + on, .2, 38, 40 + lvl * 4 + rng.randint(-4, 4))     # 2·4박 탭
            add("브러시", t0 + on, .2, 44, 28 + rng.randint(-3, 3))               # 하이햇 발
        if lvl >= 1:
            for on in (1 + 2 / 3, 3 + 2 / 3):
                if rng.random() < .5:
                    add("브러시", t0 + on, .15, 38, 26 + rng.randint(-3, 3))
    elif kind == "swing":                                                   # 브러시로 스윙 (딩 딩다 딩 딩다)
        add("브러시", t0, 2, 40, 32); add("브러시", t0 + 2, 2, 40, 30)
        for on in (0, 1, 1 + 2 / 3, 2, 3, 3 + 2 / 3):
            acc = 8 if on in (1, 3) else (-8 if on % 1 else 0)
            add("브러시", t0 + on, .2, 38, 44 + lvl * 2 + acc + rng.randint(-4, 4))
        for on in (1, 3):
            add("브러시", t0 + on, .2, 44, 30 + rng.randint(-3, 3))
    if fill:
        for k, on in enumerate((3, 3 + 1 / 3, 3 + 2 / 3)):
            add("브러시", t0 + on, .15, 38, 38 + lvl * 4 + 6 * k)


# ---------------- 조립 ----------------
# 도입: 피아노 혼자 (선율 줄 + 아래 화음, 왼손 근음+7음)
piano_melody(INTRO_TOP, 58)
lh_guide(0, 4, 40, shell=True); pedals(0, 4)
add("브러시", 14, 2, 40, 26)                                               # 도입 끝에 브러시 한 번 쓸어 밴드 부르기
# A: 피아노 선율, 베이스 2박, 브러시 발라드
piano_melody(PIANO_A, 66); lh_guide(4, 12, 46); pedals(4, 12)
two_feel(4, 12, push=.25)
for bar in range(4, 12):
    brush(bar, "ballad", 0, fill=(bar == 11))
# A': 색소폰 선율, 피아노 반주
for t, d, p in SAX_A1:
    add("테너색소폰", t, d, p, arc(t, 74) + (3 if d >= 1 else 0))
comp(list(range(12, 20)), 47, SAX_A1)
two_feel(12, 18, push=.4); walking(18, 20, 72)
for bar in range(12, 20):
    brush(bar, "ballad", 1, fill=(bar == 19))
# B: 주고받기
for t, d, p in SAX_B:
    add("테너색소폰", t, d, p, arc(t, 80) + (3 if d >= 1 else 0))
comp([20, 21], 50, SAX_B); comp([24, 25], 50, SAX_B)
piano_melody(PIANO_B, 70, line=True); lh_guide(22, 24, 46); pedals(22, 24)
piano_melody(PIANO_B_UNI, 70, line=True); lh_guide(26, 28, 48)
piano_melody(PIANO_FILL, 60, line=True)
walking(20, 28, 78)
for bar in range(20, 28):
    brush(bar, "swing", 2, fill=(bar == 27))
add("브러시", 28 * 4, .3, 39, 52)                                          # A'' 들어갈 때 슬랩 한 번
# A'': 피아노 옥타브 선율 + 색소폰 가이드톤 대선율
piano_melody(PIANO_A2, 70, octave=True); lh_guide(28, 36, 46); pedals(28, 36)
for t, d, p in SAX_A2:
    add("테너색소폰", t, d, p, 58 + rng.randint(-2, 2))
walking(28, 34, 72); two_feel(34, 36, push=.3)
for bar in range(28, 36):
    brush(bar, "ballad", 1, fill=(bar == 35))
# 끝맺음: 색소폰 → 피아노 대답 → 느려지며 Eb 장9 화음
for t, d, p in SAX_END:
    add("테너색소폰", t, d, p, 66 if t < 40 * 4 else 50)
comp([36, 37], 44, SAX_END)
piano_melody(PIANO_END, 60); lh_guide(38, 40, 42); pedals(38, 40)
two_feel(36, 40, 66, push=.2)
for bar in range(36, 40):
    brush(bar, "ballad", 0)
for k, p in enumerate([39, 46, 55, 62, 65, 70, 74]):                     # 마지막 화음: 아래부터 굴려 펼치기
    add("피아노 왼손" if p < 60 else "피아노 오른손", 160 + k * .09, 6, p, 50 - k * 2 if p < 60 else 52)
pedal.append((160.02, 166.5))
add("베이스", 160, 6, 39, 64)
add("브러시", 160, 4, 40, 30); add("브러시", 160, 4, 51, 30)


# ---------------- 박 → 초 (스윙 · 템포) ----------------
def swing(b):
    f0 = math.floor(b + 1e-9)
    f = b - f0
    return f0 + (f * 2 * SWING if f <= .5 else SWING + (f - .5) * 2 * (1 - SWING))


def bpm(b):
    if b < 12:
        return 64
    if b < 15:
        return 64 - 7 * (b - 12) / 3                                       # 도입 끝 살짝 늦춤
    if b < 16:
        return 68
    if b < 152:
        return 70
    if b < 160:
        return 70 - 20 * (b - 152) / 8                                     # 끝 두 마디 느려짐
    return 46


_T = [0.0]
for i in range(1, 172 * 96):
    _T.append(_T[-1] + 60 / bpm((i - .5) / 96) / 96)


def sec(b):
    i = b * 96
    k = int(i)
    return _T[k] + (_T[k + 1] - _T[k]) * (i - k)


sh = Sheet("비 오는 날 재즈 발라드 (샘플)", "Eb")
sh.notes_text = [
    "편성: 피아노(실제 녹음) · 테너 색소폰 · 어쿠스틱 베이스 · 브러시 드럼",
    "형식: 도입4(피아노 혼자) → A8(피아노 선율) → A'8(색소폰이 같은 선율 변주) → B8(색소폰↔피아노 2마디씩 주고받기) → A''8(피아노 옥타브 선율 + 색소폰 대선율) → 끝4 + 마지막 화음",
    "진행 공식: I-IV7-iii-VI7-ii-V (2-5-1), 트라이톤 대리(C7→Gb7), 반음 내려가는 3·7음(도입·A''), IV→iv 단조 빌려오기(B), 끝맺음 iii-VI-ii-V 두 번",
    "피아노 공식: 선율 아래 드롭2 화음 · 왼손 3·7음(가이드톤) · 긴 선율음 아래 안쪽 화음만 바꾸기 · A'' 옥타브 선율 · 반주는 근음 없는 4음 + 앞당김",
    "베이스: 2박(2-feel) → B 부터 워킹(4분, 반음 접근) / 브러시: 휘젓기 + 2·4박 탭 → B 는 브러시 스윙",
    "같은 마디를 일부러 피하지 않음: 같은 동기를 조금씩 바꿔 되풀이 (A → A' → A'')",
]
sh.info = {"템포": "70 (도입 64, 끝 두 마디 느려짐)", "박자": "4/4", "스윙": f"{SWING} (8분 뒷박을 늦춤)", "잔향": "2.6"}
sh.chords = [(round(sec(a), 3), round(sec(b) if b < 164 else sec(166), 3), c) for a, b, c in SP]
for part, xs in ev.items():
    pp = sh.part(part, drum=(part == "브러시"))
    for t, d, p, v in sorted(xs):
        if part == "브러시":
            t0, t1 = sec(t), sec(t + d)
        else:
            t0, t1 = sec(swing(t)), sec(swing(t + d) - .02)
        pp.notes.append((round(t0, 3), round(max(t1, t0 + .06), 3), p, v))
sh.parts["피아노 오른손"].pedals = [(round(sec(a), 3), round(sec(b), 3)) for a, b in pedal]

if __name__ == "__main__":
    out = os.path.join(HERE, "out", "비오는날_재즈.txt")
    sh.save(out)
    # 선율 점검: 강박·긴 음이 화음음/텐션인지
    bad = 0
    for name, xs in (("피아노A", PIANO_A), ("피아노A''", PIANO_A2), ("색소폰A'", SAX_A1), ("색소폰B", SAX_B), ("피아노B", PIANO_B),
                     ("도입", INTRO_TOP), ("끝 피아노", PIANO_END), ("끝 색소폰", SAX_END), ("대선율", SAX_A2)):
        for t, d, p in xs:
            c = chord(t)
            if (d >= 1 or t % 2 == 0) and p % 12 not in c.tones() + c.tensions():
                bad += 1
                print(f"  확인: {name} 마디{int(t // 4)} 박{t % 4} {KEY.note_text(p)} ↔ {c.name(KEY)}")
    print(f"악보 → {out}  (음 {sum(len(p.notes) for p in sh.parts.values())}개, 길이 {sec(166):.0f}초, 강박 비화음 {bad})")
