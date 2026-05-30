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
from src.signalgen.atr_breakout_strategy import ATRBreakoutStrategy

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
