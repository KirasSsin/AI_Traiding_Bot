"""TL-07 regression guard — EMA / mean-reversion / Donchian reason resolution.

These three strategies historically emitted their ``Signal.reason`` as RAW
STRING LITERALS rather than ``ReasonCode.<member>.value``. The strings DID match
enum members (S49 ADR 0023 amendment), but a typo/rename had no compile- or
test-time link to the enum, so a drifted literal would silently fall through
RiskManager's ``ReasonCode(signal.reason)`` fallback to the generic
ENTRY_LONG_TREND_FOLLOWING / EXIT_SIGNAL_FLIP — losing strategy attribution.

This file drives each strategy through a full entry→exit cycle and asserts every
emitted reason:
  1. round-trips through ``ReasonCode(reason)`` WITHOUT raising (== no fallback),
  2. resolves to the SPECIFIC expected member (not merely *some* member).

The test FAILS if anyone changes a literal to a non-member (ReasonCode() raises)
OR to the wrong member (specific-member assert fails) — the durable guard that
the raw-string defect cannot silently recur.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from src.marketdata.models import Bar, DataQuality
from src.risk.reason_codes import ReasonCode
from src.signalgen.donchian_strategy import DONCHIAN_LONG_ONLY_PARAMS, DonchianBreakoutStrategy
from src.signalgen.mean_reversion_strategy import MeanReversionRsiBBStrategy
from src.signalgen.models import Signal, SignalSide
from src.signalgen.strategy import EmaCrossoverAdxRsiStrategy

_T0 = datetime(2026, 1, 1, tzinfo=UTC)


# ---------------------------------------------------------------------------
# bar builders + drivers (reuse the proven sequences from the per-strategy tests)
# ---------------------------------------------------------------------------


def _hourly_bar(close: float, idx: int, *, high: float, low: float) -> Bar:
    ot = _T0 + timedelta(hours=idx)
    ct = ot + timedelta(hours=1) - timedelta(microseconds=1)
    return Bar(
        symbol="BTCUSDT",
        interval="1h",
        open_time=ot,
        close_time=ct,
        open=Decimal(str(close)),
        high=Decimal(str(high)),
        low=Decimal(str(low)),
        close=Decimal(str(close)),
        volume=Decimal("1.0"),
        trade_count=1,
        is_closed=True,
        data_quality=DataQuality.OK,
    )


def _drive_ema() -> list[Signal]:
    """Downtrend → rally (LONG) → reversal (FLAT). Mirrors test_strategy_emits_flat_on_signal_flip."""
    bars: list[Bar] = []
    price = 100.0
    for i in range(60):  # Phase A: downtrend
        price -= 0.2
        bars.append(_hourly_bar(price, i, high=price + 0.3, low=price - 0.3))
    for i in range(60, 90):  # Phase B: gentle rally → LONG
        price += 0.2
        bars.append(_hourly_bar(price, i, high=price + 0.3, low=price - 0.3))
    for i in range(90, 150):  # Phase C: stronger downtrend → FLAT flip
        price -= 0.3
        bars.append(_hourly_bar(price, i, high=price + 0.4, low=price - 0.4))

    strat = EmaCrossoverAdxRsiStrategy(
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
    return [s for b in bars if (s := strat.on_bar(b)) is not None]


def _drive_meanrev() -> list[Signal]:
    """Stable → sharp decline (LONG) → steep recovery (FLAT). Mirrors meanrev entry/exit tests."""
    strat = MeanReversionRsiBBStrategy(
        symbol="BTCUSDT",
        rsi_period=14,
        bb_period=20,
        bb_std_mult=2.0,
        rsi_oversold=Decimal("30"),
        rsi_overbought=Decimal("70"),
        atr_period=14,
    )
    signals: list[Signal] = []
    for i in range(25):  # stable
        if (s := strat.on_bar(_hourly_bar(100.0, i, high=100.5, low=99.5))) is not None:
            signals.append(s)
    for i in range(25, 40):  # sharp decline → LONG
        c = 100.0 - (i - 24) * 2.0
        if (s := strat.on_bar(_hourly_bar(c, i, high=c + 0.5, low=c - 0.5))) is not None:
            signals.append(s)
    for i in range(40, 70):  # steep recovery → FLAT
        c = 50.0 + (i - 39) * 5.0
        if (s := strat.on_bar(_hourly_bar(c, i, high=c + 2.0, low=c - 0.1))) is not None:
            signals.append(s)
    return signals


def _four_hourly_bar(close_time: datetime, *, h: float, low: float, c: float) -> Bar:
    return Bar(
        symbol="BTCUSDT",
        interval="4h",
        open_time=close_time - timedelta(hours=4),
        close_time=close_time,
        open=Decimal(str(c)),
        high=Decimal(str(h)),
        low=Decimal(str(low)),
        close=Decimal(str(c)),
        volume=Decimal("100"),
        trade_count=1,
        is_closed=True,
        data_quality=DataQuality.OK,
    )


def _drive_donchian() -> list[Signal]:
    """Flat range → breakout (LONG) → crash > 2×ATR (EXIT_FLAT_ATR_STOP). Mirrors donchian tests."""
    strat = DonchianBreakoutStrategy(
        symbol="BTCUSDT",
        lookback_n=int(DONCHIAN_LONG_ONLY_PARAMS["lookback_n"]),  # type: ignore[arg-type]
        exit_lookback_n=int(DONCHIAN_LONG_ONLY_PARAMS["exit_lookback_n"]),  # type: ignore[arg-type]
        atr_period=int(DONCHIAN_LONG_ONLY_PARAMS["atr_period"]),  # type: ignore[arg-type]
        atr_stop_mult=Decimal(str(DONCHIAN_LONG_ONLY_PARAMS["atr_stop_mult"])),
    )
    base = datetime(2026, 1, 1, 4, tzinfo=UTC)
    signals: list[Signal] = []
    for i in range(25):  # flat range 100-105
        if (
            s := strat.on_bar(
                _four_hourly_bar(base + timedelta(hours=4 * i), h=105.0, low=100.0, c=102.0)
            )
        ) is not None:
            signals.append(s)
    # breakout → LONG
    if (
        s := strat.on_bar(
            _four_hourly_bar(base + timedelta(hours=4 * 25), h=110.0, low=104.0, c=109.0)
        )
    ) is not None:
        signals.append(s)
    # crash > 2×ATR → EXIT_FLAT_ATR_STOP
    if (
        s := strat.on_bar(
            _four_hourly_bar(base + timedelta(hours=4 * 26), h=109.0, low=80.0, c=82.0)
        )
    ) is not None:
        signals.append(s)
    return signals


# ---------------------------------------------------------------------------
# regression guard
# ---------------------------------------------------------------------------

# (strategy label, driver, {SignalSide: expected ReasonCode member})
_CASES = [
    (
        "ema",
        _drive_ema,
        {
            SignalSide.LONG: ReasonCode.ENTRY_LONG_EMA_CROSS_UP,
            SignalSide.FLAT: ReasonCode.EXIT_FLAT_SIGNAL_FLIP,
        },
    ),
    (
        "meanrev",
        _drive_meanrev,
        {
            SignalSide.LONG: ReasonCode.ENTRY_LONG_MEANREV_RSI_BB,
            SignalSide.FLAT: ReasonCode.EXIT_FLAT_MEANREV_REVERT,
        },
    ),
    (
        # Donchian exit in this sequence is the ATR-stop branch (EXIT_FLAT_ATR_STOP).
        "donchian",
        _drive_donchian,
        {
            SignalSide.LONG: ReasonCode.ENTRY_LONG_DONCHIAN_BREAKOUT,
            SignalSide.FLAT: ReasonCode.EXIT_FLAT_ATR_STOP,
        },
    ),
]


@pytest.mark.parametrize("label,driver,expected", _CASES, ids=[c[0] for c in _CASES])
def test_every_emitted_reason_resolves_to_specific_reason_code(label, driver, expected) -> None:
    """Each strategy's emitted reason resolves to the SPECIFIC ReasonCode member (no fallback)."""
    signals = driver()
    seen_sides = set()
    for sig in signals:
        # 1. Must round-trip (raises ValueError -> non-member -> fallback would hit).
        resolved = ReasonCode(sig.reason)
        # 2. Must be the SPECIFIC member expected for this side (catches wrong-member drift).
        assert resolved == expected[sig.side], (
            f"{label}: {sig.side} emitted reason={sig.reason!r} "
            f"-> resolved {resolved}, expected {expected[sig.side]}"
        )
        seen_sides.add(sig.side)
    # Sanity: the driver actually exercised both an ENTRY and an EXIT.
    assert SignalSide.LONG in seen_sides, f"{label}: no LONG entry emitted (driver under-exercised)"
    assert SignalSide.FLAT in seen_sides, f"{label}: no FLAT exit emitted (driver under-exercised)"


