---
title: Sprint 28 — Process enforcement (kit flow mechanical hook + Russian docs)
type: sprint
tags: [sprint-28, process, enforcement, hook, kit-flow, ru, sprint-flow-check]
created: 2026-04-26
updated: 2026-04-26
status: completed
sources:
  - project/decisions/0041-sprint-28-process-enforcement.md
  - project/architecture/sprint-flow-ru.md
  - project/architecture/tooling-inventory-ru.md
  - project/plans/2026-04-26-sprint-28-process-enforcement.md
---

# Sprint 28 — Process enforcement

## Overview

Operator-driven process correction sprint. После S27 ship operator complaint:

> "Последний спринт выглядит flow так что наш кит сломан. В S27 не подключались скиллы планирования, todo, superpowers:brainstorming и все наши наработки в ките."

Verified drift: 12 sprints (S16-S27) без plan files в `wiki/project/plans/`. Last plan = S15.

S28 = mechanical enforcement (hook) + Russian process docs + per-task SPRINT_STATE protocol.

## Plan / ADR links

- [[../decisions/0041-sprint-28-process-enforcement]] — Sprint 28 ADR
- [[../plans/2026-04-26-sprint-28-process-enforcement]] — Sprint 28 plan (PHASE 3 deliverable — first plan since S15)
- [[../architecture/sprint-flow-ru]] — Russian sprint lifecycle
- [[../architecture/tooling-inventory-ru]] — agents/skills/plugins/MCP catalog

## Deliverables

### Code (out-of-repo, ~/.claude/)

| Task | Files | Description |
|------|-------|-------------|
| T3 | `~/.claude/hooks/sprint-flow-check.sh` NEW | Pre-push enforcement: blocks push на feature/sprint-NN-* без plan file |
| T3 | `~/.claude/settings.json` MODIFIED | Registered sprint-flow-check.sh к PreToolUse Bash matcher |

### Wiki (in-repo)

| Task | Files | Description |
|------|-------|-------------|
| T1 | `wiki/project/architecture/sprint-flow-ru.md` NEW | Russian sprint lifecycle 9 phases с per-phase HARD-GATEs + anti-patterns + per-task SPRINT_STATE protocol |
| T2 | `wiki/project/architecture/tooling-inventory-ru.md` NEW | Catalog: 6 agents + 5 project skills + 13 superpowers + 21 agent-skills + 7 claude-mem + 5 caveman + 6 MCP + 5 hooks + decision matrix |
| T4 | `wiki/project/SPRINT_STATE.md` MODIFIED | Per-phase tracking template + Phase 4 task progress subtable (applied inline в этот sprint) |
| T5 | `CLAUDE.md` (repo root) | "BEFORE ANY SPRINT WORK" binding section с phase table + HARD-GATEs + anti-patterns + RU docs links |
| T5 | `llm-wiki/CLAUDE.md` | References к Russian docs + hook description |
| T6 | `wiki/project/decisions/0041-sprint-28-process-enforcement.md` NEW | This ADR |
| T6 | `wiki/project/sprints/sprint-28-process-enforcement.md` NEW | This page |
| T6 | `wiki/project/plans/2026-04-26-sprint-28-process-enforcement.md` NEW | Plan file (closes 12-sprint drift) |
| T6 | `wiki/index.md` MODIFIED | + new docs entries |
| T6 | `wiki/project/architecture/current-state.md` MODIFIED | + S28 sprint history row + canonical counts (40→41 ADRs, 27→28 sprint pages) |
| T6 | `wiki/log.md` MODIFIED | S28 sprint-end entry |

## FSM growth

No FSM changes (canonical counts: 16 states / 30 events / 74 transitions / 45 reason codes — unchanged).

## Reason codes

No new reason codes.

## Tests

No code tests added (process/wiki sprint).

Hook script tested manually:
- Positive: plan file exists → exit 0 ("✓ Sprint flow check OK")
- Negative: plan file removed → exit 2 + helpful error message

## Wiki updates summary

10 files touched:
- 5 NEW: ADR / sprint page / plan / sprint-flow-ru / tooling-inventory-ru
- 5 MODIFIED: SPRINT_STATE / repo CLAUDE.md / llm-wiki CLAUDE.md / index.md / current-state.md
- log.md appended

## Open issues для S29+

### S27 carry-overs (operator decision pending)
- ESC-1 Multi-symbol authorization (S29 expanded scope beyond BTCUSDT MVP)
- ESC-2 "In profit" vs "pass acceptance criteria"
- ESC-3 Operational implications 4H multi-symbol

### Trader-expert backlog (S29-S33)
- S29 Multi-symbol 4H mean_reversion (n≈135 → T5 PASS)
- S30 Regime filter + SMA50 trend gate
- S31 SL calibration {1.0/1.25/1.5}×ATR + t-stat power
- S32 Donchian 4H breakout (independent hypothesis)
- S33 DSR cross-trial sigma_SR (closes S14 Q2 carry-over)

### S28 carry-overs
- Per-task SPRINT_STATE protocol depends on controller discipline (hook не enforces in-flight)
- Optional: pre-commit hook checking SPRINT_STATE updated within last hour
- Optional: `/sprint-start` slash command automating branch + SPRINT_STATE + plan scaffold

## Key decisions

1. **Mechanical enforcement > polite reminder.** Hook = single source of truth blocking, не CLAUDE.md text reminder which drifted under load.

2. **Russian docs = single source for operator.** All process docs RU. CLAUDE.md may stay English (per operator: "А уже в claude.md если тебе надо делай на английском").

3. **Per-task SPRINT_STATE update protocol BINDING.** Phase 4 protocol требует update после КАЖДОЙ task complete (не batch в конце).

4. **Tooling catalog as decision matrix.** Operator может consult `tooling-inventory-ru.md` "TL;DR decision matrix" → знает что invoke когда без чтения skill descriptions.

5. **First plan file since S15** — closes 12-sprint drift mechanically.

## Process artifact: this sprint demonstrates the flow

S28 itself was executed по proper kit flow:
- PHASE 1 Orient (manual since session continuation)
- PHASE 2 Brainstorm SKIPPED (operator-specified deliverables, no scope questions)
- PHASE 3 Plan: `wiki/project/plans/2026-04-26-sprint-28-process-enforcement.md`
- PHASE 4 Execute: per-task TDD where applicable, per-task SPRINT_STATE update, per-task commit
- PHASE 5 Verify: bash -n hook + manual positive/negative test
- PHASE 6 Review: skipped (process/wiki, no code reviewers applicable)
- PHASE 7 Sync: wiki updates per `wiki-update` skill principles
- PHASE 8 Ship: `sprint-finish` skill HARD-GATEs (sprint page exists + counts + index sync)
- PHASE 9 Close: SPRINT_STATE between-sprints + log session-end + tag

## Related

- ADR 0017 (review-agent harness) — parent pattern для hook-based enforcement
- ADR 0041 (this sprint) — mechanical kit enforcement
- Sprint S27 (last drift, no plan file) — context для S28 trigger
- Sprint S15 (last sprint с plan file before drift)
- Hook component pages (existing pattern):
  - `wiki/project/components/adr-agent-sync-hook.md`
  - `wiki/project/components/adr-index-sync-hook.md`
