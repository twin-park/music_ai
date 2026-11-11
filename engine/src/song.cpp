#include "song.h"
#include <algorithm>
#include <cmath>
#include <functional>

const char *QUALS[11] = {"maj", "maj7", "min", "m7", "dom", "alt", "sus", "hdim", "dim", "aug", "mM7"};
static const int COLOR[11][3] = {
    {Q_MAJ, Q_6, Q_69}, {Q_MAJ7, Q_MAJ7, Q_MAJ9}, {Q_MIN, Q_M7, Q_M9}, {Q_M7, Q_M7, Q_M9}, {Q_7, Q_9, Q_13},
    {Q_7B9, Q_7B9, Q_7ALT}, {Q_SUS4, Q_7SUS4, Q_7SUS4}, {Q_M7B5, Q_M7B5, Q_M7B5}, {Q_DIM7, Q_DIM7, Q_DIM7},
    {Q_AUG, Q_AUG, Q_AUG}, {Q_MM7, Q_MM7, Q_MM7}};

static bool has(const std::vector<int> &v, int x) { return std::find(v.begin(), v.end(), x) != v.end(); }
static bool contains(const std::string &s, const char *w) { return s.find(w) != std::string::npos; }
static double frac1(double x) { return x - std::floor(x); }                    // 파이썬 x % 1
static double fmodp(double x, double m) { return x - std::floor(x / m) * m; }  // 파이썬 x % m

// 범위 안에서 조건 맞는 음 중 cost 가 가장 작은 첫 음 (파이썬 min(…, key=…))
static int pick_min(int lo, int hi_excl, const std::function<bool(int)> &ok, const std::function<double(int)> &cost, int fallback) {
    int best = fallback; double bc = 1e18;
    for (int x = lo; x < hi_excl; x++)
        if (ok(x)) { double c = cost(x); if (c < bc) { bc = c; best = x; } }
    return best;
}

int Song::part_id(const std::string &name) {
    for (size_t i = 0; i < names.size(); i++)
        if (names[i] == name) return (int)i;
    names.push_back(name);
    ev.emplace_back();
    return (int)names.size() - 1;
}

// ---------- 코드 ----------
void Song::add_chords(int bar0, const std::vector<std::vector<std::array<int, 3>>> &bars, int color, bool minor_target_b9) {
    struct F { double t; int r, q; };
    std::vector<F> flat;
    for (size_t bi = 0; bi < bars.size(); bi++)
        for (auto &x : bars[bi]) flat.push_back({(double)(bar0 + (int)bi) * ts + x[0], x[1], x[2]});
    const double end_all = (double)(bar0 + (int)bars.size()) * ts;
    for (size_t i = 0; i < flat.size(); i++) {
        const F &f = flat[i];
        double end = i + 1 < flat.size() ? flat[i + 1].t : end_all;
        int nq = i + 1 < flat.size() ? flat[i + 1].q : -1;
        int nr = i + 1 < flat.size() ? flat[i + 1].r : 0;
        int name = COLOR[f.q][color];
        if (f.q == QA_MAJ && nq >= 0 && pmod(nr - f.r, 12) == 5 && pmod(f.r - key.pc, 12) == 7)
            name = color == 0 ? Q_7 : Q_9;                                         // V 자리 장3화음 → 딸림7
        if (f.q == QA_DOM && minor_target_b9 && (nq == QA_MIN || nq == QA_M7 || nq == QA_HDIM) && pmod(nr - f.r, 12) == 5 &&
            rng.random() < b9_rate)
            name = Q_7B9;
        if ((f.q == QA_MIN || f.q == QA_M7) && color >= 1 && rng.random() < .15 && nq >= 0)
            name = color == 2 ? Q_M9 : Q_M7;
        spans.push_back({f.t, end, Chord(f.r, name)});
    }
}

const Span &Song::span(double t) const {
    // 이분 찾기: a - 1e-6 <= t < b - 1e-6
    size_t lo = 0, hi = spans.size();
    while (lo < hi) {
        size_t mid = (lo + hi) / 2;
        if (spans[mid].b - 1e-6 <= t) lo = mid + 1; else hi = mid;
    }
    static const Span none{0, 1e9, Chord(0, Q_MAJ)};
    if (spans.empty()) return none;
    return lo < spans.size() ? spans[lo] : spans.back();          // 칸 밖이면 가장 가까운 코드
}

std::vector<Span> Song::spans_in(int b0, int b1) const {
    std::vector<Span> out;
    for (auto &s : spans)
        if ((double)b0 * ts - 1e-6 <= s.a && s.a < (double)b1 * ts - 1e-6) out.push_back(s);
    return out;
}

// ---------- 음 넣기 ----------
Note *Song::add(const std::string &part, double t, double d, int p, double v) {
    int id = part_id(part);
    pool.push_back(Note{t, d, p, (int)std::max(1.0, std::min(127.0, v)), id, cur_sec});
    Note *n = &pool.back();
    ev[id].push_back(n);
    return n;
}

double Song::arc(double t, double base, double amp) const {
    double ph = fmodp(t / ts, 4) / 4;
    return base + amp * std::sin(M_PI * std::min(1.0, ph * 1.25)) - 2;
}

// ---------- 선율 ----------
void Song::lead(const std::string &part, const std::vector<BN> &notes, double base, double legato) {
    lead_parts.insert(part_id(part));
    for (auto &n : notes) {
        Note *x = add(part, n.t, n.d * legato, n.p, arc(n.t, base) + (n.d >= 1 ? 3 : 0) + rng.randint(-2, 2));
        mel.push_back(x);
    }
}

