#!/usr/bin/env python3
"""
make_win — 차량 BGM AI 윈도우 묶음 (2026-10-31, 사용자: "dist 에 윈도우 실행파일 넣어둬")

  CAR_BGM/
    CAR_BGM.exe      launcher/car_bgm_launcher.c (zig 교차 · 창 없는 프로그램 → 브라우저로 화면)
    python/          파이썬 3.12 임베드(amd64) + numpy · scipy · soundfile · mido · lameenc  (torch 없음 — AI 는 numpy 로 셈)
    fluidsynth/      FluidSynth 2.6.1 윈도우판 (리눅스와 같은 판)
    app/             score/ (작곡 · 편곡 · 연주) + score/ai/ (진행·선율 AI 생성) + score/studio/ (화면) + compose/render.py
    data/            models/ (AI 가중치 .npz) · sf/ (GeneralUser GS + Sonatina 에서 쓰는 3악기만) · piano/ (Salamander FLAC)
  → dist/CAR_BGM-win64.zip

  재료 (한 번만): build/dl/python-embed.zip · build/dl/wheels/*.whl · build/dl/fluidsynth-win64.zip
                 build/assets/sf/sso_small.sf2 (sf2_subset.py) · build/assets/piano/*.flac (prep_piano.py)
                 runs/score_*/best.npz (score/ai/npmodel.py export) · launcher/CAR_BGM.exe
  python3 win/make_win.py
"""
import os, sys, glob, shutil, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DL = os.path.join(HERE, "build", "dl")
AS = os.path.join(HERE, "build", "assets")
OUT = os.path.join(HERE, "build", "CAR_BGM")
ZIP = os.path.join(ROOT, "dist", "CAR_BGM-win64.zip")

SCORE = ["theory", "notation", "arrange", "styles", "compose", "play"]
AI = ["gen", "tok", "npmodel"]


def cp(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)


def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    # ── 파이썬 ──
    py = os.path.join(OUT, "python")
    with zipfile.ZipFile(os.path.join(DL, "python-embed.zip")) as z:
        z.extractall(py)
    pth = glob.glob(os.path.join(py, "python3*._pth"))[0]
    zipname = [l.strip() for l in open(pth) if l.strip().endswith(".zip")][0]
    open(pth, "w", newline="\r\n").write(f"{zipname}\n.\nLib\\site-packages\n..\\app\\score\n..\\app\\score\\ai\n..\\app\\compose\n")
    sp = os.path.join(py, "Lib", "site-packages")
    os.makedirs(sp)
    for w in sorted(glob.glob(os.path.join(DL, "wheels", "*.whl"))):
        with zipfile.ZipFile(w) as z:
            z.extractall(sp)
    for d in glob.glob(os.path.join(sp, "**", "tests"), recursive=True):          # 시험 코드는 안 씀 (scipy 만 수십 MB)
        if os.path.isdir(d) and ("scipy" in d or "numpy" in d):
            shutil.rmtree(d)
    # ── fluidsynth ──
    fsd = os.path.join(OUT, "fluidsynth")
    os.makedirs(fsd)
    with zipfile.ZipFile(os.path.join(DL, "fluidsynth-win64.zip")) as z:
        for n in z.namelist():
            if "/bin/" in n and not n.endswith("/"):
                with z.open(n) as f, open(os.path.join(fsd, os.path.basename(n)), "wb") as g:
                    g.write(f.read())
    # ── app ──
    app = os.path.join(OUT, "app")
    for m in SCORE:
        cp(os.path.join(ROOT, "score", m + ".py"), os.path.join(app, "score", m + ".py"))
    cp(os.path.join(ROOT, "score", "tune_table.json"), os.path.join(app, "score", "tune_table.json"))
    for m in AI:
        cp(os.path.join(ROOT, "score", "ai", m + ".py"), os.path.join(app, "score", "ai", m + ".py"))
    cp(os.path.join(ROOT, "score", "studio", "server.py"), os.path.join(app, "score", "studio", "server.py"))
    shutil.copytree(os.path.join(ROOT, "score", "studio", "web"), os.path.join(app, "score", "studio", "web"))
    cp(os.path.join(ROOT, "compose", "render.py"), os.path.join(app, "compose", "render.py"))
    # ── data ──
    data = os.path.join(OUT, "data")
    for w in ("chord", "melody"):
        cp(os.path.join(ROOT, "runs", f"score_{w}", "best.npz"), os.path.join(data, "models", f"score_{w}", "best.npz"))
    cp(os.path.join(ROOT, "data", "sf", "GeneralUser-GS.sf2"), os.path.join(data, "sf", "GeneralUser-GS.sf2"))
    cp(os.path.join(AS, "sf", "sso_small.sf2"), os.path.join(data, "sf", "sso_small.sf2"))
    shutil.copytree(os.path.join(AS, "piano"), os.path.join(data, "piano"))
    # ── 위 ──
    shutil.copy2(os.path.join(HERE, "launcher", "CAR_BGM.exe"), OUT)
    open(os.path.join(OUT, "README.txt"), "w", encoding="utf-8-sig", newline="\r\n").write(README)
    open(os.path.join(OUT, "THIRD_PARTY.txt"), "w", encoding="utf-8-sig", newline="\r\n").write(THIRD)
    # 파일 이름은 전부 영문 (윈도우 기본 압축 풀기)
    bad = [os.path.relpath(os.path.join(r, f), OUT) for r, ds, fs in os.walk(OUT) for f in fs + ds if not f.isascii()]
    if bad:
        raise SystemExit("영문이 아닌 파일 이름: " + ", ".join(bad[:5]))
    for p in glob.glob(os.path.join(OUT, "**", "__pycache__"), recursive=True):
        shutil.rmtree(p)
    os.makedirs(os.path.dirname(ZIP), exist_ok=True)
    if os.path.exists(ZIP):
        os.remove(ZIP)
    total = 0
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for root, _ds, fs in os.walk(OUT):
            for f in sorted(fs):
                p = os.path.join(root, f)
                z.write(p, os.path.join("CAR_BGM", os.path.relpath(p, OUT)))
                total += os.path.getsize(p)
    print(f"→ {ZIP}  ({os.path.getsize(ZIP) / 1e6:.0f}MB · 풀면 {total / 1e6:.0f}MB)")


