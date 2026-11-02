# 귀(ear) 모델이 알아듣는 소리 묶음과 한국어 단어.
# FSD50K 200개 이름을 차 안에서 쓸모 있는 묶음으로 모았다. 한 클립에 여러 묶음이 함께 켜질 수 있다.

GROUPS = [
    # id, FSD50K 이름들, 단어
    ("speech",    ["Speech", "Male_speech_and_man_speaking", "Female_speech_and_woman_speaking",
                   "Conversation", "Chatter", "Child_speech_and_kid_speaking"], ["대화"]),
    ("child",     ["Child_speech_and_kid_speaking"], ["아이 목소리"]),
    ("baby_cry",  [], ["아기 울음"]),            # Crying_and_sobbing 중 제목·태그에 baby 가 있는 것 (build_data 에서)
    ("crying",    ["Crying_and_sobbing"], ["울음"]),
    ("laughter",  ["Laughter", "Giggle", "Chuckle_and_chortle"], ["웃음"]),
    ("shout",     ["Shout", "Yell", "Screaming"], ["고함"]),
    ("whisper",   ["Whispering"], ["속삭임"]),
    ("singing",   ["Singing", "Male_singing", "Female_singing"], ["노래"]),
    ("breathing", ["Breathing", "Sigh"], ["숨소리"]),
    ("cough",     ["Cough", "Sneeze"], ["기침"]),
    ("music",     ["Music", "Musical_instrument"], ["음악"]),
    ("phone",     ["Telephone", "Ringtone"], ["전화벨"]),
    ("sea",       ["Ocean", "Waves_and_surf"], ["바다", "파도"]),
    ("gull",      ["Gull_and_seagull"], ["갈매기"]),
    ("bird",      ["Bird", "Bird_vocalization_and_bird_call_and_bird_song", "Chirp_and_tweet", "Crow"], ["새소리"]),
    ("insect",    ["Insect", "Cricket"], ["풀벌레"]),
    ("rain",      ["Rain", "Raindrop"], ["비"]),
    ("thunder",   ["Thunder", "Thunderstorm"], ["천둥"]),
    ("wind",      ["Wind"], ["바람"]),
    ("water",     ["Stream", "Water", "Trickle_and_dribble"], ["물소리"]),
    ("traffic",   ["Traffic_noise_and_roadway_noise", "Car", "Motor_vehicle_(road)", "Vehicle", "Engine",
                   "Idling", "Truck", "Bus", "Car_passing_by", "Accelerating_and_revving_and_vroom"], ["도로"]),
    ("horn",      ["Vehicle_horn_and_car_horn_and_honking"], ["경적"]),
    ("siren",     ["Siren"], ["사이렌"]),
    ("train",     ["Train", "Rail_transport", "Subway_and_metro_and_underground"], ["기차"]),
    ("dog",       ["Dog", "Bark"], ["강아지"]),
    ("crowd",     ["Crowd", "Cheering", "Applause", "Clapping"], ["사람들", "환호"]),
    ("bang",      ["Slam", "Knock", "Thump_and_thud", "Boom", "Explosion", "Gunshot_and_gunfire", "Crash_cymbal"],
                  ["쾅 소리"]),
    ("fireworks", ["Fireworks"], ["불꽃놀이"]),
]
GROUP_IDS = [g[0] for g in GROUPS]
N_GROUPS = len(GROUPS)
BABY_WORDS = ("baby", "infant", "newborn", "toddler", "bebe", "bébé", "neonat")

# CREMA-D 감정 (영어 배우 6명 x 91 연기) — 말투 머리
EMOTIONS = ["anger", "disgust", "fear", "happy", "neutral", "sad"]
EMOTION_WORDS = {
    "anger":   ["화난", "열이 난"],
    "disgust": ["짜증난"],
    "fear":    ["불안한"],
    "happy":   ["밝은", "신난"],
    "neutral": ["차분한"],
    "sad":     ["가라앉은", "슬픈"],
}


def fsd_to_groups(labels, text=""):
    """FSD50K 이름 목록 → 묶음 multi-hot (list of 0/1)."""
    s = set(labels)
    y = [0] * N_GROUPS
    for i, (gid, names, _) in enumerate(GROUPS):
        if s.intersection(names):
            y[i] = 1
    t = text.lower()
    if "Crying_and_sobbing" in s and any(w in t for w in BABY_WORDS):
        y[GROUP_IDS.index("baby_cry")] = 1
    return y
