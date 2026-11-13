// 변주 — 오래 들어도 되풀이 느낌이 없게, 그러나 뒤죽박죽도 아니게 (한 분위기의 정체성: 악기 팔레트 · 느낌 · 조 가족은 지킴)
//   ① 이야기 흐름: 2마디 '생각' 가 나 다 라 를 차례로 내놓고 → 한참 뒤 가' 나' 다' 로 다시 부름(앞머리 · 리듬 · 코드는 살리고 끝은 새로)
//      → 다음 장 마 바 사 아 … · 가끔 먼 메아리(두 장 전 생각) · 장 길이가 단락과 어긋나 주기가 없음
//   ② 진행: 새 생각은 진행 AI 가 앞 8마디를 이어 새로 씀(최근 코드 덩어리와 똑같으면 피함) · 재화성 · 가끔 다른 조
//   ③ 단락 종류: 주제(A) · 대비(B) · 주고받기 · 쉬어가기(4마디) · 솔로(최근 생각들 코드 위 즉흥) · 12마디
//   ④ 편성: 분위기 팔레트(선율 · 둘째 목소리 · 반주 · 베이스 · 드럼) 안에서 한 번에 한 겹만 바꿈 · 최근 조합은 피함
//   ⑤ 세기: 주기가 서로 다른 두 물결 + 천천히 걷는 값 · 사용자 조절값(음 높이 · 빠르기 · 음 수 · 세기 · 새로움)
#include "compose.h"
#include "tokens.h"
#include <algorithm>
#include <cmath>
#include <cctype>
#include <map>
#include <set>
#include <thread>

// ---------------- 분위기 팔레트 ----------------
// 선율: mode 0 = 한 줄 악기(lead) · 1 피아노 드롭2 · 2 피아노 옥타브 · 3 피아노 3·6도 · 4 피아노 한 줄
struct LeadOpt { const char *part; int mode, lo, hi; double base, legato; };
// 둘째 목소리: 0 없음 · 1 가이드톤 대선율 · 2 옥타브/같은 음 겹치기 · 3 3·6도 아래 화음
struct SecondOpt { int kind; const char *part; int lo, hi; double base; };
// 반주: 0 없음 · 1 comp · 2 왼손 가이드 · 3 왼손 껍데기 · 4 펼침 · 5 쿵짝짝 · 7 기타 · 8 현악 패드 · 9 펼침+현악 · 10 알베르티 · 11 ph 악기 펼침(하프 등)
struct CompOpt { int kind; const char *feel, *voicing; double base; int lo, hi; const char *ph, *pl; double dens; };
struct BassOpt { const char *style; double base; const char *part; };
struct DrumOpt { const char *kind; int lvl; };
struct Palette {
    std::vector<LeadOpt> lead; std::vector<SecondOpt> second; std::vector<CompOpt> comp; std::vector<BassOpt> bass; std::vector<DrumOpt> drum;
    CompOpt core; bool has_core, trade, solo;
};
static const char *PR = "피아노 오른손", *PL = "피아노 왼손";
static const CompOpt NOCOMP{0, "", "", 0, 0, 0, "", "", 0};

