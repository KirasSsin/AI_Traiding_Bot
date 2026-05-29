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
