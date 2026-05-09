---
title: 0043. Sprint 30 — Tier-2 Agents (security-auditor / test-engineer / doc-reviewer) + phase-advance hook + LLMWiki↔Claude-mem cascade
type: decision
date: 2026-04-26
sprint: 30
tags: [adr, sprint-30, agents, hook, phase-advance, wiki-mem-cascade, tier-2, ru]
sources:
  - project/architecture/sprint-flow-ru.md
  - project/architecture/tooling-inventory-ru.md
  - project/decisions/0017-review-agent-harness.md
  - project/decisions/0041-sprint-28-process-enforcement.md
  - project/decisions/0042-sprint-29-superpowers-integration.md
  - https://github.com/obra/superpowers
  - https://github.com/thedotmack/claude-mem
status: accepted
---

# 0043. Sprint 30 — Tier-2 Agents + phase-advance hook + LLMWiki↔Claude-mem cascade

**Status:** accepted
**Date:** 2026-04-26

## Контекст

Operator directive 2026-04-26 после S29 ship:

> "S30 scope: Register security-auditor + test-engineer plugins в L5 stack. Update tooling-inventory-ru.md Section 1 (8 agents instead of 6). Update sprint-flow-ru.md Phase 6 reviewer matrix. Hook добавить — phase-advance.sh validating verification-before-completion checklist runs перед merge. А также добавить doc-reviewer (haiku)."
>
> "Проанализируй как можно смержить функционал llmwiki и её потенциал с плагином claude mem, т.к. они оба призваны чтобы обеспечить экономию токенов и передачи тебе полноты контекста самым оптимальным путём."

## Решения

### Decision 1: Add 3 tier-2 reviewer agents

**Pre-S30:** 6 reviewer agents (trader-expert / trading-logic / quant-stats / data-integrity / python / architecture).
**Post-S30:** 9 reviewer agents (+3 tier-2).

| Agent | Model | Scope | Memory |
|-------|-------|-------|--------|
| `security-auditor` | opus | OWASP / API keys / signing / override paths / Mainnet | project |
| `test-engineer` | sonnet | Test pyramid / Hypothesis property / coverage / regression | project |
| `doc-reviewer` | haiku | Frontmatter / links / Block 1↔2 sync / canonical counts | project |

Each agent имеет:
- Path discipline section (absolute paths)
- Sprint context priming (TIER A — mandatory canonical file loads)
- Persistent memory directory `.claude/agent-memory/<agent>/MEMORY.md`
- Project-specific rules (security: trading rules; test: math invariants; doc: Block 1↔2 sync)

### Decision 2: phase-advance.sh hook (Phase 5 enforcement)

**Pre-S30:** Phase 5 verification depends на controller discipline. Skipped → unverified code shipped.
**Post-S30:** Hook blocks `gh pr merge` если SPRINT_STATE Phase 5 status != "done"/"skipped".

**Hook script:** `~/.claude/hooks/phase-advance.sh`
- PreToolUse Bash matcher
- Parses SPRINT_STATE Phase tracking table (S28 template)
- Extracts Phase 5 (Verify) row, 2nd column status
- Allowed: "done" / "skipped (...)"
- Blocked: "pending" / "in_progress" / unknown

**Tested:**
- Positive: Phase 5 = "done" → exit 0
- Negative: Phase 5 = "pending" → exit 2 + helpful error с required action checklist

**Registered:** `~/.claude/settings.json` PreToolUse Bash matcher.

### Decision 3: LLMWiki ↔ Claude-mem cascade rule

**Problem:** Two systems target token economy + context delivery (llmwiki structured wiki + claude-mem semantic search). Currently independent — controller picks one randomly.

**Decision:** Documentation-first cascade rule (no automation в S30):

```
STEP 1: wiki/<page>.md    (curated, structured, tagged)   ← CHECK FIRST
   ↓ not found
STEP 2: mem-search        (past sessions semantic search)
   ↓ not found
STEP 3: Grep raw          (current code state)
   ↓ needed
STEP 4: Read raw + offset (full content, controlled)
```

**Rationale:**
- Step 1 (wiki) = highest semantic density per token (curated)
- Step 2 (mem) = past learnings + decisions (compressed)
- Step 3 (Grep) = current code state (bounded output)
- Step 4 (Read) = full content (last resort)

**Documentation enforcement:** Cascade rule в `tooling-inventory-ru.md` Section 13 NEW + `sprint-flow-ru.md` Token economy section + `CLAUDE.md` (repo + llm-wiki) cascade rule sections.

