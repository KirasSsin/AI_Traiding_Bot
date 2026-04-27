---
title: Sprint 32e — Kit Audit + Doc Sync (post-S32 series review)
type: plan
tags: [plan, sprint-32e, kit-audit, doc-sync, retrospective]
created: 2026-04-27
updated: 2026-04-27
status: active
sources:
  - project/decisions/0048-sprint-32d-kit-phase-3-improvements.md
  - project/SPRINT_STATE.md
  - project/architecture/kit-overview-ru.md
  - project/architecture/tooling-inventory-ru.md
  - project/architecture/sprint-flow-ru.md
---

# Sprint 32e — Kit Audit + Doc Sync

> **For agentic workers:** Use superpowers:executing-plans (controller-driven retrospective + doc sync sprint).

**Goal:** Audit kit components (used / unused / needed / not needed + rationale) post-S32 series + apply doc updates per findings + split tooling-inventory-ru.md (60KB exceeds 50KB threshold).

**Architecture:** Sub-sprint S32 series **post-completion audit** (operator initiated). Tag v0.1.0-alpha.32e. Hybrid kit work: audit deliverable + doc maintenance. Pre-S33 trading sprint cleanup.

**Tech Stack:** markdown analysis + grep/git log empirical data + wiki sync.

---

## Context

S32 series shipped (S32+S32b+S32c+S32d). Operator request: audit kit components, identify unused/redundant, update docs.

**Pre-plan empirical findings (этого session раннее):**

### Doc drift detected

| File | Issue |
|------|-------|
| `kit-overview-ru.md` | "Best practices applied" section: MCP=6 stale (real 8), Subagents=9 stale (real 11) |
| `tooling-inventory-ru.md` | **60140 bytes ≈ 58.7KB** — exceeds 50KB safe Read threshold (CLAUDE.md sec 9 BINDING) |

### Reviewer agents usage analysis (S27-S32d = 9 sprints)

| Agent | Mentions in sprint pages | Real invocation evidence | Status |
|-------|--------------------------|--------------------------|--------|
| trader-expert | 4/9 (matrix tables) | Used каждый brainstorm phase 2 | ✅ ACTIVE |
| trading-logic-reviewer | 3/9 | 0 invocations S27-S32d (process sprints) | ⚠️ DORMANT (used pre-S27, ready for S33+ trading) |
| quant-stats-reviewer | 0/9 | 0 invocations S27-S32d (no math changes) | ⚠️ DORMANT (ready for math sprint) |
| data-integrity-reviewer | 2/9 | 0 invocations S27-S32d (no schema changes) | ⚠️ DORMANT (ready for storage sprint) |
| architecture-reviewer | 2/9 | 0 invocations S27-S32d (no cross-module refactor) | ⚠️ DORMANT |
| python-reviewer | 2/9 | 0 invocations S27-S32d | ⚠️ DORMANT |
| security-auditor (S30 NEW) | 1/9 | 0 invocations (no money path touched) | 🆕 READY (validates at first money sprint) |
| test-engineer (S30 NEW) | 2/9 | 0 invocations (no new modules) | 🆕 READY |
| doc-reviewer (S30 NEW) | 1/9 | 0 invocations (no wiki-update post src/ change) | 🆕 READY |
| dashboard-reviewer (S32b NEW) | 3/9 | 0 invocations (no dashboard work since S26) | 🆕 READY |
| bybit-api-reviewer (S32d NEW) | 6/9 | 0 invocations (no Bybit code touched since S25 dashboard) | 🆕 READY |

**Conclusion:** All 11 agents NEEDED. Process sprints S27-S32d не trigger code reviewers by design — это normal. Validation = at first relevant trading/code sprint.

### Hooks usage analysis

