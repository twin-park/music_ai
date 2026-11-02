# 음악 기본: 음높이 ↔ 악보 글자(옥타브 계이름 임시표) · 조 · 화음 · 음계 · 보이싱
import re

LETTERS = "CDEFGAB"
LETTER_PC = [0, 2, 4, 5, 7, 9, 11]
SOLFA = ["do", "re", "mi", "fa", "sol", "la", "si"]
SOLFA_IN = {"do": 0, "re": 1, "mi": 2, "fa": 3, "sol": 4, "so": 4, "la": 5, "si": 6, "ti": 6,
            "도": 0, "레": 1, "미": 2, "파": 3, "솔": 4, "라": 5, "시": 6}
ACC_OUT = {-2: "FF", -1: "F", 0: "N", 1: "S", 2: "SS"}
ACC_IN = {"FF": -2, "F": -1, "N": 0, "S": 1, "SS": 2, "bb": -2, "b": -1, "#": 1, "##": 2, "-": 0}
NAME_PC = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "Fb": 4, "E#": 5, "F": 5, "F#": 6, "Gb": 6,
           "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11, "Cb": 11, "B#": 0}
DEG_LETTER = [0, 1, 1, 2, 2, 3, 3, 4, 5, 5, 6, 6]       # 으뜸음에서 반음 몇 개 → 글자 몇 칸 (C조: C Db D Eb E F F# G Ab A Bb B)


def to_midi(octave, letter, acc):
    """악보 글자 → MIDI. 옥타브 0 = 가온 도(C4=60)가 있는 옥타브."""
    return 12 * (octave + 5) + LETTER_PC[letter] + acc


