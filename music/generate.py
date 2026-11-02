# 조건 → 악보 생성 → MIDI → wav/mp3
# 문법 상태기계로 다음에 올 수 있는 낱말만 남기고 뽑는다 (깨진 악보가 나올 수 없음).
import os, sys, subprocess, math
import numpy as np, torch
import mido
sys.path.insert(0, os.path.dirname(__file__))
from tokens import (V, TOK, VOCAB, BOS, EOS, SEP, BAR, POS0, PROG0, NV0, P0, D0, Q, MAX_BAR, FAMILIES,
                    DURS, decode, family)
from model import MusicLM

TOOLS = "/home/drboom/miniconda3/envs/car_bgm_tools/bin"
SF2 = "/home/drboom/project/car_bgm/data/sf/MuseScore_General.sf2"
N_PROG, N_NV, N_P, N_D = 129, 8, 128, len(DURS)


def load(path, dev="cuda"):
    ck = torch.load(path, map_location=dev)
    m = MusicLM(**ck["cfg"]).to(dev).eval()
    m.load_state_dict(ck["model"])
    return m


def kind(i):
    if i >= D0: return "D"
    if i >= P0: return "P"
    if i >= NV0: return "NV"
    if i >= PROG0: return "PROG"
    if i >= POS0: return "POS"
    return V[i]


KIND = [kind(i) for i in range(VOCAB)]


class Grammar:
    """마지막 낱말을 보고 다음 허용 낱말 마스크를 고른다. 마스크는 처음에 다 만들어 둔다."""

    def __init__(self, bar_len, progs=None, dev="cuda"):
        self.pos = -1
        z = lambda: torch.zeros(VOCAB, dtype=torch.bool)
        rng = lambda lo, n: (lambda m: (m.__setitem__(slice(lo, lo + n), True), m)[1])(z())
        prog = rng(PROG0, N_PROG)
        if progs is not None:       # 허용 악기만
            prog = z()
            for p in progs: prog[PROG0 + p] = True
        after_d = rng(P0, N_P) | prog
        after_d[BAR] = after_d[EOS] = True
        endbar = z(); endbar[BAR] = endbar[EOS] = True
        # 마디 안 현재 위치 p 다음에 올 수 있는 POS (p+1 ~ 마디 끝)
        posm = torch.zeros(MAX_BAR + 1, VOCAB, dtype=torch.bool)
        for p in range(-1, MAX_BAR):
            posm[p + 1, POS0 + p + 1: POS0 + bar_len] = True
        sep = z(); sep[BAR] = True
        self.m_sep, self.m_prog, self.m_nv = sep.to(dev), prog.to(dev), rng(NV0, N_NV).to(dev)
        self.m_p, self.m_d = rng(P0, N_P).to(dev), rng(D0, N_D).to(dev)
        self.m_bar = (posm[0] | endbar).to(dev)                  # BAR 다음
        self.m_afterd = (posm | after_d).to(dev)                  # (p+1, VOCAB): 음 다음

    def allowed(self, last):
        k = KIND[last]
        if last == SEP:
            return self.m_sep
        if last == BAR:
            self.pos = -1; return self.m_bar
        if k == "POS":
            self.pos = last - POS0; return self.m_prog
        if k == "PROG":
            return self.m_nv
        if k == "NV":
            return self.m_p
        if k == "P":
            return self.m_d
        if k == "D":
            return self.m_afterd[self.pos + 1]
        return torch.ones_like(self.m_sep)


FAM_PROGS = {f: ([128] if f == "drums" else list(range(i * 8, i * 8 + 8))) for i, f in enumerate(FAMILIES)}


def fam_progs(conds):
    """조건의 FAM_ 들 → 허용 악기 번호. 없으면 None(제한 없음)."""
    fs = [c[4:] for c in conds if c.startswith("FAM_")]
    return sorted({p for f in fs for p in FAM_PROGS[f]}) if fs else None


def bar_len_of(conds):
    for c in conds:
        if c.startswith("TS_") and c != "TS_other":
            a, b = map(int, c[3:].split("/")); return a * 4 * Q // b
    return 48


