// v2 생성기: 지휘자가 마디마다 코드 두 개(앞 반·뒤 반)를 정하고, 모델은 그 코드에 맞춰 음을 쓴다.
// 최근 마디와 똑같은 마디가 나오면 그 마디 처음으로 되감아 다시 쓴다 (KV 위치만 되돌림).
const NOTE = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"];
const PC = { C: 0, "C#": 1, Db: 1, D: 2, "D#": 3, Eb: 3, E: 4, F: 5, "F#": 6, Gb: 6, G: 7, "G#": 8, Ab: 8, A: 9, "A#": 10, Bb: 10, B: 11 };
const QMAP = { "": "maj", m: "min", "7": "7", maj7: "maj7", m7: "m7", m7b5: "m7b5", dim: "dim", sus: "sus", sus4: "sus",
               "7sus4": "sus", aug: "aug", "6": "maj", m6: "min", "9": "7", maj9: "maj7", m9: "m7", "7b9": "7" };
const QSHOW = { maj: "", min: "m", "7": "7", maj7: "maj7", m7: "m7", m7b5: "m7♭5", dim: "dim", sus: "sus", aug: "+" };

function parseChord(s) {
  s = s.split("/")[0];
  const r = s.length > 1 && (s[1] === "#" || s[1] === "b") ? s.slice(0, 2) : s.slice(0, 1);
  return { root: PC[r], q: QMAP[s.slice(r.length)] || "maj" };
}

function Conductor(spec, T, rand, nearKey) {
  this.spec = spec; this.T = T; this.rand = rand; this.k = 0; this.bars = []; this.pi = -1; this.made = 0;
  const ks = spec.keys;
  this.key = nearKey === undefined ? ks[0] : ks.reduce((a, b) => (dist(b, nearKey) < dist(a, nearKey) ? b : a));
}
function dist(a, b) { const d = Math.abs(a - b) % 12; return Math.min(d, 12 - d); }

Conductor.prototype.newProg = function () {
  const P = this.spec.progs;
  let i = Math.floor(this.rand() * P.length);
  if (P.length > 1 && i === this.pi) i = (i + 1) % P.length;
  this.pi = i; this.made++;
  if (this.made > 2 && this.rand() < 0.35) {                   // 가끔 가까운 조로
    const cand = this.spec.keys.filter((k) => k !== this.key);
    if (cand.length) this.key = cand.reduce((a, b) => (dist(b, this.key) < dist(a, this.key) ? b : a));
  }
  const off = (this.key - (this.spec.mode === "minor" ? 9 : 0) + 12) % 12;
  this.bars = P[i].split("|").map((bar) => {
    const cs = bar.trim().split(/\s+/).map(parseChord).map((c) => ({ root: (c.root + off) % 12, q: c.q }));
    return cs.length === 1 ? [cs[0], cs[0]] : [cs[0], cs[1]];
  });
  this.k = 0;
};
Conductor.prototype.next = function () {
  if (this.k >= this.bars.length) this.newProg();
  const pair = this.bars[this.k++];
  return { toks: pair.map((c) => this.T["CH_" + c.root + "_" + c.q]),
           label: pair[0] === pair[1] || (pair[0].root === pair[1].root && pair[0].q === pair[1].q)
             ? [NOTE[pair[0].root] + QSHOW[pair[0].q]] : pair.map((c) => NOTE[c.root] + QSHOW[c.q]) };
};

