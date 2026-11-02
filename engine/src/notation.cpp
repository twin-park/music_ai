#include "notation.h"
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <map>
#include <sstream>

static const std::map<int, std::string> DRUM_OUT = {{36, "kick"}, {37, "rim"}, {38, "snare"}, {39, "slap"}, {40, "sweep"}, {42, "hat"},
                                                    {44, "hat_foot"}, {46, "hat_open"}, {43, "tom3"}, {47, "tom2"}, {50, "tom1"},
                                                    {49, "crash"}, {51, "ride"}, {53, "bell"}, {70, "shaker"}};
static const std::map<std::string, int> DRUM_IN = {{"kick", 36}, {"rim", 37}, {"snare", 38}, {"tap", 38}, {"slap", 39}, {"sweep", 40},
                                                   {"hat", 42}, {"hat_foot", 44}, {"hat_open", 46}, {"tom3", 43}, {"tom2", 47}, {"tom1", 50},
                                                   {"crash", 49}, {"ride", 51}, {"bell", 53}, {"shaker", 70}};
static const char *ACC_OUT[5] = {"FF", "F", "N", "S", "SS"};

std::string fmt2(double x) {
    char b[32];
    std::snprintf(b, sizeof b, "%.2f", x);
    std::string s = b;
    while (!s.empty() && s.back() == '0') s.pop_back();
    if (!s.empty() && s.back() == '.') s.pop_back();
    if (s == "-0" || s.empty()) s = "0";
    return s;
}

int Sheet::part(const std::string &name, bool is_drum) {
    for (size_t i = 0; i < parts.size(); i++) if (parts[i] == name) return (int)i;
    parts.push_back(name); drum.push_back(is_drum);
    return (int)parts.size() - 1;
}

const Chord *Sheet::chord_at(double t) const {
    for (auto &c : chords) if (c.t0 - 1e-6 <= t && t < c.t1 - 1e-6) return &c.c;
    return nullptr;
}

std::string Sheet::spell(int midi, const Chord *c) const {
    if (c) {
        int iv = pmod(midi - c->root, 12);
        if (c->has_tone(midi) || c->has_tension(midi) || iv == 0) {
            int o, rl, ra;
            key.spell(60 + c->root, o, rl, ra);
            static const int ST[12] = {0, 1, 1, 2, 2, 3, 3, 4, 5, 5, 6, 6};
            int steps = ST[iv];
            if (iv == 3 && c->is_dom()) steps = 1;
            if (iv == 6 && (c->q == Q_M7B5 || c->q == Q_DIM7 || c->q == Q_DIM)) steps = 4;
            if (iv == 8 && c->q == Q_AUG) steps = 4;
            if (iv == 9 && c->q == Q_DIM7) steps = 6;
            int L = (rl + steps) % 7;
            int acc = pmod(pmod(midi, 12) - LETTER_PC[L] + 6, 12) - 6;
            if (acc >= -2 && acc <= 2) {
                int oc = (int)std::floor((midi - LETTER_PC[L] - acc) / 12.0) - 5;
                std::string os = oc == 0 ? "0" : (oc > 0 ? "+" : "-") + std::to_string(std::abs(oc));
                return os + " " + SOLFA[L] + " " + ACC_OUT[acc + 2];
            }
        }
    }
    return key.note_text(midi);
}

std::string Sheet::text(bool header) const {
    std::ostringstream o;
    if (header) {
        o << "# " << title << "\n";
        for (auto &x : notes_text) o << "# " << x << "\n";
        for (auto &x : info) o << "@" << x << "\n";
        o << "@조 " << key.name << "\n";
    }
    o << "\n[코드]\n";
    for (auto &c : chords) o << c.c.name(key) << " " << fmt2(c.t0) << "~" << fmt2(c.t1) << "\n";
    for (size_t pi = 0; pi < parts.size(); pi++) {
        struct E { double t; int k; std::string s; };
        std::vector<E> ev;
        for (auto &n : notes) {
            if (n.part != (int)pi) continue;
            std::string s;
            if (drum[pi]) {
                auto it = DRUM_OUT.find(n.p);
                std::string nm = it == DRUM_OUT.end() ? "snare" : it->second;
                if (parts[pi].find("브러시") != std::string::npos) nm = n.p == 38 ? "tap" : n.p == 39 ? "slap" : n.p == 40 ? "sweep" : nm;
                s = nm;
            } else s = spell(n.p, chord_at(n.t0));
            ev.push_back({n.t0, -n.p, s + " " + fmt2(n.t0) + "~" + fmt2(n.t1) + " " + std::to_string(n.v)});
        }
        if (parts[pi].find("피아노 오른손") != std::string::npos)
            for (auto &p : pedals) ev.push_back({p.first, 1, "페달 " + fmt2(p.first) + "~" + fmt2(p.second)});
        if (ev.empty()) continue;
        std::stable_sort(ev.begin(), ev.end(), [](const E &a, const E &b) { return a.t < b.t || (a.t == b.t && a.k < b.k); });
        o << "\n[" << parts[pi] << "]\n";
        for (auto &e : ev) o << e.s << "\n";
    }
    return o.str();
}

