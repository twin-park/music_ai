# 진행 AI / 선율 AI 학습 v3 (11-11).  python train3.py chord|melody [--d ..] [--teacher 선생.pt]
#   자료: 사람이 적은 리드시트(songs.pkl) + Lakh 리드시트(lmd_songs.pkl) + PDMX 리드시트(pdmx_songs.pkl · 클래식)
#   낱말: tok3.py (진행 SRC_classical · 선율 SRC · CT)
#   --teacher: 큰 모델(선생)의 확률을 같이 배움(증류) → 작은 모델이 선생 가까이 따라감
#   곡 단위로 검증 5% 를 떼어 두고, 검증 손실이 가장 낮은 때를 best.pt 로 저장 · 한동안 안 좋아지면 멈춤
import os, sys, time, math, json, random, pickle, argparse, zlib
import numpy as np
import torch
import torch.nn.functional as F
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.append("/home/drboom/project/car_bgm/music")
from model import MusicLM
import tok3 as T

ROOT = "/home/drboom/project/car_bgm"
CW = {"irb": .22, "lmd_jazz": .06, "pop909": .08, "lmd_pop": .11, "ewld": .07, "lmd_song": .11, "pdmx_classical": .20, "pdmx_misc": .08,
      "pdmx_pop": .04, "pdmx_folk": .02, "pdmx_jazz": .01}
MW = {"wjazzd": .13, "lmd_jazz": .08, "ewld": .10, "pop909": .11, "lmd_pop": .12, "lmd_song": .13, "pdmx_classical": .18, "pdmx_misc": .08,
      "pdmx_pop": .04, "pdmx_folk": .02, "pdmx_jazz": .01}


def is_val(s):
    return zlib.crc32((s["src"] + s["title"]).encode()) % 20 == 0


def load_songs():
    D = f"{ROOT}/data/score_ai"
    return pickle.load(open(f"{D}/songs.pkl", "rb")) + pickle.load(open(f"{D}/lmd_songs.pkl", "rb")) + pickle.load(open(f"{D}/pdmx_songs.pkl", "rb"))


def tokenized(which):
    """곡마다 (src, 검증?, 머리, 낱말 줄, 마디 시작 자리) — 한 번 만들어 두고 다시 씀"""
    path = f"{ROOT}/data/score_ai/v3_{which}_tok.pkl"
    if os.path.exists(path):
        return pickle.load(open(path, "rb"))
    out = []
    for s in load_songs():
        if which == "chord":
            if s["src"] not in CW:
                continue
            x = np.array(T.chord_tokens(s), np.int16)
            out.append((s["src"], is_val(s), x[:4], x[4:], np.nonzero(x[4:] == T.C_ID["BAR"])[0].astype(np.int32)))
        else:
            if s["src"] not in MW or s["kind"] == "chords":
                continue
            ct = T.ct_ratio(s)
            if s["src"].startswith(("lmd_", "pdmx_")) and (ct is None or ct < .4):
                continue                                      # 선율을 잘못 고른 곡 (코드와 거의 안 맞음)
            s["ct"] = ct
            r = T.melody_song(s)
            if not r:
                continue
            head, bars = r
            offs = np.cumsum([0] + [len(b) for b in bars[:-1]]).astype(np.int32)
            out.append((s["src"], is_val(s), np.array(head, np.int16), np.array([t for b in bars for t in b], np.int16), offs))
    pickle.dump(out, open(path, "wb"))
    return out


