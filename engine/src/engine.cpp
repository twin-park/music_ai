#include "engine.h"
#include "util.h"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <ctime>
#include <sstream>

// 악기 이름(대괄호 안 낱말) → (엔진, 목표 크기 dB, 좌우, 잔향, 저역컷) — score/play.py INST 와 같은 순서 (낱말 맞추기 순서가 중요)
const std::vector<InstDef> &insts() {
    static const std::vector<InstDef> I = {
        {"피아노", 0, "", 0, 0, false, -18, -0.05, 0.26, 40},
        // (11-13 오후 새 악기 중 이름이 다른 악기 이름을 품는 것 — 먼저 맞춰야 함: 스틸팬 ⊃ 스틸 · 클린기타 ⊃ 기타 · 하프시코드 ⊃ 하프 · …)
        {"스틸팬", 1, "gu", 0, 114, false, -21, 0.15, 0.30, 120},
        {"클린기타", 1, "gu", 0, 27, false, -23, -0.3, 0.22, 90},
        {"하프시코드", 1, "gu", 0, 6, false, -22, -0.2, 0.30, 100},
        {"슬랩베이스", 1, "gu", 0, 36, false, -21.5, 0.05, 0.08, 30},
        {"신스베이스", 1, "gu", 0, 38, false, -22, 0.0, 0.08, 30},
        {"빠른현악", 1, "gu", 0, 48, false, -25, 0.1, 0.45, 90},
        {"팝드럼", 1, "gu", 128, 0, true, -27, -0.1, 0.16, 40},
        {"808드럼", 1, "gu", 128, 25, true, -27, 0.0, 0.14, 40},
        {"테너", 1, "gu", 0, 66, false, -18, 0.3, 0.30, 90},
        {"알토", 1, "gu", 0, 65, false, -18.5, 0.3, 0.30, 110},
        {"뮤트", 1, "gu", 0, 59, false, -19.5, 0.3, 0.30, 150},
        {"트럼펫", 1, "gu", 0, 56, false, -19, 0.3, 0.30, 150},
        {"비브라폰", 1, "gu", 0, 11, false, -21, -0.3, 0.30, 120},
        {"나일론", 1, "gu", 0, 24, false, -21, -0.3, 0.20, 80},
        {"스틸", 1, "gu", 0, 25, false, -23, -0.3, 0.20, 90},                 // (11-13 새 악기 — "기타" 보다 앞에: 이름에 '기타' 가 들어 있어서)
        {"기타", 1, "gu", 0, 26, false, -23, -0.35, 0.20, 80},
        {"로즈", 1, "gu", 0, 4, false, -22, -0.2, 0.30, 80},
        {"플루트", 1, "sso", 0, 14, false, -19.5, 0.25, 0.35, 250},
        {"첼로", 1, "sso", 0, 8, false, -21, -0.3, 0.45, 50},
        {"바이올린", 1, "sso", 0, 2, false, -22, 0.35, 0.45, 200},
        {"현악", 1, "gu", 0, 49, false, -25, 0.0, 0.50, 100},
        {"일렉", 1, "gu", 0, 33, false, -22, 0.05, 0.08, 30},
        {"첼레스타", 1, "gu", 0, 8, false, -23, 0.3, 0.40, 200},
        {"베이스", 1, "gu", 0, 32, false, -21.5, 0.05, 0.08, 30},
        {"브러시", 1, "gu", 128, 40, true, -31, -0.12, 0.22, 60},
        {"드럼", 1, "gu", 128, 32, true, -27, -0.1, 0.18, 40},
        // 11-13 새 악기: 하프 · 클라리넷 · 오보에 · 호른 · 글로켄 (Sonatina) · 마림바 (GeneralUser) — 상황에 맞는 음색을 고르려고
        {"하프", 1, "sso", 0, 1, false, -21, -0.25, 0.40, 60},
        {"클라리넷", 1, "sso", 0, 20, false, -20, 0.2, 0.32, 120},
        {"오보에", 1, "sso", 0, 16, false, -21, 0.25, 0.32, 200},
        {"호른", 1, "sso", 0, 29, false, -22, -0.15, 0.45, 60},
        {"글로켄", 1, "sso", 0, 39, false, -26, 0.3, 0.35, 300},
        {"마림바", 1, "gu", 0, 12, false, -21, 0.2, 0.25, 100},
        // 11-13 오후: 장르 분위기 17개용 (GeneralUser GS)
        {"클라비넷", 1, "gu", 0, 7, false, -23, 0.25, 0.20, 90},
        {"오르간", 1, "gu", 0, 16, false, -25, -0.25, 0.30, 80},
        {"하모니카", 1, "gu", 0, 22, false, -20, 0.2, 0.30, 150},
        {"반도네온", 1, "gu", 0, 23, false, -20, 0.2, 0.32, 100},
        {"아코디언", 1, "gu", 0, 21, false, -21, -0.2, 0.30, 100},
        {"트롬본", 1, "gu", 0, 57, false, -20, -0.25, 0.30, 70},
        {"브라스", 1, "gu", 0, 61, false, -21, 0.1, 0.30, 90},
        {"소프라노", 1, "gu", 0, 64, false, -19, 0.3, 0.30, 150},
        {"휘슬", 1, "gu", 0, 78, false, -21, 0.25, 0.32, 250},
        {"리코더", 1, "gu", 0, 74, false, -20, 0.25, 0.32, 200},
        {"피들", 1, "gu", 0, 110, false, -20, 0.3, 0.30, 150},
        {"반조", 1, "gu", 0, 105, false, -23, -0.3, 0.20, 100},
        {"칼림바", 1, "gu", 0, 108, false, -21, 0.2, 0.35, 150},
        {"뮤직박스", 1, "gu", 0, 10, false, -23, 0.25, 0.40, 250},
        {"실로폰", 1, "gu", 0, 13, false, -21, 0.2, 0.25, 150},
        {"따뜻한패드", 1, "gu", 0, 89, false, -27, 0.0, 0.45, 100},
        {"신스리드", 1, "gu", 0, 81, false, -22, 0.2, 0.30, 120},
        {"폴리신스", 1, "gu", 0, 90, false, -25, -0.2, 0.30, 100},
        {"합창", 1, "gu", 0, 52, false, -24, 0.0, 0.50, 100},
        {"튜바", 1, "gu", 0, 58, false, -21, -0.1, 0.20, 30},
        {"타이코", 1, "gu", 0, 116, false, -22, 0.0, 0.30, 30},
        {"팀파니", 1, "gu", 0, 47, false, -22, 0.0, 0.35, 30},
        {"피치카토", 1, "gu", 0, 45, false, -23, 0.2, 0.30, 60},
    };
    return I;
}

int inst_of(const std::string &part) {
    auto &I = insts();
    for (size_t i = 0; i < I.size(); i++) if (part.find(I[i].kw) != std::string::npos) return (int)i;
    return -1;
}

