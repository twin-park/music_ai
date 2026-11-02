// 마디 단위 생성기: 조건 → (문법 막기 + top-p 뽑기) → 한 마디씩 음표로.
// 조건을 바꾸면 앞 마디 몇 개를 실마리로 다시 시작해 곡이 끊기지 않고 넘어간다.
function Gen(engine, head, seed) {
  this.e = engine; this.head = head;
  const V = head.vocab, T = {};
  V.forEach((t, i) => (T[t] = i));
  this.T = T; this.V = V;
  this.BOS = T.BOS; this.EOS = T.EOS; this.SEP = T.SEP; this.BAR = T.BAR;
  this.POS0 = T.POS_0; this.PROG0 = T.PROG_0; this.NV0 = T.NV_0; this.P0 = T.P_0; this.D0 = T.D_0;
  this.nD = head.durs.length; this.maxBar = head.max_bar;
  this.rand = mulberry(seed || 1);
  this.temp = 1.0; this.topP = 0.95;
  this.history = [];            // 지금까지 만든 마디들 [{idx, toks}]
  this.barIdx = 0;
  this.cand = new Int32Array(engine.V); this.prob = new Float32Array(engine.V);
}

function mulberry(a) { return function () { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a);
  t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }

Gen.prototype.barLenOf = function (conds) {
  for (const c of conds) if (c.startsWith("TS_") && c !== "TS_other") {
    const [a, b] = c.slice(3).split("/").map(Number); return a * 4 * this.head.Q / b;
  }
  return 48;
};

// 조건을 정하고 실마리(앞 마디들)로 처음부터 다시 채움. 끝나면 BAR 를 하나 넣어 새 마디 시작 상태.
Gen.prototype.start = function (conds, progs, keepUpTo) {
  this.conds = conds; this.barLen = this.barLenOf(conds);
  this.progOK = new Uint8Array(129);
  if (progs && progs.length) progs.forEach((p) => (this.progOK[p] = 1)); else this.progOK.fill(1);
  if (keepUpTo !== undefined) this.history = this.history.filter((b) => b.idx <= keepUpTo);
  // 실마리: 마지막 3마디, 300 낱말 이하
  let ctxT = [], used = 0;
  for (let k = this.history.length - 1; k >= 0 && k >= this.history.length - 3; k--) {
    const tk = this.history[k].toks;
    if (used + tk.length > 300) break;
    ctxT = tk.concat(ctxT); used += tk.length;
  }
  const pre = [this.BOS].concat(conds.map((c) => this.T[c]), [this.SEP], ctxT, [this.BAR]);
  this.e.reset();
  let lg = null;
  for (const t of pre) lg = this.e.step(t);
  this.logits = lg; this.last = this.BAR; this.pos = -1; this.cur = null;
  this.barIdx = this.history.length ? this.history[this.history.length - 1].idx + 1 : 0;
  this.prefill = pre.length;
};

// 문법상 다음에 올 수 있는 낱말 목록을 cand 에 채우고 개수를 돌려준다
Gen.prototype.allowed = function () {
  const c = this.cand, L = this.last; let n = 0;
  const range = (lo, k) => { for (let i = 0; i < k; i++) c[n++] = lo + i; };
  const progs = () => { for (let p = 0; p < 129; p++) if (this.progOK[p]) c[n++] = this.PROG0 + p; };
  const poss = () => { for (let p = this.pos + 1; p < this.barLen; p++) c[n++] = this.POS0 + p; };
  if (L === this.BAR) { poss(); c[n++] = this.BAR; c[n++] = this.EOS; }
  else if (L >= this.D0) { range(this.P0, 128); progs(); poss(); c[n++] = this.BAR; c[n++] = this.EOS; }
  else if (L >= this.P0) range(this.D0, this.nD);
  else if (L >= this.NV0) range(this.P0, 128);
  else if (L >= this.PROG0) range(this.NV0, 8);
  else if (L >= this.POS0) progs();
  else c[n++] = this.BAR;
  return n;
};

