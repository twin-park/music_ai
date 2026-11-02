#include "theory.h"
#include <algorithm>
#include <cmath>
#include <map>

const char *LETTERS = "CDEFGAB";
const int LETTER_PC[7] = {0, 2, 4, 5, 7, 9, 11};
const char *SOLFA[7] = {"do", "re", "mi", "fa", "sol", "la", "si"};
static const int DEG_LETTER[12] = {0, 1, 1, 2, 2, 3, 3, 4, 5, 5, 6, 6};
static const char *ACC_OUT[5] = {"FF", "F", "N", "S", "SS"};

int pmod(int a, int m) { return ((a % m) + m) % m; }

static int name_pc(const std::string &n) {
    int base = LETTER_PC[std::string(LETTERS).find(n[0])];
    for (size_t i = 1; i < n.size(); i++) base += n[i] == '#' ? 1 : n[i] == 'b' ? -1 : 0;
    return pmod(base, 12);
}

Key::Key(const std::string &nm) : name(nm) {
    minor = !nm.empty() && nm.back() == 'm';
    tonic = minor ? nm.substr(0, nm.size() - 1) : nm;
    pc = name_pc(tonic);
    letter = (int)std::string(LETTERS).find(tonic[0]);
    static const int MAJ[7] = {0, 2, 4, 5, 7, 9, 11}, MIN[7] = {0, 2, 3, 5, 7, 8, 10};
    for (int i = 0; i < 7; i++) scale.push_back((pc + (minor ? MIN[i] : MAJ[i])) % 12);
}

bool Key::in_scale(int p) const { return std::find(scale.begin(), scale.end(), pmod(p, 12)) != scale.end(); }

void Key::spell(int midi, int &octave, int &L, int &acc) const {
    int d = pmod(midi - pc, 12);
    L = (letter + DEG_LETTER[d]) % 7;
    acc = pmod(pmod(midi, 12) - LETTER_PC[L] + 6, 12) - 6;
    if (acc > 2 || acc < -2) {
        int best = 99;
        for (int k = 0; k < 7; k++) {
            int a = pmod(pmod(midi, 12) - LETTER_PC[k] + 6, 12) - 6;
            if (std::abs(a) < best) { best = std::abs(a); L = k; acc = a; }
        }
    }
    int v = midi - LETTER_PC[L] - acc;
    octave = (int)std::floor(v / 12.0) - 5;
}

std::string Key::note_text(int midi) const {
    int o, L, a;
    spell(midi, o, L, a);
    std::string os = o == 0 ? "0" : (o > 0 ? "+" : "-") + std::to_string(std::abs(o));
    return os + " " + SOLFA[L] + " " + ACC_OUT[a + 2];
}

std::string Key::pc_name(int p) const {
    int o, L, a;
    spell(60 + pmod(p - 60, 12), o, L, a);
    static const char *FL[12] = {"C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"};
    static const char *SH[12] = {"C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"};
    if (a == 2 || a == -2) return (a < 0 ? FL : SH)[pmod(p, 12)];
    return std::string(1, LETTERS[L]) + (a < 0 ? "b" : a > 0 ? "#" : "");
}

// ---------------- 화음 표 ----------------
static const std::vector<int> IONIAN{0, 2, 4, 5, 7, 9, 11}, LYDIAN{0, 2, 4, 6, 7, 9, 11}, DORIAN{0, 2, 3, 5, 7, 9, 10},
    AEOLIAN{0, 2, 3, 5, 7, 8, 10}, MIXO{0, 2, 4, 5, 7, 9, 10}, PHRDOM{0, 1, 4, 5, 7, 8, 10}, ALTERED{0, 1, 3, 4, 6, 8, 10},
    LYDDOM{0, 2, 4, 6, 7, 9, 10}, LOCRIAN{0, 1, 3, 5, 6, 8, 10}, WHOLEHALF{0, 2, 3, 5, 6, 8, 9, 11}, WHOLETONE{0, 2, 4, 6, 8, 10},
    MELMIN{0, 2, 3, 5, 7, 9, 11};

