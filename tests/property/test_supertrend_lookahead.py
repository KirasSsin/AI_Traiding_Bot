"""Look-ahead property + vectorized cross-validation for SupertrendStrategy (S50 T5).

Guarantees enforced (ADR 0067 LOCKED, Lazybear variant):

1. **Streaming-vs-vectorized parity** — the stateful ``on_bar`` output
   (``_supertrend_line`` + ``_trend_direction``) must match a full-history
   vectorized Lazybear reference at EVERY post-seed bar within 1e-9. This proves
   the ATR is computed over full history (no windowed re-seed) and the
   carry/clamp formula matches the reference exactly.

2. **Truncation-invariance (look-ahead)** — feeding bars ``0..k`` alone must
   produce the same per-bar signals as feeding the full series and reading the
   first ``k`` signals. A strategy that peeks at future bars would violate this.

3. **Determinism** — identical input -> identical signal sequence.

The vectorized reference uses :func:`src.signalgen.indicators.wilder_atr`
(full-history Wilder RMA), which is the canonical ATR the streaming path must
reproduce incrementally.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import numpy as np
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from src.marketdata.models import Bar, DataQuality
from src.signalgen.indicators import wilder_atr
from src.signalgen.models import Signal, SignalSide
from src.signalgen.supertrend_strategy import SupertrendStrategy

_ATR_PERIOD = 10
_MULT = 3.0


# ---------------------------------------------------------------------------
# Vectorized Lazybear Supertrend reference (full-history, batch numpy).
# Mirrors SupertrendStrategy.on_bar carry/clamp/seed semantics EXACTLY.
# ---------------------------------------------------------------------------


def _vectorized_supertrend(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    atr_period: int,
    mult: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Whole-array Lazybear Supertrend using full-history ``wilder_atr``.

    Returns:
        ``(line, trend)`` arrays length ``n``. Indices ``< atr_period-1`` are
        NaN/empty (ATR invalid). At the seed bar ``atr_period-1`` the line is
        seeded on the basic upper band with trend ``"BEAR"`` (matching the
        streaming seed). From ``atr_period`` onward the Lazybear carry/clamp
        applies.

    Trend strings: ``"BULL"`` / ``"BEAR"`` / ``""`` (pre-seed sentinel).
    """
    n = len(close)
    atr = wilder_atr(high, low, close, atr_period)
    hl2 = (high + low) / 2.0
    basic_ub = hl2 + mult * atr
    basic_lb = hl2 - mult * atr

    line = np.full(n, np.nan, dtype=np.float64)
    trend = np.array([""] * n, dtype=object)

    seed_idx = atr_period - 1
    if n <= seed_idx or np.isnan(atr[seed_idx]):
        return line, trend

    # Seed bar: no prior carry -> conservative upper-band seed, trend BEAR.
    final_ub = basic_ub[seed_idx]
    final_lb = basic_lb[seed_idx]
    line[seed_idx] = final_ub  # conservative seed on the upper band
    trend[seed_idx] = "BEAR"
    prev_final_ub = final_ub
    prev_final_lb = final_lb
    prev_supertrend = final_ub
    prev_close = close[seed_idx]

    for i in range(seed_idx + 1, n):
        b_ub = basic_ub[i]
        b_lb = basic_lb[i]
        c = close[i]

        f_ub = b_ub if (b_ub < prev_final_ub or prev_close > prev_final_ub) else prev_final_ub
        f_lb = b_lb if (b_lb > prev_final_lb or prev_close < prev_final_lb) else prev_final_lb

        if prev_supertrend == prev_final_ub:
            st_line = f_ub if c <= f_ub else f_lb
        else:
            st_line = f_lb if c >= f_lb else f_ub

        tr = "BULL" if st_line == f_lb else "BEAR"

        line[i] = st_line
        trend[i] = tr

        prev_final_ub = f_ub
        prev_final_lb = f_lb
        prev_supertrend = st_line
        prev_close = c

    return line, trend


# ---------------------------------------------------------------------------
# Bar synthesis helpers
# ---------------------------------------------------------------------------


def _bars_from_prices(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    *,
    base_time: datetime | None = None,
    symbol: str = "BTCUSDT",
) -> list[Bar]:
    """Build closed 1h Bars from HLC arrays (open clamped to satisfy OHLC invariants)."""
    t0 = base_time or datetime(2024, 1, 1, tzinfo=UTC)
    bars: list[Bar] = []
    for i in range(len(closes)):
        ot = t0 + timedelta(hours=i)
        ct = ot + timedelta(hours=1) - timedelta(microseconds=1)
        hi = float(highs[i])
        lo = float(lows[i])
        cl = float(closes[i])
        # open must lie within [low, high]; clamp close-derived open.
        op = min(max(cl, lo), hi)
        bars.append(
            Bar(
                symbol=symbol,
                interval="1h",
                open_time=ot,
                close_time=ct,
                open=Decimal(str(op)),
                high=Decimal(str(hi)),
                low=Decimal(str(lo)),
                close=Decimal(str(cl)),
                volume=Decimal("1.0"),
                trade_count=1,
                is_closed=True,
                data_quality=DataQuality.OK,
            )
        )
    return bars


