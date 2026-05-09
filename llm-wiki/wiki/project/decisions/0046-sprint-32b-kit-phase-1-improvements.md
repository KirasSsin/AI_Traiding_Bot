---
title: ADR 0046 — Sprint 32b Kit Improvement Phase 1 (CI + pre-commit + SQLite MCP + freshness hook + dashboard-reviewer)
type: decision
tags: [adr, sprint-32b, kit-improvement, phase-1, ci-cd, pre-commit, sqlite-mcp, freshness-hook, dashboard-reviewer, ku-driven]
created: 2026-04-27
updated: 2026-04-27
status: accepted
sources:
  - project/plans/2026-04-27-sprint-32b-kit-phase-1-improvements.md
  - project/decisions/0045-sprint-32-kit-phase-0-improvements.md
  - project/decisions/0044-sprint-31-kit-revision-best-practices.md
  - project/SPRINT_STATE.md
---

# ADR 0046 — Sprint 32b Kit Improvement Phase 1

## Статус

Accepted (2026-04-27) — implemented in S32b (`feature/sprint-32b-kit-phase-1-improvements` → tag `v0.1.0-alpha.32b`). Sub-sprint S32 series (mirror S8a/S8b/S8c pattern).

## Контекст

Per ADR 0045 carry-overs, Kit Phase 1 = 5 changes с КУ avg 63%, time 4-6 hours (forecast 10.5 КУ/час). Operator directive (session 2026-04-27): continue с Phase 1 в S32 series, не open S33. Trading work blocked via ESC-1/2/3 → S32 series занимает sprint slots без conflict.

**Pain points addressed:**

1. **No CI gate** — каждый PR merge = manual pytest run. Risk silent regression. Pre-S32b: 3 pytest failures pre-existed на main (test_replay_long_only / test_replay_next_open) — surfaced ONLY на S32 Phase 5 verify, not earlier
2. **No local pre-commit gate** — ruff/mypy errors caught only после push (CI или manual). Adds latency
3. **SQLite debugging via shell hack** — execution state / fills / halts queries через `sqlite3 ./data/bot.db "SELECT..."`. Verbose, error-prone
4. **SPRINT_STATE staleness recurrence risk** — S32 Phase 0 fixed P0 staleness, но nothing prevents recurrence в next sprints
5. **Dashboard module не имеет specialist reviewer** — python-reviewer (haiku) generic, не знает S25 ADR 0039 conditions / FastAPI patterns

## Варианты

**Option A: Single big sprint covering Phase 1 + Phase 2 (memory corpus org + remaining mappings)**
- Pros: всё сразу
- Cons: scope слишком большой; CI + memory org оба требуют experimentation; conflate process improvements

**Option B: Phased rollout — Phase 1 only S32b, Phase 2 → S32c**
- Pros: incremental ROI; CI/SQLite MCP infrastructure isolated; allows failure recovery (если CI broken, easy revert)
- Cons: extra sprint cycle для Phase 2

**Option C: Skip CI/MCP infrastructure, focus только doc improvements**
- Pros: zero infrastructure risk
- Cons: ignores 74% КУ items (CI + pre-commit), continues silent regression risk

## Решение

**Option B selected.** Sprint 32b = Kit Phase 1 = 6 changes:

| # | Change | Type | КУ % |
|---|--------|------|------|
| T1 | dashboard-reviewer L5 agent (out-of-repo + wiki page) | L5 agent | 50% |
| T2 | sprint-state-freshness-check.sh hook (out-of-repo + wiki page + settings.json) | Hook | 58% |
| T3 | Pre-commit hooks upgraded (.pre-commit-config.yaml: ruff v0.4.0 + mypy --strict + yamllint) | Local gate | 74% |
| T4 | GitHub Actions CI (.github/workflows/ci.yml: TA-Lib + ruff + mypy baseline + pytest baseline + canonical counts) | CI gate | 74% |
| T5 | SQLite MCP server (.mcp.json sqlite-trading → data/bot.db) | MCP | 66% |
| T6 | ADR 0046 + sprint-32b page + index sync + canonical counts | Wiki sync | 42% |

**КУ avg 60.5%** (close к forecast 63%). Time invested: ~3 hours (faster than 6h forecast — некоторые items pre-built i.e. `pre-commit` уже в dev deps).

### Settings.json schema constraint discovered

During T5 implementation: `settings.json` schema REJECTS `mcpServers` field (validation error). MCP server config goes в project-level `.mcp.json` instead, then enabled через `enabledMcpjsonServers` в settings (or `enableAllProjectMcpServers: true`). Documented в ADR Consequences.

### Hook regex iteration (T2)

