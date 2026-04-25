"""Tests for WFA reporter (3-series Sharpe routing per cross-cutting concern #1).

Sprint 10 Q4 + Q6 + Q7 (per pre-s10-backlog.md cross-cutting concerns).
"""
from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import numpy as np
import pandas as pd
from src.backtest.wfa_reporter import format_wfa_report
from src.risk.reason_codes import ReasonCode
from src.risk.trade_history import TradeRecord


def _make_trade_record(*, pnl_pct: Decimal, exit_offset_hours: int) -> TradeRecord:
    entry = datetime(2026, 4, 25, 12, 0, 0, tzinfo=UTC)
    return TradeRecord(
        symbol="BTCUSDT",
        entry_signal_id=uuid4(),
        entry_ts=entry,
        exit_ts=entry + timedelta(hours=exit_offset_hours),
        qty=Decimal("0.5"),
        entry_price=Decimal("100000"),
        exit_price=Decimal("100000") * (Decimal("1") + pnl_pct),
        pnl_quote=Decimal("100"),
        pnl_pct=pnl_pct,
        fees_paid=Decimal("0.05"),
        reason_code=ReasonCode.EXIT_TP_HIT,
        kelly_phase=1,
        recorded_at=entry + timedelta(hours=exit_offset_hours, minutes=1),
    )


def _empty_runner_result() -> dict:
    return {"folds": [], "aggregate": {"oos_trades_df": pd.DataFrame(),
                                          "k_folds": 0, "fold_oos_sharpes": []}}


def test_report_contains_three_sharpe_series() -> None:
    """Report routes 3 distinct Sharpe series (cross-cutting concern #1)."""
    runner_result = {
        "folds": [
            {
                "fold_idx": 0,
                "is_metrics": {"Sharpe Ratio": 1.5},
                "oos_metrics": {"Sharpe Ratio": 1.2},
                "oos_is_sharpe_ratio": 0.8,
                "oos_trades_df": pd.DataFrame({"net_pnl": [10.0]}),
                "train_window": (0, 2000),
                "test_window": (2020, 2520),
            },
        ],
        "aggregate": {
            "oos_trades_df": pd.DataFrame({"net_pnl": [10.0]}),
            "k_folds": 1,
            "fold_oos_sharpes": [1.2],
        },
    }
    trades_for_dsr = [_make_trade_record(pnl_pct=Decimal("0.01"),
                                          exit_offset_hours=i) for i in range(1, 11)]
    gate_result = {"passed": True, "sharpe_gate_passed": True, "mc_gate_passed": True,
                   "failed_folds": [], "fold_sharpe_ratios": [0.8], "mc_p_value": 0.02,
                   "thresholds": {"sharpe": 0.7, "p_value": 0.05}}

    report = format_wfa_report(
        runner_result=runner_result,
        trades_for_dsr=trades_for_dsr,
        mc_p_value=0.02,
        gate_result=gate_result,
    )

    assert "bar_returns_sharpe_per_fold" in report
    assert "per_trade_sharpe" in report
    assert "display_sharpe" in report


def test_report_includes_dsr_aggregate_informational() -> None:
    """DSR computed across all OOS trades (informational, NOT gate)."""
    runner_result = {
        "folds": [
            {"fold_idx": i, "is_metrics": {"Sharpe Ratio": 1.5},
             "oos_metrics": {"Sharpe Ratio": 1.2}, "oos_is_sharpe_ratio": 0.8,
             "oos_trades_df": pd.DataFrame(), "train_window": (0, 0),
             "test_window": (0, 0)}
            for i in range(5)
        ],
        "aggregate": {"oos_trades_df": pd.DataFrame(), "k_folds": 5,
                      "fold_oos_sharpes": [1.2, 1.0, 1.3, 1.1, 1.4]},
    }
    trades_for_dsr = [_make_trade_record(pnl_pct=Decimal("0.01") if i % 2 == 0
                                           else Decimal("-0.005"),
                                           exit_offset_hours=i) for i in range(1, 21)]
    gate_result = {"passed": True, "sharpe_gate_passed": True, "mc_gate_passed": True,
                   "failed_folds": [], "fold_sharpe_ratios": [0.8]*5, "mc_p_value": 0.02,
                   "thresholds": {"sharpe": 0.7, "p_value": 0.05}}

    report = format_wfa_report(
        runner_result=runner_result,
        trades_for_dsr=trades_for_dsr,
        mc_p_value=0.02,
        gate_result=gate_result,
    )

    assert "dsr_aggregate" in report
    assert math.isfinite(report["dsr_aggregate"])
    assert "dsr_per_fold" in report


def test_report_passes_through_gate_result() -> None:
    """Gate result included verbatim в report."""
    gate_result = {"passed": False, "sharpe_gate_passed": True, "mc_gate_passed": False,
                   "failed_folds": [], "fold_sharpe_ratios": [], "mc_p_value": 0.10,
                   "thresholds": {"sharpe": 0.7, "p_value": 0.05}}

    report = format_wfa_report(
        runner_result=_empty_runner_result(),
        trades_for_dsr=[],
        mc_p_value=0.10,
        gate_result=gate_result,
    )

    assert report["acceptance_gate"] == gate_result


def test_display_sharpe_uses_fixed_8760_factor() -> None:
    """Display Sharpe annualized с sqrt(8760) per Q6 (NOT derived from trade frequency)."""
    trades_for_dsr = [_make_trade_record(pnl_pct=Decimal("0.01") if i % 2 == 0
                                           else Decimal("-0.005"),
                                           exit_offset_hours=i) for i in range(1, 21)]
    gate_result = {"passed": True, "sharpe_gate_passed": True, "mc_gate_passed": True,
                   "failed_folds": [], "fold_sharpe_ratios": [], "mc_p_value": 0.02,
                   "thresholds": {"sharpe": 0.7, "p_value": 0.05}}

    report = format_wfa_report(
        runner_result=_empty_runner_result(),
        trades_for_dsr=trades_for_dsr,
        mc_p_value=0.02,
        gate_result=gate_result,
    )

    assert "display_sharpe" in report
    assert math.isfinite(report["display_sharpe"])
    assert report["display_sharpe_annualization_factor"] == np.sqrt(8760)
