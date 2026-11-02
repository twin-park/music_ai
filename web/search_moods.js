// node search_moods.js <모델폴더> <jazz|orch> [시드수] [마디수] [이름들,…]
// 상황마다 후보 설정 몇 개 × 시드 몇 개로 만들어 보고 점수로 고름 → test/best_<v>.json
// 점수 = 화성(강박 구성음·구성음+텐션) − 단조로움(선율 악기가 같은 음 되풀이) − 노트북 속도 초과 − 무음 + 악기 섞임
const fs = require("fs"), path = require("path");
const { EngineWasm } = require("./src/engine.js");
const { Gen } = require("./src/gen2.js");
const [dir, variant] = [process.argv[2], process.argv[3] || "jazz"];
const NSEED = +(process.argv[4] || 3), NBAR = +(process.argv[5] || 24), ONLY = (process.argv[6] || "").split(",").filter(Boolean);
const head = JSON.parse(fs.readFileSync(path.join(dir, "model.json")));
const b = fs.readFileSync(path.join(dir, "model.bin")); const buf = b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength);
const MJ = JSON.parse(fs.readFileSync(path.join(__dirname, `test/moods_${variant}.json`)));
const FP = MJ.fp, V = head.vocab, ID = (t) => V.indexOf(t);
const e = new EngineWasm(head, buf, fs.readFileSync(path.join(__dirname, "build/engine.wasm")));
const IV = { maj: [0, 4, 7], min: [0, 3, 7], "7": [0, 4, 7, 10], maj7: [0, 4, 7, 11], m7: [0, 3, 7, 10], m7b5: [0, 3, 6, 10], dim: [0, 3, 6], sus: [0, 5, 7], aug: [0, 4, 8] };
const TENS = { maj: [2, 9], min: [2, 5, 10], "7": [2, 9], maj7: [2, 9, 6], m7: [2, 5], m7b5: [5, 8], dim: [9], sus: [2, 10], aug: [10] };
const EDGE = [40, 60, 70, 80, 90, 100, 110, 120, 135, 150, 170, 190];
const LIMIT = 120;          // 노트북에서 넉넉히 버틸 초당 낱말 (이 컴퓨터 크롬 실측 360~700, 느린 노트북을 1/3 로 잡음)
const sortC = (c) => [...new Set(c)].sort((x, y) => ID(x) - ID(y));

function run(m, seed) {
  const g = new Gen(e, head, seed); g.setSpec({ progs: m.progs, keys: m.keys, mode: m.mode, bias: m.bias || {} }); g.temp = m.temp || 0.9;
  const progs = m.conds.filter((c) => c.startsWith("FAM_")).flatMap((c) => (m.only || {})[c.slice(4)] || FP[c.slice(4)] || []);
  g.start(m.conds, progs);
  const bars = []; let ntok = 0, guard = 0;
  while (bars.length < NBAR && guard++ < NBAR * 40) { const bar = g.stepBar(64); if (bar) { bars.push(bar); ntok += bar.toks.length; } }
  let s = 0, so = 0, a = 0, ao = 0, empty = 0; const lines = {}, fam = {};
  bars.forEach((bar, bi) => {
    const chs = bar.toks.slice(1, 3).map((t) => V[t].split("_")), half = bar.barLen / 2, top = {};
    let n = 0;
    for (const [pos, p, pitch] of bar.notes) {
      const f = p === 128 ? 16 : p >> 3; fam[f] = (fam[f] || 0) + 1;
      if (p === 128) continue; n++;
      const k = p + ":" + (bi * 96 + pos); top[k] = Math.max(top[k] ?? -1, pitch);
      const c = chs[pos < half ? 0 : 1]; if (c[1] === "NC") continue;
      const iv = (pitch - +c[1] + 120) % 12, ok = IV[c[2]].includes(iv);
      a++; ao += ok || TENS[c[2]].includes(iv); if (pos % 12 === 0) { s++; so += ok; }
    }
    if (n === 0) empty++;
    for (const [k, t] of Object.entries(top)) { const p = k.split(":")[0]; (lines[p] = lines[p] || []).push([+k.split(":")[1], t]); }
  });
  let mono = 0, mw = 0;
  for (const [p, arr] of Object.entries(lines)) {
    const P = +p; if (P >= 32 && P < 40) continue;                  // 베이스는 빼고
    const w = (P >= 16 && P < 32 ? 0.3 : 1) * arr.length;           // 기타·오르간 반주는 같은 음 반주가 자연스러워 덜 셈
    arr.sort((x, y) => x[0] - y[0]); let rep = 0;
    for (let i = 1; i < arr.length; i++) rep += arr[i][1] === arr[i - 1][1];
    mono += w * rep / Math.max(1, arr.length - 1); mw += w;
  }
  mono = mw ? mono / mw : 1;
  const tb = m.conds.find((c) => c.startsWith("TEMPO_")), ti = +tb.split("_")[1], qpm = (EDGE[ti] + EDGE[ti + 1]) / 2;
  const barSec = bars[0].barLen * 60 / (qpm * head.Q), need = ntok / bars.length / barSec;
  const tot = Object.values(fam).reduce((x, y) => x + y, 0), want = m.conds.filter((c) => c.startsWith("FAM_")).length;
  const present = Object.values(fam).filter((x) => x / tot >= 0.05).length;
  const strong = so / Math.max(1, s), all = ao / Math.max(1, a), notesPerBar = a / bars.length;
  const score = 1.0 * strong + 0.5 * all - 1.2 * Math.max(0, mono - 0.35) - 0.6 * Math.max(0, need / LIMIT - 1)
    - 1.0 * (empty / bars.length) - 0.5 * Math.max(0, 1 - notesPerBar / 3) + 0.15 * Math.min(1, present / Math.max(1, want));
  return { score, strong, all, mono, need, empty, present, want, tpb: ntok / bars.length };
}