struct WindDef { const char *kw; double scoop, fall, vib_rate, vib_depth; };
static const WindDef WIND[] = {{"테너", .5, .22, 5.2, 16}, {"알토", .45, .22, 5.4, 14}, {"뮤트", .4, .2, 4.8, 9}, {"트럼펫", .35, .2, 4.8, 10},
                               {"플루트", .1, 0, 5.4, 12}, {"첼로", .1, 0, 5.6, 14}, {"바이올린", .1, 0, 5.8, 14},
                               {"클라리넷", .15, 0, 5.0, 8}, {"오보에", .12, 0, 5.4, 10}, {"호른", .2, .1, 4.8, 8},
                               {"소프라노", .4, .2, 5.4, 12}, {"트롬본", .35, .2, 4.8, 9}, {"브라스", .25, .15, 4.8, 7}, {"하모니카", .3, .15, 5.6, 14},
                               {"휘슬", .1, 0, 5.6, 10}, {"리코더", .05, 0, 5.2, 6}, {"피들", .1, 0, 5.8, 16}, {"반도네온", .05, 0, 5.0, 6}};
static const WindDef *wind_of(const std::string &kw) {
    for (auto &w : WIND) if (kw == w.kw) return &w;
    return nullptr;
}
static int bend_val(double cents) { return (int)std::max(-8191.0, std::min(8191.0, cents / 200 * 8192)); }

// ---------------- 시작 ----------------
bool Engine::init(const std::string &data_dir, std::string *err) {
    data = data_dir;
    if (!M.chord.load(data + "/chord.bin", err) || !M.melody.load(data + "/melody.bin", err)) return false;
    const char *fl = std::getenv("CAR_BGM_FLUID");
#ifdef _WIN32
    std::string flp = fl ? fl : exe_dir() + "\\libfluidsynth-3.dll";
#elif defined(__ANDROID__)
    std::string flp = fl ? fl : "libfluidsynth.so";                       // APK 의 lib/<abi>/ (앱 이름 공간에서 찾음)
#else
    std::string flp = fl ? fl : "libfluidsynth.so.3";
#endif
    if (!FL.load(flp)) { if (err) *err = FL.err; return false; }
    sf_gu = data + "/sf/gu_small.sf2";                                    // 쓰는 악기 14개만 남긴 판(8MB) — 없으면 원본(32MB)
    if (FILE *fp = std::fopen(sf_gu.c_str(), "rb")) std::fclose(fp); else sf_gu = data + "/sf/GeneralUser-GS.sf2";
    sf_sso = data + "/sf/sso_small.sf2";
    amb.open(data + "/amb");
    {                                                                     // 지휘자 (없거나 틀려도 음악은 됨 — 직접 고르기만)
        std::string ce;
        if (!cond.load(data + "/conductor", &ce)) std::fprintf(stderr, "지휘자 못 읽음: %s\n", ce.c_str());
        trk_talk.assign(insts().size(), .3f);
        for (size_t i = 0; i < insts().size(); i++) trk_talk[i] = (float)cond.talk_of(insts()[i].kw);
    }
    if (!piano.open(data + "/piano")) { if (err) *err = "피아노 샘플이 없음: " + data + "/piano"; return false; }
    piano.preload_common();                                              // 자주 쓰는 음역만 뒤에서 미리 (나머지는 예약할 때)
    std::string t;
    if (read_file(data + "/tune.txt", t)) {
        std::istringstream in(t); std::string ln;
        while (std::getline(in, ln)) {
            if (ln.empty() || ln[0] == '#') continue;
            std::istringstream w(ln); std::string kw; int n; double c, ms;
            if (w >> kw >> n >> c >> ms) tune[kw][n] = {std::max(-30.0, std::min(30.0, c)), std::max(0.0, ms) / 1000};
        }
    }
    if (read_file(data + "/calib.txt", t)) {
        std::istringstream in(t); std::string ln;
        while (std::getline(in, ln)) {
            if (ln.empty() || ln[0] == '#') continue;
            std::istringstream w(ln); std::string mood, kw; double v;
            if (w >> mood >> kw >> v) { if (kw == "_master") calib[mood].master_db = v; else calib[mood].act[kw] = v; }
        }
    }
    tracks.resize(insts().size());
    for (auto *v : {&sendL, &sendR, &dryL, &dryR, &wetL, &wetR}) v->assign(Convolver::B, 0.f);
    rev_a.make(2.4, 1);
    rev_sec = 2.4;
    return true;
}

Engine::~Engine() {
    for (auto &t : tracks)
        if (t && t->syn) { FL.delete_synth(t->syn); FL.delete_settings(t->set); }
}

// 켤 때마다 다른 곡: 나노초 시계 + 차례 번호 섞기 (같은 초에 두 번 켜도 다름)
static uint64_t fresh_seed() {
    static uint64_t n = 0;
    if (const char *e = std::getenv("CAR_BGM_SEED")) return std::strtoull(e, nullptr, 10) * 1000003ull + ++n;   // 시험용: 늘 같은 곡
    uint64_t x = (uint64_t)std::chrono::system_clock::now().time_since_epoch().count() ^ (uint64_t)std::chrono::steady_clock::now().time_since_epoch().count() * 0x9E3779B97F4A7C15ull;
    x += ++n * 0xBF58476D1CE4E5B9ull;
    x ^= x >> 31; x *= 0x94D049BB133111EBull; x ^= x >> 29;
    return x;
}

std::pair<double, double> Engine::tune_of(const std::string &kw, int p) const {
    auto it = tune.find(kw);
    if (it == tune.end() || it->second.empty()) return {0, 0};
    const std::pair<double, double> *best = nullptr; int bd = 999;
    for (auto &kv : it->second) if (std::abs(kv.first - p) < bd) { bd = std::abs(kv.first - p); best = &kv.second; }
    return *best;
}

Track &Engine::track(int i) {
    {
        std::lock_guard<std::mutex> g(mtx);
        if (tracks[i]) return *tracks[i];
    }
    auto tr = std::make_unique<Track>();
    const InstDef &d = insts()[i];
    tr->def = &d;
    if (d.engine == 1) {
        tr->set = FL.new_settings();
        FL.setnum(tr->set, "synth.sample-rate", SR);
        FL.setnum(tr->set, "synth.gain", 0.7);
        FL.setint(tr->set, "synth.reverb.active", 0);
        FL.setint(tr->set, "synth.chorus.active", 0);
        FL.setint(tr->set, "synth.polyphony", 256);
        // 악기 하나가 쓰는 샘플만 메모리에 (사운드폰트 통째로 X) — 9번 채널도 드럼 아닌 악기면 같은 악기로
        if (!std::getenv("CAR_BGM_FULLSF")) {
            FL.setint(tr->set, "synth.dynamic-sample-loading", 1);
            if (!d.drum) FL.setint(tr->set, "synth.drums-channel.active", 0);
        }
        tr->syn = FL.new_synth(tr->set);
        FL.sfload(tr->syn, (std::string(d.font) == "sso" ? sf_sso : sf_gu).c_str(), 1);
        if (d.drum) FL.program_change(tr->syn, 9, d.prog);
        else
            for (int c = 0; c < 16; c++) {
                if (c == 9 && std::getenv("CAR_BGM_FULLSF")) continue;
                FL.bank_select(tr->syn, c, d.bank); FL.program_change(tr->syn, c, d.prog);
                FL.cc(tr->syn, c, 7, 110); FL.cc(tr->syn, c, 11, 100);
            }
    }
    if (d.hp > 0) for (auto &b : tr->hp) b.design(true, d.hp);
    tr->bl.assign(Convolver::B, 0.f); tr->br.assign(Convolver::B, 0.f);
    std::lock_guard<std::mutex> g(mtx);
    tracks[i] = std::move(tr);
    return *tracks[i];
}