std::vector<int> Song::block_under(int m, const Chord &c, int n, int lo) const {
    std::vector<int> pcs, all = rootless(c);
    for (int t : c.tones()) all.push_back(t);
    for (int x : all)
        if (!has(pcs, x) && x != pmod(m, 12) && x != pmod(m - 1, 12)) pcs.push_back(x);
    if ((c.q == Q_MAJ7 || c.q == Q_MAJ9 || c.q == Q_6 || c.q == Q_69 || c.q == Q_MAJ) && pmod(m, 12) == c.root)
        pcs.erase(std::remove(pcs.begin(), pcs.end(), (c.root + 11) % 12), pcs.end());
    std::vector<int> cand;
    for (int pc : pcs) { int k = pmod(m - pc, 12); cand.push_back(m - (k ? k : 12)); }
    std::sort(cand.begin(), cand.end()); cand.erase(std::unique(cand.begin(), cand.end()), cand.end());
    std::reverse(cand.begin(), cand.end());
    std::vector<int> below;
    for (int p : cand) {
        bool ok = (int)below.size() < n;
        for (int q : below) ok = ok && std::abs(p - q) > 1;
        if (ok) below.push_back(p);
    }
    if (below.size() >= 3 && below[0] - 12 >= lo) { int f = below[0]; below.erase(below.begin()); below.push_back(f - 12); }
    std::vector<int> out;
    for (int p : below) if (p >= lo - 2) out.push_back(p);
    return out;
}

void Song::piano_melody(const std::vector<BN> &notes, double base, const std::string &mode, const std::string &part) {
    lead_parts.insert(part_id(part));
    for (auto &nn : notes) {
        double t = nn.t, d = nn.d; int m = nn.p;
        const Span &sp = span(t);
        Chord c = sp.c; double a = sp.a, b = sp.b;
        double v = arc(t, base) + (d >= 1 ? 3 : 0) + rng.randint(-2, 2);
        Note *top = add(part, t, d, m, v);
        mel.push_back(top);
        if (mode == "octave" && d >= .5) follow.push_back({add(part, t, d, m - 12, v - 12), top, -12});
        bool strong = d >= 1 || std::fabs(t - a) < 1e-6 || std::fabs(fmodp(t, ts) - ts / 2.0) < 1e-6;
        if (mode == "line") strong = std::fabs(t - a) < 1e-6 && d >= 1;
        if (strong && (mode == "block" || mode == "octave" || mode == "line")) {
            auto hs = block_under(m, c, mode != "block" ? 2 : 3, mode == "block" ? 52 : 55);
            for (int h : hs)
                if (mode != "octave" || (m - 12 < h && h < m)) follow.push_back({add(part, t + .02, d, h, v - 17), top, -17});
            if (t + d > b + 1e-6 && mode != "line") {
                Chord c2 = chord(b);
                for (int h : block_under(m, c2, mode == "octave" ? 2 : 3, 52))
                    if (mode != "octave" || (m - 12 < h && h < m)) follow.push_back({add(part, b + .02, t + d - b, h, v - 19), top, -19});
            }
        } else if ((mode == "block" || mode == "dyad") && d >= .5 && rng.random() < (mode == "block" ? .35 : .7)) {
            for (int k : {3, 4, 8, 9})
                if (c.has_tone(m - k) || c.has_tension(m - k)) { follow.push_back({add(part, t, d, m - k, v - 18), top, -18}); break; }
        }
    }
}

// ---------- 피아노 왼손 / 반주 ----------
void Song::lh_guide(int b0, int b1, double base, bool shell, const std::string &part) {
    std::vector<int> prev; bool hp = false;
    int k = 0;
    for (auto &s : spans_in(b0, b1)) {
        std::vector<int> v;
        if (shell) { int r = fit(s.c.root, 36, 47); v = {r, fit(guide(s.c)[k % 2], r + 7, r + 16)}; }
        else v = stack(guide(s.c), 46, 62, hp ? &prev : nullptr);
        prev = v; hp = true;
        double vel = base + rng.randint(-3, 3);
        for (int p : v) add(part, s.a, s.b - s.a, p, vel);
        if (s.b - s.a >= 4 && rng.random() < .35 && !shell)
            for (int p : v) add(part, s.a + 2.5, s.b - s.a - 2.5, p, vel - 8);
        k++;
    }
}

void Song::pedals(int b0, int b1, int every) {
    for (auto &s : spans_in(b0, b1)) {
        std::vector<double> cuts{s.a};
        for (int x = (int)s.a + every; x < (int)s.b; x += every) if (x > s.a) cuts.push_back(x);
        cuts.push_back(s.b);
        for (size_t i = 0; i + 1 < cuts.size(); i++) pedal.push_back({cuts[i] + .04, cuts[i + 1] - .03});
    }
}

struct Hit { double on, d; };
using Pat = std::vector<Hit>;
static const std::map<std::string, std::pair<std::vector<Pat>, std::vector<Pat>>> &COMP() {
    static const std::map<std::string, std::pair<std::vector<Pat>, std::vector<Pat>>> m = {
        {"ballad", {{{{0, 3.5}}, {{0, 1.5}, {2.5, 1.5}}, {{-.5, 2.5}}, {{0, .5}, {1.5, 2.5}}, {{1, 2.5}}},
                    {{{0, 2}, {2, 2}}, {{0, 1.5}, {1.5, 2.5}}, {{-.5, 2}, {2, 2}}}}},
        {"swing", {{{{0, .4}, {1.5, 1.2}}, {{-.5, .9}, {2, .4}}, {{1.5, .4}, {3.5, .9}}, {{0, 1.4}}, {{1, .4}, {2.5, .4}},
                    {{-.5, 1.2}}, {{.5, .4}, {3, .9}}, {{0, .4}, {2.5, 1.2}}},
                   {{{0, .4}, {2, .4}}, {{-.5, .9}, {1.5, .9}}, {{0, 1.4}, {2, 1.4}}, {{.5, .4}, {2.5, .9}}}}},
        {"bossa", {{{{0, .9}, {1.5, .45}, {2.5, .9}}, {{.5, .45}, {1.5, .9}, {3, .45}}}, {{{0, .9}, {1.5, .45}, {2, .9}, {3.5, .45}}}}},
        {"straight", {{{{0, .45}, {1.5, .45}, {3, .9}}, {{0, 1.4}, {2.5, .45}}, {{.5, .45}, {2, .9}, {3.5, .45}}},
                      {{{0, .9}, {2, .9}}, {{0, .45}, {1.5, .45}, {2, .9}}}}},
        {"waltz", {{{{1, .9}, {2, .9}}, {{0, 2.8}}, {{1, .9}, {2.5, .45}}}, {{{0, 1.4}, {1.5, 1.4}}}}},
    };
    return m;
}

