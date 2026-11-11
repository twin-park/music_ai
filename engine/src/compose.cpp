#include "compose.h"
#include "tokens.h"
#include <algorithm>
#include <cmath>
#include <set>

const char *ROLE_NAME[10] = {"도입", "A", "A'", "B", "A''", "끝", "이음", "주고받기", "쉬어가기", "솔로"};

// ---------------- 분위기 표 (styles.py MOODS) ----------------
const std::vector<Mood> &moods() {
    static const std::vector<Mood> M = {
        {"비오는날", "비 오는 날", {"Eb", "Db", "F"}, false, 68, 4, .62, 1, "jazz", "swing", "TEMPO_slow", 1, 1, 60, 82, .9, 6, 9, 2,
         "테너색소폰", 50, 74, 2.6, "피아노 · 테너 색소폰 · 베이스 · 브러시",
         "느린 스윙 발라드 · 피아노 선율 아래 드롭2 화음 · 색소폰이 같은 선율 변주 · B 2마디씩 주고받기 · A'' 피아노 옥타브 + 색소폰 3·7음 대선율 · 베이스 2박→워킹 · 브러시",
         true, 1.0, 0, 0.35},
        {"평온한재즈", "평온한 재즈", {"F", "Bb", "G"}, false, 104, 4, .64, 1, "jazz", "swing", "TEMPO_med", 1, 1, 62, 82, .9, 7, 9, 2,
         "", 0, 0, 2.2, "피아노 트리오 · 재즈기타 · 브러시",
         "미디엄 스윙 · 피아노 3·6도 겹 선율 → 기타가 선율 + 피아노 반주 → 피아노 화음 선율 + 기타 4분 반주 → 피아노 옥타브 · 워킹 베이스 · 브러시 스윙",
         true, 1.0, 1, 0.3},
        {"밤드라이브", "밤 드라이브", {"Dm", "Am", "Em"}, true, 96, 4, 0, 1, "jazz", "straight", "TEMPO_med", 1, 1, 60, 80, .9, 7, 9, 2,
         "", 0, 0, 2.6, "로즈 · 뮤트 트럼펫 · 피아노 · 베이스 · 드럼",
         "곧은 8분 쿨재즈 · 로즈 4도 쌓기 반주 · 뮤트 트럼펫 선율 → B 피아노 선율 · 곧은 8분 베이스 · 하이햇+림", true, 1.0, 2, 0.42},
        {"즐거운대화", "즐거운 대화", {"Bb", "F", "Eb"}, false, 176, 4, .6, 1, "jazz", "swing", "TEMPO_fast", 2, 1, 60, 82, .92, 9, 10, 2,
         "", 0, 0, 2.0, "알토 색소폰 · 비브라폰 · 피아노 · 베이스 · 드럼",
         "빠른 스윙 · 알토 → 비브라폰 → 2마디씩 주고받기 → 둘이 옥타브로 같이 · 피아노 찰스턴 반주 · 워킹 베이스 · 라이드 심벌", true, 1.0, 3, 0.42},
        {"바닷가보사노바", "바닷가 보사노바", {"D", "F", "G"}, false, 128, 4, 0, 1, "jazz", "latin", "TEMPO_med", 1, 2, 64, 86, .9, 7, 9, 2,
         "", 0, 0, 2.4, "나일론 기타 · 플루트 · 피아노 · 로즈 · 베이스 · 림샷 · 현악",
         "보사노바 · 나일론 기타 엄지 베이스 + 화음 뜯기 · 플루트 선율 → B 피아노 → A'' 현악 · 보사 베이스 · 림샷·킥·하이햇", true, 1.0, 4, 0.35},
        {"아이재우기", "아이 재우기", {"F", "G", "C"}, false, 82, 3, 0, 0, "song", "straight", "TEMPO_slow", 1, 1, 62, 80, .88, 5, 7, 2,
         "", 0, 0, 2.8, "피아노 · 첼레스타 · 현악",
         "3/4 왈츠 자장가 · 왼손 쿵-짝-짝 · 3·6도 겹 선율 → 첼레스타가 한 옥타브 위 같이 → 현악이 감쌈 · B 만 아주 작은 브러시", false, 1.0, 5, 0.08},
        {"진정", "마음 가라앉히기", {"Db", "Eb", "Ab"}, false, 58, 4, .6, 1, "jazz", "swing", "TEMPO_slow", 1, 1, 62, 82, .88, 6, 8, 2,
         "", 0, 0, 3.0, "피아노 혼자 · 현악(끝 무렵)",
         "아주 느린 피아노 발라드 · 왼손 1-5-10 펼침 · 선율 아래 화음 · 네 마디마다 살짝 늦춤(루바토) · A'' 현악 아주 작게", false, 1.0, 6, 0.22},
        {"위로", "위로", {"A", "D", "E"}, false, 72, 4, 0, 0, "pop", "straight", "TEMPO_slow", 1, 1, 62, 82, .9, 6, 9, 2,
         "", 0, 0, 2.8, "피아노 · 첼로 · 바이올린 · 현악",
         "영화음악 느낌 · 피아노 옥타브 선율 + 왼손 펼침 → 첼로 선율 → 바이올린 + 현악 → 피아노 옥타브 + 첼로 대선율", false, 1.0, 7, 0.15},
        {"낮드라이브", "낮 드라이브", {"G", "A", "Bb"}, false, 120, 4, 0, 1, "jazz", "straight", "TEMPO_med", 2, 1, 60, 82, .92, 8, 10, 2,
         "", 0, 0, 2.0, "테너 색소폰 · 피아노 · 로즈 · 일렉 베이스 · 드럼",
         "곧은 8분 그루브 · 테너 색소폰 선율 + 피아노 반주 → B 피아노 옥타브 + 로즈 → 색소폰과 피아노가 같이 · 일렉 베이스 · 백비트 드럼", true, 1.0, 8, 0.38},
        // ── 클래식 (11-11): 진행 · 선율 AI 가 클래식 악보(PDMX)로 배운 갈래를 씀 · 3화음 중심 · 스윙 없음
        {"클래식피아노", "클래식 피아노", {"C", "G", "F", "Eb"}, false, 80, 4, 0, 0, "classical", "straight", "TEMPO_slow", 1, 1, 62, 84, .9, 8, 9, 2,
         "", 0, 0, 2.6, "피아노 혼자",
         "고전 · 낭만 피아노 소품 · 오른손 선율(한 줄 → 3·6도 → 옥타브) · 왼손 알베르티 / 펼침 · 3화음 중심 진행 · 네 마디마다 살짝 늦춤", false, 1.12, 9, .12},
        {"현악앙상블", "현악 앙상블", {"D", "G", "Bb", "F"}, false, 66, 4, 0, 0, "classical", "straight", "TEMPO_slow", 0, 1, 62, 84, .88, 6, 8, 2,
         "바이올린", 67, 88, 3.0, "바이올린 · 첼로 · 현악 · 피아노",
         "느린 현악 · 바이올린 선율 ↔ 첼로 선율 · 현악이 길게 받침 · 첼로 대선율 · 피아노 펼침은 가끔", false, 1.12, 10, .1},
        {"클래식왈츠", "클래식 왈츠", {"G", "D", "A", "F"}, false, 132, 3, 0, 0, "classical", "straight", "TEMPO_med", 1, 1, 64, 86, .9, 6, 9, 2,
         "", 0, 0, 2.4, "피아노 · 플루트 · 바이올린 · 첼로 · 현악",
         "3/4 왈츠 · 왼손 쿵-짝-짝 · 선율은 피아노 3·6도 → 플루트 → 바이올린 · 첼로 대선율 · 현악이 감쌈", false, 1.12, 11, .12},
    };
    return M;
}

