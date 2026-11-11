# AI 가중치 → C++ 엔진용 이진 파일 + 낱말 번호 헤더 (v3: 낱말은 score/ai/tok3.py, 학습본은 best.pt 를 바로 읽음)
#   python tools/export_model.py [진행 best.pt] [선율 best.pt]
#     → data/chord.bin · data/melody.bin (int8, 줄마다 크기) · src/tokens.h
#   (torch 가 있는 env 로: ~/miniconda3/envs/car_bgm/bin/python)
import os, sys, struct
import numpy as np
import torch
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "..")
sys.path.insert(0, os.path.join(ROOT, "score", "ai"))
import tok3 as T


def write(pt, out, vocab):
    ck = torch.load(pt, map_location="cpu")
    c, z = ck["cfg"], {k: v.float().numpy() for k, v in ck["model"].items()}
    assert c["vocab"] == vocab, (pt, c["vocab"], vocab)
    d = c["d"]; f = int(d * 8 / 3 / 64 + 0.999) * 64
    with open(out, "wb") as fo:
        fo.write(b"CBGM" + struct.pack("<8i", 1, c["vocab"], d, c["layers"], c["heads"], c["ctx"], f, 1))
        def vec(a):
            fo.write(np.ascontiguousarray(a, np.float32).tobytes())
        def mat(a):
            a = np.asarray(a, np.float32)
            s = np.abs(a).max(1) / 127 + 1e-12
            fo.write(np.round(a / s[:, None]).clip(-127, 127).astype(np.int8).tobytes()); vec(s)
        mat(z["emb.weight"]); vec(z["norm.weight"])
        for i in range(c["layers"]):
            p = f"layers.{i}."
            vec(z[p + "n1.weight"]); mat(z[p + "qkv.weight"]); mat(z[p + "o.weight"])
            vec(z[p + "n2.weight"]); mat(z[p + "w12.weight"]); mat(z[p + "w3.weight"])
    print("→", out, f"{os.path.getsize(out) / 1e6:.2f}MB", {k: c[k] for k in ("d", "layers", "heads", "ctx")}, f"검증 {ck.get('val', 0):.4f} (걸음 {ck.get('step')})")


runs = os.path.join(ROOT, "runs", "v3")
cpt = sys.argv[1] if len(sys.argv) > 1 else f"{runs}/chord/best.pt"
mpt = sys.argv[2] if len(sys.argv) > 2 else f"{runs}/melody/best.pt"
write(cpt, os.path.join(HERE, "..", "data", "chord.bin"), len(T.C_VOCAB))
write(mpt, os.path.join(HERE, "..", "data", "melody.bin"), len(T.M_VOCAB))

C, M = T.C_ID, T.M_ID
L = ["// 낱말 번호 — tools/export_model.py 가 score/ai/tok3.py 에서 만듦 (손으로 고치지 말 것)", "#pragma once", "namespace tk {"]
L += [f"constexpr int TPB = {T.TPB}, P_LO = {T.P_LO}, P_HI = {T.P_HI}, NDUR = {len(T.DUR_SET)};",
      "constexpr int DUR_SET[NDUR] = {" + ", ".join(map(str, T.DUR_SET)) + "};",
      "constexpr int DUR_IDX[200] = {" + ", ".join(map(str, T.DUR_IDX.tolist())) + "};"]
for k in ("BOS", "EOS", "BAR"):
    L.append(f"constexpr int C_{k} = {C[k]}, M_{k} = {M[k]};")
L.append("// 갈래: 0 재즈 · 1 팝 · 2 노래 · 3 클래식")
L.append(f"constexpr int C_SRC0 = {C['SRC_jazz']}, M_SRC0 = {M['SRC_jazz']}, M_HEAD = {T.M_HEAD};")
L.append(f"constexpr int C_MODE_maj = {C['MODE_maj']}, C_MODE_min = {C['MODE_min']}, C_TS_4 = {C['TS_4']}, C_TS_3 = {C['TS_3']};")
L.append(f"constexpr int C_SEC0 = {C['SEC_A']}, C_BEAT0 = {C['BEAT_0']}, C_DEG0 = {C['DEG_0']}, C_Q0 = {C['Q_0']};")
for k in ("KIND_solo", "KIND_head", "FEEL_swing", "FEEL_straight", "FEEL_latin", "TEMPO_slow", "TEMPO_med", "TEMPO_fast",
          "TS_4", "TS_3", "MODE_maj", "MODE_min", "CNONE", "NNONE"):
    L.append(f"constexpr int M_{k} = {M[k]};")
L.append(f"constexpr int M_DENS0 = {M['DENS_0']}, M_REG0 = {M['REG_0']}, M_CT0 = {M['CT_0']}, M_CPOS0 = {M['CPOS_0']}, M_CR0 = {M['CR_0']}, M_CQ0 = {M['CQ_0']};")
L.append(f"constexpr int M_NR0 = {M['NR_0']}, M_NQ0 = {M['NQ_0']}, M_POS0 = {M['POS_0']}, M_P0 = {M[f'P_{T.P_LO}']}, M_D0 = {M[f'D_{T.DUR_SET[0]}']};")
L.append("}")
open(os.path.join(HERE, "..", "src", "tokens.h"), "w").write("\n".join(L) + "\n")
print("→ src/tokens.h")
