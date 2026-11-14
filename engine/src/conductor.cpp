#include "conductor.h"
#include "util.h"
#include <algorithm>
#include <cmath>
#include <ctime>

static double clampd(double x, double lo, double hi) { return std::max(lo, std::min(hi, x)); }

// ---------------- 읽기 ----------------
bool Conductor::load(const std::string &dir, std::string *e) {
    auto rd = [&](const char *name, Json &out) {
        std::string t, pe;
        if (!read_file(dir + "/" + name, t)) { err = std::string("지휘자 파일이 없음: ") + name; return false; }
        out = Json::parse(t, &pe);
        if (!pe.empty()) { err = std::string(name) + " 읽기 실패: " + pe; return false; }
        return true;
    };
    Json sig, rul, sce, ins, moo;
    if (!rd("signals.json", sig) || !rd("rules.json", rul) || !rd("scenes.json", sce) || !rd("instruments.json", ins) || !rd("moods.json", moo)) {
        if (e) *e = err;
        return false;
    }
    for (auto &kv : sig["speech_words"].o) {
        std::vector<std::string> ws;
        for (auto &w : kv.second.a) ws.push_back(w.str());
        words_.push_back({kv.first, ws});
    }
    for (auto &r : rul["rules"].a) {
        Rule x;
        x.id = r["id"].str(); x.aspect = r["aspect"].str(); x.say = r["say"].str();
        x.when = r["when"]; x.set = r["set"]; x.priority = (int)r["priority"].num(0); x.hold = r["hold_sec"].num(2); x.release = r["release_sec"].num(4);
        rules_.push_back(x);
    }
    for (auto &c : sce["scenes"].a) {
        Scene x;
        x.id = c["id"].str(); x.name = c["name"].str(); x.say = c["say"].str(); x.match = c["match"]; x.body = c;
        scenes_.push_back(x);
    }
    for (auto &kv : ins.o) {
        Inst x; const Json &j = kv.second;
        x.warm = j["warm"].num(.5); x.bright = j["bright"].num(.5); x.lively = j["lively"].num(.5); x.talk = j["talk"].num(.5); x.soft = j["soft"].num(.5);
        x.baby = j["baby"].t == Json::BOOL ? j["baby"].b : true; x.brass = j["brass"].truthy(); x.drum = j["drum"].truthy();
        for (auto &v : j["evokes"].a) x.evokes.push_back(v.str());
        inst_[kv.first] = x;
    }
    for (auto &m : moods()) {                                             // 엔진에 있는 분위기만 (차례도 엔진 것)
        const Json &j = moo[m.id];
        if (j.is_null()) continue;
        MoodP p; p.energy = j["energy"].num(50); p.bright = j["bright"].num(50); p.genre = j["genre"].str(m.src);
        for (auto &v : j["evokes"].a) p.evokes.push_back(v.str());
        mood_[m.id] = p; mood_ids.push_back(m.id);
    }
    sit = Json::obj_();
    loaded = !rules_.empty() && !mood_ids.empty();
    if (!loaded) { err = "지휘자 규칙 · 분위기가 비어 있음"; if (e) *e = err; }
    return loaded;
}

// ---------------- 상황 ----------------
void Conductor::update(const Json &patch, double now) {
    sit.merge(patch);
    const std::string pk = sit.path("place.kind").str();
    if (pk != place_now) { if (!place_now.empty()) { place_prev = place_now; place_at = now; } place_now = pk; }
    if (!patch.path("place.ahead").is_null()) ahead_at = now;
    if (!patch.path("trip.eta_min").is_null()) eta_at = now;
    last_now = now;
}