static const QualInfo QT[Q_COUNT] = {
    {"", "", {0, 4, 7}, {14}, IONIAN},
    {"6", "6", {0, 4, 7, 9}, {14}, IONIAN},
    {"69", "69", {0, 4, 7, 9, 14}, {}, IONIAN},
    {"maj7", "M7", {0, 4, 7, 11}, {14, 21}, IONIAN},
    {"maj9", "M9", {0, 4, 7, 11, 14}, {21}, IONIAN},
    {"maj7#11", "M7(#11)", {0, 4, 7, 11, 18}, {14, 21}, LYDIAN},
    {"m", "m", {0, 3, 7}, {14}, AEOLIAN},
    {"m6", "m6", {0, 3, 7, 9}, {14}, DORIAN},
    {"m7", "m7", {0, 3, 7, 10}, {14, 17}, DORIAN},
    {"m9", "m9", {0, 3, 7, 10, 14}, {17}, DORIAN},
    {"m11", "m11", {0, 3, 7, 10, 14, 17}, {}, DORIAN},
    {"mM7", "mM7", {0, 3, 7, 11}, {14}, MELMIN},
    {"7", "7", {0, 4, 7, 10}, {14, 21}, MIXO},
    {"9", "9", {0, 4, 7, 10, 14}, {21}, MIXO},
    {"13", "13", {0, 4, 7, 10, 14, 21}, {}, MIXO},
    {"7b9", "7(b9)", {0, 4, 7, 10, 13}, {20}, PHRDOM},
    {"7alt", "7alt", {0, 4, 10, 13, 20}, {15, 18}, ALTERED},
    {"7#11", "7(#11)", {0, 4, 7, 10, 18}, {14, 21}, LYDDOM},
    {"7sus4", "7sus4", {0, 5, 7, 10}, {14, 21}, MIXO},
    {"sus4", "sus4", {0, 5, 7}, {14}, MIXO},
    {"m7b5", "m7(b5)", {0, 3, 6, 10}, {17, 20}, LOCRIAN},
    {"dim7", "dim7", {0, 3, 6, 9}, {14, 17}, WHOLEHALF},
    {"dim", "dim", {0, 3, 6}, {}, WHOLEHALF},
    {"aug", "aug", {0, 4, 8}, {}, WHOLETONE},
};

const QualInfo &qinfo(int q) { return QT[q]; }

int qual_from_name(const std::string &s) {
    static const std::map<std::string, std::string> SYN = {
        {"M7", "maj7"}, {"Δ", "maj7"}, {"Δ7", "maj7"}, {"M9", "maj9"}, {"-7", "m7"}, {"-", "m"}, {"min", "m"}, {"min7", "m7"},
        {"ø", "m7b5"}, {"ø7", "m7b5"}, {"m7(b5)", "m7b5"}, {"o7", "dim7"}, {"°7", "dim7"}, {"o", "dim"}, {"+", "aug"},
        {"7(b9)", "7b9"}, {"6/9", "69"}, {"M7(#11)", "maj7#11"}, {"7(#11)", "7#11"}};
    auto it = SYN.find(s);
    const std::string &n = it == SYN.end() ? s : it->second;
    for (int q = 0; q < Q_COUNT; q++)
        if (n == QT[q].name) return q;
    return -1;
}

bool Chord::parse(const std::string &sym, Chord &out) {
    std::string s = sym, b;
    size_t sl = s.find('/');
    if (sl != std::string::npos) { b = s.substr(sl + 1); s = s.substr(0, sl); }
    if (s.empty() || std::string(LETTERS).find(s[0]) == std::string::npos) return false;
    size_t rl = (s.size() > 2 && (s.substr(1, 2) == "bb" || s.substr(1, 2) == "##")) ? 3 : (s.size() > 1 && (s[1] == '#' || s[1] == 'b')) ? 2 : 1;
    int q = qual_from_name(s.substr(rl));
    if (q < 0) return false;
    out = Chord(name_pc(s.substr(0, rl)), q, b.empty() ? -1 : name_pc(b));
    return true;
}

std::vector<int> Chord::tones() const {
    std::vector<int> v;
    for (int i : QT[q].tones) v.push_back((root + i) % 12);
    return v;
}
std::vector<int> Chord::tensions() const {
    std::vector<int> v;
    for (int i : QT[q].tens) v.push_back((root + i) % 12);
    return v;
}
bool Chord::has_tone(int pc) const { pc = pmod(pc, 12); for (int i : QT[q].tones) if ((root + i) % 12 == pc) return true; return false; }
bool Chord::has_tension(int pc) const { pc = pmod(pc, 12); for (int i : QT[q].tens) if ((root + i) % 12 == pc) return true; return false; }

int Chord::iv(int k) const {
    int lo = k == 3 ? 3 : k == 5 ? 6 : 9;
    for (int i : QT[q].tones)
        if (i >= lo && i <= lo + 2) return (root + i) % 12;
    return -1;
}

bool Chord::is_dom() const { return q == Q_7 || q == Q_9 || q == Q_13 || q == Q_7B9 || q == Q_7ALT || q == Q_7S11 || q == Q_7SUS4; }
bool Chord::is_minor() const {
    return q == Q_MIN || q == Q_M6 || q == Q_M7 || q == Q_M9 || q == Q_M11 || q == Q_MM7 || q == Q_M7B5 || q == Q_DIM7 || q == Q_DIM;
}

