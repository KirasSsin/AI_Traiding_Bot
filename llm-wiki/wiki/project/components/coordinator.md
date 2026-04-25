---
title: Coordinator — execution orchestrator (FSM dispatch + bracket lifecycle + halt mechanics + reconcile)
type: component
tags: [execution, coordinator, orchestrator, fsm, bracket, oco, halt, reconcile, threading, sprint-6, sprint-7, sprint-8a, sprint-8b, adr-0019, adr-0020, adr-0021, adr-0022, adr-0023]
created: 2026-04-25
updated: 2026-04-25
sources:
  - src/execution/coordinator.py
  - src/execution/state_machine.py
  - src/execution/state_repo.py
  - src/execution/reconciler.py
  - migrations/0003_execution_state.sql
  - migrations/0004_execution_state_v2.sql
  - migrations/0005_halt_persistence.sql
  - project/decisions/0019-sprint-5-execution-decisions.md
  - project/decisions/0020-sprint-6-execution-spot-oco-emulation.md
  - project/decisions/0021-sprint-7-resilience.md
  - project/decisions/0022-sprint-8a-live-runtime.md
  - project/decisions/0023-halt-code-fsm-event-mapping.md
status: stable
---

# Coordinator — execution orchestrator

**TL;DR:** Central FSM owner и bracket-lifecycle orchestrator. Файл: `src/execution/coordinator.py` (628 LoC). Owns: `_lock` (threading.RLock, ADR 0022 Task 0), `_bootstrap_done` invariant, `_repo` (`ExecutionStateRepo`), `_reconciler`, `_adapter` (Bybit). Public surface: **8 methods** (bootstrap, on_ws_reconnect, on_order_event, start_bracket, arm_oco, flatten, request_halt, reconcile_arming_ttl). Все mutation paths go через `_transition(event)` → `apply(state, event)` → `_repo.upsert()`. Halt path отдельный: `_set_halt()` (γ persistence S7) + `_transition()` dispatch (ADR 0023 invariant).

## Definition / Purpose

До S5 execution был набор unit-test fixtures без owner'а. ADR 0019 (S5) ввёл `Coordinator` как single FSM mutator (one-writer invariant). S6 (ADR 0020) расширил на 3-order Spot OCO emulation. S7 (ADR 0021) добавил bootstrap reconcile + 4-valued verdicts + γ halt persistence. S8a (ADR 0022) добавил `RLock` (concurrency защита от pybit thread × main thread) + `request_halt` public API. S8b (ADR 0023) зафиксировал halt-code → FSM event mapping invariant.

## Public API

```python
class Coordinator:
    def __init__(
        self,
        *,
        adapter: Any,            # Bybit adapter
        repo: ExecutionStateRepo,
        reconciler: Any,
        symbol: str,
        base_coin: str,
    ) -> None: ...

    # Lifecycle
    def bootstrap(self) -> None: ...                          # cold/warm start, calls on_ws_reconnect
    def on_ws_reconnect(self) -> None: ...                    # unified reconcile path (4-valued)

    # Bracket lifecycle
    def start_bracket(self, *, qty, entry_price, tp_price, sl_price, ...) -> None: ...
    def arm_oco(self, *, bracket_id, ...) -> None: ...        # TP+SL placement
    def flatten(self, *, reason: ReasonCode) -> None: ...     # emergency exit

    # Event sinks
    def on_order_event(self, evt: dict) -> None: ...          # WS private order events

    # Halt
    def request_halt(self, reason: ReasonCode) -> None: ...   # ADR 0022/0023

    # TTL maintenance
    def reconcile_arming_ttl(self, ...) -> None: ...
```

## Threading lock policy (ADR 0022 Task 0 — MANDATORY)

