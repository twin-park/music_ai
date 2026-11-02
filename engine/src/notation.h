// 악보 글자 (score/notation.py): <옥타브> <계이름> <임시표> <시작초>~<끝초> [세기]  ·  [악기] · [코드] · 드럼은 이름 · 페달 a~b
#pragma once
#include "theory.h"
#include <string>
#include <vector>

struct TNote { int part; double t0, t1; int p, v; };   // 초 단위 음
struct TChord { double t0, t1; Chord c; };

struct Sheet {
    std::string title;
    Key key;
    std::vector<std::string> notes_text, info;          // # 설명 · @정보 줄
    std::vector<TChord> chords;
    std::vector<std::string> parts;                     // 악기 이름 (나온 순서)
    std::vector<bool> drum;
    std::vector<TNote> notes;
    std::vector<std::pair<double, double>> pedals;      // 피아노 페달 (초)
    int part(const std::string &name, bool is_drum);
    const Chord *chord_at(double t) const;
    std::string spell(int midi, const Chord *c) const;
    std::string text(bool header = true) const;
};

bool load_sheet(const std::string &text, Sheet &sh, std::string *err);
std::string fmt2(double x);
