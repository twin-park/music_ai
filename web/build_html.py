# HTML 한 장으로 묶기: 모델(int8)·WASM 엔진·악기 소리·화면 → dist/car_bgm_player.html
import os, sys, json, base64
ROOT = "/home/drboom/project/car_bgm"; W = f"{ROOT}/web"
sys.path.insert(0, ROOT)
from conduct import SITUATIONS, DEFAULT


def build(model_dir=f"{W}/build", out=f"{ROOT}/dist/car_bgm_player.html"):
    head = json.load(open(f"{model_dir}/model.json"))
    weights = base64.b64encode(open(f"{model_dir}/model.bin", "rb").read()).decode()
    wasm = base64.b64encode(open(f"{W}/build/engine.wasm", "rb").read()).decode()
    samples = open(f"{W}/build/samples.json").read()
    sit = [[s[0], sorted(s[1]), s[2], s[3], s[4]] for s in SITUATIONS] + [[DEFAULT[0], [], DEFAULT[2], DEFAULT[3], DEFAULT[4]]]
    src = lambda n: open(f"{W}/src/{n}").read()
    worker = src("engine.js") + "\n" + src("gen.js") + "\n" + src("worker.js")
    c = head["cfg"]
    n = sum(t["shape"][0] * (t["shape"][1] if len(t["shape"]) > 1 else 1) for t in head["tensors"].values())
    info = f"{n / 1e6:.1f}M 파라미터(int8, d{c['d']}·{c['layers']}층) · 학습 {head.get('step')}걸음 · 검증 손실 {head.get('val') or 0:.3f}"
    html = src("page.html")
    for k, v in {"__HEAD__": json.dumps(head, ensure_ascii=False), "__SIT__": json.dumps(sit, ensure_ascii=False),
                 "__SAMPLES__": samples, "__WEIGHTS__": weights, "__WASM__": wasm, "__WORKER__": worker,
                 "__PLAYER__": src("player.js"), "__MODEL_INFO__": info}.items():
        assert "</script" not in v, k
        html = html.replace(k, v, 1)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write(html)
    import datetime
    ver = f"{datetime.datetime.now():%Y-%m-%d %H:%M} · {info} · 파일 {len(html.encode()) / 1e6:.1f}MB"
    rd = f"{W}/src/readme.txt"
    if os.path.exists(rd):
        open(os.path.join(os.path.dirname(out), "읽어주세요.txt"), "w", encoding="utf-8").write(open(rd, encoding="utf-8").read().replace("__VERSION__", ver))
    print(f"{out} {len(html.encode()) / 1e6:.1f}MB · {info}")


if __name__ == "__main__":
    build(*sys.argv[1:])
