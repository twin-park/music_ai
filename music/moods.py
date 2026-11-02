# 상황 → 움직일 파라미터 (HTML 플레이어 · 정리 문서 둘 다 여기서 읽음)
# 진행은 기준 조(장조=C, 단조=A)로 적고, 연주할 때 keys 중 하나로 옮긴다. 한 마디에 코드 1~2개.
# 칸: TEMPO 경계 60/70/80/90/100/110/120/135/150/170 · DENS(박당 시점) 0.75/1/1.25/1.5/1.75/2.1/3 · POLY 1.2/2.5/3.5/4.5 · REG 48/55/60/65/70

# 악기군 안에서 쓸 악기 번호 (재즈답지 않은 디스토션 기타·하모니카·피치카토 등은 뺌)
FAM_PROGS = {
    "jazz": {"piano": [0, 1, 4, 5], "chrom_perc": [11], "organ": [16, 17, 18], "guitar": [24, 25, 26, 27], "bass": [32, 33, 35],
             "strings": [40, 41, 42, 48, 49], "brass": [56, 57, 59, 61], "reed": [64, 65, 66, 67], "pipe": [73], "drums": [128]},
    "orch": {"piano": [0, 1], "chrom_perc": [8, 9, 14], "strings": [40, 41, 42, 43, 46, 47], "ensemble": [48, 49, 52],
             "brass": [56, 57, 58, 60, 61], "reed": [68, 70, 71], "pipe": [72, 73], "drums": [128]},
}

