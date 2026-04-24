---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-04-24
sprint: 7-resilience
phase: 8-finish-pre-merge
branch: feature/sprint-7-resilience
tag: v0.1.0-alpha.7-pending
---

# SPRINT STATE

> Этот файл читается ПЕРВЫМ в каждой сессии. Обновляется после каждого значимого шага.
> Формат намеренно компактный — ≤ 2KB. Не расширяй без причины.

## Текущий статус

**Sprint 7 — Resilience (ADR 0021) — wiki Stage E COMPLETE; Phase G testnet probes PENDING (blocking pre-merge).**
Branch: `feature/sprint-7-resilience`. 33+ commits ahead of main. Tag `v0.1.0-alpha.7` not yet pushed (требует Phase G).

## Завершённые задачи (S7, 25 tasks)

- [x] Migration 0005_halt_persistence.sql (halt_reason + last_exit_reason + bootstrap_at + halt_log audit)
- [x] FSM v3: 16 states / 29 events / 59 transitions (-2 silent dups, +6 reconcile/timeout)
- [x] Reconciler 4-valued verdict (AGREE/DIVERGENCE/HEAL_ENTRY_FILLED/EXITED) + heal_max_age_seconds=3600
- [x] Coordinator.bootstrap() always reconciles + _bootstrap_done assert + _RECONCILABLE_STATES (9 states)
- [x] start_bracket entry_ack.order_id capture для HEAL path
- [x] BybitPrivateWSConsumer: pybit close-hook + check_alive watchdog (ADR 0021 sub-decision 6)
- [x] Reason codes 39→42 (+HALT_BOOTSTRAP_AMBIGUOUS, +HALT_EXIT_RECONCILE_DIVERGENCE, +EXIT_RECONCILE_DETECTED)
- [x] γ halt persistence (write-ahead halt_log → execution_state.halt_reason; primary-wins)
- [x] Property test: bootstrap+ws-reconnect idempotent under N reconnects
- [x] Integration test (opt-in Demo): bootstrap HEAL path
- [x] Final domain reviewers (parallel trading-logic + python): 7 BLOCKERS closed (commit 97b29cb)
- [x] Test suite: 481 unit/integration/property pass; 28 skipped (pre-existing gaps unrelated)
- [x] Wiki Stage E: 5 components + runbook + NEW ws-private-consumer.md + reason-codes + index + log

## В процессе

Phase G testnet probes — **operator-driven**, requires separate testnet API keys (см. `scripts/spot_oco_probe_testnet.py`). Не выполнимо в автономной сессии.

## Следующее действие

Operator: на `api-testnet.bybit.com` с testnet keys прогнать probes B2 + v3-D + v2 S2. После зелёного результата — `git tag v0.1.0-alpha.7`, merge PR в main.

## Ключевые решения последней сессии (S7)

- B1 narrow scope: только passive WS consumer; driver loop отнесён в S8.
- pybit on_disconnect: wired via inner WebSocketApp.on_close + heartbeat watchdog backstop (pybit upgrade resilient).
- 4-valued verdicts с recommended_state hint — coordinator делегирует FSM-выбор reconciler'у.
- halt_reason primary-wins semantics (first non-null sticks до MANUAL_RESET) + halt_log append-only audit.
- heal_max_age_seconds = 3600 (1H bar period) — heal только если fill свежее.

## Блокеры / concerns

- Pre-existing test_risk_flow OverrideStore signature drift (unrelated to S7).
- pyarrow/talib/asyncio test gaps (28 skipped) — defer до S8+.

## Активные файлы (где работаем)

- `src/execution/coordinator.py` — bootstrap + 4-valued verdicts + entry_ack capture
- `src/execution/reconciler.py` — 4-valued + heal_max_age + OrderSnapshot snake_case
- `src/execution/bybit/ws_private.py` — close-hook + check_alive watchdog
- `migrations/0005_halt_persistence.sql` — halt_reason + halt_log

## Как обновлять этот файл

После каждого значимого шага (task complete / phase change / blocker found / session end):
1. Обнови "Текущий статус" (sprint / phase)
2. Перенеси task из "В процессе" → "Завершённые задачи" (checkbox)
3. Обнови "Следующее действие" — конкретное, с командой если применимо
4. Добавь в "Ключевые решения" только нетривиальное
5. Обнови `updated:` в frontmatter
