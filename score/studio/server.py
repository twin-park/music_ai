# 차량 BGM AI 화면 — 분위기를 고르면 AI 가 악보를 쓰고(진행 AI → 선율 AI → 편곡 공식) 그 악보를 소리로 연주
#   python score/studio/server.py [--port 7600] [--no-browser]
#   윈도우 묶음(CAR_BGM.exe)은 CAR_BGM_HOME 을 넣어 띄움 → 재료 경로를 여기서 정하고, 브라우저 탭이 닫히면 30초 뒤 꺼짐
import os, sys, json, time, threading, webbrowser, argparse, socket, random, traceback, tempfile
from datetime import datetime
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, quote

HERE = os.path.dirname(os.path.abspath(__file__))
SCORE = os.path.dirname(HERE)
HOME = os.environ.get("CAR_BGM_HOME")
os.environ.setdefault("SCORE_BACKEND", "numpy")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "4")
if HOME:                                                   # 묶음 안 재료
    D = os.path.join(HOME, "data")
    for k, v in dict(CAR_BGM_ROOT=HOME, CAR_BGM_TOOLS=os.path.join(HOME, "fluidsynth"), CAR_BGM_RUNS=os.path.join(D, "models"),
                     CAR_BGM_SF_GU=os.path.join(D, "sf", "GeneralUser-GS.sf2"), CAR_BGM_SF_SSO=os.path.join(D, "sf", "sso_small.sf2"),
                     CAR_BGM_PIANO=os.path.join(D, "piano")).items():
        os.environ.setdefault(k, v)
    # fluidsynth 는 경로를 ANSI 로 받음 → 임시 폴더가 영문 경로가 아니면 영문 경로로
    if not tempfile.gettempdir().isascii():
        for cand in (os.path.join(HOME, "work"), os.path.join(os.environ.get("PUBLIC", r"C:\Users\Public"), "car_bgm_tmp")):
            if cand.isascii():
                os.makedirs(cand, exist_ok=True); tempfile.tempdir = cand; break
sys.path.insert(0, SCORE)
sys.path.insert(0, os.path.join(SCORE, "ai"))

import numpy as np
import compose as C
import play
from notation import load
from styles import MOODS

OUT = Path(os.environ.get("CAR_BGM_OUT", Path.home() / "차량BGM_결과"))
OUT.mkdir(parents=True, exist_ok=True)
SHOW = {"비오는날": "비 오는 날", "평온한재즈": "평온한 재즈", "밤드라이브": "밤 드라이브", "즐거운대화": "즐거운 대화",
        "바닷가보사노바": "바닷가 보사노바", "아이재우기": "아이 재우기", "진정": "마음 가라앉히기", "위로": "위로", "낮드라이브": "낮 드라이브"}
JOBS, LOCK = {}, threading.Lock()
LAST_PING = 0.0


def busy():
    return any(j["state"] == "running" for j in JOBS.values())


def mp3_bytes(y, sr):
    import lameenc
    enc = lameenc.Encoder()
    enc.set_bit_rate(192); enc.set_in_sample_rate(sr); enc.set_channels(2); enc.set_quality(2)
    pcm = (np.clip(y, -1, 1) * 32767).astype("<i2").tobytes()
    return enc.encode(pcm) + enc.flush()


def save_audio(y, base):
    """mp3 (lameenc) — 없으면 wav"""
    import render as R
    try:
        data = mp3_bytes(y, R.SR)
        p = base.with_suffix(".mp3"); p.write_bytes(data)
    except ImportError:
        import soundfile as sf
        p = base.with_suffix(".wav"); sf.write(str(p), y, R.SR, subtype="PCM_16")
    return p.name


