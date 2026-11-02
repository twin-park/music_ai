# AxonData 아기 울음 공개 샘플(CC-BY 4.0, 18개 녹음)을 귀 데이터에 덧붙인다. 녹음 단위로 학습 14 / 검증 4.
import glob, os, sys
import numpy as np, soundfile as sf
sys.path.insert(0, os.path.dirname(__file__))
from labels import GROUP_IDS, N_GROUPS

D = "/home/drboom/project/car_bgm/data"
ix = dict(np.load(f"{D}/ear/index.npz"))
if (ix["src"] == 2).any():
    sys.exit("이미 넣음")
files = sorted(glob.glob(f"{D}/babycry/cry_*_16k.wav"))
off = os.path.getsize(f"{D}/ear/wav.i16") // 2
y0 = np.zeros(N_GROUPS, np.uint8); y0[GROUP_IDS.index("baby_cry")] = 1; y0[GROUP_IDS.index("crying")] = 1
add = {k: [] for k in ("offset", "length", "y", "emo", "split", "src", "license")}
with open(f"{D}/ear/wav.i16", "ab") as f:
    for k, p in enumerate(files):
        x, sr = sf.read(p, dtype="int16"); assert sr == 16000
        for s in range(0, len(x), 10 * sr):          # 10초 조각
            c = x[s:s + 10 * sr]
            if len(c) < 2 * sr:
                continue
            f.write(c.tobytes())
            add["offset"].append(off); add["length"].append(len(c)); off += len(c)
            add["y"].append(y0); add["emo"].append(-1); add["split"].append(0 if k < 14 else 1)
            add["src"].append(2); add["license"].append("CC-BY-4.0 AxonData")
for k in add:
    ix[k] = np.concatenate([ix[k], np.array(add[k]).astype(ix[k].dtype)])
np.savez(f"{D}/ear/index.npz", **ix)
print("덧붙인 조각", len(add["offset"]), "학습", add["split"].count(0), "검증", add["split"].count(1))
