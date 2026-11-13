// 실시간 엔진: 작곡(단락씩 미리) → 연주 사건(음정 보정·지연·관악기 표현) → 악기별 소리(fluidsynth·피아노) → 믹서
//   작곡은 작곡 줄(스레드)이, 소리는 소리 줄이 만듦. 분위기를 바꾸면 소리 줄보다 조금 앞 마디에서 자르고 이음 2마디 → 새 분위기.
#pragma once
#include "amb.h"
#include "compose.h"
#include "dsp.h"
#include "fluid.h"
#include "piano.h"
#include <atomic>
#include <map>
#include <memory>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

struct InstDef {
    const char *kw;
    int engine;                       // 0 피아노(녹음) · 1 사운드폰트
    const char *font; int bank, prog; bool drum;
    double db, pan, rv, hp;
};
const std::vector<InstDef> &insts();
int inst_of(const std::string &part);         // 악기 이름 → insts() 번호 (-1 모름)

enum EvType { EV_ON, EV_OFF, EV_CC, EV_BEND, EV_PROG, EV_BANK, EV_ALLOFF, EV_PIANO, EV_CAP };   // EV_CAP: 피아노 울리던 음을 t1 에 손 뗌
struct Ev { double t; int prio, type, ch, a, b; double t1; };

struct Track {
    const InstDef *def;
    Fluid::synth_t *syn = nullptr;
    Fluid::settings_t *set = nullptr;
    std::vector<Ev> q;                // 시각 순 (소리 줄이 앞에서부터 씀)
    size_t qh = 0;
    double gain_db = 0, gain_to = 0;  // 지금 · 목표 (천천히 따라감)
    bool gain_set = false;
    Biquad hp[2];
    // 연주 상태 (작곡 줄만 씀)
    double busy[16] = {0};
    std::vector<TNote> held;          // 한 줄 악기: 다음 음을 봐야 끝을 정함
    // 계측 (보정표 만들 때)
    bool measure = false;
    std::vector<float> meas;
    std::vector<float> bl, br;
};

struct Calib { std::map<std::string, double> act; double master_db = 0; };

struct Engine {
    std::string data, out_dir;
    Models M;
    Piano piano;
    std::map<std::string, std::map<int, std::pair<double, double>>> tune;     // 악기 → 음 → (센트, 지연초)
    std::map<std::string, Calib> calib;                                       // 분위기 → 보정
    std::string sf_gu, sf_sso;
    std::mutex mtx;                    // 사건 줄 · 악보 · 상태
    std::vector<std::unique_ptr<Track>> tracks;     // insts() 번호마다 (처음 쓸 때 만듦)

    // 시간
    std::atomic<long> frame{0};        // 소리 줄이 만든 샘플 수
    double play_latency = 0;           // 소리 장치 버퍼 (초) — 화면 표시에 씀

    // 작곡
    struct Sess { std::unique_ptr<Session> s; double t0; Sheet sheet; };
    std::unique_ptr<Sess> cur, prev;
    double composed_until = 0;         // 이 시각까지 사건이 들어 있음
    uint64_t seed = 1;
    std::atomic<int> req_mood{-1};
    std::atomic<bool> req_end{false}, ending{false}, stopped{false};
    double lookahead = 14;             // 초 — 이만큼 앞까지 미리 작곡

    // 믹서
    Convolver rev_a, rev_b;
    Convolver *rev = &rev_a, *rev_old = nullptr;
    double rev_x = 1, rev_sec = 0;     // 잔향 바꿀 때 섞기
    double rev_switch_t = -1, rev_next_sec = 0;
    Compressor comp;
    Limiter lim;
    double master_db = 0, master_to = 0;
    std::atomic<float> volume{1.f}, duck{1.f};
    Ambience amb;                      // 주변 소리 (바닷가 파도 · 빗소리) — 음악 밑에 작게
    float vol_now = 1, fade = 0;       // 시작 페이드 · 끝 페이드
    std::atomic<bool> fading_out{false};
    std::vector<float> sendL, sendR, dryL, dryR, wetL, wetR;
    bool master_set = false;
    bool measure_master = false;       // 보정표 만들 때: 압축 뒤 · 마스터 앞 크기
    double mm_sum = 0; long mm_n = 0;

    // 화면용
    struct Status { std::string mood, mood_name, role, key; int bar = 0; double bpm = 0; double t = 0; };
    Status st;
    struct Block { double t; std::string head; Sheet sh; std::string text; };
    std::vector<Block> score_log;                            // 단락마다 (시작 시각, 머리말, 악보, 글자)
    std::vector<std::pair<double, Status>> marks;            // 단락마다 상태 (재생 위치에 맞춰 보여 줌)
    std::string score_file, score_head;

    bool init(const std::string &data_dir, std::string *err);
    void request_mood(const std::string &id);
    void request_end() { req_end = true; }
    // 조절값 (화면 옆 막대): 울림은 바로, 나머지는 다음 2마디 덩어리부터 다시 작곡
    Params params;
    std::atomic<bool> req_params{false}, params_pending{false};
    std::atomic<float> space{0.f};
    void set_params(const Params &p);
    Params get_params() { std::lock_guard<std::mutex> g(mtx); return params; }
    void request_stop() { req_stop = true; }
    std::atomic<bool> req_stop{false};
    std::atomic<bool> live{false};     // 연주 중 (끄면 false)
    std::atomic<double> run_t0{0};     // 이번 연주를 시작한 엔진 시각 (화면 · 악보 시각은 여기부터)
    double end_time() { std::lock_guard<std::mutex> g(mtx); return composed_until; }
    bool playing() const { return cur != nullptr && !stopped; }
    // 작곡 한 걸음 (한 일이 있으면 true)
    bool compose_step(double now);
    // 소리 n 개 (n 은 512 배수)
    void render(float *L, float *R, int n);
    Status status_at(double t);
    std::string recent_score(int n_sections);

    // 연주
    void emit(Sess &ss, const Section &sec, bool flush_all);
    void perform_fluid(Track &tr, std::vector<TNote> notes, double cut, std::vector<Ev> &out, Rng &rng);
    Track &track(int i);
    void push_events(Track &tr, std::vector<Ev> &evs);
    void cut_at(double t, double ring = 0);       // ring > 0: 울리던 음은 ring 초까지 이어 울리고 끝 (분위기 · 조절값 바꿀 때)
    int phrase_cut(Session &os, double t0, double now, double *tc);   // 다음 2마디 덩어리 끝(4초 안) 또는 다음 마디
    void set_mood_mix(const Mood &m, double t);
    std::pair<double, double> tune_of(const std::string &kw, int p) const;
    std::vector<std::pair<double, double>> pending_gain;     // (시각, 목표 master) — 안 씀
    struct GainAt { double t; int track; double db; };
    std::vector<GainAt> gain_sched;
    std::vector<std::pair<double, double>> master_sched;

    ~Engine();
};
