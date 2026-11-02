// 음악 AI 계산기 — score/ai/npmodel.py 와 같은 셈 (RMSNorm · RoPE 짝 섞기 · SwiGLU · 가중치 묶음 · KV 캐시)
// 가중치 파일은 tools/export_model.py 가 만든 .bin (int8 줄마다 크기 → 읽을 때 float 로 풀어 둠)
#pragma once
#include <string>
#include <vector>

struct Model {
    int vocab = 0, d = 0, layers = 0, heads = 0, ctx = 0, f = 0, hd = 0;
    struct Layer { std::vector<float> n1, qkv, o, n2, w12, w3; };
    std::vector<float> emb, norm, cosT, sinT;
    std::vector<Layer> L;

    struct Cache { std::vector<float> k, v; };       // [층][머리][ctx][hd]
    bool load(const std::string &path, std::string *err = nullptr);
    Cache new_cache() const;
    // ids 를 pos 자리부터 넣고 마지막 낱말 다음 점수(vocab 개)를 logits 에
    void step(const int *ids, int T, Cache &c, int pos, float *logits) const;
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
    // 같은 문맥에서 여러 번 써 볼 때: 처음 상태를 통째로 기억했다 되돌림 (다시 넣기보다 빠름)
    struct Snap { std::vector<int> toks; std::vector<float> logits, k, v; };
    Snap snapshot() const { return {toks, logits, cache.k, cache.v}; }
    void restore(const Snap &s) { toks = s.toks; logits = s.logits; cache.k = s.k; cache.v = s.v; }
};
