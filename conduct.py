# 지휘: 귀가 뽑은 단어 → 상황 → 음악 지시(조건 낱말 + 사람이 읽는 지시 단어 + 볼륨)
# 감지한 감정을 따라가지 않고 '음악이 해야 할 일'로 바꾼다. 예) 화난 → 느리고 부드럽게.

# 상황: (이 단어들 중 하나라도 있으면, 조건 낱말, 지시 단어, 볼륨 dB)
# DENS = 박당 소리 나는 시점 수 칸(0.75/1/1.25/1.5/1.75/2.1/3), POLY = 동시음 칸(1.2/2.5/3.5/4.5) — PDMX 분위수 기준
SITUATIONS = [
    ("아이 재우기", {"아기 울음", "속삭임", "숨소리"},
     ["TS_3/4", "TEMPO_1", "MODE_major", "DENS_1", "POLY_2", "REG_3", "VEL_1", "GENRE_classical", "FAM_piano"],
     ["느린 템포", "부드러운 피아노", "작은 소리", "단순한 반주"], -8),
    ("진정", {"화난", "열이 난", "고함", "격한", "짜증난"},
     ["TS_4/4", "TEMPO_2", "MODE_major", "DENS_2", "POLY_3", "REG_2", "VEL_1", "GENRE_classical", "FAM_piano", "FAM_strings"],
     ["느린 템포", "부드러운 현악", "낮은 음역", "따뜻한 장조"], -4),
    ("위로", {"슬픈", "가라앉은", "울음", "불안한"},
     ["TS_4/4", "TEMPO_2", "MODE_major", "DENS_2", "POLY_3", "REG_3", "VEL_1", "GENRE_classical", "FAM_piano"],
     ["잔잔한", "따뜻한 피아노"], -3),
    ("즐거운 대화", {"웃음", "신난", "밝은", "노래", "환호"},
     ["TS_4/4", "TEMPO_7", "MODE_major", "DENS_6", "POLY_3", "REG_3", "VEL_2", "GENRE_pop", "FAM_piano", "FAM_bass", "FAM_drums"],
     ["빠른 템포", "밝은 장조", "리듬 악기"], 0),
    ("바닷가", {"바다", "파도", "갈매기"},
     ["TS_4/4", "TEMPO_4", "MODE_major", "DENS_4", "POLY_2", "REG_4", "VEL_1", "GENRE_soundtrack", "FAM_piano", "FAM_strings"],
     ["탁 트인", "밝은 피아노와 현악", "중간 템포"], 0),
    ("비 오는 길", {"비", "천둥"},
     ["TS_4/4", "TEMPO_2", "MODE_minor", "DENS_2", "POLY_2", "REG_3", "VEL_1", "GENRE_classical", "FAM_piano"],
     ["단조", "잔잔한 피아노", "느린 템포"], -2),
    ("자연 속", {"새소리", "풀벌레", "바람", "물소리"},
     ["TS_3/4", "TEMPO_3", "MODE_major", "DENS_3", "POLY_2", "REG_4", "VEL_1", "GENRE_classical", "FAM_piano", "FAM_pipe"],
     ["자연스러운", "플루트와 피아노"], 0),
    ("드라이브", {"도로", "경적", "기차"},
     ["TS_4/4", "TEMPO_6", "MODE_major", "DENS_5", "POLY_3", "REG_3", "VEL_2", "GENRE_pop", "FAM_piano", "FAM_bass", "FAM_drums"],
     ["경쾌한", "중간 빠르기"], 0),
]
DEFAULT = ("기본", set(), ["TS_4/4", "TEMPO_4", "MODE_major", "DENS_4", "POLY_3", "REG_3", "VEL_1", "FAM_piano"],
           ["편안한 피아노"], 0)


def conduct(words):
    """words: [(단어, 점수, 종류)] 또는 단어 목록 → dict"""
    ws = {w[0] if isinstance(w, (tuple, list)) else w for w in words}
    name, _, conds, say, vol = next((s for s in SITUATIONS if s[1] & ws), DEFAULT)
    conds, say = list(conds), list(say)
    if name not in ("바닷가",) and ws & {"바다", "파도", "갈매기"} and "FAM_strings" not in conds:
        conds.append("FAM_strings"); say.append("바다 느낌 현악 조금")
    actions = []
    if "전화벨" in ws:
        actions.append("통화 — 음악 크게 낮춤"); vol = min(vol, -20)
    if "갈매기" in ws and name == "아이 재우기":
        say.append("갈매기·효과음 빼기")
    return {"상황": name, "조건": conds, "지시": say, "볼륨dB": vol, "동작": actions}
