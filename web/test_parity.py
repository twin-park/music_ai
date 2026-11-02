# JS 엔진 ↔ PyTorch 맞춰보기. 인자: 체크포인트(없으면 무작위 작은 모델) → web/test/ 에 기준값
import os, sys, json, subprocess
import numpy as np, torch
ROOT = "/home/drboom/project/car_bgm"
sys.path += [f"{ROOT}/music", f"{ROOT}/web"]
from model import MusicLM
from tokens import VOCAB
from train import Windows
import export_web
T = f"{ROOT}/web/test"; os.makedirs(T, exist_ok=True)
ck = sys.argv[1] if len(sys.argv) > 1 else None
if ck is None:
    torch.manual_seed(0)
    m = MusicLM(VOCAB, d=384, layers=8, heads=6, ctx=1024)
    ck = f"{T}/rand.pt"; torch.save({"model": m.state_dict(), "cfg": m.cfg}, ck)
export_web.main(ck, T)
c = torch.load(ck, map_location="cpu"); m = MusicLM(**c["cfg"]); m.load_state_dict(c["model"]); m.eval()
ds = Windows(1, 1024, seed=1, fixed=True); ds.setup()
x = None
rng = np.random.default_rng(1)
while x is None:
    s = ds.sample(rng); x = s if s is not None else None
seq = [int(t) for t in x[0][:300] if t != 0]
def run(model):
    with torch.no_grad():
        return model(torch.tensor([seq]))[0].float().numpy()
ref = run(m)
# int8 로 줄인 가중치를 다시 풀어 넣은 PyTorch (엔진 구현 오차만 보기 위함)
mq = MusicLM(**c["cfg"]); sd = {k: v.clone() for k, v in c["model"].items()}
for k, v in sd.items():
    if v.dim() == 2:
        s_ = v.abs().amax(1, keepdim=True) / 127.0 + 1e-12
        sd[k] = torch.clamp(torch.round(v / s_), -127, 127) * s_
mq.load_state_dict(sd); mq.eval(); refq = run(mq)
json.dump({"seq": seq, "pos": [10, 100, len(seq) - 1]}, open(f"{T}/seq.json", "w"))
np.save(f"{T}/refq.npy", refq[[10, 100, len(seq) - 1]])
r = subprocess.run(["node", f"{ROOT}/web/test_parity.js", T], capture_output=True, text=True)
print(r.stdout, r.stderr[-500:])
js = np.array(json.load(open(f"{T}/js_out.json"))["logits"])
for k, p in enumerate([10, 100, len(seq) - 1]):
    a, b, cq = ref[p], js[k], refq[p]
    sm = lambda z: np.exp(z - z.max()) / np.exp(z - z.max()).sum()
    kl = float((sm(a) * (np.log(sm(a) + 1e-12) - np.log(sm(b) + 1e-12))).sum())
    print(f"위치 {p}: JS↔int8풀린PyTorch 최대차 {np.abs(b - cq).max():.2e} · JS↔원래PyTorch 최대차 {np.abs(b - a).max():.3f} · 1등 같음 {a.argmax() == b.argmax()} · KL {kl:.5f}")
