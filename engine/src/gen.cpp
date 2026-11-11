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

uint64_t cell_sig(const Bar &a, const Bar &b) {
    //                       maj maj7 min m7 dom alt sus hdim dim aug mM7
    static const int FAM[11] = {0, 0, 1, 1, 2, 2, 2, 3, 3, 2, 1};
    uint64_t h = 1469598103934665603ull;
    for (const Bar *x : {&a, &b}) {
        for (auto &c : *x) h = (h ^ (uint64_t)(c[0] * 100 + c[1] * 4 + FAM[c[2]] + 1)) * 1099511628211ull;
        h = (h ^ 0xffull) * 1099511628211ull;
    }
    return h;
}

int src_id(const std::string &src) { return src == "pop" ? 1 : src == "song" ? 2 : src == "classical" ? 3 : 0; }
const std::vector<int> TONES_Q[11] = {{0, 4, 7}, {0, 4, 7, 11}, {0, 3, 7}, {0, 3, 7, 10}, {0, 4, 7, 10}, {0, 4, 10},
                                      {0, 5, 7, 10}, {0, 3, 6, 10}, {0, 3, 6, 9}, {0, 4, 8}, {0, 3, 7, 11}};
const std::vector<int> TENS_Q[11] = {{2, 9}, {2, 9}, {2, 5, 10}, {2, 5}, {2, 9}, {1, 3, 8}, {2, 9}, {5, 8}, {2, 5}, {2}, {2}};

