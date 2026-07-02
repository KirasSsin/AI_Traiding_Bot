#!/usr/bin/env python3
"""C1 Auto-Resume (S58): разбор StopFailure-payload и атомарная запись маркера.

stdin: JSON payload хука StopFailure (error, session_id, cwd, transcript_path).
Маркер пишется ТОЛЬКО для error in {rate_limit, overloaded} — остальные ошибки
(billing, auth, ...) требуют человека, машине их не чинить.

Выход: 0 = маркер записан; 1 = не наше событие (не лимит); 2 = ошибка разбора.
Совместимо с системным python3 (3.9): без PEP 604 аннотаций в рантайме.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

RESUMABLE = {"rate_limit", "overloaded"}


def main() -> int:
    ar_dir = Path(os.environ.get("AR_DIR", str(Path.home() / ".claude" / "auto-resume")))
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 2
    error = payload.get("error", "")
    if error not in RESUMABLE:
        return 1

    marker = {
        "ts": int(time.time()),
        "error": error,
        "session_id": payload.get("session_id", ""),
        "cwd": payload.get("cwd", ""),
        "transcript_path": payload.get("transcript_path", ""),
        "noprog": 0,
    }
    ar_dir.mkdir(parents=True, exist_ok=True)
    tmp = ar_dir / "pending.json.tmp"
    tmp.write_text(json.dumps(marker, ensure_ascii=False), encoding="utf-8")
    tmp.replace(ar_dir / "pending.json")  # атомарно

    with (ar_dir / "log").open("a", encoding="utf-8") as f:
        f.write(
            time.strftime("%Y-%m-%d %H:%M:%S")
            + f" MARKER error={error} session={marker['session_id'][:12]} cwd={marker['cwd']}\n"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
