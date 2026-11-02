// 소리 다듬기 (compose/render.py 믹서의 실시간판): 2차 버터워스 · 팬 · 합성곱 잔향(나눠 FFT) · 압축 · 미리보기 리미터
#pragma once
#include <complex>
#include <vector>

constexpr int SR = 48000;

struct Biquad {                       // scipy butter(2, f, fs) 와 같은 꼴 (RBJ Q=1/√2)
    double b0 = 1, b1 = 0, b2 = 0, a1 = 0, a2 = 0, z1 = 0, z2 = 0;
    void design(bool high, double f);
    inline float run(float x) {
        double y = b0 * x + z1;
        z1 = b1 * x - a1 * y + z2;
        z2 = b2 * x - a2 * y;
        return (float)y;
    }
};

void fft(std::vector<std::complex<float>> &a, bool inv);

// 잔향: render.py make_ir 과 같은 꼴(소음 × 지수 감쇠, 꼬리일수록 고음 빠짐, 앞 지연) · 블록 512 나눠 합성곱
struct Convolver {
    static constexpr int B = 512, N = 1024;
    int P = 0;
    std::vector<std::vector<std::complex<float>>> H[2], X[2];
    std::vector<float> in[2], out[2];
    int head = 0;
    void make(double sec, unsigned seed = 0);
    void process(const float *inL, const float *inR, float *outL, float *outR);   // B 개씩
};

// 압축 (render.compress 와 같은 셈 — 30ms 창을 가운데 맞추려 720 샘플 늦춤)
struct Compressor {
    double thr = -15, ratio = 1.5, att = .02, rel = .4;
    static constexpr int W = 1440, D = 720, RING = 4096;
    std::vector<float> ms = std::vector<float>(RING, 0.f), xl = std::vector<float>(RING, 0.f), xr = std::vector<float>(RING, 0.f);
    double sum = 0, sm_r = 0, sm_a = 0;
    long i = 0;
    void process(float *L, float *R, int n);
};

// 미리보기 리미터 (render.limit 와 같은 셈: 앞뒤 3ms 최대 → 3ms 평균, -1dB) — 216 샘플 늦춤
struct Limiter {
    static constexpr int LOOK = 144, D = 216, RING = 2048;
    double c = 0.891250938;
    std::vector<float> a = std::vector<float>(RING, 0.f), gm = std::vector<float>(RING, 1.f);
    std::vector<float> xl = std::vector<float>(RING, 0.f), xr = std::vector<float>(RING, 0.f);
    std::vector<std::pair<long, float>> dq;      // 미끄럼 최대 (단조 큐)
    size_t dq_head = 0;
    double gsum = LOOK;                           // gm 평균 창 합
    long i = 0;
    void process(float *L, float *R, int n);
};

double active_db(const std::vector<float> &mono);
