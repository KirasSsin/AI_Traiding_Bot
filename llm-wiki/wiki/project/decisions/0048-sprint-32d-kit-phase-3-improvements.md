---
title: ADR 0048 — Sprint 32d Kit Improvement Phase 3 final (bybit-api-reviewer + context budget hook + schedule wire + sprint metrics + corpus bridges research notes)
type: decision
tags: [adr, sprint-32d, kit-improvement, phase-3, bybit-reviewer, context-hook, sprint-metrics, corpus-research, s32-series-complete]
created: 2026-04-27
updated: 2026-04-27
status: accepted
sources:
  - project/plans/2026-04-27-sprint-32d-kit-phase-3-improvements.md
  - project/decisions/0047-sprint-32c-kit-phase-2-improvements.md
  - project/decisions/0046-sprint-32b-kit-phase-1-improvements.md
  - project/decisions/0045-sprint-32-kit-phase-0-improvements.md
  - project/SPRINT_STATE.md
---

# ADR 0048 — Sprint 32d Kit Improvement Phase 3 (S32 series FINAL)

## Status

Accepted (2026-04-27) — implemented in S32d (`feature/sprint-32d-kit-phase-3-improvements` → tag `v0.1.0-alpha.32d`). Sub-sprint S32 series **FINAL**. After ship → S33 trading work begins.

## Context

Per ADR 0047 carry-overs, Kit Phase 3 = 7 items total (Phase 2 deferred research + Phase 3 originals). Pre-plan analysis revealed:
- 4 implementations = clear wins
- 3 research items (memory corpus bridges 2-4) = claude-mem internal API constraints, plugin not maintained by us

**Honest scope decision:** S32d ships 5 changes + research notes documenting feasibility. S32 series concluded. After S32d → S33 trading sprint preparation.

**Pain points addressed:**

1. **No Bybit-specific reviewer** — trading-logic-reviewer focuses на business logic, не API protocol details. Bybit V5 retCodes, schema versions, sign format require specialist
2. **Reactive context overflow management** — operator notices session sluggish после fact, /compact too late
3. **No formal audit_formulas.py automation** — manual invocation only, regressions могут go undetected
4. **No sprint metrics tracking** — velocity / revision rate / КУ blind, can't measure kit improvement effectiveness
5. **Memory corpus bridges 2-4 vague status** — deferred S30+S31, no honest feasibility assessment

## Options

**Option A: Full Phase 3 — все 7 items implemented**
- Pros: всё ship'd, no carry-overs
- Cons: corpus bridges 2-4 = 6-10 hours focused research для marginal benefit (corpus only 17 obs), risk burning operator time

**Option B: Reduced scope — 4 implementations + research notes**
- Pros: Predictable ship, clear deliverables, КУ ~45% / 2.5-3 hours, S32 series concluded cleanly
- Cons: corpus bridges remain undocumented in deep — но research notes provide enough для future revisit

**Option C: Skip S32d, jump directly к S33 trading**
- Pros: One sprint less, faster к trading work
- Cons: Lose 4 quick wins (bybit-reviewer / context hook / schedule wire / metrics tracking) + corpus bridges status remains vague

## Decision

**Option B selected.** Sprint 32d = Kit Phase 3 = 5 changes:

| # | Change | Type | КУ % |
|---|--------|------|------|
| T1 | bybit-api-reviewer L5 agent (out-of-repo + wiki page) | L5 agent | 50% |
| T2 | Context budget hook MVP (transcript size warning, advisory) | Hook (UserPromptSubmit) | 46% |
| T3 | anthropic-skills:schedule wire docs (Section 23) + Sprint metrics tracking template | Process / metrics | 38% |
| T4 | Memory corpus bridges 2-4 research notes (Section 24 — feasibility + recommendations) | Wiki research | 30% |
| T5 | ADR 0048 + sprint-32d page + index/counts sync (47→48 ADRs / 34→35 sprints / 40→43 components / 10→11 agents) | Wiki sync | 42% |

**КУ avg ~41%** / ~2.5 hours forecast.

### S32 series complete — accumulated achievements

| Metric | Pre-S32 baseline | Post-S32d | Δ |
|--------|------------------|-----------|---|
| Reviewer agents (L5) | 9 | **11** | +2 (dashboard-reviewer + bybit-api-reviewer) |
| Active push hooks | 6 | **7** | +1 (sprint-state-freshness-check) |
| UserPromptSubmit hooks | 1 (caveman) | **2** | +1 (context-budget-warn) |
| MCP servers | 6 | **8** | +2 (sqlite-trading + fetch) |
| Skills × Phase mapped | 26 | **36** | +10 (S32 +6 / S32c +4) |
| Components | 38 | **43** | +5 (dashboard-reviewer + freshness-hook + bybit-api-reviewer + context-budget-hook + sprint-metrics) |
| ADRs | 44 | **48** | +4 (0045/0046/0047/0048) |
| Sprint pages | 31 | **35** | +4 (sprint-32 + sprint-32b + sprint-32c + sprint-32d) |
| CI infrastructure | NO | **YES** | GitHub Actions + pre-commit + baseline guards (S32b) |
| Memory corpus design | flat | **scheme designed (Section 22)** | bridge 4 spec ready (script S32d declined as not recommended) |
| Sprint metrics tracking | NO | **YES** (sprint-metrics.md NEW) | Per-sprint table + trends |

### Bybit-api-reviewer rationale

Specialist L5 agent для Bybit V5 protocol correctness:
- Rate limits (600 req/min spot)
- Order param validation (lotSizeFilter / priceFilter)
- WebSocket schema (V5 data list, ms timestamps)
- retCode handling (10001-170134)
- HMAC SHA256 sign format
- 6-axis review checklist