def test_donchian_channel_exit_resolves() -> None:
    """The Donchian channel-exit branch (EXIT_FLAT_CHANNEL) also resolves to its member.

    The ATR-stop branch is covered by the parametrized case above; this drives the
    OTHER exit literal (close < lower Donchian channel without an ATR-stop hit).
    """
    strat = DonchianBreakoutStrategy(
        symbol="BTCUSDT",
        lookback_n=int(DONCHIAN_LONG_ONLY_PARAMS["lookback_n"]),  # type: ignore[arg-type]
        exit_lookback_n=int(DONCHIAN_LONG_ONLY_PARAMS["exit_lookback_n"]),  # type: ignore[arg-type]
        atr_period=int(DONCHIAN_LONG_ONLY_PARAMS["atr_period"]),  # type: ignore[arg-type]
        atr_stop_mult=Decimal("50.0"),  # huge stop mult -> ATR stop never hit -> channel exit wins
    )
    base = datetime(2026, 1, 1, 4, tzinfo=UTC)
    for i in range(
        25
    ):  # flat range with a wide band so exit_lookback low is well above the dip close
        strat.on_bar(_four_hourly_bar(base + timedelta(hours=4 * i), h=105.0, low=100.0, c=102.0))
    strat.on_bar(
        _four_hourly_bar(base + timedelta(hours=4 * 25), h=110.0, low=104.0, c=109.0)
    )  # LONG
    # Modest drop below the lower Donchian channel but NOT past the (huge) ATR stop.
    exit_sig = strat.on_bar(
        _four_hourly_bar(base + timedelta(hours=4 * 26), h=103.0, low=98.0, c=99.0)
    )
    assert exit_sig is not None and exit_sig.side == SignalSide.FLAT
    assert ReasonCode(exit_sig.reason) == ReasonCode.EXIT_FLAT_CHANNEL
