#!/bin/bash
# 휴대폰(차 · 에뮬레이터도)에 앱 깔고 → 켜고 → 오류 기록 보기 — DGX 에서 adb, 무선 디버깅으로 (USB 는 udev 규칙이 없어 권한 막힘)
#
# 휴대폰 준비 (처음 한 번)
#   설정 → 휴대전화 정보 → 소프트웨어 정보 → 빌드번호 7번 누르기 → 개발자 옵션 → [무선 디버깅] 켜기 (DGX 와 같은 와이파이)
#   ./android/phone.sh pair 192.168.0.12:37123 123456     [페어링 코드로 기기 페어링] 창의 IP:포트 · 6자리 코드
#   ./android/phone.sh connect 192.168.0.12:41234         [무선 디버깅] 첫 화면의 IP 주소 및 포트 (페어링 포트와 다름)
#
# 깔고 켜기 (기록은 화면에 나오고 logs/phone/ 에도 남음 · Ctrl+C 로 기록 보기만 끝, 앱은 계속)
#   ./android/phone.sh ear2        박수현 님 앱 music_android v1.0-ear2 (기기 ABI 에 맞춰 arm64 / x86_64 자동)
#   ./android/phone.sh ours        우리 앱 dist/CAR_BGM-android.apk
#   ./android/phone.sh 파일.apk     아무 APK
#   ./android/phone.sh log ear2    깔지 않고 기록만 다시 (앱이 죽었으면 죽은 이유)
#   ./android/phone.sh devices     연결된 기기 · ./android/phone.sh stop  adb 끄기
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(dirname "$HERE")
source "$HERE/env.sh"
EAR2=/home/drboom/project/music_android/releases/v1.0-ear2
usage() { sed -n '2,14p' "$0" | sed 's/^# \{0,1\}//'; exit 1; }

LOGONLY=0
case "${1:-}" in
    pair) [ $# -eq 3 ] || usage; exec adb pair "$2" "$3" ;;
    connect) [ $# -eq 2 ] || usage; adb connect "$2"; adb devices -l; exit ;;
    devices) adb devices -l; exit ;;
    stop) adb kill-server; echo "adb 끔"; exit ;;
    log) LOGONLY=1; shift ;;
    ""|-h|--help) usage ;;
esac
WHAT=${1:-}
[ -n "$WHAT" ] || usage

if [ "$(adb get-state 2>/dev/null)" != "device" ]; then
    echo "연결된 기기가 없습니다. 먼저 pair → connect (맨 위 설명: ./android/phone.sh)"
    adb devices -l
    exit 1
fi
ABI=$(adb shell getprop ro.product.cpu.abi | tr -d '\r')
MODEL=$(adb shell getprop ro.product.model | tr -d '\r')
SDK=$(adb shell getprop ro.build.version.sdk | tr -d '\r')
case "$WHAT" in
    ear2) [ "$ABI" = x86_64 ] && APK=$EAR2/music_android-ear2-x86_64.apk || APK=$EAR2/music_android-ear2-arm64.apk ;;
    ours) APK=$ROOT/dist/CAR_BGM-android.apk ;;
    *) APK=$WHAT ;;
esac
[ -f "$APK" ] || { echo "APK 가 없음: $APK"; exit 1; }
PKG=$(aapt2 dump badging "$APK" 2>/dev/null | sed -n "s/^package: name='\([^']*\)'.*/\1/p")
ACT=$(aapt2 dump badging "$APK" 2>/dev/null | sed -n "s/^launchable-activity: name='\([^']*\)'.*/\1/p")
[ -n "$PKG" ] && [ -n "$ACT" ] || { echo "APK 에서 패키지 · 시작 화면을 못 읽음: $APK"; exit 1; }
echo "기기 $MODEL (Android API $SDK · $ABI) · 앱 $PKG · $(basename "$APK")"

if [ $LOGONLY = 0 ]; then
    echo "깔는 중 ($(du -h "$APK" | cut -f1), 와이파이라 30초~1분)…"
    out=$(adb install -r "$APK" 2>&1); echo "$out" | tail -1
    if echo "$out" | grep -q "UPDATE_INCOMPATIBLE\|signatures do not match"; then
        echo "→ 예전에 다른 키로 깐 같은 앱이 있습니다. 지우고 다시: adb uninstall $PKG  (앱 안의 기록 · 설정도 지워짐)"; exit 1
    fi
    echo "$out" | grep -q "^Success" || exit 1
    adb logcat -c
    adb shell am start -W -n "$PKG/$ACT" | grep -E "Status|TotalTime" | tr -d '\r'
fi

mkdir -p "$ROOT/logs/phone"
LOG=$ROOT/logs/phone/${PKG}_$(date +%m%d_%H%M%S).txt
PID=""
for _ in $(seq 1 20); do PID=$(adb shell pidof "$PKG" | tr -d '\r'); [ -n "$PID" ] && break; sleep 0.5; done
if [ -z "$PID" ]; then
    echo "앱이 떠 있지 않습니다 (죽었거나 안 켜짐) — 죽은 기록:" | tee "$LOG"
    adb logcat -d -b crash -v time | tee -a "$LOG" | tail -40
    adb logcat -d -v time | grep -E "$PKG|AndroidRuntime|DEBUG|libc" | tee -a "$LOG" | tail -40
    echo "→ 기록 $LOG"
    exit 1
fi
echo "켜짐 (pid $PID) — 이 앱의 기록 (Ctrl+C 로 끝, 앱은 계속) → $LOG"
trap 'echo; echo "→ 기록 $LOG"; adb logcat -d -b crash -v time | grep -q "$PKG" && echo "⚠ 죽은 기록 있음: ./android/phone.sh log $WHAT"' EXIT
adb logcat -v time --pid="$PID" '*:I' | tee "$LOG"
