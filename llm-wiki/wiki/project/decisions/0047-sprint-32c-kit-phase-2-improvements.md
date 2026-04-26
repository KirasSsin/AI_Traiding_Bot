---
title: ADR 0047 — Sprint 32c Kit Improvement Phase 2 (4 skill mappings + Fetch MCP + corpus categorization scheme)
type: decision
tags: [adr, sprint-32c, kit-improvement, phase-2, skill-mappings, fetch-mcp, corpus-scheme, ku-driven]
created: 2026-04-27
updated: 2026-04-27
status: accepted
sources:
  - project/plans/2026-04-27-sprint-32c-kit-phase-2-improvements.md
  - project/decisions/0046-sprint-32b-kit-phase-1-improvements.md
  - project/decisions/0045-sprint-32-kit-phase-0-improvements.md
  - project/SPRINT_STATE.md
---

# ADR 0047 — Sprint 32c Kit Improvement Phase 2

## Status

Accepted (2026-04-27) — implemented in S32c (`feature/sprint-32c-kit-phase-2-improvements` → tag `v0.1.0-alpha.32c`). Sub-sprint S32 series.

## Context

Per ADR 0046 carry-overs, Kit Phase 2 = 7 changes total. Pre-plan analysis (this session) revealed:
- 5 changes = clear wins (skill mappings + Fetch MCP)
- 2 changes = research-heavy (memory corpus bridges 2-3 + bridge 4 implementation script + context budget hook)

**Reduced scope decision:** S32c делает только clear wins + scheme docs для bridge 4. Implementation scripts → S32d.

**Pain points addressed:**

1. **AS:performance-optimization not mapped** — backtest engine slow on 5y backfill, no formal Phase 6 trigger для profile-first optimization
2. **AS:api-and-interface-design not mapped** — CLI commands и module boundaries designed ad-hoc, no formal Phase 3 trigger для interface stability
3. **AS:browser-testing-with-devtools not mapped** — dashboard sprints (S25/S26) testing manual, no formal Phase 5 trigger для Chrome DevTools verification
4. **AS:idea-refine basic mapping incomplete** — S32 added entry but no explicit workflow steps; operator vague ideas → unfocused brainstorm-init questionnaires
5. **No web docs lookup MCP** — Bybit API v5 docs / PyPI versions / GitHub releases require manual browser navigation
6. **claude-mem corpus flat** — mem-search noisy when queries span multiple domains (trading + process + debug), будет компаундироваться через 5-10 спринтов

## Options

**Option A: Full Phase 2 — все 7 deliverables в S32c**
- Pros: Phase 2 closed completely
- Cons: Memory corpus bridges 2-4 + context budget hook = research-heavy, scope creep, potential 2x overrun

**Option B: Reduced scope — 5 clear wins, defer 2 research items**
- Pros: Predictable ship, clear deliverables, KU avg ~50% / ~1.5-2 hours
- Cons: 2 items pushed к S32d (Phase 3 expanded scope)

**Option C: Skip S32c, jump directly к S32d с full research scope**
- Pros: One sprint less
- Cons: Lose 5 quick wins (4 skill mappings + Fetch MCP); operator productivity gap

## Decision

**Option B selected.** Sprint 32c = Kit Phase 2 reduced = 4 changes:

| # | Change | Type | КУ % |
|---|--------|------|------|
| T1 | Fetch/HTTP MCP server (.mcp.json fetch + tooling-inventory Section 7.7+7.8 doc) | MCP | 46% |
| T2 | 4 skill mappings (api-design Phase 3 / browser-test Phase 5 / perf-opt Phase 6 / idea-refine extension Phase 2 PRE workflow) | Skills × Phase | 42% (avg) |
| T3 | Memory corpus categorization scheme docs (tooling-inventory-ru.md Section 22 NEW) | Wiki design | 50% |
| T4 | ADR 0047 + sprint-32c page + index/counts sync | Wiki sync | 42% |

**КУ avg ~45-50%** / ~1.5-2 hours forecast.

### Skill mapping rationales

**`api-and-interface-design` → Phase 3:** triggered когда plan включает new public API (REST endpoint / CLI subcommand / module exports). Ensures interface stability ДО implementation locks contracts.

**`browser-testing-with-devtools` → Phase 5:** triggered для dashboard sprints (S25/S26-class). Requires Chrome MCP enabled (✓ via Claude_in_Chrome). NOT для CLI sprints.

**`performance-optimization` → Phase 6 OPT:** triggered backtest/replay sprints touching `src/backtest/`. Profile FIRST через cProfile/timeit. Avoid premature optimization. NOT для new code.

