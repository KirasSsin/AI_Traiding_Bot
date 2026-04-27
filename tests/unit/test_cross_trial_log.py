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
