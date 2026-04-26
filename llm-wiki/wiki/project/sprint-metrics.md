---
title: Sprint Metrics — velocity / revision rate / KU / time tracking
type: metrics
tags: [metrics, velocity, revision-rate, ku, sprint-tracking, kit-improvement]
created: 2026-04-27
updated: 2026-04-27
status: active
sources:
  - project/decisions/0048-sprint-32d-kit-phase-3-improvements.md
  - project/SPRINT_STATE.md
---

# Sprint Metrics

**TL;DR:** Manual per-sprint update at PHASE 9 Close. Tracks velocity (tasks/sprint), bugs found, review iterations, КУ achieved, time invested.

**Update protocol:** PHASE 9 Close skill (`sprint-finish`) extension — see "Update protocol" section bottom.

## Per-sprint table

Newer sprints добавляются вверху (reverse chronological).

| Sprint | Tasks | Bugs found | Review iterations | Pytest count | КУ avg | Time | КУ/час | Notes |
|--------|-------|-----------|-------------------|--------------|--------|------|--------|-------|
| S32d | 5 | 0 | 0 | 773 (TBD) | TBD | TBD | TBD | Kit Phase 3 final S32 series |
| S32c | 4 | 0 | 0 | 773 | 51% | 1.5h | 75 | Kit Phase 2 reduced — 4 skill mappings + Fetch MCP + corpus scheme docs |
| S32b | 6 | 0 | 0 | 773 | 60.5% | 3h | 120 | Kit Phase 1 — CI + pre-commit + SQLite MCP + freshness hook + dashboard-reviewer (CI 3 fix iterations) |
| S32 | 6 | 0 | 0 | 773 | 60% | 45 min | 80 | Kit Phase 0 — P0 staleness fix + 5 skill mappings + cascade smart-explore + Phase 9 consolidate-memory |
| S31 | 6 | 0 | 0 | 762 | — | — | — | Kit Revision per Best Practices (kit-overview-ru NEW + CLAUDE.md prune -25%) |
| S30 | 8 | 0 | 0 | 762 | — | — | — | Tier-2 Agents (security/test/doc) + phase-advance hook + cascade |
| S29 | 4 | 0 | 0 | 762 | — | — | — | Full Superpowers Skills Integration (7 NEW skills + Skills × Phase map) |
| S28 | 6 | 0 | 0 | 762 | — | — | — | Process enforcement (sprint-flow-check hook + Russian process docs) |
| S27 | 8 | 5 (formula) | 12 | 762 | — | — | — | Formula bug fixes — TDD 5 bugs |
| S25 | — | 0 | 0 | 740 | — | — | — | Dashboard UI sprint |
| S23 | — | — | — | 712 | — | — | — | v0.5 honest close |
| S22 | — | — | — | 712 | — | — | — | BTC 4H test (62 trades, FAIL T5) |

**Note:** КУ tracking introduced S32 (kit improvement series). Pre-S32 sprints — КУ/time не measured retrospectively (would require effort estimate from logs).

## Trends (rolling 5 sprints, S32-S32d)

- **Velocity:** avg 5.4 tasks/sprint (S32 series 5/6/4/5/?)
- **Bug detection:** 0 bugs/sprint (process/wiki/config sprints — expected)
- **КУ trend:** 60% → 60.5% → 51% → ? (declining slightly per phase due reduced scope)
- **Time trend:** 45min → 3h → 1.5h → ? (Phase 1 outlier due CI 3 fix iterations)
- **КУ/час trend:** 80 → 120 → 75 → ? (Phase 1 best ROI due pre-installed deps)

## Definitions

- **Tasks** = Per-sprint plan T1-TN count completed
- **Bugs found** = Phase 5/6 reviewer outputs (BLOCKER/HIGH severity)
- **Review iterations** = Phase 6 reviewer dispatch count (1 if first-pass approved, 2+ if blocker→fix→re-review)
- **Pytest count** = Final passed count from Phase 5 verify output
- **КУ avg** = Mean КУ % across all tasks (per ADR 0045 methodology)
- **Time** = Total session duration (estimate)
- **КУ/час** = КУ avg / hours = ROI

## Update protocol (PHASE 9 Close — `sprint-finish` skill extension)

After SPRINT_STATE → between-sprints commit:

1. Count tasks completed (from sprint page Deliverables table)
2. Count bugs found (from Phase 5/6 reviewer outputs OR pre-existing baseline preserved = 0)
3. Count review iterations (Phase 6 reviewer dispatch count, includes fix→re-review cycles)
4. Read pytest passed count from Phase 5 verify Bash output
5. Compute КУ avg from sprint page (per-task table)
6. Time = total session duration estimate (от first commit к final tag push)
7. КУ/час = КУ avg / hours
8. Append row к table выше (newest at top)
9. Update Trends section если 5+ sprints accumulated в same series

## Insights (S32 series retrospective — to be filled at S32d Close)

- **Pattern:** Sub-sprint S32 series (a/b/c/d) — operator directive "пусть все фазы будут в 32 спринте"
- **КУ degradation per phase** — Phase 0 (60%) → Phase 1 (60.5%) → Phase 2 (51%) → Phase 3 (?). Expected: easier wins shipped first.
- **Time variance** — Phase 1 outlier (3h vs avg 1-1.5h) due 3 CI fix iterations
- **Pre-installed deps boost** — uvx, pre-commit, mcp-server-sqlite, mcp-server-fetch уже installed → faster ship

## Related

- [[decisions/0045-sprint-32-kit-phase-0-improvements]] — КУ methodology established
- [[decisions/0046-sprint-32b-kit-phase-1-improvements]] — CI infrastructure
- [[decisions/0047-sprint-32c-kit-phase-2-improvements]] — Reduced scope decision pattern
- [[decisions/0048-sprint-32d-kit-phase-3-improvements]] — Sprint metrics tracking introduced
- [[architecture/tooling-inventory-ru#23-anthropic-skillsschedule-wire-к-audit_formulaspy-s32d]] — schedule wire automation