static const Palette &palette(int style) {
    static std::vector<Palette> P;
    if (P.empty()) {
        P.resize(15);
        // 0 비 오는 날 — 피아노 · 테너 · 베이스 · 브러시
        P[0] = {{{PR, 1, 62, 86, 66, 1}, {"테너색소폰", 0, 50, 74, 76, 1}, {PR, 2, 64, 88, 70, 1}, {PR, 4, 64, 88, 68, 1}},
                {{0}, {1, "테너색소폰", 50, 67, 56}, {3, "테너색소폰", 50, 72, 60}, {2, PR, 64, 88, 58}},
                {{2, "", "", 46, 0, 0, "", "", .3}, {3, "", "", 40, 0, 0, "", "", .2}, {1, "ballad", "rootless", 47, 50, 68, PR, PL, .45},
                 {1, "swing", "rootless", 46, 50, 68, PR, PL, .7}, {1, "ballad", "quartal", 45, 50, 70, PR, PL, .4}},
                {{"two", 74, "베이스"}, {"walk", 75, "베이스"}, {"ballad", 70, "베이스"}},
                {{"brush", 0}, {"brush", 1}, {"brush_swing", 2}, {"", 0}}, NOCOMP, false, true, true};
        // 1 평온한 재즈 — 피아노 트리오 · 재즈기타
        P[1] = {{{PR, 3, 64, 86, 64, 1}, {"재즈기타", 0, 55, 77, 72, 1}, {PR, 1, 64, 88, 66, 1}, {PR, 2, 64, 88, 68, 1}, {"클라리넷", 0, 55, 79, 70, 1}},
                {{0}, {1, "재즈기타", 52, 67, 54}, {3, "재즈기타", 52, 72, 58}},
                {{2, "", "", 46, 0, 0, "", "", .3}, {1, "swing", "rootless", 46, 50, 68, PR, PL, .7}, {7, "swing", "", 46, 0, 0, "재즈기타", "", .6},
                 {1, "swing", "quartal", 44, 50, 70, PR, PL, .65}, {3, "", "", 40, 0, 0, "", "", .2}},
                {{"two", 72, "베이스"}, {"walk", 76, "베이스"}},
                {{"brush_swing", 0}, {"brush_swing", 1}, {"brush_swing", 2}, {"brush", 0}}, NOCOMP, false, true, true};
        // 2 밤 드라이브 — 로즈 · 뮤트 트럼펫 · 피아노 · 베이스 · 드럼
        P[2] = {{{"뮤트트럼펫", 0, 58, 80, 78, 1}, {PR, 3, 62, 86, 68, 1}, {PR, 2, 62, 86, 66, 1}},
                {{0}, {1, "뮤트트럼펫", 55, 70, 54}, {3, "뮤트트럼펫", 55, 74, 60}},
                {{1, "straight", "quartal", 48, 50, 72, "로즈", "로즈", .6}, {1, "straight", "rootless", 48, 50, 70, "로즈", "로즈", .6},
                 {1, "ballad", "quartal", 44, 50, 72, "로즈", "로즈", .35}, {1, "straight", "rootless", 46, 50, 68, PR, PL, .6}, {2, "", "", 44, 0, 0, "", "", .3}},
                {{"straight", 74, "베이스"}, {"two", 70, "베이스"}},
                {{"straight", 0}, {"straight", 1}, {"straight", 2}, {"", 0}}, NOCOMP, false, true, true};
        // 3 즐거운 대화 — 알토 · 비브라폰 · 피아노 · 베이스 · 드럼
        P[3] = {{{"알토색소폰", 0, 57, 79, 83, 1}, {"비브라폰", 0, 62, 86, 86, 1}, {PR, 1, 64, 88, 70, 1}},
                {{0}, {2, "비브라폰", 62, 91, 72}, {3, "알토색소폰", 55, 79, 66}, {1, "알토색소폰", 55, 70, 58}},
                {{1, "swing", "rootless", 50, 50, 68, PR, PL, .75}, {1, "swing", "quartal", 48, 50, 70, PR, PL, .7},
                 {1, "ballad", "rootless", 46, 50, 68, PR, PL, .45}, {2, "", "", 46, 0, 0, "", "", .3}},
                {{"walk", 80, "베이스"}, {"two", 74, "베이스"}},
                {{"ride", 0}, {"ride", 1}, {"ride", 2}, {"brush_swing", 1}}, NOCOMP, false, true, true};
        // 4 바닷가 보사노바 — 나일론 기타(늘) · 플루트 · 피아노 · 로즈 · 베이스 · 림샷 · 현악
        P[4] = {{{"플루트", 0, 67, 91, 78, .95}, {PR, 3, 64, 86, 64, 1}, {PR, 2, 64, 86, 62, 1}, {"마림바", 0, 62, 86, 72, .9}},
                {{0}, {1, "플루트", 67, 82, 58}, {3, "플루트", 64, 86, 62}},
                {{0, "", "", 0, 0, 0, "", "", .3}, {1, "bossa", "rootless", 40, 50, 68, "로즈", "로즈", .5}, {1, "bossa", "rootless", 42, 50, 68, PR, PL, .5},
                 {8, "", "", 44, 55, 74, "", "", .4}},
                {{"bossa", 74, "베이스"}},
                {{"bossa", 0}, {"bossa", 1}, {"", 0}}, {7, "bossa", "", 56, 0, 0, "나일론기타", "", .6}, true, true, true};
        // 5 아이 재우기 (3/4) — 피아노 · 첼레스타 · 현악
        P[5] = {{{PR, 3, 64, 84, 56, 1}, {PR, 4, 64, 84, 54, 1}, {"첼레스타", 0, 76, 96, 52, 1}, {PR, 1, 64, 84, 52, 1}},
                {{0}, {2, "첼레스타", 72, 96, 48}, {1, "현악", 52, 67, 38}, {2, "글로켄", 76, 100, 38}},
                {{5, "", "", 40, 0, 0, PL, "", .5}, {4, "", "", 38, 0, 0, PL, "", .6}, {9, "", "", 38, 55, 72, PL, "", .55}, {11, "", "", 38, 0, 0, "하프", "", .5}},
                {{"", 0, ""}},
                {{"", 0}, {"waltz_brush", 0}}, NOCOMP, false, false, false};
        // 6 진정 — 피아노 혼자 (+ 현악 조금)
        P[6] = {{{PR, 1, 64, 86, 58, 1}, {PR, 3, 64, 86, 58, 1}, {PR, 2, 64, 86, 60, 1}, {PR, 4, 64, 86, 56, 1}},
                {{0}, {1, "현악", 52, 67, 38}},
                {{4, "", "", 40, 0, 0, PL, "", .5}, {2, "", "", 42, 0, 0, "", "", .3}, {3, "", "", 38, 0, 0, "", "", .2}, {9, "", "", 38, 55, 74, PL, "", .5},
                 {11, "", "", 38, 0, 0, "하프", "", .5}},
                {{"", 0, ""}}, {{"", 0}}, NOCOMP, false, false, false};
        // 7 위로 — 피아노 · 첼로 · 바이올린 · 현악
        P[7] = {{{PR, 2, 66, 88, 64, 1}, {"첼로", 0, 50, 72, 66, 1}, {"바이올린", 0, 67, 91, 66, 1}, {PR, 1, 64, 86, 60, 1}, {"오보에", 0, 62, 84, 62, 1}},
                {{0}, {1, "첼로", 48, 62, 56}, {2, "바이올린", 67, 91, 54}, {1, "호른", 48, 62, 48}},
                {{4, "", "", 42, 0, 0, PL, "", .5}, {9, "", "", 40, 55, 72, PL, "", .55}, {8, "", "", 36, 43, 58, "", "", .35}, {2, "", "", 44, 0, 0, "", "", .3}},
                {{"", 0, ""}}, {{"", 0}}, NOCOMP, false, true, false};
        // 8 낮 드라이브 — 테너 · 피아노 · 로즈 · 일렉 베이스 · 드럼
        P[8] = {{{"테너색소폰", 0, 52, 76, 83, 1}, {PR, 2, 64, 88, 70, 1}, {PR, 3, 64, 86, 66, 1}},
                {{0}, {2, PR, 64, 88, 60}, {1, "테너색소폰", 50, 67, 58}, {3, "테너색소폰", 50, 74, 62}},
                {{1, "straight", "rootless", 50, 50, 68, PR, PL, .65}, {1, "straight", "quartal", 44, 48, 64, "로즈", "로즈", .55},
                 {1, "ballad", "rootless", 44, 50, 68, "로즈", "로즈", .35}, {2, "", "", 46, 0, 0, "", "", .3}, {7, "straight", "", 46, 0, 0, "스틸기타", "", .6}},
                {{"straight", 78, "일렉베이스"}, {"two", 72, "일렉베이스"}},
                {{"straight", 0}, {"straight", 1}, {"straight", 2}}, NOCOMP, false, true, true};
        // 9 클래식 피아노 — 피아노 혼자 (선율 한 줄 · 3·6도 · 옥타브 / 왼손 알베르티 · 펼침 · 길게 누름)
        P[9] = {{{PR, 4, 64, 88, 60, 1}, {PR, 3, 64, 86, 58, 1}, {PR, 2, 64, 88, 60, 1}},
                {{0}},
                {{10, "", "", 40, 0, 0, PL, "", .5}, {4, "", "", 40, 0, 0, PL, "", .55}, {2, "", "", 42, 0, 0, "", "", .3}},
                {{"", 0, ""}}, {{"", 0}}, NOCOMP, false, false, false};
        // 10 현악 앙상블 — 바이올린 · 첼로 · 현악 · 피아노
        P[10] = {{{"바이올린", 0, 67, 88, 66, 1}, {"첼로", 0, 50, 72, 66, 1}, {PR, 4, 64, 88, 58, 1}, {"클라리넷", 0, 55, 79, 62, 1}, {"오보에", 0, 62, 84, 62, 1}},
                 {{0}, {1, "첼로", 48, 62, 52}, {2, "바이올린", 67, 91, 50}, {1, "호른", 48, 62, 48}},
                 {{8, "", "", 40, 50, 70, "", "", .4}, {9, "", "", 36, 52, 70, PL, "", .55}, {4, "", "", 38, 0, 0, PL, "", .5}, {11, "", "", 38, 0, 0, "하프", "", .5}},
                 {{"", 0, ""}}, {{"", 0}}, NOCOMP, false, true, false};
        // 11 클래식 왈츠 (3/4) — 피아노 · 플루트 · 바이올린 · 첼로 · 현악
        P[11] = {{{PR, 3, 64, 86, 58, 1}, {"플루트", 0, 67, 91, 72, .95}, {"바이올린", 0, 67, 88, 66, 1}, {PR, 4, 64, 86, 56, 1}, {"클라리넷", 0, 55, 79, 64, 1},
                  {"오보에", 0, 62, 84, 62, 1}},
                 {{0}, {1, "첼로", 48, 62, 50}, {2, "글로켄", 76, 100, 40}},
                 {{5, "", "", 40, 0, 0, PL, "", .5}, {9, "", "", 38, 55, 72, PL, "", .55}},
                 {{"", 0, ""}}, {{"", 0}}, NOCOMP, false, true, false};
        // 12 상쾌한 아침 — 마림바 · 비브라폰 · 플루트 · 스틸 기타 · 일렉 베이스 · 드럼
        P[12] = {{{"마림바", 0, 62, 86, 74, .9}, {"비브라폰", 0, 62, 86, 72, 1}, {"플루트", 0, 67, 91, 72, .95}, {PR, 4, 64, 88, 64, 1}},
                 {{0}, {2, "글로켄", 76, 100, 44}, {1, "클라리넷", 52, 67, 50}},
                 {{7, "straight", "", 50, 0, 0, "스틸기타", "", .6}, {1, "straight", "rootless", 46, 50, 68, PR, PL, .55}, {7, "straight", "", 46, 0, 0, "나일론기타", "", .5}},
                 {{"straight", 74, "일렉베이스"}, {"two", 70, "일렉베이스"}},
                 {{"straight", 0}, {"straight", 1}, {"", 0}}, NOCOMP, false, true, false};
        // 13 밤 고속도로 — 비브라폰 · 테너 · 뮤트 트럼펫 · 로즈 · 재즈 기타 · 베이스 · 드럼
        P[13] = {{{"비브라폰", 0, 62, 86, 78, 1}, {"테너색소폰", 0, 52, 76, 80, 1}, {"뮤트트럼펫", 0, 58, 80, 76, 1}},
                 {{0}, {1, "테너색소폰", 50, 67, 54}, {3, "비브라폰", 60, 82, 58}},
                 {{1, "straight", "quartal", 48, 50, 72, "로즈", "로즈", .6}, {7, "straight", "", 46, 0, 0, "재즈기타", "", .6}, {1, "straight", "rootless", 46, 50, 68, PR, PL, .6}},
                 {{"straight", 76, "베이스"}, {"walk", 74, "베이스"}},
                 {{"straight", 1}, {"straight", 2}, {"straight", 0}}, NOCOMP, false, true, true};
        // 14 눈 오는 저녁 — 하프 · 첼레스타 · 클라리넷 · 호른 · 글로켄 · 현악
        P[14] = {{{"클라리넷", 0, 55, 79, 64, 1}, {"첼레스타", 0, 72, 96, 54, 1}, {PR, 4, 64, 86, 56, 1}, {"하프", 0, 62, 86, 60, 1}},
                 {{0}, {1, "호른", 48, 62, 46}, {2, "글로켄", 76, 100, 40}, {1, "첼로", 48, 62, 46}},
                 {{11, "", "", 40, 0, 0, "하프", "", .5}, {9, "", "", 36, 55, 72, PL, "", .55}, {8, "", "", 36, 52, 70, "", "", .35}},
                 {{"", 0, ""}}, {{"", 0}}, NOCOMP, false, true, false};
    }
    return P[style];
}

static bool is_piano_lead(const LeadOpt &l) { return l.mode != 0; }
static bool uses_rh(const CompOpt &c) { return c.kind == 1 && std::string(c.ph) == PR; }

static bool orch_ok(const Palette &P, const Orch &o) {
    const LeadOpt &L = P.lead[o.lead];
    const SecondOpt &S2 = P.second[o.second];
    const CompOpt &C = P.comp[o.comp];
    if (is_piano_lead(L) && uses_rh(C)) return false;                             // 피아노가 선율이면 오른손 반주는 안 됨
    if (S2.kind && std::string(S2.part) == L.part) return false;                  // 둘째 목소리는 다른 악기
    if (S2.kind == 2 && std::string(S2.part) == PR && is_piano_lead(L)) return false;
    if (C.kind == 7 && std::string(C.ph) == L.part) return false;                 // 기타가 선율이면 기타 반주 X
    if (C.kind == 11 && std::string(C.ph) == L.part) return false;                // 하프가 선율이면 하프 펼침 X
    if (S2.kind && C.kind == 11 && std::string(S2.part) == C.ph) return false;
    if (S2.kind && std::string(S2.part) == PR && uses_rh(C)) return false;
    return true;
}

