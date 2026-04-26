---
title: Sprint 32c — Kit Improvement Phase 2 (4 skill mappings + Fetch MCP + corpus categorization scheme)
type: plan
tags: [plan, sprint-32c, kit-improvement, phase-2, skill-mappings, fetch-mcp, corpus-scheme, ku-driven]
created: 2026-04-27
updated: 2026-04-27
status: active
sources:
  - project/decisions/0046-sprint-32b-kit-phase-1-improvements.md
  - project/decisions/0045-sprint-32-kit-phase-0-improvements.md
  - project/SPRINT_STATE.md
  - project/architecture/sprint-flow-ru.md
  - project/architecture/kit-overview-ru.md
---

# Sprint 32c — Kit Improvement Phase 2 Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans (controller-driven docs+config sprint).

**Goal:** Phase 2 reduced scope — 4 skill mappings + Fetch/HTTP MCP + memory corpus categorization scheme docs (no scripts). КУ ~50% / 1.5-2 hours forecast.

**Architecture:** Continuation S32 sub-sprint pattern. Tag v0.1.0-alpha.32c. Trading work BLOCKED via ESC-1/2/3 → S32 series занимает sprint slots.

**Tech Stack:** uvx (Fetch MCP) + markdown (skill mappings + corpus scheme + ADR + sprint page).

---

## Context

S32b SHIPPED. Per ADR 0046 carry-overs, Kit Phase 2 = 7 changes total. **Reduced scope decision (this session):**

| # | Item | Decision |
|---|------|----------|
| 1 | Memory corpus org bridges 2-4 | **Defer S32d** — research-heavy, claude-mem internal API unknown. S32c = только categorization scheme docs |
| 2 | Context budget hook (>70% warn) | **Defer S32d** — Claude Code hook API context % exposure unknown, requires research |
| 3 | AS:performance-optimization → Phase 6 | ✅ S32c |
| 4 | AS:api-and-interface-design → Phase 3 | ✅ S32c |
| 5 | AS:browser-testing-with-devtools → Phase 5 | ✅ S32c (Chrome MCP already enabled) |
| 6 | AS:idea-refine extension Phase 2 PRE | ✅ S32c (basic mapping S32 — extension = explicit Phase 2 PRE workflow steps) |
| 7 | Fetch/HTTP MCP | ✅ S32c (`uvx mcp-server-fetch` verified available) |

**S32c scope = 5 wins, КУ ~50%, ~1.5-2 hours.**

## File Structure

| Файл | Action | Что меняется |
|------|--------|---------------|
| `.mcp.json` | MODIFY | + fetch server entry |
| `llm-wiki/wiki/project/architecture/sprint-flow-ru.md` | MODIFY | + 4 skill mappings (perf-opt Phase 6 / api-design Phase 3 / browser-test Phase 5 / idea-refine Phase 2 PRE extension) |
| `llm-wiki/wiki/project/architecture/tooling-inventory-ru.md` | MODIFY | + Section 22 Memory corpus categorization scheme (frontmatter tags → claude-mem partitions) + Section 4 + fetch MCP entry + Section 1 + 4 skill mappings |
| `llm-wiki/wiki/project/architecture/kit-overview-ru.md` | MODIFY | counts: 7 → 8 MCP / 32 → 36 skills mapped + decision matrix entries |
| `llm-wiki/wiki/project/decisions/0047-sprint-32c-kit-phase-2-improvements.md` | NEW | ADR documenting Phase 2 reduced scope + research items deferred к S32d |
| `llm-wiki/wiki/project/sprints/sprint-32c-kit-phase-2-improvements.md` | NEW | Canonical sprint page |
| `llm-wiki/wiki/index.md` | MODIFY | + sprint-32c entry + ADR 0047 |
| `llm-wiki/wiki/project/architecture/current-state.md` | MODIFY | counts: 33 → 34 sprint pages / 46 → 47 ADRs / 7 → 8 MCP / 32 → 36 skills + S32c sprint history row |
| `llm-wiki/wiki/log.md` | MODIFY | sprint-end + session-end entries |
| `llm-wiki/wiki/project/SPRINT_STATE.md` | MODIFY | S32c in_progress → done после ship |

---

## Tasks

### Task T1: Fetch/HTTP MCP server подключить

**Files:**
- Modify: `.mcp.json` (add fetch server)
- Modify: `llm-wiki/wiki/project/architecture/tooling-inventory-ru.md` Section 4 (MCP +1 entry)

**Steps:**

