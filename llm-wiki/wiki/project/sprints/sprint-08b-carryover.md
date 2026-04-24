---
title: Sprint 8b — S8a carry-over fixes + ADR 0023 (halt-code → FSM event mapping invariant)
type: sprint
tags: [sprint-8b, execution, carry-over, halt-code, fsm-dispatch, property-test, adr-0023]
created: 2026-04-25
updated: 2026-04-25
status: completed
sources:
  - project/decisions/0023-halt-code-fsm-event-mapping
  - project/decisions/0022-sprint-8a-live-runtime
  - project/plans/2026-04-24-sprint-8b-carryover
---

# Sprint 8b — S8a carry-over fixes + ADR 0023

## Overview

Sprint 8b закрывает 4 carry-over дефекта из S8a, добавляет ADR 0023 (halt-code → FSM event mapping invariant), и ловит реальный production bug `(FLAT, RISK_HALT) → HALTED` через property test. 9 tasks, TDD throughout, per-task domain reviews APPROVED. FSM `TRANSITIONS` table вырос **70 → 73 → 74** (T1 +3 RISK_HALT для ENTRY_PENDING/EXIT_PENDING/RECONCILING; T7 +1 для FLAT — surfaced property test'ом, prevents `RuntimeManager.run()` exception в idle-state → split-brain).

**Trader-expert verdict applied:** atomic kill-switch mirror `src/risk/override.py:82-95` minus fsync (paper-trade scope verdict).

## Plan / ADR links

- Plan: [[../plans/2026-04-24-sprint-8b-carryover]]
- ADR (NEW): [[../decisions/0023-halt-code-fsm-event-mapping]]
- ADR (extends): [[../decisions/0022-sprint-8a-live-runtime]]

## Deliverables

12 commits на ветке `feature/sprint-8b-carryover`, PR #9 squash-merged → `5a4d074`.

### T1 — Coordinator.request_halt FSM transit fix

- `src/execution/coordinator.py` — `request_halt(reason: ReasonCode)` теперь dispatches FSM event:
  - `KILL_SWITCH_REQUESTED` → `ExecutionEvent.KILL_SWITCH_REQUESTED`
  - `HALT_*` → `ExecutionEvent.RISK_HALT`
  - HALTED-guard (preserves S7 γ idempotency)
- `_REQUEST_HALT_CODES = frozenset({KILL_SWITCH_REQUESTED, HALT_RUNTIME_CRASH, HALT_BAR_POLL_STALL})` — explicit allow-list contract (3 codes), NOT prefix-based selector
- Pre-S8b: 10 `KILL_SWITCH_REQUESTED` rows в TRANSITIONS были dead code

### T1 fix-up — Add 3 RISK_HALT transitions

- `src/execution/state_machine.py` — добавлены rows для `ENTRY_PENDING`, `EXIT_PENDING`, `RECONCILING` + `RISK_HALT` → `HALTED`. Bumped count 70 → 73.

### T2 — BarSource fail-fast 13-interval validator

- `src/runtime/bar_source.py` — `_INTERVAL_MS: ClassVar[dict[str, int]]` 13 Bybit V5 intervals (1, 3, 5, 15, 30, 60, 120, 240, 360, 720, D, W, M).
- ValueError на unknown interval at construction time (вместо silent KeyError при first poll).

### T3 — main() mypy no-any-return

- `src/__main__.py` — `func: Callable[[argparse.Namespace], int] = args.func; return func(args)` (typed dispatch).
- Net: mypy --strict src/ = 44 errors (vs main baseline 45; T3 -1).

### T4 — _cmd_kill atomic write

- `src/__main__.py` — `_cmd_kill` body atomic write: `os.open(O_WRONLY|O_CREAT|O_TRUNC, 0o600)` + `os.fdopen` + `os.replace` + finally `tmp.unlink(missing_ok=True)`.
- Mirrors `src/risk/override.py:82-95` minus `os.fsync` (paper-trade scope per trader-expert verdict).
- Module-level `import os` нужен для `monkeypatch.setattr("src.__main__.os.replace", ...)` resolution в tests.

### T5 — ADR 0023

- [[../decisions/0023-halt-code-fsm-event-mapping]] — halt-code → FSM event mapping invariant + 3-layer enforcement (ADR + reviewer prompt + property test).

### T6 — trading-logic-reviewer.md CRITICAL section

- `~/.claude/agents/trading-logic-reviewer.md` (outside repo) — section "Halt-code → FSM event mapping must be exhaustive". Block-level review rule, no commit.

### T7 — Property test + (FLAT, RISK_HALT) symmetry fix

- `tests/property/test_request_halt_mapping.py` (NEW, 105 lines) — parametrized по `_REQUEST_HALT_CODES` allow-list. Asserts `state == HALTED` AND `halt_reason == code.value` для каждого code из FLAT.
- **Production bug found:** `(FLAT, RISK_HALT) → HALTED` row missing. Без него `RuntimeManager.run()` exception → `request_halt(HALT_RUNTIME_CRASH)` from FLAT → `IllegalTransitionError` → split-brain (halt_reason persisted, FSM stays FLAT).
- Fix: `src/execution/state_machine.py` +1 row → 74 transitions.

### T8 — Wiki Stage E sync

- `wiki/project/components/runtime-manager.md` — atomic kill-switch sub-section
- `wiki/project/components/bar-poller.md` — supported intervals + fail-fast
- `wiki/index.md` — ADR 0023 link
- `wiki/project/decisions/0023-halt-code-fsm-event-mapping.md` — NEW ADR

### T9 — Ship

- PR #9 → squash-merge `5a4d074` → tag `v0.1.0-alpha.8b`.

## FSM growth

| Stage | Transitions | Delta | Notes |
|-------|-------------|-------|-------|
| S7 (ADR 0021) | 59 | — | Baseline |
| S8a (ADR 0022) | 70 | +11 | KILL_SWITCH_REQUESTED rows |
| S8b T1 fix-up | 73 | +3 | RISK_HALT для ENTRY_PENDING/EXIT_PENDING/RECONCILING |
| S8b T7 fix-up | **74** | +1 | (FLAT, RISK_HALT) — caught by property test |

## Reason codes

No new codes (S8b = carry-over fixes only). Total stays at **45** (per ADR 0022 sub-decision G5).

## Tests

- 643 passed / 4 pre-existing failures / 0 new regress
- mypy --strict src/ = 44 errors (baseline 45, T3 net -1)
- Property tests 8/8 (3 new в T7)

## Wiki updates (Stage E + this page)

- This sprint page (created в pre-S8c batch 2026-04-25 per Bucket A3)
- runtime-manager.md (T8)
- bar-poller.md (T8)
- index.md ADR 0023 entry (T8) + sprint-08b entry (pre-S8c batch)
- ADR 0023 NEW (T5)

## Open issues для S8c

Documented в `wiki/project/pre-s8c-backlog.md`:
- `_set_halt(reason: str)` internal wrapper signature всё ещё `str` — `request_halt(reason: ReasonCode)` уже типизирован
- ADR 0022 narrative count = 73 (live = 74 после T7 fix-up) — amend в next ADR touch
- Pre-existing test_config.py 3 env-pollution failures
- Pre-existing mypy 44 errors (coordinator.py, storage.py, gaps.py, reconciler.py)

## Key decisions (для истории)

- **Allow-list contract** для `_REQUEST_HALT_CODES` (3 codes) — explicit, NOT prefix-based. Drift mitigated by trading-logic-reviewer CRITICAL section + ADR 0023 + property test.
- **(FLAT, RISK_HALT) → HALTED** — surfaced by property test (exactly its purpose), prevents `RuntimeManager.run()` exception → split-brain.
- **Atomic kill-switch** mirror `src/risk/override.py:82-95` minus fsync (paper-trade scope, trader-expert verdict).
- **HALTED-guard** в `request_halt` — `current.state != HALTED` перед `_transition` — preserves S7 γ idempotency.

## Related

- Prior sprint: [[sprint-08a-live-runtime]] (S8a)
- Components: [[../components/coordinator]], [[../components/execution-state-machine]], [[../components/runtime-manager]], [[../components/bar-poller]]
- Backlog: [[../pre-s8c-backlog]] (carry-overs)
