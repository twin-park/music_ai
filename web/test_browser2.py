# v2 HTML 헤드리스 시험: 오류 · 속도 · 코드 표시 · 같은 마디 다시쓰기 · 상황 바꾸기 + 상황별 오프라인 녹음(wav)
import base64, json, sys, time, numpy as np, soundfile as sf
from playwright.sync_api import sync_playwright
html = sys.argv[1]; tag = sys.argv[2] if len(sys.argv) > 2 else "t"; sec = float(sys.argv[3]) if len(sys.argv) > 3 else 20
CAP = float(sys.argv[4]) if len(sys.argv) > 4 else 18     # 녹음 길이 상한(초)
OUT = "/home/drboom/project/car_bgm/web/test"
with sync_playwright() as p:
    b = p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
    pg = b.new_page(viewport={"width": 1280, "height": 860}); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto("file://" + html); t0 = time.time(); pg.click("#play")
    pg.wait_for_function("window.__stats.bars >= 1", timeout=180000); print(f"첫 마디까지 {time.time() - t0:.1f}s")
    n = pg.evaluate("document.querySelectorAll('.mood').length")
    import os
    only = [int(k) for k in os.environ.get("ONLY", "").split(",") if k]     # ONLY=5,6 이면 그 상황만
    for i in range(n):
        if only and i not in only: continue
        pg.evaluate(f"window.__ctl.press({i})"); time.sleep(4)
        n0 = pg.evaluate("window.__stats.bars"); time.sleep(sec); n1 = pg.evaluate("window.__stats.bars")
        st = json.loads(pg.evaluate("JSON.stringify(window.__stats)"))
        name = pg.inner_text("#sit-name"); ch = pg.inner_text("#chord")
        r = pg.evaluate(f"window.__renderTest({min(sec, CAP)}, {max(1, n1 - n0)}).then(r => r)")
        x = np.frombuffer(base64.b64decode(r["pcm"]), np.int16).reshape(-1, 2)
        sf.write(f"{OUT}/{tag}_{i}_{name.split(' ', 1)[-1].replace(' ', '')}.wav", x, 44100)
        print(f"{name}: 마디 {n1 - n0} · 초당 {st['tps']:.0f}낱말 · 앞으로 {st['ahead']:.1f}s · 끊김 {st['underruns']} · 다시쓰기 {st['redo']}/{st['made']} · {ch} · peak {r['peak']:.2f} 무음 {r['silentSec']}s")
    pg.screenshot(path=f"{OUT}/{tag}_shot.png")
    b.close()
print("오류", errs[:3])
