#!/bin/bash
# 윈도우 실행 파일 (리눅스에서 zig 로 교차 빌드) → build/win/CAR_BGM.exe
set -e
cd "$(dirname "$0")"
ZIG="/home/drboom/project/2026_project/hotel_win/build/tools_venv/bin/python -m ziglang"
mkdir -p build/win
python3 tools/embed_web.py
SRC="src/app.cpp src/http.cpp src/model.cpp src/gen.cpp src/theory.cpp src/song.cpp src/compose.cpp src/vary.cpp src/notation.cpp src/dsp.cpp src/piano.cpp src/amb.cpp src/json.cpp src/conductor.cpp src/fluid.cpp src/engine.cpp src/util.cpp"
$ZIG cc -target x86_64-windows-gnu -O2 -c src/ma_impl.c -o build/win/ma_impl.o
$ZIG c++ -target x86_64-windows-gnu -O2 -std=c++17 -D_USE_MATH_DEFINES -Wno-unused-result -o build/win/CAR_BGM.exe $SRC build/win/ma_impl.o win/car_bgm.rc \
    -Wl,--subsystem,windows -lws2_32 -lshell32 -lole32
ls -la build/win/CAR_BGM.exe