const Mood *mood_by_id(const std::string &id) {
    for (auto &m : moods()) if (m.id == id) return &m;
    return nullptr;
}

// ---------------- 도우미 (styles.py) ----------------
std::vector<BN> oct_fit(const std::vector<BN> &notes, int lo, int hi) {
    if (notes.empty()) return {};
    std::vector<int> ps;
    for (auto &n : notes) ps.push_back(n.p);
    std::sort(ps.begin(), ps.end());
    int med = ps[ps.size() / 2], k = 0;
    while (med + k > hi - 5) k -= 12;
    while (med + k < lo + 5) k += 12;
    std::vector<BN> out;
    for (auto &n : notes) out.push_back({n.t, n.d, fit(n.p + k, lo, hi)});
    return out;
}
std::vector<BN> sel(const std::vector<BN> &notes, const Song &S, int b0, int b1) {
    std::vector<BN> out;
    for (auto &n : notes) if ((double)b0 * S.ts - 1e-6 <= n.t && n.t < (double)b1 * S.ts - 1e-6) out.push_back(n);
    return out;
}
std::vector<BN> up(const std::vector<BN> &notes, int k) {
    std::vector<BN> out;
    for (auto &n : notes) out.push_back({n.t, n.d, n.p + k});
    return out;
}
std::vector<int> range_v(int a, int b) { std::vector<int> v; for (int i = a; i < b; i++) v.push_back(i); return v; }
static std::vector<BN> top_line(const Song &S, int b0, int b1, int lo = 70, int hi = 81) {
    std::vector<BN> out; int p = -1;
    for (auto &s : S.spans_in(b0, b1)) {
        auto g = guide(s.c);
        int best = -1; double bc = 1e18;
        for (int x = lo; x <= hi; x++) {
            if (std::find(g.begin(), g.end(), pmod(x, 12)) == g.end()) continue;
            double c = (p >= 0 ? std::abs(x - p) : std::abs(x - hi + 3)) + (x == p ? 1.5 : 0);
            if (c < bc) { bc = c; best = x; }
        }
        if (best < 0) best = fit(g[0], lo, hi);
        out.push_back({s.a, s.b - s.a, best}); p = best;
    }
    return out;
}
static void final_chord(Song &S, int FN, const std::string &lead, int lr0, int lr1, const std::string &cym, bool bass, double base) {
    double t = (double)FN * S.ts;
    Chord c = S.chord(t);
    int r = fit(c.root, 36, 43);
    auto upv = stack({c.iv(3), c.iv(7) >= 0 ? c.iv(7) : (c.root + 9) % 12, (c.root + 2) % 12, (c.root + 7) % 12}, 55, 76);
    std::vector<int> all{r, r + 7};
    const int ln = lead.empty() ? -99 : fit(c.iv(3), lr0, lr1);
    for (int q : upv)                                                              // 관악기 끝음과 반음으로 붙는 음(단조 9음 등)은 뺌
        if (ln < 0 || !(std::abs(q - ln) == 1 || std::abs(q - ln) == 11 || std::abs(q - ln) == 13)) all.push_back(q);
    for (size_t k = 0; k < all.size(); k++) S.add(all[k] < 60 ? "피아노 왼손" : "피아노 오른손", t + k * .09, 6, all[k], base + 2 - (double)k);
    S.pedal.push_back({t + .02, t + 6.5});
    if (bass) S.add("베이스", t, 6, fit(c.root, 31, 43), 62);
    if (!lead.empty()) S.add(lead, t + .25, 5.5, fit(c.iv(3), lr0, lr1), 50);
    if (cym == "브러시") { S.add("브러시", t, 4, 40, 30); S.add("브러시", t, 4, 51, 30); }
    else if (cym == "드럼") { S.add("드럼", t, 4, 51, 40); S.add("드럼", t, 3, 49, 46); }
}

// ---------------- 편곡 공식 9개 — 단락마다 ----------------
void Session::arrange(Role R, int a, int b, const std::vector<BN> &M) {
    arrange_main(R, a, b, M);
    // 큰 물결이 높을 때: 현악이 있는 분위기는 현악이 아주 작게 감쌈 (없던 단락에만)
    if (((m.style >= 4 && m.style <= 7) || m.style == 11) && energy > .62 && R != R_INTRO && R != R_TAG && R != R_TRANS) {
        bool has = false;
        for (auto &n : S.pool) has = has || (n.sec == S.cur_sec && S.names[n.part] == "현악");
        if (!has) S.strings_pad(a, b, "현악", 32 + 10 * energy, 55, 72);
    }
}

