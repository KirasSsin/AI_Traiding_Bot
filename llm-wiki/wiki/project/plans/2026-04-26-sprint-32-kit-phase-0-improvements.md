---
title: Sprint 32 — Kit Improvement Phase 0 (P0 staleness fixes + 5 skill mappings + cascade smart-explore + Phase 9 consolidate-memory)
type: plan
tags: [plan, sprint-32, kit-improvement, phase-0, p0-fixes, skill-mappings, cascade, consolidate-memory]
created: 2026-04-26
updated: 2026-04-26
status: active
sources:
  - project/SPRINT_STATE.md
  - project/architecture/current-state.md
  - project/architecture/sprint-flow-ru.md
  - project/architecture/kit-overview-ru.md
---

# Sprint 32 — Kit Improvement Phase 0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Закрыть P0 staleness (SPRINT_STATE + current-state) + интегрировать 5 высокоприоритетных skill mappings + добавить smart-explore в cascade + consolidate-memory в Phase 9 Close. Documentation-only sprint (no src/ changes).

**Architecture:** Kit improvement Phase 0 (per КУ analysis): максимальный ROI per минута — 6 doc edits закрывают 57% средний КУ за 45 минут. S32 trading work blocked (ESC-1/2/3 pending) → S32 slot занимаем kit work.

**Tech Stack:** llm-wiki markdown + frontmatter + git workflow + ADR pattern.

---

## Контекст

**Триггер sprint:** Operator-driven kit optimization plan (analysis в session 2026-04-26 после S31 ship). Аналитический prior:

- Ревью проекта выявило P0 staleness: SPRINT_STATE.md "Следующее действие" = "S27 PHASE 8 ship" при S31 between-sprints; current-state.md title = "post-S25" при реальном S31.
- КУ analysis показал 6 quick-win additions с average КУ=57% и time investment 45 мин.
- Trading work S32 blocked: ESC-1/2/3 (multi-symbol authorization / "in profit" semantics / 4H operational implications) pending operator decision per S27 carry-overs.

**Решение:** S32 slot = "Kit Phase 0 improvements" (non-blocking docs work, не трогает trading code).

**Зависимости:**
- Не зависит от ESC-1/2/3 (no trading scope)
- Не блокирует S33+ trading sprints (можно делать параллельно когда trading unblocked)

## File Structure

| Файл | Action | Что меняется |
|------|--------|---------------|
| `llm-wiki/wiki/project/SPRINT_STATE.md` | MODIFY | Stale "Текущий статус" / "Последний спринт" / "Следующее действие" sections (lines 130-175) |
| `llm-wiki/wiki/project/architecture/current-state.md` | MODIFY | Title + H1 + TL;DR + frontmatter sources/tags + test counts (post-S25 → post-S31) |
| `llm-wiki/wiki/project/architecture/sprint-flow-ru.md` | MODIFY | +5 skill mappings (Phase 2/3/4/6/8) + cascade smart-explore + Phase 9 consolidate-memory step |
| `llm-wiki/wiki/project/architecture/kit-overview-ru.md` | MODIFY | Cascade rule diagram update (STEP 2.5 smart-explore) + decision matrix entries |
| `llm-wiki/wiki/project/decisions/0045-sprint-32-kit-phase-0-improvements.md` | NEW | ADR documenting Phase 0 scope + КУ rationale + sprint history slot |
| `llm-wiki/wiki/project/sprints/sprint-32-kit-phase-0-improvements.md` | NEW | Canonical sprint page |
| `llm-wiki/wiki/index.md` | MODIFY | + sprint-32 entry + ADR 0045 entry |
| `llm-wiki/wiki/log.md` | MODIFY | sprint-end + session-end entries |

**No src/ changes** → no pytest regression risk → Phase 5 verify = baseline preservation only.

---

## Tasks

### Task T1: Fix SPRINT_STATE.md stale sections (P0)

**Files:**
- Modify: `llm-wiki/wiki/project/SPRINT_STATE.md` (lines 130-175 — stale bottom sections)

**Steps:**

- [ ] **Step 1: Read current file для контекста**

```
Read llm-wiki/wiki/project/SPRINT_STATE.md (full)
Identify stale sections:
- Line 135: "## Текущий статус" → describes S27 state с wrong counts (30 ADRs / 17 sprint pages)
- Line 145: "## Последний спринт (S27 — formula bug fixes)" → должно быть S31
- Line 158: "## Следующее действие" → "S27 PHASE 8 ship" → должно быть S32 dual-track (kit work in progress + trading pending ESC-1/2/3)
```

- [ ] **Step 2: Edit "Текущий статус" section**

