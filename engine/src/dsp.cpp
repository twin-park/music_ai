#include "dsp.h"
#include "rng.h"
#include <algorithm>
#include <cmath>

void Biquad::design(bool high, double f) {
    const double w = 2 * M_PI * f / SR, cw = std::cos(w), sw = std::sin(w), alpha = sw / (2 * 0.7071067811865476);
    double a0 = 1 + alpha;
    if (high) { b0 = (1 + cw) / 2; b1 = -(1 + cw); b2 = (1 + cw) / 2; }
    else { b0 = (1 - cw) / 2; b1 = 1 - cw; b2 = (1 - cw) / 2; }
    a1 = -2 * cw; a2 = 1 - alpha;
    b0 /= a0; b1 /= a0; b2 /= a0; a1 /= a0; a2 /= a0;
    z1 = z2 = 0;
}

void fft(std::vector<std::complex<float>> &a, bool inv) {
    const size_t n = a.size();
    for (size_t i = 1, j = 0; i < n; i++) {
        size_t bit = n >> 1;
        for (; j & bit; bit >>= 1) j ^= bit;
        j ^= bit;
        if (i < j) std::swap(a[i], a[j]);
    }
    for (size_t len = 2; len <= n; len <<= 1) {
        double ang = 2 * M_PI / len * (inv ? 1 : -1);
        std::complex<float> wl((float)std::cos(ang), (float)std::sin(ang));
        for (size_t i = 0; i < n; i += len) {
            std::complex<float> w(1);
            for (size_t j = 0; j < len / 2; j++) {
                auto u = a[i + j], v = a[i + j + len / 2] * w;
                a[i + j] = u + v; a[i + j + len / 2] = u - v;
                w *= wl;
            }
        }
    }
    if (inv) for (auto &x : a) x /= (float)n;
}

// ---------- 잔향 ----------
void Convolver::make(double sec, unsigned seed) {
    Rng rng(seed + 12345);
    const int n = (int)(sec * SR), pre = std::max(0, (int)(.02 * SR) - B);   // 블록 지연(B)만큼 앞 지연을 줄임
    std::vector<float> ir[2];
    for (int ch = 0; ch < 2; ch++) {
        std::vector<float> x(n), lo(n);
        for (int i = 0; i < n; i++) x[i] = (float)(rng.gauss(0, 1) * std::exp(-6.9 * i / SR / sec));
        Biquad b; b.design(false, 2500);
        for (int i = 0; i < n; i++) lo[i] = b.run(x[i]);
        double e = 0;
        ir[ch].assign(pre, 0.f);
        for (int i = 0; i < n; i++) {
            double w = std::min(1.0, std::max(0.0, (double)i / SR / sec * 1.5));
            float v = (float)(x[i] * (1 - w) + lo[i] * w);
            ir[ch].push_back(v);
        }
        for (float v : ir[ch]) e += (double)v * v;
        float k = (float)(1.0 / std::sqrt(e + 1e-20));
        for (float &v : ir[ch]) v *= k;
    }
    const int len = (int)ir[0].size();
    P = (len + B - 1) / B;
    for (int ch = 0; ch < 2; ch++) {
        H[ch].assign(P, std::vector<std::complex<float>>(N));
        X[ch].assign(P, std::vector<std::complex<float>>(N));
        for (int p = 0; p < P; p++) {
            auto &h = H[ch][p];
            for (int i = 0; i < B && p * B + i < len; i++) h[i] = ir[ch][p * B + i];
            fft(h, false);
        }
        in[ch].assign(N, 0.f);
        out[ch].assign(B, 0.f);
    }
    head = 0;
}

