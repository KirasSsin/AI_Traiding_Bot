---
title: Sprint 32d — Kit Improvement Phase 3 (bybit-api-reviewer + context budget hook + schedule wire + sprint metrics + corpus research notes)
type: plan
tags: [plan, sprint-32d, kit-improvement, phase-3, bybit-reviewer, context-hook, sprint-metrics, corpus-research]
created: 2026-04-27
updated: 2026-04-27
status: active
sources:
  - project/decisions/0047-sprint-32c-kit-phase-2-improvements.md
  - project/decisions/0046-sprint-32b-kit-phase-1-improvements.md
  - project/decisions/0045-sprint-32-kit-phase-0-improvements.md
  - project/SPRINT_STATE.md
---

# Sprint 32d — Kit Improvement Phase 3 Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans (controller-driven docs+config+scripts sprint).

**Goal:** Final S32 series kit sprint. 5 changes + memory corpus research notes. КУ ~45% / 2.5-3 hours forecast. After S32d ship → S33 trading sprint preparation.

**Architecture:** Sub-sprint S32 series final. Tag v0.1.0-alpha.32d. Operator directive: "к 33 спринту после 32 перейдём" — S32d closes kit improvement series.

**Tech Stack:** markdown (agent prompt + sprint metrics page + research notes) + bash (context budget hook MVP) + .mcp.json (schedule wire docs).

---

## Context

S32+S32b+S32c shipped. Kit infrastructure mature: 10 reviewer agents + 7 push hooks + 8 MCP + 36 skills + CI + pre-commit + corpus scheme designed. Per ADR 0047 carry-overs, S32d = last kit Phase = research items + Phase 3 originals.

**Pre-plan honest scope assessment:**

| # | Item | Decision |
|---|------|----------|
| Memory corpus bridges 2-4 implementation | **Research notes only** — claude-mem internal API unknown, plugin not maintained by us, would need fork/PR. Document feasibility, не implement. |
| Context budget hook MVP | ✅ S32d (transcript file size warning, crude но useful) |
| bybit-api-reviewer L5 agent | ✅ S32d (standalone .md, dashboard-reviewer pattern) |
| anthropic-skills:schedule wire | ✅ S32d (docs only — schedule MCP exists, document wire к audit_formulas.py) |
| Sprint metrics tracking | ✅ S32d (wiki page template + manual update protocol) |
| ADR 0048 + sprint-32d page + sync | ✅ S32d |

**КУ avg ~45% / 2.5-3 hours.** Final S32 series sprint.

## File Structure

| Файл | Action | Что меняется |
|------|--------|---------------|
| `~/.claude/agents/bybit-api-reviewer.md` | NEW (out-of-repo) | L5 reviewer specialized для Bybit V5 API correctness |
| `llm-wiki/wiki/project/components/bybit-api-reviewer-agent.md` | NEW (in-repo) | Wiki page для bybit-api-reviewer |
| `~/.claude/hooks/context-budget-warn.sh` | NEW (out-of-repo) | Bash hook UserPromptSubmit — warn если transcript > N MB |
| `~/.claude/settings.json` | MODIFY (out-of-repo) | Register UserPromptSubmit hook |
| `llm-wiki/wiki/project/components/context-budget-hook.md` | NEW (in-repo) | Wiki page для context budget hook |
| `llm-wiki/wiki/project/sprint-metrics.md` | NEW (in-repo) | Sprint metrics tracking page (velocity / revision rate / KU per sprint) |
| `llm-wiki/wiki/project/architecture/tooling-inventory-ru.md` | MODIFY | + Section 23 anthropic-skills:schedule wire к audit_formulas.py + Section 24 Memory corpus research notes (feasibility) + Section 7.5 update (schedule wire) + Section 1 + bybit-api-reviewer + Section 8 + context-budget-warn.sh |
| `llm-wiki/wiki/project/architecture/kit-overview-ru.md` | MODIFY | counts: 10 → 11 reviewer agents / 7 → 8 active push hooks (UserPromptSubmit hook NEW) |
| `llm-wiki/wiki/project/decisions/0048-sprint-32d-kit-phase-3-improvements.md` | NEW | ADR documenting Phase 3 implementation + research notes scope |
| `llm-wiki/wiki/project/sprints/sprint-32d-kit-phase-3-improvements.md` | NEW | Canonical sprint page |
| `llm-wiki/wiki/index.md` | MODIFY | + sprint-32d entry + ADR 0048 + 3 component pages |
| `llm-wiki/wiki/project/architecture/current-state.md` | MODIFY | counts: 34 → 35 sprint pages / 47 → 48 ADRs / 40 → 43 components / 10 → 11 agents / 7 push hooks unchanged + 1 UserPromptSubmit / + sprint metrics page |
| `llm-wiki/wiki/log.md` | MODIFY | sprint-end + session-end entries |
| `llm-wiki/wiki/project/SPRINT_STATE.md` | MODIFY | S32d in_progress → done после ship + S33 trading prep section |

