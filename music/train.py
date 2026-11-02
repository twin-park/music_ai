# 음악 모델 학습. 곡에서 마디 단위로 잘라 조건을 계산하고, 조옮김을 섞어 2048 낱말 조각으로 학습.
import os, sys, time, math, json, argparse
import numpy as np, torch, torch.nn.functional as F
sys.path.insert(0, os.path.dirname(__file__))
from tokens import (TOK, VOCAB, BOS, EOS, SEP, PAD, TIMESIGS, GENRES, MOODS, encode_bars, conditions)
from model import MusicLM

D = "/home/drboom/project/car_bgm/data/music"


SRCS = {"pdmx": "/home/drboom/project/car_bgm/data/music", "lmd": "/home/drboom/project/car_bgm/data/music_lmd"}
GB = lambda *gs: sum(1 << GENRES.index(g) for g in gs)
# 섞는 법: [(출처, 무게, 장르 비트(0=전부), 크리스마스 빼기)]
MIXES = {
    "base": [("pdmx", 0.5, 0, False), ("lmd", 0.5, 0, True)],
    "jazz": [("lmd", 0.7, GB("jazz"), True), ("pdmx", 0.3, GB("jazz", "blues", "rnb"), False)],
    # 재즈 다시(과적합 막기): 재즈 곡이 2천 개 남짓이라 재즈만 돌리면 1바퀴 뒤부터 외움 → 이웃 장르·전체 곡을 조금 섞어 잊지 않게
    "jazz2": [("lmd", 0.45, GB("jazz"), True), ("pdmx", 0.2, GB("jazz", "rnb"), False),
              ("lmd", 0.15, GB("latin", "easylistening", "ambient", "folk"), True), ("lmd", 0.1, 0, True), ("pdmx", 0.1, 0, False)],
    "orch": [("lmd", 0.5, GB("classical", "orchestral", "soundtrack"), True), ("pdmx", 0.5, GB("classical", "soundtrack"), False)],
}