**Bridges (deferred к S31+):**
- Bridge 2 — wiki-mem-corpus-sync (periodic indexing wiki → claude-mem corpus). Defer: requires claude-mem API investigation.
- Bridge 3 — chapter mark auto-link к log.md (`mcp__ccd_session__mark_chapter` writes wiki/log.md entry). Defer: requires hook integration.
- Bridge 4 — frontmatter tags → mem corpus categorization (wiki frontmatter feeds corpus filtering). Defer: requires schema understanding.

S30 deliverable = documentation enforcement only. NO new skill creation.

## Последствия

### Code / config changes

NONE in repo (process/wiki only).

Out-of-repo (`~/.claude/`):
- `~/.claude/agents/security-auditor.md` NEW
- `~/.claude/agents/test-engineer.md` NEW
- `~/.claude/agents/doc-reviewer.md` NEW
- `~/.claude/hooks/phase-advance.sh` NEW
- `~/.claude/settings.json` MODIFIED — registered phase-advance.sh

### Wiki changes (in-repo)

- `wiki/project/architecture/tooling-inventory-ru.md` MODIFIED:
  - Section 1 expanded (6 → 9 agents с status legend ✅/🆕)
  - Section 8 hooks: + 8.6 phase-advance.sh
  - Section 13 NEW: LLMWiki ↔ Claude-mem cascade rule (4-step + 5 examples + bridges deferred)
  - Decision matrix +5 entries (security/test/doc reviewers + phase-advance hook + cascade lookup)
- `wiki/project/architecture/sprint-flow-ru.md` MODIFIED:
  - Phase 6 reviewer matrix +3 tier-2 reviewers с conditions
  - Phase 5 HARD-GATE + phase-advance.sh hook block note
  - NEW Token economy cascade section с link к Section 13
- `CLAUDE.md` (repo root) MODIFIED:
  - Phase 5 row + phase-advance hook
  - Phase 6 row +3 tier-2 reviewers
  - NEW LLMWiki↔Claude-mem cascade rule section
  - Anti-patterns +4
- `llm-wiki/CLAUDE.md` MODIFIED:
  - +phase-advance.sh hook documented
  - +cascade rule reference (BINDING)
- `wiki/project/decisions/0043-sprint-30-tier-2-agents-mem-wiki-merge.md` NEW (this ADR)
- `wiki/project/sprints/sprint-30-tier-2-agents-mem-wiki-merge.md` NEW
- `wiki/project/plans/2026-04-26-sprint-30-tier-2-agents-mem-wiki-merge.md` NEW
- `wiki/index.md` MODIFIED — entries для S30 + ADR 0043
- `wiki/project/architecture/current-state.md` MODIFIED — sprint history row +S30 + canonical counts (42→43 ADRs, 29→30 sprint pages)
- `wiki/log.md` MODIFIED — sprint-end entry

### Backward compatibility

- 6 existing reviewer agents preserved
- 5 existing hooks preserved (sprint-flow-check / adr-agent-sync / adr-index-sync / wiki-broken-link / caveman-*)
- `CLAUDE.md` phase table Phase 6 expanded (не replaced)
- `tooling-inventory-ru.md` sections 1-12 preserved, Section 13 added

### Carry-overs к S31+

- S27 ESC items (multi-symbol auth / live pilot ETH 4H / operational implications) STILL pending operator decision (BLOCKING S31+ trader-expert backlog)
- S28 carry-overs preserved
- S29 carry-overs preserved
- S30 carry-overs:
  - Bridge 2 (wiki-mem-corpus-sync) — requires claude-mem API investigation
  - Bridge 3 (chapter mark auto-link) — requires hook integration
  - Bridge 4 (frontmatter tags → corpus) — requires schema understanding
  - Optional: extract security-auditor MEMORY.md template для multi-trader migration
  - Optional: pre-commit hook checking SPRINT_STATE Phase 4 task table updated within last hour (per-task discipline aid)

## Ссылки

- `wiki/project/architecture/sprint-flow-ru.md` — обязательный процесс (updated S30)
- `wiki/project/architecture/tooling-inventory-ru.md` — tooling catalog (updated S30 с Section 13)
- `wiki/project/decisions/0017-review-agent-harness.md` — review agents matrix policy (parent)
- `wiki/project/decisions/0041-sprint-28-process-enforcement.md` — process enforcement ADR
- `wiki/project/decisions/0042-sprint-29-superpowers-integration.md` — superpowers integration ADR
- `wiki/project/plans/2026-04-26-sprint-30-tier-2-agents-mem-wiki-merge.md` — S30 plan
- `wiki/project/sprints/sprint-30-tier-2-agents-mem-wiki-merge.md` — S30 page
- https://github.com/obra/superpowers — superpowers skills source
- https://github.com/thedotmack/claude-mem — claude-mem source
- https://code.claude.com/docs/sub-agents — Claude Code subagent documentation