function Gen(engine, head, seed) {
  this.e = engine; this.head = head;
  const V = head.vocab, T = {};
  V.forEach((t, i) => (T[t] = i));
  this.T = T; this.V = V;
  this.BOS = T.BOS; this.EOS = T.EOS; this.SEP = T.SEP; this.BAR = T.BAR;
  this.CH0 = T["CH_0_maj"]; this.CHN = T.CH_NC;
  this.POS0 = T.POS_0; this.PROG0 = T.PROG_0; this.NV0 = T.NV_0; this.P0 = T.P_0; this.D0 = T.D_0;
  this.nD = head.durs.length;
  this.rand = mulberry(seed || 1);
  this.temp = 0.9; this.topP = 0.92;
  this.history = []; this.barIdx = 0; this.sigs = [];
  this.cand = new Int32Array(engine.V); this.prob = new Float32Array(engine.V);
  this.retries = 0; this.stats = { bars: 0, redo: 0 };
  this.progBias = new Float32Array(129); this.ban = new Set(); this.firstP = -1;
  // 편곡자: 쉬고 있는 악기군일수록 들어올 점수를 키움 (쉰 마디 × mixBonus, 최대 mixMax) → 악기가 들어왔다 빠졌다 하며 섞임
  this.mixBonus = 0.5; this.mixMax = 3.5; this.famNow = new Set(); this.famPrev = new Set(); this.famAgo = {}; this.nBars = 0;
}
function mulberry(a) { return function () { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a);
  t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }

Gen.prototype.barLenOf = function (conds) {
  for (const c of conds) if (c.startsWith("TS_") && c !== "TS_other") {
    const [a, b] = c.slice(3).split("/").map(Number); return a * 4 * this.head.Q / b;
  }
  return 48;
};
Gen.prototype.setSpec = function (spec) {
  if (spec.mix !== undefined) this.mixBonus = spec.mix;
  if (spec.mixMax !== undefined) this.mixMax = spec.mixMax;
  this.cond = new Conductor(spec, this.T, this.rand, this.cond ? this.cond.key : undefined);
  this.progBias.fill(0);                                       // 악기 섞기: 악기군별 가중치(로그 점수에 더함)
  for (const [fam, v] of Object.entries(spec.bias || {})) {
    const f = this.head.families.indexOf(fam);
    if (f === 16) this.progBias[128] = v; else if (f >= 0) for (let k = 0; k < 8; k++) this.progBias[f * 8 + k] = v;
  }
};
Gen.prototype.isCH = function (t) { return t >= this.CH0 && t <= this.CHN; };

Gen.prototype.start = function (conds, progs, keepUpTo) {
  this.conds = conds; this.barLen = this.barLenOf(conds);
  this.progOK = new Uint8Array(129);
  if (progs && progs.length) progs.forEach((p) => (this.progOK[p] = 1)); else this.progOK.fill(1);
  if (keepUpTo !== undefined) {
    this.history = this.history.filter((b) => b.idx <= keepUpTo);
    this.sigs = this.history.map((b) => b.sig);
  }
  let ctxT = [], used = 0;
  for (let k = this.history.length - 1; k >= 0 && k >= this.history.length - 3; k--) {
    const tk = this.history[k].toks;
    if (used + tk.length > 300) break;
    ctxT = tk.concat(ctxT); used += tk.length;
  }
  const pre = [this.BOS].concat(conds.map((c) => this.T[c]).filter((x) => x !== undefined), [this.SEP], ctxT, [this.BAR]);
  this.e.reset();
  let lg = null;
  for (const t of pre) lg = this.e.step(t);
  this.logits = lg; this.last = this.BAR; this.pos = -1; this.cur = null;
  this.barIdx = this.history.length ? this.history[this.history.length - 1].idx + 1 : 0;
  this.prefill = pre.length;
};

Gen.prototype.allowed = function () {
  const c = this.cand, L = this.last; let n = 0;
  const range = (lo, k) => { for (let i = 0; i < k; i++) c[n++] = lo + i; };
  const progs = () => { for (let p = 0; p < 129; p++) if (this.progOK[p]) c[n++] = this.PROG0 + p; };
  const poss = () => { for (let p = this.pos + 1; p < this.barLen; p++) c[n++] = this.POS0 + p; };
  if (L === this.BAR || this.isCH(L)) { poss(); c[n++] = this.BAR; c[n++] = this.EOS; }
  else if (L >= this.D0) { range(this.P0, 128); progs(); poss(); c[n++] = this.BAR; c[n++] = this.EOS; }
  else if (L >= this.P0) range(this.D0, this.nD);
  else if (L >= this.NV0) range(this.P0, 128);
  else if (L >= this.PROG0) range(this.NV0, 8);
  else if (L >= this.POS0) progs();
  else c[n++] = this.BAR;
  return n;
};

