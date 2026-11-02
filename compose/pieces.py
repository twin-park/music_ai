# 곡 설계: 형식(도입-A-A'-B-A''-끝) · 코드 진행 · 편성. 클래식 3 · 재즈 3. (EDM 은 edm.py)
import random
from theory import Score, prog, chord_at, voicing, near
from melody import Melody, bebop_line
import parts as P

# 악기 설정: 엔진 · 크기dB · 팬 · 리버브 · 저역컷
PIANO = ("piano",)
SSO = lambda pr: ("sf", "sso", 0, pr, False)
GU = lambda pr: ("sf", "gu", 0, pr, False)
GUKIT = lambda kit: ("sf", "gu", 128, kit, True)


def add_mel(sc, notes, inst, vel, accent=8, rng=None, legato=1.0):
    rng = rng or random.Random(3)
    for k, (t, d, p) in enumerate(notes):
        strong = abs(t - round(t)) < 1e-3
        sc.add(t, d * legato, p, vel + (accent if strong else 0) + rng.randint(-5, 5), inst)


def rubato(sc, bars, base, phrase=4, dip=0.08, final=0.25):
    """프레이즈 끝마다 살짝 늦췄다 돌아오기 + 마지막 리타르단도"""
    pts = []
    for b in range(bars + 1):
        t = b * sc.bpb
        k = 1 - dip if (b % phrase == 0 and b > 0) else 1.0
        pts.append((t, base * k))
        pts.append((t + sc.bpb * 0.5, base))
    pts.append(((bars - 2) * sc.bpb, base)); pts.append((bars * sc.bpb, base * (1 - final)))
    sc.tempo_pts = sorted(pts)


# ======================= 클래식 =======================
def lullaby(seed=11):
    """아이 재우기 — 피아노 자장가 (F장조 3/4). 중간엔 플루트가 선율, 뒤엔 현악이 감쌈"""
    r = random.Random(seed)
    sc = Score(64, 3)
    spec = ("F | F | "                                               # 도입
            "F | Dm | Bb | C | F | Bb | Gm7 C7 | F | "                 # A
            "F | Dm | Gm7 | C | Am | Dm | Bb C7 | F | "                # A'
            "Bb | F/A | Gm | C | Am | Dm | Gm7 | C7 | "                # B
            "F | Dm | Bb | C | F/C | C7 | F | F")                      # A'' + 끝
    pr = prog(spec, 3)
    nb = 34
    P.piano_broken(sc, pr, 0, nb - 1, "piano", [0, 2, 4, 2, 3, 2], vel=44, rng=r)
    sc.add((nb - 1) * 3, 3, 41, 40, "piano"); sc.add((nb - 1) * 3, 3, 53, 38, "piano"); sc.add((nb - 1) * 3, 3, 69, 44, "piano")
    m = Melody(5, "major", 65, 84, "lullaby34", 3, r)
    a1, mot = m.phrase(pr, 2, 4, cadence="half"); a2, _ = m.phrase(pr, 6, 4, mot, cadence="full", level=0.3)
    add_mel(sc, a1 + a2, "piano", 64, rng=r)
    b1, _ = m.phrase(pr, 10, 4, mot, cadence="half", level=0.6); b2, _ = m.phrase(pr, 14, 4, mot, cadence="full", level=0.6)
    add_mel(sc, b1 + b2, "piano", 66, rng=r)
    m.lo, m.hi = 67, 88
    c1, mot2 = m.phrase(pr, 18, 4, cadence="half"); c2, _ = m.phrase(pr, 22, 4, mot2, cadence="half", level=0.4)
    add_mel(sc, c1 + c2, "flute", 70, rng=r, legato=1.02)
    m.lo, m.hi = 65, 84
    d1, _ = m.phrase(pr, 26, 4, mot, cadence="half", level=0.45); d2, _ = m.phrase(pr, 30, 3, mot, cadence="full", level=0.3)
    add_mel(sc, d1 + d2, "piano", 60, rng=r)
    voices = [("cello", 36, 57), ("viola", 48, 67), ("violin2", 55, 74)]
    P.strings_pad(sc, pr, 10, 18, voices, vel=46); P.strings_pad(sc, pr, 18, 26, voices, vel=52); P.strings_pad(sc, pr, 26, nb, voices, vel=44)
    for v in ("cello", "viola", "violin2"):
        P.swell_cc(sc, v, 10, nb, 45, 95, 4)
    rubato(sc, nb, 64, phrase=4, dip=0.06, final=0.3)
    sc.humanize("piano", 7, 3, rng=r)
    insts = {"piano": (PIANO, 0, 0, 0.32, 0), "flute": (SSO(14), -3, 0.25, 0.42, 200),
             "cello": (SSO(8), -9, -0.35, 0.5, 60), "viola": (SSO(6), -11, 0.3, 0.5, 120), "violin2": (SSO(4), -12, 0.45, 0.5, 200)}
    return sc, insts