std::string Session::orch_text() const {
    const Palette &P = palette(m.style);
    const LeadOpt &L = P.lead[orch.lead];
    static const char *LM[5] = {"", "드롭2", "옥타브", "3·6도", "한 줄"};
    std::string s = std::string(is_piano_lead(L) ? "피아노" : L.part) + (L.mode ? std::string("(") + LM[L.mode] + ")" : "");
    const SecondOpt &S2 = P.second[orch.second];
    static const char *SK[4] = {"", "대선율", "겹치기", "화음"};
    if (S2.kind) s += "+" + std::string(std::string(S2.part) == PR ? "피아노" : S2.part) + SK[S2.kind];
    const CompOpt &C = P.comp[orch.comp];
    static const char *CK[12] = {"", "컴핑", "왼손 가이드", "왼손 껍데기", "펼침", "쿵짝짝", "", "기타", "현악", "펼침+현악", "알베르티", "펼침"};
    if (C.kind) s += " / " + std::string(C.kind == 1 ? (std::string(C.ph) == PR ? "피아노 " : "로즈 ") : C.kind == 11 || (C.kind == 7 && std::string(C.ph) != "재즈기타") ? std::string(C.ph) + " " : "") +
                     CK[C.kind] + (C.kind == 1 ? std::string("(") + C.feel + ")" : "");
    const BassOpt &B = P.bass[orch.bass];
    if (B.style[0]) s += " / 베이스 " + std::string(B.style);
    const DrumOpt &D = P.drum[orch.drum];
    if (D.kind[0]) s += " / " + std::string(D.kind) + " " + std::to_string(D.lvl);
    return s;
}

// ---------------- 편성: 한 번에 한 겹만, 최근 조합 피하고, 세기에 맞게 ----------------
void Session::pick_orch(Role role) {
    const Palette &P = palette(m.style);
    auto density = [&](const Orch &o) {
        double d = P.comp[o.comp].dens * .4 + (P.drum[o.drum].kind[0] ? .25 + .12 * P.drum[o.drum].lvl : 0) + (P.bass[o.bass].style[0] ? .1 : 0) +
                   (P.second[o.second].kind ? .12 : 0);
        return d;
    };
    auto score = [&](const Orch &o, int changed) {
        double s = 0;
        int same = 0;
        for (size_t i = orch_hist.size() > 8 ? orch_hist.size() - 8 : 0; i < orch_hist.size(); i++) same += orch_hist[i] == o;
        s -= 1.1 * same;                                                         // 최근에 쓴 조합
        const double target = .15 + .7 * energy + .12 * this->P.dens;                 // 세기 · 음 수 조절값 높으면 촘촘하게
        s -= 1.6 * std::fabs(density(o) - target * ((m.style >= 5 && m.style <= 7) || (m.style >= 9 && m.style <= 11) || m.style == 14 ? .7 : 1));
        // 지휘자 지시: 상황에 맞는 악기는 더 · 쓰지 말 악기는 크게 덜
        const char *dk = P.drum[o.drum].kind;
        const std::string drum_part = dk[0] ? (std::string(dk).find("brush") != std::string::npos ? "브러시" : "드럼") : "";
        const std::string parts[5] = {P.lead[o.lead].part, P.second[o.second].kind ? P.second[o.second].part : "",
                                      P.comp[o.comp].kind == 1 || P.comp[o.comp].kind == 7 || P.comp[o.comp].kind == 11 ? P.comp[o.comp].ph : P.comp[o.comp].kind ? "피아노" : "",
                                      P.bass[o.bass].style[0] ? P.bass[o.bass].part : "", drum_part};
        for (int li = 0; li < 5; li++) {
            if (parts[li].empty()) continue;
            s += (li == 0 ? 1.0 : .6) * this->steer.weight(parts[li]);
            if (this->steer.avoided(parts[li])) s -= li == 0 ? 6 : 4;
        }
        if (changed == 0) s -= .25 + .5 * nov();                                 // 매번 조금은 바뀜 (새로움 조절값)
        if (changed > 1) s -= .7;                                                // 한꺼번에 많이 바뀌면 어색
        if (P.drum[o.drum].kind[0] == 0 && P.drum.size() > 1 && energy > .4 && !this->steer.avoided("드럼") && !this->steer.avoided("브러시")) s -= .8;
        if (role == R_SOLO && is_piano_lead(P.lead[o.lead])) s -= .6;
        return s + rng.uniform(0, .6);
    };
    if (!orch_set || steer_dirty) {                                               // 처음 · 지휘자 지시가 바뀜: 무작위 후보 중 가장 맞는 것 (실행할 때마다 다른 편성)
        steer_dirty = false;
        Orch best; double bs = -1e9;
        for (int k = 0; k < 40; k++) {
            Orch o{(int)rng.index(P.lead.size()), rng.random() < .6 ? 0 : (int)rng.index(P.second.size()), (int)rng.index(P.comp.size()),
                   (int)rng.index(P.bass.size()), (int)rng.index(P.drum.size())};
            if (!orch_ok(P, o)) continue;
            double s = score(o, 1);
            if (s > bs) { bs = s; best = o; }
        }
        orch = best; orch_set = true;
        orch_hist.push_back(orch);
        return;
    }
    std::vector<std::pair<Orch, int>> cand{{orch, 0}};
    const int sizes[5] = {(int)P.lead.size(), (int)P.second.size(), (int)P.comp.size(), (int)P.bass.size(), (int)P.drum.size()};
    for (int layer = 0; layer < 5; layer++)
        for (int v = 0; v < sizes[layer]; v++) {
            Orch o = orch;
            int *f[5] = {&o.lead, &o.second, &o.comp, &o.bass, &o.drum};
            if (*f[layer] == v) continue;
            *f[layer] = v;
            if (layer == 0 && orch_hist.size() >= 2 && orch_hist[orch_hist.size() - 2].lead != orch.lead) continue;   // 선율 악기는 2단락 이상 머문 뒤에
            cand.push_back({o, 1});
            if (rng.random() < .25) {                                             // 가끔 두 겹 함께
                Orch o2 = o;
                int l2 = (int)rng.index(5);
                int *g[5] = {&o2.lead, &o2.second, &o2.comp, &o2.bass, &o2.drum};
                if (l2 != layer) { *g[l2] = (int)rng.index(sizes[l2]); cand.push_back({o2, 2}); }
            }
        }
    Orch best = orch; double bs = -1e9;
    for (auto &[o, ch] : cand) {
        if (!orch_ok(P, o)) continue;
        double s = score(o, ch);
        if (s > bs) { bs = s; best = o; }
    }
    orch = best;
    orch_hist.push_back(orch);
}

// ---------------- 동기 변형 ----------------
static void tidy(std::vector<MelNote> &v, int span) {
    std::sort(v.begin(), v.end(), [](const MelNote &a, const MelNote &b) { return a.on < b.on; });
    std::vector<MelNote> o;
    for (auto n : v) {
        if (n.on < 0 || n.on >= span) continue;
        if (!o.empty() && n.on - o.back().on < 3) continue;
        n.d = std::max(1, std::min(n.d, span - n.on));
        o.push_back(n);
    }
    for (size_t i = 0; i + 1 < o.size(); i++) o[i].d = std::max(1, std::min(o[i].d, o[i + 1].on - o[i].on));
    v = o;
}

enum Op { OP_SEQ, OP_INV, OP_RETRO, OP_AUG, OP_DIM, OP_FRAG, OP_DISP, OP_ORN, OP_REG, OP_CROSS, OP_N };
static const char *OP_NAME[OP_N] = {"시퀀스", "반행", "역행", "늘이기", "줄이기", "조각", "밀기", "꾸밈", "음역", "교배"};

