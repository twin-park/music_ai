# 귀 모델 학습. 자르기는 CPU 한 줄, 멜 계산·섞기(차 소음·다른 소리)·가리기는 GPU.
import os, sys, time, math, json, argparse, threading, queue, copy
import numpy as np, torch, torch.nn.functional as F
sys.path.insert(0, os.path.dirname(__file__))
from model import Ear
from labels import GROUP_IDS, N_GROUPS, EMOTIONS
from sklearn.metrics import average_precision_score

D = "/home/drboom/project/car_bgm/data/ear"
SR = 16000
G = {g: i for i, g in enumerate(GROUP_IDS)}

ap = argparse.ArgumentParser()
ap.add_argument("--width", type=int, default=64)
ap.add_argument("--blocks", type=int, default=4)
ap.add_argument("--sec", type=float, default=4.0)
ap.add_argument("--bs", type=int, default=128)
ap.add_argument("--steps", type=int, default=15000)
ap.add_argument("--lr", type=float, default=1e-3)
ap.add_argument("--crema", type=float, default=0.2, help="한 묶음에서 감정 음성 비율")
ap.add_argument("--out", default="/home/drboom/project/car_bgm/runs/ear")
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--dev", default="cuda")
ap.add_argument("--init", default="", help="이어 학습할 best.pt")
ap.add_argument("--warmup", type=int, default=500)
ap.add_argument("--eval_max", type=int, default=0, help="시험용: 채점 클립 수 제한")
A = ap.parse_args()
os.makedirs(A.out, exist_ok=True)
torch.manual_seed(A.seed); torch.set_num_threads(4)
rng = np.random.default_rng(A.seed)
dev = A.dev

ix = np.load(f"{D}/index.npz")
OFF, LEN, Y, EMO, SPLIT, SRC = ix["offset"], ix["length"], ix["y"].astype(np.float32), ix["emo"], ix["split"], ix["src"]
WAV = np.memmap(f"{D}/wav.i16", dtype=np.int16, mode="r")
N = int(A.sec * SR)

vocal = [G[k] for k in ("speech", "child", "baby_cry", "crying", "laughter", "shout", "whisper", "singing")]
tr_fsd = np.where((SPLIT == 0) & (SRC != 1))[0]   # FSD + 아기울음 보강
tr_cre = np.where((SPLIT == 0) & (SRC == 1))[0]
nonvocal = tr_fsd[Y[tr_fsd][:, vocal].sum(1) == 0]
noise_bank = tr_fsd[(Y[tr_fsd, G["traffic"]] == 1) & (Y[tr_fsd][:, vocal + [G["music"]]].sum(1) == 0)]
# 드문 묶음이 자주 나오게: 양성 묶음 중 가장 드문 것의 1/sqrt(빈도)
freq = Y[tr_fsd].sum(0) + 1
w = np.where(Y[tr_fsd].sum(1) > 0, (Y[tr_fsd] / np.sqrt(freq)).max(1), np.median(1 / np.sqrt(freq)))
w = w / w.sum()
print(f"학습 FSD {len(tr_fsd)} · CREMA {len(tr_cre)} · 소음 {len(noise_bank)} · 비음성 {len(nonvocal)}", flush=True)


def crop(i, n, rnd=True):
    o, L = OFF[i], LEN[i]
    out = np.zeros(n, np.float32)
    if L >= n:
        s = rng.integers(0, L - n + 1) if rnd else (L - n) // 2
        out[:] = WAV[o + s:o + s + n]
    else:
        s = rng.integers(0, n - L + 1) if rnd else 0
        out[s:s + L] = WAV[o:o + L]
    return out / 32768.0


