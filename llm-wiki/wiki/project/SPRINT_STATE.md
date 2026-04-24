---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-04-25
sprint: pre-9-wiki-rag-shipped
phase: between-sprints
branch: main
tag: v0.1.0-alpha.8c
---

# SPRINT STATE

> Этот файл читается ПЕРВЫМ в каждой сессии. Обновляется после каждого значимого шага.
> Формат намеренно компактный — ≤ 2KB. Не расширяй без причины.

## Текущий статус

**Между спринтами. S8c shipped (tag `v0.1.0-alpha.8c`, PR #11 squash-merged → `92c8d30`).**

10 спринтов завершено: S1-S7 + S8a + S8b + S8c. Готовы к S9 brainstorm.

## Последний спринт (S8c — Wiki backfill + tooling debt)

12 tasks (T1-T12), 12 commits squashed. **PHASE 2 binding protocol caught catastrophic regression** на Q1 — maintainer DELETE recommendation для bracket.py отменена ROUND 2 trader-expert verdict (production code, 4 test importers + coordinator.py:9 production import).

- [x] T1 DELETE oco.py + 2 tests (Q4 ADR 0019/1 supersession)
- [x] T2 current-state.md bracket label fix (Q1 ROUND 2 + CC2)
- [x] T3 NEW backtest-harness.md (Q2 — 6 backtest files consolidated)
- [x] T4 NEW kill-switch-cli.md (Q3 — CLI + 3 subcommands + atomic write)
- [x] T5 NEW risk-override.md (147 LoC HMAC-signed override)
- [x] T6 NEW trade-history.md (118 LoC audit log)
- [x] T7 `_set_halt(reason: ReasonCode)` type narrow
- [x] T8 test_config env-pollution fix (3 tests pass now)
- [x] T9 ADR 0022 amend (count 73→74 + Context S8b scope, Bucket E1+E2)
- [x] T10 trace map mandatory + retro-add S5/S7/S8b (Bucket C5)
- [x] T11 adr-index-sync-check.sh hook (Bucket C6)
- [x] T12 PHASE 8 finalize (sprint-08c.md + index + canonical counts)

## Следующее действие

```
PHASE 1 (orient) для S9:
1. mem-search "sprint 8c" → surface unresolved concerns
2. Read llm-wiki/wiki/log.md (last 10 entries)
3. PHASE 2 brainstorm S9 scope (см. carry-over ниже + новые цели)
```

## Carry-over к S9+

- **Bucket F1** — `wiki/runbooks/halt-recovery.md` MISSING (referenced from 8+ places). Brainstorm scope (operator runbook multi-section). Recommend dedicated "operator readiness" sprint.
- **mypy 44 pre-existing errors** (coordinator.py LocalState undef, dict[Any,Any]; storage.py/gaps.py untyped pyarrow; reconciler.py None union-attr) — defer typed batch sprint.
- **C7 candidate** — broken-link audit hook (verify all `[[../...]]` wiki refs resolve).

## Ключевые решения S8c (для истории)

- **Iterative justify protocol caught DELETE bracket.py regression** — Q1 ROUND 2 saved production от ModuleNotFoundError.
- **CC1 recursive lesson** — orphan-audit grep MUST include `tests/` (caught 3rd file `test_execution_oco_testnet.py` permanent skip в Q4). Now PHASE 8 step 5b HARD-GATE.
- **Trace map mandatory** в PHASE 3 (HARD-GATE step 1a) — prevents spec coverage drift.
- **adr-index-sync hook** — blocks push if new ADR не в index.md (mirror adr-agent-sync pattern).
- **EXIT_RECONCILE_DETECTED categorization clarified** — comment-only edit, ADR 0021 block placement preserved для traceability.

## Как обновлять этот файл

После каждого значимого шага (task complete / phase change / blocker found / session end):
1. Обнови "Текущий статус" (sprint / phase)
2. Перенеси task из "В процессе" → "Завершённые задачи" (checkbox)
3. Обнови "Следующее действие" — конкретное, с командой если применимо
4. Добавь в "Ключевые решения" только нетривиальное
5. Обнови `updated:` в frontmatter
