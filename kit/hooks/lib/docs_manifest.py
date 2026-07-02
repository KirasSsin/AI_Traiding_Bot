#!/usr/bin/env python3
"""Обратный индекс «источник → страницы docs/» из frontmatter source_files.

Читает у каждого docs/**/*.md YAML-поле `source_files:` (список путей кода/кита,
которые страница документирует), строит карту source→[pages] и пишет
docs/manifest.json — кэш для docs-staleness-check.sh (быстро, без парсинга YAML
в bash). S60, KIT-004.

Использование: docs_manifest.py <docs-dir> [--check]
  без флага: (пере)генерирует <docs-dir>/manifest.json
  --check:   сравнивает существующий manifest с реальностью, exit 1 если дрейф
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

FM_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
SRC_RE = re.compile(r"^source_files:\s*(.+)$", re.MULTILINE)


def parse_sources(md: Path) -> list[str]:
    text = md.read_text(encoding="utf-8", errors="replace")
    m = FM_RE.match(text)
    if not m:
        return []
    fm = m.group(1)
    sm = SRC_RE.search(fm)
    if not sm:
        return []
    raw = sm.group(1).strip()
    # Поддержка inline-списка "a, b, c" и flow-списка "[a, b]"
    raw = raw.strip("[]")
    return [s.strip().strip("'\"") for s in raw.split(",") if s.strip()]


def build(root: Path) -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    for md in sorted(root.rglob("*.md")):
        rel_page = str(md.relative_to(root))
        for src in parse_sources(md):
            index.setdefault(src, [])
            if rel_page not in index[src]:
                index[src].append(rel_page)
    return index


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: docs_manifest.py <docs-dir> [--check]", file=sys.stderr)
        return 2
    root = Path(sys.argv[1])
    if not root.is_dir():
        print(f"not a dir: {root}", file=sys.stderr)
        return 2
    manifest_path = root / "manifest.json"
    fresh = build(root)

    if "--check" in sys.argv:
        if not manifest_path.exists():
            print("manifest.json missing", file=sys.stderr)
            return 1
        old = json.loads(manifest_path.read_text(encoding="utf-8"))
        if old != fresh:
            print("manifest.json out of sync with source_files frontmatter", file=sys.stderr)
            return 1
        print("manifest.json current", file=sys.stderr)
        return 0

    manifest_path.write_text(
        json.dumps(fresh, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        f"manifest.json: {len(fresh)} sources -> {sum(len(v) for v in fresh.values())} page-links"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
