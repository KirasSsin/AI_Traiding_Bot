---
title: Execution — 16-state Harel FSM (v4, ADR 0023)
type: component
tags: [execution, fsm, state-machine, sprint-5, sprint-6, sprint-7, sprint-8a, sprint-8b, adr-0020, adr-0021, adr-0022, adr-0023]
created: 2026-04-23
updated: 2026-04-25
sources: [src/execution/state_machine.py, src/execution/state_repo.py, src/execution/coordinator.py, migrations/0003_execution_state.sql, migrations/0004_execution_state_v2.sql, migrations/0005_halt_persistence.sql, project/decisions/0019-sprint-5-execution-decisions.md, project/decisions/0020-sprint-6-execution-spot-oco-emulation.md, project/decisions/0021-sprint-7-resilience.md, project/decisions/0022-sprint-8a-live-runtime.md, project/decisions/0023-halt-code-fsm-event-mapping.md]
status: stable
---

# Execution — State Machine

**TL;DR:** **16 states / 30 events / 74 transitions** (live; verify via `.venv/bin/python -c "from src.execution.state_machine import TRANSITIONS, ExecutionEvent; print(len(TRANSITIONS), len(list(ExecutionEvent)))"`). Table-driven `TRANSITIONS` table. Иллегальные переходы → `IllegalTransitionError`. SQLite persist через `ExecutionStateRepo` (warm-start) + reconcile-as-truth на startup/reconnect + γ halt persistence (ADR 0021 sub-decisions 5+9) + KILL_SWITCH_REQUESTED dispatch invariant (ADR 0023).

**Growth history:** S5 v1 = 12 states / 28 events / 29 transitions. S6 v2 (ADR 0020) = 16/29/55. S7 v3 (ADR 0021) = 16/29/59 (dedup S6 silent overrides). S8a (ADR 0022) = +1 event (KILL_SWITCH_REQUESTED) + 11 transitions → 16/30/70. S8b T1 (ADR 0023) = +3 RISK_HALT rows для ENTRY_PENDING/EXIT_PENDING/RECONCILING → 16/30/73. S8b T7 fix-up = +1 (FLAT, RISK_HALT) → **16/30/74 current**.

**Last sync:** Sprint 36 (2026-04-27, tag `v0.1.0-alpha.36`). count = **49 reason codes** — added 4 HALT_S36_* per ADR 0055 SD-4 (T5). FSM states/events/transitions unchanged: 16/30/74.

## States (16)

| # | State | Sprint | Описание |
|---|---|---|---|
| 1 | INIT | S5 | старт процесса, до загрузки state |
| 2 | FLAT | S5 | нет открытых позиций |
| 3 | ENTRY_PENDING | S5 | entry ордер отправлен, ждём fill |
| 4 | LONG_OPEN | S5 | позиция открыта, OCO ещё не выставлен |
| 5 | OCO_ARMING | **S6** | entry filled, TP/SL placement in flight |
| 6 | OCO_ARMED | S5 | позиция + OCO активен (нормальный режим) |
| 7 | PARTIAL_FILL | S5 | legacy S5 — в v2 недостижим (PARTIAL_FILL event → EXIT_SL_RESIDUAL); сохранён для back-compat при загрузке SQLite |
| 8 | EXIT_PENDING | S5 | exit ордер отправлен |
| 9 | EXIT_SIBLING_CANCELLING | **S6** | SL или TP сработал, отменяем вторую ногу |
| 10 | EXIT_SIBLING_CANCEL_FAILED | **S6** | retry-остров: отмена сестринского ордера не прошла (non-110001) |
| 11 | EXIT_SL_RESIDUAL | **S6** | IOC partial SL fill, выравниваем остаток |
| 12 | RECONCILING | S5 | post-reconnect compare |
| 13 | HALTED | S5 | risk halt — держим позицию, не торгуем |
| 14 | COOLDOWN | S5 | пауза перед re-entry |
| 15 | ERROR | S5 | unrecoverable, manual intervention |
| 16 | KILLED | S5 | kill-switch, всё остановлено |

## Persistence

Schema `execution_state` (PK = `symbol`), `migrations/0003_execution_state.sql` + S6 v2 (`0004`) + **S7 halt persistence (`0005`)**. Decimal stored as TEXT. Coordinator пишет на каждом transition end (exchange wins per ADR 0019).

### S7 columns (ADR 0021 sub-decision 5)

| Column | Тип | Назначение |
|---|---|---|
| `halt_reason` | TEXT NULL | Primary wins — first non-null sticks. Не перезаписывается до `MANUAL_RESET` |
| `last_exit_reason` | TEXT NULL | Reason code последнего exit (audit trail) |
| `last_reconcile_at` | TEXT (ISO-8601 UTC) | Время последнего успешного reconcile |
| `bootstrap_at` | TEXT (ISO-8601 UTC) | Время `Coordinator.bootstrap()` (idempotency anchor) |

