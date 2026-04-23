---
title: Execution — 16-state Harel FSM (v2, ADR 0020)
type: component
tags: [execution, fsm, state-machine, sprint-5, sprint-6, adr-0020]
created: 2026-04-23
updated: 2026-04-23
sources: [src/execution/state_machine.py, src/execution/state_repo.py, src/execution/coordinator.py, migrations/0003_execution_state.sql, project/decisions/0019-sprint-5-execution-decisions.md, project/decisions/0020-sprint-6-execution-spot-oco-emulation.md]
status: stable
---

# Execution — State Machine

**TL;DR:** 16 enum-членов (12 базовых из S5 + 4 новых из S6, ADR 0020) + table-driven `TRANSITIONS` (55 пар). Иллегальные переходы → `IllegalTransitionError`. SQLite persist через `ExecutionStateRepo` (warm-start) + reconcile-as-truth на startup/reconnect.

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

Schema `execution_state` (PK = `symbol`), `migrations/0003_execution_state.sql`. Decimal stored as TEXT. Coordinator пишет на каждом transition end (exchange wins per ADR 0019).

## Events (S6 additions)

Добавлено 8 новых событий в Sprint 6 (ADR 0020 sub-decision 8):

| Event | Описание |
|---|---|
| `TP_PLACED` | TP-нога Limit-ордера успешно выставлена |
| `SL_PLACED` | SL-нога StopMarket-ордера успешно выставлена |
| `SL_TRIGGERED` | Stop-ордер перешёл в Triggered (≠ Filled) |
| `SIBLING_CANCELLED` | Сестринский ордер отменён успешно |
| `SIBLING_CANCEL_FAILED` | Отмена сестринского ордера отклонена (non-110001) |
| `BRACKET_TIMEOUT` | TTL=60 с для arming истёк без SL_PLACED |
| `RESIDUAL_FLATTENED` | IOC-остаток после SL-частичного заполнения выровнен |
| `FLATTEN_FAILED` | Flatten-каскад не удался → HALTED |

## Key properties

- Table-driven (см. `TRANSITIONS: dict[(State, Event), State]`) — нет implicit if/else.
- **55 канонических переходов** (S5: 29, S6 net-adds: +26; locked в `test_transitions_count_exact` и `test_transitions_count_exact_v2`).
- `(state, event) not in TRANSITIONS` → `IllegalTransitionError`.
- `WS_RECONNECT` валиден для LONG_OPEN / OCO_ARMED / PARTIAL_FILL / OCO_ARMING / EXIT_SIBLING_CANCELLING / EXIT_SL_RESIDUAL.

## Halt-substates (Sprint 6)

5 концептуальных halt-подсостояний реализованы через `HALTED + halt_reason: ReasonCode`:

| halt_reason | Причина |
|---|---|
| `HALT_BRACKET_INCOMPLETE` | OCO arming прервано до завершения |
| `HALT_OCO_ARM_TIMEOUT` | `BRACKET_TIMEOUT` во время `OCO_ARMING` |
| `HALT_OCO_SIBLING_STUCK` | `EXIT_SIBLING_CANCEL_FAILED` + RISK_HALT |
| `HALT_PARTIAL_FILL_BELOW_MIN` | IOC-остаток ниже минимального qty |
| `HALT_FLATTEN_FAILED` | Flatten-каскад не удался |

**Важно:** `halt_reason` в Sprint 6 **не хранится** в колонке `ExecutionStateRow` — логируется через structlog при эмиссии FSM-события. Оператор читает event log для получения контекста.

## Known limitations (v0.1, defer to S6, was pre-S6)

Зафиксировано post-merge ревью S5 (commits 67622b5..b5d79cc, ADR 0019 follow-up):

- **Нет startup reconcile.** `Coordinator.handle_ws_reconnect` на `INIT` (local=None) короткозамыкается без вызова reconciler. Если на старте на бирже уже есть позиция от прошлой crashed-сессии — она не подхватится. **S6:** добавить `Coordinator.bootstrap()` который вызывает `reconciler.reconcile(symbol, None)` всегда и при divergence уходит в HALTED.
- **`ENTRY_PENDING` / `EXIT_PENDING` без `WS_RECONNECT`.** Если WS падает между place_order и fill, после reconnect FSM остаётся в pending state — silent drift, если ордер тем временем заполнился. **S6:** добавить `(ENTRY_PENDING|EXIT_PENDING, WS_RECONNECT) → RECONCILING` + reconciler verdicts промотируют в LONG_OPEN/FLAT/HALTED по exchange truth.
- **`_persist` берёт первый open order как OCO main leg.** v0.1 single-symbol BTC/USDT обычно безопасно (один OCO активен), но fragile. **S6:** matching по `orderLinkId` префиксу (`s5-open-`/`s5-oco-`).

## Related

- `[[../decisions/0019-sprint-5-execution-decisions]]` — sub-decision 2 (12-state) + sub-decision 3 (persistence).
- `[[../decisions/0020-sprint-6-execution-spot-oco-emulation]]` — sub-decision 8 (v2 expansion: +4 states, +8 events).
- `[[reconciler]]` — потребитель `RECONCILING` → `RECONCILE_OK`/`RECONCILE_DIVERGENCE`.
- `[[oco]]` — builder SL/TP уровней, приводит к OCO_ARMING → OCO_ARMED.
- `[[../../trading/concepts/reason-codes]]` — `HALT_RECONCILE_DIVERGENCE`, `EXIT_OCO_PARTIAL_TIMEOUT`.
- `[[../architecture/state-machine]]` — pre-S5 high-level Harel-set (12 states тот же).

## Sources

- `src/execution/{state_machine,state_repo,coordinator}.py`, `migrations/0003_execution_state.sql`.
