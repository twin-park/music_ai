// 주변 소리 — 바닷가 파도 · 빗소리를 음악 밑에 작게 깔기 (실제 녹음, data/amb/*.flac 고리)
//   켜고 끄면 몇 초에 걸쳐 천천히 커지고 작아짐 · 음악 볼륨 · 통화 중 줄이기를 따라감 · 음악이 끝나면 같이 사라짐
//   녹음은 처음 켤 때 읽음 (소리 내는 줄은 읽기를 기다리지 않음 — 다 읽은 뒤에 넘겨받음)
#pragma once
#include <atomic>
#include <cstdint>
#include <memory>
#include <mutex>
#include <string>
#include <vector>

struct Ambience {
    enum Kind { SEA, RAIN, N };
    static const char *NAME[N];                   // "sea" · "rain" (파일 이름 · API 이름)
    struct Loop { std::vector<int16_t> x; long frames = 0; };   // 48kHz 스테레오
    std::string dir;
    std::atomic<float> level[N];                  // 사용자가 정한 크기 0 (끔) … 1 (기본 · 작게) … 2
    std::atomic<bool> run{false};                 // 음악이 나오는 동안만 (작곡 줄이 정함)
    void open(const std::string &d) { dir = d; for (auto &l : level) l = 0; }
    bool set(int k, float v, std::string *err = nullptr);   // 크기 정하기 (처음이면 녹음을 읽음)
    // 소리 줄: L · R 에 더함 (gain = 음악 볼륨 × 통화 줄이기)
    void render(float *L, float *R, int n, float gain);
    size_t loaded_bytes() const;

private:
    std::atomic<Loop *> loop_[N] = {};
    std::unique_ptr<Loop> own_[N];
    std::mutex load_mtx;
    long pos_[N] = {};
    float g_[N] = {};                             // 지금 크기 (천천히 따라감)
};