### S7 audit table (ADR 0021 sub-decision 9)

`halt_log` — append-only:

```sql
CREATE TABLE halt_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    ts TEXT NOT NULL,
    reason TEXT NOT NULL,
    context_json TEXT NOT NULL
);
CREATE INDEX halt_log_symbol_ts ON halt_log(symbol, ts);
```

Write-ahead pattern: запись в `halt_log` **до** обновления `execution_state.halt_reason`. Гарантирует chronological trail даже при crash между write+state-update.

## Events (29 total)

S6 добавил 8 (ADR 0020 sub-decision 8); S7 добавил 3 (ADR 0021 sub-decisions 1, 3):

| Event | Sprint | Описание |
|---|---|---|
| `TP_PLACED` | S6 | TP-нога Limit-ордера успешно выставлена |
| `SL_PLACED` | S6 | SL-нога StopMarket-ордера успешно выставлена |
| `SL_TRIGGERED` | S6 | Stop-ордер перешёл в Triggered (≠ Filled) |
| `SIBLING_CANCELLED` | S6 | Сестринский ордер отменён успешно |
| `SIBLING_CANCEL_FAILED` | S6 | Отмена сестринского ордера отклонена (non-110001) |
| `BRACKET_TIMEOUT` | S6 | TTL=60 с для arming истёк без SL_PLACED |
| `RESIDUAL_FLATTENED` | S6 | IOC-остаток после SL-частичного заполнения выровнен |
| `FLATTEN_FAILED` | S6 | Flatten-каскад не удался → HALTED |
| `OCO_PARTIAL_TIMEOUT` | S6 | EXIT_OCO_PARTIAL_TIMEOUT branch trigger |
| `RECONCILE_ENTRY_FILLED` | **S7** | Reconciler verdict `HEAL_ENTRY_FILLED` (entry filled offline; heal local) |
| `RECONCILE_EXITED` | **S7** | Reconciler verdict `EXITED` (exit заполнен offline; perevest в FLAT с `EXIT_RECONCILE_DETECTED`) |

## Key properties

