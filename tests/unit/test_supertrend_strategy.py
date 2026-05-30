"""Unit tests for SupertrendStrategy (S50 T4, ADR 0067 LOCKED, Lazybear variant).

Hypothesis #10: BTCUSDT 1H pure Supertrend. Entry on BEAR->BULL trend flip,
exit on BULL->BEAR flip + ATR bracket SL (no TP). Look-ahead-safe streaming.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from src.marketdata.models import Bar
from src.risk.reason_codes import ReasonCode
from src.signalgen.models import SignalSide
from src.signalgen.supertrend_strategy import (
    SUPERTREND_LOCKED_PARAMS,
    SupertrendStrategy,
)


@pytest.fixture
def base_time() -> datetime:
    return datetime(2024, 1, 1, tzinfo=UTC)


def _make_bar(
    *,
    close_time: datetime,
    high: float,
    low: float,
    close: float,
    is_closed: bool = True,
    symbol: str = "BTCUSDT",
    open_: float | None = None,
    volume: float = 100.0,
) -> Bar:
    open_px = open_ if open_ is not None else close
    return Bar(
        open_time=close_time - timedelta(hours=1),
        close_time=close_time,
        symbol=symbol,
        interval="1h",
        open=Decimal(str(open_px)),
        high=Decimal(str(high)),
        low=Decimal(str(low)),
        close=Decimal(str(close)),
        volume=Decimal(str(volume)),
        trade_count=100,
        is_closed=is_closed,
    )


def _flat_warmup(
    strat: SupertrendStrategy,
    base_time: datetime,
    *,
    price: float = 100.0,
    count: int = 20,
) -> datetime:
    """Feed tight flat bars (small ATR) to clear warmup. Returns next close_time."""
    t = base_time
    for _ in range(count):
        strat.on_bar(_make_bar(close_time=t, high=price + 0.5, low=price - 0.5, close=price))
        t += timedelta(hours=1)
    return t


# ---------------------------------------------------------------------------
# LOCKED params
# ---------------------------------------------------------------------------


def test_locked_params() -> None:
    assert SUPERTREND_LOCKED_PARAMS["atr_period"] == 10
    assert SUPERTREND_LOCKED_PARAMS["multiplier"] == Decimal("3.0")


# ---------------------------------------------------------------------------
# look-ahead / live-bar guard
# ---------------------------------------------------------------------------


def test_unclosed_bar_returns_none(base_time: datetime) -> None:
    strat = SupertrendStrategy(symbol="BTCUSDT")
    bar = _make_bar(close_time=base_time, high=101, low=99, close=100, is_closed=False)
    assert strat.on_bar(bar) is None


def test_out_of_order_bar_rejected(base_time: datetime) -> None:
    strat = SupertrendStrategy(symbol="BTCUSDT")
    t = _flat_warmup(strat, base_time)
    strat.on_bar(_make_bar(close_time=t, high=101, low=99, close=100))
    earlier = _make_bar(close_time=t - timedelta(hours=5), high=200, low=150, close=199)
    # OOO bar must be rejected (no signal, even though it would be a huge breakout)
    assert strat.on_bar(earlier) is None


def test_duplicate_close_time_rejected(base_time: datetime) -> None:
    strat = SupertrendStrategy(symbol="BTCUSDT")
    t = _flat_warmup(strat, base_time)
    bar = _make_bar(close_time=t, high=300, low=250, close=290)
    strat.on_bar(bar)
    assert strat.on_bar(bar) is None  # same close_time -> dedup


# ---------------------------------------------------------------------------
# warmup
# ---------------------------------------------------------------------------


def test_warmup_returns_none(base_time: datetime) -> None:
    strat = SupertrendStrategy(symbol="BTCUSDT")
    t = base_time
    # bars before ATR is valid -> None (atr_period bars produce NaN-driven warmup)
    for _ in range(strat._atr_period):
        sig = strat.on_bar(_make_bar(close_time=t, high=101, low=99, close=100))
        assert sig is None
        t += timedelta(hours=1)


# ---------------------------------------------------------------------------
# entry: BEAR -> BULL flip
# ---------------------------------------------------------------------------


def test_entry_long_on_bull_flip(base_time: datetime) -> None:
    strat = SupertrendStrategy(symbol="BTCUSDT")
    t = _flat_warmup(strat, base_time, price=100.0, count=20)
    # Strong rally that decisively crosses above the upper band -> BEAR->BULL flip.
    sig = None
    for px in (110, 130, 160):
        sig = strat.on_bar(_make_bar(close_time=t, high=px + 1, low=px - 1, close=px))
        t += timedelta(hours=1)
        if sig is not None:
            break
    assert sig is not None
    assert sig.side == SignalSide.LONG
    assert sig.reason == ReasonCode.ENTRY_LONG_SUPERTREND.value
    assert strat._trend_direction == "BULL"


# ---------------------------------------------------------------------------
# exit: BULL -> BEAR flip
# ---------------------------------------------------------------------------


def test_exit_flat_on_bear_flip(base_time: datetime) -> None:
    strat = SupertrendStrategy(symbol="BTCUSDT")
    t = _flat_warmup(strat, base_time, price=100.0, count=20)
    # enter BULL
    for px in (110, 130, 160, 180):
        strat.on_bar(_make_bar(close_time=t, high=px + 1, low=px - 1, close=px))
        t += timedelta(hours=1)
    assert strat._trend_direction == "BULL"
    # crash that crosses below the lower band -> BULL->BEAR flip
    exit_sig = None
    for px in (140, 110, 80):
        exit_sig = strat.on_bar(_make_bar(close_time=t, high=px + 1, low=px - 1, close=px))
        t += timedelta(hours=1)
        if exit_sig is not None:
            break
    assert exit_sig is not None
    assert exit_sig.side == SignalSide.FLAT
    assert exit_sig.reason == ReasonCode.EXIT_FLAT_SUPERTREND_FLIP.value
    assert strat._trend_direction == "BEAR"


# ---------------------------------------------------------------------------
# no signal mid-trend (stable BULL -> consecutive None after entry)
# ---------------------------------------------------------------------------


def test_no_signal_mid_bull_trend(base_time: datetime) -> None:
    strat = SupertrendStrategy(symbol="BTCUSDT")
    t = _flat_warmup(strat, base_time, price=100.0, count=20)
    # enter BULL
    entered = False
    for px in (110, 130, 160, 180):
        sig = strat.on_bar(_make_bar(close_time=t, high=px + 1, low=px - 1, close=px))
        t += timedelta(hours=1)
        if sig is not None and sig.side == SignalSide.LONG:
            entered = True
    assert entered
    assert strat._trend_direction == "BULL"
    # continued uptrend -> no further signals (mid-trend)
    for px in (185, 190, 195, 200):
        sig = strat.on_bar(_make_bar(close_time=t, high=px + 1, low=px - 1, close=px))
        t += timedelta(hours=1)
        assert sig is None


# ---------------------------------------------------------------------------
# Lazybear latch: supertrend line ratchets (non-decreasing in BULL)
# ---------------------------------------------------------------------------


def test_lazybear_latch_bull_non_decreasing(base_time: datetime) -> None:
    strat = SupertrendStrategy(symbol="BTCUSDT")
    t = _flat_warmup(strat, base_time, price=100.0, count=20)
    # enter BULL
    for px in (110, 130, 160, 180):
        strat.on_bar(_make_bar(close_time=t, high=px + 1, low=px - 1, close=px))
        t += timedelta(hours=1)
    assert strat._trend_direction == "BULL"
    # within a sustained BULL trend the supertrend line (lower band) is non-decreasing
    lines: list[float] = []
    for px in (185, 190, 200, 210, 220):
        strat.on_bar(_make_bar(close_time=t, high=px + 1, low=px - 1, close=px))
        t += timedelta(hours=1)
        assert strat._trend_direction == "BULL"
        assert strat._supertrend_line is not None
        lines.append(strat._supertrend_line)
    for prev, cur in zip(lines, lines[1:], strict=False):
        assert cur >= prev - 1e-9  # non-decreasing (ratchet up)


def test_lazybear_latch_bear_non_increasing(base_time: datetime) -> None:
    strat = SupertrendStrategy(symbol="BTCUSDT")
    t = _flat_warmup(strat, base_time, price=200.0, count=20)
    # force BEAR: drop below lower band (seed trend is BEAR; keep falling stays BEAR)
    lines: list[float] = []
    for px in (170, 150, 130, 110, 90, 70):
        strat.on_bar(_make_bar(close_time=t, high=px + 1, low=px - 1, close=px))
        t += timedelta(hours=1)
        assert strat._trend_direction == "BEAR"
        if strat._supertrend_line is not None:
            lines.append(strat._supertrend_line)
    assert len(lines) >= 3
    for prev, cur in zip(lines, lines[1:], strict=False):
        assert cur <= prev + 1e-9  # non-increasing (ratchet down)
