// 생성 (score/ai/gen.py): 진행 AI(틀은 공식으로 A A B A) · 선율 AI(코드는 주고 선율만)
#pragma once
#include "model.h"
#include "rng.h"
#include <array>
#include <map>
#include <string>
#include <vector>

using ChordTok = std::array<int, 3>;                 // (박, 도수 또는 근음, 종류번호 0~10)
using Bar = std::vector<ChordTok>;

int pick(const std::vector<float> &logits, const std::vector<int> &allowed, double temp, double top_p, Rng &rng);
int src_id(const std::string &src);                  // "jazz" 0 · "pop" 1 · "song" 2 · "classical" 3
// 2마디 코드 덩어리의 '뼈대' — 근음(도수)과 큰 갈래(장 · 단 · 딸림 · 감)만 봄. 9 ↔ 7(b9) ↔ sus 처럼 색만 다른 건 같은 덩어리로 침
uint64_t cell_sig(const std::vector<std::array<int, 3>> &a, const std::vector<std::array<int, 3>> &b);
extern const std::vector<int> TONES_Q[11], TENS_Q[11];   // AI 코드 종류(11) → 구성음 · 텐션 (근음에서 반음 수)

// 진행 AI 를 조(key) 쪽으로 당기기 — 이어 쓰다 보면 조에서 멀어지는 것을 막음 (값 = 점수에서 빼는 양, 0 이면 끔)
struct ChordCtl {
    double key_pull = 0;                             // 조 밖 근음 · 그 자리에 안 맞는 화음 종류에 벌점
    double calm = 0;                                 // 긴장 큰 종류(alt · 반감 · 감 · 증 · mM7)에 벌점
    double triad = 0;                                // 7화음(장7 · 단7)에 벌점 — 클래식은 3화음 중심
    double qfit = .5;                                // 그 자리에 안 맞는 종류 벌점 = key_pull × qfit
};

// form: [('A',8),('A',8),('B',8),('A',8)] → 마디마다 [(박, 도수, 종류)]
// prefix: 먼저 문맥으로 넣을 앞 단락 진행(도수) · fixed: {마디번호: 그대로 둘 마디} — 나머지 마디만 AI 가 새로 씀
// avoid: 최근에 쓴 2마디 코드 덩어리들 — 새로 쓰는 덩어리가 이것과 똑같아지면 다시 씀
std::vector<Bar> progression(const Model &m, const std::vector<std::pair<char, int>> &form, bool minor, const std::string &src, int ts,
                             const std::vector<int> &beats, double temp, double top_p, uint64_t seed,
                             const std::vector<Bar> *prefix = nullptr, char prefix_sec = 'A', const std::map<int, Bar> *fixed = nullptr,
                             const ChordCtl *ctl = nullptr, const std::vector<std::vector<Bar>> *avoid = nullptr);

struct MelNote { int on, d, p; };                    // 틱(박당 12) · 길이틱 · 음

struct MelodyWriter {
    Runner r;
    int ts;
    Rng rng;
    std::vector<int> head;
    int prev_p = -1;
    int same_run = 0;                                // 같은 음이 몇 번 연달아 나왔나 (4번째는 막음)
    // 베끼기 막기: 선율 AI 는 같은 코드가 다시 나오면 지난 마디를 통째로 베끼려 함(되풀이 느낌의 주범)
    //   → 이번 마디가 지난 마디와 2음 넘게 (자리 · 음) 똑같이 이어지려 하면 그 음에 벌점 (리듬만 닮는 건 괜찮음)
    std::vector<std::vector<MelNote>> past;          // 지난 마디들 (최근 96마디)
    double no_copy = 0;                              // 벌점 (로짓) — 0 이면 끔
    // 조화 맞추기: 강박에 코드 밖 음이 오는 것 · 코드 밖 음을 길게 끄는 것에 벌점, 코드 밖 음 다음엔 순차로 풀리게 (0 이면 끔, 1 = 보통)
    double consonance = 0;
    int prev_kind = 0;                               // 앞 음이 코드음 0 · 텐션 1 · 그 밖 2
    // src = 갈래(재즈 · 팝 · 노래 · 클래식) · ct = 강박 코드음 정도 0~3 (높을수록 안쪽으로 조화롭게)
    MelodyWriter(const Model *m, int ts, const std::string &kind, const std::string &feel, const std::string &tempo, bool minor,
                 int dens, int reg, uint64_t seed, const std::string &src = "jazz", int ct = 2);
    std::vector<int> chord_toks(const Bar &chords, const ChordTok *nxt) const;
    // 한 마디. force 가 있으면 그대로 넣음.
    // cont = true 면 force 음들을 넣은 뒤 그 마디 나머지를 AI 가 이어 씀 (동기 앞머리만 물려받기)
    std::vector<MelNote> bar(const Bar &chords, const ChordTok *nxt, int lo, int hi, double temp, double top_p, int leap,
                             const std::vector<MelNote> *force, int max_notes, bool rest_ok, bool cont = false);
};
