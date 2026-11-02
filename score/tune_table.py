# 사운드폰트 악기의 음마다 실제 음높이(센트)·소리 시작 지연(ms)을 재서 보정표로 → tune_table.json
#  play.py 가 음마다 피치벤드로 음정을 맞추고, 시작 지연만큼 앞당겨 박을 맞춤
import sys, json, types, numpy as np
sys.path.append("../compose")
import render as R
SR = R.SR
INST = {"테너": ("gu", 0, 66, (44, 77)), "알토": ("gu", 0, 65, (49, 81)), "뮤트": ("gu", 0, 59, (52, 84)), "트럼펫": ("gu", 0, 56, (52, 84)),
        "비브라폰": ("gu", 0, 11, (53, 89)), "나일론": ("gu", 0, 24, (40, 84)), "기타": ("gu", 0, 26, (40, 84)), "로즈": ("gu", 0, 4, (36, 90)),
        "현악": ("gu", 0, 49, (36, 96)), "일렉": ("gu", 0, 33, (28, 60)), "베이스": ("gu", 0, 32, (28, 60)), "첼레스타": ("gu", 0, 8, (60, 100)),
        "플루트": ("sso", 0, 14, (60, 96)), "첼로": ("sso", 0, 8, (36, 76)), "바이올린": ("sso", 0, 2, (55, 100))}


def measure(x, p):
    m = x[int(.35 * SR):int(1.25 * SR)].mean(1)
    m = m * np.hanning(len(m))
    X = np.abs(np.fft.rfft(m, 1 << 20)); fr = np.fft.rfftfreq(1 << 20, 1 / SR)
    f = 440 * 2 ** ((p - 69) / 12)
    cs, ws = [], []
    for k in (1, 2, 3, 4):
        band = (fr > k * f * 2 ** (-70 / 1200)) & (fr < k * f * 2 ** (70 / 1200))
        if not band.any():
            continue
        i = np.argmax(X * band)
        if X[i] < X.max() * .02:
            continue
        cs.append(1200 * np.log2(fr[i] / (k * f))); ws.append(X[i])
    c = float(np.average(cs, weights=ws)) if cs else 0.0
    e = np.abs(x).max(1)
    on = float(np.argmax(e > e.max() * .15) / SR - .5)
    return c, on


out = {}
for name, (font, bank, prog, (lo, hi)) in INST.items():
    row = {}
    for p in range(lo, hi + 1, 2):
        tm = R.TimeMap(types.SimpleNamespace(notes=[[0.5, 1.2]], bpm=60, tempo_pts=None))
        y = R.fluid_render([(0.5, 1.2, p, 90)], [], [], tm, int(2.2 * SR), R.SF[font], bank, prog, False)
        if np.abs(y).max() < 1e-4:
            continue
        c, on = measure(y, p)
        row[p] = (round(c, 1), round(on * 1000, 1))
    cents = [v[0] for v in row.values()]; ons = [v[1] for v in row.values()]
    print(f"{name}: 센트 중앙 {np.median(cents):+.1f} (범위 {min(cents):+.0f}~{max(cents):+.0f}) · 시작 지연 중앙 {np.median(ons):.0f}ms", flush=True)
    out[name] = row
json.dump(out, open("tune_table.json", "w"), ensure_ascii=False)