---

## Tasks

### Task T1: bybit-api-reviewer L5 agent

**Files:**
- Create: `~/.claude/agents/bybit-api-reviewer.md` (out-of-repo)
- Create: `llm-wiki/wiki/project/components/bybit-api-reviewer-agent.md` (in-repo)

**Steps:**

- [ ] **Step 1: Write agent prompt** — specialized для Bybit V5 API correctness:
  - Rate limits (600 req/min spot, 60/sec for orders)
  - Order parameter validation (qty precision, price tick, time-in-force)
  - WebSocket message schema (topic/data structure)
  - Error code handling (`10001`/`10002`/`110001`/`170131` etc.)
  - Pagination patterns (cursor / klines paginated)
  - Authentication signature correctness (HMAC SHA256)

- [ ] **Step 2: Verify agent loads**
```bash
ls -la ~/.claude/agents/bybit-api-reviewer.md
head -10 ~/.claude/agents/bybit-api-reviewer.md
```

- [ ] **Step 3: Wiki page** — Block 1 (Code refs) + Block 2 (Description / 6-axis review checklist).

- [ ] **Step 4: Commit (in-repo wiki page only)**
```bash
git add llm-wiki/wiki/project/components/bybit-api-reviewer-agent.md
git commit -m "docs(component): T1 — bybit-api-reviewer L5 agent wiki page (out-of-repo agent created)"
```

---

### Task T2: Context budget hook (MVP transcript size warning)

**Files:**
- Create: `~/.claude/hooks/context-budget-warn.sh` (out-of-repo)
- Modify: `~/.claude/settings.json` (out-of-repo) — register UserPromptSubmit hook
- Create: `llm-wiki/wiki/project/components/context-budget-hook.md` (in-repo)

**Steps:**

- [ ] **Step 1: Research Claude Code hook API** — UserPromptSubmit получает stdin JSON:
```json
{
  "session_id": "...",
  "transcript_path": "/path/to/session.jsonl",
  "user_prompt": "...",
  ...
}
```
Use `transcript_path` → file size как proxy для context usage. Threshold: warn at > 800KB (≈ 60% of 200K context window assuming 1KB/token avg).

- [ ] **Step 2: Write hook script**

```bash
#!/usr/bin/env bash
# context-budget-warn.sh
#
# Claude Code UserPromptSubmit hook.
# Purpose: warn operator если transcript file size exceeds threshold (proxy для context %).
#
# Established by: ADR 0048 (Sprint 32d Kit Phase 3).
# Defined by: llm-wiki/wiki/project/components/context-budget-hook.md
#
# Contract: stdin = JSON, exit 0 = always allow (advisory, never block).
# Output: stderr warning visible к operator.
#
# Threshold tuning: 800KB ≈ 60% of 200K-token context (1KB/token avg estimate).
# At 70%+ recommend /compact OR /clear.

set -u

# Thresholds (KB)
WARN_KB=800       # ~60% — soft warning
URGENT_KB=1200    # ~80% — urgent (suggest /compact или /clear)

payload="$(cat || true)"
if [ -z "$payload" ]; then exit 0; fi

# Extract transcript_path
transcript_path="$(printf '%s' "$payload" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
    print(d.get("transcript_path", ""), end="")
except Exception:
    pass
' 2>/dev/null || true)"

if [ -z "$transcript_path" ] || [ ! -f "$transcript_path" ]; then
    exit 0
fi

# Get file size в KB (cross-platform: macOS stat -f, Linux stat -c)
size_kb=$(du -k "$transcript_path" 2>/dev/null | cut -f1 || echo 0)

if [ "$size_kb" -gt "$URGENT_KB" ]; then
    echo "" >&2
    echo "🔴 Context URGENT: transcript ${size_kb}KB (>${URGENT_KB}KB ≈ 80% context)." >&2
    echo "   Recommend: /compact <focus topic> OR /clear для new task." >&2
    echo "" >&2
elif [ "$size_kb" -gt "$WARN_KB" ]; then
    echo "" >&2
    echo "🟡 Context warning: transcript ${size_kb}KB (>${WARN_KB}KB ≈ 60% context)." >&2
    echo "   Consider /compact soon если task continues long." >&2
    echo "" >&2
fi

exit 0  # always allow — advisory only
```

