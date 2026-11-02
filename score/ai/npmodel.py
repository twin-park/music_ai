# numpy 판 MusicLM (윈도우 묶음용 · torch 없이) — music/model.py 와 같은 셈: RMSNorm · RoPE(짝 섞기) · SwiGLU · 가중치 묶음
#   python npmodel.py export      → runs/score_{chord,melody}/best.npz  (torch 로 학습한 best.pt 에서 뽑기)
import os, sys
import numpy as np

EPS = float(np.finfo(np.float32).eps)          # nn.RMSNorm(eps=None) 과 같음


def rms(x, w):
    return x / np.sqrt((x * x).mean(-1, keepdims=True) + EPS) * w


def rope(x, cos, sin):
    x1, x2 = x[..., ::2], x[..., 1::2]
    out = np.empty_like(x)
    out[..., ::2] = x1 * cos - x2 * sin
    out[..., 1::2] = x1 * sin + x2 * cos
    return out


class NpLM:
    TOPLEFT = False        # True = 10-31 까지의 생성 버그 재현(여러 낱말을 캐시 뒤에 넣을 때 앞 문맥을 못 봄) — 비교용

    def __init__(self, path):
        z = np.load(path)
        c = {k[4:]: int(z[k]) for k in z.files if k.startswith("cfg_")}
        self.cfg = c
        g = lambda k: np.ascontiguousarray(z[k].astype(np.float32))
        self.emb = g("emb.weight")
        self.norm = g("norm.weight")
        self.layers = []
        for i in range(c["layers"]):
            p = f"layers.{i}."
            self.layers.append(dict(n1=g(p + "n1.weight"), qkv=g(p + "qkv.weight").T.copy(), o=g(p + "o.weight").T.copy(),
                                    n2=g(p + "n2.weight"), w12=g(p + "w12.weight").T.copy(), w3=g(p + "w3.weight").T.copy()))
        d, h = c["d"], c["heads"]
        self.h, self.hd = h, d // h
        inv = 1.0 / (10000 ** (np.arange(0, self.hd, 2, dtype=np.float32) / self.hd))
        f = np.outer(np.arange(c["ctx"] * 2, dtype=np.float32), inv)
        self.cos, self.sin = np.cos(f).astype(np.float32), np.sin(f).astype(np.float32)

    def step(self, ids, caches, pos):
        """ids 를 pos 자리부터 넣고 마지막 낱말 다음의 점수(어휘 크기) 를 돌려줌. caches: 층마다 dict(max=…)"""
        T = len(ids)
        H, hd = self.h, self.hd
        x = self.emb[np.asarray(ids)]
        cos, sin = self.cos[pos:pos + T], self.sin[pos:pos + T]
        S = pos + T
        mask = np.where(np.arange(S)[None, :] <= (0 if self.TOPLEFT else pos) + np.arange(T)[:, None], 0.0, -np.inf).astype(np.float32) if T > 1 else None
        for L, cache in zip(self.layers, caches):
            qkv = (rms(x, L["n1"]) @ L["qkv"]).reshape(T, 3, H, hd).transpose(1, 2, 0, 3)     # 3,H,T,hd
            q, k, v = rope(qkv[0], cos, sin), rope(qkv[1], cos, sin), qkv[2]
            if "k" not in cache:
                cache["k"] = np.zeros((H, cache["max"], hd), np.float32)
                cache["v"] = np.zeros((H, cache["max"], hd), np.float32)
            cache["k"][:, pos:S] = k
            cache["v"][:, pos:S] = v
            K, V = cache["k"][:, :S], cache["v"][:, :S]
            att = (q @ K.transpose(0, 2, 1)) * (1.0 / np.sqrt(hd))                             # H,T,S
            if mask is not None:
                att = att + mask
            att = np.exp(att - att.max(-1, keepdims=True))
            att /= att.sum(-1, keepdims=True)
            a = (att @ V).transpose(1, 0, 2).reshape(T, H * hd)
            x = x + a @ L["o"]
            ab = rms(x, L["n2"]) @ L["w12"]
            f = ab.shape[-1] // 2
            a1, b1 = ab[:, :f], ab[:, f:]
            x = x + (a1 / (1 + np.exp(-a1)) * b1) @ L["w3"]
        return rms(x[-1], self.norm) @ self.emb.T


def export(runs):
    import torch
    for which in ("chord", "melody"):
        ck = torch.load(f"{runs}/score_{which}/best.pt", map_location="cpu")
        sd = {k: v.float().numpy() for k, v in ck["model"].items() if not k.startswith("head.")}
        cfg = {f"cfg_{k}": np.array(int(v)) for k, v in ck["cfg"].items() if k != "drop"}
        out = f"{runs}/score_{which}/best.npz"
        np.savez(out, **sd, **cfg)
        print("→", out, f"{sum(v.size for v in sd.values()) / 1e6:.2f}M", ck["cfg"])


if __name__ == "__main__" and sys.argv[1:] == ["export"]:
    export(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "runs"))
