# Salamander 피아노 샘플 → FLAC 16비트 (윈도우 묶음용). 14초까지 · 꼬리가 -80dB 아래로 내려가면 거기서 자르고 20ms 페이드.
#   조율 보정이 샘플레이트에 담겨 있어 원래 샘플레이트를 그대로 둠 (FLAC 은 47917Hz 같은 값도 됨)
import glob, os, sys
import numpy as np, soundfile as sf

src, dst = sys.argv[1], sys.argv[2]
os.makedirs(dst, exist_ok=True)
tot_in = tot_out = 0
for f in sorted(glob.glob(f"{src}/*.wav")):
    x, sr = sf.read(f, dtype="float32", frames=14 * 48000)
    pk = np.abs(x).max()
    loud = np.nonzero(np.abs(x).max(1) > pk * 10 ** (-80 / 20))[0]
    end = min(len(x), int(loud[-1] + .1 * sr) if len(loud) else len(x))
    x = x[:end].copy()
    fd = int(.02 * sr); x[-fd:] *= np.linspace(1, 0, fd)[:, None]
    out = os.path.join(dst, os.path.basename(f)[:-4] + ".flac")
    sf.write(out, x, sr, subtype="PCM_16")
    tot_in += os.path.getsize(f); tot_out += os.path.getsize(out)
print(f"→ {dst}: {tot_in / 1e6:.0f}MB → {tot_out / 1e6:.0f}MB")
