#!/usr/bin/env python3
"""從 .md 抽出 plantuml 區塊並產生 SVG,順便處理獨立的 .puml 檔。

用法:python3 render_plantuml.py [來源資料夾]  (預設 example)
"""
import re
import subprocess
import sys
from pathlib import Path

SRC_DIR = Path(sys.argv[1] if len(sys.argv) > 1 else "example")

# 匹配 ```plantuml:名稱 ... ``` 區塊;名稱與型別(如 @gantt)皆可省略
FENCE = re.compile(
    r"```plantuml(?:@\w+)?(?::(?P<name>[\w\-./]+))?\s*\n(?P<body>.*?)\n```",
    re.DOTALL,
)


def render(puml_text: str, out_svg: Path) -> None:
    body = puml_text.strip()
    if "@start" not in body:                      # 沒寫 @startuml 就自動補上
        body = f"@startuml\n{body}\n@enduml"
    out_svg.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["plantuml", "-tsvg", "-pipe"],           # 從 stdin 讀、往 stdout 輸出
        input=body.encode("utf-8"),
        capture_output=True,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stderr.decode("utf-8", "replace"))
        raise SystemExit(f"繪製失敗:{out_svg}")
    out_svg.write_bytes(result.stdout)
    print(f"產生 {out_svg}")


def main() -> None:
    if not SRC_DIR.exists():
        raise SystemExit(f"找不到來源資料夾:{SRC_DIR}")

    # 1) 獨立的 .puml / .pu / .plantuml 檔,直接渲染成同名 .svg
    for ext in ("*.puml", "*.pu", "*.plantuml"):
        for f in SRC_DIR.rglob(ext):
            render(f.read_text(encoding="utf-8"), f.with_suffix(".svg"))

    # 2) .md 內嵌的 plantuml 區塊,依 :名稱 輸出到同資料夾
    for md in SRC_DIR.rglob("*.md"):
        text = md.read_text(encoding="utf-8")
        for i, m in enumerate(FENCE.finditer(text)):
            name = m.group("name") or f"{md.stem}-{i}"
            render(m.group("body"), md.parent / f"{name}.svg")


if __name__ == "__main__":
    main()