def nocturne(seed=21):
    """비 오는 길 — 피아노 녹턴 (가단조 4/4). 흐르는 왼손, 뒤에 첼로 대선율"""
    r = random.Random(seed)
    sc = Score(66, 4)
    spec = ("Am | Am | "
            "Am | F | Dm | E7 | Am | C/G | Dm/F E7 | Am | "
            "Am | Am/G | F | E7 | Dm | G7 | Cmaj7 F | E7 | "
            "C | G/B | Am | Em | F | C/E | Dm7 | E7sus4 E7 | "
            "Am | F | Dm | E7 | Am/E | F | Dm E7 | Am | Am")
    pr = prog(spec, 4)
    nb = 35
    P.piano_broken(sc, pr, 0, nb - 1, "piano", [0, 1, 2, 3, 4, 3, 2, 1], vel=42, rng=r)
    sc.add((nb - 1) * 4, 4, 45, 40, "piano"); sc.add((nb - 1) * 4, 4, 57, 36, "piano"); sc.add((nb - 1) * 4, 4, 64, 40, "piano"); sc.add((nb - 1) * 4, 4, 72, 46, "piano")
    m = Melody(9, "harm", 64, 86, "nocturne", 4, r)
    out = []
    a1, mot = m.phrase(pr, 2, 4, cadence="half"); a2, _ = m.phrase(pr, 6, 4, mot, cadence="full", level=0.3)
    b1, _ = m.phrase(pr, 10, 4, mot, cadence="half", level=0.55); b2, _ = m.phrase(pr, 14, 4, mot, cadence="half", level=0.5)
    m.mode = "major"; m.key = 0
    c1, mot2 = m.phrase(pr, 18, 4, cadence="half"); c2, _ = m.phrase(pr, 22, 4, mot2, cadence="half", level=0.4)
    m.mode = "harm"; m.key = 9
    d1, _ = m.phrase(pr, 26, 4, mot, cadence="half", level=0.4); d2, _ = m.phrase(pr, 30, 4, mot, cadence="full", level=0.3)
    add_mel(sc, a1 + a2 + b1 + b2 + c1 + c2 + d1 + d2, "piano", 62, rng=r)
    cm = Melody(9, "harm", 45, 64, "adagio", 4, r)
    e1, cmot = cm.phrase(pr, 26, 4, cadence="half"); e2, _ = cm.phrase(pr, 30, 4, cmot, cadence="full", level=0.3)
    add_mel(sc, e1 + e2, "cello", 72, accent=4, rng=r, legato=1.03)
    P.swell_cc(sc, "cello", 26, nb, 60, 112, 2)
    voices = [("vbass", 28, 45), ("viola", 48, 64), ("violin2", 55, 72)]
    P.strings_pad(sc, pr, 18, 26, voices, vel=44)
    for v in ("vbass", "viola", "violin2"):
        P.swell_cc(sc, v, 18, 26, 40, 90, 4)
    rubato(sc, nb, 66, dip=0.08, final=0.3)
    sc.humanize("piano", 9, 3, rng=r)
    insts = {"piano": (PIANO, 0, 0, 0.36, 0), "cello": (SSO(13), -4, -0.25, 0.45, 50),
             "vbass": (SSO(10), -12, -0.4, 0.5, 40), "viola": (SSO(6), -12, 0.2, 0.5, 120), "violin2": (SSO(4), -13, 0.45, 0.5, 200)}
    return sc, insts


