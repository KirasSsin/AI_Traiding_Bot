---
title: Kit Overview — единая точка входа для всех настроек kit'а (русская версия)
type: architecture
tags: [kit, overview, single-source-of-truth, quick-reference, ru]
created: 2026-04-26
updated: 2026-04-26
status: stable
sources:
  - project/architecture/sprint-flow-ru.md
  - project/architecture/tooling-inventory-ru.md
  - project/decisions/0017-review-agent-harness.md
  - project/decisions/0041-sprint-28-process-enforcement.md
  - project/decisions/0042-sprint-29-superpowers-integration.md
  - project/decisions/0043-sprint-30-tier-2-agents-mem-wiki-merge.md
  - project/decisions/0044-sprint-31-kit-revision-best-practices.md
  - https://docs.claude.com/en/code/best-practices
---

# Kit Overview (RU) — single source of truth

> **TL;DR:** 1-страничный gateway ко всем настройкам kit'а. Detail в linked docs.
>
> **Когда читать:** Старт сессии / `/clear` / "что у нас есть в kit'е"
> **Когда обновлять:** Каждый sprint после ship (1 строка в "Sprint history")

## ⚡ Quick decision matrix (что invoke когда)

| Задача | Tool / Skill |
|--------|--------------|
| **Старт сессии** / `/clear` | `sprint-orient` skill |
| Vague operator idea (pre-brainstorm) | `agent-skills:idea-refine` 🆕 (S32) |
| Sprint scope с trading questions | `brainstorm-init` skill → `trader-expert` agent |
| Sprint scope не trading | `superpowers:brainstorming` skill |
| Non-trading feature без spec | `agent-skills:spec-driven-development` 🆕 (S32) |
| **Plan writing** (HARD-GATE — hook block) | `superpowers:writing-plans` skill → `wiki/project/plans/<date>-sprint-N-<slug>.md` |
| Execute plan code-heavy | `superpowers:subagent-driven-development` |
| Execute plan docs-heavy | `superpowers:executing-plans` (controller) |
| **TDD** каждая code task | `superpowers:test-driven-development` (RED→GREEN→COMMIT) |
| Bybit/pydantic/pybit/FastAPI/TA-Lib code | `agent-skills:source-driven-development` 🆕 (S32) — verify docs first |
| Structural code lookup ("where is X used?") | `claude-mem:smart-explore` 🆕 (S32) |
| **Bug encountered** | `superpowers:systematic-debugging` (4-phase) |
| Parallel reviewers / research | `superpowers:dispatching-parallel-agents` |
| **Pre-completion verify** (HARD-GATE — hook block) | `superpowers:verification-before-completion` checklist |
| Reviewer brief format | `superpowers:requesting-code-review` |
| Reviewer feedback processing | `superpowers:receiving-code-review` |
| Code в `src/risk/` `signalgen/` `execution/` `backtest/` | `trading-logic-reviewer` agent |
| Math формулы | `quant-stats-reviewer` agent |
| Storage / migrations / parquet | `data-integrity-reviewer` agent |
| Cross-module refactor / concurrency / DI | `architecture-reviewer` agent |
| Generic Python | `python-reviewer` agent (после domain) |
| **Money / API / override / Mainnet** | `security-auditor` agent (opus) |
| **New module без tests** / property test design | `test-engineer` agent |
| Wiki consistency check | `doc-reviewer` agent (haiku) |
| Sprint complete | `sprint-finish` skill → `superpowers:finishing-a-development-branch` |
| ADR creation per sprint | `agent-skills:documentation-and-adrs` 🆕 (S32) |
| Post-impl cleanup сложных формул | `agent-skills:code-simplification` 🆕 (S32) |
| После src/ change | `wiki-update` skill |
| Sprint Close (every 5 OR >30 obs) | `anthropic-skills:consolidate-memory` 🆕 (S32) |
| Side question (no context pollution) | `/btw` |
| Restore previous state | `/rewind` (Esc+Esc) |
| Reset context unrelated tasks | `/clear` |
| Continue prev session | `claude --continue` / `--resume` |
| Search past sessions | `mem-search` MCP |
| Chapter mark | `mark_chapter` MCP |

## 📚 Cascade rule (BINDING per ADR 0043 + ADR 0045 S32 — token economy)

При любом lookup ВСЕГДА следуй cascade order (5 шагов после S32):

