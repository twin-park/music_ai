// node test_parity.js <폴더> : JS 엔진으로 같은 낱말열 계산 + 속도
const fs = require("fs"), path = require("path");
const { Engine } = require("./src/engine.js");
const dir = process.argv[2];
const head = JSON.parse(fs.readFileSync(path.join(dir, "model.json")));
const b = fs.readFileSync(path.join(dir, "model.bin"));
const buf = b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength);
const e = new Engine(head, buf);
const { seq, pos } = JSON.parse(fs.readFileSync(path.join(dir, "seq.json")));
const out = [];
const t0 = Date.now();
seq.forEach((t, i) => { const lg = e.step(t); if (pos.includes(i)) out.push(Array.from(lg)); });
const dt = (Date.now() - t0) / 1000;
fs.writeFileSync(path.join(dir, "js_out.json"), JSON.stringify({ logits: out }));
console.log(`JS(Node ${process.version}) 낱말 ${seq.length}개 ${dt.toFixed(2)}s → 초당 ${(seq.length / dt).toFixed(0)} 낱말 (문맥 0~${seq.length})`);
