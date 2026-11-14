#!/bin/bash
# 윈도우 PC 에뮬레이터 묶음 → dist/pc_emulator/ (run_emulator.ps1 + apk/ 우리 앱 · 박수현 님 ear2 x86_64)
#   PC 에서: mkdir C:\CarBgmEmu -Force; scp -r "drboom@192.168.0.7:project/car_bgm/dist/pc_emulator/*" C:\CarBgmEmu\
#            powershell -ExecutionPolicy Bypass -File C:\CarBgmEmu\run_emulator.ps1
#   build_apk.sh 끝에서 부름 (APK 가 바뀌면 묶음도 새로)
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(dirname "$HERE")
OUT=$ROOT/dist/pc_emulator
EAR2=${EAR2_APK:-/home/drboom/project/music_android/releases/v1.0-ear2/music_android-ear2-x86_64.apk}
rm -rf "$OUT"
mkdir -p "$OUT/apk"
# PowerShell 5.1 은 BOM 없는 .ps1 을 CP949 로 읽어 한글이 깨짐 → UTF-8 BOM + CRLF 로
python3 -I -c 'import sys; s=open(sys.argv[1],encoding="utf-8").read().replace("\r\n","\n").replace("\n","\r\n"); open(sys.argv[2],"w",encoding="utf-8-sig",newline="").write(s)' \
    "$HERE/pc/run_emulator.ps1" "$OUT/run_emulator.ps1"
ln -f "$ROOT/dist/CAR_BGM-android.apk" "$OUT/apk/CAR_BGM-android.apk"
[ -f "$EAR2" ] && ln -f "$EAR2" "$OUT/apk/$(basename "$EAR2")" || echo "(박수현 님 ear2 APK 없음 — 우리 앱만: $EAR2)"
du -sh "$OUT"; ls -la "$OUT" "$OUT/apk" | grep -v "^total"
