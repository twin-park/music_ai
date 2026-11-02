#include "model.h"
#include <cmath>
#include <cstdio>
#include <cstring>
#include <cstdint>
#include <algorithm>

// ---------- 행렬 × 벡터: out[r] = Σ W[r][c] x[c] ----------
// 8칸 나눠 더하기 → 컴파일러가 SIMD 로 바꿈. x86 은 AVX2 판을 따로 만들어 실행 중에 고름.
#define MATVEC_BODY                                                         \
    for (int r = 0; r < rows; r++) {                                        \
        const float *w = W + (size_t)r * cols;                              \
        float a[8] = {0, 0, 0, 0, 0, 0, 0, 0};                              \
        int c = 0;                                                          \
        for (; c + 8 <= cols; c += 8)                                       \
            for (int k = 0; k < 8; k++) a[k] += w[c + k] * x[c + k];        \
        float s = ((a[0] + a[1]) + (a[2] + a[3])) + ((a[4] + a[5]) + (a[6] + a[7])); \
        for (; c < cols; c++) s += w[c] * x[c];                             \
        out[r] = s;                                                         \
    }

static void matvec_base(const float *W, const float *x, float *out, int rows, int cols) { MATVEC_BODY }
#if defined(__x86_64__) || defined(_M_X64)
#include <cpuid.h>
__attribute__((target("avx2,fma"))) static void matvec_avx2(const float *W, const float *x, float *out, int rows, int cols) { MATVEC_BODY }
static bool has_avx2_fma() {                       // cpuid 로 직접 (윈도우 교차 빌드엔 __builtin_cpu_supports 가 없음)
    unsigned a, b, c, d;
    if (!__get_cpuid(1, &a, &b, &c, &d)) return false;
    const bool fma = c & (1u << 12), osx = c & (1u << 27), avx = c & (1u << 28);
    if (!(fma && osx && avx)) return false;
    unsigned lo, hi;
    __asm__ volatile("xgetbv" : "=a"(lo), "=d"(hi) : "c"(0));
    if ((lo & 6) != 6) return false;
    if (!__get_cpuid_count(7, 0, &a, &b, &c, &d)) return false;
    return b & (1u << 5);
}
static void (*matvec_fn)(const float *, const float *, float *, int, int) = has_avx2_fma() ? matvec_avx2 : matvec_base;
#else
static void (*matvec_fn)(const float *, const float *, float *, int, int) = matvec_base;
#endif

static inline void matvec(const std::vector<float> &W, const float *x, float *out, int rows, int cols) {
    matvec_fn(W.data(), x, out, rows, cols);
}

static void rms(const float *x, const float *w, float *out, int d) {
    const float eps = 1.1920928955078125e-07f;     // float32 eps (nn.RMSNorm 기본)
    double ss = 0;
    for (int i = 0; i < d; i++) ss += (double)x[i] * x[i];
    float inv = 1.0f / std::sqrt((float)(ss / d) + eps);
    for (int i = 0; i < d; i++) out[i] = x[i] * inv * w[i];
}

// ---------- 읽기 ----------
bool Model::load(const std::string &path, std::string *err) {
    FILE *fp = std::fopen(path.c_str(), "rb");
    if (!fp) { if (err) *err = "못 엶: " + path; return false; }
    char mg[4]; int32_t h[8];
    if (std::fread(mg, 1, 4, fp) != 4 || std::memcmp(mg, "CBGM", 4) || std::fread(h, 4, 8, fp) != 8) {
        std::fclose(fp); if (err) *err = "형식이 아님: " + path; return false;
    }
    vocab = h[1]; d = h[2]; layers = h[3]; heads = h[4]; ctx = h[5]; f = h[6];
    const int quant = h[7];
    hd = d / heads;
    bool ok = true;
    auto vec = [&](std::vector<float> &v, size_t n) {
        v.resize(n);
        ok = ok && std::fread(v.data(), 4, n, fp) == n;
    };
    auto mat = [&](std::vector<float> &v, int rows, int cols) {
        v.resize((size_t)rows * cols);
        if (!quant) { ok = ok && std::fread(v.data(), 4, v.size(), fp) == v.size(); return; }
        std::vector<int8_t> q(v.size()); std::vector<float> s(rows);
        ok = ok && std::fread(q.data(), 1, q.size(), fp) == q.size() && std::fread(s.data(), 4, rows, fp) == (size_t)rows;
        for (int r = 0; r < rows; r++)
            for (int c = 0; c < cols; c++) v[(size_t)r * cols + c] = q[(size_t)r * cols + c] * s[r];
    };
    mat(emb, vocab, d); vec(norm, d);
    L.resize(layers);
    for (auto &l : L) {
        vec(l.n1, d); mat(l.qkv, 3 * d, d); mat(l.o, d, d);
        vec(l.n2, d); mat(l.w12, 2 * f, d); mat(l.w3, d, f);
    }
    std::fclose(fp);
    if (!ok) { if (err) *err = "덜 읽힘: " + path; return false; }
    const int half = hd / 2;
    cosT.resize((size_t)ctx * 2 * half); sinT.resize(cosT.size());
    for (int t = 0; t < ctx * 2; t++)
        for (int i = 0; i < half; i++) {
            float inv = 1.0f / std::pow(10000.0f, (float)(2 * i) / hd);
            float a = (float)t * inv;
            cosT[(size_t)t * half + i] = std::cos(a); sinT[(size_t)t * half + i] = std::sin(a);
        }
    return true;
}

