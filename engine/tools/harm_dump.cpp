// 화성 재기용 덤프: 한 분위기를 N 단락 쓰고 단락마다 코드 · 순수 선율 · 편곡된 모든 음을 글자로 (tools/harm_metrics.py 가 읽음)
//   harm_dump <data> <분위기> [단락수] [씨앗] [출력.txt] [조절값: tension=0.9/novelty=-0.5 …]
//   S 단락번호 종류 으뜸음 단조 시작마디 끝마디 박자 | C 시작박 끝박 근음 AI종류(-1=모름) 이름 구성음… / 텐션… | M 박 길이 음 | N 악기 박 길이 음 세기 선율(0/1)
#include "../src/compose.h"
#include <cstdio>
#include <set>
int main(int argc, char **argv) {
    static Models M; std::string err, d = argv[1];
    if (!M.chord.load(d + "/chord.bin", &err) || !M.melody.load(d + "/melody.bin", &err)) { std::printf("%s\n", err.c_str()); return 1; }
    const Mood *m = mood_by_id(argv[2]);
    if (!m) { std::printf("분위기 없음\n"); return 1; }
    const int N = argc > 3 ? std::atoi(argv[3]) : 16;
    Params P;                                                                     // [조절값] 예: tension=0.9/novelty=-0.5
    if (argc > 6) {
        std::string a = argv[6];
        for (size_t i = 0; i < a.size();) {
            size_t e = a.find('/', i); if (e == std::string::npos) e = a.size();
            const std::string kv = a.substr(i, e - i); const size_t q = kv.find('=');
            if (q != std::string::npos) {
                const std::string k = kv.substr(0, q); const double v = std::atof(kv.substr(q + 1).c_str());
                if (k == "reg") P.reg = v; else if (k == "tempo") P.tempo = v; else if (k == "dens") P.dens = v; else if (k == "energy") P.energy = v;
                else if (k == "novelty") P.novelty = v; else if (k == "tension") P.tension = v;
            }
            i = e + 1;
        }
    }
    Session ss(*m, M, argc > 4 ? std::strtoull(argv[4], nullptr, 10) : 11, true, 0, nullptr, -1, "", &P);
    FILE *fo = argc > 5 ? std::fopen(argv[5], "w") : stdout;
    for (int k = 0; k <= N; k++) {
        Section s = ss.next();
        const int ts = ss.S.ts;
        std::fprintf(fo, "S %d %s %d %d %d %d %d\n", k, ROLE_NAME[s.role], ss.S.key.pc, (int)ss.S.key.minor, s.a, s.b, ts);
        for (auto &sp : ss.S.spans) {
            if (!(sp.a >= (double)s.a * ts - 1e-6 && sp.a < (double)s.b * ts - 1e-6)) continue;
            int qa = -1;
            auto it = ss.bar_chords.find((int)(sp.a / ts + 1e-6));
            if (it != ss.bar_chords.end()) for (auto &c : it->second) if (c[0] <= sp.a - (double)it->first * ts + 1e-6) qa = c[2];
            const char *qn = qinfo(sp.c.q).name;
            std::fprintf(fo, "C %.3f %.3f %d %d %s", sp.a, sp.b, sp.c.root, qa, qn[0] ? qn : "maj");
            for (int x : sp.c.tones()) std::fprintf(fo, " %d", x);
            std::fprintf(fo, " /");
            for (int x : sp.c.tensions()) std::fprintf(fo, " %d", x);
            std::fprintf(fo, "\n");
        }
        for (const BN &n : ss.last_mel) std::fprintf(fo, "M %.3f %.3f %d\n", n.t, n.d, n.p);
        std::set<const Note *> mel(ss.S.mel.begin(), ss.S.mel.end());
        for (auto &n : ss.S.pool) {
            if (n.sec != s.sec || n.dead || ss.S.is_drum_part(n.part)) continue;
            std::string nm = ss.S.names[n.part];
            for (auto &ch : nm) if (ch == ' ') ch = '_';
            std::fprintf(fo, "N %s %.3f %.3f %d %d %d\n", nm.c_str(), n.t, n.d, n.p, n.v, (int)mel.count(&n));
        }
    }
    if (fo != stdout) std::fclose(fo);
}
