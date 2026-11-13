#include "json.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>

namespace {
struct P {
    const std::string &s;
    size_t i = 0;
    std::string err;
    explicit P(const std::string &x) : s(x) {}
    void ws() {
        while (i < s.size()) {
            const char c = s[i];
            if (c == ' ' || c == '\t' || c == '\n' || c == '\r') { i++; continue; }
            if (c == '/' && i + 1 < s.size() && s[i + 1] == '/') { while (i < s.size() && s[i] != '\n') i++; continue; }   // // 설명 줄 허용
            break;
        }
    }
    bool fail(const char *m) { if (err.empty()) { char b[96]; std::snprintf(b, sizeof b, "%s (%zu번째 글자)", m, i); err = b; } return false; }
    static void utf8(std::string &o, unsigned cp) {
        if (cp < 0x80) o += (char)cp;
        else if (cp < 0x800) { o += (char)(0xC0 | (cp >> 6)); o += (char)(0x80 | (cp & 0x3F)); }
        else if (cp < 0x10000) { o += (char)(0xE0 | (cp >> 12)); o += (char)(0x80 | ((cp >> 6) & 0x3F)); o += (char)(0x80 | (cp & 0x3F)); }
        else { o += (char)(0xF0 | (cp >> 18)); o += (char)(0x80 | ((cp >> 12) & 0x3F)); o += (char)(0x80 | ((cp >> 6) & 0x3F)); o += (char)(0x80 | (cp & 0x3F)); }
    }
    bool hex4(unsigned &v) {
        if (i + 4 > s.size()) return fail("\\u 가 짧음");
        v = 0;
        for (int k = 0; k < 4; k++) {
            const char c = s[i++];
            v <<= 4;
            if (c >= '0' && c <= '9') v |= c - '0'; else if (c >= 'a' && c <= 'f') v |= c - 'a' + 10; else if (c >= 'A' && c <= 'F') v |= c - 'A' + 10;
            else return fail("\\u 뒤가 16진수가 아님");
        }
        return true;
    }
    bool string(std::string &o) {
        if (s[i] != '"') return fail("따옴표가 있어야 함");
        i++;
        while (i < s.size()) {
            const char c = s[i++];
            if (c == '"') return true;
            if (c != '\\') { o += c; continue; }
            if (i >= s.size()) break;
            const char e = s[i++];
            switch (e) {
            case 'n': o += '\n'; break; case 't': o += '\t'; break; case 'r': o += '\r'; break;
            case 'b': o += '\b'; break; case 'f': o += '\f'; break;
            case 'u': {
                unsigned v; if (!hex4(v)) return false;
                if (v >= 0xD800 && v < 0xDC00 && i + 6 <= s.size() && s[i] == '\\' && s[i + 1] == 'u') {
                    i += 2; unsigned lo; if (!hex4(lo)) return false;
                    v = 0x10000 + ((v - 0xD800) << 10) + (lo - 0xDC00);
                }
                utf8(o, v); break;
            }
            default: o += e;
            }
        }
        return fail("문자열이 안 닫힘");
    }
    bool value(Json &j, int depth) {
        if (depth > 64) return fail("너무 깊음");
        ws();
        if (i >= s.size()) return fail("값이 없음");
        const char c = s[i];
        if (c == '{') {
            j.t = Json::OBJ; i++; ws();
            if (i < s.size() && s[i] == '}') { i++; return true; }
            while (true) {
                ws(); std::string k;
                if (i >= s.size() || !string(k)) return fail("칸 이름이 있어야 함");
                ws(); if (i >= s.size() || s[i] != ':') return fail(": 가 있어야 함");
                i++;
                Json v; if (!value(v, depth + 1)) return false;
                j.o.push_back({k, std::move(v)});
                ws();
                if (i < s.size() && s[i] == ',') { i++; ws(); if (i < s.size() && s[i] == '}') { i++; return true; } continue; }   // 끝 쉼표 허용
                if (i < s.size() && s[i] == '}') { i++; return true; }
                return fail(", 또는 } 가 있어야 함");
            }
        }
        if (c == '[') {
            j.t = Json::ARR; i++; ws();
            if (i < s.size() && s[i] == ']') { i++; return true; }
            while (true) {
                Json v; if (!value(v, depth + 1)) return false;
                j.a.push_back(std::move(v));
                ws();
                if (i < s.size() && s[i] == ',') { i++; ws(); if (i < s.size() && s[i] == ']') { i++; return true; } continue; }
                if (i < s.size() && s[i] == ']') { i++; return true; }
                return fail(", 또는 ] 가 있어야 함");
            }
        }
        if (c == '"') { j.t = Json::STR; return string(j.s); }
        if (s.compare(i, 4, "true") == 0) { j.t = Json::BOOL; j.b = true; i += 4; return true; }
        if (s.compare(i, 5, "false") == 0) { j.t = Json::BOOL; j.b = false; i += 5; return true; }
        if (s.compare(i, 4, "null") == 0) { j.t = Json::NUL; i += 4; return true; }
        if (c == '-' || c == '+' || (c >= '0' && c <= '9')) {
            const char *st = s.c_str() + i; char *en = nullptr;
            j.t = Json::NUM; j.n = std::strtod(st, &en);
            if (en == st) return fail("수가 아님");
            i += en - st; return true;
        }
        return fail("모르는 값");
    }
};
void dump_str(std::string &o, const std::string &s) {
    o += '"';
    for (unsigned char c : s) {
        if (c == '"') o += "\\\""; else if (c == '\\') o += "\\\\"; else if (c == '\n') o += "\\n"; else if (c == '\t') o += "\\t";
        else if (c < 0x20) { char b[8]; std::snprintf(b, sizeof b, "\\u%04x", c); o += b; }
        else o += (char)c;
    }
    o += '"';
}
void dump(const Json &j, std::string &o) {
    switch (j.t) {
    case Json::NUL: o += "null"; break;
    case Json::BOOL: o += j.b ? "true" : "false"; break;
    case Json::NUM: {
        char b[32];
        if (std::fabs(j.n - std::round(j.n)) < 1e-9 && std::fabs(j.n) < 1e15) std::snprintf(b, sizeof b, "%.0f", j.n);
        else std::snprintf(b, sizeof b, "%.4g", j.n);
        o += b; break;
    }
    case Json::STR: dump_str(o, j.s); break;
    case Json::ARR: o += '['; for (size_t k = 0; k < j.a.size(); k++) { if (k) o += ','; dump(j.a[k], o); } o += ']'; break;
    case Json::OBJ:
        o += '{';
        for (size_t k = 0; k < j.o.size(); k++) { if (k) o += ','; dump_str(o, j.o[k].first); o += ':'; dump(j.o[k].second, o); }
        o += '}'; break;
    }
}
}  // namespace

