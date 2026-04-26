---
title: Sprint 32c — Kit Improvement Phase 2 (4 skill mappings + Fetch MCP + corpus categorization scheme)
type: sprint
tags: [sprint-32c, kit-improvement, phase-2, skill-mappings, fetch-mcp, corpus-scheme, ku-driven, ru]
created: 2026-04-27
updated: 2026-04-27
status: completed
sources:
  - project/decisions/0047-sprint-32c-kit-phase-2-improvements.md
  - project/plans/2026-04-27-sprint-32c-kit-phase-2-improvements.md
  - project/decisions/0046-sprint-32b-kit-phase-1-improvements.md
  - project/sprints/sprint-32b-kit-phase-1-improvements.md
---

# Sprint 32c — Kit Improvement Phase 2

## Overview

Sub-sprint S32 series (mirror S8a/S8b/S8c pattern). Tag v0.1.0-alpha.32c. Trading work BLOCKED via ESC-1/2/3 → S32 series занимает sprint slots.

**Trigger:** Per ADR 0046 carry-overs — Kit Phase 2 = 7 changes, КУ avg 42% / ~1 sprint forecast. **Reduced scope decision** (this session): 5 clear wins shipped в S32c, 2 research items (memory corpus bridges 2-4 implementation + context budget hook) deferred к S32d.

**4 changes shipped:**

| Task | Type | Commit |
|------|------|--------|
| T1 Fetch/HTTP MCP server | `.mcp.json` fetch + tooling-inventory-ru.md Section 7.7/7.8 doc | 0761bad |
| T2 4 skill mappings | sprint-flow-ru.md +api-design Phase 3 / +browser-test Phase 5 / +perf-opt Phase 6 OPT / +idea-refine extension Phase 2 PRE workflow | 09fcdee |
| T3 Memory corpus categorization scheme | tooling-inventory-ru.md NEW Section 22 (4 partitions + tag mapping + cascade enhancement spec) | 47bba48 |
| T4 ADR 0047 + sprint-32c page + index/counts | 46→47 ADRs / 33→34 sprints / 7→8 MCP / 32→36 skills | (this commit) |

## Plan / ADR links

- [[../decisions/0047-sprint-32c-kit-phase-2-improvements]] — Sprint 32c ADR
- [[../plans/2026-04-27-sprint-32c-kit-phase-2-improvements]] — Sprint 32c plan

## КУ achieved

| Item | T (token) | P (speed) | Q (quality) | КУ % |
|------|----------|-----------|-------------|------|
| T1 Fetch MCP | 2 | 3 | 2 | 46% |
| T2 4 skill mappings | 1 | 2 | 3 | 42% |
| T3 Memory corpus scheme | 4 | 3 | 4 | 74% (forecast) |
| T4 ADR + sync | 1 | 2 | 3 | 42% |
| **Sprint avg** | — | — | — | **51%** |

T3 КУ depends on bridge 4 implementation в S32d — scheme docs alone = 50%, full implementation = 74%.

Time invested: ~1.5 hours (matches forecast 1.5-2h).

## Phase 5 Verify outcome

- pytest: 773 passed (S32b baseline preserved by construction — no src/ changes)
- mypy: 1 pre-existing error (S32b baseline)
- canonical counts: 16/30/74/45 ✓
- json validate .mcp.json: ✓ (sqlite-trading + fetch)
- yaml validate .pre-commit-config.yaml: ✓

## Phase 6 Review

Skipped (config + docs sprint, no production src/ touched).

## FSM growth

No FSM changes (canonical counts: 16/30/74/45 — unchanged).

## Reason codes

No new reason codes.

## Tests

No code tests added (process/wiki/config sprint).

PHASE 5 verify: 773 pytest passed (S32b baseline preserved by construction — no src/ changes).

## Wiki updates summary

8 files touched (in-repo):
- 2 NEW: ADR 0047 + sprint-32c page
- 5 MODIFIED: index.md + current-state.md + kit-overview-ru.md + tooling-inventory-ru.md (Section 7.7/7.8 + Section 22) + sprint-flow-ru.md (4 skill mappings + Phase 2 PRE procedure + Skills × Phase map 32→36)
- 1 MODIFIED (config): `.mcp.json` (+fetch server)
- 1 NEW (in-repo): plan file

