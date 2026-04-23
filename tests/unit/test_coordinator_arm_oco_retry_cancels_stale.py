"""Sprint 6 trading-logic-reviewer Blocker #3 — arm_oco retry cancels stale legs.

Without this guard, a retry from OCO_ARMING (after a partial-arm crash, a
WS-reconnect, or an arming-TTL halt-and-resume) would place a fresh
``oco-{bid}-tp-{N+1}`` while the stale ``oco-{bid}-tp-{N}`` is still live on
the venue. Two TP legs and two SL legs at once = double exit and unbounded
short on Spot if both fire.

Invariant: arm_oco MUST attempt to cancel any persisted oco_tp_order_id /
oco_sl_order_id before placing the new attempt. Cancellation is best-effort
(110001 = already terminal is OK; transient adapter failure must not block
the rearm — placement is the safety-critical path).
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from src.execution.bybit.errors import ReasonCode as AdapterReasonCode
from src.execution.coordinator import Coordinator
from src.execution.state_machine import ExecutionState
from src.execution.state_repo import ExecutionStateRepo, ExecutionStateRow

BRACKET_ID = "deadbeef"


@dataclass
class _Ack:
    order_id: str


@dataclass
class _CancelResult:
    cancelled: bool
    reason_code: object | None = None


class _StubAdapter:
    def __init__(self, *, cancel_raises: bool = False,
                 cancel_returns_already_terminal: bool = False) -> None:
        self.cancels: list[str] = []
        self.tp_placements: list[tuple[Decimal, Decimal, str]] = []
        self.sl_placements: list[tuple[Decimal, Decimal, str]] = []
        self._cancel_raises = cancel_raises
        self._cancel_returns_already_terminal = cancel_returns_already_terminal
        self._tp_counter = 0
        self._sl_counter = 0

    def cancel_order(self, *, symbol: str, order_id: str):  # noqa: D401
        self.cancels.append(order_id)
        if self._cancel_raises:
            raise RuntimeError("transient venue error")
        if self._cancel_returns_already_terminal:
            return _CancelResult(cancelled=False,
                                 reason_code=AdapterReasonCode.REJECT_ORDER_ALREADY_TERMINAL)
        return _CancelResult(cancelled=True)

    def place_limit_order(self, *, symbol: str, side: str, qty: Decimal,
                          price: Decimal, order_link_id: str):
        self._tp_counter += 1
        self.tp_placements.append((qty, price, order_link_id))
        return _Ack(order_id=f"TP-NEW-{self._tp_counter}")

    def place_stop_market_order(self, *, symbol: str, side: str, qty: Decimal,
                                trigger_price: Decimal, order_link_id: str):
        self._sl_counter += 1
        self.sl_placements.append((qty, trigger_price, order_link_id))
        return _Ack(order_id=f"SL-NEW-{self._sl_counter}")


def _seed(repo: ExecutionStateRepo, *, state: ExecutionState,
          tp_oid: str | None, sl_oid: str | None,
          last_attempt_num: int = 1) -> None:
    repo.upsert(ExecutionStateRow(
        symbol="BTCUSDT",
        state=state,
        position_qty=Decimal("0.001"),
        entry_price=Decimal("65000"),
        oco_main_order_id=None,
        bracket_id=BRACKET_ID,
        oco_tp_order_id=tp_oid,
        oco_sl_order_id=sl_oid,
        expected_oco_qty=Decimal("0.001"),
        arming_started_at=None,
        last_attempt_num=last_attempt_num,
        updated_at=datetime.now(tz=UTC).isoformat(),
    ))


def _make(tmp_path: Path, **adapter_kwargs):
    db_path = tmp_path / "exec.db"
    conn = sqlite3.connect(db_path)
    for p in sorted(Path("migrations").glob("*.sql")):
        conn.executescript(p.read_text())
    repo = ExecutionStateRepo(conn)
    adapter = _StubAdapter(**adapter_kwargs)
    coord = Coordinator(adapter=adapter, repo=repo, reconciler=None,
                        symbol="BTCUSDT", base_coin="BTC")
    return coord, repo, adapter


# --- Behaviour ----

def test_arm_oco_first_attempt_does_not_cancel_anything(tmp_path):
    coord, repo, adapter = _make(tmp_path)
    _seed(repo, state=ExecutionState.LONG_OPEN, tp_oid=None, sl_oid=None,
          last_attempt_num=0)
    coord.arm_oco(tp_price=Decimal("70000"),
                  sl_trigger_price=Decimal("60000"),
                  oco_qty=Decimal("0.001"))
    assert adapter.cancels == []
    assert len(adapter.tp_placements) == 1
    assert len(adapter.sl_placements) == 1


def test_arm_oco_retry_cancels_stale_tp_and_sl_first(tmp_path):
    coord, repo, adapter = _make(tmp_path)
    _seed(repo, state=ExecutionState.OCO_ARMING,
          tp_oid="TP-OLD", sl_oid="SL-OLD", last_attempt_num=1)
    coord.arm_oco(tp_price=Decimal("70000"),
                  sl_trigger_price=Decimal("60000"),
                  oco_qty=Decimal("0.001"))
    # Both stale legs cancelled before any new placement
    assert adapter.cancels == ["TP-OLD", "SL-OLD"]
    assert len(adapter.tp_placements) == 1
    assert len(adapter.sl_placements) == 1
    # New legs persisted, replacing the stale order ids
    row = repo.get("BTCUSDT")
    assert row.oco_tp_order_id == "TP-NEW-1"
    assert row.oco_sl_order_id == "SL-NEW-1"


def test_arm_oco_retry_treats_already_terminal_cancel_as_ok(tmp_path):
    """retCode 110001 (REJECT_ORDER_ALREADY_TERMINAL) on cancel of a stale
    leg is non-fatal — the order had already self-filled / expired.
    Re-arm must still proceed and place fresh legs."""
    coord, repo, adapter = _make(tmp_path,
                                  cancel_returns_already_terminal=True)
    _seed(repo, state=ExecutionState.OCO_ARMING,
          tp_oid="TP-OLD", sl_oid="SL-OLD", last_attempt_num=1)
    coord.arm_oco(tp_price=Decimal("70000"),
                  sl_trigger_price=Decimal("60000"),
                  oco_qty=Decimal("0.001"))
    assert adapter.cancels == ["TP-OLD", "SL-OLD"]
    assert len(adapter.tp_placements) == 1
    assert len(adapter.sl_placements) == 1


def test_arm_oco_retry_swallows_cancel_exception_and_still_rearms(tmp_path):
    """Transient exception cancelling a stale leg must not abort re-arm.
    Placing the fresh legs is the safety-critical path; the stale leg will
    be reaped by reconcile / bootstrap."""
    coord, repo, adapter = _make(tmp_path, cancel_raises=True)
    _seed(repo, state=ExecutionState.OCO_ARMING,
          tp_oid="TP-OLD", sl_oid="SL-OLD", last_attempt_num=1)
    coord.arm_oco(tp_price=Decimal("70000"),
                  sl_trigger_price=Decimal("60000"),
                  oco_qty=Decimal("0.001"))
    # Cancel attempted on at least the TP leg (SL may or may not be reached
    # depending on impl, but TP MUST be tried first).
    assert "TP-OLD" in adapter.cancels
    assert len(adapter.tp_placements) == 1
    assert len(adapter.sl_placements) == 1
