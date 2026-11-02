# 학습 데이터: 네 출처를 한 꼴(곡 → 마디 → 코드·선율)로 바꿈
#   WJazzD(명연주 재즈 솔로 456, ODbL) · iRb(재즈 스탠더드 코드 1185) · OpenEWLD(공개 리드시트 ~500) · POP909(팝 909, MIT)
#   python data.py  → data/score_ai/songs.pkl
# 곡 = dict(src, title, key(0~11), minor, ts(박/마디), feel, tempo, kind('solo'|'head'|'chords'),
#           bars=[dict(chords=[(박위치, 근음, 종류)], notes=[(틱, 길이틱, 음)], sec='A'|'B'|…|None)])
# 틱 = 한 박을 12 로 (8분=6, 셋잇단=4, 16분=3)
import os, re, json, glob, pickle, sqlite3, zipfile, collections
import xml.etree.ElementTree as ET
import numpy as np

ROOT = "/home/drboom/project/car_bgm/data/score_ai"
TPB = 12
PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
# 코드 종류 (선율 쓰는 데 필요한 만큼만)
QUALS = ["maj", "maj7", "min", "m7", "dom", "alt", "sus", "hdim", "dim", "aug", "mM7"]
Q = {q: i for i, q in enumerate(QUALS)}


def root_pc(s):
    """'Bb', 'F#', 'C' 로 시작하는 문자열 → (음이름, 나머지)"""
    r = PC[s[0].upper()]
    i = 1
    while i < len(s) and s[i] in "#b":
        r += 1 if s[i] == "#" else -1
        i += 1
    return r % 12, s[i:]


def qual_of(q):
    """여러 표기('min7' '-7' 'j7' 'ø7' '79b' 'maj7' 'hdim7' …) → 종류 번호"""
    q = q.strip()
    if q.startswith(":"):
        q = q[1:]
    q = q.split("/")[0]
    if q in ("", "maj", "M", "6", "69", "maj6", "add9", "2", "5", "sus2", "(1,5)"):
        return Q["maj"]
    if q.startswith("ø") or "m7b5" in q or "min7b5" in q or q.startswith("hdim") or "-7b5" in q:
        return Q["hdim"]
    if q.startswith("o") or q.startswith("dim"):
        return Q["dim"]
    if q.startswith("+") or q.startswith("aug"):
        return Q["aug"]
    if "sus" in q:
        return Q["sus"]
    minor = q.startswith("min") or q.startswith("-") or (q.startswith("m") and not q.startswith("maj"))
    if minor:
        rest = q[3:] if q.startswith("min") else q[1:]
        if rest.startswith("maj") or rest.startswith("j") or "M7" in rest or rest.startswith("Δ"):
            return Q["mM7"]
        if any(x in rest for x in ("7", "9", "11", "13")):
            return Q["m7"]
        return Q["min"]
    if q.startswith("maj") or q.startswith("j") or q.startswith("M") or q.startswith("Δ"):
        return Q["maj7"] if any(x in q for x in ("7", "9", "13")) else Q["maj"]
    if q[:1] in ("7", "9") or q.startswith("13") or q.startswith("11") or q.startswith("alt"):
        if any(x in q for x in ("b9", "9b", "#9", "9#", "alt", "b13", "13b", "#5", "5#", "+", "b5")):
            return Q["alt"]
        return Q["dom"]
    return Q["maj"]


def chord_of(sym):
    """'Gmin7' 'Bb7' 'Aø7' 'C-7' 'Ebj7' 'NC' → (근음, 종류) 또는 None(코드 없음)"""
    if not sym or sym.strip().upper() in ("NC", "N", "N.C.", "X"):
        return None
    try:
        r, rest = root_pc(sym.strip())
    except (KeyError, IndexError):
        return None
    return r, qual_of(rest)