Replace S27-era status с S31 between-sprints reality:
- Sprint counts: 30 ADRs → 44 ADRs (will be 45 after this sprint), 17 sprint pages → 31 (32 after this)
- Status block: kit infrastructure complete, trading validation negative, kit Phase 0 in progress

- [ ] **Step 3: Edit "Последний спринт" section**

Replace S27 description с S31 description (kit revision per best practices, single tools-overview file, CLAUDE.md prune -25%).

- [ ] **Step 4: Edit "Следующее действие" section**

Replace "S27 PHASE 8 ship" с current next-action: "S32 Kit Phase 0 improvements in progress (this sprint) — потом trading work pending ESC-1/2/3 operator decision".

- [ ] **Step 5: Update frontmatter `updated:` date**

- [ ] **Step 6: Commit**

```bash
git add llm-wiki/wiki/project/SPRINT_STATE.md
git commit -m "docs(sprint): SPRINT_STATE T1 — fix P0 stale sections (S27→S31 + counts)"
```

---

### Task T2: Fix current-state.md P0 staleness

**Files:**
- Modify: `llm-wiki/wiki/project/architecture/current-state.md` (lines 1-50 + line 152 test counts)

**Steps:**

- [ ] **Step 1: Edit frontmatter**

```
title: Current State — post-S31 inventory + canonical counts (Kit Phase 0 improvements active, S32 in progress)
tags: [current-state, inventory, baseline, canonical-counts, sprint-31, kit-revision-best-practices, sprint-32-pending, t5-100-structurally-unreachable, regime-independent-edge]
sources: + project/sprints/sprint-27-formula-bug-fixes.md, + project/decisions/0040-..., 0041-..., 0042-..., 0043-..., 0044-..., 0045-... (S27-S32 sources)
```

- [ ] **Step 2: Edit H1**

```
# Current State (post-S31, 2026-04-26) — Kit infrastructure complete (CLAUDE.md prune -25%, 9 reviewer agents, 6 hooks, 26 skills mapped)
```

- [ ] **Step 3: Edit TL;DR (one-paragraph S31-aware update preserving prior TL;DR for context)**

Keep S25 TL;DR as "Previous TL;DR" reference. New top TL;DR: S31 state — kit at 9 reviewer agents + 6 hooks + 26 skills + cascade rule + best practices coverage 20/20.

- [ ] **Step 4: Edit Test/quality state section (line ~150)**

```
- pytest unit: 762 passed (был 604 — обновлено per S27-S31 baseline)
- mypy --strict src/: ≤ 44 errors (S8c baseline preserved через S31)
```

- [ ] **Step 5: Commit**

```bash
git add llm-wiki/wiki/project/architecture/current-state.md
git commit -m "docs(arch): current-state T2 — fix P0 staleness (post-S25→post-S31 + test counts 604→762)"
```

---

### Task T3: Add 5 skill mappings к sprint-flow-ru.md

**Files:**
- Modify: `llm-wiki/wiki/project/architecture/sprint-flow-ru.md`

**Steps:**

- [ ] **Step 1: Phase 2 — add idea-refine + spec-driven-development**

Edit Phase 2 skills table:
```markdown
| `agent-skills:idea-refine` | Phase 2 PRE | Vague operator idea перед brainstorm-init — структурированный divergent thinking | NEW (S32) |
| `agent-skills:spec-driven-development` | Phase 2/3 | Non-trading features (dashboard / CLI / infrastructure) без spec — spec creation с AC | NEW (S32) |
```

- [ ] **Step 2: Phase 4 — add source-driven-development**

Edit Phase 4 skills table:
```markdown
| `agent-skills:source-driven-development` | Phase 4 (Bybit/pydantic/pybit tasks) | Verify против official docs ДО implementation — prevents API misuse bugs | NEW (S32) |
```

- [ ] **Step 3: Phase 6 — add code-simplification**

Edit Phase 6 skills table:
```markdown
| `agent-skills:code-simplification` | Phase 6 optional | Post-implementation cleanup сложных формул — simplify without behavior change (regression test guards) | NEW (S32) |
```

- [ ] **Step 4: Phase 8 — add documentation-and-adrs**

Edit Phase 8 skills table:
```markdown
| `agent-skills:documentation-and-adrs` | Phase 8 | ADR creation per sprint — explicit step для capturing architectural decisions context | NEW (S32) |
```

- [ ] **Step 5: Update Skills × Phase integration map (bottom of file)**

Add 5 new entries к 26 → 31 skills total. Update count: "Total: 31 skills mapped к kit flow (13 superpowers + 5 project + 13 agent-skills)".

- [ ] **Step 6: Commit**

```bash
git add llm-wiki/wiki/project/architecture/sprint-flow-ru.md
git commit -m "docs(kit): sprint-flow T3 — add 5 skill mappings (idea-refine/spec/source/simplification/docs-adrs)"
```

