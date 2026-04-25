# src/execution/bracket.py
"""ADR 0020 sub-decision 2: 3-order Spot OCO bracket builder (pure functions, no I/O).

Bybit Spot V5 has no native OCO; we emulate via:
  1. Entry Market BUY (immediate fill assumed; dust handled via G5 fee-aware sizing)
  2. Limit Sell @ TP (orderType=Limit, timeInForce=GTC)
  3. Stop Market Sell @ SL (orderType=Market, orderFilter=StopOrder, triggerBy=LastPrice)

Correlation: orderLinkId = "oco-{bracket_id}-{role}-{attempt}" — propagated to WS events.
"""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
from typing import Literal

Role = Literal["entry", "tp", "sl"]
ROLE_ENTRY: Role = "entry"
ROLE_TP: Role = "tp"
ROLE_SL: Role = "sl"


@dataclass(frozen=True, slots=True)
class BracketLeg:
    role: Role
    side: Literal["Buy", "Sell"]
    qty: Decimal
    price: Decimal | None
    trigger_price: Decimal | None
    order_link_id: str


@dataclass(frozen=True, slots=True)
class BracketLegs:
    entry: BracketLeg
    tp: BracketLeg
    sl: BracketLeg


@dataclass(frozen=True, slots=True)
class BracketParams:
    symbol: str
    entry_qty: Decimal
    entry_side: Literal["Buy", "Sell"]
    tp_price: Decimal
    sl_trigger_price: Decimal
    bracket_id: str
    attempt: int


def make_order_link_id(*, bracket_id: str, role: Role, attempt: int) -> str:
    """Deterministic orderLinkId. Bybit V5 max length 36 chars."""
    lid = f"oco-{bracket_id}-{role}-{attempt}"
    if len(lid) > 36:
        raise ValueError(f"orderLinkId too long ({len(lid)} > 36): {lid}")
    return lid


def build_bracket(p: BracketParams) -> BracketLegs:
    exit_side: Literal["Buy", "Sell"] = "Sell" if p.entry_side == "Buy" else "Buy"
    return BracketLegs(
        entry=BracketLeg(
            role=ROLE_ENTRY, side=p.entry_side, qty=p.entry_qty,
            price=None, trigger_price=None,
            order_link_id=make_order_link_id(bracket_id=p.bracket_id, role=ROLE_ENTRY, attempt=p.attempt),
        ),
        tp=BracketLeg(
            role=ROLE_TP, side=exit_side, qty=p.entry_qty,
            price=p.tp_price, trigger_price=None,
            order_link_id=make_order_link_id(bracket_id=p.bracket_id, role=ROLE_TP, attempt=p.attempt),
        ),
        sl=BracketLeg(
            role=ROLE_SL, side=exit_side, qty=p.entry_qty,
            price=None, trigger_price=p.sl_trigger_price,
            order_link_id=make_order_link_id(bracket_id=p.bracket_id, role=ROLE_SL, attempt=p.attempt),
        ),
    )


def compute_oco_qty(
    *,
    cum_exec_qty: Decimal,
    cum_exec_fee: Decimal,
    fee_currency: str,
    base_coin: str,
    qty_step: Decimal,
) -> Decimal:
    """ADR 0020 sub-decision 5 (G5): fee-aware OCO qty.

    Spot Buy fees on Bybit are deducted from the base-coin received (BTC), not from the
    quote (USDT). Submitting OCO legs with raw cumExecQty (ignoring fee) leaves dust that
    can't be cancelled and traps the bracket. Floor to qty_step after subtracting.
    """
    if fee_currency == base_coin:
        net = cum_exec_qty - cum_exec_fee
    else:
        net = cum_exec_qty
    if net <= 0:
        return Decimal("0")
    floored = (net / qty_step).quantize(Decimal("1"), rounding=ROUND_DOWN) * qty_step
    return floored
