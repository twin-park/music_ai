// 차량 BGM AI — 실시간판 실행 파일
//   켜면: AI 모델 · 사운드폰트 · 피아노 읽기 → 소리 장치 열기 → 브라우저에 리모컨 화면
//   작곡 줄: 재생 위치보다 14초 앞까지 단락(8마디)씩 작곡 · 분위기 바꾸면 다음 마디에서 이음 2마디 → 새 분위기
//   소리 줄: 0.2초 앞까지 소리를 만들어 고리 버퍼에 · 소리 장치가 거기서 꺼내 감
//   브라우저 탭을 닫으면 30초 뒤 스스로 꺼짐
#include "engine.h"
#include "http.h"
#include "util.h"
#include "web_ui.h"
#include "../third_party/miniaudio.h"
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <thread>
#ifdef _WIN32
#include <windows.h>
#include <shellapi.h>
#endif

static void say(const std::string &msg) {
#ifdef _WIN32
    int n = MultiByteToWideChar(CP_UTF8, 0, msg.c_str(), -1, nullptr, 0);
    std::wstring w(n, 0);
    MultiByteToWideChar(CP_UTF8, 0, msg.c_str(), -1, &w[0], n);
    MessageBoxW(nullptr, w.c_str(), L"차량 BGM AI", MB_OK | MB_ICONERROR);
#else
    std::fprintf(stderr, "%s\n", msg.c_str());
#endif
}

static void open_url(const std::string &u) {
#ifdef _WIN32
    int n = MultiByteToWideChar(CP_UTF8, 0, u.c_str(), -1, nullptr, 0);
    std::wstring w(n, 0);
    MultiByteToWideChar(CP_UTF8, 0, u.c_str(), -1, &w[0], n);
    ShellExecuteW(nullptr, L"open", w.c_str(), nullptr, nullptr, SW_SHOWNORMAL);
#else
    std::printf("화면: %s\n", u.c_str());
    std::fflush(stdout);
#endif
}

// 고리 버퍼 (소리 줄 → 소리 장치, 한 쪽씩만 씀)
struct Ring {
    std::vector<float> b;
    size_t cap;
    std::atomic<size_t> w{0}, r{0};
    explicit Ring(size_t frames) : b(frames * 2), cap(frames) {}
    size_t fill() const { return w.load() - r.load(); }
};

static Engine E;
static Ring ring(48000);
static std::atomic<bool> running{true};
static std::atomic<long> underruns{0};
static std::atomic<double> last_ping{0};

static void on_audio(ma_device *, void *out, const void *, ma_uint32 n) {
    float *o = (float *)out;
    size_t have = ring.fill(), rd = ring.r.load();
    size_t k = std::min<size_t>(have, n);
    for (size_t i = 0; i < k; i++) {
        size_t j = (rd + i) % ring.cap;
        o[i * 2] = ring.b[j * 2]; o[i * 2 + 1] = ring.b[j * 2 + 1];
    }
    for (size_t i = k; i < n; i++) o[i * 2] = o[i * 2 + 1] = 0;
    if (k < n && E.live) underruns++;
    ring.r = rd + k;
}

static double now_s() {
    using namespace std::chrono;
    return duration<double>(steady_clock::now().time_since_epoch()).count();
}

