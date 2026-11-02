# 편곡 공식: 코드 칸 + 선율 → 피아노(선율 아래 화음·왼손·반주)·베이스·드럼·현악 악보
# 시간은 박 단위. 마지막에 to_sheet() 가 스윙·템포를 적용해 초 단위 악보 글자로 바꿈.
import math, random
from theory import Key, Chord, rootless, quartal, guide, stack, near, fit
from notation import Sheet

# AI 코드 종류(11) → 실제 코드 이름 (색 0=단순 · 1=7·9 · 2=9·13·alt)
QUALS = ["maj", "maj7", "min", "m7", "dom", "alt", "sus", "hdim", "dim", "aug", "mM7"]
COLOR = {"maj": ["", "6", "69"], "maj7": ["maj7", "maj7", "maj9"], "min": ["m", "m7", "m9"], "m7": ["m7", "m7", "m9"],
         "dom": ["7", "9", "13"], "alt": ["7b9", "7b9", "7alt"], "sus": ["7sus4", "7sus4", "7sus4"], "hdim": ["m7b5"] * 3,
         "dim": ["dim7"] * 3, "aug": ["aug"] * 3, "mM7": ["mM7"] * 3}


class Song:
    def __init__(self, key, bpm, ts=4, swing=0.0, rng=None):
        self.key, self.bpm, self.ts, self.swing = Key(key), bpm, ts, swing
        self.rng = rng or random.Random(0)
        self.spans = []          # (시작박, 끝박, Chord)
        self.ev = {}             # 악기 → [[박, 길이, 음, 세기]]
        self.pedal = []
        self.secs = []           # (이름, 시작마디, 끝마디)
        self.tempo_pts = None    # [(박, bpm)] 있으면 템포 변화
        self.lead_parts = set()
        self.mel = []            # 선율 음 [박, 길이, 음] (반주가 피해야 할 것)
        self.mel_part = {}       # id(선율 음) → 악기
        self.follow = []         # (화음음, 선율음, 세기 차) — 선율 세기가 바뀌면 따라감

    # ---------- 코드 ----------
    def set_chords(self, bars, color=1, minor_target_b9=True):
        """bars: 마디마다 [(박, 근음, 종류번호)] → 코드 칸. 다음 코드가 단조면 도미넌트는 b9."""
        flat = []
        for bi, bar in enumerate(bars):
            for b, r, q in bar:
                flat.append([bi * self.ts + b, r, QUALS[q]])
        self.spans = []
        for i, (t, r, q) in enumerate(flat):
            end = flat[i + 1][0] if i + 1 < len(flat) else len(bars) * self.ts
            nq = flat[i + 1][2] if i + 1 < len(flat) else None
            name = COLOR[q][color]
            if q == "maj" and nq is not None and (flat[i + 1][1] - r) % 12 == 5 and (r - self.key.pc) % 12 == 7:
                name = "7" if color == 0 else "9"                                  # V 자리 장3화음 → 딸림7 (6화음 아님)
            if q == "dom" and minor_target_b9 and nq in ("min", "m7", "hdim") and (flat[i + 1][1] - r) % 12 == 5:
                name = "7b9"
            if q in ("min", "m7") and color >= 1 and self.rng.random() < .15 and nq not in (None,):
                name = "m9" if color == 2 else "m7"
            self.spans.append((t, end, Chord(r, name)))

    def span(self, t):
        for a, b, c in self.spans:
            if a - 1e-6 <= t < b - 1e-6:
                return a, b, c
        return self.spans[-1]

    def chord(self, t):
        return self.span(t)[2]

    def spans_in(self, b0, b1):
        return [(a, b, c) for a, b, c in self.spans if b0 * self.ts - 1e-6 <= a < b1 * self.ts - 1e-6]

    # ---------- 음 넣기 ----------
    def add(self, part, t, d, p, v):
        n = [t, d, int(p), int(max(1, min(127, v)))]
        self.ev.setdefault(part, []).append(n)
        return n

    def arc(self, t, base, amp=7):
        ph = ((t / self.ts) % 4) / 4
        return base + amp * math.sin(math.pi * min(1, ph * 1.25)) - 2

    # ---------- 선율 ----------
    def lead(self, part, notes, base, legato=1.0):
        """다른 악기(색소폰·플루트 등) 선율"""
        self.lead_parts.add(part)
        for t, d, p in notes:
            n = self.add(part, t, d * legato, p, self.arc(t, base) + (3 if d >= 1 else 0) + self.rng.randint(-2, 2))
            self.mel.append(n); self.mel_part[id(n)] = part

    def block_under(self, m, c, n=3, lo=50):
        pcs = [x for x in dict.fromkeys(rootless(c) + c.tones()) if x != m % 12 and x != (m - 1) % 12]
        if c.q in ("maj7", "maj9", "6", "69", "") and m % 12 == c.root:
            pcs = [x for x in pcs if x != (c.root + 11) % 12]
        below = []
        for p in sorted({m - ((m - pc) % 12 or 12) for pc in pcs}, reverse=True):
            if all(abs(p - q) > 1 for q in below) and len(below) < n:
                below.append(p)
        if len(below) >= 3 and below[0] - 12 >= lo:
            below = below[1:] + [below[0] - 12]
        return [p for p in below if p >= lo - 2]

    def piano_melody(self, notes, base, mode="block", part="피아노 오른손"):
        """mode: block(선율 아래 드롭2) · octave(옥타브 선율 + 안쪽음) · line(한 줄) · dyad(3·6도 겹)"""
        self.lead_parts.add(part)
        for t, d, m in notes:
            c = self.chord(t)
            a, b, _ = self.span(t)
            v = self.arc(t, base) + (3 if d >= 1 else 0) + self.rng.randint(-2, 2)
            top = self.add(part, t, d, m, v)
            self.mel.append(top); self.mel_part[id(top)] = part
            if mode == "octave" and d >= .5:
                self.follow.append((self.add(part, t, d, m - 12, v - 12), top, -12))
            strong = d >= 1 or abs(t - a) < 1e-6 or abs((t % self.ts) - self.ts / 2) < 1e-6
            if mode == "line":
                strong = abs(t - a) < 1e-6 and d >= 1
            if strong and mode in ("block", "octave", "line"):
                hs = self.block_under(m, c, 2 if mode != "block" else 3, lo=52 if mode == "block" else 55)
                if mode == "octave":
                    hs = [h for h in hs if m - 12 < h < m]
                for h in hs:
                    self.follow.append((self.add(part, t + .02, d, h, v - 17), top, -17))
                if t + d > b + 1e-6 and mode != "line":           # 긴 선율음 아래 코드가 바뀌면 안쪽만 바꿈
                    c2 = self.chord(b)
                    for h in self.block_under(m, c2, 2 if mode == "octave" else 3, lo=52):
                        if mode != "octave" or m - 12 < h < m:
                            self.follow.append((self.add(part, b + .02, t + d - b, h, v - 19), top, -19))
            elif mode in ("block", "dyad") and d >= .5 and self.rng.random() < (.35 if mode == "block" else .7):
                cands = [m - k for k in (3, 4, 8, 9) if (m - k) % 12 in c.tones() + c.tensions()]
                if cands:
                    self.follow.append((self.add(part, t, d, cands[0], v - 18), top, -18))

    # ---------- 피아노 왼손 / 반주 ----------
    def lh_guide(self, b0, b1, base=46, shell=False, part="피아노 왼손"):
        prev = None
        for k, (a, b, c) in enumerate(self.spans_in(b0, b1)):
            if shell:
                r = fit(c.root, 36, 47)
                v = [r, fit(guide(c)[k % 2], r + 7, r + 16)]
            else:
                v = stack(guide(c), 46, 62, prev)
            prev = v
            vel = base + self.rng.randint(-3, 3)
            for p in v:
                self.add(part, a, b - a, p, vel)
            if b - a >= 4 and self.rng.random() < .35 and not shell:
                for p in v:
                    self.add(part, a + 2.5, b - a - 2.5, p, vel - 8)

    def pedals(self, b0, b1, every=2):
        for a, b, c in self.spans_in(b0, b1):
            cuts = [a] + [x for x in range(int(a) + every, int(b), every) if x > a] + [b]
            for x, y in zip(cuts, cuts[1:]):
                self.pedal.append((x + .04, y - .03))

    COMP = {
        "ballad": ([[(0, 3.5)], [(0, 1.5), (2.5, 1.5)], [(-.5, 2.5)], [(0, .5), (1.5, 2.5)], [(1, 2.5)]],
                   [[(0, 2), (2, 2)], [(0, 1.5), (1.5, 2.5)], [(-.5, 2), (2, 2)]]),
        "swing": ([[(0, .4), (1.5, 1.2)], [(-.5, .9), (2, .4)], [(1.5, .4), (3.5, .9)], [(0, 1.4)], [(1, .4), (2.5, .4)],
                   [(-.5, 1.2)], [(.5, .4), (3, .9)], [(0, .4), (2.5, 1.2)]],
                  [[(0, .4), (2, .4)], [(-.5, .9), (1.5, .9)], [(0, 1.4), (2, 1.4)], [(.5, .4), (2.5, .9)]]),
        "bossa": ([[(0, .9), (1.5, .45), (2.5, .9)], [(.5, .45), (1.5, .9), (3, .45)]],
                  [[(0, .9), (1.5, .45), (2, .9), (3.5, .45)]]),
        "straight": ([[(0, .45), (1.5, .45), (3, .9)], [(0, 1.4), (2.5, .45)], [(.5, .45), (2, .9), (3.5, .45)]],
                     [[(0, .9), (2, .9)], [(0, .45), (1.5, .45), (2, .9)]]),
        "waltz": ([[(1, .9), (2, .9)], [(0, 2.8)], [(1, .9), (2.5, .45)]], [[(0, 1.4), (1.5, 1.4)]]),
    }

    def comp(self, bars, feel="ballad", base=48, voicing="rootless", lo=50, hi=68, avoid=(), parts=("피아노 오른손", "피아노 왼손")):
        """근음 없는 4음(또는 4도 쌓기)을 박자 꼴에 맞춰. 선율(avoid)과 반음 부딪히는 음은 빼고, 앞당겨 치면 앞 화음 끊음."""
        prev, last, ring = None, None, []
        p1, p2 = self.COMP[feel]
        for bar in bars:
            t0 = bar * self.ts
            two = len([1 for a, b, c in self.spans if t0 - 1e-6 <= a < t0 + self.ts - 1e-6]) > 1
            pats = [p for p in (p2 if two else p1) if p is not last] or (p2 if two else p1)
            if (bar - 1) not in bars:
                pats = [p for p in pats if p[0][0] >= 0] or pats
            pat = self.rng.choice(pats)
            last = pat
            for k, (on, d) in enumerate(pat):
                t = t0 + on
                if t >= self.spans[-1][1] - 1e-6:
                    continue
                c = self.chord(t + .5 if (on < 0 or on % 1) else t)
                pcs = quartal(c) if voicing == "quartal" else rootless(c)
                ov = [p for lt, ld, p in avoid if lt < t + d and lt + ld > t]
                h2 = min(hi, min(ov) - 3) if ov else hi
                l2 = min(lo, h2 - 12)
                if ov and h2 - l2 < 9 or l2 < 40:
                    pcs, l2 = guide(c), max(40, h2 - 12)                              # 자리가 좁으면 3·7음 두 개만
                v = stack(pcs, max(40, l2), max(l2 + 5, h2), prev)
                if len(v) > 1 and v[1] - v[0] == 1 and v[0] < 60:
                    v = sorted(v[1:] + [v[0] + 12])
                if len(v) > 2 and v[-1] - v[-2] == 1 and v[-1] - 12 >= 40:
                    v = sorted([v[-1] - 12] + v[:-1])
                prev = v
                for n in ring:
                    if n[0] + n[1] > t - .03:
                        n[1] = max(.1, t - .03 - n[0])
                ov = [p for lt, ld, p in avoid if lt < t + d and lt + ld > t]
                v = [q for q in v if not any((p - q) % 12 == 1 or (q - p) in (1, 13) for p in ov)]
                acc = (8 if (on < 0 or on % 1) else 0) + (4 if d <= .5 else -3) + (3 if k == 0 else 0) + self.rng.randint(-5, 5)
                if self.rng.random() < .12:
                    acc += 10                                                           # 가끔 세게 찌르기
                top_p = max(v) if v else 0
                ring = [self.add(parts[0] if p >= 60 else parts[1], t + .01 * self.rng.random(), d, p,
                                 base + acc + (4 if p == top_p else -2)) for p in v]

    def guitar_comp(self, bars, part, feel="bossa", base=56):
        """기타 반주: 보사(엄지 베이스 + 화음 뜯기) / 스윙(4분 쿵쿵 프레디 그린)"""
        prev = None
        for bar in bars:
            t0 = bar * self.ts
            c = self.chord(t0)
            pcs = c.tones() if len(c.tones()) >= 4 else c.tones() + [(c.root + 2) % 12]
            v = stack([x for x in pcs if x != c.root][:3] + [c.root], 52, 70, prev)
            prev = v
            if feel == "bossa":
                bass = fit(c.root, 40, 52)
                self.add(part, t0, .9, bass, base + 6)
                c3 = self.chord(t0 + 2)
                self.add(part, t0 + 2, .9, fit(c3.root + 7, 40, 52) if c3 is c else fit(c3.root, 40, 52), base)
                for on in ([0, 1.5, 2.5, 3.5] if bar % 2 == 0 else [.5, 1.5, 2.5, 3]):
                    c2 = self.chord(t0 + on)
                    vv = v if c2 is c else stack(rootless(c2)[:3] + [c2.root], 52, 70, v)
                    for k, p in enumerate(vv):
                        self.add(part, t0 + on + k * .012, .45, p, base - 4 + self.rng.randint(-5, 5))
            else:
                for on in range(self.ts):
                    c2 = self.chord(t0 + on)
                    vv = stack(guide(c2) + [c2.root], 48, 64, v)
                    for p in vv:
                        self.add(part, t0 + on, .45, p, base - (0 if on % 2 else 4) + self.rng.randint(-4, 4))

    def piano_pattern(self, b0, b1, kind="arp", base=46, part="피아노 왼손"):
        """클래식·영화 음악 왼손: arp(1-5-10 펼침) · waltz(쿵-짝-짝) · stride(베이스-화음 번갈아)"""
        for a, b, c in self.spans_in(b0, b1):
            r = fit(c.root, 36, 47)
            third, fifth = c.iv(3), (c.root + 7) % 12
            upper = stack([x for x in rootless(c)][:3], 52, 64)
            t = a
            k = 0
            while t < b - 1e-6:
                if kind == "arp":
                    seq = [r, fit(fifth, r + 5, r + 9), fit(third if third is not None else fifth, r + 14, r + 17), fit(fifth, r + 5, r + 9)]
                    p = seq[k % 4]
                    if k % 8 == 6:
                        p = fit(guide(c)[1], r + 9, r + 13)
                    self.add(part, t, .5 * 2.2, p, base + (6 if k % 4 == 0 else 0) + self.rng.randint(-3, 3))
                    t += .5
                elif kind == "waltz":
                    on = round(t - math.floor(t / self.ts) * self.ts, 3)
                    if on == 0:
                        self.add(part, t, .95, r if (int(t // self.ts) % 2 == 0) else fit(fifth, 36, 47), base + 6)
                    else:
                        for p in upper:
                            self.add(part, t, .6, p, base - 6 + self.rng.randint(-3, 3))
                    t += 1
                elif kind == "stride":
                    on = round(t % self.ts, 3)
                    if on in (0, 2):
                        self.add(part, t, .9, r if on == 0 else fit(fifth, 36, 47), base + 6)
                    else:
                        for p in upper:
                            self.add(part, t, .8, p, base - 4 + self.rng.randint(-3, 3))
                    t += 1
                k += 1

    # ---------- 베이스 ----------
    def bass(self, b0, b1, style="two", base=74, part="베이스", lo=28, hi=48):
        p = 39
        if style == "walk":
            for beat in range(b0 * self.ts, b1 * self.ts):
                a, b, c = self.span(beat)
                if abs(beat - a) < 1e-6:
                    pcs = [c.root] if (self.rng.random() < .85 or b - a < 4) else [c.iv(3)]
                    q = min([x for x in range(lo, hi + 1) if x % 12 in pcs], key=lambda x: abs(x - p) + (3 if x == p else 0))
                elif beat + 1 >= b - 1e-6:
                    nr = min([x for x in range(lo, hi + 1) if x % 12 == self.chord(b).root], key=lambda x: abs(x - p))
                    opts = [nr + 1, nr - 1, nr + 7 if nr + 7 <= hi else nr - 5]
                    q = self.rng.choices(opts, weights=[3, 3, 2])[0]
                    if q == p:
                        q = opts[1] if opts[0] == p else opts[0]
                else:
                    nr = min([x for x in range(lo, hi + 1) if x % 12 == self.chord(b).root], key=lambda x: abs(x - p))
                    way = 1 if nr > p else -1
                    sc = [x for x in range(lo, hi + 1) if x % 12 in c.scale(self.key)]
                    ct = [x for x in sc if x % 12 in c.tones()]
                    pool = [x for x in (ct if self.rng.random() < .6 else sc) if 1 <= (x - p) * way <= 4]
                    q = self.rng.choice(pool) if pool else min(sc, key=lambda x: abs(x - (p + way * 2)))
                q = fit(q, lo, hi)
                self.add(part, beat, .92, q, base + (5 if beat % 2 else 0) + self.rng.randint(-5, 4))
                p = q
            return
        for bar in range(b0, b1):
            t0 = bar * self.ts
            if style in ("two", "ballad"):
                halves = (0, 2) if self.ts == 4 else (0,)
                for h in halves:
                    t = t0 + h
                    a, b, c = self.span(t)
                    if abs(t - a) < 1e-6 or style == "ballad":
                        q = min([x for x in range(lo + 1, hi - 1) if x % 12 == c.root], key=lambda x: abs(x - p))
                    else:
                        f = (c.root + 7) % 12
                        q = min([x for x in range(lo + 1, hi - 1) if x % 12 in (f, c.iv(3))], key=lambda x: abs(x - p) + (0 if x % 12 == f else 2))
                    L = 2 if self.ts == 4 else 3
                    if style == "two" and self.rng.random() < .3:
                        nxt = self.chord(t + L)
                        tgt = min([x for x in range(lo, hi + 1) if x % 12 == nxt.root], key=lambda x: abs(x - q))
                        self.add(part, t, L - .55, q, base + self.rng.randint(-4, 4))
                        self.add(part, t + L - .5, .45, tgt + self.rng.choice([-1, 1]), base - 8)
                    else:
                        self.add(part, t, L - .1, q, base + self.rng.randint(-4, 4))
                    p = q
            elif style == "bossa":
                c, c3 = self.chord(t0), self.chord(t0 + 2)
                r = min([x for x in range(31, 47) if x % 12 == c.root], key=lambda x: abs(x - p))
                f = min([x for x in range(31, 50) if x % 12 == ((c3.root + 7) % 12 if c3 is c else c3.root)], key=lambda x: abs(x - r))
                for on, d, q, dv in ((0, 1.4, r, 0), (1.5, .45, r, -12), (2, 1.4, f, -4), (3.5, .45, f, -14)):
                    self.add(part, t0 + on, d, q, base + dv + self.rng.randint(-3, 3))
                p = r
            elif style == "straight":
                c = self.chord(t0)
                r = min([x for x in range(31, 47) if x % 12 == c.root], key=lambda x: abs(x - p))
                pat = self.rng.choice([[(0, .75, 0), (.75, .25, 0), (1.5, .5, 12), (2, 1, 7), (3, .5, 10), (3.5, .5, -1)],
                                       [(0, 1.5, 0), (1.5, .5, 0), (2, .5, 7), (2.5, .5, 12), (3, 1, 10)],
                                       [(0, .5, 0), (.5, .5, 12), (1, 1, 0), (2, .75, 7), (2.75, .25, 7), (3.5, .5, 5)]])
                for on, d, iv in pat:
                    cc = self.chord(t0 + on)
                    q = r + iv if cc is c else min([x for x in range(31, 47) if x % 12 == cc.root], key=lambda x: abs(x - r))
                    self.add(part, t0 + on, d * .95, q, base - (6 if on % 1 else 0) + self.rng.randint(-4, 3))
                p = r
            elif style == "waltz":
                c = self.chord(t0)
                q = min([x for x in range(lo + 1, hi - 1) if x % 12 == c.root], key=lambda x: abs(x - p))
                self.add(part, t0, 1.9, q, base + self.rng.randint(-3, 3))
                p = q

    # ---------- 드럼 ----------
    def drums(self, b0, b1, kind="brush", lvl=0, part=None, fill_every=8, crash=True):
        """드럼 공식. 스윙 뒷박은 다른 악기와 같은 자리(self.swing)에 — 셋잇단(0.667)과 0.62 가 어긋나면 박이 안 맞게 들림.
        세기: 2·4박 강세(스팡-아-랑), 뒷박 약하게, 스네어 유령음 + 가끔 강세, 4마디 숨, 단락 끝 필인은 점점 세게"""
        part = part or ("브러시" if "brush" in kind else "드럼")
        R = self.rng
        a = self.swing if self.swing else 2 / 3
        for bar in range(b0, b1):
            t0 = bar * self.ts
            fill = (bar - b0) % fill_every == fill_every - 1
            sw = 4 * math.sin(math.pi * (((bar - b0) % 4) + .5) / 4) - 2           # 4마디 숨
            if kind == "brush":
                for h in ((0, 2) if self.ts == 4 else (0,)):
                    self.add(part, t0 + h, 2 if self.ts == 4 else 3, 40, 32 + lvl * 4 + sw + R.randint(-3, 3))
                for on in ((1, 3) if self.ts == 4 else (1, 2)):
                    acc = 10 if R.random() < .15 else 0
                    self.add(part, t0 + on, .2, 38, 40 + lvl * 4 + sw + acc + R.randint(-5, 5))
                    self.add(part, t0 + on, .2, 44, 26 + R.randint(-3, 3))
                if self.ts == 4:
                    for on in (1 + a, 3 + a):
                        if R.random() < (.25 + .3 * lvl):
                            self.add(part, t0 + on, .15, 38, 20 + lvl * 3 + R.randint(-3, 4))
                    if R.random() < .2:
                        self.add(part, t0 + R.choice([a, 2 + a]), .15, 38, 18 + R.randint(0, 6))
            elif kind == "brush_swing":
                self.add(part, t0, 2, 40, 28 + sw); self.add(part, t0 + 2, 2, 40, 26 + sw)
                for on in (0, 1, 1 + a, 2, 3, 3 + a):
                    v = 44 + lvl * 2 + sw + (10 if on in (1, 3) else (-12 if on % 1 else -2)) + R.randint(-5, 5)
                    self.add(part, t0 + on, .2, 38, v)
                for on in (1, 3):
                    self.add(part, t0 + on, .2, 44, 28 + R.randint(-3, 3))
                if R.random() < .2:
                    self.add(part, t0 + R.choice([a, 2 + a]), .2, 39, 50 + R.randint(0, 10))        # 슬랩 강세
            elif kind == "ride":
                for on in (0, 1, 1 + a, 2, 3, 3 + a):
                    if on % 1 and R.random() < .1:
                        continue
                    v = 56 + lvl * 3 + sw + (10 if on in (1, 3) else (-12 if on % 1 else 0)) + R.randint(-5, 5)
                    self.add(part, t0 + on, .3, 51, v)
                for on in (1, 3):
                    self.add(part, t0 + on, .2, 44, 48 + R.randint(-4, 4))
                if not fill:
                    for on in [x + a for x in range(4)]:                                  # 스네어 유령음 (스윙 뒷박)
                        r = R.random()
                        if r < .22:
                            self.add(part, t0 + on, .2, 38, 22 + R.randint(0, 12))
                        elif r < .27:
                            self.add(part, t0 + on, .2, 38, 62 + lvl * 4 + R.randint(0, 10))  # 가끔 강세(반주 찌르기와 맞물림)
                    for on in range(4):                                                    # 킥 깃털치기 (아주 작게)
                        if R.random() < .5:
                            self.add(part, t0 + on, .2, 36, 24 + R.randint(-3, 4))
                    if R.random() < .12:
                        self.add(part, t0 + R.choice([2 + a, 3 + a]), .2, 36, 58 + R.randint(0, 10))  # 폭탄
            elif kind == "bossa":
                for on in ([0, 1.5, 3] if bar % 2 == 0 else [1, 2.5]):
                    self.add(part, t0 + on, .2, 37, 52 + sw + R.randint(-6, 6))
                for on in (0, 1.5, 2, 3.5):
                    self.add(part, t0 + on, .2, 36, 42 + (6 if on in (0, 2) else -4) + R.randint(-4, 4))
                for k in range(8):
                    self.add(part, t0 + k * .5, .2, 42, 34 + (10 if k % 2 == 0 else 0) + sw + R.randint(-6, 6))
            elif kind == "straight":
                for k in range(8):
                    self.add(part, t0 + k * .5, .2, 42, 44 + (12 if k % 2 == 0 else 0) + (6 if k in (2, 6) else 0) + lvl * 3 + sw + R.randint(-6, 6))
                for on in (0, 2.5) if R.random() < .6 else (0, 1.5, 2.5):
                    self.add(part, t0 + on, .2, 36, 60 + (6 if on == 0 else 0) + lvl * 3 + R.randint(-5, 4))
                for on in (1, 3):
                    self.add(part, t0 + on, .2, 37 if lvl == 0 else 38, 58 + lvl * 4 + sw + R.randint(-5, 5))
                for on in (1.75, 3.25, 3.75):                                              # 스네어 유령음
                    if R.random() < .25 and lvl >= 1:
                        self.add(part, t0 + on, .15, 38, 24 + R.randint(0, 10))
                if bar % 2 == 1:
                    self.add(part, t0 + 3.5, .4, 46, 46 + R.randint(-4, 6))
            elif kind == "waltz_brush":
                self.add(part, t0, 3, 40, 28 + lvl * 3 + sw + R.randint(-3, 3))
                for on in (1, 2):
                    self.add(part, t0 + on, .2, 38, 26 + lvl * 3 + (3 if on == 1 else 0) + R.randint(-3, 3))
            if fill and kind in ("brush", "brush_swing", "waltz_brush"):
                for k, on in enumerate((self.ts - 1, self.ts - 1 + 1 / 3, self.ts - 1 + 2 / 3)):
                    self.add(part, t0 + on, .15, 38, 34 + lvl * 4 + 8 * k)
            elif fill and kind in ("ride", "straight", "bossa"):
                for k, on in enumerate((2 + 2 / 3, 3, 3 + 1 / 3, 3 + 2 / 3) if kind == "ride" else (3, 3.25, 3.5, 3.75)):
                    self.add(part, t0 + on, .2, [38, 38, 47, 43][k], 48 + lvl * 4 + 9 * k)
            if crash and kind in ("ride", "straight") and (bar - b0) % 8 == 0:
                self.add(part, t0, 1.5, 49, 62 + lvl * 3)
                self.add(part, t0, .2, 36, 62 + lvl * 3)

    # ---------- 현악 ----------
    def strings_pad(self, b0, b1, part="현악", base=50, lo=52, hi=74):
        prev = None
        for a, b, c in self.spans_in(b0, b1):
            v = stack(guide(c) + [(c.root + 7) % 12], lo, hi, prev)
            prev = v
            for p in v:
                self.add(part, a, b - a + .1, p, base + self.rng.randint(-3, 3))

    def guide_line(self, b0, b1, part, base=56, lo=50, hi=67):
        """가이드톤 대선율: 3·7음을 반음·온음으로 가장 가깝게 이어 긴 음으로"""
        p = None
        for a, b, c in self.spans_in(b0, b1):
            g = guide(c)
            cands = [x for x in range(lo, hi + 1) if x % 12 in g]
            q = min(cands, key=lambda x: (abs(x - p) if p else abs(x - (lo + hi) // 2)) + (1.5 if x == p else 0))
            self.add(part + " 대선율", a, b - a, q, base + self.rng.randint(-2, 2))
            p = q

    def phrase_dynamics(self, jazz=True):
        """선율 강약 공식: 높을수록 크게 · 프레이즈 정점까지 커졌다 작아짐 · (재즈) 8분 뒷박 강세, 사이 낮은 음은 유령음,
        당김음 강세 · 첫 음 조금 세게, 끝 긴 음은 여리게. 화음음은 선율 세기를 따라감."""
        R = self.rng
        by = {}
        for n in self.mel:
            by.setdefault(self.mel_part.get(id(n), "?"), []).append(n)
        for part, ns in by.items():
            ns.sort(key=lambda n: n[0])
            phrases, cur = [], [ns[0]]
            for a, b in zip(ns, ns[1:]):
                if b[0] - (a[0] + a[1]) >= .9:
                    phrases.append(cur); cur = []
                cur.append(b)
            phrases.append(cur)
            for ph in phrases:
                ps = [n[2] for n in ph]
                mean = sum(ps) / len(ps)
                pk = ps.index(max(ps))
                L = max(1, len(ph) - 1)
                for i, n in enumerate(ph):
                    v = n[3] + (n[2] - mean) * 1.1
                    pos, pkp = i / L, pk / L
                    v += 7 * (1 - abs(pos - pkp) / max(pkp, 1 - pkp, .01)) - 3
                    frac = n[0] % 1
                    if jazz and n[1] <= .6:
                        v += 7 if abs(frac - .5) < .05 else (-3 if frac < .05 else 0)
                    if jazz and 0 < i < len(ph) - 1 and n[1] <= .55 and n[2] < ps[i - 1] and n[2] < ps[i + 1] and R.random() < .6:
                        v -= 16
                    if abs(frac - .5) < .05 and n[1] >= .9:
                        v += 8
                    if i == 0:
                        v += 3
                    if i == len(ph) - 1 and n[1] >= 1:
                        v -= 5
                    n[3] = int(max(26, min(118, v + R.randint(-3, 3))))
        for h, top, dv in self.follow:
            h[3] = int(max(20, min(110, top[3] + dv + R.randint(-2, 2))))

    SEC_DYN = {"도입": .86, "A": .95, "A'": 1.0, "B": 1.1, "A''": 1.03, "끝": .86}

    def section_dynamics(self):
        """단락마다 크기: 도입 여리게 → B 에서 가장 크게 → 끝은 다시 여리게 (모든 악기)"""
        for part, xs in self.ev.items():
            for n in xs:
                f = next((self.SEC_DYN.get(nm, 1) for nm, s0, s1 in self.secs if s0 * self.ts - 1e-6 <= n[0] < s1 * self.ts - 1e-6), 1)
                n[3] = int(max(1, min(124, n[3] * f)))

    def fix_avoid(self, notes, jazz=True):
        """선율 화성 공식 (AI 가 쓴 선율을 코드에 맞춤)
        · 강박 / 1박 가까이 긴 음 / 뛰어 들어와 뛰어 나가는 음 → 코드음 (재즈는 9·11·13 텐션도 허용, 긴 음은 코드음+9 만)
        · 반음 위 '피할 음'은 반음 내려 코드음으로
        · 코드가 바뀌는데 이어 끄는 음이 새 코드와 안 맞으면 바뀌는 자리에서 끊음"""
        xs = sorted(notes)
        out = []
        for i, (t, d, p) in enumerate(xs):
            c = self.chord(t)
            ct = set(c.tones())
            ten = set(c.tensions()) if jazz else {(c.root + 2) % 12} if not c.is_dom() else set()
            ok = ct | ten
            beat = abs(t - round(t)) < 1e-6
            strong = beat and (round(t) % (2 if self.ts == 4 else 3) == 0)
            pv = xs[i - 1][2] if i else None
            nx = xs[i + 1][2] if i + 1 < len(xs) else None
            leapy = pv is not None and nx is not None and abs(p - pv) > 2 and abs(nx - p) > 2
            need = ok if d < 1.5 else (ct | {(c.root + 2) % 12} if not c.is_dom() else ct | ten)
            if p % 12 not in need and (strong or d >= .75 or leapy):
                cand = [p + k for k in (-1, 1, -2, 2, -3, 3) if (p + k) % 12 in (ct if (d >= 1 or not jazz) else need)]
                if cand:
                    p = cand[0]
            a, b, _ = self.span(t)
            if t + d > b + .1:
                c2 = self.chord(b)
                ok2 = set(c2.tones()) | (set(c2.tensions()) if jazz else set())
                if p % 12 not in ok2:
                    d = b - t
            out.append((t, d, p))
        return out

    def declash(self, min_len=.3):
        """편곡 정리: 선율과 반음·단9도로 부딪히거나 온음 이내에서 비비는 반주음은 → 같은 코드의 안 부딪히는 가장 가까운 음으로 옮김
        (못 옮기면 뺌, 베이스 근음은 그대로). 관악기·현악 독주 선율 위를 덮는 반주음도 뺌."""
        mel_ids = {id(n) for n in self.mel} | {id(h) for h, _, _ in self.follow}
        mels = [n for n in self.mel if n[1] >= min_len]
        buck = {}
        for m in mels:
            for k in range(int(m[0]), int(m[0] + m[1]) + 1):
                buck.setdefault(k, []).append(m)
        solo = [n for n in self.mel if "피아노" not in self.mel_part.get(id(n), "피아노")]

        def near_mels(n):
            seen = {}
            for k in range(int(n[0]), int(n[0] + n[1]) + 1):
                for m in buck.get(k, []):
                    seen[id(m)] = m
            return list(seen.values())

        def clash(q, n, ms):
            tot = 0.0
            for m in ms:
                ov = min(n[0] + n[1], m[0] + m[1]) - max(n[0], m[0])
                if ov <= .05 or m[2] == q:
                    continue
                d = m[2] - q
                if (d > 0 and d % 12 == 1) or (d < 0 and -d in (1, 13)) or 0 < abs(d) <= 2:
                    tot += ov
            return tot
        moved = removed = 0
        for part, xs in self.ev.items():
            if part in ("브러시", "드럼"):
                continue
            isbass = "베이스" in part
            keep = []
            onsets = {}
            for n in xs:
                onsets.setdefault(round(n[0], 2), set()).add(n[2])
            for n in xs:
                if id(n) in mel_ids:
                    keep.append(n); continue
                ms = near_mels(n)
                lim = max(.2, .25 * n[1])
                if ms and clash(n[2], n, ms) > lim:
                    a0, _, c = self.span(n[0])
                    if isbass and abs(n[0] - a0) < 1e-6:
                        keep.append(n); continue
                    pcs = set(c.tones()) if isbass else set(c.tones()) | set(c.tensions())
                    same = onsets.get(round(n[0], 2), set())
                    cands = sorted((q for q in range(n[2] - 4, n[2] + 5) if q != n[2] and q % 12 in pcs and q not in same),
                                   key=lambda q: abs(q - n[2]))
                    best = next((q for q in cands if clash(q, n, ms) <= lim), None)
                    if best is not None:
                        same.discard(n[2]); same.add(best)
                        n[2] = best; moved += 1; keep.append(n)
                    elif isbass:
                        keep.append(n)
                    else:
                        removed += 1
                    continue
                if part not in self.lead_parts and not isbass:
                    if any(min(n[0] + n[1], m[0] + m[1]) - max(n[0], m[0]) > .25 and n[2] > m[2] + 2 and (n[2] - m[2]) % 12 != 0 for m in solo):
                        removed += 1; continue
                keep.append(n)
            self.ev[part] = keep
        return moved, removed

    def low_mud(self, top=60):
        """낮은 자리(C4 아래)에서 반음으로 붙어 울리는 반주음 정리 — 한 옥타브 올려도 선율 아래고 안 비비면 올리고,
        아니면 화음 안의 음일 때만 뺌 (혼자 치는 음·베이스·선율은 그대로)"""
        mel_ids = {id(n) for n in self.mel} | {id(h) for h, _, _ in self.follow}
        allv = [(part, n) for part, xs in self.ev.items() if part not in ("브러시", "드럼") for n in xs]
        buck = {}
        for pn in allv:
            for k in range(int(pn[1][0]), int(pn[1][0] + pn[1][1]) + 1):
                buck.setdefault(k, []).append(pn)
        ov = lambda a, b: min(a[0] + a[1], b[0] + b[1]) - max(a[0], b[0])
        dead = set()

        def around(n):
            seen = {}
            for k in range(int(n[0]), int(n[0] + n[1]) + 1):
                for pn in buck.get(k, []):
                    if pn[1] is not n and id(pn[1]) not in dead and ov(n, pn[1]) > .15:
                        seen[id(pn[1])] = pn
            return list(seen.values())

        rub = lambda q, others: any(abs(m[2] - q) == 1 for _, m in others)
        moved = 0
        for part, n in allv:
            if part in self.lead_parts or "베이스" in part or id(n) in mel_ids or n[2] >= top or id(n) in dead:
                continue
            others = around(n)
            if not rub(n[2], others):
                continue
            mel_lo = min((m[2] for m in self.mel if ov(n, m) > .05), default=999)
            up = n[2] + 12
            if up < mel_lo - 2 and not rub(up, others) and up not in {m[2] for _, m in others}:
                n[2] = up; moved += 1
            elif any(m is not n and abs(m[0] - n[0]) < 1e-3 for m in self.ev[part]):
                dead.add(id(n))
        for part in self.ev:
            self.ev[part] = [n for n in self.ev[part] if id(n) not in dead]
        return moved, len(dead)

    # ---------- 박 → 초 ----------
    def bpm_at(self, b):
        if not self.tempo_pts:
            return self.bpm
        pts = self.tempo_pts
        if b <= pts[0][0]:
            return pts[0][1]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            if x0 <= b <= x1:
                return y0 + (y1 - y0) * (b - x0) / max(1e-9, x1 - x0)
        return pts[-1][1]

    def to_sheet(self, title, notes_text=(), info=None, drum_parts=("브러시", "드럼")):
        end = max(t + d for xs in self.ev.values() for t, d, _, _ in xs) + 2
        N = int(end * 96) + 2
        T = [0.0]
        for i in range(1, N):
            T.append(T[-1] + 60 / self.bpm_at((i - .5) / 96) / 96)

        def sec(b):
            i = min(max(b, 0) * 96, N - 2)
            k = int(i)
            return T[k] + (T[k + 1] - T[k]) * (i - k)

        sw = self.swing

        def swing(b):
            if not sw:
                return b
            f0 = math.floor(b + 1e-9)
            f = b - f0
            return f0 + (f * 2 * sw if f <= .5 else sw + (f - .5) * 2 * (1 - sw))

        sh = Sheet(title, self.key.name)
        sh.notes_text = list(notes_text)
        sh.info = info or {}
        sh.chords = [(round(sec(a), 3), round(sec(b), 3), c) for a, b, c in self.spans]
        for part, xs in self.ev.items():
            drum = part in drum_parts
            pp = sh.part(part, drum=drum)
            for t, d, p, v in sorted(xs):
                if drum:
                    t0, t1 = sec(t), sec(t + d)
                else:
                    t0, t1 = sec(swing(t)), sec(swing(t + d) - .02)
                pp.notes.append((round(t0, 3), round(max(t1, t0 + .06), 3), p, v))
        if self.pedal:
            pn = next((k for k in self.ev if "피아노 오른손" in k), None) or next((k for k in self.ev if "피아노" in k), None)
            if pn:
                sh.parts[pn].pedals = [(round(sec(a), 3), round(sec(b), 3)) for a, b in self.pedal]
        return sh
