# 상황마다 30초씩 틀고 → 브라우저 안에서 같은 악기로 오프라인 녹음 → 숫자 + wav 저장
import base64, sys, time, numpy as np, soundfile as sf
from playwright.sync_api import sync_playwright
HTML = "/home/drboom/project/car_bgm/dist/car_bgm_player.html"; OUT = "/home/drboom/project/car_bgm/web/test"
with sync_playwright() as p:
    b = p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
    pg = b.new_page(); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto("file://" + HTML); pg.click("#play"); pg.wait_for_function("window.__stats.bars >= 1", timeout=120000)
    for i, name in ((7, "드라이브"), (0, "아이재우기"), (4, "바닷가"), (3, "즐거운대화"), (1, "진정")):
        pg.evaluate(f"window.__ctl.press({i})"); time.sleep(6)
        n0 = pg.evaluate("window.__stats.bars")
        time.sleep(30)
        n1 = pg.evaluate("window.__stats.bars")
        r = pg.evaluate(f"window.__renderTest(25, {n1 - n0}).then(r => r)")    # 이 상황에서 연주한 마디만
        x = np.frombuffer(base64.b64decode(r["pcm"]), np.int16).reshape(-1, 2)
        sf.write(f"{OUT}/render_{name}.wav", x, 44100)
        print(f"{name}: 마디 {r['bars']} 상황 {r['sits']} · peak {r['peak']:.2f} rms {r['rms']:.3f} · 무음 {r['silentSec']}/{r['sec']}초")
    b.close()
print("오류", errs[:3])