std::string Conductor::hear(const std::string &text, double now) {
    std::string it;
    for (auto &[intent, ws] : words_) {
        for (auto &w : ws) if (!w.empty() && text.find(w) != std::string::npos) { it = intent; break; }
        if (!it.empty()) break;
    }
    if (it == "baby_sleep") { Json p = Json::obj_(), pp = Json::obj_(); pp.set("baby", Json::str_("sleeping")); p.set("people", pp); update(p, now); }
    else if (it == "quiet" || it == "upbeat" || it == "calm") { intents.erase("quiet"); intents.erase("upbeat"); intents.erase("calm"); intents[it] = now + 600; }
    else if (it == "sea_sound") intents[it] = now + 1800;
    else if (it == "reset") clear_requests();
    return it;
}

Json Conductor::derived(double now) const {
    Json s = sit;
    if (!s.is_obj()) s = Json::obj_();
    // 시간대 · 요일 (안 보냈으면 차 시계)
    std::time_t tt = std::time(nullptr);
    std::tm lt{};
#ifdef _WIN32
    localtime_s(&lt, &tt);
#else
    localtime_r(&tt, &lt);
#endif
    Json time = s["time"].is_obj() ? s["time"] : Json::obj_();
    if (time["slot"].is_null()) {
        const int h = lt.tm_hour;
        time.set("slot", Json::str_(h < 4 ? "latenight" : h < 6 ? "dawn" : h < 9 ? "morning" : h < 17 ? "day" : h < 19 ? "dusk" : h < 21 ? "evening" : "night"));
    }
    if (time["group"].is_null()) {
        static const char *DAYS[7] = {"sun", "mon", "tue", "wed", "thu", "fri", "sat"};
        const std::string d = time["day"].str(DAYS[lt.tm_wday]);
        std::string g = d == "mon" ? "mon" : d == "fri" ? "fri" : (d == "sat" || d == "sun") ? "weekend" : "midweek";
        if (time["holiday"].truthy()) g = "holiday";
        time.set("group", Json::str_(g));
    }
    s.set("time", time);
    // 달리는 상태 (속도 · 제한속도만 보냈으면)
    Json drive = s["drive"].is_obj() ? s["drive"] : Json::obj_();
    if (drive["state"].is_null() && drive["speed"].is_num()) {
        const double v = drive["speed"].n, lim = drive["limit"].num(0);
        drive.set("state", Json::str_(v < 3 ? "stopped" : (lim > 0 && v > lim * 1.1 + 3) ? "speeding" : v < 20 ? "slow" : v >= 90 ? "fast" : "cruise"));
    }
    s.set("drive", drive);
    // 장소: 바로 앞 장소 · 지난 시간 · 터널까지 남은 초
    Json place = s["place"].is_obj() ? s["place"] : Json::obj_();
    if (!place_prev.empty()) { place.set("prev", Json::str_(place_prev)); place.set("since_sec", Json::num_(now - place_at)); }
    double tun = 1e9;
    for (auto &a : place["ahead"].a)
        if (a["kind"].str() == "tunnel") { const double left = a["in_sec"].num(1e9) - (now - ahead_at); if (left > -1 && left < tun) tun = left; }
    if (tun < 1e8) place.set("ahead_tunnel_sec", Json::num_(tun));
    s.set("place", place);
    // 도착까지 남은 분
    if (s.path("trip.eta_min").is_num()) {
        Json trip = s["trip"];
        trip.set("eta_min", Json::num_(s.path("trip.eta_min").n - (now - eta_at) / 60));
        s.set("trip", trip);
    }
    // 운전자 상태 (안 보냈으면 추정)
    if (s.path("driver.state").is_null()) {
        const std::string slot = s.path("time.slot").str(), snd = s.path("cabin.sound").str(), st = s.path("drive.state").str(), trip = s.path("trip.kind").str();
        const double dm = s.path("car.drive_min").num(0);
        std::string d;
        if (snd == "yawn" || ((slot == "latenight" || slot == "night") && dm > 60)) d = "drowsy";
        else if (st == "jam" && snd == "argument") d = "stressed";
        else if (trip == "homeward" && dm > 60) d = "tired";
        if (!d.empty()) { Json dr = Json::obj_(); dr.set("state", Json::str_(d)); dr.set("guessed", Json::bool_(true)); s.set("driver", dr); }
    }
    // 말로 한 요청 (아직 유효한 것)
    std::string last; double lt_end = -1;
    Json sp = Json::obj_();
    for (auto &[k, until] : intents) {
        if (until < now) continue;
        if (k == "sea_sound") { sp.set("sea", Json::bool_(true)); continue; }
        if (until > lt_end) { lt_end = until; last = k; }
    }
    if (!last.empty()) sp.set("intent", Json::str_(last));
    s.set("speech", sp);
    return s;
}

