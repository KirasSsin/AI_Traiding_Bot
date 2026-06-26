"""Low-level atomic cache-file writer shared across dashboard dispatch modules.

S55 DASH-03-GAP-01: the atomic write helper was first added in backtest_runner
(DASH-03), but _kronos_dispatch — imported BY backtest_runner — still wrote its
result caches with a plain `cache_path.write_text(...)`. Re-importing the helper
from backtest_runner would create an import cycle, so the helper lives here in a
dependency-free low-level module that BOTH backtest_runner and _kronos_dispatch
import.
"""

from __future__ import annotations

import os
from pathlib import Path


def atomic_write_text(path: Path, text: str) -> None:
    """Write text atomically: stage to a sibling .tmp then os.replace into place.

    os.replace is atomic on POSIX, so a reader (e.g. ``get_run`` /
    ``GET /api/runs/{run_id}``) always sees either the old file or the fully-written
    new one — never a torn intermediate. Two concurrent same-run_id writers cannot
    interleave/truncate the final JSON. Mirrors the tmp+os.replace idiom in
    src/marketdata/storage.py.
    """
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp_path.write_text(text)
        os.replace(tmp_path, path)
    finally:
        # tmp is gone after a successful replace; only matters if write/replace raised.
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
