# v2(큰 모델) 와 v3(작은 모델) 를 같은 검증 조각으로 견줌 — 낱말 번호만 맞춰 주고, 맞히는 낱말은 똑같이
#   옛 출처(v2 가 배운 갈래: 재즈 · 팝 · 노래)의 검증 곡만 씀. 클래식은 v3 만 잼.
#   python eval_v2_v3.py chord|melody  v3.pt [v3_다른.pt …]
import os, sys, random
import numpy as np, torch, torch.nn.functional as F
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.append("/home/drboom/project/car_bgm/music")
from model import MusicLM
import tok as T2, tok3 as T3, train3 as TR

ROOT = "/home/drboom/project/car_bgm"
OLD = {"wjazzd", "ewld", "pop909", "lmd_jazz", "lmd_pop", "lmd_song", "irb"}
which = sys.argv[1]
V3, I2 = (T3.C_VOCAB, T2.C_ID) if which == "chord" else (T3.M_VOCAB, T2.M_ID)
MAP = np.array([I2.get(t, -1) for t in V3])
dev = "cuda"


def load(pt):
    ck = torch.load(pt, map_location=dev)
    m = MusicLM(**ck["cfg"]).to(dev).eval()
    m.load_state_dict(ck["model"])
    return m, ck


def loss_of(model, seqs, given, skip):
    """seqs: 낱말 줄들 · given: 안 맞히는 낱말(bool 표) · skip: 앞에서 안 세는 목표 수"""
    tot = n = 0
    for i in range(0, len(seqs), 32):
        xs = seqs[i:i + 32]
        L = max(len(x) for x in xs)
        inp = torch.zeros(len(xs), L - 1, dtype=torch.long); tgt = torch.full((len(xs), L - 1), -100, dtype=torch.long)
        for k, x in enumerate(xs):
            t = torch.from_numpy(x)
            inp[k, :len(x) - 1] = t[:-1]
            y = t[1:].clone()
            if given is not None:
                y[torch.from_numpy(given[x[1:]])] = -100
            y[:skip] = -100
            tgt[k, :len(x) - 1] = y
        with torch.no_grad(), torch.autocast("cuda", torch.bfloat16):
            lg = model(inp.to(dev)).float()
        tot += F.cross_entropy(lg.reshape(-1, lg.shape[-1]), tgt.to(dev).reshape(-1), ignore_index=-100, reduction="sum").item()
        n += (tgt != -100).sum().item()
    return tot / n, n


items = TR.tokenized(which)
ctx = 256 if which == "chord" else 512
va = TR.Data(which, items, True, ctx)
g3 = va.given
g2 = None
if which == "melody":
    g2 = np.zeros(len(T2.M_VOCAB), bool); g2[list(T2.M_GIVEN)] = True
out = {}
for name, srcs in (("옛 갈래 전체", OLD), ("재즈", {"wjazzd", "lmd_jazz", "irb"} | ({"ewld"} if which == "melody" else set())),
                   ("팝·노래", {"pop909", "lmd_pop", "lmd_song"} | (set() if which == "melody" else {"ewld"})), ("클래식", {"pdmx_classical"}),
                   ("ewld(옛 스탠더드 노래)", {"ewld"}), ("wjazzd(재즈 솔로)", {"wjazzd"}), ("lmd_jazz", {"lmd_jazz"}), ("pop909", {"pop909"}), ("irb", {"irb"})):
    if not any(va.by.get(k) for k in srcs):
        continue
    va.W = {k: w for k, w in (TR.CW if which == "chord" else TR.MW).items() if k in srcs and va.by.get(k)}
    rng = random.Random(77)
    seqs = [va.sample(rng)[0] for _ in range(32 * 20)]
    out[name] = seqs
models = {os.path.basename(os.path.dirname(p)): load(p) for p in sys.argv[2:]}
v2, ck2 = load(f"{ROOT}/runs/score_{which}_v2/best.pt")
print(f"{which} — 검증 손실 (낮을수록 좋음)")
print(f"  v2 큰 모델: 매개변수 {sum(p.numel() for p in v2.parameters()) / 1e6:.2f}M")
for nm, (m, ck) in models.items():
    print(f"  {nm}: 매개변수 {sum(p.numel() for p in m.parameters()) / 1e6:.2f}M (걸음 {ck['step']})")
for name, seqs in out.items():
    line = f"  [{name}] "
    if name != "클래식":
        if which == "melody":                              # v2 낱말로: 머리의 SRC(1) · CT(9) 를 빼고 번호 바꿈
            s2 = [MAP[np.concatenate([x[:1], x[2:9], x[10:]])] for x in seqs]
        else:
            s2 = [MAP[x] for x in seqs]
        assert all((x >= 0).all() for x in s2)
        l2, n2 = loss_of(v2, s2, g2, 3 if which == "chord" else 0)
        line += f"v2 {l2:.4f} · "
    for nm, (m, ck) in models.items():
        l3, n3 = loss_of(m, seqs, g3, 3 if which == "chord" else 0)
        line += f"{nm} {l3:.4f} · "
    print(line + f"(낱말 {n3})")