Fills gap между trading-logic-reviewer (business logic) и data-integrity-reviewer (storage). Sonnet model, parallel-dispatchable.

### Context budget hook MVP rationale

Crude transcript file size proxy для context %. NOT exact token counter (would require 8-12h focused work). MVP version 30 min:
- WARN_KB=800 (~60% context)
- URGENT_KB=1200 (~80% context)
- UserPromptSubmit hook, advisory only (exit 0 always)
- Tested 4 scenarios: small/yellow/red/missing-path

Future iteration (S33+ kit work если operator wants): exact token counter via JSONL parse + tokenizer.

### Schedule wire rationale

Docs only — schedule registration happens at session level через MCP tool. Operator setup procedure documented Section 23. Frequency recommendations: weekly active dev, monthly stable, daily pre-release.

### Sprint metrics rationale

Process visibility — without metrics, kit improvement effectiveness unknown. Table tracks: tasks / bugs / review iterations / pytest count / КУ avg / time / КУ/час. Manual update at PHASE 9 Close per `sprint-finish` skill extension.

КУ retroactively N/A для pre-S32 sprints (would require effort estimate from logs). S32 series fully tracked.

### Corpus bridges research notes rationale

Honest feasibility assessment vs more sprint cycles wasted on attempted implementations:

| Bridge | Cost | Value | Recommendation |
|--------|------|-------|----------------|
| Bridge 2 (cron rebuild) | LOW | MEDIUM | ✅ Operator setup S33+ |
| Bridge 3 (chapter auto-link) | MEDIUM | LOW | ⏸️ Defer |
| Bridge 4 (partition impl) | HIGH | LOW (corpus small) | ❌ NOT recommended until corpus > 100 obs |

S32c scheme docs (Section 22) provide stable design ready для future implementation если priorities change.

## Consequences

### Positive

1. **Bybit V5 protocol coverage** — bybit-api-reviewer fills gap, money-touching code больше не reviewed только generic agents
2. **Proactive context management** — context-budget-warn warns 60%/80%, prevents session crash
3. **audit_formulas automation ready** — operator one-time setup → weekly auto-run
4. **Sprint metrics visible** — kit improvement ROI measurable, future kit sprints data-driven
5. **Corpus bridges honest status** — feasibility documented, no more vague carry-overs
6. **S32 series complete** — kit infrastructure mature, attention shifts к S33 trading work

### Negative

1. **Context budget hook crude** — file size proxy off by 2-3× depending на content density. Not exact token count. Mitigated через conservative thresholds.
2. **Bridge 4 (corpus partition) not implemented** — high effort vs low current value. Re-evaluate когда corpus > 100 observations.
3. **Schedule wire requires operator action** — not auto-deployed (session-level MCP tool). Documented в Section 23.
4. **Sprint metrics retroactive incomplete** — pre-S32 sprints not tracked.
5. **bybit-api-reviewer first-time validation pending** — agent prompt не tested на real Bybit code review yet (will validate at S33+ first trading sprint).

### Neutral

1. No code regression risk — config + scripts + docs только sprint
2. No FSM / reason codes / canonical state changes (16/30/74/45 unchanged)
3. Pattern continues S28-S32c (8-th consecutive non-trading sprint) — series ends here
4. CI infrastructure (S32b) validated 3rd PR (S32d) — confirms ongoing reliability

## Implementation

Per plan `2026-04-27-sprint-32d-kit-phase-3-improvements.md`:
- T1 → a15ff4c (bybit-api-reviewer wiki page; agent file out-of-repo)
- T2 → e87d532 (context-budget-warn wiki page; hook + settings.json out-of-repo)
- T3+T4 → 2707f6f (Section 23 + Section 24 + sprint-metrics.md)
- T5 → (this commit)

Tag: `v0.1.0-alpha.32d`.

## Follow-ups

**S33 trading sprint preparation (operator action):**
1. Resolve ESC-1/2/3 (multi-symbol authorization / "in profit" semantics / 4H operational)
2. Brainstorm S33 scope (single-symbol BTC mean-reversion regime-confirmed per S22? OR multi-symbol pending ESC-1?)
3. Approve fetch MCP at next session start (one-time prompt — same pattern S32b sqlite-trading)
4. Optional: setup audit_formulas.py weekly schedule per Section 23
5. Optional: setup corpus bridge 2 (cron rebuild) per Section 24

**Test debt (carry-over к first trading sprint):**
- 3 pytest failures (test_replay_long_only / test_replay_next_open)
- 1 mypy error (__main__.py:636 bars_per_year_map redef)
- ~169 ruff baseline cleanup

**Trading carry-overs (BLOCKED — operator decisions required):**
- ESC-1 multi-symbol authorization
- ESC-2 "in profit" semantics
- ESC-3 4H operational implications

**Kit work future (low priority unless blocker):**
- Bridge 4 corpus partition implementation (when corpus > 100 obs, likely S40+)
- Context budget hook exact token counter (вместо file size proxy)
- bybit-api-reviewer first real-world validation (at S33+ Bybit-touching sprint)

## Related

- ADR 0017 (review-agent harness) — L5 agent matrix policy (bybit-api-reviewer = 11-th agent)
- ADR 0044 (S31 best practices) — kit baseline + context discipline references
- ADR 0045/0046/0047 (S32 series Phase 0/1/2) — direct predecessors
- ADR 0048 (this) — Kit Phase 3 final S32 series sprint
- Sprint S32 / S32b / S32c / S32d (this) — S32 series Phase 0/1/2/3 COMPLETE
- Anthropic Claude Code best practices: https://docs.claude.com/en/code/best-practices
- Bybit V5 API docs: https://bybit-exchange.github.io/docs/v5/
