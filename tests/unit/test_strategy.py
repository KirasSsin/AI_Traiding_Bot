"""Unit tests for signalgen.strategy — on_bar contract scenarios."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from src.marketdata.models import Bar, DataQuality
from src.signalgen.strategy import EmaCrossoverAdxRsiStrategy


def _bar(close: float, idx: int, symbol: str = "BTCUSDT") -> Bar:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    ot = t0 + timedelta(hours=idx)
    ct = ot + timedelta(hours=1) - timedelta(microseconds=1)
    return Bar(
        symbol=symbol,
        interval="1h",
        open_time=ot,
        close_time=ct,
        open=Decimal(str(close)),
        high=Decimal(str(close + 0.5)),
        low=Decimal(str(close - 0.5)),
        close=Decimal(str(close)),
        volume=Decimal("1.0"),
        trade_count=1,
        is_closed=True,
        data_quality=DataQuality.OK,
    )


def test_strategy_returns_none_during_warmup() -> None:
    """Стратегия требует warm-up = max(slow_ema, 2·adx_period) закрытых баров.

    На первых 30 закрытых барах сигнал = None.
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
    for i in range(30):
        result = strat.on_bar(_bar(100.0 + i * 0.1, i))
        assert result is None, f"bar {i}: ожидался warm-up None, получили {result}"


def test_strategy_skips_non_closed_bars() -> None:
    """is_closed=False баров стратегия игнорирует (execution-timing invariant)."""
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
    live_bar = _bar(100.0, 0).model_copy(update={"is_closed": False})
    assert strat.on_bar(live_bar) is None
    assert len(strat._bars) == 0  # type: ignore[attr-defined]
