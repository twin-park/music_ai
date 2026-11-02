# 기준 음악 만들기: 곡 설계 → 악기별 렌더 → 믹스·마스터 → reference/*.wav (+mp3)
import os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import render as R
from pieces import PIECES

OUT = "/home/drboom/project/car_bgm/reference"
_piano = None


def piano():
    global _piano
    if _piano is None:
        _piano = R.Salamander()
    return _piano


def render_score(sc, insts, tail=4.0):
    tm = R.TimeMap(sc)
    end_beat = max(n[0] + n[1] for n in sc.notes)
    length = int((tm(end_beat) + tail) * R.SR)
    tracks = []
    for name, (eng, db, pn, rv, hp) in insts.items():
        ns = [n for n in sc.notes if n[4] == name]
        if not ns:
            continue
        peds = [(a, b) for a, b, i in sc.pedal if i == name]
        if eng[0] == "piano":
            out = []
            for t, d, p, v, _ in ns:
                e = t + d
                for a, b in peds:
                    if a <= e <= b + 1e-6:
                        e = max(e, b); break
                out.append((float(tm(t)), float(tm(e)), p, v))
            x = piano().render(out, tm, length)
        else:
            _, font, bank, prog, drum = eng
            ccs = [(t, c, v) for t, i, c, v in sc.cc if i == name]
            x = R.fluid_render([(t, d, p, v) for t, d, p, v, _ in ns], ccs, peds, tm, length, R.SF[font], bank, prog, drum)
        tracks.append((x, db, pn, rv, hp))
    return R.master(tracks, length)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    names = sys.argv[1:] or list(PIECES)
    for nm in names:
        t0 = time.time()
        sc, insts = PIECES[nm]()
        y = render_score(sc, insts)
        R.write(y, f"{OUT}/{nm}.wav")
        pk = np.abs(y).max(); rms = np.sqrt((y ** 2).mean())
        print(f"{nm}: {len(y) / R.SR:.0f}초 · 음표 {len(sc.notes)} · peak {20 * np.log10(pk):.1f}dB rms {20 * np.log10(rms):.1f}dB · {time.time() - t0:.0f}s", flush=True)
