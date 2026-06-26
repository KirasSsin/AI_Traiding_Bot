"""S55 TL-04 — volume_breakout live/backtest exit-priority parity.

The vectorised runner (``src.backtest.volume_breakout_runner._backtest_single``,
lines 154-173) evaluates exits in this order::

    if low[i] <= stop_price:        -> ATR stop, fill at stop_price
    elif channel_exit:              -> channel exit, fill at open[i]

The runner docstring (line 155) states: "Exit conditions — ATR stop checked
FIRST (research/backtest_v2.py line 140)". This is the WFA-validated execution
order. When BOTH the channel exit (close[T-1] < channel low) AND the intrabar
ATR stop (low[T] <= entry_price - stop_mult*atr) fire on the same bar, the
runner books the ATR stop. The streaming ``VolumeBreakoutStrategy.on_bar`` must
emit the SAME exit (reason EXIT_FLAT_ATR_STOP_VB) — otherwise live diverges from
backtest on every same-bar double-exit.

Note (out of TL-04 scope): the streaming reference windows include bar(T-1)
(``lows_arr[-(N+1):-1]``) whereas the runner uses ``roll_low[i-2]`` (through
T-2). That window off-by-one makes a natural channel exit hard to reach via the
public entry path, so this parity test sets up the rolling buffers + LONG state
directly (white-box) to make BOTH exit conditions simultaneously true — exactly
the same-bar double-exit the runner resolves to the ATR stop.
"""

from __future__ import annotations

from collections import deque
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from src.marketdata.models import Bar
from src.risk.reason_codes import ReasonCode
from src.signalgen.models import SignalSide
from src.signalgen.volume_breakout_strategy import VolumeBreakoutStrategy


def _seed_long_position(
    strat: VolumeBreakoutStrategy,
    *,
    entry_price: float,
    flat_price: float,
    prev_close: float,
) -> None:
    """Seed rolling buffers + LONG state for a same-bar double-exit scenario.

    All historical lows are ``flat_price`` so the channel low (min of the prior
    ``exit_lookback_n`` lows) equals ``flat_price``. The last historical close
    is ``prev_close`` (< ``flat_price``) so that, once the exit bar is appended,
    ``prev_close < channel_low`` arms the channel exit.
    """
    bs = strat._buffer_size
    highs = [flat_price] * bs
    lows = [flat_price] * bs
    closes = [flat_price] * bs
    vols = [1000.0] * bs
    closes[-1] = prev_close  # becomes close[T-1] after the exit bar is appended
    strat._highs = deque(highs, maxlen=bs)
    strat._lows = deque(lows, maxlen=bs)
    strat._closes = deque(closes, maxlen=bs)
    strat._volumes = deque(vols, maxlen=bs)
    strat._current_side = SignalSide.LONG
    strat._entry_price = entry_price


def test_same_bar_double_exit_picks_atr_stop_like_runner() -> None:
    """Both exits fire same bar -> streaming books ATR stop (runner priority).

    Channel exit (close[T-1] < channel low) AND intrabar ATR stop
    (low[T] <= entry_price - stop_mult*atr) both fire on the exit bar. The
    vectorised runner evaluates the stop FIRST, so live ``on_bar`` must emit
    EXIT_FLAT_ATR_STOP_VB — NOT EXIT_FLAT_VOLUME_CHANNEL.
    """
    strat = VolumeBreakoutStrategy(symbol="BTCUSDT")
    entry_price = 1000.0
    _seed_long_position(
        strat,
        entry_price=entry_price,
        flat_price=1000.0,  # channel low == 1000
        prev_close=900.0,  # close[T-1] = 900 < channel low -> channel armed
    )

    # Exit bar: low wicks far below the ATR stop (intrabar stop fires). With a
    # flat 1000 history the ATR is tiny, so any deep low breaches the stop.
    t = datetime(2024, 1, 1, tzinfo=UTC)
    step = timedelta(hours=4)
    exit_bar = Bar(
        symbol="BTCUSDT",
        interval="4h",
        open_time=t,
        close_time=t + step - timedelta(microseconds=1),
        open=Decimal("900"),
        high=Decimal("900"),
        low=Decimal("-100000"),  # guarantees low[T] <= stop level
        close=Decimal("900"),
        volume=Decimal("1000"),
        trade_count=100,
        is_closed=True,
    )
    sig = strat.on_bar(exit_bar)

    assert sig is not None, "expected an exit signal on same-bar double-exit"
    assert sig.side == SignalSide.FLAT
    # Runner books the ATR stop first -> live must match.
    assert sig.reason == ReasonCode.EXIT_FLAT_ATR_STOP_VB, (
        f"same-bar double-exit must book ATR stop (runner priority), " f"got {sig.reason}"
    )


def test_channel_exit_alone_still_fires() -> None:
    """Channel exit alone (stop NOT breached) still emits EXIT_FLAT_VOLUME_CHANNEL.

    Guards the reorder: making the ATR stop first must NOT suppress the channel
    exit when only the channel condition is true.
    """
    strat = VolumeBreakoutStrategy(symbol="BTCUSDT")
    _seed_long_position(
        strat,
        entry_price=1000.0,
        flat_price=1000.0,
        prev_close=900.0,  # channel armed
    )

    # Exit bar whose low stays ABOVE the stop level (no stop) but channel armed.
    # The channel is armed by the SEEDED close[T-1] (== 900 < channel low 1000),
    # so this exit bar can stay flat at the entry price (low never breaches the
    # stop) while the channel still fires.
    t = datetime(2024, 1, 1, tzinfo=UTC)
    step = timedelta(hours=4)
    exit_bar = Bar(
        symbol="BTCUSDT",
        interval="4h",
        open_time=t,
        close_time=t + step - timedelta(microseconds=1),
        open=Decimal("1000"),
        high=Decimal("1000"),
        low=Decimal("1000"),  # == entry price -> ATR stop NOT breached
        close=Decimal("1000"),
        volume=Decimal("1000"),
        trade_count=100,
        is_closed=True,
    )
    sig = strat.on_bar(exit_bar)

    assert sig is not None and sig.side == SignalSide.FLAT
    assert (
        sig.reason == ReasonCode.EXIT_FLAT_VOLUME_CHANNEL
    ), f"channel-only exit must still emit channel reason, got {sig.reason}"