void Engine::push_events(Track &tr, std::vector<Ev> &evs) {
    if (evs.empty()) return;
    auto lt = [](const Ev &a, const Ev &b) { return a.t < b.t || (a.t == b.t && a.prio < b.prio); };
    std::stable_sort(evs.begin(), evs.end(), lt);
    std::lock_guard<std::mutex> g(mtx);
    if (tr.qh > 4096) { tr.q.erase(tr.q.begin(), tr.q.begin() + tr.qh); tr.qh = 0; }
    size_t mid = tr.q.size();
    tr.q.insert(tr.q.end(), evs.begin(), evs.end());
    std::inplace_merge(tr.q.begin() + tr.qh, tr.q.begin() + mid, tr.q.end(), lt);
}

void Engine::cut_at(double t, double ring) {
    std::lock_guard<std::mutex> g(mtx);
    // 잘린 단락은 악보 · 상태에서도 뺌 (걸친 단락은 t 앞 음만 남김)
    while (!score_log.empty() && score_log.back().t >= t - 1e-6) score_log.pop_back();
    if (!score_log.empty()) {
        Block &b = score_log.back();
        const double tr0 = t - run_t0.load();
        auto &ns = b.sh.notes;
        ns.erase(std::remove_if(ns.begin(), ns.end(), [&](const TNote &n) { return n.t0 >= tr0 - 1e-6; }), ns.end());
        for (auto &n : ns) n.t1 = std::min(n.t1, tr0 + ring);
        auto &cs = b.sh.chords;
        cs.erase(std::remove_if(cs.begin(), cs.end(), [&](const TChord &c) { return c.t0 >= tr0 - 1e-6; }), cs.end());
        for (auto &c : cs) c.t1 = std::min(c.t1, tr0);
        b.text = b.head + b.sh.text(false);
    }
    while (!marks.empty() && marks.back().first >= t - 1e-6) marks.pop_back();
    for (auto &tp : tracks) {
        if (!tp) continue;
        Track &tr = *tp;
        std::vector<Ev> keep(tr.q.begin(), tr.q.begin() + tr.qh);
        for (size_t k = tr.qh; k < tr.q.size(); k++)
            if (tr.q[k].t < t) { Ev e = tr.q[k]; if (ring > 0 && e.type == EV_PIANO) e.t1 = std::min(e.t1, t + ring); keep.push_back(e); }
        if (ring <= 0) keep.push_back({t, -1, EV_ALLOFF, 0, 0, 0, 0});
        else if (tr.def->engine == 0) keep.push_back({t, -2, EV_CAP, 0, 0, 0, t + ring});
        else {
            // 울리던 음: 끝 신호를 t + ring 안으로 당김 (새 음은 t 부터 따로 — 채널 돌려쓰기로 안 겹침)
            std::map<std::pair<int, int>, int> act;
            for (auto &e : tr.q) {
                if (e.t >= t) break;
                if (e.type == EV_ON) act[{e.ch, e.a}]++;
                else if (e.type == EV_OFF) { auto it = act.find({e.ch, e.a}); if (it != act.end() && it->second > 0) it->second--; }
                else if (e.type == EV_ALLOFF) act.clear();
            }
            for (size_t k = tr.qh; k < tr.q.size(); k++) {
                const Ev &e = tr.q[k];
                if (e.t < t || e.type != EV_OFF) continue;
                auto it = act.find({e.ch, e.a});
                Ev x = e; x.prio = -3;
                if (it != act.end() && it->second > 0) { it->second--; x.t = std::min(e.t, t + ring); }
                else x.t = t;
                keep.push_back(x);
            }
            for (auto &kv : act) for (int i = 0; i < kv.second; i++) keep.push_back({t + ring, -3, EV_OFF, kv.first.first, kv.first.second, 0, 0});
            for (double &b : tr.busy) b = std::min(b, t + ring);
        }
        std::stable_sort(keep.begin() + tr.qh, keep.end(), [](const Ev &a, const Ev &b) { return a.t < b.t || (a.t == b.t && a.prio < b.prio); });
        tr.q = keep;
        std::vector<TNote> h;
        for (auto n : tr.held) if (n.t0 < t) { n.t1 = std::min(n.t1, t + ring); h.push_back(n); }
        tr.held = h;
    }
}

int Engine::phrase_cut(Session &os, double t0, double now, double *tc) {
    // 다음 2마디 덩어리 끝 (단락 시작 기준 짝수 마디) 이 4초 안이면 거기, 아니면 다음 마디 — 선율 한 덩어리를 끝까지 들려줌
    const int ts = os.m.ts;
    int first = -1, phrase = -1;
    for (int k = 0; k <= os.next_bar; k++) {
        const double tk = t0 + os.sec((double)k * ts);
        if (tk < now + .4) continue;
        if (first < 0) first = k;
        int a = 0;
        for (auto &h : os.hist) if (h.a <= k) a = h.a;
        if ((k - a) % 2 == 0 && tk <= now + 4.0) { phrase = k; break; }
        if (tk > now + 4.0) break;
    }
    const int k = phrase >= 0 ? phrase : first >= 0 ? first : os.next_bar;
    *tc = t0 + os.sec((double)k * ts);
    return k;
}

void Engine::set_mood_mix(const Mood &m, double t) {
    auto &I = insts();
    auto c = calib.find(m.id);
    std::lock_guard<std::mutex> g(mtx);
    for (size_t i = 0; i < I.size(); i++) {
        // 이 분위기에서 못 잰 악기는 다른 분위기에서 잰 값의 평균 (없으면 -30)
        double act = -30, sum = 0; int n = 0;
        for (auto &kv : calib) { auto a = kv.second.act.find(I[i].kw); if (a != kv.second.act.end()) { sum += a->second; n++; } }
        if (n) act = sum / n;
        if (c != calib.end()) { auto a = c->second.act.find(I[i].kw); if (a != c->second.act.end()) act = a->second; }
        gain_sched.push_back({t, (int)i, I[i].db - act});
    }
    master_sched.push_back({t, c != calib.end() ? c->second.master_db : 0.0});
    rev_switch_t = t; rev_next_sec = m.reverb;
}

