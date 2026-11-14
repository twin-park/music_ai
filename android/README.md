# 차량 BGM AI — 안드로이드 앱

윈도우판과 같은 C++ 엔진을 앱 안에서 돌리고, 같은 화면을 WebView로 띄웁니다.
결과물은 `dist/CAR_BGM-android.apk` 하나입니다(휴대폰 arm64 + PC·Pleos 에뮬레이터 x86_64).

```
앱 켜기 → EngineService(포그라운드 · 알림) → assets/data 를 앱 폴더로 풂(처음 한 번 · 약 140MB)
       → libcarbgm.so(엔진) 켜기 → 127.0.0.1:7700 HTTP → MainActivity 의 WebView 가 그 화면을 엶
```

## 설치 · 실행

1. `CAR_BGM-android.apk`를 휴대폰으로 옮겨 누릅니다. "출처를 알 수 없는 앱" 허용을 물으면 허용합니다.
   - USB로 연결했다면 DGX에서 `source android/env.sh && adb install -r dist/CAR_BGM-android.apk`도 됩니다.
2. 처음 켜면 마이크·알림 권한을 묻습니다.
   - 마이크: 🎙 말로 요청하기, 차 안 말소리 듣기에 씁니다.
   - 알림: 연주 중 알림과 [끄기] 단추에 씁니다.
3. 처음 한 번은 "음악 자료 푸는 중 n%"가 몇 초 걸립니다. 다음부터는 바로 켜집니다.
4. 화면은 윈도우판과 같습니다(🤖 알아서 / ✋ 직접, 분위기 32개, 상황 바꿔 보기).
5. 끄는 법
   - 뒤로 가기: 앱만 내려가고 음악은 계속됩니다.
   - 완전히 끄기: 알림의 [끄기]를 누르세요.

문제가 생기면 화면에 오류와 기록(앱 폴더의 `log.txt` 끝부분)이 뜹니다. 그 화면을 찍어 보내 주세요.

## 개발 환경 (DGX Spark · arm64 · sudo 없이)

구글 공식 NDK clang, aapt2, zipalign, adb는 x86_64 전용이라 DGX에서는 돌지 않습니다. 그래서 아래처럼 대신했습니다.
환경은 `source android/env.sh` 한 줄로 켜집니다.

- **SDK** `~/Android/Sdk`
  - cmdline-tools 20.0: 최신 21판은 sdkmanager가 x86 실행 파일이라 못 씁니다.
  - platforms android-34 · 35, build-tools 35.0.1(jar만 씀), NDK r27d.
- **C/C++ 컴파일러** `~/opt/android/bin/{aarch64,x86_64}-linux-android24-clang[++]`
  - conda env `car_bgm_android`의 clang 18에 NDK r27d(같은 clang 18)의 sysroot와 런타임을 붙인 감싸기 스크립트입니다.
- **aapt2 · zipalign · adb** `~/opt/android/bin/*`
  - 우분투 24.04 arm64 패키지(`apt-get download`)를 `~/opt/android/ubuntu-tools`에 풀어 쓴 감싸기 스크립트입니다.
  - 우분투 aapt2는 안드로이드 14판이라 android-35 리소스 표를 못 읽습니다. 그래서 컴파일·링크는 android-34로 합니다(targetSdk 34).
- **자바** conda env `car_bgm_android`의 OpenJDK 17
  - javac, d8(build-tools jar), apksigner(jar)에 씁니다.
- **FluidSynth** 공식 `fluidsynth-v2.6.2-android24.zip`을 `~/opt/android/dl_fluidsynth/x`에 풀었습니다.
  - libfluidsynth와 그 짝들(sndfile·oboe·ogg·opus·FLAC·vorbis)이 들어 있습니다.
- **서명 키** `~/.android/debug.keystore`(디버그 키)
  - 같은 키로 서명해야 지운 뒤 다시 깔지 않고 덮어 설치됩니다.

빌드:

```bash
./android/build_apk.sh                       # 두 ABI · 30초 안팎 → dist/CAR_BGM-android.apk
ABIS="arm64-v8a" ./android/build_apk.sh      # 휴대폰용만
```

Gradle은 쓰지 않습니다. 순서는 `build_apk.sh` 안에 다 있습니다:
화면 넣기 → 엔진 .so → javac → d8 → aapt2 → zip → zipalign → apksigner.

## 파일

- `jni/jni.cpp`: 자바와 엔진을 잇는 다리입니다. `run_app()`을 줄 하나에서 띄우고 포트와 오류를 알려 줍니다.
- `app/src/main/AndroidManifest.xml`: 권한(INTERNET · 마이크 · 포그라운드 서비스 · 알림), cleartext(127.0.0.1)가 들어 있습니다.
- `app/src/main/java/com/carbgm/app/`
  - `MainActivity`: WebView와 준비 문구를 띄우고, getUserMedia 마이크 권한을 넘겨줍니다.
  - `EngineService`: 포그라운드 서비스입니다. 자료 풀기, 엔진 켜기, 알림 [끄기]를 맡습니다.
  - `SpeechBridge`: 🎙를 안드로이드 SpeechRecognizer에 잇습니다. `index.html`이 이것을 `webkitSpeechRecognition` 꼴로 감쌉니다.
  - `Native`: JNI 함수를 둡니다.
- `tools/make_icon.py`: 아이콘(다크 + 초록)을 만듭니다.
- 엔진 쪽에서 고친 것
  - `app.cpp`: `main`을 `run_app`으로 나누고, `--out`·`--no-watch` 옵션을 더했습니다. 안드로이드에선 오류를 logcat으로 보냅니다.
  - `engine.cpp`: 안드로이드에서는 `libfluidsynth.so`를 엽니다.

## 아직 안 된 것

- 실제 기기·에뮬레이터 실행은 아직 시험하지 못했습니다. DGX(arm64 리눅스)용 안드로이드 에뮬레이터가 없습니다.
- 귀(ear) 모델은 아직 앱에 들어 있지 않습니다. 말소리 크기만 웹 화면의 마이크로 듣습니다.
- 음성 인식은 기기의 음성 인식기(구글 앱 등)가 있어야 🎙가 보입니다.
- Pleos Connect(AAOS)용으로 다듬는 일이 남았습니다. 운전 중 화면 제한(distraction optimized)과 차량 API 연결입니다.
