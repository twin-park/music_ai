# search_moods.js 결과(test/best_<v>_*.json) → music/moods_tuned.json (moods.py 가 마지막에 덮어 씀)
# 지금 설정보다 점수가 0.02 이상 좋을 때만 바꿈
import json, glob, os
R = "/home/drboom/project/car_bgm"
out = {}
for v in ("jazz", "orch"):
    out[v] = {}
    for f in sorted(glob.glob(f"{R}/web/test/best_{v}_*.json")):
        for name, b in json.load(open(f)).items():
            if b["tag"] != "지금" and b["score"] - b["base"] >= 0.02:
                out[v][name] = {"tag": b["tag"], "conds": b["conds"], "temp": b.get("temp"), "gain": round(b["score"] - b["base"], 3)}
json.dump(out, open(f"{R}/music/moods_tuned.json", "w"), ensure_ascii=False, indent=1)
for v in out:
    for n, b in out[v].items(): print(v, n, b["tag"], f"+{b['gain']}")
