# 음악 모델: 악보 낱말을 하나씩 이어 쓰는 디코더 (RoPE · SwiGLU · 가중치 묶음)
import math
import torch
import torch.nn as nn
import torch.nn.functional as F


def rope(x, cos, sin):
    x1, x2 = x[..., ::2], x[..., 1::2]
    return torch.stack([x1 * cos - x2 * sin, x1 * sin + x2 * cos], -1).flatten(-2)


class Layer(nn.Module):
    def __init__(self, d, h, drop):
        super().__init__()
        self.h = h
        self.n1 = nn.RMSNorm(d)
        self.qkv = nn.Linear(d, 3 * d, bias=False)
        self.o = nn.Linear(d, d, bias=False)
        self.n2 = nn.RMSNorm(d)
        f = int(d * 8 / 3 / 64 + 0.999) * 64
        self.w12 = nn.Linear(d, 2 * f, bias=False)
        self.w3 = nn.Linear(f, d, bias=False)
        self.drop = drop

    def forward(self, x, cos, sin, cache=None, pos=0):
        B, T, D = x.shape
        q, k, v = self.qkv(self.n1(x)).view(B, T, 3, self.h, D // self.h).permute(2, 0, 3, 1, 4)
        q, k = rope(q, cos, sin), rope(k, cos, sin)
        if cache is not None:      # 미리 잡아 둔 KV 칸에 써 넣기 (이어 붙이기 복사 없음)
            if "k" not in cache:
                cache["k"] = k.new_zeros(B, self.h, cache["max"], D // self.h)
                cache["v"] = torch.zeros_like(cache["k"])
            cache["k"][:, :, pos:pos + T] = k
            cache["v"][:, :, pos:pos + T] = v
            k, v = cache["k"][:, :, :pos + T], cache["v"][:, :, :pos + T]
        if cache is not None and pos > 0 and T > 1:
            # 캐시 뒤에 여러 낱말을 한 번에 넣을 때: is_causal 은 왼쪽 위 기준이라 앞 문맥을 못 봄 → 오른쪽 아래 기준 마스크
            mask = torch.ones(T, pos + T, dtype=torch.bool, device=x.device).tril(pos)
            a = F.scaled_dot_product_attention(q, k, v, attn_mask=mask)
        else:
            a = F.scaled_dot_product_attention(q, k, v, is_causal=T > 1,
                                               dropout_p=self.drop if self.training else 0.0)
        x = x + F.dropout(self.o(a.transpose(1, 2).reshape(B, T, D)), self.drop, self.training)
        a, b = self.w12(self.n2(x)).chunk(2, -1)
        return x + F.dropout(self.w3(F.silu(a) * b), self.drop, self.training)


class MusicLM(nn.Module):
    def __init__(self, vocab, d=768, layers=12, heads=12, ctx=2048, drop=0.1):
        super().__init__()
        self.cfg = dict(vocab=vocab, d=d, layers=layers, heads=heads, ctx=ctx, drop=drop)
        self.emb = nn.Embedding(vocab, d)
        self.layers = nn.ModuleList(Layer(d, heads, drop) for _ in range(layers))
        self.norm = nn.RMSNorm(d)
        self.head = nn.Linear(d, vocab, bias=False)
        self.head.weight = self.emb.weight
        hd = d // heads
        inv = 1.0 / (10000 ** (torch.arange(0, hd, 2).float() / hd))
        t = torch.arange(ctx * 2).float()
        f = torch.outer(t, inv)
        self.register_buffer("cos", f.cos()[None, None], persistent=False)
        self.register_buffer("sin", f.sin()[None, None], persistent=False)
        self.apply(self._init)
        for l in self.layers:
            nn.init.normal_(l.o.weight, std=0.02 / math.sqrt(2 * layers))
            nn.init.normal_(l.w3.weight, std=0.02 / math.sqrt(2 * layers))

    @staticmethod
    def _init(m):
        if isinstance(m, (nn.Linear, nn.Embedding)):
            nn.init.normal_(m.weight, std=0.02)

    def forward(self, idx, caches=None, pos=0):
        T = idx.shape[1]
        cos, sin = self.cos[:, :, pos:pos + T], self.sin[:, :, pos:pos + T]
        x = self.emb(idx)
        for i, l in enumerate(self.layers):
            x = l(x, cos, sin, None if caches is None else caches[i], pos)
        return self.head(self.norm(x))
