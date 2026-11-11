// 시험·보정 도구 (소리 장치 없이 파일로)
//   engine_cli render <data> <출력.wav> <초> "0:비오는날,70:즐거운대화,100:@reg=0.5/tempo=-0.3,140:끝"  — 실시간 엔진을 그대로 빨리 돌려 녹음 (@ = 조절값)
//   engine_cli calib <data> [초]                                                    — 분위기마다 악기 크기 · 마스터 크기 재서 data/calib.txt
#include "../src/engine.h"
#include "../src/util.h"
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <sstream>

static void write_wav(const std::string &path, const std::vector<float> &L, const std::vector<float> &R) {
    std::string d;
    auto u32 = [&](uint32_t v) { d.append((char *)&v, 4); };
    auto u16 = [&](uint16_t v) { d.append((char *)&v, 2); };
    uint32_t n = (uint32_t)L.size();
    d += "RIFF"; u32(36 + n * 4); d += "WAVEfmt "; u32(16); u16(1); u16(2); u32(SR); u32(SR * 4); u16(4); u16(16); d += "data"; u32(n * 4);
    for (uint32_t i = 0; i < n; i++)
        for (float x : {L[i], R[i]}) { int16_t s = (int16_t)std::lround(std::max(-1.f, std::min(1.f, x)) * 32767); d.append((char *)&s, 2); }
    write_file(path, d);
}

int main(int argc, char **argv) {
    std::string cmd = argc > 1 ? argv[1] : "", data = argc > 2 ? argv[2] : "data";
    if (cmd == "render") {
        Engine E; std::string err;
        if (!E.init(data, &err)) { std::printf("%s\n", err.c_str()); return 1; }
        if (const char *od = std::getenv("CAR_BGM_OUT")) E.out_dir = od;      // 악보 글자도 남기기
        double total = std::atof(argv[4]);
        std::vector<std::pair<double, std::string>> plan;
        std::stringstream ss(argv[5]); std::string it;
        while (std::getline(ss, it, ',')) { auto c = it.find(':'); plan.push_back({std::atof(it.substr(0, c).c_str()), it.substr(c + 1)}); }
        std::vector<float> L, R, bl(4096), br(4096);
        size_t pi = 0;
        double t_comp = 0, t_rend = 0;
        while ((double)L.size() / SR < total) {
            double now = (double)E.frame.load() / SR;
            while (pi < plan.size() && plan[pi].first <= now) {
                const std::string &a = plan[pi].second;
                if (a == "끝") E.request_end();
                else if (a[0] == '@') {                                          // @reg=0.5/tempo=-0.3 … (조절값)
                    Params p = E.get_params();
                    std::stringstream ps(a.substr(1)); std::string kv;
                    while (std::getline(ps, kv, '/')) {
                        auto e = kv.find('='); if (e == std::string::npos) continue;
                        const std::string k = kv.substr(0, e); const double v = std::atof(kv.substr(e + 1).c_str());
                        if (k == "reg") p.reg = v; else if (k == "tempo") p.tempo = v; else if (k == "dens") p.dens = v;
                        else if (k == "energy") p.energy = v; else if (k == "novelty") p.novelty = v; else if (k == "space") p.space = v; else if (k == "tension") p.tension = v;
                    }
                    E.set_params(p);
                } else E.request_mood(a);
                pi++;
            }
            auto a = std::chrono::steady_clock::now();
            while (E.compose_step(now)) {}
            auto b = std::chrono::steady_clock::now();
            E.render(bl.data(), br.data(), 4096);
            auto c = std::chrono::steady_clock::now();
            t_comp += std::chrono::duration<double>(b - a).count(); t_rend += std::chrono::duration<double>(c - b).count();
            L.insert(L.end(), bl.begin(), bl.end()); R.insert(R.end(), br.begin(), br.end());
        }
        write_wav(argv[3], L, R);
        double pk = 0, ss2 = 0;
        for (size_t i = 0; i < L.size(); i++) { pk = std::max(pk, (double)std::max(std::fabs(L[i]), std::fabs(R[i]))); ss2 += L[i] * L[i] + R[i] * R[i]; }
        std::printf("→ %s %.0f초 · 작곡 %.1f초 · 소리 %.1f초 (실시간의 %.1f배 빠름) · 최고 %.2f · 평균 %.1fdB\n", argv[3], total, t_comp, t_rend,
                    total / (t_comp + t_rend), pk, 10 * std::log10(ss2 / (2 * L.size()) + 1e-12));
        std::printf("%s", E.recent_score(1).substr(0, 300).c_str());
        return 0;
    }
    if (cmd == "calib") {
        double secs = argc > 3 ? std::atof(argv[3]) : 75;
        std::string only = argc > 4 ? argv[4] : "";
        std::string out = "# 분위기 악기 연주중크기dB (_master = 압축 뒤 -17dB 로 맞출 이득) — engine_cli calib 이 만듦\n";
        for (auto &m : moods()) {
            if (!only.empty() && m.id != only) continue;
            std::map<std::string, double> act;
            for (int pass = 0; pass < 2; pass++) {
                Engine E; std::string err;
                if (!E.init(data, &err)) { std::printf("%s\n", err.c_str()); return 1; }
                E.seed = 5;
                if (pass == 1) { E.calib[m.id].act = act; E.measure_master = true; }
                E.request_mood(m.id);
                std::vector<float> bl(4096), br(4096);
                for (int i = 0; (double)E.frame.load() / SR < secs; i++) {
                    double now = (double)E.frame.load() / SR;
                    while (E.compose_step(now)) {}
                    if (pass == 0) for (auto &t : E.tracks) if (t) t->measure = true;
                    E.render(bl.data(), br.data(), 4096);
                }
                if (pass == 0) {
                    for (auto &t : E.tracks) if (t && !t->meas.empty()) {
                        double a = active_db(t->meas);
                        std::printf("  [%s 사건 %zu 크기 %.1f]", t->def->kw, t->qh, a);
                        if (a > -90) act[t->def->kw] = a;                // 소리가 안 났으면 기본값
                    }
                } else {
                    double rms = 10 * std::log10(E.mm_sum / std::max(1L, E.mm_n) + 1e-12);
                    out += m.id + " _master " + fmt2(-17 - rms) + "\n";
                    std::printf("%s: 마스터 %+.1fdB ·", m.id.c_str(), -17 - rms);
                }
            }
            for (auto &[k, v] : act) { out += m.id + " " + k + " " + fmt2(v) + "\n"; std::printf(" %s %.1f", k.c_str(), v); }
            std::printf("\n");
        }
        if (only.empty()) write_file(data + "/calib.txt", out);
        return 0;
    }
    std::printf("engine_cli render|calib …\n");
    return 1;
}
