# tests/unit/test_bracket_builder.py
"""ADR 0020 sub-decision 2: 3-order Spot OCO bracket. Pure function — no I/O."""
from decimal import Decimal
import re
import uuid
from src.execution.bracket import (
    BracketParams, BracketLegs, build_bracket, make_order_link_id, ROLE_ENTRY, ROLE_TP, ROLE_SL,
)


def test_build_bracket_returns_three_legs_with_shared_bracket_id():
    p = BracketParams(
        symbol="BTCUSDT",
        entry_qty=Decimal("0.001"),
        entry_side="Buy",
        tp_price=Decimal("70000.00"),
        sl_trigger_price=Decimal("60000.00"),
        bracket_id="abc-uuid",
        attempt=1,
    )
    legs = build_bracket(p)
    assert legs.entry.role == ROLE_ENTRY
    assert legs.tp.role == ROLE_TP
    assert legs.sl.role == ROLE_SL
    assert legs.entry.order_link_id == "oco-abc-uuid-entry-1"
    assert legs.tp.order_link_id    == "oco-abc-uuid-tp-1"
    assert legs.sl.order_link_id    == "oco-abc-uuid-sl-1"


def test_make_order_link_id_pattern_and_length():
    lid = make_order_link_id(bracket_id="abc-uuid", role="tp", attempt=2)
    assert lid == "oco-abc-uuid-tp-2"
    assert re.match(r"^oco-[A-Za-z0-9_-]+-(entry|tp|sl)-\d+$", lid)
    short = make_order_link_id(bracket_id=str(uuid.uuid4())[:8], role="entry", attempt=1)
    assert len(short) <= 36


def test_tp_and_sl_legs_use_sell_side_when_entry_buy():
    p = BracketParams(
        symbol="BTCUSDT", entry_qty=Decimal("0.001"), entry_side="Buy",
        tp_price=Decimal("70000.00"), sl_trigger_price=Decimal("60000.00"),
        bracket_id="x", attempt=1,
    )
    legs = build_bracket(p)
    assert legs.entry.side == "Buy"
    assert legs.tp.side == "Sell"
    assert legs.sl.side == "Sell"
