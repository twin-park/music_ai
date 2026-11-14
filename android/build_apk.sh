#!/bin/bash
# 안드로이드 APK 만들기 (DGX arm64 에서 Gradle 없이) → dist/CAR_BGM-android.apk
#   ./android/build_apk.sh            arm64-v8a(휴대폰 · 차) + x86_64(PC 에뮬레이터 · Pleos 에뮬레이터)
#   ABIS="arm64-v8a" ./android/build_apk.sh   휴대폰용만 (빠름 · 작음)
# 순서: 화면 넣기 → C++ 엔진 .so (ABI 마다) → 자바 → dex → 리소스 · 자료(assets/data) → APK → 정렬 → 서명(디버그 키)
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(dirname "$HERE")
EN=$ROOT/engine
source "$HERE/env.sh"
ABIS=${ABIS:-"arm64-v8a x86_64"}
B=$HERE/build
APP=$HERE/app/src/main
VN="0.6-$(date +%m%d)"
VC=$(date +%y%m%d%H)
OUT=$ROOT/dist/CAR_BGM-android.apk
rm -rf "$B/obj" "$B/stage" "$B/classes" "$B/assets" "$B"/*.apk "$B"/res.zip
mkdir -p "$B/obj" "$B/stage/lib" "$B/classes" "$B/assets/data"

echo "── 1. 화면 (web/index.html → src/web_ui.h)"
python3 "$EN/tools/embed_web.py"

echo "── 2. C++ 엔진 ($ABIS)"
SRC="app.cpp http.cpp model.cpp gen.cpp theory.cpp song.cpp compose.cpp vary.cpp notation.cpp dsp.cpp piano.cpp amb.cpp json.cpp conductor.cpp fluid.cpp engine.cpp util.cpp"
TC=$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/linux-x86_64
for abi in $ABIS; do
    case $abi in
        arm64-v8a) T=aarch64-linux-android ;;
        x86_64) T=x86_64-linux-android ;;
        *) echo "모르는 ABI: $abi"; exit 1 ;;
    esac
    CC=$ANDROID_TOOLS/${T}24-clang; CXX=$ANDROID_TOOLS/${T}24-clang++
    O=$B/obj/$abi; mkdir -p "$O" "$B/stage/lib/$abi"
    CXXF="-O3 -std=c++17 -fPIC -DNDEBUG -ffunction-sections -fdata-sections -Wall -Wno-unused-result"
    # 파일마다 따로 (4개씩 — CPU 를 꽉 채우지 않게)
    { for f in $SRC; do echo "$EN/src/$f"; done; echo "$HERE/jni/jni.cpp"; } |
        xargs -P 4 -I{} sh -c '"$0" $1 -c "$2" -o "$3/$(basename "$2" .cpp).o"' "$CXX" "$CXXF" {} "$O"
    "$CC" -O2 -fPIC -c "$EN/src/ma_impl.c" -o "$O/ma_impl.o"
    "$CXX" -shared -o "$B/stage/lib/$abi/libcarbgm.so" "$O"/*.o -llog -ldl -lm \
        -Wl,--no-undefined -Wl,--gc-sections -Wl,-z,max-page-size=16384 -Wl,--build-id=sha1 -s
    # FluidSynth 2.6.2 (공식 android24 판) 과 그 짝들 · libc++_shared (NDK)
    for l in fluidsynth sndfile oboe ogg opus FLAC vorbis vorbisenc; do cp "$FLUIDSYNTH_ANDROID/lib/$abi/lib$l.so" "$B/stage/lib/$abi/"; done
    cp "$TC/sysroot/usr/lib/$T/libc++_shared.so" "$B/stage/lib/$abi/"
    ls -la "$B/stage/lib/$abi/libcarbgm.so" | awk '{print "   " $5 " " $9}'
done

echo "── 3. 자바 → dex"
javac -source 8 -target 8 -bootclasspath "$ANDROID_PLATFORM_JAR:$ANDROID_BUILD_TOOLS/core-lambda-stubs.jar" -encoding UTF-8 -Xlint:-options -nowarn \
    -d "$B/classes" $(find "$APP/java" -name '*.java')
mkdir -p "$B/stage/dex"
java -cp "$ANDROID_BUILD_TOOLS/lib/d8.jar" com.android.tools.r8.D8 --release --min-api 24 --lib "$ANDROID_PLATFORM_JAR" \
    --output "$B/stage" $(find "$B/classes" -name '*.class')

echo "── 4. 자료 (engine/data → assets/data) — 윈도우판(make_zip.py)과 같은 목록"
D=$EN/data
A=$B/assets/data
put() { mkdir -p "$(dirname "$A/$1")"; ln -f "$(realpath "$D/$1")" "$A/$1" 2>/dev/null || cp "$(realpath "$D/$1")" "$A/$1"; }
for f in chord.bin melody.bin tune.txt calib.txt sf/gu_small.sf2 sf/sso_small.sf2 amb/sea.flac amb/rain.flac; do put "$f"; done
for f in "$D"/conductor/*.json; do put "conductor/$(basename "$f")"; done
for f in "$D"/piano/*.flac; do put "piano/$(basename "$f")"; done
(cd "$A" && find . -type f | sed 's#^\./##' | LC_ALL=C sort | while read -r f; do printf '%s\t%s\n' "$f" "$(stat -c %s "$f")"; done) > "$B/assets/data.list"
(cd "$A" && LC_ALL=C sort "$B/assets/data.list" | cut -f1 | xargs cat | sha1sum | cut -c1-16) > "$B/assets/data.version"
echo "   $(wc -l < "$B/assets/data.list")개 · $(du -shL "$A" | cut -f1) · 판 $(cat "$B/assets/data.version")"

echo "── 5. 리소스 · APK"
aapt2 compile --dir "$APP/res" -o "$B/res.zip"
aapt2 link -o "$B/unsigned.apk" -I "$ANDROID_PLATFORM_JAR" --manifest "$APP/AndroidManifest.xml" \
    --min-sdk-version 24 --target-sdk-version 34 --version-code "$VC" --version-name "$VN" \
    -A "$B/assets" -0 flac --auto-add-overlay "$B/res.zip"
(cd "$B/stage" && zip -q -r -9 "$B/unsigned.apk" classes*.dex lib)

echo "── 6. 정렬 · 서명 (디버그 키 ~/.android/debug.keystore — 같은 키로 서명해야 덮어 설치됨)"
KS=$HOME/.android/debug.keystore
if [ ! -f "$KS" ]; then
    mkdir -p "$(dirname "$KS")"
    keytool -genkeypair -keystore "$KS" -storepass android -alias androiddebugkey -keypass android \
        -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=Android Debug,O=Android,C=US" >/dev/null 2>&1
fi
zipalign -f 4 "$B/unsigned.apk" "$B/aligned.apk"
mkdir -p "$(dirname "$OUT")"
java -jar "$ANDROID_BUILD_TOOLS/lib/apksigner.jar" sign --ks "$KS" --ks-pass pass:android --key-pass pass:android \
    --ks-key-alias androiddebugkey --out "$OUT" "$B/aligned.apk"
java -jar "$ANDROID_BUILD_TOOLS/lib/apksigner.jar" verify "$OUT"
rm -f "$OUT.idsig"
echo "→ $OUT ($(du -h "$OUT" | cut -f1) · 판 $VN · 코드 $VC · $ABIS)"
