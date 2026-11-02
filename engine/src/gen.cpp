#include "gen.h"
#include "tokens.h"
#include <algorithm>
#include <cmath>
#include <numeric>

int pick(const std::vector<float> &logits, const std::vector<int> &allowed, double temp, double top_p, Rng &rng) {
    const double T = std::max(temp, 1e-3);
    double mx = -1e30;
    for (int a : allowed) mx = std::max(mx, (double)logits[a] / T);
    std::vector<std::pair<double, int>> p;
    double sum = 0;
    for (int a : allowed) { double e = std::exp(logits[a] / T - mx); p.push_back({e, a}); sum += e; }
    for (auto &x : p) x.first /= sum;
    std::stable_sort(p.begin(), p.end(), [](auto &a, auto &b) { return a.first > b.first; });
    double cs = 0; size_t n = 0;
    while (n < p.size()) { cs += p[n].first; n++; if (cs >= top_p) break; }       // np.searchsorted(cs, top_p) + 1
    double tot = 0;
    for (size_t i = 0; i < n; i++) tot += p[i].first;
    double r = rng.random() * tot;
    for (size_t i = 0; i < n; i++) { r -= p[i].first; if (r < 0) return p[i].second; }
    return p[n - 1].second;
}

std::vector<Bar> progression(const Model &m, const std::vector<std::pair<char, int>> &form, bool minor, const std::string &src, int ts,
                             const std::vector<int> &beats, double temp, double top_p, uint64_t seed,
                             const std::vector<Bar> *prefix, char prefix_sec, const std::map<int, Bar> *fixed) {
    using namespace tk;
    Rng rng(seed);
    Runner r(&m);
    std::vector<int> head{C_BOS, src == "pop" ? C_SRC_pop : src == "song" ? C_SRC_song : C_SRC_jazz, minor ? C_MODE_min : C_MODE_maj,
                          ts == 3 ? C_TS_3 : C_TS_4};
    r.feed(head);
    if (prefix)                                                                   // 앞 단락을 문맥으로
        for (size_t k = 0; k < prefix->size(); k++) {
            std::vector<int> t{C_BAR};
            if (k == 0) t.push_back(C_SEC0 + (prefix_sec - 'A'));
            for (auto &c : (*prefix)[k]) { t.push_back(C_BEAT0 + c[0]); t.push_back(C_DEG0 + c[1]); t.push_back(C_Q0 + c[2]); }
            r.feed(t);
        }
    std::vector<Bar> out;
    int bar_i = prefix ? (int)prefix->size() : 0;
    int out_i = 0;
    std::vector<int> DEG(12), QQ(11);
    for (int i = 0; i < 12; i++) DEG[i] = C_DEG0 + i;
    for (int i = 0; i < 11; i++) QQ[i] = C_Q0 + i;
    for (auto &[sec, n] : form) {
        for (int k = 0; k < n; k++) {
            r.room(40, (int)head.size(), C_BAR);
            std::vector<int> b{C_BAR};
            if (k == 0) b.push_back(C_SEC0 + (sec - 'A'));
            r.feed(b);
            Bar bar;
            int last = -1;
            auto fx = fixed ? fixed->find(out_i) : std::map<int, Bar>::const_iterator();
            if (fixed && fx != fixed->end()) {                                    // 그대로 둘 마디
                for (auto &c : fx->second) { r.feed({C_BEAT0 + c[0], C_DEG0 + c[1], C_Q0 + c[2]}); bar.push_back(c); }
                out.push_back(bar); bar_i++; out_i++;
                continue;
            }
            while (true) {
                std::vector<int> allowed;
                for (int bt : beats) if (last < bt && bt < ts) allowed.push_back(C_BEAT0 + bt);
                if (!bar.empty() || bar_i > 0) allowed.push_back(C_BAR);
                if (bar_i == 0 && bar.empty()) allowed = {C_BEAT0};
                int t = pick(r.logits, allowed, temp, top_p, rng);
                if (t == C_BAR) break;
                int bt = t - C_BEAT0;
                r.feed1(t);
                int d = pick(r.logits, DEG, temp, top_p, rng) - C_DEG0; r.feed1(C_DEG0 + d);
                int q = pick(r.logits, QQ, temp, top_p, rng) - C_Q0; r.feed1(C_Q0 + q);
                bar.push_back({bt, d, q});
                last = bt;
            }
            out.push_back(bar);
            bar_i++; out_i++;
        }
    }
    ChordTok cur{-1, 0, 0};
    for (auto &b : out) {
        if (b.empty() && cur[0] >= 0) b.push_back({0, cur[1], cur[2]});
        if (!b.empty()) cur = b.back();
    }
    return out;
}

