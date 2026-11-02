# 강약 점검: 악기별 세기 평균·표준편차·범위 (같은 세기로만 치는지)
import sys, numpy as np
from notation import load
for path in sys.argv[1:]:
    sh = load(path)
    row = []
    for k, p in sh.parts.items():
        v = np.array([n[3] for n in p.notes])
        if len(v):
            row.append(f"{k} {v.mean():.0f}±{v.std():.0f}({v.min()}~{v.max()})")
    print(path.split("/")[-1], " · ".join(row))
