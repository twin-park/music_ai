// 음악 모델 계산기 — WebAssembly SIMD 판. engine.js 와 같은 계산(int8 가중치, float32 활성값).
// 모든 위치는 wasm 메모리 바이트 위치. JS 가 메모리를 배치하고 cfg 배열로 알려 준다.
#include <wasm_simd128.h>
#include <math.h>

typedef struct { const signed char *q; const float *s; int rows, cols; } Q8;
typedef struct { const float *n1, *n2; Q8 qkv, o, w12, w3; } Layer;

static int D, L, H, HD, CTX, NV, F;
static float EPS;
static Q8 EMB;
static const float *NORM;
static Layer LY[64];
static float *KC, *VC, *COS, *SIN, *X, *Hb, *QKV, *ATT, *TMP, *U, *G, *SC, *LOG;

static void *P(int off) { return (void *)(long)off; }

// cfg: [d, layers, heads, ctx, vocab, f, eps(float bits), emb_q, emb_s, norm,
//       층마다 n1 n2 qkv_q qkv_s o_q o_s w12_q w12_s w3_q w3_s,
//       K V cos sin x h qkv att tmp u g sc logits]
__attribute__((export_name("init"))) void init(const int *c) {
  D = c[0]; L = c[1]; H = c[2]; CTX = c[3]; NV = c[4]; F = c[5];
  EPS = *(const float *)&c[6]; HD = D / H;
  EMB = (Q8){P(c[7]), P(c[8]), NV, D};
  NORM = P(c[9]);
  int k = 10;
  for (int l = 0; l < L; l++) {
    LY[l].n1 = P(c[k++]); LY[l].n2 = P(c[k++]);
    LY[l].qkv = (Q8){P(c[k]), P(c[k + 1]), 3 * D, D}; k += 2;
    LY[l].o = (Q8){P(c[k]), P(c[k + 1]), D, D}; k += 2;
    LY[l].w12 = (Q8){P(c[k]), P(c[k + 1]), 2 * F, D}; k += 2;
    LY[l].w3 = (Q8){P(c[k]), P(c[k + 1]), D, F}; k += 2;
  }
  KC = P(c[k++]); VC = P(c[k++]); COS = P(c[k++]); SIN = P(c[k++]); X = P(c[k++]); Hb = P(c[k++]);
  QKV = P(c[k++]); ATT = P(c[k++]); TMP = P(c[k++]); U = P(c[k++]); G = P(c[k++]); SC = P(c[k++]); LOG = P(c[k++]);
}

static inline float hsum(v128_t a) {
  return wasm_f32x4_extract_lane(a, 0) + wasm_f32x4_extract_lane(a, 1) +
         wasm_f32x4_extract_lane(a, 2) + wasm_f32x4_extract_lane(a, 3);
}

static short XQ[4096];

// out = W·x : x 를 13비트 정수로 바꿔 i16 내적(dot_i16x8)으로 8개씩. 합이 int32 를 넘지 않게 ±8191.
static void matvec(const Q8 *W, const float *x, float *out) {
  const int n = W->cols;
  float mx = 1e-20f;
  for (int i = 0; i < n; i++) { float a = fabsf(x[i]); if (a > mx) mx = a; }
  const float sx = mx / 8191.0f, inv = 1.0f / sx;
  for (int i = 0; i < n; i++) XQ[i] = (short)lrintf(x[i] * inv);
  for (int r = 0; r < W->rows; r++) {
    const signed char *w = W->q + (long)r * n;
    v128_t a0 = wasm_i32x4_splat(0), a1 = a0;
    for (int c = 0; c < n; c += 16) {
      v128_t b = wasm_v128_load(w + c);
      a0 = wasm_i32x4_add(a0, wasm_i32x4_dot_i16x8(wasm_i16x8_extend_low_i8x16(b), wasm_v128_load(XQ + c)));
      a1 = wasm_i32x4_add(a1, wasm_i32x4_dot_i16x8(wasm_i16x8_extend_high_i8x16(b), wasm_v128_load(XQ + c + 8)));
    }
    v128_t s = wasm_i32x4_add(a0, a1);
    int tot = wasm_i32x4_extract_lane(s, 0) + wasm_i32x4_extract_lane(s, 1) + wasm_i32x4_extract_lane(s, 2) + wasm_i32x4_extract_lane(s, 3);
    out[r] = (float)tot * sx * W->s[r];
  }
}