Gen.prototype.sample = function () {
  const n = this.allowed(), c = this.cand, p = this.prob, lg = this.logits, T = this.temp;
  let mx = -Infinity;
  for (let i = 0; i < n; i++) if (lg[c[i]] > mx) mx = lg[c[i]];
  const idx = [];
  let sum = 0;
  for (let i = 0; i < n; i++) { const e = Math.exp((lg[c[i]] - mx) / T); p[i] = e; sum += e; idx.push(i); }
  idx.sort((a, b) => p[b] - p[a]);
  let acc = 0, cut = idx.length;
  for (let k = 0; k < idx.length; k++) { acc += p[idx[k]] / sum; if (acc - p[idx[k]] / sum > this.topP) { cut = k; break; } }
  let tot = 0;
  for (let k = 0; k < cut; k++) tot += p[idx[k]];
  let r = this.rand() * tot;
  for (let k = 0; k < cut; k++) { r -= p[idx[k]]; if (r <= 0) return c[idx[k]]; }
  return c[idx[cut - 1]];
};

Gen.prototype.feed = function (t) {
  if (t >= this.POS0 && t < this.PROG0) this.pos = t - this.POS0;
  if (t === this.BAR) this.pos = -1;
  this.last = t;
  this.logits = this.e.step(t);
};

// 조금씩 만들기: 낱말 maxTok 개까지 진행, 마디가 끝나면 그 마디를, 아니면 null (중간에 조건 바꾸기 받으려고)
Gen.prototype.stepBar = function (maxTok) {
  if (!this.cur) {
    if (this.e.pos > this.e.ctx - 320) this.start(this.conds, this.progs(), undefined);
    this.cur = [this.BAR];
  }
  const toks = this.cur;
  for (let k = 0; k < maxTok; k++) {
    if (this.e.pos >= this.e.ctx - 2) {          // 마디 도중 문맥이 다 차면 여기서 마디를 닫고 새로 시작
      const bar = this.finish(toks); this.cur = null; this.start(this.conds, this.progs(), undefined); return bar;
    }
    const t = this.sample();
    if (t === this.EOS) { const bar = this.finish(toks); this.cur = null; this.start(this.conds, this.progs(), undefined); return bar; }
    this.feed(t);
    if (t === this.BAR) { this.cur = null; return this.finish(toks); }
    toks.push(t);
    if (toks.length > 600) { this.feed(this.BAR); this.cur = null; return this.finish(toks); }
  }
  return null;
};

// 한 마디 만들기 → {idx, toks, notes:[[pos, prog, pitch, durTick, vel]], barLen}
Gen.prototype.nextBar = function () {
  if (this.e.pos > this.e.ctx - 160) this.start(this.conds, this.progs(), undefined);   // 문맥 다 차면 앞 마디로 새로 시작
  const toks = [this.BAR];
  for (let guard = 0; guard < 600; guard++) {
    const t = this.sample();
    if (t === this.EOS) {                       // 곡이 끝났다고 하면 같은 조건으로 이어 쓰기
      const bar = this.finish(toks);
      this.start(this.conds, this.progs(), undefined);
      return bar;
    }
    this.feed(t);
    if (t === this.BAR) return this.finish(toks);
    toks.push(t);
  }
  this.feed(this.BAR);                          // 한 마디가 너무 길면 끊는다
  return this.finish(toks);
};

Gen.prototype.progs = function () { const out = []; for (let p = 0; p < 129; p++) if (this.progOK[p]) out.push(p); return out; };

Gen.prototype.finish = function (toks) {
  const notes = []; let pos = 0, prog = 0, vel = 64, pitch = -1;
  for (const t of toks) {
    if (t >= this.D0) { if (pitch >= 0) notes.push([pos, prog, pitch, this.head.durs[t - this.D0], vel]); pitch = -1; }
    else if (t >= this.P0) pitch = t - this.P0;
    else if (t >= this.NV0) vel = (t - this.NV0) * 16 + 8;
    else if (t >= this.PROG0) prog = t - this.PROG0;
    else if (t >= this.POS0) pos = t - this.POS0;
  }
  const bar = { idx: this.barIdx++, toks, notes, barLen: this.barLen };
  this.history.push({ idx: bar.idx, toks });
  if (this.history.length > 16) this.history.shift();
  return bar;
};

if (typeof module !== "undefined") module.exports = { Gen };
