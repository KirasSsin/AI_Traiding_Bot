"""Unit tests for signalgen.strategy — on_bar contract scenarios."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from src.marketdata.models import Bar, DataQuality
from src.signalgen.models import Signal, SignalSide
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


def _crafted_bars_for_long_entry() -> list[Bar]:
    """Crafted series: 60 downward drift bars + 30 mild-rally bars.

    Goal: после rally EMA(12) crosses above EMA(26), ADX > 25, +DI > -DI,
    RSI < 70 — все LONG entry gates выполняются хотя бы раз.

    Note: rally step намеренно мал (+0.2), чтобы EMA12 пересекла EMA26
    позже, когда RSI уже не overbought (резкий разворот выбивает RSI > 70
    раньше, чем EMAs успевают пересечься).
    """
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    out: list[Bar] = []
    price = 100.0
    # 60 bars downward drift (-0.2 per bar)
    for i in range(60):
        price -= 0.2
        ot = t0 + timedelta(hours=i)
        ct = ot + timedelta(hours=1) - timedelta(microseconds=1)
        out.append(
            Bar(
                symbol="BTCUSDT",
                interval="1h",
                open_time=ot,
                close_time=ct,
                open=Decimal(str(price + 0.1)),
                high=Decimal(str(price + 0.3)),
                low=Decimal(str(price - 0.3)),
                close=Decimal(str(price)),
                volume=Decimal("1.0"),
                trade_count=1,
                is_closed=True,
                data_quality=DataQuality.OK,
            )
        )
    # 30 bars mild rally (+0.2 per bar) — EMAs пересекаются ~idx 74
    for i in range(60, 90):
        price += 0.2
        ot = t0 + timedelta(hours=i)
        ct = ot + timedelta(hours=1) - timedelta(microseconds=1)
        out.append(
            Bar(
                symbol="BTCUSDT",
                interval="1h",
                open_time=ot,
                close_time=ct,
                open=Decimal(str(price - 0.1)),
                high=Decimal(str(price + 0.5)),
                low=Decimal(str(price - 0.5)),
                close=Decimal(str(price)),
                volume=Decimal("1.0"),
                trade_count=1,
                is_closed=True,
                data_quality=DataQuality.OK,
            )
        )
    return out


def test_strategy_emits_long_on_cross_with_gates() -> None:
    """After downtrend→uptrend: EMA12 crosses EMA26 up, ADX>25, +DI>-DI, RSI<70 → LONG."""
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
    bars = _crafted_bars_for_long_entry()
    signals: list[Signal] = []
    for b in bars:
        sig = strat.on_bar(b)
        if sig is not None:
            signals.append(sig)

    longs = [s for s in signals if s.side == SignalSide.LONG]
    assert len(longs) >= 1, f"Expected at least one LONG signal, got {signals!r}"
    s = longs[0]
    assert s.symbol == "BTCUSDT"
    assert s.adx_14 > Decimal("25")
    assert s.rsi_14 < Decimal("70")
    assert s.plus_di_14 > s.minus_di_14
    assert s.ema_fast > s.ema_slow
    assert s.atr_14 > 0
    assert s.generated_at >= s.bar_close_time  # look-ahead invariant


def test_strategy_rejects_when_adx_below_threshold() -> None:
    """Слабый тренд (ADX<threshold) — no signal даже при cross up.

    Искусственно задираем threshold=99 — ADX никогда не превысит.
    """
    strat = EmaCrossoverAdxRsiStrategy(
        symbol="BTCUSDT",
        ema_fast=12,
        ema_slow=26,
        adx_period=14,
        adx_threshold=Decimal("99"),
        rsi_period=14,
        rsi_oversold=Decimal("30"),
        rsi_overbought=Decimal("70"),
        atr_period=14,
    )
    bars = _crafted_bars_for_long_entry()
    signals = [s for b in bars if (s := strat.on_bar(b)) is not None]
    assert all(s.side != SignalSide.LONG for s in signals), "ADX>99 никогда не проходит"


def test_strategy_rejects_when_rsi_overbought() -> None:
    """Низкий rsi_overbought гейт (10) — RSI крафтового рельефа всегда выше."""
    strat = EmaCrossoverAdxRsiStrategy(
        symbol="BTCUSDT",
        ema_fast=12,
        ema_slow=26,
        adx_period=14,
        adx_threshold=Decimal("25"),
        rsi_period=14,
        rsi_oversold=Decimal("5"),
        rsi_overbought=Decimal("10"),
        atr_period=14,
    )
    bars = _crafted_bars_for_long_entry()
    signals = [s for b in bars if (s := strat.on_bar(b)) is not None]
    assert all(s.side != SignalSide.LONG for s in signals), "RSI<10 никогда не выполняется на rally"


def test_strategy_ignores_wrong_symbol() -> None:
    """Бары с чужим символом не буферизируются и не триггерят сигналы."""
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
    eth_bar = _bar(2000.0, 0, symbol="ETHUSDT")
    assert strat.on_bar(eth_bar) is None
    assert len(strat._bars) == 0  # type: ignore[attr-defined]


def test_strategy_emits_flat_on_signal_flip() -> None:
    """После LONG, если EMA12 < EMA26 AND +DI < -DI → FLAT signal."""
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    bars: list[Bar] = []
    price = 100.0

    def _push(i: int, o: float, h: float, lo: float, c: float) -> None:
        ot = t0 + timedelta(hours=i)
        ct = ot + timedelta(hours=1) - timedelta(microseconds=1)
        bars.append(
            Bar(
                symbol="BTCUSDT",
                interval="1h",
                open_time=ot,
                close_time=ct,
                open=Decimal(str(o)),
                high=Decimal(str(h)),
                low=Decimal(str(lo)),
                close=Decimal(str(c)),
                volume=Decimal("1.0"),
                trade_count=1,
                is_closed=True,
                data_quality=DataQuality.OK,
            )
        )

    # Phase A: 60 bars downtrend -0.2 per bar.
    for i in range(60):
        price -= 0.2
        _push(i, price + 0.1, price + 0.3, price - 0.3, price)
    # Phase B: 30 bars gentle rally +0.2 per bar (triggers LONG per Task 9).
    for i in range(60, 90):
        price += 0.2
        _push(i, price - 0.1, price + 0.3, price - 0.3, price)
    # Phase C: 60 bars downtrend reversal -0.3 per bar (stronger to force flip).
    for i in range(90, 150):
        price -= 0.3
        _push(i, price + 0.1, price + 0.4, price - 0.4, price)

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
    signals = [s for b in bars if (s := strat.on_bar(b)) is not None]
    sides = [s.side for s in signals]
    assert SignalSide.LONG in sides, f"Expected LONG before FLAT; got {sides!r}"
    assert SignalSide.FLAT in sides, f"Expected FLAT after reversal; got {sides!r}"
    # LONG must precede FLAT in emission order.
    first_long = next(i for i, s in enumerate(signals) if s.side == SignalSide.LONG)
    first_flat = next(i for i, s in enumerate(signals) if s.side == SignalSide.FLAT)
    assert first_long < first_flat, f"LONG must precede FLAT; got order {sides!r}"
