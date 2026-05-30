"""Tests for CrossTrialLog (S15 T0 — DSR cross-trial Sharpe persistence).

Closes S14 Q2 REVISE carry-over (Bailey eq. 13 cross-trial sigma_SR).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from src.analytics.cross_trial_log import CrossTrialLog


def test_load_seeded_log(tmp_path: Path) -> None:
    p = tmp_path / "trials.json"
    p.write_text(json.dumps({"trials": [{"sprint": 13, "oos_sharpe": -44.46}]}))
    log = CrossTrialLog(path=p)
    assert log.get_oos_sharpes() == [-44.46]
    assert log.n_trials() == 1


def test_append_new_trial_persists(tmp_path: Path) -> None:
    p = tmp_path / "trials.json"
    p.write_text(json.dumps({"trials": [{"sprint": 13, "oos_sharpe": -44.46}]}))
    log = CrossTrialLog(path=p)
    log.append_trial(sprint=15, oos_sharpe=2.5)
    assert log.get_oos_sharpes() == [-44.46, 2.5]
    # Verify persisted on disk
    re_read = CrossTrialLog(path=p)
    assert re_read.get_oos_sharpes() == [-44.46, 2.5]
    assert re_read.n_trials() == 2


def test_missing_file_starts_empty(tmp_path: Path) -> None:
    p = tmp_path / "nonexistent.json"
    log = CrossTrialLog(path=p)
    assert log.get_oos_sharpes() == []
    assert log.n_trials() == 0
    assert log.sigma_sr() is None


def test_append_creates_parent_dir(tmp_path: Path) -> None:
    p = tmp_path / "nested" / "subdir" / "trials.json"
    log = CrossTrialLog(path=p)
    log.append_trial(sprint=13, oos_sharpe=-44.46)
    assert p.exists()
    assert log.get_oos_sharpes() == [-44.46]


def test_sigma_sr_two_trials(tmp_path: Path) -> None:
    """ADR 0056 (S36): N<3 → NaN (was: stdev). df=1 statistically inadmissible."""
    import math

    p = tmp_path / "trials.json"
    log = CrossTrialLog(path=p)
    log.append_trial(sprint=13, oos_sharpe=-44.46)
    log.append_trial(sprint=15, oos_sharpe=10.0)
    sigma = log.sigma_sr()
    assert sigma is not None
    assert math.isnan(sigma)


def test_sigma_sr_three_trials_returns_stdev(tmp_path: Path) -> None:
    """ADR 0056 (S36) PREFERRED: N>=3 → stdev(oos_sharpes)."""
    import statistics as _stats

    p = tmp_path / "trials.json"
    log = CrossTrialLog(path=p)
    log.append_trial(sprint=13, oos_sharpe=-44.46)
    log.append_trial(sprint=15, oos_sharpe=10.0)
    log.append_trial(sprint=17, oos_sharpe=2.5)
    sigma = log.sigma_sr()
    assert sigma is not None
    expected = _stats.stdev([-44.46, 10.0, 2.5])
    assert sigma == pytest.approx(expected, abs=1e-6)


def test_sigma_sr_one_trial_returns_nan(tmp_path: Path) -> None:
    """ADR 0056 (S36): N=1 → NaN (was: None). DEGENERATE marker."""
    import math

    p = tmp_path / "trials.json"
    log = CrossTrialLog(path=p)
    log.append_trial(sprint=13, oos_sharpe=-44.46)
    sigma = log.sigma_sr()
    assert sigma is not None
    assert math.isnan(sigma)


def test_atomic_write_no_partial_on_failure(tmp_path: Path) -> None:
    """tmp+rename pattern: even if write interrupted, original file intact."""
    p = tmp_path / "trials.json"
    p.write_text(json.dumps({"trials": [{"sprint": 13, "oos_sharpe": -44.46}]}))
    log = CrossTrialLog(path=p)
    log.append_trial(sprint=15, oos_sharpe=5.0)
    # Verify no .tmp leftovers
    tmp_files = list(tmp_path.glob("*.tmp"))
    assert tmp_files == []


# ---------------------------------------------------------------------------
# S51 D5 — two-level pool scoping (strategy_class field + per-class sigma_sr)
# ---------------------------------------------------------------------------


def test_strategy_class_field_persisted(tmp_path: Path) -> None:
    """S51 D5 — strategy_class stored and retrievable per entry."""
    log = CrossTrialLog(path=tmp_path / "trials.json")
    log.append_trial(sprint=50, symbol="BTCUSDT", strategy_class="supertrend", oos_sharpe=2.5)
    entries = log.get_entries()
    assert len(entries) == 1
    assert entries[0]["strategy_class"] == "supertrend"


def test_strategy_class_round_trips_across_instances(tmp_path: Path) -> None:
    """S51 D5 — strategy_class survives persistence (atomic write + reload)."""
    path = tmp_path / "trials.json"
    log1 = CrossTrialLog(path=path)
    log1.append_trial(sprint=44, symbol="ETHUSDT", strategy_class="atr_breakout", oos_sharpe=-89.0)
    log2 = CrossTrialLog(path=path)
    assert log2.get_entries()[0]["strategy_class"] == "atr_breakout"


def test_legacy_entry_without_strategy_class_backfilled(tmp_path: Path) -> None:
    """S51 D5 — legacy entries without strategy_class backfilled to 'unknown'."""
    path = tmp_path / "trials.json"
    path.write_text(
        json.dumps({"trials": [{"sprint": 13, "symbol": "BTCUSDT", "oos_sharpe": -44.46}]})
    )
    log = CrossTrialLog(path=path)
    entries = log.get_entries()
    assert len(entries) == 1
    assert entries[0]["strategy_class"] == "unknown"  # backfilled default
    assert entries[0]["oos_sharpe"] == -44.46  # value preserved exactly


def test_default_strategy_class_when_not_specified(tmp_path: Path) -> None:
    """S51 D5 — appending without strategy_class uses 'unknown' default."""
    log = CrossTrialLog(path=tmp_path / "trials.json")
    log.append_trial(sprint=13, oos_sharpe=1.0)
    assert log.get_entries()[0]["strategy_class"] == "unknown"


def test_sigma_sr_per_class_isolates_classes(tmp_path: Path) -> None:
    """S51 D5 verdict (e) — within-class sigma ignores other classes.

    S44 atr_breakout contamination must NOT poison a supertrend DSR.
    """
    log = CrossTrialLog(path=tmp_path / "trials.json")
    # 3 tight supertrend entries + 2 wild atr_breakout entries
    log.append_trial(sprint=50, symbol="BTC_a", strategy_class="supertrend", oos_sharpe=1.0)
    log.append_trial(sprint=50, symbol="BTC_b", strategy_class="supertrend", oos_sharpe=2.0)
    log.append_trial(sprint=50, symbol="BTC_c", strategy_class="supertrend", oos_sharpe=3.0)
    log.append_trial(sprint=44, symbol="ETH_a", strategy_class="atr_breakout", oos_sharpe=-89.0)
    log.append_trial(sprint=44, symbol="ETH_b", strategy_class="atr_breakout", oos_sharpe=-40.0)
    # within-class supertrend sigma = stdev([1,2,3]) = 1.0, NOT poisoned by -89/-40
    class_sigma = log.sigma_sr(strategy_class="supertrend")
    assert class_sigma is not None
    assert abs(class_sigma - 1.0) < 1e-9


def test_sigma_sr_global_unchanged_when_no_class(tmp_path: Path) -> None:
    """S51 D5 — sigma_sr() with no class arg stays GLOBAL (legacy callers)."""
    log = CrossTrialLog(path=tmp_path / "trials.json")
    log.append_trial(sprint=50, symbol="BTC_a", strategy_class="supertrend", oos_sharpe=1.0)
    log.append_trial(sprint=50, symbol="BTC_b", strategy_class="supertrend", oos_sharpe=2.0)
    log.append_trial(sprint=44, symbol="ETH_a", strategy_class="atr_breakout", oos_sharpe=3.0)
    # global stdev([1,2,3]) = 1.0 (mixes classes — the legacy/global behaviour)
    global_sigma = log.sigma_sr()
    assert global_sigma is not None
    assert abs(global_sigma - 1.0) < 1e-9


def test_sigma_sr_per_class_nan_with_fewer_than_three(tmp_path: Path) -> None:
    """S51 D5 — 1-2 within-class entries → NaN (df<2, mirrors ADR 0056)."""
    import math

    log = CrossTrialLog(path=tmp_path / "trials.json")
    log.append_trial(sprint=50, symbol="BTC_a", strategy_class="supertrend", oos_sharpe=1.0)
    log.append_trial(sprint=50, symbol="BTC_b", strategy_class="supertrend", oos_sharpe=2.0)
    # 5 atr_breakout entries → global N large, supertrend class has only 2
    for i in range(5):
        log.append_trial(
            sprint=44, symbol=f"X_{i}", strategy_class="atr_breakout", oos_sharpe=float(i)
        )
    sigma = log.sigma_sr(strategy_class="supertrend")
    assert sigma is not None
    assert math.isnan(sigma)


def test_sigma_sr_per_class_none_when_class_absent(tmp_path: Path) -> None:
    """S51 D5 — 0 within-class entries → None (mirrors ADR 0056 EMPTY branch)."""
    log = CrossTrialLog(path=tmp_path / "trials.json")
    log.append_trial(sprint=44, symbol="ETH_a", strategy_class="atr_breakout", oos_sharpe=1.0)
    assert log.sigma_sr(strategy_class="supertrend") is None


def test_n_trials_stays_global_across_classes(tmp_path: Path) -> None:
    """S51 D5 — n_trials() counts ALL classes (GLOBAL breadth, anti-snooping)."""
    log = CrossTrialLog(path=tmp_path / "trials.json")
    log.append_trial(sprint=50, symbol="BTC_a", strategy_class="supertrend", oos_sharpe=1.0)
    log.append_trial(sprint=44, symbol="ETH_a", strategy_class="atr_breakout", oos_sharpe=2.0)
    log.append_trial(sprint=44, symbol="ETH_b", strategy_class="atr_breakout", oos_sharpe=3.0)
    # GLOBAL count = 3 across 2 classes (NOT per-class — that's the loophole)
    assert log.n_trials() == 3
