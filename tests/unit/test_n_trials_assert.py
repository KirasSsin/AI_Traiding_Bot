"""S47 T12 — n_trials >=1 assert test (S45 quant follow-up).

compute_dsr: n_trials=0 or negative makes no sense — multiple-comparisons
correction references log(n_trials) / 1/n_trials; zero/negative are undefined.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from src.analytics.dsr import compute_dsr
from src.risk.reason_codes import ReasonCode
from src.risk.trade_history import TradeRecord


def _make_trade(pnl_pct: float, hours_offset: int = 0) -> TradeRecord:
    base = datetime(2024, 1, 1, tzinfo=UTC)
    qty = Decimal("0.001")
    entry = Decimal("50000")
    notional = qty * entry
    pnl_quote = Decimal(str(pnl_pct)) * notional
    exit_price = entry + (pnl_quote / qty)
    return TradeRecord(
        symbol="BTCUSDT",
        entry_signal_id=uuid4(),
        entry_ts=base + timedelta(hours=hours_offset),
        exit_ts=base + timedelta(hours=hours_offset + 1),
        qty=qty,
        entry_price=entry,
        exit_price=exit_price,
        pnl_quote=pnl_quote,
        pnl_pct=Decimal(str(pnl_pct)),
        fees_paid=Decimal("0.0"),
        reason_code=ReasonCode.EXIT_TP_HIT,
        kelly_phase=1,
        recorded_at=base,
    )


_TRADES = [_make_trade(0.01, i) for i in range(10)]


def test_n_trials_zero_raises() -> None:
    """n_trials=0 must raise — multiple-comparisons correction divides by N."""
    with pytest.raises((ValueError, AssertionError)):
        compute_dsr(_TRADES, n_trials=0)


def test_n_trials_negative_raises() -> None:
    """n_trials=-5 must raise — negative trial count is nonsensical."""
    with pytest.raises((ValueError, AssertionError)):
        compute_dsr(_TRADES, n_trials=-5)


def test_n_trials_one_works() -> None:
    """n_trials=1 = no multiple-comparisons correction (single trial), must not raise."""
    result = compute_dsr(_TRADES, n_trials=1)
    # Result is float (possibly NaN for degenerate inputs; not an exception)
    assert isinstance(result, float)