---

### Task T4: Add smart-explore к cascade rule

**Files:**
- Modify: `llm-wiki/wiki/project/architecture/sprint-flow-ru.md` (Token economy section)
- Modify: `llm-wiki/wiki/project/architecture/kit-overview-ru.md` (Cascade rule section)

**Steps:**

- [ ] **Step 1: sprint-flow-ru.md cascade update**

Replace 4-step cascade с 5-step:
```
STEP 1: wiki/<page>.md            (curated, structured)   ← CHECK FIRST
   ↓ not found
STEP 2: mem-search                (past sessions semantic)
   ↓ not found
STEP 2.5: claude-mem:smart-explore (token-optimized structural code nav)  ← NEW (S32)
   ↓ needed
STEP 3: Grep raw                  (current code state)
   ↓ needed
STEP 4: Read raw + offset         (full content, controlled)
```

Add rationale paragraph: smart-explore = выбор когда нужна structural understanding (call graph, file relationships) перед naked grep — экономит ~30-50% tokens vs grep+full-read sequence.

- [ ] **Step 2: kit-overview-ru.md cascade update (mirror)**

Same diagram update в "📚 Cascade rule" section.

- [ ] **Step 3: Commit**

```bash
git add llm-wiki/wiki/project/architecture/sprint-flow-ru.md llm-wiki/wiki/project/architecture/kit-overview-ru.md
git commit -m "docs(kit): cascade T4 — add smart-explore STEP 2.5 (token-optimized code nav)"
```

---

### Task T5: Phase 9 Close — consolidate-memory step

**Files:**
- Modify: `llm-wiki/wiki/project/architecture/sprint-flow-ru.md` (Phase 9 Close section)

**Steps:**

- [ ] **Step 1: Add Step 5 к Phase 9 Close procedure**

```markdown
## Phase 9: Close (between-sprints)

### Procedure
1. SPRINT_STATE → phase=between-sprints, sprint=N+1 ready, tag updated
2. Append wiki/log.md session-end entry
3. mark_chapter "Sprint N — ship complete"
4. git commit -m "docs(sprint): SPRINT_STATE → between-sprints alpha.N"
5. **(Каждые 5 спринтов OR при >30 observations в claude-mem)**: Invoke `anthropic-skills:consolidate-memory` — reflective pass over corpus, organize learnings в structured chunks, persist consolidated memory.
   - Ratio check: `mcp__plugin_claude-mem_mcp-search__list_corpora` показывает observation count
   - Trigger: >30 observations OR sprint number divisible by 5 (S35, S40, ...)
   - Output: consolidated knowledge categories (trading-decisions / formula-knowledge / process-patterns / debug-knowledge)
```

- [ ] **Step 2: Commit**

```bash
git add llm-wiki/wiki/project/architecture/sprint-flow-ru.md
git commit -m "docs(kit): Phase 9 T5 — add consolidate-memory step (every 5 sprints OR 30+ observations)"
```

---

### Task T6: ADR 0045 + sprint-32 page + index.md + canonical counts sync

**Files:**
- Create: `llm-wiki/wiki/project/decisions/0045-sprint-32-kit-phase-0-improvements.md`
- Create: `llm-wiki/wiki/project/sprints/sprint-32-kit-phase-0-improvements.md`
- Modify: `llm-wiki/wiki/index.md` (+ ADR 0045 + sprint-32 entries)
- Modify: `llm-wiki/wiki/project/architecture/current-state.md` (canonical counts: 44→45 ADRs, 31→32 sprint pages, sprint history row)

**Steps:**

- [ ] **Step 1: Create ADR 0045**

Standard ADR skeleton:
- Status: accepted
- Context: КУ analysis Phase 0 deliverables
- Decision: 6 specific changes (T1-T5 + T6 sync)
- Consequences: token economy +15% per session, skill coverage 8→13 AS skills, kit alignment с best practices

- [ ] **Step 2: Create sprint-32 page**

Standard sprint page skeleton:
- Overview: Kit Improvement Phase 0 (КУ-driven)
- Plan/ADR links
- Deliverables table (6 tasks)
- Tests: 762 pytest preserved
- FSM growth: none
- Reason codes: none
- Wiki updates: 8 files touched
- Open issues для S33+ (Phase 1 items: CI / pre-commit / SQLite MCP / SPRINT_STATE freshness hook / dashboard-reviewer)
- Key decisions: 6 changes per КУ analysis

- [ ] **Step 3: index.md +entries**

Add S32 sprint entry + ADR 0045 entry в alphabetical/numerical positions.

- [ ] **Step 4: current-state.md sync canonical counts**