// ---------------- 연주: 사운드폰트 악기 (play.py perform) ----------------
void Engine::perform_fluid(Track &tr, std::vector<TNote> notes, double cut, std::vector<Ev> &out, Rng &rng) {
    const InstDef &d = *tr.def;
    const std::string kw = d.kw;
    const double tick = 1.0 / 960;
    if (d.drum) {
        // 같은 북을 다시 치면 앞 소리 끝을 그 직전으로 (안 그러면 새로 친 소리가 앞 음의 끝 신호에 바로 잘림)
        std::sort(notes.begin(), notes.end(), [](const TNote &a, const TNote &b) { return a.t0 < b.t0; });
        for (size_t i = 0; i < notes.size(); i++) {
            for (size_t j = i + 1; j < notes.size(); j++)
                if (notes[j].p == notes[i].p) { notes[i].t1 = std::min(notes[i].t1, notes[j].t0 - .002); break; }
            notes[i].t1 = std::max(notes[i].t1, notes[i].t0 + .01);
            out.push_back({notes[i].t0, 2, EV_ON, 9, notes[i].p, notes[i].v, 0});
            out.push_back({notes[i].t1, 1, EV_OFF, 9, notes[i].p, 0, 0});
        }
        return;
    }
    const WindDef *w = wind_of(kw);
    const bool mono = w || kw == "베이스" || kw == "일렉";
    // 한 줄 악기: 앞에서 남긴 음 + 새 음, 마지막 음은 다음 단락을 볼 때까지 남김
    if (mono) { notes.insert(notes.begin(), tr.held.begin(), tr.held.end()); tr.held.clear(); }
    std::sort(notes.begin(), notes.end(), [](const TNote &a, const TNote &b) {
        return a.t0 < b.t0 || (a.t0 == b.t0 && (a.t1 < b.t1 || (a.t1 == b.t1 && a.p < b.p))); });
    if (mono && cut < 0 && !notes.empty()) { tr.held.push_back(notes.back()); notes.pop_back(); }
    std::vector<TNote> ns = notes;
    if (mono)
        for (size_t i = 0; i + 1 < ns.size(); i++) ns[i].t1 = std::min(ns[i].t1, ns[i + 1].t0 - .008);
    const TNote *after = mono && !tr.held.empty() ? &tr.held[0] : nullptr;          // 남긴 다음 음 (끝 정하기에 씀)
    if (mono && after && !ns.empty()) ns.back().t1 = std::min(ns.back().t1, after->t0 - .008);
    for (size_t i = 0; i < ns.size(); i++) {
        double t0 = ns[i].t0, t1 = ns[i].t1; int p = ns[i].p, v = ns[i].v;
        auto [cents, delay] = tune_of(kw, p);
        const double base = -cents, sh = std::max(0.0, delay - .005);
        double t0s = std::max(0.0, t0 - sh), t1s = std::max(t0s + .03, t1 - sh);
        int c = 0;
        if (!mono) {
            int best = -1;
            for (int x = 0; x < 13; x++) {
                if (x == 9) continue;
                if (best < 0 || std::make_pair(tr.busy[x] > t0s, tr.busy[x]) < std::make_pair(tr.busy[best] > t0s, tr.busy[best])) best = x;
            }
            c = best;
            tr.busy[c] = t1s + .3;
        }
        out.push_back({t0s - 2 * tick, 0, EV_BEND, c, bend_val(base), 0, 0});
        if (w) {
            const TNote *prev = i ? &ns[i - 1] : nullptr;
            const TNote *nxt = i + 1 < ns.size() ? &ns[i + 1] : after;
            double gap_before = prev ? t0 - prev->t1 : 9, gap_after = nxt ? nxt->t0 - t1 : 9, dur = t1s - t0s;
            int e0 = (int)std::max(40.0, std::min(127.0, 30 + v * .85));
            out.push_back({t0s - tick, 0, EV_CC, c, 11, e0, 0});
            if ((gap_before > .25 || (prev && p - prev->p >= 4)) && rng.random() < w->scoop && dur > .12) {   // 스쿱
                double depth = rng.uniform(40, 80);
                for (int k = 0; k < 8; k++) { double x = k / 7.0; out.push_back({t0s + x * .075, 3, EV_BEND, c, bend_val(base - depth * (1 - x) * (1 - x)), 0, 0}); }
            }
            if (dur > .45) {                                                                     // 숨 + 늦은 비브라토
                double st = t0s + std::max(.18, dur * .35);
                for (double t = st; t < t1s - .03; t += .012) {
                    double ramp = std::min(1.0, (t - st) / .35);
                    out.push_back({t, 3, EV_BEND, c, bend_val(base + w->vib_depth * ramp * std::sin(2 * M_PI * w->vib_rate * (t - st))), 0, 0});
                }
                bool last = gap_after > .4;
                for (int k = 1; k <= 8; k++) {
                    double x = k / 8.0;
                    double e = e0 * (1 + .12 * std::sin(M_PI * std::min(1.0, x * 1.4))) * (1 - (last ? .3 : .08) * std::max(0.0, x - .6) / .4);
                    out.push_back({t0s + dur * x, 3, EV_CC, c, 11, (int)std::max(20.0, std::min(127.0, e)), 0});
                }
            } else if (gap_after > .6 && rng.random() < w->fall && dur > .12) {                     // 폴
                for (int k = 0; k < 8; k++) {
                    double x = k / 7.0, tt = t1s - .14 + x * .2;
                    out.push_back({tt, 3, EV_BEND, c, bend_val(base - 190 * std::pow(x, 1.6)), 0, 0});
                    out.push_back({tt, 3, EV_CC, c, 11, (int)(e0 * (1 - .6 * x)), 0});
                }
                t1s += .07;
            }
        }
        out.push_back({t0s, 2, EV_ON, c, p, v, 0});
        out.push_back({t1s, 1, EV_OFF, c, p, 0, 0});
    }
}

