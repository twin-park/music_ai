# 작곡 본체: 분위기 → (진행 AI 후보 → 공식 점수로 고름) → (선율 AI, A' 는 A 앞부분을 이어 받아 변주) → 편곡 공식 → 악보 글자
#   python compose.py 비오는날 [씨앗]      → out/<이름>_<씨앗>.txt  (+ --play 면 mp3 까지)
import os, sys, random, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai"))
import numpy as np
import gen
import tok as T
from theory import Key, Chord
from arrange import Song, QUALS
from styles import MOODS

HERE = os.path.dirname(os.path.abspath(__file__))
_M = {}


def model(which):
    if which not in _M:
        _M[which] = gen.load(which)
    return _M[which]


# ---------------- 진행: 후보 여러 개 → 공식 점수 ----------------
def prog_score(bars, form, minor):
    """좋은 진행 공식: A 안 코드 5개+, 2마디 되풀이 적게, ii-V 있음, B 는 A 와 다름, 끝은 으뜸화음"""
    A = bars[:form[0][1]]
    flat = [(d, q) for bar in A for _, d, q in bar]
    distinct = len(set(flat))
    loop = sum(1 for i in range(2, len(A)) if A[i] == A[i - 2])
    allf = [(d, q) for bar in bars for _, d, q in bar]
    iiv = sum(1 for (d1, q1), (d2, q2) in zip(allf, allf[1:]) if QUALS[q1] in ("m7", "hdim", "min") and QUALS[q2] in ("dom", "alt") and (d2 - d1) % 12 == 5)
    s0 = sum(n for _, n in form[:2])
    B = bars[s0: s0 + form[2][1]] if len(form) > 2 else []
    b_diff = len(set((d, q) for bar in B for _, d, q in bar) - set(flat))
    end_ok = any(d == 0 for _, d, q in bars[-1])
    return min(distinct, 8) * 1.0 - loop * 0.8 + min(iiv, 6) * 0.5 + min(b_diff, 4) * 0.6 + (2 if end_ok else 0)


def pick_progression(mood, form, seed, n=8):
    best = None
    for k in range(n):
        bars = gen.progression(model("chord"), form, minor=mood["minor"], src=mood["src"], ts=mood["ts"],
                               beats=(0, 2) if mood["ts"] == 4 else (0,), temp=mood.get("ctemp", 1.0), seed=seed * 100 + k)
        sc = prog_score(bars, form, mood["minor"])
        if best is None or sc > best[0]:
            best = (sc, bars)
    return best[1], best[0]


# ---------------- 선율: AI 가 쓰고, 공식 점수로 마디 묶음 고르기 ----------------
TONES = {"maj": [0, 4, 7], "maj7": [0, 4, 7, 11], "min": [0, 3, 7], "m7": [0, 3, 7, 10], "dom": [0, 4, 7, 10], "alt": [0, 4, 10],
         "sus": [0, 5, 7, 10], "hdim": [0, 3, 6, 10], "dim": [0, 3, 6, 9], "aug": [0, 4, 8], "mM7": [0, 3, 7, 11]}
TENS = {"maj": [2, 9], "maj7": [2, 9], "min": [2, 5, 10], "m7": [2, 5], "dom": [2, 9], "alt": [1, 3, 8], "sus": [2, 9],
        "hdim": [5, 8], "dim": [2, 5], "aug": [2], "mM7": [2]}


def mel_score(notes, abs_bars, ts, dens_target):
    """강박 음이 코드음/텐션인지, 마디당 음 수가 목표에 가까운지, 같은 음 연타가 적은지"""
    if not notes:
        return -9
    good = tot = rep = 0
    for i, (bi, on, d, p) in enumerate(notes):
        ch = [c for c in abs_bars[bi] if c[0] * T.TPB <= on] or abs_bars[bi][:1]
        if not ch:
            continue
        b, r, q = ch[-1]
        if on % T.TPB == 0 or d >= T.TPB:
            tot += 1
            iv = (p - r) % 12
            good += 1 if iv in TONES[QUALS[q]] else .6 if iv in TENS[QUALS[q]] else 0
        if i and p == notes[i - 1][3]:
            rep += 1
    ps = [n[3] for n in notes]
    span = max(ps) - min(ps)
    return good / max(1, tot) - .5 * rep / len(notes) - .15 * abs(len(notes) / len(abs_bars) - dens_target) + .2 * min(1, span / 12)


