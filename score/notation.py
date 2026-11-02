# 악보 글자 형식 쓰기·읽기
#   음:   <옥타브> <계이름> <임시표> <시작초>~<끝초> [세기]      예) -1 mi F 3~6 70
#         옥타브 0 = 가온 도(C4)가 있는 옥타브, 계이름은 고정 도(do=C), 임시표 F=플랫 S=샵 N=제자리 (FF·SS 겹)
#   드럼: <이름> <시작초>~<끝초> [세기]                          예) tap 1.71~1.9 44
#   페달: 페달 <시작초>~<끝초>
#   [이름] 줄로 악기를 나누고, [코드] 칸엔 코드 이름을 적음. # 은 설명, @ 는 곡 정보.
import re
from theory import Key, Chord, SOLFA, SOLFA_IN, ACC_IN, ACC_OUT, LETTERS, LETTER_PC, to_midi

DRUM_IN = {"kick": 36, "rim": 37, "snare": 38, "tap": 38, "slap": 39, "sweep": 40, "hat": 42, "hat_foot": 44,
           "hat_open": 46, "tom3": 43, "tom2": 47, "tom1": 50, "crash": 49, "ride": 51, "bell": 53, "shaker": 70}
DRUM_OUT = {36: "kick", 37: "rim", 38: "snare", 39: "slap", 40: "sweep", 42: "hat", 44: "hat_foot", 46: "hat_open",
            43: "tom3", 47: "tom2", 50: "tom1", 49: "crash", 51: "ride", 53: "bell", 70: "shaker"}
BRUSH_OUT = {**DRUM_OUT, 38: "tap", 39: "slap", 40: "sweep"}


def fmt(x):
    s = f"{x:.2f}".rstrip("0").rstrip(".")
    return s if s not in ("-0", "") else "0"


class Part:
    def __init__(self, name, drum=False):
        self.name, self.drum = name, drum
        self.notes = []          # (시작초, 끝초, 음 또는 드럼번호, 세기)
        self.pedals = []         # (시작초, 끝초)


class Sheet:
    def __init__(self, title="", key="C"):
        self.title, self.key = title, Key(key)
        self.info = {}           # @템포 등
        self.notes_text = []     # # 설명 줄
        self.chords = []         # (시작초, 끝초, Chord)
        self.parts = {}

    def part(self, name, drum=False):
        if name not in self.parts:
            self.parts[name] = Part(name, drum)
        return self.parts[name]

    def chord_at(self, t):
        for a, b, c in self.chords:
            if a - 1e-6 <= t < b - 1e-6:
                return c
        return None

    # ---------- 쓰기 ----------
    def spell(self, midi, chord):
        """화음 안의 음이면 화음 근음 기준으로 이름 붙임 (C7 의 3음 = E, Fb 아님)"""
        k = self.key
        if chord is not None:
            iv = (midi - chord.root) % 12
            pcs = set(chord.tones()) | set(chord.tensions())
            if midi % 12 in pcs or iv in (0,):
                _, rl, ra = k.spell(60 + chord.root)
                steps = {0: 0, 1: 1, 2: 1, 3: 2, 4: 2, 5: 3, 6: 3, 7: 4, 8: 5, 9: 5, 10: 6, 11: 6}[iv]
                if iv == 3 and chord.is_dom():
                    steps = 1                                   # #9
                if iv == 6 and chord.q in ("m7b5", "dim7", "dim"):
                    steps = 4                                   # b5
                if iv == 8 and chord.q in ("aug",):
                    steps = 4                                   # #5
                if iv == 9 and chord.q == "dim7":
                    steps = 6                                   # bb7
                L = (rl + steps) % 7
                acc = ((midi % 12) - LETTER_PC[L] + 6) % 12 - 6
                if -2 <= acc <= 2:
                    o = (midi - LETTER_PC[L] - acc) // 12 - 5
                    return f"{'0' if o == 0 else f'{o:+d}'} {SOLFA[L]} {ACC_OUT[acc]}"
        return k.note_text(midi)

    def text(self):
        out = [f"# {self.title}"] + [f"# {x}" for x in self.notes_text]
        out += [f"@{k} {v}" for k, v in self.info.items()] + [f"@조 {self.key.name}", ""]
        out.append("[코드]")
        out += [f"{c.name(self.key)} {fmt(a)}~{fmt(b)}" for a, b, c in self.chords]
        for p in self.parts.values():
            out += ["", f"[{p.name}]"]
            ev = []
            for t0, t1, x, v in p.notes:
                if p.drum:
                    names = BRUSH_OUT if "브러시" in p.name else DRUM_OUT
                    ev.append((t0, -x, f"{names[x]} {fmt(t0)}~{fmt(t1)} {v}"))
                else:
                    ev.append((t0, -x, f"{self.spell(x, self.chord_at(t0))} {fmt(t0)}~{fmt(t1)} {v}"))
            for a, b in p.pedals:
                ev.append((a, 1, f"페달 {fmt(a)}~{fmt(b)}"))
            out += [e[2] for e in sorted(ev, key=lambda e: (e[0], e[1]))]
        return "\n".join(out) + "\n"

    def save(self, path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.text())


# ---------- 읽기 ----------
NOTE_RE = re.compile(r"^([+-]?\d+)\s+(\S+)\s+(FF|SS|F|S|N|bb|##|b|#|-)\s+([\d.]+)\s*~\s*([\d.]+)(?:\s+(\d+))?$")
DRUM_RE = re.compile(r"^([a-z_0-9]+)\s+([\d.]+)\s*~\s*([\d.]+)(?:\s+(\d+))?$")
PED_RE = re.compile(r"^(?:페달|ped)\s+([\d.]+)\s*~\s*([\d.]+)$")
CHORD_RE = re.compile(r"^(\S+)\s+([\d.]+)\s*~\s*([\d.]+)$")


def load(path):
    sh, cur = Sheet(), None
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    for ln in lines:
        s = ln.strip()
        if not s:
            continue
        if s.startswith("#"):
            if not sh.title:
                sh.title = s[1:].strip()
            continue
        if s.startswith("@"):
            k, _, v = s[1:].partition(" ")
            if k == "조":
                sh.key = Key(v.strip())
            else:
                sh.info[k] = v.strip()
            continue
        if s.startswith("[") and s.endswith("]"):
            nm = s[1:-1].strip()
            cur = None if nm == "코드" else sh.part(nm, drum=("드럼" in nm or "브러시" in nm))
            continue
        if cur is None:
            m = CHORD_RE.match(s)
            if m:
                sh.chords.append((float(m.group(2)), float(m.group(3)), Chord.parse(m.group(1))))
            continue
        m = PED_RE.match(s)
        if m:
            cur.pedals.append((float(m.group(1)), float(m.group(2))))
            continue
        if cur.drum:
            m = DRUM_RE.match(s)
            if m and m.group(1) in DRUM_IN:
                cur.notes.append((float(m.group(2)), float(m.group(3)), DRUM_IN[m.group(1)], int(m.group(4) or 70)))
                continue
        m = NOTE_RE.match(s)
        if m and m.group(2) in SOLFA_IN:
            midi = to_midi(int(m.group(1)), SOLFA_IN[m.group(2)], ACC_IN[m.group(3)])
            cur.notes.append((float(m.group(4)), float(m.group(5)), midi, int(m.group(6) or 70)))
            continue
        raise ValueError(f"못 읽는 줄: {ln}")
    return sh
