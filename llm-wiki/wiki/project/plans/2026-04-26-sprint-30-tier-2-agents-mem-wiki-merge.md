# Sprint 30 — Tier-2 Agents + LLMWiki↔Claude-mem Integration

> **For agentic workers:** REQUIRED SUB-SKILL: `superpowers:executing-plans` (controller-driven, docs-heavy).

**Goal:** (1) Add 3 tier-2 reviewer agents (security-auditor / test-engineer / doc-reviewer) к L5 stack. (2) Implement phase-advance.sh hook (Phase 5 verification enforcement). (3) Design + document llmwiki ↔ claude-mem integration (token economy + context delivery cascade).

**Architecture:**
- 3 NEW agent prompts в `~/.claude/agents/` per ADR 0017 pattern (Path discipline + Sprint context priming TIER A + memory: project)
- Hook `~/.claude/hooks/phase-advance.sh` — pre-merge check verifying SPRINT_STATE Phase 5 verification done
- Documentation-first wiki+mem integration: cascade rule (wiki → mem → raw), skill `mem-search-wiki-first`, ADR 0043

**Tech Stack:** Markdown agents, Bash hook, wiki updates. NO src/ code changes.

---

## Context

S29 ship landed full superpowers integration (13/13). Operator next directives:

> "S30 scope (если operator agrees):
> - Register security-auditor + test-engineer plugins в L5 stack
> - Update tooling-inventory-ru.md Section 1 (8 agents instead of 6)
> - Update sprint-flow-ru.md Phase 6 reviewer matrix
> - Hook добавить — phase-advance.sh validating verification-before-completion checklist runs перед merge
> - А также добавить doc-reviewer (haiku)"

> "Проанализируй как можно смержить функционал llmwiki и её потенциал с плагином claude mem, т.к. они оба призваны чтобы обеспечить экономию токенов и передачи тебе полноты контекста самым оптимальным путём. Если их адаптировать в наш flow то будет лучшее решение."

### Current state

- 6 reviewer agents (trader-expert / trading-logic / quant-stats / data-integrity / python / architecture)
- 5 hooks (adr-agent-sync / adr-index-sync / sprint-flow-check / wiki-broken-link / caveman-*)
- Wiki + mem-search separate — no formal cascade

### Gap analysis

**Tier-2 agents:**
| Agent | Current gap | Filled by |
|-------|-------------|-----------|
| security-auditor | Money/API key/override changes — only `agent-skills:security-and-hardening` checklist (no actual analysis agent). S5+ live trading approaches → security risk | NEW agent (opus, opt-in для money paths) |
| test-engineer | New modules без tests / coverage gaps. S27 audit revealed 4 formula bugs survived 25 sprints — better test design might've caught earlier | NEW agent (sonnet) |
| doc-reviewer | wiki-update skill + wiki-broken-link hook покрывают 80%. Marginal value, но operator requested | NEW agent (haiku, lightweight) |

**Phase 5 enforcement:**
- Currently: controller manually runs pytest/mypy. No hook enforces `superpowers:verification-before-completion` checklist
- Risk: Phase 5 skipped → unverified code shipped
- Fix: `phase-advance.sh` hook checks SPRINT_STATE Phase 5 status before merge

**Wiki ↔ Mem cascade:**
- llmwiki = structured wiki/ (curated, frontmatter-tagged, cross-linked)
- claude-mem = MCP semantic search past sessions (raw observations)
- Currently: independent — controller picks one OR другой
- Optimal: cascade order saves tokens + improves accuracy

---

## File Structure

NEW files:
- `~/.claude/agents/security-auditor.md` — agent prompt
- `~/.claude/agents/test-engineer.md` — agent prompt
- `~/.claude/agents/doc-reviewer.md` — agent prompt
- `~/.claude/hooks/phase-advance.sh` — Phase 5 enforcement hook
- `llm-wiki/wiki/project/decisions/0043-sprint-30-tier-2-agents-mem-wiki-merge.md` — ADR
- `llm-wiki/wiki/project/sprints/sprint-30-tier-2-agents-mem-wiki-merge.md` — sprint page
- `llm-wiki/wiki/project/plans/2026-04-26-sprint-30-tier-2-agents-mem-wiki-merge.md` — этот plan

MODIFY:
- `llm-wiki/wiki/project/architecture/tooling-inventory-ru.md` — Section 1 (9 agents) + Section 8 (new hook) + NEW Section 13 wiki↔mem cascade
- `llm-wiki/wiki/project/architecture/sprint-flow-ru.md` — Phase 6 expanded matrix + token economy cascade
- `CLAUDE.md` (repo root) — phase table добавить tier-2 agents + cascade rule
- `llm-wiki/CLAUDE.md` — wiki-first cascade documented
- `llm-wiki/wiki/index.md` — entries для S30 + ADR 0043 + new agent docs
- `llm-wiki/wiki/project/architecture/current-state.md` — sprint history row +S30 + counts
- `llm-wiki/wiki/log.md` — sprint-end entry
- `llm-wiki/wiki/project/SPRINT_STATE.md` — phase tracking template

