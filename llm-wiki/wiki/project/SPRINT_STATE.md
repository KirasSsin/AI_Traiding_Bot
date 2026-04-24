---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-04-24
sprint: 8b
phase: 8-ship
branch: feature/sprint-8b-carryover
tag: v0.1.0-alpha.8a
---

# SPRINT STATE

> Этот файл читается ПЕРВЫМ в каждой сессии. Обновляется после каждого значимого шага.
> Формат намеренно компактный — ≤ 2KB. Не расширяй без причины.

## Текущий статус

**Sprint 8b — Carry-over fixes (S8a) + ADR 0023 — PHASE 8 (ship).**

Все 9 tasks done. pytest 643 passed / 4 pre-existing failed / 0 new regress. mypy --strict src/ = 44 errors (main baseline = 45; T3 fix снизил на 1). Property tests 8/8. Per-task domain reviews APPROVED (T1 trading-logic, T2 python, T3 spec+python, T4 spec+python, T7 trading-logic). Final sweep skip — quota exhausted, anti-bloat per CLAUDE.md.

## Завершённые задачи (S8b)

- [x] T1 Coordinator.request_halt — FSM transit fix (`37b7535` + `32db325` + `150870d` count addendum)
- [x] T2 BarSource — fail-fast 13-interval validator (`7cd5b48` + `6583b05`)
- [x] T3 main() mypy no-any-return — typed `Callable[[Namespace], int]` dispatch (`5f811c2`)
- [x] T4 _cmd_kill atomic — os.open + os.replace + finally cleanup (`ac2ddba` + `df3b007`)
- [x] T5 ADR 0023 — halt-code → FSM event mapping invariant (`1f46877`)
- [x] T6 trading-logic-reviewer.md CRITICAL section "Halt-code mapping" (outside repo, no commit)
- [x] T7 property test + (FLAT, RISK_HALT) row symmetry (`351b49f` + `97ec79b`)
- [x] T8 Wiki Stage E sync — runtime-manager + bar-poller + index + log + ADR (`08084b2`)
- [x] T9 Verify (this entry) — pytest + mypy + property green; ship next

## В процессе

T9 Step 4 — PR via `superpowers:finishing-a-development-branch`. Then tag `v0.1.0-alpha.8b`.

## Следующее действие

```
git push -u origin feature/sprint-8b-carryover
gh pr create --title "Sprint 8b — S8a carry-over fixes" ...
# squash merge → tag v0.1.0-alpha.8b → SPRINT_STATE между-sprints
```

## Carry-over в S8c (concerns не блокирующие S8b merge)

- `_set_halt(reason: str)` internal wrapper signature всё ещё `str` — `request_halt(reason: ReasonCode)` уже типизирован; cleanup в S8c.
- `coordinator.md` wiki page отсутствует — request_halt FSM-transit semantics только в commit log + ADR 0023; создать в dedicated wiki sprint.
- ADR 0022 narrative transition count = 73; live = 74 после T7 fix-up. Update at next ADR amendment.
- Pre-existing test_config.py 3 failures (env-pollution от .env) + test_risk_flow OverrideStore signature drift — не S8b regression.
- Pre-existing mypy 44 errors в `src/execution/coordinator.py` (LocalState undef, dict[Any,Any]), `src/marketdata/storage.py|gaps.py` (untyped pyarrow calls), `src/execution/reconciler.py` (None union-attr) — pre-existing technical debt.

## Ключевые решения S8b (для истории)

- **Allow-list contract** для `_REQUEST_HALT_CODES` (3 codes) — explicit, NOT prefix-based selector. Future drift mitigated by trading-logic-reviewer CRITICAL section + ADR 0023.
- **(FLAT, RISK_HALT) → HALTED** — surfaced by property test, prevents `RuntimeManager.run()` exception → split-brain (halt_reason persisted, FSM stays FLAT).
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
