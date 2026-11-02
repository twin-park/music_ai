# 악보 글자(.txt) → 소리(.wav/.mp3).  python play.py 악보.txt [출력.wav]
# 피아노 = 실제 녹음(Salamander), 나머지 = 사운드폰트(fluidsynth). 연주 단계에서 사람 손 같은 ms 흔들림만 더함.
import os, sys, random, types
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.append(os.path.join(HERE, "..", "compose"))
import render as R
from notation import load

# 악기 이름(대괄호 안 낱말) → (엔진, 연주하는 동안 목표 크기 dBFS, 좌우, 잔향, 저역컷Hz)
INST = [("피아노", ("piano",), -18, -0.05, 0.26, 40),
        ("테너", ("sf", "gu", 0, 66, False), -18, 0.3, 0.30, 90),
        ("알토", ("sf", "gu", 0, 65, False), -18.5, 0.3, 0.30, 110),
        ("뮤트", ("sf", "gu", 0, 59, False), -19.5, 0.3, 0.30, 150),
        ("트럼펫", ("sf", "gu", 0, 56, False), -19, 0.3, 0.30, 150),
        ("비브라폰", ("sf", "gu", 0, 11, False), -21, -0.3, 0.30, 120),
        ("나일론", ("sf", "gu", 0, 24, False), -21, -0.3, 0.20, 80),
        ("기타", ("sf", "gu", 0, 26, False), -23, -0.35, 0.20, 80),
        ("로즈", ("sf", "gu", 0, 4, False), -22, -0.2, 0.30, 80),
        ("플루트", ("sf", "sso", 0, 14, False), -19.5, 0.25, 0.35, 250),
        ("첼로", ("sf", "sso", 0, 8, False), -21, -0.3, 0.45, 50),
        ("바이올린", ("sf", "sso", 0, 2, False), -22, 0.35, 0.45, 200),
        ("현악", ("sf", "gu", 0, 49, False), -25, 0.0, 0.50, 100),
        ("일렉", ("sf", "gu", 0, 33, False), -22, 0.05, 0.08, 30),
        ("첼레스타", ("sf", "gu", 0, 8, False), -23, 0.3, 0.40, 200),
        ("베이스", ("sf", "gu", 0, 32, False), -21.5, 0.05, 0.08, 30),
        ("브러시", ("sf", "gu", 128, 40, True), -31, -0.12, 0.22, 60),
        ("드럼", ("sf", "gu", 128, 32, True), -27, -0.1, 0.18, 40)]
JITTER_MS = {"piano": 7, "drum": 3, "bass": 5, "lead": 9}


def inst_of(name):
    for kw, eng, db, pn, rv, hp in INST:
        if kw in name:
            return kw, eng, db, pn, rv, hp
    raise KeyError(f"모르는 악기: {name}")


def humanize(notes, ms, rng, melody_lead=False):
    """같은 순간에 치는 음은 함께 움직이고(화음이 흩어지지 않게), 피아노는 맨 윗음이 아주 조금 먼저."""
    groups = {}
    for n in notes:
        groups.setdefault(round(n[0], 3), []).append(n)
    out = []
    for t, ns in groups.items():
        d = rng.gauss(0, ms / 1000)
        top = max(n[2] for n in ns)
        for t0, t1, p, v in ns:
            e = d + (-0.006 if (melody_lead and p == top and len(ns) > 1) else rng.uniform(0, 0.006) if len(ns) > 1 else 0)
            out.append((max(0, t0 + e), t1 + e, p, int(np.clip(v + rng.gauss(0, 2.5), 1, 127))))
    return out