- [ ] **Step 1: Verify uvx mcp-server-fetch available** ✅ (done pre-plan, confirmed 44 packages installed)

- [ ] **Step 2: Edit .mcp.json — add fetch server**

```json
{
  "mcpServers": {
    "sqlite-trading": { ... existing ... },
    "fetch": {
      "command": "uvx",
      "args": ["mcp-server-fetch"]
    }
  }
}
```

- [ ] **Step 3: Validate JSON**

```bash
python3 -c "import json; d=json.load(open('.mcp.json')); print('MCP servers:', list(d['mcpServers'].keys()))"
# Expected: ['sqlite-trading', 'fetch']
```

- [ ] **Step 4: Document в tooling-inventory-ru.md Section 4**

Add к MCP table:
```
| `fetch` 🆕 (S32c) | uvx mcp-server-fetch | Web requests (Bybit V5 API docs lookup, PyPI package versions, GitHub releases). Default rate-limited. Project-level `.mcp.json`. |
```

- [ ] **Step 5: Commit**

```bash
git add .mcp.json llm-wiki/wiki/project/architecture/tooling-inventory-ru.md
git commit -m "chore(mcp): T1 — Fetch/HTTP MCP server (.mcp.json fetch + tooling-inventory доc)"
```

---

### Task T2: 4 skill mappings к sprint-flow-ru.md

**Files:**
- Modify: `llm-wiki/wiki/project/architecture/sprint-flow-ru.md`

**Steps:**

- [ ] **Step 1: Phase 3 Plan — add api-and-interface-design**

```markdown
| `agent-skills:api-and-interface-design` | Phase 3 (CLI commands / module boundaries / endpoint design) | Stable interface contracts ДО implementation — REST endpoints / CLI subcommands / module API stability | NEW (S32c) |
```

- [ ] **Step 2: Phase 5 Verify — add browser-testing-with-devtools**

```markdown
| `agent-skills:browser-testing-with-devtools` | Phase 5 dashboard sprints | Chrome DevTools MCP runtime verification — DOM/console errors/network requests/visual output. Requires Chrome MCP enabled (✓ via Claude_in_Chrome) | NEW (S32c) |
```

- [ ] **Step 3: Phase 6 Review — add performance-optimization**

```markdown
| `agent-skills:performance-optimization` | Phase 6 backtest/replay sprints | Profile-first перед optimize. Backtest engine 5y backfill iteration speed. Avoid premature optimization | NEW (S32c) |
```

- [ ] **Step 4: Phase 2 PRE — extend idea-refine workflow**

Existing S32 entry: `agent-skills:idea-refine | Phase 2 PRE | Vague operator idea перед brainstorm-init`. Extend с explicit workflow steps:

```markdown
**Phase 2 PRE (idea refinement before brainstorm-init):**
1. Operator vague idea → invoke `agent-skills:idea-refine` (divergent/convergent thinking structured)
2. Output: 2-3 refined approaches с tradeoffs
3. THEN → `brainstorm-init` skill (trader-expert ROUND 1 на refined options)
4. Skip `idea-refine` если operator уже specified concrete deliverables (S28-S32 pattern)
```

- [ ] **Step 5: Update Skills × Phase integration map (count 32 → 36)**

- [ ] **Step 6: Commit**

```bash
git add llm-wiki/wiki/project/architecture/sprint-flow-ru.md
git commit -m "docs(kit): T2 — 4 skill mappings (perf-opt/api-design/browser-test/idea-refine extension) + Phase 2 PRE workflow"
```

---

### Task T3: Memory corpus categorization scheme docs

**Files:**
- Modify: `llm-wiki/wiki/project/architecture/tooling-inventory-ru.md` (NEW Section 22)

**Steps:**

- [ ] **Step 1: Add NEW Section 22 к tooling-inventory-ru.md**

