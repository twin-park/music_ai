# 안드로이드 빌드 환경 (DGX Spark · arm64 · sudo 없이) — source android/env.sh
#   구글 공식 NDK clang · aapt2 · zipalign · adb 는 x86_64 전용이라 DGX 에선 못 돌림 → 이렇게 대신:
#     컴파일러   conda env car_bgm_android 의 clang 18 + NDK r27d(clang 18) 의 sysroot · 런타임  (~/opt/android/bin/<abi>-linux-android24-clang[++])
#     aapt2 · zipalign · adb   우분투 arm64 패키지에서 꺼낸 것 (~/opt/android/ubuntu-tools, 감싼 스크립트 ~/opt/android/bin)
#     javac(JDK 17) · d8 · apksigner   자바라 어디서나 (conda openjdk 17 · build-tools 35.0.1 의 jar)
export ANDROID_HOME=${ANDROID_HOME:-/home/drboom/Android/Sdk}
export ANDROID_SDK_ROOT=$ANDROID_HOME
export ANDROID_NDK_HOME=${ANDROID_NDK_HOME:-$ANDROID_HOME/ndk/27.3.13750724}
export JAVA_HOME=${CAR_BGM_JAVA_HOME:-/home/drboom/miniconda3/envs/car_bgm_android/lib/jvm}
export ANDROID_TOOLS=/home/drboom/opt/android/bin
export ANDROID_PLATFORM_JAR=$ANDROID_HOME/platforms/android-34/android.jar   # 우분투 aapt2(안드로이드 14판)는 android-35 리소스 표를 못 읽음 → 34 (targetSdk 도 34)
export ANDROID_BUILD_TOOLS=$ANDROID_HOME/build-tools/35.0.1
export FLUIDSYNTH_ANDROID=/home/drboom/opt/android/dl_fluidsynth/x          # fluidsynth-v2.6.2-android24.zip 푼 곳 (include · lib/<abi>)
export PATH=$ANDROID_TOOLS:$JAVA_HOME/bin:$ANDROID_HOME/cmdline-tools/latest/bin:$PATH