# ---------------- iRb (코드 진행만) ----------------
def load_irb():
    s = open(f"{ROOT}/irb/sharp11-irb/index.js", encoding="utf-8").read()
    d = json.loads(s[s.index("{"): s.rindex("}") + 1])
    out = []
    for c in d["charts"]:
        info = c["info"]
        ts = info.get("time", [4, 4])[0]
        if ts not in (3, 4):
            continue
        key, _ = root_pc(info["key"])
        bars, sec_prev = [], None
        for name in c["sections"]:
            sec = name[0] if name[0] in "ABCDE" else (sec_prev or "A")     # N1/N2 = 끝맺음 → 앞 단락 소속
            beat, cur = 0.0, None
            content = c["content"].get(name, [])
            for ch in content:
                b = ch["duration"]["beats"]
                cc = chord_of(ch["chord"])
                while beat >= ts - 1e-6 or cur is None:
                    cur = dict(chords=[], notes=[], sec=sec if (cur is None and name[0] in "ABCDE") else None)
                    bars.append(cur)
                    beat = beat - ts if beat >= ts - 1e-6 else beat
                if cc is not None and b > 0:
                    cur["chords"].append((beat, cc[0], cc[1]))
                beat += b
                while beat > ts + 1e-6:                    # 마디를 넘는 코드
                    beat -= ts
                    cur = dict(chords=[], notes=[], sec=None)
                    bars.append(cur)
            sec_prev = sec
        if len(bars) >= 4:
            out.append(dict(src="irb", title=info["title"], key=key, minor=bool(info.get("minor")), ts=ts,
                            feel="swing", tempo=None, kind="chords", bars=bars))
    return out


# ---------------- WJazzD (솔로 선율 + 코드) ----------------
def load_wjazzd():
    db = sqlite3.connect(f"{ROOT}/wjazzd/wjazzd.db")
    out = []
    for melid, title, perf, key, sig, feel, tempo, instr, style in db.execute(
            "select melid,title,performer,key,signature,rhythmfeel,avgtempo,instrument,style from solo_info"):
        if sig not in ("4/4", "3/4"):
            continue
        ts = int(sig[0])
        try:
            kp, rest = root_pc(key.split("-")[0])
            minor = "min" in key
        except (KeyError, IndexError, AttributeError):
            kp, minor = 0, False
        beats = db.execute("select bar,beat,chord from beats where melid=? order by onset", (melid,)).fetchall()
        mel = db.execute("select bar,beat,tatum,division,duration,beatdur,pitch from melody where melid=? order by onset", (melid,)).fetchall()
        if not mel:
            continue
        b0 = min(r[0] for r in mel if r[0] is not None)
        b1 = max(r[0] for r in mel if r[0] is not None)
        bars = {b: dict(chords=[], notes=[], sec=None) for b in range(b0, b1 + 1)}
        cur = None
        first_seen = set()
        for bar, beat, ch in beats:
            if ch:
                cur = chord_of(ch)
                if bar in bars and cur is not None:
                    bars[bar]["chords"].append((beat - 1.0, cur[0], cur[1]))
            if bar in bars and bar not in first_seen:          # 바뀌지 않고 이어지는 코드는 마디 첫 박에 다시 적음
                first_seen.add(bar)
                if not ch and cur is not None:
                    bars[bar]["chords"].insert(0, (0.0, cur[0], cur[1]))
        for bar, beat, tat, div, dur, bdur, p in mel:
            if bar is None or bar not in bars or not div:
                continue
            on = int(round(((beat - 1) + (tat - 1) / div) * TPB))
            d = max(1, int(round(dur / max(bdur, 0.05) * TPB)))
            if 0 <= on < ts * TPB:
                bars[bar]["notes"].append((on, d, int(p)))
        bl = [bars[b] for b in sorted(bars)]
        out.append(dict(src="wjazzd", title=f"{perf} - {title}", key=kp, minor=minor, ts=ts,
                        feel={"SWING": "swing", "LATIN": "latin", "FUNK": "straight", "TWOBEAT": "swing", "BALLAD": "swing"}.get(feel, "swing"),
                        tempo=tempo, kind="solo", instr=instr, bars=bl))
    return out


# ---------------- OpenEWLD (리드시트) ----------------
KIND = {"major": "maj", "minor": "min", "augmented": "aug", "diminished": "o", "dominant": "7", "major-seventh": "maj7",
        "minor-seventh": "m7", "diminished-seventh": "o7", "augmented-seventh": "+7", "half-diminished": "ø",
        "major-minor": "mmaj7", "major-sixth": "6", "minor-sixth": "m6", "dominant-ninth": "9", "major-ninth": "maj9",
        "minor-ninth": "m9", "dominant-11th": "11", "major-11th": "maj9", "minor-11th": "m11", "dominant-13th": "13",
        "major-13th": "maj9", "minor-13th": "m9", "suspended-second": "sus2", "suspended-fourth": "sus4", "power": "5",
        "Neapolitan": "maj", "Italian": "7", "French": "7", "German": "7", "Tristan": "ø", "pedal": "maj", "other": "maj"}
STEP_PC = PC