def make_batch():
    nc = int(A.bs * A.crema)
    idx = np.concatenate([rng.choice(tr_fsd, A.bs - nc, p=w), rng.choice(tr_cre, nc)])
    part = np.where(SRC[idx] == 1, rng.choice(nonvocal, A.bs), rng.choice(tr_fsd, A.bs, p=w))
    nz = rng.choice(noise_bank, A.bs)
    x = np.stack([crop(i, N) for i in idx]); x2 = np.stack([crop(i, N) for i in part]); n = np.stack([crop(i, N) for i in nz])
    return [torch.from_numpy(a) for a in (x, Y[idx], EMO[idx].astype(np.int64), SRC[idx].astype(np.int64), x2, Y[part], n)]


# 파형 전체를 GPU 에 올려 두고 거기서 바로 자른다 (CPU 거의 안 씀)
if dev.startswith("cuda"):
    # 통합 메모리라 한 번에 읽으면 RAM 사본+파일 캐시로 순간 부족 → 256MB 씩 올리고 그 구간 캐시는 바로 비움
    WAVG = torch.empty(len(WAV), dtype=torch.int16, device=dev)
    _fd, _st = os.open(f"{D}/wav.i16", os.O_RDONLY), 1 << 27
    for _s in range(0, len(WAV), _st):
        WAVG[_s:_s + _st] = torch.from_numpy(np.array(WAV[_s:_s + _st]))
        os.posix_fadvise(_fd, _s * 2, _st * 2, os.POSIX_FADV_DONTNEED)
    os.close(_fd)
    OFFG, LENG = torch.from_numpy(OFF).to(dev), torch.from_numpy(LEN).to(dev)
    YG, EMOG, SRCG = torch.from_numpy(Y).to(dev), torch.from_numpy(EMO.astype(np.int64)).to(dev), torch.from_numpy(SRC.astype(np.int64)).to(dev)
    AR = torch.arange(N, device=dev)


def gcrop(ix):
    ix = torch.as_tensor(ix, device=dev)
    o, L = OFFG[ix], LENG[ix]
    long_ = L >= N
    r = torch.rand(len(ix), device=dev)
    base = torch.where(long_, o + (r * (L - N + 1).clamp(min=1)).long(), o)
    shift = torch.where(long_, 0, (r * (N - L + 1).clamp(min=1)).long())
    ln = torch.where(long_, N, L)
    rel = AR[None] - shift[:, None]
    ok = (rel >= 0) & (rel < ln[:, None])
    src = base[:, None] + rel.clamp(min=0).minimum(ln[:, None] - 1)
    return torch.where(ok, WAVG[src].float() / 32768.0, 0.0)


def make_batch_gpu():
    nc = int(A.bs * A.crema)
    idx = np.concatenate([rng.choice(tr_fsd, A.bs - nc, p=w), rng.choice(tr_cre, nc)])
    part = np.where(SRC[idx] == 1, rng.choice(nonvocal, A.bs), rng.choice(tr_fsd, A.bs, p=w))
    nz = rng.choice(noise_bank, A.bs)
    return gcrop(idx), YG[idx], EMOG[idx], SRCG[idx], gcrop(part), YG[part], gcrop(nz)


if not dev.startswith("cuda"):
    q = queue.Queue(maxsize=6)
    def feeder():
        while True:
            q.put(make_batch())
    threading.Thread(target=feeder, daemon=True).start()


def rms(x):
    return x.pow(2).mean(-1, keepdim=True).sqrt() + 1e-5


