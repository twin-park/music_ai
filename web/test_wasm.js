// node test_wasm.js <폴더> : wasm 엔진 = JS 엔진 인지 + 속도 (문맥 길이별)
const fs = require("fs"), path = require("path");
const { Engine, EngineWasm } = require("./src/engine.js");
const dir = process.argv[2];
const head = JSON.parse(fs.readFileSync(path.join(dir, "model.json")));
const b = fs.readFileSync(path.join(dir, "model.bin"));
const buf = b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength);
const w = new EngineWasm(head, buf, fs.readFileSync(path.join(__dirname, "build/engine.wasm")));
const j = new Engine(head, buf);
const { seq } = JSON.parse(fs.readFileSync(path.join(dir, "seq.json")));
let md = 0;
for (let i = 0; i < 120; i++) { const a = j.step(seq[i]), c = w.step(seq[i]); for (let k = 0; k < a.length; k++) md = Math.max(md, Math.abs(a[k] - c[k])); }
console.log("wasm↔JS 최대차", md.toExponential(2));
w.reset();
let t0 = Date.now(), n = 0, marks = [];
for (let i = 0; i < head.cfg.ctx; i++) {
  w.step(seq[i % seq.length]); n++;
  if ([255, 511, 1023].includes(i)) { const dt = (Date.now() - t0) / 1000; marks.push(`~${i + 1}: 초당 ${(256 / dt).toFixed(0)}`); t0 = Date.now(); }
}
console.log("wasm 속도(문맥 위치별 256낱말 구간)", marks.join(" · "));
