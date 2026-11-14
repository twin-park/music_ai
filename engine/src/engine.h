// 실시간 엔진: 작곡(단락씩 미리) → 연주 사건(음정 보정·지연·관악기 표현) → 악기별 소리(fluidsynth·피아노) → 믹서
//   작곡은 작곡 줄(스레드)이, 소리는 소리 줄이 만듦. 분위기를 바꾸면 소리 줄보다 조금 앞 마디에서 자르고 이음 2마디 → 새 분위기.
#pragma once
#include "amb.h"
#include "compose.h"
#include "conductor.h"
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
    std::string calib_name = "calib.txt";                                     // 보정표 파일 (안드로이드 TinySoundFont 판은 calib_tsf.txt — 소리 크기가 fluidsynth 와 다름)
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
    // 지휘자 (상황 → 음악): 알아서(auto) 면 분위기 · 조절값 · 악기를 지휘자가 정함. 섞기(말소리 · 길 안내 · 통화)는 직접 고를 때도 늘 함
    Conductor cond;
    std::mutex cond_mtx;               // cond · dec 를 지킴 (화면 줄 · 작곡 줄)
    Decision dec;
    std::atomic<bool> auto_mode{false}, auto_start{false};
    std::atomic<bool> change_now{false};   // "다른 거" — 다음 걸음에서 바로 (머무는 시간 · 사람이 고른 15분도 넘김)
    double cond_last = -1, mood_since = -1e9, pend_since = 0, params_at = -1e9, user_pick_until = -1e9, keep_until = -1e9;
    std::string pend_mood;
    bool cond_ended = false;
    double start_at = -1;
    Steer steer_cur;                   // 지금 지시 (mtx)
    void set_steer(const Steer &s);
    Steer get_steer() { std::lock_guard<std::mutex> g(mtx); return steer_cur; }
    void cond_tick(double now);
    std::string cur_mood_id();
    void user_mood(const std::string &id);          // 알아서 하는 중에 사람이 직접 고름 → 15분은 그 분위기 (반응 기록)
    std::string hear(const std::string &text, std::string *intent);   // 말 → 요청 (지휘자) + 그에 따른 일
    void situation(const Json &patch);              // 상황 일부
    // 섞기 (소리 줄): 전체 크기 · 말소리만큼 줄이기 · 말 대역 파내기 · 말과 겹치는 악기 줄이기
    std::atomic<float> mix_db{0}, talk_level{0}, talk_duck_db{0}, talk_cut_db{0}, overlap_db{0};
    std::atomic<float> out_db{-90};    // 지금 나가는 소리 크기 (화면 · 마이크 메아리 빼기용)
    float mix_now = 1, talk_env = 0, talk_hold = 0;
    double peq_db = 0, peq_b[3] = {1, 0, 0}, peq_a[2] = {0, 0}, peq_z[2][2] = {{0, 0}, {0, 0}};
    std::vector<float> trk_talk;       // insts() 번호마다 말소리 겹침 (지휘자 악기 성격표)
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
    // 사람이 얹는 조절량 (안드로이드 노브 4분면) — '알아서' 일 때 지휘자가 고른 조절값 위에 더함 (데스크톱은 늘 0)
    Params knob;
    Params with_knob(const Params &p) const {
        auto c = [](double v) { return std::max(-1.0, std::min(1.0, v)); };
        if (!knob.reg && !knob.tempo && !knob.dens && !knob.energy && !knob.novelty && !knob.space && !knob.tension) return p;   // 노브 안 씀 = 예전 그대로
        Params r = p;
        r.reg = c(p.reg + knob.reg); r.tempo = c(p.tempo + knob.tempo); r.dens = c(p.dens + knob.dens);
        r.energy = c(p.energy + knob.energy); r.novelty = c(p.novelty + knob.novelty); r.space = c(p.space + knob.space); r.tension = c(p.tension + knob.tension);
        return r;
    }
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
    // 음 시작 알림 — render 가 음을 낼 때마다 넣음 (소리 줄 하나가 쓰고 다른 줄 하나가 읽음 · 가득 차면 버림)
    //   안드로이드 앱(music_android)의 박자 신호 · 피아노 화면이 씀. frame = 소리 줄이 만든 샘플 위치, s = 세기(킥이 가장 큼)
    struct Onset { long frame = 0; int key = -1, vel = 0, track = -1; float s = 0.f; };
    static constexpr size_t kOnsetCap = 1024;
    Onset onset_q[kOnsetCap];
    std::atomic<size_t> onset_w{0}, onset_r{0};
    void push_onset(long frame, int key, int vel, int track, bool drum);
    bool pop_onset(long played, Onset *o);          // 재생 위치(played)에 닿은 것 하나를 꺼냄 (없으면 false)
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