def adagio(seed=31):
    """진정 — 현악 아다지오 (라장조). 성부 진행 + 부풀었다 가라앉는 표현, 뒤에 하프·호른"""
    r = random.Random(seed)
    sc = Score(56, 4)
    spec = ("D | D | "
            "D | A/C# | Bm | F#m/A | G | D/F# | Em7 | A7sus4 A7 | "
            "D | A/C# | Bm | G | Em7 | F#m | G A7 | D | "
            "Bm | F#m | G | D | Em | Bm/D | Gmaj7 | A7sus4 A7 | "
            "D | A/C# | Bm | F#m | G | D/F# | Em7 A7 | D | D")
    pr = prog(spec, 4)
    nb = 35
    voices = [("basses", 28, 48), ("cellos", 40, 60), ("violas", 50, 69), ("violins2", 57, 77)]
    P.strings_pad(sc, pr, 0, nb, voices, vel=64)
    m = Melody(2, "major", 69, 90, "adagio", 4, r)
    a1, mot = m.phrase(pr, 2, 4, cadence="half"); a2, _ = m.phrase(pr, 6, 4, mot, cadence="full", level=0.3)
    b1, _ = m.phrase(pr, 10, 4, mot, cadence="half", level=0.5); b2, _ = m.phrase(pr, 14, 4, mot, cadence="full", level=0.4)
    c1, mot2 = m.phrase(pr, 18, 4, cadence="half"); c2, _ = m.phrase(pr, 22, 4, mot2, cadence="half", level=0.4)
    d1, _ = m.phrase(pr, 26, 4, mot, cadence="half", level=0.35); d2, _ = m.phrase(pr, 30, 4, mot, cadence="full", level=0.2)
    add_mel(sc, a1 + a2 + b1 + b2 + c1 + c2 + d1 + d2, "violins1", 82, accent=4, rng=r, legato=1.04)
    for v in ("basses", "cellos", "violas", "violins2", "violins1"):
        P.swell_cc(sc, v, 0, nb, 52, 118, 4)
    # 하프: 뒤 절반 펼친화음 (위로 올라가는)
    for s, e, c in P.chord_spans(pr, 18, nb, 4):
        v = voicing(c.tones(), None, 50, 86, 6)
        for k, p in enumerate(v):
            sc.add(s + k * 0.33, 2.5, p, 50 + k * 3 + r.randint(-4, 4), "harp")
    # 호른: B 에서 따뜻하게
    for s, e, c in P.chord_spans(pr, 18, 26, 4):
        sc.add(s, e - s, near(c.tones()[1], 60), 58, "horns")
    P.swell_cc(sc, "horns", 18, 26, 40, 100, 4)
    rubato(sc, nb, 56, dip=0.05, final=0.3)
    for v in ("basses", "cellos", "violas", "violins2", "violins1", "harp"):
        sc.humanize(v, 10, 3, rng=r)
    insts = {"violins1": (SSO(2), -2, 0.35, 0.5, 200), "violins2": (SSO(4), -6, 0.55, 0.5, 200),
             "violas": (SSO(6), -6, -0.15, 0.5, 120), "cellos": (SSO(8), -5, -0.45, 0.5, 50),
             "basses": (SSO(10), -8, -0.6, 0.5, 30), "harp": (SSO(1), -5, 0.15, 0.45, 80), "horns": (SSO(30), -12, -0.2, 0.55, 60)}
    return sc, insts


