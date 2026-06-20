"""S51 D4 — atr_breakout live/backtest ATR-VALUE parity.

Scope (per operator decision 2026-05-30): D4 fixes ONLY the windowed-ATR
re-seed defect. The streaming ``ATRBreakoutStrategy.on_bar`` now maintains both
Wilder ATRs (signal period + stop period) incrementally over FULL history, so
the ATR *values* match ``src.signalgen.indicators.wilder_atr`` /
``atr_breakout_runner._atr`` — the path ADR 0064 WFA validated — instead of
re-seeding the RMA each bar over a bounded sliding deque (maxlen 31), which
diverged up to ~39% rel on BTCUSDT 4H.

These tests assert ATR-VALUE parity to 1e-9 on a LONG series (where the old
deque would saturate and re-seed). The strategy's signal indexing (atr[-2] /
closes[-2,-3]) and entry/exit semantics are deliberately UNCHANGED; a separate
(larger) ATR-index-offset finding is flagged to the operator out of D4 scope.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import numpy as np
import pandas as pd
from src.backtest.atr_breakout_runner import _atr
from src.marketdata.models import Bar
from src.risk.reason_codes import ReasonCode
from src.signalgen.atr_breakout_strategy import ATRBreakoutStrategy
from src.signalgen.models import SignalSide

# LOCKED params for BTCUSDT 4H (ADR 0060).
_AP, _ASP = 9, 21
_DATA = "data/BTCUSDT_4h.parquet"


def _bars_from_df(df: pd.DataFrame) -> list[Bar]:
    """Build closed 4h Bar objects from the runner's OHLCV columns.

    open is clamped into [low, high] to satisfy the Bar OHLC invariant; the
    strategy never reads open so this does not affect ATR or signals.
    """
    t0 = datetime(2023, 1, 1, tzinfo=UTC)
    out: list[Bar] = []
    highs = df["high"].to_numpy(float)
    lows = df["low"].to_numpy(float)
    closes = df["close"].to_numpy(float)
    opens = df["open"].to_numpy(float)
    for i in range(len(df)):
        ot = t0 + timedelta(hours=4 * i)
        ct = ot + timedelta(hours=4) - timedelta(microseconds=1)
        op = min(max(float(opens[i]), float(lows[i])), float(highs[i]))
        out.append(
            Bar(
                symbol="BTCUSDT",
                interval="4h",
                open_time=ot,
                close_time=ct,
                open=Decimal(str(op)),
                high=Decimal(str(highs[i])),
                low=Decimal(str(lows[i])),
                close=Decimal(str(closes[i])),
                volume=Decimal("1000"),
                trade_count=100,
                is_closed=True,
            )
        )
    return out


def test_streaming_atr_matches_full_history_btcusdt_4h() -> None:
    """on_bar's signal & stop ATR (through bar T) == full-history wilder_atr within 1e-9.

    Kills the windowed re-seed: on the 7000+ bar BTCUSDT 4H series the old deque
    (maxlen 31) re-seeds the RMA every bar; the incremental full-history ATR must
    equal ``atr_breakout_runner._atr`` (== ``indicators.wilder_atr``) exactly.
    """
    df = pd.read_parquet(_DATA)
    atr_sig_full = _atr(df, _AP)
    atr_stop_full = _atr(df, _ASP)

    strat = ATRBreakoutStrategy(symbol="BTCUSDT")
    bars = _bars_from_df(df)

    compared = 0
    for i, bar in enumerate(bars):
        strat.on_bar(bar)
        if not np.isnan(atr_sig_full[i]):
            assert strat._last_atr_signal is not None, f"bar {i}: signal ATR None"
            assert abs(strat._last_atr_signal - atr_sig_full[i]) < 1e-9, (
                f"bar {i}: streaming signal ATR {strat._last_atr_signal} != "
                f"full-history {atr_sig_full[i]}"
            )
            compared += 1
        if not np.isnan(atr_stop_full[i]):
            assert strat._last_atr_stop is not None, f"bar {i}: stop ATR None"
            assert abs(strat._last_atr_stop - atr_stop_full[i]) < 1e-9, (
                f"bar {i}: streaming stop ATR {strat._last_atr_stop} != "
                f"full-history {atr_stop_full[i]}"
            )
    assert compared > 7000, f"expected >7000 compared bars, got {compared}"


def test_streaming_atr_no_reseed_long_synthetic() -> None:
    """Synthetic 600-bar series: incremental ATR == full-history (no deque re-seed).

    600 >> the old buffer (31) — guarantees the sliding window would have
    saturated and re-seeded. The incremental ATR must still match the full
    Wilder recursion to 1e-9 for both periods.
    """
    n = 600
    rng = np.random.default_rng(123)
    base = 100.0 + np.cumsum(rng.normal(0, 1, n))
    highs = base + rng.uniform(0.5, 2.0, n)
    lows = base - rng.uniform(0.5, 2.0, n)
    closes = base + rng.uniform(-0.4, 0.4, n)
    opens = base.copy()
    df = pd.DataFrame({"high": highs, "low": lows, "close": closes, "open": opens})

    atr_sig_full = _atr(df, _AP)
    atr_stop_full = _atr(df, _ASP)

    strat = ATRBreakoutStrategy(symbol="BTCUSDT")
    for i, bar in enumerate(_bars_from_df(df)):
        strat.on_bar(bar)
        if not np.isnan(atr_sig_full[i]):
            assert abs(strat._last_atr_signal - atr_sig_full[i]) < 1e-9  # type: ignore[operator]
        if not np.isnan(atr_stop_full[i]):
            assert abs(strat._last_atr_stop - atr_stop_full[i]) < 1e-9  # type: ignore[operator]


# ----------------------------------------------------------------------------
# TL-03 — same-bar double-exit priority parity (live == WFA backtest runner)
# ----------------------------------------------------------------------------
#
# The vectorised runner (atr_breakout_runner._backtest_single, lines 234-247)
# evaluates the ATR stop BEFORE the reverse-breakdown exit:
#
#     if low[i] <= stop_price:        -> stop fill at stop_price
#     elif exit_[i]:                  -> reverse fill at open[i]
#
# This is the WFA-validated execution order (runner docstring line 14: "ATR stop
# checked BEFORE reverse signal (research _backtest priority)"). When BOTH exit
# conditions fire on the same bar, the runner books the ATR stop. The streaming
# ``on_bar`` must pick the SAME exit (reason EXIT_FLAT_ATR_STOP_AB), otherwise
# live diverges from backtest on every same-bar double-exit.


def _mk_bar(t: datetime, close: float, low: float, high: float) -> Bar:
    """OHLC bar with open==close; low/high clamped to satisfy the Bar invariant."""
    p = Decimal(str(close))
    lo = min(Decimal(str(low)), p)
    hi = max(Decimal(str(high)), p)
    return Bar(
        symbol="BTCUSDT",
        interval="4h",
        open_time=t,
        close_time=t + timedelta(hours=4) - timedelta(microseconds=1),
        open=p,
        high=hi,
        low=lo,
        close=p,
        volume=Decimal("1000"),
        trade_count=100,
        is_closed=True,
    )


def test_same_bar_double_exit_picks_atr_stop_like_runner() -> None:
    """Both exits fire same bar -> streaming books ATR stop (runner priority).

    Drives a LONG position, then feeds an exit bar where the reverse ATR
    breakdown (close[T-1] < close[T-2] - mult*atr_sig[T-2]) AND the intrabar ATR
    stop (low[T] <= entry_close - stop_mult*atr_stop) BOTH fire. The vectorised
    runner (atr_breakout_runner._backtest_single) evaluates the stop FIRST
    (docstring: "ATR stop checked BEFORE reverse signal"), so on a same-bar
    double-exit it books the ATR stop. Live ``on_bar`` must emit the matching
    reason EXIT_FLAT_ATR_STOP_AB — NOT EXIT_FLAT_ATR_REVERSE.

    The volatility regime (volatile history then a calm tail) makes the
    21-period stop ATR ~2.8x the 9-period signal ATR, so the reverse band
    (entry - 2.5*atr_sig) sits ABOVE the stop level (entry - 1.5*atr_stop).
    That separation lets a T-1 close land below the reverse band while its low
    stays above the stop (no premature exit), and the exit bar's low wicks
    below the stop — a genuine same-bar double-exit.
    """
    strat = ATRBreakoutStrategy(symbol="BTCUSDT")
    t = datetime(2024, 1, 1, tzinfo=UTC)
    step = timedelta(hours=4)

    def feed(close: float, low: float, high: float) -> object:
        nonlocal t
        sig = strat.on_bar(_mk_bar(t, close, low, high))
        t += step
        return sig

    # Volatile history (inflates 21-period ATR) then a calm tail (deflates the
    # 9-period ATR) -> ratio atr_stop/atr_sig >> 1.67 at entry.
    vol, calm_tail, jump = 30.0, 20, 20.0
    n_bars = strat._warmup + 30
    for i in range(n_bars):
        if i < n_bars - calm_tail:
            px = 100.0 + (vol / 2 if i % 2 == 0 else -vol / 2)
            feed(px, px - vol / 2, px + vol / 2)
        else:
            px = 100.0 + (0.2 if i % 2 == 0 else -0.2)
            feed(px, px - 0.4, px + 0.4)

    # Gentle gap-up entry: close jumps by `jump` over two bars (tight ranges so
    # the entry does not over-inflate the signal ATR).
    feed(100.0, 99.8, 100.2)
    feed(100.0 + jump, 100.0 + jump - 0.3, 100.0 + jump + 0.3)
    entry_sig = feed(100.0 + jump, 100.0 + jump - 0.3, 100.0 + jump + 0.3)
    assert entry_sig is not None and entry_sig.side == SignalSide.LONG  # type: ignore[union-attr]
    assert strat._current_side == SignalSide.LONG

    entry_close = strat._entry_close
    atr_sig = strat._last_atr_signal
    atr_stop = strat._last_atr_stop
    assert entry_close is not None and atr_sig is not None and atr_stop is not None

    reverse_band = entry_close - strat._atr_breakout_mult * atr_sig
    stop_level = entry_close - strat._atr_stop_mult * atr_stop
    assert reverse_band - stop_level > 1.0, "regime must separate reverse band above stop"

    # Hold one bar so the exit bar's close[T-2] == entry_close.
    feed(entry_close, entry_close - 0.3, entry_close + 0.3)

    # T-1 bar: close BELOW the reverse band (arms the reverse exit) but low ABOVE
    # the stop level (so this bar itself does NOT exit).
    t1_close = (reverse_band + stop_level) / 2.0
    t1_exit = feed(t1_close, stop_level + 1.0, t1_close + 0.3)
    assert t1_exit is None, "T-1 bar must not exit (low kept above stop)"
    assert strat._current_side == SignalSide.LONG

    # Exit bar: low wicks below the stop (intrabar stop fires) while the reverse
    # breakdown is already armed (prev_close == t1_close < reverse_band).
    exit_sig = feed(t1_close, stop_level - 3.0, t1_close + 0.3)
    assert exit_sig is not None, "expected an exit signal on same-bar double-exit"
    assert exit_sig.side == SignalSide.FLAT  # type: ignore[union-attr]
    # Runner books the ATR stop first -> live must match.
    assert exit_sig.reason == ReasonCode.EXIT_FLAT_ATR_STOP_AB, (  # type: ignore[union-attr]
        f"same-bar double-exit must book ATR stop (runner priority), " f"got {exit_sig.reason}"  # type: ignore[union-attr]
    )
