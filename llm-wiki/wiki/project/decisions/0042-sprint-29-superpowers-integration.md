---
title: 0042. Sprint 29 — Full Superpowers Skills Integration (7 missing skills + Skills × Phase map)
type: decision
date: 2026-04-26
sprint: 29
tags: [adr, sprint-29, superpowers, skills, integration, kit-flow, ru]
sources:
  - project/architecture/sprint-flow-ru.md
  - project/architecture/tooling-inventory-ru.md
  - project/decisions/0041-sprint-28-process-enforcement.md
  - https://github.com/obra/superpowers
status: accepted
---

# 0042. Sprint 29 — Full Superpowers Skills Integration

**Status:** accepted
**Date:** 2026-04-26

## Context

Operator directive 2026-04-26 после S28 ship:

> "У нас есть множество полезных скиллов, вот репозиторий лучших https://github.com/obra/superpowers
> Их надо внедрить в наш flow разработки по спринтам, и встроить в наш кит, чтобы они вызывались там, где они действительно нужны.
> Но учитывай что скиллы частично уже используются.
> Переработай кит и внедри максимально нужное количество скиллов, чтобы максимально увеличить качество разработки."

### Gap analysis (pre-S29)

Обнаружено: 6 of 13 superpowers skills uses, 7 missing. Существующее kit использовало:
- `superpowers:brainstorming` (alternative к brainstorm-init)
- `superpowers:writing-plans`
- `superpowers:subagent-driven-development`
- `superpowers:executing-plans`
- `superpowers:test-driven-development`
- `superpowers:finishing-a-development-branch`

Missing skills с concrete integration points:
| Skill | Gap | Phase |
|-------|-----|-------|
| `systematic-debugging` | Bug ad-hoc fixes (S27 had multiple bug fixes без systematic process) | 4 sub-flow |
| `verification-before-completion` | Verify только pytest/mypy — нет extended checklist | 5 |
| `requesting-code-review` | Reviewer briefs ad-hoc формат | 6 |
| `receiving-code-review` | Reviewer feedback ad-hoc processing | 6 |
| `dispatching-parallel-agents` | Parallel reviewer pattern implicit (используется но без explicit skill ref) | 4+6 |
| `using-git-worktrees` | Sandbox audits (S27 audit re-run could've used worktree) | cross-phase |
| `writing-skills` | New project skills создавались ad-hoc (S28 brainstorm-init/sprint-orient/wiki-update/sprint-finish) | cross-phase |

## Options

### Option A — Status quo (6 skills)
- **Pros:** No work
- **Cons:** Quality gaps (ad-hoc bug fixes, ad-hoc reviewer briefs, no checklist verification)

### Option B — Selective addition (3-4 skills)
- **Pros:** Minimal change
- **Cons:** Still gaps

### Option C — Full integration (all 13 + map)
- **Pros:** Comprehensive quality coverage. Single source of truth для skill invocation. Aligns с operator "максимально нужное количество".
- **Cons:** More documentation surface (3 files updated)

## Decision

**Option C** — full integration of 7 missing superpowers skills + Skills × Phase integration map (26 skills total).

### Components

1. **`sprint-flow-ru.md`** MODIFIED:
   - Per-phase "Используемые skills" subsection (skill name + when triggered)
   - Phase 4 NEW sub-flows: "Bug encountered → systematic-debugging", "Parallel reviewers → dispatching-parallel-agents"
   - Phase 5 verification-before-completion checklist
   - Phase 6 expanded с requesting-code-review + receiving-code-review pattern
   - NEW "Cross-phase optional skills" section (using-git-worktrees / writing-skills / using-superpowers)
   - NEW "Skills × Phase integration map" — 26 skills mapped к kit flow
   - Anti-patterns +8 для new skills

2. **`tooling-inventory-ru.md`** MODIFIED:
   - Decision matrix +8 entries (bug, pre-completion, reviewer brief format, feedback processing, parallel reviewers, sandbox sprint, new project skill, security)
   - Section 3 Superpowers: status legend (✅ EXISTING / 🆕 NEW S29) per skill, "Where invoked в kit flow" per skill, full detail для 7 NEW skills
   - NEW Section 12 "Skills × Phase integration map" — 26 skills table

3. **`CLAUDE.md`** (repo root) MODIFIED:
   - "BEFORE ANY SPRINT WORK" phase table expanded — "Primary skill(s)" + "Optional/sub-skills" columns per phase
   - Cross-phase optional skills subsection
   - Anti-patterns +6 для new skills

## Consequences

### Code changes

NONE (pure docs/wiki sprint).

### Wiki changes

Touched 5 files:
- `wiki/project/architecture/sprint-flow-ru.md` MODIFIED (+ 7 superpowers + integration map + anti-patterns)
- `wiki/project/architecture/tooling-inventory-ru.md` MODIFIED (Section 12 NEW + Section 3 expanded + decision matrix expanded)
- `CLAUDE.md` (repo root) MODIFIED (phase table expanded)
- `wiki/project/decisions/0042-sprint-29-superpowers-integration.md` NEW (this ADR)
- `wiki/project/sprints/sprint-29-superpowers-integration.md` NEW

Plus:
- `wiki/index.md` MODIFIED — entries для S29 + ADR 0042
- `wiki/project/architecture/current-state.md` MODIFIED — sprint history row +S29 + canonical counts (41→42 ADRs, 28→29 sprint pages)
- `wiki/log.md` MODIFIED — sprint-end entry

### Backward compatibility

- Existing skill references (6 superpowers + 5 project + 8 agent-skills) preserved
- Phase table expanded, не replaced — old "Skill / Tool" column → "Primary skill(s)" + "Optional/sub-skills"
- Hook `sprint-flow-check.sh` (S28) unchanged

### Carry-overs к S30+

- S27 ESC items (multi-symbol authorization / live pilot ETH 4H / operational implications) STILL pending operator decision
- S28 carry-overs (per-task SPRINT_STATE depends на controller discipline / optional pre-commit hook for SPRINT_STATE freshness / optional `/sprint-start` slash command) STILL pending
- S29 carry-overs:
  - Optional: project-level `/skill-discover` slash command querying tooling-inventory-ru.md decision matrix
  - Optional: enforce verification-before-completion checklist via hook (pre-merge?)
  - Optional: dispatch-pattern detection (warn если sequential where parallel possible)

### Skills × Phase mapping = single source of truth

После S29 любой вопрос "какой skill в какой фазе invoked" → consult Section 12 в tooling-inventory-ru.md. Replaces scattered references в multiple docs.

## References

- `wiki/project/architecture/sprint-flow-ru.md` — обязательный процесс (updated S29)
- `wiki/project/architecture/tooling-inventory-ru.md` — tooling catalog (updated S29 с integration map)
- `wiki/project/decisions/0041-sprint-28-process-enforcement.md` — process enforcement (parent ADR)
- `wiki/project/decisions/0017-review-agent-harness.md` — review agents matrix
- `wiki/project/plans/2026-04-26-sprint-29-superpowers-integration.md` — S29 plan
- `wiki/project/sprints/sprint-29-superpowers-integration.md` — S29 page
- https://github.com/obra/superpowers — superpowers skills source repo
