# v2 HTML 묶기: 재즈판 / 오케스트라판.  python build_html2.py jazz|orch <모델폴더>
import os, sys, json, base64, datetime
ROOT = "/home/drboom/project/car_bgm"; W = f"{ROOT}/web"
sys.path += [ROOT, f"{ROOT}/music"]
from moods import JAZZ, ORCH, FAM_PROGS
from tokens import GENRES, MOODS

VAR = {
    "jazz": dict(title="무드 컨덕터 · 재즈", moods=JAZZ, out="mood_jazz.html",
                 fams=[["piano", "피아노·로즈"], ["bass", "베이스"], ["drums", "드럼"], ["reed", "색소폰"], ["chrom_perc", "비브라폰"],
                       ["guitar", "기타"], ["organ", "오르간"], ["brass", "트럼펫"], ["pipe", "플루트"], ["strings", "현악"]],
                 data="Lakh MIDI(MidiCaps) 재즈 930곡 + PDMX 재즈·소울 993곡 중심으로 다듬음(라틴·이지리스닝 등 이웃 장르를 조금 섞어 과적합 방지) (기본 학습: PDMX 9.7만 + Lakh 2.8만)",
                 sound="피아노 Salamander Grand(Yamaha C5 실제 녹음, CC-BY 3.0) · 베이스·드럼·관악 GeneralUser GS · 플루트 Sonatina"),
    "orch": dict(title="무드 컨덕터 · 오케스트라", moods=ORCH, out="mood_orchestra.html",
                 fams=[["piano", "피아노"], ["strings", "현악"], ["ensemble", "현악 합주·합창"], ["brass", "금관"], ["reed", "목관"],
                       ["pipe", "플루트"], ["chrom_perc", "글로켄"], ["drums", "타악"]],
                 data="Lakh MIDI(MidiCaps) 클래식·오케스트라·영화음악 1만여 곡 + PDMX 클래식으로 다듬음 (기본 학습: PDMX 9.7만 + Lakh 2.8만)",
                 sound="피아노 Salamander Grand(CC-BY 3.0) · 현악·목관·금관·하프 Sonatina Symphonic Orchestra"),
}


def build(variant, model_dir):
    v = VAR[variant]
    head = json.load(open(f"{model_dir}/model.json"))
    weights = base64.b64encode(open(f"{model_dir}/model.bin", "rb").read()).decode()
    wasm = base64.b64encode(open(f"{W}/build/engine.wasm", "rb").read()).decode()
    samples = open(f"{W}/build/samples_{variant}.json").read()
    src = lambda n: open(f"{W}/src/{n}", encoding="utf-8").read()
    worker = src("engine.js") + "\n" + src("gen2.js") + "\n" + src("worker2.js")
    c = head["cfg"]
    n = sum(t["shape"][0] * (t["shape"][1] if len(t["shape"]) > 1 else 1) for t in head["tensors"].values())
    model_info = f"{n / 1e6:.1f}M 파라미터(int8, d{c['d']}·{c['layers']}층) · 학습 {head.get('step')}걸음 · 검증 손실 {head.get('val') or 0:.3f}"
    info = f"음악 모델 {model_info} · {v['data']} · 소리 {v['sound']}"
    cfg = {"variant": variant, "title": v["title"], "genres": GENRES, "moods": MOODS, "fams": v["fams"], "famProgs": FAM_PROGS[variant]}
    html = src("page2.html")
    for k, val in {"__HEAD__": json.dumps(head, ensure_ascii=False), "__SIT__": json.dumps(v["moods"], ensure_ascii=False),
                   "__CFG__": json.dumps(cfg, ensure_ascii=False), "__SAMPLES__": samples, "__WEIGHTS__": weights, "__WASM__": wasm,
                   "__WORKER__": worker, "__PLAYER__": src("player2.js"), "__INFO__": info}.items():
        assert "</script" not in val, k
        html = html.replace(k, val, 1)
    out = f"{ROOT}/dist/{v['out']}"
    open(out, "w", encoding="utf-8").write(html)
    print(f"{out} {len(html.encode()) / 1e6:.1f}MB · {model_info}")
    return out, model_info


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2])
