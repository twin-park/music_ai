// 낱말 번호 — tools/export_model.py 가 score/ai/tok.py 에서 만듦 (손으로 고치지 말 것)
#pragma once
namespace tk {
constexpr int TPB = 12, P_LO = 36, P_HI = 96, NDUR = 17;
constexpr int DUR_SET[NDUR] = {1, 2, 3, 4, 6, 8, 9, 12, 16, 18, 24, 30, 36, 48, 60, 72, 96};
constexpr int DUR_IDX[200] = {0, 0, 1, 2, 3, 3, 4, 4, 5, 6, 6, 7, 7, 7, 7, 8, 8, 8, 9, 9, 9, 9, 10, 10, 10, 10, 10, 10, 11, 11, 11, 11, 11, 11, 12, 12, 12, 12, 12, 12, 12, 12, 12, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16};
constexpr int C_BOS = 1, M_BOS = 1;
constexpr int C_EOS = 2, M_EOS = 2;
constexpr int C_BAR = 3, M_BAR = 3;
constexpr int C_SRC_jazz = 4, C_SRC_pop = 5, C_SRC_song = 6;
constexpr int C_MODE_maj = 7, C_MODE_min = 8, C_TS_4 = 9, C_TS_3 = 10;
constexpr int C_SEC0 = 11, C_BEAT0 = 16, C_DEG0 = 20, C_Q0 = 32;
constexpr int M_KIND_solo = 4;
constexpr int M_KIND_head = 5;
constexpr int M_FEEL_swing = 6;
constexpr int M_FEEL_straight = 7;
constexpr int M_FEEL_latin = 8;
constexpr int M_TEMPO_slow = 9;
constexpr int M_TEMPO_med = 10;
constexpr int M_TEMPO_fast = 11;
constexpr int M_TS_4 = 13;
constexpr int M_TS_3 = 14;
constexpr int M_MODE_maj = 15;
constexpr int M_MODE_min = 16;
constexpr int M_CNONE = 51;
constexpr int M_NNONE = 75;
constexpr int M_DENS0 = 17, M_REG0 = 21, M_CPOS0 = 24, M_CR0 = 28, M_CQ0 = 40;
constexpr int M_NR0 = 52, M_NQ0 = 64, M_POS0 = 76, M_P0 = 124, M_D0 = 185;
}