// ---------------- 단락 → 사건 ----------------
void Engine::emit(Sess &ss, const Section &sec, bool flush_all) {
    Sheet sh; sh.key = ss.s->S.key;
    section_to_sheet(*ss.s, sec, sh, ss.t0);
    Rng rng(seed * 1000003 + sec.sec * 7919 + (uint64_t)(ss.t0 * 1000));
    // 악기별로 묶기
    std::map<int, std::vector<TNote>> by;
    for (auto &n : sh.notes) {
        int i = inst_of(sh.parts[n.part]);
        if (i >= 0) by[i].push_back(n);
    }
    std::vector<std::pair<int, std::vector<Ev>>> outs;
    for (auto &[i, ns] : by) {
        const InstDef &d = insts()[i];
        const int ms = d.engine == 0 ? 7 : d.drum ? 3 : (std::string(d.kw) == "베이스" || std::string(d.kw) == "일렉") ? 5 : 9;
        // 사람 손: 같은 순간 음은 함께 흔들림, 피아노는 맨 윗음이 아주 조금 먼저
        std::map<long, std::vector<TNote *>> groups;
        for (auto &n : ns) groups[std::lround(n.t0 * 1000)].push_back(&n);
        for (auto &[k, g] : groups) {
            double dd = rng.gauss(0, ms / 1000.0);
            int top = 0;
            for (auto *n : g) top = std::max(top, n->p);
            for (auto *n : g) {
                double e = dd + ((d.engine == 0 && n->p == top && g.size() > 1) ? -.006 : g.size() > 1 ? rng.uniform(0, .006) : 0);
                n->t0 = std::max(0.0, n->t0 + e); n->t1 += e;
                n->v = (int)std::max(1.0, std::min(127.0, n->v + rng.gauss(0, 2.5)));
            }
        }
        std::vector<Ev> evs;
        Track &tr = track(i);
        if (d.engine == 0) {
            const double sh_t = .018 - .005;                                  // 피아노 샘플 소리 시작 지연만큼 앞당김
            for (auto &n : ns) {
                double e = n.t1;
                for (auto &pd : sh.pedals) if (pd.first - .02 <= n.t1 && n.t1 <= pd.second + 1e-6) { e = std::max(e, pd.second); break; }
                evs.push_back({std::max(0.0, n.t0 - sh_t), 2, EV_PIANO, 0, n.p, n.v, e - sh_t});
                piano.warm(n.p, n.v);                                         // 이 음의 녹음을 지금(작곡 줄에서) 읽어 둠
            }
        } else perform_fluid(tr, ns, flush_all ? 1.0 : -1.0, evs, rng);
        outs.push_back({i, std::move(evs)});
    }
    // 한 줄 악기의 남긴 음은 이번 단락에 음이 없어도 너무 오래 두지 않음
    for (int i = 0; i < (int)tracks.size(); i++) {
        if (!tracks[i] || tracks[i]->held.empty() || by.count(i)) continue;
        std::vector<Ev> evs;
        perform_fluid(*tracks[i], {}, 1.0, evs, rng);
        outs.push_back({i, std::move(evs)});
    }
    for (auto &[i, evs] : outs) push_events(*tracks[i], evs);
    // 악보 · 상태
    const Mood &m = ss.s->m;
    std::ostringstream hd;
    const double r0 = run_t0.load();
    hd << "\n# ── " << m.name << " · " << ROLE_NAME[sec.role] << " · " << sh.key.name << "조 · ♩=" << (int)std::lround(ss.s->bpm_at(sec.a * m.ts))
       << " · " << fmt2(ss.t0 + ss.s->sec((double)sec.a * m.ts) - r0) << "초부터";
    if (!ss.s->plan_note.empty() && sec.role != R_INTRO && sec.role != R_TAG && sec.role != R_TRANS)
        hd << "\n# (" << ss.s->plan_note << ")";                               // 이번 단락을 앞 단락에서 어떻게 바꿨나
    hd << "\n";
    Sheet shown = sh;                                                     // 악보 글자 시각은 이번 연주 시작부터
    for (auto &c : shown.chords) { c.t0 -= r0; c.t1 -= r0; }
    for (auto &n : shown.notes) { n.t0 = std::max(0.0, n.t0 - r0); n.t1 = std::max(0.0, n.t1 - r0); }
    for (auto &p : shown.pedals) { p.first -= r0; p.second -= r0; }
    std::string block = hd.str() + shown.text(false);
    Block blk{0, hd.str(), shown, block};
    double t_start = ss.t0 + ss.s->sec((double)sec.a * m.ts);
    Status s;
    s.mood = m.id; s.mood_name = m.name; s.role = ROLE_NAME[sec.role]; s.key = sh.key.name; s.bpm = ss.s->bpm_at((double)(sec.a + 1) * m.ts); s.bar = sec.a; s.t = t_start;
    {
        std::lock_guard<std::mutex> g(mtx);
        composed_until = ss.t0 + ss.s->sec((double)ss.s->next_bar * m.ts);
        blk.t = t_start;
        score_log.push_back(std::move(blk));
        if (score_log.size() > 400) score_log.erase(score_log.begin());
        marks.push_back({t_start, s});
        if (marks.size() > 400) marks.erase(marks.begin());
    }
    if (!score_file.empty()) {                                           // 파일은 통째로 다시 씀 (잘린 단락이 안 남게)
        std::string all = score_head;
        std::lock_guard<std::mutex> g(mtx);
        for (auto &b : score_log) if (b.t >= run_t0.load() - 1e-6) all += b.text;
        write_file(score_file, all);
    }
}

// ---------------- 작곡 한 걸음 ----------------
void Engine::set_params(const Params &p) {
    bool music;
    {
        std::lock_guard<std::mutex> g(mtx);
        music = !p.same_music(params);
        params = p;
    }
    space = (float)p.space;
    if (music) { params_pending = true; req_params = true; }
}

void Engine::set_steer(const Steer &s) {
    bool ch;
    {
        std::lock_guard<std::mutex> g(mtx);
        ch = !s.same(steer_cur);
        steer_cur = s;
    }
    if (ch) { params_pending = true; req_params = true; }
}

std::string Engine::cur_mood_id() {
    if (!cur || !cur->s) return "";
    return cur->s->m.id;
}

static Json brief_situation(const Json &s) {                              // 반응 기록에 남길 상황 (몇 칸만)
    Json b = Json::obj_();
    for (const char *k : {"trip.kind", "time.slot", "time.group", "weather.kind", "place.kind", "drive.state", "people.group", "people.baby", "cabin.sound"}) {
        const Json &v = s.path(k);
        if (!v.is_null()) b.set(k, v);
    }
    return b;
}

static void log_feedback(const std::string &dir, const std::string &action, const std::string &mood, const Json &sit) {
    if (dir.empty()) return;
    Json j = Json::obj_();
    j.set("t", Json::num_((double)std::time(nullptr))); j.set("action", Json::str_(action)); j.set("mood", Json::str_(mood));
    j.set("situation", brief_situation(sit));
    write_file(dir + "/반응기록.jsonl", j.dump() + "\n", true);           // 둘째 겹(개인 학습)이 읽을 것
}

void Engine::user_mood(const std::string &id) {
    const double now = (double)frame.load() / SR;
    if (auto_mode) {
        user_pick_until = now + 900;                                       // 알아서 하는 중이라도 사람이 고른 건 15분 지킴
        mood_since = now;
        std::lock_guard<std::mutex> g(cond_mtx);
        log_feedback(out_dir, "pick", id, cond.derived(now));
    }
    request_mood(id);
}

void Engine::situation(const Json &patch) {
    const double now = (double)frame.load() / SR;
    std::lock_guard<std::mutex> g(cond_mtx);
    cond.update(patch, now);
    const Json &t = patch.path("cabin.talk");
    if (t.is_num()) talk_level = (float)std::max(0.0, std::min(1.0, t.n));
}

std::string Engine::hear(const std::string &text, std::string *intent) {
    const double now = (double)frame.load() / SR;
    std::string it, cm = cur_mood_id();
    {
        std::lock_guard<std::mutex> g(cond_mtx);
        it = cond.hear(text, now);
        if (it == "change" && !cm.empty()) cond.exclude_mood(cm, now + 600);
        if (it == "like" || it == "change") log_feedback(out_dir, it, cm, cond.derived(now));
    }
    if (intent) *intent = it;
    if (it == "like") { keep_until = now + 600; return "이 느낌 오래 둘게요"; }
    if (it == "change") { mood_since = -1e9; pend_since = -1e9; return "다른 분위기로 바꿀게요"; }
    if (it == "music_off") { request_end(); return "음악을 마무리할게요"; }
    if (it == "auto_off") { auto_mode = false; set_steer(Steer()); return "자동을 껐어요 · 직접 골라 주세요"; }
    if (it == "baby_sleep") return "아기가 자요 → 잔잔하게 바꿀게요";
    if (it == "quiet") return "조용히 할게요";
    if (it == "upbeat") return "신나게 갈게요";
    if (it == "calm") return "잔잔하게 갈게요";
    if (it == "sea_sound") return "파도 소리를 깔게요";
    if (it == "reset") return "원래대로 할게요";
    return "잘 못 알아들었어요";
}

