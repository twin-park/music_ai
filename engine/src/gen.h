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

// form: [('A',8),('A',8),('B',8),('A',8)] → 마디마다 [(박, 도수, 종류)]
// prefix: 먼저 문맥으로 넣을 앞 단락 진행(도수) · fixed: {마디번호: 그대로 둘 마디} — 나머지 마디만 AI 가 새로 씀
std::vector<Bar> progression(const Model &m, const std::vector<std::pair<char, int>> &form, bool minor, const std::string &src, int ts,
                             const std::vector<int> &beats, double temp, double top_p, uint64_t seed,
                             const std::vector<Bar> *prefix = nullptr, char prefix_sec = 'A', const std::map<int, Bar> *fixed = nullptr);

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
    MelodyWriter(const Model *m, int ts, const std::string &kind, const std::string &feel, const std::string &tempo, bool minor,
                 int dens, int reg, uint64_t seed);
    std::vector<int> chord_toks(const Bar &chords, const ChordTok *nxt) const;
    // 한 마디. force 가 있으면 그대로 넣음.
    // cont = true 면 force 음들을 넣은 뒤 그 마디 나머지를 AI 가 이어 씀 (동기 앞머리만 물려받기)
    std::vector<MelNote> bar(const Bar &chords, const ChordTok *nxt, int lo, int hi, double temp, double top_p, int leap,
                             const std::vector<MelNote> *force, int max_notes, bool rest_ok, bool cont = false);
};
