# PDMX(MusPy JSON) → 학습용 배열.  4분음표 = 12칸으로 맞춘다.
# 결과 data/music/: notes.npy (N,5: t, prog(128=드럼), pitch, dur, vel), bars.npy (마디 시작),
#                   pieces.npz (곡별 음표·마디 범위, 템포, 박자, 장르, 평점, 나눔)
import os, sys, json
import numpy as np, pandas as pd
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(__file__))
from tokens import Q, MAX_BAR, TIMESIGS, GENRES

ROOT = "/home/drboom/project/car_bgm/data/pdmx/PDMX"
OUT = "/home/drboom/project/car_bgm/data/music"
GMAP = {"classical": "classical", "pop": "pop", "rock": "rock", "jazz": "jazz", "folk": "folk",
        "soundtrack": "soundtrack", "religiousmusic": "religious", "electronic": "electronic",
        "worldmusic": "world", "rbfunksoul": "rnb", "metal": "metal", "country": "country"}


def one(args):
    path, genres = args
    try:
        j = json.load(open(os.path.join(ROOT, path)))
    except Exception:
        return None
    r = j["resolution"]
    cv = lambda t: int(round(t * Q / r))
    rows = []
    for tr in j["tracks"]:
        drum = str(tr.get("is_drum")) == "True"
        prog = 128 if drum else int(tr.get("program", 0))
        for n in tr["notes"]:
            if n.get("is_grace"):
                continue
            d = cv(n["duration"])
            if d <= 0 or not (0 <= n["pitch"] < 128):
                continue
            rows.append((cv(n["time"]), prog, n["pitch"], min(d, 4 * MAX_BAR), n.get("velocity", 64)))
    if len(rows) < 32:
        return None
    notes = np.array(rows, np.int32)
    end = max(cv(j.get("song_length") or 0), int((notes[:, 0] + notes[:, 3]).max()))
    bl = sorted({cv(b["time"]) for b in j.get("barlines", [])})
    if len(bl) < 4:
        return None
    if bl[0] > 0:
        bl = [0] + bl
    bars = np.array(bl + [end], np.int32)
    lens = np.diff(bars)
    if (lens <= 0).any() or (lens[:-1] > MAX_BAR).any():
        return None
    bars = bars[:-1]
    if lens[-1] > MAX_BAR:          # 마지막 마디가 길면(끝 늘임 등) 잘라 둠
        notes = notes[notes[:, 0] < bars[-1] + MAX_BAR]
    ts = j["time_signatures"][0] if j.get("time_signatures") else {"numerator": 4, "denominator": 4}
    tss = f"{ts['numerator']}/{ts['denominator']}"
    qpm = float(j["tempos"][0]["qpm"]) if j.get("tempos") else 120.0
    g = 0
    for x in str(genres).split("-"):
        if x in GMAP:
            g |= 1 << GENRES.index(GMAP[x])
    return notes, bars, min(max(qpm, 30), 250), TIMESIGS.index(tss) if tss in TIMESIGS else TIMESIGS.index("other"), g


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    d = pd.read_csv(f"{ROOT}/PDMX.csv", low_memory=False)
    d = d[d["subset:deduplicated"]].reset_index(drop=True)
    jobs = [(p[2:] if p.startswith("./") else p, gg) for p, gg in zip(d.path, d.genres)]
    res = []
    with Pool(6) as pool:      # CPU 6코어만, 몇 분
        for k, r in enumerate(pool.imap(one, jobs, chunksize=64)):
            res.append(r)
            if k % 20000 == 0:
                print(k, flush=True)
    keep = [i for i, r in enumerate(res) if r is not None]
    print(f"쓸 수 있는 곡 {len(keep)}/{len(res)}")
    notes = np.concatenate([res[i][0] for i in keep])
    bars = np.concatenate([res[i][1] for i in keep])
    nn = np.array([len(res[i][0]) for i in keep]); nb = np.array([len(res[i][1]) for i in keep])
    rng = np.random.default_rng(0)
    split = np.zeros(len(keep), np.int8)
    perm = rng.permutation(len(keep))
    split[perm[:1000]] = 1                       # 검증
    split[perm[1000:2000]] = 2                   # 시험(새로움 검사용으로도)
    np.save(f"{OUT}/notes.npy", notes)
    np.save(f"{OUT}/bars.npy", bars)
    np.savez(f"{OUT}/pieces.npz",
             note_off=np.concatenate([[0], np.cumsum(nn)[:-1]]), note_n=nn,
             bar_off=np.concatenate([[0], np.cumsum(nb)[:-1]]), bar_n=nb,
             qpm=np.array([res[i][2] for i in keep], np.float32), ts=np.array([res[i][3] for i in keep], np.int8),
             genre=np.array([res[i][4] for i in keep], np.int32),
             rated=d["subset:rated_deduplicated"].values[keep], rating=d.rating.values[keep].astype(np.float32),
             split=split, path=d.path.values[keep])
    v = notes[:, 4]
    print("음표", len(notes), "마디", len(bars), "세기 종류", np.unique(v).size, "세기 평균", v.mean())