// 지휘자 한 걸음 (0.5초마다, 작곡 줄): 섞기는 늘 · 분위기 · 조절값 · 악기는 '알아서' 일 때만
void Engine::cond_tick(double now) {
    Decision d;
    double lv;
    std::string snd;
    const std::string curm = cur_mood_id();
    {
        std::lock_guard<std::mutex> g(cond_mtx);
        d = cond.decide(now, curm);
        dec = d;
        lv = cond.sit.path("cabin.talk").num(-1);
        snd = cond.sit.path("cabin.sound").str();
    }
    mix_db = (float)(d.volume_db + d.duck_db);
    talk_duck_db = (float)d.talk_duck_db; talk_cut_db = (float)d.talk_cut_db; overlap_db = (float)d.overlap_db;
    if (lv < 0) talk_level = (snd == "talk" || snd == "argument") ? 1.f : snd == "laugh" ? .7f : 0.f;   // 마이크 값이 없으면 차 안 소리 상태로
    if (!auto_mode) return;
    if (std::fabs(amb.level[0].load() - d.amb_sea) > 1e-3) amb.set(0, (float)d.amb_sea);
    if (std::fabs(amb.level[1].load() - d.amb_rain) > 1e-3) amb.set(1, (float)d.amb_rain);
    const bool playing = cur && live && !ending && !stopped;
    if (!playing) {
        if (auto_start && start_at < 0) start_at = now;                    // 상황이 자리 잡을 2.5초를 기다렸다가 시작
        if (auto_start && now - start_at >= 3.6 && !d.mood.empty()) {     // (장면은 3초 이어져야 켜짐)
            auto_start = false; start_at = -1;
            set_params(d.params); set_steer(d.steer); params_at = now;
            request_mood(d.mood); mood_since = now; pend_mood.clear(); cond_ended = false;
        }
        return;
    }
    if (d.end) { if (!cond_ended) { cond_ended = true; request_end(); } return; }
    cond_ended = false;
    // 분위기: 몇 초 이어져야 · 한 분위기는 얼마쯤 머문 뒤에 (급한 일 — 아기 · 언성 · 과속 — 은 빨리)
    if (!d.mood.empty() && d.mood != curm && now >= user_pick_until) {
        if (pend_mood != d.mood) { pend_mood = d.mood; pend_since = now; }
        const double need = d.urgent ? 3 : 8;
        const double dwell = d.urgent ? 8 : (now < keep_until ? 600 : 45);
        if (now - pend_since >= need && now - mood_since >= dwell) {
            set_params(d.params); set_steer(d.steer); params_at = now;
            request_mood(d.mood); mood_since = now; pend_mood.clear();
            return;
        }
    } else pend_mood.clear();
    // 같은 분위기 안: 조절값 · 악기 지시가 꽤 달라졌으면 (터널 · 급한 일은 2초, 보통은 15초 간격)
    const Params cp = get_params();
    const Steer cs = get_steer();
    const double pd = std::max({std::fabs(cp.reg - d.params.reg), std::fabs(cp.tempo - d.params.tempo), std::fabs(cp.dens - d.params.dens),
                                std::fabs(cp.energy - d.params.energy), std::fabs(cp.novelty - d.params.novelty), std::fabs(cp.tension - d.params.tension),
                                std::fabs(cp.space - d.params.space)});
    double idiff = 0;
    std::set<std::string> keys;
    for (auto &kv : cs.instr) keys.insert(kv.first);
    for (auto &kv : d.steer.instr) keys.insert(kv.first);
    for (auto &k : keys) idiff += std::fabs((cs.instr.count(k) ? cs.instr.at(k) : 0) - (d.steer.instr.count(k) ? d.steer.instr.at(k) : 0));
    const bool big = d.steer.thin != cs.thin || d.steer.lead_rest != cs.lead_rest || d.steer.avoid != cs.avoid ||
                     std::fabs(d.steer.energy_max - cs.energy_max) > .01 || std::fabs(d.steer.tempo_max - cs.tempo_max) > .5;
    const double gap = (d.move_now || d.urgent || big) ? 2 : 15;
    if ((pd > .12 || big || idiff > .8) && now - params_at >= gap) {
        set_params(d.params); set_steer(d.steer); params_at = now;
    }
}

void Engine::request_mood(const std::string &id) {
    auto &ms = moods();
    for (size_t i = 0; i < ms.size(); i++) if (ms[i].id == id) req_mood = (int)i;
}

