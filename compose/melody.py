# 선율 만들기: 동기(리듬+모양)를 화음에 맞춰 옮기고 조금씩 바꾼다. 같은 마디가 두 번 나오지 않게.
import random
from theory import chord_at, near, SCALES

# 한 마디 리듬 모음 (시작박, 길이박)
RHY = {
    "lullaby34": [[(0, 1.5), (1.5, 0.5), (2, 1)], [(0, 1), (1, 1), (2, 1)], [(0, 2), (2, 1)],
                  [(0, 1.5), (1.5, 0.5), (2, 0.5), (2.5, 0.5)], [(0, 1), (1, 0.5), (1.5, 0.5), (2, 1)], [(0, 3)]],
    "nocturne": [[(0, 1.5), (1.5, 0.5), (2, 2)], [(0, 1), (1, 1), (2, 1.5), (3.5, 0.5)], [(0, 3), (3, 0.5), (3.5, 0.5)],
                 [(0, 0.5), (0.5, 0.5), (1, 1), (2, 1), (3, 1)], [(0, 2), (2, 0.75), (2.75, 0.25), (3, 1)], [(0, 4)]],
    "adagio": [[(0, 2), (2, 2)], [(0, 3), (3, 1)], [(0, 1), (1, 1), (2, 2)], [(0, 4)], [(0, 1.5), (1.5, 0.5), (2, 2)]],
    "ballad": [[(0, 1.5), (1.5, 0.5), (2, 2)], [(0.5, 1), (1.5, 0.5), (2, 1), (3, 1)], [(0, 3), (3.5, 0.5)],
               [(0, 1), (1, 0.5), (1.5, 1.5), (3, 1)], [(0, 4)]],
    "bossa": [[(0, 1.5), (1.5, 1), (2.5, 1.5)], [(0.5, 1), (1.5, 1), (2.5, 0.5), (3, 1)], [(0, 1), (1, 0.5), (1.5, 2.5)],
              [(0, 0.5), (0.5, 0.5), (1, 0.5), (1.5, 1.5), (3, 1)], [(0, 4)]],
    "swinghead": [[(0, 0.5), (0.5, 0.5), (1, 1), (2.5, 1.5)], [(0.5, 0.5), (1, 0.5), (1.5, 0.5), (2, 1), (3.5, 0.5)],
                  [(0, 1.5), (1.5, 0.5), (2, 0.5), (2.5, 1.5)], [(0, 3), (3.5, 0.5)], [(0, 0.5), (0.5, 0.5), (1, 0.5), (1.5, 2.5)]],
    "edm": [[(0, 0.5), (0.75, 0.25), (1, 0.5), (1.5, 0.5), (2.5, 0.5), (3, 1)], [(0, 0.75), (0.75, 0.75), (1.5, 0.5), (2, 1), (3, 0.5), (3.5, 0.5)],
            [(0, 1.5), (1.5, 0.5), (2, 0.5), (2.5, 0.5), (3, 1)], [(0.5, 0.5), (1, 0.5), (1.5, 0.5), (2, 2)],
            [(0, 0.25), (0.25, 0.25), (0.5, 0.5), (1, 1), (2, 0.75), (2.75, 0.75), (3.5, 0.5)]],
}


def scale_pitches(pcs, lo, hi):
    return [p for p in range(lo, hi + 1) if p % 12 in pcs]


def step_from(p, pitches, k):
    """음계 위에서 k 칸 움직이기"""
    if p not in pitches:
        p = min(pitches, key=lambda q: abs(q - p))
    i = pitches.index(p) + k
    return pitches[max(0, min(len(pitches) - 1, i))]