// 화음 안에서 반음으로 붙은 두 음 풀기 (재즈 보이싱의 '까슬한' 맛 — 순한 분위기에선 뺌)
void Song::smooth_voicing(std::vector<int> &v, const Chord &c) const {
    if (crunch >= .5 || v.size() < 2) return;
    std::sort(v.begin(), v.end());
    for (size_t i = 0; i + 1 < v.size(); i++) {
        if (v[i + 1] - v[i] != 1) continue;
        const int lo_iv = pmod(v[i] - c.root, 12);
        int repl = v[i] - 2;                                                       // 아랫음을 온음 내림: 13→5 · 9→근음 · 장7→6
        if (!(lo_iv == 9 || lo_iv == 2 || lo_iv == 11 || lo_iv == 1)) repl = -1;     // 그 밖의 꼴은 아랫음을 뺌
        if (repl >= 0 && (i == 0 || repl - v[i - 1] > 1)) v[i] = repl;
        else { v.erase(v.begin() + i); if (i) i--; }
    }
}

void Song::comp(const std::vector<int> &bars, const std::string &feel, double base, const std::string &voicing, int lo, int hi,
                const std::vector<BN> &avoid, const std::string &p_hi, const std::string &p_lo) {
    std::vector<int> prev; bool hp = false;
    const Pat *last = nullptr;
    std::vector<Note *> ring;
    auto &pp = COMP().at(feel);
    for (int bar : bars) {
        double t0 = (double)bar * ts;
        int cnt = 0;
        for (auto &s : spans) if (t0 - 1e-6 <= s.a && s.a < t0 + ts - 1e-6) cnt++;
        const auto &src = cnt > 1 ? pp.second : pp.first;
        std::vector<const Pat *> pats;
        for (auto &p : src) if (&p != last) pats.push_back(&p);
        if (pats.empty()) for (auto &p : src) pats.push_back(&p);
        if (!has(bars, bar - 1)) {
            std::vector<const Pat *> q;
            for (auto *p : pats) if ((*p)[0].on >= 0) q.push_back(p);
            if (!q.empty()) pats = q;
        }
        const Pat *pat = pats[rng.index(pats.size())];
        last = pat;
        for (size_t k = 0; k < pat->size(); k++) {
            double on = (*pat)[k].on, d = (*pat)[k].d, t = t0 + on;
            if (t >= spans.back().b - 1e-6) continue;
            bool off = on < 0 || frac1(on) != 0;
            Chord c = chord(off ? t + .5 : t);
            std::vector<int> pcs = voicing == "quartal" ? quartal(c) : rootless(c);
            std::vector<int> ov;
            for (auto &a : avoid) if (a.t < t + d && a.t + a.d > t) ov.push_back(a.p);
            int h2 = ov.empty() ? hi : std::min(hi, *std::min_element(ov.begin(), ov.end()) - 3);
            int l2 = std::min(lo, h2 - 12);
            if ((!ov.empty() && h2 - l2 < 9) || l2 < 40) { pcs = guide(c); l2 = std::max(40, h2 - 12); }
            std::vector<int> v = stack(pcs, std::max(40, l2), std::max(l2 + 5, h2), hp ? &prev : nullptr);
            if (v.size() > 1 && v[1] - v[0] == 1 && v[0] < 60) { int f = v[0]; v.erase(v.begin()); v.push_back(f + 12); std::sort(v.begin(), v.end()); }
            if (v.size() > 2 && v[v.size() - 1] - v[v.size() - 2] == 1 && v.back() - 12 >= 40) { int f = v.back(); v.pop_back(); v.push_back(f - 12); std::sort(v.begin(), v.end()); }
            smooth_voicing(v, c);
            prev = v; hp = true;
            for (Note *n : ring) if (n->t + n->d > t - .03) n->d = std::max(.1, t - .03 - n->t);
            std::vector<int> keep;
            for (int q : v) {
                bool bad = false;
                for (int p : ov) bad = bad || pmod(p - q, 12) == 1 || q - p == 1 || q - p == 13;
                if (!bad) keep.push_back(q);
            }
            double acc = (off ? 8 : 0) + (d <= .5 ? 4 : -3) + (k == 0 ? 3 : 0) + rng.randint(-5, 5);
            if (rng.random() < .12) acc += 10;                                          // 가끔 세게 찌르기
            int top_p = keep.empty() ? 0 : *std::max_element(keep.begin(), keep.end());
            ring.clear();
            for (int p : keep)
                ring.push_back(add(p >= 60 ? p_hi : p_lo, t + .01 * rng.random(), d, p, base + acc + (p == top_p ? 4 : -2)));
        }
    }
}

void Song::guitar_comp(const std::vector<int> &bars, const std::string &part, const std::string &feel, double base) {
    std::vector<int> prev; bool hp = false;
    for (int bar : bars) {
        double t0 = (double)bar * ts;
        Chord c = chord(t0);
        std::vector<int> pcs = c.tones();
        if (pcs.size() < 4) pcs.push_back((c.root + 2) % 12);
        std::vector<int> x3;
        for (int x : pcs) if (x != c.root && x3.size() < 3) x3.push_back(x);
        x3.push_back(c.root);
        std::vector<int> v = stack(x3, 52, 70, hp ? &prev : nullptr);
        smooth_voicing(v, c);
        prev = v; hp = true;
        if (feel == "bossa") {
            add(part, t0, .9, fit(c.root, 40, 52), base + 6);
            Chord c3 = chord(t0 + 2);
            bool same = &span(t0 + 2) == &span(t0);
            add(part, t0 + 2, .9, same ? fit(c3.root + 7, 40, 52) : fit(c3.root, 40, 52), base);
            std::vector<double> ons = bar % 2 == 0 ? std::vector<double>{0, 1.5, 2.5, 3.5} : std::vector<double>{.5, 1.5, 2.5, 3};
            for (double on : ons) {
                const Span &s2 = span(t0 + on);
                std::vector<int> vv = v;
                if (&s2 != &span(t0)) {
                    auto r = rootless(s2.c); r.resize(std::min<size_t>(3, r.size())); r.push_back(s2.c.root);
                    vv = stack(r, 52, 70, &v);
                    smooth_voicing(vv, s2.c);
                }
                for (size_t k = 0; k < vv.size(); k++) add(part, t0 + on + k * .012, .45, vv[k], base - 4 + rng.randint(-5, 5));
            }
        } else {
            for (int on = 0; on < ts; on++) {
                Chord c2 = chord(t0 + on);
                auto g = guide(c2); g.push_back(c2.root);
                auto vv = stack(g, 48, 64, &v);
                smooth_voicing(vv, c2);
                for (int p : vv) add(part, t0 + on, .45, p, base - (on % 2 ? 0 : 4) + rng.randint(-4, 4));
            }
        }
    }
}