class Data:
    def __init__(self, which, items, val, ctx):
        self.which, self.ctx = which, ctx
        self.W = CW if which == "chord" else MW
        self.vocab = len(T.C_VOCAB if which == "chord" else T.M_VOCAB)
        self.by = {k: [] for k in self.W}
        for src, v, head, flat, offs in items:
            if v == val:
                self.by[src].append((head, flat, offs))
        self.W = {k: w for k, w in self.W.items() if self.by[k]}
        self.given = None
        if which == "melody":
            self.given = np.zeros(self.vocab, bool)
            self.given[list(T.M_GIVEN)] = True
        self.group = {k: (T.C_SRC if which == "chord" else T.M_SRC)[k] for k in self.W}

    def sample(self, rng, only=None):
        ks = [k for k in self.W if only is None or self.group[k] == only]
        k = rng.choices(ks, weights=[self.W[x] for x in ks])[0]
        head, flat, offs = rng.choice(self.by[k])
        room = self.ctx + 1 - len(head)
        if self.which == "chord":
            if len(flat) <= room:
                st = 0
            else:
                c = [b for b in offs if b < len(flat) - self.ctx // 2]
                st = int(rng.choice(c)) if c else 0
            x = np.concatenate([head, flat[st: st + room]]).astype(np.int64)
            self.last_src = k
            return x, None
        self.last_src = k
        st = int(offs[rng.randrange(max(1, len(offs) - 4))])
        x = np.concatenate([head, flat[st: st + room]]).astype(np.int64)
        ps = x[(x >= T.P0) & (x <= T.P0 + T.P_HI - T.P_LO)] - T.P0 + T.P_LO
        lo, hi = (-5, 6) if len(ps) == 0 else (max(-5, T.P_LO - ps.min()), min(6, T.P_HI - ps.max()))
        return T.transpose(x, rng.randint(lo, hi) if lo <= hi else 0), self.given


OLD_SRC = {"wjazzd", "ewld", "pop909", "lmd_jazz", "lmd_pop", "lmd_song", "irb"}      # v2 가 배운 출처


def batch(data, rng, bs, dev, only=None, with_old=False):
    xs, ms, old = [], [], []
    for _ in range(bs):
        x, given = data.sample(rng, only)
        xs.append(x)
        ms.append(given)
        old.append(data.last_src in OLD_SRC)
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
    if with_old:
        return inp.to(dev), tgt.to(dev), torch.tensor(old, device=dev)
    return inp.to(dev), tgt.to(dev)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("which", choices=["chord", "melody"])
    ap.add_argument("--d", type=int, default=0); ap.add_argument("--layers", type=int, default=0)
    ap.add_argument("--heads", type=int, default=0); ap.add_argument("--ctx", type=int, default=0)
    ap.add_argument("--bs", type=int, default=48); ap.add_argument("--steps", type=int, default=12000)
    ap.add_argument("--lr", type=float, default=8e-4); ap.add_argument("--drop", type=float, default=0.1)
    ap.add_argument("--eval_every", type=int, default=500); ap.add_argument("--patience", type=int, default=3000)
    ap.add_argument("--teacher", default=""); ap.add_argument("--kd", type=float, default=0.5, help="증류 손실 비중")
    ap.add_argument("--teacher_v2", default="", help="v2 큰 모델(옛 낱말)을 선생으로 — 옛 출처 곡에서만 그 확률을 같이 배움 (선율)")
    ap.add_argument("--sel_jazz", type=float, default=0.0, help="가장 좋은 때를 고를 때 재즈 검증의 비중 (0 = 전체만)")
    ap.add_argument("--jazz_x", type=float, default=1.0, help="재즈 출처를 뽑는 비율 배수")
    ap.add_argument("--ema", type=float, default=0.0, help="가중치 이동 평균 (0 = 안 씀, 0.999 쯤)")
    ap.add_argument("--init", default="", help="이 저장본의 가중치에서 이어 배움 (멈춘 학습 잇기)")
    ap.add_argument("--warmup", type=int, default=200)
    ap.add_argument("--out", required=True)
    A = ap.parse_args()
    cfg = dict(chord=dict(d=128, layers=4, heads=4, ctx=256), melody=dict(d=256, layers=6, heads=8, ctx=512))[A.which]
    for k in cfg:
        if getattr(A, k):
            cfg[k] = getattr(A, k)
    os.makedirs(A.out, exist_ok=True)
    items = tokenized(A.which)
    tr, va = Data(A.which, items, False, cfg["ctx"]), Data(A.which, items, True, cfg["ctx"])
    if A.jazz_x != 1.0:
        tr.W = {k: w * (A.jazz_x if tr.group[k] == "jazz" else 1.0) for k, w in tr.W.items()}
    print("곡 수(학습/검증):", {k: (len(tr.by[k]), len(va.by.get(k, []))) for k in tr.W}, flush=True)
    dev = "cuda"
    torch.manual_seed(0)
    model = MusicLM(tr.vocab, cfg["d"], cfg["layers"], cfg["heads"], cfg["ctx"], A.drop).to(dev)
    print(f"{A.which}: 매개변수 {sum(p.numel() for p in model.parameters()) / 1e6:.2f}M · 설정 {cfg}", flush=True)
    if A.init:
        ck0 = torch.load(A.init, map_location=dev)
        model.load_state_dict(ck0["model"])
        print(f"이어 배움: {A.init} (걸음 {ck0.get('step')} · 검증 {ck0.get('val', 0):.4f})", flush=True)
    teacher = None
    if A.teacher:
        ck = torch.load(A.teacher, map_location=dev)
        teacher = MusicLM(**ck["cfg"]).to(dev).eval()
        teacher.load_state_dict(ck["model"])
        print(f"선생: {A.teacher} (검증 {ck['val']:.4f})", flush=True)
    t2 = None
    if A.teacher_v2:                                          # v2 선생: 머리의 SRC(1) · CT(9) 를 빼고 낱말 번호를 옛 것으로 바꿔 넣음
        import tok as T2
        assert A.which == "melody"
        ck = torch.load(A.teacher_v2, map_location=dev)
        t2 = MusicLM(**ck["cfg"]).to(dev).eval()
        t2.load_state_dict(ck["model"])
        mp = torch.tensor([T2.M_ID.get(t, -1) for t in T.M_VOCAB], device=dev)
        MAPC, MAPV = mp.clamp(min=0), (mp >= 0).float()
        print(f"v2 선생: {A.teacher_v2}", flush=True)
    opt = torch.optim.AdamW(model.parameters(), lr=A.lr, betas=(0.9, 0.95), weight_decay=0.1)
    ema = None
    if A.ema > 0:                                              # 이동 평균한 가중치로 검증 · 저장 (끝 무렵 흔들림이 줄어듦)
        ema = MusicLM(tr.vocab, cfg["d"], cfg["layers"], cfg["heads"], cfg["ctx"], 0.0).to(dev).eval()
        ema.load_state_dict(model.state_dict())
        for p_ in ema.parameters():
            p_.requires_grad_(False)
    vr = random.Random(123)
    groups = sorted(set(va.group.values()))
    vb = {"전체": [batch(va, vr, 32, dev) for _ in range(16)]}
    for g in groups:
        vb[g] = [batch(va, vr, 32, dev, g) for _ in range(6)]

    def evaluate():
        net = ema if ema is not None else model
        model.eval()
        out = {}
        with torch.no_grad(), torch.autocast("cuda", torch.bfloat16):
            for name, bl in vb.items():
                tot = n = 0
                for x, y in bl:
                    l = F.cross_entropy(net(x).float().reshape(-1, tr.vocab), y.reshape(-1), ignore_index=-100, reduction="sum")
                    tot += l.item(); n += (y != -100).sum().item()
                out[name] = tot / n
        model.train()
        return out

    rng = random.Random(0)
    best, best_step, t0, log = 1e9, 0, time.time(), []
    for step in range(A.steps + 1):
        if step % A.eval_every == 0:
            v = evaluate()
            log.append((step, v))
            mark = ""
            sc = (1 - A.sel_jazz) * v["전체"] + A.sel_jazz * v.get("jazz", v["전체"])
            if sc < best:
                best, best_step = sc, step
                torch.save(dict(model=(ema if ema is not None else model).state_dict(), cfg=model.cfg, step=step, val=v["전체"], vals=v, which=A.which, tok="v3"),
                           f"{A.out}/best.pt")
                mark = " ★"
            print(f"  걸음 {step} · 검증 {v['전체']:.4f}{mark} · " + " ".join(f"{g} {v[g]:.3f}" for g in groups) + f" · {time.time() - t0:.0f}초", flush=True)
            if step == A.steps or step - best_step >= A.patience:
                break
        lr = A.lr * min(1, (step + 1) / A.warmup) * (0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * step / A.steps)))
        for g in opt.param_groups:
            g["lr"] = lr
        x, y, is_old = batch(tr, rng, A.bs, dev, with_old=True)
        with torch.autocast("cuda", torch.bfloat16):
            lg = model(x).float()
            loss = F.cross_entropy(lg.reshape(-1, tr.vocab), y.reshape(-1), ignore_index=-100)
            if t2 is not None:
                with torch.no_grad():
                    x2 = MAPC[torch.cat([x[:, :1], x[:, 2:9], x[:, 10:]], 1)]
                    p2 = F.softmax(t2(x2).float(), -1)[:, 7:]                    # v2 자리 i-2 ↔ v3 자리 i (i ≥ 9)
                    tp = p2[..., MAPC] * MAPV                                     # 옛 낱말 확률 → 새 낱말 자리
                m = (y[:, 9:] != -100) & is_old[:, None]
                ce_tok = F.cross_entropy(lg.reshape(-1, tr.vocab), y.reshape(-1), ignore_index=-100, reduction="none").reshape(y.shape)
                kd_tok = -(tp * F.log_softmax(lg[:, 9:], -1)).sum(-1)
                tok = ce_tok.clone()
                tok[:, 9:] = torch.where(m, (1 - A.kd) * ce_tok[:, 9:] + A.kd * kd_tok, ce_tok[:, 9:])
                loss = tok[y != -100].mean()
            elif teacher is not None:
                with torch.no_grad():
                    tp = F.softmax(teacher(x).float(), -1)
                m = (y != -100)
                kl = -(tp[m] * F.log_softmax(lg[m], -1)).sum(-1).mean()     # 선생 확률을 맞히기 (교차 엔트로피)
                loss = (1 - A.kd) * loss + A.kd * kl
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        if ema is not None:
            d_ = min(A.ema, (1 + step) / (10 + step))
            with torch.no_grad():
                for pe, pm in zip(ema.parameters(), model.parameters()):
                    pe.mul_(d_).add_(pm.detach(), alpha=1 - d_)
    json.dump(log, open(f"{A.out}/log.json", "w"), ensure_ascii=False)
    print(f"끝: 가장 좋은 검증 {best:.4f} (걸음 {best_step})", flush=True)


if __name__ == "__main__":
    main()