- [ ] **Step 3: bash -n + chmod**
```bash
bash -n ~/.claude/hooks/context-budget-warn.sh && echo "OK"
chmod +x ~/.claude/hooks/context-budget-warn.sh
```

- [ ] **Step 4: Register UserPromptSubmit hook в settings.json**

Add к `hooks.UserPromptSubmit[0].hooks` array (alongside caveman-mode-tracker.js):
```json
{
  "type": "command",
  "command": "$HOME/.claude/hooks/context-budget-warn.sh"
}
```

- [ ] **Step 5: Test (manual — fake transcript_path)**

```bash
# Create fake 1MB file
dd if=/dev/zero of=/tmp/fake-transcript.jsonl bs=1024 count=1000 2>/dev/null
echo '{"transcript_path":"/tmp/fake-transcript.jsonl","user_prompt":"test"}' | bash ~/.claude/hooks/context-budget-warn.sh
# Expected: 🟡 warning visible на stderr, exit 0
rm /tmp/fake-transcript.jsonl
```

- [ ] **Step 6: Wiki page** — Block 1 + Block 2.

- [ ] **Step 7: Commit (in-repo wiki page only)**
```bash
git add llm-wiki/wiki/project/components/context-budget-hook.md
git commit -m "docs(component): T2 — context-budget-warn hook wiki page (out-of-repo hook + settings.json registered)"
```

---

### Task T3: anthropic-skills:schedule wire + Sprint metrics tracking

**Files:**
- Modify: `llm-wiki/wiki/project/architecture/tooling-inventory-ru.md` (NEW Section 23 schedule wire)
- Create: `llm-wiki/wiki/project/sprint-metrics.md` (NEW)

**Steps:**

- [ ] **Step 1: Add Section 23 — anthropic-skills:schedule wire к audit_formulas.py**

Document operator setup procedure:
```
1. Verify scripts/audit_formulas.py runs successfully manually
2. Use anthropic-skills:schedule MCP tool:
   - Frequency: weekly (Monday 09:00 UTC) OR monthly если backtests stable
   - Command: cd <repo> && source .venv/bin/activate && python scripts/audit_formulas.py
   - Output: data/formulas_audit_v1.json (overwritten OR _post_sNN.json snapshot)
3. Persist schedule via mcp__scheduled-tasks__create_scheduled_task
```

NOTE: Schedule registration happens at session level — operator action, not committed к repo.

- [ ] **Step 2: Create sprint-metrics.md template page**

