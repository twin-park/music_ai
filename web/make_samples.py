# 브라우저 악기 소리 만들기: MuseScore_General.sf2(MIT)에서 악기별로 몇 음씩 떠서 opus 로 압축.
# 결과 web/build/samples.json  {악기: {"notes": [...], "data": [base64 ...], "release": 초}}
import os, sys, json, base64, subprocess, tempfile
import numpy as np, soundfile as sf, mido

ROOT = "/home/drboom/project/car_bgm"
TOOLS = "/home/drboom/miniconda3/envs/car_bgm_tools/bin"
SF2 = f"{ROOT}/data/sf/MuseScore_General.sf2"
OUT = f"{ROOT}/web/build"

# 이름: (GM 악기 번호, 낮은 음, 높은 음, 간격, 길이(초), 떼는 시간(초))
INSTS = {
    "piano":   (0, 21, 108, 3, 3.5, 0.25),
    "vibes":   (11, 48, 96, 4, 3.0, 0.4),
    "organ":   (19, 36, 96, 4, 3.0, 0.15),
    "guitar":  (24, 40, 84, 4, 2.5, 0.25),
    "bass":    (33, 28, 64, 3, 2.5, 0.15),
    "strings": (48, 36, 96, 4, 4.0, 0.4),
    "harp":    (46, 36, 96, 4, 3.0, 0.5),
    "brass":   (61, 40, 84, 4, 3.0, 0.2),
    "reed":    (71, 50, 90, 4, 3.0, 0.2),
    "flute":   (73, 60, 96, 4, 3.0, 0.2),
    "pad":     (89, 36, 84, 4, 4.0, 0.6),
}
DRUMS = [35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 59, 69, 70, 75]


def render(prog, note, dur, drum=False):
    with tempfile.TemporaryDirectory() as td:
        mid = mido.MidiFile(ticks_per_beat=480); tr = mido.MidiTrack(); mid.tracks.append(tr)
        tr.append(mido.MetaMessage("set_tempo", tempo=500000, time=0))     # 120bpm: 1박=0.5초=480틱
        ch = 9 if drum else 0
        if not drum:
            tr.append(mido.Message("program_change", channel=ch, program=prog, time=0))
        hold = int((dur - 0.6 if not drum else 0.3) * 960)
        tr.append(mido.Message("note_on", channel=ch, note=note, velocity=100, time=10))
        tr.append(mido.Message("note_off", channel=ch, note=note, velocity=0, time=hold))
        tr.append(mido.MetaMessage("end_of_track", time=int(0.8 * 960)))
        mid.save(f"{td}/a.mid")
        subprocess.run([f"{TOOLS}/fluidsynth", "-ni", "-R", "0", "-C", "0", "-g", "0.8", "-r", "48000",
                        "-F", f"{td}/a.wav", SF2, f"{td}/a.mid"], check=True, capture_output=True)
        x, sr = sf.read(f"{td}/a.wav")
        x = x.mean(1)
        a = np.abs(x)
        start = int(np.argmax(a > 1e-3)) if (a > 1e-3).any() else 0
        x = x[max(0, start - 48):][: int(dur * sr)]
        fade = min(len(x), int(0.05 * sr))
        x[-fade:] *= np.linspace(1, 0, fade)
        peak = np.abs(x).max() + 1e-9
        sf.write(f"{td}/b.wav", (x / peak * 0.9).astype(np.float32), sr)
        subprocess.run([f"{TOOLS}/ffmpeg", "-y", "-loglevel", "error", "-i", f"{td}/b.wav", "-c:a", "libopus",
                        "-b:a", "40k", "-ac", "1", f"{td}/c.ogg"], check=True)
        return base64.b64encode(open(f"{td}/c.ogg", "rb").read()).decode(), float(peak)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    out, total = {}, 0
    for name, (prog, lo, hi, step, dur, rel) in INSTS.items():
        notes = list(range(lo, hi + 1, step))
        data, peaks = zip(*[render(prog, n, dur) for n in notes])
        out[name] = {"notes": notes, "data": list(data), "release": rel, "gain": [round(p, 4) for p in peaks]}
        sz = sum(len(d) for d in data); total += sz
        print(f"{name:8s} {len(notes)}음 {sz / 1e6:.2f}MB", flush=True)
    data, peaks = zip(*[render(0, n, 1.5 if n not in (49, 52, 55, 57) else 2.5, drum=True) for n in DRUMS])
    out["drums"] = {"notes": DRUMS, "data": list(data), "release": 0.1, "gain": [round(p, 4) for p in peaks]}
    total += sum(len(d) for d in data)
    json.dump(out, open(f"{OUT}/samples.json", "w"))
    print(f"합계 {total / 1e6:.2f}MB (base64)")
