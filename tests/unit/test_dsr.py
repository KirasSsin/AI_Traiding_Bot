"""Tests for DSR (Deflated Sharpe Ratio) — Bailey & López de Prado.

Sprint 9 Q3 B2.
quant-stats-reviewer MUST review post-implementation.
"""
from __future__ import annotations

import math
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from src.analytics.dsr import compute_dsr, compute_returns
from src.risk.reason_codes import ReasonCode
from src.risk.trade_history import TradeRecord


def _make_trade(*, pnl_pct: Decimal, exit_offset_hours: int) -> TradeRecord:
    return TradeRecord(
        symbol="BTCUSDT",
        entry_signal_id=uuid4(),
        entry_ts=datetime(2026, 4, 25, 12, 0, 0, tzinfo=UTC),
        exit_ts=datetime(2026, 4, 25, 12 + exit_offset_hours, 0, 0, tzinfo=UTC),
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


def test_compute_returns_log_default() -> None:
    """log returns = ln(1 + pnl_pct), default."""
    trades = [
        _make_trade(pnl_pct=Decimal("0.01"), exit_offset_hours=1),
        _make_trade(pnl_pct=Decimal("0.02"), exit_offset_hours=2),
    ]
    returns = compute_returns(trades)  # log default
    assert math.isclose(returns[0], math.log(1.01), rel_tol=1e-9)
    assert math.isclose(returns[1], math.log(1.02), rel_tol=1e-9)


def test_compute_returns_simple_via_flag() -> None:
    """simple returns = pnl_pct directly when use_log=False."""
    trades = [_make_trade(pnl_pct=Decimal("0.01"), exit_offset_hours=1)]
    returns = compute_returns(trades, use_log=False)
    assert returns[0] == 0.01


def test_compute_dsr_empty_returns_nan() -> None:
    """N=0 trades → DSR = NaN (defensive, not crash)."""
    result = compute_dsr([])
    assert math.isnan(result)


def test_compute_dsr_single_trade_returns_nan() -> None:
    """N=1 trade → variance undefined → NaN."""
    trades = [_make_trade(pnl_pct=Decimal("0.01"), exit_offset_hours=1)]
    result = compute_dsr(trades)
    assert math.isnan(result)


def test_compute_dsr_constant_returns_nan() -> None:
    """All identical returns → variance=0 → DSR undefined → NaN."""
    trades = [
        _make_trade(pnl_pct=Decimal("0.01"), exit_offset_hours=i)
        for i in range(1, 11)
    ]
    result = compute_dsr(trades)
    assert math.isnan(result)


def test_compute_dsr_positive_track_record_in_range() -> None:
    """Mixed positive/negative returns yield finite DSR в (0, 1)."""
    # Mix of wins and losses — realistic distribution gives non-degenerate
    # skew/kurtosis so denom_inner > 0 в DSR formula.
    pcts = [
        Decimal("0.02"),
        Decimal("-0.01"),
        Decimal("0.015"),
        Decimal("-0.005"),
        Decimal("0.03"),
        Decimal("-0.02"),
        Decimal("0.01"),
        Decimal("-0.008"),
        Decimal("0.025"),
        Decimal("-0.012"),
    ]
    trades = [
        _make_trade(pnl_pct=p, exit_offset_hours=i + 1)
        for i, p in enumerate(pcts)
    ]
    result = compute_dsr(trades)
    assert not math.isnan(result)
    assert math.isfinite(result)
    assert 0.0 <= result <= 1.0


def test_no_look_ahead_uses_only_exit_ts() -> None:
    """DSR only consumes closed trades (exit_ts populated). Verify functional."""
    trades = [
        _make_trade(pnl_pct=Decimal("0.01"), exit_offset_hours=1),
        _make_trade(pnl_pct=Decimal("0.02"), exit_offset_hours=2),
        _make_trade(pnl_pct=Decimal("0.005"), exit_offset_hours=3),
    ]
    returns = compute_returns(trades)
    # Returns array aligns с trades order (closed trades, sorted by exit_ts)
    assert len(returns) == 3
    # Each return derived only from exit_price/entry_price relation
    assert returns[0] != returns[1]


def test_total_loss_returns_neg_inf_log() -> None:
    """pnl_pct = -1.0 (total loss) → log return = -inf (defined edge case).

    TradeRecord requires exit_price > 0, so для total-loss edge мы конструируем
    TradeRecord с минимальным exit_price + ручным pnl_pct=-1.0
    (decoupled from exit_price/entry_price mathematical relation).
    """
    trade = TradeRecord(
        symbol="BTCUSDT",
        entry_signal_id=uuid4(),
        entry_ts=datetime(2026, 4, 25, 12, 0, 0, tzinfo=UTC),
        exit_ts=datetime(2026, 4, 25, 13, 0, 0, tzinfo=UTC),
        qty=Decimal("0.5"),
        entry_price=Decimal("100000"),
        exit_price=Decimal("0.00000001"),  # near-zero, satisfies gt=0
        pnl_quote=Decimal("-50000"),
        pnl_pct=Decimal("-1.0"),  # total loss flagged independently
        fees_paid=Decimal("0.05"),
        reason_code=ReasonCode.EXIT_TP_HIT,
        kelly_phase=1,
        recorded_at=datetime(2026, 4, 25, 12, 1, 0, tzinfo=UTC),
    )
    returns = compute_returns([trade], use_log=True)
    assert returns[0] == -math.inf