```markdown
---
title: Sprint Metrics — velocity / revision rate / KU tracking
type: metrics
tags: [metrics, velocity, revision-rate, ku, sprint-tracking]
created: 2026-04-27
updated: 2026-04-27
status: active
---

# Sprint Metrics

Manual per-sprint update at PHASE 9 Close. Tracks velocity (tasks/sprint), bugs found, review iterations, KU achieved.

## Per-sprint table

| Sprint | Tasks | Bugs found | Review iterations | Pytest count | КУ avg | Time | КУ/час |
|--------|-------|-----------|-------------------|--------------|--------|------|--------|
| S27 | 8 | 5 (formula) | 12 | 762 | — | 1 session | — |
| S28 | 6 | 0 | 0 | 762 | — | 1 session | — |
| ... |
| S32 | 6 | 0 | 0 | 773 | 60% | 45 min | 80 |
| S32b | 6 | 0 | 0 | 773 | 60.5% | 3h | 120 |
| S32c | 4 | 0 | 0 | 773 | 51% | 1.5h | 75 |
| S32d | 5 | 0 | 0 | 773 (TBD) | TBD | TBD | TBD |

## Trends (rolling 5 sprints)

- Velocity: avg X tasks/sprint
- Bug detection: Y bugs/sprint (lower = better)
- КУ trend: ↑/↓/→
- Time trend: ↑/↓/→

## Update protocol

PHASE 9 Close skill (`sprint-finish`) extension:
1. Count tasks completed (from sprint page Deliverables table)
2. Count bugs found (from Phase 5/6 outcomes)
3. Count review iterations (Phase 6 reviewer dispatch count)
4. Read pytest passed count from Phase 5 verify output
5. Compute КУ avg from sprint page (per-task table)
6. Time = total session duration
7. Append row к table выше
8. Update Trends section если 5+ sprints accumulated
```

- [ ] **Step 3: Commit**

```bash
git add llm-wiki/wiki/project/architecture/tooling-inventory-ru.md \
        llm-wiki/wiki/project/sprint-metrics.md
git commit -m "docs(metrics): T3 — anthropic-skills:schedule wire (Section 23) + sprint-metrics.md tracking template"
```

---

### Task T4: Memory corpus bridges 2-4 research notes (feasibility doc)

**Files:**
- Modify: `llm-wiki/wiki/project/architecture/tooling-inventory-ru.md` (NEW Section 24)

**Steps:**

- [ ] **Step 1: Inspect claude-mem plugin source**

```bash
ls ~/.claude/plugins/cache/thedotmack/claude-mem/
# Read MCP server source (если accessible)
# Document: API endpoints, corpus partition support (or not), search filter syntax
```

- [ ] **Step 2: Add Section 24 — Memory corpus bridges feasibility research**

Document what's feasible / not feasible per claude-mem current API:

```markdown
## 24. Memory corpus bridges — feasibility research notes (S32d)

**Status:** Research notes only. Implementation BLOCKED on claude-mem internal API constraints. Не shippable until plugin upstream supports OR fork.

### Bridge 2 — corpus periodic sync (auto-rebuild от wiki/log.md)

**Goal:** mem-search corpus auto-rebuild when wiki/log.md gets new entries (chronological journal).

**API check:**
- claude-mem MCP exposes: `build_corpus`, `prime_corpus`, `rebuild_corpus`, `list_corpora`
- ✅ Build/rebuild API exists
- ❌ No "watch directory" / "trigger on file change" мechanism
- Workaround: Cron-based via anthropic-skills:schedule (S32d Section 23 pattern)

**Implementation cost:** LOW if cron acceptable. Use `mcp__scheduled-tasks__create_scheduled_task` daily 03:00 UTC to invoke `mcp__plugin_claude-mem_mcp-search__rebuild_corpus`.

**Decision:** SHIPPABLE via cron. Operator setup task (not in-repo).

### Bridge 3 — chapter mark auto-link к log.md

**Goal:** When `mark_chapter` MCP called, append linked entry к `llm-wiki/wiki/log.md` automatically.

**API check:**
- ccd_session MCP `mark_chapter` tool — does NOT support post-call hooks (one-shot operation)
- ❌ No webhook / callback mechanism
- Workaround: PostToolUse hook fired on `mcp__ccd_session__mark_chapter` invocation

**Implementation cost:** MEDIUM. Need PostToolUse hook script that:
1. Parses chapter title + summary from tool_input JSON
2. Appends к log.md: `## [YYYY-MM-DD] chapter | <title>\n<summary>`
3. Atomic file write (avoid race conditions)

**Decision:** SHIPPABLE via PostToolUse hook. Defer к S33+ kit work если operator wants.

### Bridge 4 — frontmatter tags → corpus partition (S32c scheme implementation)

