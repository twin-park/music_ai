#include "model.h"
#include <cmath>
#include <cstdio>
#include <cstring>
#include <algorithm>

// ---------- 빠른 exp (softmax · SiLU 용, 상대 오차 2e-5 안쪽) ----------
static inline __attribute__((always_inline)) float fexp(float x) {
    x = x < -80.f ? -80.f : (x > 80.f ? 80.f : x);
    const float t = x * 1.44269504f;
    const int e = (int)(t + 1000.f) - 1000;                   // 내림
    const float f = t - (float)e;                             // 0 … 1
    const float p = 1.f + f * (0.693147181f + f * (0.240226507f + f * (0.0555041087f + f * (0.00961812911f + f * (0.00133335581f + f * 0.000154035304f)))));
    uint32_t u = (uint32_t)(e + 127) << 23;
    float s;
    std::memcpy(&s, &u, 4);
    return p * s;
}

// ---------- 행렬 × 벡터 (int8 가중치 × 13비트 활성값 → int32 합): out[r] = s[r] · xs · Σ q[r][c] · x[c] ----------
// 정수 합이라 컴파일러가 그대로 SIMD(pmaddwd · smlal)로 바꿈. x86 은 AVX2 판을 따로 만들어 실행 중에 고름.
static inline __attribute__((always_inline)) void k_matvec(const int8_t *W, const int16_t *x, const float *s, float xs, float *out, int rows, int cols) {
    for (int r = 0; r < rows; r++) {
        const int8_t *w = W + (size_t)r * cols;
        int32_t acc = 0;
        for (int c = 0; c < cols; c++) acc += (int32_t)w[c] * (int32_t)x[c];
        out[r] = (float)acc * s[r] * xs;
    }
}
// 활성값 → 13비트 정수 (가장 큰 값이 4095 가 되게), 돌려주는 값 = 정수 1 의 크기
static inline __attribute__((always_inline)) float k_quant(const float *x, int16_t *q, int n) {
    float mx = 0;
    for (int i = 0; i < n; i++) { const float a = x[i] < 0 ? -x[i] : x[i]; mx = a > mx ? a : mx; }
    if (!(mx > 0)) { std::memset(q, 0, (size_t)n * 2); return 0; }
    const float k = 4095.f / mx;
    for (int i = 0; i < n; i++) { const float v = x[i] * k; q[i] = (int16_t)(int)(v + (v >= 0 ? .5f : -.5f)); }
    return mx / 4095.f;
}
// 한 낱말의 주의(attention): q(d) 가 K(n×d)·V(n×d) 를 봄 → out(d). sc 는 heads×n 칸.
static inline __attribute__((always_inline)) void k_attn(const float *q, const float *K, const float *V, int n, int d, int heads, int hd,
                                                          float scale, float *sc, float *out) {
    for (int j = 0; j < n; j++) {
        const float *kj = K + (size_t)j * d;
        for (int hh = 0; hh < heads; hh++) {
            const float *a = q + hh * hd, *b = kj + hh * hd;
            float acc[8] = {0, 0, 0, 0, 0, 0, 0, 0};
            int i = 0;
            for (; i + 8 <= hd; i += 8)
                for (int k = 0; k < 8; k++) acc[k] += a[i + k] * b[i + k];
            float s = ((acc[0] + acc[1]) + (acc[2] + acc[3])) + ((acc[4] + acc[5]) + (acc[6] + acc[7]));
            for (; i < hd; i++) s += a[i] * b[i];
            sc[(size_t)hh * n + j] = s * scale;
        }
    }
    for (int hh = 0; hh < heads; hh++) {
        float *s = sc + (size_t)hh * n;
        float mx = -1e30f;
        for (int j = 0; j < n; j++) mx = s[j] > mx ? s[j] : mx;
        float sum = 0;
        for (int j = 0; j < n; j++) { s[j] = fexp(s[j] - mx); sum += s[j]; }
        const float inv = 1.f / sum;
        for (int j = 0; j < n; j++) s[j] *= inv;
    }
    for (int i = 0; i < d; i++) out[i] = 0;
    for (int j = 0; j < n; j++) {
        const float *vj = V + (size_t)j * d;
        for (int hh = 0; hh < heads; hh++) {
            const float w = sc[(size_t)hh * n + j];
            float *o = out + hh * hd;
            const float *v = vj + hh * hd;
            for (int i = 0; i < hd; i++) o[i] += w * v[i];
        }
    }
}
static inline __attribute__((always_inline)) void k_swiglu(const float *u, float *g, int f) {
    for (int i = 0; i < f; i++) { const float z = u[i]; g[i] = z / (1.f + fexp(-z)) * u[f + i]; }
}

