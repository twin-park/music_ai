# 앱 아이콘 (다크 + 초록) → app/src/main/res/mipmap-*/ic_launcher.png
#   python make_icon.py   (PIL 필요 — conda env car_bgm)
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "..", "app", "src", "main", "res")
BG, GREEN, DARK = (16, 18, 20, 255), (61, 214, 140, 255), (16, 18, 20, 255)
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def icon(n):
    S = n * 4                                   # 크게 그려서 줄임 (가장자리 매끈)
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, S - 1, S - 1], radius=S * 0.22, fill=BG)
    # 소리 물결 3줄 (상황에 따라 바뀌는 음악)
    for i, (h, x) in enumerate([(0.26, 0.24), (0.44, 0.38), (0.30, 0.52)]):
        w = S * 0.075
        cx = S * x
        d.rounded_rectangle([cx - w / 2, S * (0.5 - h / 2), cx + w / 2, S * (0.5 + h / 2)], radius=w / 2, fill=GREEN)
    f = ImageFont.truetype(FONT, int(S * 0.46))
    d.text((S * 0.74, S * 0.52), "♪", font=f, fill=GREEN, anchor="mm")
    return im.resize((n, n), Image.LANCZOS)


for name, n in [("mdpi", 48), ("hdpi", 72), ("xhdpi", 96), ("xxhdpi", 144), ("xxxhdpi", 192)]:
    out = os.path.join(RES, f"mipmap-{name}")
    os.makedirs(out, exist_ok=True)
    icon(n).save(os.path.join(out, "ic_launcher.png"), optimize=True)
    print(out, n)
