# 브라우저 악기 소리 v2: 실제 녹음 피아노(Salamander, 2층) + 사운드폰트(Sonatina·GeneralUser) → opus
# 결과 web/build/samples_jazz.json · samples_orch.json
import os, sys, json, base64, subprocess, tempfile, glob, re
import numpy as np, soundfile as sf
sys.path.insert(0, os.path.dirname(__file__))
from make_samples import render as fluid_one, TOOLS
import make_samples as MS

ROOT = "/home/drboom/project/car_bgm"
OUT = f"{ROOT}/web/build"
SAL = f"{ROOT}/data/salamander"
SF = {"sso": f"{ROOT}/data/sf/Sonatina_Symphonic_Orchestra.sf2", "gu": f"{ROOT}/data/sf/GeneralUser-GS.sf2"}


def enc(x, sr, br="48k"):
    with tempfile.TemporaryDirectory() as td:
        sf.write(f"{td}/a.wav", x, sr)
        subprocess.run([f"{TOOLS}/ffmpeg", "-y", "-loglevel", "error", "-i", f"{td}/a.wav", "-c:a", "libopus", "-b:a", br,
                        f"{td}/b.ogg"], check=True)
        return base64.b64encode(open(f"{td}/b.ogg", "rb").read()).decode()


def salamander(layer):
    notes, data, gain = [], [], []
    for f in sorted(glob.glob(f"{SAL}/*v{layer}.wav")):
        n = int(os.path.basename(f)[:3])
        x, sr = sf.read(f, dtype="float32")
        keep = 6.0 if n <= 48 else (4.5 if n <= 72 else 3.0)
        x = x[: int(keep * sr)]
        fd = int(0.3 * sr); x[-fd:] *= np.linspace(1, 0, fd)[:, None]
        pk = float(np.abs(x).max()) + 1e-9
        notes.append(n); data.append(enc(x / pk * 0.9, sr, "56k")); gain.append(round(pk, 4))
    return {"notes": notes, "data": data, "release": 0.35, "gain": gain}


def sfont(font, prog, lo, hi, step, dur, rel, drum_notes=None, bank=0):
    MS.SF2 = SF[font]
    if drum_notes:
        res = [fluid_kit(font, prog, n) for n in drum_notes]
        return {"notes": drum_notes, "data": [r[0] for r in res], "release": rel, "gain": [round(r[1], 4) for r in res]}
    notes = list(range(lo, hi + 1, step))
    res = [fluid_one(prog, n, dur) for n in notes]
    return {"notes": notes, "data": [r[0] for r in res], "release": rel, "gain": [round(r[1], 4) for r in res]}


def fluid_kit(font, kit, note):
    """드럼 킷 하나의 소리 하나 (채널 10, 킷 번호 = program)"""
    import mido
    with tempfile.TemporaryDirectory() as td:
        mid = mido.MidiFile(ticks_per_beat=480); tr = mido.MidiTrack(); mid.tracks.append(tr)
        tr.append(mido.MetaMessage("set_tempo", tempo=500000, time=0))
        tr.append(mido.Message("program_change", channel=9, program=kit, time=0))
        tr.append(mido.Message("note_on", channel=9, note=note, velocity=100, time=10))
        tr.append(mido.Message("note_off", channel=9, note=note, velocity=0, time=300))
        tr.append(mido.MetaMessage("end_of_track", time=int(2.2 * 960)))
        mid.save(f"{td}/a.mid")
        subprocess.run([f"{TOOLS}/fluidsynth", "-ni", "-R", "0", "-C", "0", "-g", "0.8", "-r", "48000", "-F", f"{td}/a.wav",
                        SF[font], f"{td}/a.mid"], check=True, capture_output=True)
        x, sr = sf.read(f"{td}/a.wav"); x = x.mean(1)
        a = np.abs(x); st = int(np.argmax(a > 1e-3)) if (a > 1e-3).any() else 0
        x = x[max(0, st - 48):][: int(2.0 * sr)]
        nz = np.where(np.abs(x) > 1e-4)[0]; x = x[: (nz[-1] + 480) if len(nz) else 4800]
        fd = min(len(x), 2400); x[-fd:] *= np.linspace(1, 0, fd)
        pk = float(np.abs(x).max()) + 1e-9
        return enc((x / pk * 0.9).astype(np.float32), sr, "40k"), pk


