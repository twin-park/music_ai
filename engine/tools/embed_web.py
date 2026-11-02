# web/index.html → src/web_ui.h (exe 안에 화면을 넣음)
import os
HERE = os.path.dirname(os.path.abspath(__file__))
html = open(os.path.join(HERE, "..", "web", "index.html"), encoding="utf-8").read()
assert ")WEB\"" not in html
open(os.path.join(HERE, "..", "src", "web_ui.h"), "w", encoding="utf-8").write(
    "// web/index.html 에서 만듦 (tools/embed_web.py) — 손으로 고치지 말 것\n#pragma once\nstatic const char *WEB_UI = R\"WEB(" + html + ")WEB\";\n")
print("→ src/web_ui.h", len(html))