Json Json::parse(const std::string &text, std::string *err) {
    P p(text);
    Json j;
    if (!p.value(j, 0)) { if (err) *err = p.err; return Json(); }
    p.ws();
    if (p.i != text.size()) { if (err) *err = "값 뒤에 남는 글자"; return Json(); }
    if (err) err->clear();
    return j;
}

std::string Json::dump() const { std::string o; ::dump(*this, o); return o; }

const Json &Json::operator[](const std::string &k) const {
    static const Json nil;
    if (t != OBJ) return nil;
    for (auto &kv : o) if (kv.first == k) return kv.second;
    return nil;
}

Json *Json::find(const std::string &k) {
    if (t != OBJ) return nullptr;
    for (auto &kv : o) if (kv.first == k) return &kv.second;
    return nullptr;
}

void Json::set(const std::string &k, const Json &v) {
    if (t != OBJ) { *this = obj_(); }
    if (Json *x = find(k)) *x = v; else o.push_back({k, v});
}

const Json &Json::path(const std::string &dotted) const {
    static const Json nil;
    const Json *cur = this;
    size_t st = 0;
    while (st <= dotted.size()) {
        const size_t e = dotted.find('.', st);
        const std::string k = dotted.substr(st, e == std::string::npos ? std::string::npos : e - st);
        cur = &(*cur)[k];
        if (cur->is_null()) return nil;
        if (e == std::string::npos) break;
        st = e + 1;
    }
    return *cur;
}

void Json::merge(const Json &other) {
    if (other.t != OBJ) { *this = other; return; }
    if (t != OBJ) *this = obj_();
    for (auto &kv : other.o) {
        if (kv.second.is_null()) {                             // null = 그 칸 지우기
            for (size_t k = 0; k < o.size(); k++) if (o[k].first == kv.first) { o.erase(o.begin() + k); break; }
            continue;
        }
        Json *x = find(kv.first);
        if (x && x->is_obj() && kv.second.is_obj()) x->merge(kv.second);
        else if (x) *x = kv.second;
        else o.push_back(kv);
    }
}
