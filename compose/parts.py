# 반주·베이스·드럼 패턴 (장르별)
import random
from theory import chord_at, near, voicing, QUAL


def bass_note(ch, lo=36, hi=52, ref=43):
    p = near(ch.bass, ref)
    while p < lo: p += 12
    while p > hi: p -= 12
    return p


# ---------- 클래식 ----------
def piano_broken(sc, prog, b0, b1, inst, pattern, vel=52, lh_ref=45, pedal=True, rng=None, swell=None):
    """왼손 펼친화음. pattern: 화음 안 순번 목록(0=베이스, 1..=위 구성음), 8분음 단위. 화음 바뀔 때마다 페달."""
    rng = rng or random.Random(1)
    prev = None
    for s, e, ch in chord_spans(prog, b0, b1, sc.bpb):
        bass = bass_note(ch, 33, 50, lh_ref - 7)
        up = voicing(ch.tones(), prev, bass + 7, min(bass + 19, 64), 3); prev = up
        notes = [bass] + up + [up[0] + 12 if up[0] + 12 <= 67 else up[-1]]     # 선율 자리(65 위)는 비워 둠
        # 마디마다 모양을 조금씩: 기본 / 순서 뒤집기 / 한 음 쉬기 / 위로 펼쳐 올라가기 (프레이즈 끝)
        bar_i = int(s // sc.bpb)
        roll = rng.random()
        pat = list(pattern)
        if bar_i % 4 == 3:
            pat = sorted(set(pattern)) + sorted(set(pattern))[::-1][1:]     # 프레이즈 끝: 올라갔다 내려오기
        elif roll < 0.3:
            pat = [pattern[0]] + pattern[1:][::-1]
        elif roll < 0.5:
            pat = [pattern[0]] + [x if i % 3 != 1 else -1 for i, x in enumerate(pattern[1:])]
        if rng.random() < 0.25:                                               # 베이스를 옥타브 아래로
            notes[0] = notes[0] - 12 if notes[0] - 12 >= 28 else notes[0]
        k, tt = 0, s
        while tt < e - 1e-6:
            idx = pat[k % len(pat)]
            if idx >= 0:
                v = vel + (6 if k == 0 else 0) + rng.randint(-4, 4) + (swell(tt) if swell else 0)
                sc.add(tt, 1.6 if idx == 0 else 1.0, notes[min(idx, len(notes) - 1)], v, inst)
            tt += 0.5; k += 1
        if pedal:
            sc.pedal.append((s, e - 0.03, inst))


def chord_spans(prog, b0, b1, bpb):
    for s, c in prog:
        if b0 * bpb - 1e-6 <= s < b1 * bpb - 1e-6:
            yield s, min(s + c.beats, b1 * bpb), c


def strings_pad(sc, prog, b0, b1, voices, vel=60, rng=None, top=None):
    """현악 합주: voices = [(악기, 낮은음, 높은음)] 아래→위. 성부 진행으로 이어 잡음. top 주면 맨 위는 그 선율 대신 생략."""
    prev = None
    for s, e, c in chord_spans(prog, b0, b1, sc.bpb):
        bass = bass_note(c, 28, 48, 38)
        pcs = c.tones()
        upper = voicing(pcs, prev, 50, 76, len(voices) - 1); prev = upper
        notes = [bass] + upper
        rng = rng or random.Random(7)
        for vi, ((inst, lo, hi), p) in enumerate(zip(voices, notes)):
            while p < lo: p += 12
            while p > hi: p -= 12
            span = e - s
            if vi > 0 and span >= 2 and rng.random() < 0.45:             # 안쪽 성부가 가끔 지나가는 음으로 움직임
                q = p + rng.choice([-2, -1, 1, 2])
                if not any((q - c) % 12 in (1, 11) for c in pcs) and lo <= q <= hi:
                    sc.add(s, span / 2, p, vel + rng.randint(-4, 4), inst); sc.add(s + span / 2, span / 2 + 0.05, q, vel - 4, inst)
                    continue
            if span >= 3 and rng.random() < 0.3:                          # 다시 긋기
                sc.add(s, span / 2, p, vel + rng.randint(-4, 4), inst); sc.add(s + span / 2, span / 2 + 0.05, p, vel - 6, inst)
                continue
            sc.add(s, span + 0.05, p, vel + rng.randint(-4, 4), inst)


def swell_cc(sc, inst, b0, b1, lo=50, hi=110, per=4):
    """표현(CC11) 부풀었다 가라앉기: per 마디마다 한 번"""
    import math
    t = b0 * sc.bpb
    while t < b1 * sc.bpb:
        ph = ((t - b0 * sc.bpb) / (per * sc.bpb)) % 1.0
        sc.cc.append((t, inst, 11, int(lo + (hi - lo) * (0.5 - 0.5 * math.cos(2 * math.pi * ph)))))
        t += 0.25


# ---------- 재즈 ----------
def walking_bass(sc, prog, b0, b1, inst, rng, vel=82):
    """워킹 베이스: 1박 근음, 2~3박 구성음/음계로 다음 근음 쪽, 4박 반음 접근."""
    t, p = b0 * sc.bpb, None
    while t < b1 * sc.bpb - 1e-6:
        ch, nxt = chord_at(prog, t), chord_at(prog, t + 1)
        beat_in = round(t) % 4
        root = bass_note(ch, 28, 50, p or 40)
        next_root = bass_note(chord_at(prog, t + (4 - beat_in) if beat_in else t + 4), 28, 50, root)
        if abs(t - [s for s, c in prog if c is ch][0]) < 1e-6:
            q = root
        elif beat_in == 3 or chord_at(prog, t + 1) is not ch:
            q = next_root + rng.choice([-1, 1, 7 - 12, -1])                    # 접근음
        else:
            tones = [x for x in range(28, 52) if x % 12 in ch.tones() + [(ch.root + 2) % 12, (ch.root + 9) % 12]]
            q = min(tones, key=lambda x: abs(x - (p + rng.choice([-5, -3, -2, 2, 3, 5]))) + 0.01 * rng.random())
        q = max(28, min(52, q))
        sc.add(t, 0.95, q, vel + (6 if beat_in in (1, 3) else 0) + rng.randint(-6, 6), inst)
        p = q; t += 1


def two_feel_bass(sc, prog, b0, b1, inst, rng, vel=74):
    t = b0 * sc.bpb
    while t < b1 * sc.bpb - 1e-6:
        ch = chord_at(prog, t)
        root = bass_note(ch, 28, 50, 38)
        sc.add(t, 1.9, root, vel + rng.randint(-5, 5), inst)
        fifth = root + 7 if root + 7 <= 52 else root - 5
        sc.add(t + 2, 1.9, fifth if chord_at(prog, t + 2) is ch else bass_note(chord_at(prog, t + 2), 28, 50, root), vel - 6 + rng.randint(-5, 5), inst)
        t += 4


def rootless(ch, prev):
    """3·5·7·9 또는 7·9·3·5 (근음 없는 보이싱)"""
    r, iv = ch.root, QUAL[ch.q][0]
    third = next((i for i in iv if i in (3, 4)), 4); sev = next((i for i in iv if i in (9, 10, 11)), 10)
    fifth = 6 if ch.q in ("m7b5", "dim") else 7
    ninth = 1 if ch.q in ("7b9",) else 2
    pcs = [(r + i) % 12 for i in (third, fifth, sev, ninth)]
    return voicing(pcs, prev, 52, 74, 4)


COMP_RHY = [[(0, 1.4)], [(0, 0.4), (1.5, 1.2)], [(1.5, 0.4), (3.5, 0.9)], [(-0.5, 1.2), (2, 0.4)],
            [(0, 0.4), (2.5, 1.2)], [(1, 0.4), (2.5, 0.4)], [(-0.5, 1.8)], [(0.5, 0.4), (3, 0.9)]]


def jazz_comp(sc, prog, b0, b1, inst, rng, vel=56, density=1.0):
    prev = None
    for s, e, c in chord_spans(prog, b0, b1, sc.bpb):
        v = rootless(c, prev); prev = v
        span = e - s
        for on, d in rng.choice(COMP_RHY):
            if on >= span or rng.random() > density:
                continue
            t = s + on
            if t < b0 * sc.bpb:
                continue
            for p in v:
                sc.add(t, d, p, vel + rng.randint(-6, 6), inst)


def swing_drums(sc, b0, b1, inst, rng, vel=70, fill_every=8, brushes=False):
    RIDE, HH, SN, KICK, CRASH = (51, 44, 38, 36, 49)
    for b in range(b0, b1):
        t0 = b * 4
        for k, on in enumerate([0, 1, 1 + 2 / 3, 2, 3, 3 + 2 / 3]):          # 딩 딩-다 딩 딩-다
            if rng.random() < 0.08 and on % 1:
                continue
            sc.add(t0 + on, 0.3, RIDE, vel + (8 if on in (1, 3) else 0) - (10 if on % 1 else 0) + rng.randint(-6, 6), inst)
        sc.add(t0 + 1, 0.2, HH, vel - 10, inst); sc.add(t0 + 3, 0.2, HH, vel - 10, inst)
        if (b - b0) % fill_every == fill_every - 1:                          # 프레이즈 끝 채우기
            for on in [2 + 2 / 3, 3, 3 + 1 / 3, 3 + 2 / 3]:
                sc.add(t0 + on, 0.2, SN, vel + rng.randint(0, 14), inst)
        else:
            for on in [1.5 + 1 / 6, 2 + 2 / 3, 3.5 + 1 / 6]:                  # 스네어 툭툭(유령음)
                if rng.random() < 0.3:
                    sc.add(t0 + on, 0.2, SN, vel - 25 + rng.randint(0, 12), inst)
        if rng.random() < 0.25:
            sc.add(t0 + rng.choice([0, 2 + 2 / 3, 3 + 2 / 3]), 0.2, KICK, vel - 20, inst)
        if (b - b0) % 8 == 0:
            sc.add(t0, 1, CRASH, vel - 8, inst)


# ---------- 보사노바 ----------
BOSSA_GTR = [0, 1.5, 2.5, 3.5]          # 화음 뜯는 자리 (2마디 꼴 중 첫 마디)
BOSSA_GTR2 = [0.5, 1.5, 2.5, 3]


def bossa_guitar(sc, prog, b0, b1, inst, rng, vel=58):
    prev = None
    for b in range(b0, b1):
        t0 = b * 4
        ch = chord_at(prog, t0)
        v = voicing(ch.tones() if len(ch.tones()) >= 4 else ch.tones() + [(ch.root + 2) % 12], prev, 52, 70, 4); prev = v
        sc.add(t0, 0.9, bass_note(ch, 40, 52, 45), vel + 6, inst)              # 엄지 베이스
        sc.add(t0 + 2, 0.9, bass_note(ch, 40, 52, 45) + (7 if rng.random() < 0.5 else 0), vel, inst)
        for on in (BOSSA_GTR if b % 2 == 0 else BOSSA_GTR2):
            c2 = chord_at(prog, t0 + on)
            vv = v if c2 is ch else voicing(c2.tones(), v, 52, 70, 4)
            for k, p in enumerate(vv):
                sc.add(t0 + on + k * 0.012, 0.45, p, vel - 4 + rng.randint(-5, 5), inst)


def bossa_drums(sc, b0, b1, inst, rng, vel=60):
    RIM, KICK, SHK, HH = 37, 36, 70, 42
    for b in range(b0, b1):
        t0 = b * 4
        for on in ([0, 1.5, 3] if b % 2 == 0 else [1, 2.5]):
            sc.add(t0 + on, 0.2, RIM, vel + rng.randint(-6, 6), inst)
        for on in (0, 1.5, 2, 3.5):
            sc.add(t0 + on, 0.2, KICK, vel - 14 + rng.randint(-4, 4), inst)
        for k in range(16):
            sc.add(t0 + k * 0.25, 0.1, SHK, vel - 22 + (8 if k % 2 == 0 else 0) + rng.randint(-5, 5), inst)
