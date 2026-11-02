import os, sys, struct, numpy as np
sys.path.insert(0, "/home/drboom/project/car_bgm/score/ai")
from npmodel import NpLM
out = sys.argv[1]
for w in ("chord", "melody"):
    m = NpLM(f"/home/drboom/project/car_bgm/runs/score_{w}/best.npz")
    rng = np.random.default_rng(1); V = m.cfg["vocab"]
    seq = rng.integers(4, V, 600).tolist()
    caches = [dict(max=m.cfg["ctx"]) for _ in m.layers]
    pos, recs = 0, []
    for n in [8, 1, 1, 5, 1, 12, 1, 1, 1, 7, 3, 1] * 10:
        ids = seq[pos:pos + n]
        if pos + n > 500: break
        lg = m.step(ids, caches, pos); pos += n
        recs.append((ids, lg.astype(np.float32)))
    with open(f"{out}/test_{w}.bin", "wb") as f:
        f.write(struct.pack("<i", len(recs)))
        for ids, lg in recs:
            f.write(struct.pack("<i", len(ids)) + np.array(ids, np.int32).tobytes() + lg.tobytes())
