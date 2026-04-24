---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-04-25
sprint: pre-8c-shipped
phase: between-sprints
branch: main
tag: v0.1.0-alpha.8b
---

# SPRINT STATE

> Этот файл читается ПЕРВЫМ в каждой сессии. Обновляется после каждого значимого шага.
> Формат намеренно компактный — ≤ 2KB. Не расширяй без причины.

## Текущий статус

**Между спринтами. S8b shipped (tag `v0.1.0-alpha.8b`, PR #9 → `5a4d074`). Pre-S8c wiki-backfill batch shipped (PR #10 → `a8ad404`): 19 items (Bucket A+ + DRIFT) + 3 methodology kit updates (PHASE 8 HARD-GATE step 5/5a/6 + canonical counts pattern + binding PHASE 2 brainstorming protocol).**

Готовы к S8c brainstorm. Carry-over к S8c: Bucket B (user bugs TBD) + Bucket E (ADR 0022 narrative count + Context section amends) + S8a/S8b code carry-overs (`_set_halt(reason: str→ReasonCode)`, pre-existing test_config 3 failures, mypy 44 errors).

## Последний спринт (S8b)

- [x] T1 Coordinator.request_halt — FSM transit fix
- [x] T2 BarSource — fail-fast 13-interval validator
- [x] T3 main() mypy no-any-return — typed `Callable[[Namespace], int]` dispatch
- [x] T4 _cmd_kill atomic — os.open + os.replace + finally cleanup
- [x] T5 ADR 0023 — halt-code → FSM event mapping invariant
- [x] T6 trading-logic-reviewer.md CRITICAL section "Halt-code mapping"
- [x] T7 property test + (FLAT, RISK_HALT) row symmetry — caught real production bug
- [x] T8 Wiki Stage E sync — runtime-manager + bar-poller + index + log + ADR 0023
- [x] T9 Ship — PR #9 → squash-merge → tag v0.1.0-alpha.8b

## Следующее действие

```
PHASE 1 (orient) для S8c:
1. mem-search "sprint 8a" "sprint 8b" → surface unresolved concerns
2. Read llm-wiki/wiki/log.md (last 10 entries)
3. PHASE 2 brainstorm S8c scope (см. carry-over ниже + новые цели)
```

## Carry-over в S8c

- `_set_halt(reason: str)` internal wrapper signature всё ещё `str` — `request_halt(reason: ReasonCode)` уже типизирован; cleanup в S8c.
- `coordinator.md` wiki page отсутствует — request_halt FSM-transit semantics только в commit log + ADR 0023; создать.
- ADR 0022 narrative transition count = 73; live = 74 после T7 fix-up. Amend at next ADR touch.
- Pre-existing test_config.py 3 env-pollution failures + test_risk_flow OverrideStore signature drift.
- Pre-existing mypy 44 errors в coordinator.py (LocalState undef, dict[Any,Any]), storage.py|gaps.py (untyped pyarrow), reconciler.py (None union-attr).

## Ключевые решения S8b (для истории)

- **Allow-list contract** для `_REQUEST_HALT_CODES` (3 codes) — explicit, NOT prefix-based. Drift mitigated by trading-logic-reviewer CRITICAL section + ADR 0023 + property test.
- **(FLAT, RISK_HALT) → HALTED** — surfaced by property test, prevents `RuntimeManager.run()` exception → split-brain.
- **Atomic kill-switch** mirror `src/risk/override.py:82-95` minus fsync (paper-trade scope, trader-expert verdict).
- **HALTED-guard** в `request_halt` — `current.state != HALTED` перед `_transition` — preserves S7 γ idempotency.
- **`os` module-level import** в `src/__main__.py` — needed для `monkeypatch.setattr("src.__main__.os.replace", ...)` resolution в T4 atomicity test.

## Как обновлять этот файл

После каждого значимого шага (task complete / phase change / blocker found / session end):
1. Обнови "Текущий статус" (sprint / phase)
2. Перенеси task из "В процессе" → "Завершённые задачи" (checkbox)
3. Обнови "Следующее действие" — конкретное, с командой если применимо
4. Добавь в "Ключевые решения" только нетривиальное
5. Обнови `updated:` в frontmatter
