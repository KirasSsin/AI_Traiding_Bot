---
title: "0023. Halt-code → FSM event mapping must be exhaustive"
type: decision
status: accepted
date: 2026-04-24
sprint: 8b
tags: [adr, fsm, halt, reason-code, invariant]
sources:
  - wiki/project/decisions/0022-sprint-8a-live-runtime.md
  - wiki/project/components/coordinator.md
  - wiki/project/components/execution-state-machine.md
---

# 0023. Halt-code → FSM event mapping must be exhaustive

**Status:** accepted
**Date:** 2026-04-24
**Sprint:** 8b

## Контекст

Sprint 8a добавил три halt-class `ReasonCode` (`HALT_RUNTIME_CRASH`, `HALT_BAR_POLL_STALL`, `KILL_SWITCH_REQUESTED`) и публичный `Coordinator.request_halt(reason)`. Bug, который проехал ревью S8a и был пойман в S8b carry-over: `request_halt` вызывал `_set_halt(...)` (запись в `halt_reason` + `halt_log`) но **не** вызывал `_transition(...)`. Результат — FSM state оставался в `FLAT` / `LONG_OPEN` / etc., тогда как `halt_reason="KILL_SWITCH_REQUESTED"`. 10 строк `KILL_SWITCH_REQUESTED` в `TRANSITIONS` table стояли как dead code.

Patch (S8b T1) добавил per-branch dispatch:

```python
if reason == ReasonCode.KILL_SWITCH_REQUESTED:
    self._transition(ExecutionEvent.KILL_SWITCH_REQUESTED)
else:
    self._transition(ExecutionEvent.RISK_HALT)
```

Это работает сегодня (3 halt codes), но риск регресса критичный: когда через 2-3 спринта добавят `HALT_LIQUIDITY_LOSS` или `HALT_DATA_QUALITY`, разработчик может забыть добавить explicit dispatch — `else` branch silently подставит `RISK_HALT`, что может не соответствовать намерению (RISK_HALT не имеет transition из state `RECOVERY` или какого-то нового состояния → exception будет, но runtime halt logic уже сломан до того момента).

## Решение

**Каждый `ReasonCode` с префиксом `HALT_*` либо равный `KILL_SWITCH_REQUESTED` ОБЯЗАН иметь explicit dispatch entry в `Coordinator.request_halt()`.** "Ловящий всё" `else` branch допустим только как safety net для текущего множества `RISK_HALT`-mapped кодов; добавление нового кода в `else` без сознательного выбора = баг.

**Three-layer enforcement:**

1. **ADR (this doc)** — binding rule + rationale.
2. **`trading-logic-reviewer.md` CRITICAL section** — block-level review rule "Halt-code → FSM event mapping must be exhaustive" (см. S8b T6).
3. **Property invariant test** (`tests/property/test_request_halt_mapping.py`) — enumerate all `ReasonCode` где `name.startswith("HALT_")` или `name == "KILL_SWITCH_REQUESTED"`; для каждого `request_halt(code)` → assert `state == HALTED` AND `halt_reason == code.value`. Failure surface при добавлении нового кода без wiring.

## Последствия

- При добавлении нового halt-class `ReasonCode`:
  1. Добавить enum entry в `src/risk/reason_codes.py`.
  2. Добавить explicit dispatch branch в `Coordinator.request_halt()` (либо в существующий "RISK_HALT bucket", либо новый event).
  3. Если новый event — добавить TRANSITIONS rows из всех non-terminal source states.
  4. Property test зелёный → ОК. Property test красный → шаг 2/3 не выполнен.
- Dead-code halts больше не возможны: state ↔ halt_reason инвариант проверяется тестом.
- Reviewer prompt update — часть процесса (S8b T6).

## Рассмотренные альтернативы

- **Pure runtime introspection** (no ADR/test): rely на FSM `InvalidTransitionError` чтобы поймать missing dispatch. Reject — exception в production = halt path сломан в момент когда он нужнее всего; better to fail в CI.
- **Generic mapping dict** (`_HALT_REASON_TO_EVENT: dict[ReasonCode, ExecutionEvent]`): меньше boilerplate, но скрывает intent. Reject — explicit branch более читаем, force review при добавлении.

## Ссылки

- ADR 0022 sub-decisions 5/6/11 — halt-class reason codes введены.
- ADR 0021 sub-decision 4 — γ halt persistence (primary-wins) объясняет почему `_set_halt` отделён от `_transition`.
- `src/execution/coordinator.py:600-625` — canonical `request_halt` implementation (post-S8b T1).
- `tests/property/test_request_halt_mapping.py` — invariant test (S8b T7).

**Implementation plan:** [[../plans/2026-04-24-sprint-8b-carryover]].
**Sprint page:** [[../sprints/sprint-08b-carryover]] — delivery record (S8a carry-over fixes + ADR 0023, FSM 70→74, tag `v0.1.0-alpha.8b`).

**Затронутые компоненты:**
- [[../components/coordinator]] — `request_halt()` explicit dispatch (primary enforcement)
- [[../components/execution-state-machine]] — `TRANSITIONS` table (all halt events must have rows from all non-terminal states)
- [[../components/kill-switch-cli]] — `KILL_SWITCH_REQUESTED` dispatch target
