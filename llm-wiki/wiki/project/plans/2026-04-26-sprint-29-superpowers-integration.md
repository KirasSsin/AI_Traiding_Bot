# Sprint 29 — Superpowers Skills Integration (full kit upgrade)

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` (controller-driven OK для docs sprint).

**Goal:** Integrate all 13 superpowers skills explicitly в kit flow. Currently 6 used (brainstorming/writing-plans/subagent-driven/executing-plans/test-driven-development/finishing). Add 7 missing: systematic-debugging, verification-before-completion, requesting-code-review, receiving-code-review, dispatching-parallel-agents, using-git-worktrees, writing-skills.

**Architecture:** Update sprint-flow-ru.md (explicit skill invocation per phase + skill descriptor) + tooling-inventory-ru.md (add "Where invoked в kit flow" column) + CLAUDE.md binding section (add skill names к phase table).

**Tech Stack:** Markdown only. No code changes.

---

## Context

Operator directive 2026-04-26:

> "У нас есть множество полезных скиллов, вот репозиторий лучших https://github.com/obra/superpowers
> Их надо внедрить в наш flow разработки по спринтам, и встроить в наш кит, чтобы они вызывались там, где они действительно нужны.
> Но учитывай что скиллы частично уже используются.
> Переработай кит и внедри максимально нужное количество скиллов, чтобы максимально увеличить качество разработки."

### Gap analysis (currently vs needed)

| Phase | Current | Missing skill | Why needed |
|-------|---------|--------------|------------|
| 2 Brainstorm | brainstorm-init (project) → trader-expert | `superpowers:brainstorming` (Socratic refinement) | Fallback для non-trading scope (process design, infrastructure) — trader-expert не applies |
| 4 Execute | subagent-driven OR executing-plans + test-driven-development | `superpowers:systematic-debugging` (4-phase root cause) | Bug encountered during execution → systematic process not ad-hoc guessing |
| 4 Execute | (sequential reviewers) | `superpowers:dispatching-parallel-agents` (concurrent subagent pattern) | Explicit pattern для parallel reviewers (currently implicit) |
| 5 Verify | manual pytest+mypy | `superpowers:verification-before-completion` (pre-completion checklist) | Ensure не только "tests pass" но full verification (lint, runtime check, edge cases) |
| 6 Review | L5 domain reviewers | `superpowers:requesting-code-review` (format request) | Standardize reviewer brief — context + diff + specific concerns |
| 6 Review | (manual feedback processing) | `superpowers:receiving-code-review` (process feedback) | Systematic response к blockers/concerns, не ad-hoc |
| Cross-phase | (rare) | `superpowers:using-git-worktrees` (parallel sandboxes) | Sandbox experiments (audit re-runs, what-if scenarios) without polluting main branch |
| Meta | (manual project skill creation) | `superpowers:writing-skills` (skill creation methodology) | When adding new project skill к `.claude/skills/` (S28 brainstorm-init/sprint-orient/wiki-update/sprint-finish создавались ad-hoc — повторное создание should follow methodology) |

### Skills already integrated (NO change required)

- `superpowers:brainstorming` (alternative к brainstorm-init для non-trading scope)
- `superpowers:writing-plans` (PHASE 3 skill — referenced)
- `superpowers:subagent-driven-development` (PHASE 4 skill — referenced)
- `superpowers:executing-plans` (PHASE 4 alternative — referenced)
- `superpowers:test-driven-development` (PHASE 4 implementation — referenced)
- `superpowers:finishing-a-development-branch` (PHASE 8 — referenced)

### Skills in obra/superpowers с meta nature (auto-loaded)

- `superpowers:using-superpowers` — meta-skill auto-loaded session start (no explicit invocation needed)

---

## File Structure

MODIFY:
- `llm-wiki/wiki/project/architecture/sprint-flow-ru.md`
  - Add "Используемые superpowers скиллы" subsection per phase
  - Add explicit invoke commands где applies
  - Add new sub-phases: "Bug encountered → systematic-debugging", "Verification → verification-before-completion"
- `llm-wiki/wiki/project/architecture/tooling-inventory-ru.md`
  - Add "Where invoked в kit flow" column к Superpowers skills table
  - Add explicit per-skill phase mapping
- `CLAUDE.md` (repo root)
  - Update phase table column "Skill / Tool" с specific names

NEW:
- `llm-wiki/wiki/project/decisions/0042-sprint-29-superpowers-integration.md` — ADR
- `llm-wiki/wiki/project/sprints/sprint-29-superpowers-integration.md` — sprint page

---

## Task Breakdown

### Task 1: sprint-flow-ru.md — explicit skill invocation per phase

**Files:**
- Modify: `llm-wiki/wiki/project/architecture/sprint-flow-ru.md`

- [ ] **Step 1:** В каждый phase section добавить subsection "Используемые superpowers скиллы" с invoke command + when triggered.

- [ ] **Step 2:** Add explicit "Phase 4 sub-flows":
  - Bug encountered → `superpowers:systematic-debugging` (4-phase root cause)
  - Parallel reviewer dispatch → `superpowers:dispatching-parallel-agents`

- [ ] **Step 3:** Add к Phase 5 explicit checklist invocation:
  - `superpowers:verification-before-completion` checklist

- [ ] **Step 4:** Add к Phase 6 review skills:
  - `superpowers:requesting-code-review` для format reviewer brief
  - `superpowers:receiving-code-review` для systematic feedback processing

- [ ] **Step 5:** Add cross-phase section "Optional skills":
  - `superpowers:using-git-worktrees` (parallel sandboxes)
  - `superpowers:writing-skills` (создание new project skill)

- [ ] **Step 6:** Update "Связанные документы" — все 13 superpowers skills referenced

- [ ] **Step 7:** Commit

```bash
git commit -m "docs(s29-t1): sprint-flow-ru.md — explicit superpowers skills per phase"
```

### Task 2: tooling-inventory-ru.md — "Where invoked" column + integration map

**Files:**
- Modify: `llm-wiki/wiki/project/architecture/tooling-inventory-ru.md`

- [ ] **Step 1:** Replace "## 3. Superpowers Plugin Skills (13)" section с new format — каждый skill имеет:
  - Назначение
  - Когда (specific phase/sub-trigger)
  - **Where invoked в kit flow** (NEW column)
  - Invoke command pattern

- [ ] **Step 2:** Add new section "## 12. Skills × Phase integration map" — table mapping каждый skill к каждой phase где invoked.

- [ ] **Step 3:** Update "TL;DR decision matrix" с new entries:
  - Bug encountered → `superpowers:systematic-debugging`
  - Pre-completion check → `superpowers:verification-before-completion`
  - Reviewer brief format → `superpowers:requesting-code-review`
  - Reviewer feedback processing → `superpowers:receiving-code-review`
  - Parallel subagents → `superpowers:dispatching-parallel-agents`
  - Sandbox sprint → `superpowers:using-git-worktrees`
  - New project skill → `superpowers:writing-skills`

- [ ] **Step 4:** Commit

```bash
git commit -m "docs(s29-t2): tooling-inventory-ru.md — integration map + decision matrix expansion"
```

### Task 3: CLAUDE.md — skill names per phase row

**Files:**
- Modify: `CLAUDE.md` (repo root)

- [ ] **Step 1:** Update "BEFORE ANY SPRINT WORK" phase table:
  - Phase 4: add `+ systematic-debugging (если bug) + dispatching-parallel-agents (для parallel reviewers)`
  - Phase 5: replace "pytest + mypy" → `superpowers:verification-before-completion` skill
  - Phase 6: add `+ requesting-code-review + receiving-code-review`
  - Cross-phase note: `using-git-worktrees` (rare — parallel sandboxes), `writing-skills` (новые project skills)

- [ ] **Step 2:** Commit

### Task 4: ADR 0042 + sprint-29 page + wiki sync

**Files:**
- Create: `llm-wiki/wiki/project/decisions/0042-sprint-29-superpowers-integration.md`
- Create: `llm-wiki/wiki/project/sprints/sprint-29-superpowers-integration.md`
- Modify: `llm-wiki/wiki/index.md`
- Modify: `llm-wiki/wiki/project/architecture/current-state.md`
- Modify: `llm-wiki/wiki/log.md`

- [ ] **Step 1:** ADR 0042 — context (S28 process enforcement landed, but skill integration shallow), options (full vs partial integration), decision (full integration of 7 missing skills + integration map), consequences.

- [ ] **Step 2:** Sprint-29 page — deliverables table, key decisions, S29 process artifact (executed по proper kit flow per S28 binding rules).

- [ ] **Step 3:** index.md +S29 entry +ADR 0042 entry

- [ ] **Step 4:** current-state.md +S29 sprint history row + canonical counts (41 → 42 ADRs, 28 → 29 sprint pages)

- [ ] **Step 5:** log.md sprint-end entry

- [ ] **Step 6:** Commit

### Task 5: PHASE 5-8 ship

- [ ] **Step 1:** PHASE 5 verify — pytest baseline preserved (no code changes)
- [ ] **Step 2:** PHASE 7 sync done (T4 covered)
- [ ] **Step 3:** Touch agent prompts (ADR sync hook)
- [ ] **Step 4:** Push branch
- [ ] **Step 5:** gh pr create
- [ ] **Step 6:** gh pr merge --squash --delete-branch
- [ ] **Step 7:** Tag v0.1.0-alpha.29
- [ ] **Step 8:** SPRINT_STATE → between-sprints

---

## Self-Review Checklist

- [x] Gap analysis explicit (current vs needed per phase)
- [x] All 13 superpowers skills mapped к phase
- [x] Каждый missing skill имеет concrete integration point
- [x] No code changes (process/wiki only)
- [x] Backward compat (existing skills preserved)

## Execution mode

Controller-driven (docs only, не code). 4 commits + 1 ship.
