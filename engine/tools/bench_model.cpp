// AI 계산 속도 · 값 확인: 한 낱말씩 이어 넣으며 초당 낱말 수를 재고, 몇 걸음의 점수(logits)를 파일로 (옛 계산과 견줌)
//   bench_model <모델.bin> [낱말수=600] [점수파일]
#include "../src/model.h"
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <ctime>
static double cpu_s() { timespec t; clock_gettime(CLOCK_THREAD_CPUTIME_ID, &t); return t.tv_sec + t.tv_nsec * 1e-9; }
int main(int argc, char **argv) {
    Model m; std::string err;
    if (!m.load(argv[1], &err)) { std::printf("%s\n", err.c_str()); return 1; }
    const int N = std::min(argc > 2 ? std::atoi(argv[2]) : 600, m.ctx - 4);
    Runner r(&m);
    unsigned s = 12345;
    FILE *fo = argc > 3 ? std::fopen(argv[3], "wb") : nullptr;
    auto t0 = std::chrono::steady_clock::now();
    const double c0 = cpu_s();
    double sum = 0;
    for (int i = 0; i < N; i++) {
        s = s * 1664525u + 1013904223u;
        r.feed1(i == 0 ? 1 : 4 + (int)((s >> 8) % (unsigned)(m.vocab - 4)));
        sum += r.logits[i % m.vocab];
        if (fo && i % 50 == 49) std::fwrite(r.logits.data(), 4, m.vocab, fo);
    }
    const double dt = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
    const double ct = cpu_s() - c0;
    std::printf("%s: d%d L%d ctx%d · %d 낱말 · 벽시계 %.3f초 · CPU %.3f초 → 낱말당 %.3fms (초당 %.0f) · 합 %.4f\n", argv[1], m.d, m.layers, m.ctx, N, dt, ct, 1000 * ct / N, N / ct, sum);
    if (fo) std::fclose(fo);
}
