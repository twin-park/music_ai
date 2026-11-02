# AI 가중치 → C++ 엔진용 이진 파일 + 낱말 번호 헤더
#   python tools/export_model.py        → data/chord.bin · data/melody.bin (int8, 줄마다 크기) · data/*_f32.bin (시험용) · src/tokens.h
import os, sys, struct
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "..")
sys.path.insert(0, os.path.join(ROOT, "score", "ai"))
import tok as T

def write(npz, out, quant):
    z = np.load(npz)
    c = {k[4:]: int(z[k]) for k in z.files if k.startswith("cfg_")}
    d = c["d"]; f = int(d * 8 / 3 / 64 + 0.999) * 64
    with open(out, "wb") as fo:
        fo.write(b"CBGM" + struct.pack("<8i", 1, c["vocab"], d, c["layers"], c["heads"], c["ctx"], f, quant))
        def vec(a):
            fo.write(np.ascontiguousarray(a, np.float32).tobytes())
        def mat(a):
            a = np.asarray(a, np.float32)
            if quant:
                s = np.abs(a).max(1) / 127 + 1e-12
                fo.write(np.round(a / s[:, None]).clip(-127, 127).astype(np.int8).tobytes()); vec(s)
            else:
                vec(a)
        mat(z["emb.weight"]); vec(z["norm.weight"])
        for i in range(c["layers"]):
            p = f"layers.{i}."
            vec(z[p + "n1.weight"]); mat(z[p + "qkv.weight"]); mat(z[p + "o.weight"])
            vec(z[p + "n2.weight"]); mat(z[p + "w12.weight"]); mat(z[p + "w3.weight"])
    print("→", out, f"{os.path.getsize(out) / 1e6:.1f}MB", c)

runs = os.path.join(ROOT, "runs")
for w in ("chord", "melody"):
    write(f"{runs}/score_{w}/best.npz", os.path.join(HERE, "..", "data", f"{w}.bin"), 1)
    write(f"{runs}/score_{w}/best.npz", os.path.join(HERE, "..", "data", f"{w}_f32.bin"), 0)

C, M = T.C_ID, T.M_ID
L = ["// 낱말 번호 — tools/export_model.py 가 score/ai/tok.py 에서 만듦 (손으로 고치지 말 것)", "#pragma once", "namespace tk {"]
L += [f"constexpr int TPB = {T.TPB}, P_LO = {T.P_LO}, P_HI = {T.P_HI}, NDUR = {len(T.DUR_SET)};",
      "constexpr int DUR_SET[NDUR] = {" + ", ".join(map(str, T.DUR_SET)) + "};",
      "constexpr int DUR_IDX[200] = {" + ", ".join(map(str, T.DUR_IDX.tolist())) + "};"]
for k in ("BOS", "EOS", "BAR"):
    L.append(f"constexpr int C_{k} = {C[k]}, M_{k} = {M[k]};")
L.append(f"constexpr int C_SRC_jazz = {C['SRC_jazz']}, C_SRC_pop = {C['SRC_pop']}, C_SRC_song = {C['SRC_song']};")
L.append(f"constexpr int C_MODE_maj = {C['MODE_maj']}, C_MODE_min = {C['MODE_min']}, C_TS_4 = {C['TS_4']}, C_TS_3 = {C['TS_3']};")
L.append(f"constexpr int C_SEC0 = {C['SEC_A']}, C_BEAT0 = {C['BEAT_0']}, C_DEG0 = {C['DEG_0']}, C_Q0 = {C['Q_0']};")
for k in ("KIND_solo", "KIND_head", "FEEL_swing", "FEEL_straight", "FEEL_latin", "TEMPO_slow", "TEMPO_med", "TEMPO_fast",
          "TS_4", "TS_3", "MODE_maj", "MODE_min", "CNONE", "NNONE"):
    L.append(f"constexpr int M_{k} = {M[k]};")
L.append(f"constexpr int M_DENS0 = {M['DENS_0']}, M_REG0 = {M['REG_0']}, M_CPOS0 = {M['CPOS_0']}, M_CR0 = {M['CR_0']}, M_CQ0 = {M['CQ_0']};")
L.append(f"constexpr int M_NR0 = {M['NR_0']}, M_NQ0 = {M['NQ_0']}, M_POS0 = {M['POS_0']}, M_P0 = {M[f'P_{T.P_LO}']}, M_D0 = {M[f'D_{T.DUR_SET[0]}']};")
L.append("}")
open(os.path.join(HERE, "..", "src", "tokens.h"), "w").write("\n".join(L) + "\n")
print("→ src/tokens.h")