static std::vector<MelNote> apply_op(std::vector<MelNote> v, int op, int span, Rng &r, const std::vector<MelNote> *other) {
    if (v.empty()) return v;
    const int L = span / 2;
    switch (op) {
    case OP_SEQ: { static const int S[6] = {-5, -3, -2, 2, 3, 5}; int k = S[r.index(6)]; for (auto &n : v) n.p += k; break; }
    case OP_INV: { int p0 = v[0].p; for (auto &n : v) n.p = p0 - (n.p - p0); break; }
    case OP_RETRO: { std::vector<int> ps; for (auto &n : v) ps.push_back(n.p); std::reverse(ps.begin(), ps.end()); for (size_t i = 0; i < v.size(); i++) v[i].p = ps[i]; break; }
    case OP_AUG: { for (auto &n : v) { n.on *= 2; n.d *= 2; } break; }
    case OP_DIM: {
        std::vector<MelNote> h;
        for (auto n : v) { n.on /= 2; n.d = std::max(1, n.d / 2); h.push_back(n); }
        std::vector<MelNote> o = h;
        const int k = r.random() < .5 ? 0 : (r.random() < .5 ? 2 : -2);
        for (auto n : h) { n.on += L; n.p += k; o.push_back(n); }
        v = o; break;
    }
    case OP_FRAG: {
        const int n = std::min<int>((int)v.size(), 2 + (int)r.index(3));
        std::vector<MelNote> f(v.begin(), v.begin() + n);
        const int base = f[0].on, len = std::max(6, (f.back().on - base) + f.back().d);
        const int step = len <= 12 ? 12 : len <= 24 ? 24 : 48;
        static const int S[4] = {-2, 2, -1, 3};
        const int tr = S[r.index(4)];
        std::vector<MelNote> o;
        for (int k = 0, t = base; t < span && k < 6; k++, t += step)
            for (auto x : f) { x.on = x.on - base + t; x.p += tr * k; o.push_back(x); }
        v = o; break;
    }
    case OP_DISP: { int k = r.random() < .5 ? 6 : -6; for (auto &n : v) n.on += k; break; }
    case OP_ORN: {
        std::vector<MelNote> o;
        for (size_t i = 0; i < v.size(); i++) {
            o.push_back(v[i]);
            if (i + 1 < v.size() && v[i + 1].on - v[i].on >= 12 && std::abs(v[i + 1].p - v[i].p) >= 3) {
                MelNote pass{v[i].on + (v[i + 1].on - v[i].on) / 2, (v[i + 1].on - v[i].on) / 2, (v[i].p + v[i + 1].p) / 2};
                o.back().d = std::min(o.back().d, pass.on - v[i].on);
                o.push_back(pass);
            }
        }
        v = o; break;
    }
    case OP_REG: { int k = r.random() < .5 ? 12 : -12; for (auto &n : v) n.p += k; break; }
    case OP_CROSS:
        if (other && !other->empty()) {
            const int p0 = v[0].p;
            for (size_t i = 0; i < v.size(); i++) {
                const auto &b = (*other)[i % other->size()];
                v[i].p = p0 + (b.p - (*other)[0].p);
            }
        }
        break;
    }
    tidy(v, span);
    return v;
}

// ---------------- 재화성 ----------------
std::vector<Bar> Session::reharm(std::vector<Bar> bars, Role role, int &n) {
    n = 0;
    // 얼마나 자주: 분위기 양념(spice) × 세기 × 새로움 — 양념이 순하면 거의 안 하고, 조 밖으로 나가는 수(트라이톤 대리 · 반음 위 딸림)는 매운 쪽에서만
    const double sp = spice();
    const double rate = (m.jazzy ? .16 : .06) * (role == R_B || role == R_SOLO ? 1.4 : 1) * (.6 + .8 * energy) * (.5 + nov()) * (2.0 * sp);
    const int kp = S.key.pc, ts = m.ts;
    for (size_t i = 0; i < bars.size(); i++) {
        Bar &b = bars[i];
        if (b.empty()) continue;
        const ChordTok *nx = i + 1 < bars.size() && !bars[i + 1].empty() ? &bars[i + 1][0] : nullptr;
        for (auto &c : b) {                                                       // 트라이톤 대리: 5도 아래로 풀리는 딸림 → 반음 위에서 풀리게
            if (c[2] == QA_DOM && nx && pmod(c[1] - (*nx)[1], 12) == 7 && m.jazzy && sp >= .4 && rng.random() < rate * .7) { c[1] = (c[1] + 6) % 12; n++; }
        }
        if (ts == 4 && b.size() == 1 && b[0][2] == QA_DOM && rng.random() < rate * 1.3) {     // ii 끼우기
            const int r = b[0][1];
            b = {{0, (r + 7) % 12, QA_M7}, {2, r, QA_DOM}}; n++;
        } else if (ts == 4 && b.size() == 1 && nx && m.jazzy && sp >= .45 && rng.random() < rate * .4 && (*nx)[1] != b[0][1]) {   // 반음 위 딸림으로 다가가기
            b.push_back({2, ((*nx)[1] + 1) % 12, QA_DOM}); n++;
        }
        if (!m.minor && rng.random() < rate * .7)                                 // 빌린 화음: IV → iv
            for (auto &c : b) if (pmod(c[1] - kp, 12) == 5 && (c[2] == QA_MAJ || c[2] == QA_MAJ7)) { c[2] = QA_M7; n++; break; }
    }
    if (bars.size() >= 2 && !bars.back().empty() && bars.back()[0][1] == kp && rng.random() < rate) {   // 속임 종지: 끝 I → vi
        bars.back()[0] = {0, (kp + (m.minor ? 8 : 9)) % 12, m.minor ? QA_MAJ7 : QA_M7}; n++;
    }
    return bars;
}

// ---------------- 단락 종류 ----------------
Role Session::pick_kind() {
    if (n_body == 0) return R_A;
    const Palette &P = palette(m.style);
    std::vector<std::pair<Role, double>> w = {
        {R_A, 1.0 * (last_role == R_A ? .55 : 1)},
        {R_B, last_role == R_B ? 0 : since_b >= 2 ? .45 + .3 * (since_b - 2) : .04},
        {R_TRADE, P.trade && since_trade >= 3 && last_role != R_TRADE ? .3 + .05 * since_trade : 0},
        {R_BREAK, since_break >= 5 && energy > .55 && last_role != R_BREAK ? .22 + .04 * (since_break - 5) : 0},
        {R_SOLO, P.solo && m.jazzy && since_solo >= 6 && last_role != R_SOLO ? .25 + .04 * (since_solo - 6) : 0}};
    std::vector<double> ww;
    for (auto &x : w) ww.push_back(x.second);
    return w[rng.weighted(ww)].first;
}

// ---------------- 이야기 흐름: 가 나 다 라 → 가' 나' 다' → 마 바 사 아 → 마' 바' 사' (가끔 먼 메아리 나'') ----------------
//   새 생각 = 선율 AI 가 앞 흐름을 이어 새로 씀 (코드도 진행 AI 가 이어 씀) · 다시 부름 = 그 생각의 코드 + 앞머리 · 리듬은 살리고 끝만 새로
//   장(章) 길이(6~10칸)가 단락(4칸)과 어긋나 있어 주기가 생기지 않음
static const char *HANGUL[14] = {"가", "나", "다", "라", "마", "바", "사", "아", "자", "차", "카", "타", "파", "하"};

void Session::plan_chapter() {
    const double nv = nov();
    const int chap = ++chapter;
    const int n_new = 3 + (int)rng.weighted({.1 + .35 * (1 - nv), .45, .1 + .35 * nv});
    const int n_rec = std::max(2, n_new - (rng.random() < .2 + .35 * nv ? 1 : 0));
    for (int o = 0; o < n_new; o++) plan_q.push_back({0, chap, o});
    for (int o = 0; o < n_rec; o++) plan_q.push_back({1, chap, o});
    // 먼 메아리: 두 장 넘게 지난 생각 하나가 장 끝에 돌아옴 (익숙하게 할수록 자주)
    std::vector<int> old;
    for (size_t i = 0; i < ideas.size(); i++) if (ideas[i].chap < chap - 1 && ideas[i].recalls < 3 && !ideas[i].mel.empty()) old.push_back((int)i);
    if (!old.empty() && rng.random() < .5 - .3 * nv) { const Idea &x = ideas[old[rng.index(old.size())]]; plan_q.push_back({1, x.chap, x.ord}); }
}

const Idea *Session::find_idea(int chap, int ord) const {
    for (auto &x : ideas) if (x.chap == chap && x.ord == ord) return &x;
    return nullptr;
}

