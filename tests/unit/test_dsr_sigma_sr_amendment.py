"""S36 T6 ADR 0056 — sigma_SR sourcing hierarchy.

PREFERRED:    N>=3 cross-trial entries → sigma_SR = stdev(oos_sharpes)
DEGENERATE:   1-2 entries → sigma_SR = NaN (df<2 statistically inadmissible)
EMPTY:        0 entries → None (caller knows to use n_trials=1, mark UNDERPOWERED)
INADMISSIBLE: per-fold Sharpe stdev as sigma_SR proxy → REMOVED (Bailey 2014 eq.12).
"""

from __future__ import annotations

import math
import statistics
from pathlib import Path

import pytest
from src.analytics.cross_trial_log import CrossTrialLog


def _make_log(tmp_path: Path, *, n_entries: int) -> CrossTrialLog:
    log_path = tmp_path / "cross_trial.json"
    log = CrossTrialLog(path=log_path)
    for i in range(n_entries):
        log.append_trial(sprint=10 + i, oos_sharpe=1.0 + i * 0.1, symbol="BTCUSDT")
    return log


def test_sigma_sr_from_log_n_3_or_more_returns_stdev(tmp_path: Path) -> None:
    """ADR 0056 PREFERRED: N>=3 entries → sigma_SR = stdev(oos_sharpes)."""
    log = _make_log(tmp_path, n_entries=3)
    sigma = log.sigma_sr()
    assert sigma is not None
    assert not math.isnan(sigma)
    expected = statistics.stdev([1.0, 1.1, 1.2])
    assert sigma == pytest.approx(expected, abs=1e-6)


def test_sigma_sr_from_log_n_below_3_returns_nan(tmp_path: Path) -> None:
    """ADR 0056 DEGENERATE: 1-2 entries → sigma_SR=NaN (was: stdev with df=0/1)."""
    log = _make_log(tmp_path, n_entries=2)
    sigma = log.sigma_sr()
    assert sigma is not None
    assert math.isnan(sigma)


def test_sigma_sr_from_log_n_0_returns_none(tmp_path: Path) -> None:
    """ADR 0056: empty log → None (caller knows to use n_trials=1, mark UNDERPOWERED)."""
    log_path = tmp_path / "cross_trial.json"
    log = CrossTrialLog(path=log_path)
    assert log.sigma_sr() is None


def test_donchian_runner_no_inadmissible_fallback() -> None:
    """ADR 0056: per-fold stdev fallback REMOVED (donchian_runner.py:191-193)."""
    src_text = (Path(__file__).parents[2] / "src" / "backtest" / "donchian_runner.py").read_text()
    assert (
        "stdev(fold_sharpes)" not in src_text
    ), "ADR 0056 REMOVED: per-fold Sharpe stdev as sigma_SR proxy"


def test_donchian_runner_uses_trial_mean_fold_oos_sharpe() -> None:
    """ADR 0056 variable rename: aggregate_oos_sharpe → trial_mean_fold_oos_sharpe."""
    src_text = (Path(__file__).parents[2] / "src" / "backtest" / "donchian_runner.py").read_text()
    assert (
        "aggregate_oos_sharpe" not in src_text
    ), "ADR 0056: variable renamed to trial_mean_fold_oos_sharpe"
    assert "trial_mean_fold_oos_sharpe" in src_text
