#!/usr/bin/env python3
"""S62 P1-CASCADE: WARN при полном чтении banned/крупных файлов.

Каскад wiki→mem→grep→read (ADR 0043) держится на дисциплине. Механизируемая
часть: не читать целиком banned-from-full-read файлы (00-All.md, крупные планы,
log.md) — Read tool имеет ~25k-токенный лимит, превышение проваливает turn.

Событие: PreToolUse на Read ИЛИ Bash. Читает payload-JSON на stdin.
- Read: tool_input.file_path без limit + файл > порога / в banned → WARN.
- Bash: `cat/less/more <file>` (без пайпа в head/tail) на крупный файл → WARN.
Политика WARN-only (fail-OPEN): печатает напоминание на stderr, exit 0. Это
подсказка (offset/grep), а не барьер — жёсткий блок ломал бы легальные сценарии.

Порог: 50КБ (≈15k токенов, эмпирика CLAUDE.md §9).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

THRESHOLD = 50 * 1024
# review MEDIUM #3: авторитет списка banned — ~/.claude/CLAUDE.md §9. Здесь —
# defense-in-depth на случай файла, переименованного НИЖЕ 50КБ но всё ещё
# «banned» по смыслу. Сегодня THRESHOLD (50КБ) покрывает все §9-файлы на 100%
# (00-All.md 1.4МБ / log.md 233КБ / планы >90КБ). При правке §9 — синхронь тут.
BANNED_BASENAMES = {
    "00-All.md",
    "log.md",
}
BANNED_SUBSTR = ("FINAL-CONSOLIDATED", "00-All")


def _warn(path: str, size: int, how: str) -> None:
    kb = size // 1024
    print(
        f"⚠️  CASCADE-WARN: {how} крупного файла {path} (~{kb}КБ > 50КБ). "
        "Read tool лимит ~25k токенов — превышение провалит turn. "
        "Читай через offset+limit ИЛИ Grep нужной секции (каскад wiki→mem→grep→read, ADR 0043).",
        file=sys.stderr,
    )


def _is_banned(p: Path) -> bool:
    name = p.name
    if name in BANNED_BASENAMES:
        return True
    return any(s in str(p) for s in BANNED_SUBSTR)


def _check_file(path_str: str, how: str) -> None:
    try:
        p = Path(path_str)
        if not p.is_file():
            return
        size = p.stat().st_size
    except OSError:
        return
    if _is_banned(p) or size > THRESHOLD:
        _warn(path_str, size, how)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if not isinstance(payload, dict):  # review LOW #4: не-dict JSON (напр. [1,2])
        return 0
    tool = payload.get("tool_name", "")
    ti = payload.get("tool_input", {})
    if not isinstance(ti, dict):
        return 0

    if tool == "Read":
        # WARN только если читают без limit (offset без limit тоже читает до конца)
        if ti.get("limit") in (None, "") and ti.get("file_path"):
            _check_file(str(ti["file_path"]), "Read-без-limit")
        return 0

    if tool == "Bash":
        cmd = str(ti.get("command", ""))
        # cat/less/more <file>, но НЕ если есть пайп в head/tail/grep/sed (частичное)
        if re.search(r"\|\s*(head|tail|grep|sed|awk)\b", cmd):
            return 0
        m = re.search(r"\b(?:cat|less|more)\s+([^\s|;&><]+)", cmd)
        if m:
            _check_file(m.group(1), "cat/less")
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