MelodyWriter::MelodyWriter(const Model *m, int ts_, const std::string &kind, const std::string &feel, const std::string &tempo, bool minor,
                           int dens, int reg, uint64_t seed)
    : r(m), ts(ts_), rng(seed) {
    using namespace tk;
    head = {M_BOS, kind == "solo" ? M_KIND_solo : M_KIND_head,
            feel == "straight" ? M_FEEL_straight : feel == "latin" ? M_FEEL_latin : M_FEEL_swing,
            tempo == "TEMPO_slow" ? M_TEMPO_slow : tempo == "TEMPO_fast" ? M_TEMPO_fast : M_TEMPO_med,
            ts == 3 ? M_TS_3 : M_TS_4, minor ? M_MODE_min : M_MODE_maj, M_DENS0 + dens, M_REG0 + reg};
    r.feed(head);
}

std::vector<int> MelodyWriter::chord_toks(const Bar &chords, const ChordTok *nxt) const {
    using namespace tk;
    std::vector<int> t{M_BAR};
    for (auto &c : chords) { t.push_back(M_CPOS0 + c[0]); t.push_back(M_CR0 + c[1]); t.push_back(M_CQ0 + c[2]); }
    if (chords.empty()) t.push_back(M_CNONE);
    if (nxt) { t.push_back(M_NR0 + (*nxt)[1]); t.push_back(M_NQ0 + (*nxt)[2]); }
    else t.push_back(M_NNONE);
    return t;
}

std::vector<MelNote> MelodyWriter::bar(const Bar &chords, const ChordTok *nxt, int lo, int hi, double temp, double top_p, int leap,
                                       const std::vector<MelNote> *force, int max_notes, bool rest_ok, bool cont) {
    using namespace tk;
    r.room(80, (int)head.size(), M_BAR);
    r.feed(chord_toks(chords, nxt));
    std::vector<MelNote> notes;
    if (force) {
        for (auto &f : *force) {
            int dd = DUR_SET[DUR_IDX[std::min(f.d, 199)]];
            r.feed({M_POS0 + f.on, M_P0 + std::min(std::max(f.p, P_LO), P_HI) - P_LO, M_D0 + DUR_IDX[std::min(dd, 199)]});
            notes.push_back({f.on, dd, f.p});
            same_run = f.p == prev_p ? same_run + 1 : 1;
            prev_p = f.p;
        }
        if (!cont) { past.push_back(notes); if (past.size() > 96) past.erase(past.begin()); return notes; }
    }
    int last = notes.empty() ? -1 : notes.back().on;
    const int L = ts * TPB;
    std::vector<int> D(NDUR);
    for (int i = 0; i < NDUR; i++) D[i] = M_D0 + i;
    while ((int)notes.size() < max_notes) {
        std::vector<int> allowed;
        for (int p = last + 1; p < L; p++) allowed.push_back(M_POS0 + p);
        if (!notes.empty() || rest_ok) allowed.push_back(M_BAR);
        int t = pick(r.logits, allowed, temp, top_p, rng);
        if (t == M_BAR) break;
        int on = t - M_POS0;
        r.feed1(t);
        std::vector<int> ps;
        for (int p = lo; p <= hi; p++)
            if (prev_p < 0 || std::abs(p - prev_p) <= leap) ps.push_back(M_P0 + p - P_LO);
        if (ps.empty()) for (int p = lo; p <= hi; p++) ps.push_back(M_P0 + p - P_LO);
        if (same_run >= 3 && prev_p >= lo && prev_p <= hi && ps.size() > 1)          // 같은 음 4번 연달아는 안 됨
            ps.erase(std::remove(ps.begin(), ps.end(), M_P0 + prev_p - P_LO), ps.end());
        int pt;
        if (no_copy > 0 && !notes.empty()) {
            // 지금까지 이 마디가 어떤 지난 마디의 앞부분과 (자리 · 음) 똑같으면, 그 마디의 다음 음을 그대로 따라가는 것에 벌점
            std::vector<float> lg = r.logits;
            const size_t n = notes.size();
            for (size_t bi = 0; bi < past.size(); bi++) {
                const auto &b = past[bi];
                const bool just_before = bi + 1 == past.size();                  // 바로 앞 마디를 한 번 되받는 건 자연스러움 → 벌점만
                if (b.size() <= n || b[n].on != on) continue;
                bool same = true;
                for (size_t i = 0; i < n && same; i++) same = b[i].on == notes[i].on && b[i].p == notes[i].p;
                if (same && b[n].p >= P_LO && b[n].p <= P_HI) {                  // 둘째 음은 벌점, 셋째부터는 막음 (두 음까지만 같아도 됨)
                    float &x = lg[M_P0 + b[n].p - P_LO];
                    x = n >= 2 && !just_before ? -1e9f : std::min(x, r.logits[M_P0 + b[n].p - P_LO] - (float)no_copy);
                }
            }
            pt = pick(lg, ps, temp, top_p, rng);
        } else pt = pick(r.logits, ps, temp, top_p, rng);
        int p = P_LO + (pt - M_P0);
        r.feed1(pt);
        int dt = pick(r.logits, D, temp, top_p, rng);
        r.feed1(dt);
        notes.push_back({on, DUR_SET[dt - M_D0], p});
        same_run = p == prev_p ? same_run + 1 : 1;
        prev_p = p;
        last = on;
    }
    if (!notes.empty()) { past.push_back(notes); if (past.size() > 96) past.erase(past.begin()); }
    return notes;
}
