// FluidSynth 를 실행 중에 불러 씀 (윈도우 libfluidsynth-3.dll · 리눅스 libfluidsynth.so.3) — 링크 없이 함수 주소만
#pragma once
#include <string>

struct Fluid {
    typedef void settings_t;
    typedef void synth_t;
    settings_t *(*new_settings)();
    void (*delete_settings)(settings_t *);
    int (*setnum)(settings_t *, const char *, double);
    int (*setint)(settings_t *, const char *, int);
    synth_t *(*new_synth)(settings_t *);
    void (*delete_synth)(synth_t *);
    int (*sfload)(synth_t *, const char *, int);
    int (*noteon)(synth_t *, int, int, int);
    int (*noteoff)(synth_t *, int, int);
    int (*cc)(synth_t *, int, int, int);
    int (*pitch_bend)(synth_t *, int, int);
    int (*program_change)(synth_t *, int, int);
    int (*bank_select)(synth_t *, int, int);
    int (*write_float)(synth_t *, int, void *, int, int, void *, int, int);
    int (*all_notes_off)(synth_t *, int);
    int (*all_sounds_off)(synth_t *, int);
    void *(*set_log_function)(int, void *, void *);
    bool ok = false;
    std::string err;
    bool load(const std::string &path);
};
extern Fluid FL;
