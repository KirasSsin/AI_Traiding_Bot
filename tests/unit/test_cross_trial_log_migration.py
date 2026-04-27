"""TrialEntry schema migration guard — S33 T3 (Item #9).

Per trading-logic-reviewer ROUND 2:
Adding `symbol: str` field к TrialEntry breaks legacy entries (no symbol key).
Loader must backfill default `symbol="BTCUSDT"` для pre-S33 entries.

Per quant-stats-reviewer ROUND 2 Item #6+#7:
Pooling protocol (a) — pool all (sprint, symbol) pairs as independent trials.
n_trials counts entries (3 per multi-symbol sprint, не 1 sprint).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.analytics.cross_trial_log import CrossTrialLog


def test_load_legacy_entry_no_symbol_field_backfills_BTCUSDT(tmp_path: Path) -> None:
    """Pre-S33 entries без symbol field → backfill 'BTCUSDT' (all prior single-symbol)."""
    p = tmp_path / "legacy.json"
    p.write_text(json.dumps({"trials": [{"sprint": 22, "oos_sharpe": 0.996}]}))
    log = CrossTrialLog(path=p)
    entries = log.get_entries()
    assert len(entries) == 1
    assert entries[0]["sprint"] == 22
    assert entries[0]["symbol"] == "BTCUSDT"  # backfilled
    assert entries[0]["oos_sharpe"] == 0.996


def test_append_with_symbol_persists_correctly(tmp_path: Path) -> None:
    """New entries (S33+) с symbol field stored как-is."""
    p = tmp_path / "trials.json"
    log = CrossTrialLog(path=p)
    log.append_trial(sprint=33, symbol="BTCUSDT", oos_sharpe=0.85)
    log.append_trial(sprint=33, symbol="ETHUSDT", oos_sharpe=0.72)
    log.append_trial(sprint=33, symbol="SOLUSDT", oos_sharpe=0.61)

    entries = log.get_entries()
    assert len(entries) == 3
    assert {e["symbol"] for e in entries} == {"BTCUSDT", "ETHUSDT", "SOLUSDT"}


def test_append_without_symbol_defaults_to_BTCUSDT(tmp_path: Path) -> None:
    """Backward-compat: append_trial без symbol → defaults BTCUSDT (preserves legacy callers)."""
    p = tmp_path / "trials.json"
    log = CrossTrialLog(path=p)
    log.append_trial(sprint=13, oos_sharpe=-44.46)  # legacy call signature

    entries = log.get_entries()
    assert len(entries) == 1
    assert entries[0]["symbol"] == "BTCUSDT"


def test_n_trials_counts_all_entries_protocol_a(tmp_path: Path) -> None:
    """Per Item #7 pooling protocol (a): n_trials = total entries (NOT unique sprints).

    S33 multi-symbol: 1 sprint × 3 symbols → n_trials=3 (correct multi-testing penalty).
    """
    p = tmp_path / "trials.json"
    log = CrossTrialLog(path=p)
    log.append_trial(sprint=33, symbol="BTCUSDT", oos_sharpe=0.85)
    log.append_trial(sprint=33, symbol="ETHUSDT", oos_sharpe=0.72)
    log.append_trial(sprint=33, symbol="SOLUSDT", oos_sharpe=0.61)
    assert log.n_trials() == 3  # 3 separate trials per protocol (a), не 1 sprint


def test_legacy_persisted_data_round_trips_with_symbol_backfilled(tmp_path: Path) -> None:
    """Append к legacy file: backfilled BTCUSDT preserved across re-load."""
    p = tmp_path / "legacy.json"
    p.write_text(json.dumps({"trials": [{"sprint": 22, "oos_sharpe": 0.996}]}))
    log = CrossTrialLog(path=p)
    log.append_trial(sprint=33, symbol="ETHUSDT", oos_sharpe=0.5)

    re_read = CrossTrialLog(path=p)
    entries = re_read.get_entries()
    assert len(entries) == 2
    assert entries[0]["symbol"] == "BTCUSDT"  # legacy backfilled
    assert entries[1]["symbol"] == "ETHUSDT"  # new explicit


def test_get_oos_sharpes_legacy_compat(tmp_path: Path) -> None:
    """get_oos_sharpes() returns ordered list (no symbol filter) — backward-compat method."""
    p = tmp_path / "trials.json"
    log = CrossTrialLog(path=p)
    log.append_trial(sprint=33, symbol="BTCUSDT", oos_sharpe=0.85)
    log.append_trial(sprint=33, symbol="ETHUSDT", oos_sharpe=0.72)
    assert log.get_oos_sharpes() == [0.85, 0.72]
