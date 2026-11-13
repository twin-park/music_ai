#!/usr/bin/env python3
"""윈도우 묶음 (C++ 실시간판) → dist/CAR_BGM-win64.zip
  CAR_BGM/ CAR_BGM.exe (build_win.sh) · libfluidsynth-3.dll · sndfile.dll · SDL3.dll · data/ (AI · 보정표 · 사운드폰트 · 피아노) · README.txt · THIRD_PARTY.txt
  python3 tools/make_zip.py"""
import os, glob, shutil, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
EN = os.path.dirname(HERE)
ROOT = os.path.dirname(EN)
OUT = os.path.join(EN, "build", "CAR_BGM")
ZIP = os.path.join(ROOT, "dist", "CAR_BGM-win64.zip")
FS = glob.glob(os.path.join(ROOT, "win", "build", "dl", "fs_x", "*", "bin"))[0]

def cp(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(os.path.realpath(src), dst)

if os.path.isdir(OUT):
    shutil.rmtree(OUT)
cp(os.path.join(EN, "build", "win", "CAR_BGM.exe"), os.path.join(OUT, "CAR_BGM.exe"))
for d in ("libfluidsynth-3.dll", "sndfile.dll", "SDL3.dll"):
    cp(os.path.join(FS, d), os.path.join(OUT, d))
D = os.path.join(EN, "data")
for f in ("chord.bin", "melody.bin", "tune.txt", "calib.txt"):
    cp(os.path.join(D, f), os.path.join(OUT, "data", f))
for f in ("gu_small.sf2", "sso_small.sf2"):          # GeneralUser GS 는 쓰는 악기 14개만 남긴 판 (win/sf2_subset.py)
    cp(os.path.join(D, "sf", f), os.path.join(OUT, "data", "sf", f))
for f in ("sea.flac", "rain.flac"):                    # 주변 소리 (win/build/assets/amb, 링크)
    cp(os.path.join(D, "amb", f), os.path.join(OUT, "data", "amb", f))
for f in sorted(glob.glob(os.path.join(D, "piano", "*.flac"))):
    cp(f, os.path.join(OUT, "data", "piano", os.path.basename(f)))

README = """차량 BGM AI (실시간판) — 듣는 동안 AI 가 다음 악보를 계속 써서 바로 연주합니다

1. zip 을 통째로 풉니다 (바탕 화면 · 다운로드 어디든)
2. CAR_BGM 폴더의 CAR_BGM.exe 를 두 번 누릅니다 → 브라우저에 리모컨 화면이 뜹니다
   (처음 한 번은 Windows 가 "PC 보호" 창을 띄울 수 있습니다 → [추가 정보] → [실행])
3. 분위기를 누르면 1초 안에 음악이 시작됩니다 (스피커 · 이어폰)
   · 분위기 12개: 재즈 6 (비 오는 날 · 평온한 재즈 · 밤 드라이브 · 즐거운 대화 · 바닷가 보사노바 · 낮 드라이브)
     · 잔잔한 3 (아이 재우기 · 마음 가라앉히기 · 위로) · 클래식 3 (클래식 피아노 · 현악 앙상블 · 클래식 왈츠)
   · 켤 때마다 다른 곡입니다 (조 · 진행 · 선율 · 첫 편성이 매번 새로)
   · 이야기처럼 흘러갑니다: 2마디짜리 생각 가 · 나 · 다 · 라 를 차례로 들려주고, 한참 뒤에 가' · 나' · 다' 로 다시 불러
     (앞머리 · 리듬 · 코드는 기억나게, 끝은 새로) → 다음엔 마 · 바 · 사 · 아 … — 바로 되풀이하지 않고, 뒤죽박죽도 아님
     - 선율 AI 가 지난 마디를 통째로 베끼지 못하게 막음 (두 음까지만 같아도 됨) · 같은 음은 3번까지만 연달아
     - 진행은 진행 AI 가 앞 8마디를 이어 새로 쓰고, 다시 부를 땐 그 생각의 코드로 · 편성은 한 겹씩 · 가끔 가까운 조로
     - 진행이 조에서 떠내려가지 않게 붙잡음 (으뜸화음으로 돌아오기 · 조 안 화음 위주 · 양념은 분위기마다 정한 만큼만)
   · 듣는 중에 다른 분위기를 누르면 → 선율 한 덩어리가 끝나는 곳에서(4초 안), 마지막 음에서 이어지는 2마디 선율로
     가까운 조의 새 분위기로 넘어갑니다 (울리던 음은 바로 끊지 않음)
   · [세부 조절] 음 높이 · 빠르기 · 음 수 · 세기 · 새로움 · 긴장감 · 울림 — 울림은 바로, 나머지는 다음 2마디부터 AI 가 다시 써서 반영
     - 긴장감: 편안하게 = 조 안의 순한 화음 · 선율도 화음 안쪽으로 / 긴장되게 = 재화성 · 조 밖 화음 · 텐션이 늘어남
   · [끝내기] 마지막 4마디 + 마지막 화음으로 자연스럽게 끝 · 끝나는 중에 한 번 더 누르면 바로 끔
   · 소리 크기 · [📞 통화 중] (누르면 바로 작아짐 — 차 안에서 전화 올 때)
   · [🌊 바닷가 파도] [🌧 빗소리] 실제 녹음을 음악 밑에 작게 (음악보다 약 15dB 작게, 켜고 끌 때 3초쯤 천천히)
   · [악보 보기] AI 가 지금 쓰고 있는 악보 글자 (-1 mi F 3~6 70 = 옥타브 · 계이름 · 임시표 · 초 · 세기)
4. 악보는 C:\\Users\\<이름>\\차량BGM_결과\\<날짜시각>_실시간악보.txt 에 계속 쌓입니다 ([악보 폴더])

인터넷 · 설치 필요 없음 (AI · 사운드폰트 · 피아노 샘플이 전부 들어 있음, 파이썬 없음)
브라우저 탭을 닫으면 30초 뒤 프로그램이 스스로 꺼집니다.
"""
THIRD = """차량 BGM AI 에 들어 있는 남의 것

프로그램
- FluidSynth 2.6.1 (LGPL-2.1) · SDL3 (zlib) · libsndfile (LGPL-2.1) — https://github.com/FluidSynth/fluidsynth (DLL 그대로)
- miniaudio 0.11.22 (MIT-0 / Public Domain) · dr_flac (MIT-0 / Public Domain) — https://github.com/mackron
- 실행 파일은 zig c++ (libc++ · MIT/Apache-2.0 with LLVM exception) 로 빌드

소리
- Accurate-Salamander Grand Piano (Chisato Yamauchi) / Salamander Grand Piano (Alexander Holm) — CC-BY 3.0, FLAC 16비트로 바꾸고 14초에서 자름
- GeneralUser GS (S. Christian Collins) — 자유 사용 · 재배포 허용, 쓰는 악기 14개 프리셋만 남김
- 바닷가 파도: "Ocean Waves on a Tropical Beach" (J.D. Savanyu, Wikimedia Commons) — CC0, 60초 고리로 다듬음
- 빗소리: "Rain (1)" (ezwa) · "Rain against the window" (cori) (Wikimedia Commons) — 퍼블릭 도메인, 섞어 120초 고리로 다듬음
- Sonatina Symphonic Orchestra (Mattias Westlund) — Creative Commons Sampling Plus 1.0, 바이올린 · 첼로 · 플루트 프리셋만 남김

AI 학습 자료 (가중치만 들어 있음)
- Weimar Jazz Database (ODbL) · iRealPro 재즈 스탠더드 진행 (sharp11-irb) · OpenEWLD (공개 저작물) · POP909 (MIT)
- Lakh MIDI Dataset (Colin Raffel, CC-BY 4.0) + MidiCaps 꼬리표 (CC-BY-SA 4.0) — 선율 · 코드를 뽑아 리드시트 8,865곡으로 바꿔 씀
  (원곡 저작권은 각 곡에 남아 있음 → 상용화 전 검토)
- PDMX: Public Domain MusicXML (Long 외, 자료집 CC-BY 4.0 · 악보는 공개 저작물/CC0 표시) — 반주가 있는 악보에서 선율 · 코드를 뽑아
  리드시트 19,714곡 (그중 클래식 9,601곡) 으로 바꿔 씀
"""
open(os.path.join(OUT, "README.txt"), "w", encoding="utf-8-sig", newline="\r\n").write(README)
open(os.path.join(OUT, "THIRD_PARTY.txt"), "w", encoding="utf-8-sig", newline="\r\n").write(THIRD)
bad = [os.path.relpath(os.path.join(r, f), OUT) for r, ds, fs in os.walk(OUT) for f in fs + ds if not f.isascii()]
if bad:
    raise SystemExit("영문이 아닌 파일 이름: " + ", ".join(bad[:5]))
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