def active_db(x, win=0.05):
    """소리 나는 구간만의 크기(dB): 50ms 창마다 재서 가장 큰 창보다 40dB 이상 작은 창(쉬는 곳)은 뺌"""
    n = int(win * R.SR)
    w = (x[: len(x) // n * n] ** 2).mean(1).reshape(-1, n).mean(1)
    db = 10 * np.log10(w + 1e-12)
    keep = db > db.max() - 40
    return float(10 * np.log10(w[keep].mean() + 1e-12))


# ---------------- 연주 단계: 음정 보정 · 박 맞추기 · 관악기 표현 ----------------
import json, tempfile, subprocess, mido
_TUNE = json.load(open(os.path.join(HERE, "tune_table.json"), encoding="utf-8")) if os.path.exists(os.path.join(HERE, "tune_table.json")) else {}
WIND = {"테너": dict(scoop=.5, fall=.22, vib=(5.2, 16)), "알토": dict(scoop=.45, fall=.22, vib=(5.4, 14)),
        "뮤트": dict(scoop=.4, fall=.2, vib=(4.8, 9)), "트럼펫": dict(scoop=.35, fall=.2, vib=(4.8, 10)),
        "플루트": dict(scoop=.1, fall=0, vib=(5.4, 12)), "첼로": dict(scoop=.1, fall=0, vib=(5.6, 14)),
        "바이올린": dict(scoop=.1, fall=0, vib=(5.8, 14))}
PIANO_DELAY = .018


def tune_of(kw, p):
    """보정표에서 그 음(없으면 가장 가까운 음)의 (센트 어긋남, 시작 지연 초)"""
    row = _TUNE.get(kw)
    if not row:
        return 0.0, 0.0
    k = min(row, key=lambda x: abs(int(x) - p))
    c, on = row[k]
    return max(-30, min(30, c)), max(0, on) / 1000


def bend_val(cents):
    return int(max(-8191, min(8191, cents / 200 * 8192)))


def perform(notes, kw, eng, length, rng, pedals=()):
    """사운드폰트 악기 연주. 음마다: 음정 보정(피치벤드) · 소리 시작 지연만큼 앞당김.
    관악기(한 줄 선율)는 + 프레이즈 숨(CC11 이어짐) · 아래서 밀어 올리기(스쿱) · 끝 떨어뜨리기(폴) · 늦게 들어오는 비브라토"""
    _, font, bank, prog, drum = eng
    TPB = 960                                     # 1박 = 1초 (템포 60)
    ev = []
    tk = lambda t: max(0, int(round(t * TPB)))
    if drum:
        ev.append((0, 0, mido.Message("program_change", channel=9, program=prog)))
        for t0, t1, p, v in notes:
            ev.append((tk(t0), 2, mido.Message("note_on", channel=9, note=p, velocity=v)))
            ev.append((tk(t1), 1, mido.Message("note_off", channel=9, note=p, velocity=0)))
    else:
        mono = kw in WIND or kw in ("베이스", "일렉")
        chans = [0] if mono else [c for c in range(16) if c != 9][:12]
        for c in chans:
            ev.append((0, 0, mido.Message("control_change", channel=c, control=0, value=bank)))
            ev.append((0, 0, mido.Message("program_change", channel=c, program=prog)))
            ev.append((0, 0, mido.Message("control_change", channel=c, control=7, value=110)))
            ev.append((0, 0, mido.Message("control_change", channel=c, control=11, value=100)))
        ns = sorted(notes)
        if mono:                                   # 한 줄: 다음 음이 오면 앞 음은 거기서 끝 (레가토)
            ns = [(t0, min(t1, ns[i + 1][0] - .008) if i + 1 < len(ns) else t1, p, v) for i, (t0, t1, p, v) in enumerate(ns)]
        w = WIND.get(kw)
        busy = {c: -1.0 for c in chans}
        for i, (t0, t1, p, v) in enumerate(ns):
            cents, delay = tune_of(kw, p)
            base = -cents
            t0s = max(0, t0 - max(0, delay - .005))
            t1s = max(t0s + .03, t1 - max(0, delay - .005))
            if mono:
                c = 0
            else:                                  # 화음 악기: 비어 있는 채널을 돌려 써서 음마다 따로 보정
                c = min(chans, key=lambda x: (busy[x] > t0s, busy[x]))
                busy[c] = t1s + .3
            ev.append((tk(t0s) - 2, 0, mido.Message("pitchwheel", channel=c, pitch=bend_val(base))))
            if w:
                prev = ns[i - 1] if i else None
                nxt = ns[i + 1] if i + 1 < len(ns) else None
                gap_before = t0 - prev[1] if prev else 9
                gap_after = nxt[0] - t1 if nxt else 9
                dur = t1s - t0s
                e0 = int(max(40, min(127, 30 + v * .85)))
                ev.append((tk(t0s) - 1, 0, mido.Message("control_change", channel=c, control=11, value=e0)))
                # 스쿱: 쉬고 들어오거나 위로 뛰어 들어갈 때 아래서 밀어 올림
                if (gap_before > .25 or (prev and p - prev[2] >= 4)) and rng.random() < w["scoop"] and dur > .12:
                    depth = rng.uniform(40, 80)
                    for k in range(8):
                        x = k / 7
                        ev.append((tk(t0s + x * .075), 3, mido.Message("pitchwheel", channel=c, pitch=bend_val(base - depth * (1 - x) ** 2))))
                # 긴 음: 숨 부풀렸다 가라앉기 + 늦게 들어오는 비브라토
                if dur > .45:
                    rate, depth = w["vib"]
                    st = t0s + max(.18, dur * .35)
                    t = st
                    while t < t1s - .03:
                        ramp = min(1, (t - st) / .35)
                        ev.append((tk(t), 3, mido.Message("pitchwheel", channel=c, pitch=bend_val(base + depth * ramp * np.sin(2 * np.pi * rate * (t - st))))))
                        t += .012
                    last = gap_after > .4
                    for k in range(1, 9):
                        x = k / 8
                        e = e0 * (1 + .12 * np.sin(np.pi * min(1, x * 1.4))) * (1 - (.3 if last else .08) * max(0, x - .6) / .4)
                        ev.append((tk(t0s + dur * x), 3, mido.Message("control_change", channel=c, control=11, value=int(max(20, min(127, e))))))
                # 폴: 프레이즈 끝 짧은 음을 아래로 흘림
                elif gap_after > .6 and rng.random() < w["fall"] and dur > .12:
                    for k in range(8):
                        x = k / 7
                        tt = t1s - .14 + x * .2
                        ev.append((tk(tt), 3, mido.Message("pitchwheel", channel=c, pitch=bend_val(base - 190 * x ** 1.6))))
                        ev.append((tk(tt), 3, mido.Message("control_change", channel=c, control=11, value=int(e0 * (1 - .6 * x)))))
                    t1s += .07
            ev.append((tk(t0s), 2, mido.Message("note_on", channel=c, note=p, velocity=int(v))))
            ev.append((tk(t1s), 1, mido.Message("note_off", channel=c, note=p, velocity=0)))
        for a, b in pedals:
            for c in chans:
                ev.append((tk(a), 0, mido.Message("control_change", channel=c, control=64, value=127)))
                ev.append((tk(b), 0, mido.Message("control_change", channel=c, control=64, value=0)))
    ev.sort(key=lambda e: (e[0], e[1]))
    mid = mido.MidiFile(ticks_per_beat=TPB)
    tr = mido.MidiTrack(); mid.tracks.append(tr)
    tr.append(mido.MetaMessage("set_tempo", tempo=1000000, time=0))
    now = 0
    for t, _, m in ev:
        t = max(0, t)
        tr.append(m.copy(time=t - now)); now = t
    with tempfile.TemporaryDirectory() as td:
        mid.save(f"{td}/a.mid")
        R.run_fluid(R.SF[font], f"{td}/a.mid", f"{td}/a.wav")
        import soundfile as sf
        x, _ = sf.read(f"{td}/a.wav", dtype="float32")
    out = np.zeros((length, 2), np.float32)
    n = min(length, len(x)); out[:n] = x[:n]
    return out


def master(tracks, length, reverb_sec=2.4, target_rms_db=-17):
    """믹스: 압축을 약하게(1.5:1) 해서 강약이 살아 있게"""
    from scipy.signal import fftconvolve
    dry = np.zeros((length, 2), np.float32); send = np.zeros((length, 2), np.float32)
    for x, db, p, rv, hp in tracks:
        y = x * 10 ** (db / 20)
        if hp:
            y = R.filt(y, "high", hp)
        y = R.pan(y, p)
        dry += y; send += y * rv
    if reverb_sec:
        dry = dry + fftconvolve(send, R.make_ir(reverb_sec), axes=0)[:length].astype(np.float32) * .9
    y = R.compress(dry, thr_db=-15, ratio=1.5, att=.02, rel=.4)
    rms = np.sqrt((y[np.abs(y).max(1) > 1e-4] ** 2).mean() + 1e-12)
    y *= 10 ** (target_rms_db / 20) / rms
    y = R.limit(y)
    fade = int(1.5 * R.SR); y[-fade:] *= np.linspace(1, 0, fade)[:, None]
    return y


def render_sheet(sh, seed=1, progress=None):
    """progress(악기 이름, 몇 번째, 모두) · 끝에 progress(None, n, n) = 믹스"""
    rng = random.Random(seed)
    end = max(n[1] for p in sh.parts.values() for n in p.notes)
    length = int((end + 4.5) * R.SR)
    groups = {}
    for p in sh.parts.values():
        kw = inst_of(p.name)[0]
        g = groups.setdefault(kw, {"notes": [], "pedals": [], "name": p.name})
        g["notes"] += p.notes; g["pedals"] += p.pedals
    tracks = []
    for gi, (kw, g) in enumerate(groups.items()):
        if progress:
            progress(g["name"], gi, len(groups))
        _, eng, db, pn, rv, hp = inst_of(g["name"])
        kind = "piano" if eng[0] == "piano" else "drum" if eng[4] else "bass" if kw in ("베이스", "일렉") else "lead"
        ns = humanize(g["notes"], JITTER_MS[kind], rng, melody_lead=(kind == "piano"))
        if eng[0] == "piano":
            out = []
            sh_t = PIANO_DELAY - .005                                             # 피아노 샘플 소리 시작 지연만큼 앞당김
            for t0, t1, p, v in ns:
                e = t1
                for a, b in g["pedals"]:
                    if a - 0.02 <= t1 <= b + 1e-6:
                        e = max(e, b); break
                out.append((max(0, t0 - sh_t), e - sh_t, p, v))
            x = piano().render(out, None, length)
        else:
            x = perform(ns, kw, eng, length, rng, g["pedals"])
        act = active_db(x)
        print(f"  {g['name']}: 음 {len(ns)} · 연주 중 크기 {act:.1f}dB → {db}dB", flush=True)
        tracks.append((x, db - act, pn, rv, hp))
    if progress:
        progress(None, len(groups), len(groups))
    return master(tracks, length, reverb_sec=float(sh.info.get("잔향", 2.4)))


_piano = None


def piano():
    global _piano
    if _piano is None:
        _piano = R.Salamander()
    return _piano


if __name__ == "__main__":
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(src)[0] + ".wav"
    sh = load(src)
    y = render_sheet(sh)
    R.write(y, dst)
    print(f"→ {dst} ({len(y) / R.SR:.0f}초)")
