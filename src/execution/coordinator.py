"""Execution coordinator — Sprint 6 (ADR 0020 sub-decision 2).

Orchestrates 3-order Spot OCO emulation:
1. start_bracket: Market BUY entry, FLAT → ENTRY_PENDING, persist bracket_id.
2. on_order_event: WS event router (Tasks 17-18 will extend).
3. arm_oco / flatten helpers (Tasks 19+).

S5 handle_ws_reconnect removed — ws-reconnect handling moves to Task 22 bootstrap.
"""

from __future__ import annotations

import logging
import socket
import threading
import uuid
from datetime import UTC, datetime
from decimal import ROUND_DOWN, Decimal
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.execution.reconciler import LocalState

from src.execution.bracket import (
    BracketParams,
    build_bracket,
    compute_oco_qty,
    make_flatten_link_id,
    make_order_link_id,
)
from src.execution.bybit.adapter import BybitAPIError
from src.execution.bybit.errors import ReasonCode as AdapterReasonCode
from src.execution.state_machine import (
    ExecutionEvent,
    ExecutionState,
    IllegalTransitionError,
    apply,
)
from src.execution.state_repo import ExecutionStateRepo, ExecutionStateRow
from src.risk.reason_codes import ReasonCode

_log = logging.getLogger(__name__)


class _SendOutcome(Enum):
    """S55 BYBIT-02 — tri-state result of a flatten Market Sell attempt.

    A flatten cascade fires up to two Market Sells with DIFFERENT orderLinkIds
    (qty vs qty-step), so the S49 B1 / S51 D1 deterministic-orderLinkId dedupe does
    NOT span the two attempts. Collapsing every failure to a single bool ``False``
    therefore conflated two opposite situations:

    * ``NOT_SENT`` — a SYNCHRONOUS rejection (param/balance/filter/rate-limit retCode
      or any non-network error): the order never reached the matching engine, so
      attempt-2 is safe.
    * ``UNKNOWN`` — a NETWORK / I/O exception after submit: the order MAY have landed
      server-side while the ack read failed. Firing attempt-2 (different orderLinkId)
      risks a SECOND real Market Sell → oversell / phantom short on Spot. Must HALT for
      operator reconciliation, never auto-retry.
    * ``SENT_OK`` — the sell succeeded (incl. a 110072 duplicate proving a prior
      idempotent submit already landed).
    """

    SENT_OK = auto()
    NOT_SENT = auto()
    UNKNOWN = auto()


# S55 BYBIT-02 — exceptions whose occurrence means the order MAY already be on the
# matching engine (the ack/response read failed at the transport layer). pybit's
# _retry_with_backoff propagates these WITHOUT retrying (rest.py), so they surface here.
# Treated as UNKNOWN outcome → HALT, never blind attempt-2. OSError covers stdlib
# ConnectionError / socket.timeout (TimeoutError) / BrokenPipeError, etc.
_NETWORK_UNKNOWN_EXC: tuple[type[BaseException], ...]
try:  # pragma: no cover - import wiring only
    import requests.exceptions as _req_exc
    from pybit.exceptions import FailedRequestError as _PybitFailedRequest

    _NETWORK_UNKNOWN_EXC = (
        OSError,
        socket.timeout,
        _req_exc.RequestException,
        _PybitFailedRequest,
    )
except Exception:  # pragma: no cover - defensive: missing optional transport deps
    _NETWORK_UNKNOWN_EXC = (OSError, socket.timeout)


_TERMINAL_STATES: frozenset[ExecutionState] = frozenset(
    {
        ExecutionState.FLAT,
        ExecutionState.HALTED,
        ExecutionState.KILLED,
        ExecutionState.ERROR,
    }
)