JAZZ = [
    dict(name="비 오는 날", emoji="🌧️", say=["느린 발라드", "단조", "브러시", "색소폰 한숨"],
         conds=["TS_4/4", "TEMPO_1", "MODE_minor", "DENS_2", "POLY_3", "REG_3", "VEL_1", "GENRE_jazz",
                "FAM_piano", "FAM_bass", "FAM_reed", "FAM_drums", "MOOD_relaxing", "MOOD_dark", "SWING_1"],
         bias={"reed": 1.3, "piano": 0.9, "drums": -0.5}, only={"reed": [66], "piano": [0, 1]}, kit="brush", vol=-2, mode="minor", keys=[9, 2, 7, 0],
         progs=["Am7 | Dm7 G7 | Cmaj7 | Fmaj7 | Bm7b5 | E7 | Am7 | E7",
                "Am7 | F7 | Bm7b5 E7 | Am7 | Dm7 | G7 | Cmaj7 | Bm7b5 E7",
                "Dm7 | G7 | Cmaj7 | Am7 | Dm7 | E7 | Am7 | Am7",
                "Am7 | Am7 | Dm7 | Dm7 | Fmaj7 | E7 | Am7 | E7"]),
    dict(name="평온한 재즈", emoji="☕", say=["느긋한 스윙", "장조", "따뜻한 화음", "재즈 기타 컴핑"],
         conds=["TS_4/4", "TEMPO_2", "MODE_major", "DENS_2", "POLY_3", "REG_3", "VEL_1", "GENRE_jazz",
                "FAM_piano", "FAM_guitar", "FAM_bass", "FAM_drums", "MOOD_relaxing", "MOOD_meditative", "MOOD_ballad", "SWING_1"],
         bias={"piano": 0.6, "guitar": -0.5, "drums": -1.3}, only={"guitar": [26], "piano": [0, 1]}, kit="brush", vol=-1, mode="major", keys=[5, 10, 3, 0],
         progs=["Cmaj7 | Am7 | Dm7 | G7 | Em7 | A7 | Dm7 G7 | Cmaj7",
                "Fmaj7 | Em7 | Dm7 | Cmaj7 | Bm7b5 E7 | Am7 | D7 | G7",
                "Cmaj7 | Cmaj7 | Fmaj7 | Fmaj7 | Em7 | A7 | Dm7 | G7",
                "Cmaj7 | Bm7b5 E7 | Am7 | Gm7 C7 | Fmaj7 | Fm7 Bb7 | Em7 A7 | Dm7 G7"]),
    dict(name="밤 드라이브", emoji="🌃", say=["쿨 재즈", "단조 모드", "로즈 피아노", "뮤트 트럼펫", "곧은 8분"],
         conds=["TS_4/4", "TEMPO_4", "MODE_minor", "DENS_3", "POLY_3", "REG_3", "VEL_1", "GENRE_jazz",
                "FAM_piano", "FAM_guitar", "FAM_bass", "FAM_brass", "FAM_drums", "MOOD_dark", "MOOD_space", "SWING_0"],
         bias={"piano": 0.3, "brass": 0.7, "guitar": -0.6, "drums": -0.4}, only={"piano": [4, 5], "brass": [59], "guitar": [26]}, kit="jazz", vol=0, mode="minor", keys=[2, 9, 4],
         progs=["Am7 | Am7 | D7 | D7 | Am7 | Am7 | Fmaj7 | E7",
                "Am7 | Bm7 | Cmaj7 | Bm7 | Am7 | G7 | Fmaj7 | E7",
                "Am7 | D7 | Am7 | D7 | Fmaj7 | E7 | Am7 | Am7"]),
    dict(name="즐거운 대화", emoji="😄", say=["빠른 스윙", "밝은 장조", "비브라폰·알토 주고받기", "워킹 베이스"],
         conds=["TS_4/4", "TEMPO_8", "MODE_major", "DENS_3", "POLY_3", "REG_3", "VEL_2", "GENRE_jazz",
                "FAM_piano", "FAM_chrom_perc", "FAM_reed", "FAM_bass", "FAM_drums", "MOOD_happy", "MOOD_energetic", "SWING_2"],
         bias={"chrom_perc": 0.5, "reed": 0.4, "piano": 0.3, "drums": -0.5}, only={"reed": [65]}, kit="jazz", vol=0, mode="major", keys=[10, 3, 5, 0],
         progs=["Cmaj7 A7 | Dm7 G7 | Cmaj7 A7 | Dm7 G7 | Gm7 C7 | Fmaj7 Bb7 | Em7 A7 | Dm7 G7",
                "Cmaj7 | Dm7 G7 | Em7 A7 | Dm7 G7 | Cmaj7 | Fm7 Bb7 | Em7 A7 | Dm7 G7",
                "C7 | F7 | C7 | C7 | F7 | F7 | C7 | A7 | Dm7 | G7 | C7 A7 | Dm7 G7"]),
    dict(name="바닷가 보사노바", emoji="🌊", say=["보사노바", "나일론 기타", "플루트", "곧은 8분"],
         conds=["TS_4/4", "TEMPO_7", "MODE_major", "DENS_4", "POLY_3", "REG_3", "VEL_1", "GENRE_jazz", "GENRE_latin",
                "FAM_guitar", "FAM_bass", "FAM_pipe", "FAM_drums", "MOOD_relaxing", "MOOD_happy", "SWING_0"],
         bias={"pipe": 1.2, "guitar": 0.3, "drums": -0.9}, only={"guitar": [24]}, kit="latin", vol=0, mode="major", keys=[2, 7, 0, 5],
         progs=["Cmaj7 | Cmaj7 | D7 | D7 | Dm7 | G7 | Cmaj7 | G7",
                "Fmaj7 | Fm7 | Em7 | A7 | Dm7 | G7 | Cmaj7 | G7",
                "Cmaj7 | Bm7b5 E7 | Am7 | D7 | Dm7 | G7 | Cmaj7 | Cmaj7"]),
    dict(name="아이 재우기", emoji="🍼", say=["피아노 혼자", "느리게 흐르는 펼친화음", "여린 소리"],
         conds=["TS_4/4", "TEMPO_1", "MODE_major", "DENS_2", "POLY_1", "REG_3", "VEL_0", "GENRE_jazz",
                "FAM_piano", "MOOD_relaxing", "MOOD_love", "MOOD_ballad", "MOOD_slow", "SWING_1"],
         bias={}, only={"piano": [0]}, temp=0.85, kit=None, vol=-8, mode="major", keys=[5, 0, 7],
         progs=["Cmaj7 | Fmaj7 | Em7 | Am7 | Dm7 | G7 | Cmaj7 | G7",
                "Fmaj7 | Em7 | Dm7 | Cmaj7 | Fmaj7 | Em7 A7 | Dm7 | G7"]),
    dict(name="진정", emoji="🫖", say=["피아노와 베이스", "드럼 없음", "낮은 음역"],
         conds=["TS_4/4", "TEMPO_1", "MODE_major", "DENS_2", "POLY_3", "REG_2", "VEL_0", "GENRE_jazz",
                "FAM_piano", "FAM_bass", "MOOD_meditative", "MOOD_relaxing", "MOOD_ballad", "SWING_1"],
         bias={"piano": 0.5}, temp=0.8, kit=None, vol=-4, mode="major", keys=[10, 3, 8],
         progs=["Cmaj7 | Cmaj7 | Fmaj7 | Fmaj7 | Em7 | Am7 | Dm7 | G7",
                "Cmaj7 | Em7 | Fmaj7 | G7 | Am7 | Dm7 | Fm7 | G7"]),
    dict(name="위로", emoji="🤍", say=["발라드", "현악 살짝", "브러시"],
         conds=["TS_4/4", "TEMPO_1", "MODE_major", "DENS_2", "POLY_3", "REG_3", "VEL_1", "GENRE_jazz",
                "FAM_piano", "FAM_strings", "FAM_bass", "FAM_drums", "MOOD_emotional", "MOOD_love", "SWING_1"],
         bias={"strings": 1.6, "piano": 0.3, "drums": -1.2}, only={"strings": [48, 49], "piano": [0, 1]}, kit="brush", vol=-3, mode="major", keys=[3, 8, 0],
         progs=["Cmaj7 | Em7 A7 | Dm7 | Fm7 Bb7 | Em7 | A7 | Dm7 | G7",
                "Fmaj7 | Em7 | Am7 | Dm7 G7 | Cmaj7 | Am7 | Dm7 | G7"]),
    dict(name="낮 드라이브", emoji="🚗", say=["소울 재즈 그루브", "오르간", "테너 색소폰", "경쾌한 박"],
         conds=["TS_4/4", "TEMPO_6", "MODE_major", "DENS_4", "POLY_3", "REG_3", "VEL_2", "GENRE_jazz",
                "FAM_piano", "FAM_organ", "FAM_guitar", "FAM_bass", "FAM_reed", "FAM_drums", "MOOD_happy", "MOOD_energetic", "SWING_1"],
         bias={"organ": 0.7, "reed": 0.6, "guitar": -0.7, "drums": -0.3}, only={"reed": [66]}, kit="jazz", vol=0, mode="major", keys=[7, 0, 5],
         progs=["C7 | C7 | F7 | F7 | C7 | A7 | Dm7 | G7",
                "Cmaj7 | Am7 | Dm7 | G7 | Cmaj7 | Am7 | Fmaj7 | G7"]),
]

