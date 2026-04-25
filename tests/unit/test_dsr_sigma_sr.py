"""Tests for DSR sigma_sr extension (Bailey eq. 12 для n_trials > 1).

Sprint 10 Q7 (per pre-s10-backlog.md verdict — closes S9 NotImplementedError).
quant-stats-reviewer MANDATORY post-implementation per cross-cutting concern #4.
"""
from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from src.analytics.dsr import compute_dsr
from src.risk.reason_codes import ReasonCode
from src.risk.trade_history import TradeRecord


def _make_trade(*, pnl_pct: Decimal, exit_offset_hours: int) -> TradeRecord:
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
        recorded_at=datetime(2026, 4, 25, 12, 1, 0, tzinfo=UTC),
    )


def test_n_trials_gt_1_requires_sigma_sr() -> None:
    """n_trials > 1 без sigma_sr raises ValueError (no longer NotImplementedError)."""
    trades = [
        _make_trade(pnl_pct=Decimal(f"0.0{i}"), exit_offset_hours=i)
        for i in range(1, 11)
    ]
    with pytest.raises(ValueError, match="sigma_sr"):
        compute_dsr(trades, n_trials=5)


def test_n_trials_gt_1_с_sigma_sr_returns_finite() -> None:
    """n_trials=5 + sigma_sr=0.1 returns finite DSR (Bailey eq. 12 applied)."""
    trades = [
        _make_trade(
            pnl_pct=Decimal("0.01") if i % 2 == 0 else Decimal("-0.005"),
            exit_offset_hours=i,
        )
        for i in range(1, 21)
    ]
    result = compute_dsr(trades, n_trials=5, sigma_sr=0.1)
    assert math.isfinite(result)
    assert 0.0 <= result <= 1.0


def test_n_trials_1_unchanged_behavior() -> None:
    """n_trials=1 (default) ignores sigma_sr, behaves как S9 baseline."""
    trades = [
        _make_trade(
            pnl_pct=Decimal("0.01") if i % 2 == 0 else Decimal("-0.005"),
            exit_offset_hours=i,
        )
        for i in range(1, 11)
    ]
    result_no_sigma = compute_dsr(trades, n_trials=1)
    result_with_sigma = compute_dsr(trades, n_trials=1, sigma_sr=0.5)
    assert result_no_sigma == result_with_sigma


def test_higher_n_trials_lowers_dsr() -> None:
    """Higher n_trials = stronger multi-testing penalty = lower DSR."""
    trades = [
        _make_trade(
            pnl_pct=Decimal("0.01") if i % 3 != 0 else Decimal("-0.005"),
            exit_offset_hours=i,
        )
        for i in range(1, 21)
    ]
    dsr_low_trials = compute_dsr(trades, n_trials=2, sigma_sr=0.1)
    dsr_high_trials = compute_dsr(trades, n_trials=20, sigma_sr=0.1)
    assert dsr_high_trials <= dsr_low_trials
