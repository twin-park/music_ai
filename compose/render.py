# 소리 만들기: 실제 녹음 피아노(Salamander) · 사운드폰트(fluidsynth) · 믹서(팬·리버브·압축·리미터)
import os, re, glob, subprocess, tempfile, math
import numpy as np, soundfile as sf, mido
from scipy.signal import fftconvolve, butter, sosfilt

SR = 48000
# 경로는 환경 변수로 바꿀 수 있음 (윈도우 묶음: score/app/server.py 가 넣어 줌)
ROOT = os.environ.get("CAR_BGM_ROOT", "/home/drboom/project/car_bgm")
TOOLS = os.environ.get("CAR_BGM_TOOLS", "/home/drboom/miniconda3/envs/car_bgm_tools/bin")
SF = {"sso": os.environ.get("CAR_BGM_SF_SSO", f"{ROOT}/data/sf/Sonatina_Symphonic_Orchestra.sf2"),
      "gu": os.environ.get("CAR_BGM_SF_GU", f"{ROOT}/data/sf/GeneralUser-GS.sf2"),
      "msg": f"{ROOT}/data/sf/MuseScore_General.sf2"}
PIANO = os.environ.get("CAR_BGM_PIANO", f"{ROOT}/data/salamander")
FLUID = os.path.join(TOOLS, "fluidsynth.exe" if os.name == "nt" else "fluidsynth")
NOWIN = {"creationflags": 0x08000000} if os.name == "nt" else {}       # 윈도우: 검은 창 안 띄우기


def run_fluid(font, mid, wav, gain=0.7):
    subprocess.run([FLUID, "-ni", "-R", "0", "-C", "0", "-g", str(gain), "-r", str(SR), "-F", wav, font, mid],
                   check=True, capture_output=True, **NOWIN)


# ---------- 박 → 초 (템포 흔들림 포함) ----------
class TimeMap:
    def __init__(self, sc):
        pts = getattr(sc, "tempo_pts", None) or [(0, sc.bpm)]
        end = max([n[0] + n[1] for n in sc.notes] + [0]) + 16
        self.res = 96
        b = np.arange(0, end * self.res + 1) / self.res
        bpm = np.interp(b, [p[0] for p in pts], [p[1] for p in pts])
        self.bpm = bpm
        self.t = np.concatenate([[0], np.cumsum(60 / bpm[:-1] / self.res)])

    def __call__(self, beat):
        return np.interp(beat, np.arange(len(self.t)) / self.res, self.t)