ORCH = [
    dict(name="아이 재우기", emoji="🍼", say=["자장가", "피아노 펼친화음", "하프·첼로 살짝", "느린 3박"],
         conds=["TS_3/4", "TEMPO_1", "MODE_major", "DENS_1", "POLY_2", "REG_3", "VEL_1", "GENRE_classical", "FAM_piano",
                "FAM_strings", "MOOD_relaxing", "MOOD_love"], bias={"piano": 0.3}, only={"strings": [46, 42]}, kit=None, vol=-8, mode="major", keys=[5, 0, 7],
         progs=["C | Am | F | G | C | F | Dm G | C", "F | C/E | Dm | G | Am | F | G | C"]),
    dict(name="진정", emoji="🫖", say=["현악 합주", "느리게", "따뜻한 장조"],
         conds=["TS_4/4", "TEMPO_2", "MODE_major", "DENS_2", "POLY_3", "REG_2", "VEL_1", "GENRE_classical", "FAM_strings",
                "FAM_ensemble", "MOOD_meditative", "MOOD_relaxing"], bias={"strings": 0.5}, kit=None, vol=-4, mode="major", keys=[2, 7, 0],
         progs=["C | G/B | Am | Em/G | F | C/E | Dm7 | Gsus G", "Am | Em | F | C | Dm | Am/C | F | G"]),
    dict(name="위로", emoji="🤍", say=["피아노와 현악", "잔잔하게"],
         conds=["TS_4/4", "TEMPO_2", "MODE_major", "DENS_2", "POLY_3", "REG_3", "VEL_1", "GENRE_classical", "FAM_piano",
                "FAM_strings", "MOOD_emotional", "MOOD_film", "MOOD_ballad"], only={"strings": [40, 42]}, kit=None, vol=-3, mode="major", keys=[0, 5, 10],
         progs=["C | Em | Am | F | Dm | G | C | G", "F | G | Em | Am | Dm | G | C | C"]),
    dict(name="비 오는 길", emoji="🌧️", say=["녹턴", "단조", "흐르는 왼손", "첼로 대선율"],
         conds=["TS_4/4", "TEMPO_2", "MODE_minor", "DENS_3", "POLY_2", "REG_3", "VEL_1", "GENRE_classical", "FAM_piano",
                "FAM_strings", "MOOD_dark", "MOOD_emotional"], bias={"piano": 0.4}, only={"strings": [42, 40]}, kit=None, vol=-2, mode="minor", keys=[9, 4, 2],
         progs=["Am | F | Dm | E7 | Am | C | Dm E7 | Am", "Am | G | F | E7 | Dm | Am | Bm7b5 E7 | Am"]),
    dict(name="바닷가", emoji="🌊", say=["탁 트인", "하프와 플루트", "밝게"],
         conds=["TS_4/4", "TEMPO_4", "MODE_major", "DENS_4", "POLY_2", "REG_4", "VEL_1", "GENRE_soundtrack", "FAM_strings",
                "FAM_pipe", "FAM_piano", "MOOD_inspiring", "MOOD_happy", "MOOD_melodic"], bias={"pipe": 0.8, "strings": 1.6, "piano": -0.8},
         only={"strings": [46, 40]}, kit=None, vol=0, mode="major", keys=[2, 9, 4],
         progs=["C | G | Am | F | C | G | F | G", "F | C | G | Am | F | C | Dm | G"]),
    dict(name="즐거운 대화", emoji="😄", say=["밝은 오케스트라", "빠르게"],
         conds=["TS_4/4", "TEMPO_7", "MODE_major", "DENS_5", "POLY_3", "REG_3", "VEL_2", "GENRE_soundtrack", "FAM_strings",
                "FAM_brass", "FAM_reed", "FAM_piano", "MOOD_happy", "MOOD_positive"], bias={"reed": 0.5, "brass": 0.3, "strings": 0.3, "piano": 0.5}, kit=None, vol=0, mode="major", keys=[7, 2, 0],
         progs=["C | F | G | C | Am | Dm | G7 | C", "C | G | Am | Em | F | C | Dm7 G7 | C"]),
    dict(name="드라이브", emoji="🚗", say=["영화 음악", "웅장하게", "현악·금관"],
         conds=["TS_4/4", "TEMPO_6", "MODE_minor", "DENS_4", "POLY_3", "REG_3", "VEL_2", "GENRE_soundtrack", "FAM_strings",
                "FAM_ensemble", "FAM_brass", "FAM_drums", "MOOD_epic", "MOOD_film"],
         bias={"ensemble": 0.5, "brass": 0.7, "strings": 0.2}, only={"ensemble": [48, 49], "strings": [40, 42, 47]}, kit="orch", vol=0, mode="minor", keys=[2, 9, 7],
         progs=["Am | F | C | G | Am | F | G | E7", "Am | Am | F | F | C | G | F | E7"]),
]

# 조건 낱말은 학습 때 순서(=낱말 번호 순)로 정렬 — 플레이어도 이 순서로 넣으므로 시험·연주가 같아짐
from tokens import TOK as _TOK
for _m in JAZZ + ORCH:
    _m["conds"] = sorted(_m["conds"], key=lambda c: _TOK[c])

# 자동 탐색(web/search_moods.js → web/apply_best.py)으로 고른 조건·창의성 덮어쓰기
import json as _json, os as _os
_T = _os.path.join(_os.path.dirname(__file__), "moods_tuned.json")
if _os.path.exists(_T):
    _tuned = _json.load(open(_T, encoding="utf-8"))
    for _v, _M in (("jazz", JAZZ), ("orch", ORCH)):
        for _m in _M:
            _b = _tuned.get(_v, {}).get(_m["name"])
            if _b:
                _m["conds"] = _b["conds"]
                if _b.get("temp"): _m["temp"] = _b["temp"]
                _m["tuned"] = _b["tag"]