void Session::arrange_main(Role R, int a, int b, const std::vector<BN> &M) {
    Song &s = S;
    const int lr0 = m.lead_lo, lr1 = m.lead_hi;
    const std::string L = m.lead;
    auto bars = range_v(a, b);
    switch (m.style) {
    case 0:                                                                       // 비 오는 날
        if (R == R_INTRO) {
            s.piano_melody(top_line(s, a, b), 56, "block"); s.lh_guide(a, b, 40, true); s.pedals(a, b);
            s.add("브러시", (b - 1) * s.ts + 2, 2, 40, 26);
        } else if (R == R_A) {
            s.piano_melody(oct_fit(M, 62, 86), 66, "block"); s.lh_guide(a, b, 46); s.pedals(a, b); s.bass(a, b, "two"); s.drums(a, b, "brush", 0);
        } else if (R == R_A2) {
            auto la = oct_fit(M, lr0, lr1);
            s.lead(L, la, 74); s.comp(bars, "ballad", 47, "rootless", 50, 68, la);
            s.bass(a, b - 2, "two"); s.bass(b - 2, b, "walk", 72); s.drums(a, b, "brush", 1);
        } else if (R == R_B) {
            for (int k = 0; k < 8; k += 2) {
                auto seg = sel(M, s, a + k, a + k + 2);
                if (k == 0 || k == 4 || k == 6) {
                    auto s2 = oct_fit(seg, lr0, lr1);
                    s.lead(L, s2, 80);
                    if (k == 6) { s.piano_melody(up(s2, 12), 66, "line"); s.lh_guide(a + k, a + k + 2, 46); }
                    else s.comp(range_v(a + k, a + k + 2), "ballad", 50, "rootless", 50, 68, s2);
                } else {
                    s.piano_melody(oct_fit(seg, 64, 88), 70, "line"); s.lh_guide(a + k, a + k + 2, 46); s.pedals(a + k, a + k + 2);
                }
            }
            s.bass(a, b, "walk", 78); s.drums(a, b, "brush_swing", 2);
        } else if (R == R_A3) {
            s.add("브러시", (double)a * s.ts, .3, 39, 52);
            s.piano_melody(oct_fit(M, 64, 88), 70, "octave"); s.lh_guide(a, b, 46); s.pedals(a, b);
            s.guide_line(a, b - 2, L, 56, lr0, lr0 + 17);
            s.bass(a, b - 2, "walk", 72); s.bass(b - 2, b, "two"); s.drums(a, b, "brush", 1);
        } else if (R == R_TAG) {
            auto s1 = oct_fit(sel(M, s, a, a + 2), lr0, lr1);
            s.lead(L, s1, 66); s.comp({a, a + 1}, "ballad", 44, "rootless", 50, 68, s1);
            s.piano_melody(oct_fit(sel(M, s, a + 2, b), 64, 86), 60, "block"); s.lh_guide(a + 2, b, 42); s.pedals(a + 2, b);
            s.bass(a, b, "two", 66); s.drums(a, b, "brush", 0, 99);
            final_chord(s, b, L, lr0, lr0 + 14, "브러시", true, 50);
        }
        break;
    case 1:                                                                       // 평온한 재즈
        if (R == R_INTRO) { s.comp(bars, "swing", 46); s.bass(a, b, "two", 70); s.drums(a, b, "brush_swing", 0, 4); }
        else if (R == R_A) { s.piano_melody(oct_fit(M, 64, 86), 64, "dyad"); s.lh_guide(a, b, 46); s.bass(a, b, "two", 72); s.drums(a, b, "brush_swing", 0); }
        else if (R == R_A2) {
            auto g = oct_fit(M, 55, 77);
            s.lead("재즈기타", g, 72); s.comp(bars, "swing", 46, "rootless", 50, 68, g); s.bass(a, b, "walk", 74); s.drums(a, b, "brush_swing", 1);
        } else if (R == R_B) {
            s.piano_melody(oct_fit(M, 64, 88), 66, "block"); s.lh_guide(a, b, 46); s.guitar_comp(bars, "재즈기타", "swing", 46);
            s.bass(a, b, "walk", 76); s.drums(a, b, "brush_swing", 2);
        } else if (R == R_A3) {
            s.piano_melody(oct_fit(M, 64, 88), 68, "octave"); s.lh_guide(a, b, 46); s.bass(a, b, "walk", 74); s.drums(a, b, "brush_swing", 1);
        } else if (R == R_TAG) {
            s.piano_melody(oct_fit(M, 64, 86), 60, "block"); s.lh_guide(a, b, 42); s.pedals(a + 2, b);
            s.bass(a, b, "two", 66); s.drums(a, b, "brush", 0, 99);
            final_chord(s, b, "재즈기타", 55, 70, "브러시", true, 50);
        }
        break;
    case 2: {                                                                     // 밤 드라이브
        const std::string RH = "로즈", RL = "로즈";
        if (R == R_INTRO) { s.comp(bars, "straight", 50, "quartal", 50, 72, {}, RH, RL); s.bass(a, b, "straight", 72); s.drums(a, b, "straight", 0, 4); }
        else if (R == R_A || R == R_A2) {
            int lvl = R == R_A ? 0 : 1;
            auto t = oct_fit(M, 58, 80);
            s.lead("뮤트트럼펫", t, 76 + lvl * 3); s.comp(bars, "straight", 48, "quartal", 50, 72, t, RH, RL);
            s.bass(a, b, "straight", 74); s.drums(a, b, "straight", lvl);
        } else if (R == R_B) {
            auto pb = oct_fit(M, 62, 86);
            s.piano_melody(pb, 68, "dyad"); s.comp(bars, "straight", 44, "quartal", 48, 64, pb, RH, RL);
            s.bass(a, b, "straight", 76); s.drums(a, b, "straight", 1);
        } else if (R == R_A3) {
            auto t = oct_fit(M, 58, 80);
            s.lead("뮤트트럼펫", t, 80); s.comp(bars, "straight", 48, "quartal", 50, 72, t, RH, RL);
            s.bass(a, b, "straight", 74); s.drums(a, b, "straight", 1);
        } else if (R == R_TAG) {
            auto t = oct_fit(M, 58, 78);
            s.lead("뮤트트럼펫", t, 70); s.comp(bars, "straight", 44, "quartal", 50, 72, t, RH, RL);
            s.bass(a, b, "straight", 66); s.drums(a, b, "straight", 0, 99, false);
            final_chord(s, b, "뮤트트럼펫", 58, 72, "드럼", true, 50);
        }
        break;
    }
    case 3:                                                                       // 즐거운 대화
        if (R == R_INTRO) { s.comp(bars, "swing", 52); s.bass(a, b, "walk", 76); s.drums(a, b, "ride", 0, 4); }
        else if (R == R_A) {
            auto x = oct_fit(M, 57, 79); s.lead("알토색소폰", x, 82); s.comp(bars, "swing", 50, "rootless", 50, 68, x);
            s.bass(a, b, "walk", 80); s.drums(a, b, "ride", 1);
        } else if (R == R_A2) {
            auto v = oct_fit(M, 62, 86); s.lead("비브라폰", v, 86); s.comp(bars, "swing", 48, "rootless", 50, 68, v);
            s.bass(a, b, "walk", 80); s.drums(a, b, "ride", 1);
        } else if (R == R_B) {
            for (int k = 0; k < 8; k += 2) {
                auto seg = sel(M, s, a + k, a + k + 2);
                auto x = k % 4 == 0 ? oct_fit(seg, 57, 79) : oct_fit(seg, 62, 86);
                s.lead(k % 4 == 0 ? "알토색소폰" : "비브라폰", x, 84);
                s.comp(range_v(a + k, a + k + 2), "swing", 50, "rootless", 50, 68, x);
            }
            s.bass(a, b, "walk", 80); s.drums(a, b, "ride", 2);
        } else if (R == R_A3) {
            auto x = oct_fit(M, 57, 79);
            s.lead("알토색소폰", x, 84); s.lead("비브라폰", up(x, 12), 72); s.comp(bars, "swing", 48, "rootless", 50, 68, x);
            s.bass(a, b, "walk", 80); s.drums(a, b, "ride", 2);
        } else if (R == R_TAG) {
            auto t = oct_fit(M, 57, 77); s.lead("알토색소폰", t, 76); s.comp(bars, "swing", 46, "rootless", 50, 68, t);
            s.bass(a, b, "walk", 80); s.drums(a, b, "ride", 0, 99, false);
            final_chord(s, b, "알토색소폰", 57, 72, "드럼", true, 50);
        }
        break;
    case 4:                                                                       // 바닷가 보사노바
        s.guitar_comp(bars, "나일론기타", "bossa", 56); s.bass(a, b, "bossa", 74); s.drums(a, b, "bossa", 0, R == R_INTRO ? 99 : 8);
        if (R == R_A) s.lead("플루트", oct_fit(M, 67, 91), 76, .95);
        else if (R == R_A2) {
            auto f = oct_fit(M, 67, 91);
            s.lead("플루트", f, 80, .95); s.comp(bars, "bossa", 40, "rootless", 50, 68, f, "로즈", "로즈");
        } else if (R == R_B) s.piano_melody(oct_fit(M, 64, 86), 64, "dyad");
        else if (R == R_A3) { s.lead("플루트", oct_fit(M, 67, 91), 80, .95); s.strings_pad(a, b, "현악", 46, 55, 74); }
        else if (R == R_TAG) {
            s.lead("플루트", oct_fit(M, 67, 91), 70, .95); s.strings_pad(a, b, "현악", 46, 55, 74);
            final_chord(s, b, "플루트", 67, 82, "드럼", true, 50);
        }
        break;
    case 5:                                                                       // 아이 재우기 (3/4)
        s.piano_pattern(a, b, "waltz", 40); s.pedals(a, b, 3);
        if (R == R_INTRO) s.piano_melody(top_line(s, a, b, 67, 79), 50, "dyad");
        else if (R == R_A) s.piano_melody(oct_fit(M, 64, 84), 56, "dyad");
        else if (R == R_A2) { auto a2 = oct_fit(M, 64, 84); s.piano_melody(a2, 54, "line"); s.lead("첼레스타", up(a2, 12), 50); }
        else if (R == R_B) {
            s.piano_melody(oct_fit(M, 64, 86), 58, "dyad"); s.strings_pad(a, b, "현악", 40, 55, 72); s.drums(a, b, "waltz_brush", 0, 99);
        } else if (R == R_A3) { s.piano_melody(oct_fit(M, 64, 84), 54, "dyad"); s.strings_pad(a, b, "현악", 38, 55, 72); }
        else if (R == R_TAG) {
            s.piano_melody(oct_fit(M, 64, 82), 48, "dyad"); s.strings_pad(a, b, "현악", 38, 55, 72);
            final_chord(s, b, "첼레스타", 76, 88, "", false, 42);
        }
        break;
    case 6:                                                                       // 진정 (피아노 혼자)
        s.piano_pattern(a, b, "arp", 40); s.pedals(a, b);
        if (R == R_INTRO) s.piano_melody(top_line(s, a, b, 68, 79), 50, "block");
        else if (R == R_A) s.piano_melody(oct_fit(M, 64, 86), 58, "block");
        else if (R == R_A2) s.piano_melody(oct_fit(M, 64, 86), 58, "dyad");
        else if (R == R_B) s.piano_melody(oct_fit(M, 64, 86), 62, "block");
        else if (R == R_A3) { s.piano_melody(oct_fit(M, 64, 86), 60, "octave"); s.strings_pad(a, b, "현악", 38, 55, 74); }
        else if (R == R_TAG) {
            s.piano_melody(oct_fit(M, 64, 86), 52, "block"); s.strings_pad(a, b, "현악", 38, 55, 74);
            final_chord(s, b, "", 0, 0, "", false, 44);
        }
        break;
    case 7:                                                                       // 위로 (영화음악)
        s.piano_pattern(a, b, "arp", 42); s.pedals(a, b);
        if (R == R_INTRO) s.piano_melody(top_line(s, a, b, 68, 80), 52, "block");
        else if (R == R_A) s.piano_melody(oct_fit(M, 66, 88), 64, "octave");
        else if (R == R_A2) { s.lead("첼로", oct_fit(M, 50, 72), 66); s.strings_pad(a, b, "현악", 36, 43, 58); }
        else if (R == R_B) { s.lead("바이올린", oct_fit(M, 67, 91), 66); s.strings_pad(a, b, "현악", 44, 52, 72); }
        else if (R == R_A3) {
            s.piano_melody(oct_fit(M, 66, 88), 68, "octave"); s.guide_line(a, b, "첼로", 56, 48, 62); s.strings_pad(a, b, "현악", 40, 55, 72);
        } else if (R == R_TAG) {
            s.piano_melody(oct_fit(M, 64, 86), 56, "block");
            final_chord(s, b, "첼로", 48, 60, "", false, 46);
        }
        break;
    case 9:                                                                       // 클래식 피아노 (혼자)
        s.piano_pattern(a, b, "alberti", 40); s.pedals(a, b);
        if (R == R_INTRO) s.piano_melody(top_line(s, a, b, 67, 79), 50, "line");
        else if (R == R_TAG) { s.piano_melody(oct_fit(M, 64, 86), 52, "line"); final_chord(s, b, "", 0, 0, "", false, 44); }
        else s.piano_melody(oct_fit(M, 64, 86), 58, "line");
        break;
    case 10:                                                                      // 현악 앙상블
        s.strings_pad(a, b, "현악", 40, 50, 70);
        for (auto &sp : s.spans_in(a, b)) s.add("현악", sp.a, sp.b - sp.a + .05, fit(sp.c.root, 36, 47), 40);
        if (R == R_INTRO) s.lead("바이올린", top_line(s, a, b, 72, 84), 56);
        else if (R == R_TAG) { s.lead("바이올린", oct_fit(M, 67, 88), 62); s.guide_line(a, b, "첼로", 50, 48, 62); final_chord(s, b, "첼로", 48, 60, "", false, 40); }
        else s.lead("바이올린", oct_fit(M, 67, 88), 66);
        break;
    case 11:                                                                      // 클래식 왈츠 (3/4)
        s.piano_pattern(a, b, "waltz", 40); s.pedals(a, b, 3);
        if (R == R_INTRO) s.piano_melody(top_line(s, a, b, 67, 79), 50, "dyad");
        else if (R == R_TAG) { s.piano_melody(oct_fit(M, 64, 84), 50, "dyad"); s.strings_pad(a, b, "현악", 36, 55, 72); final_chord(s, b, "", 0, 0, "", false, 42); }
        else s.piano_melody(oct_fit(M, 64, 84), 56, "dyad");
        break;
    case 8:                                                                       // 낮 드라이브
        s.bass(a, b, "straight", 78, "일렉베이스");
        if (R == R_INTRO) { s.comp(bars, "straight", 52); s.drums(a, b, "straight", 0, 4); }
        else if (R == R_A || R == R_A2) {
            auto x = oct_fit(M, 52, 76); s.lead("테너색소폰", x, 82); s.comp(bars, "straight", 50, "rootless", 50, 68, x); s.drums(a, b, "straight", 1);
        } else if (R == R_B) {
            auto pb = oct_fit(M, 64, 88); s.piano_melody(pb, 70, "octave");
            s.comp(bars, "straight", 44, "quartal", 48, 64, pb, "로즈", "로즈"); s.drums(a, b, "straight", 2);
        } else if (R == R_A3) {
            auto x = oct_fit(M, 52, 76); s.lead("테너색소폰", x, 84); s.piano_melody(up(x, 12), 60, "line");
            s.comp(bars, "straight", 44, "quartal", 48, 64, x, "로즈", "로즈"); s.drums(a, b, "straight", 2);
        } else if (R == R_TAG) {
            auto x = oct_fit(M, 52, 74); s.lead("테너색소폰", x, 74); s.comp(bars, "straight", 46, "rootless", 50, 68, x);
            s.drums(a, b, "straight", 0, 99, false);
            final_chord(s, b, "테너색소폰", 52, 68, "드럼", false, 50);
            s.add("일렉베이스", (double)b * s.ts, 5, fit(s.chord((double)b * s.ts).root, 31, 43), 64);
        }
        break;
    }
}

