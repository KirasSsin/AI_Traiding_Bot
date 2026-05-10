"""S45 T3 — CrossTrialLog idempotency guard tests (B1 fix)."""

from __future__ import annotations

from pathlib import Path

from src.analytics.cross_trial_log import CrossTrialLog


def test_append_trial_idempotent_on_repeat_call(tmp_path: Path) -> None:
    """S45 B1 — same (sprint, symbol) tuple appended twice → only 1 entry."""
    log = CrossTrialLog(path=tmp_path / "log.json")
    log.append_trial(sprint=44, symbol="BTCUSDT_9_2.5", oos_sharpe=1.22)
    log.append_trial(sprint=44, symbol="BTCUSDT_9_2.5", oos_sharpe=1.22)
    assert log.n_trials() == 1


def test_append_trial_distinct_symbols_kept(tmp_path: Path) -> None:
    """Different (sprint, symbol) tuples appended separately."""
    log = CrossTrialLog(path=tmp_path / "log.json")
    log.append_trial(sprint=44, symbol="BTCUSDT_9_2.5", oos_sharpe=1.22)
    log.append_trial(sprint=44, symbol="ETHUSDT_14_2.5", oos_sharpe=0.85)
    log.append_trial(sprint=45, symbol="BTCUSDT_9_2.5", oos_sharpe=1.30)
    assert log.n_trials() == 3


def test_append_trial_repeat_with_different_sharpe_overwrites(tmp_path: Path) -> None:
    """Same (sprint, symbol) с new oos_sharpe → updates existing entry."""
    log = CrossTrialLog(path=tmp_path / "log.json")
    log.append_trial(sprint=44, symbol="BTCUSDT_9_2.5", oos_sharpe=1.22)
    log.append_trial(sprint=44, symbol="BTCUSDT_9_2.5", oos_sharpe=1.55)
    assert log.n_trials() == 1
    assert log.get_oos_sharpes() == [1.55]


def test_append_trial_legacy_no_symbol_arg_dedup_default(tmp_path: Path) -> None:
    """Backward compat: legacy callers без symbol — same default → dedup."""
    log = CrossTrialLog(path=tmp_path / "log.json")
    log.append_trial(sprint=13, oos_sharpe=0.5)
    log.append_trial(sprint=13, oos_sharpe=0.5)
    assert log.n_trials() == 1


def test_append_trial_preserves_order(tmp_path: Path) -> None:
    """Append order preserved (oldest first); update preserves position."""
    log = CrossTrialLog(path=tmp_path / "log.json")
    log.append_trial(sprint=13, symbol="A", oos_sharpe=0.5)
    log.append_trial(sprint=14, symbol="B", oos_sharpe=0.7)
    log.append_trial(sprint=13, symbol="A", oos_sharpe=0.6)  # update first
    assert log.n_trials() == 2
    assert log.get_oos_sharpes() == [0.6, 0.7]  # A position preserved