# ======================= 재즈 =======================
def swing(seed=41):
    """즐거운 대화 — 미디엄 업 스윙 (Bb, 152). 비브라폰 테마 → 피아노 즉흥 → 테마"""
    r = random.Random(seed)
    sc = Score(152, 4)
    A = "Bbmaj7 G7 | Cm7 F7 | Dm7 G7 | Cm7 F7 | Fm7 Bb7 | Ebmaj7 Ab7 | Dm7 G7 | Cm7 F7 | "
    spec = "Bbmaj7 G7 | Cm7 F7 | Bbmaj7 G7 | Cm7 F7 | " + A * 5 + "Bbmaj7 | Bb6"
    pr = prog(spec, 4)
    nb = 4 + 40 + 2
    P.walking_bass(sc, pr, 0, nb - 1, "bass", r)
    sc.add((nb - 1) * 4, 4, 34, 84, "bass")
    P.swing_drums(sc, 0, nb - 1, "drums", r, vel=66)
    sc.add((nb - 1) * 4, 2, 49, 80, "drums"); sc.add((nb - 1) * 4, 1, 36, 70, "drums")
    # 피아노 반주: 테마 동안 보통, 즉흥 동안 왼손만 가볍게
    P.jazz_comp(sc, pr, 0, 4, "piano", r, vel=58)
    P.jazz_comp(sc, pr, 4, 20, "piano", r, vel=56, density=0.9)
    P.jazz_comp(sc, pr, 20, 36, "piano", r, vel=50, density=0.55)
    P.jazz_comp(sc, pr, 36, nb - 1, "piano", r, vel=56, density=0.9)
    m = Melody(10, "major", 62, 82, "swinghead", 4, r)
    h1, mot = m.phrase(pr, 4, 4, cadence="half"); h2, _ = m.phrase(pr, 8, 4, mot, cadence="full", level=0.3)
    h3, _ = m.phrase(pr, 12, 4, mot, cadence="half", level=0.5); h4, _ = m.phrase(pr, 16, 4, mot, cadence="full", level=0.4)
    add_mel(sc, h1 + h2 + h3 + h4, "vibes", 84, rng=r)
    solo = bebop_line(pr, 20 * 4, 36 * 4, 63, 89, r, key_pc=10)
    add_mel(sc, solo, "piano", 70, accent=10, rng=r)
    h5, _ = m.phrase(pr, 36, 4, mot, cadence="half", level=0.35); h6, _ = m.phrase(pr, 40, 4, mot, cadence="full", level=0.2)
    add_mel(sc, h5 + h6, "vibes", 86, rng=r)
    for p in (58, 62, 65, 69, 74):
        sc.add((nb - 1) * 4, 4, p, 62, "vibes")
    sc.humanize("piano", 10, 5, swing=0.64, rng=r); sc.humanize("vibes", 9, 4, swing=0.64, rng=r)
    sc.humanize("bass", 6, 4, rng=r); sc.humanize("drums", 5, 4, rng=r)
    insts = {"piano": (PIANO, -2, -0.2, 0.25, 60), "vibes": (GU(11), -1, 0.25, 0.3, 120), "bass": (GU(32), 0, 0, 0.1, 30),
             "drums": (GUKIT(32), -3, 0.05, 0.18, 30)}
    return sc, insts


def ballad(seed=51):
    """비 오는 길 — 재즈 발라드 (F, 66). 피아노가 선율+화음, 브러시, 2박 베이스 → 워킹, 뒤에 로즈"""
    r = random.Random(seed)
    sc = Score(66, 4)
    A = "Fmaj7 | Em7b5 A7 | Dm7 | Cm7 F7 | Bbmaj7 | Bbm7 Eb7 | Am7 D7 | Gm7 C7 | "
    spec = "Gm7 C7 | Gm7 C7 | " + A + A.replace("Gm7 C7 | ", "Gm7 C7 | ", 1) + "Fmaj7 | Fmaj7"
    pr = prog(spec, 4)
    nb = 2 + 16 + 2
    P.two_feel_bass(sc, pr, 0, 10, "bass", r); P.walking_bass(sc, pr, 10, nb - 1, "bass", r, vel=70)
    sc.add((nb - 1) * 4, 4, 29, 70, "bass")
    P.swing_drums(sc, 2, nb - 1, "drums", r, vel=44, fill_every=8)
    # 피아노: 화음 바뀔 때 부드러운 보이싱 + 선율
    prev = None
    for s, e, c in P.chord_spans(pr, 0, nb, 4):
        v = P.rootless(c, prev); prev = v
        for k, p in enumerate(v):
            sc.add(s + k * 0.02 + (0.5 if r.random() < 0.3 else 0), e - s, p - (12 if p > 70 else 0), 42 + r.randint(-4, 4), "piano")
        sc.pedal.append((s, e - 0.05, "piano"))
    m = Melody(5, "major", 65, 86, "ballad", 4, r)
    a1, mot = m.phrase(pr, 2, 4, cadence="half"); a2, _ = m.phrase(pr, 6, 4, mot, cadence="half", level=0.3)
    b1, _ = m.phrase(pr, 10, 4, mot, cadence="half", level=0.6); b2, _ = m.phrase(pr, 14, 4, mot, cadence="full", level=0.4)
    add_mel(sc, a1 + a2 + b1 + b2, "piano", 66, rng=r)
    for s, e, c in P.chord_spans(pr, 10, nb, 4):
        for p in voicing(c.tones(), None, 55, 72, 4):
            sc.add(s, e - s, p, 40, "rhodes")
    sc.humanize("piano", 12, 3, swing=0.6, rng=r); sc.humanize("bass", 8, 4, rng=r); sc.humanize("drums", 8, 4, rng=r)
    rubato(sc, nb, 66, dip=0.05, final=0.35)
    insts = {"piano": (PIANO, 0, -0.1, 0.33, 50), "bass": (GU(32), -1, 0.05, 0.12, 30), "drums": (GUKIT(40), -7, 0.1, 0.25, 40),
             "rhodes": (GU(4), -12, 0.35, 0.4, 100)}
    return sc, insts