**`idea-refine` extension Phase 2 PRE:** explicit 5-step procedure ДО brainstorm-init когда operator vague idea. Skip если operator уже specified deliverables (S28-S32 pattern).

### Fetch MCP server rationale

`uvx mcp-server-fetch` — verified pre-installed (44 packages downloaded на test invocation). Use cases:
- Bybit V5 API docs lookup (https://bybit-exchange.github.io/docs/v5/)
- PyPI package version checks
- GitHub releases / CHANGELOG fetch

NOT для trading data fetch (use pybit V5 client с proper auth + rate limiting).

### Memory corpus scheme rationale

4 partitions chosen после analysis 17 existing observations:
- ~6 trading-decisions (S14/S17/S22/S23/S27 verdicts)
- ~3 formula-knowledge (S27 audit fixes)
- ~5 process-patterns (S28/S29/S30/S31/S32 kit improvements)
- ~3 debug-knowledge (S8a/S27 fix patterns)

Tag mapping based on existing frontmatter conventions across 33 sprint pages + 47 ADRs. Implementation deferred к S32d — needs claude-mem internal API research.

## Consequences

### Positive

1. **Skill coverage:** 32 → 36 skills mapped (17 agent-skills total, +4 в S32c)
2. **MCP servers:** 7 → 8 (+fetch для web docs lookup)
3. **Phase 2 PRE workflow** explicit — vague ideas refined ДО trader-expert dispatch (forecast: 30% reduction в trader ROUND 2 invocations)
4. **Dashboard quality** improved — Phase 5 browser-testing-with-devtools formal trigger
5. **Backtest performance gate** ready — Phase 6 perf-opt OPT formal trigger когда backtest > 30 sec
6. **Memory corpus scheme committed** — implementation в S32d has clear target

### Negative

1. **Memory corpus bridges 2-4 implementation deferred** — corpus continues flat (precision degrades через S33-S35 если не implement)
2. **Context budget hook deferred** — operator continues manual `/compact`, no proactive warning
3. **2nd CI run** — S32b CI infrastructure first time validates non-S32b PR (low risk — baseline guards designed для это)
4. **Fetch MCP requires session restart** — operator approve prompt at next `claude` start (one-time)

### Neutral

1. No code regression risk — config + docs only sprint
2. No FSM / reason codes / canonical state changes (16/30/74/45 unchanged)
3. Pattern continues S28-S32b (7-th consecutive non-trading sprint)

## Implementation

Per plan `2026-04-27-sprint-32c-kit-phase-2-improvements.md`:
- T1 → 0761bad (.mcp.json + tooling-inventory Section 7.7/7.8)
- T2 → 09fcdee (sprint-flow-ru.md 4 mappings + Skills × Phase 32→36)
- T3 → 47bba48 (tooling-inventory-ru.md Section 22 NEW)
- T4 → (this commit)

Tag: `v0.1.0-alpha.32c`.

## Follow-ups

**S32d candidate (Kit Phase 3 = Phase 2 deferred research + Phase 3 originals):**

Phase 2 deferred research items:
- Memory corpus org bridge 2 (corpus periodic sync) — auto-rebuild от wiki/log.md новых entries
- Memory corpus org bridge 3 (chapter mark auto-link к log.md)
- Memory corpus org bridge 4 implementation script (uses scheme от S32c Section 22)
- Context budget hook (>70% warn) — requires Claude Code hook API research

Original Phase 3 items (per S32 Phase 0 plan):
- bybit-api-reviewer L5 agent (Bybit V5 rate limits / endpoint params / error codes)
- anthropic-skills:schedule (audit_formulas.py automation)
- Sprint metrics tracking (velocity / revision rate)

**Test debt (carry-over к first trading sprint):**
- 3 pytest failures (test_replay_long_only / test_replay_next_open)
- 1 mypy error (__main__.py:636 bars_per_year_map redef)
- ~169 ruff baseline cleanup

**Trading carry-overs (BLOCKED — operator):**
- ESC-1 / ESC-2 / ESC-3

## Related

- ADR 0017 (review-agent harness) — L5 agent matrix policy
- ADR 0043 (S30 tier-2 agents + cascade) — bridges 2-4 origin
- ADR 0044 (S31 best practices revision) — kit baseline
- ADR 0045 (S32 Phase 0) — initial КУ analysis source + skill mappings precedent
- ADR 0046 (S32b Kit Phase 1) — direct predecessor + CI infrastructure foundation
- ADR 0047 (this) — Kit Phase 2 reduced scope implementation
- Anthropic Claude Code best practices: https://docs.claude.com/en/code/best-practices
- MCP server registry: https://github.com/modelcontextprotocol/servers/tree/main/src/fetch