def augment(model, x, y, emo, src, x2, y2, nz):
    B = x.shape[0]
    u = lambda lo, hi: torch.empty(B, 1, device=dev).uniform_(lo, hi)
    # 다른 소리 섞기: 감정 음성은 비음성 소리만 뒤에 작게, FSD 끼리는 비슷한 크기로
    mix = (torch.rand(B, 1, device=dev) < torch.where(src[:, None] == 1, 0.5, 0.3))
    snr = torch.where(src[:, None] == 1, u(5, 25), u(-5, 10))
    x2s = x2 * rms(x) / rms(x2) * 10 ** (-snr / 20)
    x = torch.where(mix, x + x2s, x)
    y = torch.where(mix, torch.maximum(y, y2), y)
    # 차 소음 깔기
    car = torch.rand(B, 1, device=dev) < 0.5
    nzs = nz * rms(x) / rms(nz) * 10 ** (-u(0, 20) / 20)
    x = torch.where(car, x + nzs, x)
    y[:, G["traffic"]] = torch.where(car[:, 0], 1.0, y[:, G["traffic"]])
    x = x * 10 ** (u(-10, 10) / 20)
    p = model.mel.power(x)
    # 차 안에서 들리는 바깥 소리처럼 고음 깎기
    lp = torch.rand(B, device=dev) < 0.3
    cut = torch.randint(20, 56, (B, 1), device=dev)
    k = torch.arange(p.shape[1], device=dev)[None]
    att = torch.where((k > cut) & lp[:, None], 10 ** (-(k - cut).clamp(0, 12) / 12 * u(6, 20) / 10), 1.0)
    lm = torch.log(p * att[..., None] + 1e-6)
    # 가리기 (SpecAugment)
    T, M = lm.shape[2], lm.shape[1]
    fill = lm.mean((1, 2), keepdim=True)
    for _ in range(2):
        t0 = torch.randint(0, T, (B, 1, 1), device=dev); tw = torch.randint(0, 40, (B, 1, 1), device=dev)
        tt = torch.arange(T, device=dev)[None, None]
        lm = torch.where((tt >= t0) & (tt < t0 + tw), fill, lm)
        f0 = torch.randint(0, M, (B, 1, 1), device=dev); fw = torch.randint(0, 8, (B, 1, 1), device=dev)
        ff = torch.arange(M, device=dev)[None, :, None]
        lm = torch.where((ff >= f0) & (ff < f0 + fw), fill, lm)
    return lm, y, emo


@torch.no_grad()
def evaluate(model, split, noisy=False, sec=10.0):
    model.eval()
    ids = np.where(SPLIT == split)[0]
    if A.eval_max:
        ids = np.random.default_rng(0).choice(ids, min(A.eval_max, len(ids)), replace=False)
    n = int(sec * SR)
    erng = np.random.default_rng(123)
    nb = np.where((SPLIT == 1) & (SRC == 0) & (Y[:, G["traffic"]] == 1) & (Y[:, vocal].sum(1) == 0))[0]
    P, E = [], []
    for k in range(0, len(ids), 64):
        b = ids[k:k + 64]
        x = torch.from_numpy(np.stack([crop(i, n, rnd=False) for i in b])).to(dev)
        if noisy:   # 차 소음 SNR 10dB
            nz = torch.from_numpy(np.stack([crop(i, n, rnd=False) for i in erng.choice(nb, len(b))])).to(dev)
            x = x + nz * rms(x) / rms(nz) * 10 ** (-10 / 20)
        with torch.autocast(dev.split(":")[0], torch.bfloat16):
            clip, emo, _ = model(model.mel(x))
        P.append(clip.float().cpu()); E.append(emo.float().argmax(1).cpu())
    P = torch.cat(P).numpy(); E = torch.cat(E).numpy()
    yt = Y[ids]
    aps = {}
    for g in range(N_GROUPS):
        if g == G["traffic"] and noisy:
            continue
        if yt[:, g].sum() > 0 and (SRC[ids] != 1).any():
            m = SRC[ids] != 1
            if yt[m, g].sum() > 0:
                aps[GROUP_IDS[g]] = float(average_precision_score(yt[m, g], P[m, g]))
    em = EMO[ids] >= 0
    eacc = float((E[em] == EMO[ids][em]).mean()) if em.any() else 0.0
    model.train()
    return float(np.mean(list(aps.values()))), aps, eacc, P


model = Ear(A.width, A.blocks).to(dev)
if A.init:
    model.load_state_dict(torch.load(A.init, map_location=dev)["model"])
    print("이어 학습:", A.init, flush=True)