// ---------------- 조건 ----------------
static bool cond(const Json &v, const Json &spec) {
    if (spec.is_arr()) { for (auto &x : spec.a) if (cond(v, x)) return true; return false; }
    if (spec.is_obj()) {
        if (!spec["not"].is_null()) return !cond(v, spec["not"]);
        if (spec["gt"].is_num()) return v.is_num() && v.n > spec["gt"].n;
        if (spec["lt"].is_num()) return v.is_num() && v.n < spec["lt"].n;
        return true;
    }
    if (spec.t == Json::BOOL) return v.truthy() == spec.b;
    if (spec.is_num()) return v.is_num() && std::fabs(v.n - spec.n) < 1e-9;
    if (spec.is_str()) return v.is_str() && v.s == spec.s;
    return v.is_null();
}

bool Conductor::match(const Json &s, const Json &when) const {
    if (!when.is_obj()) return false;
    for (auto &kv : when.o) if (!cond(s.path(kv.first), kv.second)) return false;
    return true;
}

// 켜짐은 hold 초 이어져야 · 꺼짐은 release 초 늦게 — 상태가 바뀌는 사이(아기 잠 → 울음 …) 바탕으로 잠깐 튀지 않게
bool Conductor::held(const std::string &id, bool now_true, double hold, double release, double now) {
    auto it = since_.find(id);
    if (now_true) {
        last_true_[id] = now;
        if (it == since_.end()) { since_[id] = now; return hold <= 0; }
        return now - it->second >= hold;
    }
    if (it == since_.end()) return false;
    const double lt = last_true_.count(id) ? last_true_[id] : -1e9;
    if (lt - it->second >= hold && now - lt < release) return true;
    since_.erase(it); last_true_.erase(id);
    return false;
}

double Conductor::talk_of(const std::string &part) const {
    const Inst *best = nullptr; size_t bl = 0;
    for (auto &kv : inst_) if (part.find(kv.first) != std::string::npos && kv.first.size() > bl) { best = &kv.second; bl = kv.first.size(); }
    if (!best) {                                                          // 엔진 악기 이름이 짧을 때 (테너 · 알토 · 뮤트 · 나일론 · 스틸 · 일렉 …)
        for (auto &kv : inst_) if (kv.first.find(part) != std::string::npos && (!best || kv.first.size() < bl)) { best = &kv.second; bl = kv.first.size(); }
    }
    return best ? best->talk : .3;
}