void Song::piano_pattern(int b0, int b1, const std::string &kind, double base, const std::string &part) {
    for (auto &s : spans_in(b0, b1)) {
        const Chord &c = s.c;
        int r = fit(c.root, 36, 47), third = c.iv(3), fifth = (c.root + 7) % 12;
        auto rl = rootless(c); rl.resize(std::min<size_t>(3, rl.size()));
        auto upper = stack(rl, 52, 64);
        double t = s.a; int k = 0;
        while (t < s.b - 1e-6) {
            if (kind == "arp") {
                if (k == 0 && rng.random() < .22) arp_fig = rng.randint(0, 3);     // 펼침 꼴을 가끔 바꿈
                const int f5 = fit(fifth, r + 5, r + 9), t10 = fit(third >= 0 ? third : fifth, r + 14, r + 17);
                const int FIG[4][4] = {{r, f5, t10, f5}, {r, f5, r + 12, t10}, {r, t10, f5, t10}, {r, f5, t10, r + 12}};
                int p = FIG[arp_fig][k % 4];
                if (k % 8 == 6) p = fit(guide(c)[1], r + 9, r + 13);
                add(part, t, .5 * 2.2, p, base + (k % 4 == 0 ? 6 : 0) + rng.randint(-3, 3));
                t += .5;
            } else if (kind == "alberti") {
                const int rr = fit(c.root, 43, 54);
                const int th = fit(third >= 0 ? third : fifth, rr + 2, rr + 5), fi = fit(fifth, rr + 6, rr + 9);
                const int FIG[4] = {rr, fi, th, fi};
                add(part, t, .5, k == 0 ? rr : FIG[k % 4], base + (k % 4 == 0 ? 5 : k % 2 == 0 ? 1 : -3) + rng.randint(-2, 2));
                t += .5;
            } else if (kind == "waltz") {
                double on = std::round((t - std::floor(t / ts) * ts) * 1000) / 1000;
                if (on == 0) add(part, t, .95, ((int)std::floor(t / ts) % 2 == 0) ? r : fit(fifth, 36, 47), base + 6);
                else for (int p : upper) add(part, t, .6, p, base - 6 + rng.randint(-3, 3));
                t += 1;
            } else {                                                                   // stride
                double on = std::round(fmodp(t, ts) * 1000) / 1000;
                if (on == 0 || on == 2) add(part, t, .9, on == 0 ? r : fit(fifth, 36, 47), base + 6);
                else for (int p : upper) add(part, t, .8, p, base - 4 + rng.randint(-3, 3));
                t += 1;
            }
            k++;
        }
    }
}

