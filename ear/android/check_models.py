# ONNX · TFLite 가 시험 벡터에서 파이토치 정답(test/expected.json)과 같은지
#   python check_models.py <묶음 폴더>      (onnxruntime · soundfile 필요, tflite 는 tensorflow 또는 ai_edge_litert 가 있으면)
import os, sys, json, glob
import numpy as np, soundfile as sf
D = sys.argv[1] if len(sys.argv) > 1 else "."
exp = json.load(open(f"{D}/test/expected.json"))
lab = json.load(open(f"{D}/labels.json"))
ids = [s["id"] for s in lab["sounds"]]; emos = [e["id"] for e in lab["emotion"]]
def ref(name): return np.array([exp[name]["sounds"][k] for k in ids]), np.array([exp[name]["emotion"][k] for k in emos])
runs = {}
import onnxruntime as ort
for f in ("ear_wave.onnx",):
    s = ort.InferenceSession(f"{D}/{f}", providers=["CPUExecutionProvider"])
    runs[f] = lambda x, s=s: s.run(None, {"wav": x[None]})
try:
    try:
        from ai_edge_litert.interpreter import Interpreter
    except ImportError:
        from tensorflow.lite import Interpreter
    for f in sorted(glob.glob(f"{D}/*.tflite")):
        it = Interpreter(model_path=f); it.allocate_tensors()
        def run(x, it=it):
            it.set_tensor(it.get_input_details()[0]["index"], x[None]); it.invoke()
            o = {tuple(d["shape"]): it.get_tensor(d["index"]) for d in it.get_output_details()}
            return o[(1, 28)], o[(1, 6)]                      # TFLite 출력은 차례가 바뀌어 있어 모양으로 고름
        runs[os.path.basename(f)] = run
except ImportError:
    print("(tflite 해석기 없음 — ONNX 만 확인)")
for f, run in runs.items():
    ds = de = 0
    for name in exp:
        x, sr = sf.read(f"{D}/test/test_vectors/{name}.wav", dtype="int16")
        o = run((x.astype(np.float32) / 32768.0))
        rs, re_ = ref(name)
        ds = max(ds, float(np.abs(o[0][0] - rs).max())); de = max(de, float(np.abs(o[1][0] - re_).max()))
    print(f"{f}: 정답과 차 — 소리 확률 최대 {ds:.1e} · 감정 최대 {de:.1e} ({'같음' if max(ds, de) < 5e-3 else '다름!'})")
