#include "http.h"
#include <cstring>
#include <thread>
#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
typedef int socklen_t;
static void closes(long long s) { closesocket((SOCKET)s); }
#else
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>
static void closes(long long s) { close((int)s); }
#endif

bool HttpServer::listen_on(int start) {
#ifdef _WIN32
    WSADATA w;
    WSAStartup(MAKEWORD(2, 2), &w);
#endif
    for (int p = start; p < start + 50; p++) {
        long long s = (long long)socket(AF_INET, SOCK_STREAM, 0);
        if (s < 0) return false;
        sockaddr_in a{};
        a.sin_family = AF_INET;
        a.sin_port = htons((unsigned short)p);
        a.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
        if (bind((int)s, (sockaddr *)&a, sizeof a) == 0 && listen((int)s, 16) == 0) { sock = s; port = p; return true; }
        closes(s);
    }
    return false;
}

static bool recv_all(long long c, HttpReq &r) {
    std::string buf;
    char tmp[8192];
    size_t hdr_end = std::string::npos;
    while (hdr_end == std::string::npos) {
        int n = recv((int)c, tmp, sizeof tmp, 0);
        if (n <= 0) return false;
        buf.append(tmp, n);
        hdr_end = buf.find("\r\n\r\n");
        if (buf.size() > 1 << 20) return false;
    }
    std::string head = buf.substr(0, hdr_end);
    size_t sp1 = head.find(' '), sp2 = head.find(' ', sp1 + 1);
    if (sp1 == std::string::npos || sp2 == std::string::npos) return false;
    r.method = head.substr(0, sp1);
    std::string url = head.substr(sp1 + 1, sp2 - sp1 - 1);
    size_t q = url.find('?');
    r.path = url.substr(0, q);
    r.query = q == std::string::npos ? "" : url.substr(q + 1);
    size_t len = 0;
    for (size_t p = 0; (p = head.find('\n', p)) != std::string::npos; p++) {
        std::string ln = head.substr(p + 1, head.find('\n', p + 1) - p - 1);
        if (ln.size() > 15 && (ln.compare(0, 15, "Content-Length:") == 0 || ln.compare(0, 15, "content-length:") == 0)) len = std::stoul(ln.substr(15));
    }
    r.body = buf.substr(hdr_end + 4);
    while (r.body.size() < len) {
        int n = recv((int)c, tmp, sizeof tmp, 0);
        if (n <= 0) break;
        r.body.append(tmp, n);
    }
    return true;
}

void HttpServer::serve(const std::function<void(const HttpReq &, HttpRes &)> &h) {
    while (true) {
        sockaddr_in a{};
        socklen_t l = sizeof a;
        long long c = (long long)accept((int)sock, (sockaddr *)&a, &l);
        if (c < 0) continue;
        std::thread([c, h] {
            HttpReq r;
            if (recv_all(c, r)) {
                HttpRes res;
                h(r, res);
                const char *st = res.code == 200 ? "OK" : res.code == 404 ? "Not Found" : "Error";
                std::string out = "HTTP/1.1 " + std::to_string(res.code) + " " + st + "\r\nContent-Type: " + res.type +
                                  "\r\nContent-Length: " + std::to_string(res.body.size()) + "\r\nCache-Control: no-store\r\nConnection: close\r\n\r\n" + res.body;
                size_t off = 0;
                while (off < out.size()) {
                    int n = send((int)c, out.data() + off, (int)(out.size() - off), 0);
                    if (n <= 0) break;
                    off += n;
                }
            }
            closes(c);
        }).detach();
    }
}

std::string json_str(const std::string &s) {
    std::string o = "\"";
    for (unsigned char ch : s) {
        if (ch == '"') o += "\\\"";
        else if (ch == '\\') o += "\\\\";
        else if (ch == '\n') o += "\\n";
        else if (ch == '\r') {}
        else if (ch == '\t') o += "\\t";
        else if (ch < 0x20) {}
        else o += (char)ch;
    }
    return o + "\"";
}

std::string json_get(const std::string &b, const std::string &key) {
    size_t k = b.find("\"" + key + "\"");
    if (k == std::string::npos) return "";
    size_t c = b.find(':', k);
    if (c == std::string::npos) return "";
    size_t i = b.find_first_not_of(" \t\r\n", c + 1);
    if (i == std::string::npos) return "";
    if (b[i] == '"') {
        std::string o;
        for (size_t j = i + 1; j < b.size() && b[j] != '"'; j++) {
            if (b[j] == '\\' && j + 1 < b.size()) { j++; o += b[j] == 'n' ? '\n' : b[j]; }
            else o += b[j];
        }
        return o;
    }
    size_t e = b.find_first_of(",}", i);
    return b.substr(i, e - i);
}
