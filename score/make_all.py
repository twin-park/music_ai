# 분위기 9개를 한 번에: 작곡(AI) → 악보 글자 → 소리 → dist/샘플/AI재즈/
#   python make_all.py [씨앗] [분위기,…]
import os, sys, shutil, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import compose as C
import play
import render as R
from styles import MOODS

seed = int(sys.argv[1]) if len(sys.argv) > 1 else 1
names = sys.argv[2].split(",") if len(sys.argv) > 2 else list(MOODS)
DST = os.path.join(HERE, "..", "dist", "샘플", "AI재즈")
os.makedirs(DST, exist_ok=True)
lines = []
for i, nm in enumerate(names):
    sh = C.compose(nm, seed)
    src = os.path.join(HERE, "out", f"{nm}_{seed}.txt")
    sh.save(src)
    y = play.render_sheet(sh)
    R.write(y, src[:-4] + ".wav")
    chk = subprocess.run([sys.executable, os.path.join(HERE, "check.py"), src], capture_output=True, text=True).stdout.strip().splitlines()
    clash = next((l for l in chk if "부딪힘" in l), "")
    k = list(MOODS).index(nm) + 1
    base = f"{k}_{nm}"
    shutil.copy(src[:-4] + ".mp3", os.path.join(DST, base + ".mp3"))
    shutil.copy(src, os.path.join(DST, base + ".txt"))
    m = MOODS[nm]
    sec = len(y) / R.SR
    lines.append(f"{base}.mp3  ({int(sec // 60)}:{int(sec % 60):02d}, {sh.key.name}, ♩={m['bpm']})\n  편성: {m['band']}\n  공식: {m['recipe']}\n")
    print(f"  ✔ {base} · {sec:.0f}초 · {clash}", flush=True)
with open(os.path.join(DST, "읽어주세요.txt"), "w", encoding="utf-8") as f:
    f.write("AI 작곡 재즈 — 분위기별 샘플 (AI가 쓴 악보 → 소리)\n\n"
            "만드는 순서\n"
            "  1. 진행 AI: 재즈 스탠더드·리드시트·팝 2,800곡의 코드 진행을 배운 작은 AI가 A-A-B-A 32마디 진행을 8번 써 보고,\n"
            "     공식 점수(코드 다양성 · ii-V · 같은 2마디 반복 적게 · B 는 A 와 다르게 · 으뜸화음으로 끝)로 하나를 고름\n"
            "  2. 선율 AI: 명연주 재즈 솔로(WJazzD)·리드시트·팝 선율 1,700곡을 배운 AI가 코드를 받아 단락마다 선율을 3번 써 보고 고름.\n"
            "     A' · A'' 는 A 의 첫 두 마디를 이어 받아 같은 느낌으로 변주\n"
            "  3. 편곡 공식: 분위기마다 누가 선율 · 반주 · 베이스 · 드럼을 맡는지, 어떤 보이싱 · 리듬 꼴을 쓰는지\n"
            "  4. 결과는 악보 글자(.txt, -1 mi F 3~6 형식) → 그대로 소리(.mp3)\n\n"
            "곡 목록\n\n" + "\n".join(lines) +
            "\n같은 분위기라도 씨앗을 바꾸면 다른 곡이 나옵니다 (python score/make_all.py <씨앗>).\n")
print("→", DST)
