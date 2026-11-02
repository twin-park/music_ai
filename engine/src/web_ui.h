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
.tune{background:var(--card);border-radius:16px;padding:6px 16px 10px}
.tune summary{list-style:none;cursor:pointer;display:flex;justify-content:space-between;align-items:center;padding:10px 0;font-size:15px;font-weight:600}
.tune summary::-webkit-details-marker{display:none}
.tune summary span{color:var(--sub);font-weight:400;font-size:13px}
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
  main{max-width:960px;padding:28px 28px 40px}
  .wrap{display:grid;grid-template-columns:minmax(0,1fr) 320px;gap:28px;align-items:start}
  .side{margin-top:22px;position:sticky;top:20px}
}
h1{font-size:25px;font-weight:700;line-height:1.35;letter-spacing:-.3px;margin-top:26px}
.top{display:flex;justify-content:space-between;align-items:center;color:var(--sub);font-size:14px}
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
pre{margin-top:12px;background:var(--card);border-radius:14px;padding:14px;font:12.5px/1.55 ui-monospace,Consolas,monospace;max-height:44vh;overflow:auto;white-space:pre;color:var(--text)}
.info{margin-top:12px;background:var(--card);border-radius:14px;padding:14px 16px;font-size:14px;line-height:1.6;color:var(--sub)}
.info b{color:var(--text);font-weight:600}
.hide{display:none}
@media (max-width:400px){.tile{font-size:15px;padding:20px 4px}h1{font-size:22px}}
</style>
</head>
<body>
<main>
  <div class="top"><span>차량 BGM AI</span><button class="ic" id="theme" title="화면 밝기">◐</button></div>

  <div class="now off" id="now">
    <div class="eq" id="eq"><i></i><i></i><i></i><i></i></div>
    <div class="nw"><b id="nm"></b><span id="sub"></span></div>
    <button class="end" id="end">끝내기</button>
  </div>

  <div class="wrap">
  <div>
  <h1 id="ask">어떤 분위기로<br>시작할까요?</h1>
  <div class="grid" id="moods"></div>

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
    <details class="tune" id="tune">
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
let MOODS = [], S = {}, wantMood = null, showScore = false;
try { const t = localStorage.getItem("theme"); if (t) document.documentElement.dataset.theme = t; } catch (e) {}
$("theme").onclick = () => {
  const t = document.documentElement.dataset.theme === "light" ? "dark" : "light";
  document.documentElement.dataset.theme = t;
  try { localStorage.setItem("theme", t); } catch (e) {}
};
const fmt = s => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

api("/api/moods").then(ms => {
  MOODS = ms;
  $("moods").innerHTML = ms.map(m => `<button class="tile" data-id="${m.id}">${m.name}</button>`).join("");
  document.querySelectorAll(".tile").forEach(b => b.onclick = () => {
    wantMood = b.dataset.id; draw();
    api("/api/mood", {id: b.dataset.id});
  });
});

function draw() {
  const on = S.playing;
  $("now").classList.toggle("off", !on && !S.ending);
  $("eq").classList.toggle("paused", !on);
  $("ask").innerHTML = on ? "지금 분위기를<br>바꿀까요?" : "어떤 분위기로<br>시작할까요?";
  if (on || S.ending) {
    $("nm").textContent = S.name || "준비 중";
    $("sub").textContent = [S.role, S.key && S.key + "조", S.bpm && "♩=" + S.bpm, fmt(S.t || 0)].filter(Boolean).join(" · ");
  }
  $("end").textContent = S.ending ? "바로 끄기" : "끝내기";
  if (wantMood && S.mood === wantMood) wantMood = null;
  document.querySelectorAll(".tile").forEach(b => {
    b.classList.toggle("on", on && b.dataset.id === S.mood && !wantMood);
    b.classList.toggle("wait", b.dataset.id === wantMood);
  });
  const m = MOODS.find(x => x.id === S.mood);
  $("info").innerHTML = m ? `<b>${m.name}</b><br><b>편성</b> ${m.band}<br><b>공식</b> ${m.recipe}` : "아직 연주 중이 아니에요";
  $("duck").classList.toggle("on", !!S.duck);
}
function poll() {
  api("/api/state").then(s => { if (S.vol === undefined) $("vol").value = Math.round(s.vol * 100); S = s; draw(); syncKnobs(s.params, s.pending); }).catch(() => {});
  if (showScore) fetch("/api/score").then(r => r.text()).then(t => { const p = $("score"); const atEnd = p.scrollTop + p.clientHeight >= p.scrollHeight - 30; p.textContent = t || "(아직 없음)"; if (atEnd) p.scrollTop = p.scrollHeight; }).catch(() => {});
}
setInterval(poll, 600); poll();
setInterval(() => fetch("/api/ping").catch(() => {}), 5000); fetch("/api/ping");

$("end").onclick = () => api(S.ending ? "/api/stop" : "/api/end", {});
$("vol").oninput = e => api("/api/volume", {v: e.target.value / 100});
$("duck").onclick = () => api("/api/duck", {on: S.duck ? 0 : 1}).then(poll);
$("b-score").onclick = () => { showScore = !showScore; $("score").classList.toggle("hide", !showScore); $("b-score").textContent = showScore ? "악보 접기 ▲" : "악보 보기 ▼"; poll(); };
$("b-info").onclick = () => $("info").classList.toggle("hide");

// 세부 조절: -1 … +1 (가운데 = 분위기 기본). 울림은 바로, 나머지는 다음 2마디 덩어리부터 AI 가 다시 씀
const KNOBS = [
  ["reg", "음 높이", "낮게", "높게"], ["tempo", "빠르기", "느리게", "빠르게"], ["dens", "음 수", "성기게", "촘촘하게"],
  ["energy", "세기", "잔잔하게", "힘차게"], ["novelty", "새로움", "익숙하게", "새롭게"], ["space", "울림", "가깝게", "넓게"]];
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
    let v = el.value / 100; if (Math.abs(v) < .08) v = 0;                 // 가운데 근처는 기본으로 붙음
    PV[k] = v; showK(k, v);
    if (k === "space") sendK();                                          // 울림은 바로
  };
  el.onchange = () => { if (Math.abs(el.value) < 8) el.value = 0; sendK(); };
});
$("reset").onclick = () => { KNOBS.forEach(([k]) => { PV[k] = 0; $("k-" + k).value = 0; showK(k, 0); }); sendK(); };
try { if (window.matchMedia("(min-width:900px)").matches || localStorage.getItem("tuneOpen") === "1") $("tune").open = true; } catch (e) {}
$("tune").ontoggle = () => { $("tsum").textContent = $("tune").open ? "▲" : "▼"; try { localStorage.setItem("tuneOpen", $("tune").open ? "1" : "0"); } catch (e) {} };
function syncKnobs(p, pending) {
  if (!p) return;
  if (Date.now() - touched > 1500) KNOBS.forEach(([k]) => { if (p[k] === undefined) return; PV[k] = p[k]; $("k-" + k).value = Math.round(p[k] * 100); showK(k, p[k]); });
  $("pend").textContent = pending && S.playing ? "다음 마디부터 바뀌어요" : "";
}
$("b-folder").onclick = () => api("/api/open", {}).then(r => { if (!navigator.userAgent.includes("Windows")) alert(r.path); });
</script>
</body>
</html>
)WEB";
