# 조화 점검: 0.05초마다 울리는 음을 모아
#  ① 선율이 다른 음과 반음·단9도로 부딪히는 시간 비율  ② 선율이 코드음/텐션 밖인 시간 비율
#  ③ 반주가 선율보다 위에서 울리는(덮는) 시간 비율       ④ 낮은 자리(C4 아래) 반음 뭉침 시간 비율
#  python harmony_check.py 악보.txt …
import sys
from notation import load

LEAD_EXCL = ("피아노", "베이스", "브러시", "드럼", "기타", "현악", "로즈", "대선율")


def check(path):
    sh = load(path)
    P = sh.parts
    leads = [k for k in P if not any(w in k for w in LEAD_EXCL)]
    end = max((n[1] for p in P.values() for n in p.notes), default=0)
    clash = nct = cover = mud = mel_t = tot_t = 0
    t, dt = 0.0, .05
    # 선율 = 다른 선율 악기가 쉬는 동안엔 피아노 오른손 맨 윗음
    pr = sorted(P["피아노 오른손"].notes) if "피아노 오른손" in P else []
    while t < end:
        sound = []
        for k, p in P.items():
            if "브러시" in k or "드럼" in k:
                continue
            for a, b, q, v in p.notes:
                if a <= t < b:
                    sound.append((k, q))
        tot_t += 1
        lead_now = [q for k, q in sound if k in leads]
        if lead_now:
            m = max(lead_now)
            mk = next(k for k, q in sound if q == m and k in leads)
        else:
            rh = [q for k, q in sound if k == "피아노 오른손"]
            if not rh:
                t += dt; continue
            m, mk = max(rh), "피아노 오른손"
        mel_t += 1
        others = [q for k, q in sound if not (k == mk and q == m)]
        if any((q < m and (m - q) in (1, 13)) or (q > m and (q - m) in (1, 13)) for q in others):
            clash += 1
        c = sh.chord_at(t)
        if c is not None and m % 12 not in set(c.tones()) | set(c.tensions()):
            nct += 1
        if any(q > m + 2 and "베이스" not in k for k, q in sound if k != mk and (q - m) % 12 != 0):
            cover += 1
        low = sorted(q for k, q in sound if q < 60)
        if any(b - a == 1 for a, b in zip(low, low[1:])):
            mud += 1
        t += dt
    f = lambda x, n: 100 * x / max(1, n)
    return f(clash, mel_t), f(nct, mel_t), f(cover, mel_t), f(mud, tot_t)


if __name__ == "__main__":
    for p in sys.argv[1:]:
        a, b, c, d = check(p)
        print(f"{p.split('/')[-1]:24s} 선율 반음충돌 {a:4.1f}% · 선율 코드밖 {b:4.1f}% · 반주가 선율 덮음 {c:4.1f}% · 낮은 반음뭉침 {d:4.1f}%")