bool Engine::compose_step(double now) {
    if (cond.loaded && now - cond_last >= .5) { cond_last = now; cond_tick(now); }
    {                                                                     // 주변 소리는 음악이 나오는 동안만 (끝맺음이 다 울린 뒤엔 같이 사라짐)
        std::lock_guard<std::mutex> g(mtx);
        amb.run = live && !stopped && !(ending && now > composed_until + 1.0);
    }
    if (req_stop.exchange(false) && cur) {                                // 바로 끄기: 1.5초 동안 작아지며 끝
        fading_out = true;
        cut_at(now + 1.6);
        std::lock_guard<std::mutex> g(mtx);
        prev = std::move(cur); stopped = true; ending = false; live = false;
        return true;
    }
    int rq = req_mood.exchange(-1);
    if (rq >= 0) {
        const Mood &m = moods()[rq];
        if (!cur || ending) {
            const double t_start = now + (cur ? .4 : .2);
            cut_at(t_start);                                              // 앞에 남은 소리(끝맺음·끄기 꼬리)는 여기서 정리
            if (cur) prev = std::move(cur);
            ending = false;
            if (!out_dir.empty()) {
                char b[64]; std::time_t tt = std::time(nullptr); std::strftime(b, sizeof b, "%m%d_%H%M%S", std::localtime(&tt));
                score_file = out_dir + "/" + b + "_실시간악보.txt";
                score_head = "# 차량 BGM AI — 실시간으로 쓴 악보 (단락마다 이어 붙임 · 시각은 재생 시작부터 초)\n"
                             "# 형식: <옥타브> <계이름> <임시표> <시작초>~<끝초> <세기>   예) -1 mi F 3~6 70\n";
                write_file(score_file, score_head);
            }
            cur = std::make_unique<Sess>();
            const Params pp = get_params();
            const Steer st = get_steer();
            cur->s = std::make_unique<Session>(m, M, fresh_seed(), true, 0, nullptr, -1, "", &pp, &st);
            cur->t0 = t_start;
            run_t0 = t_start;
            set_mood_mix(m, cur->t0);
            {
                std::lock_guard<std::mutex> g(mtx);
                composed_until = cur->t0;
                fading_out = false; stopped = false; live = true;
            }
            Section s = cur->s->next();                                   // 도입
            emit(*cur, s, false);
            return true;
        }
        // 2마디 덩어리 끝(4초 안)에서 자르고, 앞 선율의 마지막 음에서 이어지는 이음 2마디 → 새 분위기 (가까운 조)
        Session &os = *cur->s;
        double tc;
        const int bar = phrase_cut(os, cur->t0, now, &tc);
        const double prev_bpm = os.bpm_at((double)bar * os.m.ts);
        std::string last_part;
        const int last_p = os.last_mel_pitch(bar, &last_part);
        const Key old_key = os.S.key;
        cut_at(tc, .9);                                                       // 울리던 음은 1초 가까이 이어 울림
        os.S.cut_after((double)bar * os.m.ts);
        prev = std::move(cur);
        cur = std::make_unique<Sess>();
        const Params pp = get_params();
        const Steer st = get_steer();
        cur->s = std::make_unique<Session>(m, M, fresh_seed(), false, prev_bpm, &old_key, last_p, last_part, &pp, &st);
        cur->t0 = tc;
        set_mood_mix(m, tc);
        emit(*cur, {R_TRANS, 0, 2, 0}, false);
        return true;
    }
    if (req_params.exchange(false)) {                                     // 조절값: 다음 2마디 덩어리부터 되감아 다시 씀
        if (cur && !ending && live) {
            Session &os = *cur->s;
            const Params pp = get_params();
            const Steer st = get_steer();
            if (!pp.same_music(os.P) || !st.same(os.steer)) {
                os.P = pp;
                if (!st.same(os.steer)) { os.steer = st; os.steer_dirty = true; }
                double tc;
                const int bar = phrase_cut(os, cur->t0, now, &tc);
                if (bar >= 2 && bar < os.next_bar) {
                    cut_at(tc, .6);
                    os.rollback(bar);
                    Section s = os.next();
                    emit(*cur, s, false);
                }
            }
        }
        params_pending = false;
        return true;
    }
    if (req_end.exchange(false) && cur && !ending) {
        Session &os = *cur->s;
        const int ts = os.m.ts;
        double t_min = now + .4; int bar = os.next_bar;
        for (int k = 0; k <= os.next_bar; k++) if (cur->t0 + os.sec((double)k * ts) >= t_min) { bar = k; break; }
        double tc = cur->t0 + os.sec((double)bar * ts);
        cut_at(tc);
        os.S.cut_after((double)bar * ts);
        os.next_bar = bar;
        Section s = os.ending();
        emit(*cur, s, true);
        ending = true;
        return true;
    }
    if (cur && !ending && composed_until - now < lookahead) {
        Section s = cur->s->next();
        emit(*cur, s, false);
        return true;
    }
    return false;
}