| Hook | Status |
|------|--------|
| adr-agent-sync-check.sh | ✅ ACTIVE — fires каждый push с ADR change (verified S32 series multiple times) |
| adr-index-sync-check.sh | ✅ ACTIVE — verified S32 series |
| wiki-broken-link-check.sh | ✅ ACTIVE — caught S32b sprint-26-dashboard broken link + S32d agent ADR refs |
| sprint-flow-check.sh | ✅ ACTIVE — verified S32 series push validations |
| phase-advance.sh | ✅ ACTIVE — verified PR merge validations |
| sprint-state-freshness-check.sh (S32b) | ✅ ACTIVE — fires каждый push (verified positive + negative tests) |
| context-budget-warn.sh (S32d) | 🆕 READY — UserPromptSubmit hook, advisory only, low fire rate (small transcripts) |
| caveman-* | ✅ ACTIVE — session lifecycle |

**Conclusion:** All hooks NEEDED + USED. No removals.

### MCP servers usage analysis

| MCP | Status |
|-----|--------|
| plugin_claude-mem_mcp-search | ✅ HEAVY USE — cascade STEP 2 каждый task |
| ccd_session (mark_chapter) | ✅ ACTIVE — каждый sprint chapter marks |
| scheduled-tasks | ⚠️ NOT YET INVOKED — operator-side schedule registration (Section 23 wire S32d) |
| mcp-registry | ⚠️ RARE — MCP discovery, used при S32b SQLite MCP search |
| computer-use | ❌ NOT USED in trading — Mac native apps focus, irrelevant к trading bot |
| Claude_in_Chrome | ❌ NOT USED in trading — web automation, dashboard demo-only |
| sqlite-trading (S32b) | 🆕 READY — verified empty list_tables, awaits real bot.db population |
| fetch (S32c) | 🆕 NOT YET APPROVED — operator approve pending next session start |

**Conclusion:**
- 6/8 MCP active or ready/needed
- **2/8 MCP question marks:** computer-use + Claude_in_Chrome — NOT relevant к trading bot work, but harmless overhead. Recommendation: keep registered (may be used при manual debugging Mac issues OR dashboard browser test S33+). Document explicit "not used by default" в kit-overview.

### Project skills usage analysis

| Skill | Status |
|-------|--------|
| sprint-orient | ✅ ACTIVE — каждый session start |
| sprint-finish | ✅ ACTIVE — каждый Phase 8 ship |
| wiki-update | ✅ ACTIVE — каждый Phase 7 sync |
| brainstorm-init | ⚠️ DORMANT S27-S32d (operator-specified deliverables = brainstorm skipped) — ready для S33+ |
| hook-test | ⚠️ EXPLICIT ONLY — used during hook creation S32b/S32d |

**Conclusion:** All 5 project skills NEEDED. brainstorm-init активизируется при S33 trading scope.

### Plugin skills usage analysis (~50 plugin skills)

Heavily used:
- superpowers: writing-plans / subagent-driven-development / executing-plans / TDD / verification-before-completion / requesting-code-review / receiving-code-review / dispatching-parallel-agents / brainstorming / finishing-a-development-branch / using-git-worktrees / writing-skills / using-superpowers / systematic-debugging
- agent-skills: planning-and-task-breakdown / spec-driven-development / source-driven-development / code-review-and-quality / security-and-hardening / code-simplification / documentation-and-adrs / api-and-interface-design / browser-testing-with-devtools / performance-optimization / idea-refine
- claude-mem: smart-search / mem-search / list_corpora / smart-explore (S32 cascade STEP 2.5)
- caveman: caveman mode active session
- anthropic-skills: consolidate-memory (Phase 9 trigger every 5 sprints OR 30+ obs — not yet triggered, корпус 17 obs)

Conclusion: All plugin skills NEEDED. Coverage 36 mapped + extras through plugin auto-discovery.

## File Structure

