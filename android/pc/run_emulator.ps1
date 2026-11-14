# 윈도우 PC 에뮬레이터 — Pleos Connect(현대 차량 OS) 화면에서 차량 BGM AI(우리 앱) · Music(박수현 님 ear2 앱) 깔고 켜기
#
#   PowerShell 에서:
#     mkdir C:\CarBgmEmu -Force; scp -r "drboom@192.168.0.7:project/car_bgm/dist/pc_emulator/*" C:\CarBgmEmu\
#     powershell -ExecutionPolicy Bypass -File C:\CarBgmEmu\run_emulator.ps1
#
#   처음 한 번: Pleos Connect v2.1.0 이미지 4GB 받기(풀면 18GB · C: 여유 30GB 필요) + 42dot 라이선스 동의
#   다음부터는 바로 켜짐 (Pleos 안내대로 매번 콜드 부트 1~2분)
#
#   -Open ours     우리 앱을 앞에 띄움 (기본은 박수현 님 앱 ear2)
#   -Os plain      Pleos 대신 일반 안드로이드 14 태블릿 화면 (1920x1080)
#   -Drive         감포 내륙 → 해안 주행(7분, 70km/h)을 에뮬레이터 GPS 로 재생 — 2분쯤 뒤 바닷가에 들어서면 음악이 바뀜
#                  (에뮬레이터가 켜져 있으면 깔기는 건너뛰고 바로 달림 · 경로 파일은 routes\ — GPX 는 에뮬레이터 ⋯ → Location → Routes 로도 재생 가능)
#   -Log           에뮬레이터 기록을 C:\CarBgmEmu\logcat_*.txt 로 저장 (앱이 죽었을 때 이 파일을 보내 주세요)
#   -Wipe          가상 기기를 새로 만듦 (앱 · 설정 다 지워짐)
#   다 지우기: 에뮬레이터 창 닫고 C:\CarBgmEmu 폴더 삭제
param([string]$Root = "C:\CarBgmEmu", [string]$Open = "ear2", [string]$Os = "pleos", [switch]$Log, [switch]$Wipe, [switch]$Drive, [string]$Route = "gampo_coast")

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

# ── 주행 재생: 경로(1초마다 위도,경도)를 에뮬레이터 GPS 로 ──
function Drive-Route {
    $csv = Join-Path $Root "routes\$Route.csv"
    if (-not (Test-Path $csv)) { Say "경로 파일이 없습니다: $csv (맨 위 scp 줄을 먼저)" "Red"; return }
    $pts = @(Get-Content $csv | Where-Object { $_ -match "," })
    Run $Adb @("-e", "shell", "cmd", "location", "set-location-enabled", "true") | Out-Null              # 위치 켜기 (꺼져 있으면 앱이 못 받음)
    Run $Adb @("-e", "shell", "cmd", "location", "set-location-enabled", "true", "--user", "10") | Out-Null # 차량 OS 화면 사용자
    Say "주행 재생: $Route ($([math]::Floor($pts.Count / 60))분 $($pts.Count % 60)초 · 70km/h) — 2분쯤 뒤 바닷가에 들어서면 음악이 바닷가로 바뀌고 파도 소리가 깔립니다"
    Say "  (Music 앱 DEV: 'AI IS CONDUCTING' 길게 누르기 → 맨 아래 위치 · 해안까지 거리 · 속도 · 멈추려면 Ctrl+C)" "White"
    $t0 = Get-Date
    for ($i = 0; $i -lt $pts.Count; $i++) {
        $p = $pts[$i].Split(",")
        Run $Adb @("-e", "emu", "geo", "fix", $p[1].Trim(), $p[0].Trim()) | Out-Null                 # geo fix 는 경도 먼저
        if ($i % 30 -eq 0) { Write-Host ("  {0}분 {1:00}초 · {2}, {3}" -f [math]::Floor($i / 60), ($i % 60), $p[0], $p[1]) }
        $wait = ($t0.AddSeconds($i + 1) - (Get-Date)).TotalMilliseconds
        if ($wait -gt 0) { Start-Sleep -Milliseconds ([int]$wait) }
    }
    Say "도착 (위치는 마지막 자리에 그대로 둡니다)"
}

