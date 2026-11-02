// v2 생성 일꾼 (Web Worker): 지휘자(코드 진행) + 모델(음표). 화면과 따로 돌아 끊기지 않게.
let gen = null, running = false, ahead = 0, target = 3, epoch = 0, kind = "js", tokCount = 0, tokTime = 0;
const tick = () => new Promise((r) => { const ch = new MessageChannel(); ch.port1.onmessage = () => r(); ch.port2.postMessage(0); });
function b64(s) { const bin = atob(s), u = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i); return u; }

onmessage = (ev) => {
  const m = ev.data;
  if (m.type === "init") {
    const buf = b64(m.weights).buffer;
    let eng;
    try { eng = new EngineWasm(m.head, buf, b64(m.wasm)); kind = "wasm"; }
    catch (e) { eng = new Engine(m.head, buf); kind = "js"; }
    gen = new Gen(eng, m.head, (Math.random() * 1e9) | 0);
    postMessage({ type: "ready", kind });
  } else if (m.type === "start" || m.type === "switch") {
    epoch = m.epoch; gen.temp = m.temp; gen.setSpec(m.spec);
    if (m.type === "start") { gen.history = []; gen.sigs = []; }
    const t0 = performance.now();
    gen.start(m.conds, m.progs, m.type === "switch" ? m.keep : undefined);
    postMessage({ type: "prefill", n: gen.prefill, ms: performance.now() - t0 });
    ahead = m.type === "switch" ? m.queued : 0;
    if (!running) { running = true; pump(); }
  } else if (m.type === "ahead") ahead = m.n;
  else if (m.type === "temp") gen.temp = m.temp;
  else if (m.type === "stop") running = false;
  else if (m.type === "resume") { if (!running) { running = true; pump(); } }
};

async function pump() {
  while (running) {
    if (ahead >= target) { await new Promise((r) => setTimeout(r, 30)); continue; }
    const ep = epoch, t0 = performance.now(), p0 = gen.e.pos;
    const bar = gen.stepBar(24);
    const dt = performance.now() - t0, dn = Math.max(0, gen.e.pos - p0);
    tokCount += dn; tokTime += dt;
    if (bar && ep === epoch) {
      ahead++;
      postMessage({ type: "bar", epoch: ep, bar: { idx: bar.idx, notes: bar.notes, barLen: bar.barLen, chords: bar.chords, ntok: bar.toks.length },
                    tps: tokTime > 0 ? (tokCount * 1000) / tokTime : 0, redo: gen.stats.redo, made: gen.stats.bars });
      if (tokTime > 4000) { tokCount *= 0.5; tokTime *= 0.5; }
    }
    await tick();
  }
}
