# 소리 특징 계산 (신경망 아님). 로그 멜 + 말투 숫자(크기·높낮이·빠르기·밝기).
import math
import torch
import torch.nn.functional as F

SR = 16000
N_FFT, WIN, HOP, N_MELS = 512, 400, 160, 64
FMIN, FMAX = 50.0, 8000.0


def _hz2mel(f):
    return 2595.0 * math.log10(1.0 + f / 700.0)


def mel_fb(device="cpu"):
    """HTK 멜 필터 (n_fft//2+1, n_mels)."""
    m = torch.linspace(_hz2mel(FMIN), _hz2mel(FMAX), N_MELS + 2)
    hz = 700.0 * (10 ** (m / 2595.0) - 1.0)
    bins = torch.linspace(0, SR / 2, N_FFT // 2 + 1)
    fb = torch.zeros(N_FFT // 2 + 1, N_MELS)
    for i in range(N_MELS):
        lo, c, hi = hz[i], hz[i + 1], hz[i + 2]
        up = (bins - lo) / (c - lo)
        down = (hi - bins) / (hi - c)
        fb[:, i] = torch.clamp(torch.minimum(up, down), min=0)
    return fb.to(device)


class LogMel(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.register_buffer("fb", mel_fb())
        self.register_buffer("win", torch.hann_window(WIN))

    def power(self, x):
        """x (B, N) float 파형 → 멜 파워 (B, n_mels, T)"""
        s = torch.stft(x, N_FFT, HOP, WIN, self.win, center=True, return_complex=True)
        p = s.real ** 2 + s.imag ** 2
        return torch.einsum("bft,fm->bmt", p, self.fb)

    def forward(self, x):
        return torch.log(self.power(x) + 1e-6)


@torch.no_grad()
def prosody(x, sr=SR):
    """파형 1개 (N,) → 말투 숫자. 값은 마이크마다 달라 대략적인 기준으로만 쓴다."""
    x = x.float()
    fl, hop = 640, 160                                   # 40ms 창, 10ms 간격
    fr = x.unfold(0, fl, hop)                            # (T, fl)
    rms = fr.pow(2).mean(1).sqrt() + 1e-8
    db = 20 * torch.log10(rms)
    loud = db.max().item()
    active = db > (loud - 25)                            # 가장 큰 소리 기준 25dB 안쪽 = 소리 나는 구간
    # 높낮이: 정규화 자기상관 (60~500Hz)
    w = fr - fr.mean(1, keepdim=True)
    spec = torch.fft.rfft(w, n=2 * fl)
    ac = torch.fft.irfft(spec.abs() ** 2)[:, :fl]
    ac = ac / (ac[:, :1] + 1e-8)
    lo, hi = sr // 500, sr // 60
    peak, lag = ac[:, lo:hi].max(1)
    voiced = (peak > 0.5) & active
    f0 = sr / (lag + lo).float()
    semis = 12 * torch.log2(f0[voiced] / 100.0) if voiced.any() else torch.zeros(1)
    # 빠르기: 90ms 로 편 크기 곡선(dB)에서 앞뒤 100ms 안 최댓값이면서 주변 골보다 3dB 이상 솟은 봉우리 = 음절
    env = F.avg_pool1d(db[None, None], 9, 1, 4, count_include_pad=False)[0, 0]
    mx = F.max_pool1d(env[None, None], 21, 1, 10)[0, 0]
    mn = -F.max_pool1d(-env[None, None], 31, 1, 15)[0, 0]
    pk = (env == mx) & (env - mn >= 3) & (env > loud - 25)
    act_sec = active.float().sum().item() * hop / sr
    rate = pk.float().sum().item() / max(act_sec, 0.5)
    # 밝기: 스펙트럼 무게중심
    mag = torch.fft.rfft(fr * torch.hann_window(fl, device=x.device), dim=1).abs()
    freqs = torch.linspace(0, sr / 2, mag.shape[1], device=x.device)
    cent = ((mag * freqs).sum(1) / (mag.sum(1) + 1e-8))[active]
    return {
        "loud_db": loud,                                         # 가장 큰 구간 dBFS
        "loud_var": db[active].std().item() if active.sum() > 1 else 0.0,
        "voiced_ratio": voiced.float().mean().item(),
        "pitch_med": float(100 * 2 ** (semis.median().item() / 12)) if voiced.any() else 0.0,
        "pitch_var": semis.std().item() if voiced.sum() > 2 else 0.0,   # 반음 단위 흔들림
        "rate": rate,                                            # 초당 봉우리 수
        "bright": cent.mean().item() if active.any() else 0.0,
    }
