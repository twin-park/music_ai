#include "amb.h"
#include "dsp.h"
#include "util.h"
#include <algorithm>
#include <cmath>
#include "../third_party/dr_flac.h"                     // (구현은 piano.cpp 에서 한 번)

const char *Ambience::NAME[N] = {"sea", "rain"};
// 기본 크기 (녹음은 RMS -20dBFS 로 맞춰 둠) — 음악(마스터 뒤 약 -17dB)보다 15dB 안팎 작게
static const float BASE[Ambience::N] = {.26f, .22f};

bool Ambience::set(int k, float v, std::string *err) {
    if (k < 0 || k >= N) return false;
    v = std::max(0.f, std::min(2.f, v));
    if (v > 0 && !loop_[k].load()) {
        std::lock_guard<std::mutex> g(load_mtx);
        if (!loop_[k].load()) {
            std::string data;
            const std::string path = dir + "/" + NAME[k] + ".flac";
            if (!read_file(path, data)) { if (err) *err = "주변 소리 파일이 없음: " + path; return false; }
            unsigned ch = 0, sr = 0; drflac_uint64 n = 0;
            drflac_int16 *pcm = drflac_open_memory_and_read_pcm_frames_s16(data.data(), data.size(), &ch, &sr, &n, nullptr);
            if (!pcm || n < (drflac_uint64)SR) { if (pcm) drflac_free(pcm, nullptr); if (err) *err = "주변 소리를 못 읽음: " + path; return false; }
            auto L = std::make_unique<Loop>();
            L->frames = (long)n;
            L->x.resize((size_t)n * 2);
            for (drflac_uint64 i = 0; i < n; i++) {
                L->x[i * 2] = pcm[i * ch];
                L->x[i * 2 + 1] = pcm[i * ch + (ch > 1 ? 1 : 0)];
            }
            drflac_free(pcm, nullptr);
            own_[k] = std::move(L);
            loop_[k].store(own_[k].get());                // 다 읽은 뒤에 소리 줄에 넘김
        }
    }
    level[k] = v;
    return true;
}

void Ambience::render(float *L, float *R, int n, float gain) {
    const float a = 1.f / (2.5f * SR);                    // 켜고 끌 때 몇 초에 걸쳐
    const bool on = run.load();
    for (int k = 0; k < N; k++) {
        const Loop *lp = loop_[k].load();
        const float tgt = on && lp ? BASE[k] * level[k].load() : 0.f;
        if (!lp || (g_[k] < 1e-5f && tgt == 0)) { g_[k] = 0; continue; }
        long p = pos_[k];
        float g = g_[k];
        const int16_t *x = lp->x.data();
        for (int i = 0; i < n; i++) {
            g += (tgt - g) * a;
            const float s = g * gain / 32768.f;
            L[i] += x[p * 2] * s; R[i] += x[p * 2 + 1] * s;
            if (++p >= lp->frames) p = 0;
        }
        pos_[k] = p; g_[k] = g;
    }
}

size_t Ambience::loaded_bytes() const {
    size_t b = 0;
    for (int k = 0; k < N; k++) if (const Loop *lp = loop_[k].load()) b += lp->x.size() * 2;
    return b;
}