# ---------- 실제 녹음 피아노 ----------
class Salamander:
    LAYERS = [("04", 40), ("08", 70), ("12", 96), ("15", 120)]

    def __init__(self, path=PIANO, max_sec=14):
        self.files, self.cache, self.max_sec = {}, {}, max_sec
        for f in glob.glob(f"{path}/*.wav") + glob.glob(f"{path}/*.flac"):
            m = re.match(r"(\d{3})_.*v(\d{2})\.(wav|flac)", os.path.basename(f))
            if m:
                self.files[(int(m.group(1)), m.group(2))] = f
        self.notes = sorted({k[0] for k in self.files})
        self.s = self                                                        # self.s[(음, 층)] → 처음 쓸 때 읽음

    def __getitem__(self, key):
        if key not in self.cache:
            x, sr = sf.read(self.files[key], dtype="float32", frames=self.max_sec * SR)
            # Accurate-Salamander 는 조율 보정을 샘플레이트로 담아 둠 → 재생 속도에 sr/SR 을 곱함
            self.cache[key] = (x if x.ndim == 2 else np.stack([x, x], 1), sr / SR)
        return self.cache[key]

    def render(self, notes, tm, length):
        """notes: [(시작초, 끝초, 음높이, 세기)] (끝초 = 페달까지 반영) → (N,2)"""
        out = np.zeros((length, 2), np.float32)
        for t0, t1, p, v in notes:
            n = min(self.notes, key=lambda q: abs(q - p))
            ratio = 2 ** ((p - n) / 12)
            # 세기층 두 개 섞기
            lv = [l for l in self.LAYERS]
            w = []
            for (a, va), (b, vb) in zip(lv, lv[1:]):
                if va <= v <= vb:
                    f = (v - va) / (vb - va); w = [(a, 1 - f), (b, f)]; break
            if not w:
                w = [(lv[0][0], v / lv[0][1])] if v < lv[0][1] else [(lv[-1][0], 1.0)]
            rel = 0.25 + max(0, (60 - p)) * 0.012                         # 낮은 음일수록 길게 울림
            dur = max(0.05, t1 - t0) + rel * 4
            nout = int(dur * SR)
            i0 = int(t0 * SR)
            if i0 >= length:
                continue
            seg = np.zeros((nout, 2), np.float32)
            for layer, wt in w:
                x, srr = self.s[(n, layer)]
                pos = np.arange(nout) * ratio * srr
                m = pos < len(x) - 1
                ip = pos[m].astype(np.int64); fr = (pos[m] - ip)[:, None].astype(np.float32)
                seg[m] += wt * (x[ip] * (1 - fr) + x[ip + 1] * fr)
            k1 = int((t1 - t0) * SR)
            if k1 < nout:                                                    # 손 떼면(페달 떼면) 줄 멈춤
                env = np.ones(nout, np.float32)
                env[k1:] = np.exp(-np.arange(nout - k1) / (rel * SR))
                seg *= env[:, None]
            e = min(length, i0 + nout)
            out[i0:e] += seg[: e - i0]
        return out


