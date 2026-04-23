"""ADR 0020 sub-decision 10: emergency flatten of base-coin position.

1. cancel_all_orders to release locked balance
2. Read wallet, free_qty = walletBalance - locked
3. Step-floor → place Market Sell free_qty
4. On failure: retry once with qty -= qty_step (handles step-quantization race)
5. Second failure → FLATTEN_FAILED event → HALTED

Drift fixes vs plan (lines 2309-2406):
- ExecutionStateRow has no `halt_reason` field — assert state==HALTED only.
- ExecutionStateRow has no `last_exit_reason` field — drop those upserts.
- Coordinator attributes are underscore-prefixed (_adapter, _symbol, _repo, _base_coin).
- _halt(...) helper does not exist — use _transition(FLATTEN_FAILED) only.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

import pytest

from src.execution.bybit.adapter import OrderAck, WalletSnapshot
from src.execution.coordinator import Coordinator
from src.execution.state_machine import ExecutionState
from src.execution.state_repo import ExecutionStateRepo, ExecutionStateRow
from src.marketdata.filters import BybitFilters
from src.risk.reason_codes import ReasonCode


@dataclass
class _FakeAdapter:
    """Minimal adapter for flatten cascade — supports cancel_all + place_order + wallet."""

    _filters: BybitFilters
    placed_orders: list[dict] = field(default_factory=list)
    cancel_all_called: bool = False
    fail_next_market_sell: bool = False
    fail_market_sell_count: int = 0
    wallet_balance: Decimal = Decimal("0.001234")
    wallet_locked: Decimal = Decimal("0")

    def cancel_all_orders(self, *, symbol: str) -> None:
        self.cancel_all_called = True

    def get_wallet_balance(self, *, coin: str) -> WalletSnapshot:
        return WalletSnapshot(
            coin=coin,
            wallet_balance=self.wallet_balance,
            available=self.wallet_balance - self.wallet_locked,
            locked=self.wallet_locked,
        )

    def place_order(self, *, symbol, side, qty, order_link_id=None, extra_payload=None):
        if self.fail_market_sell_count > 0:
            self.fail_market_sell_count -= 1
            raise RuntimeError("simulated market sell failure")
        if self.fail_next_market_sell:
            self.fail_next_market_sell = False
            raise RuntimeError("simulated market sell failure")
        self.placed_orders.append({
            "symbol": symbol, "side": side, "qty": str(qty),
            "orderLinkId": order_link_id, "orderType": "Market",
        })
        return OrderAck(order_id="EX-flatten", order_link_id=order_link_id)


@pytest.fixture
def coordinator_armed_harness(tmp_path):
    db_path = tmp_path / "exec.db"
    conn = sqlite3.connect(db_path)
    for p in sorted(Path("migrations").glob("*.sql")):
        conn.executescript(p.read_text())
    repo = ExecutionStateRepo(conn)
    filters = BybitFilters(
        symbol="BTCUSDT",
        step_size=Decimal("0.000001"),
        tick_size=Decimal("0.01"),
        min_order_qty=Decimal("0.000001"),
        max_order_qty=Decimal("100"),
        min_order_amt=Decimal("5"),
    )
    adapter = _FakeAdapter(_filters=filters)
    repo.upsert(ExecutionStateRow(
        symbol="BTCUSDT",
        state=ExecutionState.OCO_ARMED,
        position_qty=Decimal("0.001234"),
        entry_price=Decimal("65000"),
        oco_main_order_id=None,
        bracket_id="abcd1234",
        oco_tp_order_id="EX-tp",
        oco_sl_order_id="EX-sl",
        expected_oco_qty=Decimal("0.001234"),
        arming_started_at=None,
        last_attempt_num=1,
        updated_at="2026-04-23T10:00:00+00:00",
    ))
    coord = Coordinator(adapter=adapter, repo=repo, reconciler=None,
                        symbol="BTCUSDT", base_coin="BTC")
    return type("H", (), {
        "adapter": adapter, "repo": repo, "coordinator": coord,
        "qty_step": filters.step_size,
    })()


def test_flatten_happy_path(coordinator_armed_harness):
    """cancel_all called, then exactly one Market Sell of free_qty (step-floored)."""
    h = coordinator_armed_harness
    h.coordinator.flatten(reason=ReasonCode.HALT_RECONCILE_DIVERGENCE)
    assert h.adapter.cancel_all_called is True
    sells = [o for o in h.adapter.placed_orders
             if o["side"] == "Sell" and o["orderType"] == "Market"]
    assert len(sells) == 1


def test_flatten_retries_with_qty_minus_step_on_failure(coordinator_armed_harness):
    """First Market Sell fails → retry once with qty -= qty_step."""
    h = coordinator_armed_harness
    h.adapter.fail_next_market_sell = True
    h.coordinator.flatten(reason=ReasonCode.HALT_RECONCILE_DIVERGENCE)
    sells = [o for o in h.adapter.placed_orders
             if o["side"] == "Sell" and o["orderType"] == "Market"]
    assert len(sells) == 1  # retry succeeded; only retry got recorded
    # Compare retry qty against what the first attempt would have been (free_qty step-floored).
    # Free qty = 0.001234, step = 0.000001 → first attempt = 0.001234, retry = 0.001233.
    assert Decimal(sells[0]["qty"]) == Decimal("0.001234") - h.qty_step


def test_flatten_halts_on_second_failure(coordinator_armed_harness):
    """Both attempts fail → FLATTEN_FAILED event → HALTED."""
    h = coordinator_armed_harness
    h.adapter.fail_market_sell_count = 2  # both attempts fail
    h.coordinator.flatten(reason=ReasonCode.HALT_RECONCILE_DIVERGENCE)
    row = h.repo.get("BTCUSDT")
    assert row.state == ExecutionState.HALTED