# ── 기록만 저장 ──
if ($Log) {
    $f = Join-Path $Root ("logcat_" + (Get-Date -Format "MMdd_HHmmss") + ".txt")
    Start-Process -FilePath $Adb -ArgumentList "-e logcat -d -v time" -RedirectStandardOutput $f -NoNewWindow -Wait
    Say "기록 저장: $f (이 파일을 보내 주세요)"
    exit 0
}

# ── 0. 어떤 화면(OS) ──
$G = "https://dl.google.com/android/repository/"
$PleosXml = "https://nexus-playground.pleos.ai/repository/raw-releases/connect-avd/2.x/crp-sys-img.xml"
if ($Os -eq "plain") {
    $Avd = "car_bgm"
    $Img = @{ Name = "안드로이드 14 (Google APIs · x86_64, 1.5GB)"; Url = $G + "sys-img/google_apis/x86_64-34_r14.zip"; Size = 1563721130; Sha1 = "e0f6c9a0691aa27bd597d0deb1bcfdc943ac8ca7"
              Into = "system-images\android-34\google_apis"; Top = "x86_64" }
} else {
    $Avd = "pleos"
    $Img = @{ Name = "Pleos Connect v2.1.0 (42dot · x86_64, 4GB)"; Url = "https://nexus-playground.pleos.ai/repository/raw-releases/connect-avd/2.x/crp_car_emulator.zip"; Size = 4087751964; Sha1 = "b4f858d5bcc6c71506d7edfc872bcb9e5a11acaa"
              Into = "system-images\android-34\pleos_car_emulator"; Top = "crp_avd_out_x86_64" }
}
$ImgDir = Join-Path (Join-Path $Sdk $Img.Into) "x86_64"
$ImgOk = Join-Path $ImgDir ".carbgm_ok"

# ── 1. 받기 (구글 · Pleos 공식, SHA1 확인 · 끊기면 다시 실행하면 이어 받음) ──
function Get-Zip($p) {
    $zip = Join-Path $Dl ([IO.Path]::GetFileName($p.Url))
    if (Test-Path $zip) {
        $len = (Get-Item $zip).Length
        if ($len -eq $p.Size -and (Get-FileHash $zip -Algorithm SHA1).Hash -eq $p.Sha1.ToUpper()) { return $zip }
        if ($len -ge $p.Size) { Remove-Item $zip }
    }
    Say "받는 중: $($p.Name)"
    & curl.exe -L --fail -C - -o $zip $p.Url
    if ($LASTEXITCODE -ne 0) { throw "받기 실패 (다시 실행하면 이어 받습니다): $($p.Url)" }
    if ((Get-FileHash $zip -Algorithm SHA1).Hash -ne $p.Sha1.ToUpper()) { Remove-Item $zip; throw "받은 파일이 깨졌습니다 (SHA1 다름) — 다시 실행하세요" }
    return $zip
}

$Tools = @(
    @{ Name = "에뮬레이터 37.2.13"; Url = $G + "emulator-windows_x64-16740729.zip"; Size = 455344678; Sha1 = "4d7268aa7787c640ad892844e6c9a5f159e91ad3"; Check = "emulator\emulator.exe" },
    @{ Name = "adb (platform-tools 37.0.1)"; Url = $G + "platform-tools_r37.0.1-win.zip"; Size = 8044989; Sha1 = "e03e78b1d80b396f1c3358e31251cb31740e1110"; Check = "platform-tools\adb.exe" }
)
foreach ($p in $Tools) {
    if (Test-Path (Join-Path $Sdk $p.Check)) { continue }
    $zip = Get-Zip $p
    Say "푸는 중: $($p.Name)"
    & tar.exe -xf $zip -C $Sdk
    if ($LASTEXITCODE -ne 0) { throw "풀기 실패: $zip" }
    Remove-Item $zip
}

$plainOld = Join-Path $Sdk "system-images\android-34\google_apis\x86_64\system.img"   # 이전 판 스크립트로 받아 둔 일반 이미지
if ($Os -eq "plain" -and (Test-Path $plainOld) -and -not (Test-Path $ImgOk)) { New-Item -ItemType File -Force $ImgOk | Out-Null }