std::vector<Bar> Session::story_prog(Role role, const std::vector<Slot> &slots, int len, const std::map<int, Bar> *must) {
    const char sec = role == R_B ? 'B' : 'A';
    const std::vector<int> beats = m.ts == 4 ? std::vector<int>{0, 2} : std::vector<int>{0};
    std::vector<Bar> ctx_abs;                                                     // 문맥 = 바로 앞 8마디 코드
    for (int k = std::max(0, next_bar - 8); k < next_bar; k++) {                  // (재화성 전 것 — 양념이 문맥에 쌓이면 조에서 떠내려감)
        auto it = ai_chords.find(k);
        if (it == ai_chords.end()) { it = bar_chords.find(k); if (it == bar_chords.end()) continue; }
        ctx_abs.push_back(it->second);
    }
    const std::vector<Bar> ctx = to_deg(ctx_abs);
    std::map<int, Bar> fixed;
    const double nv = nov();
    for (size_t j = 0; j < slots.size(); j++) {                                   // 다시 부르는 칸은 그 생각의 코드 (둘째 마디는 가끔 새로)
        if (slots[j].kind != 1) continue;
        const Idea *x = find_idea(slots[j].chap, slots[j].ord);
        if (!x || x->deg.size() < 2) continue;
        fixed[(int)(2 * j)] = x->deg[0];
        if (role == R_SOLO || rng.random() < .8 - .4 * nv) fixed[(int)(2 * j + 1)] = x->deg[1];
    }
    if (must) for (auto &kv : *must) fixed[kv.first] = kv.second;
    // 클래식: 악절 끝을 종지로 — 가운데 칸 끝은 가끔 V 에 머물고(반종지), 마지막 칸은 (ii/IV/I →) V7 → I 로 맺거나 V 에 머묾. 새 생각 칸에만.
    if (m.src == "classical" && role != R_SOLO && role != R_BREAK && !m.minor) {
        const int ns2 = (int)slots.size();
        for (int j = 1; j < ns2; j += 2) {
            if (slots[j].kind != 0 || fixed.count(2 * j) || fixed.count(2 * j + 1)) continue;
            const bool last = j == ns2 - 1;
            if (last && rng.random() < .65) {
                static const Bar PRE4[4] = {{{0, 2, QA_MIN}, {2, 7, QA_DOM}}, {{0, 5, QA_MAJ}, {2, 7, QA_DOM}}, {{0, 0, QA_MAJ}, {2, 7, QA_DOM}}, {{0, 7, QA_DOM}}};
                fixed[2 * j] = m.ts == 4 ? PRE4[rng.index(4)] : Bar{{0, 7, QA_DOM}};
                fixed[2 * j + 1] = Bar{{0, 0, QA_MAJ}};
            } else if (last || rng.random() < .5) fixed[2 * j + 1] = Bar{{0, 7, QA_MAJ}};
        }
    }
    std::vector<Bar> best; double bs = -1e9; int brep = 99;
    const uint64_t base = rng.next();
    const ChordCtl ctl = chord_ctl();
    for (int k = 0; k < 5; k++) {
        if (k >= 3 && brep < 2) break;                                            // 최근 코드 덩어리와 많이 겹칠 때만 더 뜨겁게 다시
        auto bars = progression(M.chord, {{sec, len}}, m.minor, m.src, m.ts, beats, m.ctemp * (k < 3 ? 1.0 : 1.15 + .1 * (k - 3)), .92, base + k,
                                ctx.empty() ? nullptr : &ctx, last_sec, fixed.empty() ? nullptr : &fixed, &ctl, role == R_SOLO ? nullptr : &recent_cells);
        int rep = 0;
        for (size_t j = 0; j < slots.size() && 2 * j + 1 < bars.size(); j++) {
            if (slots[j].kind == 1) continue;
            const uint64_t sig = cell_sig(bars[2 * j], bars[2 * j + 1]);
            bool hit = false;
            for (auto &c : recent_cells) if (cell_sig(c[0], c[1]) == sig) { hit = true; break; }
            for (size_t i = 0; !hit && i < j; i++) hit = cell_sig(bars[2 * i], bars[2 * i + 1]) == sig;     // 이번 단락 앞 칸과 같은 뼈대
            rep += hit;
        }
        for (size_t j = 0; j < slots.size(); j++) {                               // 같은 단락에서 막 태어난 생각을 다시 부르면 그 칸 코드를 그대로
            if (slots[j].kind != 1 || find_idea(slots[j].chap, slots[j].ord)) continue;
            for (size_t i = 0; i < j; i++)
                if (slots[i].kind == 0 && slots[i].chap == slots[j].chap && slots[i].ord == slots[j].ord && 2 * j + 1 < bars.size()) {
                    bars[2 * j] = bars[2 * i]; bars[2 * j + 1] = bars[2 * i + 1];
                }
        }
        const double sc = score8(bars, m.src == "jazz") + Rng(base * 7 + k).uniform(0, .9) - 1.5 * rep + tonal_score(bars, false);
        if (sc > bs) { bs = sc; best = bars; brep = rep; }
    }
    for (size_t j = 0; j < slots.size() && 2 * j + 1 < best.size(); j++)
        if (slots[j].kind == 0) recent_cells.push_back({best[2 * j], best[2 * j + 1]});
    while (recent_cells.size() > 16) recent_cells.erase(recent_cells.begin());
    tonal_score(best, true);                                                      // 으뜸화음이 언제 마지막이었나 기억
    last_sec = sec;
    prog_score = bs;
    return best;
}