function variants(m) {
  const out = [["지금", m]];
  const mk = (tag, f) => { const x = JSON.parse(JSON.stringify(m)); f(x); x.conds = sortC(x.conds); out.push([tag, x]); };
  const bump = (x, k, d) => { x.conds = x.conds.map((c) => { if (!c.startsWith(k + "_")) return c; const n = +c.split("_")[1] + d; return ID(k + "_" + n) >= 0 && n >= 0 ? k + "_" + n : c; }); };
  if (!m.conds.includes("MOOD_melodic")) mk("+melodic", (x) => x.conds.push("MOOD_melodic"));
  if (!m.conds.includes("MOOD_ballad") && +m.conds.find((c) => c.startsWith("TEMPO_")).split("_")[1] <= 3) mk("+ballad", (x) => x.conds.push("MOOD_ballad"));
  if (m.conds.includes("MOOD_ballad")) mk("-ballad", (x) => (x.conds = x.conds.filter((c) => c !== "MOOD_ballad" && c !== "MOOD_slow")));
  mk("DENS-1", (x) => bump(x, "DENS", -1));
  mk("POLY-1", (x) => bump(x, "POLY", -1));
  mk("temp+0.1", (x) => (x.temp = (x.temp || 0.9) + 0.1));
  return out;
}

const best = {};
for (const m0 of MJ.moods) {
  if (ONLY.length && !ONLY.includes(m0.name)) continue;
  const m = JSON.parse(JSON.stringify(m0)); m.conds = sortC(m.conds);
  const res = [];
  for (const [tag, x] of variants(m)) {
    const rs = []; for (let k = 0; k < NSEED; k++) rs.push(run(x, 11 + k * 7));
    const avg = (f) => rs.reduce((q, r) => q + r[f], 0) / rs.length, worst = Math.min(...rs.map((r) => r.score));
    const sc = 0.7 * avg("score") + 0.3 * worst;          // 평균 + 가장 나쁜 시드도 봄 (한 번이라도 폭주하면 깎임)
    res.push({ tag, sc, x, line: `${tag.padEnd(9)} 점수 ${sc.toFixed(3)} (최저 ${worst.toFixed(2)}) · 강박 ${(avg("strong") * 100).toFixed(0)}% · 구성음+텐션 ${(avg("all") * 100).toFixed(0)}% · 같은음 ${(avg("mono") * 100).toFixed(0)}% · 필요 ${avg("need").toFixed(0)}낱말/s · 무음마디 ${avg("empty").toFixed(1)} · 악기 ${avg("present").toFixed(1)}/${rs[0].want}` });
  }
  res.sort((p, q) => q.sc - p.sc);
  console.log(`\n${m.name}`); for (const r of res) console.log("  " + (r === res[0] ? "★ " : "  ") + r.line);
  best[m.name] = { tag: res[0].tag, conds: res[0].x.conds, temp: res[0].x.temp, score: res[0].sc, base: res.find((r) => r.tag === "지금").sc };
}
const out = path.join(__dirname, `test/best_${variant}_${process.argv[7] || "all"}.json`);
fs.writeFileSync(out, JSON.stringify(best, null, 1)); console.log("\n→", out);
