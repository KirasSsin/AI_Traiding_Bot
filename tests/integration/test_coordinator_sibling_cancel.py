"""ADR 0020 sub-decisions 6+7: Spot Stop Triggered→Filled gap is 0ms; Triggered is the only
window to cancel sibling before it self-fills. Cancel-of-Filled (retCode 110001) is classified
REJECT_ORDER_ALREADY_TERMINAL (non-fatal race) — treat as SIBLING_CANCELLED.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

import pytest

from src.execution.bybit.adapter import CancelResult, OrderAck
from src.execution.bybit.errors import ReasonCode as AdapterReasonCode
from src.execution.coordinator import Coordinator
from src.execution.state_machine import ExecutionState
from src.execution.state_repo import ExecutionStateRepo, ExecutionStateRow


@dataclass
class _FakeAdapter:
    placed_orders: list[dict] = field(default_factory=list)
    cancel_calls: list[dict] = field(default_factory=list)
    next_cancel_result: AdapterReasonCode | None = None  # if set, cancel returns non-cancelled with this reason

    def place_order(self, *, symbol, side, qty, order_link_id=None, extra_payload=None):
        self.placed_orders.append({"symbol": symbol, "side": side, "qty": str(qty),
                                    "orderLinkId": order_link_id})
        return OrderAck(order_id=f"EX-{order_link_id}", order_link_id=order_link_id)

    def cancel_order(self, *, symbol, order_id):
        self.cancel_calls.append({"symbol": symbol, "orderId": order_id})
        if self.next_cancel_result is not None:
            reason = self.next_cancel_result
            self.next_cancel_result = None
            return CancelResult(cancelled=False, reason_code=reason)
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
    # Seed repo as if bracket armed
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
        "bracket_id": bracket_id, "tp_oid": tp_oid, "sl_oid": sl_oid,
    })()


def test_sl_triggered_cancels_tp_sibling(coordinator_armed_harness):
    h = coordinator_armed_harness
    h.coordinator.on_order_event({
        "orderLinkId": f"oco-{h.bracket_id}-sl-1",
        "orderStatus": "Triggered",
        "side": "Sell",
        "cumExecQty": "0",
    })
    cancelled = [c for c in h.adapter.cancel_calls if c["orderId"] == h.tp_oid]
    assert len(cancelled) == 1
    row = h.repo.get("BTCUSDT")
    # After successful cancel, sibling transitions to FLAT per FSM: OCO_ARMED→SL_TRIGGERED→EXIT_SIBLING_CANCELLING→SIBLING_CANCELLED→FLAT
    assert row.state == ExecutionState.FLAT


def test_tp_filled_cancels_sl_sibling(coordinator_armed_harness):
    h = coordinator_armed_harness
    h.coordinator.on_order_event({
        "orderLinkId": f"oco-{h.bracket_id}-tp-1",
        "orderStatus": "Filled",
        "side": "Sell",
        "cumExecQty": "0.001",
    })
    cancelled = [c for c in h.adapter.cancel_calls if c["orderId"] == h.sl_oid]
    assert len(cancelled) == 1
    row = h.repo.get("BTCUSDT")
    assert row.state == ExecutionState.FLAT


def test_sibling_already_filled_classified_non_fatal(coordinator_armed_harness):
    """cancel returns 110001 → REJECT_ORDER_ALREADY_TERMINAL: treat as expected race → FLAT, NOT HALTED."""
    h = coordinator_armed_harness
    h.adapter.next_cancel_result = AdapterReasonCode.REJECT_ORDER_ALREADY_TERMINAL
    h.coordinator.on_order_event({
        "orderLinkId": f"oco-{h.bracket_id}-sl-1",
        "orderStatus": "Triggered",
        "side": "Sell",
        "cumExecQty": "0",
    })
    row = h.repo.get("BTCUSDT")
    assert row.state == ExecutionState.FLAT
