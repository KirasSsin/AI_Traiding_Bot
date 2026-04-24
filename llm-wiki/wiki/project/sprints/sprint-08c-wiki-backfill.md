---
title: Sprint 8c — Wiki backfill + tooling debt + S8a/S8b carry-overs
type: sprint
tags: [sprint-8c, wiki, tooling, carry-over, hooks, methodology]
created: 2026-04-25
updated: 2026-04-25
status: completed
sources:
  - project/plans/2026-04-25-sprint-8c-wiki-backfill
  - project/pre-s8c-backlog
  - project/decisions/0022-sprint-8a-live-runtime
  - project/decisions/0023-halt-code-fsm-event-mapping
---

# Sprint 8c — Wiki backfill + tooling debt + S8a/S8b carry-overs

## Overview

Sprint 8c closes accumulated documentation debt + small code carry-overs from S8a/S8b + process hooks before next feature sprint. Cohesive theme = **"wiki backfill + tooling debt"**. 12 tasks, 11 commits, 0 new ADRs (only ADR 0022 amendments per Bucket E1+E2). 4 new component pages + 3 file deletions (ADR 0019 sub-decision 1 obsolete) + 1 type narrow + 1 test fix + 1 process hook + trace map mandatory section.

**PHASE 2 brainstorm trail (BINDING protocol applied):** 4 questions — Q1 ROUND 1 REVISE → ROUND 2 CONFIRM_REVISE (KEEP bracket.py — production code, NOT orphan; trader caught maintainer's catastrophic delete recommendation); Q2 CONFIRM (single backtest-harness.md); Q3 CONFIRM (dedicated kill-switch-cli.md); Q4 ROUND 1 CONFIRM with scope expansion (DELETE 3 files оco.py + 2 tests, 3rd file caught via CC1 grep). Both cross-cutting concerns applied to kit (CC1 — orphan-audit grep MUST include tests/; CC2 — current-state.md label drift fix).

**Iterative justify protocol caught real regression:** maintainer's DELETE recommendation на bracket.py would have caused production startup `ModuleNotFoundError` (coordinator.py:19 imports + 4 test files). ROUND 2 saved before plan locked scope.

## Plan / ADR links

- Plan: [[../plans/2026-04-25-sprint-8c-wiki-backfill]]
- Backlog: [[../pre-s8c-backlog]]
- ADR amendments: [[../decisions/0022-sprint-8a-live-runtime]] (Bucket E1+E2)
- No new ADRs (this sprint = wiki/tooling/carry-over, no design decisions requiring ADR)

## Deliverables

12 commits на ветке `feature/sprint-8c-wiki-backfill`.

### Code changes (T1, T7, T8 — minimal src/ touch)

- **T1 (`cccba98`):** DELETE `src/execution/oco.py` (55 LoC ADR 0019 sub-decision 1) + `tests/unit/test_oco.py` + `tests/integration/test_execution_oco_testnet.py` (already permanently `pytest.mark.skip` per ADR 0020 supersession). Per Q4 trader-expert verdict.
- **T7 (`10572be`):** `Coordinator._set_halt(reason: ReasonCode)` type narrow (was `str`) — parity with public `request_halt(reason: ReasonCode)`. 4 call boundaries converted via `ReasonCode(...)` constructor (StrEnum, zero runtime impact). Carry-over from S8a/S8b.
- **T8 (`360c675`):** `tests/unit/test_config.py` env-pollution fix — 3 tests (`test_missing_api_key_raises` + `_secret_raises` + `_hmac_key_raises`) — Pattern C (combined `monkeypatch.delenv` + `Settings(_env_file=None)`). Closes 3 pre-existing failures.

### New wiki component pages (T3, T4, T5, T6)

- **T3 (`22fecf2`):** [[../components/backtest-harness]] (Q2 verdict — single page consolidating 6 backtest files, ~700 LoC src). S2-era reference, S9+ DSR/MC/WFA deferred.
- **T4 (`d45777d`):** [[../components/kill-switch-cli]] (Q3 verdict — operator-facing CLI page covering kill + run + backfill + reconcile-only). Atomic write semantics (S8b T4) + FSM dispatch invariant (ADR 0023) + recovery workflow.
- **T5 (`28ec785`):** [[../components/risk-override]] (security-critical 147 LoC backfill — HMAC-SHA256 signed JSON + config_hash anti-replay + atomic write 0o600 + fsync).
- **T6 (`4825491`):** [[../components/trade-history]] (audit log 118 LoC — TradeRecord + TradeHistoryRepository + UNIQUE INDEX entry_signal_id per S4 Kelly trade-count requirement + AwareDatetime).

### Wiki cross-link + label fixes (T2)

- **T2 (`04ea8d7`):** `current-state.md` `bracket` row label fix (`legacy 100` → `oco-builder, ADR 0020 sub-decision 2, 101 LoC`). Drop `oco,` after T1 deletion. Per Q1 ROUND 2 verdict + CC2.

### ADR amendments (T9 — Bucket E batch)

- **T9 (`02c1c0f`):** ADR 0022 amendments — transition count narrative `59→70` annotated `+ 70→74 (S8b T7 fix-up adding (FLAT, RISK_HALT) row)`; Context section S8b scope annotated "actually delivered carry-over + ADR 0023, original analytics/epsilon-halt scope deferred to S9+". New `## Amendments` section created.

### Methodology kit updates (T10, T11)

- **T10 (`950dc3d`):** Trace map mandatory section в PHASE 3 (HARD-GATE step 1a) + retro-add к S5 (10-row map), S7 (13-row map), S8b (9-row map). Bucket C5 closed.
- **T11 (`f22e2e7`):** `~/.claude/hooks/adr-index-sync-check.sh` NEW (mirror `adr-agent-sync-check.sh` pattern). Blocks `git push` if new ADR not referenced в `wiki/index.md`. Wiki page [[../components/adr-index-sync-hook]] created. Bucket C6 closed.

### Bucket F1 logged (post-T4 discovery)

- T4 implementer попытался cross-link к `wiki/runbooks/halt-recovery.md` — found dir + file MISSING. Referenced from 8+ places (runtime-manager.md, index.md, plans S6/S7/S8c). Logged как Bucket F1 в backlog для S9+ resolution. Out-of-scope для S8c.

## FSM growth

| Stage | Transitions | Delta | Notes |
|-------|-------------|-------|-------|
| S8b end | 74 | — | Baseline |
| S8c end | **74** | 0 | No FSM changes (wiki/tooling sprint) |

## Reason codes

No new codes (S8c = wiki/tooling). Total stays at **45**.

## Tests

- 602 passed / 24 skipped / 0 failed (vs 604/24/3 S8b baseline = -5 deleted oco tests + 3 fixed config tests = net -2 + 3 fail→pass)
- mypy --strict src/: 44 errors (unchanged from S8b baseline; T7 narrow didn't resolve pre-existing tech debt)
- ruff: clean

## Wiki updates

- 4 new component pages (backtest-harness, kill-switch-cli, risk-override, trade-history)
- 1 new tooling page (adr-index-sync-hook)
- 1 new sprint summary page (this file)
- Multiple cross-link updates (runtime-manager.md, oco.md, execution-state-machine.md, reconciler.md per A13 Bucket A+ already shipped в pre-S8c)
- index.md +6 entries
- current-state.md canonical counts (Component pages 22→27, Sprint pages 9→10)
- ADR 0022 amendments
- 3 retro-added trace maps
- pre-s8c-backlog.md fully closed (19 items + S8c brainstorm trail + Bucket F follow-up)

## Methodology kit changes

- **PHASE 3 step 1a NEW HARD-GATE:** trace map mandatory (Bucket C5)
- **PHASE 8 step 5b NEW HARD-GATE:** orphan-audit grep includes tests/ (CC1, added в pre-S8c batch)
- **`adr-index-sync-check.sh` hook:** blocks push if new ADR не в index.md (Bucket C6)
- **trader-expert iterative justify protocol:** worked as designed (Q1 caught catastrophic regression)

## Open issues для S9+

- **F1 — `wiki/runbooks/halt-recovery.md` missing** — operator runbook referenced from 8+ places, not exists. Brainstorm scope (multi-section operator post-mortem) + create в S9 dedicated "operator readiness" sprint.
- **mypy 44 errors** — pre-existing tech debt (coordinator.py LocalState undef + dict[Any,Any] + storage.py/gaps.py untyped pyarrow + reconciler.py None union-attr). Defer until typed batch sprint.
- **C7 candidate (process):** broken-link audit hook — verify all `[[../...]]` wiki refs resolve to existing files. Discovered necessary by F1 lesson.

## Key decisions (для истории)

- **Bracket.py KEEP** — Q1 ROUND 2 binding verdict prevented production catastrophe. Iterative justify protocol working as designed.
- **Single backtest-harness.md** (Q2) — YAGNI per S2-era code, no active dev S3-S8b.
- **Dedicated kill-switch-cli.md** (Q3) — operator surface ≠ runtime mechanics, fold all CLI commands here (avoids 4th tiny page).
- **DELETE 3 files** (Q4) — trader-expert caught 3rd file (test_execution_oco_testnet.py permanent skip) maintainer missed via CC1 grep recursion.
- **CC1 process gap** — orphan-audit grep MUST include tests/ — applied recursively (caught Q1 + Q4 expansion). PHASE 8 step 5b HARD-GATE prevents recurrence.

## Related

- Prior sprint: [[sprint-08b-carryover]]
- Backlog: [[../pre-s8c-backlog]]
- Methodology updates: [[../architecture/development-workflow]] (PHASE 3 step 1a + PHASE 8 step 5b)
