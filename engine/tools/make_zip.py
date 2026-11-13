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
for f in sorted(glob.glob(os.path.join(D, "conductor", "*.json"))):   # 지휘자: 상황 어휘 · 규칙 · 장면 · 악기 · 분위기 성격 (글자 파일 — 고쳐 쓸 수 있음)
    cp(f, os.path.join(OUT, "data", "conductor", os.path.basename(f)))
for f in ("gu_small.sf2", "sso_small.sf2"):          # GeneralUser GS 16악기 · Sonatina 8악기만 남긴 판 (win/sf2_subset.py)
    cp(os.path.join(D, "sf", f), os.path.join(OUT, "data", "sf", f))
for f in ("sea.flac", "rain.flac"):                    # 주변 소리 (win/build/assets/amb, 링크)
    cp(os.path.join(D, "amb", f), os.path.join(OUT, "data", "amb", f))
for f in sorted(glob.glob(os.path.join(D, "piano", "*.flac"))):
    cp(f, os.path.join(OUT, "data", "piano", os.path.basename(f)))

README = """차량 BGM AI (실시간판) — 차 안 상황을 보고 AI 가 알아서 고르고, 듣는 동안 다음 악보를 계속 써서 바로 연주합니다

1. zip 을 통째로 풉니다 (바탕 화면 · 다운로드 어디든)
2. CAR_BGM 폴더의 CAR_BGM.exe 를 두 번 누릅니다 → 브라우저에 화면이 뜹니다
   (처음 한 번은 Windows 가 "PC 보호" 창을 띄울 수 있습니다 → [추가 정보] → [실행])
3. 🤖 알아서 (처음 화면)
   · [시작] → 지금 상황(여정 · 요일 · 시간대 · 날씨 · 장소 · 달리기 · 누구랑 · 차 안 소리 · 창문)을 보고 분위기 · 악기 · 빠르기를 정해 시작
   · 실제 차에선 내비 · 날씨 · 차량 센서 · 실내 마이크가 상황을 보냅니다. 시연에선 오른쪽(휴대폰은 아래) [상황 바꿔 보기]로 바꿔 보세요
     - 위 4개 단추는 한 번에 바꾸는 예: 비 오는 월요일 출근 · 주말 가족 바닷길 · 금요일 밤 둘이 · 심야 고속도로 혼자
     - 칸을 하나씩 바꾸면 음악이 몇 초 ~ 한 덩어리 뒤에 따라 바뀝니다 (아기 · 언성 · 과속 · 터널은 빨리)
     - 점선 칸 = 지휘자가 시계로 채운 것
   · "지금 이렇게 골랐어요" 에 왜 그렇게 했는지 한 줄이 나옵니다 (ⓘ 를 누르면 본 상황들)
   · 말로 요청: 칸에 쓰거나 🎙 (크롬 · 엣지 음성 인식) — 아기 잔다 · 조용히 · 신나게 · 다른 거 · 이거 좋다 · 파도 소리 · 음악 꺼 …
   · [🎙 차 안 말소리 듣기] 노트북 마이크로 말소리를 들어, 말이 커지면 음악을 줄이고 말과 겹치는 소리를 비웁니다
     (스피커로 나오는 음악 크기만큼은 빼고 듣습니다 · 이어폰이면 더 정확)
4. ✋ 직접 — 분위기 15개를 직접 고르고 [세부 조절] (음 높이 · 빠르기 · 음 수 · 세기 · 새로움 · 긴장감 · 울림)
   · 재즈 6 (비 오는 날 · 평온한 재즈 · 밤 드라이브 · 즐거운 대화 · 바닷가 보사노바 · 낮 드라이브)
   · 잔잔한 3 (아이 재우기 · 마음 가라앉히기 · 위로) · 클래식 3 (클래식 피아노 · 현악 앙상블 · 클래식 왈츠)
   · 새 3 (상쾌한 아침 · 밤 고속도로 · 눈 오는 저녁)
5. 켤 때마다 다른 곡입니다 (조 · 진행 · 선율 · 첫 편성이 매번 새로) · 이야기처럼 흘러가고(가 · 나 · 다 · 라 → 가' · 나' …),
   분위기가 바뀔 땐 선율 한 덩어리가 끝나는 곳에서 마지막 음에서 이어지는 2마디로 넘어갑니다
   · [끝내기] 마지막 4마디 + 마지막 화음으로 자연스럽게 끝 · 끝나는 중에 한 번 더 누르면 바로 끔
   · [악보 보기] AI 가 지금 쓰고 있는 악보 글자 · 악보는 C:\\Users\\<이름>\\차량BGM_결과\\ 에 쌓입니다 ([악보 폴더])
   · 알아서 하는 중에 직접 고른 것 · "이거 좋다" · "다른 거" 는 반응기록.jsonl 에 남습니다 (나중에 운전자 습관 학습용)
6. 지휘자 규칙은 data\\conductor\\*.json 글자 파일입니다 (상황 어휘 · 규칙 94개 · 장면 32개 · 악기 성격 25개 · 분위기 성격)

인터넷 · 설치 필요 없음 (AI · 사운드폰트 · 피아노 샘플이 전부 들어 있음, 파이썬 없음 · 음성 인식 🎙 만 브라우저가 인터넷을 씀)
브라우저 탭을 닫으면 30초 뒤 프로그램이 스스로 꺼집니다.
"""
THIRD = """차량 BGM AI 에 들어 있는 남의 것

프로그램
- FluidSynth 2.6.1 (LGPL-2.1) · SDL3 (zlib) · libsndfile (LGPL-2.1) — https://github.com/FluidSynth/fluidsynth (DLL 그대로)
- miniaudio 0.11.22 (MIT-0 / Public Domain) · dr_flac (MIT-0 / Public Domain) — https://github.com/mackron
- 실행 파일은 zig c++ (libc++ · MIT/Apache-2.0 with LLVM exception) 로 빌드

소리
- Accurate-Salamander Grand Piano (Chisato Yamauchi) / Salamander Grand Piano (Alexander Holm) — CC-BY 3.0, FLAC 16비트로 바꾸고 14초에서 자름
- GeneralUser GS (S. Christian Collins) — 자유 사용 · 재배포 허용, 쓰는 악기 16개 프리셋만 남김
- 바닷가 파도: "Ocean Waves on a Tropical Beach" (J.D. Savanyu, Wikimedia Commons) — CC0, 60초 고리로 다듬음
- 빗소리: "Rain (1)" (ezwa) · "Rain against the window" (cori) (Wikimedia Commons) — 퍼블릭 도메인, 섞어 120초 고리로 다듬음
- Sonatina Symphonic Orchestra (Mattias Westlund) — Creative Commons Sampling Plus 1.0, 바이올린 · 첼로 · 플루트 · 하프 · 클라리넷 · 오보에 · 호른 · 글로켄 프리셋만 남김

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
