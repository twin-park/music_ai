// 작곡 (score/compose.py + styles.py) — 실시간판: 단락(8마디)씩 끝없이 이어 씀
//   첫 분위기: 도입 4마디 → 몸통 단락이 정해진 차례 없이 이어짐 (vary.cpp: 이야기 흐름 가 나 다 라 → 가' 나' 다' → 마 바 …)
//   분위기 바꿈: 2마디 덩어리 끝에서 · 이음 2마디(앞 선율 마지막 음에서 이어지는 선율 · 공통 화음 → 새 조 V · 템포 서서히) → 새 분위기
//   조절값 바꿈: 다음 2마디 덩어리부터 되감아 다시 씀 (rollback) · 끝내기: 끝 4마디 + 마지막 화음
#pragma once
#include "gen.h"
#include "song.h"
#include <algorithm>
#include <cstdlib>
#include <deque>
#include <map>
#include <memory>
#include <string>
#include <vector>

enum Role { R_INTRO, R_A, R_A2, R_B, R_A3, R_TAG, R_TRANS, R_TRADE, R_BREAK, R_SOLO };
extern const char *ROLE_NAME[10];

struct Mood {
    std::string id, name;
    std::vector<std::string> keys;
    bool minor; double bpm; int ts; double swing; int color;
    std::string src, feel, tempo;
    int dens, reg, mel_lo, mel_hi; double mtemp; int maxn, leap, copy;
    std::string lead; int lead_lo, lead_hi; double reverb;
    std::string band, recipe;
    bool jazzy; double ctemp;
    int style;                         // 편곡 공식 번호 (0 비오는날 … 8 낮드라이브 · 9 클래식 피아노 · 10 현악 앙상블 · 11 왈츠)
    double spice;                      // 화성 양념 0 순하게(조 안 · 3화음 쪽) … 1 맵게(재화성 · 조 밖 · 텐션)
};
const std::vector<Mood> &moods();
const Mood *mood_by_id(const std::string &id);

struct Section { Role role; int a, b; int sec; };
// 편성 상태 (분위기 팔레트 안에서 겹마다 몇 번째 선택지인가)
struct Orch { int lead = 0, second = 0, comp = 0, bass = 0, drum = 0;
    bool operator==(const Orch &o) const { return lead == o.lead && second == o.second && comp == o.comp && bass == o.bass && drum == o.drum; } };
// 이야기 흐름: 2마디 '생각'(가 나 다 라 …)을 차례로 내놓고, 한참 뒤에 가볍게 바꿔 다시 부름 (가' 나' 다') → 다음 장(마 바 사 …)
struct Idea { int chap = 0, ord = 0, seq = 0; std::string name; std::vector<Bar> deg; std::vector<MelNote> mel; int key_pc = 0, bar = 0, recalls = 0; };
struct Slot { int kind = 0, chap = 0, ord = 0; };     // kind 0 새 생각 · 1 다시 부름(chap·ord 의 생각) · 2 쉼
struct SecRec { int a = 0, b = 0; std::string key; std::vector<std::pair<int, Slot>> slots; };   // 단락 기록 (되감기용)
// 사용자 조절값 (-1 … +1, 0 = 분위기 기본) — 화면 옆 막대
struct Params { double reg = 0, tempo = 0, dens = 0, energy = 0, novelty = 0, space = 0, tension = 0;
    bool same_music(const Params &o) const { return reg == o.reg && tempo == o.tempo && dens == o.dens && energy == o.energy && novelty == o.novelty && tension == o.tension; } };

struct Models { Model chord, melody; };
struct BNote { int bi, on, d, p; };                 // 마디 번호 · 틱 · 길이틱 · 음

// 작곡 도우미 (compose.cpp)
std::vector<BN> oct_fit(const std::vector<BN> &notes, int lo, int hi);
std::vector<BN> sel(const std::vector<BN> &notes, const Song &S, int b0, int b1);
std::vector<BN> up(const std::vector<BN> &notes, int k);
std::vector<int> range_v(int a, int b);
double mel_score(const std::vector<BNote> &notes, const std::vector<Bar> &bars, double dens_target);
double score8(const std::vector<Bar> &bars, bool jazz = true);
std::string key_name(int pc, bool minor);

struct Session {
    const Mood &m;
    const Models &M;
    Song S;
    Rng rng;
    std::unique_ptr<MelodyWriter> w;
    int next_bar = 0, n_sec = 0;
    bool need_intro;
    std::vector<Bar> prog_a;                        // 첫 진행 (도입이 뒤 4마디를 씀)
    // 이야기 흐름
    std::vector<Idea> ideas;
    std::deque<Slot> plan_q;
    int chapter = 0, idea_seq = 0;
    std::vector<SecRec> hist;
    std::vector<std::pair<int, int>> recall_log;    // (마디, ideas 번호) — 되감을 때 되돌림
    std::map<int, Bar> bar_chords;                  // 마디 → 코드 (근음 절대, 재화성 뒤 = 실제 울리는 것)
    std::map<int, Bar> ai_chords;                   // 마디 → 진행 AI 가 쓴 그대로(재화성 전) — 다음 단락의 AI 문맥 (양념이 문맥에 쌓여 조를 잃지 않게)
    int since_tonic = 0;                            // 으뜸화음이 마지막으로 나온 뒤 지난 마디 수
    std::vector<std::vector<Bar>> recent_cells;     // 최근 새 2마디 코드 (똑같은 것 피함)
    char last_sec = 'A';
    Params P;
    Orch orch; bool orch_set = false;
    std::vector<Orch> orch_hist;
    std::vector<uint64_t> prog_hist;
    std::unique_ptr<MelodyWriter> w_solo;
    double walk = .45, wT1 = 11, wT2 = 4.3, wP1 = 0, wP2 = 0;
    int since_trade = 0, since_break = 0, since_solo = 0;
    double energy = .42, e_vel = 0;                 // 몇 분에 걸친 큰 강약 물결
    int since_b = 0, since_mod = 0, n_body = 0;
    Role last_role = R_INTRO;
    std::map<int, int> role_last;                   // 단락 종류 → 마지막으로 쓴 몸통 번호
    std::string plan_note;                          // 이번 단락을 어떻게 만들었나 (악보 머리말)
    std::vector<std::pair<double, double>> tempo_pts;
    double prog_score = 0;
    std::vector<BN> last_mel;                       // 방금 쓴 단락 선율 (악보 보기용)

