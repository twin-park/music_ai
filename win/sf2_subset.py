# SF2 사운드폰트에서 쓰는 프리셋만 남겨 작게 만들기 (윈도우 묶음용)
#   python sf2_subset.py 원본.sf2 출력.sf2 0:2 0:8 0:14      ← 뱅크:프로그램
#   프리셋 → 악기 → 샘플을 따라가며 쓰는 것만 남기고 번호를 다시 매김. 샘플 소리 데이터는 그대로 복사(뒤에 0 46개).
import struct, sys

GEN_INST, GEN_SAMPLE = 41, 53


def chunks(b, off, end):
    while off < end:
        cid, size = b[off:off + 4], struct.unpack_from("<I", b, off + 4)[0]
        yield cid, off + 8, size
        off += 8 + size + (size & 1)


def recs(data, size, fmt):
    n = struct.calcsize(fmt)
    return [list(struct.unpack_from(fmt, data, i)) for i in range(0, size, n)]


F = {"phdr": "<20sHHHIII", "pbag": "<HH", "pmod": "<HHhHH", "pgen": "<HH", "inst": "<20sH", "ibag": "<HH",
     "imod": "<HHhHH", "igen": "<HH", "shdr": "<20sIIIIIBbHH"}


def read(path):
    b = open(path, "rb").read()
    assert b[:4] == b"RIFF" and b[8:12] == b"sfbk"
    out = {}
    for cid, o, s in chunks(b, 12, len(b)):
        assert cid == b"LIST"
        kind = b[o:o + 4]
        if kind == b"INFO":
            out["INFO"] = b[o:o + s]
        for sid, so, ss in chunks(b, o + 4, o + s):
            name = sid.decode()
            if kind == b"sdta":
                out[name] = b[so:so + ss]
            elif kind == b"pdta":
                out[name] = recs(b[so:so + ss], ss, F[name])
    return out


def subset(sf, want):
    ph, pb, pm, pg = sf["phdr"], sf["pbag"], sf["pmod"], sf["pgen"]
    it, ib, im, ig, sh = sf["inst"], sf["ibag"], sf["imod"], sf["igen"], sf["shdr"]
    keep_p = [i for i in range(len(ph) - 1) if (ph[i][2], ph[i][1]) in want]
    # 프리셋 쪽 모으기
    n_ph, n_pb, n_pm, n_pg, insts = [], [], [], [], []
    for i in keep_p:
        r = list(ph[i]); r[3] = len(n_pb); n_ph.append(r)
        for bi in range(ph[i][3], ph[i + 1][3]):
            n_pb.append([len(n_pg), len(n_pm)])
            n_pm += [list(x) for x in pm[pb[bi][1]:pb[bi + 1][1]]]
            for g in pg[pb[bi][0]:pb[bi + 1][0]]:
                g = list(g)
                if g[0] == GEN_INST:
                    if g[1] not in insts:
                        insts.append(g[1])
                    g[1] = insts.index(g[1])
                n_pg.append(g)
    # 악기 쪽
    n_it, n_ib, n_im, n_ig, samples = [], [], [], [], []
    for j in insts:
        r = list(it[j]); r[1] = len(n_ib); n_it.append(r)
        for bi in range(it[j][1], it[j + 1][1]):
            n_ib.append([len(n_ig), len(n_im)])
            n_im += [list(x) for x in im[ib[bi][1]:ib[bi + 1][1]]]
            for g in ig[ib[bi][0]:ib[bi + 1][0]]:
                g = list(g)
                if g[0] == GEN_SAMPLE and g[1] not in samples:
                    samples.append(g[1])
                n_ig.append(g)
    # 스테레오 짝 샘플도 함께
    k = 0
    while k < len(samples):
        s = sh[samples[k]]
        if s[9] & 0x0E and s[8] < len(sh) - 1 and s[8] not in samples:
            samples.append(s[8])
        k += 1
    samples.sort()
    sid = {o: n for n, o in enumerate(samples)}
    for g in n_ig:
        if g[0] == GEN_SAMPLE:
            g[1] = sid[g[1]]
    # 소리 데이터 다시 쌓기
    smpl, sm24 = sf["smpl"], sf.get("sm24")
    new16, new24, n_sh = bytearray(), bytearray() if sm24 is not None else None, []
    for o in samples:
        s = list(sh[o])
        a, e = s[1], s[2]
        start = len(new16) // 2
        new16 += smpl[a * 2:e * 2] + b"\0" * 92
        if new24 is not None:
            new24 += sm24[a:e] + b"\0" * 46
        d = start - a
        s[1], s[2], s[3], s[4] = a + d, e + d, s[3] + d, s[4] + d
        if s[9] & 0x0E:
            s[8] = sid.get(s[8], 0)
        n_sh.append(s)
    # 끝 표시 레코드
    n_ph.append([b"EOP", 0, 0, len(n_pb), 0, 0, 0]); n_pb.append([len(n_pg), len(n_pm)])
    n_pm.append([0, 0, 0, 0, 0]); n_pg.append([0, 0])
    n_it.append([b"EOI", len(n_ib)]); n_ib.append([len(n_ig), len(n_im)])
    n_im.append([0, 0, 0, 0, 0]); n_ig.append([0, 0])
    n_sh.append([b"EOS", 0, 0, 0, 0, 0, 0, 0, 0, 0])
    pd = dict(phdr=n_ph, pbag=n_pb, pmod=n_pm, pgen=n_pg, inst=n_it, ibag=n_ib, imod=n_im, igen=n_ig, shdr=n_sh)
    return bytes(new16), (bytes(new24) if new24 is not None else None), pd, len(keep_p), len(insts), len(samples)


def ck(cid, data):
    return cid + struct.pack("<I", len(data)) + data + (b"\0" if len(data) & 1 else b"")


def write(path, info, s16, s24, pd):
    sd = b"sdta" + ck(b"smpl", s16) + (ck(b"sm24", s24) if s24 is not None else b"")
    pdta = b"pdta" + b"".join(ck(n.encode(), b"".join(struct.pack(F[n], *r) for r in pd[n]))
                              for n in ("phdr", "pbag", "pmod", "pgen", "inst", "ibag", "imod", "igen", "shdr"))
    body = b"sfbk" + ck(b"LIST", info) + ck(b"LIST", sd) + ck(b"LIST", pdta)
    open(path, "wb").write(b"RIFF" + struct.pack("<I", len(body)) + body)


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    want = {tuple(int(x) for x in a.split(":")) for a in sys.argv[3:]}
    sf = read(src)
    s16, s24, pd, np_, ni, ns = subset(sf, want)
    write(dst, sf["INFO"], s16, s24, pd)
    print(f"→ {dst}: 프리셋 {np_} · 악기 {ni} · 샘플 {ns} · {len(s16) / 1e6:.0f}MB")
