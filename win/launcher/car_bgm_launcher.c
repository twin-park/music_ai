/*
 * CAR_BGM.exe — 차량 BGM AI 윈도우판 실행 파일 (2026-10-31)
 *
 *   사용자: "dist 에 윈도우 실행파일 넣어둬"
 *   같은 폴더의 python\pythonw.exe 로 app\score\studio\server.py 를 띄운다 (콘솔 창 없음) — 서버가 브라우저를 연다.
 *   AI 모델 · 사운드폰트 · 피아노 샘플 · fluidsynth 는 이 폴더 안의 것만 쓴다 (CAR_BGM_HOME).
 *   브라우저 탭을 닫으면 서버가 30초 뒤 스스로 꺼진다.
 *
 *   빌드 (리눅스에서 교차): python -m ziglang cc -target x86_64-windows-gnu -O2 -municode -Wl,--subsystem,windows -o CAR_BGM.exe car_bgm_launcher.c car_bgm.rc
 */
#define WIN32_LEAN_AND_MEAN
#ifndef UNICODE
#define UNICODE
#endif
#define _UNICODE
#include <windows.h>
#include <stdio.h>
#include <wchar.h>

static void fail(const wchar_t *msg)
{
    MessageBoxW(NULL, msg, L"차량 BGM AI", MB_OK | MB_ICONERROR);
}

static int exists(const wchar_t *p)
{
    return GetFileAttributesW(p) != INVALID_FILE_ATTRIBUTES;
}

int WINAPI wWinMain(HINSTANCE hi, HINSTANCE hp, PWSTR cl, int show)
{
    (void)hi; (void)hp; (void)cl; (void)show;
    wchar_t exe[MAX_PATH * 4], dir[MAX_PATH * 4], py[MAX_PATH * 4], app[MAX_PATH * 4];
    DWORD n = GetModuleFileNameW(NULL, exe, (DWORD)(sizeof(exe) / sizeof(exe[0])));
    if (n == 0 || n >= sizeof(exe) / sizeof(exe[0])) {
        fail(L"실행 파일 위치를 못 읽었습니다");
        return 2;
    }
    wcscpy(dir, exe);
    wchar_t *slash = wcsrchr(dir, L'\\');
    if (slash) *slash = 0;
    swprintf(py, sizeof(py) / sizeof(py[0]), L"%ls\\python\\pythonw.exe", dir);
    swprintf(app, sizeof(app) / sizeof(app[0]), L"%ls\\app\\score\\studio\\server.py", dir);
    if (!exists(py) || !exists(app)) {
        fail(L"python\\pythonw.exe 또는 app\\score\\studio\\server.py 가 없습니다.\r\n"
             L"zip 을 통째로 푼 폴더 안에서 CAR_BGM.exe 를 실행하십시오.");
        return 2;
    }
    SetEnvironmentVariableW(L"PYTHONUTF8", L"1");
    SetEnvironmentVariableW(L"PYTHONIOENCODING", L"utf-8");
    SetEnvironmentVariableW(L"PYTHONDONTWRITEBYTECODE", L"1");
    SetEnvironmentVariableW(L"CAR_BGM_HOME", dir);

    wchar_t cmd[MAX_PATH * 10];
    swprintf(cmd, sizeof(cmd) / sizeof(cmd[0]), L"\"%ls\" -X utf8 -B \"%ls\"", py, app);
    STARTUPINFOW si;
    PROCESS_INFORMATION pi;
    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    ZeroMemory(&pi, sizeof(pi));
    if (!CreateProcessW(py, cmd, NULL, NULL, FALSE, CREATE_NO_WINDOW, NULL, dir, &si, &pi)) {
        wchar_t m[256];
        swprintf(m, 256, L"파이썬을 시작하지 못했습니다 (오류 %lu)", GetLastError());
        fail(m);
        return 2;
    }
    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);
    return 0;
}