std::vector<Bar> progression(const Model &m, const std::vector<std::pair<char, int>> &form, bool minor, const std::string &src, int ts,
                             const std::vector<int> &beats, double temp, double top_p, uint64_t seed,
                             const std::vector<Bar> *prefix, char prefix_sec, const std::map<int, Bar> *fixed, const ChordCtl *ctl,
                             const std::vector<std::vector<Bar>> *avoid) {
    using namespace tk;
    Rng rng(seed);
    Runner r(&m);
    std::vector<int> head{C_BOS, C_SRC0 + src_id(src), minor ? C_MODE_min : C_MODE_maj, ts == 3 ? C_TS_3 : C_TS_4};
    // 조 쪽으로 당기기: 조 밖 근음 · 그 자리에 안 맞는 종류(예: 장조 IV 에 딸림7, vii 에 단7) · 긴장 큰 종류의 점수를 깎음
    static const bool DIA_MAJ[12] = {1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1}, DIA_MIN[12] = {1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0};
    static const bool TENSE_Q[11] = {0, 0, 0, 0, 0, 1, 0, 1, 1, 1, 1};
    //                         종류:  maj maj7 min m7 dom alt sus hdim dim aug mM7   (도수마다 그 조의 화음으로 맞는 것)
    static const int FIT_MAJ[12] = {0b00001000011, 0, 0b00001001100, 0, 0b00000001100, 0b00000000011, 0, 0b00001010001, 0, 0b00000001100, 0, 0b00110000000};
    static const int FIT_MIN[12] = {0b10000001100, 0, 0b00110000000, 0b00000000011, 0, 0b00000001100, 0, 0b00001111101, 0b00000000011, 0, 0b00000010001, 0b00100000000};
    auto fits = [&](int d, int q) { return ((minor ? FIT_MIN : FIT_MAJ)[d] >> q) & 1; };
    auto deg_logits = [&]() {
        std::vector<float> lg = r.logits;
        for (int i = 0; i < 12; i++) if (!(minor ? DIA_MIN : DIA_MAJ)[i]) lg[C_DEG0 + i] -= (float)ctl->key_pull;
        return lg;
    };
    auto q_logits = [&](int d) {
        std::vector<float> lg = r.logits;
        const bool dia = (minor ? DIA_MIN : DIA_MAJ)[d];
        for (int q = 0; q < 11; q++) {
            const bool ok = dia && fits(d, q);
            if (dia && !ok) lg[C_Q0 + q] -= (float)(ctl->key_pull * ctl->qfit);
            if (TENSE_Q[q] && !ok) lg[C_Q0 + q] -= (float)ctl->calm;
        }
        lg[C_Q0 + 1] -= (float)ctl->triad; lg[C_Q0 + 3] -= (float)ctl->triad;
        return lg;
    };
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
    ChordTok last_c{-1, 0, 0};                                                    // 바로 앞 코드 (빈 마디 = 앞 코드가 이어짐)
    if (prefix) for (auto &b : *prefix) if (!b.empty()) last_c = b.back();
    for (auto &[sec, n] : form) {
        for (int k = 0; k < n; k++) {
            r.room(40, (int)head.size(), C_BAR);
            std::vector<int> b{C_BAR};
            if (k == 0) b.push_back(C_SEC0 + (sec - 'A'));
            r.feed(b);
            Bar bar;
            auto fx = fixed ? fixed->find(out_i) : std::map<int, Bar>::const_iterator();
            if (fixed && fx != fixed->end()) {                                    // 그대로 둘 마디
                for (auto &c : fx->second) { r.feed({C_BEAT0 + c[0], C_DEG0 + c[1], C_Q0 + c[2]}); bar.push_back(c); }
                if (bar.empty() && last_c[0] >= 0) bar.push_back({0, last_c[1], last_c[2]});
                if (!bar.empty()) last_c = bar.back();
                out.push_back(bar); bar_i++; out_i++;
                continue;
            }
            // 피할 2마디 덩어리(avoid)와 똑같아지면 둘째 마디를 조금 더 뜨겁게 다시 씀 (최대 3번) — 같은 코드 덩어리만 맴돌지 않게
            const bool check = avoid && out_i % 2 == 1;
            Runner::Snap snap;
            if (check) snap = r.snapshot();
            std::vector<int> banned;                                              // 다시 쓸 때: 앞 시도의 첫 근음은 못 고르게 (그래야 정말 달라짐)
            for (int attempt = 0;; attempt++) {
                bar.clear();
                int last = -1;
                const double tt = temp * (1 + .35 * attempt);
                while (true) {
                    std::vector<int> allowed;
                    for (int bt : beats) if (last < bt && bt < ts) allowed.push_back(C_BEAT0 + bt);
                    if (!bar.empty() || (bar_i > 0 && banned.empty())) allowed.push_back(C_BAR);
                    if (bar_i == 0 && bar.empty()) allowed = {C_BEAT0};
                    int t = pick(r.logits, allowed, tt, top_p, rng);
                    if (t == C_BAR) break;
                    int bt = t - C_BEAT0;
                    r.feed1(t);
                    std::vector<float> lgd = ctl ? deg_logits() : r.logits;
                    if (bar.empty()) for (int bd : banned) lgd[C_DEG0 + bd] = -1e9f;
                    int d = pick(lgd, DEG, tt, top_p, rng) - C_DEG0; r.feed1(C_DEG0 + d);
                    int q = pick(ctl ? q_logits(d) : r.logits, QQ, tt, top_p, rng) - C_Q0; r.feed1(C_Q0 + q);
                    bar.push_back({bt, d, q});
                    last = bt;
                }
                if (bar.empty() && last_c[0] >= 0) bar.push_back({0, last_c[1], last_c[2]});
                if (!check || attempt >= 4 || bar.empty()) break;
                const uint64_t sig = cell_sig(out.back(), bar);
                bool dup = false;
                for (auto &c : *avoid) if (c.size() == 2 && cell_sig(c[0], c[1]) == sig) { dup = true; break; }
                for (int j = 0; !dup && j + 1 < out_i - 1; j += 2) dup = cell_sig(out[j], out[j + 1]) == sig;         // 이번 단락 앞 덩어리
                if (!dup) break;
                banned.push_back(bar[0][1]);
                r.restore(snap);
            }
            if (!bar.empty()) last_c = bar.back();
            out.push_back(bar);
            bar_i++; out_i++;
        }
    }
    return out;
}

