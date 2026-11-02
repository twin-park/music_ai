# 분위기 9개 — 무엇을 움직이는가(빠르기·조·스윙·화음 색·선율 밀도/음역·편성·단락별 악기 배치)
# arrange(S, MEL, P, m): 단락마다 누가 선율을 맡고 누가 반주하는지 = "편곡 공식"
from theory import fit, guide, stack

# ---------------- 도우미 ----------------
def oct_fit(notes, lo, hi):
    """선율을 악기 음역으로 옥타브 옮김 (가운데 음 기준), 튀는 음만 접기"""
    if not notes:
        return []
    ps = sorted(p for _, _, p in notes)
    med, k = ps[len(ps) // 2], 0
    while med + k > hi - 5:
        k -= 12
    while med + k < lo + 5:
        k += 12
    return [(t, d, fit(p + k, lo, hi)) for t, d, p in notes]


def sel(notes, S, b0, b1):
    return [(t, d, p) for t, d, p in notes if b0 * S.ts - 1e-6 <= t < b1 * S.ts - 1e-6]


def top_line(S, b0, b1, lo=70, hi=81):
    """도입용 맨 윗줄: 3·7음을 가장 가깝게 이어 (반음씩 내려가는 가이드톤 줄)"""
    out, p = [], None
    for a, b, c in S.spans_in(b0, b1):
        cands = [x for x in range(lo, hi + 1) if x % 12 in guide(c)]
        q = min(cands, key=lambda x: (abs(x - p) if p else abs(x - hi + 3)) + (1.5 if x == p else 0))
        out.append((a, b - a, q))
        p = q
    return out


def final_chord(S, P, lead=None, lead_rng=(55, 72), cym="브러시", bass=True, base=50):
    t = P["FN"] * S.ts
    c = S.chord(t)
    r = fit(c.root, 36, 43)
    up = stack([c.iv(3), c.iv(7) if c.iv(7) is not None else (c.root + 9) % 12, (c.root + 2) % 12, (c.root + 7) % 12], 55, 76)
    if lead:                                                   # 관악기 끝음과 반음으로 붙는 음(단조 9음 등)은 뺌
        ln = fit(c.iv(3), *lead_rng)
        up = [q for q in up if abs(q - ln) not in (1, 11, 13)]
    for k, p in enumerate([r, r + 7] + up):
        S.add("피아노 왼손" if p < 60 else "피아노 오른손", t + k * .09, 6, p, base + 2 - k)
    S.pedal.append((t + .02, t + 6.5))
    if bass:
        S.add("베이스", t, 6, fit(c.root, 31, 43), 62)
    if lead:
        S.add(lead, t + .25, 5.5, fit(c.iv(3), *lead_rng), 50)
    if cym == "브러시":
        S.add("브러시", t, 4, 40, 30); S.add("브러시", t, 4, 51, 30)
    elif cym == "드럼":
        S.add("드럼", t, 4, 51, 40); S.add("드럼", t, 3, 49, 46)


def ending_tempo(S, P, slow=.68, last=.6):
    b = S.bpm
    S.tempo_pts = [(0, b), ((P["FN"] - 2) * S.ts, b), (P["FN"] * S.ts, b * slow), (P["FN"] * S.ts + .01, b * last)]


# ---------------- 편곡 공식들 ----------------
def ballad_combo(S, M, P, m):
    """비 오는 날: 피아노(선율+아래 화음) → 색소폰(같은 선율 변주) → 2마디씩 주고받기 → 피아노 옥타브 + 색소폰 대선율"""
    L, lr = m["lead"], m["lead_rng"]
    I0, A1, A2, B, A3, TG, FN = (P[k] for k in ("I0", "A1", "A2", "B", "A3", "TG", "FN"))
    S.piano_melody(top_line(S, I0, A1), 56, "block"); S.lh_guide(I0, A1, 40, shell=True); S.pedals(I0, A1)
    S.add("브러시", (A1 - 1) * S.ts + 2, 2, 40, 26)
    S.piano_melody(oct_fit(M["A"], 62, 86), 66, "block"); S.lh_guide(A1, A2, 46); S.pedals(A1, A2)
    S.bass(A1, A2, "two"); S.drums(A1, A2, "brush", 0)
    la = oct_fit(M["A'"], *lr)
    S.lead(L, la, 74); S.comp(list(range(A2, B)), "ballad", 47, avoid=la)
    S.bass(A2, B - 2, "two"); S.bass(B - 2, B, "walk", 72); S.drums(A2, B, "brush", 1)
    mb = M["B"]
    for k in range(0, 8, 2):
        seg = sel(mb, S, B + k, B + k + 2)
        if k in (0, 4, 6):
            s2 = oct_fit(seg, *lr)
            S.lead(L, s2, 80)
            if k == 6:
                S.piano_melody([(t, d, p + 12) for t, d, p in s2], 66, "line"); S.lh_guide(B + k, B + k + 2, 46)
            else:
                S.comp(list(range(B + k, B + k + 2)), "ballad", 50, avoid=s2)
        else:
            S.piano_melody(oct_fit(seg, 64, 88), 70, "line"); S.lh_guide(B + k, B + k + 2, 46); S.pedals(B + k, B + k + 2)
    S.bass(B, A3, "walk", 78); S.drums(B, A3, "brush_swing", 2)
    S.add("브러시", A3 * S.ts, .3, 39, 52)
    S.piano_melody(oct_fit(M["A''"], 64, 88), 70, "octave"); S.lh_guide(A3, TG, 46); S.pedals(A3, TG)
    S.guide_line(A3, TG - 2, L, 56, lr[0], lr[0] + 17)
    S.bass(A3, TG - 2, "walk", 72); S.bass(TG - 2, TG, "two"); S.drums(A3, TG, "brush", 1)
    mt = M["끝"]
    s1 = oct_fit(sel(mt, S, TG, TG + 2), *lr)
    S.lead(L, s1, 66); S.comp([TG, TG + 1], "ballad", 44, avoid=s1)
    S.piano_melody(oct_fit(sel(mt, S, TG + 2, FN), 64, 86), 60, "block"); S.lh_guide(TG + 2, FN, 42); S.pedals(TG + 2, FN)
    S.bass(TG, FN, "two", 66); S.drums(TG, FN, "brush", 0, fill_every=99)
    final_chord(S, P, L, (lr[0], lr[0] + 14)); ending_tempo(S, P)


def trio_swing(S, M, P, m):
    """평온한 재즈: 피아노 트리오 + 재즈기타. 피아노 선율 → 기타가 선율, 피아노 반주 → 피아노 → 피아노 옥타브"""
    I0, A1, A2, B, A3, TG, FN = (P[k] for k in ("I0", "A1", "A2", "B", "A3", "TG", "FN"))
    S.comp(list(range(I0, A1)), "swing", 46); S.bass(I0, A1, "two", 70); S.drums(I0, A1, "brush_swing", 0, fill_every=4)
    S.piano_melody(oct_fit(M["A"], 64, 86), 64, "dyad"); S.lh_guide(A1, A2, 46)
    S.bass(A1, A2, "two", 72); S.drums(A1, A2, "brush_swing", 0)
    g = oct_fit(M["A'"], 55, 77)
    S.lead("재즈기타", g, 72); S.comp(list(range(A2, B)), "swing", 46, avoid=g)
    S.bass(A2, B, "walk", 74); S.drums(A2, B, "brush_swing", 1)
    S.piano_melody(oct_fit(M["B"], 64, 88), 66, "block"); S.lh_guide(B, A3, 46)
    S.guitar_comp(list(range(B, A3)), "재즈기타", "swing", 46)
    S.bass(B, A3, "walk", 76); S.drums(B, A3, "brush_swing", 2)
    S.piano_melody(oct_fit(M["A''"], 64, 88), 68, "octave"); S.lh_guide(A3, TG, 46)
    S.bass(A3, TG, "walk", 74); S.drums(A3, TG, "brush_swing", 1)
    S.piano_melody(oct_fit(M["끝"], 64, 86), 60, "block"); S.lh_guide(TG, FN, 42); S.pedals(TG + 2, FN)
    S.bass(TG, FN, "two", 66); S.drums(TG, FN, "brush", 0, fill_every=99)
    final_chord(S, P, "재즈기타", (55, 70)); ending_tempo(S, P)


def cool_straight(S, M, P, m):
    """밤 드라이브: 로즈 4도 반주 + 뮤트 트럼펫 선율, 곧은 8분 베이스·드럼 → B 는 피아노가 선율"""
    I0, A1, A2, B, A3, TG, FN = (P[k] for k in ("I0", "A1", "A2", "B", "A3", "TG", "FN"))
    R = ("로즈", "로즈")
    S.comp(list(range(I0, A1)), "straight", 50, "quartal", 50, 72, parts=R); S.bass(I0, A1, "straight", 72); S.drums(I0, A1, "straight", 0, fill_every=4)
    for sec, a, b, lvl in (("A", A1, A2, 0), ("A'", A2, B, 1)):
        t = oct_fit(M[sec], 58, 80)
        S.lead("뮤트트럼펫", t, 76 + lvl * 3); S.comp(list(range(a, b)), "straight", 48, "quartal", 50, 72, avoid=t, parts=R)
        S.bass(a, b, "straight", 74); S.drums(a, b, "straight", lvl)
    pb = oct_fit(M["B"], 62, 86)
    S.piano_melody(pb, 68, "dyad"); S.comp(list(range(B, A3)), "straight", 44, "quartal", 48, 64, avoid=pb, parts=R)
    S.bass(B, A3, "straight", 76); S.drums(B, A3, "straight", 1)
    t = oct_fit(M["A''"], 58, 80)
    S.lead("뮤트트럼펫", t, 80); S.comp(list(range(A3, TG)), "straight", 48, "quartal", 50, 72, avoid=t, parts=R)
    S.bass(A3, TG, "straight", 74); S.drums(A3, TG, "straight", 1)
    t = oct_fit(M["끝"], 58, 78)
    S.lead("뮤트트럼펫", t, 70); S.comp(list(range(TG, FN)), "straight", 44, "quartal", 50, 72, avoid=t, parts=R)
    S.bass(TG, FN, "straight", 66); S.drums(TG, FN, "straight", 0, fill_every=99, crash=False)
    final_chord(S, P, "뮤트트럼펫", (58, 72), cym="드럼"); ending_tempo(S, P, .75, .7)


def uptempo(S, M, P, m):
    """즐거운 대화: 알토 색소폰 ↔ 비브라폰 주고받기, 피아노 스윙 반주, 워킹 베이스, 라이드"""
    I0, A1, A2, B, A3, TG, FN = (P[k] for k in ("I0", "A1", "A2", "B", "A3", "TG", "FN"))
    S.comp(list(range(I0, A1)), "swing", 52); S.bass(I0, A1, "walk", 76); S.drums(I0, A1, "ride", 0, fill_every=4)
    a = oct_fit(M["A"], 57, 79); S.lead("알토색소폰", a, 82); S.comp(list(range(A1, A2)), "swing", 50, avoid=a)
    v = oct_fit(M["A'"], 62, 86); S.lead("비브라폰", v, 86); S.comp(list(range(A2, B)), "swing", 48, avoid=v)
    for k in range(0, 8, 2):
        seg = sel(M["B"], S, B + k, B + k + 2)
        x = oct_fit(seg, 57, 79) if k % 4 == 0 else oct_fit(seg, 62, 86)
        S.lead("알토색소폰" if k % 4 == 0 else "비브라폰", x, 84)
        S.comp(list(range(B + k, B + k + 2)), "swing", 50, avoid=x)
    a = oct_fit(M["A''"], 57, 79)
    S.lead("알토색소폰", a, 84); S.lead("비브라폰", [(t, d, p + 12) for t, d, p in a], 72)
    S.comp(list(range(A3, TG)), "swing", 48, avoid=a)
    t = oct_fit(M["끝"], 57, 77); S.lead("알토색소폰", t, 76); S.comp(list(range(TG, FN)), "swing", 46, avoid=t)
    S.bass(A1, FN, "walk", 80); S.drums(A1, B, "ride", 1); S.drums(B, TG, "ride", 2); S.drums(TG, FN, "ride", 0, fill_every=99, crash=False)
    final_chord(S, P, "알토색소폰", (57, 72), cym="드럼"); ending_tempo(S, P, .7, .6)


def bossa(S, M, P, m):
    """바닷가 보사노바: 나일론 기타 + 보사 베이스·림샷, 플루트 선율 → B 는 피아노 → A'' 플루트 + 현악"""
    I0, A1, A2, B, A3, TG, FN = (P[k] for k in ("I0", "A1", "A2", "B", "A3", "TG", "FN"))
    S.guitar_comp(list(range(I0, FN)), "나일론기타", "bossa", 56)
    S.bass(I0, FN, "bossa", 74); S.drums(I0, A1, "bossa", 0, fill_every=99); S.drums(A1, FN, "bossa", 0)
    for sec, a, b, v in (("A", A1, A2, 76), ("A'", A2, B, 80), ("A''", A3, TG, 80), ("끝", TG, FN, 70)):
        S.lead("플루트", oct_fit(M[sec], 67, 91), v, legato=.95)
    pb = oct_fit(M["B"], 64, 86)
    S.piano_melody(pb, 64, "dyad")
    S.comp(list(range(A2, B)), "bossa", 40, avoid=oct_fit(M["A'"], 67, 91), parts=("로즈", "로즈"))
    S.strings_pad(A3, FN, "현악", 46, 55, 74)
    final_chord(S, P, "플루트", (67, 82), cym="드럼"); ending_tempo(S, P, .75, .7)


def lullaby_waltz(S, M, P, m):
    """아이 재우기 (3/4): 피아노 쿵-짝-짝 + 3·6도 겹 선율 → 첼레스타가 한 옥타브 위에서 같이 → 현악이 감쌈"""
    I0, A1, A2, B, A3, TG, FN = (P[k] for k in ("I0", "A1", "A2", "B", "A3", "TG", "FN"))
    S.piano_pattern(I0, FN, "waltz", 40); S.pedals(I0, FN, every=3)
    S.piano_melody(top_line(S, I0, A1, 67, 79), 50, "dyad")
    S.piano_melody(oct_fit(M["A"], 64, 84), 56, "dyad")
    a2 = oct_fit(M["A'"], 64, 84)
    S.piano_melody(a2, 54, "line"); S.lead("첼레스타", [(t, d, p + 12) for t, d, p in a2], 50)
    S.piano_melody(oct_fit(M["B"], 64, 86), 58, "dyad"); S.strings_pad(B, A3, "현악", 40, 55, 72)
    S.piano_melody(oct_fit(M["A''"], 64, 84), 54, "dyad"); S.strings_pad(A3, FN, "현악", 38, 55, 72)
    S.drums(B, A3, "waltz_brush", 0, fill_every=99)
    S.piano_melody(oct_fit(M["끝"], 64, 82), 48, "dyad")
    final_chord(S, P, "첼레스타", (76, 88), cym=None, bass=False, base=42); ending_tempo(S, P, .7, .6)


def calm_piano(S, M, P, m):
    """진정: 피아노 혼자 (왼손 1-5-10 펼침 + 선율 아래 화음), A'' 에 현악이 아주 작게"""
    I0, A1, A2, B, A3, TG, FN = (P[k] for k in ("I0", "A1", "A2", "B", "A3", "TG", "FN"))
    S.piano_pattern(I0, FN, "arp", 40); S.pedals(I0, FN)
    S.piano_melody(top_line(S, I0, A1, 68, 79), 50, "block")
    for sec, v, mode in (("A", 58, "block"), ("A'", 58, "dyad"), ("B", 62, "block"), ("A''", 60, "octave"), ("끝", 52, "block")):
        S.piano_melody(oct_fit(M[sec], 64, 86), v, mode)
    S.strings_pad(A3, FN, "현악", 38, 55, 74)
    final_chord(S, P, None, cym=None, bass=False, base=44)
    b = S.bpm
    pts = []
    for bar in range(0, P["FN"] + 1, 4):                       # 네 마디마다 끝에서 살짝 늦췄다 돌아오기
        pts += [(bar * S.ts, b), ((bar + 4) * S.ts - 1, b), ((bar + 4) * S.ts - .01, b * .9)]
    S.tempo_pts = sorted([p for p in pts if p[0] < (P["FN"] - 2) * S.ts]) + [((P["FN"] - 2) * S.ts, b), (P["FN"] * S.ts, b * .7), (P["FN"] * S.ts + .01, b * .6)]


def comfort(S, M, P, m):
    """위로 (영화음악 느낌): 피아노 옥타브 선율 + 왼손 펼침 → 첼로가 선율 → 바이올린 + 현악 → 피아노 옥타브 + 첼로 대선율"""
    I0, A1, A2, B, A3, TG, FN = (P[k] for k in ("I0", "A1", "A2", "B", "A3", "TG", "FN"))
    S.piano_pattern(I0, FN, "arp", 42); S.pedals(I0, FN)
    S.piano_melody(top_line(S, I0, A1, 68, 80), 52, "block")
    S.piano_melody(oct_fit(M["A"], 66, 88), 64, "octave")
    S.lead("첼로", oct_fit(M["A'"], 50, 72), 66); S.strings_pad(A2, B, "현악", 36, 43, 58)
    S.lead("바이올린", oct_fit(M["B"], 67, 91), 66); S.strings_pad(B, A3, "현악", 44, 52, 72)
    S.piano_melody(oct_fit(M["A''"], 66, 88), 68, "octave"); S.guide_line(A3, TG, "첼로", 56, 48, 62); S.strings_pad(A3, TG, "현악", 40, 55, 72)
    S.piano_melody(oct_fit(M["끝"], 64, 86), 56, "block")
    final_chord(S, P, "첼로", (48, 60), cym=None, bass=False, base=46); ending_tempo(S, P, .7, .6)


def groove(S, M, P, m):
    """낮 드라이브: 테너 색소폰 + 피아노 곧은 8분 반주, 일렉 베이스, 백비트 드럼 → B 는 피아노 옥타브 → 둘이 같이"""
    I0, A1, A2, B, A3, TG, FN = (P[k] for k in ("I0", "A1", "A2", "B", "A3", "TG", "FN"))
    S.comp(list(range(I0, A1)), "straight", 52); S.bass(I0, FN, "straight", 78, part="일렉베이스")
    S.drums(I0, A1, "straight", 0, fill_every=4)
    for sec, a, b in (("A", A1, A2), ("A'", A2, B)):
        x = oct_fit(M[sec], 52, 76); S.lead("테너색소폰", x, 82); S.comp(list(range(a, b)), "straight", 50, avoid=x)
    pb = oct_fit(M["B"], 64, 88); S.piano_melody(pb, 70, "octave"); S.comp(list(range(B, A3)), "straight", 44, "quartal", 48, 64, avoid=pb, parts=("로즈", "로즈"))
    x = oct_fit(M["A''"], 52, 76); S.lead("테너색소폰", x, 84); S.piano_melody([(t, d, p + 12) for t, d, p in x], 60, "line")
    S.comp(list(range(A3, TG)), "straight", 44, "quartal", 48, 64, avoid=x, parts=("로즈", "로즈"))
    x = oct_fit(M["끝"], 52, 74); S.lead("테너색소폰", x, 74); S.comp(list(range(TG, FN)), "straight", 46, avoid=x)
    S.drums(A1, B, "straight", 1); S.drums(B, TG, "straight", 2); S.drums(TG, FN, "straight", 0, fill_every=99, crash=False)
    final_chord(S, P, "테너색소폰", (52, 68), cym="드럼", bass=False); S.add("일렉베이스", P["FN"] * S.ts, 5, fit(S.chord(P["FN"] * S.ts).root, 31, 43), 64)
    ending_tempo(S, P, .78, .7)


# ---------------- 분위기 표 ----------------
MOODS = {
    "비오는날": dict(keys=["Eb", "Db", "F"], minor=False, bpm=68, ts=4, swing=.62, color=1, src="jazz", feel="swing", tempo="TEMPO_slow",
                    dens=1, reg=1, mel_range=(60, 82), mtemp=0.9, maxn=6, leap=9, copy=2, lead="테너색소폰", lead_rng=(50, 74), reverb=2.6,
                    band="피아노 · 테너 색소폰 · 베이스 · 브러시", arrange=ballad_combo,
                    recipe="느린 스윙 발라드 · 피아노 선율 아래 드롭2 화음 · 색소폰이 같은 선율 변주 · B 2마디씩 주고받기 · A'' 피아노 옥타브 + 색소폰 3·7음 대선율 · 베이스 2박→워킹 · 브러시"),
    "평온한재즈": dict(keys=["F", "Bb", "G"], minor=False, bpm=104, ts=4, swing=.64, color=1, src="jazz", feel="swing", tempo="TEMPO_med",
                     dens=1, reg=1, mel_range=(62, 82), mtemp=0.9, maxn=7, leap=9, copy=2, reverb=2.2,
                     band="피아노 트리오 · 재즈기타 · 브러시", arrange=trio_swing,
                     recipe="미디엄 스윙 · 피아노 3·6도 겹 선율 → 기타가 선율 + 피아노 반주 → 피아노 화음 선율 + 기타 4분 반주 → 피아노 옥타브 · 워킹 베이스 · 브러시 스윙"),
    "밤드라이브": dict(keys=["Dm", "Am", "Em"], minor=True, bpm=96, ts=4, swing=0, color=1, src="jazz", feel="straight", tempo="TEMPO_med",
                    dens=1, reg=1, mel_range=(60, 80), mtemp=0.9, maxn=7, leap=9, copy=2, reverb=2.6,
                    band="로즈 · 뮤트 트럼펫 · 피아노 · 베이스 · 드럼", arrange=cool_straight,
                    recipe="곧은 8분 쿨재즈 · 로즈 4도 쌓기 반주 · 뮤트 트럼펫 선율 → B 피아노 선율 · 곧은 8분 베이스 · 하이햇+림"),
    "즐거운대화": dict(keys=["Bb", "F", "Eb"], minor=False, bpm=176, ts=4, swing=.6, color=1, src="jazz", feel="swing", tempo="TEMPO_fast",
                    dens=2, reg=1, mel_range=(60, 82), mtemp=0.92, maxn=9, leap=10, copy=2, reverb=2.0,
                    band="알토 색소폰 · 비브라폰 · 피아노 · 베이스 · 드럼", arrange=uptempo,
                    recipe="빠른 스윙 · 알토 → 비브라폰 → 2마디씩 주고받기 → 둘이 옥타브로 같이 · 피아노 찰스턴 반주 · 워킹 베이스 · 라이드 심벌"),
    "바닷가보사노바": dict(keys=["D", "F", "G"], minor=False, bpm=128, ts=4, swing=0, color=1, src="jazz", feel="latin", tempo="TEMPO_med",
                      dens=1, reg=2, mel_range=(64, 86), mtemp=0.9, maxn=7, leap=9, copy=2, reverb=2.4,
                      band="나일론 기타 · 플루트 · 피아노 · 로즈 · 베이스 · 림샷 · 현악", arrange=bossa,
                      recipe="보사노바 · 나일론 기타 엄지 베이스 + 화음 뜯기 · 플루트 선율 → B 피아노 → A'' 현악 · 보사 베이스 · 림샷·킥·하이햇"),
    "아이재우기": dict(jazzy=False, keys=["F", "G", "C"], minor=False, bpm=82, ts=3, swing=0, color=0, src="song", feel="straight", tempo="TEMPO_slow",
                    dens=1, reg=1, mel_range=(62, 80), mtemp=0.88, maxn=5, leap=7, copy=2, reverb=2.8,
                    band="피아노 · 첼레스타 · 현악", arrange=lullaby_waltz,
                    recipe="3/4 왈츠 자장가 · 왼손 쿵-짝-짝 · 3·6도 겹 선율 → 첼레스타가 한 옥타브 위 같이 → 현악이 감쌈 · B 만 아주 작은 브러시"),
    "진정": dict(jazzy=False, keys=["Db", "Eb", "Ab"], minor=False, bpm=58, ts=4, swing=.6, color=1, src="jazz", feel="swing", tempo="TEMPO_slow",
               dens=1, reg=1, mel_range=(62, 82), mtemp=0.88, maxn=6, leap=8, copy=2, reverb=3.0,
               band="피아노 혼자 · 현악(끝 무렵)", arrange=calm_piano,
               recipe="아주 느린 피아노 발라드 · 왼손 1-5-10 펼침 · 선율 아래 화음 · 네 마디마다 살짝 늦춤(루바토) · A'' 현악 아주 작게"),
    "위로": dict(jazzy=False, keys=["A", "D", "E"], minor=False, bpm=72, ts=4, swing=0, color=0, src="pop", feel="straight", tempo="TEMPO_slow",
               dens=1, reg=1, mel_range=(62, 82), mtemp=0.9, maxn=6, leap=9, copy=2, reverb=2.8,
               band="피아노 · 첼로 · 바이올린 · 현악", arrange=comfort,
               recipe="영화음악 느낌 · 피아노 옥타브 선율 + 왼손 펼침 → 첼로 선율 → 바이올린 + 현악 → 피아노 옥타브 + 첼로 대선율"),
    "낮드라이브": dict(keys=["G", "A", "Bb"], minor=False, bpm=120, ts=4, swing=0, color=1, src="jazz", feel="straight", tempo="TEMPO_med",
                    dens=2, reg=1, mel_range=(60, 82), mtemp=0.92, maxn=8, leap=10, copy=2, reverb=2.0,
                    band="테너 색소폰 · 피아노 · 로즈 · 일렉 베이스 · 드럼", arrange=groove,
                    recipe="곧은 8분 그루브 · 테너 색소폰 선율 + 피아노 반주 → B 피아노 옥타브 + 로즈 → 색소폰과 피아노가 같이 · 일렉 베이스 · 백비트 드럼"),
}