// ---------- 베이스 ----------
void Song::bass(int b0, int b1, const std::string &style, double base, const std::string &part, int lo, int hi) {
    int &p = walk_p;
    auto absd = [](int a) { return (double)std::abs(a); };
    if (style == "walk") {
        for (int beat = b0 * ts; beat < b1 * ts; beat++) {
            const Span &sp = span(beat);
            const Chord &c = sp.c;
            int q;
            if (std::fabs(beat - sp.a) < 1e-6) {
                double r0 = rng.random();
                int pc = (r0 < .85 || sp.b - sp.a < 4) ? c.root : c.iv(3);
                const int pp = p;
                q = pick_min(lo, hi + 1, [&](int x) { return pmod(x, 12) == pc; }, [&](int x) { return absd(x - pp) + (x == pp ? 3 : 0); }, fit(pc, lo, hi));
            } else if (beat + 1 >= sp.b - 1e-6) {
                int nrr = chord(sp.b).root; const int pp = p;
                int nr = pick_min(lo, hi + 1, [&](int x) { return pmod(x, 12) == nrr; }, [&](int x) { return absd(x - pp); }, fit(nrr, lo, hi));
                int opts[3] = {nr + 1, nr - 1, nr + 7 <= hi ? nr + 7 : nr - 5};
                q = opts[rng.weighted({3, 3, 2})];
                if (q == p) q = opts[0] == p ? opts[1] : opts[0];
            } else {
                int nrr = chord(sp.b).root; const int pp = p;
                int nr = pick_min(lo, hi + 1, [&](int x) { return pmod(x, 12) == nrr; }, [&](int x) { return absd(x - pp); }, fit(nrr, lo, hi));
                int way = nr > p ? 1 : -1;
                auto scl = c.scale(&key);
                std::vector<int> sc, ct;
                for (int x = lo; x <= hi; x++) if (has(scl, pmod(x, 12))) sc.push_back(x);
                for (int x : sc) if (c.has_tone(x)) ct.push_back(x);
                bool use_ct = rng.random() < .6;
                std::vector<int> pool;
                for (int x : use_ct ? ct : sc) if (1 <= (x - p) * way && (x - p) * way <= 4) pool.push_back(x);
                if (!pool.empty()) q = rng.choice(pool);
                else {
                    q = sc.empty() ? p : sc[0]; double bc = 1e9;
                    for (int x : sc) if (std::abs(x - (p + way * 2)) < bc) { bc = std::abs(x - (p + way * 2)); q = x; }
                }
            }
            q = fit(q, lo, hi);
            add(part, beat, .92, q, base + (beat % 2 ? 5 : 0) + rng.randint(-5, 4));
            p = q;
        }
        return;
    }
    for (int bar = b0; bar < b1; bar++) {
        double t0 = (double)bar * ts;
        if (style == "two" || style == "ballad") {
            std::vector<int> halves = ts == 4 ? std::vector<int>{0, 2} : std::vector<int>{0};
            for (int h : halves) {
                double t = t0 + h;
                const Span &sp = span(t);
                const Chord &c = sp.c;
                int q; const int pp = p;
                if (std::fabs(t - sp.a) < 1e-6 || style == "ballad")
                    q = pick_min(lo + 1, hi - 1, [&](int x) { return pmod(x, 12) == c.root; }, [&](int x) { return absd(x - pp); }, fit(c.root, lo, hi));
                else {
                    int f = (c.root + 7) % 12, t3 = c.iv(3);
                    q = pick_min(lo + 1, hi - 1, [&](int x) { return pmod(x, 12) == f || pmod(x, 12) == t3; },
                                 [&](int x) { return absd(x - pp) + (pmod(x, 12) == f ? 0 : 2); }, fit(f, lo, hi));
                }
                int L = ts == 4 ? 2 : 3;
                if (style == "two" && rng.random() < .3) {
                    int nr = chord(t + L).root;
                    int tgt = pick_min(lo, hi + 1, [&](int x) { return pmod(x, 12) == nr; }, [&](int x) { return absd(x - q); }, fit(nr, lo, hi));
                    add(part, t, L - .55, q, base + rng.randint(-4, 4));
                    add(part, t + L - .5, .45, tgt + (rng.random() < .5 ? -1 : 1), base - 8);
                } else add(part, t, L - .1, q, base + rng.randint(-4, 4));
                p = q;
            }
        } else if (style == "bossa") {
            const Span &s0 = span(t0), &s2 = span(t0 + 2);
            const Chord &c = s0.c, &c3 = s2.c;
            const int pp = p;
            int r = pick_min(31, 47, [&](int x) { return pmod(x, 12) == c.root; }, [&](int x) { return absd(x - pp); }, fit(c.root, 31, 46));
            int fpc = &s0 == &s2 ? (c3.root + 7) % 12 : c3.root;
            int f = pick_min(31, 50, [&](int x) { return pmod(x, 12) == fpc; }, [&](int x) { return absd(x - r); }, fit(fpc, 31, 49));
            const double hits[4][4] = {{0, 1.4, 0, 0}, {1.5, .45, 0, -12}, {2, 1.4, 1, -4}, {3.5, .45, 1, -14}};
            for (auto &h : hits) add(part, t0 + h[0], h[1], h[2] ? f : r, base + h[3] + rng.randint(-3, 3));
            p = r;
        } else if (style == "straight") {
            const Span &s0 = span(t0);
            const Chord &c = s0.c; const int pp = p;
            int r = pick_min(31, 47, [&](int x) { return pmod(x, 12) == c.root; }, [&](int x) { return absd(x - pp); }, fit(c.root, 31, 46));
            static const std::vector<std::vector<std::array<double, 3>>> PATS = {
                {{0, .75, 0}, {.75, .25, 0}, {1.5, .5, 12}, {2, 1, 7}, {3, .5, 10}, {3.5, .5, -1}},
                {{0, 1.5, 0}, {1.5, .5, 0}, {2, .5, 7}, {2.5, .5, 12}, {3, 1, 10}},
                {{0, .5, 0}, {.5, .5, 12}, {1, 1, 0}, {2, .75, 7}, {2.75, .25, 7}, {3.5, .5, 5}}};
            const auto &pat = PATS[rng.index(3)];
            for (auto &h : pat) {
                const Span &sc = span(t0 + h[0]);
                int q = &sc == &s0 ? r + (int)h[2]
                                   : pick_min(31, 47, [&](int x) { return pmod(x, 12) == sc.c.root; }, [&](int x) { return absd(x - r); }, fit(sc.c.root, 31, 46));
                add(part, t0 + h[0], h[1] * .95, q, base - (frac1(h[0]) ? 6 : 0) + rng.randint(-4, 3));
            }
            p = r;
        } else if (style == "waltz") {
            const Chord &c = chord(t0); const int pp = p;
            int q = pick_min(lo + 1, hi - 1, [&](int x) { return pmod(x, 12) == c.root; }, [&](int x) { return absd(x - pp); }, fit(c.root, lo, hi));
            add(part, t0, 1.9, q, base + rng.randint(-3, 3));
            p = q;
        }
    }
}