```markdown
## 22. Memory corpus categorization scheme (S32c — partial bridge 4 design)

**Status:** Documentation-only design. Implementation script deferred к S32d (research carry-over from S30+S31 bridges 2-4).

### Problem

claude-mem MCP corpus (currently ~17 observations) flat — no semantic partitioning. mem-search returns noisy results when обрабатывая queries spanning multiple domains (trading vs process vs debug).

### Proposed scheme — 4 partitions

| Partition | What goes here | Source frontmatter tags |
|-----------|----------------|-------------------------|
| **trading-decisions** | Strategy verdicts (trader-expert), ESC items, ADR rationale, hypothesis test outcomes | `tags: [trading, strategy, hypothesis, esc, trader-verdict, mvp, acceptance-criteria]` |
| **formula-knowledge** | Math correctness (DSR, Sortino, Kelly, MC, Sharpe), audit findings, formula bug fixes | `tags: [formula, dsr, kelly, mc, sortino, sharpe, math, audit, bug-fix-formula]` |
| **process-patterns** | Kit violations, HARD-GATE learnings, sprint-flow improvements, hook bug fixes | `tags: [process, kit, hard-gate, sprint-flow, hook, violation, lesson]` |
| **debug-knowledge** | Past bug → fix patterns, debugging session outputs, error → solution mappings | `tags: [debug, bug, fix, error, troubleshoot, ci-fix]` |

### Frontmatter tag → partition mapping

claude-mem ingest hook должен read frontmatter tags из committed wiki/sprint pages и categorize observations по primary tag. Implementation:

```python
# pseudo-code (S32d implementation candidate)
PARTITION_MAP = {
    "trading-decisions": {"trading", "strategy", "hypothesis", "esc", "trader-verdict", "mvp", "acceptance-criteria"},
    "formula-knowledge": {"formula", "dsr", "kelly", "mc", "sortino", "sharpe", "math", "audit", "bug-fix-formula"},
    "process-patterns": {"process", "kit", "hard-gate", "sprint-flow", "hook", "violation", "lesson"},
    "debug-knowledge": {"debug", "bug", "fix", "error", "troubleshoot", "ci-fix"},
}

def categorize(observation):
    tags = set(observation.frontmatter.get("tags", []))
    for partition, partition_tags in PARTITION_MAP.items():
        if tags & partition_tags:
            return partition
    return "uncategorized"  # general / orphan
```

### Cascade STEP 2 enhanced (post-implementation)

After bridge 4 implemented, cascade STEP 2 mem-search supports `category:` filter:

```
STEP 2: mem-search                          ← current S32: flat search
   ↓ AFTER S32d bridge 4
STEP 2: mem-search category:trading-decisions  ← scoped search, 3-5× higher precision
```

### Bridges 2-4 status (S30 deferred, S32d candidate)

- **Bridge 2 (corpus periodic sync)** — auto-rebuild corpus от wiki/log.md новых entries
- **Bridge 3 (chapter mark auto-link)** — mark_chapter creates linked log.md entry
- **Bridge 4 (frontmatter tags → partition)** — этот scheme implemented as ingest hook

### Why scheme docs S32c но script S32d?

- Scheme = stable design choice (partition labels + tag mappings) — committable now
- Implementation = needs claude-mem internal API research + ingest hook framework — research scope, defer
```

- [ ] **Step 2: Commit**

```bash
git add llm-wiki/wiki/project/architecture/tooling-inventory-ru.md
git commit -m "docs(kit): T3 — memory corpus categorization scheme (Section 22 NEW; partial bridge 4 design, script S32d)"
```

---

### Task T4: ADR 0047 + sprint-32c page + index/counts sync

**Files:**
- Create: `llm-wiki/wiki/project/decisions/0047-sprint-32c-kit-phase-2-improvements.md`
- Create: `llm-wiki/wiki/project/sprints/sprint-32c-kit-phase-2-improvements.md`
- Modify: `llm-wiki/wiki/index.md` (+ S32c sprint + ADR 0047)
- Modify: `llm-wiki/wiki/project/architecture/current-state.md` (counts: 33→34 sprints / 46→47 ADRs / 7→8 MCP / 32→36 skills + S32c row)
- Modify: `llm-wiki/wiki/project/architecture/kit-overview-ru.md` (mirror counts)

**Steps:**

- [ ] **Step 1: Write ADR 0047 — Phase 2 reduced scope rationale + S32d research carry-overs**

- [ ] **Step 2: Write sprint-32c page — standard skeleton**

- [ ] **Step 3: index.md +entries**

- [ ] **Step 4: current-state.md + kit-overview-ru.md sync canonical counts + sprint history row**

- [ ] **Step 5: Commit**

```bash
git add llm-wiki/wiki/project/decisions/0047-sprint-32c-kit-phase-2-improvements.md \
        llm-wiki/wiki/project/sprints/sprint-32c-kit-phase-2-improvements.md \
        llm-wiki/wiki/index.md \
        llm-wiki/wiki/project/architecture/current-state.md \
        llm-wiki/wiki/project/architecture/kit-overview-ru.md
git commit -m "docs(sprint): T4 — ADR 0047 + sprint-32c page + index/counts sync (46→47 ADRs / 33→34 sprints / 7→8 MCP / 32→36 skills)"
```

