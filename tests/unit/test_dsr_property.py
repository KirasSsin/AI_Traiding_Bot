"""S47 T12 — DSR ∈ [0,1] property test (test-engineer S44 C2).

compute_dsr takes a list[TradeRecord] — we build synthetic trades from
hypothesis-generated pnl_pct values to exercise the full numeric pipeline.
NaN is allowed for degenerate inputs (zero variance, < 2 trades, etc.).
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import hypothesis.strategies as st
from hypothesis import given, settings
from src.analytics.dsr import compute_dsr
from src.risk.reason_codes import ReasonCode
from src.risk.trade_history import TradeRecord


def _make_trade(pnl_pct: float, hours_offset: int = 0) -> TradeRecord:
    """Build a minimal valid TradeRecord for a given pnl_pct return."""
    base = datetime(2024, 1, 1, tzinfo=UTC)
    qty = Decimal("0.001")
    entry = Decimal("50000")
    notional = qty * entry
    # Clamp pnl_pct above -1 to avoid invalid exit_price
    safe_pct = max(pnl_pct, -0.999)
    pnl_quote = Decimal(str(round(safe_pct, 8))) * notional
    exit_price = entry + (pnl_quote / qty)
    if exit_price <= Decimal("0"):
        exit_price = Decimal("1")  # guard against non-positive exit price
    return TradeRecord(
        symbol="BTCUSDT",
        entry_signal_id=uuid4(),
        entry_ts=base + timedelta(hours=hours_offset),
        exit_ts=base + timedelta(hours=hours_offset + 1),
        qty=qty,
        entry_price=entry,
        exit_price=exit_price,
        pnl_quote=pnl_quote,
        pnl_pct=Decimal(str(round(safe_pct, 8))),
        fees_paid=Decimal("0.0"),
        reason_code=ReasonCode.EXIT_TP_HIT,
        kelly_phase=1,
        recorded_at=base,
    )


@given(
    pnl_pcts=st.lists(
        st.floats(min_value=-0.5, max_value=0.5, allow_nan=False, allow_infinity=False),
        min_size=2,
        max_size=200,
    ),
    n_trials=st.just(1),  # n_trials=1 avoids sigma_sr requirement
)
@settings(max_examples=200, deadline=None)
def test_dsr_in_unit_interval(pnl_pcts: list[float], n_trials: int) -> None:
    """DSR semantics: probability ∈ [0, 1]. NaN OK for degenerate inputs."""
    trades = [_make_trade(p, i) for i, p in enumerate(pnl_pcts)]
    dsr = compute_dsr(trades, n_trials=n_trials)
    if math.isnan(dsr):
        return  # NaN allowed for edge cases (zero variance, etc.)
    assert 0.0 <= dsr <= 1.0, f"DSR={dsr} outside [0,1] for n_trades={len(trades)}"
