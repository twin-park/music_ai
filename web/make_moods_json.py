# moods.py → web/test/moods_{jazz,orch}.json (test_chords.js 가 읽음). moods.py 를 고치면 다시 돌릴 것.
import sys, json
sys.path += ["/home/drboom/project/car_bgm/music"]
from moods import JAZZ, ORCH, FAM_PROGS
for v, M in (("jazz", JAZZ), ("orch", ORCH)):
    json.dump({"moods": M, "fp": FAM_PROGS[v]}, open(f"/home/drboom/project/car_bgm/web/test/moods_{v}.json", "w"), ensure_ascii=False)
    print(v, len(M))