def write_section(w, abs_bars, nexts, rng_seed, lo, hi, temp, leap, copy=None, tries=3, dens_target=4, ts=4, maxn=8):
    """w: MelodyWriter (문맥 이어 감). 후보를 tries 번 써 보고 가장 나은 것을 문맥에 남김.
    copy: 앞 단락 선율 [(마디, 틱, 길이, 음)] 중 처음 몇 마디를 그대로 넣음 (A' = A 의 시작을 이어 받기)"""
    best = None
    base_toks = list(w.r.toks)
    for k in range(tries):
        w.r.reset(); w.r.feed(base_toks); w.prev_p = None
        w.rng = np.random.default_rng(rng_seed * 10 + k)
        out = []
        for bi, (chords, nxt) in enumerate(zip(abs_bars, nexts)):
            force = None
            if copy is not None and bi in copy:
                force = copy[bi]
            ns = w.bar(chords, nxt, lo, hi, temp=temp, leap=leap, force=force, rest_ok=(bi % 8 == 7), max_notes=maxn)   # 통째로 쉬는 마디는 단락 끝에서만
            out += [(bi, on, d, p) for on, d, p in ns]
        sc = mel_score([n for n in out if not (copy and n[0] in copy)], abs_bars, ts, dens_target)
        if best is None or sc > best[0]:
            best = (sc, out, list(w.r.toks))
    w.r.reset(); w.r.feed(best[2])
    return best[1], best[0]


def to_beats(notes, bar0, ts, end_bar=None):
    """(마디, 틱, 길이틱, 음) → (박, 길이박, 음). 다음 음과 겹치면 자르기."""
    xs = sorted(((bar0 + bi) * ts + on / T.TPB, d / T.TPB, p) for bi, on, d, p in notes)
    out = []
    for i, (t, d, p) in enumerate(xs):
        if i + 1 < len(xs):
            d = min(d, xs[i + 1][0] - t)
        if end_bar is not None:
            d = min(d, end_bar * ts - t)
        if d > .05:
            out.append((t, d, p))
    return out