```
STEP 1: wiki/<page>.md             (curated)                          ← CHECK FIRST
   ↓ not found
STEP 2: mem-search                 (past sessions)
   ↓ not found
STEP 2.5: claude-mem:smart-explore (token-optimized structural code)  ← NEW (S32)
   ↓ needed
STEP 3: Grep raw                   (current code, text match)
   ↓ needed
STEP 4: Read + offset              (full content)
```

**Когда STEP 2.5 vs STEP 3:**
- STEP 2.5 = structural questions ("where is X used?", call graph, file relationships)
- STEP 3 = exact text matching (regex, specific string lookup)

Anti-patterns:
- ❌ Skip wiki check → straight к Read raw (loses curation, increases tokens)
- ❌ Naked Grep для structural questions (smart-explore = 30-50% дешевле)

Detail: [[tooling-inventory-ru#13-llmwiki--claude-mem-cascade-rule-s30-adr-0043]]

## 🛡️ Active Hooks (7 push + 2 UserPromptSubmit + 1 session — mechanical enforcement)

| Hook | Triggers | Block если |
|------|----------|-----------|
| `adr-agent-sync-check.sh` | git push | ADR changed без agent prompt touch |
| `adr-index-sync-check.sh` | git push | New ADR без index.md entry |
| `wiki-broken-link-check.sh` | git push | Broken `[[wiki-link]]` |
| `sprint-flow-check.sh` (S28+) | git push | feature/sprint-NN-* без plan file |
| `phase-advance.sh` (S30+) | gh pr merge | SPRINT_STATE Phase 5 != done/skipped |
| `sprint-state-freshness-check.sh` 🆕 (S32b+) | git push | "Следующее действие" references S<N-2> с actionable patterns (PHASE X ship/pending/in_progress/next) |
| `context-budget-warn.sh` 🆕 (S32d) | UserPromptSubmit (every prompt) | Advisory warning при transcript > 800KB ~60% (yellow) / > 1200KB ~80% (red). Always exits 0. |
| `caveman-*` | session lifecycle | Caveman mode tracking (not push-related) |

## 👥 Reviewer agents (11 — `~/.claude/agents/`)

| Agent | Model | Когда |
|-------|-------|-------|
| `trader-expert` | sonnet 4.6 effort:max | PHASE 2 trading scope decisions (CONFIRM/REVISE/DEFER/EXPAND) |
| `trading-logic-reviewer` | sonnet 4.6 | `src/{signalgen,execution,backtest,risk}/` changes |
| `quant-stats-reviewer` | sonnet 4.6 effort:max | Math formulas (DSR/Kelly/MC/RSI/ATR) |
| `data-integrity-reviewer` | sonnet | Storage / migrations / parquet / WAL |
| `architecture-reviewer` | sonnet 4.6 | Cross-module refactor / concurrency / DI / API |
| `python-reviewer` | haiku | Generic Python (после domain) |
| `security-auditor` 🆕 | **opus** | Money / API / override / Mainnet (BLOCKER/HIGH/MEDIUM/LOW) |
| `test-engineer` 🆕 | sonnet | Test pyramid / Hypothesis property / coverage / regression |
| `doc-reviewer` 🆕 | **haiku** (lightweight) | Frontmatter / links / Block 1↔2 sync / canonical counts |
| `dashboard-reviewer` 🆕 (S32b) | sonnet | `src/dashboard/` FastAPI + vanilla JS (5-axis review per S25 ADR 0039 conditions) |
| `bybit-api-reviewer` 🆕 (S32d) | sonnet | Bybit V5 Spot API protocol correctness (6-axis: rate limits / order params / WS schema / retCodes / pagination / HMAC sign) |

## 🔧 Project skills (5 — `.claude/skills/`)

| Skill | Auto-trigger |
|-------|--------------|
| `sprint-orient` | Session start / `/clear` / "ориентируйся" |
| `brainstorm-init` | "брейнштурм" / scope questions surface |
| `wiki-update` | После src/ change |
| `sprint-finish` | "ship" / "финишируем" |
| `hook-test` | `/hook-test` explicit only |

## 🎁 Plugin skills (~50 — auto-loaded)

| Plugin | Skills |
|--------|--------|
| superpowers (5.0.7) | 13 (brainstorming / writing-plans / subagent-driven / TDD / systematic-debugging / verification-before-completion / requesting-code-review / receiving-code-review / dispatching-parallel-agents / using-git-worktrees / writing-skills / using-superpowers / finishing-a-development-branch) |
| addy-agent-skills (1.0.0) | 21 (depth checklists — TDD / debugging / code-review / security / performance / planning / spec / shipping / etc) |
| claude-mem (12.3.7) | 7 (mem-search / version-bump / knowledge-agent / smart-explore / etc) |
| caveman (84cc3c14fa1e) | 5 (caveman mode / compress / commit / etc) |

## 🔌 MCP servers (8)

| MCP | Назначение |
|-----|-----------|
| `plugin_claude-mem_mcp-search` | Semantic search past sessions (cascade STEP 2) |
| `ccd_session` | `mark_chapter` (TOC) + `spawn_task` (chip) |
| `scheduled-tasks` | Defer tasks (rare) |
| `mcp-registry` | Discover MCP servers |
| `computer-use` | Mac native apps (NOT trading work) |
| `Claude_in_Chrome` | Web automation |
| `sqlite-trading` 🆕 (S32b) | Direct SQLite queries → `data/bot.db` (execution_states / fills / halts debug). Project-level `.mcp.json`. |
| `fetch` 🆕 (S32c) | Web requests (Bybit V5 API docs / PyPI versions / GitHub releases / Anthropic docs). uvx mcp-server-fetch. Project-level `.mcp.json`. |

## 📂 Critical files (navigation anchors)

| File | Role |
|------|------|
| `llm-wiki/wiki/project/SPRINT_STATE.md` | Living sprint state — FIRST READ |
| `kit-overview-ru.md` (this) | Single source of truth gateway |
| `sprint-flow-ru.md` | 9-фаз обязательный процесс |
| `tooling-inventory-ru.md` | Catalog (9 agents + 26 skills + 6 MCP + 6 hooks + cascade) |
| `CLAUDE.md` (repo root) | Bootstrap anchor (English) |
| `llm-wiki/CLAUDE.md` | Wiki maintainer rules + skills hierarchy |
| `~/.claude/CLAUDE.md` | Global rules + token economy |
| `wiki/log.md` | Chronological journal |
| `wiki/index.md` | Wiki catalog |
| `wiki/project/architecture/current-state.md` | Canonical counts + sprint history |

## 🎯 Top 10 commands operator должен знать

1. `Skill: sprint-orient` — старт сессии
2. `claude --continue` — resume последнюю session
3. `claude --resume` — выбрать из recent sessions
4. `/clear` — reset context между unrelated tasks
5. `/btw <question>` — side question без context pollution
6. `/rewind` (Esc+Esc) — restore previous state
7. `/compact <instructions>` — controlled context summarization
8. `/agents` — manage subagents
9. `/permissions` — review/configure permissions
10. `/statusline` — configure status line (context tracking visibility)

## ⚠️ Top 5 anti-patterns (не делать)

1. ❌ Прямой `Agent` dispatch вместо kit skill (skill encodes process — bypassing = drift)
2. ❌ Skip wiki check (cascade STEP 1) — jump straight к mem-search OR Read raw
3. ❌ SPRINT_STATE update только в конце спринта (Phase 4 protocol требует per-task)
4. ❌ Code на feature/sprint-* без plan file — hook `sprint-flow-check.sh` БЛОКИРУЕТ push
5. ❌ Merge sprint без Phase 5 status="done" — hook `phase-advance.sh` БЛОКИРУЕТ

## 🔁 Sprint lifecycle (9 phases)

| # | Phase | Skill / Tool | HARD-GATE |
|---|-------|--------------|-----------|
| 1 | Orient | `sprint-orient` | SPRINT_STATE прочитан |
| 2 | Brainstorm | `brainstorm-init` → trader-expert OR `superpowers:brainstorming` | `pre-s{N}-backlog.md` |
| 3 | Plan | `superpowers:writing-plans` | 🔒 Hook: plan file MUST exist |
| 4 | Execute | `subagent-driven-development` OR `executing-plans` + `test-driven-development` | Per-task SPRINT_STATE update |
| 5 | Verify | `verification-before-completion` | 🔒 Hook: Phase 5 = done в SPRINT_STATE |
| 6 | Review | Domain reviewer (L5) + `requesting/receiving-code-review` | Blockers addressed |
| 7 | Sync | `wiki-update` | Block 1↔2 sync |
| 8 | Ship | `sprint-finish` → `finishing-a-development-branch` | sprint-NN.md + counts + index sync |
| 9 | Close | SPRINT_STATE between-sprints + log session-end | — |

Detail: [[sprint-flow-ru]]

## 📦 Best practices applied (per Anthropic Claude Code docs)

1. ✅ Verify work — test-engineer agent + superpowers:verification-before-completion
2. ✅ Plan Mode (explore→plan→code) — kit Phase 2-3
3. ✅ Specific context в prompts — controller discipline + Path discipline в agents
4. ✅ CLAUDE.md разумно короткий — S31 prune (target -35%)
5. ✅ Auto mode permissions — documented (Section 14)
6. ✅ Sandboxing — documented (Section 14)
7. ✅ MCP servers — 8 active (post-S32d: +sqlite-trading + fetch)
8. ✅ Hooks — 7 push + 2 UserPromptSubmit + 1 SessionStart active mechanical enforcement
9. ✅ Skills — 36 mapped к kit flow (post-S32c)
10. ✅ Subagents — 11 reviewer agents (post-S32d: +dashboard-reviewer + bybit-api-reviewer)
11. ✅ Plugins — 4 curated (Section 15)
12. ✅ `/clear` discipline — anti-pattern documented
13. ✅ `/btw` для side questions — Section 18
14. ✅ `/rewind` checkpoints — Section 18
15. ✅ `--continue` / `--resume` — Section 18
16. ✅ Non-interactive `claude -p` — Section 19
17. ✅ Fan-out parallel — Section 19
18. ✅ Status line (`/statusline`) — Section 17
19. ✅ CLI tools (gh / git / pytest / mypy / ruff / bash -n) — Section 16
20. ✅ Common failure patterns — anti-patterns documented

## 📊 Sprint history (last 10)

| Sprint | Tag | Date | Summary |
|--------|-----|------|---------|
| S22 | alpha.22 | 2026-04-26 | BTC 4H test (62 trades, FAIL T5) |
| S23 | alpha.23 | 2026-04-26 | v0.5 honest close |
| S25 | alpha.25 | 2026-04-26 | Dashboard UI |
| S26 | alpha.26 | 2026-04-26 | Dashboard UI redesign + README |
| S27 | alpha.27 | 2026-04-26 | Formula bug fixes (5 bugs) |
| S28 | alpha.28 | 2026-04-26 | Process enforcement (sprint-flow-check hook + Russian docs) |
| S29 | alpha.29 | 2026-04-26 | Full Superpowers Integration (7 NEW + Skills × Phase map) |
| S30 | alpha.30 | 2026-04-26 | Tier-2 Agents (security/test/doc) + phase-advance hook + cascade |
| S31 | alpha.31 | 2026-04-26 | Kit Revision per Best Practices + Single Tools-Overview File |
| S32 | alpha.32 | 2026-04-27 | Kit Phase 0 (P0 fixes + 5 skill mappings + cascade smart-explore + Phase 9 consolidate-memory) |
| S32b | alpha.32b | 2026-04-27 | Kit Phase 1 (CI + pre-commit + SQLite MCP + freshness hook + dashboard-reviewer) |
| S32c | alpha.32c | 2026-04-27 | Kit Phase 2 reduced (4 skill mappings + Fetch MCP + corpus categorization scheme docs) |
| S32d | alpha.32d | 2026-04-27 | Kit Phase 3 final (bybit-api-reviewer + context budget hook + schedule wire + sprint metrics + corpus research notes) — **S32 series COMPLETE** |

Full history: [[../architecture/current-state#карта-спринтов-sprint-history]]

## Связанные документы

- [[sprint-flow-ru]] — обязательный 9-фаз процесс с per-phase HARD-GATEs
- [[tooling-inventory-ru]] — full catalog (9 agents + 26 skills + 6 MCP + 6 hooks + cascade)
- [[../decisions/0017-review-agent-harness]] — review agents matrix policy
- [[../decisions/0041-sprint-28-process-enforcement]] — process enforcement ADR
- [[../decisions/0042-sprint-29-superpowers-integration]] — full superpowers integration
- [[../decisions/0043-sprint-30-tier-2-agents-mem-wiki-merge]] — tier-2 agents + cascade
- [[../decisions/0044-sprint-31-kit-revision-best-practices]] — best practices revision (S31)
- [[kit-audit-2026-04-27]] — Kit audit findings post-S32 series (S32e — usage analysis: ALL components NEEDED, no removals)
- https://docs.claude.com/en/code/best-practices — Anthropic Claude Code best practices
- https://github.com/obra/superpowers — superpowers source
- https://github.com/thedotmack/claude-mem — claude-mem source
