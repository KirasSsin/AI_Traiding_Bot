#!/usr/bin/env python3
"""Вставляет/заменяет AUTO-блок инвентаря кита в markdown-файлах.

Использование: kit_inventory_update.py "<блок>" file1.md [file2.md ...]
Блок ограничен маркерами <!-- AUTO:kit-inventory --> ... <!-- /AUTO:kit-inventory -->.
Если маркеры есть — блок заменяется; нет — вставляется после YAML-frontmatter.
Идемпотентен: повторный прогон с теми же числами не меняет файл.
"""

import re
import sys
from pathlib import Path

START = "<!-- AUTO:kit-inventory"
END = "<!-- /AUTO:kit-inventory -->"


def update(path: Path, block: str) -> str:
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), flags=re.DOTALL)
    if pattern.search(text):
        new_text = pattern.sub(block, text)
        action = "replaced"
    else:
        # после frontmatter (вторая строка '---'), иначе — в начало
        m = re.match(r"^---\n.*?\n---\n", text, flags=re.DOTALL)
        insert_at = m.end() if m else 0
        new_text = text[:insert_at] + "\n" + block + "\n" + text[insert_at:]
        action = "inserted"
    if new_text != text:
        path.write_text(new_text, encoding="utf-8")
        return action
    return "unchanged"


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: kit_inventory_update.py '<block>' file.md [...]", file=sys.stderr)
        return 1
    block = sys.argv[1]
    if START not in block or END not in block:
        print("block must contain AUTO markers", file=sys.stderr)
        return 1
    for f in sys.argv[2:]:
        p = Path(f)
        if not p.exists():
            print(f"SKIP missing: {f}", file=sys.stderr)
            continue
        print(f"{update(p, block)}: {f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