Gen.prototype.sample = function (temp) {
  const n = this.allowed(), c = this.cand, p = this.prob, lg = this.logits, T = temp || this.temp;
  const famOf = (p) => (p === 128 ? 16 : p >> 3);
  const rest = (f) => { if (this.famNow.has(f)) return 0; const a = this.famAgo[f] ?? this.nBars; return a < 1 ? 0 : Math.min(this.mixMax, this.mixBonus * a); };
  const bias = (t) => (t >= this.PROG0 && t < this.NV0 ? this.progBias[t - this.PROG0] + rest(famOf(t - this.PROG0)) : 0)
    + (this.firstP < 0 && this.curProg !== 128 && t >= this.P0 && t < this.D0 && this.ban.has(t) ? -1e9 : 0);   // 다시 쓸 땐 앞 시도의 첫 음(드럼 말고) 금지
  let mx = -Infinity;
  for (let i = 0; i < n; i++) { const v = lg[c[i]] + bias(c[i]); if (v > mx) mx = v; }
  const idx = []; let sum = 0;
  for (let i = 0; i < n; i++) { const e = Math.exp((lg[c[i]] + bias(c[i]) - mx) / T); p[i] = e; sum += e; idx.push(i); }
  idx.sort((a, b) => p[b] - p[a]);
  let acc = 0, cut = idx.length;
  for (let k = 0; k < idx.length; k++) { acc += p[idx[k]] / sum; if (acc - p[idx[k]] / sum > this.topP) { cut = k; break; } }
  let tot = 0; for (let k = 0; k < cut; k++) tot += p[idx[k]];
  let r = this.rand() * tot;
  for (let k = 0; k < cut; k++) { r -= p[idx[k]]; if (r <= 0) return c[idx[k]]; }
  return c[idx[cut - 1]];
};

Gen.prototype.feed = function (t) {
  if (t >= this.POS0 && t < this.PROG0) this.pos = t - this.POS0;
  if (t >= this.PROG0 && t < this.NV0) { this.curProg = t - this.PROG0; this.famNow.add(this.curProg === 128 ? 16 : this.curProg >> 3); }
  if (t === this.BAR || this.isCH(t)) this.pos = -1;
  this.last = t; this.logits = this.e.step(t);
};

Gen.prototype.beginBar = function () {                          // BAR 는 이미 들어간 상태 → 코드 두 개 넣고 되감기 지점 저장
  const ch = this.cond.next();
  for (const t of ch.toks) this.feed(t);
  this.cur = [this.BAR, ch.toks[0], ch.toks[1]]; this.curLabel = ch.label;
  for (const f in this.famAgo) this.famAgo[f]++;
  for (const f of this.famNow) this.famAgo[f] = 0;
  this.nBars++; this.famPrev = this.famNow; this.famNow = new Set();
  this.save = { pos: this.e.pos, logits: Float32Array.from(this.logits) };
  this.retries = 0; this.ban.clear(); this.firstP = -1;
};
Gen.prototype.rewind = function () {
  this.e.pos = this.save.pos; this.logits = Float32Array.from(this.save.logits);
  this.last = this.cur[2]; this.pos = -1; this.cur = this.cur.slice(0, 3);
  if (this.firstP >= 0) this.ban.add(this.firstP); this.firstP = -1; this.famNow = new Set();
  this.retries++; this.stats.redo++;
};

