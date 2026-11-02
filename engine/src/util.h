// 파일 도우미 — 윈도우에서도 한글 경로(UTF-8)로
#pragma once
#include <string>
#include <vector>

bool read_file(const std::string &path, std::string &out);
bool write_file(const std::string &path, const std::string &data, bool append = false);
std::vector<std::string> list_dir(const std::string &dir);      // 파일 이름만
bool make_dirs(const std::string &dir);
std::string home_dir();
std::string exe_dir();
