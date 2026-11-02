// 화면 + 악기 + 박자 맞춰 틀기. 생성은 Web Worker 가 하고 여기서는 받은 마디를 제때 연주한다.
(() => {
  const $ = (s) => document.querySelector(s);
  const head = JSON.parse($("#d-head").textContent);
  const SIT = JSON.parse($("#d-sit").textContent);        // [이름, 단어들, 조건, 지시, 볼륨dB]
  const FAM = head.families, EDGE = head.edges;
  const EMOJI = { "아이 재우기": "🍼", "진정": "🫖", "위로": "🤍", "즐거운 대화": "😄", "바닷가": "🌊",
                  "비 오는 길": "🌧️", "자연 속": "🌿", "드라이브": "🚗", "기본": "🎹" };
  const FAM_KO = { piano: "피아노", strings: "현악", ensemble: "앙상블", bass: "베이스", drums: "드럼", guitar: "기타",
                   pipe: "플루트", reed: "클라리넷", brass: "금관", organ: "오르간", synth_pad: "신스 패드", chrom_perc: "비브라폰" };
  const UI_FAMS = Object.keys(FAM_KO);
  const famProgs = (f) => (f === "drums" ? [128] : Array.from({ length: 8 }, (_, k) => FAM.indexOf(f) * 8 + k));
  const binOf = (v, e) => { let i = 0; while (i < e.length && v >= e[i]) i++; return i; };
  const tempoMid = (i) => { const e = [40, ...EDGE.TEMPO, 190]; return (e[i] + e[i + 1]) / 2; };

  // ---------- 상태 ----------
  const S = { sit: 7, ts: "4/4", qpm: 115, dens: 5, poly: 3, reg: 3, mode: "major", vel: 1, genre: "pop",
              fams: new Set(["piano", "bass", "drums"]), temp: 1.0, custom: false, vol: 0.8, duck: false };
  function fromPreset(i) {
    const c = SIT[i][2];
    S.sit = i; S.custom = false; S.fams = new Set(); S.genre = null;
    for (const t of c) {
      const [k, v] = [t.slice(0, t.indexOf("_")), t.slice(t.indexOf("_") + 1)];
      if (k === "TS") S.ts = v; else if (k === "TEMPO") S.qpm = tempoMid(+v); else if (k === "MODE") S.mode = v;
      else if (k === "DENS") S.dens = +v; else if (k === "POLY") S.poly = +v; else if (k === "REG") S.reg = +v;
      else if (k === "VEL") S.vel = +v; else if (k === "GENRE") S.genre = v; else if (k === "FAM") S.fams.add(v);
    }
  }
  function conds() {
    const c = ["TS_" + S.ts, "TEMPO_" + binOf(S.qpm, EDGE.TEMPO), "MODE_" + S.mode, "DENS_" + S.dens, "POLY_" + S.poly,
               "REG_" + S.reg, "VEL_" + S.vel];
    if (S.genre) c.push("GENRE_" + S.genre);
    FAM.forEach((f) => { if (S.fams.has(f)) c.push("FAM_" + f); });
    return c;
  }
  const progs = () => [...S.fams].flatMap(famProgs).sort((a, b) => a - b);

  // ---------- 악기 ----------
  const MIX = { piano: 0.9, vibes: 0.55, organ: 0.42, guitar: 0.75, bass: 0.95, strings: 0.5, harp: 0.7, brass: 0.42,
                reed: 0.55, flute: 0.55, pad: 0.38, drums: 0.72 };
  const ATTACK = { strings: 0.08, pad: 0.12, organ: 0.02, flute: 0.03, brass: 0.03, reed: 0.03 };
  function instOf(p) {
    if (p === 128) return "drums";
    if (p < 8) return "piano"; if (p < 16) return "vibes"; if (p < 24) return "organ"; if (p < 32) return "guitar";
    if (p < 40) return "bass"; if (p === 45 || p === 46) return "harp"; if (p === 47) return "bass";
    if (p < 52) return "strings"; if (p < 56) return "pad"; if (p < 64) return "brass"; if (p < 72) return "reed";
    if (p < 88) return "flute"; if (p < 104) return "pad"; if (p < 112) return "guitar"; if (p < 120) return "vibes";
    return "pad";
  }
  const FAMCOLOR = { piano: "#4ade80", strings: "#60a5fa", harp: "#93c5fd", bass: "#f59e0b", drums: "#a1a1aa", guitar: "#fb923c",
                     flute: "#c084fc", reed: "#e879f9", brass: "#f87171", organ: "#facc15", pad: "#2dd4bf", vibes: "#38bdf8" };

  class Synth {
    constructor(ac, dest) { this.ac = ac; this.dest = dest; this.bank = {}; }
    async load(samples, prog) {
      const names = Object.keys(samples); let done = 0, total = names.reduce((a, n) => a + samples[n].notes.length, 0);
      for (const n of names) {
        const s = samples[n], med = [...s.gain].sort((a, b) => a - b)[s.gain.length >> 1];
        this.bank[n] = { rel: s.release, list: await Promise.all(s.data.map(async (b64, k) => {
          const bin = atob(b64), u = new Uint8Array(bin.length);
          for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
          const buf = await this.ac.decodeAudioData(u.buffer);
          prog && prog(++done / total);
          return { note: s.notes[k], buf, g: Math.min(1.5, Math.max(0.5, s.gain[k] / med)) };
        })) };
      }
    }
    play(p, pitch, t, dur, vel, k = 1) {
      const name = instOf(p), b = this.bank[name]; if (!b) return;
      let best = b.list[0];
      for (const s of b.list) if (Math.abs(s.note - pitch) < Math.abs(best.note - pitch)) best = s;
      if (name === "drums" && best.note !== pitch && Math.abs(best.note - pitch) > 2) return;
      const ac = this.ac, src = ac.createBufferSource(), g = ac.createGain();
      src.buffer = best.buf;
      if (name !== "drums") src.playbackRate.value = Math.pow(2, (pitch - best.note) / 12);
      const amp = MIX[name] * best.g * Math.pow(vel / 100, 1.6) * 0.32 * k, a = ATTACK[name] || 0.004;
      const end = name === "drums" ? t + best.buf.duration : t + Math.max(dur, 0.05);
      g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(amp, t + a);
      g.gain.setValueAtTime(amp, end); g.gain.setTargetAtTime(0, end, b.rel / 3);
      src.connect(g).connect(this.dest);
      src.start(t); src.stop(end + b.rel * 2 + 0.05);
    }
  }

  function makeGraph(ac) {
    const comp = ac.createDynamicsCompressor();
    comp.threshold.value = -18; comp.knee.value = 6; comp.ratio.value = 4; comp.attack.value = 0.01; comp.release.value = 0.3;
    const lim = ac.createDynamicsCompressor();              // 최고점 막기
    lim.threshold.value = -4; lim.knee.value = 0; lim.ratio.value = 20; lim.attack.value = 0.002; lim.release.value = 0.2;
    const clip = ac.createWaveShaper(), cv = new Float32Array(2049);
    for (let i = 0; i < 2049; i++) { const x = i / 1024 - 1; cv[i] = Math.tanh(1.6 * x) / Math.tanh(1.6); }
    clip.curve = cv;
    const master = ac.createGain(), duck = ac.createGain(), sit = ac.createGain();
    const bus = ac.createGain(), wet = ac.createGain(), conv = ac.createConvolver();
    const len = Math.floor(ac.sampleRate * 2.6), ir = ac.createBuffer(2, len, ac.sampleRate);
    for (let ch = 0; ch < 2; ch++) { const d = ir.getChannelData(ch); for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, 2.5) * Math.exp(-3 * i / len); }
    conv.buffer = ir; wet.gain.value = 0.22;
    bus.connect(comp); bus.connect(conv).connect(wet).connect(comp);
    comp.connect(sit).connect(duck).connect(master).connect(lim).connect(clip).connect(ac.destination);
    return { bus, master, duck, sit, wet };
  }

  // ---------- 연주 ----------
  let ac, G, synth, worker, ready = false, playing = false, epoch = 0, queue = [], nextT = 0, lastSched = -1;
  let played = [];
  let tps = 0, engineKind = "-", roll = [], started = false, prefillMs = 0;
  const spt = () => 60 / (S.qpm * head.Q);
  window.__stats = { bars: 0, underruns: 0, switches: 0 };

  // 마디에서 가장 많이 겹친 음 수 → 음 하나 크기 줄이는 비율 (화음이 두꺼워도 전체 크기가 비슷하게)
  function overlapGain(notes) {
    let mx = 1;
    for (const [pos] of notes) { let c = 0; for (const [q, p2, , d2] of notes) if (p2 !== 128 && q <= pos && q + d2 > pos) c++; if (c > mx) mx = c; }
    return 1 / Math.sqrt(Math.max(1, mx / 2));
  }
  function scheduleBar(b, t0) {
    const k = spt(), og = overlapGain(b.notes);
    for (const [pos, p, pitch, dur, vel] of b.notes) {
      const t = t0 + pos * k, d = dur * k;
      synth.play(p, pitch, t, d, vel, og);
      roll.push({ t, d, pitch, c: FAMCOLOR[instOf(p)] || "#4ade80" });
    }
    if (roll.length > 3000) roll = roll.slice(-2000);
    window.__stats.bars++;
    played.push({ notes: b.notes, barLen: b.barLen, qpm: S.qpm, sit: S.custom ? "직접" : SIT[S.sit][0] });
    if (played.length > 64) played.shift();
  }
  function loop() {
    if (!playing) return;
    const now = ac.currentTime;
    if (nextT < now - 0.02) { if (queue.length) window.__stats.underruns++; nextT = now + 0.08; }
    while (queue.length && nextT < now + 0.6) {
      const b = queue.shift(); scheduleBar(b, nextT); lastSched = b.idx; nextT += b.barLen * spt();
      worker.postMessage({ type: "ahead", n: queue.length });
    }
  }
  function aheadSec() { return Math.max(0, nextT - (ac ? ac.currentTime : 0)) + queue.reduce((a, b) => a + b.barLen * spt(), 0); }

  function apply(first) {
    epoch++;
    const msg = { epoch, conds: conds(), progs: progs(), temp: S.temp };
    if (first) { queue = []; worker.postMessage({ type: "start", ...msg }); }
    else {
      const keep = queue.length ? queue[0].idx : lastSched;          // 다음 1마디는 다리로 남김
      queue = queue.filter((b) => b.idx <= keep);
      worker.postMessage({ type: "switch", ...msg, keep, queued: queue.length });
      window.__stats.switches++;
      toast(lastSched < 0 ? "곧 시작해요" : "다음 마디부터 바뀌어요");
    }
    rampSit();
    render();
  }
  function rampSit() {
    if (!G) return;
    const db = S.custom ? 0 : SIT[S.sit][4];
    G.sit.gain.setTargetAtTime(Math.pow(10, db / 20), ac.currentTime, 0.6);
    G.wet.gain.setTargetAtTime(S.sit === 0 && !S.custom ? 0.3 : 0.22, ac.currentTime, 0.6);
  }

  async function boot() {
    setBusy("악기 소리를 불러오는 중");
    ac = new (window.AudioContext || window.webkitAudioContext)({ latencyHint: "playback" });
    G = makeGraph(ac); G.master.gain.value = S.vol;
    synth = new Synth(ac, G.bus);
    await synth.load(JSON.parse($("#d-samples").textContent), (r) => setBusy(`악기 소리를 불러오는 중 ${Math.round(r * 100)}%`));
    setBusy("AI 모델을 올리는 중");
    const src = $("#w-src").textContent;
    worker = new Worker(URL.createObjectURL(new Blob([src], { type: "text/javascript" })));
    await new Promise((res) => {
      worker.onmessage = (ev) => {
        const m = ev.data;
        if (m.type === "ready") { engineKind = m.kind; res(); }
        else if (m.type === "bar") { if (m.epoch === epoch) { queue.push(m.bar); tps = m.tps; worker.postMessage({ type: "ahead", n: queue.length }); } }
        else if (m.type === "prefill") prefillMs = m.ms;
      };
      worker.postMessage({ type: "init", head, weights: $("#d-weights").textContent.trim(), wasm: $("#d-wasm").textContent.trim() });
    });
    ready = true; setBusy(null);
    setInterval(loop, 25);
  }

  async function togglePlay() {
    if (!ready) { $("#play").disabled = true; await boot(); $("#play").disabled = false; }
    if (!playing) {
      await ac.resume(); playing = true;
      if (!started) { started = true; apply(true); } else worker.postMessage({ type: "resume" });
    } else {
      playing = false; await ac.suspend(); worker.postMessage({ type: "stop" });
    }
    render();
  }

  // ---------- 화면 ----------
  function setBusy(t) { const el = $("#busy"); el.hidden = !t; if (t) el.querySelector("span").textContent = t; }
  let toastT;
  function toast(t) { const el = $("#toast"); el.textContent = t; el.classList.add("on"); clearTimeout(toastT); toastT = setTimeout(() => el.classList.remove("on"), 1800); }

  function render() {
    $("#play").classList.toggle("on", playing);
    $("#play").setAttribute("aria-label", playing ? "멈추기" : "시작");
    $("#play-ico").textContent = playing ? "❚❚" : "▶";
    const name = S.custom ? "직접 조절" : SIT[S.sit][0];
    $("#sit-name").textContent = (S.custom ? "🎛️" : EMOJI[name] || "🎵") + " " + name;
    $("#sit-say").innerHTML = (S.custom ? ["내가 고른 대로"] : SIT[S.sit][3]).map((w) => `<span class="chip">${w}</span>`).join("");
    $("#conds").textContent = conds().join(" · ");
    document.querySelectorAll(".mood").forEach((b, i) => b.classList.toggle("sel", !S.custom && i === S.sit));
    $("#qpm").value = S.qpm; $("#qpm-v").textContent = Math.round(S.qpm);
    $("#dens").value = S.dens; $("#poly").value = S.poly; $("#reg").value = S.reg; $("#temp").value = S.temp;
    for (const k of ["dens", "poly", "reg"]) $("#" + k).nextElementSibling.textContent = S[k];
    $("#temp-v").textContent = S.temp.toFixed(2);
    document.querySelectorAll("[data-mode]").forEach((b) => b.classList.toggle("sel", b.dataset.mode === S.mode));
    document.querySelectorAll("[data-ts]").forEach((b) => b.classList.toggle("sel", b.dataset.ts === S.ts));
    document.querySelectorAll("[data-fam]").forEach((b) => b.classList.toggle("sel", S.fams.has(b.dataset.fam)));
    $("#phone").classList.toggle("sel", S.duck);
  }

  function buildUI() {
    $("#moods").innerHTML = SIT.map((s, i) => `<button class="mood" data-i="${i}"><b>${EMOJI[s[0]] || "🎵"}</b><span>${s[0]}</span></button>`).join("");
    document.querySelectorAll(".mood").forEach((b) => b.onclick = () => { fromPreset(+b.dataset.i); if (started) apply(); else render(); });
    $("#fams").innerHTML = UI_FAMS.map((f) => `<button class="pill" data-fam="${f}">${FAM_KO[f]}</button>`).join("");
    let deb;
    const changed = () => { S.custom = true; render(); clearTimeout(deb); if (started) deb = setTimeout(() => apply(), 500); };
    document.querySelectorAll("[data-fam]").forEach((b) => b.onclick = () => {
      const f = b.dataset.fam; if (S.fams.has(f)) { if (S.fams.size > 1) S.fams.delete(f); } else S.fams.add(f); changed(); });
    document.querySelectorAll("[data-mode]").forEach((b) => b.onclick = () => { S.mode = b.dataset.mode; changed(); });
    document.querySelectorAll("[data-ts]").forEach((b) => b.onclick = () => { S.ts = b.dataset.ts; changed(); });
    $("#qpm").oninput = (e) => { S.qpm = +e.target.value; $("#qpm-v").textContent = S.qpm; };
    $("#qpm").onchange = changed;
    for (const k of ["dens", "poly", "reg"]) $("#" + k).onchange = (e) => { S[k] = +e.target.value; changed(); };
    $("#temp").oninput = (e) => { S.temp = +e.target.value; $("#temp-v").textContent = S.temp.toFixed(2); worker && worker.postMessage({ type: "temp", temp: S.temp }); };
    $("#play").onclick = togglePlay;
    $("#vol").oninput = (e) => { S.vol = +e.target.value; if (G) G.master.gain.setTargetAtTime(S.vol, ac.currentTime, 0.05); };
    $("#phone").onclick = () => {
      S.duck = !S.duck;
      if (G) G.duck.gain.setTargetAtTime(S.duck ? 0.1 : 1, ac.currentTime, S.duck ? 0.04 : 0.8);
      toast(S.duck ? "통화 중 — 음악을 크게 줄였어요" : "통화 끝 — 천천히 돌아와요"); render();
    };
    $("#more").onclick = () => { const p = $("#detail"); p.hidden = !p.hidden; $("#more").textContent = p.hidden ? "세부 조절 ▼" : "세부 조절 ▲"; };
    $("#theme").onclick = () => { document.documentElement.dataset.theme = document.documentElement.dataset.theme === "light" ? "dark" : "light"; };
    $("#info").onclick = () => { const p = $("#info-box"); p.hidden = !p.hidden; };
  }

  function draw() {
    const cv = $("#roll"), cx = cv.getContext("2d"), dpr = window.devicePixelRatio || 1;
    const w = cv.clientWidth, h = cv.clientHeight;
    if (cv.width !== w * dpr) { cv.width = w * dpr; cv.height = h * dpr; }
    cx.setTransform(dpr, 0, 0, dpr, 0, 0); cx.clearRect(0, 0, w, h);
    const now = ac ? ac.currentTime : 0, past = 6, fut = 3, x = (t) => ((t - now + past) / (past + fut)) * w;
    const y = (p) => h - ((p - 24) / 84) * h;
    for (const n of roll) {
      if (n.t + n.d < now - past || n.t > now + fut) continue;
      cx.globalAlpha = n.t <= now ? 0.95 : 0.35; cx.fillStyle = n.c;
      cx.fillRect(x(n.t), y(n.pitch) - 2, Math.max(2, x(n.t + n.d) - x(n.t)), 3);
    }
    cx.globalAlpha = 1; cx.fillStyle = getComputedStyle(document.body).getPropertyValue("--accent");
    cx.fillRect(x(now), 0, 2, h);
    const st = ready ? `AI 엔진 ${engineKind === "wasm" ? "WASM" : "JS"} · 초당 ${tps.toFixed(0)}낱말 · 앞으로 ${aheadSec().toFixed(1)}초 준비됨` : "아직 시작 전";
    $("#stat").textContent = st;
    window.__stats.tps = tps; window.__stats.ahead = ready ? aheadSec() : 0; window.__stats.engine = engineKind;
    window.__stats.prefillMs = prefillMs; window.__stats.queue = queue.length;
    requestAnimationFrame(draw);
  }

  // 시험용: 지금까지 연주한 마디를 같은 악기로 오프라인 녹음 → 크기·무음·찢어짐 숫자 + 16비트 PCM(base64)
  window.__renderTest = async (sec, from) => {
    const sr = 44100, oc = new OfflineAudioContext(2, sr * sec, sr), g = makeGraph(oc), sy = new Synth(oc, g.bus);
    g.master.gain.value = 0.8;
    await sy.load(JSON.parse($("#d-samples").textContent));
    let t = 0.1;
    for (const b of played.slice(-(from || played.length))) {
      const k = 60 / (b.qpm * head.Q);
      const og = overlapGain(b.notes);
      for (const [pos, p, pitch, dur, vel] of b.notes) if (t + pos * k < sec) sy.play(p, pitch, t + pos * k, dur * k, vel, og);
      t += b.barLen * k; if (t > sec) break;
    }
    const buf = await oc.startRendering(), L = buf.getChannelData(0), R = buf.getChannelData(1);
    let peak = 0, silent = 0; const pcm = new Int16Array(L.length * 2);
    for (let s0 = 0; s0 < L.length; s0 += sr) {
      let e = 0; for (let i = s0; i < Math.min(L.length, s0 + sr); i++) { e += L[i] * L[i]; peak = Math.max(peak, Math.abs(L[i]), Math.abs(R[i])); }
      if (Math.sqrt(e / sr) < 0.003) silent++;
    }
    for (let i = 0; i < L.length; i++) { pcm[2 * i] = Math.max(-1, Math.min(1, L[i])) * 32767; pcm[2 * i + 1] = Math.max(-1, Math.min(1, R[i])) * 32767; }
    let bin = ""; const u8 = new Uint8Array(pcm.buffer);
    for (let i = 0; i < u8.length; i += 32768) bin += String.fromCharCode.apply(null, u8.subarray(i, i + 32768));
    let e = 0; for (let i = 0; i < L.length; i++) e += L[i] * L[i];
    return { peak, rms: Math.sqrt(e / L.length), silentSec: silent, sec, bars: played.length, pcm: btoa(bin), sits: [...new Set(played.map((b) => b.sit))] };
  };

  fromPreset(7); buildUI(); render(); requestAnimationFrame(draw);
  window.__ctl = { press: (i) => document.querySelectorAll(".mood")[i].click(), play: togglePlay };
})();