def run_job(jid, mood=None, seed=None, text=None):
    j = JOBS[jid]

    def step(i, note=""):
        j["step"], j["note"] = i, note
    try:
        t0 = time.time()
        stamp = datetime.now().strftime("%m%d_%H%M%S")
        if text is None:
            sh = C.compose(mood, seed, verbose=False, progress=step)
            base = OUT / f"{stamp}_{SHOW.get(mood, mood)}_{seed}"
            sh.save(str(base.with_suffix(".txt")))
        else:
            step(3)
            base = OUT / f"{stamp}_내악보"
            base.with_suffix(".txt").write_text(text, encoding="utf-8")
            sh = load(str(base.with_suffix(".txt")))
        step(4, "")
        y = play.render_sheet(sh, seed or 1, progress=lambda name, i, n: step(4 if name else 5, f"{name.replace(' 오른손', '').replace(' 왼손', '')} ({i + 1}/{n})" if name else ""))
        import render as R
        name = save_audio(y, base)
        m = MOODS.get(mood, {})
        j["result"] = dict(audio=name, txt=base.with_suffix(".txt").name, title=SHOW.get(mood, sh.title or "내 악보"),
                           seed=seed, key=sh.key.name, bpm=sh.info.get("템포", ""), sec=round(len(y) / R.SR),
                           band=m.get("band", ""), recipe=m.get("recipe", ""), took=round(time.time() - t0))
        j["state"] = "done"
    except Exception as e:
        j["state"], j["error"] = "error", f"{type(e).__name__}: {e}"
        with open(OUT / "_오류기록.txt", "a", encoding="utf-8") as f:
            f.write(f"\n[{datetime.now()}] {mood or '내 악보'}\n{traceback.format_exc()}")


def start(**kw):
    with LOCK:
        if busy():
            return None
        jid = f"{int(time.time() * 1000)}"
        JOBS[jid] = dict(state="running", step=0, note="", t0=time.time())
        threading.Thread(target=run_job, args=(jid,), kwargs=kw, daemon=True).start()
        return jid


class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=os.path.join(HERE, "web"), **k)

    def log_message(self, *a):
        pass

    def send_json(self, obj, code=200):
        b = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def end_headers(self):
        if not self.path.startswith("/api/"):
            self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def do_GET(self):
        global LAST_PING
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path == "/api/ping":
            LAST_PING = time.time()
            return self.send_json({"ok": True})
        if u.path == "/api/moods":
            return self.send_json([dict(id=k, name=SHOW.get(k, k), band=m["band"], recipe=m["recipe"], bpm=m["bpm"],
                                        ts=m["ts"]) for k, m in MOODS.items()])
        if u.path == "/api/job":
            j = JOBS.get(q.get("id", [""])[0])
            if not j:
                return self.send_json({"state": "missing"}, 404)
            return self.send_json({k: v for k, v in j.items()} | {"elapsed": round(time.time() - j["t0"])})
        if u.path.startswith("/out/"):
            from urllib.parse import unquote
            name = unquote(u.path[5:])
            p = (OUT / name).resolve()
            if p.parent != OUT.resolve() or not p.is_file():
                return self.send_error(404)
            data = p.read_bytes()
            ctype = {".mp3": "audio/mpeg", ".wav": "audio/wav", ".txt": "text/plain; charset=utf-8"}.get(p.suffix, "application/octet-stream")
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            if "dl" in q:
                self.send_header("Content-Disposition", f"attachment; filename*=UTF-8''{quote(name)}")
            self.end_headers()
            self.wfile.write(data)
            return
        return super().do_GET()

    def do_POST(self):
        u = urlparse(self.path)
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n) or b"{}")
        if u.path == "/api/make":
            mood = body.get("mood")
            if mood not in MOODS:
                return self.send_json({"error": "모르는 분위기"}, 400)
            seed = int(body.get("seed") or random.randint(1, 9999))
            jid = start(mood=mood, seed=seed)
            return self.send_json({"job": jid} if jid else {"error": "이미 만드는 중이에요"}, 200 if jid else 409)
        if u.path == "/api/play":
            text = body.get("text", "")
            if "[" not in text:
                return self.send_json({"error": "악보 글자가 비어 있어요"}, 400)
            jid = start(text=text)
            return self.send_json({"job": jid} if jid else {"error": "이미 만드는 중이에요"}, 200 if jid else 409)
        if u.path == "/api/open":
            if os.name == "nt":
                os.startfile(str(OUT))
            return self.send_json({"ok": True, "path": str(OUT)})
        self.send_error(404)


def free_port(start):
    for p in range(start, start + 50):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", p)); return p
            except OSError:
                pass
    raise SystemExit("빈 포트가 없어요")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=7600)
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args()
    port = free_port(a.port)
    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    url = f"http://127.0.0.1:{port}/"
    print(url, flush=True)
    if not a.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    if HOME:                                               # exe — 마지막 박동 30초 뒤 (만드는 중이면 기다림) 종료
        def watch():
            t_start = time.time()
            while True:
                time.sleep(5)
                idle = time.time() - (LAST_PING or t_start)
                if not busy() and idle > (30 if LAST_PING else 120):
                    os._exit(0)
        threading.Thread(target=watch, daemon=True).start()
    srv.serve_forever()


if __name__ == "__main__":
    main()
