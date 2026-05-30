"""Unit tests for src.signalgen.indicators.wilder_atr (manual Wilder RMA recursion).

Distinct from talib-based indicators.atr() — uses prev_close[0]=close[0] seed and
SMA-seed at index period-1, mirroring scripts/autoresearch_endless.py::_atr().

S51 D4: ATRBreakoutStrategy now computes ATR incrementally over full history
(the static ``_wilder_atr`` wrapper was removed); the parity test below asserts
the streaming per-bar ATR == this vectorized function (anti-drift guarantee).
"""

import numpy as np
from src.signalgen.indicators import wilder_atr


def test_wilder_atr_matches_recursion() -> None:
    high = np.array([10.0, 11.0, 12.0, 11.0, 13.0, 12.0, 14.0], dtype=np.float64)
    low = np.array([9.0, 9.5, 10.0, 10.0, 11.0, 11.0, 12.0], dtype=np.float64)
    close = np.array([9.5, 10.5, 11.0, 10.5, 12.0, 11.5, 13.0], dtype=np.float64)
    period = 3
    atr = wilder_atr(high, low, close, period)
    assert np.isnan(atr[: period - 1]).all()
    prev_c = np.concatenate([[close[0]], close[:-1]])
    tr = np.maximum.reduce([high - low, np.abs(high - prev_c), np.abs(low - prev_c)])
    assert abs(atr[period - 1] - tr[:period].mean()) < 1e-12
    assert abs(atr[period] - (atr[period - 1] * (period - 1) + tr[period]) / period) < 1e-12


def test_wilder_atr_all_nan_when_short() -> None:
    result = wilder_atr(
        np.array([1.0, 2.0]),
        np.array([0.5, 1.0]),
        np.array([1.0, 1.5]),
        5,
    )
    assert np.isnan(result).all()


def test_wilder_atr_matches_atr_breakout_streaming() -> None:
    """Parity: streaming ATRBreakoutStrategy ATR == vectorized wilder_atr (S51 D4).

    ATRBreakoutStrategy now maintains the Wilder ATR incrementally over full
    history (the static ``_wilder_atr`` wrapper was removed). The streaming
    per-bar value (``_last_atr_signal``, atr_period=9) must equal the canonical
    vectorized ``wilder_atr`` to 1e-9 — the anti-drift guarantee the old
    wrapper-parity test protected.
    """
    from datetime import UTC, datetime, timedelta
    from decimal import Decimal

    from src.marketdata.models import Bar
    from src.signalgen.atr_breakout_strategy import ATRBreakoutStrategy

    rng = np.random.default_rng(42)
    n = 50
    close = 100 + np.cumsum(rng.normal(0, 1, n))
    high = close + np.abs(rng.normal(0, 0.5, n))
    low = close - np.abs(rng.normal(0, 0.5, n))
    period = 9  # ATRBreakoutStrategy LOCKED atr_period

    vectorized = wilder_atr(high, low, close, period)
    assert np.isnan(vectorized[: period - 1]).all()
    assert not np.isnan(vectorized[period:]).any()

    strat = ATRBreakoutStrategy(symbol="BTCUSDT")
    t0 = datetime(2024, 1, 1, tzinfo=UTC)
    for i in range(n):
        ot = t0 + timedelta(hours=4 * i)
        ct = ot + timedelta(hours=4) - timedelta(microseconds=1)
        op = min(max(float(close[i]), float(low[i])), float(high[i]))
        strat.on_bar(
            Bar(
                symbol="BTCUSDT",
                interval="4h",
                open_time=ot,
                close_time=ct,
                open=Decimal(str(op)),
                high=Decimal(str(high[i])),
                low=Decimal(str(low[i])),
                close=Decimal(str(close[i])),
                volume=Decimal("1000"),
                trade_count=100,
                is_closed=True,
            )
        )
        if not np.isnan(vectorized[i]):
            assert strat._last_atr_signal is not None
            assert abs(strat._last_atr_signal - vectorized[i]) < 1e-9