@torch.no_grad()
def generate(model, conds, n_bars=16, prompt=None, temp=1.0, top_p=0.95, progs=None, seed=None, max_tokens=None):
    """conds: 조건 낱말 목록, prompt: 이어 쓸 앞 마디 낱말(BAR 부터). → 새로 만든 낱말(BAR 부터)."""
    dev = next(model.parameters()).device
    g = torch.Generator(device=dev)
    if seed is not None: g.manual_seed(seed)
    pre = [BOS] + [TOK[c] for c in conds] + [SEP] + (prompt or [])
    ctx = model.cfg["ctx"]
    gram = Grammar(bar_len_of(conds), progs, dev)
    for t in pre[len([BOS] + conds) + 1:]:
        gram.allowed(t)                         # 상태만 맞춰 둠
    caches = [{"max": ctx * 2} for _ in model.layers]
    x = torch.tensor([pre], device=dev)
    logits = model(x, caches)[0, -1]
    out, bars, last = [], 0, pre[-1]
    budget = max_tokens or (ctx - len(pre))
    for _ in range(budget):
        m = gram.allowed(last)
        lg = logits.float() / temp
        lg[~m] = -float("inf")
        p = torch.softmax(lg, -1)
        sp, si = p.sort(descending=True)
        cut = (sp.cumsum(0) - sp) > top_p
        sp[cut] = 0
        nxt = int(si[torch.multinomial(sp / sp.sum(), 1, generator=g)])
        if nxt == EOS:
            break
        if nxt == BAR:
            bars += 1
            if bars > n_bars:
                break
        out.append(nxt); last = nxt
        pos = len(pre) + len(out) - 1
        if pos >= ctx * 2 - 1:
            break
        logits = model(torch.tensor([[nxt]], device=dev), caches, pos=pos)[0, -1]
    return out


def invalid_mass(model, seq):
    """문법 막기 없이 모델이 문법 밖 낱말에 준 확률 평균 (모델이 문법을 얼마나 배웠나)."""
    dev = next(model.parameters()).device
    x = torch.tensor([seq], device=dev)
    with torch.no_grad():
        p = torch.softmax(model(x)[0].float(), -1)
    conds = [V[i] for i in seq[1:seq.index(SEP)]]
    gram = Grammar(bar_len_of(conds), None, dev)
    tot, n = 0.0, 0
    for k in range(seq.index(SEP), len(seq) - 1):
        m = gram.allowed(seq[k])
        tot += float(p[k][~m].sum()); n += 1
    return tot / max(1, n)


def to_midi(notes, qpm, path):
    mid = mido.MidiFile(ticks_per_beat=480)
    k = 480 // Q
    tr0 = mido.MidiTrack(); mid.tracks.append(tr0)
    tr0.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(qpm), time=0))
    progs = sorted({n[1] for n in notes})
    ch, c = {}, 0
    for p in progs:
        if p == 128: ch[p] = 9
        else:
            if c == 9: c += 1
            ch[p] = min(c, 15); c += 1
    for p in progs:
        tr = mido.MidiTrack(); mid.tracks.append(tr)
        if p != 128:
            tr.append(mido.Message("program_change", channel=ch[p], program=p, time=0))
        ev = []
        for t, pr, pi, d, v in notes:
            if pr != p: continue
            ev.append((t * k, 1, pi, v)); ev.append(((t + d) * k - 1, 0, pi, 0))
        ev.sort(key=lambda e: (e[0], e[1]))
        now = 0
        for t, on, pi, v in ev:
            tr.append(mido.Message("note_on" if on else "note_off", channel=ch[p], note=pi, velocity=v if on else 0,
                                   time=max(0, t - now)))
            now = max(now, t)
    mid.save(path)


def render(midi, wav, mp3=None, gain=0.5):
    subprocess.run([f"{TOOLS}/fluidsynth", "-ni", "-g", str(gain), "-r", "44100", "-F", wav, SF2, midi],
                   check=True, capture_output=True)
    if mp3:
        subprocess.run([f"{TOOLS}/ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-af", "loudnorm=I=-18:TP=-1.5",
                        "-ar", "44100", "-b:a", "192k", mp3], check=True)


def qpm_of(conds):
    from tokens import TEMPO_EDGES
    for c in conds:
        if c.startswith("TEMPO_"):
            i = int(c[6:]); e = [40] + TEMPO_EDGES + [190]
            return (e[i] + e[i + 1]) / 2
    return 100.0
