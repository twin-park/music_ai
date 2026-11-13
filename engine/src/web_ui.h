// web/index.html 에서 만듦 (tools/embed_web.py) — 손으로 고치지 말 것
#pragma once
static const char *WEB_UI = R"WEB(<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>차량 BGM AI</title>
<style>
:root{--bg:#0f1114;--card:#1a1d22;--card2:#23272e;--text:#f2f4f6;--sub:#8b95a1;--line:#2c3138;--green:#22c55e;--green2:#16a34a;--glow:rgba(34,197,94,.14)}
:root[data-theme=light]{--bg:#f4f5f7;--card:#fff;--card2:#eef0f3;--text:#191f28;--sub:#6b7684;--line:#e5e8eb;--green:#16a34a;--green2:#15803d;--glow:rgba(22,163,74,.10)}
*{box-sizing:border-box;margin:0;padding:0}
html,body{background:var(--bg);color:var(--text);font-family:"Pretendard","Apple SD Gothic Neo","Malgun Gothic",system-ui,sans-serif;-webkit-font-smoothing:antialiased}
body{min-height:100vh;display:flex;justify-content:center}
main{width:100%;max-width:560px;padding:28px 16px 40px}
.wrap{display:block}
.side{margin-top:12px}
details.box{background:var(--card);border-radius:16px;padding:6px 16px 10px}
details.box summary{list-style:none;cursor:pointer;display:flex;justify-content:space-between;align-items:center;padding:10px 0;font-size:15px;font-weight:600}
details.box summary::-webkit-details-marker{display:none}
details.box summary span{color:var(--sub);font-weight:400;font-size:13px}
.knob{padding:9px 0 7px;border-top:1px solid var(--line)}
.knob:first-of-type{border-top:0}
.kh{display:flex;justify-content:space-between;align-items:baseline;font-size:14px}
.kh b{font-weight:600}
.kh em{font-style:normal;color:var(--green);font-size:13px;font-variant-numeric:tabular-nums}
.kh em.base{color:var(--sub)}
.knob input{width:100%;accent-color:var(--green);margin:8px 0 2px}
.ends{display:flex;justify-content:space-between;color:var(--sub);font-size:12px}
.reset{background:none;border:0;color:var(--sub);font-size:13px;cursor:pointer;padding:8px 0 4px}
.reset:hover{color:var(--text)}
.pend{color:var(--green);font-size:12px;min-height:16px;padding-top:2px}
@media (min-width:900px){
  main{max-width:980px;padding:28px 28px 40px}
  .wrap{display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:28px;align-items:start}
  .side{margin-top:22px;position:sticky;top:20px;max-height:calc(100vh - 40px);overflow:auto}
}
h1{font-size:25px;font-weight:700;line-height:1.35;letter-spacing:-.3px;margin-top:26px}
.top{display:flex;justify-content:space-between;align-items:center;gap:8px;color:var(--sub);font-size:14px}
.top .r{display:flex;align-items:center;gap:6px}
.seg{display:flex;background:var(--card);border-radius:12px;padding:3px}
.seg button{background:none;border:0;color:var(--sub);font-size:14px;font-weight:600;padding:7px 12px;border-radius:9px;cursor:pointer}
.seg button.on{background:var(--card2);color:var(--text)}
.ic{background:none;border:0;color:var(--sub);font-size:18px;cursor:pointer;padding:6px;border-radius:8px}
.now{background:var(--card);border-radius:20px;padding:20px;margin-top:22px;display:flex;align-items:center;gap:16px}
.now.off{display:none}
.eq{display:flex;gap:3px;align-items:flex-end;height:26px;flex:none}
.eq i{width:4px;background:var(--green);border-radius:2px;animation:eq 1s ease-in-out infinite}
.eq i:nth-child(2){animation-delay:.2s}.eq i:nth-child(3){animation-delay:.4s}.eq i:nth-child(4){animation-delay:.1s}
@keyframes eq{0%,100%{height:6px}50%{height:24px}}
.eq.paused i{animation:none;height:6px}
.nw{flex:1;min-width:0}
.nw b{display:block;font-size:19px;font-weight:700}
.nw span{display:block;color:var(--sub);font-size:14px;margin-top:3px;font-variant-numeric:tabular-nums}
.end{background:var(--card2);border:0;color:var(--text);border-radius:12px;padding:11px 14px;font-size:15px;font-weight:600;cursor:pointer;flex:none}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:22px}
.tile{background:var(--card);border:1.5px solid var(--line);border-radius:16px;padding:22px 6px;font-size:16px;font-weight:600;color:var(--text);cursor:pointer;text-align:center;transition:transform .1s,border-color .15s,background .15s;word-break:keep-all}
.tile:hover{border-color:var(--green)}
.tile:active{transform:scale(.97)}
.tile.on{border-color:var(--green);background:var(--glow)}
.tile.wait{border-color:var(--green);border-style:dashed}
.ctl{display:flex;align-items:center;gap:12px;margin-top:24px;background:var(--card);border-radius:16px;padding:14px 16px}
.ctl input[type=range]{flex:1;accent-color:var(--green)}
.ctl label{color:var(--sub);font-size:14px;flex:none}
.tg{background:none;border:1px solid var(--line);color:var(--sub);border-radius:10px;padding:8px 10px;font-size:13px;cursor:pointer;flex:none}
.tg.on{border-color:var(--green);color:var(--green)}
.row{display:flex;gap:8px;margin-top:12px}
.chip{flex:1;background:none;border:1px solid var(--line);color:var(--sub);border-radius:12px;padding:11px 6px;font-size:14px;cursor:pointer}
.chip:hover{color:var(--text)}
.chip.on{border-color:var(--green);color:var(--green);background:var(--glow)}
pre{margin-top:12px;background:var(--card);border-radius:14px;padding:14px;font:12.5px/1.55 ui-monospace,Consolas,monospace;max-height:44vh;overflow:auto;white-space:pre;color:var(--text)}
.info{margin-top:12px;background:var(--card);border-radius:14px;padding:14px 16px;font-size:14px;line-height:1.6;color:var(--sub)}
.info b{color:var(--text);font-weight:600}
.hide{display:none!important}
/* 알아서 */
.go{display:block;width:100%;margin-top:22px;background:var(--green);color:#fff;border:0;border-radius:16px;padding:18px;font-size:17px;font-weight:700;cursor:pointer}
.go:active{transform:scale(.99)}
.why{background:var(--card);border-radius:18px;padding:18px 18px 16px;margin-top:22px}
.why .hd{display:flex;justify-content:space-between;align-items:center;color:var(--sub);font-size:13px}
.why .ln{font-size:18px;font-weight:700;line-height:1.5;margin-top:8px;word-break:keep-all}
.why .ln em{font-style:normal;color:var(--green)}
.ib{background:none;border:1px solid var(--line);color:var(--sub);width:24px;height:24px;border-radius:50%;font-size:12px;font-weight:700;cursor:pointer;flex:none}
.ib.on{border-color:var(--green);color:var(--green)}
.tags{display:flex;flex-wrap:wrap;gap:6px;margin-top:12px}
.tags span{background:var(--card2);color:var(--sub);border-radius:8px;padding:5px 9px;font-size:13px}
.say{display:flex;gap:8px;margin-top:12px;background:var(--card);border-radius:16px;padding:8px}
.say input{flex:1;min-width:0;background:none;border:0;color:var(--text);font-size:16px;padding:8px 8px;outline:none}
.say input::placeholder{color:var(--sub)}
.say button{background:var(--card2);border:0;color:var(--text);border-radius:11px;padding:0 14px;font-size:15px;font-weight:600;cursor:pointer;flex:none}
.say button.mic.on{background:var(--green);color:#fff}
.reply{color:var(--green);font-size:14px;min-height:20px;padding:8px 4px 0}
/* 상황 판 (시연) */
.pre{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:2px 0 6px}
.pre button{background:var(--card2);border:1.5px solid transparent;color:var(--text);border-radius:12px;padding:12px 8px;font-size:14px;font-weight:600;cursor:pointer;word-break:keep-all;line-height:1.35}
.pre button.on{border-color:var(--green);background:var(--glow)}
.grp{padding:10px 0 4px;border-top:1px solid var(--line)}
.grp:first-of-type{border-top:0}
.grp b{display:block;font-size:13px;font-weight:600;margin-bottom:7px}
.pills{display:flex;flex-wrap:wrap;gap:6px}
.pills button{background:none;border:1px solid var(--line);color:var(--sub);border-radius:999px;padding:6px 11px;font-size:13.5px;cursor:pointer}
.pills button:hover{color:var(--text)}
.pills button.on{border-color:var(--green);color:var(--green);background:var(--glow)}
.pills button.auto{border-style:dashed;border-color:var(--green);color:var(--green)}
.mrow{display:flex;align-items:center;gap:10px;padding:12px 0 4px;border-top:1px solid var(--line)}
.meter{flex:1;height:6px;background:var(--card2);border-radius:3px;overflow:hidden}
.meter i{display:block;height:100%;width:0;background:var(--green);transition:width .1s}
.note{color:var(--sub);font-size:12.5px;line-height:1.55;padding:6px 0 2px}
@media (max-width:400px){.tile{font-size:15px;padding:20px 4px}h1{font-size:22px}.why .ln{font-size:17px}.seg button{padding:7px 9px;font-size:13px}}
</style>
</head>
<body>
<main>
  <div class="top">
    <span>차량 BGM AI</span>
    <div class="r">
      <div class="seg" id="seg"><button data-m="auto">🤖 알아서</button><button data-m="hand">✋ 직접</button></div>
      <button class="ic" id="theme" title="화면 밝기">◐</button>
    </div>
  </div>

  <div class="now off" id="now">
    <div class="eq" id="eq"><i></i><i></i><i></i><i></i></div>
    <div class="nw"><b id="nm"></b><span id="sub"></span></div>
    <button class="end" id="end">끝내기</button>
  </div>

  <div class="wrap">
  <div>
    <!-- 🤖 알아서: 상황을 보고 AI 가 고름 -->
    <div id="autoMain">
      <div id="startBox">
        <h1>상황에 맞춰<br>알아서 틀어 줄게요</h1>
        <button class="go" id="go">시작</button>
      </div>
      <div class="why hide" id="why">
        <div class="hd"><span>지금 이렇게 골랐어요</span><button class="ib" id="whyI" title="왜 그런지">i</button></div>
        <div class="ln" id="line"></div>
        <div class="tags hide" id="tags"></div>
      </div>
      <div class="say">
        <button class="mic hide" id="mic" title="말로 하기">🎙</button>
        <input id="sayIn" placeholder="말로 요청 · 예: 아기 잔다" autocomplete="off">
        <button id="sayGo">보내기</button>
      </div>
      <div class="reply" id="reply"></div>
    </div>

    <!-- ✋ 직접: 분위기 고르기 -->
    <div id="handMain" class="hide">
      <h1 id="ask">어떤 분위기로<br>시작할까요?</h1>
      <div class="grid" id="moods"></div>
      <div class="row">
        <button class="chip" id="a-sea">🌊 바닷가 파도</button>
        <button class="chip" id="a-rain">🌧 빗소리</button>
      </div>
    </div>

    <div class="ctl">
      <label>소리</label><input type="range" id="vol" min="0" max="100" value="80">
      <button class="tg" id="duck">📞 통화 중</button>
    </div>
    <div class="row">
      <button class="chip" id="b-score">악보 보기 ▼</button>
      <button class="chip" id="b-info">ⓘ 지금 편성</button>
      <button class="chip" id="b-folder">악보 폴더</button>
    </div>
    <div class="info hide" id="info"></div>
    <pre class="hide" id="score"></pre>
  </div>

  <div class="side">
    <details class="box" id="sitBox">
      <summary>상황 바꿔 보기 · 시연 <span id="ssum">▼</span></summary>
      <div class="pre" id="presets"></div>
      <div id="groups"></div>
      <div class="mrow">
        <button class="tg" id="talkMic">🎙 차 안 말소리 듣기</button>
        <div class="meter"><i id="talkBar"></i></div>
      </div>
      <div class="note hide" id="talkNote">말소리가 커지면 음악을 줄이고, 말과 겹치는 소리를 비워요. 음악이 스피커로 나오면 그만큼은 빼고 들어요.</div>
      <button class="reset" id="sitReset">상황 모두 지우기</button>
    </details>
    <details class="box hide" id="tune">
      <summary>세부 조절 <span id="tsum">▼</span></summary>
      <div id="knobs"></div>
      <div class="pend" id="pend"></div>
      <button class="reset" id="reset">원래대로</button>
    </details>
  </div>
  </div>
</main>
<script>
const $ = id => document.getElementById(id);
const api = (p, body) => fetch(p, body ? {method: "POST", body: JSON.stringify(body)} : {}).then(r => r.json());
const esc = s => String(s).replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
let MOODS = [], S = {}, wantMood = null, showScore = false, mode = null;
const store = {get: k => { try { return localStorage.getItem(k); } catch (e) { return null; } }, set: (k, v) => { try { localStorage.setItem(k, v); } catch (e) {} }};
if (store.get("theme")) document.documentElement.dataset.theme = store.get("theme");
$("theme").onclick = () => {
  const t = document.documentElement.dataset.theme === "light" ? "dark" : "light";
  document.documentElement.dataset.theme = t; store.set("theme", t);
};
const fmt = s => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
const wide = () => window.matchMedia("(min-width:900px)").matches;

// ── 알아서 / 직접 ──
function setMode(m, send) {
  if (m === mode) return;
  mode = m;
  document.querySelectorAll("#seg button").forEach(b => b.classList.toggle("on", b.dataset.m === m));
  $("autoMain").classList.toggle("hide", m !== "auto");
  $("handMain").classList.toggle("hide", m !== "hand");
  $("sitBox").classList.toggle("hide", m !== "auto");
  $("tune").classList.toggle("hide", m !== "hand");
  $("duck").classList.toggle("hide", m === "auto");                       // 알아서: 통화는 상황(차 안 소리)으로
  if (send) api("/api/auto", {on: m === "auto" ? 1 : 0}).catch(() => {});
}
document.querySelectorAll("#seg button").forEach(b => b.onclick = () => setMode(b.dataset.m, true));
let goAt = 0;
$("go").onclick = () => { goAt = Date.now(); $("go").textContent = "상황 보는 중…"; api("/api/auto", {start: 1}).catch(() => {}); };

api("/api/moods").then(ms => {
  MOODS = ms;
  $("moods").innerHTML = ms.map(m => `<button class="tile" data-id="${esc(m.id)}">${esc(m.name)}</button>`).join("");
  document.querySelectorAll(".tile").forEach(b => b.onclick = () => {
    wantMood = b.dataset.id; draw();
    api("/api/mood", {id: b.dataset.id});
  });
});

function draw() {
  const on = S.playing;
  if (S.conductor === false) $("seg").classList.add("hide");
  if (S.auto !== undefined && Date.now() - modeTouched > 1500) setMode(S.auto ? "auto" : "hand", false);
  $("now").classList.toggle("off", !on && !S.ending);
  $("eq").classList.toggle("paused", !on);
  $("ask").innerHTML = on ? "지금 분위기를<br>바꿀까요?" : "어떤 분위기로<br>시작할까요?";
  if (on || S.ending) {
    $("nm").textContent = S.name || "준비 중";
    $("sub").textContent = [S.role, S.key && S.key + "조", S.bpm && "♩=" + S.bpm, fmt(S.t || 0)].filter(Boolean).join(" · ");
  }
  $("end").textContent = S.ending ? "바로 끄기" : "끝내기";
  // 알아서: 시작 전엔 시작 단추 하나, 연주 중엔 '왜 이렇게' 한 줄
  $("startBox").classList.toggle("hide", !!(on || S.ending));
  if (!on && !S.ending) $("go").textContent = Date.now() - goAt < 8000 ? "상황 보는 중…" : "시작";
  $("why").classList.toggle("hide", !(on || S.ending));
  const d = S.dec || {};
  if (d.line !== undefined) {
    const parts = d.line.split(" → ");
    const last = parts.pop();
    $("line").innerHTML = (parts.length ? esc(parts.join(" → ")) + " → " : "") + `<em>${esc(last)}</em>`;
    $("tags").innerHTML = (d.because || []).map(b => `<span>${esc(b)}</span>`).join("");
  }
  if (wantMood && S.mood === wantMood) wantMood = null;
  document.querySelectorAll(".tile").forEach(b => {
    b.classList.toggle("on", on && b.dataset.id === S.mood && !wantMood);
    b.classList.toggle("wait", b.dataset.id === wantMood);
  });
  const m = MOODS.find(x => x.id === S.mood);
  $("info").innerHTML = m ? `<b>${esc(m.name)}</b><br><b>편성</b> ${esc(m.band)}<br><b>공식</b> ${esc(m.recipe)}` : "아직 연주 중이 아니에요";
  $("duck").classList.toggle("on", !!S.duck);
  if (S.amb && Date.now() - ambTouched > 1500) { $("a-sea").classList.toggle("on", S.amb.sea > 0); $("a-rain").classList.toggle("on", S.amb.rain > 0); }
  if (!mic) $("talkBar").style.width = Math.round((S.talk || 0) * 100) + "%";
}
let modeTouched = 0;
document.querySelectorAll("#seg button").forEach(b => b.addEventListener("click", () => modeTouched = Date.now()));
function poll() {
  api("/api/state").then(s => { if (S.vol === undefined) $("vol").value = Math.round(s.vol * 100); S = s; draw(); syncKnobs(s.params, s.pending); }).catch(() => {});
  if (showScore) fetch("/api/score").then(r => r.text()).then(t => { const p = $("score"); const atEnd = p.scrollTop + p.clientHeight >= p.scrollHeight - 30; p.textContent = t || "(아직 없음)"; if (atEnd) p.scrollTop = p.scrollHeight; }).catch(() => {});
}
setInterval(poll, 600); poll();
setInterval(() => fetch("/api/ping").catch(() => {}), 5000); fetch("/api/ping");

$("end").onclick = () => api(S.ending ? "/api/stop" : "/api/end", {});
$("vol").oninput = e => api("/api/volume", {v: e.target.value / 100});
$("duck").onclick = () => api("/api/duck", {on: S.duck ? 0 : 1}).then(poll);
$("whyI").onclick = () => { $("tags").classList.toggle("hide"); $("whyI").classList.toggle("on"); };
let ambTouched = 0;
["sea", "rain"].forEach(k => $("a-" + k).onclick = () => {
  const b = $("a-" + k), on = !b.classList.contains("on");
  b.classList.toggle("on", on); ambTouched = Date.now();
  api("/api/amb", {[k]: on ? 1 : 0}).catch(() => {});
});
$("b-score").onclick = () => { showScore = !showScore; $("score").classList.toggle("hide", !showScore); $("b-score").textContent = showScore ? "악보 접기 ▲" : "악보 보기 ▼"; poll(); };
$("b-info").onclick = () => $("info").classList.toggle("hide");
$("b-folder").onclick = () => api("/api/open", {}).then(r => { if (!navigator.userAgent.includes("Windows")) alert(r.path); });

// ── 말로 요청 ──
let replyT = 0;
function say(text) {
  text = (text || "").trim(); if (!text) return;
  $("sayIn").value = "";
  api("/api/say", {text}).then(r => {
    $("reply").textContent = `"${text}" → ${r.say}`;
    clearTimeout(replyT); replyT = setTimeout(() => $("reply").textContent = "", 9000);
    setTimeout(poll, 300);
  }).catch(() => {});
}
$("sayGo").onclick = () => say($("sayIn").value);
$("sayIn").onkeydown = e => { if (e.key === "Enter" && !e.isComposing) say($("sayIn").value); };
const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
if (SpeechRec) {
  $("mic").classList.remove("hide");
  let rec = null;
  $("mic").onclick = () => {
    if (rec) { rec.stop(); return; }
    rec = new SpeechRec(); rec.lang = "ko-KR"; rec.interimResults = true;
    $("mic").classList.add("on");
    rec.onresult = e => { const r = e.results[e.results.length - 1]; $("sayIn").value = r[0].transcript; if (r.isFinal) say(r[0].transcript); };
    rec.onend = rec.onerror = () => { rec = null; $("mic").classList.remove("on"); };
    rec.start();
  };
}

// ── 상황 판 (실제 차에선 내비 · 날씨 · 센서 · 마이크가 보냄) ──
const GROUPS = [
  ["trip.kind", "여정", [["commute", "출근"], ["homeward", "퇴근"], ["school_run", "등하원"], ["outing", "나들이"], ["long_trip", "장거리"], ["late_home", "심야 귀가"], ["hurry", "급한 이동"], ["joyride", "드라이브"]]],
  ["time.group", "요일", [["mon", "월요일"], ["midweek", "주중"], ["fri", "금요일"], ["weekend", "주말"], ["holiday", "연휴"]]],
  ["time.slot", "시간대", [["dawn", "새벽"], ["morning", "아침"], ["day", "낮"], ["dusk", "해 질 녘"], ["evening", "저녁"], ["night", "밤"], ["latenight", "심야"]]],
  ["weather.kind", "날씨", [["clear", "맑음"], ["cloudy", "흐림"], ["rain", "비"], ["storm", "폭우"], ["snow", "눈"], ["fog", "안개"], ["heat", "폭염"], ["cold", "한파"]]],
  ["place.kind", "장소", [["city", "도심"], ["residential", "주택가"], ["highway", "고속도로"], ["country_road", "국도"], ["coast", "바닷가"], ["mountain", "산길"], ["river", "강변"], ["tunnel", "터널"], ["school_zone", "어린이보호구역"]]],
  ["drive.state", "달리기", [["stopped", "신호 대기"], ["jam", "정체"], ["slow", "저속"], ["cruise", "순항"], ["fast", "고속"], ["speeding", "과속"]]],
  ["people.group", "누구랑", [["alone", "혼자"], ["partner", "연인"], ["family", "가족"], ["friends", "친구들"], ["elders", "부모님"], ["business", "손님"]]],
  ["people.baby", "아기", [["awake", "깸"], ["sleeping", "잠듦"], ["crying", "울음"]]],
  ["cabin.sound", "차 안 소리", [["quiet", "조용"], ["talk", "대화"], ["laugh", "웃음"], ["singing", "따라 부름"], ["argument", "언성"], ["call_car", "통화"], ["yawn", "하품"]]],
  ["car.windows", "창문", [["closed", "닫힘"], ["open", "열림"]]],
];
const PRESETS = [
  ["비 오는 월요일 출근", {time: {group: "mon", slot: "morning"}, trip: {kind: "commute"}, weather: {kind: "rain"}, place: {kind: "city"}, drive: {state: "cruise"}, people: {group: "alone"}, car: {windows: "closed"}, cabin: {sound: "quiet"}}],
  ["주말 가족 바닷길", {time: {group: "weekend", slot: "morning"}, trip: {kind: "outing"}, weather: {kind: "clear"}, place: {kind: "coast"}, drive: {state: "cruise"}, people: {group: "family", baby: "awake"}, car: {windows: "closed"}, cabin: {sound: "quiet"}}],
  ["금요일 밤 둘이 · 비", {time: {group: "fri", slot: "night"}, trip: {kind: "homeward"}, weather: {kind: "rain"}, place: {kind: "city"}, drive: {state: "cruise"}, people: {group: "partner"}, car: {windows: "closed"}, cabin: {sound: "quiet"}}],
  ["심야 고속도로 혼자", {time: {group: "midweek", slot: "latenight"}, trip: {kind: "late_home"}, weather: {kind: "clear"}, place: {kind: "highway"}, drive: {state: "fast"}, people: {group: "alone"}, car: {windows: "closed", drive_min: 40}, cabin: {sound: "quiet"}}],
];
$("presets").innerHTML = PRESETS.map(([n], i) => `<button data-i="${i}">${esc(n)}</button>`).join("");
$("groups").innerHTML = GROUPS.map(([p, n, vs]) => `<div class="grp"><b>${esc(n)}</b><div class="pills" data-p="${p}">` +
  vs.map(([v, l]) => `<button data-v="${v}">${esc(l)}</button>`).join("") + `</div></div>`).join("");
const patchOf = (path, v) => { const [a, b] = path.split("."); const o = {[a]: {[b]: v}}; if (path === "drive.state") o.drive.speed = null; return o; };
let SIT = {}, sitTouched = 0, preOn = -1;
const getp = (o, path) => path.split(".").reduce((x, k) => x && x[k], o);
function drawSit(sent) {
  document.querySelectorAll("#groups .pills").forEach(g => {
    const p = g.dataset.p, v = getp(SIT, p), mine = sent ? getp(sent, p) : v;
    g.querySelectorAll("button").forEach(b => {
      b.classList.toggle("on", b.dataset.v === v && mine !== undefined);
      b.classList.toggle("auto", b.dataset.v === v && mine === undefined);    // 지휘자가 시계 · 속도로 채운 칸
    });
  });
  document.querySelectorAll("#presets button").forEach(b => b.classList.toggle("on", +b.dataset.i === preOn));
}
let SENT = {};
function sendSit(patch) {
  sitTouched = Date.now();
  const merge = (a, b) => { for (const k in b) { if (b[k] === null) delete a[k]; else if (typeof b[k] === "object" && !Array.isArray(b[k])) { a[k] = a[k] || {}; merge(a[k], b[k]); } else a[k] = b[k]; } return a; };
  merge(SENT, JSON.parse(JSON.stringify(patch))); merge(SIT, JSON.parse(JSON.stringify(patch)));
  drawSit(SENT);
  return api("/api/situation", patch).then(() => setTimeout(pollSit, 400)).catch(() => {});
}
document.querySelectorAll("#groups .pills").forEach(g => g.onclick = e => {
  const b = e.target.closest("button"); if (!b) return;
  const p = g.dataset.p, cur = getp(SENT, p);
  preOn = -1;
  sendSit(patchOf(p, cur === b.dataset.v ? null : b.dataset.v));             // 같은 걸 다시 누르면 지움
});
document.querySelectorAll("#presets button").forEach(b => b.onclick = () => {
  preOn = +b.dataset.i; SENT = {}; SIT = {};
  fetch("/api/situation/reset", {method: "POST", body: "{}"}).then(() => sendSit(PRESETS[preOn][1]));
});
$("sitReset").onclick = () => { preOn = -1; SENT = {}; SIT = {}; drawSit(SENT); fetch("/api/situation/reset", {method: "POST", body: "{}"}).then(pollSit); };
function pollSit() {
  if (mode !== "auto" || !$("sitBox").open) return;
  api("/api/situation").then(s => { if (Date.now() - sitTouched > 800) { SIT = s; drawSit(SENT); } }).catch(() => {});
}
setInterval(pollSit, 2000);
if (wide() || store.get("sitOpen") === "1") $("sitBox").open = true;
$("sitBox").ontoggle = () => { $("ssum").textContent = $("sitBox").open ? "▲" : "▼"; store.set("sitOpen", $("sitBox").open ? "1" : "0"); pollSit(); };
api("/api/situation").then(s => { SIT = s; SENT = JSON.parse(JSON.stringify(s)); if (SENT.time) { delete SENT.time.slot; delete SENT.time.group; } if (SENT.drive && SENT.drive.speed !== undefined) delete SENT.drive.state; drawSit(SENT); }).catch(() => {});

// ── 차 안 말소리 (마이크) → cabin.talk 0~1 · 오래 이어지면 '대화' ──
//   스피커로 나오는 우리 음악은 /api/level 의 크기만큼 빼고 들음 (말없을 때 마이크와 음악의 차이를 배워 둠)
let mic = null;
if (!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia)) $("talkMic").classList.add("hide");
$("talkMic").onclick = async () => {
  if (mic) { micOff(); return; }
  try {
    const st = await navigator.mediaDevices.getUserMedia({audio: {echoCancellation: true, noiseSuppression: false, autoGainControl: false}});
    const ac = new (window.AudioContext || window.webkitAudioContext)();
    const src = ac.createMediaStreamSource(st);
    const hp = ac.createBiquadFilter(); hp.type = "highpass"; hp.frequency.value = 250;
    const lp = ac.createBiquadFilter(); lp.type = "lowpass"; lp.frequency.value = 3400;
    const an = ac.createAnalyser(); an.fftSize = 2048;
    src.connect(hp); hp.connect(lp); lp.connect(an);
    const buf = new Float32Array(an.fftSize);
    let outDb = -90, gap = null, floor = null, lvl = 0, sent = -1, sentAt = 0, loudSince = 0, quietSince = 0;
    const lvT = setInterval(() => api("/api/level").then(r => outDb = r.out_db).catch(() => {}), 250);
    const t = setInterval(() => {
      an.getFloatTimeDomainData(buf);
      let e = 0; for (let i = 0; i < buf.length; i++) e += buf[i] * buf[i];
      const db = 10 * Math.log10(e / buf.length + 1e-12);
      const d = db - outDb;                                                   // 마이크 - 음악
      gap = gap === null ? d : d < gap ? gap + (d - gap) * .3 : gap + .02;       // 바닥은 빨리 · 위로는 천천히 따라감
      floor = floor === null ? db : db < floor ? floor + (db - floor) * .3 : floor + .02;
      const expect = Math.max(outDb + gap, floor);
      const x = Math.max(0, Math.min(1, (db - expect - 4) / 14));
      lvl = x > lvl ? lvl + (x - lvl) * .6 : lvl + (x - lvl) * .12;
      $("talkBar").style.width = Math.round(lvl * 100) + "%";
      const now = Date.now();
      if (Math.abs(lvl - sent) > .06 || (now - sentAt > 1000 && Math.abs(lvl - sent) > .01)) {
        sent = Math.round(lvl * 100) / 100; sentAt = now;
        api("/api/situation", {cabin: {talk: sent}}).catch(() => {});
      }
      const snd = getp(SENT, "cabin.sound");
      if (lvl > .35) { quietSince = 0; if (!loudSince) loudSince = now; if (now - loudSince > 1500 && (!snd || snd === "quiet")) sendSit({cabin: {sound: "talk"}}); }
      else if (lvl < .1) { loudSince = 0; if (!quietSince) quietSince = now; if (now - quietSince > 8000 && snd === "talk") sendSit({cabin: {sound: "quiet"}}); }
    }, 100);
    mic = {st, ac, t, lvT};
    $("talkMic").classList.add("on"); $("talkNote").classList.remove("hide");
  } catch (e) { $("talkNote").textContent = "마이크를 쓸 수 없어요 (" + e.name + ")"; $("talkNote").classList.remove("hide"); }
};
function micOff() {
  if (!mic) return;
  clearInterval(mic.t); clearInterval(mic.lvT); mic.st.getTracks().forEach(t => t.stop()); mic.ac.close();
  mic = null; $("talkMic").classList.remove("on"); $("talkNote").classList.add("hide");
  api("/api/situation", {cabin: {talk: null}}).catch(() => {});
}

// ── 세부 조절 (직접): -1 … +1 (가운데 = 분위기 기본). 울림은 바로, 나머지는 다음 2마디 덩어리부터 AI 가 다시 씀 ──
const KNOBS = [
  ["reg", "음 높이", "낮게", "높게"], ["tempo", "빠르기", "느리게", "빠르게"], ["dens", "음 수", "성기게", "촘촘하게"],
  ["energy", "세기", "잔잔하게", "힘차게"], ["novelty", "새로움", "익숙하게", "새롭게"], ["tension", "긴장감", "편안하게", "긴장되게"], ["space", "울림", "가깝게", "넓게"]];
let PV = {}, touched = 0;
$("knobs").innerHTML = KNOBS.map(([k, n, lo, hi]) => `<div class="knob"><div class="kh"><b>${n}</b><em id="v-${k}" class="base">기본</em></div>
  <input type="range" id="k-${k}" min="-100" max="100" value="0" step="1"><div class="ends"><span>${lo}</span><span>${hi}</span></div></div>`).join("");
const word = (k, v) => {
  const [, , lo, hi] = KNOBS.find(x => x[0] === k);
  const a = Math.abs(v);
  if (a < .1) return "기본";
  return (a < .45 ? "조금 " : a > .85 ? "아주 " : "") + (v < 0 ? lo : hi);
};
const showK = (k, v) => { const e = $("v-" + k); e.textContent = word(k, v); e.classList.toggle("base", Math.abs(v) < .1); };
const sendK = () => { touched = Date.now(); api("/api/params", PV).catch(() => {}); };
KNOBS.forEach(([k]) => {
  const el = $("k-" + k);
  el.oninput = () => {
    let v = el.value / 100; if (Math.abs(v) < .08) v = 0;
    PV[k] = v; showK(k, v);
    if (k === "space") sendK();
  };
  el.onchange = () => { if (Math.abs(el.value) < 8) el.value = 0; sendK(); };
});
$("reset").onclick = () => { KNOBS.forEach(([k]) => { PV[k] = 0; $("k-" + k).value = 0; showK(k, 0); }); sendK(); };
if (wide() || store.get("tuneOpen") === "1") $("tune").open = true;
$("tune").ontoggle = () => { $("tsum").textContent = $("tune").open ? "▲" : "▼"; store.set("tuneOpen", $("tune").open ? "1" : "0"); };
function syncKnobs(p, pending) {
  if (!p) return;
  if (Date.now() - touched > 1500) KNOBS.forEach(([k]) => { if (p[k] === undefined) return; PV[k] = p[k]; $("k-" + k).value = Math.round(p[k] * 100); showK(k, p[k]); });
  $("pend").textContent = pending && S.playing ? "다음 마디부터 바뀌어요" : "";
}
</script>
</body>
</html>
)WEB";
