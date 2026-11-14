# 귀(ear) 모델 — 안드로이드 묶음 v2 (2026-11-14)

차 안 소리 4초를 넣으면 **소리 28가지 확률 + 말투 감정 6가지 확률**이 나옵니다.
문턱을 넘은 소리를 한국어 단어로 바꾸는 규칙(`EarWords.java`)도 같이 들어 있습니다.

```
마이크 16kHz 모노 → 4초 창(2초마다) → ear_wave.onnx (또는 .tflite) → sounds[28] · emotion[6]
                                                                   → EarWords.toWords(… , Prosody.compute(창)) → "대화 · 웃음 · 밝은 …"
```

## 요청하신 4가지

**1. best.pt · thresholds.json** — 이 폴더에 있습니다.
- 레포의 `runs/ear`(10-30 1차본) 대신, 그걸 이어서 더 학습한 **ear2** 를 넣었습니다. 같은 시험 자료에서 mAP 0.273 → 0.315, 감정 0.562 → 0.577 로 더 좋습니다.
- 문턱도 ear2 에 맞춰 **앱과 같은 방식(4초 창 · 2초 간격)** 으로 다시 정했습니다. 1차본의 thresholds.json 은 ear2 와 짝이 안 맞으니 쓰지 마세요.

**2. 전처리 사양** — `ear_wave.onnx` / `.tflite` 를 쓰면 **전처리가 필요 없습니다.** 로그 멜 계산까지 모델 안에 넣어 두었습니다. 파형만 넣으면 됩니다. 멜을 직접 계산하고 싶을 때만 아래 "멜 직접 계산" 칸을 보세요.

**3. 클래스 순서 · 단어 규칙** — `labels.json`(순서 · 단어 · 문턱 · 믿을 만한 정도)과 `java/com/carbgm/ear/EarWords.java`(파이썬 규칙을 그대로 옮김)에 있습니다.

**4. ONNX · TFLite**

| 파일 | 크기 | 입력 |
|---|---|---|
| `ear_wave.onnx` | 22.7MB | 파형 `wav` float32 [N, 64000] |
| `ear_wave_float32.tflite` | 22.7MB | 파형 [1, 64000] |
| `ear_wave_float16.tflite` | 12.2MB | 파형 [1, 64000] (가중치 반정밀도, 결과 차이 0.001 안팎) |
| `ear_mel.onnx` | 19.9MB | 로그 멜 `logmel` [N, 64, 401] |

셋 다 파이토치 결과와 같은지 시험 벡터로 확인했습니다. 쓰는 연산은 Conv · Gather · MatMul · BatchNorm · AveragePool · Softmax 같은 기본 연산뿐입니다(opset 17).

## 4초 창 · 2초 간격

**그대로 두시면 됩니다.** 학습도 4초 조각으로 했고, 문턱도 4초 창 · 2초 간격으로 들어서 정했습니다.

## 입력 · 출력

- **입력** `wav`: 16kHz · 모노 · float32 · `int16 값 / 32768`(-1~1) · 64000개(4초). 마이크가 48kHz면 16kHz로 내려서 넣어 주세요.
- **출력**
  - `sounds` [1, 28]: 소리마다 0~1. 서로 따로 계산한 값이라 여러 개가 같이 켜질 수 있습니다.
  - `emotion` [1, 6]: 말투 감정 확률, 다 더하면 1. 순서는 anger · disgust · fear · happy · neutral · sad.
- ⚠ **TFLite 는 출력 차례가 바뀌어 있습니다**(0번이 [1,6] 감정, 1번이 [1,28] 소리). 모양으로 골라 쓰세요.
- **속도**: DGX(ARM) 코어 1개에서 창 하나 0.26초 걸렸습니다. 휴대폰은 아직 재 보지 않았는데, 2초마다 한 번이라 스레드 2~4개면 넉넉할 것 같습니다.

