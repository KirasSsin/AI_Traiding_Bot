---
title: Sprint 30 — Tier-2 Agents (security/test/doc) + phase-advance hook + LLMWiki↔Claude-mem cascade
type: sprint
tags: [sprint-30, agents, hook, phase-advance, wiki-mem-cascade, tier-2, ru]
created: 2026-04-26
updated: 2026-04-26
status: completed
sources:
  - project/decisions/0043-sprint-30-tier-2-agents-mem-wiki-merge.md
  - project/architecture/sprint-flow-ru.md
  - project/architecture/tooling-inventory-ru.md
  - project/plans/2026-04-26-sprint-30-tier-2-agents-mem-wiki-merge.md
---

# Sprint 30 — Tier-2 Agents + phase-advance hook + LLMWiki↔Claude-mem cascade

## Overview

Operator-driven kit hardening sprint. После S29 (full superpowers integration), 2 directives:
1. Add tier-2 reviewer agents (security-auditor / test-engineer / doc-reviewer) к L5 stack
2. Analyze llmwiki + claude-mem merge potential (token economy / context delivery)

Plus phase-advance.sh hook (Phase 5 verify enforcement closes gap S28 didn't address).

## Plan / ADR links

- [[../decisions/0043-sprint-30-tier-2-agents-mem-wiki-merge]] — Sprint 30 ADR
- [[../plans/2026-04-26-sprint-30-tier-2-agents-mem-wiki-merge]] — Sprint 30 plan
- [[../architecture/sprint-flow-ru]] — Phase 6 reviewer matrix expanded
- [[../architecture/tooling-inventory-ru]] — Section 1 (9 agents) + Section 8 (+phase-advance hook) + Section 13 NEW (cascade)

## Deliverables

### Out-of-repo (~/.claude/)

| Task | Files | Description |
|------|-------|-------------|
| T1 | `~/.claude/agents/security-auditor.md` NEW | Opus model, OWASP + trading-specific rules (HMAC override, withdraw whitelist, kill-switch auth, position bounds, Mainnet/Testnet detection). Severity BLOCKER/HIGH/MEDIUM/LOW. memory: project. |
| T2 | `~/.claude/agents/test-engineer.md` NEW | Sonnet model, test pyramid + Hypothesis property tests (DSR/Kelly/MC math invariants). Trading-specific rules (Decimal precision, timeframe parametrization S27 lesson, OHLCV invariants, look-ahead regression). memory: project. |
| T3 | `~/.claude/agents/doc-reviewer.md` NEW | Haiku model lightweight, wiki consistency (frontmatter + links + Block 1↔2 sync per ADR 0017 + canonical counts). Read-only. memory: project. |
| T4 | `~/.claude/hooks/phase-advance.sh` NEW + `settings.json` registered | Pre-merge hook blocks `gh pr merge` если SPRINT_STATE Phase 5 status != "done"/"skipped". Tested positive + negative. |

### Wiki (in-repo)

| Task | Files | Description |
|------|-------|-------------|
| T5+T6 | `wiki/project/architecture/tooling-inventory-ru.md` MODIFIED | Section 1 expanded (6→9 agents с status legend) + Section 8 +8.6 phase-advance + Section 13 NEW LLMWiki↔Claude-mem cascade rule (4-step + 5 examples + bridges deferred) + decision matrix +5 entries |
| T7 | `wiki/project/architecture/sprint-flow-ru.md` MODIFIED | Phase 6 reviewer matrix +3 tier-2 + Phase 5 hook note + NEW Token economy cascade section |
| T8 | `CLAUDE.md` (repo root) MODIFIED | Phase 5/6 rows expanded + NEW cascade rule section + 4 anti-patterns |
| T8 | `llm-wiki/CLAUDE.md` MODIFIED | +phase-advance hook documented + cascade rule reference |
| T9 | `wiki/project/decisions/0043-sprint-30-tier-2-agents-mem-wiki-merge.md` NEW | This ADR |
| T9 | `wiki/project/sprints/sprint-30-tier-2-agents-mem-wiki-merge.md` NEW | This page |
| T9 | `wiki/project/plans/2026-04-26-sprint-30-tier-2-agents-mem-wiki-merge.md` NEW | Plan file |
| T9 | `wiki/index.md` MODIFIED | + S30 entry + ADR 0043 entry |
| T9 | `wiki/project/architecture/current-state.md` MODIFIED | + S30 sprint history row + canonical counts (42→43 ADRs, 29→30 sprint pages) |
| T9 | `wiki/log.md` MODIFIED | S30 sprint-end entry |

## 3 NEW reviewer agents (tier-2)

| Agent | Model | When MUST | Memory |
|-------|-------|-----------|--------|
| security-auditor | opus | Money / API keys / override.py / HMAC / signing / withdrawal / Mainnet integration changes | project |
| test-engineer | sonnet | New module без tests / coverage gaps / property test design / regression tests для fixed bugs | project |
| doc-reviewer | haiku | After wiki-update skill runs / before sprint ship | project |

## NEW hook (Phase 5 enforcement)

| Hook | Trigger | Block |
|------|---------|-------|
| `phase-advance.sh` (S30+) | PreToolUse on `gh pr merge` | Phase 5 status != "done"/"skipped" в SPRINT_STATE |

Combined hooks (6 total):
1. adr-agent-sync (S8c+)
2. adr-index-sync (S8c+)
3. wiki-broken-link
4. caveman-*
5. sprint-flow-check (S28+)
6. **phase-advance** (S30+) 🆕

## LLMWiki ↔ Claude-mem cascade (NEW Section 13)

Documentation-first integration (no automation). Cascade order:
```
wiki → mem-search → grep → raw
```
- Saves tokens (curated wiki = highest density per token)
- Enforced via documentation в 4 places (tooling-inventory Section 13 + sprint-flow Token economy + CLAUDE.md repo + CLAUDE.md llm-wiki)

Bridges 2-4 (corpus sync / chapter mark auto-link / frontmatter tags) deferred к S31+ requires claude-mem API investigation.

## FSM growth

No FSM changes (canonical counts: 16/30/74/45 — unchanged).

## Reason codes

No new reason codes.

## Tests

No code tests added (process/wiki sprint).

PHASE 5 verify: 762 pytest passed (S29 baseline preserved).

## Wiki updates summary

10 files touched:
- 4 NEW (in-repo): ADR / sprint page / plan / sprint-flow-ru changes
- 5 MODIFIED (in-repo): tooling-inventory-ru / sprint-flow-ru / CLAUDE.md repo / CLAUDE.md llm-wiki / index.md / current-state.md / log.md
- 4 NEW (out-of-repo): 3 agents + 1 hook
- 1 MODIFIED (out-of-repo): settings.json

## Open issues для S31+

### S27 carry-overs (operator decision pending — BLOCKING S31+ trader-expert backlog)
- ESC-1 Multi-symbol authorization
- ESC-2 "In profit" vs "pass acceptance criteria"
- ESC-3 Operational implications 4H multi-symbol

### S30 carry-overs (cascade bridges deferred)
- Bridge 2: wiki-mem-corpus-sync (periodic indexing)
- Bridge 3: chapter mark auto-link к log.md
- Bridge 4: frontmatter tags → mem corpus categorization
- Optional: extract security-auditor MEMORY.md template для multi-tier expansion

## Key decisions

1. **Tier-2 agents focused, not bloat.** 3 agents address concrete gaps (security/test/wiki consistency). Not arbitrary expansion.

2. **Hook over checklist.** phase-advance.sh = mechanical Phase 5 enforcement, not polite reminder. Aligns с S28 pattern (mechanical enforcement > reminder).

3. **Documentation-first cascade.** S30 deliverable = enforcement через docs, NOT new skill or hook automation. Bridges 2-4 deferred — operator can pilot cascade rule first, then automate если works.

4. **Skills × Phase integration map updated** (Section 12 в tooling-inventory-ru.md) — 9 agents instead of 6.

5. **Backward compat preserved.** All 6 existing agents + 5 existing hooks unchanged.

## S30 process artifact

S30 executed по proper kit flow per S28 binding rules + S29 expanded skills:
- ✅ PHASE 3 plan file `plans/2026-04-26-sprint-30-tier-2-agents-mem-wiki-merge.md`
- ✅ PHASE 4 controller-driven (docs/agents sprint), per-task TDD pattern
- ✅ Per-task SPRINT_STATE update после каждой task (S28 protocol)
- ✅ 6 task commits (T1+plan, T2+T3+T4, T5+T6, T7+T8, T9, ship)
- ✅ TodoWrite phase tracker
- ✅ PHASE 5 verify (762 pytest preserved + bash -n hook + positive/negative test)
- ✅ PHASE 7 sync (index + current-state + log)
- ✅ PHASE 8 ship via gh pr + squash merge + tag
- ✅ Все 4 push hooks fire correctly (sprint-flow-check + adr-agent-sync + adr-index-sync + phase-advance)

## Related

- ADR 0017 (review-agent harness) — parent matrix policy
- ADR 0041 (S28 process enforcement) — sprint-flow-check hook precedent
- ADR 0042 (S29 superpowers integration) — full skills mapping
- ADR 0043 (this) — tier-2 agents + phase-advance + cascade
- Sprint S28 — established kit flow + Russian docs
- Sprint S29 — full superpowers (13/13)
- Sprint S30 (this) — tier-2 + cascade
- obra/superpowers + thedotmack/claude-mem — source repos