// ---------------- 진행: 후보 여러 개 → 공식 점수 ----------------
static bool qin(int q, std::initializer_list<int> qs) { for (int x : qs) if (q == x) return true; return false; }

static double score_progression(const std::vector<Bar> &bars) {
    std::vector<Bar> A(bars.begin(), bars.begin() + 8);
    std::set<std::pair<int, int>> flat, bset;
    for (auto &b : A) for (auto &c : b) flat.insert({c[1], c[2]});
    int loop = 0;
    for (size_t i = 2; i < A.size(); i++) if (A[i] == A[i - 2]) loop++;
    std::vector<std::pair<int, int>> allf;
    for (auto &b : bars) for (auto &c : b) allf.push_back({c[1], c[2]});
    int iiv = 0;
    for (size_t i = 0; i + 1 < allf.size(); i++)
        if (qin(allf[i].second, {QA_M7, QA_HDIM, QA_MIN}) && qin(allf[i + 1].second, {QA_DOM, QA_ALT}) && pmod(allf[i + 1].first - allf[i].first, 12) == 5) iiv++;
    for (size_t i = 16; i < 24 && i < bars.size(); i++) for (auto &c : bars[i]) bset.insert({c[1], c[2]});
    int b_diff = 0;
    for (auto &x : bset) if (!flat.count(x)) b_diff++;
    bool end_ok = false;
    for (auto &c : bars.back()) end_ok = end_ok || c[1] == 0;
    return std::min<int>((int)flat.size(), 8) - loop * .8 + std::min(iiv, 6) * .5 + std::min(b_diff, 4) * .6 + (end_ok ? 2 : 0);
}

