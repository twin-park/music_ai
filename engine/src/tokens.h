// 낱말 번호 — tools/export_model.py 가 score/ai/tok3.py 에서 만듦 (손으로 고치지 말 것)
#pragma once
namespace tk {
constexpr int TPB = 12, P_LO = 36, P_HI = 96, NDUR = 17;
constexpr int DUR_SET[NDUR] = {1, 2, 3, 4, 6, 8, 9, 12, 16, 18, 24, 30, 36, 48, 60, 72, 96};
constexpr int DUR_IDX[200] = {0, 0, 1, 2, 3, 3, 4, 4, 5, 6, 6, 7, 7, 7, 7, 8, 8, 8, 9, 9, 9, 9, 10, 10, 10, 10, 10, 10, 11, 11, 11, 11, 11, 11, 12, 12, 12, 12, 12, 12, 12, 12, 12, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16};
constexpr int C_BOS = 1, M_BOS = 1;
constexpr int C_EOS = 2, M_EOS = 2;
constexpr int C_BAR = 3, M_BAR = 3;
// 갈래: 0 재즈 · 1 팝 · 2 노래 · 3 클래식
constexpr int C_SRC0 = 4, M_SRC0 = 4, M_HEAD = 10;
constexpr int C_MODE_maj = 8, C_MODE_min = 9, C_TS_4 = 10, C_TS_3 = 11;
constexpr int C_SEC0 = 12, C_BEAT0 = 17, C_DEG0 = 21, C_Q0 = 33;
constexpr int M_KIND_solo = 8;
constexpr int M_KIND_head = 9;
constexpr int M_FEEL_swing = 10;
constexpr int M_FEEL_straight = 11;
constexpr int M_FEEL_latin = 12;
constexpr int M_TEMPO_slow = 13;
constexpr int M_TEMPO_med = 14;
constexpr int M_TEMPO_fast = 15;
constexpr int M_TS_4 = 17;
constexpr int M_TS_3 = 18;
constexpr int M_MODE_maj = 19;
constexpr int M_MODE_min = 20;
constexpr int M_CNONE = 59;
constexpr int M_NNONE = 83;
constexpr int M_DENS0 = 21, M_REG0 = 25, M_CT0 = 28, M_CPOS0 = 32, M_CR0 = 36, M_CQ0 = 48;
constexpr int M_NR0 = 60, M_NQ0 = 72, M_POS0 = 84, M_P0 = 132, M_D0 = 193;
}
