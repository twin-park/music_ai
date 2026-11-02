// 음악 기본 (score/theory.py): 음높이 ↔ 악보 글자 · 조 · 화음 · 음계 · 보이싱
#pragma once
#include <string>
#include <vector>

extern const char *LETTERS;               // "CDEFGAB"
extern const int LETTER_PC[7];
extern const char *SOLFA[7];

struct Key {
    std::string name, tonic;
    bool minor = false;
    int pc = 0, letter = 0;
    std::vector<int> scale;
    Key() {}
    explicit Key(const std::string &name);
    void spell(int midi, int &octave, int &L, int &acc) const;
    std::string note_text(int midi) const;
    std::string pc_name(int pc) const;
    bool in_scale(int pc) const;
};

// 화음 종류 — QUAL 표와 같은 순서
enum Q { Q_MAJ, Q_6, Q_69, Q_MAJ7, Q_MAJ9, Q_MAJ7S11, Q_MIN, Q_M6, Q_M7, Q_M9, Q_M11, Q_MM7, Q_7, Q_9, Q_13,
         Q_7B9, Q_7ALT, Q_7S11, Q_7SUS4, Q_SUS4, Q_M7B5, Q_DIM7, Q_DIM, Q_AUG, Q_COUNT };

struct QualInfo { const char *name, *show; std::vector<int> tones, tens; std::vector<int> scale; };
const QualInfo &qinfo(int q);
int qual_from_name(const std::string &s);       // "maj7" "M7" "m7(b5)" … → Q (없으면 -1)

struct Chord {
    int root = 0, q = Q_MAJ, bass = 0;
    Chord() {}
    Chord(int r, int q_, int b = -1) : root(((r % 12) + 12) % 12), q(q_), bass(b < 0 ? root : ((b % 12) + 12) % 12) {}
    static bool parse(const std::string &sym, Chord &out);
    std::vector<int> tones() const;
    std::vector<int> tensions() const;
    int iv(int k) const;                           // 3 · 5 · 7음 (없으면 -1)
    std::vector<int> scale(const Key *key = nullptr) const;
    bool is_dom() const;
    bool is_minor() const;
    std::string name(const Key &key) const;
    bool has_tone(int pc) const;
    bool has_tension(int pc) const;
};

int pmod(int a, int m);
int near(int pc, int ref);
int fit(int p, int lo, int hi);
std::vector<int> stack(const std::vector<int> &pcs, int lo, int hi, const std::vector<int> *prev = nullptr);
std::vector<int> rootless(const Chord &c);
std::vector<int> quartal(const Chord &c);
std::vector<int> guide(const Chord &c);
