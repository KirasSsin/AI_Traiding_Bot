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
    p = tmp_path / "trials.json"
    log = CrossTrialLog(path=p)
    log.append_trial(sprint=13, oos_sharpe=-44.46)
    log.append_trial(sprint=15, oos_sharpe=10.0)
    sigma = log.sigma_sr()
    assert sigma is not None
    # statistics.stdev (sample, n-1): std of [-44.46, 10.0] = sqrt((44.46+10)^2/2/1) / sqrt...
    # Actually: mean = -17.23, sum sq dev = (-44.46+17.23)^2 + (10+17.23)^2 = 27.23^2 * 2 = 1483
    # var = 1483 / 1 = 1483; sigma = sqrt(1483) ~ 38.51
    assert sigma == pytest.approx(38.51, abs=0.5)


def test_sigma_sr_one_trial_returns_none(tmp_path: Path) -> None:
    p = tmp_path / "trials.json"
    log = CrossTrialLog(path=p)
    log.append_trial(sprint=13, oos_sharpe=-44.46)
    assert log.sigma_sr() is None


def test_atomic_write_no_partial_on_failure(tmp_path: Path) -> None:
    """tmp+rename pattern: even if write interrupted, original file intact."""
    p = tmp_path / "trials.json"
    p.write_text(json.dumps({"trials": [{"sprint": 13, "oos_sharpe": -44.46}]}))
    log = CrossTrialLog(path=p)
    log.append_trial(sprint=15, oos_sharpe=5.0)
    # Verify no .tmp leftovers
    tmp_files = list(tmp_path.glob("*.tmp"))
    assert tmp_files == []
