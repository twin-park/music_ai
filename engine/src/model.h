// 음악 AI 계산기 — score/ai/npmodel.py 와 같은 셈 (RMSNorm · RoPE 짝 섞기 · SwiGLU · 가중치 묶음 · KV 캐시)
// 가중치 파일은 tools/export_model.py 가 만든 .bin (int8 줄마다 크기). v3: 메모리에도 int8 그대로 두고 정수 곱으로 계산
//   (활성값을 13비트 정수로 바꿔 int8 × int16 → int32 합 — 메모리 1/4, 훨씬 빠름. float 로 풀어 계산한 값과 차이는 재서 확인)
#pragma once
#include <cstdint>
#include <string>
#include <vector>

struct Model {
    int vocab = 0, d = 0, layers = 0, heads = 0, ctx = 0, f = 0, hd = 0;
    struct Mat { int rows = 0, cols = 0; std::vector<int8_t> q; std::vector<float> s; };   // W[r][c] = q[r·cols+c] × s[r]
    struct Layer { std::vector<float> n1, n2; Mat qkv, o, w12, w3; };
    Mat emb;
    std::vector<float> norm, cosT, sinT;
    std::vector<Layer> L;

    struct Cache { std::vector<float> k, v; };       // [층][자리][d] (머리별로 hd 씩 이어 붙음)
    bool load(const std::string &path, std::string *err = nullptr);
    Cache new_cache() const;
    // ids 를 pos 자리부터 넣고 마지막 낱말 다음 점수(vocab 개)를 logits 에
    void step(const int *ids, int T, Cache &c, int pos, float *logits) const;
    size_t weight_bytes() const;                     // 메모리에 올린 가중치 크기
};

// 낱말을 이어 넣는 손잡이 — 문맥이 차면 머리 + 최근 마디로 다시 채움 (gen.py Runner)
struct Runner {
    const Model *m;
    Model::Cache cache;
    std::vector<int> toks;
    std::vector<float> logits;
    explicit Runner(const Model *m_) : m(m_), cache(m_->new_cache()), logits(m_->vocab) {}
    void reset() { toks.clear(); }
    void feed(const std::vector<int> &ids);
    void feed1(int id) { feed(std::vector<int>{id}); }
    void room(int need, int head_len, int bar_id);
    // 같은 문맥에서 여러 번 써 볼 때: 처음 상태를 기억했다 되돌림 (쓴 자리까지만 복사)
    struct Snap { std::vector<int> toks; std::vector<float> logits, k, v; };
    Snap snapshot() const;
    void restore(const Snap &s);
};