class Key:
    def __init__(self, name):
        self.minor = name.endswith("m")
        t = name[:-1] if self.minor else name
        self.name, self.tonic = name, t
        self.pc, self.letter = NAME_PC[t], LETTERS.index(t[0])
        self.scale = [(self.pc + i) % 12 for i in ([0, 2, 3, 5, 7, 8, 10] if self.minor else [0, 2, 4, 5, 7, 9, 11])]

    def spell(self, midi):
        """MIDI → (옥타브, 글자번호, 임시표). 조에 맞는 이름으로 (A장조 1 → C#, Eb장조 3 → Eb)."""
        d = (midi - self.pc) % 12
        L = (self.letter + DEG_LETTER[d]) % 7
        acc = ((midi % 12) - LETTER_PC[L] + 6) % 12 - 6
        if acc > 2 or acc < -2:                         # 이상한 경우는 가까운 이름으로
            L = min(range(7), key=lambda k: abs(((midi % 12) - LETTER_PC[k] + 6) % 12 - 6))
            acc = ((midi % 12) - LETTER_PC[L] + 6) % 12 - 6
        octave = (midi - LETTER_PC[L] - acc) // 12 - 5
        return octave, L, acc

    def note_text(self, midi):
        o, L, a = self.spell(midi)
        return f"{'0' if o == 0 else f'{o:+d}'} {SOLFA[L]} {ACC_OUT[a]}"

    def pc_name(self, pc):
        _, L, a = self.spell(60 + (pc - 60) % 12)
        if abs(a) == 2:                    # 코드 이름에 겹임시표(Bbb·F##)는 안 씀 → 같은 소리 쉬운 이름 (Bbb → A)
            return (["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"] if a < 0 else
                    ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"])[pc % 12]
        return LETTERS[L] + {-1: "b", 0: "", 1: "#"}[a]


# ---------------- 화음 ----------------
# 이름: (구성음, 쓸 수 있는 텐션, 어울리는 음계)  — 숫자는 근음에서 반음
QUAL = {
    "":        ([0, 4, 7], [14], "ionian"),
    "6":       ([0, 4, 7, 9], [14], "ionian"),
    "69":      ([0, 4, 7, 9, 14], [], "ionian"),
    "maj7":    ([0, 4, 7, 11], [14, 21], "ionian"),
    "maj9":    ([0, 4, 7, 11, 14], [21], "ionian"),
    "maj7#11": ([0, 4, 7, 11, 18], [14, 21], "lydian"),
    "m":       ([0, 3, 7], [14], "aeolian"),
    "m6":      ([0, 3, 7, 9], [14], "dorian"),
    "m7":      ([0, 3, 7, 10], [14, 17], "dorian"),
    "m9":      ([0, 3, 7, 10, 14], [17], "dorian"),
    "m11":     ([0, 3, 7, 10, 14, 17], [], "dorian"),
    "mM7":     ([0, 3, 7, 11], [14], "melmin"),
    "7":       ([0, 4, 7, 10], [14, 21], "mixo"),
    "9":       ([0, 4, 7, 10, 14], [21], "mixo"),
    "13":      ([0, 4, 7, 10, 14, 21], [], "mixo"),
    "7b9":     ([0, 4, 7, 10, 13], [20], "phrdom"),
    "7alt":    ([0, 4, 10, 13, 20], [15, 18], "altered"),
    "7#11":    ([0, 4, 7, 10, 18], [14, 21], "lyddom"),
    "7sus4":   ([0, 5, 7, 10], [14, 21], "mixo"),
    "sus4":    ([0, 5, 7], [14], "mixo"),
    "m7b5":    ([0, 3, 6, 10], [17, 20], "locrian"),
    "dim7":    ([0, 3, 6, 9], [14, 17], "wholehalf"),
    "dim":     ([0, 3, 6], [], "wholehalf"),
    "aug":     ([0, 4, 8], [], "wholetone"),
}
SCALES = {"ionian": [0, 2, 4, 5, 7, 9, 11], "lydian": [0, 2, 4, 6, 7, 9, 11], "dorian": [0, 2, 3, 5, 7, 9, 10],
          "aeolian": [0, 2, 3, 5, 7, 8, 10], "phrygian": [0, 1, 3, 5, 7, 8, 10], "mixo": [0, 2, 4, 5, 7, 9, 10],
          "phrdom": [0, 1, 4, 5, 7, 8, 10], "altered": [0, 1, 3, 4, 6, 8, 10], "lyddom": [0, 2, 4, 6, 7, 9, 10],
          "locrian": [0, 1, 3, 5, 6, 8, 10], "wholehalf": [0, 2, 3, 5, 6, 8, 9, 11], "wholetone": [0, 2, 4, 6, 8, 10],
          "melmin": [0, 2, 3, 5, 7, 9, 11]}
DOM = {"7", "9", "13", "7b9", "7alt", "7#11", "7sus4"}
MINORISH = {"m", "m6", "m7", "m9", "m11", "mM7", "m7b5", "dim7", "dim"}
SHOW = {"": "", "maj7": "M7", "maj9": "M9", "maj7#11": "M7(#11)", "m7b5": "m7(b5)", "7b9": "7(b9)", "7#11": "7(#11)",
        "7sus4": "7sus4", "69": "69", "mM7": "mM7"}
SYN = {"M7": "maj7", "Δ": "maj7", "Δ7": "maj7", "M9": "maj9", "-7": "m7", "-": "m", "min": "m", "min7": "m7",
       "ø": "m7b5", "ø7": "m7b5", "m7(b5)": "m7b5", "o7": "dim7", "°7": "dim7", "o": "dim", "+": "aug",
       "7(b9)": "7b9", "6/9": "69", "M7(#11)": "maj7#11", "7(#11)": "7#11"}


class Chord:
    __slots__ = ("root", "q", "bass")

    def __init__(self, root, q, bass=None):
        self.root, self.q = root % 12, q
        self.bass = self.root if bass is None else bass % 12

    @staticmethod
    def parse(sym):
        """'F#m7b5', 'Bbmaj9/D', 'G7alt' → Chord"""
        s, _, b = sym.partition("/")
        r = s[:3] if s[1:3] in ("bb", "##") else s[:2] if len(s) > 1 and s[1] in "#b" else s[:1]
        q = s[len(r):]
        q = SYN.get(q, q)
        pc = lambda n: (NAME_PC[n[0]] + n[1:].count("#") - n[1:].count("b")) % 12
        return Chord(pc(r), q, pc(b) if b else None)

    def tones(self):
        return [(self.root + i) % 12 for i in QUAL[self.q][0]]

    def tensions(self):
        return [(self.root + i) % 12 for i in QUAL[self.q][1]]

    def iv(self, k):
        """구성음 찾기: k = 3 / 5 / 7 → 해당 음이름 (없으면 None)"""
        iv = QUAL[self.q][0]
        want = {3: (3, 4, 5), 5: (6, 7, 8), 7: (9, 10, 11)}[k]
        x = next((i for i in iv if i in want), None)
        return None if x is None else (self.root + x) % 12

    def scale(self, key=None):
        """선율에 쓸 음계. 화음이 조 안에 다 있으면 조의 음계(자리만 옮김)를 써서 조에서 안 벗어나게."""
        own = [(self.root + i) % 12 for i in SCALES[QUAL[self.q][2]]]
        if key is not None and all(t in key.scale for t in self.tones()) and self.q not in DOM | {"m7b5", "dim7"}:
            return sorted(key.scale)
        return sorted(set(own))

    def is_dom(self):
        return self.q in DOM

    def is_minor(self):
        return self.q in MINORISH

    def name(self, key):
        s = key.pc_name(self.root) + SHOW.get(self.q, self.q)
        return s + ("/" + key.pc_name(self.bass) if self.bass != self.root else "")

    def same(self, o):
        return o is not None and self.root == o.root and self.q == o.q and self.bass == o.bass


ROMAN = {"I": 0, "II": 2, "III": 4, "IV": 5, "V": 7, "VI": 9, "VII": 11}
UP = {"": "", "6": "6", "69": "69", "maj7": "maj7", "maj9": "maj9", "maj7#11": "maj7#11", "7": "7", "9": "9", "13": "13",
      "7b9": "7b9", "7alt": "7alt", "7#11": "7#11", "7sus4": "7sus4", "sus4": "sus4", "+": "aug"}
LOW = {"": "m", "6": "m6", "7": "m7", "9": "m9", "11": "m11", "M7": "mM7", "ø7": "m7b5", "o7": "dim7", "o": "dim"}


def roman(tok, key):
    """'bVII7', 'iiø7', '#io7', 'V7/3'(3음이 베이스), 'iv/5' → Chord"""
    m = re.match(r"^([b#]?)([IViv]+)([^/]*)(?:/(\d))?$", tok)
    if not m:
        raise ValueError(tok)
    acc, num, suf, inv = m.groups()
    root = key.pc + ROMAN[num.upper()] + {"b": -1, "#": 1, "": 0}[acc]
    q = UP[suf] if num.isupper() else LOW[suf]
    c = Chord(root, q)
    if inv:
        c.bass = c.iv(int(inv)) if int(inv) in (3, 5, 7) else c.root
    return c


# ---------------- 보이싱 ----------------
def near(pc, ref):
    """음이름 pc 를 ref 에 가장 가까운 실제 음높이로"""
    p = ref - ((ref - pc) % 12)
    return p if ref - p <= 6 else p + 12


def fit(p, lo, hi):
    while p < lo:
        p += 12
    while p > hi:
        p -= 12
    return p


def stack(pcs, lo, hi, prev=None):
    """음이름 순서를 지키며 아래→위로 쌓되(자리바꿈 모두 시도) lo~hi 안에서 앞 화음과 가장 덜 움직이는 것"""
    best, bc = None, 1e9
    n = len(pcs)
    center = sum(prev) / len(prev) if prev else (lo + hi) / 2
    for inv in range(n):
        order = pcs[inv:] + pcs[:inv]
        for o in range(lo // 12 - 1, hi // 12 + 1):
            v, last = [], o * 12 - 1
            for pc in order:
                p = last + 1 + ((pc - (last + 1)) % 12)
                v.append(p)
                last = p
            if v[0] < lo or v[-1] > hi:
                continue
            cost = (sum(min(abs(a - b) for b in prev) for a in v) if prev else 0) + abs(sum(v) / n - center) * 0.4
            if cost < bc:
                best, bc = v, cost
    return best or sorted(fit(near(pc, (lo + hi) // 2), lo, hi) for pc in pcs)


def rootless(c):
    """근음 없는 4음 (빌 에반스식): 3·5(13)·7·9 — 베이스가 근음을 맡을 때 피아노 왼손/오른손 반주용"""
    r, q = c.root, c.q
    I = lambda *xs: [(r + x) % 12 for x in xs]
    if q in ("maj7", "maj9", "maj7#11"):
        return I(4, 7, 11, 14) if q != "maj7#11" else I(4, 6, 11, 14)
    if q in ("6", "69", ""):
        return I(4, 7, 9, 14)
    if q in ("m7", "m9", "m11"):
        return I(3, 7, 10, 14)
    if q in ("m6", "m"):
        return I(3, 7, 9, 14)
    if q == "mM7":
        return I(3, 7, 11, 14)
    if q in ("7", "9", "13", "7#11"):
        return I(4, 9, 10, 14)
    if q == "7b9":
        return I(4, 8, 10, 13)
    if q == "7alt":
        return I(4, 8, 10, 15)
    if q in ("7sus4", "sus4"):
        return I(5, 7, 10, 14)
    if q == "m7b5":
        return I(3, 6, 10, 17)
    if q in ("dim7", "dim"):
        return I(0, 3, 6, 9)
    if q == "aug":
        return I(4, 8, 10, 14)
    return c.tones()


def quartal(c):
    """4도 쌓기 (So What 꼴) — 단7은 9·5·1·11·13, 장7은 3·13·9·5"""
    r = c.root
    if c.q in ("m7", "m9", "m11", "m6"):
        return [(r + x) % 12 for x in (2, 7, 0, 5, 9)]
    if c.q in ("maj7", "maj9", "6", "69", "maj7#11"):
        return [(r + x) % 12 for x in (4, 9, 2, 7)]
    if c.q in ("7sus4", "sus4"):
        return [(r + x) % 12 for x in (10, 2, 5, 9)] if False else [(r + x) % 12 for x in (5, 10, 2, 7)]
    return rootless(c)


def guide(c):
    """가이드톤: 3음·7음 (7음 없으면 6/5음)"""
    t3 = c.iv(3)
    t7 = c.iv(7)
    if t7 is None:
        t7 = (c.root + (9 if c.q in ("6", "69", "m6") else 7)) % 12
    return [t3, t7]