// ---------------- 진행: 앞 단락을 물려받아 몇 마디만 새로 ----------------
static double r_jit(uint64_t base, int k) { Rng r(base * 7 + k); return r.uniform(0, .9); }   // 늘 같은 '최고점'만 고르지 않게

double score8(const std::vector<Bar> &bars, bool jazz) {
    std::set<std::pair<int, int>> flat;
    for (auto &b : bars) for (auto &c : b) flat.insert({c[1], c[2]});
    int loop = 0;
    for (size_t i = 2; i < bars.size(); i++) if (bars[i] == bars[i - 2]) loop++;
    std::vector<std::pair<int, int>> allf;
    for (auto &b : bars) for (auto &c : b) allf.push_back({c[1], c[2]});
    int iiv = 0;
    for (size_t i = 0; i + 1 < allf.size(); i++)
        if (qin(allf[i].second, {QA_M7, QA_HDIM, QA_MIN}) && qin(allf[i + 1].second, {QA_DOM, QA_ALT}) && pmod(allf[i + 1].first - allf[i].first, 12) == 5) iiv++;
    bool end_ok = false;
    for (auto &c : bars.back()) end_ok = end_ok || c[1] == 0 || c[1] == 7;
    if (!jazz) {                                                                  // 재즈가 아니면: ii-V 대신 V → I 끝맺음, 화음 가짓수는 5개까지만 쳐줌
        int cad = 0;
        for (size_t i = 0; i + 1 < allf.size(); i++)
            if (allf[i].first == 7 && qin(allf[i].second, {QA_DOM, QA_MAJ}) && allf[i + 1].first == 0) cad++;
        return std::min<int>((int)flat.size(), 5) - loop * .8 + std::min(cad, 2) * .5 + (end_ok ? .7 : 0);
    }
    return std::min<int>((int)flat.size(), 6) - loop * .8 + std::min(iiv, 3) * .35 + (end_ok ? .7 : 0);
}

// 진행 후보(도수)가 조에 얼마나 붙어 있나 — 이어 쓰기가 조에서 떠내려가지 않게 하는 닻
//   조 안 근음 비율(85% 밑이면 벌점) · 으뜸화음이 너무 오래 안 나오면 벌점 · 긴장 큰 종류(반감 · 감 · alt · 증)가 많으면 벌점
double Session::tonal_score(const std::vector<Bar> &bars, bool update) {
    static const bool DIA_MAJ[12] = {1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1}, DIA_MIN[12] = {1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0};
    int n = 0, dia = 0, tense = 0, first_tonic = -1, last_tonic = -1, chrom = 0, n_tonic = 0, hd = 0, misfit = 0;
    //                         종류:  maj maj7 min m7 dom alt sus hdim dim aug mM7   (gen.cpp 와 같은 표)
    static const int FIT_MAJ[12] = {0b00001000011, 0, 0b00001001100, 0, 0b00000001100, 0b00000000011, 0, 0b00001010001, 0, 0b00000001100, 0, 0b00110000000};
    static const int FIT_MIN[12] = {0b10000001100, 0, 0b00110000000, 0b00000000011, 0, 0b00000001100, 0, 0b00001111101, 0b00000000011, 0, 0b00000010001, 0b00100000000};
    int prev_root = -1;
    for (size_t i = 0; i < bars.size(); i++)
        for (auto &c : bars[i]) {
            n++;
            dia += (m.minor ? DIA_MIN : DIA_MAJ)[c[1]];
            const bool tonic = c[1] == 0 && (m.minor ? (c[2] == QA_MIN || c[2] == QA_M7 || c[2] == QA_MM7) : (c[2] == QA_MAJ || c[2] == QA_MAJ7));
            if (tonic) { if (first_tonic < 0) first_tonic = (int)i; last_tonic = (int)i; n_tonic++; }
            hd += c[2] == QA_HDIM;
            misfit += (m.minor ? DIA_MIN : DIA_MAJ)[c[1]] && !(((m.minor ? FIT_MIN : FIT_MAJ)[c[1]] >> c[2]) & 1);
            tense += (c[2] == QA_HDIM && !m.minor) || c[2] == QA_DIM || c[2] == QA_ALT || c[2] == QA_AUG;
            if (prev_root >= 0) { const int mv = pmod(c[1] - prev_root, 12); chrom += mv == 1 || mv == 11 || mv == 6; }
            prev_root = c[1];
        }
    if (!n) return 0;
    const double sp = spice();
    double s = 0;
    s += 5.0 * std::min(0.0, (double)dia / n - (.9 - .25 * sp));                          // 조 안 근음
    s -= 3.0 * std::max(0.0, (double)tense / n - (.08 + .22 * sp));                        // 긴장 큰 종류
    s -= 2.5 * std::max(0.0, (double)chrom / n - (.06 + .2 * sp));                         // 반음 · 증4도 근음 움직임
    s -= 4.0 * std::max(0.0, (double)misfit / n - (m.src == "jazz" ? .2 + .3 * sp : .1 + .25 * sp));   // 조 안 근음인데 종류가 안 맞음 (다른 조로 기울어짐)
    const int gap = first_tonic < 0 ? since_tonic + (int)bars.size() : std::max(since_tonic + first_tonic, (int)bars.size() - 1 - last_tonic);
    if (first_tonic < 0) s -= .8;
    s += .3 * std::min(n_tonic, 2);                                                        // 8마디에 으뜸화음 두 번쯤 (ii-V 만 줄줄이 이어지지 않게)
    if (m.minor) s -= 3.0 * std::max(0.0, (double)hd / n - .14);                           // 단조: 반감 ii 가 마디마다 나오지 않게
    s -= .35 * std::max(0, gap - 8);                                                       // 으뜸화음 없이 8마디 넘게 가면
    if (update) since_tonic = last_tonic < 0 ? since_tonic + (int)bars.size() : (int)bars.size() - 1 - last_tonic;
    return s;
}

std::vector<Bar> Session::to_deg(const std::vector<Bar> &a) const {
    std::vector<Bar> o;
    for (auto &b : a) { Bar x; for (auto &c : b) x.push_back({c[0], pmod(c[1] - S.key.pc, 12), c[2]}); o.push_back(x); }
    return o;
}
std::vector<Bar> Session::to_abs(const std::vector<Bar> &d) const {
    std::vector<Bar> o;
    for (auto &b : d) { Bar x; for (auto &c : b) x.push_back({c[0], (S.key.pc + c[1]) % 12, c[2]}); o.push_back(x); }
    return o;
}

