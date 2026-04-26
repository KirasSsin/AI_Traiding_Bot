---
title: dashboard-reviewer (L5 reviewer agent для src/dashboard/)
type: component
tags: [agent, l5-reviewer, dashboard, fastapi, vanilla-js, sonnet, sprint-32b]
created: 2026-04-27
updated: 2026-04-27
status: stable
sources:
  - ~/.claude/agents/dashboard-reviewer.md
  - project/decisions/0046-sprint-32b-kit-phase-1-improvements.md
  - project/decisions/0039-sprint-25-dashboard.md
  - project/sprints/sprint-25-dashboard.md
  - project/sprints/sprint-26-dashboard-redesign.md
---

# dashboard-reviewer (L5 reviewer agent)

**TL;DR:** Specialized L5 reviewer agent для `src/dashboard/` module. Sonnet model. Reviews FastAPI + Jinja2 + vanilla JS code per S25 ADR 0039 architecture conditions + trader spec compliance.

## Block 1 — Code refs

| Element | Anchor |
|---------|--------|
| Agent prompt | `~/.claude/agents/dashboard-reviewer.md` (out-of-repo) |
| Scope target | `src/dashboard/` (FastAPI app + templates + JS + CSS) |
| Created in | ADR 0046 (Sprint 32b Kit Phase 1) |
| Trigger pattern | After dashboard module changes OR pre-merge для S25/S26-class sprints |

## Block 2 — Description

### Назначение

L5 domain reviewer для dashboard module. Заполняет gap между python-reviewer (generic Python) и architecture-reviewer (cross-module). Specializes на FastAPI patterns, vanilla JS quality, trader spec compliance, S25 architecture conditions enforcement.

### Когда invoke

- ANY change в `src/dashboard/` module
- Pre-merge для sprints touching dashboard
- Post-implementation для new dashboard features

### Не scope

- Trading strategy logic → `trading-logic-reviewer`
- Math formulas → `quant-stats-reviewer`
- Storage / migrations → `data-integrity-reviewer`
- Generic Python → `python-reviewer` (после dashboard-reviewer)
- Money/security trading state mutation → `security-auditor` (если dashboard violates read-only condition — flag as BLOCKER)

### Review checklist (5 axes)

1. **FastAPI correctness** — response models, error handling, validation, CORS, TESTNET enforcement, async/sync, DI, background tasks
2. **Template & JS data flow** — Jinja2 vars match endpoint, fetch error handling, memory leaks, DOM batching, accessibility
3. **Bybit/backtest data display** — no look-ahead, UTC timestamps, trader spec (TIER 1/2 + 4 warnings + Sortino guard), strategy presets, MVP symbol filter
4. **Security** — no secrets в JS, no eval(), HTML escaping, read-only enforcement, rate limiting, input validation
5. **Architecture** (per S25 conditions) — process isolation, optional dep, read-only data, isolated context, graceful degradation

### Output format

Per `superpowers:requesting-code-review` standard: Blockers / Concerns / Verified / Follow-ups for wiki.

Severity: BLOCKER (security / look-ahead / TESTNET / live trading violation) / HIGH (correctness) / MEDIUM (perf / a11y) / LOW (style).

### Configuration

| Setting | Value |
|---------|-------|
| Model | claude-sonnet-4-5 |
| Memory | project (auto-creates `.claude/agent-memory/dashboard-reviewer/MEMORY.md` on first WRITE) |
| Tools | Read, Grep, Glob, Bash (read-only access) |

## Related

- [[../decisions/0017-review-agent-harness]] — L5 agent matrix policy
- [[../decisions/0039-sprint-25-dashboard]] — S25 dashboard architecture (APPROVE_WITH_CONDITIONS)
- [[../decisions/0046-sprint-32b-kit-phase-1-improvements]] — этот agent создан здесь
- [[../sprints/sprint-25-dashboard]] — S25 dashboard sprint
- S26 (no separate sprint page — UI/CSS-only redesign, no ADR; tag v0.1.0-alpha.26)
- [[../sprints/sprint-32b-kit-phase-1-improvements]] — S32b Kit Phase 1 (agent creation)