First version of freshness hook flagged carry-over context references (S14 Q2 carry-over). Refined to actionable patterns only:
```
S[0-9]+[^A-Za-z0-9].{0,30}(PHASE [0-9]|ship|pending|in_progress|next action|in progress)
```
This avoids false positives для legitimate historical references.

### CI baseline guards

CI пропускает на baseline failures (3 pytest pre-existing + 1 mypy pre-existing) — informational gates. Strict guards trip ONLY на regression (count > baseline). This unblocks S32b ship despite test debt carry-over.

## Последствия

### Positive

1. **CI gate active:** Every PR + push к main runs pytest + mypy + ruff + canonical counts verify. Silent regression больше невозможна
2. **Local pre-commit:** Ruff + mypy + yamllint каждый commit. Catches errors ДО push (saves CI cycle)
3. **SQLite debugging:** Direct queries `SELECT * FROM execution_states` через MCP. Speed +40% для debug sessions (forecast)
4. **Freshness hook active:** P0 staleness recurrence mechanically prevented. 6th hook (was 5)
5. **Dashboard reviewer:** L5 specialist для FastAPI + vanilla JS. python-reviewer no longer overloaded для dashboard scope
6. **Skill counts:** 9 → 10 reviewer agents / 6 → 7 active push hooks / 6 → 7 MCP servers (including new sqlite-trading)

### Negative

1. **CI run time:** ~5-8 min per PR (TA-Lib build dominates). Cached after first run.
2. **Pre-commit local cost:** Adds 5-30 sec per commit (mypy slowest). Operator может --no-verify если urgent
3. **Settings.json constraint:** MCP server config split (`.mcp.json` + `enabledMcpjsonServers`). Two-file edit для adding new MCP. Mitigated через documenting в tooling-inventory-ru.md
4. **Hook chain growth:** 6 → 7 push hooks. Each push fires all 7. Per-hook cost ~50-100ms (negligible)
5. **First-time MCP approval:** SQLite MCP requires session restart + operator approve prompt (per Claude Code MCP security policy)

### Neutral

1. No code regression risk — config + scripts + docs only sprint
2. No FSM / reason codes / canonical state changes (16/30/74/45 unchanged)
3. Pattern continues S28-S32 (6-th consecutive non-trading sprint)

## Реализация

Per plan `2026-04-27-sprint-32b-kit-phase-1-improvements.md`:
- T1 → 6c2ea66 (dashboard-reviewer wiki page; agent file out-of-repo)
- T2 → 373d527 (freshness hook wiki page; hook + settings.json out-of-repo)
- T3 → (commit pending T6 batch) (.pre-commit-config.yaml upgrade)
- T4 → 167fc9d (.github/workflows/ci.yml)
- T5 → 8a24abf (.mcp.json)
- T6 → (this commit)

Tag: `v0.1.0-alpha.32b`.

## Дальнейшие действия

**S32c candidate (Kit Phase 2, КУ avg 42%):**
- Memory corpus organization (bridges 2-4 deferred from S30 + S31)
- Context budget hook (>70% warn)
- AS:performance-optimization mapping (Phase 6 backtest)
- AS:api-and-interface-design mapping (Phase 3)
- AS:browser-testing-with-devtools mapping (Phase 5 dashboard)
- AS:idea-refine extension (Phase 2 PRE)
- Fetch/HTTP MCP

**S32d candidate (Kit Phase 3, КУ avg 30%):**
- bybit-api-reviewer L5 agent
- anthropic-skills:schedule (audit automation)
- Sprint metrics tracking

**Test debt (immediate carry-over к S33+ trading sprint):**
- Fix 3 pytest failures (test_replay_long_only / test_replay_next_open)
- Fix 1 mypy error (`__main__.py:636 bars_per_year_map redef`)

**Trading carry-overs (BLOCKED — operator):**
- ESC-1 / ESC-2 / ESC-3

## Связанные документы

- ADR 0017 (review-agent harness) — L5 dashboard-reviewer pattern
- ADR 0041 (S28 process enforcement) — sprint-flow-check.sh predecessor pattern для freshness hook
- ADR 0043 (S30 tier-2 agents) — phase-advance.sh predecessor pattern
- ADR 0044 (S31 best practices revision) — kit baseline
- ADR 0045 (S32 Phase 0) — direct predecessor (КУ analysis source)
- ADR 0046 (this) — Kit Phase 1 implementation
- Anthropic Claude Code best practices: https://docs.claude.com/en/code/best-practices
- [[../sprints/sprint-32b-kit-phase-1-improvements]] — спринт delivery record
- MCP server registry: https://github.com/modelcontextprotocol/servers/tree/main/src/sqlite (mcp-server-sqlite source)
