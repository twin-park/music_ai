// 시험: 분위기 하나로 한 곡(도입 + A A' B A'' + 끝) 악보 글자 → 파일.   compose_song <data폴더> <분위기> <씨앗> <출력.txt> [바퀴수]
#include "../src/compose.h"
#include <chrono>
#include <cstdio>
#include <fstream>
int main(int argc, char **argv) {
    std::string dir = argv[1];
    static Models M; std::string err;
    if (!M.chord.load(dir + "/chord.bin", &err) || !M.melody.load(dir + "/melody.bin", &err)) { std::printf("%s\n", err.c_str()); return 1; }
    const Mood *m = mood_by_id(argv[2]);
    if (!m) { std::printf("모르는 분위기\n"); return 1; }
    int choruses = argc > 5 ? std::atoi(argv[5]) : 1;
    auto t0 = std::chrono::steady_clock::now();
    Session ss(*m, M, std::strtoull(argv[3], nullptr, 10), true);
    Sheet sh; sh.key = ss.S.key; sh.title = m->id + " (C++ AI 작곡 · 씨앗 " + argv[3] + ")";
    sh.info = {"템포 " + std::to_string((int)m->bpm), "박자 " + std::to_string(m->ts) + "/4", "잔향 " + fmt2(m->reverb)};
    std::vector<double> took;
    auto lap = std::chrono::steady_clock::now();
    auto add = [&](const Section &s) {
        section_to_sheet(ss, s, sh, 0);
        auto now = std::chrono::steady_clock::now();
        took.push_back(std::chrono::duration<double>(now - lap).count()); lap = now;
    };
    add(ss.next());
    for (int c = 0; c < choruses; c++) for (int k = 0; k < 4; k++) add(ss.next());
    add(ss.ending());
    double tot = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
    std::ofstream(argv[4]) << sh.text();
    std::printf("%s 씨앗 %s · 조 %s · 진행점수 %.1f · 단락마다", m->id.c_str(), argv[3], ss.S.key.name.c_str(), ss.prog_score);
    for (double x : took) std::printf(" %.2f", x);
    std::printf("초 · 합 %.2f초\n", tot);
}
