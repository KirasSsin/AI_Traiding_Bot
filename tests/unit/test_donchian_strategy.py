"""Donchian breakout long-only strategy tests (S35 α track per ADR 0054 LOCKED)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from src.marketdata.models import Bar, DataQuality
from src.signalgen.donchian_strategy import (
    DONCHIAN_LONG_ONLY_PARAMS,
    DonchianBreakoutStrategy,
)
from src.signalgen.models import SignalSide


def _bar(close_time: datetime, *, h: float, low: float, c: float, o: float | None = None) -> Bar:
    return Bar(
        symbol="BTCUSDT",
        interval="4h",
        open_time=close_time - timedelta(hours=4),
        close_time=close_time,
        open=Decimal(str(o if o is not None else c)),
        high=Decimal(str(h)),
        low=Decimal(str(low)),
        close=Decimal(str(c)),
        volume=Decimal("100"),
        trade_count=1,
        is_closed=True,
        data_quality=DataQuality.OK,
    )


def _strategy() -> DonchianBreakoutStrategy:
    return DonchianBreakoutStrategy(
        symbol="BTCUSDT",
        lookback_n=int(DONCHIAN_LONG_ONLY_PARAMS["lookback_n"]),  # type: ignore[arg-type]
        exit_lookback_n=int(DONCHIAN_LONG_ONLY_PARAMS["exit_lookback_n"]),  # type: ignore[arg-type]
        atr_period=int(DONCHIAN_LONG_ONLY_PARAMS["atr_period"]),  # type: ignore[arg-type]
        atr_stop_mult=Decimal(str(DONCHIAN_LONG_ONLY_PARAMS["atr_stop_mult"])),
    )


def test_warmup_no_signal_until_buffer_full() -> None:
    s = _strategy()
    base = datetime(2026, 1, 1, 4, tzinfo=UTC)
    for i in range(15):  # less than lookback_n=20
        sig = s.on_bar(_bar(base + timedelta(hours=4 * i), h=100 + i, low=99 + i, c=99.5 + i))
        assert sig is None, f"premature signal at bar {i}"


def test_breakout_above_donchian_high_emits_long_signal() -> None:
    s = _strategy()
    base = datetime(2026, 1, 1, 4, tzinfo=UTC)
    # Fill buffer с flat range 100-105
    for i in range(25):
        s.on_bar(_bar(base + timedelta(hours=4 * i), h=105.0, low=100.0, c=102.0))
    # Breakout bar: close > prior 20-bar high
    breakout_bar = _bar(
        base + timedelta(hours=4 * 25),
        h=110.0,
        low=104.0,
        c=109.0,  # close > 105
    )
    sig = s.on_bar(breakout_bar)
    assert sig is not None
    assert sig.side == SignalSide.LONG
    assert sig.reason == "ENTRY_LONG_DONCHIAN_BREAKOUT"


def test_long_only_invariant_no_short_signals() -> None:
    """ADR 0054 LOCKED: signal_side_mode=long_only — strategy NEVER emits SHORT."""
    s = _strategy()
    base = datetime(2026, 1, 1, 4, tzinfo=UTC)
    # Fill buffer
    for i in range(25):
        s.on_bar(_bar(base + timedelta(hours=4 * i), h=105.0, low=100.0, c=102.0))
    # Breakdown below low (would be SHORT in symmetric Donchian)
    breakdown = _bar(
        base + timedelta(hours=4 * 25),
        h=101.0,
        low=95.0,
        c=96.0,  # close < 100
    )
    sig = s.on_bar(breakdown)
    # Long-only invariant: SHORT never в SignalSide enum в v0.1, but assert defensively
    if sig is not None:
        assert sig.side != "SHORT", "long-only invariant violated — SHORT emitted"


def test_atr_stop_exit_when_in_long() -> None:
    """When LONG, exit if close < entry_close - 2 × ATR."""
    s = _strategy()
    base = datetime(2026, 1, 1, 4, tzinfo=UTC)
    # Fill buffer + breakout entry
    for i in range(25):
        s.on_bar(_bar(base + timedelta(hours=4 * i), h=105.0, low=100.0, c=102.0))
    s.on_bar(_bar(base + timedelta(hours=4 * 25), h=110.0, low=104.0, c=109.0))  # LONG entry
    # Sharp drop > 2×ATR below entry close
    crash_bar = _bar(base + timedelta(hours=4 * 26), h=109.0, low=80.0, c=82.0)
    sig = s.on_bar(crash_bar)
    assert sig is not None
    assert sig.side == SignalSide.FLAT
    assert sig.reason == "EXIT_FLAT_ATR_STOP"
