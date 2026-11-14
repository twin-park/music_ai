# 에뮬레이터 주행 경로: 감포 내륙 → 감포항 → 해안 따라 북쪽 (바닷가로 들어가는 순간을 보여 줌)
#   python3 -I android/tools/make_route.py <music_android/app/src/main/assets/geo/coast_kr.bin> android/pc/routes  → gampo_coast.csv (1초마다 위도,경도 · 70km/h) · gampo_coast.gpx
import math, struct, sys, datetime
coast_bin, out = sys.argv[1], sys.argv[2]
b = open(coast_bin, "rb").read(); n, = struct.unpack_from("<i", b, 0); o = 4; L = []
for _ in range(n):
    k, = struct.unpack_from("<i", b, o); o += 4
    L.append([struct.unpack_from("<ff", b, o + 8 * i) for i in range(k)]); o += 8 * k
def dist(lat, lon):
    c = math.cos(math.radians(lat)); best = 1e9
    for ln in L:
        for (a1, o1), (a2, o2) in zip(ln, ln[1:]):
            x1, y1 = (o1 - lon) * c * 111.32, (a1 - lat) * 110.57; x2, y2 = (o2 - lon) * c * 111.32, (a2 - lat) * 110.57
            dx, dy = x2 - x1, y2 - y1; t = 0 if dx == dy == 0 else max(0, min(1, -(x1 * dx + y1 * dy) / (dx * dx + dy * dy)))
            best = min(best, math.hypot(x1 + t * dx, y1 + t * dy))
    return best
# 해안선을 따라 육지 쪽(서쪽)으로 300m 들인 길
#   위도 0.004° 칸마다 가장 동쪽(바다 쪽) 꼭짓점 하나 → 지그재그 없이 북쪽으로 (감포 35.80 → 35.86, 6km 남짓)
bins = {}
for ln in L:
    for a, o in ln:
        if 35.800 <= a <= 35.862 and 129.45 <= o <= 129.60:
            k = int((a - 35.800) / 0.004)
            if k not in bins or o > bins[k][1]: bins[k] = (a, o)
coast_path = [(bins[k][0], bins[k][1] - 0.0033) for k in sorted(bins)]
way = [(35.8050, 129.4550), (35.8040, 129.4750), (35.8030, 129.4900)] + coast_path
# 70km/h 로 1초마다 점
v = 70 / 3.6
res = [way[0]]
for (a1, o1), (a2, o2) in zip(way, way[1:]):
    c = math.cos(math.radians(a1))
    d = math.hypot((o2 - o1) * c * 111320, (a2 - a1) * 110570)
    steps = max(1, int(d / v))
    for s in range(1, steps + 1):
        res.append((a1 + (a2 - a1) * s / steps, o1 + (o2 - o1) * s / steps))
open(f"{out}/gampo_coast.csv", "w").write("".join(f"{a:.6f},{o:.6f}\n" for a, o in res))
t0 = datetime.datetime(2026, 11, 15, 9, 0, 0)
gpx = ['<?xml version="1.0" encoding="UTF-8"?>', '<gpx version="1.1" creator="car_bgm" xmlns="http://www.topografix.com/GPX/1/1">',
       '<trk><name>감포 내륙 → 해안 (70km/h)</name><trkseg>']
gpx += [f'<trkpt lat="{a:.6f}" lon="{o:.6f}"><time>{(t0 + datetime.timedelta(seconds=i)).isoformat()}Z</time></trkpt>' for i, (a, o) in enumerate(res)]
gpx += ['</trkseg></trk>', '</gpx>']
open(f"{out}/gampo_coast.gpx", "w", encoding="utf-8").write("\n".join(gpx) + "\n")
first_coast = next((i for i, (a, o) in enumerate(res) if dist(a, o) <= 2.0), None)
print(f"점 {len(res)}개 = {len(res) // 60}분 {len(res) % 60}초 · 출발 해안까지 {dist(*res[0]):.1f}km · 바닷가 들어가는 때 {first_coast}초 · 해안 구간 최대 거리 {max(dist(a, o) for a, o in res[first_coast:]):.1f}km")