def load_ewld():
    out = []
    for path in glob.glob(f"{ROOT}/openewld/OpenEWLD/dataset/*/*/*.mxl"):
        try:
            with zipfile.ZipFile(path) as z:
                name = next(n for n in z.namelist() if n.endswith(".xml") and not n.startswith("META"))
                root = ET.fromstring(z.read(name))
        except Exception:
            continue
        part = root.find("part")
        if part is None:
            continue
        div, ts, key, minor = 1, 4, 0, False
        bars, tie_open = [], {}
        ok = True
        for meas in part.findall("measure"):
            a = meas.find("attributes")
            if a is not None:
                if a.find("divisions") is not None:
                    div = int(a.find("divisions").text)
                if a.find("time/beats") is not None:
                    try:
                        ts = int(a.find("time/beats").text)
                        if a.find("time/beat-type").text == "8":
                            ts = 0                                     # 6/8 등은 뺌
                    except ValueError:
                        ts = 0
                if a.find("key/fifths") is not None and not bars:
                    f = int(a.find("key/fifths").text)
                    minor = (a.find("key/mode") is not None and a.find("key/mode").text == "minor")
                    key = (f * 7 + (9 if minor else 0)) % 12
            if ts not in (3, 4):
                ok = False
                break
            bar = dict(chords=[], notes=[], sec=None)
            t = 0
            for el in meas:
                if el.tag == "harmony":
                    st = el.find("root/root-step")
                    if st is None:
                        continue
                    r = STEP_PC[st.text] + int(float(el.findtext("root/root-alter") or 0))
                    kind = el.find("kind")
                    kt = KIND.get(kind.text if kind is not None and kind.text else "major", "maj")
                    if kt in ("7", "9", "13", "11") and any((d.findtext("degree-alter") or "0") not in ("0", "") and d.findtext("degree-value") in ("9", "5", "13")
                                                           for d in el.findall("degree")):
                        kt = "7b9"
                    off = int(el.findtext("offset") or 0)
                    bar["chords"].append(((t + off) / div, r % 12, qual_of(kt)))
                elif el.tag == "note":
                    if el.find("grace") is not None or el.find("chord") is not None:
                        continue
                    if el.findtext("voice") not in (None, "1"):
                        d = int(el.findtext("duration") or 0)
                        continue
                    d = int(el.findtext("duration") or 0)
                    if el.find("rest") is None and el.find("pitch") is not None:
                        p = 12 * (int(el.findtext("pitch/octave")) + 1) + STEP_PC[el.findtext("pitch/step")] + int(float(el.findtext("pitch/alter") or 0))
                        ties = [x.get("type") for x in el.findall("tie")]
                        if "stop" in ties and p in tie_open:
                            nb, ni = tie_open[p]
                            on, dd, pp = bars[nb]["notes"][ni] if nb < len(bars) else bar["notes"][ni]
                            tgt = bars[nb]["notes"] if nb < len(bars) else bar["notes"]
                            tgt[ni] = (on, dd + int(round(d / div * TPB)), pp)
                            if "start" not in ties:
                                tie_open.pop(p)
                        else:
                            bar["notes"].append((int(round(t / div * TPB)), max(1, int(round(d / div * TPB))), p))
                            if "start" in ties:
                                tie_open[p] = (len(bars), len(bar["notes"]) - 1)
                    t += d
                elif el.tag == "backup":
                    t -= int(el.findtext("duration") or 0)
                elif el.tag == "forward":
                    t += int(el.findtext("duration") or 0)
            bars.append(bar)
        if not ok or len(bars) < 8 or sum(len(b["notes"]) for b in bars) < 20:
            continue
        # 코드가 없는 마디는 앞 코드 이어 받기
        cur = None
        for b in bars:
            if b["chords"]:
                cur = b["chords"][-1]
            elif cur is not None:
                b["chords"].append((0.0, cur[1], cur[2]))
        out.append(dict(src="ewld", title=os.path.basename(path)[:-4], key=key, minor=minor, ts=ts, feel="straight",
                        tempo=None, kind="head", bars=bars))
    return out


