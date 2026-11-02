# 악보 점검: 선율의 긴 음이 반주와 반음·단9도로 부딪히는지 + 악기별 음 수·구간.  python check.py 악보.txt
import sys
from notation import load

sh = load(sys.argv[1])
P = sh.parts
LEADS = [k for k in P if not any(w in k for w in ("피아노", "베이스", "브러시", "드럼", "기타", "현악", "로즈", "대선율"))]
lead_notes = [(k, n) for k in LEADS for n in P[k].notes]
busy = [(a, b) for _, (a, b, _, _) in lead_notes]
tops = {}
for n in P.get("피아노 오른손", type("x", (), {"notes": []})).notes:
    tops[round(n[0], 2)] = max(tops.get(round(n[0], 2), 0), n[2])
for n in P.get("피아노 오른손", type("x", (), {"notes": []})).notes:
    if tops[round(n[0], 2)] == n[2] and not any(a < n[1] and b > n[0] for a, b in busy):
        lead_notes.append(("피아노 선율", n))
acc = [(k, n) for k in P if k not in LEADS and "브러시" not in k and "드럼" not in k for n in P[k].notes]
bad = tot = 0
for who, (t0, t1, p, v) in lead_notes:
    if t1 - t0 < .5:
        continue
    tot += 1
    for k, (a, b, q, w) in acc:
        if q != p and a < t1 - .05 and b > t0 + .05 and ((p - q) % 12 == 1 and q < p or (q - p) in (1, 13)):
            bad += 1
            c = sh.chord_at(t0)
            print(f"  {who} {sh.key.note_text(p)} @{t0:.1f}초 ↔ {k} {sh.key.note_text(q)} ({c.name(sh.key) if c else '-'})")
            break
print(f"긴 선율음 {tot}개 중 반음·단9도 부딪힘 {bad}")
for k, p in P.items():
    print(f"  {k}: 음 {len(p.notes)} · {min(n[0] for n in p.notes):.0f}~{max(n[1] for n in p.notes):.0f}초")
