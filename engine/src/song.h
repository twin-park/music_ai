// 편곡 공식 (score/arrange.py Song): 코드 칸 + 선율 → 피아노(선율 아래 화음·왼손·반주)·베이스·드럼·현악
// 시간은 박 단위. 실시간판은 단락(8마디)씩 덧붙이고, 공식(강약·부딪힘 정리)도 새 단락에만 적용.
#pragma once
#include "theory.h"
#include "rng.h"
#include <array>
#include <deque>
#include <map>
#include <set>
#include <string>
#include <vector>

struct Note {
    double t, d;          // 시작박 · 길이박
    int p, v;             // 음(드럼은 번호) · 세기
    int part;             // 악기 번호 (Song::names)
    int sec;              // 몇 번째 단락에서 생겼나
    bool dead = false;
};
struct BN { double t, d; int p; };          // 선율 음 (박 · 길이 · 음)
struct Span { double a, b; Chord c; };

// AI 코드 종류(11) → 실제 코드 (색 0 단순 · 1 7·9 · 2 9·13·alt)
enum { QA_MAJ, QA_MAJ7, QA_MIN, QA_M7, QA_DOM, QA_ALT, QA_SUS, QA_HDIM, QA_DIM, QA_AUG, QA_MM7 };
extern const char *QUALS[11];

// 드럼 꼴 → 북 파트 이름 (브러시 · 재즈 드럼 · 팝 드럼 · 808)
const char *drum_kit(const std::string &kind);

struct Song {
    Key key;
    double bpm;
    int ts;
    double swing;
    Rng rng;
    std::vector<Span> spans;
    std::deque<Note> pool;
    std::vector<std::string> names;
    std::vector<std::vector<Note *>> ev;          // 악기마다
    std::vector<std::pair<double, double>> pedal;
    std::set<int> lead_parts;
    std::vector<Note *> mel;
    struct Follow { Note *h, *top; int dv; };
    std::vector<Follow> follow;
    int cur_sec = 0;                              // 지금 쓰는 단락 번호
    double sec_factor = 1.0;                      // 지금 단락 세기 배율 (도입 .86 · A .95 · A' 1 · B 1.1 · A'' 1.03 · 끝 .86)
    int walk_p = 39;                              // 워킹 베이스 이어 가기
    double energy = .5;                           // 큰 물결 (0~1) — 드럼 세기층 · 크래시 · 필인
    int arp_fig = 0;                              // 펼침 꼴 (가끔 바뀜)
    double b9_rate = .6;                          // 단조 쪽으로 풀리는 딸림7 을 7(b9) 로 물들일 확률 (화성 양념에 따라)
    double crunch = .5;                           // 화음 안 반음 부딪힘을 얼마나 두나 — .5 아래면 반음으로 붙은 음을 풀어 줌 (13·b7 → 5·b7, 9·b3 → 1·b3, 7·1 → 6·1)
    void smooth_voicing(std::vector<int> &v, const Chord &c) const;

    Song(const std::string &k, double bpm_, int ts_, double sw, uint64_t seed) : key(k), bpm(bpm_), ts(ts_), swing(sw), rng(seed) {}

    int part_id(const std::string &name);
    bool is_drum_part(int id) const { return drum_name(names[id]); }
    static bool drum_name(const std::string &n) { return n == "브러시" || n == "드럼" || n == "팝드럼" || n == "808드럼"; }
    // 코드 칸: bars[마디] = [(박, 근음, 종류번호)] · bar0 부터 덧붙임
    void add_chords(int bar0, const std::vector<std::vector<std::array<int, 3>>> &bars, int color, bool minor_target_b9 = true);
    void add_span(double a, double b, const Chord &c) { spans.push_back({a, b, c}); }
    const Span &span(double t) const;
    const Chord &chord(double t) const { return span(t).c; }
    std::vector<Span> spans_in(int b0, int b1) const;

    Note *add(const std::string &part, double t, double d, int p, double v);
    double arc(double t, double base, double amp = 7) const;

    void lead(const std::string &part, const std::vector<BN> &notes, double base, double legato = 1.0);
    std::vector<int> block_under(int m, const Chord &c, int n = 3, int lo = 50) const;
    void piano_melody(const std::vector<BN> &notes, double base, const std::string &mode = "block", const std::string &part = "피아노 오른손");
    void lh_guide(int b0, int b1, double base = 46, bool shell = false, const std::string &part = "피아노 왼손");
    void pedals(int b0, int b1, int every = 2);
    void comp(const std::vector<int> &bars, const std::string &feel = "ballad", double base = 48, const std::string &voicing = "rootless",
              int lo = 50, int hi = 68, const std::vector<BN> &avoid = {}, const std::string &p_hi = "피아노 오른손",
              const std::string &p_lo = "피아노 왼손");
    void guitar_comp(const std::vector<int> &bars, const std::string &part, const std::string &feel = "bossa", double base = 56);
    void piano_pattern(int b0, int b1, const std::string &kind = "arp", double base = 46, const std::string &part = "피아노 왼손");
    void bass(int b0, int b1, const std::string &style = "two", double base = 74, const std::string &part = "베이스", int lo = 28, int hi = 48);
    void bass_pat(int b0, int b1, const std::string &style, double base, const std::string &part, int lo, int hi);   // 리듬 꼴 베이스 (펑크 · 레게 · 삼바 · 탱고 …)
    void drums(int b0, int b1, const std::string &kind = "brush", int lvl = 0, int fill_every = 8, bool crash = true);
    void strings_pad(int b0, int b1, const std::string &part = "현악", double base = 50, int lo = 52, int hi = 74);
    void guide_line(int b0, int b1, const std::string &part, double base = 56, int lo = 50, int hi = 67);

    // 공식 다듬기 (지금 단락의 음만)
    std::vector<BN> fix_avoid(const std::vector<BN> &notes, bool jazz = true) const;
    void phrase_dynamics(bool jazz = true);
    void section_dynamics();
    std::pair<int, int> declash(double min_len = .3);
    std::pair<int, int> low_mud(int top = 60);
    // 이 박 뒤의 음·코드 지우기 (분위기 바꿀 때)
    void cut_after(double beat);
};