# ---------------- 곡 만들기 ----------------
def compose(name, seed=1, verbose=True, progress=None):
    """progress(단계번호) — 1 진행 AI · 2 선율 AI · 3 편곡 (윈도우 화면에서 씀)"""
    step = progress or (lambda *a: None)
    mood = MOODS[name]
    rng = random.Random(seed)
    ts = mood["ts"]
    keyname = rng.choice(mood["keys"])
    K = Key(keyname)
    form = [("A", 8), ("A", 8), ("B", 8), ("A", 8)]
    step(1)
    rel, psc = pick_progression(mood, form, seed)
    # 도입(A 의 끝 4마디) + AABA + 끝맺음(공식: 2-5 두 번 → I)
    if mood["minor"]:
        tag = [[(0, 2, 7), (2, 7, 5)], [(0, 0, 3)], [(0, 2, 7), (2, 7, 5)], [(0, 0, 3)]]
        final = [(0, 0, 10 if mood.get("color", 1) == 2 else 2)]
    else:
        tag = [[(0, 4, 3), (2, 9, 4)], [(0, 2, 3), (2, 7, 4)], [(0, 4, 3), (2, 9, 4)], [(0, 2, 3), (2, 7, 6)]]
        final = [(0, 0, 1)]
    if ts == 3:
        tag = [[(0, 2, 3)], [(0, 7, 4)], [(0, 2, 3)], [(0, 7, 4)]] if not mood["minor"] else [[(0, 2, 7)], [(0, 7, 5)], [(0, 2, 7)], [(0, 7, 5)]]
    intro = [list(b) for b in rel[4:8]]
    body = intro + rel + tag + [final]
    absb = [[(b, (K.pc + d) % 12, q) for b, d, q in bar] for bar in body]
    nexts = [absb[i + 1][0] if i + 1 < len(absb) and absb[i + 1] else None for i in range(len(absb))]
    S = Song(keyname, mood["bpm"], ts, mood.get("swing", 0), rng)
    S.set_chords(absb, color=mood.get("color", 1))
    I0, A1, A2, B, A3, TG, FN = 0, 4, 12, 20, 28, 36, 40
    S.secs = [("도입", I0, A1), ("A", A1, A2), ("A'", A2, B), ("B", B, A3), ("A''", A3, TG), ("끝", TG, FN + 1)]

    # 선율 AI
    step(2)
    lo, hi = mood["mel_range"]
    w = gen.MelodyWriter(model("melody"), ts=ts, kind="head", feel=mood["feel"], tempo=mood["tempo"], minor=mood["minor"],
                         dens=mood["dens"], reg=mood["reg"], seed=seed)
    sec_bars = lambda a, b: (absb[a:b], nexts[a:b])
    dt = {0: 2, 1: 3.5, 2: 5.5, 3: 8}[mood["dens"]]
    mA, sA = write_section(w, *sec_bars(A1, A2), seed + 1, lo, hi, mood["mtemp"], mood["leap"], dens_target=dt, ts=ts, maxn=mood.get('maxn', 8))
    copyA = {bi: [(on, d, p) for b2, on, d, p in mA if b2 == bi] for bi in range(mood.get("copy", 2))}
    mA2, sA2 = write_section(w, *sec_bars(A2, B), seed + 2, lo, hi, mood["mtemp"], mood["leap"], copy=copyA, dens_target=dt, ts=ts, maxn=mood.get('maxn', 8))
    mB, sB = write_section(w, *sec_bars(B, A3), seed + 3, lo, hi, mood["mtemp"] + .05, mood["leap"], dens_target=dt, ts=ts, maxn=mood.get('maxn', 8))
    mA3, sA3 = write_section(w, *sec_bars(A3, TG), seed + 4, lo, hi, mood["mtemp"], mood["leap"], copy={0: copyA[0], 1: copyA.get(1, [])} if mood.get("copy", 2) >= 2 else {0: copyA[0]}, dens_target=dt, ts=ts, maxn=mood.get('maxn', 8))
    mT, sT = write_section(w, *sec_bars(TG, FN), seed + 5, lo, hi, mood["mtemp"], mood["leap"], dens_target=dt * .8, ts=ts, maxn=mood.get('maxn', 8))
    MEL = {"A": to_beats(mA, A1, ts, A2), "A'": to_beats(mA2, A2, ts, B), "B": to_beats(mB, B, ts, A3),
           "A''": to_beats(mA3, A3, ts, TG), "끝": to_beats(mT, TG, ts, FN)}
    MEL = {k: S.fix_avoid(v, jazz=mood.get('jazzy', True)) for k, v in MEL.items()}
    if verbose:
        print(f"[{name}] 조 {keyname} · 진행 점수 {psc:.1f} · 선율 점수 A {sA:.2f} A' {sA2:.2f} B {sB:.2f} A'' {sA3:.2f} 끝 {sT:.2f}")

    step(3)
    # 편곡 공식 (moods.py 의 arrange 함수가 단락별로 악기를 배치)
    mood["arrange"](S, MEL, dict(I0=I0, A1=A1, A2=A2, B=B, A3=A3, TG=TG, FN=FN), mood)
    S.phrase_dynamics(jazz=mood.get("jazzy", True))
    S.section_dynamics()
    mv, rm = S.declash()
    lm, lr = S.low_mud()
    if verbose:
        print(f"  반주 정리: 선율과 부딪히는 음 {mv}개 옮김 · {rm}개 뺌 · 낮은 반음 뭉침 {lm}개 옥타브 올림 · {lr}개 뺌")
    title = f"{name} (AI 작곡 · 씨앗 {seed})"
    chords_txt = " | ".join(" ".join(c.name(K) for a, b, c in S.spans if bar * ts <= a < (bar + 1) * ts) for bar in range(A1, A2))
    notes = [f"편성: {mood['band']}", f"형식: 도입4 → A8 → A'8 → B8 → A''8 → 끝4 + 마지막 화음",
             f"진행 AI(재즈 스탠더드 등 2,800곡 학습) 후보 8개 중 공식 점수 {psc:.1f} 로 고름 · A 진행: {chords_txt}",
             f"선율 AI(명연주 솔로·리드시트·팝 1,700곡 학습)가 단락마다 3번 써서 공식 점수로 고름 · A' 와 A'' 는 A 의 첫 {mood.get('copy', 2)}마디를 이어 받아 변주",
             f"편곡 공식: {mood['recipe']}"]
    info = {"템포": f"{mood['bpm']}", "박자": f"{ts}/4", "스윙": f"{mood.get('swing', 0)}", "잔향": f"{mood.get('reverb', 2.4)}"}
    return S.to_sheet(title, notes, info, drum_parts=("브러시", "드럼"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mood"); ap.add_argument("seed", nargs="?", type=int, default=1)
    ap.add_argument("--play", action="store_true")
    A = ap.parse_args()
    names = list(MOODS) if A.mood == "all" else [A.mood]
    for nm in names:
        sh = compose(nm, A.seed)
        out = os.path.join(HERE, "out", f"{nm}_{A.seed}.txt")
        sh.save(out)
        print("  →", out)
        if A.play:
            import play, render as R
            y = play.render_sheet(sh)
            R.write(y, out[:-4] + ".wav")
