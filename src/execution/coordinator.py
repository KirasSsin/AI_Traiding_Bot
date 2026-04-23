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
