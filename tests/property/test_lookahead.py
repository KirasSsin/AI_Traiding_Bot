"""Property tests: look-ahead invariant от execution-timing.md."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from src.marketdata.models import Bar, DataQuality
from src.signalgen.models import Signal
from src.signalgen.strategy import EmaCrossoverAdxRsiStrategy


@st.composite
def bar_sequence(draw: st.DrawFn, min_size: int = 80, max_size: int = 200) -> list[Bar]:
    n = draw(st.integers(min_value=min_size, max_value=max_size))
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    prices = draw(
        st.lists(
            st.decimals(min_value="50.0", max_value="200.0", places=2),
            min_size=n,
            max_size=n,
        )
    )
    bars: list[Bar] = []
    for i, p in enumerate(prices):
        ot = t0 + timedelta(hours=i)
        ct = ot + timedelta(hours=1) - timedelta(microseconds=1)
        high = p + Decimal("0.5")
        low = p - Decimal("0.5")
        bars.append(
            Bar(
                symbol="BTCUSDT",
                interval="1h",
                open_time=ot,
                close_time=ct,
                open=p,
                high=high,
                low=low,
                close=p,
                volume=Decimal("1.0"),
                trade_count=1,
                is_closed=True,
                data_quality=DataQuality.OK,
            )
        )
    return bars


@given(bar_sequence())
@settings(
    deadline=None,
    max_examples=30,
    suppress_health_check=[HealthCheck.too_slow],
)
def test_signal_generated_at_ge_bar_close_time(bars: list[Bar]) -> None:
    """Look-ahead invariant: signal.generated_at >= signal.bar_close_time для каждого signal.

    Fuzz-тест: any random hourly OHLC sequence -> любой emitted Signal удовлетворяет invariant'у
    (pydantic Signal validator + strategy contract).
    """
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
    signals: list[Signal] = []
    for b in bars:
        sig = strat.on_bar(b)
        if sig is not None:
            signals.append(sig)

    for s in signals:
        assert s.generated_at >= s.bar_close_time, (
            f"look-ahead violation: generated_at={s.generated_at} < "
            f"bar_close_time={s.bar_close_time}"
        )