std::vector<BN> Session::write_story(Role role, const std::vector<Bar> &bars, int bar0, const std::vector<Slot> &slots) {
    using tk::TPB;
    const int L = m.ts * TPB, nb = (int)bars.size(), ns = (int)slots.size();
    const double nv = nov();
    struct Plan { int idea = -1, same = -1; int op = -1; double keep = 1; bool rest = false; std::string label; };
    std::vector<Plan> plan(ns);
    for (int j = 0; j < ns; j++) {
        Plan &p = plan[j];
        const Slot &sl = slots[j];
        if (sl.kind == 2) { p.rest = true; p.label = "쉼"; continue; }
        if (sl.kind != 1) continue;
        const Idea *x = find_idea(sl.chap, sl.ord);
        if (!x) {                                                                 // 같은 단락 앞 칸에서 막 태어난 생각이면 그 칸을 다시 부름
            for (int i = 0; i < j; i++) if (slots[i].kind == 0 && slots[i].chap == sl.chap && slots[i].ord == sl.ord) p.same = i;
            if (p.same < 0) continue;                                             // (못 찾으면 새로)
        } else p.idea = (int)(x - ideas.data());
        const int g = x ? x->recalls : 0;                                         // 0 → 가' (가볍게) · 1 이상 → 가'' (조금 더)
        //                                   시퀀스 반행 역행 늘이기 줄이기 조각 밀기 꾸밈 음역 교배
        static const double W1[OP_N] = {0, 0, 0, .07, .07, .2, .24, .42, 0, 0};
        static const double W2[OP_N] = {0, .08, .04, .12, .12, .2, .16, .28, 0, 0};
        if (rng.random() < (g == 0 ? .45 : .75) + .3 * (nv - .5)) { std::vector<double> w(g == 0 ? W1 : W2, (g == 0 ? W1 : W2) + OP_N); p.op = rng.weighted(w); }
        p.keep = g == 0 ? rng.uniform(.6, .85) : rng.uniform(.45, .7);
        p.keep = std::max(.3, std::min(.95, p.keep - .3 * (nv - .5)));
        p.label = (x ? x->name : std::string("@")) + (g < 2 ? std::string(g + 1, (char)39) : "(" + std::to_string(g + 1) + ")") + (p.op >= 0 ? std::string("(") + OP_NAME[p.op] + ")" : "");
    }
    std::vector<const ChordTok *> nexts;
    for (int i = 0; i < nb; i++) { const Bar &x = i + 1 < nb ? bars[i + 1] : bars[0]; nexts.push_back(x.empty() ? nullptr : &x[0]); }
    const double dt = (m.dens == 0 ? 2 : m.dens == 1 ? 3.5 : m.dens == 2 ? 5.5 : 8) * (role == R_BREAK ? .5 : 1) * (1 + .35 * P.dens);
    const double temp = m.mtemp + (role == R_B ? .05 : 0) + (energy - .5) * .06;
    const int maxn = std::max(2, m.maxn + (energy > .7 ? 1 : energy < .25 ? -1 : 0) + (int)std::lround(2 * P.dens));
    const int lo = m.mel_lo + reg_shift(), hi = m.mel_hi + reg_shift();
    // 세 번 써 보기를 동시에 (각자 선율 AI 문맥 사본) — 앞 단락 마지막 음에서 이어 씀
    const uint64_t seed0 = rng.next();
    w->no_copy = 2.0 + 2.0 * nv;                                                  // 지난 마디 통째로 베끼기 막기 (새로움 높을수록 세게)
    w->consonance = consonance();                                                 // 강박 · 긴 음을 코드 안쪽으로 (긴장감 조절값이 높으면 느슨하게)
    struct Try { MelodyWriter w; std::vector<BNote> out; std::vector<std::vector<MelNote>> ph; double sc = -1e18; };
    std::vector<Try> tries;
    for (int t = 0; t < 3; t++) tries.push_back({*w, {}, {}, -1e18});
    auto run = [&](int t) {
        Try &T = tries[t];
        MelodyWriter &wr = T.w;
        wr.rng.reseed(seed0 + t);
        Rng r(seed0 * 31 + t);
        std::vector<BNote> out;
        std::vector<std::vector<MelNote>> ph(ns);
        for (int j = 0; j < ns; j++) {
            const Plan &p = plan[j];
            std::vector<MelNote> f;
            if ((p.idea >= 0 && !ideas[p.idea].mel.empty()) || (p.same >= 0 && !ph[p.same].empty())) {
                f = p.idea >= 0 ? ideas[p.idea].mel : ph[p.same];
                const int key0 = p.idea >= 0 ? ideas[p.idea].key_pc : S.key.pc;
                if (p.op >= 0) f = apply_op(f, p.op, 2 * L, r, nullptr);
                if (!f.empty()) {
                    // 조가 바뀌었으면 그만큼 옮기고, 옥타브는 통째로 (첫 음이 앞 음과 가깝게)
                    const int delta = pmod(S.key.pc - key0 + 6, 12) - 6;
                    int lo_p = 999, hi_p = -999; double mean = 0;
                    for (auto &n : f) { n.p += delta; lo_p = std::min(lo_p, n.p); hi_p = std::max(hi_p, n.p); mean += n.p; }
                    mean /= f.size();
                    const double mid = (lo + hi) / 2.0;
                    int bo = 0; double bc = 1e9;
                    for (int o = -24; o <= 24; o += 12) {
                        const double cost = 4 * (std::max(0, lo - (lo_p + o)) + std::max(0, hi_p + o - hi)) +
                                            (wr.prev_p > 0 ? .6 * std::fabs(f[0].p + o - wr.prev_p) : 0) + .15 * std::fabs(mean + o - mid);
                        if (cost < bc) { bc = cost; bo = o; }
                    }
                    for (auto &n : f) {
                        n.p += bo;
                        while (n.p > hi + 2) n.p -= 12;
                        while (n.p < lo - 2) n.p += 12;
                        n.p = std::min(std::max(n.p, tk::P_LO), tk::P_HI);
                    }
                    const int k = std::max(1, (int)std::lround(f.size() * p.keep));          // 앞머리만 물려받고 끝은 AI 가 새로
                    if ((int)f.size() > k) f.resize(k);
                }
            }
            for (int h = 0; h < 2; h++) {
                const int bi = 2 * j + h;
                std::vector<MelNote> fb;
                for (auto &n : f) if (n.on / L == h) fb.push_back({n.on - h * L, n.d, n.p});
                auto got = wr.bar(bars[bi], nexts[bi], lo, hi, temp, .92, m.leap, fb.empty() ? nullptr : &fb, p.rest ? 0 : maxn,
                                  bi == nb - 1 || p.rest, true);
                for (auto &n : got) { out.push_back({bi, n.on, n.d, n.p}); ph[j].push_back({n.on + h * L, n.d, n.p}); }
            }
        }
        T.sc = role == R_BREAK ? 0 : mel_score(out, bars, dt);
        T.out = std::move(out); T.ph = std::move(ph);
    };
    {
        std::vector<std::thread> th;
        for (int t = 1; t < 3; t++) th.emplace_back(run, t);
        run(0);
        for (auto &x : th) x.join();
    }
    int bt = 0;
    for (int t = 1; t < 3; t++) if (tries[t].sc > tries[bt].sc) bt = t;
    std::vector<BNote> best = std::move(tries[bt].out);
    std::vector<std::vector<MelNote>> best_ph = std::move(tries[bt].ph);
    *w = std::move(tries[bt].w);
    // 새 생각은 이름 붙여 기억 · 다시 부른 생각은 횟수 셈
    std::string note;
    for (int j = 0; j < ns; j++) {
        Plan &p = plan[j];
        if (p.same >= 0) {                                                        // 같은 단락 앞 칸의 생각을 다시 부름
            for (auto &x : ideas)
                if (x.chap == slots[j].chap && x.ord == slots[j].ord) {
                    x.recalls++; recall_log.push_back({bar0 + 2 * j, x.seq});
                    const size_t at = p.label.find('@');
                    if (at != std::string::npos) p.label.replace(at, 1, x.name);
                }
        } else if (slots[j].kind != 2 && p.idea < 0) {
            Idea x;
            x.chap = slots[j].chap; x.ord = slots[j].ord; x.seq = idea_seq++;
            x.name = std::string(HANGUL[x.seq % 14]) + (x.seq >= 14 ? std::to_string(x.seq / 14 + 1) : "");
            x.deg = to_deg({bars[2 * j], bars[2 * j + 1]});
            x.mel = best_ph[j]; x.key_pc = S.key.pc; x.bar = bar0 + 2 * j;
            if (slots[j].kind == 1) x.chap = -1;                                      // (찾던 생각이 없어 새로 쓴 칸 — 다시 부를 대상 아님)
            ideas.push_back(x);
            p.label = x.name;
        } else if (p.idea >= 0) {
            ideas[p.idea].recalls++;
            recall_log.push_back({bar0 + 2 * j, ideas[p.idea].seq});
        }
        note += (j ? "·" : "") + p.label;
    }
    if (ideas.size() > 64) {                                                      // 오래된 생각은 잊음 (먼 메아리는 몇 장 안에서만)
        const int keep_from = chapter - 6;
        ideas.erase(std::remove_if(ideas.begin(), ideas.end(), [&](const Idea &x) { return x.chap < keep_from; }), ideas.end());
    }
    plan_note = "선율 " + note;
    // 틱 → 박
    std::vector<BN> xs;
    for (auto &n : best) xs.push_back({(double)(bar0 + n.bi) * S.ts + (double)n.on / TPB, (double)n.d / TPB, n.p});
    std::sort(xs.begin(), xs.end(), [](const BN &a, const BN &b) { return a.t < b.t; });
    std::vector<BN> outb;
    const double end = (double)(bar0 + nb) * S.ts;
    for (size_t i = 0; i < xs.size(); i++) {
        double d = xs[i].d;
        if (i + 1 < xs.size()) d = std::min(d, xs[i + 1].t - xs[i].t);
        d = std::min(d, end - xs[i].t);
        if (d > .12) outb.push_back({xs[i].t, d, xs[i].p});
    }
    return S.fix_avoid(outb, m.jazzy);
}

// ---------------- 되감기: 조절값이 바뀌면 이 마디부터 다시 씀 (이미 들린 생각 · 템포 곡선은 그대로) ----------------
void Session::rollback(int k) {
    std::vector<Slot> back;                                                       // 안 들린 칸은 계획 줄 앞으로 되돌림
    for (auto &h : hist) for (auto &bs : h.slots) if (bs.first >= k && bs.second.kind != 2) back.push_back(bs.second);
    for (auto it = back.rbegin(); it != back.rend(); ++it) plan_q.push_front(*it);
    for (auto &rl : recall_log) if (rl.first >= k) for (auto &x : ideas) if (x.seq == rl.second) x.recalls--;
    recall_log.erase(std::remove_if(recall_log.begin(), recall_log.end(), [&](const std::pair<int, int> &rl) { return rl.first >= k; }), recall_log.end());
    ideas.erase(std::remove_if(ideas.begin(), ideas.end(), [&](const Idea &x) { return x.bar >= k; }), ideas.end());
    idea_seq = 0;
    for (auto &x : ideas) idea_seq = std::max(idea_seq, x.seq + 1);
    while (!hist.empty() && hist.back().a >= k) hist.pop_back();
    if (!hist.empty()) {
        SecRec &h = hist.back();
        if (h.b > k) {
            h.b = k;
            h.slots.erase(std::remove_if(h.slots.begin(), h.slots.end(), [&](const std::pair<int, Slot> &x) { return x.first >= k; }), h.slots.end());
        }
        S.key = Key(h.key);
    }
    bar_chords.erase(bar_chords.lower_bound(k), bar_chords.end());
    ai_chords.erase(ai_chords.lower_bound(k), ai_chords.end());
    const double kb = (double)k * S.ts, bk = bpm_at(kb);                         // 들린 곳까지의 템포 곡선은 그대로 두고 여기서 끊음
    while (tempo_pts.size() > 1 && tempo_pts.back().first > kb + 1e-6) tempo_pts.pop_back();
    if (tempo_pts.back().first < kb - 1e-6) tempo_pts.push_back({kb, bk});
    if (T96.size() > (size_t)(kb * 96)) T96.resize((size_t)(kb * 96));
    pts_seen = tempo_pts.size();
    S.cut_after(kb);
    next_bar = k;
    w->prev_p = last_mel_pitch(k);
}