if (-not (Test-Path $ImgOk)) {
    if ($Os -ne "plain") {
        # Pleos Connect SDK 는 42dot 라이선스 동의가 있어야 씀 (Android Studio SDK Manager 에서 받을 때와 같은 글)
        $lic = Join-Path $Root "PLEOS_SDK_LICENSE.txt"
        $agreed = Join-Path $Root ".pleos_license_agreed"
        if (-not (Test-Path $agreed)) {
            $licXml = Join-Path $Dl "crp-sys-img.xml"
            & curl.exe -sL --fail -o $licXml $PleosXml
            if ($LASTEXITCODE -ne 0) { throw "Pleos 목록을 못 받음: $PleosXml" }
            $xml = [IO.File]::ReadAllText($licXml, [Text.Encoding]::UTF8)
            if ($xml -match '(?s)<license[^>]*>(.*?)</license>') { [IO.File]::WriteAllText($lic, [Net.WebUtility]::HtmlDecode($Matches[1]), [Text.Encoding]::UTF8) }
            Say "Pleos Connect 에뮬레이터는 42dot 의 'Software Development Kit License Agreement' 에 동의해야 받을 수 있습니다." "Yellow"
            Say "  전문: $lic  (Android Studio 에서 받을 때 나오는 것과 같은 글)" "Yellow"
            $ans = Read-Host "  동의하면 y 를 입력하세요"
            if ($ans -ne "y") { Say "동의하지 않아 멈춥니다. (일반 안드로이드 화면은: -Os plain)" "Yellow"; exit 1 }
            New-Item -ItemType File -Force $agreed | Out-Null
        }
    }
    $drive = $Root.Substring(0, 1)
    $needGB = if ($Os -eq "plain") { 6 } else { 30 }
    $freeGB = [math]::Floor((Get-PSDrive -Name $drive).Free / 1GB)
    if ($freeGB -lt $needGB) { throw "${drive}: 여유 공간이 모자랍니다 (필요 ${needGB}GB · 남음 ${freeGB}GB)" }
    $zip = Get-Zip $Img
    $into = Join-Path $Sdk $Img.Into
    if (Test-Path $ImgDir) { Remove-Item -Recurse -Force $ImgDir }
    $top = Join-Path $into $Img.Top
    if (Test-Path $top) { Remove-Item -Recurse -Force $top }
    New-Item -ItemType Directory -Force $into | Out-Null
    Say "푸는 중: $($Img.Name) — 몇 분 걸립니다"
    & tar.exe -xf $zip -C $into
    if ($LASTEXITCODE -ne 0) { throw "풀기 실패: $zip" }
    if ($Img.Top -ne "x86_64") { Rename-Item $top "x86_64" }
    New-Item -ItemType File -Force $ImgOk | Out-Null
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

# ── -Drive: 이미 켜져 있으면 깔기 없이 바로 달림 ──
if ($Drive -and ((Run $Adb @("devices")) -match "emulator-\d+\s+device") -and ((Run $Adb @("-e", "shell", "getprop", "sys.boot_completed")).Trim() -eq "1")) {
    Drive-Route
    exit 0
}

# ── 3. 가상 기기 ──
$AvdDir = Join-Path $AvdHome "$Avd.avd"
if ($Wipe -and (Test-Path $AvdDir)) {
    Run $Adb @("-e", "emu", "kill") | Out-Null
    Start-Sleep 5
    Remove-Item -Recurse -Force $AvdDir
}
if (-not (Test-Path (Join-Path $AvdDir "config.ini"))) {
    New-Item -ItemType Directory -Force $AvdDir | Out-Null
    @("avd.ini.encoding=UTF-8", "path=$AvdDir", "target=android-34") | Set-Content -Encoding ASCII (Join-Path $AvdHome "$Avd.ini")
    $common = @(
        "AvdId=$Avd", "avd.ini.encoding=UTF-8", "abi.type=x86_64", "hw.cpu.arch=x86_64", "hw.cpu.ncore=4",
        "hw.ramSize=4096", "disk.dataPartition.size=8G", "target=android-34",
        "hw.keyboard=yes", "hw.mainKeys=no", "hw.audioInput=yes", "hw.audioOutput=yes",
        "hw.gpu.enabled=yes", "hw.initialOrientation=landscape", "showDeviceFrame=no", "PlayStore.enabled=false"
    )
    if ($Os -eq "plain") {
        $cfg = $common + @(
            "avd.ini.displayname=Car BGM 1920x1080", "image.sysdir.1=system-images\android-34\google_apis\x86_64\",
            "tag.id=google_apis", "tag.display=Google APIs", "vm.heapSize=512",
            "hw.lcd.width=1920", "hw.lcd.height=1080", "hw.lcd.density=240", "hw.gpu.mode=auto"
        )
    } else {
        # Pleos 이미지 안의 devices.xml(Pleos Connect v2.1.0 · 2560x1440 · 160dpi) + Pleos 안내(RAM 4GB · 콜드 부트)
        $cfg = $common + @(
            "avd.ini.displayname=Pleos Connect v2.1.0", "image.sysdir.1=system-images\android-34\pleos_car_emulator\x86_64\",
            "tag.id=android-automotive", "tag.display=Pleos Connect v2.1.0 APIs",
            "hw.device.name=Pleos_Connect_v2_0", "hw.device.manufacturer=42dot",
            "hw.lcd.width=2560", "hw.lcd.height=1440", "hw.lcd.density=160", "hw.gpu.mode=host",
            "hw.multi_display_window=no", "hw.hotplug_multi_display=no",
            "fastboot.forceColdBoot=yes", "fastboot.forceFastBoot=no"
        )
    }
    $cfg | Set-Content -Encoding ASCII (Join-Path $AvdDir "config.ini")
    Say "가상 기기 만듦: $Avd"
}

# ── 4. 켜기 (다른 가상 기기가 켜져 있으면 끄고) · 다 켜질 때까지 ──
Run $Adb @("start-server") | Out-Null
$start = $true
if ((Run $Adb @("devices")) -match "emulator-\d+\s+device") {
    $cur = ((Run $Adb @("-e", "emu", "avd", "name")) -split "`n")[0].Trim()
    if ($cur -eq $Avd) { $start = $false }
    else {
        Say "켜져 있던 '$cur' 을 끄고 '$Avd' 를 켭니다" "Yellow"
        Run $Adb @("-e", "emu", "kill") | Out-Null
        Start-Sleep 8
    }
} elseif (Get-Process -Name "qemu-system-x86_64*" -ErrorAction SilentlyContinue) {
    $start = $false   # 이미 켜지는 중
}
if ($start) {
    Say "에뮬레이터 켜는 중 ($Avd · 처음엔 2~5분) — 창이 따로 뜹니다"
    # -allow-host-audio: PC 마이크를 에뮬레이터 마이크로 (말소리 듣기 · 귀 모델)
    $args2 = @("-avd", $Avd, "-allow-host-audio", "-no-boot-anim", "-gpu", "auto")
    if ($Os -ne "plain") { $args2 += "-no-snapshot" }    # Pleos 안내: 콜드 부트
    Start-Process -FilePath $Emu -ArgumentList $args2
}
$t0 = Get-Date
while ((Run $Adb @("-e", "shell", "getprop", "sys.boot_completed")).Trim() -ne "1") {
    if (((Get-Date) - $t0).TotalSeconds -gt 600) { throw "10분이 지나도 안 켜졌습니다 — 에뮬레이터 창의 오류 글을 확인하세요" }
    Start-Sleep 3
}
Start-Sleep 5
Say "켜짐"

# ── 5. apk\ 의 APK 전부 깔기 (권한은 미리 허용 -g · 모든 사용자에게) ──
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

# ── 6. 앱 켜기 (차량 OS 는 화면 쓰는 사용자가 10번이라 --user current) ──
$comp = if ($Open -eq "ours") { "com.carbgm.app/.MainActivity" } else { "com.twinpark.music/.MainActivity" }
Run $Adb @("-e", "shell", "am", "start", "--user", "current", "-n", $comp) | Out-Null
Say ""
Say "다 됐습니다. 에뮬레이터 창에서 쓰시면 됩니다."
Say "  · 두 앱: 아래 막대의 앱 목록(네모 4개) — '차량 BGM AI'(우리 앱) · 'Music'(박수현 님 앱)" "White"
Say "  · 소리는 PC 스피커로, 마이크는 PC 마이크로 들어갑니다" "White"
Say "  · 앱이 죽으면: powershell -ExecutionPolicy Bypass -File $Root\run_emulator.ps1 -Log  → 저장된 파일을 보내 주세요" "White"
Say "  · 차가 달리는 것처럼: 같은 명령 끝에 -Drive (감포 내륙 → 해안 7분 · 2분쯤 뒤 바닷가)" "White"
Say "  · 끄기: 에뮬레이터 창 닫기 · 다시 켜기: 같은 명령 (받기 · 깔기는 건너뜀)" "White"
if ($Drive) { Start-Sleep 20; Drive-Route }                                 # 앱이 음악을 시작할 틈을 두고 달림