def _gbm_hlc(
    n: int, seed: int, *, s0: float = 100.0, mu: float = 0.0002, sigma: float = 0.02
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Seeded geometric-brownian-motion close path + synthetic intrabar high/low."""
    rng = np.random.default_rng(seed)
    rets = rng.normal(mu, sigma, size=n)
    closes = s0 * np.exp(np.cumsum(rets))
    # intrabar range proportional to price, jittered.
    spread = np.abs(rng.normal(0.0, 0.01, size=n)) * closes + 0.05 * closes
    highs = closes + spread / 2.0
    lows = closes - spread / 2.0
    lows = np.maximum(lows, 1e-6)
    return highs, lows, closes


def _stream_capture(bars: list[Bar]) -> tuple[list[float], list[str], list[Signal | None]]:
    """Feed bars through SupertrendStrategy; capture per-bar line/trend/signal."""
    strat = SupertrendStrategy(symbol="BTCUSDT", atr_period=_ATR_PERIOD, multiplier=_MULT)
    lines: list[float] = []
    trends: list[str] = []
    sigs: list[Signal | None] = []
    for b in bars:
        sig = strat.on_bar(b)
        sigs.append(sig)
        lines.append(strat._supertrend_line if strat._supertrend_line is not None else float("nan"))
        trends.append(strat._trend_direction if strat._trend_direction is not None else "")
    return lines, trends, sigs


# ---------------------------------------------------------------------------
# 1. Cross-validation: streaming on_bar == vectorized reference (parity).
#    This is the acceptance gate that catches the windowed-ATR re-seed bug.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("seed", [1, 7, 42, 1234])
def test_streaming_matches_vectorized_reference(seed: int) -> None:
    """300 GBM bars: streaming line+trend == full-history vectorized at every post-seed bar.

    A windowed-ATR recompute re-seeds the Wilder recursion once the buffer
    saturates, so its supertrend line diverges from the full-history reference.
    Incremental ATR recursion (full history, no re-seed) matches exactly.
    """
    n = 300
    highs, lows, closes = _gbm_hlc(n, seed)
    bars = _bars_from_prices(highs, lows, closes)

    lines, trends, _ = _stream_capture(bars)
    ref_line, ref_trend = _vectorized_supertrend(highs, lows, closes, _ATR_PERIOD, _MULT)

    seed_idx = _ATR_PERIOD - 1
    # Every post-seed bar must match to 1e-9 (line) and exactly (trend).
    for i in range(seed_idx, n):
        assert trends[i] == ref_trend[i], (
            f"trend mismatch at bar {i} (seed={seed}): "
            f"streaming={trends[i]!r} vs vectorized={ref_trend[i]!r}"
        )
        assert abs(lines[i] - float(ref_line[i])) <= 1e-9, (
            f"supertrend line mismatch at bar {i} (seed={seed}): "
            f"streaming={lines[i]!r} vs vectorized={ref_line[i]!r} "
            f"(abs diff={abs(lines[i] - float(ref_line[i]))})"
        )


# ---------------------------------------------------------------------------
# 2. Truncation-invariance (look-ahead): prefix run == prefix of full run.
# ---------------------------------------------------------------------------


@st.composite
def _price_path(draw: st.DrawFn, min_size: int = 60, max_size: int = 160) -> np.ndarray:
    n = draw(st.integers(min_value=min_size, max_value=max_size))
    seed = draw(st.integers(min_value=0, max_value=2**31 - 1))
    _, _, closes = _gbm_hlc(n, seed)
    return closes


@given(
    seed=st.integers(min_value=0, max_value=2**31 - 1), n=st.integers(min_value=40, max_value=120)
)
@settings(deadline=None, max_examples=40, suppress_health_check=[HealthCheck.too_slow])
@pytest.mark.property
def test_truncation_invariance(seed: int, n: int) -> None:
    """Feeding bars 0..k alone yields the same signals as the prefix of the full run.

    The streaming strategy must depend only on bars seen so far (no look-ahead).
    Equivalent to: signals are a function of the causal prefix only.
    """
    highs, lows, closes = _gbm_hlc(n, seed)
    full_bars = _bars_from_prices(highs, lows, closes)

    _, _, full_sigs = _stream_capture(full_bars)

    # Truncate at a representative cut point past warmup.
    k = max(_ATR_PERIOD + 5, n // 2)
    _, _, prefix_sigs = _stream_capture(full_bars[:k])

    assert len(prefix_sigs) == k
    for i in range(k):
        a = prefix_sigs[i]
        b = full_sigs[i]
        # Compare the causal payload (side + reason). signal_id/generated_at are
        # intentionally non-deterministic (uuid/now) and excluded.
        a_key = None if a is None else (a.side, a.reason)
        b_key = None if b is None else (b.side, b.reason)
        assert a_key == b_key, (
            f"truncation/look-ahead violation at bar {i} (seed={seed}, n={n}, k={k}): "
            f"prefix={a_key} vs full-prefix={b_key}"
        )


# ---------------------------------------------------------------------------
# 3. Determinism: identical input -> identical signal sequence.
# ---------------------------------------------------------------------------


@given(
    seed=st.integers(min_value=0, max_value=2**31 - 1), n=st.integers(min_value=40, max_value=120)
)
@settings(deadline=None, max_examples=40, suppress_health_check=[HealthCheck.too_slow])
@pytest.mark.property
def test_determinism(seed: int, n: int) -> None:
    """Same bars fed twice produce the same (side, reason) sequence."""
    highs, lows, closes = _gbm_hlc(n, seed)
    bars = _bars_from_prices(highs, lows, closes)

    _, _, sigs_a = _stream_capture(bars)
    _, _, sigs_b = _stream_capture(bars)

    keys_a = [None if s is None else (s.side, s.reason) for s in sigs_a]
    keys_b = [None if s is None else (s.side, s.reason) for s in sigs_b]
    assert keys_a == keys_b


# ---------------------------------------------------------------------------
# 4. Look-ahead invariant on the emitted Signal (generated_at >= bar_close_time).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("seed", [3, 99])
def test_signal_generated_at_ge_bar_close_time(seed: int) -> None:
    """Any emitted Supertrend Signal satisfies generated_at >= bar_close_time."""
    highs, lows, closes = _gbm_hlc(200, seed)
    bars = _bars_from_prices(highs, lows, closes)
    _, _, sigs = _stream_capture(bars)
    for s in sigs:
        if s is None:
            continue
        assert s.generated_at >= s.bar_close_time
        # long-only invariant: spot-only v0.1 has no SHORT (SignalSide ∈ {LONG, FLAT}).
        assert s.side in (SignalSide.LONG, SignalSide.FLAT)


# ---------------------------------------------------------------------------
# 5. Backtest FILL look-ahead guard (S50 PHASE 6 BLOCKER — trading-logic).
#
#    The Lazybear trend at bar i is RECURSIVE: trend[i] depends on close[i]
#    (the active-band selection ``supertrend[i] = final_ub if close[i] <= final_ub
#    else final_lb``). A flip BEAR->BULL whose deciding bar is i is therefore only
#    KNOWN after close[i]. Filling that entry at open[i] (the open of the very bar
#    whose close produced the signal) is same-bar look-ahead — the fill price
#    predates the information that generated the trade. The correct fill is the
#    NEXT bar open, open[i+1] (close(T) -> open(T+1)), matching the streaming
#    SupertrendStrategy contract (signal on closed bar T, FSM fills T+1) and the
#    atr_breakout research kernel (signal from data <= i-1 -> fill open[i]).
#
#    These tests construct a series with a single round-trip whose entry flip is
#    at bar e and exit flip at bar x, with DISTINCTIVE open prices at e, e+1, x,
#    x+1 so the realised fill index is unambiguous. They FAIL against an open[i]
#    fill (look-ahead) and PASS only when the fill is open[i+1].
# ---------------------------------------------------------------------------


def _round_trip_df() -> tuple[object, int, int]:  # noqa: F821 (pd.DataFrame)
    """Build an OHLCV frame with exactly one BEAR->BULL->BEAR round-trip.

    Flip detection (close-based) lands the entry at bar 30 and the exit at bar 40
    for atr_period=10, mult=3.0 (verified empirically). ``open`` is set DISTINCT
    from ``close`` at the fill-candidate bars so the fill index is observable:
      - open[30] (wrong: entry flip bar)      = 1_000_000  (absurd — never correct)
      - open[31] (right: bar after entry flip) =   400.0
      - open[40] (wrong: exit flip bar)        = 2_000_000  (absurd)
      - open[41] (right: bar after exit flip)  =   500.0
    All other opens equal close (the streaming strategy ignores open entirely, so
    this does not perturb the trend computation).
    """
    import numpy as np
    import pandas as pd

    closes = (
        [100.0] * 30
        + [110, 130, 160, 200, 240, 280, 300, 310, 315, 320]
        + [270, 220, 180, 150, 120, 100, 90]
    )
    closes_arr = np.array(closes, dtype=np.float64)
    highs = closes_arr + 1.0
    lows = closes_arr - 1.0
    opens = closes_arr.copy()
    # Distinctive opens at fill-candidate bars (entry flip @30, exit flip @40).
    opens[30] = 1_000_000.0  # entry flip bar — filling here is look-ahead
    opens[31] = 400.0  # correct entry fill = open after the flip
    opens[40] = 2_000_000.0  # exit flip bar — filling here is look-ahead
    opens[41] = 500.0  # correct exit fill = open after the flip

    n = len(closes)
    t0 = datetime(2024, 1, 1, tzinfo=UTC)
    df = pd.DataFrame(
        {
            "ts": [t0 + timedelta(hours=i) for i in range(n)],
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes_arr,
            "volume": np.ones(n),
        }
    )
    return df, 30, 40


def test_runner_backtest_fills_bar_after_flip() -> None:
    """supertrend_runner._backtest_single must fill at open[flip+1], not open[flip].

    Reads the realised entry/exit prices from the trade record. open[flip] is set
    to an absurd 1e6/2e6 so a same-bar fill is unmistakable; the correct fill is
    open[flip+1] * (1 ± SLIPPAGE).
    """
    from src.backtest.supertrend_runner import _SLIPPAGE, _backtest_single

    df, entry_flip, exit_flip = _round_trip_df()
    result = _backtest_single(df, {"atr_period": 10, "multiplier": 3.0}, bars_per_year=8766)

    assert result["n_trades"] >= 1, "expected at least one round-trip trade"
    trade = result["trades"][0]

    expected_entry = float(df["open"].iloc[entry_flip + 1]) * (1.0 + _SLIPPAGE)
    expected_exit = float(df["open"].iloc[exit_flip + 1]) * (1.0 - _SLIPPAGE)

    assert abs(trade.entry_price - expected_entry) < 1e-6, (
        f"entry filled at {trade.entry_price} — must be open[{entry_flip + 1}] "
        f"(={expected_entry}), NOT open[{entry_flip}] (look-ahead). "
        f"open[{entry_flip}]={df['open'].iloc[entry_flip]}"
    )
    assert abs(trade.exit_price - expected_exit) < 1e-6, (
        f"exit filled at {trade.exit_price} — must be open[{exit_flip + 1}] "
        f"(={expected_exit}), NOT open[{exit_flip}] (look-ahead). "
        f"open[{exit_flip}]={df['open'].iloc[exit_flip]}"
    )


def test_autoresearch_backtest_fills_bar_after_flip() -> None:
    """strat_supertrend + _backtest (autoresearch) must realise PnL from open[flip+1].

    The shared _backtest engine has no per-trade price record, so we assert via the
    realised round-trip PnL. With a flip-only exit (atr_stop_mult huge so the ATR
    stop never triggers) the single trade's net PnL must equal:
        (open[x+1]*(1-S) - open[e+1]*(1+S)) / (open[e+1]*(1+S)) - 2*commission
    i.e. fills at the bar AFTER each flip — NOT open[e]/open[x] (look-ahead).
    """
    import numpy as np
    from scripts.autoresearch_endless import (
        COMMISSION_TAKER,
        SLIPPAGE,
        _backtest,
        strat_supertrend,
    )

    df, entry_flip, exit_flip = _round_trip_df()
    entry, exit_, warmup, atr_arr = strat_supertrend(df, atr_period=10, mult=3.0)

    # atr_stop_mult huge -> ATR stop can never fire; exit is the trend flip only.
    metrics = _backtest(
        df, entry, exit_, atr_arr, atr_stop_mult=1e9, warmup=warmup, bars_per_year=8766
    )
    assert metrics["n_trades"] == 1, f"expected exactly one trade, got {metrics['n_trades']}"

    open_arr = df["open"].to_numpy(dtype=np.float64)
    fill_entry = open_arr[entry_flip + 1] * (1.0 + SLIPPAGE)
    fill_exit = open_arr[exit_flip + 1] * (1.0 - SLIPPAGE)
    expected_pnl_pct = ((fill_exit - fill_entry) / fill_entry - 2.0 * COMMISSION_TAKER) * 100.0

    assert abs(metrics["pnl_pct"] - expected_pnl_pct) < 1e-6, (
        f"realised PnL {metrics['pnl_pct']:.6f}% != open[i+1]-fill PnL "
        f"{expected_pnl_pct:.6f}%. A same-bar (open[i]) fill would use the absurd "
        f"open[{entry_flip}]={open_arr[entry_flip]} / open[{exit_flip}]="
        f"{open_arr[exit_flip]} and diverge wildly (look-ahead)."
    )
