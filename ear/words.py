# 귀 모델 출력 + 말투 숫자 → 한국어 단어
from labels import GROUPS, GROUP_IDS, EMOTIONS, EMOTION_WORDS

VOCAL = {"speech", "child", "baby_cry", "crying", "laughter", "shout", "whisper", "singing"}


def to_words(clip, th, emo, pros):
    """clip: 묶음 확률(list), th: 묶음별 문턱(dict), emo: 감정 확률(list), pros: features.prosody 결과.
    반환: [(단어, 점수, 종류)] 점수 높은 순."""
    out = {}

    def add(w, s, kind):
        if w not in out or out[w][0] < s:
            out[w] = (round(float(s), 3), kind)

    on = {g: clip[i] for i, g in enumerate(GROUP_IDS) if clip[i] >= th.get(g, 0.5)}
    if "baby_cry" in on:
        on.pop("crying", None)
    if len([g for g in on if g in VOCAL]) > 1:
        on.pop("speech", None)          # 더 구체적인 목소리 단어가 있으면 '대화'는 뺀다
    for g, p in on.items():
        for w in GROUPS[GROUP_IDS.index(g)][2]:
            add(w, p, "소리")

    sp = clip[GROUP_IDS.index("speech")]
    talking = sp >= th.get("speech", 0.5) or "shout" in on
    if talking:
        k = max(range(len(emo)), key=lambda i: emo[i])
        if emo[k] >= 0.4:
            for w in EMOTION_WORDS[EMOTIONS[k]]:
                add(w, emo[k] * sp, "감정")
        # 말투 숫자 (마이크마다 기준이 달라 대략값)
        # 기준: CREMA 시험 화자 실측 — 화남 3.6, 보통 2.6, 슬픔 2.1 (초당 음절 봉우리)
        if pros["rate"] >= 3.8:
            add("템포 빠른", min(1, pros["rate"] / 5), "말투")
        elif 0 < pros["rate"] <= 1.9:
            add("템포 느린", 0.6, "말투")
        if pros["pitch_var"] >= 4.0 and pros["loud_var"] >= 8:
            add("격한", min(1, pros["pitch_var"] / 6), "말투")
    if pros["loud_db"] >= -12:
        add("시끄러운", 0.7, "말투")
    elif pros["loud_db"] <= -42:
        add("조용한", 0.7, "말투")
    if not on and pros["loud_db"] <= -42:
        add("고요한", 0.8, "소리")
    return sorted(((w, s, k) for w, (s, k) in out.items()), key=lambda t: -t[1])