// 같은 계산을 SIMD 명령으로 직접 (컴파일러가 알아서 바꾼 것보다 2~3배 빠름): 16칸씩 int8→int16 넓혀 int16 곱·짝 더하기
#if defined(__aarch64__)
#include <arm_neon.h>
static void matvec_neon(const int8_t *W, const int16_t *x, const float *s, float xs, float *out, int rows, int cols) {
    const int n16 = cols & ~15;
    for (int r = 0; r < rows; r++) {
        const int8_t *w = W + (size_t)r * cols;
        int32x4_t a0 = vdupq_n_s32(0), a1 = a0, a2 = a0, a3 = a0;
        for (int c = 0; c < n16; c += 16) {
            const int8x16_t wv = vld1q_s8(w + c);
            const int16x8_t wl = vmovl_s8(vget_low_s8(wv)), wh = vmovl_high_s8(wv);
            const int16x8_t xl = vld1q_s16(x + c), xh = vld1q_s16(x + c + 8);
            a0 = vmlal_s16(a0, vget_low_s16(wl), vget_low_s16(xl));
            a1 = vmlal_high_s16(a1, wl, xl);
            a2 = vmlal_s16(a2, vget_low_s16(wh), vget_low_s16(xh));
            a3 = vmlal_high_s16(a3, wh, xh);
        }
        int32_t acc = vaddvq_s32(vaddq_s32(vaddq_s32(a0, a1), vaddq_s32(a2, a3)));
        for (int c = n16; c < cols; c++) acc += (int32_t)w[c] * (int32_t)x[c];
        out[r] = (float)acc * s[r] * xs;
    }
}
#endif
#if defined(__x86_64__) || defined(_M_X64)
#include <immintrin.h>
__attribute__((target("avx2,fma"))) static void matvec_avx2(const int8_t *W, const int16_t *x, const float *s, float xs, float *out, int rows, int cols) {
    const int n16 = cols & ~15;
    for (int r = 0; r < rows; r++) {
        const int8_t *w = W + (size_t)r * cols;
        __m256i a0 = _mm256_setzero_si256(), a1 = a0;
        int c = 0;
        for (; c + 32 <= n16; c += 32) {
            a0 = _mm256_add_epi32(a0, _mm256_madd_epi16(_mm256_cvtepi8_epi16(_mm_loadu_si128((const __m128i *)(w + c))), _mm256_loadu_si256((const __m256i *)(x + c))));
            a1 = _mm256_add_epi32(a1, _mm256_madd_epi16(_mm256_cvtepi8_epi16(_mm_loadu_si128((const __m128i *)(w + c + 16))), _mm256_loadu_si256((const __m256i *)(x + c + 16))));
        }
        for (; c < n16; c += 16)
            a0 = _mm256_add_epi32(a0, _mm256_madd_epi16(_mm256_cvtepi8_epi16(_mm_loadu_si128((const __m128i *)(w + c))), _mm256_loadu_si256((const __m256i *)(x + c))));
        a0 = _mm256_add_epi32(a0, a1);
        __m128i h = _mm_add_epi32(_mm256_castsi256_si128(a0), _mm256_extracti128_si256(a0, 1));
        h = _mm_add_epi32(h, _mm_shuffle_epi32(h, 0x4e));
        h = _mm_add_epi32(h, _mm_shuffle_epi32(h, 0xb1));
        int32_t acc = _mm_cvtsi128_si32(h);
        for (c = n16; c < cols; c++) acc += (int32_t)w[c] * (int32_t)x[c];
        out[r] = (float)acc * s[r] * xs;
    }
}
#endif