// ---------------- 소리 ----------------
void Engine::render(float *L, float *R, int n) {
    const int B = Convolver::B, SUB = 32;
    for (int off = 0; off < n; off += B) {
        const long f0 = frame.load();
        const double t0 = (double)f0 / SR, t1 = (double)(f0 + B) / SR;
        // 이번 블록 사건 꺼내기
        std::vector<std::pair<Track *, std::vector<Ev>>> todo;
        {
            std::lock_guard<std::mutex> g(mtx);
            for (auto &gs : gain_sched)                                     // 아직 없는 악기는 생길 때 적용 (처음엔 바로 그 크기로)
                if (gs.t < t1 && tracks[gs.track]) {
                    Track &tr = *tracks[gs.track];
                    tr.gain_to = gs.db;
                    if (!tr.gain_set) { tr.gain_db = gs.db; tr.gain_set = true; }
                }
            std::vector<GainAt> keep;
            for (auto &gs : gain_sched) if (!(gs.t < t1 && tracks[gs.track])) keep.push_back(gs);
            gain_sched = keep;
            std::vector<std::pair<double, double>> mk;
            for (auto &ms : master_sched) {
                if (ms.first < t1) { master_to = ms.second; if (!master_set) { master_db = ms.second; master_set = true; } }
                else mk.push_back(ms);
            }
            master_sched = mk;
            for (auto &tp : tracks) {
                if (!tp) continue;
                std::vector<Ev> ev;
                while (tp->qh < tp->q.size() && tp->q[tp->qh].t < t1) ev.push_back(tp->q[tp->qh++]);
                todo.push_back({tp.get(), std::move(ev)});
            }
        }
        if (rev_switch_t >= 0 && rev_switch_t < t1) {                     // 잔향 바꾸기 (3초 섞음)
            if (std::fabs(rev_next_sec - rev_sec) > .05) {
                Convolver *nr = rev == &rev_a ? &rev_b : &rev_a;
                nr->make(rev_next_sec, (unsigned)rev_next_sec * 100);
                rev_old = rev; rev = nr; rev_x = 0; rev_sec = rev_next_sec;
            }
            rev_switch_t = -1;
        }
        std::fill(dryL.begin(), dryL.end(), 0.f); std::fill(dryR.begin(), dryR.end(), 0.f);
        std::fill(sendL.begin(), sendL.end(), 0.f); std::fill(sendR.begin(), sendR.end(), 0.f);
        for (auto &[tr, ev] : todo) {
            std::fill(tr->bl.begin(), tr->bl.end(), 0.f); std::fill(tr->br.begin(), tr->br.end(), 0.f);
            size_t ei = 0;
            if (tr->def->engine == 0) {
                for (; ei < ev.size(); ei++) {
                    int at = std::max(0, std::min(B - 1, (int)std::lround((ev[ei].t - t0) * SR)));
                    if (ev[ei].type == EV_ALLOFF) piano.release_all(at);
                    else if (ev[ei].type == EV_CAP) piano.cap_all(at, (long)((ev[ei].t1 - ev[ei].t) * SR));
                    else if (ev[ei].type == EV_PIANO) piano.note(ev[ei].a, ev[ei].b, std::max(.02, ev[ei].t1 - ev[ei].t), at);
                }
                piano.render(tr->bl.data(), tr->br.data(), B);
            } else {
                for (int s = 0; s < B; s += SUB) {
                    const double te = t0 + (double)(s + SUB) / SR;
                    for (; ei < ev.size() && ev[ei].t < te; ei++) {
                        const Ev &e = ev[ei];
                        switch (e.type) {
                        case EV_ON: FL.noteon(tr->syn, e.ch, e.a, e.b); break;
                        case EV_OFF: FL.noteoff(tr->syn, e.ch, e.a); break;
                        case EV_CC: FL.cc(tr->syn, e.ch, e.a, e.b); break;
                        case EV_BEND: FL.pitch_bend(tr->syn, e.ch, e.a + 8192); break;
                        case EV_ALLOFF:
                            for (int c = 0; c < 16; c++) {
                                FL.all_notes_off(tr->syn, c);
                                if (!tr->def->drum) { FL.pitch_bend(tr->syn, c, 8192); FL.cc(tr->syn, c, 11, 100); }
                            }
                            for (double &b : tr->busy) b = 0;
                            break;
                        }
                    }
                    FL.write_float(tr->syn, SUB, tr->bl.data() + s, 0, 1, tr->br.data() + s, 0, 1);
                }
            }
            if (tr->measure) for (int i = 0; i < B; i++) tr->meas.push_back(std::sqrt((tr->bl[i] * tr->bl[i] + tr->br[i] * tr->br[i]) * .5f));
            // 크기 · 저역컷 · 좌우 · 잔향 보내기
            const double g0 = std::pow(10.0, tr->gain_db / 20);
            tr->gain_db += (tr->gain_to - tr->gain_db) * .08;
            const double g1 = std::pow(10.0, tr->gain_db / 20);
            const double pa = tr->def->pan, pl0 = std::cos((pa + 1) * M_PI / 4) * 1.414, pr0 = std::sin((pa + 1) * M_PI / 4) * 1.414;
            double ovg = 1;                                                   // 말소리 중: 말과 많이 겹치는 악기(색소폰 · 트럼펫 · 오보에 …)를 더 줄임
            {
                const size_t ti = (size_t)(tr->def - &insts()[0]);
                const double ov = overlap_db.load() * talk_env, at = ti < trk_talk.size() ? trk_talk[ti] : .3;
                if (ov < -.05) ovg = std::pow(10.0, ov * std::max(0.0, std::min(1.0, (at - .4) / .5)) / 20);
            }
            const double pl = pl0 * ovg, pr = pr0 * ovg;
            const float rv = (float)tr->def->rv;
            const bool hp = tr->def->hp > 0;
            for (int i = 0; i < B; i++) {
                float g = (float)(g0 + (g1 - g0) * i / B);
                float l = tr->bl[i] * g, r = tr->br[i] * g;
                if (hp) { l = tr->hp[0].run(l); r = tr->hp[1].run(r); }
                l *= (float)pl; r *= (float)pr;
                dryL[i] += l; dryR[i] += r; sendL[i] += l * rv; sendR[i] += r * rv;
            }
        }
        rev->process(sendL.data(), sendR.data(), wetL.data(), wetR.data());
        if (rev_old) {
            std::vector<float> ol(B), orr(B);
            rev_old->process(sendL.data(), sendR.data(), ol.data(), orr.data());
            for (int i = 0; i < B; i++) {
                float x = (float)std::min(1.0, rev_x + (double)i / B / (3.0 * SR / B));
                wetL[i] = wetL[i] * x + ol[i] * (1 - x); wetR[i] = wetR[i] * x + orr[i] * (1 - x);
            }
            rev_x += 1.0 / (3.0 * SR / B);
            if (rev_x >= 1) rev_old = nullptr;
        }
        float *oL = L + off, *oR = R + off;
        const float sp = space.load(), wg = .9f * (sp >= 0 ? 1 + .9f * sp : 1 + .65f * sp);   // 울림: 가깝게 .3 … 넓게 1.7 배
        for (int i = 0; i < B; i++) { oL[i] = dryL[i] + wetL[i] * wg; oR[i] = dryR[i] + wetR[i] * wg; }
        comp.process(oL, oR, B);
        {                                                                 // 섞기: 말소리 덮개 (빨리 붙고 · 말이 멈춰도 3초 버티다 · 1.5초에 걸쳐 풀림)
            const float tl = talk_level.load(), bt = (float)B / SR;
            if (tl >= talk_env - .02f) { talk_env += (tl - talk_env) * std::min(1.f, bt / .15f); talk_hold = 3.f; }
            else if ((talk_hold -= bt) <= 0) talk_env += (tl - talk_env) * std::min(1.f, bt / 1.5f);
            const double cut = talk_cut_db.load() * talk_env;               // 말 대역(1.5kHz 둘레 넓게) 만 깎음 — 베이스 · 울림은 남김
            if (std::fabs(cut - peq_db) > .05) {
                peq_db = cut;
                const double A = std::pow(10.0, cut / 40), w0 = 2 * M_PI * 1500 / SR, al = std::sin(w0) / (2 * .6), cw = std::cos(w0), a0 = 1 + al / A;
                peq_b[0] = (1 + al * A) / a0; peq_b[1] = -2 * cw / a0; peq_b[2] = (1 - al * A) / a0; peq_a[0] = -2 * cw / a0; peq_a[1] = (1 - al / A) / a0;
            }
            if (std::fabs(peq_db) > .05) {
                float *ch[2] = {oL, oR};
                for (int c = 0; c < 2; c++) {
                    double z1 = peq_z[c][0], z2 = peq_z[c][1];
                    for (int i = 0; i < B; i++) {
                        const double x = ch[c][i], y = peq_b[0] * x + z1;
                        z1 = peq_b[1] * x - peq_a[0] * y + z2; z2 = peq_b[2] * x - peq_a[1] * y;
                        ch[c][i] = (float)y;
                    }
                    peq_z[c][0] = z1; peq_z[c][1] = z2;
                }
            } else { peq_z[0][0] = peq_z[0][1] = peq_z[1][0] = peq_z[1][1] = 0; }
        }
        if (measure_master)
            for (int i = 0; i < B; i++)
                if (std::max(std::fabs(oL[i]), std::fabs(oR[i])) > 1e-4) { mm_sum += (oL[i] * oL[i] + oR[i] * oR[i]) * .5; mm_n++; }
        const double m0 = std::pow(10.0, master_db / 20);
        master_db += (master_to - master_db) * .05;
        const double m1 = std::pow(10.0, master_db / 20);
        const float vt = volume.load() * duck.load();
        const float mt = std::pow(10.f, (mix_db.load() + talk_duck_db.load() * talk_env) / 20.f);   // 지휘자 섞기 (뚜껑 · 길 안내 · 통화 · 말소리)
        for (int i = 0; i < B; i++) {
            if (fading_out) fade = std::max(0.f, fade - 1.f / (1.5f * SR)); else fade = std::min(1.f, fade + 1.f / (.05f * SR));
            vol_now += (vt - vol_now) * .0008f;
            mix_now += (mt - mix_now) * (mt < mix_now ? 1.f / (.25f * SR) : 1.f / (1.2f * SR));
            float g = (float)(m0 + (m1 - m0) * i / B) * vol_now * mix_now * fade;
            oL[i] *= g; oR[i] *= g;
        }
        amb.render(oL, oR, B, vol_now * mix_now);                         // 주변 소리 (음악 볼륨 · 통화 중 · 섞기를 따라감)
        lim.process(oL, oR, B);
        {
            double ss = 0;
            for (int i = 0; i < B; i++) ss += oL[i] * oL[i] + oR[i] * oR[i];
            const float db = (float)(10 * std::log10(ss / (2 * B) + 1e-12));
            out_db = out_db.load() * .8f + db * .2f;
        }
        frame += B;
    }
}

Engine::Status Engine::status_at(double t) {
    std::lock_guard<std::mutex> g(mtx);
    Status s;
    for (auto &m : marks) if (m.first <= t + 1e-6) s = m.second;
    return s;
}

std::string Engine::recent_score(int n) {
    const double t = (double)frame.load() / SR - play_latency;
    std::lock_guard<std::mutex> g(mtx);
    std::vector<std::string> out;
    for (auto &b : score_log) if (b.t <= t + .05) out.push_back(b.text);
    std::string s;
    for (size_t i = out.size() > (size_t)n ? out.size() - n : 0; i < out.size(); i++) s += out[i];
    return s;
}
