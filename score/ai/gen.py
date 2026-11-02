# 생성: 진행 AI(틀은 공식으로 강제: A A B A …) · 선율 AI(코드는 주고 선율만 씀)
#   셈은 torch(학습한 그대로) 또는 numpy(npmodel.py · 윈도우 묶음). SCORE_BACKEND=numpy 거나 torch 가 없으면 numpy.
import os, sys, math, random
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tok as T

RUNS = os.environ.get("CAR_BGM_RUNS", os.path.join(HERE, "..", "..", "runs"))
BACKEND = os.environ.get("SCORE_BACKEND", "torch")
if BACKEND == "torch":
    try:
        import torch
        sys.path.append(os.path.join(HERE, "..", "..", "music"))
        from model import MusicLM
        torch.set_num_threads(4)
    except ImportError:
        BACKEND = "numpy"


class TorchLM:
    def __init__(self, which, dev="cpu"):
        ck = torch.load(f"{RUNS}/score_{which}/best.pt", map_location=dev)
        c = ck["cfg"]
        self.m = MusicLM(c["vocab"], c["d"], c["layers"], c["heads"], c["ctx"], 0.0).to(dev)
        self.m.load_state_dict(ck["model"])
        self.m.eval()
        self.cfg, self.layers = c, self.m.layers

    def step(self, ids, caches, pos):
        with torch.no_grad():
            return self.m(torch.tensor([ids], dtype=torch.long), caches, pos)[0, -1].float().numpy()


def load(which):
    if BACKEND == "numpy":
        from npmodel import NpLM
        return NpLM(f"{RUNS}/score_{which}/best.npz")
    return TorchLM(which)