MelodyWriter::MelodyWriter(const Model *m, int ts_, const std::string &kind, const std::string &feel, const std::string &tempo, bool minor,
                           int dens, int reg, uint64_t seed, const std::string &src, int ct)
    : r(m), ts(ts_), rng(seed) {
    using namespace tk;
    head = {M_BOS, M_SRC0 + src_id(src), kind == "solo" ? M_KIND_solo : M_KIND_head,
            feel == "straight" ? M_FEEL_straight : feel == "latin" ? M_FEEL_latin : M_FEEL_swing,
            tempo == "TEMPO_slow" ? M_TEMPO_slow : tempo == "TEMPO_fast" ? M_TEMPO_fast : M_TEMPO_med,
            ts == 3 ? M_TS_3 : M_TS_4, minor ? M_MODE_min : M_MODE_maj, M_DENS0 + dens, M_REG0 + reg, M_CT0 + std::max(0, std::min(3, ct))};
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
        // 이 자리의 코드 → 음마다 코드음 0 · 텐션 1 · 그 밖 2
        const ChordTok *ch = nullptr;
        for (auto &c : chords) if (c[0] * TPB <= on) ch = &c;
        if (!ch && !chords.empty()) ch = &chords[0];
        auto kind_of = [&](int p) {
            if (!ch) return 0;
            const int iv = (((p - (*ch)[1]) % 12) + 12) % 12;
            const auto &T = TONES_Q[(*ch)[2]], &E = TENS_Q[(*ch)[2]];
            return std::count(T.begin(), T.end(), iv) ? 0 : std::count(E.begin(), E.end(), iv) ? 1 : 2;
        };
        const bool onbeat = on % TPB == 0, strong = onbeat && (on / TPB) % (ts == 4 ? 2 : 3) == 0;
        const bool guide = consonance > 0 && ch;
        int pt;
        if ((no_copy > 0 && !notes.empty()) || guide) {
            std::vector<float> lg = r.logits;
            if (guide)
                for (int t : ps) {
                    const int p = P_LO + (t - M_P0), k = kind_of(p);
                    float b = 0;
                    if (k == 2) b -= (float)(consonance * (strong ? 2.2 : onbeat ? .8 : 0));       // 코드 밖 음: 강박일수록 피함 (약박의 지나가는 음은 그대로)
                    else if (k == 1 && strong) b -= (float)(consonance * .5);
                    if (prev_kind == 2 && prev_p >= 0 && std::abs(p - prev_p) <= 2 && k != 2) b += (float)(consonance * 1.2);   // 코드 밖 음은 순차로 풀림
                    lg[t] += b;
                }
            // 지금까지 이 마디가 어떤 지난 마디의 앞부분과 (자리 · 음) 똑같으면, 그 마디의 다음 음을 그대로 따라가는 것에 벌점
            const size_t n = notes.size();
            for (size_t bi = 0; no_copy > 0 && n > 0 && bi < past.size(); bi++) {
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
        const int pk = kind_of(p);
        int dt;
        if (guide && pk == 2) {                                                   // 코드 밖 음은 짧게 (한 박 넘게 끌지 않게)
            std::vector<float> lg = r.logits;
            for (int i = 0; i < NDUR; i++) if (DUR_SET[i] > TPB) lg[M_D0 + i] -= (float)(consonance * (DUR_SET[i] >= 2 * TPB ? 4.0 : 2.0));
            dt = pick(lg, D, temp, top_p, rng);
        } else dt = pick(r.logits, D, temp, top_p, rng);
        r.feed1(dt);
        notes.push_back({on, DUR_SET[dt - M_D0], p});
        same_run = p == prev_p ? same_run + 1 : 1;
        prev_p = p; prev_kind = pk;
        last = on;
    }
    if (!notes.empty()) { past.push_back(notes); if (past.size() > 96) past.erase(past.begin()); }
    return notes;
}
