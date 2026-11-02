// 되풀이 재기: 한 분위기를 40 단락 이어 쓰고, 단락끼리 얼마나 닮았나를 간격(1~8 단락)별로
//   선율 = 음정·길이 3-그램 집합, 화음 = 코드 2-그램 집합, 편성 = (악기 · 드럼 세기층) 집합 — Jaccard
//   evolve_stats <data> <분위기> [단락수] [씨앗] [선율덤프.txt]  (덤프: 단락 마디 틱 길이틱 음 — tools/mel_metrics.py 로 실제 곡과 비교)
#include "../src/compose.h"
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <set>
#include <tuple>
int main(int argc, char **argv) {
    static Models M; std::string err, d = argv[1];
    if (!M.chord.load(d + "/chord.bin", &err) || !M.melody.load(d + "/melody.bin", &err)) { std::printf("%s\n", err.c_str()); return 1; }
    const Mood *m = mood_by_id(argv[2]);
    int N = argc > 3 ? std::atoi(argv[3]) : 40;
    Session ss(*m, M, argc > 4 ? std::strtoull(argv[4], nullptr, 10) : 11, true);
    FILE *dump = argc > 5 ? std::fopen(argv[5], "w") : nullptr;
    ss.next();                                                     // 도입
    std::vector<std::set<long>> mel, chd, arr;
    std::vector<std::string> roles;
    for (int k = 0; k < N; k++) {
        Section s = ss.next();
        roles.push_back(ROLE_NAME[s.role]);
        std::vector<Note *> ms;
        for (Note *n : ss.S.mel) if (n->sec == s.sec && !n->dead) ms.push_back(n);
        std::sort(ms.begin(), ms.end(), [](Note *a, Note *b) { return a->t < b->t; });
        if (dump) for (const BN &n : ss.last_mel) {                   // 작곡한 선율 그대로 (둘째 목소리 · 겹치기 빼고)
            const double rb = n.t - (double)s.a * ss.S.ts;
            const int bar = (int)std::floor(rb / ss.S.ts + 1e-6);
            std::fprintf(dump, "%d %d %d %d %d\n", k, bar, (int)std::lround((rb - bar * ss.S.ts) * 12), std::max(1, (int)std::lround(n.d * 12)), n.p);
        }
        std::set<long> g;
        for (size_t i = 0; i + 3 < ms.size(); i++) {
            long h = 0;
            for (int j = 0; j < 3; j++) h = h * 97 + (ms[i + j + 1]->p - ms[i + j]->p + 40) * 7 + std::min(6, (int)std::lround(ms[i + j]->d * 2));
            g.insert(h);
        }
        mel.push_back(g);
        std::set<long> c;
        std::vector<const Span *> sp;
        for (auto &x : ss.S.spans) if (x.a >= (double)s.a * ss.S.ts - 1e-6 && x.a < (double)s.b * ss.S.ts - 1e-6) sp.push_back(&x);
        for (size_t i = 0; i + 1 < sp.size(); i++) c.insert(((long)sp[i]->c.root * 30 + sp[i]->c.q) * 1000 + sp[i + 1]->c.root * 30 + sp[i + 1]->c.q);
        chd.push_back(c);
        std::set<long> a;
        for (auto &n : ss.S.pool) if (n.sec == s.sec && !n.dead) a.insert((long)n.part * 1000 + (ss.S.is_drum_part(n.part) ? n.p * 4 + n.v / 32 : 0));
        arr.push_back(a);
    }
    auto jac = [](const std::set<long> &x, const std::set<long> &y) {
        if (x.empty() && y.empty()) return 1.0;
        int in = 0; for (long v : x) in += y.count(v);
        return (double)in / (x.size() + y.size() - in);
    };
    std::printf("%s 단락 순서:", m->id.c_str());
    for (size_t i = 0; i < roles.size() && i < 24; i++) std::printf(" %s", roles[i].c_str());
    std::printf("\n간격    선율   화음   편성\n");
    for (int lag = 1; lag <= 8; lag++) {
        double a = 0, b = 0, c = 0; int n = 0;
        for (int i = 0; i + lag < N; i++) { a += jac(mel[i], mel[i + lag]); b += jac(chd[i], chd[i + lag]); c += jac(arr[i], arr[i + lag]); n++; }
        std::printf("  %d   %.3f  %.3f  %.3f\n", lag, a / n, b / n, c / n);
    }
    if (dump) std::fclose(dump);
}