def bossa(seed=61):
    """드라이브 — 보사노바 (D, 132). 나일론 기타 · 베이스 · 림샷/셰이커 · 플루트 선율"""
    r = random.Random(seed)
    sc = Score(132, 4)
    spec = ("Dmaj7 | Dmaj7 | Gmaj7 | A7 | "
            "Dmaj7 | Dmaj7 | E7 | E7 | Em7 | A7 | Dmaj7 | A7sus4 A7 | "
            "Gmaj7 | Gm6 | F#m7 | B7 | Em7 | A7 | Dmaj7 | A7 | "
            "Dmaj7 | B7 | Em7 | A7 | F#m7 | B7b9 | Em7 A7 | Dmaj7 | "
            "Gmaj7 | Gm6 | Dmaj7 | Dmaj7")
    pr = prog(spec, 4)
    nb = 32
    P.bossa_guitar(sc, pr, 0, nb, "guitar", r)
    for b in range(nb):                                                     # 보사 베이스: 1박 근음, 3박 5음(앞당김)
        t0 = b * 4; c = chord_at(pr, t0); c3 = chord_at(pr, t0 + 2)
        root = P.bass_note(c, 31, 50, 38); f = P.bass_note(c3, 31, 50, root + 7) if c3 is not c else (root + 7 if root + 7 <= 50 else root - 5)
        sc.add(t0, 1.4, root, 80, "bass"); sc.add(t0 + 1.5, 0.45, root, 66, "bass")
        sc.add(t0 + 2, 1.4, f, 74, "bass"); sc.add(t0 + 3.5, 0.45, f, 62, "bass")
    P.bossa_drums(sc, 0, nb, "drums", r)
    m = Melody(2, "major", 67, 91, "bossa", 4, r)
    a1, mot = m.phrase(pr, 4, 4, cadence="half"); a2, _ = m.phrase(pr, 8, 4, mot, cadence="full", level=0.3)
    b1, mot2 = m.phrase(pr, 12, 4, cadence="half"); b2, _ = m.phrase(pr, 16, 4, mot2, cadence="half", level=0.4)
    c1, _ = m.phrase(pr, 20, 4, mot, cadence="half", level=0.5); c2, _ = m.phrase(pr, 24, 4, mot, cadence="full", level=0.3)
    add_mel(sc, a1 + a2 + b1 + b2 + c1 + c2, "flute", 78, rng=r, legato=0.95)
    for s, e, c in P.chord_spans(pr, 20, nb, 4):
        for p in voicing(c.tones(), None, 57, 74, 4):
            sc.add(s, e - s, p, 36, "rhodes")
    sc.humanize("guitar", 7, 4, rng=r); sc.humanize("flute", 10, 4, rng=r); sc.humanize("bass", 5, 4, rng=r)
    sc.humanize("drums", 4, 3, rng=r)
    insts = {"guitar": (GU(24), -2, -0.3, 0.22, 80), "bass": (GU(32), -1, 0, 0.08, 30), "drums": (GUKIT(0), -10, 0.2, 0.15, 60),
             "flute": (SSO(14), -2, 0.25, 0.35, 250), "rhodes": (GU(4), -14, 0.45, 0.35, 120)}
    return sc, insts


PIECES = {"클래식_아이재우기_자장가": lullaby, "클래식_비오는길_녹턴": nocturne, "클래식_진정_현악아다지오": adagio,
          "재즈_즐거운대화_스윙": swing, "재즈_비오는길_발라드": ballad, "재즈_드라이브_보사노바": bossa}
