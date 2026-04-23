---
title: Execution — 12-state Harel FSM
type: component
tags: [execution, fsm, state-machine, sprint-5]
created: 2026-04-23
updated: 2026-04-23
sources: [src/execution/state_machine.py, src/execution/state_repo.py, src/execution/coordinator.py, migrations/0003_execution_state.sql, project/decisions/0019-sprint-5-execution-decisions.md]
status: stable
---

# Execution — State Machine

**TL;DR:** 12 explicit состояний (Harel-style) + table-driven `TRANSITIONS` (29 пар). Иллегальные переходы → `IllegalTransitionError` → ERROR. SQLite persist через `ExecutionStateRepo` (warm-start) + reconcile-as-truth на startup/reconnect.

## States (12)

| # | State | Описание |
|---|---|---|
| 1 | INIT | старт процесса, до загрузки state |
| 2 | FLAT | нет открытых позиций |
| 3 | ENTRY_PENDING | entry ордер отправлен, ждём fill |
| 4 | LONG_OPEN | позиция открыта, OCO ещё не выставлен |
| 5 | OCO_ARMED | позиция + OCO активен (нормальный режим) |
| 6 | PARTIAL_FILL | partial OCO fill |
| 7 | EXIT_PENDING | exit ордер отправлен |
| 8 | RECONCILING | post-reconnect compare |
| 9 | HALTED | risk halt — держим позицию, не торгуем |
| 10 | COOLDOWN | пауза перед re-entry |
| 11 | ERROR | unrecoverable, manual intervention |
| 12 | KILLED | kill-switch, всё остановлено |

## Persistence

Schema `execution_state` (PK = `symbol`), `migrations/0003_execution_state.sql`. Decimal stored as TEXT. Coordinator пишет на каждом transition end (exchange wins per ADR 0019).

## Key properties

- Table-driven (см. `TRANSITIONS: dict[(State, Event), State]`) — нет implicit if/else.
- 29 канонических переходов (см. `src/execution/state_machine.py`).
- `(state, event) not in TRANSITIONS` → `IllegalTransitionError`.
- `WS_RECONNECT` валиден только для LONG_OPEN / OCO_ARMED / PARTIAL_FILL.

## Known limitations (v0.1, defer to S6)

Зафиксировано post-merge ревью S5 (commits 67622b5..b5d79cc, ADR 0019 follow-up):

- **Нет startup reconcile.** `Coordinator.handle_ws_reconnect` на `INIT` (local=None) короткозамыкается без вызова reconciler. Если на старте на бирже уже есть позиция от прошлой crashed-сессии — она не подхватится. **S6:** добавить `Coordinator.bootstrap()` который вызывает `reconciler.reconcile(symbol, None)` всегда и при divergence уходит в HALTED.
- **`ENTRY_PENDING` / `EXIT_PENDING` без `WS_RECONNECT`.** Если WS падает между place_order и fill, после reconnect FSM остаётся в pending state — silent drift, если ордер тем временем заполнился. **S6:** добавить `(ENTRY_PENDING|EXIT_PENDING, WS_RECONNECT) → RECONCILING` + reconciler verdicts промотируют в LONG_OPEN/FLAT/HALTED по exchange truth.
- **`_persist` берёт первый open order как OCO main leg.** v0.1 single-symbol BTC/USDT обычно безопасно (один OCO активен), но fragile. **S6:** matching по `orderLinkId` префиксу (`s5-open-`/`s5-oco-`).

## Related

- `[[../decisions/0019-sprint-5-execution-decisions]]` — sub-decision 2 (12-state) + sub-decision 3 (persistence).
- `[[reconciler]]` — потребитель `RECONCILING` → `RECONCILE_OK`/`RECONCILE_DIVERGENCE`.
- `[[../../trading/concepts/reason-codes]]` — `HALT_RECONCILE_DIVERGENCE`, `EXIT_OCO_PARTIAL_TIMEOUT`.
- `[[../architecture/state-machine]]` — pre-S5 high-level Harel-set (12 states тот же).

## Sources

- `src/execution/{state_machine,state_repo,coordinator}.py`, `migrations/0003_execution_state.sql`.
