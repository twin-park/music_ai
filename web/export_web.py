# 음악 모델 → 브라우저용 가중치 (선형층·임베딩은 줄마다 int8 + float32 배율, 정규화는 float32)
# 결과: web/build/model.bin, web/build/model.json
import os, sys, json
import numpy as np, torch
ROOT = "/home/drboom/project/car_bgm"
sys.path.insert(0, f"{ROOT}/music")
from tokens import V, DURS, Q, MAX_BAR, TEMPO_EDGES, DENS_EDGES, POLY_EDGES, REG_EDGES, VEL_EDGES, FAMILIES

OUT = f"{ROOT}/web/build"


def main(ckpt, out=OUT):
    os.makedirs(out, exist_ok=True)
    ck = torch.load(ckpt, map_location="cpu")
    sd = {k: v.float().numpy() for k, v in ck["model"].items()}
    cfg = ck["cfg"]
    blob, tensors = bytearray(), {}

    def put(arr):
        while len(blob) % 4:
            blob.append(0)
        off = len(blob); blob.extend(arr.tobytes()); return off

    def q8(name, w):
        s = np.abs(w).max(1) / 127.0 + 1e-12
        q = np.clip(np.round(w / s[:, None]), -127, 127).astype(np.int8)
        tensors[name] = {"kind": "q8", "shape": list(w.shape), "q": put(q), "s": put(s.astype(np.float32))}

    def f32(name, w):
        tensors[name] = {"kind": "f32", "shape": list(w.shape), "off": put(w.astype(np.float32))}

    q8("emb", sd["emb.weight"])
    for i in range(cfg["layers"]):
        p = f"layers.{i}."
        f32(p + "n1", sd[p + "n1.weight"]); f32(p + "n2", sd[p + "n2.weight"])
        for k in ("qkv", "o", "w12", "w3"):
            q8(p + k, sd[p + k + ".weight"])
    f32("norm", sd["norm.weight"])
    head = {"cfg": cfg, "tensors": tensors, "vocab": V, "durs": DURS, "Q": Q, "max_bar": MAX_BAR,
            "edges": {"TEMPO": TEMPO_EDGES, "DENS": DENS_EDGES, "POLY": POLY_EDGES, "REG": REG_EDGES, "VEL": VEL_EDGES},
            "families": FAMILIES, "step": ck.get("step"), "val": ck.get("val"), "eps": float(np.finfo(np.float32).eps)}
    open(f"{out}/model.bin", "wb").write(bytes(blob))
    json.dump(head, open(f"{out}/model.json", "w"), ensure_ascii=False)
    print(f"{ckpt} → model.bin {len(blob) / 1e6:.1f}MB · step {ck.get('step')} val {ck.get('val')}")


if __name__ == "__main__":
    main(sys.argv[1], *(sys.argv[2:3]))