// ---------------- 정하기 ----------------
Decision Conductor::decide(double now, const std::string &cur) {
    Decision d;
    if (!loaded) return d;
    const Json s = derived(now);
    if (!cur.empty() && (mood_hist.empty() || mood_hist.back().first != cur)) mood_hist.push_back({cur, now});
    while (mood_hist.size() > 12) mood_hist.erase(mood_hist.begin());

    // 켜진 규칙 · 장면
    std::vector<const Rule *> on;
    for (auto &r : rules_) if (held(r.id, match(s, r.when), r.hold, r.release, now)) on.push_back(&r);
    std::sort(on.begin(), on.end(), [](const Rule *a, const Rule *b) { return a->priority > b->priority; });
    const Scene *scene = nullptr; size_t scene_keys = 0;
    for (auto &c : scenes_) {
        const bool ok = held("scene:" + c.id, match(s, c.match), 3, 5, now);
        if (ok && c.match.size() > scene_keys) { scene = &c; scene_keys = c.match.size(); }
    }
    // 바탕: 장면 > 가장 센 바탕 규칙 > 기본
    const Rule *base = nullptr;
    for (auto *r : on) if (r->aspect == "base") { base = r; break; }
    const Json &bset = scene ? scene->body["base"] : base ? base->set : Json();
    double energy = bset["energy"].num(50), bright = bset["bright"].num(55);
    std::map<std::string, double> genre, moods, instr;
    std::set<std::string> avoid_m, avoid_i, evokes;
    for (auto &kv : bset["genre"].o) genre[kv.first] += kv.second.num();
    if (scene && base) for (auto &kv : base->set["genre"].o) genre[kv.first] += .5 * kv.second.num();   // 장면이어도 여정의 갈래는 조금
    for (auto &kv : bset["moods"].o) moods[kv.first] += (scene ? 1.5 : 1.0) * kv.second.num();
    if (scene && base) for (auto &kv : base->set["moods"].o) moods[kv.first] += .5 * kv.second.num();
    double tempo = 0, dens = 0, tension = 0, novelty = 0, space = 0, vol_add = 0;
    double cap_tempo = 0, cap_energy = 100, cap_bright = 100, cap_vol = 0, cap_rear = 0;
    bool drums = true, brass = true, baby_only = false, lead_rest = false, end = false, move_now = false, urgent = false;
    double duck = 0, tduck = 0, tcut = 0, overlap = 0;
    std::map<std::string, std::pair<int, double>> amb;                    // 주변 소리: 가장 센 규칙이 정함
    std::pair<int, bool> thin{-1, false};
    std::string job;
    auto take = [&](const Json &x, int prio, bool is_base) {
        if (!is_base) { energy += x["energy"].num(0); bright += x["bright"].num(0); }
        tempo += x["tempo"].num(0); dens += x["dens"].num(0); tension += x["tension"].num(0); novelty += x["novelty"].num(0); space += x["space"].num(0);
        vol_add += x["volume_db"].num(0);
        if (!is_base) {
            for (auto &kv : x["moods"].o) moods[kv.first] += kv.second.num();
            for (auto &kv : x["genre"].o) genre[kv.first] += kv.second.num();
        }
        for (auto &kv : x["instr"].o) instr[kv.first] += kv.second.num();
        for (auto &v : x["avoid_moods"].a) avoid_m.insert(v.str());
        for (auto &v : x["avoid_instr"].a) avoid_i.insert(v.str());
        for (auto &v : x["evokes"].a) evokes.insert(v.str());
        const Json &c = x["caps"];
        if (c["tempo_max"].is_num()) cap_tempo = cap_tempo > 0 ? std::min(cap_tempo, c["tempo_max"].n) : c["tempo_max"].n;
        if (c["energy_max"].is_num()) cap_energy = std::min(cap_energy, c["energy_max"].n);
        if (c["bright_max"].is_num()) cap_bright = std::min(cap_bright, c["bright_max"].n);
        if (c["volume_db"].is_num()) cap_vol = std::min(cap_vol, c["volume_db"].n);
        if (c["rear_db"].is_num()) cap_rear = std::min(cap_rear, c["rear_db"].n);
        if (c["drums"].t == Json::BOOL && !c["drums"].b) drums = false;
        if (c["brass"].t == Json::BOOL && !c["brass"].b) brass = false;
        if (x["baby_only"].truthy()) baby_only = true;
        if (x["lead_rest"].truthy()) lead_rest = true;
        if (x["end"].truthy()) end = true;
        if (x["move"].str() == "now") move_now = true;
        duck = std::min(duck, x["duck_db"].num(0)); tduck = std::min(tduck, x["talk_duck_db"].num(0));
        tcut = std::min(tcut, x["talk_cut_db"].num(0)); overlap = std::min(overlap, x["overlap_db"].num(0));
        for (auto &kv : x["ambience"].o) { auto it = amb.find(kv.first); if (it == amb.end() || prio > it->second.first) amb[kv.first] = {prio, kv.second.num()}; }
        if (x["thin"].t == Json::BOOL && prio > thin.first) thin = {prio, x["thin"].b};
        if (job.empty() && !x["job"].str().empty()) job = x["job"].str();
    };
    if (scene) {
        take(scene->body, 50, true);                                      // 장면의 악기 · 뚜껑 · 양념
        for (auto &v : scene->body["avoid_moods"].a) avoid_m.insert(v.str());
    }
    for (auto *r : on) {
        take(r->set, r->priority, r == base);
        if (r->priority >= 85 && (r->aspect == "care" || r->aspect == "mix" || r->aspect == "motion")) urgent = true;
        if (r->id.rfind("cabin.", 0) == 0 || r->id.rfind("people.baby", 0) == 0 || r->id.rfind("drive.hard", 0) == 0) {}
        d.rules.push_back(r->id);
        if (!r->say.empty() && std::find(d.because.begin(), d.because.end(), r->say) == d.because.end()) d.because.push_back(r->say);
    }
    auto soft = [](double x) { return x > 80 ? 80 + (x - 80) * .4 : x < 15 ? 15 - (15 - x) * .5 : x; };   // 여럿이 더해져도 끝까지 치솟지 않게
    energy = clampd(std::min(soft(energy), cap_energy), 0, 100);
    bright = clampd(std::min(soft(bright), cap_bright), 0, 100);
    d.energy = energy; d.bright = bright;

    // 분위기 고르기
    double best = -1e9;
    const Mood *bm = nullptr;
    for (auto &id : mood_ids) {
        const MoodP &p = mood_[id];
        const Mood *m = mood_by_id(id);
        if (!m) continue;
        const double gw = genre.empty() ? .5 : (genre.count(p.genre) ? genre[p.genre] : .2);   // (바탕에 없는 갈래도 0 은 아님)
        double sc = 1.6 * gw + (moods.count(id) ? moods[id] : 0) - .035 * std::fabs(energy - p.energy) - .02 * std::fabs(bright - p.bright);
        int ev = 0;
        for (auto &e : p.evokes) ev += evokes.count(e);
        sc += .12 * ev;
        if (avoid_m.count(id)) sc -= 10;
        auto ex = excluded.find(id);
        if (ex != excluded.end() && ex->second > now) sc -= 10;
        if (cap_tempo > 0 && m->bpm * .75 > cap_tempo) sc -= 8;
        if (p.energy > cap_energy + 20) sc -= .05 * (p.energy - cap_energy - 20);
        if (id == cur) sc += .5;                                          // 지금 것을 조금 더 (자주 바뀌지 않게)
        for (auto &h : mood_hist) if (h.first == id && id != cur && now - h.second < 1200) { sc -= .25; break; }   // 최근에 들은 것은 조금 덜
        d.ranking.push_back({id, sc});
        if (sc > best) { best = sc; bm = m; }
    }
    std::sort(d.ranking.begin(), d.ranking.end(), [](auto &a, auto &b) { return a.second > b.second; });
    if (d.ranking.size() > 4) d.ranking.resize(4);
    if (!bm) return d;
    d.mood = bm->id; d.mood_name = bm->name;
    const MoodP &p = mood_[bm->id];

    // 조절값 (고른 분위기 기준으로 얼마나 비켜 가나)
    const double desired = 56 + 1.1 * energy;
    double tp = clampd((desired / bm->bpm - 1) / .2, -1, 1) * .6 + tempo;
    if (cap_tempo > 0) tp = std::min(tp, (cap_tempo / bm->bpm - 1) / .2);
    auto r2 = [](double x) { return std::round(x * 20) / 20; };          // 0.05 단위 (작은 흔들림에 다시 쓰지 않게)
    d.params.tempo = r2(clampd(tp, -1, 1));
    d.params.energy = r2(clampd((energy - p.energy) / 35, -1, 1));
    d.params.reg = r2(clampd((bright - p.bright) / 60, -.5, .5));
    d.params.dens = r2(clampd(dens + (energy - p.energy) / 120, -1, 1));
    d.params.novelty = r2(clampd(novelty, -1, 1));
    d.params.tension = r2(clampd(tension, -1, 1));
    d.params.space = r2(clampd(space, -1, 1));
    if (cap_energy < 100) {                                              // 기운 뚜껑(아기 · 졸음 막기 아닌 지킴 · 폭우 …)이 있으면 고른 분위기보다 세게 · 촘촘하게는 안 감
        d.params.energy = std::min(d.params.energy, 0.0);
        d.params.dens = std::min(d.params.dens, 0.0);
    }

    // 악기 지시
    const double talk = std::max(s.path("cabin.talk").num(0), (s.path("cabin.sound").str() == "talk" || s.path("cabin.sound").str() == "argument") ? 1.0 : 0.0);
    for (auto &[id, a] : inst_) {
        double w = instr.count(id) ? instr[id] : 0;
        int ev = 0;
        for (auto &e : a.evokes) ev += evokes.count(e);
        w += .2 * ev;
        if (talk > .2) w -= .9 * a.talk * talk;                           // 대화 중엔 말소리와 덜 겹치는 악기
        w = std::round(clampd(w, -2, 2) * 20) / 20;
        if (std::fabs(w) >= .05) d.steer.instr[id] = w;
        if (!drums && a.drum) d.steer.avoid.insert(id);
        if (!brass && a.brass) d.steer.avoid.insert(id);
        if (baby_only && !a.baby) d.steer.avoid.insert(id);
    }
    for (auto &a : avoid_i) d.steer.avoid.insert(a);
    for (auto &a : d.steer.avoid) { auto it = d.steer.instr.find(a); if (it != d.steer.instr.end() && it->second > 0) d.steer.instr.erase(it); }   // 뺀 악기는 '더 쓰기' 에서도 지움
    d.steer.energy_max = cap_energy / 100;
    d.steer.tempo_max = cap_tempo;
    d.steer.thin = thin.first >= 0 && thin.second;
    d.steer.lead_rest = lead_rest;

    // 주변 소리 · 섞기
    d.amb_sea = amb.count("sea") ? amb["sea"].second : 0;
    d.amb_rain = amb.count("rain") ? amb["rain"].second : 0;
    d.volume_db = cap_vol + vol_add; d.rear_db = cap_rear;
    d.duck_db = duck; d.talk_duck_db = tduck; d.talk_cut_db = tcut; d.overlap_db = overlap;
    d.end = end; d.urgent = urgent; d.move_now = move_now;
    d.job = job;
    // 화면 한 줄
    if (scene) { d.scene = scene->id; d.scene_name = scene->name; }
    // 장면이면 장면 한 줄 + 그 위에 덧칠된 것 중 센 것 (정체 · 터널 · 통화 · 아기 …) — 장면이 아니면 센 규칙 3개
    std::string head, extra;
    if (scene) {
        head = scene->say;
        int k = 0;
        for (auto *r : on) {
            if (r->say.empty() || r->aspect == "base" || r->priority < 45 || k >= 2) continue;
            bool in_scene = false;                                            // 장면 조건에 이미 들어 있는 신호면 빼고
            for (auto &kv : scene->match.o) for (auto &w : r->when.o) in_scene = in_scene || w.first == kv.first;
            if (in_scene) continue;
            extra += (extra.empty() ? "" : " · ") + r->say; k++;
        }
    } else {
        int k = 0;
        for (auto &b : d.because) { if (k++ == 3) break; head += (head.empty() ? "" : " · ") + b; }
    }
    d.line = (head.empty() ? std::string("") : head + (extra.empty() ? "" : " + " + extra) + " → ") + bm->name;
    return d;
}