# ---------- 사운드폰트 ----------
def fluid_render(notes, ccs, pedals, tm, length, font, bank, prog, drum=False, gain=0.7):
    """notes: [(시작박, 길이박, 음, 세기)] → (N,2). MIDI 는 박 단위, 템포는 TimeMap 대로 바꿔 넣음."""
    tpb = 480
    mid = mido.MidiFile(ticks_per_beat=tpb)
    tr = mido.MidiTrack(); mid.tracks.append(tr)
    ch = 9 if drum else 0
    ev = []
    last_b = int(max([n[0] + n[1] for n in notes] + [0]) * 4 + 16)
    for q in range(last_b):                                                    # 템포 (4분의 1박마다)
        bpm = float(np.interp(q / 4, np.arange(len(tm.bpm)) / tm.res, tm.bpm))
        ev.append((q * tpb // 4, 0, mido.MetaMessage("set_tempo", tempo=int(6e7 / bpm))))
    if not drum:
        ev.append((0, 1, mido.Message("control_change", channel=ch, control=0, value=bank)))
    ev.append((0, 2, mido.Message("program_change", channel=ch, program=prog)))
    ev.append((0, 3, mido.Message("control_change", channel=ch, control=7, value=110)))
    for t, d, p, v in notes:
        a, b = int(t * tpb), int((t + d) * tpb)
        ev.append((max(0, a), 5, mido.Message("note_on", channel=ch, note=p, velocity=v)))
        ev.append((max(0, b), 4, mido.Message("note_off", channel=ch, note=p, velocity=0)))
    for t, num, val in ccs:
        ev.append((int(t * tpb), 3, mido.Message("control_change", channel=ch, control=num, value=val)))
    for a, b in pedals:
        ev.append((int(a * tpb), 3, mido.Message("control_change", channel=ch, control=64, value=127)))
        ev.append((int(b * tpb), 3, mido.Message("control_change", channel=ch, control=64, value=0)))
    ev.sort(key=lambda e: (e[0], e[1]))
    now = 0
    for tk, _, m in ev:
        tr.append(m.copy(time=tk - now)); now = tk
    with tempfile.TemporaryDirectory() as td:
        mid.save(f"{td}/a.mid")
        run_fluid(font, f"{td}/a.mid", f"{td}/a.wav", gain)
        x, sr = sf.read(f"{td}/a.wav", dtype="float32")
    out = np.zeros((length, 2), np.float32)
    n = min(length, len(x)); out[:n] = x[:n]
    return out


# ---------- 믹서 ----------
def filt(x, kind, f, order=2):
    sos = butter(order, f, btype=kind, fs=SR, output="sos")
    return sosfilt(sos, x, axis=0).astype(np.float32)


def make_ir(sec=2.6, pre=0.02, damp=6000, seed=0):
    rng = np.random.default_rng(seed)
    n = int(sec * SR)
    t = np.arange(n) / SR
    ir = rng.standard_normal((n, 2)).astype(np.float32) * np.exp(-6.9 * t / sec)[:, None]
    lo = filt(ir, "low", 2500)
    mixw = np.clip(t / sec * 1.5, 0, 1)[:, None]                              # 꼬리일수록 고음 빠짐
    ir = ir * (1 - mixw) + lo * mixw
    ir = np.concatenate([np.zeros((int(pre * SR), 2), np.float32), ir])
    return ir / np.sqrt((ir ** 2).sum(0, keepdims=True))


def pan(x, p):
    l, r = math.cos((p + 1) * math.pi / 4), math.sin((p + 1) * math.pi / 4)
    return np.stack([x[:, 0] * l * 1.414, x[:, 1] * r * 1.414], 1)


def compress(x, thr_db=-18, ratio=2.5, att=0.01, rel=0.25):
    env = np.sqrt(np.convolve((x ** 2).mean(1), np.ones(int(0.03 * SR)) / int(0.03 * SR), "same")) + 1e-9
    db = 20 * np.log10(env)
    gr = np.minimum(0, (thr_db - db) * (1 - 1 / ratio))
    # 빨리 줄이고 천천히 풀기
    a, r = math.exp(-1 / (att * SR)), math.exp(-1 / (rel * SR))
    from scipy.signal import lfilter
    sm = lfilter([1 - r], [1, -r], gr)
    sm = np.minimum(sm, lfilter([1 - a], [1, -a], gr))
    return x * (10 ** (sm / 20))[:, None]


def limit(x, ceil_db=-1.0):
    """미리 보고 줄이는 리미터 (3ms)"""
    from scipy.ndimage import maximum_filter1d, uniform_filter1d
    c, look = 10 ** (ceil_db / 20), int(0.003 * SR)
    pk = maximum_filter1d(np.abs(x).max(1), 2 * look + 1)
    g = uniform_filter1d(np.minimum(1, c / (pk + 1e-9)), look)
    g = np.minimum(g, c / (np.abs(x).max(1) + 1e-9))
    return x * g[:, None]


def master(tracks, length, reverb_sec=2.4, target_rms_db=-17):
    """tracks: [(소리(N,2), 크기dB, 팬, 리버브 보내기, 저역컷Hz)] → 최종 (N,2)"""
    dry = np.zeros((length, 2), np.float32); send = np.zeros((length, 2), np.float32)
    for x, db, p, rv, hp in tracks:
        y = x * 10 ** (db / 20)
        if hp: y = filt(y, "high", hp)
        y = pan(y, p)
        dry += y; send += y * rv
    if reverb_sec:
        wet = fftconvolve(send, make_ir(reverb_sec), axes=0)[:length].astype(np.float32)
        dry = dry + wet * 0.9
    y = compress(dry)
    rms = np.sqrt((y[np.abs(y).max(1) > 1e-4] ** 2).mean() + 1e-12)
    y *= 10 ** (target_rms_db / 20) / rms
    y = limit(y)
    fade = int(1.5 * SR); y[-fade:] *= np.linspace(1, 0, fade)[:, None]
    return y


def write(y, path):
    sf.write(path, y, SR, subtype="PCM_24")
    subprocess.run([f"{TOOLS}/ffmpeg", "-y", "-loglevel", "error", "-i", path, "-b:a", "256k", path[:-4] + ".mp3"], check=True)
