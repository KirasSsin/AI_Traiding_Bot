---
title: Sprint 8c — Wiki backfill + tooling debt + S8a/S8b carry-overs
type: sprint
tags: [sprint-8c, wiki, tooling, hooks, adr-index-sync, oco-supersede, trace-map, backfill]
created: 2026-04-25
updated: 2026-04-25
status: completed
sources:
  - project/plans/2026-04-25-sprint-8c-wiki-backfill
  - project/decisions/0017-review-agent-harness
  - project/decisions/0019-sprint-5-execution-decisions
---

# Sprint 8c — Wiki backfill + tooling debt

## Overview

Sprint 8c закрывает накопленный wiki debt + tooling gaps до начала S9 brainstorm (operator-readiness). Pure docs/process/tooling sprint — 0 src/ behavioral changes. 12 tasks, 12 commits squash-merged → tag `v0.1.0-alpha.8c`, PR #11 → `92c8d30`.

**PHASE 2 binding protocol caught catastrophic regression** на Q1: trader-expert ROUND 2 iterative justify отменил maintainer's recommendation DELETE `src/execution/bracket.py`. Файл был active production code, не orphan — ROUND 2 saved production. Подтвердило binding protocol value.

## Plan / ADR links

- Plan: [[../plans/2026-04-25-sprint-8c-wiki-backfill]]
- ADR (referenced): [[../decisions/0017-review-agent-harness]] (review agent set), [[../decisions/0019-sprint-5-execution-decisions]] (oco.py supersession)

## Deliverables

12 tasks, 12 commits squash-merged on `feature/sprint-8c-wiki-backfill`.

### T1-T4 — Wiki backfill (4 new component pages + cluster index)

- **NEW** [[../components/backtest-harness]] — single-page covering 6 src/backtest files (replay_engine + vector_backtest + reporter + indicators + data_collector + replay-stub)
- **NEW** [[../components/kill-switch-cli]] — operator CLI (kill/run/backfill/reconcile-only) + sentinel-file atomic write
- **NEW** [[../components/risk-override]] — manual CB resume gate (HMAC-SHA256 + atomic write 0o600 + config_hash anti-replay)
- **NEW** [[../components/trade-history]] — per-trade audit log + UNIQUE INDEX entry_signal_id (Kelly trade-count source)

### T5-T7 — Code cleanup (per ADR 0019/1 supersession)

- **DELETED** `src/execution/oco.py` + `tests/unit/test_oco.py` + `tests/unit/test_oco_builder.py` (3 files removed; bracket builder reused через `src/execution/bracket.py`)
- **TRADER ROUND 2 SAVED:** original recommendation DELETE `src/execution/bracket.py` was REJECTED — file is active production code (Coordinator.start_bracket consumer, не legacy)

### T8-T10 — Trace map + adr-index-sync hook

- **NEW HARD-GATE** dev-workflow.md PHASE 3 step 1a: trace map mandatory section в каждом plan (Files Created/Modified/Tests/Wiki dependency map)
- **NEW HOOK** `~/.claude/hooks/adr-index-sync-check.sh` (Bucket C6) — blocks `git push` если new ADR не referenced в `wiki/index.md`
- **NEW PAGE** [[../components/adr-index-sync-hook]] — hook spec + behavior + test scenarios

### T11-T12 — Wiki polish + categorization

- EXIT_RECONCILE_DETECTED categorization fix (exit class, не halt class)
- HALT_RECONCILE_DIVERGENCE rename consistency check
- 6 orphan component pages "Referenced by" sections added

## FSM growth

Нет (pure docs/process sprint). Counts unchanged: 16 states / 30 events / 74 transitions / 45 reason codes.

## Reason codes growth

Нет.

## Tests

- pytest: 602 passed / 24 skipped / 0 failed (S8b baseline maintained)
- 0 src/ behavioral changes

## Wiki updates

- 4 new component pages (backtest-harness, kill-switch-cli, risk-override, trade-history)
- 1 new hook component page (adr-index-sync-hook)
- New HARD-GATE в dev-workflow.md (trace map PHASE 3 step 1a)

## Open issues для S9

- Bucket F1 — `wiki/runbooks/halt-recovery.md` MISSING (operator runbook, deferred к S9 dedicated operator-readiness OR follow-up batch)
- mypy 44 pre-existing errors (typed batch sprint)
- Block 1/2 paradigm для existing component pages (later resolved: defer per-page refactor, paradigm implicit)

## Key decisions

- **PHASE 2 trader iterative justify ROUND 2 mandatory на REVISE-disagreement** (caught DELETE bracket.py regression)
- **CC1 recursive lesson:** orphan-audit grep MUST include `tests/` directory, not src/ alone. Added к PHASE 8 step 5b HARD-GATE.
- **Trace map mandatory** — каждый plan PHASE 3 имеет explicit dependency map (Files Created/Modified/Tests/Wiki). Prevents PHASE 4 surprises.
- **adr-index-sync hook deployed** — automation > reminders (Anthropic best practice).

## Related

- [[../plans/2026-04-25-sprint-8c-wiki-backfill]] — full plan + trace map
- [[../decisions/0017-review-agent-harness]] — agent set referenced (architecture-reviewer added later в PR-β)
- [[../decisions/0019-sprint-5-execution-decisions]] — oco.py supersession source
- [[sprint-08b-carryover]] — predecessor sprint
- [[../architecture/development-workflow]] — PHASE 8 HARD-GATEs source
