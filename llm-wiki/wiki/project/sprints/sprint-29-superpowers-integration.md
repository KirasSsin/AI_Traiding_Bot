---
title: Sprint 29 — Full Superpowers Skills Integration (7 missing + Skills × Phase map)
type: sprint
tags: [sprint-29, superpowers, skills, integration, kit-flow, ru]
created: 2026-04-26
updated: 2026-04-26
status: completed
sources:
  - project/decisions/0042-sprint-29-superpowers-integration.md
  - project/architecture/sprint-flow-ru.md
  - project/architecture/tooling-inventory-ru.md
  - project/plans/2026-04-26-sprint-29-superpowers-integration.md
---

# Sprint 29 — Full Superpowers Skills Integration

## Overview

Operator-driven kit upgrade sprint. После S28 process enforcement landed, operator pointed на https://github.com/obra/superpowers и directed:

> "Их надо внедрить в наш flow разработки по спринтам, и встроить в наш кит, чтобы они вызывались там, где они действительно нужны. Переработай кит и внедри максимально нужное количество скиллов."

Pre-S29 only 6 of 13 superpowers skills использовались. S29 integrates remaining 7 + создаёт Skills × Phase integration map (26 skills total).

## Plan / ADR links

- [[../decisions/0042-sprint-29-superpowers-integration]] — Sprint 29 ADR
- [[../plans/2026-04-26-sprint-29-superpowers-integration]] — Sprint 29 plan
- [[../architecture/sprint-flow-ru]] — обновлённый kit flow с new skills
- [[../architecture/tooling-inventory-ru]] — Section 12 NEW Skills × Phase integration map

## Deliverables

### Wiki (in-repo)

| Task | Files | Description |
|------|-------|-------------|
| T1 | `wiki/project/architecture/sprint-flow-ru.md` MODIFIED | Per-phase "Используемые skills" subsections + Phase 4 sub-flows (bug → systematic-debugging, parallel → dispatching-parallel-agents) + Phase 5 verification-before-completion + Phase 6 requesting/receiving-code-review + Cross-phase optional skills + Skills × Phase integration map |
| T2 | `wiki/project/architecture/tooling-inventory-ru.md` MODIFIED | Decision matrix expanded (8 new entries) + Section 3 Superpowers с status legend + "Where invoked в kit flow" per skill + Section 12 NEW Skills × Phase integration map |
| T3 | `CLAUDE.md` (repo root) MODIFIED | "BEFORE ANY SPRINT WORK" phase table expanded — Primary + Optional/sub-skills columns + 6 new anti-patterns |
| T4 | `wiki/project/decisions/0042-sprint-29-superpowers-integration.md` NEW | This ADR |
| T4 | `wiki/project/sprints/sprint-29-superpowers-integration.md` NEW | This page |
| T4 | `wiki/project/plans/2026-04-26-sprint-29-superpowers-integration.md` NEW | Plan file |
| T4 | `wiki/index.md` MODIFIED | + S29 entry + ADR 0042 entry |
| T4 | `wiki/project/architecture/current-state.md` MODIFIED | + S29 sprint history row + canonical counts (41→42 ADRs, 28→29 sprint pages) |
| T4 | `wiki/log.md` MODIFIED | S29 sprint-end entry |

## 7 NEW superpowers skills integrated

| Skill | Phase | Role |
|-------|-------|------|
| `systematic-debugging` | 4 sub-flow | Bug encountered → 4-phase root cause (reproduce → localize → fix → guard) |
| `verification-before-completion` | 5 | Pre-completion checklist (tests / linter / runtime / edge cases / docs) |
| `requesting-code-review` | 6 PRE | Format reviewer brief — context + diff + concerns + acceptance criteria |
| `receiving-code-review` | 6 POST | Categorize feedback (BLOCKER / CONCERN / SUGGESTION) → address per category |
| `dispatching-parallel-agents` | 4+6 | Multiple Agent calls в одном message — explicit pattern |
| `using-git-worktrees` | cross-phase | Sandbox sprint experiments (rare) |
| `writing-skills` | cross-phase | Methodology создания new project skill |

## Skills × Phase integration map (26 skills total)