std::vector<int> Chord::scale(const Key *key) const {
    std::vector<int> own;
    for (int i : QT[q].scale) own.push_back((root + i) % 12);
    if (key && !is_dom() && q != Q_M7B5 && q != Q_DIM7) {
        bool all = true;
        for (int t : tones()) all = all && key->in_scale(t);
        if (all) { std::vector<int> s = key->scale; std::sort(s.begin(), s.end()); return s; }
    }
    std::sort(own.begin(), own.end());
    own.erase(std::unique(own.begin(), own.end()), own.end());
    return own;
}

std::string Chord::name(const Key &key) const {
    std::string s = key.pc_name(root) + QT[q].show;
    if (bass != root) s += "/" + key.pc_name(bass);
    return s;
}

// ---------------- 보이싱 ----------------
int near(int pc, int ref) {
    int p = ref - pmod(ref - pc, 12);
    return ref - p <= 6 ? p : p + 12;
}

int fit(int p, int lo, int hi) {
    while (p < lo) p += 12;
    while (p > hi) p -= 12;
    return p;
}

std::vector<int> stack(const std::vector<int> &pcs, int lo, int hi, const std::vector<int> *prev) {
    std::vector<int> best;
    double bc = 1e9;
    const int n = (int)pcs.size();
    if (n == 0) return best;
    double center = (lo + hi) / 2.0;
    if (prev && !prev->empty()) { center = 0; for (int x : *prev) center += x; center /= prev->size(); }
    auto fdiv = [](int a, int b) { return (int)std::floor((double)a / b); };
    for (int inv = 0; inv < n; inv++) {
        for (int o = fdiv(lo, 12) - 1; o < fdiv(hi, 12) + 1; o++) {
            std::vector<int> v;
            int last = o * 12 - 1;
            for (int k = 0; k < n; k++) {
                int pc = pcs[(inv + k) % n];
                int p = last + 1 + pmod(pc - (last + 1), 12);
                v.push_back(p); last = p;
            }
            if (v.front() < lo || v.back() > hi) continue;
            double cost = 0, sum = 0;
            for (int a : v) sum += a;
            if (prev && !prev->empty())
                for (int a : v) { int m = 999; for (int b : *prev) m = std::min(m, std::abs(a - b)); cost += m; }
            cost += std::fabs(sum / n - center) * 0.4;
            if (cost < bc) { best = v; bc = cost; }
        }
    }
    if (best.empty()) {
        for (int pc : pcs) best.push_back(fit(near(pc, (lo + hi) / 2), lo, hi));
        std::sort(best.begin(), best.end());
    }
    return best;
}

std::vector<int> rootless(const Chord &c) {
    int r = c.root, q = c.q;
    auto I = [r](std::initializer_list<int> xs) { std::vector<int> v; for (int x : xs) v.push_back((r + x) % 12); return v; };
    if (q == Q_MAJ7 || q == Q_MAJ9) return I({4, 7, 11, 14});
    if (q == Q_MAJ7S11) return I({4, 6, 11, 14});
    if (q == Q_6 || q == Q_69 || q == Q_MAJ) return I({4, 7, 9, 14});
    if (q == Q_M7 || q == Q_M9 || q == Q_M11) return I({3, 7, 10, 14});
    if (q == Q_M6 || q == Q_MIN) return I({3, 7, 9, 14});
    if (q == Q_MM7) return I({3, 7, 11, 14});
    if (q == Q_7 || q == Q_9 || q == Q_13 || q == Q_7S11) return I({4, 9, 10, 14});
    if (q == Q_7B9) return I({4, 8, 10, 13});
    if (q == Q_7ALT) return I({4, 8, 10, 15});
    if (q == Q_7SUS4 || q == Q_SUS4) return I({5, 7, 10, 14});
    if (q == Q_M7B5) return I({3, 6, 10, 17});
    if (q == Q_DIM7 || q == Q_DIM) return I({0, 3, 6, 9});
    if (q == Q_AUG) return I({4, 8, 10, 14});
    return c.tones();
}

std::vector<int> quartal(const Chord &c) {
    int r = c.root, q = c.q;
    auto I = [r](std::initializer_list<int> xs) { std::vector<int> v; for (int x : xs) v.push_back((r + x) % 12); return v; };
    if (q == Q_M7 || q == Q_M9 || q == Q_M11 || q == Q_M6) return I({2, 7, 0, 5, 9});
    if (q == Q_MAJ7 || q == Q_MAJ9 || q == Q_6 || q == Q_69 || q == Q_MAJ7S11) return I({4, 9, 2, 7});
    if (q == Q_7SUS4 || q == Q_SUS4) return I({5, 10, 2, 7});
    return rootless(c);
}

std::vector<int> guide(const Chord &c) {
    int t3 = c.iv(3), t7 = c.iv(7);
    if (t7 < 0) t7 = (c.root + ((c.q == Q_6 || c.q == Q_69 || c.q == Q_M6) ? 9 : 7)) % 12;
    return {t3, t7};
}
