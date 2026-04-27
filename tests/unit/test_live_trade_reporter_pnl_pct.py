"""S38 T2 F2 fix — compute_live_sharpe returns extracted from pnl_pct (NOT pnl_quote).

Per ROUND 6 quant-stats-reviewer F2 HIGH + ADR 0056 amendment 2:
  Sharpe formula requires dimensionless returns commensurable across trade sizes.
  pnl_quote scales с position size — Kelly variance bias.
  pnl_pct = correct fractional returns.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from src.analytics.live_trade_reporter import compute_live_sharpe
from src.risk.reason_codes import ReasonCode
from src.risk.trade_history import TradeRecord


def _trade(*, pnl_quote: Decimal, pnl_pct: Decimal, exit_ts: datetime) -> TradeRecord:
    return TradeRecord(
        symbol="BTCUSDT",
        entry_signal_id=uuid4(),
        entry_ts=exit_ts - timedelta(minutes=30),
        exit_ts=exit_ts,
        qty=Decimal("0.1"),
        entry_price=Decimal("50000"),
        exit_price=Decimal("50000") + pnl_quote if pnl_quote != Decimal("0") else Decimal("50001"),
        pnl_quote=pnl_quote,
        pnl_pct=pnl_pct,
        fees_paid=Decimal("0.1"),
        reason_code=ReasonCode.EXIT_SL_HIT,
        kelly_phase=1,
        recorded_at=exit_ts,
    )


def test_sharpe_uses_pnl_pct_not_pnl_quote() -> None:
    """ROUND 6 F2: returns must use pnl_pct, NOT pnl_quote.

    Construct trades с identical pnl_pct но varying pnl_quote (varying position sizes).
    Sharpe should depend ONLY on pnl_pct (dimensionless), NOT pnl_quote (size-biased).
    """
    base = datetime(2026, 1, 1, tzinfo=UTC)
    # 12 trades с alternating wins/losses, identical pnl_pct (±0.01) но varying pnl_quote
    trades_small = [
        _trade(
            pnl_quote=Decimal("100") * (Decimal("1") if i % 2 == 0 else Decimal("-1")),
            pnl_pct=Decimal("0.01") * (Decimal("1") if i % 2 == 0 else Decimal("-1")),
            exit_ts=base + timedelta(hours=i),
        )
        for i in range(12)
    ]
    # Same pnl_pct, BUT pnl_quote scaled 10x (larger position size)
    trades_large = [
        _trade(
            pnl_quote=Decimal("1000") * (Decimal("1") if i % 2 == 0 else Decimal("-1")),
            pnl_pct=Decimal("0.01") * (Decimal("1") if i % 2 == 0 else Decimal("-1")),
            exit_ts=base + timedelta(hours=i),
        )
        for i in range(12)
    ]
    sharpe_small = compute_live_sharpe(trades_small)["sharpe"]
    sharpe_large = compute_live_sharpe(trades_large)["sharpe"]
    # Sharpe should be IDENTICAL (pnl_pct same) — pnl_quote scaling должен НЕ matter
    assert sharpe_small == pytest.approx(sharpe_large, abs=1e-9)


def test_sharpe_pnl_pct_extraction_correct_value() -> None:
    """Verify Sharpe computed на pnl_pct values produces expected magnitude."""
    base = datetime(2026, 1, 1, tzinfo=UTC)
    # 12 trades с known pnl_pct: alternating +0.02 / -0.01
    trades = [
        _trade(
            pnl_quote=Decimal("1") if i % 2 == 0 else Decimal("-1"),  # quote irrelevant
            pnl_pct=Decimal("0.02") if i % 2 == 0 else Decimal("-0.01"),
            exit_ts=base + timedelta(hours=i),
        )
        for i in range(12)
    ]
    result = compute_live_sharpe(trades, bars_per_year=2190, avg_bars_per_trade=12.0)
    # Mean = (0.02*6 + -0.01*6) / 12 = 0.005
    # Sharpe positive (mean > 0)
    assert result["sharpe"] > 0
    assert result["status"] == "UNDERPOWERED"  # n=12 < 30


def test_sharpe_zero_variance_pnl_pct_returns_degenerate() -> None:
    """Defensive: pnl_pct constant → DEGENERATE_VARIANCE status."""
    base = datetime(2026, 1, 1, tzinfo=UTC)
    trades = [
        _trade(
            pnl_quote=Decimal("100"),
            pnl_pct=Decimal("0.001"),  # constant
            exit_ts=base + timedelta(hours=i),
        )
        for i in range(12)
    ]
    result = compute_live_sharpe(trades)
    assert result["status"] == "DEGENERATE_VARIANCE"