```kotlin
// ONNX Runtime (implementation "com.microsoft.onnxruntime:onnxruntime-android:<최신판>")
val env = OrtEnvironment.getEnvironment()
val session = env.createSession(assets.open("ear_wave.onnx").readBytes())
val x = OnnxTensor.createTensor(env, FloatBuffer.wrap(window), longArrayOf(1, 64000))   // window: FloatArray(64000)
session.run(mapOf("wav" to x)).use { r ->
    val sounds = (r[0].value as Array<FloatArray>)[0]      // 28
    val emotion = (r[1].value as Array<FloatArray>)[0]     // 6
    val words = EarWords.toWords(sounds, thresholds, emotion, Prosody.compute(window))
}
```

`thresholds` 는 `labels.json` 의 `sounds[i].threshold` 를 순서대로 담은 FloatArray(28)입니다.

## 확률 → 단어 (`EarWords.toWords`)

1. 문턱(`threshold`) 이상인 소리를 켭니다.
2. 아기 울음이 켜지면 '울음'은 끕니다. 목소리 종류가 둘 이상 켜지면 '대화'는 뺍니다(더 구체적인 단어를 남김).
3. 켜진 소리의 단어를 그 확률을 점수로 해서 넣습니다(바다 → "바다", "파도" 처럼 단어가 둘인 것도 있음).
4. 말하는 중일 때(대화가 문턱 이상이거나 고함이 켜짐) 감정 1등 확률이 0.4 이상이면 감정 단어를 넣습니다. 점수는 감정 확률 × 대화 확률입니다.
5. 말투 숫자 규칙(선택)
   - 말하는 중일 때만: 빠르기 3.8 이상 → "템포 빠른", 1.9 이하 → "템포 느린", 높낮이 흔들림 4반음 이상이면서 크기 흔들림 8dB 이상 → "격한"
   - 늘: 가장 큰 소리 -12dBFS 이상 → "시끄러운", -42 이하 → "조용한", 켜진 소리가 없고 -42 이하 → "고요한"
6. 점수 높은 순으로 돌려줍니다. 단어마다 종류(소리 · 감정 · 말투)가 붙어 있습니다.

창을 여러 개 합쳐서 판단하고 싶으면 `EarWords.merge(최근 창들)` 를 쓰세요. 소리는 최댓값, 감정은 대화 확률로 무게를 준 평균입니다(우리 파이썬 `listen.py` 와 같은 방식).

## 말투 숫자 (`Prosody.compute`, 선택)

신경망이 아니라 계산입니다. 4초 창 하나에 24ms쯤 걸립니다(DGX 자바 기준). 40ms 틀 · 10ms 간격으로 계산합니다.

- `loudDb`: 틀마다 RMS dB 의 최댓값
- `loudVar`: 소리 나는 틀(최댓값 -25dB 안쪽) dB 의 표준편차
- `pitchVar`: 목소리 틀(정규화 자기상관 최대값 > 0.5, 60~500Hz)의 높이를 반음으로 바꾼 표준편차
- `rate`: 90ms 로 편 크기 곡선에서 ±100ms 안 최댓값이면서 ±150ms 골보다 3dB 이상 솟은 봉우리 수 ÷ 소리 나는 시간(초)

마이크마다 절대값이 달라 대략적인 기준입니다. 빼고 써도 소리 · 감정 단어는 그대로 나옵니다(`toWords(…, null)`).

## 멜 직접 계산할 때 (`ear_mel.onnx` 입력)

- 16kHz · 4초 = 64000 샘플
- STFT: n_fft 512 · 창 400(hann periodic, 512 안 가운데 → 앞뒤 0 56개씩) · hop 160 · center(앞뒤 256 거울 붙이기 reflect) → 401틀
- 파워 |X|² (257칸) → HTK 멜 삼각 필터 64개(50~8000Hz, 정규화 없음) → 자연로그 `ln(멜 + 1e-6)`
- 모양 [1, 64, 401]
- 정답: `test/logmel_speech_ko.json` (`test/test_vectors/speech_ko.wav` 의 로그 멜)

