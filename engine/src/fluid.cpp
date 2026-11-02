#include "fluid.h"
#ifdef _WIN32
#include <windows.h>
#else
#include <dlfcn.h>
#endif

Fluid FL;

bool Fluid::load(const std::string &path) {
#ifdef _WIN32
    int n = MultiByteToWideChar(CP_UTF8, 0, path.c_str(), -1, nullptr, 0);
    std::wstring w(n, 0);
    MultiByteToWideChar(CP_UTF8, 0, path.c_str(), -1, &w[0], n);
    HMODULE h = LoadLibraryExW(w.c_str(), nullptr, LOAD_WITH_ALTERED_SEARCH_PATH);
    if (!h) { err = "fluidsynth 를 못 불러옴: " + path + " (오류 " + std::to_string(GetLastError()) + ")"; return false; }
    auto sym = [&](const char *s) { return (void *)GetProcAddress(h, s); };
#else
    void *h = dlopen(path.c_str(), RTLD_NOW | RTLD_LOCAL);
    if (!h) { const char *e = dlerror(); err = "fluidsynth 를 못 불러옴: " + path + " (" + (e ? e : "?") + ")"; return false; }
    auto sym = [&](const char *s) { return dlsym(h, s); };
#endif
    bool all = true;
    auto get = [&](auto &fp, const char *s) { void *p = sym(s); all = all && p; fp = reinterpret_cast<std::remove_reference_t<decltype(fp)>>(p); if (!p) err += std::string(" ") + s; };
    get(new_settings, "new_fluid_settings"); get(delete_settings, "delete_fluid_settings");
    get(setnum, "fluid_settings_setnum"); get(setint, "fluid_settings_setint");
    get(new_synth, "new_fluid_synth"); get(delete_synth, "delete_fluid_synth"); get(sfload, "fluid_synth_sfload");
    get(noteon, "fluid_synth_noteon"); get(noteoff, "fluid_synth_noteoff"); get(cc, "fluid_synth_cc");
    get(pitch_bend, "fluid_synth_pitch_bend"); get(program_change, "fluid_synth_program_change"); get(bank_select, "fluid_synth_bank_select");
    get(write_float, "fluid_synth_write_float"); get(all_notes_off, "fluid_synth_all_notes_off"); get(all_sounds_off, "fluid_synth_all_sounds_off");
    get(set_log_function, "fluid_set_log_function");
    if (!all) { err = "fluidsynth 함수가 없음:" + err; return false; }
    for (int lv = 0; lv < 5; lv++) set_log_function(lv, nullptr, nullptr);       // 경고 글 안 찍기
    ok = true;
    return true;
}