- Table-driven (см. `TRANSITIONS: dict[(State, Event), State]`) — нет implicit if/else.
- **59 канонических переходов** (S5: 29, S6 net-adds: +26 с дублирующими S5-ключами OVERRIDE'ом; **S7: -2 silent dup-keys удалены, +6 reconcile/timeout transitions** = 59 final). Locked в `test_transitions_count_exact*`.
- `(state, event) not in TRANSITIONS` → `IllegalTransitionError`.
- `WS_RECONNECT` валиден для **9 active states** (`_RECONCILABLE_STATES` в coordinator): ENTRY_PENDING, EXIT_PENDING, OCO_ARMING, EXIT_SIBLING_CANCELLING, EXIT_SL_RESIDUAL, LONG_OPEN, OCO_ARMED, PARTIAL_FILL, EXIT_SIBLING_CANCEL_FAILED.

### S7 dedup note (ADR 0021 follow-up)

S6 OVERRIDE-блок переопределял два legacy S5-ключа (`(OCO_ARMED, PARTIAL_FILL)` + `(OCO_ARMED, TP_HIT)`) через silent dict-shadow. Ruff `F601` flag'нул дубликаты в final review S7. Удалены ранние записи; bracket-aware paths остались единственным источником истины.

## Halt-substates (Sprint 6)

5 концептуальных halt-подсостояний реализованы через `HALTED + halt_reason: ReasonCode`:

| halt_reason | Причина |
|---|---|
| `HALT_BRACKET_INCOMPLETE` | OCO arming прервано до завершения |
| `HALT_OCO_ARM_TIMEOUT` | `BRACKET_TIMEOUT` во время `OCO_ARMING` |
| `HALT_OCO_SIBLING_STUCK` | `EXIT_SIBLING_CANCEL_FAILED` + RISK_HALT |
| `HALT_PARTIAL_FILL_BELOW_MIN` | IOC-остаток ниже минимального qty |
| `HALT_FLATTEN_FAILED` | Flatten-каскад не удался |

**Sprint 7 update:** `halt_reason` теперь **persisted** в `execution_state.halt_reason` (ADR 0021 sub-decision 5) + audit-trail в `halt_log` (sub-decision 9). Primary-wins semantics: первая non-null причина залипает до `MANUAL_RESET`. S6-only обработчики (без write через `state_repo.set_halt_reason()`) считаются legacy и подлежат миграции.

### S7 halts (ADR 0021)

Добавлены 2 новых halt-substate'а (через `halt_reason`, не state-enum):

| halt_reason | Триггер |
|---|---|
| `HALT_BOOTSTRAP_AMBIGUOUS` | Bootstrap reconcile не смог классифицировать local↔exchange расхождение |
| `HALT_EXIT_RECONCILE_DIVERGENCE` | Exit-фаза reconcile увидела mismatch между local EXIT_PENDING и exchange |

## Closed in S7 (ADR 0021)

Все три pre-S6 limitations (startup reconcile / pending+WS_RECONNECT / fragile OCO main lookup) закрыты:

- **C1 closed (S6 + S7):** `Coordinator.bootstrap()` всегда вызывает `reconciler.reconcile()` для классификации; `_bootstrap_done` assert на всех external entry points.
- **C2 closed (S7):** `(ENTRY_PENDING|EXIT_PENDING, WS_RECONNECT) → RECONCILING` промотирует через 4-valued reconciler verdict (`AGREE` / `DIVERGENCE` / `HEAL_ENTRY_FILLED` / `EXITED`).
- **OCO main lookup (S6):** `oco_main_order_id` пишется в `start_bracket()` из `entry_ack.order_id` (не угадывается по open-orders).

## Invariants (CRITICAL — verified by tests + code review)

| # | Invariant | Enforcement | Test |
|---|-----------|-------------|------|
| 1 | TRANSITIONS table-driven — no implicit if/else dispatch | `src/execution/state_machine.py::TRANSITIONS` dict | `tests/unit/test_execution_fsm.py::test_transitions_count_exact` |
| 2 | `(state, event) not in TRANSITIONS` → `IllegalTransitionError` | `src/execution/state_machine.py::apply` raises | `tests/unit/test_execution_fsm.py::test_illegal_transition_raises` |
| 3 | `WS_RECONNECT` valid for exactly 9 `_RECONCILABLE_STATES` | `src/execution/coordinator.py::_RECONCILABLE_STATES` frozenset | `tests/unit/test_coordinator_on_ws_reconnect.py::test_on_ws_reconnect_flat_state_is_noop` |
| 4 | `halt_log` write-ahead — written BEFORE `execution_state.halt_reason` update | `migrations/0005_halt_persistence.sql` schema; `src/execution/state_repo.py::_set_halt` order | `tests/unit/test_halt_persistence.py::test_set_halt_first_call_writes_column_and_log` |
| 5 | `PARTIAL_FILL` state unreachable in v2 (preserved for SQLite warm-start back-compat only) | `src/execution/state_machine.py::ExecutionState.PARTIAL_FILL` — no inbound transitions in v2 | `tests/unit/test_execution_fsm_v2.py::test_transitions_count_exact_v2` |

## Related

- `[[../decisions/0019-sprint-5-execution-decisions]]` — sub-decision 2 (12-state) + sub-decision 3 (persistence).
- `[[../decisions/0020-sprint-6-execution-spot-oco-emulation]]` — sub-decision 8 (v2 expansion: +4 states, +8 events).
- `[[../decisions/0021-sprint-7-resilience]]` — sub-decisions 1, 3, 5, 9 (bootstrap reconcile + 4-valued verdicts + halt persistence).
- `[[coordinator]]` — owns FSM dispatch (`_transition`) и halt mechanics (`request_halt` + ADR 0023 invariant); 8 RLock-protected methods (S8a).
- `[[reconciler]]` — 4-valued verdict consumer (`AGREE`/`DIVERGENCE`/`HEAL_ENTRY_FILLED`/`EXITED`).
- `[[oco]]` — builder SL/TP уровней, приводит к OCO_ARMING → OCO_ARMED.
- `[[ws-private-consumer]]` — pybit close-hook + check_alive watchdog → triggers `WS_RECONNECT`.
- `[[../../trading/concepts/reason-codes]]` — 42 codes (S7: `HALT_BOOTSTRAP_AMBIGUOUS`, `HALT_EXIT_RECONCILE_DIVERGENCE`, `EXIT_RECONCILE_DETECTED`).
- `[[../architecture/state-machine]]` — pre-S5 high-level Harel-set (12 states тот же).

## Transitions

| States | Event | Target | Примечание |
|---|---|---|---|
| FLAT / ENTRY_PENDING / LONG_OPEN / OCO_ARMING / OCO_ARMED / EXIT_PENDING / EXIT_SIBLING_CANCELLING / EXIT_SIBLING_CANCEL_FAILED / EXIT_SL_RESIDUAL / RECONCILING | `KILL_SWITCH_REQUESTED` | HALTED | ADR 0022 sub-decision 5. Operator-initiated HALT (NOT terminal kill — KILL_SWITCH остаётся для KILLED). |

## Concurrency / Lock policy (S8a)

Все мутации FSM row проходят через `Coordinator._lock` (`threading.RLock`, ADR 0022 sub-decision 1). Это защищает от race между:
- main thread (`start_bracket`, `flatten`, `bootstrap`)
- pybit thread (`on_order_event`, `on_ws_reconnect`)

Reconciler-side: `Reconciler._lock` (`threading.Lock`, non-reentrant) — wraps `on_wallet_event` + `reconcile`.

См. [[runtime-manager]] — Lock policy reference table.

## Sources

- `src/execution/{state_machine,state_repo,coordinator}.py`, `migrations/0003_execution_state.sql`.
