# 화성 잣대 — 엔진 덤프(tools/harm_dump) 를 읽어 '얼마나 조화로운가' 를 숫자로
#   ① 선율 ↔ 코드: 강박 · 긴 음이 코드음/텐션/그 밖 · 프레이즈 끝음 · 코드 밖 음이 순차로 풀리나 · 조 밖 음
#   ② 세로 울림: 같이 울리는 음들 사이 반음(1) · 단9도(13) 부딪힘이 있는 시간 비율, 누가 부딪히나
#   ③ 진행: 근음 움직임(5도 아래 · 반음 · 증4도) · 조 안 근음 · 코드 종류
#   python tools/harm_metrics.py 덤프.txt [덤프2.txt …]      · --real 이면 실제 곡(선율↔코드)도 같이
import sys, collections, pickle
import numpy as np

TONES_Q = [[0, 4, 7], [0, 4, 7, 11], [0, 3, 7], [0, 3, 7, 10], [0, 4, 7, 10], [0, 4, 10], [0, 5, 7, 10], [0, 3, 6, 10], [0, 3, 6, 9], [0, 4, 8], [0, 3, 7, 11]]
TENS_Q = [[2, 9], [2, 9], [2, 5, 10], [2, 5], [2, 9], [1, 3, 8], [2, 9], [5, 8], [2, 5], [2], [2]]
MAJ, MIN = [0, 2, 4, 5, 7, 9, 11], [0, 2, 3, 5, 7, 8, 10]


def read(path):
    secs, cur = [], None
    for line in open(path, encoding="utf-8"):
        f = line.split()
        if not f:
            continue
        if f[0] == "S":
            cur = dict(k=int(f[1]), role=f[2], key=int(f[3]), minor=int(f[4]), a=int(f[5]), b=int(f[6]), ts=int(f[7]), C=[], M=[], N=[])
            secs.append(cur)
        elif f[0] == "C":
            i = f.index("/")
            cur["C"].append(dict(a=float(f[1]), b=float(f[2]), root=int(f[3]), qa=int(f[4]), name=f[5], tones=[int(x) for x in f[6:i]], tens=[int(x) for x in f[i + 1:]]))
        elif f[0] == "M":
            cur["M"].append((float(f[1]), float(f[2]), int(f[3])))
        elif f[0] == "N":
            cur["N"].append((f[1], float(f[2]), float(f[3]), int(f[4]), int(f[5]), int(f[6])))
    return secs


def chord_at(C, t):
    best = None
    for c in C:
        if c["a"] - 1e-6 <= t:
            best = c
    return best or (C[0] if C else None)


def melody_fit(sections):
    """sections: [dict(ts, key, minor, C=[dict(a,b,root,tones(pc),tens(pc))], M=[(t,d,p)])] → 비율들"""
    R = collections.Counter()
    for s in sections:
        ts, M = s["ts"], sorted(s["M"])
        scale = [(s["key"] + x) % 12 for x in (MIN if s["minor"] else MAJ)]
        for i, (t, d, p) in enumerate(M):
            c = chord_at(s["C"], t)
            if c is None:
                continue
            pc = p % 12
            kind = "ct" if pc in c["tones"] else "ten" if pc in c["tens"] else "out"
            beat = abs(t - round(t)) < 1e-3
            strong = beat and int(round(t)) % (2 if ts == 4 else 3) == 0
            R["n"] += 1; R["dur"] += d
            R["dur_" + kind] += d
            if strong:
                R["strong"] += 1; R["strong_" + kind] += 1
            if d >= 1:
                R["long"] += 1; R["long_" + kind] += 1
            if pc not in scale and kind != "ct":
                R["chrom"] += 1
            nxt = M[i + 1] if i + 1 < len(M) else None
            if nxt is None or nxt[0] - (t + d) >= 1.0:
                R["end"] += 1; R["end_" + kind] += 1
            if kind == "out" and nxt is not None:
                R["out_n"] += 1; R["out_step"] += abs(nxt[2] - p) <= 2
            if nxt is not None:
                iv = abs(nxt[2] - p)
                R["iv"] += 1; R["iv_step"] += iv <= 2; R["iv_leap"] += iv > 7; R["iv_tri"] += iv == 6; R["iv_sum"] += iv
    g = lambda a, b: R[a] / max(1, R[b])
    return {"강박 코드음": g("strong_ct", "strong"), "강박 텐션": g("strong_ten", "strong"), "강박 그밖": g("strong_out", "strong"),
            "긴음 코드음": g("long_ct", "long"), "긴음 그밖": g("long_out", "long"),
            "길이 코드음": g("dur_ct", "dur"), "길이 그밖": g("dur_out", "dur"), "끝음 코드음": g("end_ct", "end"), "끝음 그밖": g("end_out", "end"),
            "그밖→순차": g("out_step", "out_n"), "조밖 음": g("chrom", "n"), "순차": g("iv_step", "iv"), "큰도약": g("iv_leap", "iv"),
            "증4도약": g("iv_tri", "iv"), "평균음정": g("iv_sum", "iv")}


