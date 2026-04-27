"""Multi-symbol DSR pooling protocol — S33 T3 (Items #6+#7).

Per consilium ROUND 2 decision (a): pool all (sprint, symbol) pairs.
S33 multi-symbol → 3 trials per sprint (BTC + ETH + SOL).

Protocol (a) rationale: methodologically more honest (each symbol = independent
hypothesis test, different return series, different WFA folds). Conservative для
multi-symbol (over-penalizes когда symbols cluster differently — но safe side
per Bailey & López de Prado eq. 12).
"""

from __future__ import annotations

import statistics
from pathlib import Path

import pytest

from src.analytics.cross_trial_log import CrossTrialLog


def test_multi_symbol_S33_adds_3_trials(tmp_path: Path) -> None:
    """S33 BTC+ETH+SOL → n_trials=3 (NOT 1 pooled sprint)."""
    p = tmp_path / "trials.json"
    log = CrossTrialLog(path=p)
    log.append_trial(sprint=33, symbol="BTCUSDT", oos_sharpe=0.85)
    log.append_trial(sprint=33, symbol="ETHUSDT", oos_sharpe=0.72)
    log.append_trial(sprint=33, symbol="SOLUSDT", oos_sharpe=0.61)

    assert log.n_trials() == 3


def test_sigma_sr_pools_across_sprint_and_symbol(tmp_path: Path) -> None:
    """Pooling protocol (a): sigma_sr from all entries pooled (sprint, symbol)."""
    p = tmp_path / "trials.json"
    log = CrossTrialLog(path=p)
    log.append_trial(sprint=33, symbol="BTCUSDT", oos_sharpe=0.85)
    log.append_trial(sprint=33, symbol="ETHUSDT", oos_sharpe=0.72)
    log.append_trial(sprint=33, symbol="SOLUSDT", oos_sharpe=0.61)

    # Pooled sample stdev across 3 entries
    expected = statistics.stdev([0.85, 0.72, 0.61])
    sigma = log.sigma_sr()
    assert sigma is not None
    assert sigma == pytest.approx(expected, abs=1e-9)


def test_sigma_sr_pools_across_multiple_sprints_and_symbols(tmp_path: Path) -> None:
    """Cross-sprint + cross-symbol pooling — full protocol (a)."""
    p = tmp_path / "trials.json"
    log = CrossTrialLog(path=p)
    # S22 single-symbol
    log.append_trial(sprint=22, symbol="BTCUSDT", oos_sharpe=0.996)
    # S33 multi-symbol
    log.append_trial(sprint=33, symbol="BTCUSDT", oos_sharpe=0.85)
    log.append_trial(sprint=33, symbol="ETHUSDT", oos_sharpe=0.72)
    log.append_trial(sprint=33, symbol="SOLUSDT", oos_sharpe=0.61)

    assert log.n_trials() == 4
    expected = statistics.stdev([0.996, 0.85, 0.72, 0.61])
    assert log.sigma_sr() == pytest.approx(expected, abs=1e-9)


def test_sigma_sr_one_trial_returns_none(tmp_path: Path) -> None:
    """sigma_sr requires ≥ 2 entries (cannot compute stdev на 1 sample)."""
    p = tmp_path / "trials.json"
    log = CrossTrialLog(path=p)
    log.append_trial(sprint=33, symbol="BTCUSDT", oos_sharpe=0.85)
    assert log.sigma_sr() is None
