"""Execution coordinator — Sprint 6 (ADR 0020 sub-decision 2).

Orchestrates 3-order Spot OCO emulation:
1. start_bracket: Market BUY entry, FLAT → ENTRY_PENDING, persist bracket_id.
2. on_order_event: WS event router (Tasks 17-18 will extend).
3. arm_oco / flatten helpers (Tasks 19+).

S5 handle_ws_reconnect removed — ws-reconnect handling moves to Task 22 bootstrap.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from src.execution.bracket import BracketParams, build_bracket
from src.execution.bybit.errors import ReasonCode as AdapterReasonCode
from src.execution.state_machine import ExecutionEvent, ExecutionState, apply
from src.execution.state_repo import ExecutionStateRepo, ExecutionStateRow


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


class Coordinator:
    """Sprint 6 Coordinator — orchestrates 3-order Spot OCO emulation."""

    def __init__(
        self,
        *,
        adapter: Any,
        repo: ExecutionStateRepo,
        reconciler: Any,
        symbol: str,
        base_coin: str,
    ) -> None:
        self._adapter = adapter
        self._repo = repo
        self._reconciler = reconciler
        self._symbol = symbol
        self._base_coin = base_coin

    def start_bracket(
        self,
        *,
        entry_qty: Decimal,
        entry_side: str,
        tp_price: Decimal,
        sl_trigger_price: Decimal,
    ) -> str:
        """ADR 0020 sub-decision 2: place Market entry leg, transition FLAT → ENTRY_PENDING.

        TP/SL legs are armed later in on_entry_filled (Task 19 arm_oco).
        Returns the generated 8-char bracket_id (UUIDv4 prefix fits Bybit 36-char orderLinkId).
        """
        bracket_id = str(uuid.uuid4())[:8]
        params = BracketParams(
            symbol=self._symbol,
            entry_qty=entry_qty,
            entry_side=entry_side,  # type: ignore[arg-type]
            tp_price=tp_price,
            sl_trigger_price=sl_trigger_price,
            bracket_id=bracket_id,
            attempt=1,
        )
        legs = build_bracket(params)
        self._adapter.place_order(
            symbol=self._symbol,
            side=legs.entry.side,
            qty=legs.entry.qty,
            order_link_id=legs.entry.order_link_id,
        )
        current = self._repo.get(self._symbol)
        cur_state = current.state if current is not None else ExecutionState.INIT
        if cur_state == ExecutionState.INIT:
            cur_state = apply(cur_state, ExecutionEvent.STATE_LOADED)
        new_state = apply(cur_state, ExecutionEvent.ENTRY_PLACED)
        self._repo.upsert(
            ExecutionStateRow(
                symbol=self._symbol,
                state=new_state,
                position_qty=Decimal("0"),
                entry_price=None,
                oco_main_order_id=None,
                bracket_id=bracket_id,
                oco_tp_order_id=None,
                oco_sl_order_id=None,
                expected_oco_qty=None,
                arming_started_at=None,
                last_attempt_num=1,
                updated_at=_now_iso(),
            )
        )
        return bracket_id

    def on_order_event(self, evt: dict) -> None:
        """ADR 0020 sub-decisions 6+7: WS event router.

        Routes Triggered/Filled/PartiallyFilled events to sibling-cancel and
        residual-flatten handlers. The Triggered→Filled gap on Bybit Spot Stop
        is 0ms, so Triggered is the only window to cancel the sibling before
        it self-fills; a 110001 response is a non-fatal race (sub-decision 6).
        """
        link_id = evt.get("orderLinkId", "")
        status = evt.get("orderStatus", "")
        role = self._role_from_link_id(link_id)
        if status == "Triggered" and role == "sl":
            self._transition(ExecutionEvent.SL_TRIGGERED)
            self._cancel_sibling(role_to_cancel="tp")
        elif status == "Filled" and role == "tp":
            self._transition(ExecutionEvent.TP_HIT)
            self._cancel_sibling(role_to_cancel="sl")
        elif status == "PartiallyFilled" and role == "sl":
            self._handle_sl_partial(evt)

    def _handle_sl_partial(self, evt: dict) -> None:
        """Placeholder for IOC partial handling — Task 18 (ADR 0020 sub-decision 4)."""

    def _cancel_sibling(self, *, role_to_cancel: str) -> None:
        """Cancel the surviving sibling leg once its pair fired.

        On a 110001 response (REJECT_ORDER_ALREADY_TERMINAL) the sibling had
        already self-filled in the 0ms Triggered→Filled window — classify as
        SIBLING_CANCELLED (non-fatal race, ADR 0020 sub-decision 6).
        """
        row = self._repo.get(self._symbol)
        if row is None:
            return
        sibling_oid = row.oco_tp_order_id if role_to_cancel == "tp" else row.oco_sl_order_id
        if sibling_oid is None:
            self._transition(ExecutionEvent.SIBLING_CANCELLED)
            return
        res = self._adapter.cancel_order(symbol=self._symbol, order_id=sibling_oid)
        if res.cancelled:
            self._transition(ExecutionEvent.SIBLING_CANCELLED)
        elif res.reason_code is AdapterReasonCode.REJECT_ORDER_ALREADY_TERMINAL:
            self._transition(ExecutionEvent.SIBLING_CANCELLED)
        else:
            self._transition(ExecutionEvent.SIBLING_CANCEL_FAILED)

    def _role_from_link_id(self, link_id: str) -> str | None:
        """Extract the role ('tp'/'sl'/'entry') from orderLinkId.

        Pattern: oco-{bracket}-{role}-{attempt} → role is second-from-last token.
        """
        parts = link_id.split("-")
        return parts[-2] if len(parts) >= 4 else None

    def _transition(self, event: ExecutionEvent) -> None:
        """Apply FSM event to persisted row and upsert with refreshed timestamp."""
        current = self._repo.get(self._symbol)
        if current is None:
            return
        new_state = apply(current.state, event)
        self._repo.upsert(
            ExecutionStateRow(
                symbol=current.symbol,
                state=new_state,
                position_qty=current.position_qty,
                entry_price=current.entry_price,
                oco_main_order_id=current.oco_main_order_id,
                bracket_id=current.bracket_id,
                oco_tp_order_id=current.oco_tp_order_id,
                oco_sl_order_id=current.oco_sl_order_id,
                expected_oco_qty=current.expected_oco_qty,
                arming_started_at=current.arming_started_at,
                last_attempt_num=current.last_attempt_num,
                updated_at=_now_iso(),
            )
        )
