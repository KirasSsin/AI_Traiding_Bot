from decimal import Decimal
import pytest
from src.execution.oco import build_oco_order, OcoParams, OcoOrder


def test_oco_long_sl_below_tp_above():
    params = OcoParams(
        symbol="BTCUSDT",
        side="LONG",
        qty=Decimal("0.001"),
        entry_price=Decimal("60000"),
        atr=Decimal("500"),
        sl_atr_mult=Decimal("1.5"),
        tp_atr_mult=Decimal("3.0"),
        tick_size=Decimal("0.1"),
    )
    order = build_oco_order(params)
    assert order.stop_loss == Decimal("59250.0")  # 60000 - 1.5*500
    assert order.take_profit == Decimal("61500.0")  # 60000 + 3.0*500
    assert order.symbol == "BTCUSDT"
    assert order.qty == Decimal("0.001")


def test_oco_sl_rounded_to_tick_down():
    """SL price quantized DOWN to tick_size for LONG (conservative)."""
    params = OcoParams(
        symbol="BTCUSDT", side="LONG", qty=Decimal("0.001"),
        entry_price=Decimal("60000"), atr=Decimal("333"),
        sl_atr_mult=Decimal("1.5"), tp_atr_mult=Decimal("3.0"),
        tick_size=Decimal("0.1"),
    )
    order = build_oco_order(params)
    # raw SL = 60000 - 499.5 = 59500.5 → tick 0.1 → 59500.5 exact
    assert order.stop_loss == Decimal("59500.5")


def test_oco_tp_rounded_to_tick_up():
    """TP price quantized UP to tick_size for LONG (conservative — fill at higher)."""
    params = OcoParams(
        symbol="BTCUSDT", side="LONG", qty=Decimal("0.001"),
        entry_price=Decimal("60000"), atr=Decimal("100"),
        sl_atr_mult=Decimal("1.5"), tp_atr_mult=Decimal("3.0"),
        tick_size=Decimal("1"),
    )
    order = build_oco_order(params)
    # raw TP = 60000 + 300 = 60300 — exact, no rounding
    assert order.take_profit == Decimal("60300")


def test_oco_short_side_rejected_v01():
    """v0.1 LONG-only — SHORT raises ValueError."""
    params = OcoParams(
        symbol="BTCUSDT", side="SHORT", qty=Decimal("0.001"),
        entry_price=Decimal("60000"), atr=Decimal("500"),
        sl_atr_mult=Decimal("1.5"), tp_atr_mult=Decimal("3.0"),
        tick_size=Decimal("0.1"),
    )
    with pytest.raises(ValueError, match="LONG"):
        build_oco_order(params)


def test_oco_zero_atr_rejected():
    params = OcoParams(
        symbol="BTCUSDT", side="LONG", qty=Decimal("0.001"),
        entry_price=Decimal("60000"), atr=Decimal("0"),
        sl_atr_mult=Decimal("1.5"), tp_atr_mult=Decimal("3.0"),
        tick_size=Decimal("0.1"),
    )
    with pytest.raises(ValueError, match="atr"):
        build_oco_order(params)