Model::Cache Model::new_cache() const {
    Cache c;
    c.k.assign((size_t)layers * heads * ctx * hd, 0.f);
    c.v.assign(c.k.size(), 0.f);
    return c;
}

void Model::step(const int *ids, int T, Cache &C, int pos, float *logits) const {
    const int half = hd / 2, S = pos + T;
    std::vector<float> x((size_t)T * d), h(d), qkv((size_t)T * 3 * d), a((size_t)T * d), tmp(d), u(2 * f), g(f), sc(S);
    for (int t = 0; t < T; t++) std::memcpy(&x[(size_t)t * d], &emb[(size_t)ids[t] * d], d * 4);
    const float scale = 1.0f / std::sqrt((float)hd);
    for (int li = 0; li < layers; li++) {
        const Layer &l = L[li];
        float *K = &C.k[(size_t)li * heads * ctx * hd], *V = &C.v[(size_t)li * heads * ctx * hd];
        for (int t = 0; t < T; t++) {
            rms(&x[(size_t)t * d], l.n1.data(), h.data(), d);
            matvec(l.qkv, h.data(), &qkv[(size_t)t * 3 * d], 3 * d, d);
            float *q = &qkv[(size_t)t * 3 * d], *k = q + d, *v = q + 2 * d;
            const float *cs = &cosT[(size_t)(pos + t) * half], *sn = &sinT[(size_t)(pos + t) * half];
            for (int hh = 0; hh < heads; hh++)
                for (int i = 0; i < half; i++) {
                    float *qq = q + hh * hd, *kk = k + hh * hd;
                    float q1 = qq[2 * i], q2 = qq[2 * i + 1], k1 = kk[2 * i], k2 = kk[2 * i + 1];
                    qq[2 * i] = q1 * cs[i] - q2 * sn[i]; qq[2 * i + 1] = q1 * sn[i] + q2 * cs[i];
                    kk[2 * i] = k1 * cs[i] - k2 * sn[i]; kk[2 * i + 1] = k1 * sn[i] + k2 * cs[i];
                }
            for (int hh = 0; hh < heads; hh++) {
                std::memcpy(&K[((size_t)hh * ctx + pos + t) * hd], k + hh * hd, hd * 4);
                std::memcpy(&V[((size_t)hh * ctx + pos + t) * hd], v + hh * hd, hd * 4);
            }
        }
        for (int t = 0; t < T; t++) {                      // 오른쪽 아래 기준 인과 마스크: 낱말 t 는 pos+t 까지 봄
            const int n = pos + t + 1;
            for (int hh = 0; hh < heads; hh++) {
                const float *q = &qkv[(size_t)t * 3 * d + hh * hd];
                float mx = -1e30f;
                for (int j = 0; j < n; j++) {
                    const float *kk = &K[((size_t)hh * ctx + j) * hd];
                    float s = 0;
                    for (int i = 0; i < hd; i++) s += q[i] * kk[i];
                    sc[j] = s * scale; mx = std::max(mx, sc[j]);
                }
                double sum = 0;
                for (int j = 0; j < n; j++) { sc[j] = std::exp(sc[j] - mx); sum += sc[j]; }
                float *o = &a[(size_t)t * d + hh * hd];
                std::fill(o, o + hd, 0.f);
                for (int j = 0; j < n; j++) {
                    const float w = (float)(sc[j] / sum), *vv = &V[((size_t)hh * ctx + j) * hd];
                    for (int i = 0; i < hd; i++) o[i] += w * vv[i];
                }
            }
        }
        for (int t = 0; t < T; t++) {
            float *xt = &x[(size_t)t * d];
            matvec(l.o, &a[(size_t)t * d], tmp.data(), d, d);
            for (int i = 0; i < d; i++) xt[i] += tmp[i];
            rms(xt, l.n2.data(), h.data(), d);
            matvec(l.w12, h.data(), u.data(), 2 * f, d);
            for (int i = 0; i < f; i++) { float z = u[i]; g[i] = z / (1.0f + std::exp(-z)) * u[f + i]; }
            matvec(l.w3, g.data(), tmp.data(), d, f);
            for (int i = 0; i < d; i++) xt[i] += tmp[i];
        }
    }
    rms(&x[(size_t)(T - 1) * d], norm.data(), h.data(), d);
    matvec(emb, h.data(), logits, vocab, d);
}

// ---------- Runner ----------
void Runner::feed(const std::vector<int> &ids) {
    if (ids.empty()) return;
    m->step(ids.data(), (int)ids.size(), cache, (int)toks.size(), logits.data());
    toks.insert(toks.end(), ids.begin(), ids.end());
}

void Runner::room(int need, int head_len, int bar_id) {
    if ((int)toks.size() + need < m->ctx - 2) return;
    std::vector<int> keep(toks.begin(), toks.begin() + head_len), bars;
    for (int i = head_len; i < (int)toks.size(); i++)
        if (toks[i] == bar_id) bars.push_back(i);
    int cut = bars.empty() ? head_len : bars.back();
    for (int b : bars)
        if ((int)toks.size() - b < m->ctx / 2) { cut = b; break; }
    keep.insert(keep.end(), toks.begin() + cut, toks.end());
    reset();
    feed(keep);
}
