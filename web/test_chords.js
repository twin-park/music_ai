// node test_chords.js <모델폴더> <재즈|오케> : 상황마다 32마디 만들고 코드 따르기 · 악기 · 반복 숫자로
const fs = require("fs"), path = require("path");
const { EngineWasm } = require("./src/engine.js");
const { Gen } = require("./src/gen2.js");
const dir = process.argv[2], variant = process.argv[3] || "jazz";
const head = JSON.parse(fs.readFileSync(path.join(dir, "model.json")));
const b = fs.readFileSync(path.join(dir, "model.bin")); const buf = b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength);
const MJ = JSON.parse(fs.readFileSync(process.env.MOODS_FILE || path.join(__dirname, `test/moods_${variant}.json`)));
const moods = MJ.moods, FP = MJ.fp;
const IV = { maj: [0, 4, 7], min: [0, 3, 7], "7": [0, 4, 7, 10], maj7: [0, 4, 7, 11], m7: [0, 3, 7, 10], m7b5: [0, 3, 6, 10], dim: [0, 3, 6], sus: [0, 5, 7], aug: [0, 4, 8] };
const TENS = { maj: [2, 9], min: [2, 5, 10], "7": [2, 9], maj7: [2, 9, 6], m7: [2, 5], m7b5: [5, 8], dim: [9], sus: [2, 10], aug: [10] };
const FAMOF = (p) => (p === 128 ? 16 : p >> 3);
const e = new EngineWasm(head, buf, fs.readFileSync(path.join(__dirname, "build/engine.wasm")));
const tot = { strong: 0, strongOK: 0, all: 0, allOK: 0 };
for (const m of moods.slice(0, process.argv[4] ? +process.argv[4] : moods.length)) {
  const g = new Gen(e, head, +(process.env.SEED || 7)); g.setSpec({ progs: m.progs, keys: m.keys, mode: m.mode, bias: m.bias || {} }); g.temp = m.temp || 0.9;
  const progs = m.conds.filter((c) => c.startsWith("FAM_")).flatMap((c) => (m.only || {})[c.slice(4)] || FP[c.slice(4)] || []);
  const ID = (t) => head.vocab.indexOf(t); m.conds = [...m.conds].sort((x, y) => ID(x) - ID(y));   // 플레이어와 같은 순서
  g.start(m.conds, progs);
  const t0 = Date.now(); let bars = [], ntok = 0;
  while (bars.length < 32) { const bar = g.stepBar(64); if (bar) { bars.push(bar); ntok += bar.toks.length; } }
  const dt = (Date.now() - t0) / 1000;
  let s = 0, so = 0, a = 0, ao = 0; const used = {}; const sigs = new Set(); let dup = 0;
  for (const bar of bars) {
    const chs = bar.toks.slice(1, 3).map((t) => head.vocab[t].split("_")); // CH r q
    const half = bar.barLen / 2;
    for (const [pos, p, pitch] of bar.notes) {
      used[p] = (used[p] || 0) + 1;
      if (p === 128) continue;
      const c = chs[pos < half ? 0 : 1]; if (c[1] === "NC") continue;
      const r = +c[1], q = c[2], iv = (pitch - r + 120) % 12;
      const ok = IV[q].includes(iv), okT = ok || TENS[q].includes(iv);
      a++; ao += okT;
      if (pos % 12 === 0) { s++; so += ok; }
    }
    const sig = bar.notes.filter((n) => n[1] !== 128).map((n) => n.slice(0, 3).join(".")).join(",");
    if (sigs.has(sig)) dup++; sigs.add(sig);
  }
  // 음악다움: 악기마다 가장 높은 음을 이어 본 도약 폭(반음, 사람 선율은 보통 2~4) · 한 번에 누르는 음 수 · 세기
  const lines = {}; let ons = 0, onN = 0; const vels = [];
  bars.forEach((bar, bi) => {
    const g = {};
    for (const [pos, p, pitch, , vel] of bar.notes) {
      if (p === 128) continue; vels.push(vel);
      const k = p + ":" + (bi * 96 + pos); g[k] = Math.max(g[k] || 0, pitch); ons++;
    }
    onN += Object.keys(g).length;
    for (const [k, top] of Object.entries(g)) { const p = k.split(":")[0]; (lines[p] = lines[p] || []).push([+k.split(":")[1], top]); }
  });
  let leap = 0, ln = 0;
  for (const [p, arr] of Object.entries(lines)) {
    if (+p >= 32 && +p < 40) continue;                    // 베이스는 빼고
    arr.sort((a, b) => a[0] - b[0]);
    for (let i = 1; i < arr.length; i++) { leap += Math.abs(arr[i][1] - arr[i - 1][1]); ln++; }
  }
  if (process.env.DETAIL) {      // 악기마다: 음 수 · 평균 도약 · 같은 음 되풀이 비율
    const det = Object.entries(lines).map(([p, arr]) => { let lp = 0, rep = 0; for (let i = 1; i < arr.length; i++) { const d = Math.abs(arr[i][1] - arr[i - 1][1]); lp += d; rep += d === 0; }
      return `${p}:${arr.length}개 도약${(lp / Math.max(1, arr.length - 1)).toFixed(1)} 같은음${(rep / Math.max(1, arr.length - 1) * 100).toFixed(0)}%`; });
    console.log("   ", det.join(" | "));
  }
  const vm = vels.reduce((a, b) => a + b, 0) / Math.max(1, vels.length);
  const vs = Math.sqrt(vels.reduce((a, b) => a + (b - vm) ** 2, 0) / Math.max(1, vels.length));
  const musical = `도약 ${(leap / Math.max(1, ln)).toFixed(1)}반음 · 동시음 ${(ons / Math.max(1, onN)).toFixed(1)} · 세기 ${vm.toFixed(0)}±${vs.toFixed(0)}`;
  tot.strong += s; tot.strongOK += so; tot.all += a; tot.allOK += ao;
  const top = Object.entries(used).sort((x, y) => y[1] - x[1]).slice(0, 5).map(([p, n]) => `${p}:${n}`).join(" ");
  console.log(`${m.name}: 강박 구성음 ${(so / Math.max(1, s) * 100).toFixed(0)}% · 전체 구성음+텐션 ${(ao / Math.max(1, a) * 100).toFixed(0)}% · 마디당 낱말 ${(ntok / 32).toFixed(0)} · 똑같은 마디 ${dup}/32 (다시쓰기 ${g.stats.redo}, 두드리기 ${g.stats.mono || 0}) · 악기 ${top} · ${musical} · ${(ntok / dt).toFixed(0)}낱말/s`);
}
console.log(`합계: 강박 구성음 ${(tot.strongOK / tot.strong * 100).toFixed(1)}% · 구성음+텐션 ${(tot.allOK / tot.all * 100).toFixed(1)}%  (무작위면 강박 약 33%, 전체 약 50%)`);