std::vector<BN> Session::write_solo(const std::vector<Bar> &bars, int bar0) {
    using tk::TPB;
    if (!w_solo) w_solo = std::make_unique<MelodyWriter>(&M.melody, m.ts, "solo", m.feel, m.tempo, m.minor, std::min(3, m.dens + 1), m.reg, rng.next(),
                                                         m.src, std::max(1, ct_level() - 1));
    w_solo->no_copy = 3.0;
    w_solo->consonance = .8 * consonance();
    const int nb = (int)bars.size();
    std::vector<const ChordTok *> nexts;
    for (int i = 0; i < nb; i++) { const Bar &x = i + 1 < nb ? bars[i + 1] : bars[0]; nexts.push_back(x.empty() ? nullptr : &x[0]); }
    auto base = w_solo->r.snapshot();
    double bs = -1e18; std::vector<BNote> best; Runner::Snap bsn;
    const uint64_t s0 = rng.next();
    for (int t = 0; t < 2; t++) {
        if (t) w_solo->r.restore(base);
        w_solo->prev_p = -1; w_solo->rng.reseed(s0 + t);
        std::vector<BNote> out;
        for (int bi = 0; bi < nb; bi++)
            for (auto &n : w_solo->bar(bars[bi], nexts[bi], m.mel_lo - 2, m.mel_hi + 2, m.mtemp + .04, .93, m.leap + 2, nullptr, m.maxn + 4, bi == nb - 1))
                out.push_back({bi, n.on, n.d, n.p});
        double sc = mel_score(out, bars, 6);
        if (sc > bs) { bs = sc; best = out; bsn = w_solo->r.snapshot(); }
    }
    w_solo->r.restore(bsn);
    plan_note = "솔로 (선율 AI 즉흥)";
    std::vector<BN> xs;
    for (auto &n : best) xs.push_back({(double)(bar0 + n.bi) * S.ts + (double)n.on / TPB, (double)n.d / TPB, n.p});
    std::sort(xs.begin(), xs.end(), [](const BN &a, const BN &b) { return a.t < b.t; });
    std::vector<BN> o;
    for (size_t i = 0; i < xs.size(); i++) {
        double d = xs[i].d;
        if (i + 1 < xs.size()) d = std::min(d, xs[i + 1].t - xs[i].t);
        d = std::min(d, (double)(bar0 + nb) * S.ts - xs[i].t);
        if (d > .1) o.push_back({xs[i].t, d, xs[i].p});
    }
    return S.fix_avoid(o, m.jazzy);
}

// ---------------- 편곡 (팔레트) ----------------
void Session::arrange_body(Role role, int a, int b, const std::vector<BN> &mel) {
    const Palette &P = palette(m.style);
    Song &s = S;
    const LeadOpt &L = P.lead[orch.lead];
    const SecondOpt &S2 = P.second[orch.second];
    const CompOpt &C = P.comp[orch.comp];
    const BassOpt &B = P.bass[orch.bass];
    const DrumOpt &D = P.drum[orch.drum];
    auto bars = range_v(a, b);
    static const char *MODE[5] = {"", "block", "octave", "dyad", "line"};
    const int rs = reg_shift();                                                   // 음 높이 조절값 (선율 · 둘째 목소리)
    auto place = [&](const LeadOpt &lo, const std::vector<BN> &notes, double vadj) {
        auto x = oct_fit(notes, lo.lo + rs, lo.hi + rs);
        if (lo.mode == 0) s.lead(lo.part, x, lo.base + vadj, lo.legato);
        else s.piano_melody(x, lo.base + vadj, MODE[lo.mode]);
        return x;
    };
    std::vector<BN> placed;
    const bool rest_lead = steer.thin || steer.lead_rest;                         // 지휘자: 터널(비우기) · 언성(선율 쉼) — 선율은 기억만 하고 소리는 안 냄
    if (rest_lead) {}
    else if (role == R_TRADE) {                                                   // 주고받기: 2마디씩 두 악기
        int alt = -1;
        for (int k = 0; k < (int)P.lead.size(); k++)
            if (k != orch.lead && std::string(P.lead[k].part) != L.part && (P.lead[k].mode == 0 || L.mode == 0) &&
                !(is_piano_lead(P.lead[k]) && uses_rh(C))) { alt = k; if (rng.random() < .5) break; }
        for (int k = 0; a + k < b; k += 2) {
            auto seg = sel(mel, s, a + k, a + k + 2);
            auto x = place((k / 2) % 2 == 0 || alt < 0 ? L : P.lead[alt], seg, 4);
            placed.insert(placed.end(), x.begin(), x.end());
        }
    } else if (!mel.empty()) placed = place(L, mel, role == R_SOLO ? 4 : role == R_BREAK ? -6 : 0);
    // 둘째 목소리 (쉬어가기 · 솔로엔 없음)
    if (S2.kind && role != R_BREAK && role != R_SOLO && !placed.empty()) {
        if (S2.kind == 1) s.guide_line(a, b, S2.part, S2.base, S2.lo + rs / 2, S2.hi + rs / 2);
        else if (S2.kind == 2) {
            auto x = oct_fit(up(placed, 12), S2.lo + rs, S2.hi + rs);
            if (std::string(S2.part) == PR) s.piano_melody(x, S2.base, "line");
            else s.lead(S2.part, x, S2.base);
        } else if (S2.kind == 3) {
            for (auto &n : placed) {
                if (n.d < .45) continue;
                const Chord &c = s.chord(n.t);
                for (int k : {3, 4, 8, 9}) {
                    int h = n.p - k;
                    if (!(c.has_tone(h) || c.has_tension(h))) continue;
                    h = fit(h, S2.lo + rs, S2.hi + rs);
                    s.add(S2.part, n.t + .01, n.d, h, S2.base + rng.randint(-3, 3));
                    break;
                }
            }
        }
    }
    // 반주
    auto do_comp = [&](const CompOpt &c) {
        switch (c.kind) {
        case 1: s.comp(bars, c.feel, c.base + (role == R_BREAK ? 2 : 0), c.voicing, c.lo, c.hi, placed, c.ph, c.pl); break;
        case 2: s.lh_guide(a, b, c.base); s.pedals(a, b, m.ts == 3 ? 3 : 2); break;
        case 3: s.lh_guide(a, b, c.base, true); s.pedals(a, b, m.ts == 3 ? 3 : 2); break;
        case 4: s.piano_pattern(a, b, "arp", c.base); s.pedals(a, b, m.ts == 3 ? 3 : 2); break;
        case 5: s.piano_pattern(a, b, "waltz", c.base); s.pedals(a, b, 3); break;
        case 7: s.guitar_comp(bars, c.ph, c.feel, c.base); break;
        case 8: s.strings_pad(a, b, "현악", c.base, c.lo, c.hi); break;
        case 9: s.piano_pattern(a, b, m.ts == 3 ? "waltz" : "arp", c.base); s.pedals(a, b, m.ts == 3 ? 3 : 2); s.strings_pad(a, b, "현악", c.base, c.lo, c.hi); break;
        case 11: s.piano_pattern(a, b, m.ts == 3 ? "waltz" : "arp", c.base, c.ph); break;
        case 10: s.piano_pattern(a, b, "alberti", c.base); s.pedals(a, b, 2); break;
        }
    };
    if (P.has_core) do_comp(P.core);
    do_comp(C);
    if (m.style == 10)                                                            // 현악 앙상블: 베이스 악기가 없으니 현악 저음이 근음을 길게 받침
        for (auto &sp : s.spans_in(a, b)) s.add("현악", sp.a, sp.b - sp.a + .05, fit(sp.c.root, 36, 47), 38 + 8 * energy);
    const std::string dpart = std::string(D.kind).find("brush") != std::string::npos ? "브러시" : "드럼";
    const bool drums_ok = !steer.thin && !steer.avoided(dpart);
    if (B.style[0] && !(role == R_BREAK && rng.random() < .5)) s.bass(a, b, role == R_SOLO && std::string(B.style) == "two" && P.bass.size() > 1 ? "walk" : B.style, B.base, B.part);
    if (drums_ok && D.kind[0] && role != R_BREAK) s.drums(a, b, D.kind, std::min(2, D.lvl + (role == R_SOLO ? 1 : 0)), 8, true);
    if (drums_ok && D.kind[0] && role == R_BREAK && std::string(D.kind).find("brush") != std::string::npos) s.drums(a, b, D.kind, 0, 99, false);
    // 세기가 높을 때 현악이 있는 분위기는 현악이 아주 작게 감쌈 (없던 단락에만)
    if (((m.style >= 4 && m.style <= 7) || m.style == 11 || m.style == 14) && energy > .62 && role != R_BREAK && !steer.thin) {
        bool has = false;
        for (auto &n : S.pool) has = has || (n.sec == S.cur_sec && S.names[n.part] == "현악");
        if (!has) S.strings_pad(a, b, "현악", 32 + 10 * energy, 55, 72);
    }
}