# ---------------- POP909 (팝 선율 + 코드) ----------------
def load_pop909():
    import mido
    out = []
    for d in sorted(glob.glob(f"{ROOT}/pop909/POP909-Dataset/POP909/[0-9][0-9][0-9]")):
        n = os.path.basename(d)
        try:
            beats = np.loadtxt(f"{d}/beat_midi.txt")
            chords = [l.split("\t") for l in open(f"{d}/chord_midi.txt").read().strip().splitlines()]
            keyl = open(f"{d}/key_audio.txt").read().split()
            mid = mido.MidiFile(f"{d}/{n}.mid")
        except Exception:
            continue
        bt = beats[:, 0]
        down = np.where(beats[:, 2] > 0.5)[0]
        if len(down) < 8:
            continue
        per = np.diff(down)
        ts = int(np.bincount(per).argmax())
        if ts not in (3, 4):
            continue
        # 초 → 박 (박 격자 따라 늘여 맞춤)
        def beat_of(t):
            i = np.searchsorted(bt, t) - 1
            i = min(max(i, 0), len(bt) - 2)
            return i + (t - bt[i]) / (bt[i + 1] - bt[i])
        first = down[0]
        sec_notes, on = [], {}
        # 틱 → 초 (템포는 0번 트랙)
        tempo_map = []
        t = 0
        for msg in mid.tracks[0]:
            t += msg.time
            if msg.type == "set_tempo":
                tempo_map.append((t, msg.tempo))
        if not tempo_map:
            tempo_map = [(0, 500000)]

        def tick2sec(tk):
            s, last_t, last_tempo = 0.0, 0, tempo_map[0][1]
            for tt, tp in tempo_map[1:]:
                if tt >= tk:
                    break
                s += (tt - last_t) / mid.ticks_per_beat * last_tempo / 1e6
                last_t, last_tempo = tt, tp
            return s + (tk - last_t) / mid.ticks_per_beat * last_tempo / 1e6
        mel = next((tr for tr in mid.tracks if tr.name == "MELODY"), None)
        if mel is None:
            continue
        t = 0
        for msg in mel:
            t += msg.time
            if msg.type == "note_on" and msg.velocity > 0:
                on[msg.note] = t
            elif msg.type in ("note_off", "note_on") and msg.note in on:
                a = on.pop(msg.note)
                sec_notes.append((tick2sec(a), tick2sec(t), msg.note))
        nb = (len(bt) - first) // ts
        bars = [dict(chords=[], notes=[], sec=None) for _ in range(nb)]
        for a, b, p in sec_notes:
            ba, bb = beat_of(a) - first, beat_of(b) - first
            k = int(ba // ts)
            if 0 <= k < nb:
                on_t = int(round((ba - k * ts) * TPB))
                if on_t >= ts * TPB:
                    k, on_t = k + 1, 0
                if k < nb:
                    bars[k]["notes"].append((on_t, max(1, int(round((bb - ba) * TPB))), p))
        for a, b, sym in chords:
            cc = chord_of(sym.replace(":", "")) if sym != "N" else None
            if cc is None:
                continue
            ba = beat_of(float(a)) - first
            k = int(ba // ts)
            if 0 <= k < nb:
                pos = round((ba - k * ts) * 2) / 2
                if pos >= ts:
                    continue
                bars[k]["chords"].append((pos, cc[0], cc[1]))
        cur = None
        for b in bars:
            b["chords"].sort()
            if b["chords"] and b["chords"][0][0] > 0 and cur is not None:
                b["chords"].insert(0, (0.0, cur[1], cur[2]))
            if b["chords"]:
                cur = b["chords"][-1]
            elif cur is not None:
                b["chords"].append((0.0, cur[1], cur[2]))
        # 앞뒤 빈 마디 자르기
        while bars and not bars[0]["notes"]:
            bars.pop(0)
        while bars and not bars[-1]["notes"]:
            bars.pop()
        try:
            kp, rest = root_pc(keyl[2].split(":")[0])
            minor = "min" in keyl[2]
        except Exception:
            kp, minor = 0, False
        bpm = 60 / float(np.median(np.diff(bt)))
        if len(bars) >= 8:
            out.append(dict(src="pop909", title=n, key=kp, minor=minor, ts=ts, feel="straight", tempo=bpm, kind="head", bars=bars))
    return out


# chord_of 가 Harte 표기('B:maj' → 'Bmaj', 'A:min7' → 'Amin7', 'G:hdim7')도 읽게 qual_of 에서 처리됨


if __name__ == "__main__":
    songs = []
    for name, f in (("iRb", load_irb), ("WJazzD", load_wjazzd), ("OpenEWLD", load_ewld), ("POP909", load_pop909)):
        xs = f()
        nb = sum(len(s["bars"]) for s in xs)
        nn = sum(len(b["notes"]) for s in xs for b in s["bars"])
        nc = sum(len(b["chords"]) for s in xs for b in s["bars"])
        qc = collections.Counter(QUALS[c[2]] for s in xs for b in s["bars"] for c in b["chords"])
        print(f"{name}: 곡 {len(xs)} · 마디 {nb} · 음 {nn} · 코드 {nc} · 박자 {collections.Counter(s['ts'] for s in xs)} · 종류 {dict(qc.most_common())}", flush=True)
        songs += xs
    pickle.dump(songs, open(f"{ROOT}/songs.pkl", "wb"))
    print("→", f"{ROOT}/songs.pkl", len(songs))
