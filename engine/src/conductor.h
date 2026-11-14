// 지휘자 (첫 겹: 규칙) — 상황(위치 · 날씨 · 여정 · 동승자 · 차 안 소리 · 말)을 받아 '무슨 음악을 어떻게' 를 정함
//   data/conductor/*.json: signals(상황 어휘) · rules(갈래 규칙) · scenes(장면) · instruments(악기 성격표) · moods(분위기 성격)
//   갈래마다 음악의 다른 면을 맡음 — 바탕(장르 · 기운) · 결(시간 · 요일) · 색(날씨) · 공간(장소) · 지킴(사람 · 안전) · 움직임(주행) · 섞기(차 안 소리)
//   → 상황이 겹쳐도 평균으로 뭉개지지 않고, 뜻 있는 조합은 '장면' 이 고유한 색을 줌
#pragma once
#include "compose.h"
#include "json.h"
#include <map>
#include <set>
#include <string>
#include <vector>

struct Decision {
    std::string mood, mood_name;                    // 고른 분위기
    double energy = 50, bright = 55;                // 감정 눈금 (0~100)
    Params params;                                  // 엔진 조절값
    Steer steer;                                    // 악기 · 뚜껑 지시
    double amb_sea = 0, amb_rain = 0;               // 주변 소리 (0 끔 · 1 기본)
    double volume_db = 0, duck_db = 0;              // 전체 크기 (뚜껑 · 길 안내 · 통화)
    double talk_duck_db = 0, talk_cut_db = 0, overlap_db = 0;   // 말소리만큼 (실시간) — 전체 · 말 대역 · 말과 겹치는 악기
    double rear_db = 0;                             // 뒷자리 (차의 자리별 스피커가 있을 때)
    bool end = false, urgent = false, move_now = false;
    std::string scene, scene_name, job, line;
    std::vector<std::string> because;               // 켜진 규칙 (사람이 읽는 말)
    std::vector<std::string> rules;                 // 켜진 규칙 id
    std::vector<std::pair<std::string, double>> ranking;   // 분위기 점수 위 4개
    Json to_json() const;
};

struct Conductor {
    bool loaded = false;
    std::string err;
    Json sit;                                       // 지금 상황 (보낸 것을 합쳐 둔 것)
    bool load(const std::string &dir, std::string *err);
    void update(const Json &patch, double now);     // 상황 일부 (null = 그 칸 지움)
    // 말 → 요청 (signals.json speech_words) · 돌려주는 값 = 요청 id ("" = 못 알아들음)
    std::string hear(const std::string &text, double now);
    void clear_requests() { intents.clear(); excluded.clear(); }
    void reset_holds() { since_.clear(); last_true_.clear(); }
    void exclude_mood(const std::string &id, double until) { excluded[id] = until; }
    Decision decide(double now, const std::string &cur_mood);
    Json derived(double now) const;                 // 상황 + 지휘자가 채운 칸 (시간대 · 주행 상태 · 터널 앞 …)
    double talk_of(const std::string &part) const;  // 악기의 말소리 겹침 (섞기용)
    const std::vector<std::string> &mood_order() const { return mood_ids; }
    // 켜진 규칙 · 장면이 어떤 상황 칸 때문인지 (화면 그림용): [{id, aspect, say, priority, keys:["place.kind", …]}]
    Json explain(const std::vector<std::string> &ids) const;

private:
    struct Rule { std::string id, aspect, say; Json when, set; int priority = 0; double hold = 2, release = 4; };
    struct Scene { std::string id, name, say; Json match, body; };
    struct Inst { double warm = .5, bright = .5, lively = .5, talk = .5, soft = .5; bool baby = true, brass = false, drum = false; std::vector<std::string> evokes; };
    struct MoodP { double energy = 50, bright = 50; std::string genre; std::vector<std::string> evokes; };
    std::vector<Rule> rules_;
    std::vector<Scene> scenes_;
    std::map<std::string, Inst> inst_;
    std::map<std::string, MoodP> mood_;
    std::vector<std::string> mood_ids;
    std::vector<std::pair<std::string, std::vector<std::string>>> words_;   // 요청 → 낱말들 (앞부터)
    std::map<std::string, double> since_;           // 규칙 · 장면 → 조건이 처음 맞은 시각 (이어짐 재기)
    std::map<std::string, double> last_true_;       // 규칙 · 장면 → 조건이 마지막으로 맞은 시각 (꺼짐 늦추기)
    std::map<std::string, double> intents;          // 말로 한 요청 → 끝나는 시각
    std::map<std::string, double> excluded;         // "다른 거" → 이 분위기는 이 시각까지 안 고름
    std::string place_now, place_prev;
    double place_at = -1e9, ahead_at = 0, eta_at = 0, last_now = 0;
    std::vector<std::pair<std::string, double>> mood_hist;   // (분위기, 고른 시각) — 같은 것만 돌지 않게
    bool match(const Json &s, const Json &when) const;
    bool held(const std::string &id, bool now_true, double hold, double release, double now);
};
