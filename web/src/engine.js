// 음악 모델 계산기 (브라우저·Node 공용). PyTorch music/model.py 와 같은 계산을 int8 가중치로 한다.
// 낱말 하나 넣으면 다음 낱말 점수(logits)를 돌려준다. KV 캐시를 들고 있어 한 번에 한 낱말씩.
function Engine(head, buf) {
  const c = head.cfg;
  this.d = c.d; this.L = c.layers; this.H = c.heads; this.hd = c.d / c.heads; this.ctx = c.ctx;
  this.V = c.vocab; this.eps = head.eps;
  this.f = Math.ceil(c.d * 8 / 3 / 64 - 1e-9) * 64;
  const T = head.tensors;
  const q8 = (n) => ({ q: new Int8Array(buf, T[n].q, T[n].shape[0] * T[n].shape[1]),
                       s: new Float32Array(buf, T[n].s, T[n].shape[0]), rows: T[n].shape[0], cols: T[n].shape[1] });
  const f32 = (n) => new Float32Array(buf, T[n].off, T[n].shape.reduce((a, b) => a * b, 1));
  this.emb = q8("emb"); this.norm = f32("norm");
  this.layers = [];
  for (let i = 0; i < this.L; i++) {
    const p = "layers." + i + ".";
    this.layers.push({ n1: f32(p + "n1"), n2: f32(p + "n2"), qkv: q8(p + "qkv"), o: q8(p + "o"),
                       w12: q8(p + "w12"), w3: q8(p + "w3") });
  }
  const maxT = this.ctx;
  this.K = new Float32Array(this.L * maxT * this.d);
  this.Vc = new Float32Array(this.L * maxT * this.d);
  // RoPE 표
  const half = this.hd / 2;
  this.cos = new Float32Array(maxT * half); this.sin = new Float32Array(maxT * half);
  for (let t = 0; t < maxT; t++) for (let i = 0; i < half; i++) {
    const inv = 1 / Math.pow(10000, (2 * i) / this.hd);
    const a = Math.fround(Math.fround(t) * Math.fround(inv));
    this.cos[t * half + i] = Math.cos(a); this.sin[t * half + i] = Math.sin(a);
  }
  const d = this.d, f = this.f;
  this.x = new Float32Array(d); this.h = new Float32Array(d); this.qkvb = new Float32Array(3 * d);
  this.att = new Float32Array(d); this.tmp = new Float32Array(d); this.u = new Float32Array(2 * f);
  this.g = new Float32Array(f); this.sc = new Float32Array(maxT); this.logits = new Float32Array(this.V);
  this.pos = 0;
}

// out = W·x  (W: int8 줄마다 배율)
function matvec(W, x, out) {
  const q = W.q, s = W.s, n = W.cols;
  for (let r = 0, base = 0; r < W.rows; r++, base += n) {
    let a0 = 0, a1 = 0, a2 = 0, a3 = 0, c = 0;
    for (; c + 3 < n; c += 4) {
      a0 += q[base + c] * x[c]; a1 += q[base + c + 1] * x[c + 1];
      a2 += q[base + c + 2] * x[c + 2]; a3 += q[base + c + 3] * x[c + 3];
    }
    for (; c < n; c++) a0 += q[base + c] * x[c];
    out[r] = (a0 + a1 + a2 + a3) * s[r];
  }
}

Engine.prototype.rms = function (x, w, out) {
  let ss = 0;
  for (let i = 0; i < this.d; i++) ss += x[i] * x[i];
  const k = 1 / Math.sqrt(ss / this.d + this.eps);
  for (let i = 0; i < this.d; i++) out[i] = x[i] * k * w[i];
};

Engine.prototype.reset = function () { this.pos = 0; };