    // 박 → 초 (템포 변화 반영, 이 세션 처음부터) · 스윙 자리
    double sec(double beat);
    double swing_pos(double beat) const;

    // near = 앞 분위기의 조 (가까운 조로 고름) · last_p / last_part = 앞 분위기 선율의 마지막 음 · 악기 (이음 선율이 거기서 이어짐)
    Session(const Mood &m, const Models &M, uint64_t seed, bool intro, double prev_bpm = 0, const Key *near = nullptr, int last_p = -1,
            const std::string &last_part = "", const Params *p = nullptr);
    Section next();                                 // 다음 단락 작곡 + 편곡
    Section ending();                               // 끝 4마디 + 마지막 화음 (+ 느려지기)
    double bpm_at(double beat) const;
    double base_bpm() const { return m.bpm * (1 + .2 * P.tempo); }    // 분위기 빠르기 × 조절값
    int reg_shift() const { return (int)std::lround(P.reg * 7); }     // 선율 음역 옮김 (반음)
    double nov() const { return .5 + .5 * P.novelty; }                 // 새로움 0 … 1
    double spice() const { return std::max(0.0, std::min(1.0, m.spice + .45 * P.tension)); }   // 화성 양념 (분위기 + 긴장감 조절값)
    ChordCtl chord_ctl() const { return {1.8 - 1.6 * spice(), 1.6 - 1.6 * spice(), m.src == "classical" ? 1.5 : 0.0, m.src == "jazz" ? .5 : 1.1}; }   // 진행 AI 를 조 쪽으로 당기는 세기
    double consonance() const { const char *e = std::getenv("CBGM_CONS"); return (e ? std::atof(e) : 1.0) * (1.25 - .9 * spice()); }   // 선율을 코드 안쪽으로 당기는 세기 (CBGM_CONS = 실험용 배율)
    int ct_level() const { if (const char *e = std::getenv("CBGM_CT")) return std::atoi(e); return spice() < .1 ? 3 : spice() < .75 ? 2 : 1; }   // 선율 AI 조건 (강박 코드음 정도)
    double tonal_score(const std::vector<Bar> &deg_bars, bool update);                         // 진행 후보가 조에 얼마나 붙어 있나
    void rollback(int bar);                         // 이 마디부터 다시 쓰기 (조절값이 바뀌면 · 다음 2마디 덩어리부터)
    int last_mel_pitch(int bar, std::string *part = nullptr) const;   // 이 마디 앞 마지막 선율 음

private:
    std::vector<double> T96;                        // 1/96 박마다 누적 초
    size_t pts_seen = 0;
    std::vector<Bar> to_deg(const std::vector<Bar> &abs_bars) const;
    std::vector<Bar> to_abs(const std::vector<Bar> &deg) const;
    std::vector<Bar> new_prog(char sec, const std::vector<Bar> *prev_deg, int n_change, const std::vector<Bar> *context_deg,
                              const std::map<int, Bar> *must = nullptr, int n_bars = 8);
    Role pick_kind();
    std::vector<Bar> reharm(std::vector<Bar> bars, Role role, int &n_done);
    void plan_chapter();
    const Idea *find_idea(int chap, int ord) const;
    std::vector<Bar> story_prog(Role role, const std::vector<Slot> &slots, int len, const std::map<int, Bar> *must);
    std::vector<BN> write_story(Role role, const std::vector<Bar> &bars, int bar0, const std::vector<Slot> &slots);
    std::vector<BN> write_solo(const std::vector<Bar> &bars, int bar0);
    void pick_orch(Role role);
    std::string orch_text() const;
    void arrange_body(Role role, int a, int b, const std::vector<BN> &mel);
    std::vector<BN> write_melody(const std::vector<Bar> &bars, const std::vector<const ChordTok *> &nexts, int bar0, double temp,
                                 double dens_target, const std::map<int, std::vector<MelNote>> *copy, int tries = 3);
    void arrange(Role role, int a, int b, const std::vector<BN> &mel);
    void arrange_main(Role role, int a, int b, const std::vector<BN> &mel);
    void finish_section(Role role);
    void transition(double prev_bpm, const Key *near_key, int last_p, const std::string &last_part);
};

#include "notation.h"
// 단락 → 악보(초). t_off = 이 세션이 시작한 시각(초). 이미 넣은 악기 이름은 Sheet 쪽 번호로 바꿈.
void section_to_sheet(Session &ss, const Section &sec, Sheet &sh, double t_off);
