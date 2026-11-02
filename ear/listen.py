# 소리 파일 → 단어.  python listen.py 파일.wav [파일2 ...]
import os, sys, json
import numpy as np, soundfile as sf, soxr, torch
sys.path.insert(0, os.path.dirname(__file__))
from model import Ear
from features import prosody, SR
from words import to_words

RUN = os.environ.get("EAR_RUN", "/home/drboom/project/car_bgm/runs/ear")


class Listener:
    def __init__(self, run=RUN, dev="cuda"):
        ck = torch.load(f"{run}/best.pt", map_location=dev)
        self.m = Ear(ck["width"], ck["blocks"]).to(dev).eval()
        self.m.load_state_dict(ck["model"])
        self.th = json.load(open(f"{run}/thresholds.json"))
        self.dev = dev

    @torch.no_grad()
    def __call__(self, x, sr=SR, win=4.0, hop=2.0):
        """x: 파형(넘파이). 여러 창으로 나눠 듣고 묶음은 최댓값, 감정은 말소리 많은 창 위주로 평균."""
        if x.ndim > 1:
            x = x.mean(1)
        if sr != SR:
            x = soxr.resample(x, sr, SR)
        x = torch.from_numpy(np.ascontiguousarray(x, dtype=np.float32)).to(self.dev)
        n, h = int(win * SR), int(hop * SR)
        if len(x) < n:
            x = torch.nn.functional.pad(x, (0, n - len(x)))
        fr = x.unfold(0, n, h)
        with torch.autocast(self.dev.split(":")[0], torch.bfloat16):
            clip, emo, _ = self.m(self.m.mel(fr))
        clip, emo = clip.float(), torch.softmax(emo.float(), 1)
        sp = clip[:, 0:1]
        e = (emo * sp).sum(0) / sp.sum().clamp(min=1e-6)
        c = clip.max(0).values
        pros = prosody(x)
        return {"words": to_words(c.tolist(), self.th, e.tolist(), pros),
                "clip": [round(v, 3) for v in c.tolist()], "emotion": [round(v, 3) for v in e.tolist()],
                "prosody": {k: round(v, 2) for k, v in pros.items()}}


if __name__ == "__main__":
    L = Listener(dev=os.environ.get("EAR_DEV", "cuda"))
    for p in sys.argv[1:]:
        x, sr = sf.read(p, dtype="float32")
        r = L(x, sr)
        print(os.path.basename(p), " · ".join(f"{w}({s:.2f})" for w, s, _ in r["words"]))