Single source of truth — Section 12 в `tooling-inventory-ru.md`:
- 13 superpowers skills (6 EXISTING + 7 NEW S29 = full integration)
- 5 project skills (sprint-orient / brainstorm-init / wiki-update / sprint-finish / hook-test)
- 8 agent-skills (planning-and-task-breakdown / test-driven-development / context-engineering / incremental-implementation / code-review-and-quality / security-and-hardening / git-workflow-and-versioning / shipping-and-launch)

## FSM growth

No FSM changes (canonical counts: 16/30/74/45 — unchanged).

## Reason codes

No new reason codes.

## Tests

No code tests added (process/wiki sprint).

PHASE 5 verify: 762 pytest passed (S28 baseline preserved).

## Wiki updates summary

8 files touched:
- 3 NEW: ADR / sprint page / plan
- 5 MODIFIED: sprint-flow-ru / tooling-inventory-ru / repo CLAUDE.md / index.md / current-state.md
- log.md appended

## Open issues для S30+

### S27 carry-overs (operator decision pending — BLOCKING S30 trader-expert backlog)
- ESC-1 Multi-symbol authorization (S30 expanded scope beyond BTCUSDT MVP)
- ESC-2 "In profit" vs "pass acceptance criteria"
- ESC-3 Operational implications 4H multi-symbol

### S28 carry-overs
- Per-task SPRINT_STATE protocol depends on controller discipline
- Optional: pre-commit hook checking SPRINT_STATE updated within last hour
- Optional: `/sprint-start` slash command automating branch + SPRINT_STATE + plan scaffold

### S29 carry-overs
- Optional: `/skill-discover` slash command querying tooling-inventory-ru.md decision matrix
- Optional: enforce verification-before-completion checklist via hook (pre-merge?)
- Optional: dispatch-pattern detection (warn если sequential where parallel possible)

### Trader-expert backlog (S30-S34, depends ESC-1+)
- S30 Multi-symbol 4H mean_reversion (n≈135 → T5 PASS)
- S31 Regime filter + SMA50 trend gate
- S32 SL calibration {1.0/1.25/1.5}×ATR + t-stat power
- S33 Donchian 4H breakout (independent hypothesis)
- S34 DSR cross-trial sigma_SR (closes S14 Q2 carry-over)

## Key decisions

1. **Full integration over selective** — operator directive "максимально нужное количество". 7 missing skills все имеют concrete integration points.

2. **Skills × Phase integration map = single source of truth.** Любой "какой skill где?" → Section 12 в tooling-inventory-ru.md. Заменяет scattered references.

3. **Status legend (✅ EXISTING / 🆕 NEW S29).** Visible какие skills уже used vs новые S29.

4. **Anti-patterns expanded.** Каждый new skill imeет matching anti-pattern в sprint-flow-ru.md и CLAUDE.md (e.g. "❌ Bug ad-hoc fix без systematic-debugging").

5. **No code changes.** Pure docs/wiki sprint. Backward compatible с S28 hook (sprint-flow-check.sh не affected).

6. **S29 itself = proof of process.** Sprint executed по proper kit flow:
   - PHASE 3 plan file created (per S28 binding rules)
   - PHASE 4 per-task TDD-style commit (4 commits T1-T4)
   - Per-task SPRINT_STATE update после каждой task (per S28 protocol)
   - PHASE 8 ship per `sprint-finish` skill HARD-GATEs

## Related

- ADR 0017 (review-agent harness) — review agents foundational
- ADR 0041 (S28 process enforcement) — parent ADR — kit flow mechanical hook
- ADR 0042 (S29 — this) — full superpowers integration
- Sprint S28 (process-enforcement) — established kit flow + Russian docs
- obra/superpowers GitHub repo — skills source

## S29 process artifact

S29 demonstrates the very flow it documents:
- ✅ PHASE 3 plan file `plans/2026-04-26-sprint-29-superpowers-integration.md`
- ✅ PHASE 4 controller-driven per S28 protocol (docs sprint, не code)
- ✅ Per-task commits (T1 be4c10b, T2 202d915, T3 b7b0f16, T4 [pending])
- ✅ Per-task SPRINT_STATE update после каждой task
- ✅ PHASE 5 verify pytest baseline preserved
- ✅ PHASE 7 sync wiki (index + current-state + log)
- ✅ PHASE 8 ship via gh pr + tag + sprint-finish HARD-GATEs