Все 8 публичных методов wrapped в `with self._lock:` block. `_lock = threading.RLock()` (reentrant — нужен потому что `bootstrap()` вызывает `on_ws_reconnect()` внутри собственного lock'а).

| Method | Lock acquisition | Why |
|--------|------------------|-----|
| bootstrap | RLock entered | Re-entry: вызывает on_ws_reconnect inside |
| on_ws_reconnect | RLock entered | Standalone OR called from bootstrap |
| start_bracket | RLock entered | Mutation: writes execution_state row |
| arm_oco | RLock entered | Mutation: TP/SL order IDs written |
| on_order_event | RLock entered | pybit thread → main FSM mutation |
| flatten | RLock entered | Emergency exit, mutates state |
| request_halt | RLock entered | Halt path, mutates halt_reason + state |
| reconcile_arming_ttl | RLock entered | TTL housekeeping |

Защищает от race: pybit thread (`on_order_event`) ↔ main thread (RuntimeManager tick → `start_bracket` / `request_halt`).

## FSM dispatch invariant (ADR 0023)

Всё mutation = `_transition(event)`:

```python
def _transition(self, event: ExecutionEvent) -> None:
    current = self._repo.get(self._symbol)
    if current is None:
        return
    new_state = apply(current.state, event)  # → may raise IllegalTransitionError
    self._repo.upsert(ExecutionStateRow(state=new_state, ...))
```

Halt path (ADR 0023 invariant):

```python
def request_halt(self, reason: ReasonCode) -> None:
    with self._lock:
        self._set_halt(reason=reason, last_event=RISK_HALT, ...)  # γ persistence (S7)
        # ADR 0023: explicit dispatch для каждого halt-class ReasonCode
        current = self._repo.get(self._symbol)
        if current is not None and current.state != ExecutionState.HALTED:
            if reason == ReasonCode.KILL_SWITCH_REQUESTED:
                self._transition(ExecutionEvent.KILL_SWITCH_REQUESTED)
            else:
                # HALT_RUNTIME_CRASH, HALT_BAR_POLL_STALL → HALTED via RISK_HALT
                self._transition(ExecutionEvent.RISK_HALT)
```

**HALTED-guard** preserves S7 γ idempotency: HALTED state не имеет outbound RISK_HALT/KILL_SWITCH_REQUESTED arcs, повторный вызов из HALTED был бы IllegalTransitionError. `_set_halt` уже handled primary-wins persistence — re-entry безопасен.

**Allow-list contract** (S8b T1, enforced via property test `tests/property/test_request_halt_mapping.py`):
```python
_REQUEST_HALT_CODES = frozenset({
    ReasonCode.KILL_SWITCH_REQUESTED,
    ReasonCode.HALT_RUNTIME_CRASH,
    ReasonCode.HALT_BAR_POLL_STALL,
})
```

Future halt code → MUST добавить explicit branch в `request_halt` ИЛИ существующий "RISK_HALT bucket" + TRANSITIONS row(s) для всех source states + property test parameter. Reviewer enforcement: trading-logic-reviewer.md CRITICAL section "Halt-code → FSM event mapping".

## Bootstrap sequencing (ADR 0021 sub-decision 1, ADR 0022 sub-decision 7)

```
bootstrap()
  acquire _lock
  row = _repo.get(symbol)
  if row is None:
      _bootstrap_done = True
      return                   # cold start, no row to reconcile
  _recover_attempt_num(row)    # S6 sub-decision 9: max(persisted, exchange evidence)
  on_ws_reconnect()            # delegates to live reconcile path
  _bootstrap_done = True
```

**Sequencing invariant:** `_bootstrap_done` MUST be True перед любым `start_bracket` / `on_order_event`. Enforced ассертами (S7).

## Reconcile path (4-valued verdicts, ADR 0021 sub-decision 3)

`on_ws_reconnect()` routes через RECONCILING state:

| Verdict | Action | FSM transition |
|---------|--------|----------------|
| AGREE | no-op (no state change beyond RECONCILE_OK ack) | `RECONCILE_OK` → OCO_ARMED |
| HEAL_ENTRY_FILLED | `_apply_heal_entry_filled` (silent state-fix, fill_age ≤ 3600s) | `RECONCILE_ENTRY_FILLED` → LONG_OPEN |
| EXITED | `_apply_exited` (TP/SL terminal observed remotely) | `RECONCILE_EXITED` → FLAT |
| DIVERGENCE | `_set_halt(HALT_RECONCILE_DIVERGENCE)` | `RECONCILE_DIVERGENCE` → HALTED |

`_RECONCILABLE_STATES` frozenset (9 active states) гейт — non-reconcilable states (KILLED, INIT, ERROR) → noop.

## γ Halt persistence (S7 ADR 0021 sub-decisions 5+9)

`_set_halt(reason, last_event, extra)`:
1. Capture row state BEFORE transition (state_at_halt, position_qty, oco_tp_id, oco_sl_id, expected_qty, last_event, last_attempt_num, arming_started_at) → ctx dict.
2. Append to `halt_log` (write-ahead, append-only audit).
3. Update `execution_state.halt_reason` — **primary-wins**: first non-null sticks до MANUAL_RESET. Subsequent halts append to log но не перезаписывают primary halt_reason → root-cause attribution preserved.

Note: `_set_halt(reason: str)` internal wrapper signature всё ещё `str` (не ReasonCode) — carry-over для S8c cleanup (см. `wiki/project/pre-s8c-backlog.md`).

## OCO bracket lifecycle (S6 ADR 0020)

`start_bracket(qty, entry_price, tp_price, sl_price, ...)`:
1. Submit Entry Market order via adapter.
2. Persist `bracket_id`, `oco_main_order_id`, `expected_oco_qty`.
3. Transition: FLAT → ENTRY_PENDING → (on fill via on_order_event) → LONG_OPEN.

`arm_oco(bracket_id, ...)`:
1. Place TP Limit + SL StopMarket IOC orders.
2. Persist `oco_tp_order_id`, `oco_sl_order_id`, `arming_started_at`.
3. Transition: LONG_OPEN → OCO_ARMING → (after both placed) OCO_ARMED.

`reconcile_arming_ttl(...)`:
- TTL housekeeping для OCO_ARMING — если TP/SL не placed within timeout → BRACKET_TIMEOUT event → HALTED.

`on_order_event(evt)`:
- WS private feed routes здесь. Branches on `orderLinkId` role suffix (entry/tp/sl) + status (Filled/PartiallyFilled/Cancelled).
- TP_HIT / SL_TRIGGERED → EXIT_SIBLING_CANCELLING → cancel sibling → SIBLING_CANCELLED → FLAT.
- IOC partial SL → EXIT_SL_RESIDUAL → flatten residual → RESIDUAL_FLATTENED → FLAT.

`flatten(reason)`:
- Emergency exit. Cancel TP+SL siblings, place market sell, transition through EXIT_PENDING → FLAT (or HALTED on failure).

## State persistence

Schema `execution_state` (PK = `symbol`):
- migration `0003_execution_state.sql` — base S5
- migration `0004_execution_state_v2.sql` — S6 expansion (+oco_tp_order_id, +oco_sl_order_id, +bracket_id, +expected_oco_qty, +arming_started_at, +last_attempt_num)
- migration `0005_halt_persistence.sql` — S7 γ (+halt_reason, +last_exit_reason, +last_reconcile_at, +bootstrap_at) + halt_log table

Decimal stored as TEXT. Coordinator упсёртит row на каждом transition end. Exchange wins per ADR 0019 sub-decision 3 (reconcile-as-truth).

## Invariants (CRITICAL — verified by tests + code review)

| # | Invariant | Enforcement | Test |
|---|-----------|-------------|------|
| 1 | `_bootstrap_done=True` before any `start_bracket`/`on_order_event` | `src/execution/coordinator.py::bootstrap` (sets flag at end), assertions in start_bracket/on_order_event | (no test yet — TODO) |
| 2 | All 8 public methods under `RLock` (RE-entrant required because `bootstrap` calls `on_ws_reconnect` while holding lock) | `src/execution/coordinator.py::Coordinator.__init__` (`_lock = threading.RLock()`) + ADR 0022 sub-decision 1 | `tests/unit/test_coordinator_threading.py` |
| 3 | All FSM mutation via `_transition` only — no direct state write | `src/execution/coordinator.py::_transition` — only writer | `tests/unit/test_execution_fsm.py::test_transitions_count_exact` |
| 4 | Halt allow-list: every `ReasonCode` in `request_halt` has explicit dispatch branch + TRANSITIONS row(s) | `src/execution/coordinator.py::request_halt` + ADR 0023 invariant | `tests/property/test_request_halt_mapping.py::test_request_halt_dispatches_every_allow_listed_code` |
| 5 | γ halt persistence — first non-null `halt_reason` sticks, subsequent halts append to `halt_log` but MUST NOT overwrite primary | `src/execution/coordinator.py::_set_halt` + ADR 0021 sub-decisions 5+9 | `tests/unit/test_halt_persistence.py::test_set_halt_secondary_call_log_appends_primary_preserved` |

## Related

- [[execution-state-machine]] — FSM (16 states / 30 events / 74 transitions live)
- [[reconciler]] — 4-valued verdict producer; called from `on_ws_reconnect` and `bootstrap`
- [[oco]] — bracket order semantics (TP Limit + SL StopMarket IOC + sibling cancel)
- [[runtime-manager]] — owner: calls `coordinator.bootstrap()`, `start_bracket()`, `request_halt()`
- [[ws-private-consumer]] — sink: routes order/wallet events → `on_order_event`/`on_wallet_event` (через reconciler)
- [[bybit-adapter]] — REST partner (entry/exit/cancel)
- [[../decisions/0019-sprint-5-execution-decisions]] — Coordinator origin (one-writer invariant)
- [[../decisions/0020-sprint-6-execution-spot-oco-emulation]] — 3-order OCO emulation (start_bracket + arm_oco + on_order_event)
- [[../decisions/0021-sprint-7-resilience]] — bootstrap, on_ws_reconnect 4-valued, _set_halt γ
- [[../decisions/0022-sprint-8a-live-runtime]] — RLock policy (Task 0), request_halt API
- [[../decisions/0023-halt-code-fsm-event-mapping]] — halt-code → FSM event invariant
- [[../runbooks/halt-recovery]] — operator runbook для 19 halt codes (Coordinator owns `request_halt` API + `_set_halt` internal)

## Open questions / S8c carry-over

- `_set_halt(reason: str)` internal wrapper signature → narrow to `ReasonCode` (parity с public `request_halt`).
- ADR 0022 narrative transition count = 73; live = 74 после S8b T7. Amend at next ADR touch.
- mypy --strict: 4 pre-existing errors в coordinator.py (LocalState undef + `dict[Any, Any]`).

## Sources

- `src/execution/coordinator.py:59-628`
- `src/execution/state_machine.py` (TRANSITIONS table, ExecutionEvent enum)
- `src/execution/state_repo.py` (ExecutionStateRepo, ExecutionStateRow, _set_halt write)
- ADRs: 0019, 0020, 0021, 0022, 0023
- `tests/property/test_request_halt_mapping.py` — invariant test (S8b T7)