class Melody:
    def __init__(self, key_pc, mode, lo, hi, style, bpb, rng):
        self.key, self.mode, self.lo, self.hi, self.style, self.bpb, self.r = key_pc, mode, lo, hi, style, bpb, rng
        self.prev = (lo + hi) // 2
        self.seen = set()

    def fit_bar(self, prog, t0, rhythm, contour, cadence=None, peak=None):
        """한 마디: 강박은 화음 구성음, 약박은 음계 따라. contour: 리듬 음마다 움직일 칸(+/-)."""
        out = []
        for k, (on, d) in enumerate(rhythm):
            t = t0 + on
            ch = chord_at(prog, t)
            pcs = ch.scale(self.key, self.mode)
            pitches = scale_pitches(pcs, self.lo, self.hi)
            strong = (abs(on - round(on)) < 1e-6 and round(on) % (2 if self.bpb == 4 else 3) == 0) or d >= 0.99
            nxt = chord_at(prog, t + d - 0.01)
            want = step_from(self.prev, pitches, contour[k % len(contour)])
            if strong or nxt is not ch:   # 길거나 강박이거나 화음을 걸치면: 구성음 (걸치면 두 화음 공통음 우선)
                tones = [p for p in pitches if p % 12 in ch.tones()]
                both = [p for p in tones if p % 12 in nxt.tones()]
                pool = both if (nxt is not ch and both) else tones
                want = min(pool, key=lambda q: (abs(q - want), abs(q - self.prev)))
                if nxt is not ch and not both:                     # 공통음 없으면 화음 바뀌는 자리에서 끊기
                    cut = next(s for s in [x / 4 for x in range(int(t * 4) + 1, int((t + d) * 4) + 1)] if chord_at(prog, s) is not ch)
                    d = max(0.25, cut - t)
            elif d >= 0.5:                # 8분 이상 약박: 구성음과 반음으로 부딪히면 피함
                ct = ch.tones()
                if any((want - c) % 12 in (1, 11) for c in ct):
                    alt = [q for q in pitches if not any((q - c) % 12 in (1, 11) for c in ct)]
                    if alt:
                        want = min(alt, key=lambda q: abs(q - want))
            if peak is not None and want > peak:
                want = step_from(peak, pitches, -1)
            out.append([t, d, want])
            self.prev = want
        if cadence and out:
            ch = chord_at(prog, out[-1][0])
            tones = [p for p in scale_pitches(ch.scale(self.key, self.mode), self.lo, self.hi)
                     if p % 12 == (self.key if cadence == "full" else ch.tones()[1 if len(ch.tones()) > 1 else 0])]
            if tones:
                out[-1][2] = min(tones, key=lambda q: abs(q - out[-2][2] if len(out) > 1 else q - self.prev))
                self.prev = out[-1][2]
        return out

    def unique(self, bar_notes, t0):
        """이미 나온 마디와 같으면(리듬+음) 음 하나를 이웃음으로 바꿈"""
        sig = tuple((round(t - t0, 2), round(d, 2), p) for t, d, p in bar_notes)
        tries = 0
        while sig in self.seen and tries < 6 and bar_notes:
            i = self.r.randrange(len(bar_notes))
            bar_notes[i][2] += self.r.choice([-2, -1, 1, 2])
            sig = tuple((round(t - t0, 2), round(d, 2), p) for t, d, p in bar_notes); tries += 1
        self.seen.add(sig)
        return bar_notes

    def vary(self, rhythm, level):
        """리듬 변주: 음 쪼개기 / 합치기 / 그대로"""
        r = [list(x) for x in rhythm]
        if level > 0 and self.r.random() < level:
            i = self.r.randrange(len(r))
            on, d = r[i]
            if d >= 1 and self.r.random() < 0.6:
                r[i] = [on, d / 2]; r.insert(i + 1, [on + d / 2, d / 2])
            elif i + 1 < len(r):
                r[i] = [on, d + r[i + 1][1]]; r.pop(i + 1)
        return [tuple(x) for x in r]

    def phrase(self, prog, start_bar, n_bars, motif=None, cadence="half", level=0.35):
        """n_bars 마디 프레이즈. motif=(리듬, 모양) 주면 그걸 발전, 없으면 새로 만듦. → (음표들, 쓴 동기)"""
        lib = RHY[self.style]
        if motif is None:
            rhythm = self.r.choice(lib[:-1])
            contour = [self.r.choice([-1, 1, 2, -2, 1, -1, 0]) for _ in range(len(rhythm))]
            motif = (rhythm, contour)
        out = []
        for b in range(n_bars):
            t0 = (start_bar + b) * self.bpb
            last = b == n_bars - 1
            if last:
                rhythm = [x for x in self.r.choice(lib[-2:])]                 # 마침: 긴 음
                contour = [0, -1, -1]
            elif b == 0:
                rhythm, contour = motif[0], motif[1]
            elif b % 2 == 1:                                                   # 동기를 화음에 맞춰 옮기기 + 조금 변주
                rhythm, contour = self.vary(motif[0], level), [c + self.r.choice([0, 0, 1, -1]) for c in motif[1]]
            else:                                                              # 대비: 다른 리듬, 반대 방향
                rhythm, contour = self.r.choice(lib[:-1]), [-c for c in motif[1]]
            bar = self.fit_bar(prog, t0, rhythm, contour, cadence if last else None)
            out += self.unique(bar, t0)
        return out, motif


def bebop_line(prog, t_start, t_end, lo, hi, rng, key_pc=0, rest_prob=0.35):
    """재즈 즉흥: 1~3마디짜리 말 같은 프레이즈 + 쉼. 8분 위주, 목표음 감싸기, 반음 지나가기, 가끔 셋잇단."""
    out, t = [], t_start + rng.choice([0, 0.5, 1])
    p = rng.randint(lo + 7, hi - 7)
    while t < t_end - 1:
        plen = rng.choice([4, 6, 8, 8, 10, 12])                                # 프레이즈 길이(박)
        end = min(t_end - 0.5, t + plen)
        direction = rng.choice([-1, 1])
        while t < end:
            ch = chord_at(prog, t)
            sc = scale_pitches(ch.scale(key_pc, "major"), lo, hi)
            tones = [q for q in sc if q % 12 in ch.tones() + [(ch.root + 2) % 12]]
            on_beat = abs(t - round(t)) < 1e-6
            r = rng.random()
            if on_beat and r < 0.18 and t + 1 <= end:                          # 감싸기: 위·아래 → 구성음
                tgt = min(tones, key=lambda q: abs(q - (p + direction * 2)))
                for q, dd in ((tgt + 1, 1 / 3), (tgt - 1, 1 / 3), (tgt, 1 / 3)):
                    out.append([t, dd, q]); t += dd
                p = tgt; continue
            if on_beat:
                p = min(tones, key=lambda q: abs(q - (p + direction)))
            else:
                if rng.random() < 0.25:                                          # 반음 지나가기
                    p = p + direction
                else:
                    p = step_from(p, sc, direction)
            if p > hi - 3: direction = -1
            if p < lo + 3: direction = 1
            if rng.random() < 0.15: direction = -direction
            out.append([t, 0.5, p]); t += 0.5
        if out:                                                                  # 프레이즈 끝: 긴 음(구성음, 뒷박)
            ch = chord_at(prog, out[-1][0])
            out[-1][1] = rng.choice([1, 1.5, 2])
            out[-1][2] = min([q for q in range(lo, hi) if q % 12 in ch.guide()] or [out[-1][2]], key=lambda q: abs(q - out[-1][2]))
            t = out[-1][0] + out[-1][1]
        t += rng.choice([1, 1.5, 2, 2.5, 3]) if rng.random() < 0.8 else 0.5     # 숨 쉬기
    return [n for n in out if n[0] < t_end]