// ---------------- 새 분위기의 도입 · 끝 (팔레트만으로) ----------------
void Session::arrange_generic(Role R, int a, int b, const std::vector<BN> &M) {
    const Palette &P = palette(m.style);
    Song &s = S;
    const LeadOpt &L = P.lead[0];
    const CompOpt &C = P.comp[0];
    const BassOpt &B = P.bass[0];
    const DrumOpt &D = P.drum[0];
    auto bars = range_v(a, b);
    auto comp = [&](double base) {
        switch (C.kind) {
        case 1: s.comp(bars, C.feel, base, C.voicing, C.lo, C.hi, {}, C.ph, C.pl); break;
        case 7: s.guitar_comp(bars, C.ph, C.feel, base); break;
        case 11: s.piano_pattern(a, b, m.ts == 3 ? "waltz" : "arp", base, C.ph); break;
        case 8: s.strings_pad(a, b, "현악", base, C.lo, C.hi); break;
        default: s.piano_pattern(a, b, m.ts == 3 ? "waltz" : "arp", base); s.pedals(a, b, m.ts == 3 ? 3 : 2);
        }
    };
    const std::string dpart = std::string(D.kind).find("brush") != std::string::npos ? "브러시" : "드럼";
    const bool drums_ok = D.kind[0] && !steer.avoided(dpart);
    if (R == R_INTRO) {                                                           // 반주 + (베이스 · 가벼운 북) + 선율 악기가 가이드톤으로 살짝
        comp(C.base - 2);
        if (B.style[0]) s.bass(a, b, B.style, B.base - 4, B.part);
        if (drums_ok) s.drums(a, b, D.kind, 0, 4, false);
        auto t = top_line(s, a, b, std::max(L.lo, 64), std::min(L.hi, 84));
        if (L.mode == 0) s.lead(L.part, t, L.base - 10, L.legato); else s.piano_melody(t, L.base - 10, "line");
        if (m.style == 14) s.strings_pad(a, b, "현악", 34, 55, 72);
    } else {                                                                      // 끝 (R_TAG): 선율 + 반주 + 마지막 화음
        auto x = oct_fit(M, L.lo, L.hi);
        if (L.mode == 0) s.lead(L.part, x, L.base - 4, L.legato); else s.piano_melody(x, L.base - 4, "line");
        comp(C.base - 4);
        if (B.style[0]) s.bass(a, b, B.style, B.base - 6, B.part);
        if (drums_ok) s.drums(a, b, D.kind, 0, 99, false);
        if (m.style == 14) s.strings_pad(a, b, "현악", 34, 55, 72);
        final_chord(s, b, L.mode == 0 ? L.part : "", L.lo, std::min(L.hi, L.lo + 14), drums_ok ? (dpart == "브러시" ? "브러시" : "드럼") : "", B.style[0] != 0, 48);
    }
}

// ---------------- 다음 단락 ----------------
Section Session::next() {
    S.cur_sec = n_sec;
    const int ts = m.ts;
    if (prog_a.empty()) {
        prog_a = to_abs(new_prog('A', nullptr, 0, nullptr));
        wT1 = rng.uniform(9, 14); wT2 = rng.uniform(3.4, 5.6); wP1 = rng.uniform(0, 6.283); wP2 = rng.uniform(0, 6.283);
        walk = rng.uniform(.35, .55);
    }
    if (need_intro) {                                                             // 도입: 첫 진행의 뒤 4마디 (분위기 고유 공식)
        need_intro = false;
        std::vector<Bar> intro(prog_a.begin() + 4, prog_a.begin() + 8);
        for (int i = 0; i < 4; i++) bar_chords[next_bar + i] = intro[i];
        S.add_chords(next_bar, intro, m.color);
        int a = next_bar, b = next_bar + 4;
        S.energy = energy;
        arrange_main(R_INTRO, a, b, {});
        finish_section(R_INTRO);
        next_bar = b;
        plan_note = "";
        return {R_INTRO, a, b, n_sec++};
    }
    const Role role = pick_kind();
    const int len = role == R_BREAK ? 4 : (role == R_A && n_body > 2 && rng.random() < .14) ? 12 : 8;
    const int a = next_bar, b = next_bar + len;
    // 세기: 천천히 걷는 값 + 주기가 서로 다른 두 물결
    if (n_body > 0) {
        e_vel = .6 * e_vel + rng.gauss(0, .05);
        walk = std::max(.2, std::min(.8, walk + e_vel));
    }
    energy = std::max(.08, std::min(std::max(.1, std::min(.95, steer.energy_max)), walk + .25 * P.energy + .17 * std::sin(6.283 * n_body / wT1 + wP1) + .1 * std::sin(6.283 * n_body / wT2 + wP2) +
                                             (role == R_B ? .05 : role == R_BREAK ? -.2 : role == R_SOLO ? .08 : 0)));
    // 이번 단락의 칸 (2마디씩) — 계획 줄에서 꺼냄 · 솔로는 최근 생각들의 코드 위에서 즉흥 · 쉬어가기는 한 칸 + 쉼
    const int ns = len / 2;
    std::vector<Slot> slots;
    if (role == R_SOLO) {
        for (int j = 0; j < ns; j++) {
            const int i = (int)ideas.size() - ns + j;
            slots.push_back(i >= 0 && ideas[i].chap > 0 ? Slot{1, ideas[i].chap, ideas[i].ord} : Slot{0, 0, 0});
        }
    } else {
        const int take = role == R_BREAK ? 1 : ns;
        while ((int)plan_q.size() < take) plan_chapter();
        for (int j = 0; j < take; j++) { slots.push_back(plan_q.front()); plan_q.pop_front(); }
        while ((int)slots.size() < ns) slots.push_back({2, 0, 0});
    }
    // 진행: 새 칸은 진행 AI 가 앞 8마디를 이어 쓰고, 다시 부르는 칸은 그 생각의 코드 · 가끔 가까운 조로 (새 칸에서만)
    std::string hnote;
    std::map<int, Bar> must;
    const bool modulate = (role == R_A || role == R_TRADE) && n_body >= 5 && since_mod >= 6 && slots[0].kind == 0 && rng.random() < .3 * (.5 + nov());
    if (modulate) {
        static const int UP_MAJ[5] = {5, 7, 2, 3, -3}, UP_MIN[4] = {5, 7, 3, -2};
        const int up = m.minor ? UP_MIN[rng.index(4)] : UP_MAJ[rng.weighted({.32, .32, .12, .12, .12})];
        S.key = Key(key_name(S.key.pc + up, m.minor));
        if (ts == 4) must[0] = m.minor ? Bar{{0, 2, QA_HDIM}, {2, 7, QA_DOM}} : Bar{{0, 2, QA_M7}, {2, 7, QA_DOM}};
        else must[0] = Bar{{0, 7, QA_DOM}};
        must[1] = Bar{{0, 0, m.minor ? QA_MIN : QA_MAJ7}};
        since_mod = 0;
        hnote = "조 옮김 → " + S.key.name;
    }
    std::vector<Bar> prog = to_abs(story_prog(role, slots, len, modulate ? &must : nullptr));
    if (len == 12) hnote += std::string(hnote.empty() ? "" : " · ") + "12마디로 늘임";
    for (int i = 0; i < (int)prog.size(); i++) ai_chords[a + i] = prog[i];
    S.b9_rate = .2 + .7 * spice();
    S.crunch = spice();
    int nre = 0;
    if (role != R_BREAK && n_body > 0) prog = reharm(prog, role, nre);
    if (nre) hnote += std::string(hnote.empty() ? "" : " · ") + "재화성 " + std::to_string(nre);
    for (int i = 0; i < (int)prog.size(); i++) bar_chords[a + i] = prog[i];
    S.add_chords(a, prog, m.color);
    // 템포도 아주 조금 따라 움직임 (±1.5%, 조절값 반영) — 진정은 루바토가 따로
    const double bb = base_bpm();
    if (m.style == 6 || m.style == 9) {                                           // 피아노 혼자: 네 마디마다 살짝 늦춤 (루바토)
        const double rit = m.style == 6 ? .9 : .94;
        if (tempo_pts.back().first < (double)a * ts - 1e-6) tempo_pts.push_back({(double)a * ts, bpm_at((double)a * ts)});
        for (int g = a; g < b; g += 4) {
            tempo_pts.push_back({(double)g * ts + .01, bb});
            tempo_pts.push_back({(double)(g + 4) * ts - 1, bb});
            tempo_pts.push_back({(double)(g + 4) * ts - .01, bb * rit});
        }
    } else {
        if (tempo_pts.back().first < (double)a * ts - 1e-6) tempo_pts.push_back({(double)a * ts, bpm_at((double)a * ts)});
        tempo_pts.push_back({(double)b * ts, bb * (1 + .03 * (energy - .5))});
    }
    // 편성 → 선율 → 편곡
    pick_orch(role);
    auto mel = role == R_SOLO ? write_solo(prog, a) : write_story(role, prog, a, slots);
    plan_note = (hnote.empty() ? "" : hnote + " · ") + plan_note + " · 편성 " + orch_text() + " · 세기 " + std::to_string((int)std::lround(energy * 100));
    {
        SecRec h; h.a = a; h.b = b; h.key = S.key.name;
        if (role != R_SOLO) for (int j = 0; j < ns; j++) h.slots.push_back({a + 2 * j, slots[j]});
        hist.push_back(h);
        if (hist.size() > 64) hist.erase(hist.begin());
    }
    last_mel = mel;
    S.energy = energy;
    arrange_body(role, a, b, mel);
    finish_section(role == R_TRADE || role == R_SOLO ? R_A : role == R_BREAK ? R_A2 : role);
    next_bar = b;
    role_last[role] = n_body;
    since_b = role == R_B ? 0 : since_b + 1;
    since_trade = role == R_TRADE ? 0 : since_trade + 1;
    since_break = role == R_BREAK ? 0 : since_break + 1;
    since_solo = role == R_SOLO ? 0 : since_solo + 1;
    since_mod++;
    last_role = role;
    n_body++;
    return {role, a, b, n_sec++};
}
