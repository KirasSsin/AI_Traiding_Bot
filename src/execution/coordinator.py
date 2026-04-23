"""Execution coordinator: wires Reconciler into FSM on WS reconnect.

ADR 0019 sub-decision 3 (Reconcile-as-truth).
"""
from __future__ import annotations

from datetime import UTC, datetime

from src.execution.reconciler import Reconciler, ReconcileResult, ReconcileVerdict
from src.execution.state_machine import (
    TRANSITIONS,
    ExecutionEvent,
    ExecutionState,
    apply,
)
from src.execution.state_repo import ExecutionStateRepo, ExecutionStateRow


class Coordinator:
    """Minimal v0.1 coordinator: handles WS reconnect path only.

    Other event paths (entry/exit/risk halt) wired in S6+.
    """

    def __init__(
        self,
        repo: ExecutionStateRepo,
        reconciler: Reconciler,
        symbol: str,
    ) -> None:
        self._repo = repo
        self._reconciler = reconciler
        self._symbol = symbol

    def handle_ws_reconnect(self) -> ExecutionState:
        """Reconcile local FSM state vs exchange. Persist + return final state.

        Flow:
        1. Read local row.
        2. If current state has no WS_RECONNECT transition (FLAT/INIT/HALTED/etc),
           short-circuit: nothing to reconcile, return current as-is.
        3. Otherwise apply WS_RECONNECT → RECONCILING.
        4. Run reconciler.reconcile(symbol, local).
        5. Apply RECONCILE_OK or RECONCILE_DIVERGENCE per verdict.
        6. Persist new state to repo (exchange wins on divergence — ADR 0019).
        """
        local = self._repo.get(self._symbol)
        current = local.state if local is not None else ExecutionState.INIT

        if (current, ExecutionEvent.WS_RECONNECT) not in TRANSITIONS:
            return current

        reconciling = apply(current, ExecutionEvent.WS_RECONNECT)
        result = self._reconciler.reconcile(self._symbol, local)

        if result.verdict == ReconcileVerdict.DIVERGENCE:
            final = apply(reconciling, ExecutionEvent.RECONCILE_DIVERGENCE)
        else:
            final = apply(reconciling, ExecutionEvent.RECONCILE_OK)

        self._persist(final, result)
        return final

    def _persist(self, state: ExecutionState, result: ReconcileResult) -> None:
        """Write new state to repo using exchange-side truth as ADR 0019 dictates."""
        ex = result.exchange_state
        qty = ex.position.qty
        entry = ex.position.avg_price
        # First open order's id, if any (v0.1 has at most one OCO main leg)
        oco_id: str | None = ex.open_orders[0].order_id if ex.open_orders else None
        row = ExecutionStateRow(
            symbol=self._symbol,
            state=state,
            position_qty=qty,
            entry_price=entry,
            oco_main_order_id=oco_id,
            updated_at=datetime.now(tz=UTC).isoformat(),
        )
        self._repo.upsert(row)
