# 악보 점검: 강박 구성음 비율 · 반주와 반음 충돌 · 똑같은 마디 반복
import sys, collections
from pieces import PIECES
from theory import chord_at, prog
MEL = {"piano", "flute", "violins1", "vibes", "cello"}
for nm, f in PIECES.items():
    sc, insts = f()
    notes = sc.notes
    # 선율 악기 = 그 곡에서 가장 높은 음역을 많이 낸 것
    by = collections.defaultdict(list)
    for n in notes: by[n[4]].append(n)
    clash = tot = 0
    for inst, ns in by.items():
        if inst not in MEL: continue
        others = [m for m in notes if m[4] != inst and m[4] != "drums"]
        for t, d, p, v, _ in ns:
            if p < 64 or d < 0.75: continue
            tot += 1
            for t2, d2, p2, v2, _ in others:
                if t2 <= t + 0.01 < t2 + d2 and (abs(p - p2) % 12) in (1, 11) and abs(p - p2) < 24:
                    clash += 1; break
    # 똑같은 마디
    bars = collections.Counter()
    for inst, ns in by.items():
        if inst == "drums": continue
        sig = collections.defaultdict(list)
        for t, d, p, v, _ in ns: sig[int(t // sc.bpb)].append((round(t % sc.bpb, 2), p))
        for b, s in sig.items(): bars[(inst, tuple(sorted(s)))] += 1
    rep = sum(c - 1 for c in bars.values() if c > 1); nbar = sum(bars.values())
    print(f"{nm}: 음표 {len(notes)} · 높은음 반음충돌 {clash}/{tot} ({clash / max(1, tot) * 100:.1f}%) · 똑같은 마디 {rep}/{nbar}")
