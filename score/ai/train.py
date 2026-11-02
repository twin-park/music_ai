# 진행 AI / 선율 AI 학습.  python train.py chord|melody [--steps N] [--d ..]
# 곡 단위로 검증 5% 를 떼어 두고, 검증 손실이 가장 낮은 때를 best.pt 로 저장 (적은 데이터라 오래 돌리면 외움)
import os, sys, time, math, json, random, pickle, argparse, zlib
import numpy as np
import torch
import torch.nn.functional as F
sys.path.insert(0, "/home/drboom/project/car_bgm/music")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from model import MusicLM
import tok as T

ROOT = "/home/drboom/project/car_bgm"


def is_val(s):
    return zlib.crc32((s["src"] + s["title"]).encode()) % 20 == 0


class ChordData:
    W = {"irb": .5, "pop909": .3, "ewld": .2}
    W2 = {"irb": .30, "pop909": .12, "ewld": .10, "lmd_jazz": .10, "lmd_pop": .20, "lmd_song": .18}   # --more (Lakh 리드시트 섞기)

    def __init__(self, songs, val, ctx):
        self.ctx, self.vocab = ctx, len(T.C_VOCAB)
        self.seqs = {k: [T.chord_tokens(s) for s in songs if s["src"] == k and is_val(s) == val] for k in self.W}

    def sample(self, rng):
        k = rng.choices(list(self.W), weights=list(self.W.values()))[0]
        s = rng.choice(self.seqs[k])
        if len(s) <= self.ctx + 1:
            x = s
        else:
            bars = [i for i, t in enumerate(s) if t == T.C_ID["BAR"]]
            st = rng.choice([b for b in bars if b < len(s) - self.ctx // 2] or bars[:1])
            x = s[:4] + s[st: st + self.ctx + 1 - 4]
        return np.array(x[: self.ctx + 1]), None


class MelodyData:
    W = {"wjazzd": .36, "pop909": .38, "ewld": .26}
    W2 = {"wjazzd": .18, "pop909": .17, "ewld": .12, "lmd_jazz": .10, "lmd_pop": .22, "lmd_song": .21}

    def __init__(self, songs, val, ctx):
        self.ctx, self.vocab = ctx, len(T.M_VOCAB)
        self.songs = {k: [] for k in self.W}
        for s in songs:
            if s["src"] in self.W and is_val(s) == val:
                r = T.melody_song(s)
                if r:
                    self.songs[s["src"]].append(r)
        self.given = np.zeros(self.vocab, bool)
        self.given[list(T.M_GIVEN)] = True

    def sample(self, rng):
        k = rng.choices(list(self.W), weights=list(self.W.values()))[0]
        head, bars = rng.choice(self.songs[k])
        st = rng.randrange(max(1, len(bars) - 4))
        x = list(head)
        for b in bars[st:]:
            x += b
            if len(x) > self.ctx + 1:
                break
        x = np.array(x[: self.ctx + 1])
        ps = x[(x >= T.P0) & (x <= T.P0 + T.P_HI - T.P_LO)] - T.P0 + T.P_LO
        lo, hi = (-5, 6) if len(ps) == 0 else (max(-5, T.P_LO - ps.min()), min(6, T.P_HI - ps.max()))
        x = T.transpose(x, rng.randint(lo, hi) if lo <= hi else 0)
        return x, self.given


def batch(data, rng, bs, dev):
    xs, ms = [], []
    for _ in range(bs):
        x, given = data.sample(rng)
        xs.append(x)
        ms.append(given)
    L = max(len(x) for x in xs)
    inp = torch.zeros(bs, L - 1, dtype=torch.long)
    tgt = torch.full((bs, L - 1), -100, dtype=torch.long)
    for i, x in enumerate(xs):
        t = torch.from_numpy(x)
        inp[i, : len(x) - 1] = t[:-1]
        y = t[1:].clone()
        if ms[i] is not None:
            y[torch.from_numpy(ms[i][x[1:]])] = -100           # 주어지는 낱말(코드 등)은 안 배움
        y[t[1:] == 0] = -100
        tgt[i, : len(x) - 1] = y
    return inp.to(dev), tgt.to(dev)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("which", choices=["chord", "melody"])
    ap.add_argument("--d", type=int, default=0); ap.add_argument("--layers", type=int, default=0)
    ap.add_argument("--heads", type=int, default=0); ap.add_argument("--ctx", type=int, default=0)
    ap.add_argument("--bs", type=int, default=32); ap.add_argument("--steps", type=int, default=4000)
    ap.add_argument("--lr", type=float, default=1e-3); ap.add_argument("--drop", type=float, default=0.15)
    ap.add_argument("--eval_every", type=int, default=250); ap.add_argument("--out", default="")
    ap.add_argument("--more", action="store_true", help="Lakh 리드시트(lmd_songs.pkl)까지 섞어 학습")
    A = ap.parse_args()
    cfg = dict(chord=dict(d=192, layers=4, heads=4, ctx=512), melody=dict(d=320, layers=6, heads=5, ctx=1024))[A.which]
    for k in cfg:
        if getattr(A, k):
            cfg[k] = getattr(A, k)
    out = A.out or f"{ROOT}/runs/score_{A.which}"
    os.makedirs(out, exist_ok=True)
    songs = pickle.load(open(f"{ROOT}/data/score_ai/songs.pkl", "rb"))
    D = ChordData if A.which == "chord" else MelodyData
    if A.more:
        songs += pickle.load(open(f"{ROOT}/data/score_ai/lmd_songs.pkl", "rb"))
        D.W = D.W2
    tr, va = D(songs, False, cfg["ctx"]), D(songs, True, cfg["ctx"])
    dev = "cuda"
    torch.manual_seed(0)
    model = MusicLM(tr.vocab, cfg["d"], cfg["layers"], cfg["heads"], cfg["ctx"], A.drop).to(dev)
    print(f"{A.which}: 매개변수 {sum(p.numel() for p in model.parameters()) / 1e6:.2f}M · 설정 {cfg}", flush=True)
    opt = torch.optim.AdamW(model.parameters(), lr=A.lr, betas=(0.9, 0.95), weight_decay=0.1)
    vr = random.Random(123)
    vb = [batch(va, vr, A.bs, dev) for _ in range(12)]

    def evaluate():
        model.eval()
        tot = n = 0
        with torch.no_grad(), torch.autocast("cuda", torch.bfloat16):
            for x, y in vb:
                l = F.cross_entropy(model(x).float().reshape(-1, tr.vocab), y.reshape(-1), ignore_index=-100, reduction="sum")
                tot += l.item(); n += (y != -100).sum().item()
        model.train()
        return tot / n

    rng = random.Random(0)
    best, t0, log = 1e9, time.time(), []
    for step in range(A.steps + 1):
        if step % A.eval_every == 0:
            v = evaluate()
            log.append((step, v))
            mark = ""
            if v < best:
                best = v
                torch.save(dict(model=model.state_dict(), cfg=model.cfg, step=step, val=v, which=A.which), f"{out}/best.pt")
                mark = " ★"
            print(f"  걸음 {step} · 검증 {v:.4f}{mark} · {time.time() - t0:.0f}초", flush=True)
            if step == A.steps:
                break
        lr = A.lr * min(1, (step + 1) / 200) * (0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * step / A.steps)))
        for g in opt.param_groups:
            g["lr"] = lr
        x, y = batch(tr, rng, A.bs, dev)
        with torch.autocast("cuda", torch.bfloat16):
            loss = F.cross_entropy(model(x).float().reshape(-1, tr.vocab), y.reshape(-1), ignore_index=-100)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
    json.dump(log, open(f"{out}/log.json", "w"))
    print(f"끝: 가장 좋은 검증 {best:.4f}", flush=True)


if __name__ == "__main__":
    main()