**Goal:** When wiki page committed, parse frontmatter tags + categorize observation into 4 partitions (per S32c Section 22 scheme).

**API check:**
- claude-mem MCP exposes: corpus management API но NO partition support в current version
- corpora are flat topical (set via `prime_corpus(corpus_name)`)
- ❌ Cannot create sub-partitions within corpus
- Workaround: Create 4 separate corpora — `trading-decisions`, `formula-knowledge`, `process-patterns`, `debug-knowledge`
- Then `mem-search` queries specific corpus instead of "category:" filter

**Implementation cost:** HIGH. Requires:
1. Create 4 corpora via `mcp__plugin_claude-mem_mcp-search__build_corpus`
2. Ingest hook parses frontmatter, calls `mcp__plugin_claude-mem_mcp-search__prime_corpus(<partition>)` then writes observation
3. Cascade STEP 2 syntax change: `mem-search corpus:trading-decisions`
4. Existing 17 observations need re-categorization (manual OR script)

**Decision:** NOT SHIPPABLE this sprint. Requires multi-corpus refactor + re-ingest existing data + cascade rule update. Estimate 6-10 hours focused work. Defer к operator-funded kit work OR skip permanently если flat search "good enough" в practice.

### Honest recommendation

**Bridge 2 ship-ready** (cron-based rebuild) — operator setup task at next session.

**Bridge 3 medium effort** — defer к next kit kit work iteration if operator wants.

**Bridge 4 NOT recommended** — high effort vs marginal benefit. Current 17 observations search well через flat corpus. Re-evaluate когда corpus > 100 observations (likely S40+).

### What S32c scheme docs (Section 22) provide despite no impl?