## 확인하는 법

- `test/test_vectors/*.wav`: 4초 소리 6개(우리 TTS 한국어 · 영어 말, 우리 엔진 음악, 파도, 비, 고요)
- `test/expected.json`: 그 6개에 대한 파이토치 정답(소리 · 감정 확률, 말투 숫자, 단어)
- 자바 확인: `javac -d out java/com/carbgm/ear/*.java && java -cp out com.carbgm.ear.CheckVectors .` → "6개 중 6개 같음"
- 모델 확인: `python check_models.py .` (onnxruntime, 있으면 tflite 까지) → 확률 차이 0.00001 안팎(float16 은 0.001)

## 성능 · 한계 (꼭 봐 주세요)

시험 기준은 FSD50K 시험 세트, 4초 창입니다. 소리마다 점수가 `labels.json` 에 `test_ap` · `precision` · `recall` · `reliability` 로 들어 있습니다.

- **믿을 만함(good)**: 대화 · 노래 · 기침 · 음악 · 천둥 · 물소리 · 도로 · 사람들 · 쾅 소리
- **보통(ok)**: 웃음 · 고함 · 숨소리 · 새소리 · 풀벌레 · 비 · 사이렌 · 강아지 · 불꽃놀이
- **약함(weak)**: 아이 목소리 · 아기 울음 · 울음 · 속삭임 · 전화벨 · 바다 · 갈매기 · 바람 · 경적 · 기차. 화면에 바로 띄우기보다 참고용으로 쓰는 걸 권합니다.

그 밖에 알아 둘 것:
- **한국어 말**: 학습 자료가 거의 영어라서 약합니다. 우리 한국어 TTS 는 4초 창의 45%만 "대화"로 잡았습니다(영어는 86%). 예시 `speech_ko` 에서도 대화 확률이 0.49로 문턱 0.55 아래입니다.
- **감정**: 영어 배우 연기(CREMA-D)로 배워서 한국어 말투에는 대략적입니다. 시험 정확도는 58%(6가지 중)입니다.
- **차 소음**: 소음을 섞으면(SNR 10dB) mAP 가 0.315 → 0.256 으로 떨어집니다.
- 1차본보다 나아진 점: 1차 문턱을 그대로 쓰면 말소리에 "기침 · 음악"이 자주 같이 켜졌는데, ear2 와 새 문턱에선 사라졌습니다.

## 파일

- `best.pt`: ear2 파이토치 가중치(걸음 3000, 레포 `ear/model.py` 의 `Ear(64, 4)`)
- `thresholds.json` · `labels.json`
- `report/test_report_ear2.json` · `report/test_report_ear1_old.json`: 시험 점수(소리마다 AP, 문턱에서 정밀도 · 재현율)
- `java/com/carbgm/ear/`: `EarWords.java` · `Prosody.java` · `CheckVectors.java`(Java 11, 다른 라이브러리 없음, 패키지 이름은 바꿔 쓰셔도 됨)
- 만든 스크립트(레포 `car_bgm/ear/`): `export_android.py`(ONNX) · `eval_android.py`(채점 · 문턱) · `android/testvec.py` · `android/check_models.py`

## 출처

- 가중치를 학습한 자료: FSD50K(클립별 CC 라이선스) · CREMA-D(ODbL) · AxonData 아기 울음 샘플(CC-BY 4.0). 이 묶음에는 가중치만 들어 있고 원본 소리는 없습니다.
- 시험 벡터 소리: 우리 TTS · 우리 엔진 음악 · 파도 "Ocean Waves on a Tropical Beach"(CC0) · 비 "Rain (1)" · "Rain against the window"(퍼블릭 도메인) · 합성 잡음
