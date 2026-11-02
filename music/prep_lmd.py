# Lakh MIDI(MidiCaps 꼬리표 포함) → 학습용 배열 (PDMX 와 같은 꼴 + 분위기·크리스마스 표시)
import io, os, sys, glob, random
import numpy as np, pyarrow.parquet as pq, pretty_midi
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(__file__))
from tokens import Q, MAX_BAR, TIMESIGS, GENRES, MOODS

SRC = "/home/drboom/project/car_bgm/data/midicaps"
OUT = "/home/drboom/project/car_bgm/data/music_lmd"
GMAP = {"jazz": "jazz", "classical": "classical", "orchestral": "orchestral", "soundtrack": "soundtrack", "pop": "pop",
        "rock": "rock", "electronic": "electronic", "folk": "folk", "world": "world", "latin": "latin", "country": "country",
        "metal": "metal", "ambient": "ambient", "easylistening": "easylistening", "reggae": "world", "dance": "electronic",
        "instrumentalpop": "pop", "instrumentalrock": "rock", "techno": "electronic", "trance": "electronic", "popfolk": "folk"}


def one(row):
    try:
        pm = pretty_midi.PrettyMIDI(io.BytesIO(row["midi"]))
    except Exception:
        return None
    r = pm.resolution
    tick = lambda s: pm.time_to_tick(s)
    rows = []
    for ins in pm.instruments:
        prog = 128 if ins.is_drum else ins.program
        for n in ins.notes:
            a = int(round(tick(n.start) * Q / r)); b = int(round(tick(n.end) * Q / r))
            rows.append((a, prog, n.pitch, max(1, min(b - a, 4 * MAX_BAR)), n.velocity))
    if len(rows) < 100:
        return None
    notes = np.array(rows, np.int32); notes = notes[np.lexsort((notes[:, 2], notes[:, 0]))]
    end = int((notes[:, 0] + notes[:, 3]).max())
    tss = pm.time_signature_changes or [pretty_midi.TimeSignature(4, 4, 0.0)]
    bars, ts0 = [], tss[0]
    for k, ts in enumerate(tss):
        s = int(round(tick(ts.time) * Q / r)); e = int(round(tick(tss[k + 1].time) * Q / r)) if k + 1 < len(tss) else end
        L = ts.numerator * 4 * Q // ts.denominator
        if L <= 0 or L > MAX_BAR:
            return None
        t = s
        while t < e:
            bars.append(t); t += L
    if len(bars) < 16:
        return None
    bars = np.array(sorted(set(bars)), np.int32)
    tempo = pm.get_tempo_changes()[1]
    qpm = float(tempo[0]) if len(tempo) else 120.0
    tsn = f"{ts0.numerator}/{ts0.denominator}"
    g = 0
    for x in (row["genre"] or [])[:2]:
        if x in GMAP and GMAP[x] in GENRES:
            g |= 1 << GENRES.index(GMAP[x])
    md = 0
    for x in (row["mood"] or [])[:3]:
        if x in MOODS:
            md |= 1 << MOODS.index(x)
    xmas = int("christmas" in (row["mood"] or [])[:3])
    return notes, bars, min(max(qpm, 30), 250), TIMESIGS.index(tsn) if tsn in TIMESIGS else TIMESIGS.index("other"), g, md, xmas


def rows_iter(keep):
    for f in sorted(glob.glob(f"{SRC}/pool-*.parquet")):
        t = pq.read_table(f, columns=["id", "midi", "genre", "mood"])
        ids = t.column("id").to_pylist()
        for k, i in enumerate(ids):
            if i in keep:
                yield {c: t.column(c)[k].as_py() for c in ("midi", "genre", "mood")}


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    meta = []
    for f in sorted(glob.glob(f"{SRC}/pool-*.parquet")):
        meta += pq.read_table(f, columns=["id", "genre", "mood"]).to_pylist()
    rnd = random.Random(0)
    top1 = lambda m: (m["genre"] or ["-"])[0]
    pick = [m["id"] for m in meta if "jazz" in (m["genre"] or [])[:2]]
    pick += [m["id"] for m in meta if top1(m) in ("classical", "orchestral", "soundtrack", "ambient", "easylistening", "folk",
                                                    "world", "latin", "reggae", "country") and "jazz" not in (m["genre"] or [])[:2]]
    rest = [m["id"] for m in meta if top1(m) in ("pop", "electronic", "rock", "instrumentalpop") and "jazz" not in (m["genre"] or [])[:2]]
    rnd.shuffle(rest); pick += rest[:12000]
    keep = set(pick)
    print("고른 곡", len(keep), flush=True)
    res = []
    with Pool(6) as pool:                                     # CPU 6코어만
        for k, r in enumerate(pool.imap(one, rows_iter(keep), chunksize=16)):
            res.append(r)
            if k % 3000 == 0:
                print(k, flush=True)
    ok = [r for r in res if r is not None]
    print(f"쓸 수 있는 곡 {len(ok)}/{len(res)}")
    nn = np.array([len(r[0]) for r in ok]); nb = np.array([len(r[1]) for r in ok])
    np.save(f"{OUT}/notes.npy", np.concatenate([r[0] for r in ok])); np.save(f"{OUT}/bars.npy", np.concatenate([r[1] for r in ok]))
    split = np.zeros(len(ok), np.int8); perm = np.random.default_rng(0).permutation(len(ok)); split[perm[:400]] = 1; split[perm[400:800]] = 2
    np.savez(f"{OUT}/pieces.npz", note_off=np.concatenate([[0], np.cumsum(nn)[:-1]]), note_n=nn,
             bar_off=np.concatenate([[0], np.cumsum(nb)[:-1]]), bar_n=nb,
             qpm=np.array([r[2] for r in ok], np.float32), ts=np.array([r[3] for r in ok], np.int8),
             genre=np.array([r[4] for r in ok], np.int32), mood=np.array([r[5] for r in ok], np.int32),
             xmas=np.array([r[6] for r in ok], np.int8), rated=np.zeros(len(ok), bool), rating=np.zeros(len(ok), np.float32), split=split)
    g = np.array([r[4] for r in ok])
    print("재즈", int((g >> GENRES.index("jazz") & 1).sum()), "클래식", int((g >> GENRES.index("classical") & 1).sum()),
          "크리스마스", int(sum(r[6] for r in ok)))