Engine.prototype.step = function (tok) {
  const d = this.d, H = this.H, hd = this.hd, half = hd / 2, f = this.f, t = this.pos;
  if (t >= this.ctx) throw new Error("문맥 넘침");
  const E = this.emb, x = this.x;
  for (let i = 0, b = tok * d; i < d; i++) x[i] = E.q[b + i] * E.s[tok];
  const cos = this.cos, sin = this.sin, scale = 1 / Math.sqrt(hd);
  for (let l = 0; l < this.L; l++) {
    const Ly = this.layers[l], qkv = this.qkvb;
    this.rms(x, Ly.n1, this.h);
    matvec(Ly.qkv, this.h, qkv);
    // RoPE: 머리마다 (짝, 홀) 쌍
    for (let h = 0; h < H; h++) {
      for (let part = 0; part < 2; part++) {
        const o = part * d + h * hd;
        for (let i = 0; i < half; i++) {
          const x1 = qkv[o + 2 * i], x2 = qkv[o + 2 * i + 1];
          const cc = cos[t * half + i], ss = sin[t * half + i];
          qkv[o + 2 * i] = x1 * cc - x2 * ss; qkv[o + 2 * i + 1] = x1 * ss + x2 * cc;
        }
      }
    }
    const Kl = this.K, Vl = this.Vc, lo = l * this.ctx * d;
    Kl.set(qkv.subarray(d, 2 * d), lo + t * d);
    Vl.set(qkv.subarray(2 * d, 3 * d), lo + t * d);
    const att = this.att, sc = this.sc;
    for (let h = 0; h < H; h++) {
      const qo = h * hd;
      let mx = -Infinity;
      for (let j = 0; j <= t; j++) {
        const ko = lo + j * d + qo;
        let s = 0;
        for (let i = 0; i < hd; i++) s += qkv[qo + i] * Kl[ko + i];
        s *= scale; sc[j] = s; if (s > mx) mx = s;
      }
      let sum = 0;
      for (let j = 0; j <= t; j++) { const e = Math.exp(sc[j] - mx); sc[j] = e; sum += e; }
      for (let i = 0; i < hd; i++) att[qo + i] = 0;
      for (let j = 0; j <= t; j++) {
        const p = sc[j] / sum, vo = lo + j * d + qo;
        for (let i = 0; i < hd; i++) att[qo + i] += p * Vl[vo + i];
      }
    }
    matvec(Ly.o, att, this.tmp);
    for (let i = 0; i < d; i++) x[i] += this.tmp[i];
    this.rms(x, Ly.n2, this.h);
    matvec(Ly.w12, this.h, this.u);
    const u = this.u, g = this.g;
    for (let i = 0; i < f; i++) { const a = u[i]; g[i] = a / (1 + Math.exp(-a)) * u[f + i]; }
    matvec(Ly.w3, g, this.tmp);
    for (let i = 0; i < d; i++) x[i] += this.tmp[i];
  }
  this.rms(x, this.norm, this.h);
  matvec(this.emb, this.h, this.logits);
  this.pos++;
  return this.logits;
};

// WebAssembly SIMD 판 — 같은 겉모양(reset/step/pos/ctx/V). 안 되면 위 JS 판을 쓴다.
function EngineWasm(head, buf, wasmBytes) {
  const c = head.cfg, d = c.d, L = c.layers, ctx = c.ctx, V = c.vocab, H = c.heads, hd = d / H, half = hd / 2;
  const f = Math.ceil(d * 8 / 3 / 64 - 1e-9) * 64;
  this.d = d; this.ctx = ctx; this.V = V; this.pos = 0;
  const inst = new WebAssembly.Instance(new WebAssembly.Module(wasmBytes), {});
  if (inst.exports._initialize) inst.exports._initialize();
  const mem = inst.exports.memory;
  const al = (n) => (n + 15) & ~15;
  let p = al(inst.exports.__heap_base.value);
  const wBase = p; p = al(p + buf.byteLength);
  const take = (bytes) => { const o = p; p = al(p + bytes); return o; };
  const K = take(L * ctx * d * 4), Vc = take(L * ctx * d * 4), cos = take(ctx * half * 4), sin = take(ctx * half * 4);
  const x = take(d * 4), h = take(d * 4), qkv = take(3 * d * 4), att = take(d * 4), tmp = take(d * 4);
  const u = take(2 * f * 4), g = take(f * 4), sc = take(ctx * 4), lg = take(V * 4), cfgP = take(4 * (10 + 10 * L + 13));
  const need = Math.ceil(p / 65536) - mem.buffer.byteLength / 65536;
  if (need > 0) mem.grow(need);
  new Uint8Array(mem.buffer, wBase, buf.byteLength).set(new Uint8Array(buf));
  const cs = new Float32Array(mem.buffer, cos, ctx * half), sn = new Float32Array(mem.buffer, sin, ctx * half);
  for (let t = 0; t < ctx; t++) for (let i = 0; i < half; i++) {
    const a = Math.fround(Math.fround(t) * Math.fround(1 / Math.pow(10000, (2 * i) / hd)));
    cs[t * half + i] = Math.cos(a); sn[t * half + i] = Math.sin(a);
  }
  const T = head.tensors, cfg = new Int32Array(mem.buffer, cfgP, 10 + 10 * L + 13);
  const epsBits = new Int32Array(new Float32Array([head.eps]).buffer)[0];
  const arr = [d, L, H, ctx, V, f, epsBits, wBase + T.emb.q, wBase + T.emb.s, wBase + T.norm.off];
  for (let i = 0; i < L; i++) {
    const pfx = "layers." + i + ".";
    arr.push(wBase + T[pfx + "n1"].off, wBase + T[pfx + "n2"].off);
    for (const k of ["qkv", "o", "w12", "w3"]) arr.push(wBase + T[pfx + k].q, wBase + T[pfx + k].s);
  }
  arr.push(K, Vc, cos, sin, x, h, qkv, att, tmp, u, g, sc, lg);
  cfg.set(arr);
  inst.exports.init(cfgP);
  this.ex = inst.exports;
  this.logits = new Float32Array(mem.buffer, lg, V);
}
EngineWasm.prototype.reset = function () { this.pos = 0; };
EngineWasm.prototype.step = function (tok) {
  if (this.pos >= this.ctx) throw new Error("문맥 넘침");
  this.ex.step(tok, this.pos++);
  return this.logits;
};

if (typeof module !== "undefined") module.exports = { Engine, EngineWasm };