DRUMS = [35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 59, 69, 70, 75, 76, 77]

JAZZ = {
    "piano_soft": "SAL08", "piano_loud": "SAL12",
    "epiano": ("gu", 4, 36, 96, 4, 3.0, 0.3), "organ": ("gu", 17, 36, 96, 4, 3.0, 0.12),
    "vibes": ("gu", 11, 48, 96, 4, 3.0, 0.5), "jguitar": ("gu", 26, 40, 84, 4, 2.5, 0.2), "nylon": ("gu", 24, 40, 84, 4, 2.5, 0.25),
    "bass": ("gu", 32, 28, 64, 3, 2.5, 0.12), "tenor": ("gu", 66, 44, 80, 3, 2.5, 0.12), "alto": ("gu", 65, 49, 84, 3, 2.5, 0.12),
    "trumpet": ("gu", 56, 52, 86, 3, 2.5, 0.12), "flute": ("sso", 14, 60, 96, 4, 3.0, 0.2), "strings": ("gu", 49, 36, 96, 4, 4.0, 0.45),
    "kit_jazz": ("gu", 32, 0, 0, 0, 0, 0.1, DRUMS), "kit_brush": ("gu", 40, 0, 0, 0, 0, 0.1, DRUMS), "kit_latin": ("gu", 0, 0, 0, 0, 0, 0.1, DRUMS),
}
ORCH = {
    "piano_soft": "SAL08", "piano_loud": "SAL12",
    "violins": ("sso", 2, 55, 100, 4, 4.0, 0.4), "violas": ("sso", 6, 48, 88, 4, 4.0, 0.4), "cellos": ("sso", 8, 36, 76, 4, 4.0, 0.4),
    "basses": ("sso", 10, 28, 60, 4, 4.0, 0.4), "harp": ("sso", 1, 36, 96, 4, 3.0, 0.5), "flute": ("sso", 14, 60, 96, 4, 3.0, 0.2),
    "oboe": ("sso", 16, 58, 91, 4, 3.0, 0.2), "clarinet": ("sso", 20, 50, 91, 4, 3.0, 0.2), "bassoon": ("sso", 23, 34, 72, 4, 3.0, 0.2),
    "horn": ("sso", 30, 40, 77, 4, 3.0, 0.3), "trumpet": ("sso", 27, 54, 86, 4, 3.0, 0.2), "trombone": ("sso", 32, 40, 72, 4, 3.0, 0.2),
    "tuba": ("sso", 34, 28, 58, 4, 3.0, 0.2), "timpani": ("sso", 40, 38, 57, 3, 3.0, 0.6), "glock": ("sso", 39, 72, 108, 4, 2.5, 0.6),
    "choir": ("sso", 35, 45, 84, 4, 4.0, 0.5), "kit_orch": ("gu", 48, 0, 0, 0, 0, 0.1, DRUMS),
}


def build(spec, out):
    res = {}
    for name, v in spec.items():
        if isinstance(v, str):
            res[name] = salamander(v[3:])
        elif len(v) == 8:
            res[name] = sfont(v[0], v[1], 0, 0, 0, 0, v[6], v[7])
        else:
            res[name] = sfont(v[0], v[1], v[2], v[3], v[4], v[5], v[6])
        print(f"  {name:11s} {len(res[name]['notes'])}음 {sum(len(d) for d in res[name]['data']) / 1e6:.2f}MB", flush=True)
    json.dump(res, open(out, "w"))
    print(out, f"{os.path.getsize(out) / 1e6:.1f}MB")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    which = sys.argv[1:] or ["jazz", "orch"]
    if "jazz" in which: build(JAZZ, f"{OUT}/samples_jazz.json")
    if "orch" in which: build(ORCH, f"{OUT}/samples_orch.json")