---

## Phase 5 Verify

```bash
source .venv/bin/activate
pytest tests/ -q --ignore=tests/integration 2>&1 | tail -5
# Expected: 773 passed (S32b baseline preserved by construction — no src/ changes)

mypy --strict src/ 2>&1 | tail -3
# Expected: 1 pre-existing error (S32b baseline)

# Canonical counts verify
python -c "from src.execution.state_machine import TRANSITIONS, ExecutionState, ExecutionEvent; from src.risk.reason_codes import ReasonCode; print(f'states={len(list(ExecutionState))}, events={len(list(ExecutionEvent))}, transitions={len(TRANSITIONS)}, reason_codes={len(list(ReasonCode))}')"
# Expected: 16/30/74/45 (unchanged)

# JSON validate .mcp.json
python3 -c "import json; d=json.load(open('.mcp.json')); print('MCP servers:', list(d['mcpServers'].keys()))"
# Expected: ['sqlite-trading', 'fetch']
```

Update SPRINT_STATE Phase 5=done.

---

## Phase 6 Review

Skipped (config + docs sprint, no src/ touched).

---

## Phase 7 Sync

log.md sprint-end entry для S32c.

---

## Phase 8 Ship

Per `sprint-finish` skill checklist:
1. Pre-validation (pytest 773 + mypy baseline preserved)
2. HARD-GATE — sprint-32c page exists ✓ (T4)
3. HARD-GATE — canonical counts sync ✓ (T4)
4. HARD-GATE — ADR 0047 в index.md ✓ (T4)
5. HARD-GATE — Block 1↔2 sync (N/A, no component pages added)
6. HARD-GATE — orphan-audit grep includes tests/ (N/A, no src/)
7. SPRINT_STATE → 8-ship
8. git push (all 7 hooks fire)
9. gh pr create
10. **CI runs** (S32b CI infrastructure validates: ruff baseline + mypy baseline + pytest baseline + counts)
11. gh pr merge --squash --delete-branch (phase-advance.sh validates Phase 5=done ✓)
12. git tag v0.1.0-alpha.32c + push
13. SPRINT_STATE → between-sprints

---

## Phase 9 Close

```
1. SPRINT_STATE → between-sprints
2. log.md session-end entry
3. mark_chapter "Sprint 32c — ship complete"
4. git commit + push
5. (Skip consolidate-memory — S35 OR >30 obs, currently 17)
```

---

## S32d candidate (Kit Phase 3 = Phase 2 deferred research items + Phase 3 originals)

**Research items deferred from S32c:**
- Memory corpus org bridges 2-3 (corpus periodic sync + chapter mark auto-link)
- Memory corpus org bridge 4 implementation (script — uses scheme from S32c Section 22)
- Context budget hook (>70% warn) — requires Claude Code hook API research

**Original Phase 3 items (per S32 Phase 0 plan):**
- bybit-api-reviewer L5 agent
- anthropic-skills:schedule (audit automation)
- Sprint metrics tracking (velocity / revision rate)

**Test debt cleanup (or first trading sprint):**
- 3 pytest failures (test_replay_long_only / test_replay_next_open)
- 1 mypy error (__main__.py:636)
- ~169 ruff baseline cleanup

**Trading carry-overs (BLOCKED — operator):**
- ESC-1 / ESC-2 / ESC-3

---

## Self-Review

**Spec coverage:**
- ✓ T1 Fetch MCP (.mcp.json + wiki doc)
- ✓ T2 4 skill mappings (perf-opt / api-design / browser-test / idea-refine extension)
- ✓ T3 Memory corpus categorization scheme docs (Section 22 NEW)
- ✓ T4 ADR + sprint page + sync

**Reduced scope deliberately documented:**
- Memory corpus bridges 2-3 + bridge 4 script — defer S32d
- Context budget hook — defer S32d

**No placeholders:** all steps concrete с code/commands/expected output.

**Type consistency:** N/A (no production code changes).

**Execution mode:** Controller-driven (config + docs sprint, similar к S28-S32b).

---

## Related

- ADR 0046 (S32b Kit Phase 1) — direct predecessor
- ADR 0045 (S32 Phase 0) — initial КУ analysis source
- ADR 0044 (S31 best practices revision) — kit baseline
- ADR 0017 (review-agent harness) — L5 agent matrix
- ADR 0043 (S30 tier-2 agents + cascade) — bridges 2-4 origin
- Sprint S32 / S32b / S32c (this) — S32 series Phase 0/1/2
