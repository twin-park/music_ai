# 음악 이론 도구: 음계 · 화음 · 성부 진행 · 사람 같은 흔들림
import random
import numpy as np

NAMES = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7,
         "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}
SCALES = {"major": [0, 2, 4, 5, 7, 9, 11], "minor": [0, 2, 3, 5, 7, 8, 10], "harm": [0, 2, 3, 5, 7, 8, 11],
          "dorian": [0, 2, 3, 5, 7, 9, 10], "mixo": [0, 2, 4, 5, 7, 9, 10], "lydian": [0, 2, 4, 6, 7, 9, 11],
          "locrian2": [0, 2, 3, 5, 6, 8, 10], "altered": [0, 1, 3, 4, 6, 8, 10], "penta": [0, 2, 4, 7, 9]}
QUAL = {  # 화음 구성음(근음 기준 반음), 어울리는 음계
    "maj": ([0, 4, 7], "major"), "min": ([0, 3, 7], "dorian"), "dim": ([0, 3, 6], "locrian2"),
    "sus4": ([0, 5, 7], "mixo"), "maj7": ([0, 4, 7, 11], "major"), "6": ([0, 4, 7, 9], "major"),
    "m7": ([0, 3, 7, 10], "dorian"), "7": ([0, 4, 7, 10], "mixo"), "m7b5": ([0, 3, 6, 10], "locrian2"),
    "7b9": ([0, 4, 7, 10, 13], "altered"), "add9": ([0, 4, 7, 14], "major"), "madd9": ([0, 3, 7, 14], "minor"),
    "m9": ([0, 3, 7, 10, 14], "dorian"), "maj9": ([0, 4, 7, 11, 14], "major"), "9": ([0, 4, 7, 10, 14], "mixo"),
    "m6": ([0, 3, 7, 9], "dorian"), "7sus4": ([0, 5, 7, 10], "mixo"),
}


class Chord:
    def __init__(self, sym, beats):
        """sym 예: 'Cmaj7', 'F#m7b5', 'G7/B', 'Am'. beats: 길이(박)"""
        s, self.bass = (sym.split("/") + [None])[:2]
        r = s[:2] if len(s) > 1 and s[1] in "#b" else s[:1]
        q = s[len(r):] or "maj"
        q = {"m": "min", "": "maj"}.get(q, q)
        self.root, self.q, self.beats, self.sym = NAMES[r], q, beats, sym
        self.bass = NAMES[self.bass] if self.bass else self.root

    def tones(self):                      # 구성음 음이름(0~11)
        return [(self.root + i) % 12 for i in QUAL[self.q][0]]

    def scale(self, key_pc, key_mode):    # 선율에 쓸 음계: 조성 음계를 기본, 화음 구성음은 꼭 포함
        ks = {(key_pc + i) % 12 for i in SCALES[key_mode]}
        cs = {(self.root + i) % 12 for i in SCALES[QUAL[self.q][1]]}
        ct = set(self.tones())
        out = {p for p in ks if p in cs} | ct
        if len(out) < 6:
            out |= ks
        return sorted(out)

    def guide(self):                      # 3음·7음 (재즈 성부)
        iv = QUAL[self.q][0]
        third = [i for i in iv if i in (3, 4, 5)][:1]
        sev = [i for i in iv if i in (9, 10, 11)][:1] or [i for i in iv if i == 7]
        return [(self.root + i) % 12 for i in third + sev]


def prog(spec, beats_per):
    """'C Am | F G7' 처럼 마디를 | 로, 한 마디 안 여러 화음은 공백으로 → [(시작박, Chord)]"""
    out, t = [], 0.0
    for bar in spec.split("|"):
        syms = bar.split()
        for s in syms:
            out.append((t, Chord(s, beats_per / len(syms)))); t += beats_per / len(syms)
    return out


def chord_at(progression, t):
    for s, c in reversed(progression):
        if t >= s - 1e-6:
            return c
    return progression[0][1]


def near(pc, ref):
    """음이름 pc 를 ref 에 가장 가까운 실제 음높이로"""
    p = ref - ((ref - pc) % 12)
    return p if ref - p <= 6 else p + 12


def voicing(pcs, prev, lo, hi, n=None):
    """음이름들 → lo~hi 안에서 앞 화음과 가장 덜 움직이는 배치 (성부 진행)"""
    n = n or len(pcs)
    best, bc = None, 1e9
    center = np.mean(prev) if prev else (lo + hi) / 2
    for inv in range(len(pcs)):
        order = pcs[inv:] + pcs[:inv]
        for start_oct in range(lo // 12 - 1, hi // 12 + 1):
            v, last = [], start_oct * 12 - 1
            for pc in (order * 2)[:n]:
                p = last + 1 + ((pc - (last + 1)) % 12)
                v.append(p); last = p
            if v[0] < lo or v[-1] > hi:
                continue
            cost = (sum(min(abs(a - b) for b in prev) for a in v) if prev else 0) + abs(np.mean(v) - center) * 0.3
            cost += 0.5 * (v[-1] - v[0] > 19)
            if cost < bc:
                best, bc = v, cost
    return best or sorted(near(pc, (lo + hi) // 2) for pc in pcs[:n])


class Score:
    """음표 모음. 시간은 박(4분음표) 단위. 악기 이름별로 나눠 렌더."""

    def __init__(self, bpm, beats_per_bar=4):
        self.bpm, self.bpb = bpm, beats_per_bar
        self.notes = []          # (시작박, 길이박, 음높이, 세기, 악기)
        self.cc = []             # (시작박, 악기, cc번호, 값)
        self.pedal = []          # (시작박, 끝박, 악기)

    def add(self, t, d, p, v, inst):
        if d > 0.01:
            self.notes.append([float(t), float(d), int(p), int(np.clip(v, 1, 127)), inst])

    def humanize(self, inst, t_ms=8, v_sd=6, swing=None, rng=None, keep_beat=False):
        """inst 의 음을 사람처럼: 시간 흔들림(ms), 세기 흔들림, 스윙(8분 뒷박을 늦춤: 0.5→swing)"""
        rng = rng or random.Random(0)
        sec = 60 / self.bpm
        for n in self.notes:
            if n[4] != inst:
                continue
            if swing:
                b, frac = divmod(n[0], 1.0)
                if abs(frac - 0.5) < 0.02:
                    n[0] = b + swing
            if not (keep_beat and abs(n[0] - round(n[0])) < 1e-3):
                n[0] += rng.gauss(0, t_ms / 1000 / sec)
            n[3] = int(np.clip(n[3] + rng.gauss(0, v_sd), 1, 127))