Json Decision::to_json() const {
    Json j = Json::obj_();
    j.set("mood", Json::str_(mood)); j.set("mood_name", Json::str_(mood_name));
    j.set("energy", Json::num_(std::round(energy))); j.set("bright", Json::num_(std::round(bright)));
    Json p = Json::obj_();
    p.set("reg", Json::num_(params.reg)); p.set("tempo", Json::num_(params.tempo)); p.set("dens", Json::num_(params.dens));
    p.set("energy", Json::num_(params.energy)); p.set("novelty", Json::num_(params.novelty)); p.set("tension", Json::num_(params.tension)); p.set("space", Json::num_(params.space));
    j.set("params", p);
    Json in = Json::obj_();
    std::vector<std::pair<std::string, double>> iv(steer.instr.begin(), steer.instr.end());
    std::sort(iv.begin(), iv.end(), [](auto &a, auto &b) { return a.second > b.second; });
    for (size_t k = 0; k < iv.size() && k < 6; k++) if (iv[k].second > 0) in.set(iv[k].first, Json::num_(iv[k].second));
    j.set("instr", in);
    Json av = Json::arr_();
    for (auto &a : steer.avoid) av.a.push_back(Json::str_(a));
    j.set("avoid", av);
    Json caps = Json::obj_();
    if (steer.tempo_max > 0) caps.set("tempo_max", Json::num_(steer.tempo_max));
    if (steer.energy_max < 1) caps.set("energy_max", Json::num_(std::round(steer.energy_max * 100)));
    if (volume_db != 0) caps.set("volume_db", Json::num_(volume_db));
    if (rear_db != 0) caps.set("rear_db", Json::num_(rear_db));
    if (steer.thin) caps.set("thin", Json::bool_(true));
    if (steer.lead_rest) caps.set("lead_rest", Json::bool_(true));
    j.set("caps", caps);
    Json am = Json::obj_(); am.set("sea", Json::num_(amb_sea)); am.set("rain", Json::num_(amb_rain)); j.set("ambience", am);
    Json mx = Json::obj_();
    mx.set("duck_db", Json::num_(duck_db)); mx.set("talk_duck_db", Json::num_(talk_duck_db)); mx.set("talk_cut_db", Json::num_(talk_cut_db)); mx.set("overlap_db", Json::num_(overlap_db));
    j.set("mix", mx);
    j.set("scene", Json::str_(scene)); j.set("scene_name", Json::str_(scene_name)); j.set("job", Json::str_(job));
    j.set("line", Json::str_(line));
    Json bc = Json::arr_(); for (auto &b : because) bc.a.push_back(Json::str_(b)); j.set("because", bc);
    Json rl = Json::arr_(); for (auto &b : rules) rl.a.push_back(Json::str_(b)); j.set("rules", rl);
    Json rk = Json::arr_();
    for (auto &r : ranking) { Json x = Json::obj_(); x.set("mood", Json::str_(r.first)); x.set("score", Json::num_(std::round(r.second * 100) / 100)); rk.a.push_back(x); }
    j.set("ranking", rk);
    j.set("end", Json::bool_(end)); j.set("urgent", Json::bool_(urgent));
    return j;
}

Json Conductor::explain(const std::vector<std::string> &ids) const {
    Json out = Json::arr_();
    auto keys_of = [](const Json &w) {
        Json ks = Json::arr_();
        if (w.is_obj()) for (auto &kv : w.o) ks.a.push_back(Json::str_(kv.first));
        return ks;
    };
    for (auto &id : ids) {
        bool found = false;
        for (auto &r : rules_) {
            if (r.id != id) continue;
            Json j = Json::obj_();
            j.set("id", Json::str_(r.id)); j.set("aspect", Json::str_(r.aspect)); j.set("say", Json::str_(r.say));
            j.set("priority", Json::num_(r.priority)); j.set("keys", keys_of(r.when));
            out.a.push_back(j); found = true; break;
        }
        if (found) continue;
        for (auto &sc : scenes_) {
            if (sc.id != id) continue;
            Json j = Json::obj_();
            j.set("id", Json::str_(sc.id)); j.set("aspect", Json::str_("scene")); j.set("say", Json::str_(sc.name));
            j.set("priority", Json::num_(50)); j.set("keys", keys_of(sc.match));
            out.a.push_back(j); break;
        }
    }
    return out;
}
