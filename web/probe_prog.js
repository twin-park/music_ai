// node probe_prog.js <모델폴더> <재즈|오케> <상황번호> : 첫 마디들에서 악기(PROG) 고를 때 모델이 매기는 확률 보기
const fs = require("fs"), path = require("path");
const { EngineWasm } = require("./src/engine.js");
const { Gen } = require("./src/gen2.js");
const [dir, variant, mi] = [process.argv[2], process.argv[3] || "jazz", +(process.argv[4] || 0)];
const head = JSON.parse(fs.readFileSync(path.join(dir, "model.json")));
const b = fs.readFileSync(path.join(dir, "model.bin")); const buf = b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength);
const MJ = JSON.parse(fs.readFileSync(path.join(__dirname, `test/moods_${variant}.json`)));
const m = MJ.moods[mi], FP = MJ.fp;
const e = new EngineWasm(head, buf, fs.readFileSync(path.join(__dirname, "build/engine.wasm")));
const g = new Gen(e, head, 7); g.setSpec({ progs: m.progs, keys: m.keys, mode: m.mode, bias: m.bias || {} });
const progs = m.conds.filter((c) => c.startsWith("FAM_")).flatMap((c) => (m.only || {})[c.slice(4)] || FP[c.slice(4)] || []);
g.start(m.conds, progs);
const P0 = head.vocab.indexOf("PROG_0");
const agg = {}; let n = 0;
const orig = g.sample.bind(g);
g.sample = function (t) {
  if (this.last >= this.POS0 && this.last < this.PROG0) {       // 위치 다음 = 악기 고르는 자리
    const lg = this.logits; let mx = -1e9; for (const p of progs) mx = Math.max(mx, lg[P0 + p]);
    let s = 0; const pr = {}; for (const p of progs) { pr[p] = Math.exp(lg[P0 + p] - mx); s += pr[p]; }
    for (const p of progs) agg[p] = (agg[p] || 0) + pr[p] / s; n++;
  }
  return orig(t);
};
let bars = 0; while (bars < 16) if (g.stepBar(64)) bars++;
console.log(m.name, "악기 고르는 자리", n, "번 · 모델 확률 평균(가중치 빼고):");
console.log(Object.entries(agg).sort((a, b) => b[1] - a[1]).map(([p, v]) => `${p}:${(v / n * 100).toFixed(1)}%`).join(" "));