std::vector<Bar> Session::new_prog(char sec, const std::vector<Bar> *prev, int n_change, const std::vector<Bar> *ctx, const std::map<int, Bar> *must,
                                   int n_bars) {
    const std::vector<std::pair<char, int>> form = {{sec, n_bars}};
    const std::vector<int> beats = m.ts == 4 ? std::vector<int>{0, 2} : std::vector<int>{0};
    std::vector<Bar> best; double bs = -1e9;
    const uint64_t base = rng.next();
    const int tries = prev ? 3 : 6;
    auto n_diff = [&](const std::vector<Bar> &bars) {                            // 앞 진행과 다른 마디 수 (겹치는 길이만)
        int d = 0;
        for (size_t i = 0; prev && i < std::min(bars.size(), prev->size()); i++) d += bars[i] != (*prev)[i];
        return d;
    };
    for (int k = 0; k < tries + 4; k++) {
        if (k >= tries && !(prev && n_diff(best) == 0)) break;                    // 바꾸라 한 마디를 AI 가 그대로 다시 쓰면 → 조금 더 뜨겁게 다시
        const double temp = m.ctemp * (k < tries ? 1.0 : 1.15 + .1 * (k - tries));
        std::map<int, Bar> fixed;
        if (prev) {                                                               // 바꿀 마디 고르기 (나머지는 그대로 물려받음)
            const int np = std::min<int>((int)prev->size(), n_bars);
            std::vector<int> idx;
            for (int i = 0; i < np; i++) idx.push_back(i);
            Rng r2(base + 1000 + k);
            for (int i = np - 1; i > 0; i--) std::swap(idx[i], idx[r2.index(i + 1)]);
            std::set<int> change(idx.begin(), idx.begin() + std::min(n_change, np));
            for (int i = 0; i < np; i++) if (!change.count(i)) fixed[i] = (*prev)[i];
        }
        if (must) for (auto &kv : *must) fixed[kv.first] = kv.second;
        const ChordCtl ctl = chord_ctl();
        auto bars = progression(M.chord, form, m.minor, m.src, m.ts, beats, temp, .92, base + k, ctx, 'A', fixed.empty() ? nullptr : &fixed, &ctl);
        double sc = score8(bars, m.src == "jazz") + r_jit(base, k) + tonal_score(bars, false);
        if (prev && n_diff(bars) == 0) sc -= 5;                                   // 하나도 안 바뀌면 안 됨
        uint64_t h = 1469598103934665603ull;
        for (auto &b : bars) for (auto &c : b) h = (h ^ (uint64_t)(c[0] * 1000 + c[1] * 20 + c[2])) * 1099511628211ull;
        for (auto x : prog_hist) if (x == h) sc -= 3;                             // 최근에 쓴 진행과 똑같으면 피함
        if (sc > bs) { bs = sc; best = bars; }
    }
    prog_score = bs;
    return best;
}

// ---------------- 선율: AI 가 쓰고 공식 점수로 고르기 ----------------

double mel_score(const std::vector<BNote> &notes, const std::vector<Bar> &bars, double dens_target) {
    using tk::TPB;
    if (notes.empty()) return -9;
    double good = 0; int tot = 0, rep = 0, lo = 999, hi = -1;
    for (size_t i = 0; i < notes.size(); i++) {
        auto &n = notes[i];
        lo = std::min(lo, n.p); hi = std::max(hi, n.p);
        const Bar &cb = bars[n.bi];
        const ChordTok *ch = nullptr;
        for (auto &c : cb) if (c[0] * TPB <= n.on) ch = &c;
        if (!ch && !cb.empty()) ch = &cb[0];
        if (!ch) continue;
        if (n.on % TPB == 0 || n.d >= TPB) {
            tot++;
            int iv = pmod(n.p - (*ch)[1], 12);
            auto &T = TONES_Q[(*ch)[2]], &E = TENS_Q[(*ch)[2]];
            good += std::count(T.begin(), T.end(), iv) ? 1 : std::count(E.begin(), E.end(), iv) ? .6 : 0;
        }
        if (i && n.p == notes[i - 1].p) rep++;
    }
    return good / std::max(1, tot) - .5 * rep / notes.size() - .15 * std::fabs((double)notes.size() / bars.size() - dens_target) +
           .2 * std::min(1.0, (hi - lo) / 12.0);
}

std::vector<BN> Session::write_melody(const std::vector<Bar> &bars, const std::vector<const ChordTok *> &nexts, int bar0, double temp,
                                      double dens_target, const std::map<int, std::vector<MelNote>> *copy, int tries) {
    using tk::TPB;
    auto base = w->r.snapshot();
    double bs = -1e18;
    std::vector<BNote> best;
    Runner::Snap best_snap;
    uint64_t seed0 = rng.next();
    const int pp = w->prev_p, lo = m.mel_lo + reg_shift(), hi = m.mel_hi + reg_shift();
    w->consonance = consonance();
    for (int k = 0; k < tries; k++) {
        if (k) w->r.restore(base);
        w->prev_p = pp;                                                            // 앞 단락 마지막 음에서 이어 씀
        w->rng.reseed(seed0 + k);
        std::vector<BNote> out, scored;
        for (size_t bi = 0; bi < bars.size(); bi++) {
            const std::vector<MelNote> *force = nullptr;
            if (copy) { auto it = copy->find((int)bi); if (it != copy->end()) force = &it->second; }
            auto ns = w->bar(bars[bi], nexts[bi], lo, hi, temp, .92, m.leap, force, m.maxn, bi % 8 == 7);
            for (auto &n : ns) { out.push_back({(int)bi, n.on, n.d, n.p}); if (!force) scored.push_back(out.back()); }
        }
        double sc = mel_score(scored, bars, dens_target);
        if (sc > bs) { bs = sc; best = out; best_snap = w->r.snapshot(); }
    }
    w->r.restore(best_snap);
    if (!best.empty()) w->prev_p = best.back().p;
    // 틱 → 박, 다음 음과 겹치면 자르기
    std::vector<BN> xs;
    for (auto &n : best) xs.push_back({(double)(bar0 + n.bi) * S.ts + (double)n.on / TPB, (double)n.d / TPB, n.p});
    std::sort(xs.begin(), xs.end(), [](const BN &a, const BN &b) { return a.t < b.t || (a.t == b.t && (a.d < b.d || (a.d == b.d && a.p < b.p))); });
    std::vector<BN> out;
    const double end = (double)(bar0 + (int)bars.size()) * S.ts;
    for (size_t i = 0; i < xs.size(); i++) {
        double d = xs[i].d;
        if (i + 1 < xs.size()) d = std::min(d, xs[i + 1].t - xs[i].t);
        d = std::min(d, end - xs[i].t);
        if (d > .05) out.push_back({xs[i].t, d, xs[i].p});
    }
    return S.fix_avoid(out, m.jazzy);
}

// ---------------- 세션 ----------------
// 앞 분위기 조에서 가까운 조 (같은 으뜸음 > 나란한조 > 5도 이웃 순) — 분위기 바꿀 때 갑자기 먼 조로 튀지 않게
static std::string near_key(const Mood &m, const Key &k, Rng &r) {
    auto dist = [&](const std::string &name) {
        Key x(name);
        int a = x.pc, b = k.pc;
        if (x.minor != k.minor) { if (x.minor) a = (a + 3) % 12; else b = (b + 3) % 12; }   // 나란한조로 맞춰 견줌
        int f = 0;
        for (int d = 0; d < 12; d++) if ((b + 7 * d) % 12 == a) { f = std::min(d, 12 - d); break; }
        return f + (x.minor != k.minor ? .5 : 0) + r.uniform(0, .3);
    };
    std::string best = m.keys[0]; double bd = 1e9;
    for (auto &kn : m.keys) { double d = dist(kn); if (d < bd) { bd = d; best = kn; } }
    return best;
}

