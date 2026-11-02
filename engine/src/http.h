// 아주 작은 HTTP 서버 (127.0.0.1 만) — 브라우저 화면이 리모컨
#pragma once
#include <functional>
#include <string>

struct HttpReq { std::string method, path, query, body; };
struct HttpRes { int code = 200; std::string type = "application/json; charset=utf-8", body; };

struct HttpServer {
    int port = 0;
    long long sock = -1;
    bool listen_on(int start_port);                               // 빈 포트 찾기
    void serve(const std::function<void(const HttpReq &, HttpRes &)> &h);   // 막고 돎
};

std::string json_str(const std::string &s);                       // "…" (이스케이프)
std::string json_get(const std::string &body, const std::string &key);   // {"key": "값" | 숫자}