class Windows(torch.utils.data.IterableDataset):
    def __init__(self, split, ctx, seed=0, mix="base", drop=0.1, fixed=False):
        self.split, self.ctx, self.seed, self.mix, self.drop, self.fixed = split, ctx, seed, mix, drop, fixed

    def setup(self):
        self.src = []
        for name, wt, gbits, noxmas in MIXES[self.mix]:
            d = SRCS[name]
            if not os.path.exists(f"{d}/pieces.npz"):
                continue
            P = dict(np.load(f"{d}/pieces.npz", allow_pickle=True))
            ok = P["split"] == self.split
            if gbits:
                ok &= (P["genre"] & gbits) > 0
            if noxmas and "xmas" in P:
                ok &= P["xmas"] == 0
            ids = np.where(ok)[0]
            if len(ids) == 0:
                continue
            w = np.minimum(P["note_n"][ids], 4000).astype(np.float64)
            self.src.append(dict(notes=np.load(f"{d}/notes.npy", mmap_mode="r"), bars=np.load(f"{d}/bars.npy", mmap_mode="r"),
                                 P=P, ids=ids, w=w / w.sum(), wt=wt))
        tw = np.array([x["wt"] for x in self.src]); self.sw = tw / tw.sum()

    def sample(self, rng):
        S = self.src[rng.choice(len(self.src), p=self.sw)]
        P = S["P"]
        i = rng.choice(S["ids"], p=S["w"])
        nt = np.array(S["notes"][P["note_off"][i]:P["note_off"][i] + P["note_n"][i]], np.int64)
        bs = np.array(S["bars"][P["bar_off"][i]:P["bar_off"][i] + P["bar_n"][i]], np.int64)
        end = int((nt[:, 0] + nt[:, 3]).max())
        bl = np.diff(np.append(bs, max(end, bs[-1] + 1)))
        bl = np.minimum(bl, 96)
        nb = len(bs)
        b0 = 0 if (self.fixed or rng.random() < 0.3) else int(rng.integers(0, max(1, nb - 4)))
        if not self.fixed:      # 조옮김 -5~+6
            k = int(rng.integers(-5, 7))
            pm = nt[:, 1] != 128
            if pm.any() and 0 <= nt[pm, 2].min() + k and nt[pm, 2].max() + k <= 127:
                nt[pm, 2] += k
        nt[:, 4] = np.clip(nt[:, 4], 1, 127)
        body, nbar, sel = encode_bars(nt, bs, bl, b0, self.ctx - 48)
        if nbar == 0:
            return None
        genres = [GENRES[g] for g in range(len(GENRES)) if P["genre"][i] >> g & 1]
        moods = [MOODS[m] for m in range(len(MOODS)) if "mood" in P and P["mood"][i] >> m & 1]
        conds = conditions(sel, int(np.median(bl[b0:b0 + nbar])), float(P["qpm"][i]), TIMESIGS[P["ts"][i]], genres, nbar, moods)
        if not self.fixed:       # 조건 일부를 빼고도 쓸 수 있게 (박자는 남김)
            conds = [c for c in conds if c.startswith("TS_") or rng.random() > self.drop]
        pre = [BOS] + [TOK[c] for c in conds] + [SEP]
        seq = pre + body + ([EOS] if b0 + nbar >= nb else [])
        seq = seq[:self.ctx + 1]
        x = np.full(self.ctx + 1, PAD, np.int64); x[:len(seq)] = seq
        m = np.zeros(self.ctx, np.float32); m[len(pre) - 1:len(seq) - 1] = 1    # 조건 부분은 학습 안 함
        return x, m

    def __iter__(self):
        self.setup()
        wi = torch.utils.data.get_worker_info()
        rng = np.random.default_rng(self.seed + (wi.id if wi else 0) * 1000 + int(time.time()) % 1000 * (not self.fixed))
        while True:
            try:
                s = self.sample(rng)
            except Exception as e:      # 이상한 곡 하나 때문에 학습이 멈추지 않게
                print("조각 건너뜀:", repr(e)[:120], flush=True); s = None
            if s is not None:
                yield torch.from_numpy(s[0]), torch.from_numpy(s[1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--d", type=int, default=768); ap.add_argument("--layers", type=int, default=12)
    ap.add_argument("--heads", type=int, default=12); ap.add_argument("--ctx", type=int, default=2048)
    ap.add_argument("--bs", type=int, default=16); ap.add_argument("--accum", type=int, default=4)
    ap.add_argument("--steps", type=int, default=20000); ap.add_argument("--lr", type=float, default=6e-4)
    ap.add_argument("--warmup", type=int, default=1000); ap.add_argument("--drop", type=float, default=0.1)
    ap.add_argument("--mix", default="base"); ap.add_argument("--val_mix", default=""); ap.add_argument("--init", default="")
    ap.add_argument("--workers", type=int, default=5); ap.add_argument("--eval_every", type=int, default=1000)
    ap.add_argument("--out", default="/home/drboom/project/car_bgm/runs/music")
    ap.add_argument("--bench", type=int, default=0)
    ap.add_argument("--no_compile", action="store_true")
    A = ap.parse_args()
    os.makedirs(A.out, exist_ok=True)
    torch.manual_seed(0); torch.set_num_threads(2)
    torch.backends.cuda.matmul.allow_tf32 = True
    dev = "cuda"
    model = MusicLM(VOCAB, A.d, A.layers, A.heads, A.ctx, A.drop).to(dev)
    if A.init:
        model.load_state_dict(torch.load(A.init, map_location=dev)["model"])
    print(f"모델 {sum(p.numel() for p in model.parameters()) / 1e6:.1f}M · 낱말 {VOCAB}", flush=True)
    fwd = model if A.no_compile else torch.compile(model)
    dl = torch.utils.data.DataLoader(Windows(0, A.ctx, mix=A.mix), batch_size=A.bs,
                                     num_workers=A.workers, pin_memory=True, prefetch_factor=4, persistent_workers=True)
    vds = Windows(1, A.ctx, seed=7, mix=A.val_mix or A.mix, fixed=True); vds.setup()
    vrng = np.random.default_rng(7)
    val = [s for s in (vds.sample(vrng) for _ in range(400)) if s is not None][:256]
    vx = torch.stack([torch.from_numpy(v[0]) for v in val]); vm = torch.stack([torch.from_numpy(v[1]) for v in val])
    decay = [p for n, p in model.named_parameters() if p.dim() >= 2]
    nodecay = [p for n, p in model.named_parameters() if p.dim() < 2]
    opt = torch.optim.AdamW([{"params": decay, "weight_decay": 0.1}, {"params": nodecay, "weight_decay": 0}],
                            lr=A.lr, betas=(0.9, 0.95), fused=True)
    lr_at = lambda s: A.lr * min(1, s / A.warmup) * (0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * min(1, s / A.steps))))

    @torch.no_grad()
    def evaluate():
        model.eval(); tot, n = 0.0, 0.0
        for k in range(0, len(vx), 16):
            x, m = vx[k:k + 16].to(dev), vm[k:k + 16].to(dev)
            with torch.autocast("cuda", torch.bfloat16):
                lg = model(x[:, :-1])
            l = F.cross_entropy(lg.float().reshape(-1, VOCAB), x[:, 1:].reshape(-1), reduction="none")
            tot += float((l * m.reshape(-1)).sum()); n += float(m.sum())
        model.train()
        return tot / n

    it = iter(dl)
    log = open(f"{A.out}/log.txt", "a")
    best, t0, tok = 1e9, time.time(), 0
    if A.init:      # 시작점(기본 모델) 점수부터 — 미세조정이 정말 나아졌는지 비교용
        vl = evaluate(); best = vl
        msg = f"[검증] step 0 loss {vl:.4f} ppl {math.exp(vl):.3f}"
        print(msg, flush=True); log.write(msg + "\n"); log.flush()
        torch.save({"model": model.state_dict(), "cfg": model.cfg, "step": 0, "val": vl}, f"{A.out}/best.pt")
    for step in range(1, A.steps + 1):
        for g in opt.param_groups:
            g["lr"] = lr_at(step)
        lsum = 0.0
        for _ in range(A.accum):
            x, m = next(it)
            x, m = x.to(dev, non_blocking=True), m.to(dev, non_blocking=True)
            with torch.autocast("cuda", torch.bfloat16):
                lg = fwd(x[:, :-1])
            l = F.cross_entropy(lg.float().reshape(-1, VOCAB), x[:, 1:].reshape(-1), reduction="none")
            loss = (l * m.reshape(-1)).sum() / m.sum().clamp(min=1)
            (loss / A.accum).backward()
            lsum += loss.item() / A.accum; tok += int(m.sum())
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step(); opt.zero_grad(set_to_none=True)
        if A.bench and step == A.bench:
            dt = time.time() - t0
            print(f"[속도] {step}걸음 {dt:.1f}s · {tok / dt:.0f} 낱말/s · 걸음당 {dt / step:.2f}s", flush=True)
            return
        if step % 50 == 0:
            msg = f"step {step} loss {lsum:.4f} lr {lr_at(step):.2e} {tok / (time.time() - t0):.0f}tok/s {time.time() - t0:.0f}s"
            print(msg, flush=True); log.write(msg + "\n"); log.flush()
        if step % A.eval_every == 0 or step == A.steps:
            vl = evaluate()
            msg = f"[검증] step {step} loss {vl:.4f} ppl {math.exp(vl):.3f}"
            print(msg, flush=True); log.write(msg + "\n"); log.flush()
            ck = {"model": model.state_dict(), "cfg": model.cfg, "step": step, "val": vl}
            torch.save(ck, f"{A.out}/last.pt")
            if vl < best:
                best = vl; torch.save(ck, f"{A.out}/best.pt")


if __name__ == "__main__":
    main()
