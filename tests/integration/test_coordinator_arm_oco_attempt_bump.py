"""ADR 0020 sub-decision 9: arm_oco bumps last_attempt_num on retry so orderLinkId is unique.
Bybit rejects duplicate orderLinkId with retCode 10006."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

import pytest

from src.execution.bybit.adapter import OrderAck
from src.execution.coordinator import Coordinator
from src.execution.state_machine import ExecutionState
from src.execution.state_repo import ExecutionStateRepo, ExecutionStateRow


@dataclass
class _FakeAdapter:
    placed_orders: list[dict] = field(default_factory=list)
    fail_next_stop_order: bool = False
    fail_next_limit_order: bool = False

    def place_limit_order(self, *, symbol, side, qty, price, order_link_id):
        if self.fail_next_limit_order:
            self.fail_next_limit_order = False
            raise RuntimeError("simulated limit order failure")
        self.placed_orders.append({
            "symbol": symbol, "side": side, "qty": str(qty), "price": str(price),
            "orderLinkId": order_link_id, "orderType": "Limit",
        })
        return OrderAck(order_id=f"EX-{order_link_id}", order_link_id=order_link_id)

    def place_stop_market_order(self, *, symbol, side, qty, trigger_price, order_link_id):
        if self.fail_next_stop_order:
            self.fail_next_stop_order = False
            raise RuntimeError("simulated stop order failure")
        self.placed_orders.append({
            "symbol": symbol, "side": side, "qty": str(qty), "triggerPrice": str(trigger_price),
            "orderLinkId": order_link_id, "orderType": "Market", "orderFilter": "StopOrder",
        })
        return OrderAck(order_id=f"EX-{order_link_id}", order_link_id=order_link_id)


@pytest.fixture
def coordinator_long_open_harness(tmp_path):
    db_path = tmp_path / "exec.db"
    conn = sqlite3.connect(db_path)
    for p in sorted(Path("migrations").glob("*.sql")):
        conn.executescript(p.read_text())
    repo = ExecutionStateRepo(conn)
    adapter = _FakeAdapter()
    bracket_id = "abcd1234"
    repo.upsert(ExecutionStateRow(
        symbol="BTCUSDT",
        state=ExecutionState.LONG_OPEN,
        position_qty=Decimal("0.001"),
        entry_price=Decimal("65000"),
        oco_main_order_id=None,
        bracket_id=bracket_id,
        oco_tp_order_id=None,
        oco_sl_order_id=None,
        expected_oco_qty=None,
        arming_started_at=None,
        last_attempt_num=0,  # not yet armed
        updated_at="2026-04-23T10:00:00+00:00",
    ))
    coord = Coordinator(adapter=adapter, repo=repo, reconciler=None,
                        symbol="BTCUSDT", base_coin="BTC")
    return type("H", (), {"adapter": adapter, "repo": repo, "coordinator": coord,
                           "bracket_id": bracket_id})()


def test_arm_oco_first_attempt_uses_attempt_one_and_reaches_armed(coordinator_long_open_harness):
    h = coordinator_long_open_harness
    h.coordinator.arm_oco(
        tp_price=Decimal("70000"), sl_trigger_price=Decimal("60000"),
        oco_qty=Decimal("0.001"),
    )
    row = h.repo.get("BTCUSDT")
    assert row.state == ExecutionState.OCO_ARMED
    assert row.last_attempt_num == 1
    assert row.oco_tp_order_id == f"EX-oco-{h.bracket_id}-tp-1"
    assert row.oco_sl_order_id == f"EX-oco-{h.bracket_id}-sl-1"
    assert any(o["orderLinkId"] == f"oco-{h.bracket_id}-tp-1" for o in h.adapter.placed_orders)
    assert any(o["orderLinkId"] == f"oco-{h.bracket_id}-sl-1" for o in h.adapter.placed_orders)


def test_arm_oco_bumps_attempt_on_retry_after_sl_failure(coordinator_long_open_harness):
    h = coordinator_long_open_harness
    # First attempt: TP places OK, SL fails
    h.adapter.fail_next_stop_order = True
    h.coordinator.arm_oco(
        tp_price=Decimal("70000"), sl_trigger_price=Decimal("60000"),
        oco_qty=Decimal("0.001"),
    )
    row = h.repo.get("BTCUSDT")
    assert row.last_attempt_num == 1
    assert row.state in (ExecutionState.OCO_ARMING, ExecutionState.LONG_OPEN)
    # Retry: should bump attempt to 2 and use -2 suffix
    h.adapter.fail_next_stop_order = False
    h.coordinator.arm_oco(
        tp_price=Decimal("70000"), sl_trigger_price=Decimal("60000"),
        oco_qty=Decimal("0.001"),
    )
    row = h.repo.get("BTCUSDT")
    assert row.last_attempt_num == 2
    assert row.state == ExecutionState.OCO_ARMED
    # New orderLinkIds use -2 suffix
    assert any(o.get("orderLinkId", "").endswith("-tp-2") for o in h.adapter.placed_orders)
    assert any(o.get("orderLinkId", "").endswith("-sl-2") for o in h.adapter.placed_orders)


def test_arm_oco_persists_arming_started_at(coordinator_long_open_harness):
    h = coordinator_long_open_harness
    h.coordinator.arm_oco(
        tp_price=Decimal("70000"), sl_trigger_price=Decimal("60000"),
        oco_qty=Decimal("0.001"),
    )
    row = h.repo.get("BTCUSDT")
    assert row.arming_started_at is not None  # ISO timestamp set during arm
    assert row.expected_oco_qty == Decimal("0.001")
