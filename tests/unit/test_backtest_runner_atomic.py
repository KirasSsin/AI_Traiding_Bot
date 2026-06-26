"""S55 DASH-03 — atomic cache writes + single-flight lock across research dispatch.

Bug: cache writes used plain `cache_path.write_text` (non-atomic) — two concurrent
same-run_id requests could interleave/truncate the JSON, and a parallel
`get_run` could read a half-written file → JSONDecodeError 500. ALSO the research
branches (volume_breakout / atr_breakout / supertrend / kronos) all returned BEFORE
`with _lock:`, so POST /api/backtest (plain def → threadpool) ran research runners
fully parallel, breaking the documented single-flight contract.

Fix: (a) _atomic_write_text helper (tmp + os.replace, mirrors storage.py);
(b) hoist `with _lock:` to cover the whole dispatch body so ALL strategy types
serialize, matching the module docstring.
"""

from __future__ import annotations

import json

import pytest
from src.dashboard import _cache_io as cio
from src.dashboard import backtest_runner as br
from src.dashboard.backtest_runner import BacktestRequest, _atomic_write_text

# S55 PHASE6.2 NEW-LOW-01: _atomic_write_text is now an alias of _cache_io.atomic_write_text
# (DRY consolidation), so os.replace resolves from the _cache_io module — patch it there.


# --- (a) atomic write helper ---
def test_atomic_write_text_writes_via_tmp_then_replace(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """_atomic_write_text must stage to a .tmp sibling and os.replace into place —
    never a direct write to the final path."""
    target = tmp_path / "run.json"
    replace_calls: list[tuple[str, str]] = []
    real_replace = cio.os.replace

    def spy_replace(src, dst):  # type: ignore[no-untyped-def]
        replace_calls.append((str(src), str(dst)))
        return real_replace(src, dst)

    monkeypatch.setattr(cio.os, "replace", spy_replace)
    _atomic_write_text(target, '{"a": 1}')

    # Exactly one os.replace, from <target>.tmp → <target>.
    assert len(replace_calls) == 1
    src, dst = replace_calls[0]
    assert src.endswith(".json.tmp")
    assert dst == str(target)
    # Final file is the fully-written content; no leftover tmp.
    assert json.loads(target.read_text()) == {"a": 1}
    assert not (tmp_path / "run.json.tmp").exists()


def test_atomic_write_text_no_torn_final_on_replace_failure(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """If os.replace fails, the final path must NOT contain a partial write —
    the bytes only ever landed in the .tmp, and the tmp is cleaned up."""
    target = tmp_path / "run.json"
    target.write_text('{"old": true}')  # pre-existing good file

    def boom(_src, _dst):  # type: ignore[no-untyped-def]
        raise OSError("replace failed")

    monkeypatch.setattr(cio.os, "replace", boom)
    with pytest.raises(OSError, match="replace failed"):
        _atomic_write_text(target, '{"new": false}')

    # Old file untouched (never overwritten in place); tmp cleaned up.
    assert json.loads(target.read_text()) == {"old": True}
    assert not (tmp_path / "run.json.tmp").exists()


# --- (b) single-flight lock across a research-strategy dispatch ---
def test_volume_breakout_dispatch_holds_lock(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """The volume_breakout research branch must execute under `_lock` (single-flight).
    Previously it returned before the lock → concurrent runners ran in parallel."""
    monkeypatch.setattr(br, "_RUNS_DIR", tmp_path)

    lock_held_during_run: dict[str, bool] = {}

    import src.backtest.research_runner_envelope as env_mod
    import src.backtest.volume_breakout_runner as vb_mod

    def fake_wfa(**_kwargs):  # type: ignore[no-untyped-def]
        return None

    def fake_raw(**_kwargs):  # type: ignore[no-untyped-def]
        # acquire(blocking=False) returns False iff the lock is already held →
        # confirms the dispatch holds _lock around this research runner.
        acquired = br._lock.acquire(blocking=False)
        lock_held_during_run["held"] = not acquired
        if acquired:
            br._lock.release()
        return {
            "n_trades": 0,
            "sharpe": 0.0,
            "win_rate": 0.0,
            "total_pnl_pct": 0.0,
            "bars_per_year": 2191,
            "equity_curve": {"equity_pct": [], "timestamps": []},
        }

    def fake_envelope(**_kwargs):  # type: ignore[no-untyped-def]
        return {"verdict": "RAW", "metrics": {}, "warnings": []}

    monkeypatch.setattr(vb_mod, "_run_volume_breakout_wfa", fake_wfa)
    monkeypatch.setattr(vb_mod, "run_volume_breakout_backtest", fake_raw)
    monkeypatch.setattr(env_mod, "build_research_runner_envelope", fake_envelope)

    req = BacktestRequest(
        strategy_id="volume_breakout_iter10",
        symbol="BTCUSDT",
        interval="240",
        start="2020-01-01",
        end="2021-01-01",
    )
    result = br.run_backtest(req)
    assert result["run_id"] == req.run_id()
    assert lock_held_during_run.get("held") is True
