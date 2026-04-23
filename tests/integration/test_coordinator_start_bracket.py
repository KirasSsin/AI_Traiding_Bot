"""ADR 0020 sub-decision 2: start_bracket places entry Market BUY,
transitions FLAT → ENTRY_PENDING, persists bracket_id + attempt=1."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

import pytest

from src.execution.coordinator import Coordinator
from src.execution.state_machine import ExecutionState
from src.execution.state_repo import ExecutionStateRepo


@dataclass
class _FakeAdapter:
    placed_orders: list[dict] = field(default_factory=list)

    def place_order(self, *, symbol, side, qty, order_link_id=None, extra_payload=None):
        self.placed_orders.append({
            "symbol": symbol, "side": side, "qty": str(qty),
            "orderLinkId": order_link_id,
        })
        from src.execution.bybit.adapter import OrderAck
        return OrderAck(order_id=f"EX-{order_link_id}", order_link_id=order_link_id)


@pytest.fixture
def coordinator_harness(tmp_path):
    db_path = tmp_path / "exec.db"
    conn = sqlite3.connect(db_path)
    migrations_dir = Path("migrations")
    for name in ("001_initial.sql", "0003_execution_state.sql", "0004_execution_state_v2.sql"):
        conn.executescript((migrations_dir / name).read_text())
    repo = ExecutionStateRepo(conn)
    adapter = _FakeAdapter()
    reconciler = None
    return type(
        "H", (),
        {"adapter": adapter, "repo": repo, "reconciler": reconciler, "conn": conn},
    )()


def test_start_bracket_emits_entry_and_persists_bracket_id(coordinator_harness):
    h = coordinator_harness
    coord = Coordinator(
        adapter=h.adapter, repo=h.repo, reconciler=h.reconciler,
        symbol="BTCUSDT", base_coin="BTC",
    )
    bracket_id = coord.start_bracket(
        entry_qty=Decimal("0.001"), entry_side="Buy",
        tp_price=Decimal("70000.00"), sl_trigger_price=Decimal("60000.00"),
    )
    assert h.adapter.placed_orders[-1]["orderLinkId"] == f"oco-{bracket_id}-entry-1"
    row = h.repo.get("BTCUSDT")
    assert row is not None
    assert row.state == ExecutionState.ENTRY_PENDING
    assert row.bracket_id == bracket_id
    assert row.last_attempt_num == 1
    assert len(bracket_id) == 8


def test_start_bracket_returns_unique_bracket_ids(coordinator_harness):
    """Sequential start_bracket calls from FLAT yield distinct bracket_ids."""
    h = coordinator_harness
    coord = Coordinator(
        adapter=h.adapter, repo=h.repo, reconciler=h.reconciler,
        symbol="BTCUSDT", base_coin="BTC",
    )
    id1 = coord.start_bracket(
        entry_qty=Decimal("0.001"), entry_side="Buy",
        tp_price=Decimal("70000"), sl_trigger_price=Decimal("60000"),
    )
    # Reset to FLAT between calls (simulating bracket completion)
    row = h.repo.get("BTCUSDT")
    h.repo.upsert(
        type(row)(
            symbol=row.symbol,
            state=ExecutionState.FLAT,
            position_qty=row.position_qty,
            entry_price=row.entry_price,
            oco_main_order_id=row.oco_main_order_id,
            bracket_id=row.bracket_id,
            oco_tp_order_id=row.oco_tp_order_id,
            oco_sl_order_id=row.oco_sl_order_id,
            expected_oco_qty=row.expected_oco_qty,
            arming_started_at=row.arming_started_at,
            last_attempt_num=row.last_attempt_num,
            updated_at=row.updated_at,
        )
    )
    id2 = coord.start_bracket(
        entry_qty=Decimal("0.001"), entry_side="Buy",
        tp_price=Decimal("70000"), sl_trigger_price=Decimal("60000"),
    )
    assert id1 != id2
