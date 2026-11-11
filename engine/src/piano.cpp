#include "piano.h"
#include "dsp.h"
#include "util.h"
#include <algorithm>
#include <cmath>
#define DR_FLAC_IMPLEMENTATION
#include "../third_party/dr_flac.h"

static const int LAYER_V[4] = {40, 70, 96, 120};          // 층 04 08 12 15
static const char *LAYER_N[4] = {"04", "08", "12", "15"};

bool Piano::open(const std::string &d) {
    dir = d;
    for (auto &f : list_dir(d)) {
        // 021_A0v04.flac
        if (f.size() < 12 || f.substr(f.size() - 5) != ".flac") continue;
        int note = std::atoi(f.substr(0, 3).c_str());
        size_t v = f.rfind('v');
        if (v == std::string::npos) continue;
        std::string ln = f.substr(v + 1, 2);
        for (int k = 0; k < 4; k++)
            if (ln == LAYER_N[k]) files[{note, k}] = d + "/" + f;
    }
    for (auto &kv : files) if (notes.empty() || notes.back() != kv.first.first) notes.push_back(kv.first.first);
    std::sort(notes.begin(), notes.end());
    notes.erase(std::unique(notes.begin(), notes.end()), notes.end());
    voices.resize(160);
    return !notes.empty();
}

const PianoSample *Piano::get(int note, int layer) {
    const auto key = std::make_pair(note, layer);
    {
        std::lock_guard<std::mutex> g(mtx);
        auto it = cache.find(key);
        if (it != cache.end()) return it->second.get();
    }
    auto s = std::make_unique<PianoSample>();                 // 파일 풀기는 자물쇠 밖에서 (그동안 소리 내는 줄이 안 기다리게)
    auto f = files.find(key);
    std::string data;
    if (f != files.end() && read_file(f->second, data)) {
        unsigned ch = 0, sr = 0; drflac_uint64 n = 0;
        drflac_int16 *pcm = drflac_open_memory_and_read_pcm_frames_s16(data.data(), data.size(), &ch, &sr, &n, nullptr);
        if (pcm) {
            s->frames = (long)n;
            s->x.resize((size_t)n * 2);
            for (drflac_uint64 i = 0; i < n; i++) {
                s->x[i * 2] = pcm[i * ch];
                s->x[i * 2 + 1] = pcm[i * ch + (ch > 1 ? 1 : 0)];
            }
            drflac_free(pcm, nullptr);
            s->srr = (double)sr / SR;                         // Accurate-Salamander 는 조율 보정을 샘플레이트로 담아 둠
        }
    }
    std::lock_guard<std::mutex> g(mtx);
    auto &slot = cache[key];
    if (!slot) slot = std::move(s);                           // (그 사이 다른 줄이 먼저 넣었으면 그걸 씀)
    return slot.get();
}

void Piano::preload() {
    for (auto &kv : files) get(kv.first.first, kv.first.second);
}

void Piano::preload_common() {
    if (bg.joinable()) return;
    bg = std::thread([this] {                                 // 가운데 도(60) 에서 가까운 음부터, 세기 층 0~2
        std::vector<int> order = notes;
        std::sort(order.begin(), order.end(), [](int a, int b) { return std::abs(a - 62) < std::abs(b - 62); });
        for (int n : order) {
            if (n < 36 || n > 90) continue;
            for (int k = 0; k < 3 && !bg_stop; k++) get(n, k);
        }
    });
}

void Piano::pick(int p, int v, int &n, int &la, int &lb, double &f) const {
    n = notes[0];
    for (int q : notes) if (std::abs(q - p) < std::abs(n - p)) n = q;
    la = lb = -1; f = 0;
    for (int k = 0; k + 1 < 4; k++)
        if (LAYER_V[k] <= v && v <= LAYER_V[k + 1]) { la = k; lb = k + 1; f = (double)(v - LAYER_V[k]) / (LAYER_V[k + 1] - LAYER_V[k]); break; }
}

void Piano::warm(int p, int v) {
    int n, la, lb; double f;
    pick(p, v, n, la, lb, f);
    if (la < 0) get(n, v < LAYER_V[0] ? 0 : 3);
    else { get(n, la); get(n, lb); }
}

