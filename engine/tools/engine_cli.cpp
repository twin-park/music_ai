// 시험·보정 도구 (소리 장치 없이 파일로)
//   engine_cli render <data> <출력.wav> <초> "0:비오는날,70:즐거운대화,100:@reg=0.5/tempo=-0.3,120:~sea=1/rain=0,140:끝"
//      — 실시간 엔진을 그대로 빨리 돌려 녹음 (@ = 조절값 · ~ = 주변 소리)
//   engine_cli scenario <data> <출력.wav> <시나리오.json> [기록.txt]  — 주행 시나리오(시간마다 상황 · 말 · 말소리)를 지휘자가 알아서 연주
//      {"seconds":300, "steps":[{"t":0,"set":{상황}}, {"t":40,"say":"이제 애기 재우자"}, {"t":60,"talk":0.8}, {"t":70,"talk":0}]}
//   engine_cli calib <data> [초]                                                    — 분위기마다 악기 크기 · 마스터 크기 재서 data/calib.txt
#include "../src/engine.h"
#include "../src/util.h"
#include "../src/json.h"
#include <algorithm>
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
                else if (a[0] == '~') {                                          // ~sea=1/rain=0 (주변 소리)
                    std::stringstream ps(a.substr(1)); std::string kv;
                    while (std::getline(ps, kv, '/')) {
                        auto e = kv.find('='); if (e == std::string::npos) continue;
                        for (int k = 0; k < Ambience::N; k++) if (kv.substr(0, e) == Ambience::NAME[k]) E.amb.set(k, (float)std::atof(kv.substr(e + 1).c_str()));
                    }
                }
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
    if (cmd == "scenario") {
        Engine E; std::string err;
        if (!E.init(data, &err)) { std::printf("%s\n", err.c_str()); return 1; }
        if (!E.cond.loaded) { std::printf("지휘자 없음: %s\n", E.cond.err.c_str()); return 1; }
        if (const char *od = std::getenv("CAR_BGM_OUT")) E.out_dir = od;
        std::string txt, pe;
        if (!read_file(argv[4], txt)) { std::printf("시나리오 파일 없음\n"); return 1; }
        Json sc = Json::parse(txt, &pe);
        if (!pe.empty()) { std::printf("시나리오 JSON: %s\n", pe.c_str()); return 1; }
        const double total = sc["seconds"].num(300);
        std::vector<const Json *> steps;
        for (auto &s : sc["steps"].a) steps.push_back(&s);
        std::stable_sort(steps.begin(), steps.end(), [](const Json *a, const Json *b) { return (*a)["t"].num() < (*b)["t"].num(); });
        E.auto_mode = true; E.auto_start = true;
        std::vector<float> L, R, bl(4096), br(4096);
        size_t si = 0;
        std::string log, last_line, last_mood, last_rules;
        auto stamp = [](double t) { char b[16]; std::snprintf(b, sizeof b, "%d:%02d", (int)t / 60, (int)t % 60); return std::string(b); };
        while ((double)L.size() / SR < total) {
            const double now = (double)E.frame.load() / SR;
            while (si < steps.size() && (*steps[si])["t"].num() <= now) {
                const Json &st = *steps[si++];
                if (st["set"].is_obj()) { E.situation(st["set"]); log += stamp(now) + "  상황 " + st["set"].dump() + "\n"; }
                if (st["say"].is_str()) { std::string it; const std::string rep = E.hear(st["say"].s, &it); log += stamp(now) + "  말 \"" + st["say"].s + "\" → " + it + " (" + rep + ")\n"; }
                if (st["talk"].is_num()) { Json p = Json::obj_(), c = Json::obj_(); c.set("talk", st["talk"]); p.set("cabin", c); E.situation(p); log += stamp(now) + "  말소리 크기 " + st["talk"].dump() + "\n"; }
                if (st["end"].truthy()) { E.request_end(); log += stamp(now) + "  끝내기\n"; }
            }
            while (E.compose_step(now)) {}
            {
                std::lock_guard<std::mutex> g(E.cond_mtx);
                const std::string cm = E.cur_mood_id();
                std::string rl;
                for (auto &x : E.dec.rules) rl += x + " ";
                if (E.dec.line != last_line || cm != last_mood || rl != last_rules) {
                    char b[160];
                    std::snprintf(b, sizeof b, "  [에너지 %d · 밝기 %d · 섞기 %.0fdB · 말 %.0fdB · 파도 %.1f · 비 %.1f]", (int)E.dec.energy, (int)E.dec.bright,
                                  E.dec.volume_db + E.dec.duck_db, E.dec.talk_cut_db, E.dec.amb_sea, E.dec.amb_rain);
                    log += stamp(now) + "  ▶ " + E.dec.line + "  (연주 중: " + (cm.empty() ? "-" : cm) + ")" + b + "\n";
                    std::string because;
                    for (auto &x : E.dec.because) because += (because.empty() ? "" : " · ") + x;
                    std::string av;
                    for (auto &x : E.dec.steer.avoid) av += x + " ";
                    std::string top;
                    std::vector<std::pair<std::string, double>> iv(E.dec.steer.instr.begin(), E.dec.steer.instr.end());
                    std::sort(iv.begin(), iv.end(), [](auto &a, auto &b) { return a.second > b.second; });
                    for (size_t k = 0; k < iv.size() && k < 4; k++) if (iv[k].second > 0) top += iv[k].first + " ";
                    log += "        왜: " + because + "\n        악기 ↑ " + top + (av.empty() ? "" : "· 빼기 " + av) +
                           (E.dec.steer.thin ? "· 비우기 " : "") + (E.dec.steer.lead_rest ? "· 선율 쉼 " : "") +
                           (E.dec.steer.tempo_max > 0 ? "· 빠르기 ≤" + std::to_string((int)E.dec.steer.tempo_max) + " " : "") + (E.dec.end ? "· 끝맺음 " : "") + "\n";
                    last_line = E.dec.line; last_mood = cm; last_rules = rl;
                }
            }
            E.render(bl.data(), br.data(), 4096);
            L.insert(L.end(), bl.begin(), bl.end()); R.insert(R.end(), br.begin(), br.end());
        }
        write_wav(argv[3], L, R);
        if (argc > 5) write_file(argv[5], log);
        std::printf("%s", log.c_str());
        std::printf("→ %s %.0f초\n", argv[3], total);
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
