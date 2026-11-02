// 시험: numpy(npmodel) 점수와 C++ 점수 비교 + 속도.  test_model <모델.bin> <시험.bin>
#include "../src/model.h"
#include <cstdio>
#include <cmath>
#include <chrono>
#include <vector>
int main(int argc, char **argv) {
    Model m; std::string err;
    if (!m.load(argv[1], &err)) { std::printf("%s\n", err.c_str()); return 1; }
    FILE *f = std::fopen(argv[2], "rb");
    int n; std::fread(&n, 4, 1, f);
    Runner r(&m);
    double md = 0, kl = 0; int cnt = 0;
    for (int i = 0; i < n; i++) {
        int T; std::fread(&T, 4, 1, f);
        std::vector<int> ids(T); std::fread(ids.data(), 4, T, f);
        std::vector<float> ref(m.vocab); std::fread(ref.data(), 4, m.vocab, f);
        r.feed(ids);
        double mr = -1e30, mc = -1e30, zr = 0, zc = 0, k = 0;
        for (int v = 0; v < m.vocab; v++) { md = std::fmax(md, std::fabs(ref[v] - r.logits[v])); mr = std::fmax(mr, ref[v]); mc = std::fmax(mc, r.logits[v]); }
        for (int v = 0; v < m.vocab; v++) { zr += std::exp(ref[v] - mr); zc += std::exp(r.logits[v] - mc); }
        for (int v = 0; v < m.vocab; v++) { double p = std::exp(ref[v] - mr) / zr, q = std::exp(r.logits[v] - mc) / zc; if (p > 0) k += p * std::log(p / (q + 1e-30)); }
        kl += k; cnt++;
    }
    std::printf("%s: 최대차 %.2e · KL 평균 %.2e\n", argv[1], md, kl / cnt);
    Runner r2(&m); auto t0 = std::chrono::steady_clock::now();
    for (int i = 0; i < 400; i++) r2.feed1(4 + i % (m.vocab - 4));
    double ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - t0).count();
    std::printf("  한 낱말 %.3fms\n", ms / 400);
}
