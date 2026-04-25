---
title: Sprint 11 — Operator-readiness + pre-flight gap closure
type: sprint
tags: [sprint-11, operator-readiness, cli, monitoring, di-wiring, pre-flight]
created: 2026-04-25
updated: 2026-04-25
status: completed
sources:
  - project/plans/2026-04-25-sprint-11-operator-readiness
  - project/decisions/0026-sprint-11-operator-readiness
  - project/pre-s11-backlog
---

# Sprint 11 — Operator-readiness + pre-flight

## Overview

S11 ships pre-flight gap closure (P0) + operator infrastructure (A scope) per pre-s11-backlog.md verdicts. 10 TDD tasks, 13 commits squash-merged. Tag `v0.1.0-alpha.11`.

**Closes:**
- 8-month-old S8a T20 STUB (`_cmd_run` + `_cmd_reconcile_only` DI wiring)
- S4-era test drift (test_risk_flow.py OverrideStore signature)
- Halt priority indexing gap (operator wouldn't know which halts wake them at 3 AM)
- WFA CLI exposure для on-demand baseline

## Plan / ADR links

- Plan: [[../plans/2026-04-25-sprint-11-operator-readiness]]
- ADR (NEW): [[../decisions/0026-sprint-11-operator-readiness]]
- Brainstorm trail: [[../pre-s11-backlog]]

## Deliverables

10 tasks squash-merged.

### P0 pre-flight (4 tasks)

- T1 (`afb5760`): test_risk_flow.py OverrideStore hmac_key signature restored + fixture hmac_key добавлен
- T2 (`ead6dca` + `d7b196f`): `_cmd_run` DI wiring (architecture-reviewer SOUND verdict + 1 inline fix MagicMock→_NoopFillRecorder)
- T3 (`bb8cba9` + `e4df4cd`): `_cmd_reconcile_only` DI wiring + ARG002 noqa
- T4 (`6e1fff2`): `_cmd_wfa` CLI subcommand (Sharpe + MC gate)

### A scope (4 tasks)

- T5 (`0b57062`): halt-recovery.md priority matrix + escalation column (Q3 REVISE)
- T6 (`26f7b68`): NEW log-grep-templates.md (structlog jq filters + halt_log SQL)
- T7 (`281896e`): `_cmd_monitor` CLI (read-only per C2, `?mode=ro` URI)
- T8 (`92c37b9`): NEW pre-flight.md operator checklist (5 gates + 4 recommendations)

### Wiki + ADR (2 tasks)

- T9 (`6ba4a41`): ADR 0026 + index.md entry
- T10: Sprint page + counts updates + mental-map

## FSM growth

NONE. CLI = orchestration layer. Counts unchanged: 16/30/74/45.

## Reason codes growth

NONE.

## Tests

- pytest unit: 666 passed (baseline 656 + 10 new tests for CLI subcommands)
- pytest integration: test_risk_flow.py ✅ (was failing pre-S11)
- mypy --strict src/: clean
- ruff: clean

## Wiki updates

- 2 NEW runbook pages: log-grep-templates.md + pre-flight.md
- 1 NEW ADR (0026)
- 1 NEW sprint page (this)
- Modified: halt-recovery.md (priority matrix + escalation column)
- current-state.md (counts: ADR 25→26, sprint pages 12→13, components unchanged)
- mental-map.md (4 new query rows для operator runbooks)

## Open issues для S12+

- F (Live demo Mainnet 24-72h validation) — main S12 scope
- FillRecorder production wiring (currently `_NoopFillRecorder` stub в _cmd_run)
- _load_ohlcv production data integration в _cmd_wfa (currently empty DataFrame stub)
- **Endpoint string fix (T2 review C1):** `"demo.bybit.com"` semantically wrong для testnet — fix к contain `"testnet"` substring при actual testnet validation
- **init_db dual-conn comment (T2 review C3):** code comment for two-connection sequence
- Per-fold DSR DataFrame→TradeRecord conversion (informational, deferred)
- DSR threshold calibration (S15+ per Q5 verdict)

## Key decisions

- **A-first vs F-first** (Q1) — A wins per architecturally correct sequencing (live Mainnet требует runnable bot, blocked by _cmd_run STUB)
- **halt priority matrix INTO halt-recovery.md** (Q3 REVISE) — single source of truth, prevents drift vs separate dashboard
- **_cmd_monitor strictly read-only** (C2) — SQLite WAL contention prevention via `?mode=ro` URI
- **architecture-reviewer mandatory _cmd_run** (Q7) — DI graph + concurrency implications per ADR 0017 trigger cascade
- **DI feasibility read-pass** (C1) — pre-plan verification confirmed constructors aligned, no mini-ADR needed. T2 architecture verdict: SOUND.
- **MagicMock→_NoopFillRecorder** (T2 review C2 fix) — replace test library import в production с simple stub class

## Related

- [[../plans/2026-04-25-sprint-11-operator-readiness]] — full plan + trace map
- [[../decisions/0026-sprint-11-operator-readiness]] — aggregate ADR
- [[../pre-s11-backlog]] — PHASE 2 verdicts trail
- [[sprint-10-wfa-dsr-mc]] — predecessor sprint (WFA components consumed by T4)
- [[../runbooks/halt-recovery]] + [[../runbooks/log-grep-templates]] + [[../runbooks/pre-flight]] — operator runbooks