// ---------- 드럼 ----------
void Song::drums(int b0, int b1, const std::string &kind, int lvl, int fill_every, bool crash) {
    const std::string part = contains(kind, "brush") ? "브러시" : "드럼";
    Rng &R = rng;
    const double a = swing ? swing : 2.0 / 3;
    // 큰 물결에 따라 세기층 ±1 · 4마디 숨은 위상을 섞고 · 필인/크래시는 정해진 마디마다가 아니라 확률로 (되풀이 느낌 줄이기)
    lvl = std::max(0, std::min(2, lvl + (energy > .68 ? 1 : energy < .28 ? -1 : 0)));
    const int ph = R.randint(0, 3);
    for (int bar = b0; bar < b1; bar++) {
        double t0 = (double)bar * ts;
        bool fill = (bar - b0) % fill_every == fill_every - 1;
        if (fill_every == 8) fill = bar == b1 - 1 ? R.random() < .72 : (bar - b0 == 3 ? R.random() < .15 + .15 * energy : false);
        double sw = 4 * std::sin(M_PI * (((bar - b0 + ph) % 4) + .5) / 4) - 2;
        if (kind == "brush") {
            for (int h : (ts == 4 ? std::vector<int>{0, 2} : std::vector<int>{0}))
                add(part, t0 + h, ts == 4 ? 2 : 3, 40, 32 + lvl * 4 + sw + R.randint(-3, 3));
            for (int on : (ts == 4 ? std::vector<int>{1, 3} : std::vector<int>{1, 2})) {
                double acc = R.random() < .15 ? 10 : 0;
                add(part, t0 + on, .2, 38, 40 + lvl * 4 + sw + acc + R.randint(-5, 5));
                add(part, t0 + on, .2, 44, 26 + R.randint(-3, 3));
            }
            if (ts == 4) {
                for (double on : {1 + a, 3 + a})
                    if (R.random() < (.25 + .3 * lvl)) add(part, t0 + on, .15, 38, 20 + lvl * 3 + R.randint(-3, 4));
                if (R.random() < .2) add(part, t0 + (R.random() < .5 ? a : 2 + a), .15, 38, 18 + R.randint(0, 6));
            }
        } else if (kind == "brush_swing") {
            add(part, t0, 2, 40, 28 + sw); add(part, t0 + 2, 2, 40, 26 + sw);
            for (double on : {0.0, 1.0, 1 + a, 2.0, 3.0, 3 + a}) {
                double v = 44 + lvl * 2 + sw + ((on == 1 || on == 3) ? 10 : (frac1(on) ? -12 : -2)) + R.randint(-5, 5);
                add(part, t0 + on, .2, 38, v);
            }
            for (int on : {1, 3}) add(part, t0 + on, .2, 44, 28 + R.randint(-3, 3));
            if (R.random() < .2) add(part, t0 + (R.random() < .5 ? a : 2 + a), .2, 39, 50 + R.randint(0, 10));
        } else if (kind == "ride") {
            for (double on : {0.0, 1.0, 1 + a, 2.0, 3.0, 3 + a}) {
                if (frac1(on) && R.random() < .1) continue;
                double v = 56 + lvl * 3 + sw + ((on == 1 || on == 3) ? 10 : (frac1(on) ? -12 : 0)) + R.randint(-5, 5);
                add(part, t0 + on, .3, 51, v);
            }
            for (int on : {1, 3}) add(part, t0 + on, .2, 44, 48 + R.randint(-4, 4));
            if (!fill) {
                for (int x = 0; x < 4; x++) {
                    double r = R.random();
                    if (r < .22) add(part, t0 + x + a, .2, 38, 22 + R.randint(0, 12));
                    else if (r < .27) add(part, t0 + x + a, .2, 38, 62 + lvl * 4 + R.randint(0, 10));
                }
                for (int on = 0; on < 4; on++) if (R.random() < .5) add(part, t0 + on, .2, 36, 24 + R.randint(-3, 4));
                if (R.random() < .12) add(part, t0 + (R.random() < .5 ? 2 + a : 3 + a), .2, 36, 58 + R.randint(0, 10));
            }
        } else if (kind == "bossa") {
            for (double on : (bar % 2 == 0 ? std::vector<double>{0, 1.5, 3} : std::vector<double>{1, 2.5}))
                add(part, t0 + on, .2, 37, 52 + sw + R.randint(-6, 6));
            for (double on : {0.0, 1.5, 2.0, 3.5}) add(part, t0 + on, .2, 36, 42 + ((on == 0 || on == 2) ? 6 : -4) + R.randint(-4, 4));
            for (int k = 0; k < 8; k++) add(part, t0 + k * .5, .2, 42, 34 + (k % 2 == 0 ? 10 : 0) + sw + R.randint(-6, 6));
        } else if (kind == "straight") {
            for (int k = 0; k < 8; k++)
                add(part, t0 + k * .5, .2, 42, 44 + (k % 2 == 0 ? 12 : 0) + ((k == 2 || k == 6) ? 6 : 0) + lvl * 3 + sw + R.randint(-6, 6));
            std::vector<double> kicks = R.random() < .6 ? std::vector<double>{0, 2.5} : std::vector<double>{0, 1.5, 2.5};
            for (double on : kicks) add(part, t0 + on, .2, 36, 60 + (on == 0 ? 6 : 0) + lvl * 3 + R.randint(-5, 4));
            for (int on : {1, 3}) add(part, t0 + on, .2, lvl == 0 ? 37 : 38, 58 + lvl * 4 + sw + R.randint(-5, 5));
            for (double on : {1.75, 3.25, 3.75})
                if (R.random() < .25 && lvl >= 1) add(part, t0 + on, .15, 38, 24 + R.randint(0, 10));
            if (bar % 2 == 1) add(part, t0 + 3.5, .4, 46, 46 + R.randint(-4, 6));
        } else if (kind == "waltz_brush") {
            add(part, t0, 3, 40, 28 + lvl * 3 + sw + R.randint(-3, 3));
            for (int on : {1, 2}) add(part, t0 + on, .2, 38, 26 + lvl * 3 + (on == 1 ? 3 : 0) + R.randint(-3, 3));
        }
        if (fill && (kind == "brush" || kind == "brush_swing" || kind == "waltz_brush")) {
            for (int k = 0; k < 3; k++) add(part, t0 + ts - 1 + k / 3.0, .15, 38, 34 + lvl * 4 + 8 * k);
        } else if (fill && (kind == "ride" || kind == "straight" || kind == "bossa")) {
            const double ons_r[4] = {2 + 2 / 3.0, 3, 3 + 1 / 3.0, 3 + 2 / 3.0}, ons_s[4] = {3, 3.25, 3.5, 3.75};
            const int notes[4] = {38, 38, 47, 43};
            for (int k = 0; k < 4; k++) add(part, t0 + (kind == "ride" ? ons_r[k] : ons_s[k]), .2, notes[k], 48 + lvl * 4 + 9 * k);
        }
        if (crash && (kind == "ride" || kind == "straight") &&
            ((bar == b0 && R.random() < .4 + .45 * energy) || (bar - b0 == 4 && R.random() < .1 + .15 * energy))) {
            add(part, t0, 1.5, 49, 62 + lvl * 3);
            add(part, t0, .2, 36, 62 + lvl * 3);
        }
    }
}

// ---------- 현악 ----------
void Song::strings_pad(int b0, int b1, const std::string &part, double base, int lo, int hi) {
    std::vector<int> prev; bool hp = false;
    for (auto &s : spans_in(b0, b1)) {
        auto g = guide(s.c); g.push_back((s.c.root + 7) % 12);
        auto v = stack(g, lo, hi, hp ? &prev : nullptr);
        prev = v; hp = true;
        for (int p : v) add(part, s.a, s.b - s.a + .1, p, base + rng.randint(-3, 3));
    }
}

