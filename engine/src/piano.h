// 실제 녹음 피아노 (Accurate-Salamander, compose/render.py Salamander 의 실시간판)
//   가까운 녹음 음을 속도만 바꿔 쓰고, 세기층 두 개를 섞음. 손(페달) 떼면 낮은 음일수록 길게 울리며 사라짐.
#pragma once
#include <atomic>
#include <map>
#include <memory>
#include <mutex>
#include <thread>
#include <string>
#include <vector>

struct PianoSample { std::vector<short> x; long frames = 0; double srr = 1; };

struct Piano {
    std::string dir;
    std::map<std::pair<int, int>, std::string> files;     // (음, 층번호 0~3) → 파일
    std::map<std::pair<int, int>, std::unique_ptr<PianoSample>> cache;
    std::vector<int> notes;
    std::mutex mtx;
    std::thread bg;
    std::atomic<bool> bg_stop{false};
    ~Piano() { bg_stop = true; if (bg.joinable()) bg.join(); }
    bool open(const std::string &dir);
    const PianoSample *get(int note, int layer);          // 처음 쓸 때 읽음 (파일 풀기는 자물쇠 밖에서)
    void preload();                                       // 다 읽어 두기
    // 메모리 아끼기: 자주 쓰는 가운데 음역 · 여린~보통 세기만 뒤에서 미리 읽고(preload_common),
    // 나머지는 작곡 줄이 그 음을 예약할 때(warm) 읽음 → 소리 내는 줄은 파일을 읽지 않음
    void preload_common();
    void warm(int p, int v);
    void pick(int p, int v, int &note, int &la, int &lb, double &f) const;   // 음 · 세기 → 가까운 녹음 음 · 섞을 두 층
    size_t loaded_bytes();

    struct Voice {
        const PianoSample *s[2] = {nullptr, nullptr};
        float w[2] = {0, 0};
        double pos[2] = {0, 0}, inc[2] = {0, 0};
        long t = 0, k1 = 0, nout = 0;                     // 지난 샘플 · 손 뗀 자리 · 끝
        double rel = .25;
        bool on = false;
    };
    std::vector<Voice> voices;
    // 소리 시작 (start 는 이 블록 안 샘플 자리), dur = 손 떼기까지 초
    void note(int p, int v, double dur, int start);
    void release_all(int at);                             // 지금 블록 at 자리에서 모두 손 뗌
    void cap_all(int at, long n);                         // 지금 울리는 음은 at + n 샘플 안에 손 뗌 (뒤에 오는 새 음은 그대로)
    void render(float *L, float *R, int n);
    struct Pending { int p, v; double dur; int start; };
    std::vector<Pending> pend;
};
