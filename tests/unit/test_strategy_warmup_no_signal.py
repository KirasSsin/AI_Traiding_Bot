"""Strategy.warmup feeds catch-up bars to rolling buffer without emitting signals.

ADR 0022 sub-decision 2: prevents look-ahead trades on historical data after restart.
ADR 0022 sub-decision 8: look-ahead invariant (warmup MUST NOT emit).
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from src.marketdata.models import Bar, DataQuality
from src.signalgen.strategy import EmaCrossoverAdxRsiStrategy


def _bars(n: int) -> list[Bar]:
    out: list[Bar] = []
    base = datetime(2026, 1, 1, tzinfo=UTC)
    for i in range(n):
        out.append(
            Bar(
                symbol="BTCUSDT",
                interval="1h",
                open_time=base + timedelta(hours=i),
                close_time=base + timedelta(hours=i + 1),
                open=Decimal("60000") + Decimal(i),
                high=Decimal("60100") + Decimal(i),
                low=Decimal("59900") + Decimal(i),
                close=Decimal("60050") + Decimal(i),
                volume=Decimal("10"),
                trade_count=0,
                is_closed=True,
                data_quality=DataQuality.OK,
            )
        )
    return out


def _strat() -> EmaCrossoverAdxRsiStrategy:
    return EmaCrossoverAdxRsiStrategy(
        symbol="BTCUSDT",
        ema_fast=12,
        ema_slow=26,
        adx_period=14,
        adx_threshold=Decimal("25"),
        rsi_period=14,
        rsi_oversold=Decimal("30"),
        rsi_overbought=Decimal("70"),
        atr_period=14,
    )


def test_warmup_50_bars_emits_zero_signals() -> None:
    """warmup(bar) must always return None — never emit signals."""
    s = _strat()
    bars = _bars(50)
    for b in bars:
        result = s.warmup(b)
        assert result is None, f"warmup returned non-None: {result!r}"


def test_warmup_seeds_buffer_for_subsequent_on_bar() -> None:
    """After warmup of N bars, buffer length matches min(N, buffer_size)."""
    s = _strat()
    for b in _bars(50):
        s.warmup(b)
    # buffer_size = max(26, 28, 14, 14) + 5 = 33; we fed 50 → buffer truncated to 33
    # Use private attr access intentionally — we're testing internal seeding contract.
    assert len(s._bars) == s._buffer_size, (
        f"expected buffer to be filled to {s._buffer_size}, got {len(s._bars)}"
    )


def test_warmup_then_on_bar_does_not_raise() -> None:
    """After warmup, on_bar of a subsequent bar runs the full pipeline (no exception).

    Не утверждаем что sig != None (зависит от данных) — только что вызов не raise
    и indicators seeded достаточно чтобы пройти warm-up gate.
    """
    s = _strat()
    for b in _bars(50):
        s.warmup(b)
    new_bar = _bars(51)[-1]  # 51st bar via on_bar
    sig = s.on_bar(new_bar)
    assert sig is None or hasattr(sig, "side"), "on_bar must return Signal-like or None"


def test_warmup_filters_non_closed_and_wrong_symbol() -> None:
    """warmup MUST apply same filter rules as on_bar (closed, symbol match, monotonic)."""
    s = _strat()
    closed_bar = _bars(1)[0]
    # Non-closed bar — must be filtered out
    open_bar = closed_bar.model_copy(update={"is_closed": False})
    s.warmup(open_bar)
    assert len(s._bars) == 0, "non-closed bar must be filtered out by warmup"
    # Wrong symbol — must be filtered out
    foreign_bar = closed_bar.model_copy(update={"symbol": "ETHUSDT"})
    s.warmup(foreign_bar)
    assert len(s._bars) == 0, "wrong-symbol bar must be filtered out by warmup"
    # Closed BTCUSDT bar — must be appended
    s.warmup(closed_bar)
    assert len(s._bars) == 1, "closed BTCUSDT bar must be appended"