void Song::guide_line(int b0, int b1, const std::string &part, double base, int lo, int hi) {
    int p = -1;
    for (auto &s : spans_in(b0, b1)) {
        auto g = guide(s.c);
        const int pp = p;
        int q = pick_min(lo, hi + 1, [&](int x) { return has(g, pmod(x, 12)); },
                         [&](int x) { return (pp >= 0 ? std::abs(x - pp) : std::abs(x - (lo + hi) / 2)) + (x == pp ? 1.5 : 0); }, fit(g[0], lo, hi));
        add(part + " 대선율", s.a, s.b - s.a, q, base + rng.randint(-2, 2));
        p = q;
    }
}

// ---------- 다듬기 ----------
std::vector<BN> Song::fix_avoid(const std::vector<BN> &notes, bool jazz) const {
    std::vector<BN> xs = notes, out;
    std::sort(xs.begin(), xs.end(), [](const BN &a, const BN &b) { return a.t < b.t || (a.t == b.t && (a.d < b.d || (a.d == b.d && a.p < b.p))); });
    for (size_t i = 0; i < xs.size(); i++) {
        double t = xs[i].t, d = xs[i].d; int p = xs[i].p;
        const Chord &c = chord(t);
        auto ct = c.tones();
        std::vector<int> ten = jazz ? c.tensions() : (!c.is_dom() ? std::vector<int>{(c.root + 2) % 12} : std::vector<int>{});
        std::vector<int> ok = ct; ok.insert(ok.end(), ten.begin(), ten.end());
        bool beat = std::fabs(t - std::round(t)) < 1e-6;
        bool strong = beat && ((long)std::round(t) % (ts == 4 ? 2 : 3) == 0);
        bool leapy = i > 0 && i + 1 < xs.size() && std::abs(p - xs[i - 1].p) > 2 && std::abs(xs[i + 1].p - p) > 2;
        const bool phrase_end = i + 1 == xs.size() || xs[i + 1].t - (t + d) >= 1.0 - 1e-6;      // 뒤에 한 박 넘게 쉼 = 프레이즈 끝음
        std::vector<int> need;
        if (d < 1.5) need = ok;
        else { need = ct; if (!c.is_dom()) need.push_back((c.root + 2) % 12); else need.insert(need.end(), ten.begin(), ten.end()); }
        if (!has(need, pmod(p, 12)) && (strong || d >= .75 || leapy || phrase_end)) {
            const std::vector<int> &pool = (d >= 1 || !jazz) ? ct : need;
            for (int k : {-1, 1, -2, 2, -3, 3})
                if (has(pool, pmod(p + k, 12))) { p += k; break; }
        }
        const Span &sp = span(t);
        if (t + d > sp.b + .1) {
            const Chord &c2 = chord(sp.b);
            if (!(c2.has_tone(p) || (jazz && c2.has_tension(p)))) d = sp.b - t;
        }
        out.push_back({t, d, p});
    }
    return out;
}

void Song::phrase_dynamics(bool jazz) {
    Rng &R = rng;
    std::map<int, std::vector<Note *>> by;
    std::vector<int> order;
    for (Note *n : mel)
        if (n->sec == cur_sec && !n->dead) { if (!by.count(n->part)) order.push_back(n->part); by[n->part].push_back(n); }
    for (int part : order) {
        auto &ns = by[part];
        std::stable_sort(ns.begin(), ns.end(), [](Note *a, Note *b) { return a->t < b->t; });
        std::vector<std::vector<Note *>> phrases{{ns[0]}};
        for (size_t i = 1; i < ns.size(); i++) {
            if (ns[i]->t - (ns[i - 1]->t + ns[i - 1]->d) >= .9) phrases.emplace_back();
            phrases.back().push_back(ns[i]);
        }
        for (auto &ph : phrases) {
            double mean = 0; int pk = 0;
            for (size_t i = 0; i < ph.size(); i++) { mean += ph[i]->p; if (ph[i]->p > ph[pk]->p) pk = (int)i; }
            mean /= ph.size();
            double L = std::max<size_t>(1, ph.size() - 1);
            for (size_t i = 0; i < ph.size(); i++) {
                Note *n = ph[i];
                double v = n->v + (n->p - mean) * 1.1;
                double pos = i / L, pkp = pk / L;
                v += 7 * (1 - std::fabs(pos - pkp) / std::max({pkp, 1 - pkp, .01})) - 3;
                double fr = frac1(n->t);
                if (jazz && n->d <= .6) v += std::fabs(fr - .5) < .05 ? 7 : (fr < .05 ? -3 : 0);
                if (jazz && i > 0 && i + 1 < ph.size() && n->d <= .55 && n->p < ph[i - 1]->p && n->p < ph[i + 1]->p && R.random() < .6) v -= 16;
                if (std::fabs(fr - .5) < .05 && n->d >= .9) v += 8;
                if (i == 0) v += 3;
                if (i + 1 == ph.size() && n->d >= 1) v -= 5;
                n->v = (int)std::max(26.0, std::min(118.0, v + R.randint(-3, 3)));
            }
        }
    }
    for (auto &f : follow)
        if (f.h->sec == cur_sec) f.h->v = (int)std::max(20.0, std::min(110.0, (double)f.top->v + f.dv + R.randint(-2, 2)));
}

void Song::section_dynamics() {
    for (auto &n : pool)
        if (n.sec == cur_sec) n.v = (int)std::max(1.0, std::min(124.0, n.v * sec_factor));
}

static double ovl(const Note *a, const Note *b) { return std::min(a->t + a->d, b->t + b->d) - std::max(a->t, b->t); }