struct Kern {
    void (*matvec)(const int8_t *, const int16_t *, const float *, float, float *, int, int);
    float (*quant)(const float *, int16_t *, int);
    void (*attn)(const float *, const float *, const float *, int, int, int, int, float, float *, float *);
    void (*swiglu)(const float *, float *, int);
};
static void matvec_b(const int8_t *W, const int16_t *x, const float *s, float xs, float *out, int rows, int cols) { k_matvec(W, x, s, xs, out, rows, cols); }
static float quant_b(const float *x, int16_t *q, int n) { return k_quant(x, q, n); }
static void attn_b(const float *q, const float *K, const float *V, int n, int d, int heads, int hd, float scale, float *sc, float *out) { k_attn(q, K, V, n, d, heads, hd, scale, sc, out); }
static void swiglu_b(const float *u, float *g, int f) { k_swiglu(u, g, f); }
#if defined(__x86_64__) || defined(_M_X64)
#include <cpuid.h>
#define AVX2 __attribute__((target("avx2,fma")))
AVX2 static float quant_a(const float *x, int16_t *q, int n) { return k_quant(x, q, n); }
AVX2 static void attn_a(const float *q, const float *K, const float *V, int n, int d, int heads, int hd, float scale, float *sc, float *out) { k_attn(q, K, V, n, d, heads, hd, scale, sc, out); }
AVX2 static void swiglu_a(const float *u, float *g, int f) { k_swiglu(u, g, f); }
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
// AVX2 판이 기본 판과 똑같은 값을 내는지 켤 때 한 번 확인 (다르면 기본 판으로 — 정수 합이라 완전히 같아야 함)
static bool avx2_ok() {
    if (!has_avx2_fma()) return false;
    const int rows = 3, cols = 85;                            // 16칸 묶음 + 남는 칸이 모두 나오는 길이
    std::vector<int8_t> W((size_t)rows * cols);
    std::vector<int16_t> x(cols + 32);
    std::vector<float> s(rows, 1.f), a(rows), b(rows);
    unsigned z = 2463534242u;
    for (auto &w : W) { z ^= z << 13; z ^= z >> 17; z ^= z << 5; w = (int8_t)((int)(z % 255) - 127); }
    for (int c = 0; c < cols; c++) { z ^= z << 13; z ^= z >> 17; z ^= z << 5; x[c] = (int16_t)((int)(z % 8191) - 4095); }
    matvec_avx2(W.data(), x.data(), s.data(), 1.f, a.data(), rows, cols);
    matvec_b(W.data(), x.data(), s.data(), 1.f, b.data(), rows, cols);
    for (int r = 0; r < rows; r++) if (a[r] != b[r]) return false;
    return true;
}
static const Kern KN = avx2_ok() ? Kern{matvec_avx2, quant_a, attn_a, swiglu_a} : Kern{matvec_b, quant_b, attn_b, swiglu_b};
#elif defined(__aarch64__)
static const Kern KN = Kern{matvec_neon, quant_b, attn_b, swiglu_b};
#else
static const Kern KN = Kern{matvec_b, quant_b, attn_b, swiglu_b};
#endif

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
    auto mat = [&](Mat &m, int rows, int cols) {
        m.rows = rows; m.cols = cols;
        m.q.resize((size_t)rows * cols); m.s.resize(rows);
        if (quant) { ok = ok && std::fread(m.q.data(), 1, m.q.size(), fp) == m.q.size() && std::fread(m.s.data(), 4, rows, fp) == (size_t)rows; return; }
        std::vector<float> w((size_t)rows * cols);                           // float 파일(시험용)은 읽으면서 int8 로
        ok = ok && std::fread(w.data(), 4, w.size(), fp) == w.size();
        for (int r = 0; r < rows; r++) {
            float mx = 0;
            for (int c = 0; c < cols; c++) mx = std::max(mx, std::fabs(w[(size_t)r * cols + c]));
            const float s = mx / 127 + 1e-12f;
            m.s[r] = s;
            for (int c = 0; c < cols; c++) m.q[(size_t)r * cols + c] = (int8_t)std::lround(std::max(-127.f, std::min(127.f, w[(size_t)r * cols + c] / s)));
        }
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

size_t Model::weight_bytes() const {
    size_t n = emb.q.size() + emb.s.size() * 4 + norm.size() * 4 + (cosT.size() + sinT.size()) * 4;
    for (auto &l : L)
        for (const Mat *m : {&l.qkv, &l.o, &l.w12, &l.w3}) n += m->q.size() + m->s.size() * 4;
    return n;
}

Model::Cache Model::new_cache() const {
    Cache c;
    c.k.assign((size_t)layers * ctx * d, 0.f);
    c.v.assign(c.k.size(), 0.f);
    return c;
}

void Model::step(const int *ids, int T, Cache &C, int pos, float *logits) const {
    const int half = hd / 2, S = pos + T;
    // 계산용 칸 (줄(thread)마다 따로, 다시 잡지 않음)
    thread_local std::vector<float> x, h, qkv, a, tmp, u, g, sc;
    thread_local std::vector<int16_t> xq;
    x.resize((size_t)T * d); h.resize(d); qkv.resize((size_t)T * 3 * d); a.resize((size_t)T * d); tmp.resize(d);
    u.resize(2 * f); g.resize(f); sc.resize((size_t)heads * S); xq.resize((size_t)std::max(d, f) + 32);
    for (int t = 0; t < T; t++) {
        const int8_t *e = &emb.q[(size_t)ids[t] * d];
        const float s = emb.s[ids[t]];
        float *xt = &x[(size_t)t * d];
        for (int i = 0; i < d; i++) xt[i] = e[i] * s;
    }
    const float scale = 1.0f / std::sqrt((float)hd);
    auto mv = [&](const Mat &m, const float *in, float *out) {
        const float xs = KN.quant(in, xq.data(), m.cols);
        KN.matvec(m.q.data(), xq.data(), m.s.data(), xs, out, m.rows, m.cols);
    };
    for (int li = 0; li < layers; li++) {
        const Layer &l = L[li];
        float *K = &C.k[(size_t)li * ctx * d], *V = &C.v[(size_t)li * ctx * d];
        for (int t = 0; t < T; t++) {
            rms(&x[(size_t)t * d], l.n1.data(), h.data(), d);
            mv(l.qkv, h.data(), &qkv[(size_t)t * 3 * d]);
            float *q = &qkv[(size_t)t * 3 * d], *k = q + d, *v = q + 2 * d;
            const float *cs = &cosT[(size_t)(pos + t) * half], *sn = &sinT[(size_t)(pos + t) * half];
            for (int hh = 0; hh < heads; hh++)
                for (int i = 0; i < half; i++) {
                    float *qq = q + hh * hd, *kk = k + hh * hd;
                    float q1 = qq[2 * i], q2 = qq[2 * i + 1], k1 = kk[2 * i], k2 = kk[2 * i + 1];
                    qq[2 * i] = q1 * cs[i] - q2 * sn[i]; qq[2 * i + 1] = q1 * sn[i] + q2 * cs[i];
                    kk[2 * i] = k1 * cs[i] - k2 * sn[i]; kk[2 * i + 1] = k1 * sn[i] + k2 * cs[i];
                }
            std::memcpy(&K[(size_t)(pos + t) * d], k, (size_t)d * 4);
            std::memcpy(&V[(size_t)(pos + t) * d], v, (size_t)d * 4);
        }
        for (int t = 0; t < T; t++)                         // 오른쪽 아래 기준 인과 마스크: 낱말 t 는 pos+t 까지 봄
            KN.attn(&qkv[(size_t)t * 3 * d], K, V, pos + t + 1, d, heads, hd, scale, sc.data(), &a[(size_t)t * d]);
        for (int t = 0; t < T; t++) {
            float *xt = &x[(size_t)t * d];
            mv(l.o, &a[(size_t)t * d], tmp.data());
            for (int i = 0; i < d; i++) xt[i] += tmp[i];
            rms(xt, l.n2.data(), h.data(), d);
            mv(l.w12, h.data(), u.data());
            KN.swiglu(u.data(), g.data(), f);
            mv(l.w3, g.data(), tmp.data());
            for (int i = 0; i < d; i++) xt[i] += tmp[i];
        }
    }
    rms(&x[(size_t)(T - 1) * d], norm.data(), h.data(), d);
    mv(emb, h.data(), logits);
}

// ---------- Runner ----------
void Runner::feed(const std::vector<int> &ids) {
    if (ids.empty()) return;
    m->step(ids.data(), (int)ids.size(), cache, (int)toks.size(), logits.data());
    toks.insert(toks.end(), ids.begin(), ids.end());
}

Runner::Snap Runner::snapshot() const {
    Snap s;
    s.toks = toks; s.logits = logits;
    const size_t n = toks.size() * m->d, st = (size_t)m->ctx * m->d;
    s.k.resize(n * m->layers); s.v.resize(n * m->layers);
    for (int li = 0; li < m->layers; li++) {
        std::memcpy(s.k.data() + li * n, cache.k.data() + li * st, n * 4);
        std::memcpy(s.v.data() + li * n, cache.v.data() + li * st, n * 4);
    }
    return s;
}

void Runner::restore(const Snap &s) {
    toks = s.toks; logits = s.logits;
    const size_t n = toks.size() * m->d, st = (size_t)m->ctx * m->d;
    for (int li = 0; li < m->layers; li++) {
        std::memcpy(cache.k.data() + li * st, s.k.data() + li * n, n * 4);
        std::memcpy(cache.v.data() + li * st, s.v.data() + li * n, n * 4);
    }
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