def vertical(secs):
    """같이 울리는 음 사이 반음 · 단9도. 1/8박 격자로 훑음."""
    tot = harsh = harsh_mel = clus = 0
    who = collections.Counter()
    for s in secs:
        N = s["N"]
        if not N:
            continue
        t0, t1 = s["a"] * s["ts"], s["b"] * s["ts"]
        grid = np.arange(t0, t1, .125) + .06
        st = np.array([n[1] for n in N]); en = np.array([n[1] + n[2] for n in N]); pp = np.array([n[3] for n in N])
        for g in grid:
            on = np.nonzero((st <= g) & (en > g + .03))[0]
            if len(on) < 2:
                tot += 1
                continue
            tot += 1
            ps = pp[on]
            d = np.abs(ps[:, None] - ps[None, :])
            bad = np.argwhere(np.triu((d == 1) | (d == 13), 1))
            if len(bad):
                harsh += 1
                involved_mel = False
                for i, j in bad:
                    a, b = N[on[i]], N[on[j]]
                    who[tuple(sorted((a[0], b[0])))] += 1
                    involved_mel = involved_mel or a[5] or b[5]
                harsh_mel += involved_mel
            clus += int((np.triu(d == 2, 1)).sum() >= 2)
    return {"반음·단9 시간": harsh / max(1, tot), "그중 선율 낌": harsh_mel / max(1, tot), "2도 뭉침": clus / max(1, tot)}, who


def chords(secs):
    R = collections.Counter(); Q = collections.Counter()
    for s in secs:
        if s["role"] in ("도입",):
            continue
        scale = [(s["key"] + x) % 12 for x in (MIN if s["minor"] else MAJ)]
        C = s["C"]
        for i, c in enumerate(C):
            R["n"] += 1; Q[c["name"]] += 1
            R["dia"] += c["root"] in scale
            if i + 1 < len(C):
                mv = (C[i + 1]["root"] - c["root"]) % 12
                R["mv"] += 1; R["m5"] += mv == 5; R["m1"] += mv in (1, 11); R["m6"] += mv == 6; R["m0"] += mv == 0; R["m2"] += mv in (2, 10)
        R["bars"] += s["b"] - s["a"]
    g = lambda a, b: R[a] / max(1, R[b])
    return {"마디당 코드": g("n", "bars"), "조 안 근음": g("dia", "n"), "5도 아래": g("m5", "mv"), "반음": g("m1", "mv"), "증4도": g("m6", "mv"),
            "온음": g("m2", "mv")}, Q


def real_fit(srcs, n=400):
    R = "/home/drboom/project/car_bgm/data/score_ai"
    songs = pickle.load(open(f"{R}/songs.pkl", "rb")) + pickle.load(open(f"{R}/lmd_songs.pkl", "rb"))
    try:
        songs += pickle.load(open(f"{R}/pdmx_songs.pkl", "rb"))
    except FileNotFoundError:
        pass
    out = {}
    for src in srcs:
        secs = []
        for s in [x for x in songs if x["src"] == src][:n]:
            ts = s["ts"]
            C, M = [], []
            for bi, b in enumerate(s["bars"]):
                for pos, r, q in b["chords"]:
                    C.append(dict(a=bi * ts + pos, b=0, root=r, tones=[(r + x) % 12 for x in TONES_Q[q]], tens=[(r + x) % 12 for x in TENS_Q[q]]))
                for on, d, p in b["notes"]:
                    M.append((bi * ts + on / 12, d / 12, p))
            if C and M:
                secs.append(dict(ts=ts, key=s["key"], minor=s["minor"], C=C, M=M))
        out[src] = melody_fit(secs)
    return out


def show(name, d):
    print(f"{name:24s} " + " · ".join(f"{k} {v:.2f}" if v >= 1.5 else f"{k} {100 * v:.0f}%" for k, v in d.items()))


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    for p in args:
        secs = read(p)
        body = [s for s in secs if s["role"] not in ("도입", "이음", "끝")]
        nm = p.split("/")[-1]
        for s in body:                                   # 엔진 덤프의 선율↔코드는 AI 종류(11) 기준으로도 봄 (실제 곡과 같은 잣대)
            for c in s["C"]:
                if c["qa"] >= 0:
                    c["tones_a"] = [(c["root"] + x) % 12 for x in TONES_Q[c["qa"]]]; c["tens_a"] = [(c["root"] + x) % 12 for x in TENS_Q[c["qa"]]]
        show(nm + " 선율", melody_fit(body))
        same = [dict(s, C=[dict(c, tones=c.get("tones_a", c["tones"]), tens=c.get("tens_a", c["tens"])) for c in s["C"]]) for s in body]
        show(nm + " 선율(11종)", melody_fit(same))
        for role in sorted({s["role"] for s in body}):
            show(f"  └ {role}", {k: v for k, v in melody_fit([s for s in same if s["role"] == role]).items() if k in ("강박 코드음", "강박 그밖", "긴음 그밖", "조밖 음", "순차")})
        v, who = vertical(body)
        show(nm + " 세로", v)
        print("    부딪히는 짝:", ", ".join(f"{a}×{b} {n}" for (a, b), n in who.most_common(6)))
        c, q = chords(body)
        show(nm + " 진행", c)
        print("    코드 종류:", " ".join(f"{k}×{v}" for k, v in q.most_common(12)))
        QN = ["maj", "maj7", "min", "m7", "dom", "alt", "sus", "hdim", "dim", "aug", "mM7"]
        qa = collections.Counter(QN[c["qa"]] for s in body for c in s["C"] if c["qa"] >= 0)
        print("    AI 종류:", " ".join(f"{k}×{v}" for k, v in qa.most_common(11)))
    if "--real" in sys.argv:
        for k, v in real_fit(["pop909", "ewld", "wjazzd", "lmd_jazz", "lmd_pop", "lmd_song", "pdmx_classical"]).items():
            show("실제:" + k, v)