int main(int argc, char **argv) {
    std::string data = exe_dir() + "/data";
    bool null_audio = false, no_browser = false;
    for (int i = 1; i < argc; i++) {
        std::string a = argv[i];
        if (a == "--data" && i + 1 < argc) data = argv[++i];
        else if (a == "--null-audio") null_audio = true;
        else if (a == "--no-browser") no_browser = true;
    }
    std::string err;
    if (!E.init(data, &err)) { say("시작하지 못했습니다\n" + err); return 2; }
    E.auto_mode = E.cond.loaded;                                             // 지휘자가 있으면 처음부터 알아서
    E.out_dir = home_dir() + "/차량BGM_결과";
    make_dirs(E.out_dir);
    const double target_fill = .2;
    E.play_latency = target_fill + .03;

    // 소리 줄
    std::thread render([&] {
        std::vector<float> L(1024), R(1024);
        while (running) {
            if (ring.cap - ring.fill() >= 1024 && ring.fill() < (size_t)(target_fill * SR)) {
                E.render(L.data(), R.data(), 1024);
                size_t w = ring.w.load();
                for (int i = 0; i < 1024; i++) { size_t j = (w + i) % ring.cap; ring.b[j * 2] = L[i]; ring.b[j * 2 + 1] = R[i]; }
                ring.w = w + 1024;
            } else std::this_thread::sleep_for(std::chrono::milliseconds(3));
        }
    });
    // 작곡 줄
    std::thread composer([&] {
        while (running)
            if (!E.compose_step((double)E.frame.load() / SR)) std::this_thread::sleep_for(std::chrono::milliseconds(20));
    });
    // 소리 장치
    ma_device dev;
    std::thread nullsink;
    if (!null_audio) {
        ma_device_config cfg = ma_device_config_init(ma_device_type_playback);
        cfg.playback.format = ma_format_f32;
        cfg.playback.channels = 2;
        cfg.sampleRate = SR;
        cfg.periodSizeInMilliseconds = 10;
        cfg.dataCallback = on_audio;
        if (ma_device_init(nullptr, &cfg, &dev) != MA_SUCCESS || ma_device_start(&dev) != MA_SUCCESS) {
            say("소리 장치를 열지 못했습니다 (스피커 · 이어폰 연결을 확인하세요)");
            return 3;
        }
    } else {                                                   // 시험용: 소리 장치 대신 실시간 속도로 버림
        nullsink = std::thread([] {
            std::vector<float> b(480 * 2);
            double t = now_s();
            while (running) {
                on_audio(nullptr, b.data(), nullptr, 480);
                t += .01;
                std::this_thread::sleep_for(std::chrono::duration<double>(std::max(0.0, t - now_s())));
            }
        });
    }

    HttpServer srv;
    if (!srv.listen_on(7700)) { say("화면용 포트를 열지 못했습니다"); return 4; }
    const std::string url = "http://127.0.0.1:" + std::to_string(srv.port) + "/";
    if (!no_browser) open_url(url); else { std::printf("화면: %s\n", url.c_str()); std::fflush(stdout); }
    last_ping = now_s();
    std::thread watch([] {                                     // 탭을 닫으면 30초 뒤 끝 (처음엔 2분 기다림)
        double t0 = now_s(); bool pinged = false;
        while (running) {
            std::this_thread::sleep_for(std::chrono::seconds(2));
            double lp = last_ping.load();
            if (lp > t0 + 1) pinged = true;
            if (now_s() - lp > (pinged ? 30 : 120)) { running = false; std::_Exit(0); }
        }
    });

    srv.serve([&](const HttpReq &q, HttpRes &r) {
        const double t = (double)E.frame.load() / SR - E.play_latency;
        if (q.path == "/" || q.path == "/index.html") { r.type = "text/html; charset=utf-8"; r.body = WEB_UI; return; }
        if (q.path == "/api/ping") { last_ping = now_s(); r.body = "{\"ok\":true}"; return; }
        if (q.path == "/api/moods") {
            std::string s = "[";
            for (auto &m : moods())
                s += (s.size() > 1 ? "," : "") + std::string("{\"id\":") + json_str(m.id) + ",\"name\":" + json_str(m.name) +
                     ",\"band\":" + json_str(m.band) + ",\"recipe\":" + json_str(m.recipe) + "}";
            r.body = s + "]"; return;
        }
        if (q.path == "/api/state") {
            auto st = E.status_at(t);
            const bool ending = E.ending && t < E.end_time() + 2.5;
            const bool playing = E.live && (!E.ending || ending);
            char b[160];
            std::snprintf(b, sizeof b, ",\"bpm\":%d,\"t\":%.1f,\"vol\":%.2f,\"duck\":%s,\"ending\":%s,\"playing\":%s,\"underruns\":%ld}",
                          (int)std::lround(st.bpm), std::max(0.0, t - E.run_t0.load()), E.volume.load(), E.duck.load() < .99 ? "true" : "false",
                          ending ? "true" : "false", playing ? "true" : "false", underruns.load());
            const Params pp = E.get_params();
            char pb[240];
            std::snprintf(pb, sizeof pb, ",\"params\":{\"reg\":%.2f,\"tempo\":%.2f,\"dens\":%.2f,\"energy\":%.2f,\"novelty\":%.2f,\"space\":%.2f,\"tension\":%.2f},\"pending\":%s}",
                          pp.reg, pp.tempo, pp.dens, pp.energy, pp.novelty, pp.space, pp.tension, E.params_pending ? "true" : "false");
            std::string tail = b;
            tail.pop_back();                                                   // 끝 } 떼고 조절값 붙임
            char ab[200];
            std::snprintf(ab, sizeof ab, ",\"amb\":{\"sea\":%.2f,\"rain\":%.2f},\"auto\":%s,\"talk\":%.2f,\"conductor\":%s}", E.amb.level[0].load(), E.amb.level[1].load(),
                          E.auto_mode ? "true" : "false", E.talk_level.load(), E.cond.loaded ? "true" : "false");
            std::string line;
            {
                std::lock_guard<std::mutex> g(E.cond_mtx);
                Json lj = Json::obj_();
                lj.set("line", Json::str_(E.dec.line)); lj.set("scene", Json::str_(E.dec.scene_name));
                Json bc = Json::arr_(); for (auto &b : E.dec.because) bc.a.push_back(Json::str_(b)); lj.set("because", bc);
                lj.set("next", Json::str_(E.dec.mood_name));
                line = lj.dump();
            }
            std::string abs = ab;
            abs.pop_back();
            abs += ",\"dec\":" + line + "}";
            std::string pbs = pb;
            pbs.pop_back();                                                    // 끝 } 떼고 주변 소리 붙임
            r.body = "{\"mood\":" + json_str(playing ? st.mood : "") + ",\"name\":" + json_str(st.mood_name) + ",\"role\":" + json_str(st.role) +
                     ",\"key\":" + json_str(st.key) + tail + pbs + abs;
            return;
        }
        if (q.path == "/api/score") { r.type = "text/plain; charset=utf-8"; r.body = E.recent_score(3); return; }
        if (q.path == "/api/params") {                                       // 조절값 (-1 … 1) — 빠진 값은 그대로
            Params p = E.get_params();
            auto get = [&](const char *k, double &v) { std::string x = json_get(q.body, k); if (!x.empty()) v = std::max(-1.0, std::min(1.0, std::atof(x.c_str()))); };
            get("reg", p.reg); get("tempo", p.tempo); get("dens", p.dens); get("energy", p.energy); get("novelty", p.novelty); get("space", p.space); get("tension", p.tension);
            E.set_params(p);
            r.body = "{\"ok\":true}";
            return;
        }
        if (q.path == "/api/amb") {                                           // 주변 소리: {"sea":1,"rain":0} (0 끔 · 1 기본 · 2 조금 크게) — 빠진 건 그대로
            std::string err;
            for (int k = 0; k < Ambience::N; k++) {
                const std::string x = json_get(q.body, Ambience::NAME[k]);
                if (!x.empty() && !E.amb.set(k, (float)std::atof(x.c_str()), &err)) { r.code = 500; r.body = "{\"error\":" + json_str(err) + "}"; return; }
            }
            r.body = "{\"ok\":true}";
            return;
        }
        if (q.path == "/api/mood") { E.user_mood(json_get(q.body, "id")); r.body = "{\"ok\":true}"; return; }
        // ── 지휘자: 상황 → 음악 ──
        if (q.path == "/api/situation") {                                    // POST = 상황 일부 (null 은 지움) · GET = 지금 상황 (지휘자가 채운 칸 포함)
            if (q.method == "POST") {
                std::string pe;
                Json patch = Json::parse(q.body, &pe);
                if (!pe.empty() || !patch.is_obj()) { r.code = 400; r.body = "{\"error\":" + json_str("상황 JSON 이 아님: " + pe) + "}"; return; }
                E.situation(patch);
                r.body = "{\"ok\":true}";
                return;
            }
            std::lock_guard<std::mutex> g(E.cond_mtx);
            r.body = E.cond.derived((double)E.frame.load() / SR).dump();
            return;
        }
        if (q.path == "/api/situation/reset") {                              // 상황 모두 지우기 (시연)
            const double now = (double)E.frame.load() / SR;
            std::lock_guard<std::mutex> g(E.cond_mtx);
            E.cond.sit = Json::obj_(); E.cond.clear_requests(); E.cond.reset_holds(); E.cond.update(Json::obj_(), now);
            r.body = "{\"ok\":true}";
            return;
        }
        if (q.path == "/api/say") {                                          // 말 (음성 인식 문장) → 요청
            std::string it;
            const std::string reply = E.hear(json_get(q.body, "text"), &it);
            r.body = "{\"intent\":" + json_str(it) + ",\"say\":" + json_str(reply) + "}";
            return;
        }
        if (q.path == "/api/auto") {                                         // {"on":1} 알아서 · {"on":0} 직접 · {"start":1} 지휘자가 고른 분위기로 시작
            const std::string on = json_get(q.body, "on"), st = json_get(q.body, "start");
            if (!on.empty()) {
                E.auto_mode = on == "1" || on == "true";
                if (E.auto_mode) { E.user_pick_until = -1e9; E.params_at = -1e9; }
                else E.set_steer(Steer());                                     // 직접: 지휘자의 악기 지시는 풀고 (조절값은 화면에 보이는 그대로)
            }
            if (st == "1" || st == "true") { E.auto_mode = true; E.auto_start = true; }
            r.body = std::string("{\"auto\":") + (E.auto_mode ? "true" : "false") + "}";
            return;
        }
        if (q.path == "/api/decision") {                                     // 지휘자가 지금 정한 것 (화면 · 시험)
            std::lock_guard<std::mutex> g(E.cond_mtx);
            r.body = E.dec.to_json().dump();
            return;
        }
        if (q.path == "/api/level") {                                        // 지금 나가는 소리 크기 (마이크 메아리 빼기용 · 자주 부름)
            char b[96];
            std::snprintf(b, sizeof b, "{\"out_db\":%.1f,\"talk\":%.2f}", E.out_db.load(), E.talk_level.load());
            r.body = b;
            return;
        }
        if (q.path == "/api/end") { E.request_end(); r.body = "{\"ok\":true}"; return; }
        if (q.path == "/api/stop") { E.request_stop(); r.body = "{\"ok\":true}"; return; }
        if (q.path == "/api/volume") { E.volume = (float)std::max(0.0, std::min(1.0, std::atof(json_get(q.body, "v").c_str()))); r.body = "{\"ok\":true}"; return; }
        if (q.path == "/api/duck") { E.duck = json_get(q.body, "on") == "1" ? .15f : 1.f; r.body = "{\"ok\":true}"; return; }
        if (q.path == "/api/open") {
#ifdef _WIN32
            open_url(E.out_dir);
#endif
            r.body = "{\"path\":" + json_str(E.out_dir) + "}"; return;
        }
        r.code = 404; r.body = "{}";
    });
    return 0;
}

#ifdef _WIN32
// 창 없는 프로그램 (콘솔 안 뜸) — 들어오는 곳만 WinMain
int WINAPI WinMain(HINSTANCE, HINSTANCE, LPSTR, int) { return main(__argc, __argv); }
#endif