Gen.prototype.stepBar = function (maxTok) {
  if (!this.cur) {
    if (this.e.pos > Math.min(this.e.ctx - 320, 640)) this.start(this.conds, this.progs(), undefined);   // 문맥이 길면 느려지니 앞 마디로 새로
    this.beginBar();
  }
  const toks = this.cur;
  for (let k = 0; k < maxTok; k++) {
    if (this.e.pos >= this.e.ctx - 2) { const bar = this.finish(toks); this.start(this.conds, this.progs(), undefined); return bar; }
    const t = this.sample(this.temp + Math.min(0.3, 0.08 * this.retries));     // 다시 쓸수록 조금 모험적으로 (너무 들뜨지 않게 +0.3 까지)
    if (t === this.BAR || t === this.EOS || toks.length > 600) {
      const sig = this.sigOf(toks);
      const dup = this.sigs.includes(sig), mono = !dup && this.monoOf(toks) >= 0.75;
      if (this.retries < 6 && (dup || mono)) { if (mono) this.stats.mono = (this.stats.mono || 0) + 1; this.rewind(); continue; }   // 똑같은 마디·같은 음 두드리기 → 다시 (첫 음을 바꿔서)
      const bar = this.finish(toks, sig);
      if (t === this.EOS) this.start(this.conds, this.progs(), undefined); else this.feed(this.BAR);
      return bar;
    }
    if (this.firstP < 0 && t >= this.P0 && t < this.D0 && this.curProg !== 128) this.firstP = t;
    this.feed(t); toks.push(t);
  }
  return null;
};

Gen.prototype.progs = function () { const out = []; for (let p = 0; p < 129; p++) if (this.progOK[p]) out.push(p); return out; };
// 한 마디 안 선율 악기의 '같은 음 되풀이' 비율 (악기마다 재서 가장 심한 것, 4번 이상 친 악기만). 드럼·베이스·기타/오르간 반주는 뺌
Gen.prototype.monoOf = function (toks) {
  const by = {};
  for (const [pos, p, pitch] of this.notesOf(toks)) {
    if (p === 128 || (p >= 16 && p < 40)) continue;
    const m = (by[p] = by[p] || {}); m[pos] = Math.max(m[pos] ?? -1, pitch);
  }
  let worst = 0;
  for (const m of Object.values(by)) {
    const ks = Object.keys(m).map(Number).sort((a, b) => a - b); if (ks.length < 4) continue;
    let rep = 0; for (let i = 1; i < ks.length; i++) rep += m[ks[i]] === m[ks[i - 1]];
    worst = Math.max(worst, rep / (ks.length - 1));
  }
  return worst;
};
Gen.prototype.notesOf = function (toks) {
  const notes = []; let pos = 0, prog = 0, vel = 64, pitch = -1;
  for (const t of toks) {
    if (t >= this.D0) { if (pitch >= 0) notes.push([pos, prog, pitch, this.head.durs[t - this.D0], vel]); pitch = -1; }
    else if (t >= this.P0) pitch = t - this.P0;
    else if (t >= this.NV0) vel = (t - this.NV0) * 16 + 8;
    else if (t >= this.PROG0) prog = t - this.PROG0;
    else if (t >= this.POS0) pos = t - this.POS0;
  }
  return notes;
};
Gen.prototype.sigOf = function (toks) {
  return this.notesOf(toks).filter((n) => n[1] !== 128).map((n) => n[0] + "." + n[1] + "." + n[2]).join(",") || "∅" + this.barIdx;
};
Gen.prototype.finish = function (toks, sig) {
  const bar = { idx: this.barIdx++, toks, notes: this.notesOf(toks), barLen: this.barLen, chords: this.curLabel };
  sig = sig || this.sigOf(toks);
  this.history.push({ idx: bar.idx, toks, sig }); this.sigs.push(sig);
  if (this.history.length > 24) this.history.shift();
  if (this.sigs.length > 24) this.sigs.shift();
  this.cur = null; this.stats.bars++;
  return bar;
};

if (typeof module !== "undefined") module.exports = { Gen, Conductor, parseChord };
