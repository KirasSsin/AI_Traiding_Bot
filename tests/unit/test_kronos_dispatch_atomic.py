"""S55 DASH-03-GAP-01 — atomic Kronos cache writes in _kronos_dispatch.

Bug: _kronos_dispatch.run_kronos_dispatch wrote its result cache via plain
`cache_path.write_text(json.dumps(...))` at 3 sites (no-cache / variant-miss /
replay). Those writes run UNDER the dashboard `_lock`, but the cache READER in
backtest_runner.run_backtest (`json.loads(cache_path.read_text())`) runs OUTSIDE
the lock → a non-atomic Kronos write can be observed mid-write → JSONDecodeError 500.

Fix: route every Kronos cache write through the shared atomic helper
(_cache_io.atomic_write_text → tmp + os.replace), mirroring DASH-03.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest
import src.dashboard._cache_io as cache_io
from src.dashboard._kronos_dispatch import run_kronos_dispatch


@dataclass(frozen=True)
class _Req:
    strategy_id: str = "kronos"
    symbol: str = "BTCUSDT"
    interval: str = "240"
    start: str = "2022-01-01"
    end: str = "2022-06-01"
    variant: str = "base"


_PRESET = {
    "label": "Kronos ML",
    "supported_combos": [("BTCUSDT", "240")],
}


def _run_no_cache_path(tmp_path: Path):  # type: ignore[no-untyped-def]
    """Drive the 'cache absent' branch (no manifest) — the simplest of the 3 write sites."""
    runs_dir = tmp_path / "runs"
    cache_dir = tmp_path / "kronos_cache"  # no _manifest.json → 'not built' branch
    cache_path = runs_dir / "abc123.json"
    return run_kronos_dispatch(
        _Req(),
        preset=_PRESET,
        run_id="abc123",
        cache_path=cache_path,
        runs_dir=runs_dir,
        cache_dir=cache_dir,
    ), cache_path


def test_kronos_no_cache_write_is_atomic_via_replace(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """The Kronos cache write must go through atomic_write_text (tmp + os.replace),
    never a direct write to the final path."""
    replace_calls: list[tuple[str, str]] = []
    real_replace = cache_io.os.replace

    def spy_replace(src, dst):  # type: ignore[no-untyped-def]
        replace_calls.append((str(src), str(dst)))
        return real_replace(src, dst)

    monkeypatch.setattr(cache_io.os, "replace", spy_replace)

    result, cache_path = _run_no_cache_path(tmp_path)

    # Exactly one os.replace, from <cache_path>.tmp → <cache_path>.
    assert len(replace_calls) == 1
    src, dst = replace_calls[0]
    assert src.endswith(".json.tmp")
    assert dst == str(cache_path)
    # Final file is the fully-written content; no leftover tmp.
    assert json.loads(cache_path.read_text())["run_id"] == "abc123"
    assert not cache_path.with_suffix(".json.tmp").exists()


def test_kronos_no_cache_no_torn_final_on_replace_failure(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """If os.replace fails mid-write, the final cache path must NOT contain a partial
    JSON — the bytes only ever landed in the .tmp, which is cleaned up. A concurrent
    out-of-lock reader can therefore never observe a torn file."""
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir(parents=True)
    cache_path = runs_dir / "abc123.json"

    def boom(_src, _dst):  # type: ignore[no-untyped-def]
        raise OSError("replace failed")

    monkeypatch.setattr(cache_io.os, "replace", boom)

    with pytest.raises(OSError, match="replace failed"):
        run_kronos_dispatch(
            _Req(),
            preset=_PRESET,
            run_id="abc123",
            cache_path=cache_path,
            runs_dir=runs_dir,
            cache_dir=tmp_path / "kronos_cache",
        )

    # No torn final file; tmp cleaned up.
    assert not cache_path.exists()
    assert not cache_path.with_suffix(".json.tmp").exists()
