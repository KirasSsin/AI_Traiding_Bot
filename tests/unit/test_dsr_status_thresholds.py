"""S36 T6 ADR 0056 — DSR n_trades thresholds.

n_trades < 10:  DSR=NaN, status=INSUFFICIENT_TRADES
10 <= n < 30:   DSR computed, status=UNDERPOWERED
n >= 30:        DSR computed, status=GATE_ELIGIBLE
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from src.analytics.dsr import compute_dsr_with_status
from src.risk.reason_codes import ReasonCode
from src.risk.trade_history import TradeRecord


def _make_trades(n: int) -> list[TradeRecord]:
    """Build n synthetic TradeRecords with non-zero variance в pnl_pct."""
    base = datetime(2026, 1, 1, tzinfo=UTC)
    trades: list[TradeRecord] = []
    for i in range(n):
        # Vary pnl_pct so DSR is finite (variance > 0).
        pct = Decimal("0.01") if i % 2 == 0 else Decimal("-0.005")
        trades.append(
            TradeRecord(
                symbol="BTCUSDT",
                entry_signal_id=uuid4(),
                entry_ts=base + timedelta(hours=i),
                exit_ts=base + timedelta(hours=i, minutes=30),
                qty=Decimal("0.1"),
                entry_price=Decimal("50000"),
                exit_price=Decimal("50000") * (Decimal("1") + pct),
                pnl_quote=Decimal("10"),
                pnl_pct=pct,
                fees_paid=Decimal("0.1"),
                reason_code=ReasonCode.EXIT_SL_HIT,
                kelly_phase=1,
                recorded_at=base + timedelta(hours=i, minutes=30),
            )
        )
    return trades


def test_dsr_nan_status_insufficient_when_n_below_10() -> None:
    """ADR 0056: n_trades < 10 → DSR=NaN + INSUFFICIENT_TRADES."""
    result = compute_dsr_with_status(trades=_make_trades(5), n_trials=1)
    assert math.isnan(result["dsr"])
    assert result["status"] == "INSUFFICIENT_TRADES"
    assert result["n_trades"] == 5


def test_dsr_underpowered_when_n_in_10_30_range() -> None:
    """ADR 0056: 10 <= n < 30 → DSR computed + UNDERPOWERED."""
    result = compute_dsr_with_status(trades=_make_trades(15), n_trials=1)
    assert not math.isnan(result["dsr"])
    assert result["status"] == "UNDERPOWERED"
    assert result["n_trades"] == 15


def test_dsr_gate_eligible_when_n_above_30() -> None:
    """ADR 0056: n >= 30 → DSR computed + GATE_ELIGIBLE."""
    result = compute_dsr_with_status(trades=_make_trades(35), n_trials=1)
    assert not math.isnan(result["dsr"])
    assert result["status"] == "GATE_ELIGIBLE"
    assert result["n_trades"] == 35