Update canonical-counts table:
- ADRs: 44 → **45** (S32 +1)
- Sprint pages: 31 → **32** (S32 +1)

Add row к sprint history table:
```
| **S32** | **0045** | **v0.1.0-alpha.32** | **2026-04-26** | **Kit Improvement Phase 0** — КУ-driven docs sprint. P0 staleness fixes (SPRINT_STATE + current-state), 5 NEW skill mappings (idea-refine/spec-driven/source-driven/code-simplification/documentation-and-adrs), cascade smart-explore STEP 2.5, Phase 9 consolidate-memory step. КУ avg 57% за 45 мин (best ROI per phase). Skill coverage 8→13 AS / 26→31 total. Phase 1 (CI/SQLite/hooks) deferred к S33. NO code changes. 762 pytest preserved. |
```

- [ ] **Step 5: Commit**

```bash
git add llm-wiki/wiki/project/decisions/0045-sprint-32-kit-phase-0-improvements.md \
        llm-wiki/wiki/project/sprints/sprint-32-kit-phase-0-improvements.md \
        llm-wiki/wiki/index.md \
        llm-wiki/wiki/project/architecture/current-state.md
git commit -m "docs(sprint): T6 — ADR 0045 + sprint-32 page + index/counts sync (44→45 ADRs, 31→32 sprints)"
```

---

## Phase 5 Verify

```bash
source /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot/.venv/bin/activate
pytest tests/ -q --ignore=tests/integration 2>&1 | tail -5
# Expected: 762 passed (S31 baseline preserved)

mypy --strict src/ 2>&1 | tail -3
# Expected: ≤ 44 errors (S8c baseline)

# Canonical counts verify
python -c "from src.execution.state_machine import TRANSITIONS, ExecutionState, ExecutionEvent; from src.risk.reason_codes import ReasonCode; print(f'states={len(list(ExecutionState))}, events={len(list(ExecutionEvent))}, transitions={len(TRANSITIONS)}, reason_codes={len(list(ReasonCode))}')"
# Expected: states=16, events=30, transitions=74, reason_codes=45
```

**No code changes** → all baselines preserved by construction.

Update SPRINT_STATE Phase 5 status="done" перед PR (HARD-GATE: phase-advance.sh blocks `gh pr merge` если != done/skipped).

---

## Phase 7 Sync

- [ ] log.md sprint-end entry для S32

---

## Phase 8 Ship

Per `sprint-finish` skill checklist:
1. Pre-validation (pytest + mypy preserved)
2. HARD-GATE — sprint-32 page exists ✓ (T6)
3. HARD-GATE — canonical counts sync ✓ (T6)
4. HARD-GATE — ADR 0045 в index.md ✓ (T6)
5. HARD-GATE — Block 1↔2 sync (N/A, no component pages touched)
6. HARD-GATE — orphan-audit grep includes tests/ (N/A, no src/ changes)
7. SPRINT_STATE → 8-ship
8. git push (sprint-flow-check.sh validates plan file ✓)
9. gh pr create
10. gh pr merge --squash --delete-branch (phase-advance.sh validates Phase 5=done ✓)
11. git tag v0.1.0-alpha.32 + push
12. SPRINT_STATE → between-sprints
13. mark_chapter "Sprint 32 — ship complete"

---

## Phase 9 Close

```
1. SPRINT_STATE → between-sprints
2. log.md session-end entry
3. mark_chapter
4. git commit docs(sprint): SPRINT_STATE → between-sprints alpha.32
5. (Skip consolidate-memory — first invocation will be S35 OR при >30 observations)
```

---

## Self-Review

**Spec coverage check:**
- ✓ T1 covers P0 SPRINT_STATE fix
- ✓ T2 covers P0 current-state fix
- ✓ T3 covers 5 skill additions (Phase 2/3/4/6/8)
- ✓ T4 covers cascade smart-explore
- ✓ T5 covers Phase 9 consolidate-memory
- ✓ T6 covers ADR + sprint page + index + counts sync

**No placeholders:** All steps contain concrete edits + commit messages.

**Type consistency:** N/A (no code).

**Execution mode:** Controller-driven (docs sprint, similar to S28-S31). Per Phase 4 sprint-flow-ru.md procedure.

---

## Related

- ADR 0044 (S31 kit revision per best practices) — direct predecessor
- ADR 0041-0043 (S28-S30 process enforcement / superpowers / tier-2 agents) — cumulative kit flow
- Pre-S32 КУ analysis (this session 2026-04-26 chapter "Kit improvement plan — КУ analysis") — source rationale
- S32-S36 trader-expert backlog (multi-symbol / regime filter / etc) — orthogonal, awaits ESC-1/2/3 operator decision