Session::Session(const Mood &m_, const Models &M_, uint64_t seed, bool intro, double prev_bpm, const Key *near, int last_p,
                 const std::string &last_part, const Params *p)
    : m(m_), M(M_), S(m_.keys[Rng(seed).index(m_.keys.size())], m_.bpm, m_.ts, m_.swing, seed * 7 + 3), rng(seed), need_intro(intro) {
    if (p) P = *p;
    if (near) { Rng r(seed ^ 0x5bd1e995); S.key = Key(near_key(m, *near, r)); }
    w = std::make_unique<MelodyWriter>(&M.melody, m.ts, "head", m.feel, m.tempo, m.minor, m.dens, m.reg, rng.next(), m.src, ct_level());
    S.b9_rate = .2 + .7 * spice();
    S.crunch = spice();
    tempo_pts.push_back({0, prev_bpm > 0 ? prev_bpm : base_bpm()});
    if (prev_bpm > 0) transition(prev_bpm, near, last_p, last_part);
}

int Session::last_mel_pitch(int bar, std::string *part) const {
    const Note *best = nullptr;
    const double t = (double)bar * S.ts;
    for (const Note *n : S.mel) if (!n->dead && n->t < t - 1e-6 && (!best || n->t > best->t)) best = n;
    if (!best) return -1;
    if (part) *part = S.names[best->part];
    return best->p;
}

double Session::bpm_at(double b) const {
    const auto &p = tempo_pts;
    if (p.size() == 1 || b <= p[0].first) return p[0].second;
    for (size_t i = 0; i + 1 < p.size(); i++)
        if (p[i].first <= b && b <= p[i + 1].first)
            return p[i].second + (p[i + 1].second - p[i].second) * (b - p[i].first) / std::max(1e-9, p[i + 1].first - p[i].first);
    return p.back().second;
}

double Session::sec(double beat) {
    if (pts_seen != tempo_pts.size()) {                                           // 템포 점이 늘었으면 그 뒤 계산은 버림
        double mn = 1e18;
        for (size_t i = pts_seen; i < tempo_pts.size(); i++) mn = std::min(mn, tempo_pts[i].first);
        size_t keep = (size_t)std::max(1.0, std::floor(mn * 96));
        if (T96.size() > keep) T96.resize(keep);
        pts_seen = tempo_pts.size();
    }
    if (beat < 0) beat = 0;
    size_t need = (size_t)(beat * 96) + 2;
    if (T96.empty()) T96.push_back(0.0);
    while (T96.size() < need) { size_t i = T96.size(); T96.push_back(T96[i - 1] + 60.0 / bpm_at((i - .5) / 96) / 96); }
    double x = beat * 96; size_t k = (size_t)x;
    return T96[k] + (T96[k + 1] - T96[k]) * (x - k);
}

double Session::swing_pos(double b) const {
    const double sw = m.swing;
    if (!sw) return b;
    double f0 = std::floor(b + 1e-9), f = b - f0;
    return f0 + (f <= .5 ? f * 2 * sw : sw + (f - .5) * 2 * (1 - sw));
}

void Session::finish_section(Role role) {
    // 세기: 도입 · 끝 · 이음은 정해진 값, 몸통은 큰 물결(energy)을 따라 (B 는 조금 더)
    static const double F[7] = {.86, .95, 1.0, 1.1, 1.03, .86, .9};
    S.phrase_dynamics(m.jazzy);
    S.sec_factor = (role == R_INTRO || role == R_TAG || role == R_TRANS) ? F[role] : .86 + .26 * energy + (role == R_B ? .03 : 0);
    S.section_dynamics();
    S.declash();
    S.low_mud();
}

void Session::transition(double prev_bpm, const Key *near_key_p, int last_p, const std::string &last_part) {
    // 이음 2마디: 앞 분위기의 마지막 음에서 이어지는 선율 + 두 조에 함께 있는 화음(가능하면) → 새 조의 V, 템포는 서서히
    //   두 배 가까이 빨라지면 반 박으로 이어 붙임 (68 → 88 → 176: 8분음표가 그대로 이어지게) · 느려질 땐 서서히
    const int ts = m.ts, pc = S.key.pc;
    S.cur_sec = n_sec;
    // 첫 마디: 새 조의 ii · IV · vi 중 앞 조 음계에 다 들어 있는 것 (공통 화음)
    Chord c1(pc + 2, m.minor ? Q_M7B5 : Q_M7);
    if (near_key_p) {
        static const int MAJ[7] = {0, 2, 4, 5, 7, 9, 11}, MIN[7] = {0, 2, 3, 5, 7, 8, 10};
        const int *sc = near_key_p->minor ? MIN : MAJ;
        auto in_old = [&](int x) { x = pmod(x - near_key_p->pc, 12); return std::find(sc, sc + 7, x) != sc + 7; };
        std::vector<Chord> cand = m.minor ? std::vector<Chord>{Chord(pc + 5, Q_M7), Chord(pc + 8, Q_MAJ7), Chord(pc + 2, Q_M7B5)}
                                          : std::vector<Chord>{Chord(pc + 2, Q_M7), Chord(pc + 5, Q_MAJ7), Chord(pc + 9, Q_M7)};
        for (auto &c : cand) {
            bool all = true;
            for (int t : c.tones()) all = all && in_old(t);
            if (all) { c1 = c; break; }
        }
    }
    S.add_span(0, ts, c1);
    S.add_span(ts, 2 * ts, Chord(pc + 7, m.minor ? Q_7B9 : Q_7));
    const double r = base_bpm() / prev_bpm;
    const double to = r > 1.55 ? base_bpm() / 2 : base_bpm();                    // 빨라질 땐 반 박으로 이어 붙이고, 느려질 땐 그냥 서서히 (리타르단도)
    tempo_pts = {{0, prev_bpm}, {2.0 * ts - .01, to}};
    if (to != base_bpm()) tempo_pts.push_back({2.0 * ts, base_bpm()});
    if (m.style == 5 || m.style == 6 || m.style == 7) {                          // 피아노 펼침 분위기
        S.piano_pattern(0, 2, m.style == 5 ? "waltz" : "arp", 40); S.pedals(0, 2, ts == 3 ? 3 : 2);
    } else {
        S.comp({0, 1}, ts == 3 ? "waltz" : "ballad", 46);
        S.bass(0, 2, ts == 3 ? "waltz" : "two", 66);
        const std::string dk = m.style == 0 ? "brush" : m.style == 1 ? "brush_swing" : m.style == 3 ? "ride" : m.style == 4 ? "bossa" : "straight";
        S.drums(0, 2, dk, 0, 2, false);
    }
    // 이음 선율: 마지막 음 근처에서 시작해 순차로 새 조에 내려앉음 (앞 선율 악기가 이어 부르고, 새 분위기 선율은 그 끝에서 시작)
    if (last_p > 0) {
        const int lo = std::max(m.mel_lo + reg_shift() - 5, std::min(m.mel_lo + reg_shift(), last_p - 7));
        const int hi = std::min(m.mel_hi + reg_shift() + 5, std::max(m.mel_hi + reg_shift(), last_p + 7));
        // 선율 AI 는 (박, 근음 절대, 종류번호 11) 꼴
        const int q1 = c1.q == Q_MAJ7 ? QA_MAJ7 : c1.q == Q_M7B5 ? QA_HDIM : QA_M7;
        Bar b1{{0, c1.root % 12, q1}}, b2{{0, (pc + 7) % 12, QA_DOM}};
        // 네 번 써 보고 고름 (같은 음 되풀이 · 코드 밖 음 적은 것) — 첫 음은 앞 마지막 음에서 4반음 안
        const Bar b3{{0, pc, m.minor ? QA_MIN : QA_MAJ7}};
        const std::vector<Bar> bb{b1, b2};
        const std::vector<const ChordTok *> nx{&b2[0], &b3[0]};
        const int maxn = std::max(2, std::min(4, m.maxn - 2));
        auto base = w->r.snapshot();
        double bs = -1e18; std::vector<BNote> best; Runner::Snap bsn;
        const uint64_t s0 = rng.next();
        for (int k = 0; k < 4; k++) {
            if (k) w->r.restore(base);
            w->prev_p = last_p; w->rng.reseed(s0 + k);
            std::vector<BNote> out;
            for (int i = 0; i < 2; i++)
                for (auto &n : w->bar(bb[i], nx[i], lo, hi, m.mtemp, .92, i == 0 ? 4 : m.leap, nullptr, i == 0 ? maxn : maxn - 1, i == 1, true))
                    out.push_back({i, n.on, n.d, n.p});
            double sc = mel_score(out, bb, 2.5);
            if (!out.empty()) sc -= .08 * std::abs(out[0].p - last_p);              // 마지막 음 가까이에서 시작
            if (sc > bs) { bs = sc; best = out; bsn = w->r.snapshot(); }
        }
        w->r.restore(bsn);
        if (!best.empty()) w->prev_p = best.back().p;
        std::vector<BN> mel;
        for (auto &n : best) mel.push_back({(double)n.bi * ts + (double)n.on / tk::TPB, (double)n.d / tk::TPB, n.p});
        std::sort(mel.begin(), mel.end(), [](const BN &a, const BN &b) { return a.t < b.t; });
        for (size_t i = 0; i + 1 < mel.size(); i++) mel[i].d = std::min(mel[i].d, mel[i + 1].t - mel[i].t);
        if (!mel.empty()) mel.back().d = std::min(mel.back().d, 2.0 * ts - mel.back().t);
        mel = S.fix_avoid(mel, m.jazzy);
        const std::string part = last_part.empty() ? m.lead : last_part;           // 앞 분위기 선율 악기가 이어 부름
        if (part.find("피아노") != std::string::npos) S.piano_melody(mel, 58, "line");
        else S.lead(part, mel, 66);
        last_mel = mel;
    }
    finish_section(R_TRANS);
    next_bar = 2;
    n_sec++;
}

