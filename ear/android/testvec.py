# 앱 쪽 확인용 시험 벡터: 4초 소리 6개 + 우리 쪽(파이토치) 정답
#   python testvec.py <best.pt> <thresholds.json> <출력 폴더>
#   → test_vectors/*.wav (16kHz · 모노 · 16비트) · expected.json · expected.txt (자바 확인용 한 줄 꼴) · logmel_speech_ko.json
#   소리 출처는 전부 공유해도 되는 것: 우리 TTS 목소리 · 우리 엔진 음악 · 파도(CC0) · 비(퍼블릭 도메인) · 합성 잡음
import os, sys, json
import numpy as np, soundfile as sf, soxr, torch
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from model import Ear
from features import prosody, SR
from words import to_words
from labels import GROUP_IDS, EMOTIONS

N = 64000
pt, thp, out = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(f"{out}/test_vectors", exist_ok=True)
ck = torch.load(pt, map_location="cpu")
m = Ear(ck["width"], ck["blocks"]).eval(); m.load_state_dict(ck["model"])
th = json.load(open(thp))


def rd(p, off):
    x, sr = sf.read(p, dtype="float32", always_2d=True)
    x = x.mean(1)
    if sr != SR:
        x = soxr.resample(x, sr, SR)
    return x[int(off * SR): int(off * SR) + N]


rng = np.random.default_rng(7)
brown = np.cumsum(rng.standard_normal(N + 8000)).astype(np.float32)
brown = (brown - np.convolve(brown, np.ones(4000) / 4000, "same"))[4000:4000 + N]
SRC = [
    ("speech_ko", rd("/home/drboom/project/eng_youtube/ep03_grows/work/voice_ko.wav", 20)),
    ("speech_en", rd("/home/drboom/project/eng_youtube/ep03_grows/work/voice_en.wav", 30)),
    ("music_carbgm", rd("/home/drboom/project/car_bgm/dist/샘플/새분위기17/01_시티팝.mp3", 30)),
    ("sea_waves", rd("/home/drboom/project/car_bgm/win/build/assets/amb/sea.flac", 5)),
    ("rain", rd("/home/drboom/project/car_bgm/win/build/assets/amb/rain.flac", 5)),
    ("quiet_noise", (rng.standard_normal(N) * 3e-4).astype(np.float32)),
]
exp, lines = {}, []
for name, x in SRC:
    x = np.clip(x, -1, 1)
    q = np.round(x * 32767).astype(np.int16)                 # 파일에 쓰는 값 그대로 다시 읽어서 채점 (앱과 같은 입력)
    sf.write(f"{out}/test_vectors/{name}.wav", q, SR, subtype="PCM_16")
    xf = torch.from_numpy(q.astype(np.float32) / 32768.0)
    with torch.no_grad():
        lm = m.mel(xf[None])
        clip, emo, _ = m(lm)
    c = clip[0].tolist(); e = torch.softmax(emo[0], 0).tolist()
    pr = prosody(xf)
    w = to_words(c, th, e, pr)
    exp[name] = {"sounds": {g: round(v, 5) for g, v in zip(GROUP_IDS, c)}, "emotion": {k: round(v, 5) for k, v in zip(EMOTIONS, e)},
                 "prosody": {k: round(v, 4) for k, v in pr.items()}, "words": [[a, b, k] for a, b, k in w]}
    lines.append(f"name {name}")
    lines.append("sounds " + " ".join(f"{v:.7g}" for v in c))
    lines.append("emotion " + " ".join(f"{v:.7g}" for v in e))
    lines.append("prosody " + " ".join(f"{pr[k]:.7g}" for k in ("loud_db", "loud_var", "pitch_var", "rate", "voiced_ratio", "pitch_med")))
    lines.append("words " + " | ".join(f"{a}:{b}:{k}" for a, b, k in w))
    if name == "speech_ko":
        json.dump({"shape": [64, int(lm.shape[2])], "logmel": [[round(v, 5) for v in row] for row in lm[0].tolist()]},
                  open(f"{out}/logmel_speech_ko.json", "w"))
    print(name, " · ".join(f"{a}({b:.2f})" for a, b, _ in w) or "(단어 없음)")
json.dump(exp, open(f"{out}/expected.json", "w"), ensure_ascii=False, indent=1)
open(f"{out}/expected.txt", "w", encoding="utf-8").write("\n".join(lines) + "\n")