// ---------- 읽기 ----------
static std::string trim(const std::string &s) {
    size_t a = s.find_first_not_of(" \t\r\n"), b = s.find_last_not_of(" \t\r\n");
    return a == std::string::npos ? "" : s.substr(a, b - a + 1);
}
static bool span_of(const std::string &s, double &a, double &b) {
    size_t t = s.find('~');
    if (t == std::string::npos) return false;
    char *e1, *e2;
    std::string x = trim(s.substr(0, t)), y = trim(s.substr(t + 1));
    a = std::strtod(x.c_str(), &e1); b = std::strtod(y.c_str(), &e2);
    return !x.empty() && !y.empty() && *e1 == 0 && *e2 == 0;
}

bool load_sheet(const std::string &text, Sheet &sh, std::string *err) {
    static const std::map<std::string, int> SOL = {{"do", 0}, {"re", 1}, {"mi", 2}, {"fa", 3}, {"sol", 4}, {"so", 4}, {"la", 5}, {"si", 6},
                                                   {"ti", 6}, {"도", 0}, {"레", 1}, {"미", 2}, {"파", 3}, {"솔", 4}, {"라", 5}, {"시", 6}};
    static const std::map<std::string, int> ACC = {{"FF", -2}, {"F", -1}, {"N", 0}, {"S", 1}, {"SS", 2}, {"bb", -2}, {"b", -1},
                                                   {"#", 1}, {"##", 2}, {"-", 0}};
    std::istringstream in(text);
    std::string ln;
    int cur = -2;                                      // -2 = 아직 없음, -1 = [코드]
    int lineno = 0;
    sh.key = Key("C");
    while (std::getline(in, ln)) {
        lineno++;
        std::string s = trim(ln);
        if (s.empty()) continue;
        if (s[0] == '#') { if (sh.title.empty()) sh.title = trim(s.substr(1)); continue; }
        if (s[0] == '@') {
            size_t sp = s.find(' ');
            std::string k = s.substr(1, sp == std::string::npos ? std::string::npos : sp - 1), v = sp == std::string::npos ? "" : trim(s.substr(sp));
            if (k == "조") sh.key = Key(v); else sh.info.push_back(k + " " + v);
            continue;
        }
        if (s.front() == '[' && s.back() == ']') {
            std::string nm = trim(s.substr(1, s.size() - 2));
            if (nm == "코드") cur = -1;
            else cur = sh.part(nm, nm.find("드럼") != std::string::npos || nm.find("브러시") != std::string::npos);
            continue;
        }
        std::istringstream ws(s);
        std::vector<std::string> w;
        std::string x;
        while (ws >> x) w.push_back(x);
        double a, b;
        if (cur == -1) {
            Chord c;
            if (w.size() >= 2 && Chord::parse(w[0], c) && span_of(s.substr(s.find(' ') + 1), a, b)) sh.chords.push_back({a, b, c});
            continue;
        }
        if (cur == -2) continue;
        if ((w[0] == "페달" || w[0] == "ped") && w.size() >= 2 && span_of(s.substr(s.find(' ') + 1), a, b)) { sh.pedals.push_back({a, b}); continue; }
        if (sh.drum[cur] && w.size() >= 2 && DRUM_IN.count(w[0])) {
            std::string rest = trim(s.substr(w[0].size()));
            size_t sp = rest.find_last_of(' ');
            int v = 70;
            std::string rng = rest;
            if (sp != std::string::npos && rest.find('~') < sp) { v = std::atoi(rest.substr(sp + 1).c_str()); rng = rest.substr(0, sp); }
            if (span_of(rng, a, b)) { sh.notes.push_back({cur, a, b, DRUM_IN.at(w[0]), v}); continue; }
        }
        if (w.size() >= 4 && SOL.count(w[1]) && ACC.count(w[2])) {
            std::string rng = w[3];
            int v = w.size() >= 5 ? std::atoi(w[4].c_str()) : 70;
            if (rng.find('~') == std::string::npos && w.size() >= 6 && w[4] == "~") { rng = w[3] + "~" + w[5]; v = w.size() >= 7 ? std::atoi(w[6].c_str()) : 70; }
            if (span_of(rng, a, b)) {
                int midi = 12 * (std::atoi(w[0].c_str()) + 5) + LETTER_PC[SOL.at(w[1])] + ACC.at(w[2]);
                sh.notes.push_back({cur, a, b, midi, v});
                continue;
            }
        }
        if (err) *err = std::to_string(lineno) + "번째 줄을 못 읽음: " + s;
        return false;
    }
    return true;
}
