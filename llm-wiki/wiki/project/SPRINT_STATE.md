---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-04-23
sprint: 6-complete
phase: between-sprints
branch: main
tag: v0.1.0-alpha.6
---

# SPRINT STATE

> Этот файл читается ПЕРВЫМ в каждой сессии. Обновляется после каждого значимого шага.
> Формат намеренно компактный — ≤ 2KB. Не расширяй без причины.

## Текущий статус

**Sprint 6 — Spot OCO emulation (ADR 0020) — COMPLETE ✅**
Merge commit: `9eff03f` на `main`. Tag: `v0.1.0-alpha.6`.
Sprint 7 — не начат. Ожидаем brainstorming.

## Завершённые задачи (S6)

- [x] Schema migration 0004_execution_state_v2.sql (+6 columns)
- [x] FSM v2: 16 states, 56 transitions, 8 new events
- [x] BybitMarketAdapter: 7 new methods, 6 banned Spot fields
- [x] Coordinator: start_bracket, arm_oco, on_order_event, bootstrap
- [x] Reconciler R4: walletBalance position truth, dust_threshold
- [x] Property tests: bracket lifecycle invariants (Hypothesis)
- [x] Stage F probes: B2 ✅ + v3-D ✅ on Demo Mainnet
- [x] Blocker fixes: #1 ENTRY_FILLED, #2 WS echo guard, #3 stale-leg cancel, #4 TP-before-flatten
- [x] trading-logic-reviewer re-review: ✅ no blockers
- [x] Wiki: oco.md, reconciler.md, execution-state-machine.md, reason-codes.md updated
- [x] Reason codes 31→39 (8 new S6 codes)
- [x] Runbook: halt-recovery.md (NEW)

## В процессе

Ничего. Между спринтами.

## Следующее действие

Начать Sprint 7. Сначала: brainstorming scope S7.

Кандидаты из review follow-ups S6:
- C1: coordinator startup reconcile при ENTRY_PENDING/EXIT_PENDING
- C2: WS-reconnect wiring для ENTRY_PENDING/EXIT_PENDING
- halt_reason / last_exit_reason колонки в schema v3

## Ключевые решения последней сессии

- stdlib logging (не structlog — нет в venv)
- _best_effort_cancel: 110001 = OK, exceptions = warn+swallow
- trading-logic-reviewer sonnet model (per agent file, не opus)
- caveman full активен, agent prompts синхронизированы с ADR 0019+0020

## Блокеры / concerns (отложены в S7)

- C1 (coordinator startup reconcile) — defer S7
- C2 (WS-reconnect wiring) — defer S7
- paranoia outer try/except в WS worker — ⚠️ concern (не blocker)
- halt_reason not persisted in execution_state — тикет S7

## Активные файлы (где работаем)

- `src/execution/coordinator.py` — последние правки (4 blocker fixes)
- `src/execution/state_machine.py` — FSM v2 (16 states)
- `src/risk/reason_codes.py` — 39 enum codes
- `migrations/0004_execution_state_v2.sql` — schema v2

## Как обновлять этот файл

После каждого значимого шага (task complete / phase change / blocker found / session end):
1. Обнови "Текущий статус" (sprint / phase)
2. Перенеси task из "В процессе" → "Завершённые задачи" (checkbox)
3. Обнови "Следующее действие" — конкретное, с командой если применимо
4. Добавь в "Ключевые решения" только нетривиальное
5. Обнови `updated:` в frontmatter
