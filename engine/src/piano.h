// 실제 녹음 피아노 (Accurate-Salamander, compose/render.py Salamander 의 실시간판)
//   가까운 녹음 음을 속도만 바꿔 쓰고, 세기층 두 개를 섞음. 손(페달) 떼면 낮은 음일수록 길게 울리며 사라짐.
#pragma once
#include <map>
#include <mutex>
#include <string>
#include <vector>

struct PianoSample { std::vector<short> x; long frames = 0; double srr = 1; };

struct Piano {
    std::string dir;
    std::map<std::pair<int, int>, std::string> files;     // (음, 층번호 0~3) → 파일
    std::map<std::pair<int, int>, PianoSample> cache;
    std::vector<int> notes;
    std::mutex mtx;
    bool open(const std::string &dir);
    const PianoSample *get(int note, int layer);          // 처음 쓸 때 읽음
    void preload();                                       // 다 읽어 두기 (실시간 중 파일 읽기 없게)

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
