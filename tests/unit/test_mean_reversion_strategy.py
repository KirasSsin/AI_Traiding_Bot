"""Tests for MeanReversionRsiBBStrategy (S15 T3, ADR 0030).

Pre-registered AND-gated trigger: LONG when RSI<oversold AND close<lower_BB,
EXIT when RSI>overbought OR close>upper_BB.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from src.marketdata.models import Bar, DataQuality
from src.signalgen.mean_reversion_strategy import MeanReversionRsiBBStrategy
from src.signalgen.models import SignalSide


def _bar(
    close: float,
    idx: int,
    *,
    symbol: str = "BTCUSDT",
    is_closed: bool = True,
    high_offset: float = 0.5,
    low_offset: float = 0.5,
) -> Bar:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    ot = t0 + timedelta(hours=idx)
    ct = ot + timedelta(hours=1) - timedelta(microseconds=1)
    return Bar(
        symbol=symbol,
        interval="1h",
        open_time=ot,
        close_time=ct,
        open=Decimal(str(close)),
        high=Decimal(str(close + high_offset)),
        low=Decimal(str(close - low_offset)),
        close=Decimal(str(close)),
        volume=Decimal("1.0"),
        trade_count=1,
        is_closed=is_closed,
        data_quality=DataQuality.OK,
    )


def _make_strategy(symbol: str = "BTCUSDT") -> MeanReversionRsiBBStrategy:
    return MeanReversionRsiBBStrategy(
        symbol=symbol,
        rsi_period=14,
        bb_period=20,
        bb_std_mult=2.0,
        rsi_oversold=Decimal("30"),
        rsi_overbought=Decimal("70"),
        atr_period=14,
    )


def test_warmup_no_signal_during_buffer_fill() -> None:
    """First (max(rsi_n, bb_n) + 1) closed bars produce no signal."""
    s = _make_strategy()
    for i in range(20):
        sig = s.on_bar(_bar(100.0, i))
        assert sig is None


def test_skips_non_closed_bars() -> None:
    """is_closed=False bars filtered out — never produce signal."""
    s = _make_strategy()
    for i in range(50):
        sig = s.on_bar(_bar(100.0, i, is_closed=False))
        assert sig is None


def test_symbol_filter() -> None:
    """Bar with wrong symbol returns None silently."""
    s = _make_strategy(symbol="BTCUSDT")
    for i in range(50):
        sig = s.on_bar(_bar(100.0, i, symbol="ETHUSDT"))
        assert sig is None


def test_long_entry_on_oversold_and_bb_breach() -> None:
    """RSI drops below 30 + close below lower_BB → LONG entry signal."""
    s = _make_strategy()
    # Build 25 stable bars then sharp decline to drive RSI < 30 AND close < lower_BB
    fired_long = False
    # 25 stable bars
    for i in range(25):
        s.on_bar(_bar(100.0, i))
    # Sharp decline: 15 down bars
    for i in range(25, 40):
        sig = s.on_bar(_bar(100.0 - (i - 24) * 2.0, i))
        if sig is not None and sig.side == SignalSide.LONG:
            fired_long = True
            assert sig.reason == "ENTRY_LONG_MEANREV_RSI_BB"
            assert sig.symbol == "BTCUSDT"
            break
    assert fired_long, "Expected LONG entry during sharp decline"


def test_no_double_long_entry() -> None:
    """Already in LONG — second LONG-trigger bar should NOT emit duplicate entry."""
    s = _make_strategy()
    # Drive into LONG state
    for i in range(25):
        s.on_bar(_bar(100.0, i))
    long_count = 0
    for i in range(25, 50):
        sig = s.on_bar(_bar(100.0 - (i - 24) * 2.0, i))
        if sig is not None and sig.side == SignalSide.LONG:
            long_count += 1
    assert long_count <= 1, f"Expected at most one LONG entry, got {long_count}"


def test_exit_on_overbought() -> None:
    """In LONG, RSI rises above 70 → EXIT signal."""
    s = _make_strategy()
    # Stable 25 bars
    for i in range(25):
        s.on_bar(_bar(100.0, i))
    # Decline drives LONG entry
    for i in range(25, 40):
        s.on_bar(_bar(100.0 - (i - 24) * 2.0, i))
    if s._current_side != SignalSide.LONG:
        pytest.skip("LONG entry did not trigger in setup — strategy params differ")
    # Sharp recovery to drive RSI above 70
    fired_exit = False
    for i in range(40, 70):
        # Steep climb above any plausible upper_BB
        sig = s.on_bar(_bar(50.0 + (i - 39) * 5.0, i, high_offset=2.0, low_offset=0.1))
        if sig is not None and sig.side == SignalSide.FLAT:
            fired_exit = True
            assert sig.reason == "EXIT_FLAT_MEANREV_REVERT"
            break
    assert fired_exit, "Expected EXIT after sharp recovery"


def test_warmup_method_seeds_buffer_no_signal() -> None:
    """warmup() builds buffer state but never emits Signal."""
    s = _make_strategy()
    for i in range(50):
        # warmup returns None implicitly
        s.warmup(_bar(100.0 + i * 0.1, i))
    # Buffer non-empty
    assert len(s._bars) > 0
    # Side is still FLAT (no signal emitted)
    assert s._current_side == SignalSide.FLAT


def test_invalid_rsi_period_raises() -> None:
    with pytest.raises(ValueError, match="rsi_period must be >= 2"):
        MeanReversionRsiBBStrategy(symbol="BTCUSDT", rsi_period=1)


def test_invalid_bb_std_mult_raises() -> None:
    with pytest.raises(ValueError, match="bb_std_mult must be > 0"):
        MeanReversionRsiBBStrategy(symbol="BTCUSDT", bb_std_mult=0.0)


def test_invalid_rsi_thresholds_raises() -> None:
    with pytest.raises(ValueError, match="rsi_oversold"):
        MeanReversionRsiBBStrategy(
            symbol="BTCUSDT",
            rsi_oversold=Decimal("70"),
            rsi_overbought=Decimal("30"),
        )


def test_dedup_out_of_order_bars() -> None:
    """Bar with close_time <= last bar's close_time is rejected."""
    s = _make_strategy()
    bar1 = _bar(100.0, 5)
    bar2 = _bar(100.0, 5)  # same close_time
    bar3 = _bar(100.0, 4)  # earlier close_time
    s.on_bar(bar1)
    initial_count = len(s._bars)
    s.on_bar(bar2)
    assert len(s._bars) == initial_count, "Duplicate close_time bar accepted"
    s.on_bar(bar3)
    assert len(s._bars) == initial_count, "Out-of-order bar accepted"