---

## LLMWiki ↔ Claude-mem Integration Design (T5)

### Problem

Two systems target token economy + context delivery:
- **llmwiki** — structured curated wiki (frontmatter + cross-links + sources tracking). Read order: components → decisions → raw ADR. 4-7× compression vs raw files.
- **claude-mem** — semantic search past sessions (mem-search returns relevant observations). "Did we solve X?" в seconds.

Currently independent. Controller picks one:
- "Did we solve X?" → mem-search
- "What does component Y do?" → wiki/components/Y.md
- Overlap: prior decisions могут быть и в wiki/decisions/ AND в mem corpus

### Design: Cascade order rule (token-optimal)

```
Query → check sequence:
  1. wiki/index.md → wiki/<page>.md (curated structured, tagged)
     ↓ if not found
  2. mem-search smart_search "<query>" (past session observations)
     ↓ if not found
  3. Grep raw src/ + docs/ (fallback)
     ↓ if needed
  4. Read raw file с offset+limit
```

**Rationale:**
- Step 1 (wiki) = highest semantic density per token (curated)
- Step 2 (mem) = past learnings + decisions (compressed)
- Step 3 (Grep) = current code state
- Step 4 (Read) = full content

### Practical bridges

**Bridge 1 — `mem-search-wiki-first` skill (NEW project skill):**
- Wraps cascade rule
- Auto-invoked on "did we / did X happen / where is" queries
- Output: wiki ref + mem observations + suggested next action

**Bridge 2 — wiki-mem-corpus-sync (DEFERRED к S31):**
- Periodic indexing of wiki/ → claude-mem corpus (wiki pages indexed как observations)
- Future: queries hit single corpus, both wiki + sessions
- Defer: requires claude-mem API investigation

**Bridge 3 — chapter mark auto-link к log.md (DEFERRED к S31):**
- `mcp__ccd_session__mark_chapter` could write entry в `wiki/log.md`
- Removes manual append step
- Defer: requires hook integration

**Bridge 4 — frontmatter tags → mem corpus categorization (DEFERRED к S31):**
- wiki frontmatter (type/tags/sources) feed mem corpus filtering
- Defer: requires claude-mem corpus schema understanding

### S30 deliverable scope

- T5a: ADR 0043 design (cascade rule + 4 bridges)
- T5b: Document cascade в `tooling-inventory-ru.md` Section 13 NEW
- T5c: Update CLAUDE.md token economy section с cascade rule
- T5d: DEFER bridges 2-4 implementation к S31 (mark в open issues)

NO new skill creation в S30 (wait для bridge implementation S31). Cascade rule = documentation enforcement.

---

## Task Breakdown

### Task 1: security-auditor agent

**Files:**
- Create: `~/.claude/agents/security-auditor.md`

- [ ] **Step 1:** Write agent prompt с frontmatter:
  - name: security-auditor
  - description: Security engineer focused on vulnerability detection, threat modeling, secure coding (OWASP, API keys, signing, override paths). Use для money/API/override changes
  - tools: Read, Grep, Glob, Bash (no Write/Edit)
  - model: opus (effort: max)
  - memory: project

- [ ] **Step 2:** Body — Path discipline + Sprint context priming + scope:
  - Vulnerability classes (OWASP 10, secrets in code, signing)
  - Trading-specific risks (API key exposure, override.py bypass, withdraw whitelist)
  - Output format (BLOCKER / HIGH / MEDIUM / LOW + rationale + fix recommendation)

- [ ] **Step 3:** Commit (out-of-repo)

### Task 2: test-engineer agent

**Files:**
- Create: `~/.claude/agents/test-engineer.md`

- [ ] **Step 1:** Frontmatter:
  - description: QA engineer specialized в test strategy, test writing, coverage analysis
  - tools: Read, Grep, Glob, Bash, Write, Edit (write tests)
  - model: sonnet
  - memory: project

- [ ] **Step 2:** Body — Path discipline + Sprint context priming + scope:
  - Test pyramid (unit / integration / property / E2E)
  - Hypothesis property tests для DSR/Kelly/MC math invariants
  - Coverage analysis (pytest-cov)
  - Test design quality (DAMP, anti-patterns)

- [ ] **Step 3:** Commit

### Task 3: doc-reviewer agent

**Files:**
- Create: `~/.claude/agents/doc-reviewer.md`

- [ ] **Step 1:** Frontmatter:
  - description: Wiki consistency + Block 1↔Block 2 sync + link integrity
  - tools: Read, Grep, Glob (read-only)
  - model: haiku
  - memory: project

