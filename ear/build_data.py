# FSD50K(16k) + CREMA-D 를 파형 하나짜리 큰 파일(int16, 16kHz)과 색인으로 만든다.
# 결과: data/ear/wav.i16 , data/ear/index.npz
#   offset/length(샘플), y(묶음 multi-hot), emo(-1=없음), split(0 학습 1 검증 2 시험), src(0 FSD 1 CREMA)
import io, os, sys, glob, re
import numpy as np, pyarrow.parquet as pq, soundfile as sf
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(__file__))
from labels import fsd_to_groups, N_GROUPS, GROUP_IDS, EMOTIONS

ROOT = "/home/drboom/project/car_bgm/data"
OUT = f"{ROOT}/ear"
SR = 16000
MAX_SEC = 30


def decode(b):
    x, sr = sf.read(io.BytesIO(b), dtype="int16", always_2d=True)
    x = x.mean(1).astype(np.int16) if x.shape[1] > 1 else x[:, 0]
    assert sr == SR, sr
    return x[: MAX_SEC * SR]


def do_fsd(path):
    split = {"train": 0, "validation": 1, "test": 2}[os.path.basename(path).split("-")[0]]
    t = pq.read_table(path, columns=["audio", "labels", "title", "tags", "license"]).to_pylist()
    out = []
    for r in t:
        x = decode(r["audio"]["bytes"])
        text = (r["title"] or "") + " " + " ".join(r["tags"] or [])
        out.append((x, fsd_to_groups(r["labels"], text), -1, split, 0, r["license"] or ""))
    return out


def crema_split(actor):
    return 0 if actor <= 1073 else (1 if actor <= 1082 else 2)   # 말하는 사람이 겹치지 않게 나눔


def do_crema(path):
    t = pq.read_table(path, columns=["file", "audio", "emotion"]).to_pylist()
    out = []
    sp = GROUP_IDS.index("speech")
    for r in t:
        actor = int(re.search(r"(\d{4})_", r["file"]).group(1))
        x = decode(r["audio"]["bytes"])
        y = [0] * N_GROUPS
        y[sp] = 1
        out.append((x, y, EMOTIONS.index(r["emotion"]), crema_split(actor), 1, "ODbL"))
    return out


def run_job(job):
    kind, path = job
    return path, (do_fsd if kind == "fsd" else do_crema)(path)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    jobs = [("fsd", p) for p in sorted(glob.glob(f"{ROOT}/fsd50k/data/*.parquet"))]
    jobs += [("crema", p) for p in sorted(glob.glob(f"{ROOT}/cremad/*.parquet"))]
    f = open(f"{OUT}/wav.i16", "wb")
    off = 0
    offs, lens, ys, emos, splits, srcs, lic = [], [], [], [], [], [], []
    with Pool(4) as pool:   # CPU 4코어만
        for path, res in pool.imap_unordered(run_job, jobs):
            for x, y, e, s, src, l in res:
                f.write(x.tobytes())
                offs.append(off); lens.append(len(x)); off += len(x)
                ys.append(y); emos.append(e); splits.append(s); srcs.append(src); lic.append(l)
            print(os.path.basename(path), len(res), f"{off / SR / 3600:.1f}h", flush=True)
    f.close()
    np.savez(f"{OUT}/index.npz", offset=np.array(offs, np.int64), length=np.array(lens, np.int64),
             y=np.array(ys, np.uint8), emo=np.array(emos, np.int8), split=np.array(splits, np.int8),
             src=np.array(srcs, np.int8), license=np.array(lic))
    y = np.array(ys); sp = np.array(splits)
    for i, g in enumerate(GROUP_IDS):
        print(f"{g:10s} 학습 {int(y[sp == 0, i].sum()):6d}  검증 {int(y[sp == 1, i].sum()):5d}  시험 {int(y[sp == 2, i].sum()):5d}")