ema = copy.deepcopy(model).eval()
print(f"모델 {sum(p.numel() for p in model.parameters()) / 1e6:.2f}M", flush=True)
opt = torch.optim.AdamW(model.parameters(), lr=A.lr, weight_decay=0.01)
sched = lambda s: min(1, s / A.warmup) * 0.5 * (1 + math.cos(math.pi * min(1, s / A.steps)))
best, t0, log = -1, time.time(), open(f"{A.out}/log.txt", "a")
for step in range(1, A.steps + 1):
    for g_ in opt.param_groups:
        g_["lr"] = A.lr * sched(step)
    if dev.startswith("cuda"):
        x, y, emo, src, x2, y2, nz = make_batch_gpu()
        y, y2 = y.clone(), y2.clone()
    else:
        x, y, emo, src, x2, y2, nz = [t.to(dev, non_blocking=True) for t in q.get()]
    with torch.no_grad():
        lm, y, emo = augment(model, x, y, emo, src, x2, y2, nz)
    with torch.autocast(dev.split(":")[0], torch.bfloat16):
        clip, elog, _ = model(lm)
    loss = F.binary_cross_entropy(clip.float(), y * 0.98 + 0.01)
    em = emo >= 0
    if em.any():
        loss = loss + 0.5 * F.cross_entropy(elog.float()[em], emo[em], label_smoothing=0.1)
    opt.zero_grad(set_to_none=True)
    loss.backward()
    torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
    opt.step()
    with torch.no_grad():
        d = min(0.999, (1 + step) / (10 + step))
        for pe, pm in zip(ema.state_dict().values(), model.state_dict().values()):
            if pe.dtype.is_floating_point:
                pe.mul_(d).add_(pm.detach(), alpha=1 - d)
            else:
                pe.copy_(pm)
    if step % 100 == 0:
        msg = f"step {step} loss {loss.item():.4f} lr {A.lr * sched(step):.2e} {time.time() - t0:.0f}s"
        print(msg, flush=True); log.write(msg + "\n"); log.flush()
    if step % 1500 == 0 or step == A.steps:
        mAP, aps, eacc, _ = evaluate(ema, 1)
        msg = f"[검증] step {step} mAP {mAP:.4f} 감정 {eacc:.4f}"
        print(msg, flush=True); log.write(msg + "\n"); log.flush()
        if mAP + 0.5 * eacc > best:
            best = mAP + 0.5 * eacc
            torch.save({"model": ema.state_dict(), "width": A.width, "blocks": A.blocks, "step": step}, f"{A.out}/best.pt")

# 마무리: 최고 판으로 검증 문턱 정하고 시험 채점
ck = torch.load(f"{A.out}/best.pt", map_location=dev)
ema.load_state_dict(ck["model"])
_, _, _, Pv = evaluate(ema, 1)
yv = Y[SPLIT == 1] if not A.eval_max else Y[np.random.default_rng(0).choice(np.where(SPLIT == 1)[0], min(A.eval_max, (SPLIT == 1).sum()), replace=False)]
th = {}
for g in range(N_GROUPS):
    if yv[:, g].sum() < 3:
        th[GROUP_IDS[g]] = 0.5; continue
    cand = np.linspace(0.05, 0.95, 91)
    f1 = [2 * ((Pv[:, g] > c) & (yv[:, g] > 0)).sum() / max(1, (Pv[:, g] > c).sum() + yv[:, g].sum()) for c in cand]
    th[GROUP_IDS[g]] = float(cand[int(np.argmax(f1))])
res = {"step": ck["step"]}
for name, noisy in (("시험", False), ("시험+차소음10dB", True)):
    mAP, aps, eacc, _ = evaluate(ema, 2, noisy)
    res[name] = {"mAP": mAP, "감정정확도": eacc, "AP": aps}
    print(f"[{name}] mAP {mAP:.4f} 감정 {eacc:.4f}", flush=True)
    for k, v in sorted(aps.items(), key=lambda t: -t[1]):
        print(f"   {k:10s} {v:.3f}")
json.dump(th, open(f"{A.out}/thresholds.json", "w"), ensure_ascii=False, indent=1)
json.dump(res, open(f"{A.out}/test_result.json", "w"), ensure_ascii=False, indent=1)
print("끝", flush=True)
