# 귀 모델 → 안드로이드용 ONNX 두 개 + 시험 벡터
#   ear_wave.onnx : 파형(16kHz · -1~1 · 4초 = 64000) 을 바로 받음 — 로그 멜까지 모델 안에서 (전처리 어긋날 일 없음)
#   ear_mel.onnx  : 로그 멜(64 x 401) 을 받음 — 앱에서 멜을 직접 계산할 때
#   python export_android.py <best.pt> <thresholds.json> <출력 폴더> [<채점 report.json>]
# 멜 계산(STFT)은 torch.stft 와 같은 값을 내는 conv1d 로 바꿔 넣음 (ONNX · TFLite 어디서나 도는 연산만)
import os, sys, json, math
import numpy as np, torch, torch.nn as nn, torch.nn.functional as F
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from model import Ear
from features import SR, N_FFT, WIN, HOP, N_MELS, FMIN, FMAX
from labels import GROUPS, GROUP_IDS, EMOTIONS, EMOTION_WORDS

SEC = 4.0
N = int(SEC * SR)                       # 64000
T = 1 + N // HOP                        # 401 (center=True)


class WaveFront(nn.Module):
    """torch.stft(n_fft 512 · win 400 hann(periodic, 가운데 놓음) · hop 160 · center · reflect) → 파워 → 멜 64 → log(+1e-6)
       틀 뽑기 = 정해 둔 번호표로 Gather (가장자리 거울 붙이기까지 번호표에 넣음) · DFT = 행렬곱 → ONNX · TFLite 어디서나"""
    def __init__(self, fb):
        super().__init__()
        w = torch.zeros(N_FFT, dtype=torch.float64)
        lp = (N_FFT - WIN) // 2
        w[lp:lp + WIN] = torch.hann_window(WIN, periodic=True, dtype=torch.float64)
        k = torch.arange(N_FFT, dtype=torch.float64)
        f = torch.arange(N_FFT // 2 + 1, dtype=torch.float64)
        ang = 2 * math.pi * k[:, None] * f[None] / N_FFT                  # (512, 257)
        self.register_buffer("kr", (torch.cos(ang) * w[:, None]).float())
        self.register_buffer("ki", (-torch.sin(ang) * w[:, None]).float())
        self.register_buffer("fb", fb.float())                          # (257, 64)
        pos = torch.arange(T)[:, None] * HOP + torch.arange(N_FFT)[None] - N_FFT // 2   # (401, 512) 원 신호 자리
        pos = torch.where(pos < 0, -pos, pos)
        pos = torch.where(pos > N - 1, 2 * (N - 1) - pos, pos)            # 거울 (reflect)
        self.register_buffer("idx", pos.reshape(-1).long())

    def forward(self, wav):                                             # (B, N)
        fr = torch.index_select(wav, 1, self.idx).reshape(-1, T, N_FFT)  # (B, 401, 512)
        re = torch.matmul(fr, self.kr)
        im = torch.matmul(fr, self.ki)                                  # (B, 401, 257)
        mel = torch.matmul(re * re + im * im, self.fb)                  # (B, 401, 64)
        return torch.log(mel + 1e-6).transpose(1, 2)                    # (B, 64, 401)


class EarMel(nn.Module):
    def __init__(self, ear):
        super().__init__()
        self.ear = ear

    def forward(self, logmel):
        clip, emo, _ = self.ear(logmel)
        return clip, torch.softmax(emo, dim=1)


class EarWave(nn.Module):
    def __init__(self, ear):
        super().__init__()
        self.front = WaveFront(ear.mel.fb)
        self.ear = ear

    def forward(self, wav):
        clip, emo, _ = self.ear(self.front(wav))
        return clip, torch.softmax(emo, dim=1)


def load(pt):
    ck = torch.load(pt, map_location="cpu")
    m = Ear(ck["width"], ck["blocks"]).eval()
    m.load_state_dict(ck["model"])
    return m, ck


def export(mod, x, path, in_name):
    torch.onnx.export(mod, (x,), path, input_names=[in_name], output_names=["sounds", "emotion"],
                      dynamic_axes={in_name: {0: "batch"}, "sounds": {0: "batch"}, "emotion": {0: "batch"}},
                      opset_version=17, dynamo=False)


if __name__ == "__main__":
    pt, thp, out = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(out, exist_ok=True)
    ear, ck = load(pt)
    wave, melm = EarWave(ear).eval(), EarMel(ear).eval()
    # 1) conv 멜 == torch.stft 멜 확인
    g = torch.Generator().manual_seed(0)
    xs = torch.randn(3, N, generator=g) * torch.tensor([[.3], [.03], [.003]])
    with torch.no_grad():
        a, b = ear.mel(xs), wave.front(xs)
        ca, ea = melm(a); cb, eb = wave(xs)
    print(f"멜 차 (log) 최대 {float((a - b).abs().max()):.2e} · 소리 확률 차 최대 {float((ca - cb).abs().max()):.2e} · 감정 차 {float((ea - eb).abs().max()):.2e}")
    # 2) ONNX 로
    export(wave, torch.zeros(1, N), f"{out}/ear_wave.onnx", "wav")
    export(melm, torch.zeros(1, N_MELS, T), f"{out}/ear_mel.onnx", "logmel")
    # 3) onnxruntime 으로 같은지
    import onnxruntime as ort
    for name, inp, ref in (("ear_wave.onnx", xs.numpy(), (cb, eb)), ("ear_mel.onnx", a.numpy(), (ca, ea))):
        s = ort.InferenceSession(f"{out}/{name}", providers=["CPUExecutionProvider"])
        o = s.run(None, {s.get_inputs()[0].name: inp})
        print(f"{name}: {os.path.getsize(f'{out}/{name}') / 1e6:.1f}MB · 파이토치와 차 소리 {np.abs(o[0] - ref[0].numpy()).max():.2e} · 감정 {np.abs(o[1] - ref[1].numpy()).max():.2e}")
    # 4) 라벨 · 문턱
    th = json.load(open(thp))
    rep = json.load(open(sys.argv[4])) if len(sys.argv) > 4 else {}
    ap = rep.get("시험(앱 방식)", {}).get("AP", {}); pr = rep.get("문턱에서 정밀도·재현율(시험)", {})
    def quality(gid):                                                   # 시험(FSD50K 시험 · 4초 창) 점수로 믿을 만한 정도
        if gid not in ap:
            return {}
        a = ap[gid]
        return {"test_ap": a, "precision": pr.get(gid, {}).get("정밀도"), "recall": pr.get(gid, {}).get("재현율"),
                "reliability": "good" if a >= .4 else "ok" if a >= .2 else "weak"}
    labels = {"sounds": [{"index": i, "id": gid, "words": words, "threshold": round(th.get(gid, .5), 3), **quality(gid)}
                         for i, (gid, _, words) in enumerate(GROUPS)],
              "emotion": [{"index": i, "id": e, "words": EMOTION_WORDS[e]} for i, e in enumerate(EMOTIONS)],
              "input": {"sample_rate": SR, "seconds": SEC, "samples": N, "range": "-1..1 float32 (int16 / 32768)", "mono": True},
              "model": {"checkpoint": os.path.basename(os.path.dirname(pt)) + "/" + os.path.basename(pt), "step": ck.get("step"),
                        "test_mAP": rep.get("시험(앱 방식)", {}).get("mAP"), "test_emotion_acc": rep.get("시험(앱 방식)", {}).get("감정"),
                        "test_mAP_car_noise_10dB": rep.get("시험+차소음10dB", {}).get("mAP")}}
    json.dump(labels, open(f"{out}/labels.json", "w"), ensure_ascii=False, indent=1)
    json.dump({k: round(v, 3) for k, v in th.items()}, open(f"{out}/thresholds.json", "w"), ensure_ascii=False, indent=1)
    print("→", out)
