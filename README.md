# 차량 BGM AI (CAR_BGM)

분위기를 고르면 AI가 그 자리에서 악보를 쓰고 바로 연주하는 차량용 배경음악입니다.
같은 분위기라도 켤 때마다 다른 곡이 나오고, 재생 중에도 계속 새로 씁니다.

- **화음 AI** (0.86M) → **선율 AI** (4.87M) → 편곡 규칙 → 악기 연주 순서로 만듭니다. (v3, 11-11: v2 보다 3배 작고 20배 넘게 빠름)
- 엔진은 C++17 하나로 돌아갑니다. AI는 int8 가중치를 정수 곱(NEON/AVX2)으로 CPU에서 계산하고, 단락 하나 쓰는 데 0.2초쯤 걸립니다.
- 진행이 조에서 떠내려가지 않게 붙잡고(조 안 화음 · 으뜸화음으로 돌아오기), 분위기마다 화성 양념 정도를 정해 둡니다.
- 분위기 12개: 재즈 6 · 잔잔 3 · 클래식 3 (클래식 피아노 · 현악 앙상블 · 클래식 왈츠)
- 곡 흐름은 "가·나·다·라 → 가'·나'·다' → 마·바·사…"처럼 짜입니다. 새 생각을 들려주고 한참 뒤에 바꿔서 다시 부릅니다.
- 선율 AI가 예전 마디를 그대로 베끼지 못하게 막아 둬서 같은 것만 되풀이하지 않습니다.
- 분위기를 바꾸면 멜로디 한 덩어리가 끝나는 곳에서 넘어갑니다. 이전 악기가 마지막 음에서 이어 받아 다리를 놓고, 가까운 조로 옮겨 갑니다.
- 화면에서 음 높이·빠르기·음 수·세기·새로움·긴장감·울림 7가지를 조절할 수 있습니다.
- 바닷가·비 같은 상황에는 실제 파도·빗소리 녹음을 음악 밑에 작게 깔 수 있습니다 (`POST /api/amb {"sea":1,"rain":0}`, 화면 버튼). 녹음은 CC0·퍼블릭 도메인이고 `engine/src/amb.cpp`가 섞습니다.

## 바로 들어 보기

[Releases](../../releases)에 받아서 바로 쓸 수 있는 파일을 올려 두었습니다.

- `CAR_BGM-win64.zip`: 윈도우 실행 파일입니다. 압축을 풀고 `CAR_BGM.exe`를 실행하면 브라우저에 화면이 뜹니다.
- `car_bgm_demo_8min.mp3`: 실시간 연주를 8분 녹음한 것입니다. 비 오는 날 → 4:42 즐거운 대화 → 6:41 바닷가 보사노바 → 7:49 끝 순서입니다.
- `score_chord_best.pt`, `score_melody_best.pt`: 학습한 체크포인트입니다. 이어서 학습하거나 다시 내보낼 때 씁니다.

## 폴더

- `engine/`: C++ 실시간 엔진 (지금 쓰는 판)
  - `src/`
    - `model.cpp`: AI 계산
    - `gen.cpp`: 낱말 뽑기와 베끼기 막기
    - `compose.cpp`: 작곡과 분위기 넘어가기
    - `vary.cpp`: 이야기 흐름
    - `engine.cpp`: 연주·섞기·실시간 처리
    - `app.cpp`, `http.cpp`: 웹 화면 (:7700)
  - `web/index.html`: 화면 (`tools/embed_web.py`로 exe 안에 넣음)
  - `data/chord.bin`, `data/melody.bin`: 엔진이 쓰는 int8 AI
  - `data/calib.txt`, `data/tune.txt`: 악기 크기 보정표와 음 높이 보정표
  - `tools/`
    - `engine_cli`: 소리 장치 없이 파일로 녹음하거나 보정
    - `evolve_stats`: 단락끼리 얼마나 닮았나 재기
    - `mel_metrics.py`: 실제 곡과 같은 잣대로 비교
    - `harm_dump` + `harm_metrics.py`: 화성 잣대 (조 안 화음 · 강박 코드음 · 세로 부딪힘)
    - `bench_model`: AI 계산 속도
    - `export_model.py`: `.pt` → `.bin`
    - `make_zip.py`: 윈도우 묶음 만들기
- `score/ai/`: 악보 AI 학습 (Python · PyTorch)
  - `tok.py`: 낱말 정의
  - `data.py`: 학습 자료
  - `lmd_leadsheet.py`: Lakh MIDI → 리드시트
  - `train3.py`: v3 학습 (`--teacher_v2` 로 옛 큰 모델에게서 증류)
  - `tok3.py`: v3 낱말 (갈래 · 강박 코드음 정도 조건)
  - `pdmx_leadsheet.py`: PDMX 공개 악보 → 리드시트 (클래식)
  - `eval_v2_v3.py`: 옛 모델과 같은 검증 조각으로 견주기
  - `train.py`: v2 학습
  - `gen.py`: 생성
  - `npmodel.py`: numpy 계산기, 내보내기 기준
- `score/`: 파이썬 작곡·편곡과 `studio/` 화면 (C++ 엔진 전 판)
- `win/`
  - `sf2_subset.py`: 사운드폰트에서 쓰는 악기만 남김
  - `prep_piano.py`: 피아노 샘플 준비
  - `launcher/`: 예전 파이썬판 실행기 소스
- `music/`, `web/`, `compose/`, `ear/`, `conduct.py`, `demo.py`: 앞선 실험들
  - `music/`: 악보 낱말 음악 모델
  - `web/`: 브라우저판
  - `compose/`: 규칙 작곡
  - `ear/`: 주변 소리·감정 듣기
- `기획안_초안.md`, `PLAN.md`: 기획안과 작업 계획
- `docs/상황_음악_정리.md`: 상황(터널 · 날씨 · 동승자 …) → 음악 정리 초안 · `docs/V3_계획.md`: v3 작업 기록
- `dist/읽어주세요.txt`, `dist/상황별_파라미터.md`: 결과물 설명

## 올리지 않은 것

- **학습 데이터** (`data/`, 51GB): POP909 · EWLD · Lakh MIDI · MidiCaps · PDMX 등입니다. 어디서 받았는지는 `data/dl_*.txt`에 적어 두었습니다.
- **학습 중간본·결과물:** `runs/`, `score/out/`, 빌드 결과, 음원은 올리지 않았습니다.
- **사운드폰트와 피아노 샘플:** GeneralUser GS, Sonatina Symphonic Orchestra 일부, Salamander 피아노입니다. Release의 윈도우 zip 안 `CAR_BGM/data/`에 들어 있습니다.

## 소스에서 빌드

리눅스에서 시험할 때는 다음처럼 합니다.

```bash
cd engine
./build_linux.sh                     # → build/car_bgm, build/engine_cli
# Release zip 의 CAR_BGM/data/sf · CAR_BGM/data/piano 를 engine/data/ 에 복사
LD_LIBRARY_PATH=<libfluidsynth.so.3 있는 곳> ./build/car_bgm --data data
```

윈도우 exe는 `engine/build_win.sh`(zig 교차 빌드) → `python3 engine/tools/make_zip.py` 순서로 만듭니다.
지금은 스크립트 안의 zig 위치와 윈도우용 DLL 위치(`win/build/dl`)가 이 컴퓨터에 맞춰져 있습니다.

## 라이선스

함께 쓰는 사운드폰트·샘플·라이브러리·학습 데이터의 출처와 조건은 윈도우 zip 안 `THIRD_PARTY.txt`에 있습니다.
`engine/tools/make_zip.py`가 이 파일을 만듭니다.