- ✅ Lock partition labels in stable contract (4 names won't change)
- ✅ Tag mapping pseudo-code ready для future implementation
- ✅ Operator can manually validate scheme на existing observations (per Section 22 procedure)
- ✅ Future kit sprint has clear target if priorities change
```

- [ ] **Step 3: Commit**

```bash
git add llm-wiki/wiki/project/architecture/tooling-inventory-ru.md
git commit -m "docs(kit): T4 — Section 24 NEW Memory corpus bridges 2-4 feasibility research (Bridge 2 ship-ready cron, Bridge 3 medium, Bridge 4 NOT recommended)"
```

---

### Task T5: ADR 0048 + sprint-32d page + index/counts sync

**Files:**
- Create: `llm-wiki/wiki/project/decisions/0048-sprint-32d-kit-phase-3-improvements.md`
- Create: `llm-wiki/wiki/project/sprints/sprint-32d-kit-phase-3-improvements.md`
- Modify: `llm-wiki/wiki/index.md` (+ S32d sprint + ADR 0048 + 3 component pages + sprint-metrics)
- Modify: `llm-wiki/wiki/project/architecture/current-state.md` (counts: 34→35 sprints / 47→48 ADRs / 40→43 components / 10→11 agents + sprint metrics page entry + S32d sprint history row + S32 series complete note)
- Modify: `llm-wiki/wiki/project/architecture/kit-overview-ru.md` (mirror counts)

**Steps:**

- [ ] **Step 1: Write ADR 0048**

- [ ] **Step 2: Write sprint-32d page**

- [ ] **Step 3: index.md +entries**

- [ ] **Step 4: current-state.md sync canonical counts + sprint history row + "S32 series complete" note**

- [ ] **Step 5: kit-overview-ru.md update counts**

- [ ] **Step 6: Commit batch**

```bash
git add llm-wiki/wiki/project/decisions/0048-sprint-32d-kit-phase-3-improvements.md \
        llm-wiki/wiki/project/sprints/sprint-32d-kit-phase-3-improvements.md \
        llm-wiki/wiki/index.md \
        llm-wiki/wiki/project/architecture/current-state.md \
        llm-wiki/wiki/project/architecture/kit-overview-ru.md
git commit -m "docs(sprint): T5 — ADR 0048 + sprint-32d page + index/counts sync (47→48 ADRs / 34→35 sprints / 40→43 components / 10→11 agents) + S32 series complete"
```

---

## Phase 5 Verify

```bash
source .venv/bin/activate
pytest tests/ -q --ignore=tests/integration 2>&1 | tail -5
# Expected: 773 passed (S32c baseline preserved by construction)

mypy --strict src/ 2>&1 | tail -3
# Expected: 1 pre-existing error

# Canonical counts verify
python -c "from src.execution.state_machine import TRANSITIONS, ExecutionState, ExecutionEvent; from src.risk.reason_codes import ReasonCode; print(f'states={len(list(ExecutionState))}, events={len(list(ExecutionEvent))}, transitions={len(TRANSITIONS)}, reason_codes={len(list(ReasonCode))}')"
# Expected: 16/30/74/45 (unchanged)

# Hook scripts bash -n
bash -n ~/.claude/hooks/context-budget-warn.sh && echo "context-budget hook OK"

# Hook positive test (small file → no warning, exit 0)
echo '{"transcript_path":"/etc/hosts"}' | bash ~/.claude/hooks/context-budget-warn.sh
echo "small file exit: $?"

# Hook negative test (large file → warning + exit 0)
dd if=/dev/zero of=/tmp/fake-transcript.jsonl bs=1024 count=1000 2>/dev/null
echo '{"transcript_path":"/tmp/fake-transcript.jsonl"}' | bash ~/.claude/hooks/context-budget-warn.sh 2>&1
rm /tmp/fake-transcript.jsonl
```

Update SPRINT_STATE Phase 5=done.

---

## Phase 6 Review

Skipped (config + scripts + docs sprint, no production src/ touched).

---

## Phase 7 Sync

log.md sprint-end entry + "S32 series COMPLETE" milestone marker.

---

## Phase 8 Ship

Per `sprint-finish` skill:
1. Pre-validation (pytest baseline preserved)
2. HARD-GATE — sprint-32d page exists ✓ (T5)
3. HARD-GATE — canonical counts sync ✓ (T5)
4. HARD-GATE — ADR 0048 в index.md ✓ (T5)
5. HARD-GATE — Block 1↔2 sync для component pages ✓ (T1, T2)
6. HARD-GATE — orphan-audit grep includes tests/ (N/A, no src/)
7. SPRINT_STATE → 8-ship
8. git push (all 6 push hooks fire — UserPromptSubmit hook NOT push-related)
9. gh pr create
10. CI runs — S32b infrastructure validates (3rd PR)
11. gh pr merge --squash --delete-branch
12. git tag v0.1.0-alpha.32d + push
13. SPRINT_STATE → between-sprints + S33 trading prep section

---

## Phase 9 Close

```
1. SPRINT_STATE → between-sprints
2. log.md session-end entry — "S32 series COMPLETE" milestone
3. mark_chapter "Sprint 32d — S32 series complete"
4. git commit + push
5. (Skip consolidate-memory — S35 OR >30 obs, currently ~17)
```

**S33 next sprint preparation:**
- S33 = trading work scope
- Operator action ESC-1/2/3 decision OR brainstorm S33 single-symbol scope
- Test debt (3 pytest + 1 mypy + ~169 ruff baseline) → fix in S33 OR separate cleanup sprint

---

## Self-Review

**Spec coverage:**
- ✓ T1 bybit-api-reviewer L5 agent
- ✓ T2 context budget hook MVP
- ✓ T3 schedule wire docs + sprint metrics template
- ✓ T4 corpus bridges research notes (honest feasibility)
- ✓ T5 ADR + sprint page + sync

**No placeholders:** все steps concrete с code/commands.

**Type consistency:** N/A (no production code).

**Execution mode:** Controller-driven (config + docs + scripts sprint).

**Honest research mode:** T4 = research notes only. Bridge 4 implementation NOT recommended due high effort vs marginal benefit. Documented decision rationale.

---

## Related

- ADR 0017 (review-agent harness) — L5 agent matrix
- ADR 0044 (S31 best practices) — kit baseline
- ADR 0045/0046/0047 (S32/S32b/S32c) — direct predecessors
- ADR 0048 (this) — Kit Phase 3 final S32 series sprint
- Sprint S32 / S32b / S32c / S32d (this) — S32 series Phase 0/1/2/3
