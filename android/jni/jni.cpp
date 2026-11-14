// 안드로이드 ↔ C++ 엔진 다리 — 엔진(app.cpp 의 run_app)을 줄 하나에 띄우고, 화면 포트 · 오류만 알려 줌
//   Java: com.carbgm.app.Native.start(데이터 폴더, 악보 폴더, 기록 파일) → port() 가 > 0 이면 http://127.0.0.1:port/ 를 WebView 로
#include <jni.h>
#include <android/log.h>
#include <atomic>
#include <cstdio>
#include <string>
#include <thread>
#include <unistd.h>
#include <vector>

int run_app(int argc, char **argv);
std::string app_error();
extern std::atomic<int> g_app_port;

static std::atomic<bool> started{false};

static std::string S(JNIEnv *env, jstring s) {
    if (!s) return "";
    const char *c = env->GetStringUTFChars(s, nullptr);
    std::string r = c ? c : "";
    if (c) env->ReleaseStringUTFChars(s, c);
    return r;
}

extern "C" JNIEXPORT jint JNICALL Java_com_carbgm_app_Native_start(JNIEnv *env, jclass, jstring jdata, jstring jout, jstring jlog) {
    if (started.exchange(true)) return 1;                       // 이미 켜짐 (서비스가 다시 불려도 한 번만)
    const std::string data = S(env, jdata), out = S(env, jout), log = S(env, jlog);
    if (!log.empty() && std::freopen(log.c_str(), "w", stdout)) {   // printf · fprintf(stderr) 를 앱 폴더 기록 파일로
        dup2(fileno(stdout), fileno(stderr));
        setvbuf(stdout, nullptr, _IOLBF, 0);
        setvbuf(stderr, nullptr, _IONBF, 0);
    }
    std::thread([data, out] {
        std::vector<std::string> a = {"car_bgm", "--data", data, "--out", out, "--no-browser", "--no-watch"};
        std::vector<char *> argv;
        for (auto &s : a) argv.push_back(&s[0]);
        argv.push_back(nullptr);
        const int rc = run_app((int)a.size(), argv.data());     // 잘 켜지면 돌아오지 않음 (HTTP 서버가 돎)
        __android_log_print(ANDROID_LOG_ERROR, "car_bgm", "엔진이 멈춤 (%d)", rc);
        if (g_app_port.load() <= 0) g_app_port = -(rc ? rc : 1);
    }).detach();
    return 0;
}

extern "C" JNIEXPORT jint JNICALL Java_com_carbgm_app_Native_port(JNIEnv *, jclass) { return g_app_port.load(); }

extern "C" JNIEXPORT jstring JNICALL Java_com_carbgm_app_Native_error(JNIEnv *env, jclass) { return env->NewStringUTF(app_error().c_str()); }
