// 난수 — 어느 컴퓨터에서나 같은 씨앗이면 같은 결과 (std 분포는 구현마다 달라서 직접 만듦)
#pragma once
#include <cstdint>
#include <cmath>
#include <vector>

struct Rng {
    uint64_t s[4];
    bool has_g = false;
    double g2 = 0;
    explicit Rng(uint64_t seed = 1) { reseed(seed); }
    void reseed(uint64_t seed) {
        uint64_t z = seed + 0x9E3779B97F4A7C15ull;
        for (auto &x : s) {
            z += 0x9E3779B97F4A7C15ull;
            uint64_t y = z;
            y = (y ^ (y >> 30)) * 0xBF58476D1CE4E5B9ull;
            y = (y ^ (y >> 27)) * 0x94D049BB133111EBull;
            x = y ^ (y >> 31);
        }
        has_g = false;
    }
    static uint64_t rotl(uint64_t x, int k) { return (x << k) | (x >> (64 - k)); }
    uint64_t next() {
        uint64_t r = rotl(s[1] * 5, 7) * 9, t = s[1] << 17;
        s[2] ^= s[0]; s[3] ^= s[1]; s[1] ^= s[2]; s[0] ^= s[3]; s[2] ^= t; s[3] = rotl(s[3], 45);
        return r;
    }
    double random() { return (next() >> 11) * (1.0 / 9007199254740992.0); }          // [0,1)
    int randint(int a, int b) { return a + (int)(random() * (b - a + 1)); }            // a~b (끝 포함)
    double uniform(double a, double b) { return a + (b - a) * random(); }
    double gauss(double mu, double sd) {
        if (has_g) { has_g = false; return mu + sd * g2; }
        double u1 = random(), u2 = random();
        if (u1 < 1e-300) u1 = 1e-300;
        double r = std::sqrt(-2 * std::log(u1)), a = 6.283185307179586 * u2;
        g2 = r * std::sin(a); has_g = true;
        return mu + sd * r * std::cos(a);
    }
    size_t index(size_t n) { return (size_t)(random() * n); }
    template <class T> const T &choice(const std::vector<T> &v) { return v[index(v.size())]; }
    // 가중치로 하나 고르기 → 번호
    int weighted(const std::vector<double> &w) {
        double tot = 0;
        for (double x : w) tot += x;
        double r = random() * tot;
        for (size_t i = 0; i < w.size(); i++) { r -= w[i]; if (r < 0) return (int)i; }
        return (int)w.size() - 1;
    }
};