- [ ] **Step 2:** Body — scope:
  - Wiki frontmatter validation (required fields)
  - Block 1 (sources/Public API anchors) ↔ Block 2 (description/settings) sync
  - Link integrity (`[[wiki-link]]` resolves к existing file)
  - Canonical counts consistency (current-state.md vs реальные counts)

- [ ] **Step 3:** Commit

### Task 4: phase-advance.sh hook

**Files:**
- Create: `~/.claude/hooks/phase-advance.sh`

- [ ] **Step 1:** Write hook (PreToolUse Bash matcher на `gh pr merge`):
  - Read SPRINT_STATE.md
  - Check Phase 5 status = "done" (parse table)
  - If not done → exit 2 (block) с error
  - If done → exit 0 (pass)

- [ ] **Step 2:** chmod +x + bash -n syntax check

- [ ] **Step 3:** Register в settings.json PreToolUse Bash matcher

- [ ] **Step 4:** Test positive (Phase 5 done → pass) + negative (Phase 5 pending → block)

- [ ] **Step 5:** Document в tooling-inventory-ru.md Section 8 hooks

### Task 5: LLMWiki ↔ Claude-mem integration design

**Files:**
- Update: `llm-wiki/wiki/project/architecture/tooling-inventory-ru.md` (NEW Section 13)
- Update: `CLAUDE.md` (token economy cascade rule)

- [ ] **Step 1:** Add Section 13 в tooling-inventory-ru.md "Wiki ↔ Mem cascade":
  - Cascade order (wiki → mem → grep → raw)
  - Per-step token cost comparison
  - Example queries

- [ ] **Step 2:** Update CLAUDE.md token economy section с cascade rule

- [ ] **Step 3:** Add к anti-patterns "Skip wiki check, jump straight к mem-search OR Read raw"

### Task 6: tooling-inventory-ru.md update

**Files:**
- Modify: `llm-wiki/wiki/project/architecture/tooling-inventory-ru.md`

- [ ] **Step 1:** Section 1 expanded (6 → 9 agents) — add security-auditor / test-engineer / doc-reviewer

- [ ] **Step 2:** Section 8 hooks — add phase-advance.sh

- [ ] **Step 3:** TL;DR decision matrix — add new entries:
  - Money/API/override changes → security-auditor
  - New module без tests → test-engineer
  - Wiki consistency check → doc-reviewer
  - Pre-merge Phase 5 verify → phase-advance.sh hook fires

### Task 7: sprint-flow-ru.md Phase 6 reviewer matrix expanded

**Files:**
- Modify: `llm-wiki/wiki/project/architecture/sprint-flow-ru.md`

- [ ] **Step 1:** Phase 6 reviewer matrix:
  - + security-auditor (money/API/override paths)
  - + test-engineer (new modules / coverage gaps / property test design)
  - + doc-reviewer (wiki sync verification — runs after wiki-update skill)

- [ ] **Step 2:** Phase 8 + Phase 5 — note phase-advance.sh hook enforcement

- [ ] **Step 3:** Skills × Phase integration map (Section 12 в tooling) updated с 9 agents + new hook

### Task 8: CLAUDE.md update

**Files:**
- Modify: `CLAUDE.md` (repo root)

- [ ] **Step 1:** Phase 6 row — добавить tier-2 reviewers
- [ ] **Step 2:** Phase 5 row — note phase-advance.sh hook block
- [ ] **Step 3:** Token economy section — wiki+mem cascade rule

### Task 9: ADR 0043 + sprint-30 page + wiki sync

**Files:**
- Create: `llm-wiki/wiki/project/decisions/0043-sprint-30-tier-2-agents-mem-wiki-merge.md`
- Create: `llm-wiki/wiki/project/sprints/sprint-30-tier-2-agents-mem-wiki-merge.md`
- Modify: `llm-wiki/wiki/index.md`, `current-state.md`, `log.md`

- [ ] **Step 1:** ADR с decision (3 agents + hook + cascade design + 3 bridges deferred)
- [ ] **Step 2:** Sprint page
- [ ] **Step 3:** index + current-state + log
- [ ] **Step 4:** Commit

### Task 10: PHASE 5-8 ship

- [ ] **Step 1:** PHASE 5 verify pytest baseline (no code changes)
- [ ] **Step 2:** Touch agent prompts (ADR sync hook compliance)
- [ ] **Step 3:** Push branch (test phase-advance.sh hook fires correctly)
- [ ] **Step 4:** PR + merge + tag v0.1.0-alpha.30
- [ ] **Step 5:** SPRINT_STATE → between-sprints

---

## Self-Review Checklist

- [x] All 3 new agents have Path discipline + Sprint context priming
- [x] Hook bash syntax check planned
- [x] Cascade rule documented но bridges 2-4 explicitly deferred (no scope creep)
- [x] No code changes (process/wiki only)
- [x] Backward compat (existing 6 agents preserved)

## Execution mode

Controller-driven (docs/agents/wiki). 9 task commits + 1 ship.
