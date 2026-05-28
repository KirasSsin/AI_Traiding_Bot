"""S49 BATCH 5 (M1+M6) — balance compounding + RunRecord length assert.

M1: final_balance must compound geometrically Π(1 + pnl_pct_i), NOT additive sum.
M6: get_run must guard equity_curve parallel-array length mismatch.
"""

from __future__ import annotations

import json

import pytest
from src.dashboard.backtest_runner import (
    _compound_balance,
    _compound_equity_pct,
    get_run,
)


# --- M1: geometric compounding ---
def test_compound_balance_three_winners() -> None:
    # 3 trades of +10% each → initial × 1.1^3 = initial × 1.331 (NOT × 1.30 additive).
    initial = 100.0
    pnl_pcts = [0.10, 0.10, 0.10]
    result = _compound_balance(initial, pnl_pcts)
    assert result == pytest.approx(133.1, abs=1e-9)


def test_compound_balance_single_trade() -> None:
    assert _compound_balance(100.0, [0.05]) == pytest.approx(105.0, abs=1e-9)


def test_compound_balance_all_loss() -> None:
    # Two -10% trades → 100 × 0.9 × 0.9 = 81.0.
    assert _compound_balance(100.0, [-0.10, -0.10]) == pytest.approx(81.0, abs=1e-9)


def test_compound_balance_no_trades() -> None:
    assert _compound_balance(100.0, []) == pytest.approx(100.0, abs=1e-9)


# --- M1: equity_pct cumulative compounded return series ---
def test_compound_equity_pct_three_winners() -> None:
    # Cumulative compounded % from initial: +10% → +21% → +33.1%.
    series = _compound_equity_pct([0.10, 0.10, 0.10])
    assert series[0] == pytest.approx(10.0, abs=1e-9)
    assert series[1] == pytest.approx(21.0, abs=1e-9)
    assert series[2] == pytest.approx(33.1, abs=1e-9)


def test_compound_equity_pct_empty() -> None:
    assert _compound_equity_pct([]) == []


# --- M6: get_run equity_curve length guard ---
def test_get_run_mismatched_equity_curve_lengths(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("src.dashboard.backtest_runner._RUNS_DIR", tmp_path)
    run_id = "abcdef0123456789"  # 16 lowercase hex (passes _is_valid_run_id)
    payload = {
        "run_id": run_id,
        "verdict": "PASS",
        "equity_curve": {
            "timestamps": [1, 2, 3],
            "equity_pct": [10.0, 20.0],  # length mismatch (3 vs 2)
            "trade_markers": None,
        },
    }
    (tmp_path / f"{run_id}.json").write_text(json.dumps(payload))
    with pytest.raises(AssertionError):
        get_run(run_id)


def test_get_run_matched_equity_curve_lengths(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("src.dashboard.backtest_runner._RUNS_DIR", tmp_path)
    run_id = "0123456789abcdef"
    payload = {
        "run_id": run_id,
        "verdict": "PASS",
        "equity_curve": {
            "timestamps": [1, 2, 3],
            "equity_pct": [10.0, 20.0, 30.0],
            "trade_markers": None,
        },
    }
    (tmp_path / f"{run_id}.json").write_text(json.dumps(payload))
    result = get_run(run_id)
    assert result is not None
    assert result["run_id"] == run_id