_RECONCILABLE_STATES: frozenset[ExecutionState] = frozenset(
    {
        # Entry/exit/arm transitions — primary HEAL targets (ADR 0021 sub-dec 3)
        ExecutionState.ENTRY_PENDING,
        ExecutionState.EXIT_PENDING,
        ExecutionState.OCO_ARMING,
        ExecutionState.EXIT_SIBLING_CANCELLING,
        ExecutionState.EXIT_SL_RESIDUAL,
        # Live armed/open states — covered by S5 (state, WS_RECONNECT)→RECONCILING
        # transitions; reconcile yields AGREE on quiet path, DIVERGENCE on drift.
        ExecutionState.LONG_OPEN,
        ExecutionState.OCO_ARMED,
        ExecutionState.PARTIAL_FILL,  # legacy S5 — back-compat
        ExecutionState.EXIT_SIBLING_CANCEL_FAILED,
    }
)


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
        self._bootstrap_done: bool = False
        self._lock: threading.RLock = threading.RLock()  # ADR 0022 sub-decision 1 — reentrant

    @property
    def symbol(self) -> str:
        """S37 ADR 0057 SD-6: public symbol accessor.

        Replaces `getattr(coord, "_symbol", None)` private leak в RuntimeManager.
        Coordinator owns symbol per ADR 0019 — public property is canonical access.
        """
        return self._symbol

    def current_state(self, symbol: str | None = None) -> ExecutionState | None:
        """S55 ARCH-03: public, lock-protected FSM-state read for callers.

        RuntimeManager's tick-loop pre-check previously read the persisted row via the
        private ``coordinator._repo.get(symbol)`` — OUTSIDE the Coordinator RLock. Because
        the pybit WS thread mutates the same row under the lock (entry-fill → arm, SL-trigger
        → flatten), that cross-thread read was a TOCTOU: the manager could observe FLAT for
        an instant after the WS thread had already begun a transition, racing a second
        ``start_bracket`` against the one-open-order invariant. Reading the row HERE, under
        ``self._lock``, makes the snapshot consistent with the single-writer FSM.

        This is a PURE repo read (no I/O) — it does not reintroduce the S55 ARCH-02
        lock-hoist hazard (which was about blocking REST fetches under the lock). The RLock
        is reentrant, so a caller already holding it (e.g. an internal helper) does not
        deadlock. ``symbol`` defaults to the Coordinator's own symbol; an explicit value is
        accepted for API symmetry with the manager's call site.

        Returns the current ExecutionState, or None when no row is persisted yet.
        """
        sym = symbol if symbol is not None else self._symbol
        with self._lock:
            row = self._repo.get(sym)
            return row.state if row is not None else None

    def on_ws_reconnect(self) -> None:
        """ADR 0021 sub-decisions 1+2+3 — unified reconcile path.

        Called by WS consumer on disconnect AND by bootstrap.
        Routes through RECONCILING state; dispatches on verdict.

        S55 ARCH-02 (lock-hoist): ``reconciler.reconcile`` does blocking REST fetches
        (get_wallet_balance / get_open_orders / get_order) that sleep up to ~15.5s under
        ``_retry_with_backoff`` on rate-limit codes. Previously that ran while the
        Coordinator RLock was held, blocking the pybit WS thread's ``on_order_event``
        (whose SL-trigger sibling-cancel must fire in the 0ms Bybit Spot Triggered→Filled
        gap) → orphan TP self-fill → phantom short. The fix splits the flow into three
        windows: (1) acquire the RLock briefly to validate state + move FLAT→RECONCILING +
        snapshot ``local``; (2) RELEASE the RLock and run reconcile's blocking I/O off-lock
        — the WS thread can now acquire the RLock during the fetch (it sees RECONCILING and
        drops any stale order echo via the existing IllegalTransitionError guard, instead of
        hanging for seconds); (3) re-acquire the RLock to apply the verdict transition. The
        single-writer FSM invariant is preserved: every transition still happens under the
        RLock. Verdict semantics are unchanged — only the lock-hold window narrowed.
        """
        with self._lock:
            row = self._repo.get(self._symbol)
            if row is None:
                return
            state = row.state
            if state not in _RECONCILABLE_STATES:
                _log.debug("on_ws_reconnect: state=%s not reconcilable; noop", state.name)
                return
            self._transition(ExecutionEvent.WS_RECONNECT)  # → RECONCILING
            local = self._build_local_state(row)

        # I/O window: blocking REST fetches run with the RLock RELEASED (ARCH-02).
        result = self._reconciler.reconcile(local, expected_state=state)

        with self._lock:
            if result.verdict == "HEAL_ENTRY_FILLED":
                self._apply_heal_entry_filled(result)
                self._transition(ExecutionEvent.RECONCILE_ENTRY_FILLED)  # → LONG_OPEN
                return
            if result.verdict == "EXITED":
                self._apply_exited()
                self._transition(ExecutionEvent.RECONCILE_EXITED)  # → FLAT
                return
            if result.verdict == "AGREE":
                self._transition(ExecutionEvent.RECONCILE_OK)  # → OCO_ARMED (existing S6 path)
                return
            # DIVERGENCE
            self._set_halt(
                reason=ReasonCode(result.halt_reason or "HALT_RECONCILE_DIVERGENCE"),
                last_event=ExecutionEvent.WS_RECONNECT,
                extra=result.heal_context or {},
            )
            self._transition(ExecutionEvent.RECONCILE_DIVERGENCE)  # → HALTED

    def _build_local_state(self, row: ExecutionStateRow) -> LocalState:
        """Build reconciler LocalState from current repo row."""
        from src.execution.reconciler import LocalState

        return LocalState(
            state=row.state.name,
            position_qty=row.position_qty,
            entry_price=row.entry_price,
            bracket_id=row.bracket_id,
            symbol=self._symbol,
            entry_order_id=row.oco_main_order_id,
            expected_entry_qty=row.expected_oco_qty,
            updated_at=datetime.fromisoformat(row.updated_at) if row.updated_at else None,
        )

    def _apply_heal_entry_filled(self, result: Any) -> None:
        self._upsert_fields(
            position_qty=result.exch_qty,
            entry_price=result.entry_price,
            last_reconcile_at=_now_iso(),
        )

    def _apply_exited(self) -> None:
        self._upsert_fields(
            position_qty=Decimal("0"),
            last_exit_reason="EXIT_RECONCILE_DETECTED",
            last_reconcile_at=_now_iso(),
        )

    def bootstrap(self) -> None:
        """ADR 0021 sub-decision 1: unified reconcile path on cold-/warm-start.

        Flow:
          1. No persisted row → cold start, mark _bootstrap_done = True, noop.
          2. Recover last_attempt_num from exchange evidence (S6 sub-decision 9).
          3. Delegate to on_ws_reconnect — reuses live reconcile path.
          4. Stamp bootstrap_at, mark _bootstrap_done = True.
        """
        with self._lock:
            row = self._repo.get(self._symbol)
            if row is None:
                self._bootstrap_done = True
                return
            self._recover_attempt_num(row)
            self.on_ws_reconnect()
            self._upsert_fields(bootstrap_at=_now_iso())
            self._bootstrap_done = True

    def _recover_attempt_num(self, row: ExecutionStateRow) -> None:
        """Extracted from pre-S7 bootstrap body (ADR 0020 sub-decision 9)."""
        if row.bracket_id is None:
            return
        open_orders = self._adapter.get_open_orders(symbol=self._symbol)
        history = self._adapter.get_order_history(symbol=self._symbol, limit=50)
        max_attempt = self._extract_max_attempt(
            bracket_id=row.bracket_id,
            candidates=list(open_orders) + list(history),
        )
        if max_attempt > row.last_attempt_num:
            self._upsert_fields(last_attempt_num=max_attempt)

    @staticmethod
    def _extract_max_attempt(*, bracket_id: str, candidates: list[dict[str, Any]]) -> int:
        """Parse 'oco-{bracket_id}-{role}-{N}' orderLinkIds, return highest N seen (0 if none)."""
        prefix = f"oco-{bracket_id}-"
        max_n = 0
        for c in candidates:
            lid = c.get("orderLinkId", "") or ""
            if not lid.startswith(prefix):
                continue
            try:
                n = int(lid.split("-")[-1])
                max_n = max(max_n, n)
            except (ValueError, IndexError):
                continue
        return max_n

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
        with self._lock:
            assert self._bootstrap_done, "bootstrap must complete before start_bracket"
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
            entry_ack = self._adapter.place_order(
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
                    # ADR 0021 sub-decision 3: persist entry order_id so post-reconnect
                    # reconcile can fetch its terminal status via get_order and reach
                    # the HEAL_ENTRY_FILLED verdict (bootstrap → reconciler classifier).
                    # Field name is legacy ('oco_main' from S5 single-OCO scheme); the
                    # reconciler reads it as LocalState.entry_order_id.
                    oco_main_order_id=entry_ack.order_id,
                    bracket_id=bracket_id,
                    oco_tp_order_id=None,
                    oco_sl_order_id=None,
                    expected_oco_qty=entry_qty,  # expected_entry_qty for reconciler qty-check
                    arming_started_at=None,
                    last_attempt_num=1,
                    updated_at=_now_iso(),
                    # S55 TL-01: persist planned exit prices so on_order_event can arm
                    # the OCO legs once the entry fills (arm_oco needs both prices).
                    bracket_tp_price=tp_price,
                    bracket_sl_trigger_price=sl_trigger_price,
                )
            )
            return bracket_id

    def on_order_event(self, evt: dict[str, Any]) -> None:
        """ADR 0020 sub-decisions 6+7: WS event router.

        Routes Triggered/Filled/PartiallyFilled events to sibling-cancel and
        residual-flatten handlers. The Triggered→Filled gap on Bybit Spot Stop
        is 0ms, so Triggered is the only window to cancel the sibling before
        it self-fills; a 110001 response is a non-fatal race (sub-decision 6).

        Idempotency / late-event safety: Bybit WS may deliver duplicate or
        out-of-order echoes (e.g. PartiallyFilled then Triggered, or a Filled
        echo arriving after the bracket already halted). Events landing in a
        terminal state (FLAT/HALTED/KILLED/ERROR) are silently dropped with a
        warning; an IllegalTransitionError from the FSM is logged but never
        propagated, so a stale echo cannot kill the executor worker.
        """
        with self._lock:
            assert self._bootstrap_done, "bootstrap must complete before on_order_event"
            link_id = evt.get("orderLinkId", "")
            status = evt.get("orderStatus", "")
            role = self._role_from_link_id(link_id)
            row = self._repo.get(self._symbol)
            if row is None or row.state in _TERMINAL_STATES:
                if row is not None and row.state in _TERMINAL_STATES:
                    _log.warning(
                        "on_order_event.dropped_in_terminal_state state=%s status=%s role=%s link_id=%s",
                        row.state,
                        status,
                        role,
                        link_id,
                    )
                return
            try:
                if role == "entry":
                    if status == "Filled":
                        self._transition(ExecutionEvent.ENTRY_FILLED)  # ENTRY_PENDING → LONG_OPEN
                        # S55 TL-01: arm the OCO bracket immediately on entry fill
                        # (ADR 0020 sub-decision 1: TP+SL legs placed после Filled).
                        # Without this the position stays LONG_OPEN with no SL/TP —
                        # an unbounded-loss defect. arm_oco re-enters self._lock (RLock).
                        self._arm_oco_after_entry_fill(evt)
                    # PartiallyFilled / other entry statuses: no-op (Spot Market BUY
                    # fills atomically; defensive against future SDK changes).
                    return
                if status == "Triggered" and role == "sl":
                    self._transition(ExecutionEvent.SL_TRIGGERED)
                    self._cancel_sibling(role_to_cancel="tp")
                elif status == "Filled" and role == "tp":
                    self._transition(ExecutionEvent.TP_HIT)
                    self._cancel_sibling(role_to_cancel="sl")
                elif status == "PartiallyFilled" and role == "sl":
                    self._handle_sl_partial(evt)
            except IllegalTransitionError as e:
                # Late / duplicate WS echo for an event the FSM has already routed
                # past. Log + drop — never crash the executor on a stale echo.
                _log.warning(
                    "on_order_event.illegal_transition_dropped error=%s status=%s role=%s link_id=%s",
                    e,
                    status,
                    role,
                    link_id,
                )

    def _arm_oco_after_entry_fill(self, evt: dict[str, Any]) -> None:
        """S55 TL-01: arm the OCO bracket from an entry-Filled WS event.

        Computes the fee-aware OCO qty (ADR 0020 sub-decision 6 / G5) from the
        fill echo — Spot Buy fees are deducted from the base coin, so the
        sellable qty is ``cumExecQty - cumExecFee`` floored to the lot step —
        then places the TP Limit + SL Stop-Market legs at the prices persisted
        by start_bracket. Runs under the lock already held by on_order_event
        (arm_oco re-enters the same RLock).

        Fail-closed: if the planned prices or fill qty are missing/invalid (e.g.
        an entry-fill echo arriving on a bracket whose prices were not persisted),
        HALT instead of leaving a naked LONG position with no stop-loss.
        """
        row = self._repo.get(self._symbol)
        if row is None or row.bracket_tp_price is None or row.bracket_sl_trigger_price is None:
            _log.error(
                "arm_after_fill.missing_bracket_prices symbol=%s bracket_id=%s",
                self._symbol,
                row.bracket_id if row is not None else None,
            )
            self._set_halt(
                reason=ReasonCode.HALT_OCO_ARM_TIMEOUT,
                last_event=ExecutionEvent.RISK_HALT,
                extra={"arm_path": "entry_fill", "cause": "missing_bracket_prices"},
            )
            self._transition(ExecutionEvent.RISK_HALT)
            return
        cum_exec_qty = Decimal(str(evt.get("cumExecQty") or "0"))
        cum_exec_fee = Decimal(str(evt.get("cumExecFee") or "0"))
        fee_currency = str(evt.get("feeCurrency") or "")
        oco_qty = compute_oco_qty(
            cum_exec_qty=cum_exec_qty,
            cum_exec_fee=cum_exec_fee,
            fee_currency=fee_currency,
            base_coin=self._base_coin,
            qty_step=self._qty_step(),
        )
        if oco_qty <= Decimal("0"):
            _log.error(
                "arm_after_fill.zero_oco_qty symbol=%s cum_exec_qty=%s cum_exec_fee=%s",
                self._symbol,
                cum_exec_qty,
                cum_exec_fee,
            )
            self._set_halt(
                reason=ReasonCode.HALT_OCO_ARM_TIMEOUT,
                last_event=ExecutionEvent.RISK_HALT,
                extra={"arm_path": "entry_fill", "cause": "zero_oco_qty"},
            )
            self._transition(ExecutionEvent.RISK_HALT)
            return
        self.arm_oco(
            tp_price=row.bracket_tp_price,
            sl_trigger_price=row.bracket_sl_trigger_price,
            oco_qty=oco_qty,
        )

    def _handle_sl_partial(self, evt: dict[str, Any]) -> None:
        """ADR 0020 sub-decision 7: SL IOC partial → flatten residual via Market Sell.

        OCO_ARMED → PARTIAL_FILL event → EXIT_SL_RESIDUAL.
        Then: RESIDUAL_FLATTENED → FLAT, or FLATTEN_FAILED → HALTED.
        Full flatten-cascade retry (Task 21) is out of scope here; single attempt only.

        Sub-decision 6 race-fix: cancel the live TP sibling FIRST. If we
        flatten the residual and transition to FLAT while the TP is still
        on the book, an orphan TP can self-fill on the next bid spike →
        phantom short on Spot (HALT_PHANTOM_SL). Cancellation is best-effort
        and never blocks the safety-critical flatten path; even leavesQty=0
        (SL fully filled in this echo) requires the TP cancel.
        """
        self._transition(ExecutionEvent.PARTIAL_FILL)  # OCO_ARMED → EXIT_SL_RESIDUAL
        row = self._repo.get(self._symbol)
        if row is not None and row.oco_tp_order_id is not None:
            self._best_effort_cancel(row.oco_tp_order_id)
        leaves_qty = Decimal(evt.get("leavesQty", "0"))
        if leaves_qty <= 0:
            self._transition(ExecutionEvent.RESIDUAL_FLATTENED)
            return
        # S49 B1: deterministic orderLinkId — idempotency key so a _retry_with_backoff
        # re-submission (on 170005/170222 after the Sell already landed) is deduped by
        # Bybit instead of executing a second Market Sell. Stable per bracket attempt.
        residual_link_id: str | None = None
        if row is not None and row.bracket_id is not None:
            residual_link_id = make_flatten_link_id(
                bracket_id=row.bracket_id, kind="res", attempt=row.last_attempt_num
            )
        try:
            self._adapter.place_order(
                symbol=self._symbol,
                side="Sell",
                qty=leaves_qty,
                order_link_id=residual_link_id,
            )
        except BybitAPIError as exc:
            # S51 D1: 110072 (OrderLinkedID duplicate) means our prior residual
            # flatten — placed with this SAME deterministic orderLinkId — already
            # landed server-side. Idempotency complete: the residual is flat, so
            # this is success, NOT a spurious HALT. Pin on retCode==110072 (not
            # the reason alone) so a future _MAP change can't swallow another
            # error as "duplicate". Mirrors the 110001 pattern in adapter.cancel_order.
            if exc.ret_code == 110072 and exc.reason is AdapterReasonCode.REJECT_DUPLICATE_ORDER:
                _log.info(
                    "flatten.ioc_residual_duplicate symbol=%s ret_code=%s link_id=%s",
                    self._symbol,
                    exc.ret_code,
                    residual_link_id,
                )
                self._transition(ExecutionEvent.RESIDUAL_FLATTENED)
                return
            self._set_halt(
                reason=ReasonCode.HALT_FLATTEN_FAILED,
                last_event=ExecutionEvent.FLATTEN_FAILED,
                extra={"flatten_path": "ioc_residual", "leaves_qty": str(leaves_qty)},
            )
            self._transition(ExecutionEvent.FLATTEN_FAILED)
            return
        except Exception:  # noqa: BLE001 — any place_order failure → halt+FLATTEN_FAILED (control flow preserved)
            self._set_halt(
                reason=ReasonCode.HALT_FLATTEN_FAILED,
                last_event=ExecutionEvent.FLATTEN_FAILED,
                extra={"flatten_path": "ioc_residual", "leaves_qty": str(leaves_qty)},
            )
            self._transition(ExecutionEvent.FLATTEN_FAILED)
            return
        self._transition(ExecutionEvent.RESIDUAL_FLATTENED)

    def arm_oco(
        self,
        *,
        tp_price: Decimal,
        sl_trigger_price: Decimal,
        oco_qty: Decimal,
    ) -> None:
        """ADR 0020 sub-decisions 2+9: place TP+SL legs with deterministic orderLinkId.

        Bumps last_attempt_num on every call so retry orderLinkIds are unique
        (Bybit rejects duplicate orderLinkId with retCode 10006). Re-entrant from
        LONG_OPEN (first attempt) and OCO_ARMING (retry after partial-arm).
        On leg-place failure, persists bumped attempt + leaves state for caller
        to handle (FSM stays in OCO_ARMING so retry can resume).
        """
        with self._lock:
            row = self._repo.get(self._symbol)
            if row is None or row.bracket_id is None:
                raise RuntimeError("arm_oco called without active bracket_id")
            # Sub-decision 9 race-fix: cancel stale TP/SL from a prior attempt
            # BEFORE placing the new attempt. Without this, a retry from
            # OCO_ARMING (after WS-reconnect, partial-arm crash, or arming-TTL
            # halt-and-resume) leaves the old `oco-{bid}-tp-{N}` live alongside
            # the new `oco-{bid}-tp-{N+1}` → double exit on Spot.
            # Cancellation is best-effort: 110001 (already terminal) and
            # transient adapter errors do NOT block re-placement, since the
            # safety-critical path is getting fresh legs onto the book; any
            # leftover stale leg is reaped by reconcile / bootstrap.
            if row.oco_tp_order_id is not None:
                self._best_effort_cancel(row.oco_tp_order_id)
            if row.oco_sl_order_id is not None:
                self._best_effort_cancel(row.oco_sl_order_id)
            attempt = row.last_attempt_num + 1
            tp_lid = make_order_link_id(bracket_id=row.bracket_id, role="tp", attempt=attempt)
            sl_lid = make_order_link_id(bracket_id=row.bracket_id, role="sl", attempt=attempt)
            # Persist attempt + arming_started_at upfront so a crash mid-arm doesn't reuse the number;
            # also clear stale TP/SL ids so a crash between cancel and new place doesn't
            # leave us pointing at the cancelled order.
            self._upsert_fields(
                last_attempt_num=attempt,
                arming_started_at=_now_iso(),
                expected_oco_qty=oco_qty,
                oco_tp_order_id=None,
                oco_sl_order_id=None,
            )
            try:
                tp_ack = self._adapter.place_limit_order(
                    symbol=self._symbol,
                    side="Sell",
                    qty=oco_qty,
                    price=tp_price,
                    order_link_id=tp_lid,
                )
                self._upsert_fields(oco_tp_order_id=tp_ack.order_id)
                # Transition LONG_OPEN→OCO_ARMING only on first attempt (already there on retry)
                current = self._repo.get(self._symbol)
                if current is not None and current.state == ExecutionState.LONG_OPEN:
                    self._transition(ExecutionEvent.TP_PLACED)
            except Exception:  # noqa: BLE001 — TP leg place failed; bumped attempt persisted, FSM stays OCO_ARMING for retry
                _log.warning("arm_oco.tp_place_failed symbol=%s", self._symbol, exc_info=True)
                return
            try:
                sl_ack = self._adapter.place_stop_market_order(
                    symbol=self._symbol,
                    side="Sell",
                    qty=oco_qty,
                    trigger_price=sl_trigger_price,
                    order_link_id=sl_lid,
                )
                self._upsert_fields(oco_sl_order_id=sl_ack.order_id)
                self._transition(ExecutionEvent.SL_PLACED)
            except Exception:  # noqa: BLE001 — SL leg place failed; FSM stays OCO_ARMING for retry (TP already live)
                _log.warning("arm_oco.sl_place_failed symbol=%s", self._symbol, exc_info=True)
                return

    def flatten(self, *, reason: ReasonCode) -> None:
        """ADR 0020 sub-decision 10: emergency flatten cascade.

        cancel_all_orders → read wallet → step-floor free qty →
        Market Sell → on failure retry once with qty -= qty_step →
        on second failure FLATTEN_FAILED event → HALTED.

        ``reason`` is accepted for caller-API consistency (e.g.
        HALT_RECONCILE_DIVERGENCE) but is not persisted on the row —
        ExecutionStateRow has no halt_reason/last_exit_reason field.
        It is conveyed to operators via the FSM event + structured logger.
        """
        with self._lock:
            self._adapter.cancel_all_orders(symbol=self._symbol)
            wallet = self._adapter.get_wallet_balance(coin=self._base_coin)
            free_qty = wallet.wallet_balance - wallet.locked
            qty_step = self._qty_step()
            qty = self._step_floor(free_qty, qty_step)
            if qty <= Decimal("0"):
                return  # already flat — no-op
            # S49 B1: deterministic orderLinkId per emergency-flatten attempt.
            # The two attempts place DIFFERENT logical orders (qty vs qty-step) → distinct
            # ids; but each id is stable so a _retry_with_backoff re-submission of the SAME
            # attempt (after a rate-limit code post-landing) is deduped by Bybit, preventing
            # a second Market Sell. bracket_id may be None on a bare divergence flatten —
            # fall back to symbol so the key stays deterministic.
            row = self._repo.get(self._symbol)
            flatten_key = row.bracket_id if row is not None and row.bracket_id else self._symbol
            trigger_reason = reason.value if hasattr(reason, "value") else str(reason)

            outcome = self._try_place_market_sell(qty, link_id=self._emg_link_id(flatten_key, 1))
            if outcome is _SendOutcome.SENT_OK:
                return
            # S55 BYBIT-02: attempt-1's outcome is UNKNOWN (network/I/O after submit) —
            # the order may already be live. Attempt-2 carries a DIFFERENT orderLinkId,
            # so Bybit can't dedupe it → a second real Market Sell. HALT instead and let
            # an operator reconcile the true position (no blind double-sell).
            if outcome is _SendOutcome.UNKNOWN:
                self._halt_flatten(trigger_reason, cause="attempt1_unknown_outcome")
                return

            retry_qty = self._step_floor(qty - qty_step, qty_step)
            if retry_qty > Decimal("0"):
                outcome = self._try_place_market_sell(
                    retry_qty, link_id=self._emg_link_id(flatten_key, 2)
                )
                if outcome is _SendOutcome.SENT_OK:
                    return
                if outcome is _SendOutcome.UNKNOWN:
                    self._halt_flatten(trigger_reason, cause="attempt2_unknown_outcome")
                    return

            self._halt_flatten(trigger_reason, cause="both_attempts_not_sent")

    def _halt_flatten(self, trigger_reason: str, *, cause: str) -> None:
        """S55 BYBIT-02 — HALT the emergency-flatten cascade (FLATTEN_FAILED → HALTED).

        ``cause`` distinguishes the unknown-outcome HALT (operator must reconcile a
        possibly-live order) from the both-attempts-rejected HALT.
        """
        self._set_halt(
            reason=ReasonCode.HALT_FLATTEN_FAILED,
            last_event=ExecutionEvent.FLATTEN_FAILED,
            extra={
                "flatten_path": "emergency",
                "trigger_reason": trigger_reason,
                "cause": cause,
            },
        )
        self._transition(ExecutionEvent.FLATTEN_FAILED)

    def _best_effort_cancel(self, order_id: str) -> None:
        """Best-effort cancel for stale arm_oco legs.

        Treats 110001 (REJECT_ORDER_ALREADY_TERMINAL) as success — the
        order had already self-filled or expired. Transient adapter errors
        are swallowed + logged: the safety-critical path is placing the
        fresh legs, and any orphan leg is reaped by reconcile / bootstrap.
        """
        try:
            res = self._adapter.cancel_order(symbol=self._symbol, order_id=order_id)
            if res.cancelled:
                return
            if res.reason_code is AdapterReasonCode.REJECT_ORDER_ALREADY_TERMINAL:
                return
            _log.warning(
                "arm_oco.stale_cancel_unknown_failure order_id=%s reason=%s",
                order_id,
                res.reason_code,
            )
        except Exception as e:
            _log.warning("arm_oco.stale_cancel_exception order_id=%s err=%s", order_id, e)

    @staticmethod
    def _emg_link_id(flatten_key: str, attempt: int) -> str:
        """S49 B1 — deterministic orderLinkId for an emergency-flatten Market Sell attempt.

        flatten_key is bracket_id when present, else the symbol (bare divergence flatten).
        Truncated to Bybit's 36-char limit via make_flatten_link_id.
        """
        return make_flatten_link_id(bracket_id=flatten_key[:24], kind="emg", attempt=attempt)

    def _try_place_market_sell(self, qty: Decimal, *, link_id: str | None = None) -> _SendOutcome:
        """S55 BYBIT-02 — place a flatten Market Sell, returning a TRI-STATE outcome.

        Returns:
            SENT_OK   — the sell landed (incl. a 110072 duplicate of a prior idempotent
                        submit) → flatten stops the cascade.
            NOT_SENT  — a synchronous rejection (retCode / non-network error): nothing
                        reached the engine → flatten may safely try attempt-2.
            UNKNOWN   — a network / I/O exception after submit: the order may already be
                        live server-side → flatten must HALT, NOT fire attempt-2 (a
                        different orderLinkId would dodge dedupe → double-sell).
        """
        try:
            self._adapter.place_order(
                symbol=self._symbol, side="Sell", qty=qty, order_link_id=link_id
            )
            return _SendOutcome.SENT_OK
        except BybitAPIError as exc:
            # S51 D1: 110072 (OrderLinkedID duplicate) — this emergency-flatten
            # Market Sell, placed with this SAME deterministic link_id, already
            # landed server-side. The sell succeeded → SENT_OK so flatten() stops
            # the cascade (no second sell, no HALT). Pin on retCode==110072 to avoid
            # swallowing a different error. Mirrors the 110001 pattern.
            if exc.ret_code == 110072 and exc.reason is AdapterReasonCode.REJECT_DUPLICATE_ORDER:
                _log.info(
                    "flatten.market_sell_duplicate symbol=%s qty=%s ret_code=%s link_id=%s",
                    self._symbol,
                    qty,
                    exc.ret_code,
                    link_id,
                )
                return _SendOutcome.SENT_OK
            # Any other BybitAPIError is a SYNCHRONOUS non-zero-retCode rejection
            # (or a re-wrapped rate-limit exhaustion, S55 BYBIT-03): the matching
            # engine refused the order → nothing landed → NOT_SENT (safe attempt-2).
            _log.warning(
                "flatten.market_sell_rejected symbol=%s qty=%s ret_code=%s",
                self._symbol,
                qty,
                exc.ret_code,
                exc_info=True,
            )
            return _SendOutcome.NOT_SENT
        except _NETWORK_UNKNOWN_EXC:
            # S55 BYBIT-02: transport-layer failure AFTER submit. The order may have
            # reached Bybit while the ack read failed → UNKNOWN outcome. Do NOT auto-fire
            # attempt-2 (it carries a different orderLinkId → no dedupe → second real
            # Market Sell → oversell). flatten() escalates to HALT for operator recon.
            _log.error(
                "flatten.market_sell_unknown_outcome symbol=%s qty=%s link_id=%s",
                self._symbol,
                qty,
                link_id,
                exc_info=True,
            )
            return _SendOutcome.UNKNOWN
        except Exception:  # noqa: BLE001 — non-network failure; nothing landed → safe attempt-2
            _log.warning(
                "flatten.market_sell_failed symbol=%s qty=%s", self._symbol, qty, exc_info=True
            )
            return _SendOutcome.NOT_SENT

    def _qty_step(self) -> Decimal:
        # S55 ARCH-03: read the lot-step via the adapter's PUBLIC step_size property
        # instead of the private _adapter._filters.step_size attribute leak.
        step: Decimal = self._adapter.step_size
        return step

    def _min_order_qty(self) -> Decimal:
        # S55 BYBIT-05: venue minimum-order-qty via the adapter's PUBLIC accessor —
        # used to classify a step-floored residual as unrecoverable dust.
        min_qty: Decimal = self._adapter.min_order_qty
        return min_qty

    @staticmethod
    def _step_floor(value: Decimal, step: Decimal) -> Decimal:
        if step <= 0 or value <= 0:
            return Decimal("0")
        return (value / step).quantize(Decimal("1"), rounding=ROUND_DOWN) * step

    def reconcile_arming_ttl(self, *, now: datetime | None = None, ttl_seconds: int = 60) -> None:
        """ADR 0020 sub-decision 11: stuck OCO_ARMING > TTL → BRACKET_TIMEOUT → HALTED.

        Args:
            now: clock injection for tests; defaults to datetime.now(tz=UTC).
            ttl_seconds: TTL in seconds; defaults to 60 (match settings.oco_arming_ttl_seconds).
        """
        with self._lock:
            row = self._repo.get(self._symbol)
            if (
                row is None
                or row.state != ExecutionState.OCO_ARMING
                or row.arming_started_at is None
            ):
                return
            started = datetime.fromisoformat(row.arming_started_at)
            current = now if now is not None else datetime.now(tz=UTC)
            age = (current - started).total_seconds()
            if age > ttl_seconds:
                self._set_halt(
                    reason=ReasonCode.HALT_OCO_ARM_TIMEOUT,
                    last_event=ExecutionEvent.BRACKET_TIMEOUT,
                    extra={"ttl_seconds": ttl_seconds, "age_seconds": str(age)},
                )
                self._transition(ExecutionEvent.BRACKET_TIMEOUT)

    def _upsert_fields(self, **changes: object) -> None:
        """Read current row, replace named fields, upsert. Bumps updated_at."""
        from dataclasses import replace

        cur = self._repo.get(self._symbol)
        if cur is None:
            return
        new_row = replace(cur, updated_at=_now_iso(), **changes)  # type: ignore[arg-type]
        self._repo.upsert(new_row)

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
        if res.cancelled or res.reason_code is AdapterReasonCode.REJECT_ORDER_ALREADY_TERMINAL:
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
                halt_reason=current.halt_reason,
                last_exit_reason=current.last_exit_reason,
                last_reconcile_at=current.last_reconcile_at,
                bootstrap_at=current.bootstrap_at,
                bracket_tp_price=current.bracket_tp_price,
                bracket_sl_trigger_price=current.bracket_sl_trigger_price,
            )
        )

    def _set_halt(
        self,
        *,
        reason: ReasonCode,
        last_event: ExecutionEvent,
        extra: dict[str, Any] | None = None,
    ) -> None:
        """ADR 0021 sub-decision 5 γ persistence — capture row state BEFORE transition.

        Required ctx keys: state_at_halt, position_qty, oco_tp_id, oco_sl_id,
        expected_qty, last_event, last_attempt_num, arming_started_at.
        """
        row = self._repo.get(self._symbol)
        ctx: dict[str, object] = {
            "state_at_halt": row.state.name if row is not None else None,
            "position_qty": str(row.position_qty) if row is not None else "0",
            "oco_tp_id": row.oco_tp_order_id if row is not None else None,
            "oco_sl_id": row.oco_sl_order_id if row is not None else None,
            "expected_qty": (
                str(row.expected_oco_qty)
                if row is not None and row.expected_oco_qty is not None
                else None
            ),
            "last_event": last_event.name,
            "last_attempt_num": row.last_attempt_num if row is not None else 0,
            "arming_started_at": row.arming_started_at if row is not None else None,
        }
        if extra:
            ctx.update(extra)
        self._repo._set_halt(symbol=self._symbol, reason=reason, context=ctx)

    def request_halt(self, reason: ReasonCode) -> None:
        """Public halt entry-point for RuntimeManager (KILL_SWITCH, RUNTIME_CRASH, STALL).

        Acquires self._lock (RLock — re-entrant if caller already holds).
        Writes halt_reason via _set_halt (primary-wins per S7 γ rule, halt_log appends),
        then transitions FSM state to HALTED via _transition.

        ADR 0022 sub-decisions 5/6/11; ADR 0023 (halt-code → FSM event mapping).
        """
        with self._lock:
            self._set_halt(
                reason=reason,
                last_event=ExecutionEvent.RISK_HALT,
                extra={"source": "request_halt"},
            )
            # FIX (S8b T1): _set_halt writes halt_reason but does not move FSM state.
            # Dispatch the matching event so reconciler / observers branching on
            # state == HALTED stay in sync with halt_reason.
            # Guard: skip transition if already HALTED (S7 γ idempotency — halt_reason
            # primary-wins is already handled by _set_halt; re-dispatching from HALTED
            # would raise IllegalTransitionError since HALTED has no outbound arcs).
            current = self._repo.get(self._symbol)
            if current is not None and current.state != ExecutionState.HALTED:
                if reason == ReasonCode.KILL_SWITCH_REQUESTED:
                    self._transition(ExecutionEvent.KILL_SWITCH_REQUESTED)
                else:
                    # HALT_RUNTIME_CRASH, HALT_BAR_POLL_STALL, HALT_DATA_QUALITY (S9)
                    # → HALTED via RISK_HALT.
                    # Future halt codes MUST add к _REQUEST_HALT_CODES allow-list
                    # в tests/property/test_request_halt_mapping.py — see ADR 0023.
                    self._transition(ExecutionEvent.RISK_HALT)
