#!/usr/bin/env python3
"""Сканер битых Obsidian-ссылок в docs/ (S57 T5, фундамент Docs-Sync Gate S59).

Поддержка форматов: [[page]], [[page|alias]], [[dir/page]], [[page#якорь]].
Якорные-only ссылки ([[#h]]) и пустые пропускаются. Код-блоки ``` исключаются.

Использование: docs_broken_link_scan.py <docs-dir> [--quiet]
Выход: 0 = битых нет; 1 = есть (список file:line: target в stdout).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


def collect_targets(root: Path) -> set[str]:
    """Все валидные цели: basename и относительный путь (без .md), lowercase."""
    targets: set[str] = set()
    for p in root.rglob("*.md"):
        rel = p.relative_to(root).with_suffix("")
        targets.add(p.stem.lower())
        targets.add(str(rel).lower())
    return targets


def iter_links(md_file: Path):
    """(line_no, raw_target) для каждой [[ссылки]] вне код-блоков."""
    in_code = False
    for i, line in enumerate(md_file.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        for m in LINK_RE.finditer(line):
            yield i, m.group(1)


def normalize(raw: str) -> str | None:
    """Цель без alias/якоря/расширения; None = пропустить (не навигация)."""
    target = raw.split("|")[0].split("#")[0].strip().strip("\\").rstrip("/")
    if not target:
        return None  # чисто якорная или пустая
    if target.endswith(".md"):
        target = target[:-3]
    return target.lower()


def scan(root: Path) -> list[tuple[str, int, str]]:
    targets = collect_targets(root)
    broken: list[tuple[str, int, str]] = []
    for md in sorted(root.rglob("*.md")):
        for line_no, raw in iter_links(md):
            t = normalize(raw)
            if t is None:
                continue
            if t in targets:
                continue
            # путь-ссылка: совпадение по хвосту (Obsidian shortest-path)
            base = t.rsplit("/", 1)[-1]
            if base in targets:
                continue
            broken.append((str(md.relative_to(root)), line_no, raw))
    return broken


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: docs_broken_link_scan.py <docs-dir> [--quiet]", file=sys.stderr)
        return 2
    root = Path(sys.argv[1])
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2
    broken = scan(root)
    quiet = "--quiet" in sys.argv
    if broken and not quiet:
        for f, ln, raw in broken:
            print(f"{f}:{ln}: [[{raw}]]")
    print(f"broken={len(broken)}", file=sys.stderr)
    return 1 if broken else 0


if __name__ == "__main__":
    raise SystemExit(main())
