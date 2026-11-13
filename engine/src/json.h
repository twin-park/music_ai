// 아주 작은 JSON 읽기 · 쓰기 (지휘자 데이터 · 상황 입력용) — 객체 · 배열 · 문자열(\u 포함) · 수 · 참거짓 · null
#pragma once
#include <map>
#include <memory>
#include <string>
#include <vector>

struct Json {
    enum Type { NUL, BOOL, NUM, STR, ARR, OBJ } t = NUL;
    bool b = false;
    double n = 0;
    std::string s;
    std::vector<Json> a;
    std::vector<std::pair<std::string, Json>> o;      // 넣은 차례 그대로

    static Json parse(const std::string &text, std::string *err = nullptr);
    std::string dump() const;

    bool is_null() const { return t == NUL; }
    bool is_obj() const { return t == OBJ; }
    bool is_arr() const { return t == ARR; }
    bool is_str() const { return t == STR; }
    bool is_num() const { return t == NUM; }
    // 없으면 빈(null) 값
    const Json &operator[](const std::string &k) const;
    const Json &at(size_t i) const { static Json nil; return i < a.size() ? a[i] : nil; }
    Json *find(const std::string &k);
    void set(const std::string &k, const Json &v);
    size_t size() const { return t == ARR ? a.size() : t == OBJ ? o.size() : 0; }
    double num(double def = 0) const { return t == NUM ? n : t == BOOL ? (b ? 1 : 0) : def; }
    std::string str(const std::string &def = "") const { return t == STR ? s : def; }
    bool truthy() const { return t == BOOL ? b : t == NUM ? n != 0 : t == STR ? !s.empty() : t == ARR || t == OBJ; }
    // "a.b.c" 길 따라 찾기
    const Json &path(const std::string &dotted) const;
    // 객체 합치기: other 의 칸을 덮어씀 (객체는 안으로 들어가 합침, null 은 칸을 지움)
    void merge(const Json &other);

    static Json num_(double v) { Json j; j.t = NUM; j.n = v; return j; }
    static Json str_(const std::string &v) { Json j; j.t = STR; j.s = v; return j; }
    static Json bool_(bool v) { Json j; j.t = BOOL; j.b = v; return j; }
    static Json obj_() { Json j; j.t = OBJ; return j; }
    static Json arr_() { Json j; j.t = ARR; return j; }
};