README = """차량 BGM AI — 분위기를 고르면 AI 가 악보를 쓰고, 그 악보를 연주합니다 (인터넷 필요 없음)

1. zip 을 통째로 풉니다 (바탕 화면 · 다운로드 어디든)
2. CAR_BGM 폴더 안의 CAR_BGM.exe 를 두 번 누릅니다 → 브라우저에 화면이 뜹니다
   (처음 한 번은 Windows 가 "PC 보호" 창을 띄울 수 있습니다 → [추가 정보] → [실행])
3. 분위기를 누르면 바로 만듭니다
   코드 진행(진행 AI) → 선율(선율 AI) → 편곡 → 악기별 연주 → 마무리
   한 곡에 보통 1~3분 걸립니다 (컴퓨터 성능에 따라)
4. 다 되면 바로 재생됩니다
   [한 곡 더] 같은 분위기로 새 곡 · [악보 보기] AI 가 쓴 악보 글자 · [파일 폴더] mp3 · 악보 txt 가 있는 곳

결과는 C:\\Users\\<이름>\\차량BGM_결과 에 쌓입니다 (mp3 + 악보 txt, 이름에 씨앗 번호)
악보 글자 형식:  -1 mi F 3~6 70  = 옥타브 -1 · 미 · 플랫 · 3초~6초 · 세기 70
[내 악보 글자로 연주하기] 에 악보 txt 를 붙여 넣으면 그 악보를 그대로 연주합니다 (고친 악보 들어 보기)

브라우저 탭을 닫으면 30초 뒤 프로그램이 스스로 꺼집니다.
문제가 생기면 차량BGM_결과\\_오류기록.txt 를 보내 주세요.
"""

THIRD = """차량 BGM AI 에 들어 있는 남의 것

프로그램
- Python 3.12 (PSF License) · numpy · scipy (BSD) · soundfile (BSD, libsndfile LGPL-2.1) · cffi (MIT) · mido (MIT)
- lameenc (LGPL-3.0, LAME LGPL-2.0) — mp3 만들기
- FluidSynth 2.6.1 (LGPL-2.1) · SDL3 (zlib) · libsndfile (LGPL-2.1) — https://github.com/FluidSynth/fluidsynth

소리
- Accurate-Salamander Grand Piano (Chisato Yamauchi) / Salamander Grand Piano (Alexander Holm) — CC-BY 3.0
  FLAC 16비트로 바꾸고 14초에서 자름
- GeneralUser GS (S. Christian Collins) — 자유 사용 · 재배포 허용
- Sonatina Symphonic Orchestra (Mattias Westlund) — Creative Commons Sampling Plus 1.0
  바이올린 · 첼로 · 플루트 프리셋만 남김

AI 학습 자료 (가중치만 들어 있음)
- Weimar Jazz Database (ODbL) · iRealPro 재즈 스탠더드 진행 (sharp11-irb) · OpenEWLD (공개 저작물) · POP909 (MIT)
"""

if __name__ == "__main__":
    main()