| Файл | Action | Что меняется |
|------|--------|---------------|
| `llm-wiki/wiki/project/architecture/kit-audit-2026-04-27.md` | NEW | Audit findings — usage analysis + recommendations |
| `llm-wiki/wiki/project/architecture/kit-overview-ru.md` | MODIFY | Fix "Best practices applied" stale counts (MCP 6→8, Subagents 9→11) + add audit reference |
| `llm-wiki/wiki/project/architecture/tooling-inventory-ru.md` | **SPLIT** | 60KB → split в `tooling-inventory-ru.md` (index, ~25KB) + `tooling-inventory-ru-part-2.md` (~30KB sections 14+) per CLAUDE.md sec 9 pattern |
| `llm-wiki/wiki/project/decisions/0049-sprint-32e-kit-audit-doc-sync.md` | NEW | ADR documenting audit findings + recommendations |
| `llm-wiki/wiki/project/sprints/sprint-32e-kit-audit-doc-sync.md` | NEW | Canonical sprint page |
| `llm-wiki/wiki/index.md` | MODIFY | + sprint-32e + ADR 0049 + kit-audit-2026-04-27 + tooling-inventory-ru-part-2 |
| `llm-wiki/wiki/project/architecture/current-state.md` | MODIFY | counts: 35→36 sprints / 48→49 ADRs + S32e sprint history row + tooling-inventory split note |
| `llm-wiki/CLAUDE.md` | MODIFY | "Banned-from-full-read" section update — `tooling-inventory-ru.md` теперь split, both parts < 50KB |
| `~/.claude/CLAUDE.md` | MODIFY | "Banned-from-full-read" section update mirror |
| `llm-wiki/wiki/log.md` | MODIFY | sprint-end + session-end |
| `llm-wiki/wiki/project/SPRINT_STATE.md` | MODIFY | S32e in_progress → done |

---

## Tasks

### Task T1: Write kit-audit-2026-04-27.md NEW page

**Files:**
- Create: `llm-wiki/wiki/project/architecture/kit-audit-2026-04-27.md`

Content sections:
- Executive summary (audit date / scope / findings count)
- Reviewer agents usage table (11 agents, ACTIVE/DORMANT/READY status + rationale)
- Hooks usage table (8 hooks + 1 session, ALL ACTIVE)
- MCP servers usage table (8 MCP, breakdown ACTIVE/RARE/NOT-USED + recommendations)
- Project skills usage table (5 skills, ACTIVE/DORMANT)
- Plugin skills usage summary (~50 skills, heavily used)
- Doc drift findings (kit-overview stale counts + tooling-inventory size)
- Recommendations (no removals, only doc updates + split)

Commit:
```bash
git add llm-wiki/wiki/project/architecture/kit-audit-2026-04-27.md
git commit -m "docs(audit): T1 — kit-audit-2026-04-27.md NEW (full audit findings: 11 agents + 8 hooks + 8 MCP + 5 project skills + ~50 plugin skills usage analysis)"
```

---

### Task T2: Fix kit-overview-ru.md drift

**Files:**
- Modify: `llm-wiki/wiki/project/architecture/kit-overview-ru.md`

Steps:
1. Edit "Best practices applied" section line 7: "MCP servers — 6 active" → "MCP servers — 8 active"
2. Edit line 10: "Subagents — 9 reviewer agents" → "Subagents — 11 reviewer agents"
3. Add reference к kit-audit page в "Связанные документы" section
4. Verify no other stale counts

Commit:
```bash
git add llm-wiki/wiki/project/architecture/kit-overview-ru.md
git commit -m "docs(kit): T2 — fix kit-overview-ru drift (Best practices section MCP 6→8 / Subagents 9→11) + audit page link"
```

---

### Task T3: Split tooling-inventory-ru.md (60KB → 2 files < 50KB each)

**Files:**
- Modify: `llm-wiki/wiki/project/architecture/tooling-inventory-ru.md` (becomes index + sections 1-13, ~32KB)
- Create: `llm-wiki/wiki/project/architecture/tooling-inventory-ru-part-2.md` (sections 14-24, ~28KB)