size_t Piano::loaded_bytes() {
    std::lock_guard<std::mutex> g(mtx);
    size_t b = 0;
    for (auto &kv : cache) b += kv.second->x.size() * 2;
    return b;
}

void Piano::note(int p, int v, double dur, int start) { pend.push_back({p, v, dur, start}); }

void Piano::release_all(int at) {
    for (auto &vo : voices)
        if (vo.on) {
            long k = vo.t + at;
            if (k < vo.k1) { vo.k1 = k; vo.nout = std::min(vo.nout, k + (long)(vo.rel * 4 * SR)); }
        }
    for (auto &pd : pend) pd.dur = std::min(pd.dur, std::max(0.0, (at - pd.start) / (double)SR));
}

void Piano::cap_all(int at, long n) {
    for (auto &vo : voices)
        if (vo.on) {
            long k = vo.t + at + n;
            if (k < vo.k1) { vo.k1 = k; vo.nout = std::min(vo.nout, k + (long)(vo.rel * 4 * SR)); }
        }
    for (auto &pd : pend) if (pd.start < at) pd.dur = std::min(pd.dur, std::max(0.0, (at + n - pd.start) / (double)SR));
}

static void start_voice(Piano &pn, Piano::Voice &vo, int p, int v, double dur) {
    int n, la, lb; double f;
    pn.pick(p, v, n, la, lb, f);
    const double ratio = std::pow(2.0, (p - n) / 12.0);
    vo = Piano::Voice();
    if (la < 0) {
        if (v < LAYER_V[0]) { vo.s[0] = pn.get(n, 0); vo.w[0] = (float)v / LAYER_V[0]; }
        else { vo.s[0] = pn.get(n, 3); vo.w[0] = 1; }
    } else {
        vo.s[0] = pn.get(n, la); vo.w[0] = (float)(1 - f);
        vo.s[1] = pn.get(n, lb); vo.w[1] = (float)f;
    }
    for (int k = 0; k < 2; k++) if (vo.s[k]) vo.inc[k] = ratio * vo.s[k]->srr;
    vo.rel = .25 + std::max(0, 60 - p) * .012;                                        // 낮은 음일수록 길게 울림
    vo.k1 = (long)(dur * SR);
    vo.nout = (long)((std::max(.05, dur) + vo.rel * 4) * SR);
    vo.on = true;
}

void Piano::render(float *L, float *R, int n) {
    std::sort(pend.begin(), pend.end(), [](const Pending &a, const Pending &b) { return a.start < b.start; });
    size_t pi = 0;
    // 블록을 시작 자리마다 나눠 소리를 켬
    int pos = 0;
    while (pos < n) {
        int end = n;
        while (pi < pend.size() && pend[pi].start <= pos) {
            Voice *slot = nullptr;
            for (auto &vo : voices) if (!vo.on) { slot = &vo; break; }
            if (!slot) {                                                              // 가장 오래된 소리 자리를 씀
                slot = &voices[0];
                for (auto &vo : voices) if (vo.t > slot->t) slot = &vo;
            }
            start_voice(*this, *slot, pend[pi].p, pend[pi].v, pend[pi].dur);
            pi++;
        }
        if (pi < pend.size()) end = std::min(n, pend[pi].start);
        for (auto &vo : voices) {
            if (!vo.on) continue;
            for (int j = pos; j < end; j++) {
                if (vo.t >= vo.nout) { vo.on = false; break; }
                double env = vo.t < vo.k1 ? 1.0 : std::exp(-(double)(vo.t - vo.k1) / (vo.rel * SR));
                float l = 0, r = 0;
                for (int k = 0; k < 2; k++) {
                    const PianoSample *s = vo.s[k];
                    if (!s || !vo.w[k]) continue;
                    long ip = (long)vo.pos[k];
                    if (ip + 1 < s->frames) {
                        float fr = (float)(vo.pos[k] - ip), w = vo.w[k] * (float)env / 32768.f;
                        l += w * (s->x[ip * 2] * (1 - fr) + s->x[ip * 2 + 2] * fr);
                        r += w * (s->x[ip * 2 + 1] * (1 - fr) + s->x[ip * 2 + 3] * fr);
                    }
                    vo.pos[k] += vo.inc[k];
                }
                L[j] += l; R[j] += r;
                vo.t++;
            }
        }
        pos = end;
    }
    pend.clear();
}