std::string key_name(int pc, bool minor) {
    static const char *MA[12] = {"C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"};
    static const char *MI[12] = {"Cm", "C#m", "Dm", "Ebm", "Em", "Fm", "F#m", "Gm", "G#m", "Am", "Bbm", "Bm"};
    return (minor ? MI : MA)[pmod(pc, 12)];
}

Section Session::ending() {
    // 끝 4마디(2-5 두 번 → I) + 마지막 화음, 마지막 두 마디에서 느려짐
    S.cur_sec = n_sec;
    plan_note = "";
    const int ts = m.ts, a = next_bar, b = next_bar + 4;
    S.cut_after((double)a * ts);
    std::vector<Bar> tag;
    if (ts == 3) tag = m.minor ? std::vector<Bar>{{{0, 2, 7}}, {{0, 7, 5}}, {{0, 2, 7}}, {{0, 7, 5}}} : std::vector<Bar>{{{0, 2, 3}}, {{0, 7, 4}}, {{0, 2, 3}}, {{0, 7, 4}}};
    else if (m.minor) tag = {{{0, 2, 7}, {2, 7, 5}}, {{0, 0, 3}}, {{0, 2, 7}, {2, 7, 5}}, {{0, 0, 3}}};
    else tag = {{{0, 4, 3}, {2, 9, 4}}, {{0, 2, 3}, {2, 7, 4}}, {{0, 4, 3}, {2, 9, 4}}, {{0, 2, 3}, {2, 7, 6}}};
    tag.push_back(m.minor ? Bar{{0, 0, m.color == 2 ? 10 : 2}} : Bar{{0, 0, 1}});
    std::vector<Bar> absb;
    for (auto &x : tag) { Bar y; for (auto &c : x) y.push_back({c[0], (S.key.pc + c[1]) % 12, c[2]}); absb.push_back(y); }
    S.add_chords(a, absb, m.color);
    std::vector<Bar> mb(absb.begin(), absb.begin() + 4);
    std::vector<const ChordTok *> nexts;
    for (int i = 0; i < 4; i++) nexts.push_back(&absb[i + 1][0]);
    const double dt = (m.dens == 0 ? 2 : m.dens == 1 ? 3.5 : m.dens == 2 ? 5.5 : 8) * .8;
    auto mel = write_melody(mb, nexts, a, m.mtemp, dt, nullptr);
    last_mel = mel;
    const double slow = m.style == 2 || m.style == 4 ? .75 : m.style == 8 ? .78 : m.style == 0 || m.style == 1 ? .68 : .7;
    const double last = m.style == 2 || m.style == 4 || m.style == 8 ? .7 : .6;
    const double bb = bpm_at((double)a * ts);
    tempo_pts.push_back({(double)(b - 2) * ts, bb});
    tempo_pts.push_back({(double)b * ts, bb * slow});
    tempo_pts.push_back({(double)b * ts + .01, bb * last});
    arrange(R_TAG, a, b, mel);
    finish_section(R_TAG);
    next_bar = b + 1;
    return {R_TAG, a, b + 1, n_sec++};
}

void section_to_sheet(Session &ss, const Section &sec, Sheet &sh, double t_off) {
    Song &S = ss.S;
    const int ts = S.ts;
    for (auto &sp : S.spans)
        if ((double)sec.a * ts - 1e-6 <= sp.a && sp.a < (double)sec.b * ts - 1e-6)
            sh.chords.push_back({t_off + ss.sec(sp.a), t_off + ss.sec(sp.b), sp.c});
    for (auto &n : S.pool) {
        if (n.sec != sec.sec || n.dead) continue;
        const bool drum = S.is_drum_part(n.part);
        double t0, t1;
        if (drum) { t0 = ss.sec(n.t); t1 = ss.sec(n.t + n.d); }
        else { t0 = ss.sec(ss.swing_pos(n.t)); t1 = ss.sec(ss.swing_pos(n.t + n.d) - .02); }
        t1 = std::max(t1, t0 + .06);
        sh.notes.push_back({sh.part(S.names[n.part], drum), t_off + t0, t_off + t1, n.p, n.v});
    }
    for (auto &p : S.pedal)
        if ((double)sec.a * ts - 1e-6 <= p.first && p.first < (double)sec.b * ts - 1e-6)
            sh.pedals.push_back({t_off + ss.sec(p.first), t_off + ss.sec(p.second)});
}