static void matvec_f(const Q8 *W, const float *x, float *out) {
  const int n = W->cols;
  for (int r = 0; r < W->rows; r++) {
    const signed char *w = W->q + (long)r * n;
    v128_t a0 = wasm_f32x4_splat(0), a1 = a0, a2 = a0, a3 = a0;
    for (int c = 0; c < n; c += 16) {
      v128_t b = wasm_v128_load(w + c);
      v128_t lo = wasm_i16x8_extend_low_i8x16(b), hi = wasm_i16x8_extend_high_i8x16(b);
      a0 = wasm_f32x4_add(a0, wasm_f32x4_mul(wasm_f32x4_convert_i32x4(wasm_i32x4_extend_low_i16x8(lo)), wasm_v128_load(x + c)));
      a1 = wasm_f32x4_add(a1, wasm_f32x4_mul(wasm_f32x4_convert_i32x4(wasm_i32x4_extend_high_i16x8(lo)), wasm_v128_load(x + c + 4)));
      a2 = wasm_f32x4_add(a2, wasm_f32x4_mul(wasm_f32x4_convert_i32x4(wasm_i32x4_extend_low_i16x8(hi)), wasm_v128_load(x + c + 8)));
      a3 = wasm_f32x4_add(a3, wasm_f32x4_mul(wasm_f32x4_convert_i32x4(wasm_i32x4_extend_high_i16x8(hi)), wasm_v128_load(x + c + 12)));
    }
    out[r] = hsum(wasm_f32x4_add(wasm_f32x4_add(a0, a1), wasm_f32x4_add(a2, a3))) * W->s[r];
  }
}

static float dot(const float *a, const float *b, int n) {
  v128_t s = wasm_f32x4_splat(0);
  for (int i = 0; i < n; i += 4) s = wasm_f32x4_add(s, wasm_f32x4_mul(wasm_v128_load(a + i), wasm_v128_load(b + i)));
  return hsum(s);
}

static void rms(const float *x, const float *w, float *out) {
  float ss = dot(x, x, D);
  float k = 1.0f / sqrtf(ss / D + EPS);
  for (int i = 0; i < D; i++) out[i] = x[i] * k * w[i];
}

__attribute__((export_name("step"))) void step(int tok, int t) {
  const int half = HD / 2;
  for (int i = 0; i < D; i++) X[i] = EMB.q[(long)tok * D + i] * EMB.s[tok];
  const float scale = 1.0f / sqrtf((float)HD);
  for (int l = 0; l < L; l++) {
    Layer *y = &LY[l];
    rms(X, y->n1, Hb);
    matvec(&y->qkv, Hb, QKV);
    for (int part = 0; part < 2; part++)
      for (int h = 0; h < H; h++) {
        float *u = QKV + part * D + h * HD;
        for (int i = 0; i < half; i++) {
          float x1 = u[2 * i], x2 = u[2 * i + 1], c = COS[t * half + i], s = SIN[t * half + i];
          u[2 * i] = x1 * c - x2 * s; u[2 * i + 1] = x1 * s + x2 * c;
        }
      }
    float *K = KC + (long)l * CTX * D, *V = VC + (long)l * CTX * D;
    for (int i = 0; i < D; i++) { K[(long)t * D + i] = QKV[D + i]; V[(long)t * D + i] = QKV[2 * D + i]; }
    for (int h = 0; h < H; h++) {
      const float *q = QKV + h * HD;
      float mx = -1e30f;
      for (int j = 0; j <= t; j++) { float s = dot(q, K + (long)j * D + h * HD, HD) * scale; SC[j] = s; if (s > mx) mx = s; }
      float sum = 0;
      for (int j = 0; j <= t; j++) { float e = expf(SC[j] - mx); SC[j] = e; sum += e; }
      v128_t acc[16];
      for (int i = 0; i < HD / 4; i++) acc[i] = wasm_f32x4_splat(0);
      for (int j = 0; j <= t; j++) {
        v128_t p = wasm_f32x4_splat(SC[j] / sum);
        const float *v = V + (long)j * D + h * HD;
        for (int i = 0; i < HD / 4; i++) acc[i] = wasm_f32x4_add(acc[i], wasm_f32x4_mul(p, wasm_v128_load(v + 4 * i)));
      }
      for (int i = 0; i < HD / 4; i++) wasm_v128_store(ATT + h * HD + 4 * i, acc[i]);
    }
    matvec(&y->o, ATT, TMP);
    for (int i = 0; i < D; i++) X[i] += TMP[i];
    rms(X, y->n2, Hb);
    matvec(&y->w12, Hb, U);
    for (int i = 0; i < F; i++) { float a = U[i]; G[i] = a / (1.0f + expf(-a)) * U[F + i]; }
    matvec(&y->w3, G, TMP);
    for (int i = 0; i < D; i++) X[i] += TMP[i];
  }
  rms(X, NORM, Hb);
  matvec(&EMB, Hb, LOG);
}
