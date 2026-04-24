"""ADR 0020 sub-decision 7: Bybit Spot Stop silently rewrites GTC→IOC (probe v3-D).
Stop Market that triggers may PartiallyFill; Coordinator flattens residual via Market Sell.
FSM: OCO_ARMED → EXIT_SL_RESIDUAL → FLAT (on success) or HALTED (on flatten failure).
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

import pytest

from src.execution.bybit.adapter import CancelResult, OrderAck
from src.execution.coordinator import Coordinator
from src.execution.state_machine import ExecutionState
from src.execution.state_repo import ExecutionStateRepo, ExecutionStateRow


@dataclass
class _FakeAdapter:
    placed_orders: list[dict] = field(default_factory=list)
    cancel_calls: list[dict] = field(default_factory=list)
    fail_next_place: bool = False

    def place_order(self, *, symbol, side, qty, order_link_id=None, extra_payload=None):
        if self.fail_next_place:
            self.fail_next_place = False
            raise RuntimeError("simulated place_order failure")
        self.placed_orders.append({
            "symbol": symbol, "side": side, "qty": str(qty),
            "orderLinkId": order_link_id, "orderType": "Market",
        })
        return OrderAck(order_id="EX-flatten", order_link_id=order_link_id)

    def cancel_order(self, *, symbol, order_id):
        self.cancel_calls.append({"symbol": symbol, "orderId": order_id})
        return CancelResult(cancelled=True)


@pytest.fixture
def coordinator_armed_harness(tmp_path):
    db_path = tmp_path / "exec.db"
    conn = sqlite3.connect(db_path)
    for p in sorted(Path("migrations").glob("*.sql")):
        conn.executescript(p.read_text())
    repo = ExecutionStateRepo(conn)
    adapter = _FakeAdapter()
    bracket_id = "abcd1234"
    tp_oid = f"EX-oco-{bracket_id}-tp-1"
    sl_oid = f"EX-oco-{bracket_id}-sl-1"
    repo.upsert(ExecutionStateRow(
        symbol="BTCUSDT",
        state=ExecutionState.OCO_ARMED,
        position_qty=Decimal("0.001"),
        entry_price=Decimal("65000"),
        oco_main_order_id=None,
        bracket_id=bracket_id,
        oco_tp_order_id=tp_oid,
        oco_sl_order_id=sl_oid,
        expected_oco_qty=Decimal("0.001"),
        arming_started_at=None,
        last_attempt_num=1,
        updated_at="2026-04-23T10:00:00+00:00",
    ))
    coord = Coordinator(adapter=adapter, repo=repo, reconciler=None,
                        symbol="BTCUSDT", base_coin="BTC")
    coord._bootstrap_done = True  # pre-S7 fixture predates ADR 0021 bootstrap guard
    return type("H", (), {
        "adapter": adapter, "repo": repo, "coordinator": coord,
        "bracket_id": bracket_id,
    })()


def test_sl_partial_triggers_residual_flatten(coordinator_armed_harness):
    """SL IOC fills 0.0006 of 0.001 → 0.0004 residual → Market Sell flatten → FLAT."""
    h = coordinator_armed_harness
    h.coordinator.on_order_event({
        "orderLinkId": f"oco-{h.bracket_id}-sl-1",
        "orderStatus": "PartiallyFilled",
        "side": "Sell",
        "cumExecQty": "0.0006",
        "leavesQty": "0.0004",
    })
    flatten = [o for o in h.adapter.placed_orders
               if o.get("side") == "Sell"
               and Decimal(o.get("qty", "0")) == Decimal("0.0004")]
    assert len(flatten) == 1
    row = h.repo.get("BTCUSDT")
    assert row.state == ExecutionState.FLAT


def test_sl_partial_zero_leaves_qty_skips_flatten(coordinator_armed_harness):
    """leavesQty=0 means fill completed between events — no residual to flatten, go straight to FLAT."""
    h = coordinator_armed_harness
    h.coordinator.on_order_event({
        "orderLinkId": f"oco-{h.bracket_id}-sl-1",
        "orderStatus": "PartiallyFilled",
        "side": "Sell",
        "cumExecQty": "0.001",
        "leavesQty": "0",
    })
    assert len(h.adapter.placed_orders) == 0  # no flatten order
    row = h.repo.get("BTCUSDT")
    assert row.state == ExecutionState.FLAT


def test_sl_partial_flatten_failure_halts(coordinator_armed_harness):
    """Market Sell flatten fails → FLATTEN_FAILED event → HALTED."""
    h = coordinator_armed_harness
    h.adapter.fail_next_place = True
    h.coordinator.on_order_event({
        "orderLinkId": f"oco-{h.bracket_id}-sl-1",
        "orderStatus": "PartiallyFilled",
        "side": "Sell",
        "cumExecQty": "0.0006",
        "leavesQty": "0.0004",
    })
    row = h.repo.get("BTCUSDT")
    assert row.state == ExecutionState.HALTED
