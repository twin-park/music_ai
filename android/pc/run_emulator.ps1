# 윈도우 PC 안드로이드 에뮬레이터 — 차량 BGM AI(우리 앱) · Music(박수현 님 ear2 앱) 같이 깔고 켜기
#
#   PowerShell 에서 (처음 한 번은 구글에서 약 2GB 받음 · 다음부터는 바로 켜짐):
#     mkdir C:\CarBgmEmu -Force; scp -r "drboom@192.168.0.7:project/car_bgm/dist/pc_emulator/*" C:\CarBgmEmu\
#     powershell -ExecutionPolicy Bypass -File C:\CarBgmEmu\run_emulator.ps1
#
#   -Open ours     우리 앱을 앞에 띄움 (기본은 박수현 님 앱 ear2)
#   -Log           에뮬레이터 기록을 C:\CarBgmEmu\logcat_*.txt 로 저장 (앱이 죽었을 때 이 파일을 보내 주세요)
#   -Wipe          가상 기기를 새로 만듦 (앱 · 설정 다 지워짐)
#   다 지우기: 에뮬레이터 창 닫고 C:\CarBgmEmu 폴더 삭제
param([string]$Root = "C:\CarBgmEmu", [string]$Open = "ear2", [switch]$Log, [switch]$Wipe)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
[Console]::OutputEncoding = [Text.Encoding]::UTF8

$Sdk = Join-Path $Root "sdk"
$Dl = Join-Path $Root "dl"
$AvdHome = Join-Path $Root "avd"
$ApkDir = Join-Path $Root "apk"
$env:ANDROID_SDK_ROOT = $Sdk
$env:ANDROID_HOME = $Sdk
$env:ANDROID_AVD_HOME = $AvdHome
New-Item -ItemType Directory -Force $Sdk, $Dl, $AvdHome | Out-Null
$Emu = Join-Path $Sdk "emulator\emulator.exe"
$Adb = Join-Path $Sdk "platform-tools\adb.exe"

# 외부 프로그램 실행 → 출력 글자 (오류 출력도 같이, 멈추지 않음)
function Run([string]$exe, [string[]]$a) {
    $old = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $o = & $exe @a 2>&1 | ForEach-Object { "$_" }
    $ErrorActionPreference = $old
    return ($o -join "`n")
}

function Say([string]$s, [string]$c = "Green") { Write-Host $s -ForegroundColor $c }

# ── 기록만 저장 ──
if ($Log) {
    $f = Join-Path $Root ("logcat_" + (Get-Date -Format "MMdd_HHmmss") + ".txt")
    Start-Process -FilePath $Adb -ArgumentList "-e logcat -d -v time" -RedirectStandardOutput $f -NoNewWindow -Wait
    Say "기록 저장: $f (이 파일을 보내 주세요)"
    exit 0
}

# ── 1. 받기 (구글 공식 · SHA1 확인) ──
$Base = "https://dl.google.com/android/repository/"
$Parts = @(
    @{ Name = "에뮬레이터 37.2.13"; Url = $Base + "emulator-windows_x64-16740729.zip"; Sha1 = "4d7268aa7787c640ad892844e6c9a5f159e91ad3"; Into = $Sdk; Check = "emulator\emulator.exe" },
    @{ Name = "adb (platform-tools 37.0.1)"; Url = $Base + "platform-tools_r37.0.1-win.zip"; Sha1 = "e03e78b1d80b396f1c3358e31251cb31740e1110"; Into = $Sdk; Check = "platform-tools\adb.exe" },
    @{ Name = "안드로이드 14 (Google APIs · x86_64, 1.5GB)"; Url = $Base + "sys-img/google_apis/x86_64-34_r14.zip"; Sha1 = "e0f6c9a0691aa27bd597d0deb1bcfdc943ac8ca7"; Into = (Join-Path $Sdk "system-images\android-34\google_apis"); Check = "system-images\android-34\google_apis\x86_64\system.img" }
)
foreach ($p in $Parts) {
    if (Test-Path (Join-Path $Sdk $p.Check)) { continue }
    $zip = Join-Path $Dl ([IO.Path]::GetFileName($p.Url))
    $ok = (Test-Path $zip) -and ((Get-FileHash $zip -Algorithm SHA1).Hash -eq $p.Sha1.ToUpper())
    if (-not $ok) {
        Say "받는 중: $($p.Name)"
        & curl.exe -L --fail -o $zip $p.Url
        if ($LASTEXITCODE -ne 0) { throw "받기 실패: $($p.Url)" }
        if ((Get-FileHash $zip -Algorithm SHA1).Hash -ne $p.Sha1.ToUpper()) { throw "받은 파일이 깨졌습니다 (SHA1 다름): $zip — 다시 실행하세요" }
    }
    Say "푸는 중: $($p.Name)"
    New-Item -ItemType Directory -Force $p.Into | Out-Null
    & tar.exe -xf $zip -C $p.Into
    if ($LASTEXITCODE -ne 0) { throw "풀기 실패: $zip" }
    Remove-Item $zip
}