**Approach:** Per CLAUDE.md sec 9 split pattern:
- Part 1 (existing file): TL;DR + decision matrix + Sections 1-13 (Domain agents / Project skills / Superpowers / Agent-Skills / Claude-Mem / Caveman / MCP / Hooks / Token economy / Curated rationale / Anti-patterns / Skills × Phase / Cascade rule). Add cross-link к Part 2 в TOC.
- Part 2 (NEW): Sections 14-24 (Permission modes / Plugin curation / CLI tools / Status line / Token-saver / Non-interactive + fan-out / Multi-session / Section 22 corpus scheme / Section 23 schedule wire / Section 24 corpus bridges research) + frontmatter с link обратно к Part 1.

Steps:
1. Read sections 14+ (offset reading чтобы не tripger 60KB)
2. Create part-2 с sections 14-24
3. Truncate part 1 — remove sections 14-24, add "→ part-2" link at TOC
4. Verify both files < 50KB
5. Update wiki/index.md + cross-references в other docs

Commit:
```bash
git add llm-wiki/wiki/project/architecture/tooling-inventory-ru.md \
        llm-wiki/wiki/project/architecture/tooling-inventory-ru-part-2.md
git commit -m "docs(kit): T3 — split tooling-inventory-ru.md (60KB → part 1 32KB + part 2 28KB) per CLAUDE.md sec 9 size threshold"
```

---

### Task T4: Update CLAUDE.md banned-from-full-read lists

**Files:**
- Modify: `llm-wiki/CLAUDE.md` Read tool guard section
- Modify: `~/.claude/CLAUDE.md` section 9 list

Add explicit note: tooling-inventory-ru.md теперь split → both parts < 50KB → safe to Read full без offset/limit. Remove from banned list если present.

Commit:
```bash
git add llm-wiki/CLAUDE.md
git commit -m "docs(claude-md): T4 — update Read tool guard (tooling-inventory split, both parts < 50KB)"
# ~/.claude/CLAUDE.md is out-of-repo — operator manually mirror update
```

---

### Task T5: ADR 0049 + sprint-32e page + index/counts sync

Standard pattern. Counts: 35→36 sprints / 48→49 ADRs / +1 architecture doc (kit-audit-2026-04-27.md) / +1 split file (tooling-inventory-ru-part-2.md).

Commit batch.

---

## Phase 5 Verify

```bash
source .venv/bin/activate
pytest tests/ -q --ignore=tests/integration 2>&1 | tail -3
mypy --strict src/ 2>&1 | tail -3
python -c "from src.execution.state_machine import TRANSITIONS, ExecutionState, ExecutionEvent; from src.risk.reason_codes import ReasonCode; print(f'states={len(list(ExecutionState))}, events={len(list(ExecutionEvent))}, transitions={len(TRANSITIONS)}, reason_codes={len(list(ReasonCode))}')"

# Verify file sizes after split
ls -la llm-wiki/wiki/project/architecture/tooling-inventory-ru*.md
# Both should be < 50KB (51200 bytes)
```

---

## Phase 6 Review — skipped (no src/ touched)

---

## Phase 7 Sync

log.md sprint-end entry.

---

## Phase 8 Ship

Standard ship checklist. CI 4th PR validation.

---

## Phase 9 Close

SPRINT_STATE → between-sprints. Update Следующее действие → S33 trading work + audit findings reference.

---

## Self-Review

**Spec coverage:**
- ✓ T1 audit page NEW
- ✓ T2 kit-overview drift fix
- ✓ T3 tooling-inventory split (60KB → 2 files)
- ✓ T4 CLAUDE.md Read guard update
- ✓ T5 ADR + sprint page + sync

**Honest finding:** No removals proposed — все 11 agents + 8 hooks + 8 MCP + 5 skills NEEDED. computer-use + Claude_in_Chrome не active в trading но harmless overhead. Document "ready" status для new agents (S30+S32b+S32d) without removing.

**No placeholders:** все steps concrete.

---

## Related

- ADR 0048 (S32d Kit Phase 3 final) — direct predecessor
- ADR 0017 (review-agent harness) — L5 agent matrix policy
- ADR 0044 (S31 best practices) — kit baseline
- Sprint S32 series (Phase 0/1/2/3) — kit improvement source
- CLAUDE.md sec 9 — Read tool guard 50KB threshold (triggers split)
