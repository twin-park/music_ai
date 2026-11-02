// 화면 + 악기 + 박자 맞춰 틀기. 생성은 Web Worker 가 하고 여기서는 받은 마디를 제때 연주한다.
(() => {
  const $ = (s) => document.querySelector(s);
  const head = JSON.parse($("#d-head").textContent);
  const MOODS = JSON.parse($("#d-sit").textContent);      // [{name, emoji, say, conds, kit, vol, mode, keys, progs}]
  const CFG = JSON.parse($("#d-cfg").textContent);         // {variant, title, genres, moods}
  const FAM = head.families, EDGE = head.edges;
  const SIT = MOODS.map((m) => [m.name, [], m.conds, m.say, m.vol]);
  const EMOJI = {}; MOODS.forEach((m) => (EMOJI[m.name] = m.emoji));
  const FAM_KO = Object.fromEntries(CFG.fams);
  const UI_FAMS = CFG.fams.map((x) => x[0]);
  const famProgs = (f) => CFG.famProgs[f] || (f === "drums" ? [128] : Array.from({ length: 8 }, (_, k) => FAM.indexOf(f) * 8 + k));
  const binOf = (v, e) => { let i = 0; while (i < e.length && v >= e[i]) i++; return i; };
  const tempoMid = (i) => { const e = [40, ...EDGE.TEMPO, 190]; return (e[i] + e[i + 1]) / 2; };

  // ---------- 상태 ----------
  const S = { sit: 0, ts: "4/4", qpm: 66, dens: 2, poly: 3, reg: 3, mode: "minor", vel: 1, genres: [], tags: [], swing: null,
              fams: new Set(["piano"]), temp: 0.9, custom: false, vol: 0.8, duck: false, kit: null };
  function fromPreset(i) {
    const c = MOODS[i].conds;
    S.sit = i; S.custom = false; S.fams = new Set(); S.genres = []; S.tags = []; S.swing = null; S.kit = MOODS[i].kit;
    S.temp = MOODS[i].temp || 0.9;                // 상황마다 창의성 기본값 (자장가는 낮게 = 더 순한 화음)
    for (const t of c) {
      const [k, v] = [t.slice(0, t.indexOf("_")), t.slice(t.indexOf("_") + 1)];
      if (k === "TS") S.ts = v; else if (k === "TEMPO") S.qpm = tempoMid(+v); else if (k === "MODE") S.mode = v;
      else if (k === "DENS") S.dens = +v; else if (k === "POLY") S.poly = +v; else if (k === "REG") S.reg = +v;
      else if (k === "VEL") S.vel = +v; else if (k === "GENRE") S.genres.push(v); else if (k === "FAM") S.fams.add(v);
      else if (k === "MOOD") S.tags.push(v); else if (k === "SWING") S.swing = +v;
    }
  }
  function conds() {   // 학습 때와 같은 순서: 박자 빠르기 조 밀도 겹침 음역 세기 장르 악기 분위기 스윙
    const c = ["TS_" + S.ts, "TEMPO_" + binOf(S.qpm, EDGE.TEMPO), "MODE_" + S.mode, "DENS_" + S.dens, "POLY_" + S.poly,
               "REG_" + S.reg, "VEL_" + S.vel];
    CFG.genres.forEach((g) => { if (S.genres.includes(g)) c.push("GENRE_" + g); });
    FAM.forEach((f) => { if (S.fams.has(f)) c.push("FAM_" + f); });
    CFG.moods.forEach((m) => { if (S.tags.includes(m)) c.push("MOOD_" + m); });
    if (S.swing !== null) c.push("SWING_" + S.swing);
    return c;
  }
  function spec() {    // 코드 진행: 지금 상황 것, 조를 바꿨으면 그 조의 첫 상황 것
    const m = MOODS[S.sit];
    const src = m.mode === S.mode ? m : MOODS.find((x) => x.mode === S.mode) || m;
    return { progs: src.progs, keys: src.keys, mode: src.mode, bias: S.custom ? {} : (m.bias || {}) };
  }
  const progs = () => [...S.fams].flatMap((f) => (!S.custom && (MOODS[S.sit].only || {})[f]) || famProgs(f)).sort((a, b) => a - b);

  // ---------- 악기 ----------
  // GM 악기 번호 → 넣어 둔 소리 이름 (재즈판 / 오케스트라판). 드럼은 지금 상황의 킷.
  const MAPS = {
    jazz: (p, pitch, vel) => {
      if (p === 128) return "kit_" + (S.kit || "jazz");
      if (p < 4) return vel >= 80 ? "piano_loud" : "piano_soft";
      if (p < 8) return "epiano"; if (p < 16) return "vibes"; if (p < 24) return "organ";
      if (p < 26) return "nylon"; if (p < 32) return "jguitar"; if (p < 40) return "bass";
      if (p < 56) return "strings"; if (p < 64) return "trumpet"; if (p < 66) return "alto"; if (p < 68) return "tenor";
      if (p < 72) return "alto"; if (p < 80) return "flute"; if (p < 96) return "strings"; if (p < 104) return "vibes";
      if (p < 112) return "jguitar"; if (p < 120) return "vibes"; return "strings";
    },
    orch: (p, pitch, vel) => {
      if (p === 128) return "kit_orch";
      if (p < 8) return vel >= 80 ? "piano_loud" : "piano_soft";
      if (p < 16) return "glock"; if (p < 24) return "choir"; if (p < 32) return "harp"; if (p < 40) return "basses";
      if (p === 40) return "violins"; if (p === 41) return "violas"; if (p === 42) return "cellos"; if (p === 43) return "basses";
      if (p === 45 || p === 46) return "harp"; if (p === 47) return "timpani"; if (p >= 52 && p <= 54) return "choir";
      if (p < 56) return pitch >= 62 ? "violins" : pitch >= 52 ? "violas" : pitch >= 40 ? "cellos" : "basses";
      if (p === 56 || p === 59) return "trumpet"; if (p === 57) return "trombone"; if (p === 58) return "tuba"; if (p < 64) return "horn";
      if (p < 68) return "clarinet"; if (p === 68 || p === 69) return "oboe"; if (p === 70) return "bassoon"; if (p === 71) return "clarinet";
      if (p < 80) return "flute"; if (p < 104) return pitch >= 58 ? "violins" : "cellos"; if (p < 120) return "harp"; return "violins";
    },
  };
  const instOf = MAPS[CFG.variant];
  const MIX = { piano_soft: 1.0, piano_loud: 0.9, epiano: 0.7, vibes: 0.6, organ: 0.45, nylon: 0.75, jguitar: 0.7, bass: 1.0,
                strings: 0.42, trumpet: 0.5, alto: 0.55, tenor: 0.6, flute: 0.55, kit_jazz: 0.75, kit_brush: 0.85, kit_latin: 0.6,
                violins: 0.55, violas: 0.5, cellos: 0.55, basses: 0.55, harp: 0.65, oboe: 0.5, clarinet: 0.55, bassoon: 0.5,
                horn: 0.45, trombone: 0.45, tuba: 0.45, timpani: 0.6, glock: 0.4, choir: 0.4, kit_orch: 0.6 };
  const ATTACK = { strings: 0.08, violins: 0.07, violas: 0.07, cellos: 0.07, basses: 0.06, choir: 0.12, organ: 0.02,
                   flute: 0.03, oboe: 0.03, clarinet: 0.03, bassoon: 0.03, horn: 0.04, trumpet: 0.02, trombone: 0.03, tuba: 0.03,
                   alto: 0.02, tenor: 0.02 };
  // 악기 자리(왼 -1 ~ 오른 +1): 무대에 앉은 것처럼 펼쳐서 섞여도 뭉개지지 않게. 피아노는 낮은 음 왼쪽·높은 음 오른쪽
  const PAN = { epiano: -0.15, vibes: -0.35, organ: -0.2, nylon: 0.3, jguitar: 0.35, bass: 0.05, strings: -0.1, trumpet: 0.3,
                alto: -0.3, tenor: -0.25, flute: -0.25, violins: -0.4, violas: -0.12, cellos: 0.25, basses: 0.38, harp: -0.45,
                oboe: -0.15, clarinet: 0.15, bassoon: 0.22, horn: -0.28, trombone: 0.3, tuba: 0.38, timpani: 0.1, glock: -0.3 };
  const colorOf = (n) => n.startsWith("piano") ? "#4ade80" : n.startsWith("kit") ? "#a1a1aa" : n === "bass" || n === "basses" ? "#f59e0b"
    : /violin|viola|cello|string/.test(n) ? "#60a5fa" : /trumpet|horn|trombone|tuba/.test(n) ? "#f87171"
    : /alto|tenor|clarinet|oboe|bassoon/.test(n) ? "#e879f9" : n === "flute" ? "#c084fc" : /guitar|nylon/.test(n) ? "#fb923c"
    : /vibes|glock/.test(n) ? "#38bdf8" : n === "organ" ? "#facc15" : n === "harp" ? "#93c5fd" : "#2dd4bf";

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
      const name = instOf(p, pitch, vel), b = this.bank[name]; if (!b) return;
      let best = b.list[0];
      for (const s of b.list) if (Math.abs(s.note - pitch) < Math.abs(best.note - pitch)) best = s;
      const drum = name.startsWith("kit_");
      if (drum && best.note !== pitch && Math.abs(best.note - pitch) > 2) return;
      const ac = this.ac, src = ac.createBufferSource(), g = ac.createGain();
      src.buffer = best.buf;
      if (!drum) src.playbackRate.value = Math.pow(2, (pitch - best.note) / 12);
      const amp = MIX[name] * best.g * Math.pow(vel / 100, 1.6) * 0.32 * k, a = ATTACK[name] || 0.004;
      const end = drum ? t + best.buf.duration : t + Math.max(dur, 0.05);
      g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(amp, t + a);
      g.gain.setValueAtTime(amp, end); g.gain.setTargetAtTime(0, end, b.rel / 3);
      const pan = name.startsWith("piano") ? Math.max(-0.3, Math.min(0.3, (pitch - 64) / 90)) : PAN[name] || 0;
      if (pan && ac.createStereoPanner) { const pn = ac.createStereoPanner(); pn.pan.value = pan; src.connect(g).connect(pn).connect(this.dest); }
      else src.connect(g).connect(this.dest);
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
  // 사람처럼 연주: 모델 세기가 평평하면(세기 없는 악보로 배운 버릇) 박 강약·4마디 숨결·높은 음 살짝으로 세기를 만들고,
  // 세기가 살아 있으면 숨결만 조금. 시간은 몇 ms 흔들어 기계 박자 느낌을 뺀다.
  let rs = 1;
  const rand = () => { rs = (rs * 1103515245 + 12345) & 0x7fffffff; return rs / 0x7fffffff; };
  function express(b, qpm) {
    const beat = head.Q, nb = Math.max(1, Math.round(b.barLen / beat)), ph = ((b.idx || 0) % 4 + 0.5) / 4;
    const vs = b.notes.filter((n) => n[1] !== 128).map((n) => n[4]);
    const m = vs.reduce((a, x) => a + x, 0) / Math.max(1, vs.length);
    const sd = Math.sqrt(vs.reduce((a, x) => a + (x - m) ** 2, 0) / Math.max(1, vs.length));
    const flat = sd < 6, arc = (flat ? 9 : 4) * (Math.sin(Math.PI * ph) - 0.5);
    // 느린 곡의 피아노는 페달: 다음 피아노 음이 나올 때까지(최대 반 마디) 울림을 이어 둠 → 치고 나서 뚝 끊기는 정적이 없게
    const pedal = (qpm || 120) <= 100, pOn = [...new Set(b.notes.filter((n) => n[1] < 8).map((n) => n[0]))].sort((x, y) => x - y);
    return b.notes.map(([pos, p, pitch, dur, vel]) => {
      if (pedal && p < 8) { const nx = pOn.find((q) => q > pos) ?? b.barLen; dur = Math.max(dur, Math.min(nx - pos, b.barLen / 2) + 2); }
      let v = vel, dt;
      if (p === 128) { v += (rand() - 0.5) * 10; dt = (rand() - 0.5) * 0.006; }
      else {
        const strong = pos === 0 || (nb === 4 && pos === 2 * beat), onBeat = pos % beat === 0;
        if (flat) v += (strong ? 7 : onBeat ? 2 : -4) + (pitch - 60) * 0.2;
        v += arc + (rand() - 0.5) * (flat ? 10 : 6);
        dt = (rand() - 0.5) * 0.014;
      }
      return [pos, p, pitch, dur, Math.max(10, Math.min(124, v)), dt];
    });
  }
  let barsOn = [], redo = 0, made = 0;
  function scheduleBar(b, t0) {
    const k = spt(), og = overlapGain(b.notes);
    barsOn.push({ t0, t1: t0 + b.barLen * k, chords: b.chords || [] }); if (barsOn.length > 32) barsOn.shift();
    for (const [pos, p, pitch, dur, vel, dt] of express(b, S.qpm)) {
      const t = Math.max(t0, t0 + pos * k + dt), d = dur * k;
      synth.play(p, pitch, t, d, vel, og);
      roll.push({ t, d, pitch, c: colorOf(instOf(p, pitch, vel)) });
    }
    if (roll.length > 3000) roll = roll.slice(-2000);
    window.__stats.bars++;
    played.push({ idx: b.idx, notes: b.notes, barLen: b.barLen, qpm: S.qpm, sit: S.custom ? "직접" : SIT[S.sit][0] });
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
    const msg = { epoch, conds: conds(), progs: progs(), temp: S.temp, spec: spec() };
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
    G.wet.gain.setTargetAtTime(!S.custom && SIT[S.sit][4] <= -6 ? 0.3 : 0.22, ac.currentTime, 0.6);
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
        else if (m.type === "bar") { if (m.epoch === epoch) { queue.push(m.bar); tps = m.tps; redo = m.redo; made = m.made; worker.postMessage({ type: "ahead", n: queue.length }); } }
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
    document.querySelectorAll("[data-swing]").forEach((b) => b.classList.toggle("sel", +b.dataset.swing === S.swing));
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
    document.querySelectorAll("[data-swing]").forEach((b) => b.onclick = () => { S.swing = +b.dataset.swing; changed(); });
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
    const st = ready ? `AI 엔진 ${engineKind === "wasm" ? "WASM" : "JS"} · 초당 ${tps.toFixed(0)}낱말 · 앞으로 ${aheadSec().toFixed(1)}초 준비됨 · 같은 마디 다시 쓰기 ${redo}/${made}` : "아직 시작 전";
    const cur = barsOn.find((b) => b.t0 <= now && now < b.t1);
    $("#chord").textContent = cur && cur.chords.length ? "코드  " + cur.chords.join("  →  ") : "";
    window.__stats.redo = redo; window.__stats.made = made;
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
      for (const [pos, p, pitch, dur, vel, dt] of express(b, b.qpm)) if (t + pos * k < sec) sy.play(p, pitch, Math.max(t, t + pos * k + dt), dur * k, vel, og);
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

  document.title = CFG.title; $("h1").textContent = CFG.title;
  fromPreset(0); buildUI(); render(); requestAnimationFrame(draw);
  window.__ctl = { press: (i) => document.querySelectorAll(".mood")[i].click(), play: togglePlay };
})();
