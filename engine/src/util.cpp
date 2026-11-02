#include "util.h"
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#ifdef _WIN32
#include <windows.h>
#else
#include <unistd.h>
#endif

namespace fs = std::filesystem;

static fs::path P(const std::string &s) {
#ifdef _WIN32
    int n = MultiByteToWideChar(CP_UTF8, 0, s.c_str(), -1, nullptr, 0);
    std::wstring w(n ? n - 1 : 0, 0);
    if (n > 1) MultiByteToWideChar(CP_UTF8, 0, s.c_str(), -1, &w[0], n);
    return fs::path(w);
#else
    return fs::path(s);
#endif
}

static std::string U8(const fs::path &p) {
#ifdef _WIN32
    std::wstring w = p.wstring();
    int n = WideCharToMultiByte(CP_UTF8, 0, w.c_str(), -1, nullptr, 0, nullptr, nullptr);
    std::string s(n ? n - 1 : 0, 0);
    if (n > 1) WideCharToMultiByte(CP_UTF8, 0, w.c_str(), -1, &s[0], n, nullptr, nullptr);
    return s;
#else
    return p.string();
#endif
}

static FILE *open_u8(const std::string &path, const char *mode) {
#ifdef _WIN32
    std::wstring wm(mode, mode + std::char_traits<char>::length(mode));
    return _wfopen(P(path).c_str(), wm.c_str());
#else
    return std::fopen(path.c_str(), mode);
#endif
}

bool read_file(const std::string &path, std::string &out) {
    FILE *f = open_u8(path, "rb");
    if (!f) return false;
    std::fseek(f, 0, SEEK_END);
    long n = std::ftell(f);
    std::fseek(f, 0, SEEK_SET);
    out.resize(n > 0 ? n : 0);
    size_t got = n > 0 ? std::fread(&out[0], 1, n, f) : 0;
    std::fclose(f);
    return (long)got == n;
}

bool write_file(const std::string &path, const std::string &data, bool append) {
    FILE *f = open_u8(path, append ? "ab" : "wb");
    if (!f) return false;
    size_t w = std::fwrite(data.data(), 1, data.size(), f);
    std::fclose(f);
    return w == data.size();
}

std::vector<std::string> list_dir(const std::string &dir) {
    std::vector<std::string> v;
    std::error_code ec;
    for (auto &e : fs::directory_iterator(P(dir), ec)) v.push_back(U8(e.path().filename()));
    return v;
}

bool make_dirs(const std::string &dir) {
    std::error_code ec;
    fs::create_directories(P(dir), ec);
    return fs::is_directory(P(dir), ec);
}

std::string home_dir() {
#ifdef _WIN32
    wchar_t *w = _wgetenv(L"USERPROFILE");
    return w ? U8(fs::path(w)) : std::string("C:\\");
#else
    const char *h = std::getenv("HOME");
    return h ? h : "/tmp";
#endif
}

std::string exe_dir() {
#ifdef _WIN32
    wchar_t b[4096];
    DWORD n = GetModuleFileNameW(nullptr, b, 4096);
    return U8(fs::path(std::wstring(b, n)).parent_path());
#else
    char b[4096];
    ssize_t n = readlink("/proc/self/exe", b, sizeof b - 1);
    return n > 0 ? U8(fs::path(std::string(b, n)).parent_path()) : ".";
#endif
}
