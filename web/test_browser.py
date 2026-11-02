# 헤드리스 크롬으로 HTML 직접 열어 확인: 오류 · 생성 속도 · 끊김 · 상황 바꾸기 · 화면 사진
import json, sys, time
from playwright.sync_api import sync_playwright

HTML = sys.argv[1] if len(sys.argv) > 1 else "/home/drboom/project/car_bgm/dist/car_bgm_player.html"
SHOT = "/home/drboom/project/car_bgm/web/test"
errs, logs = [], []
with sync_playwright() as p:
    b = p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
    pg = b.new_page(viewport={"width": 375, "height": 812})
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: logs.append(f"{m.type}: {m.text}") if m.type in ("error", "warning") else None)
    t0 = time.time()
    pg.goto("file://" + HTML)
    print(f"열기 {time.time() - t0:.1f}s")
    pg.screenshot(path=f"{SHOT}/shot_375_before.png")
    t0 = time.time()
    pg.click("#play")
    pg.wait_for_function("window.__stats.bars >= 1", timeout=120000)
    print(f"시작 → 첫 마디 연주 {time.time() - t0:.1f}s")
    def stat(tag):
        s = pg.evaluate("JSON.stringify(window.__stats)")
        print(tag, s, "| 화면:", pg.inner_text("#sit-name"), "/", pg.inner_text("#stat"))
    time.sleep(20); stat("20초 뒤")
    for i, name, sec in ((0, "아이 재우기", 15), (3, "즐거운 대화", 60), (4, "바닷가", 20), (1, "진정", 15)):
        pg.evaluate(f"window.__ctl.press({i})")
        time.sleep(sec); stat(f"{name} {sec}초 뒤")
    pg.screenshot(path=f"{SHOT}/shot_375_playing.png")
    pg.click("#more"); time.sleep(0.5)
    pg.screenshot(path=f"{SHOT}/shot_375_detail.png", full_page=True)
    pg.set_viewport_size({"width": 1280, "height": 900}); time.sleep(1)
    pg.screenshot(path=f"{SHOT}/shot_1280.png")
    b.close()
print("페이지 오류", errs[:5]); print("콘솔", logs[:8])