# ── 2. 가속 확인 (없으면 x86_64 에뮬레이터가 안 켜짐) ──
$acc = Run $Emu @("-accel-check")
if ($acc -notmatch "installed and usable") {
    Write-Host $acc
    Say "에뮬레이터 가속(하이퍼바이저)이 꺼져 있습니다." "Yellow"
    Say "  관리자 PowerShell 에서:  Enable-WindowsOptionalFeature -Online -FeatureName HypervisorPlatform -All" "Yellow"
    Say "  → 재부팅 → 이 스크립트를 다시 실행하세요. (BIOS 에서 가상화 VT-x / SVM 이 꺼져 있으면 그것도 켜야 합니다)" "Yellow"
    exit 1
}

# ── 3. 가상 기기 (가로 1920x1080 · 차 화면 비슷하게) ──
$Avd = "car_bgm"
$AvdDir = Join-Path $AvdHome "$Avd.avd"
if ($Wipe -and (Test-Path $AvdDir)) {
    Run $Adb @("-e", "emu", "kill") | Out-Null
    Start-Sleep 3
    Remove-Item -Recurse -Force $AvdDir
}
if (-not (Test-Path (Join-Path $AvdDir "config.ini"))) {
    New-Item -ItemType Directory -Force $AvdDir | Out-Null
    @(
        "avd.ini.encoding=UTF-8",
        "path=$AvdDir",
        "target=android-34"
    ) | Set-Content -Encoding ASCII (Join-Path $AvdHome "$Avd.ini")
    @(
        "AvdId=$Avd",
        "avd.ini.displayname=Car BGM 1920x1080",
        "avd.ini.encoding=UTF-8",
        "abi.type=x86_64",
        "hw.cpu.arch=x86_64",
        "hw.cpu.ncore=4",
        "hw.ramSize=4096",
        "vm.heapSize=512",
        "disk.dataPartition.size=8G",
        "image.sysdir.1=system-images\android-34\google_apis\x86_64\",
        "tag.id=google_apis",
        "tag.display=Google APIs",
        "target=android-34",
        "hw.lcd.width=1920",
        "hw.lcd.height=1080",
        "hw.lcd.density=240",
        "hw.initialOrientation=landscape",
        "hw.keyboard=yes",
        "hw.mainKeys=no",
        "hw.audioInput=yes",
        "hw.audioOutput=yes",
        "hw.gpu.enabled=yes",
        "hw.gpu.mode=auto",
        "showDeviceFrame=no",
        "PlayStore.enabled=false"
    ) | Set-Content -Encoding ASCII (Join-Path $AvdDir "config.ini")
    Say "가상 기기 만듦: $Avd"
}

# ── 4. 켜기 · 다 켜질 때까지 ──
Run $Adb @("start-server") | Out-Null
if ((Run $Adb @("devices")) -notmatch "emulator-\d+\s+device") {
    Say "에뮬레이터 켜는 중 (처음엔 1~3분) — 창이 따로 뜹니다"
    # -allow-host-audio: PC 마이크를 에뮬레이터 마이크로 (말소리 듣기 · 귀 모델)
    Start-Process -FilePath $Emu -ArgumentList @("-avd", $Avd, "-allow-host-audio", "-no-boot-anim", "-gpu", "auto")
}
$t0 = Get-Date
while ((Run $Adb @("-e", "shell", "getprop", "sys.boot_completed")).Trim() -ne "1") {
    if (((Get-Date) - $t0).TotalSeconds -gt 360) { throw "6분이 지나도 안 켜졌습니다 — 에뮬레이터 창의 오류 글을 확인하세요" }
    Start-Sleep 3
}
Say "켜짐"

# ── 5. apk\ 의 APK 전부 깔기 (권한은 미리 허용 -g) ──
$apks = @(Get-ChildItem $ApkDir -Filter *.apk -ErrorAction SilentlyContinue)
if ($apks.Count -eq 0) { Say "깔 APK 가 없습니다: $ApkDir (맨 위 scp 줄을 먼저)" "Yellow" }
foreach ($f in $apks) {
    Say "깔기: $($f.Name) ($([math]::Round($f.Length / 1MB))MB)"
    $o = Run $Adb @("-e", "install", "-r", "-g", $f.FullName)
    if ($o -match "UPDATE_INCOMPATIBLE.*?package (\S+)") {
        Say "  서명이 다른 예전 판이 있어 지우고 다시 깝니다: $($Matches[1])" "Yellow"
        Run $Adb @("-e", "uninstall", $Matches[1]) | Out-Null
        $o = Run $Adb @("-e", "install", "-r", "-g", $f.FullName)
    }
    if ($o -match "Success") { Say "  완료" } else { Say "  실패:`n$o" "Red" }
}

# ── 6. 앱 켜기 ──
$pkg = if ($Open -eq "ours") { "com.carbgm.app" } else { "com.twinpark.music" }
Run $Adb @("-e", "shell", "monkey", "-p", $pkg, "-c", "android.intent.category.LAUNCHER", "1") | Out-Null
Say ""
Say "다 됐습니다. 에뮬레이터 창에서 쓰시면 됩니다."
Say "  · 두 앱: 아래에서 위로 쓸면 앱 목록 — '차량 BGM AI'(우리 앱) · 'Music'(박수현 님 앱)" "White"
Say "  · 소리는 PC 스피커로, 마이크는 PC 마이크로 들어갑니다" "White"
Say "  · 앱이 죽으면: powershell -ExecutionPolicy Bypass -File $Root\run_emulator.ps1 -Log  → 저장된 파일을 보내 주세요" "White"
Say "  · 끄기: 에뮬레이터 창 닫기 · 다시 켜기: 같은 명령 (받기 · 깔기는 건너뜀)" "White"