std::pair<int, int> Song::declash(double min_len) {
    std::set<const Note *> mel_ids(mel.begin(), mel.end());
    for (auto &f : follow) mel_ids.insert(f.h);
    std::map<int, std::vector<Note *>> buck;
    std::vector<Note *> solo;
    for (Note *m : mel) {
        if (m->dead) continue;
        if (m->d >= min_len)
            for (int k = (int)std::floor(m->t); k <= (int)std::floor(m->t + m->d); k++) buck[k].push_back(m);
        if (!contains(names[m->part], "피아노")) solo.push_back(m);
    }
    auto near_mels = [&](Note *n) {
        std::vector<Note *> out; std::set<Note *> seen;
        for (int k = (int)std::floor(n->t); k <= (int)std::floor(n->t + n->d); k++)
            for (Note *m : buck[k]) if (seen.insert(m).second) out.push_back(m);
        return out;
    };
    auto clash = [&](int q, Note *n, const std::vector<Note *> &ms) {
        double tot = 0;
        for (Note *m : ms) {
            double ov = ovl(n, m);
            if (ov <= .05 || m->p == q) continue;
            int d = m->p - q;
            if ((d > 0 && d % 12 == 1) || (d < 0 && (-d == 1 || -d == 13)) || (std::abs(d) > 0 && std::abs(d) <= 2)) tot += ov;
        }
        return tot;
    };
    int moved = 0, removed = 0;
    for (size_t pi = 0; pi < ev.size(); pi++) {
        if (is_drum_part((int)pi)) continue;
        bool isbass = contains(names[pi], "베이스");
        std::map<long, std::set<int>> onsets;
        for (Note *n : ev[pi]) if (n->sec == cur_sec && !n->dead) onsets[std::lround(n->t * 100)].insert(n->p);
        for (Note *n : ev[pi]) {
            if (n->sec != cur_sec || n->dead || mel_ids.count(n)) continue;
            auto ms = near_mels(n);
            {
                const Chord &c7 = span(n->t).c;
                if (!isbass && (c7.q == Q_MAJ7 || c7.q == Q_MAJ9 || c7.q == Q_MAJ7S11) && pmod(n->p - c7.root, 12) == 11) {
                    bool hit = false;
                    for (Note *m : ms) hit = hit || (ovl(n, m) > .4 && m->p > n->p && pmod(m->p - c7.root, 12) == 0);
                    for (auto &f : follow) hit = hit || (!f.h->dead && f.h->sec == cur_sec && ovl(n, f.h) > .4 && f.h->p > n->p && pmod(f.h->p - c7.root, 12) == 0);
                    if (hit) { n->p -= 2; moved++; }
                }
            }
            double lim = std::max(.2, .25 * n->d);
            if (!ms.empty() && clash(n->p, n, ms) > lim) {
                const Span &sp = span(n->t);
                if (isbass && std::fabs(n->t - sp.a) < 1e-6) continue;
                std::vector<int> pcs = sp.c.tones();
                if (!isbass) for (int x : sp.c.tensions()) pcs.push_back(x);
                auto &same = onsets[std::lround(n->t * 100)];
                std::vector<int> cands;
                for (int q = n->p - 4; q <= n->p + 4; q++) if (q != n->p && has(pcs, pmod(q, 12)) && !same.count(q)) cands.push_back(q);
                std::stable_sort(cands.begin(), cands.end(), [&](int a, int b) { return std::abs(a - n->p) < std::abs(b - n->p); });
                int best = -1;
                for (int q : cands) if (clash(q, n, ms) <= lim) { best = q; break; }
                if (best >= 0) { same.erase(n->p); same.insert(best); n->p = best; moved++; }
                else if (!isbass) { n->dead = true; removed++; }
                continue;
            }
            if (!lead_parts.count((int)pi) && !isbass) {
                for (Note *m : solo)
                    if (ovl(n, m) > .25 && n->p > m->p + 2 && pmod(n->p - m->p, 12) != 0) { n->dead = true; removed++; break; }
            }
        }
    }
    return {moved, removed};
}

std::pair<int, int> Song::low_mud(int top) {
    std::set<const Note *> mel_ids(mel.begin(), mel.end());
    for (auto &f : follow) mel_ids.insert(f.h);
    std::map<int, std::vector<Note *>> buck;
    std::vector<Note *> allv;
    for (size_t pi = 0; pi < ev.size(); pi++) {
        if (is_drum_part((int)pi)) continue;
        for (Note *n : ev[pi]) {
            if (n->dead) continue;
            for (int k = (int)std::floor(n->t); k <= (int)std::floor(n->t + n->d); k++) buck[k].push_back(n);
            if (n->sec == cur_sec) allv.push_back(n);
        }
    }
    auto around = [&](Note *n) {
        std::vector<Note *> out; std::set<Note *> seen;
        for (int k = (int)std::floor(n->t); k <= (int)std::floor(n->t + n->d); k++)
            for (Note *m : buck[k]) if (m != n && !m->dead && ovl(n, m) > .15 && seen.insert(m).second) out.push_back(m);
        return out;
    };
    auto rub = [](int q, const std::vector<Note *> &o) { for (Note *m : o) if (std::abs(m->p - q) == 1) return true; return false; };
    int moved = 0, dead = 0;
    for (Note *n : allv) {
        if (lead_parts.count(n->part) || contains(names[n->part], "베이스") || mel_ids.count(n) || n->p >= top || n->dead) continue;
        auto others = around(n);
        if (!rub(n->p, others)) continue;
        int mel_lo = 999;
        for (Note *m : mel) if (!m->dead && ovl(n, m) > .05) mel_lo = std::min(mel_lo, m->p);
        int up = n->p + 12;
        bool taken = false;
        for (Note *m : others) taken = taken || m->p == up;
        if (up < mel_lo - 2 && !rub(up, others) && !taken) { n->p = up; moved++; }
        else {
            for (Note *m : ev[n->part])
                if (m != n && !m->dead && std::fabs(m->t - n->t) < 1e-3) { n->dead = true; dead++; break; }
        }
    }
    return {moved, dead};
}

void Song::cut_after(double beat) {
    for (auto &n : pool) {
        if (n.t >= beat - 1e-6) n.dead = true;
        else if (n.t + n.d > beat) n.d = beat - n.t;
    }
    while (!spans.empty() && spans.back().a >= beat - 1e-6) spans.pop_back();
    if (!spans.empty() && spans.back().b > beat) spans.back().b = beat;
    std::vector<std::pair<double, double>> pk;
    for (auto &p : pedal) if (p.first < beat) pk.push_back({p.first, std::min(p.second, beat)});
    pedal = pk;
}