class Runner:
    """KV 캐시로 낱말을 하나씩 넣고 다음 낱말 확률을 받음. 문맥이 차면 머리 + 최근 마디로 다시 채움."""

    def __init__(self, model):
        self.m, self.ctx = model, model.cfg["ctx"]
        self.reset()

    def reset(self):
        self.caches = [dict(max=self.ctx) for _ in self.m.layers]
        self.toks, self.logits = [], None

    def feed(self, ids):
        if not ids:
            return
        self.logits = self.m.step(list(ids), self.caches, len(self.toks))
        self.toks += list(ids)

    def room(self, need, head_len, bar_id):
        """need 개 더 넣을 자리가 없으면: 머리 + 뒤쪽 마디들만 남기고 다시 넣기"""
        if len(self.toks) + need < self.ctx - 2:
            return
        keep = self.toks[:head_len]
        bars = [i for i, t in enumerate(self.toks) if t == bar_id and i >= head_len]
        cut = next((b for b in bars if len(self.toks) - b < self.ctx // 2), bars[-1])
        rest = self.toks[cut:]
        self.reset()
        self.feed(keep + rest)


def pick(logits, allowed, temp, top_p, rng):
    l = np.full(logits.shape, -np.inf, np.float32)
    l[allowed] = logits[allowed] / np.float32(max(temp, 1e-3))
    p = np.exp(l - l.max())
    p = (p / p.sum()).astype(np.float64)
    order = np.argsort(-p, kind="stable")
    cs = np.cumsum(p[order])
    keep = order[: max(1, int(np.searchsorted(cs, top_p)) + 1)]
    q = p[keep] / p[keep].sum()
    return int(keep[rng.choice(len(keep), p=q)])


# ---------------- 진행 ----------------
def progression(model, form, minor=False, src="jazz", ts=4, beats=(0, 2), temp=0.9, top_p=0.92, seed=0, fixed=None):
    """form: [('A', 8), ('A', 8), ('B', 8), ('A', 8)] → 마디별 [(박, 도수, 종류)] (조 기준 도수)
    fixed: {마디번호: [(박, 도수, 종류)]} 공식으로 박아 둘 마디 (예: 끝 마디 I)"""
    C = T.C_ID
    rng = np.random.default_rng(seed)
    r = Runner(model)
    head = [C["BOS"], C[f"SRC_{src}"], C["MODE_min" if minor else "MODE_maj"], C[f"TS_{ts}"]]
    r.feed(head)
    out, bar_i = [], 0
    BEAT = [C[f"BEAT_{b}"] for b in range(4)]
    DEG = [C[f"DEG_{d}"] for d in range(12)]
    QQ = [C[f"Q_{q}"] for q in range(11)]
    for sec, n in form:
        for k in range(n):
            r.room(40, len(head), C["BAR"])
            r.feed([C["BAR"]] + ([C[f"SEC_{sec}"]] if k == 0 else []))
            bar = []
            if fixed and bar_i in fixed:
                for b, d, q in fixed[bar_i]:
                    r.feed([C[f"BEAT_{b}"], C[f"DEG_{d}"], C[f"Q_{q}"]])
                    bar.append((b, d, q))
            else:
                last = -1
                while True:
                    allowed = [BEAT[b] for b in beats if last < b < ts]
                    if bar or bar_i > 0:
                        allowed.append(C["BAR"])
                    if bar_i == 0 and not bar:
                        allowed = [BEAT[0]]
                    t = pick(r.logits, allowed, temp, top_p, rng)
                    if t == C["BAR"]:
                        break
                    b = BEAT.index(t)
                    r.feed([t])
                    d = DEG.index(pick(r.logits, DEG, temp, top_p, rng)); r.feed([DEG[d]])
                    q = QQ.index(pick(r.logits, QQ, temp, top_p, rng)); r.feed([QQ[q]])
                    bar.append((b, d, q))
                    last = b
            out.append(bar)
            bar_i += 1
    # 빈 마디는 앞 코드 이어 받음
    cur = None
    for i, bar in enumerate(out):
        if not bar and cur is not None:
            out[i] = [(0, cur[1], cur[2])]
        if out[i]:
            cur = out[i][-1]
    return out


# ---------------- 선율 ----------------
class MelodyWriter:
    """코드를 마디마다 넣어 주고 선율만 받아 씀. 같은 문맥을 이어 가므로 A → A' 에서 앞 선율을 기억해 비슷하게 씀."""

    def __init__(self, model, ts=4, kind="head", feel="swing", tempo="TEMPO_med", minor=False, dens=1, reg=1, seed=0):
        M = T.M_ID
        self.M, self.ts, self.rng = M, ts, np.random.default_rng(seed)
        self.r = Runner(model)
        self.head = [M["BOS"], M[f"KIND_{kind}"], M[f"FEEL_{feel}"], M[tempo], M[f"TS_{ts}"],
                     M["MODE_min" if minor else "MODE_maj"], M[f"DENS_{dens}"], M[f"REG_{reg}"]]
        self.r.feed(self.head)
        self.POS = [M[f"POS_{p}"] for p in range(4 * T.TPB)]
        self.P = {p: M[f"P_{p}"] for p in range(T.P_LO, T.P_HI + 1)}
        self.D = [M[f"D_{d}"] for d in T.DUR_SET]
        self.prev_p = None

    def chord_toks(self, chords, nxt):
        M = self.M
        t = [M["BAR"]]
        for b, root, q in chords:
            t += [M[f"CPOS_{b}"], M[f"CR_{root}"], M[f"CQ_{q}"]]
        if not chords:
            t.append(M["CNONE"])
        t += [M[f"NR_{nxt[1]}"], M[f"NQ_{nxt[2]}"]] if nxt else [M["NNONE"]]
        return t

    def bar(self, chords, nxt, lo, hi, temp=0.9, top_p=0.92, leap=12, force=None, max_notes=16, rest_ok=True):
        """한 마디: chords=[(박, 근음, 종류)], nxt=다음 마디 첫 코드. force=[(틱, 길이틱, 음)] 이면 그대로 넣음."""
        M = self.M
        self.r.room(80, len(self.head), M["BAR"])
        self.r.feed(self.chord_toks(chords, nxt))
        notes = []
        if force is not None:
            for on, d, p in force:
                dd = T.DUR_SET[T.DUR_IDX[min(d, 199)]]
                self.r.feed([M[f"POS_{on}"], M[f"P_{min(max(p, T.P_LO), T.P_HI)}"], M[f"D_{dd}"]])
                notes.append((on, dd, p))
                self.prev_p = p
            return notes
        last = -1
        L = self.ts * T.TPB
        while len(notes) < max_notes:
            allowed = [self.POS[p] for p in range(last + 1, L)]
            if notes or rest_ok:
                allowed.append(M["BAR"])
            t = pick(self.r.logits, allowed, temp, top_p, self.rng)
            if t == M["BAR"]:
                break
            on = self.POS.index(t)
            self.r.feed([t])
            ps = [p for p in range(lo, hi + 1) if self.prev_p is None or abs(p - self.prev_p) <= leap]
            pt = pick(self.r.logits, [self.P[p] for p in ps], temp, top_p, self.rng)
            p = T.P_LO + (pt - self.P[T.P_LO])
            self.r.feed([pt])
            dt = pick(self.r.logits, self.D, temp, top_p, self.rng)
            d = T.DUR_SET[self.D.index(dt)]
            self.r.feed([dt])
            notes.append((on, d, p))
            self.prev_p = p
            last = on
        return notes