void Convolver::process(const float *inL, const float *inR, float *outL, float *outR) {
    const float *ins[2] = {inL, inR};
    float *outs[2] = {outL, outR};
    head = (head + P - 1) % P;                     // 가장 새 칸
    for (int ch = 0; ch < 2; ch++) {
        auto &buf = in[ch];
        std::copy(buf.begin() + B, buf.end(), buf.begin());           // 겹쳐 보존(overlap-save): [앞 블록 | 새 블록]
        std::copy(ins[ch], ins[ch] + B, buf.begin() + B);
        auto &x = X[ch][head];
        for (int i = 0; i < N; i++) x[i] = buf[i];
        fft(x, false);
        std::vector<std::complex<float>> acc(N);
        for (int p = 0; p < P; p++) {
            const auto &xs = X[ch][(head + p) % P];
            const auto &h = H[ch][p];
            for (int k = 0; k < N; k++) acc[k] += xs[k] * h[k];
        }
        fft(acc, true);
        for (int i = 0; i < B; i++) outs[ch][i] = acc[B + i].real();
    }
}

// ---------- 압축 ----------
void Compressor::process(float *L, float *R, int n) {
    const double a = std::exp(-1 / (att * SR)), r = std::exp(-1 / (rel * SR)), k = 1 - 1 / ratio;
    for (int j = 0; j < n; j++, i++) {
        const int w = (int)(i % RING);
        float m = (L[j] * L[j] + R[j] * R[j]) * .5f;
        sum += m - ms[(i - W + RING * 4) % RING] * (i >= W);
        ms[w] = m; xl[w] = L[j]; xr[w] = R[j];
        // 창 [i-W+1, i] 의 가운데 = i - D (늦춘 소리에 이득을 줌)
        double env = std::sqrt(std::max(0.0, sum) / W) + 1e-9;
        double gr = std::min(0.0, (thr - 20 * std::log10(env)) * k);
        sm_r = (1 - r) * gr + r * sm_r;
        sm_a = (1 - a) * gr + a * sm_a;
        double g = std::pow(10.0, std::min(sm_r, sm_a) / 20);
        const int d = (int)((i - D + RING * 4) % RING);
        const bool ok = i >= D;
        L[j] = ok ? (float)(xl[d] * g) : 0.f;
        R[j] = ok ? (float)(xr[d] * g) : 0.f;
    }
}

// ---------- 리미터 ----------
void Limiter::process(float *L, float *R, int n) {
    for (int j = 0; j < n; j++, i++) {
        const int w = (int)(i % RING);
        float av = std::max(std::fabs(L[j]), std::fabs(R[j]));
        a[w] = av; xl[w] = L[j]; xr[w] = R[j];
        // 미끄럼 최대: 창 [i-2·LOOK, i] → pk[i-LOOK]
        while (dq.size() > dq_head && dq.back().second <= av) dq.pop_back();
        dq.push_back({i, av});
        while (dq[dq_head].first < i - 2 * LOOK) dq_head++;
        if (dq_head > 4096) { dq.erase(dq.begin(), dq.begin() + dq_head); dq_head = 0; }
        const long k = i - LOOK;
        float g_new = 1.f;
        if (k >= 0) g_new = (float)std::min(1.0, c / (dq[dq_head].second + 1e-9));
        // gm[k] 평균 창 [k-LOOK+1, k] → 가운데 k - LOOK/2 ≈ 출력 i - D
        const int kw = (int)((k + RING * 4) % RING);
        const float old = gm[(kw - LOOK + RING) % RING];
        gm[kw] = g_new;
        gsum += g_new - old;
        const long o = i - D;
        if (o < 0) { L[j] = R[j] = 0.f; continue; }
        const int ow = (int)(o % RING);
        double g = std::min(gsum / LOOK, c / (a[ow] + 1e-9));
        L[j] = (float)(xl[ow] * g); R[j] = (float)(xr[ow] * g);
    }
}

double active_db(const std::vector<float> &x) {
    const int n = (int)(.05 * SR);
    std::vector<double> w;
    for (size_t s = 0; s + n <= x.size(); s += n) {
        double e = 0;
        for (int k = 0; k < n; k++) e += (double)x[s + k] * x[s + k];
        w.push_back(e / n);
    }
    if (w.empty()) return -120;
    double mx = -1e9;
    for (double v : w) mx = std::max(mx, 10 * std::log10(v + 1e-12));
    double sum = 0; int c = 0;
    for (double v : w) if (10 * std::log10(v + 1e-12) > mx - 40) { sum += v; c++; }
    return 10 * std::log10(sum / std::max(1, c) + 1e-12);
}
