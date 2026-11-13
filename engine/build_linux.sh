#!/bin/bash
# 리눅스(DGX)에서 시험용으로 빌드 — 실행할 땐 LD_LIBRARY_PATH 에 libfluidsynth.so.3 이 있는 곳
set -e
cd "$(dirname "$0")"
mkdir -p build
SRC="src/model.cpp src/gen.cpp src/theory.cpp src/song.cpp src/compose.cpp src/vary.cpp src/notation.cpp src/dsp.cpp src/piano.cpp src/amb.cpp src/fluid.cpp src/engine.cpp src/util.cpp"
g++ -O3 -std=c++17 -Wall -Wno-unused-result -pthread -o build/engine_cli tools/engine_cli.cpp $SRC -ldl
python3 tools/embed_web.py >/dev/null
gcc -O2 -c src/ma_impl.c -o build/ma_impl.o
g++ -O3 -std=c++17 -Wall -Wno-unused-result -pthread -o build/car_bgm src/app.cpp src/http.cpp $SRC build/ma_impl.o -ldl -lm
echo "→ build/engine_cli build/car_bgm"