## Open issues для S32d+

**Kit Phase 3 (S32d candidate):**

Phase 2 deferred research items:
- Memory corpus org bridge 2 (corpus periodic sync — auto-rebuild от wiki/log.md новых entries)
- Memory corpus org bridge 3 (chapter mark auto-link к log.md)
- Memory corpus org bridge 4 implementation script (uses scheme от S32c Section 22)
- Context budget hook (>70% warn) — requires Claude Code hook API research

Original Phase 3 items (per S32 Phase 0 plan):
- bybit-api-reviewer L5 agent (Bybit V5 rate limits / endpoint params / error codes)
- anthropic-skills:schedule (audit_formulas.py automation)
- Sprint metrics tracking (velocity / revision rate)

**Test debt (carry-over к first trading sprint S33+):**
- 3 pytest failures (test_replay_long_only / test_replay_next_open)
- 1 mypy error (__main__.py:636 bars_per_year_map redef)
- ~169 ruff baseline cleanup

**Trading carry-overs (BLOCKED — operator decision):**
- ESC-1 multi-symbol authorization
- ESC-2 "in profit" semantics
- ESC-3 4H operational implications

## Key decisions

1. **Reduced scope adopted** — pre-plan analysis identified 2 research-heavy items (memory corpus bridges 2-4 implementation + context budget hook). Defer к S32d preserves S32c shippability.

2. **Memory corpus scheme committed без script** — partition labels + tag mappings stable design choice. Implementation script needs claude-mem internal API research. Splitting allows operator review scheme before implementation lock-in.

3. **Fetch MCP project-level** — same pattern как sqlite-trading (S32b). `.mcp.json` instead of settings.json (schema constraint).

4. **idea-refine extension explicit procedure** — basic mapping S32 entry expanded к 5-step Phase 2 PRE workflow с anti-pattern documentation (skip self-test guard).

5. **api-design + browser-test + perf-opt mappings deferred к S32c** — these mappings были part of original Phase 2 scope, not Phase 1 quick wins.

## S32c process artifact

S32c executed по proper kit flow per S28+ binding rules:
- ✅ PHASE 1 Orient (session continuation post-S32b ship)
- ✅ PHASE 2 Brainstorm SKIPPED — operator-specified deliverables per ADR 0046 carry-overs (но pre-plan analysis surfaced reduced-scope decision)
- ✅ PHASE 3 Plan file `plans/2026-04-27-sprint-32c-kit-phase-2-improvements.md` (7bab107) — HARD-GATE satisfied
- ✅ PHASE 4 Controller-driven (config + docs sprint), per-task TDD pattern
- ✅ Per-task SPRINT_STATE update после каждой task (S28 protocol)
- ✅ T1-T4 task commits + SPRINT_STATE updates inline
- ✅ TodoWrite phase tracker
- ✅ PHASE 5 verify (773 pytest preserved + json/yaml validate + canonical counts)
- ✅ PHASE 6 Review skipped (no src/ touched)
- ✅ PHASE 7 Sync (index + current-state + kit-overview + tooling-inventory + log)
- ✅ PHASE 8 Ship via gh pr + squash merge + tag v0.1.0-alpha.32c
- ✅ PHASE 9 Close — SPRINT_STATE → between-sprints
- ✅ Все 7 push hooks fire correctly (sprint-flow-check + adr-agent-sync + adr-index-sync + wiki-broken-link + phase-advance + sprint-state-freshness-check + 7th was added wrong-count earlier — actually 6 push hooks total post-S32b)

## Related

- ADR 0017 (review-agent harness) — L5 agent matrix policy
- ADR 0043 (S30 tier-2 agents + cascade) — bridges 2-4 origin
- ADR 0044 (S31 best practices revision) — kit baseline
- ADR 0045 (S32 Phase 0) — initial КУ analysis source
- ADR 0046 (S32b Kit Phase 1) — CI infrastructure foundation
- ADR 0047 (this) — Kit Phase 2 reduced scope implementation
- Sprint S32 / S32b / S32c (this) — S32 series Phase 0/1/2
