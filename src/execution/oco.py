"""Build OCO bracket orders. ADR 0019 sub-decision 1."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_DOWN, ROUND_UP, Decimal


@dataclass(frozen=True)
class OcoParams:
    symbol: str
    side: str  # "LONG" only in v0.1
    qty: Decimal
    entry_price: Decimal
    atr: Decimal
    sl_atr_mult: Decimal
    tp_atr_mult: Decimal
    tick_size: Decimal


@dataclass(frozen=True)
class OcoOrder:
    symbol: str
    side: str
    qty: Decimal
    entry_price: Decimal
    stop_loss: Decimal
    take_profit: Decimal


def build_oco_order(params: OcoParams) -> OcoOrder:
    """Compute SL/TP from ATR for a LONG entry. SL → tick-DOWN, TP → tick-UP.

    Raises:
        ValueError: side != LONG (v0.1 LONG-only) or atr <= 0.
    """
    if params.side != "LONG":
        raise ValueError(f"v0.1 supports LONG only, got {params.side}")
    if params.atr <= 0:
        raise ValueError(f"atr must be > 0, got {params.atr}")

    raw_sl = params.entry_price - params.sl_atr_mult * params.atr
    raw_tp = params.entry_price + params.tp_atr_mult * params.atr

    sl = raw_sl.quantize(params.tick_size, rounding=ROUND_DOWN)
    tp = raw_tp.quantize(params.tick_size, rounding=ROUND_UP)

    return OcoOrder(
        symbol=params.symbol,
        side=params.side,
        qty=params.qty,
        entry_price=params.entry_price,
        stop_loss=sl,
        take_profit=tp,
    )
