---
title: Tooling Inventory — агенты / скиллы / плагины / MCP (русская версия)
type: architecture
tags: [tooling, agents, skills, plugins, mcp, catalog, ru]
created: 2026-04-26
updated: 2026-04-26
status: stable
sources:
  - ~/.claude/agents/ (6 agents)
  - .claude/skills/ (5 project skills)
  - ~/.claude/plugins/cache/ (4 plugins)
  - project/decisions/0017-review-agent-harness.md
  - project/decisions/0041-sprint-28-process-enforcement.md
---

# Tooling Inventory (RU)

> Полный каталог: что используем / когда / зачем / как.
> Sprint flow: [[sprint-flow-ru]]

## TL;DR — decision matrix (сначала это)

| Задача | Tool sequence |
|--------|---------------|
| Старт сессии / `/clear` | `sprint-orient` skill (project) |
| Новый sprint scope с trading questions | `brainstorm-init` skill → `trader-expert` agent |
| Новый sprint scope с non-trading questions (process/infra) | `superpowers:brainstorming` skill (Socratic refinement) |
| Plan writing после brainstorm | `superpowers:writing-plans` skill |
| Execute plan (code-heavy) | `superpowers:subagent-driven-development` skill |
| Execute plan (docs/wiki-heavy) | `superpowers:executing-plans` skill (controller-driven) |
| TDD test + impl + commit | `superpowers:test-driven-development` skill |
| **Bug encountered during execution** | `superpowers:systematic-debugging` skill (4-phase root cause) |
| **Pre-completion verification** | `superpowers:verification-before-completion` skill (checklist) |
| **Format reviewer brief** | `superpowers:requesting-code-review` skill |
| **Process reviewer feedback systematically** | `superpowers:receiving-code-review` skill |
| **Parallel reviewer dispatch** | `superpowers:dispatching-parallel-agents` skill (multiple Agent calls в одном message) |
| Code change в `src/risk/`, `src/signalgen/`, `src/execution/`, `src/backtest/` | `trading-logic-reviewer` agent |
| Math формулы (`indicators.py`, `dsr.py`, `mc_permutation.py`, `strategy_metrics.py`) | `quant-stats-reviewer` agent |
| Storage / migrations / parquet / SQLite WAL | `data-integrity-reviewer` agent |
| Cross-module refactor / concurrency / DI | `architecture-reviewer` agent |
| Любой `*.py` (generic) | `python-reviewer` agent (после domain) |
| **Money / API keys / override / signing / Mainnet** 🆕 | `security-auditor` agent (opus) |
| **New module без tests / coverage gap / property test design** 🆕 | `test-engineer` agent (sonnet) |
| **Wiki consistency check (post wiki-update)** 🆕 | `doc-reviewer` agent (haiku, lightweight) |
| **Pre-merge Phase 5 verify enforcement** 🆕 | `phase-advance.sh` hook fires automatically |
| **"Did we solve X?" / past decision lookup** | wiki-mem cascade (Section 13): wiki → mem-search → grep → raw |
| **Parallel sandbox sprint / experiment** | `superpowers:using-git-worktrees` skill |
| **Создать new project skill (`.claude/skills/`)** | `superpowers:writing-skills` skill (methodology) |
| Sprint complete | `sprint-finish` skill → `superpowers:finishing-a-development-branch` |
| После src/ change | `wiki-update` skill |
| Поиск по прошлым sessions | `mcp__plugin_claude-mem_mcp-search__smart_search` MCP |
| Chapter mark в session | `mcp__ccd_session__mark_chapter` MCP |
| Out-of-scope task chip | `mcp__ccd_session__spawn_task` MCP |
| Cleanup CLAUDE.md / agent prompts (one-time) | `caveman:compress` skill |

---

## 1. Domain Reviewer Agents (9) — `~/.claude/agents/`

L5 layer per ADR 0017 + S30 expansion (ADR 0043). Custom agents с project-specific knowledge. Все имеют `memory: project` (institutional knowledge в `.claude/agent-memory/<agent>/MEMORY.md`).

**Status legend:** ✅ EXISTING (до S30), 🆕 NEW (S30 tier-2 expansion).

### 1.1 trader-expert
- **Назначение:** PHASE 2 brainstorm decision-maker. Решает scope/strategy/architecture-with-trading-semantics questions через 5-field structured questionnaire → CONFIRM/REVISE/DEFER/EXPAND verdicts. Поддерживает iterative justify ROUND 2 (BINDING) на REVISE-disagreement.
- **Когда:** Любая sprint scope question (стратегия / parameter calibration / risk policy / market mechanics). PHASE 2 brainstorming.
- **Не использовать для:** Чисто архитектурных решений без trading semantics (architecture-reviewer), формул (quant-stats-reviewer), Python idioms (python-reviewer), storage schema (data-integrity-reviewer).
- **Модель:** sonnet 4.6 (effort:max)
- **Пример invocation:**
  ```
  Agent(subagent_type="trader-expert",
        prompt="<5-field questionnaire с context>")
  ```
- **Output format:** Per-question verdict + escalation list для user (только product/regulatory/business).

### 1.2 trading-logic-reviewer
- **Назначение:** Reviews trading strategy logic, execution timing invariants, look-ahead bias, FSM transitions, reason codes, venue-filter compliance.
- **Когда:** Любая change в `src/signalgen/`, `src/execution/`, `src/backtest/`, `src/risk/`. Invoke proactively когда subagent reports completed work в этих areas.
- **Не использовать для:** Math формулы (quant-stats), storage (data-integrity), pure Python style (python-reviewer).
- **Модель:** sonnet 4.6
- **Пример:**
  ```
  Agent(subagent_type="trading-logic-reviewer",
        prompt="Review changes в src/backtest/replay_engine.py focusing на look-ahead bias")
  ```

### 1.3 quant-stats-reviewer
- **Назначение:** Reviews mathematical correctness of indicator formulas, statistical validity of backtests/walk-forward, probability models (Kelly sizing, Risk of Ruin, Monte Carlo permutations), circuit-breaker thresholds, numerical stability.
- **Когда:** Changes в `src/signalgen/indicators.py`, `src/risk/`, `src/backtest/`, `src/analytics/`. Invoke proactively когда backtest/WFA/DSR/MC modules touched.
- **Не использовать для:** Trading semantics (trading-logic-reviewer), code style.
- **Модель:** sonnet 4.6 (effort:max)
- **Memory:** `.claude/agent-memory/quant-stats-reviewer/` — DSR eq.12, Wilder EMA, Kelly caps, MC sign-flip, strategy_metrics T2/T3 bugs (institutional knowledge).

### 1.4 data-integrity-reviewer
- **Назначение:** Reviews market-data ingest, OHLCV invariants, SQLite WAL schema + migrations, Parquet writers, gap/dedup/OOO handling, event-sourcing persistence.
- **Когда:** Changes в `src/marketdata/`, `src/platform/storage/`, `migrations/`, или order/fill persistence paths.
- **Модель:** sonnet
- **Memory:** WAL schema invariants, halt persistence, fill_recorder S12.

### 1.5 python-reviewer
- **Назначение:** Generic Python review (PEP 8, Pythonic idioms, type hints, security, performance). Mechanical safety net post-domain.
- **Когда:** После domain reviewers — любой `*.py` change. MUST для Python projects.
- **Не использовать как primary** — domain reviewer first.
- **Модель:** **haiku** (downgraded post-S13 для cost efficiency)
- **Memory:** project-stack, ruff-isort config.

### 1.6 architecture-reviewer ✅
- **Назначение:** Senior backend architecture reviewer для AI Trading Bot v0.1. Purely architectural decisions без trading semantics: cross-module refactor, concurrency design (async migration, lock policy), DI patterns, component decomposition, cross-cutting concerns (error/retry/logging), performance patterns (batch vs streaming, caching), API stability + cohesion/coupling.
- **Когда:** MUST BE USED перед любым architectural change spanning multiple modules OR когда concurrency model touched.
- **Не использовать для:** Trading domain semantics (trader-expert), math (quant-stats), storage (data-integrity), Python idioms (python-reviewer).
- **Модель:** sonnet 4.6
- **Memory:** dashboard-context S25, multi-timeframe-multi-symbol S15, concurrency-model, DI-wiring S11, parallel-interval-maps.

### 1.7 security-auditor 🆕 (S30)
- **Назначение:** Vulnerability detection / threat modeling / secure coding (OWASP / API keys / signing / override paths / Mainnet integration).
- **Когда:** MUST BE USED для money paths, API keys, override.py, signing/HMAC, withdrawal/transfer code, Mainnet integration changes. S5+ stack hardening planned.
- **Не использовать для:** Trading logic correctness (trading-logic-reviewer), math (quant-stats-reviewer), generic Python (python-reviewer).
- **Модель:** opus
- **Severity output:** BLOCKER / HIGH / MEDIUM / LOW
- **Trading-specific rules:** API keys NEVER в code, HMAC override.py REQUIRED, withdraw whitelist BINDING, kill-switch auth REQUIRED, position size bounds, Bybit response validation, Mainnet/Testnet detection BINDING.
- **Memory:** `.claude/agent-memory/security-auditor/` — vulnerability classes observed, secret rotation policies, audit findings + remediation status.

### 1.8 test-engineer 🆕 (S30)
- **Назначение:** Test strategy / writing tests / coverage analysis (pytest, Hypothesis, pytest-cov, property-based tests для math invariants).
- **Когда:** New modules без tests, coverage gaps, property test design (DSR/Kelly/MC math invariants), regression tests для historical bugs (S27 lesson — 4 formula bugs survived 25 sprints).
- **Не использовать для:** Math correctness (quant-stats-reviewer оценивает correctness формулы, test-engineer оценивает coverage/quality test).
- **Модель:** sonnet
- **Trading-specific rules:** Math invariants → property tests (DSR ∈ [0,1], MC p ∈ [0,1]). Decimal precision tests. Timeframe parametrization (S27 T1 lesson). OHLCV invariants (high ≥ low etc). FSM transition coverage. ReasonCode coverage. Look-ahead regression tests (S2/S22/S27 lessons).
- **Memory:** `.claude/agent-memory/test-engineer/` — test patterns, coverage gaps recurring, property test invariants discovered, Hypothesis strategy templates.

### 1.9 doc-reviewer 🆕 (S30)
- **Назначение:** Lightweight wiki consistency reviewer — frontmatter completeness, link integrity, Block 1↔Block 2 sync (per ADR 0017 amendment 2026-04-25), canonical counts consistency, cross-reference integrity, index.md sync, tag taxonomy.
- **Когда:** AFTER `wiki-update` skill runs OR before sprint ship для verify wiki consistency.
- **Не использовать для:** Content quality / accuracy (domain reviewers), code review (python-reviewer), process methodology (controller).
- **Модель:** haiku (lightweight, speed-optimized)
- **Tools:** Read/Grep/Glob (read-only)
- **Memory:** `.claude/agent-memory/doc-reviewer/` — frontmatter omissions recurring, broken link patterns, Block 1↔2 drift patterns, canonical count drift sources.

---

## 2. Project Skills (5) — `.claude/skills/`

Workflow templates auto-trigger по description match. Заменяют hardcoded inline workflow logic per progressive disclosure.

### 2.1 sprint-orient
- **Назначение:** PHASE 1 orient sequence — SPRINT_STATE + git verify + log tail + canonical counts + chapter mark.
- **Когда:** Старт сессии / `/clear` / "где мы остановились" / "ориентируйся".
- **Как invoke:** Auto-triggers по description match. Manual: skill tool с `sprint-orient`.
- **Output:** ≤8 bullets для user (sprint, phase, branch, tag, last commit, recent log events, canonical counts, carry-overs, next action).

### 2.2 sprint-finish
- **Назначение:** PHASE 8 HARD-GATE checklist — sprint-NN.md + canonical counts sync + Block 1↔2 sync + orphan-audit + ADR/index sync.
- **Когда:** "Ship", "финишируем", "merge". После subagent-driven-development completes all batch tasks.
- **Как invoke:** Auto-triggers OR `Skill` tool. Делегирует к `superpowers:finishing-a-development-branch` после HARD-GATEs passed.

### 2.3 wiki-update
- **Назначение:** Walk dependency graph (touched src/ → component pages) + Block 1↔Block 2 sync + canonical counts verify.
- **Когда:** После src/ change. PHASE 7 sync.

### 2.4 brainstorm-init
- **Назначение:** PHASE 2 binding protocol — structured questionnaire → trader-expert ROUND 1 → iterative justify ROUND 2 на REVISE-disagreement → backlog persistence + user escalation.
- **Когда:** Новый sprint scope/architecture questions. "Брейнштурм S<N>", "scope sprint", "design questions".
- **Skip когда:** Pure execution of approved ADR.

### 2.5 hook-test
- **Назначение:** Manual env -i sandbox commands для testing hooks.
- **Когда:** Explicit `/hook-test` invocation only.

---

## 3. Superpowers Plugin Skills (13 + meta) — `~/.claude/plugins/cache/claude-plugins-official/superpowers/`

L3 process layer. Brainstorm → plans → execute → review → ship.

**Status legend:** ✅ EXISTING (используется до S29), 🆕 NEW (intergrated в S29).

### 3.1 brainstorming ✅
- **Назначение:** Refine vague ideas в fully formed designs через clarifying questions one-at-a-time → propose 2-3 approaches → present design → user approval → spec doc.
- **Когда:** Vague feature/project request. Перед writing-plans.
- **Where invoked в kit flow:** **Phase 2** (non-trading scope — process design, infrastructure). Trading scope использует `brainstorm-init` → `trader-expert` instead.
- **HARD-GATE:** No code/scaffolding до user approves design.

### 3.2 writing-plans ✅
- **Назначение:** Comprehensive implementation plans assuming engineer has zero context. Bite-sized tasks (2-5 min steps), exact file paths, exact commands, complete code в каждом step.
- **Когда:** PHASE 3 plan writing после brainstorm verdicts locked.
- **Where invoked в kit flow:** **Phase 3** PRIMARY. HARD-GATE — hook `sprint-flow-check.sh` блокирует push без plan file.
- **Output:** `wiki/project/plans/<YYYY-MM-DD>-sprint-N-<slug>.md`

### 3.3 subagent-driven-development ✅
- **Назначение:** Execute plan dispatching fresh subagent per task с two-stage review (spec compliance → code quality). Recommended для code-heavy sprints.
- **Когда:** PHASE 4 execute. Plan exists, mostly independent tasks.
- **Where invoked в kit flow:** **Phase 4** PRIMARY для code-heavy sprints.
- **Pattern:** Implementer subagent → spec reviewer → code quality reviewer → next task.

### 3.4 executing-plans ✅
- **Назначение:** Inline execution of plan tasks (controller-driven). Alternative к subagent-driven для docs-heavy sprints.
- **Когда:** PHASE 4 если subagents excessive overhead.
- **Where invoked в kit flow:** **Phase 4** ALTERNATIVE для docs/wiki sprints (S28 + S29 использовали этот path).

### 3.5 finishing-a-development-branch ✅
- **Назначение:** Verify tests → present 4 options (merge local / push+PR / keep / discard) → execute choice → cleanup worktree.
- **Когда:** PHASE 8 ship. Called by `sprint-finish` skill.
- **Where invoked в kit flow:** **Phase 8** delegated by project `sprint-finish` skill после HARD-GATEs.

### 3.6 systematic-debugging 🆕
- **Назначение:** 4-phase root cause process — Reproduce → Localize → Fix → Guard. Methodical bug isolation, не ad-hoc guessing.
- **Когда:** Bug found during execution.
- **Where invoked в kit flow:** **Phase 4 sub-flow** — STOP current task → systematic-debugging → resume original task. Replaces ad-hoc fix attempts.
- **Pattern:** minimal failing test (Reproduce) → narrow к function/line (Localize) → minimal change на root cause (Fix) → regression test (Guard).

### 3.7 test-driven-development ✅
- **Назначение:** Failing test first → minimal implementation → verify → commit. RED → GREEN → COMMIT.
- **Когда:** Каждая task в PHASE 4 с code change.
- **Where invoked в kit flow:** **Phase 4** — каждая code task. Inherited by subagent-driven-development для individual implementer tasks.

### 3.8 verification-before-completion 🆕
- **Назначение:** Pre-completion verification checklist (tests / linter / runtime check / edge cases / docs updated).
- **Когда:** Каждая task done перед mark complete + PHASE 5 sprint-level verify.
- **Where invoked в kit flow:** **Phase 5** PRIMARY checklist. Extended beyond pytest/mypy: ruff lint + runtime smoke + edge cases + doc updates.

### 3.9 dispatching-parallel-agents 🆕
- **Назначение:** Multiple Agent calls в одном message для independent work parallel.
- **Когда:** 2+ reviewers / 2+ research questions / parallel implementer subagents (rare — обычно sequential).
- **Where invoked в kit flow:** **Phase 4** (parallel research) + **Phase 6** (parallel reviewer dispatch — trading-logic + quant-stats + python в одном message).
- **Pattern:**
  ```python
  # Single message с multiple Agent calls
  Agent(subagent_type="trading-logic-reviewer", prompt=...)
  Agent(subagent_type="quant-stats-reviewer", prompt=...)
  ```

### 3.10 receiving-code-review 🆕
- **Назначение:** Process code review feedback systematically — categorize BLOCKER/CONCERN/SUGGESTION, address per category.
- **Когда:** После reviewer returned blockers/concerns.
- **Where invoked в kit flow:** **Phase 6** POST-REVIEW. Replaces ad-hoc feedback processing.
- **Pattern:** Categorize → BLOCKER (must fix перед merge) → CONCERN (decide fix-now vs defer) → SUGGESTION (consider future).

### 3.11 requesting-code-review 🆕
- **Назначение:** Format request к reviewer с context + diff + specific concerns + acceptance criteria.
- **Когда:** Перед dispatch reviewer agent.
- **Where invoked в kit flow:** **Phase 6** PRE-REVIEW. Standardize reviewer brief format.
- **Brief structure:** Sprint context + ADR refs + git diff/file refs + specific concerns + acceptance criteria.

### 3.12 using-git-worktrees 🆕
- **Назначение:** Set up isolated worktree workspace для parallel sprint OR sandbox experiments.
- **Когда:** (1) Re-run audit/experiment без disturb текущей branch, (2) parallel sprint (rare для single-developer).
- **Where invoked в kit flow:** **Cross-phase** OPTIONAL. Sandbox audits (S27 audit re-run примером был — мог использоваться worktree). NOT default — sequential workflow обычно работает direct на feature/sprint-N branch.

### 3.13 using-superpowers ✅ (meta)
- **Назначение:** Meta-skill — discovers и invokes other superpowers skills based on task type.
- **Когда:** Auto-loaded sessions start.
- **Where invoked в kit flow:** **Meta** auto-load. NOT manually invoked.

### 3.14 writing-skills 🆕
- **Назначение:** Create new skills following progressive disclosure pattern (frontmatter + when to use + steps + anti-patterns).
- **Когда:** Adding new project skill к `.claude/skills/`.
- **Where invoked в kit flow:** **Cross-phase** OPTIONAL. Когда existing skill не подходит и нужен new workflow template (S28 sprint-orient/sprint-finish/wiki-update/brainstorm-init были созданы ad-hoc — повторное создание should follow эту methodology).

---

## 4. Agent-Skills Plugin (21) — `~/.claude/plugins/cache/addy-agent-skills/`

L4 discipline checklists. Depth references для каждой engineering phase.

### Workflow phases (use в sequence)
- **idea-refine** — vague ideas → structured spec (alternative к superpowers:brainstorming)
- **spec-driven-development** — requirements + acceptance criteria перед code
- **planning-and-task-breakdown** — decompose в verifiable chunks (alternative к superpowers:writing-plans)
- **incremental-implementation** — thin vertical slices, test each
- **source-driven-development** — verify против official docs перед implementing
- **context-engineering** — right context at right time. **Используй для subagent briefs > 200 слов.**
- **test-driven-development** — depth checklist (анти-patterns, pyramid, DAMP)

### Domain skills (use по necessity)
- **frontend-ui-engineering** — production-quality UI с accessibility (для dashboard работы)
- **api-and-interface-design** — stable interfaces с clear contracts
- **browser-testing-with-devtools** — Chrome DevTools MCP runtime verification (для dashboard QA)
- **debugging-and-error-recovery** — depth checklist (alternative к superpowers:systematic-debugging)
- **code-review-and-quality** — five-axis review checklist
- **security-and-hardening** — OWASP / input validation / least privilege. **MUST для money/API key/override.py changes.**
- **performance-optimization** — measure first, optimize что matters
- **git-workflow-and-versioning** — atomic commits clean history
- **ci-cd-and-automation** — automated quality gates
- **documentation-and-adrs** — document the why
- **shipping-and-launch** — pre-launch checklist + rollback plan
- **deprecation-and-migration** — safely remove old code
- **code-simplification** — reduce complexity (anti-bloat enforcement)

### Meta
- **using-agent-skills** — meta-skill discovers right agent-skill для current task

### Conflict resolution с superpowers
| Topic | TRIGGER (superpowers process) | DEPTH (agent-skills reference) |
|-------|------------------------------|-------------------------------|
| TDD | superpowers:test-driven-development | agent-skills:test-driven-development |
| Code review | L5 domain reviewers first → agent-skills:code-review-and-quality | — |
| Planning | superpowers:writing-plans | agent-skills:planning-and-task-breakdown |
| Debugging | superpowers:systematic-debugging | agent-skills:debugging-and-error-recovery |
| Spec | superpowers:brainstorming | agent-skills:spec-driven-development |
| Ship | superpowers:finishing-a-development-branch | agent-skills:git-workflow-and-versioning + shipping-and-launch |

---

## 5. Claude-Mem Plugin (7) — `~/.claude/plugins/cache/thedotmack/`

L1 memory continuity. Session bookends.

### 5.1 mem-search
- **Назначение:** Поиск по прошлым sessions / decisions / learnings.
- **Когда:** Старт задачи — "did we solve X?" / "did we decide Y?". До чтения файлов.
- **Invoke:** `mcp__plugin_claude-mem_mcp-search__smart_search "<query>"`
- **Экономия:** "did we solve X?" за секунды vs full file scan.

### 5.2 version-bump
- **Назначение:** Semver управление при release sprints.
- **Когда:** PHASE 8 ship. Tag creation.

### 5.3 knowledge-agent
- **Назначение:** Retrieve consolidated knowledge across past sessions.
- **Когда:** Rare. Когда нужен deep historical context.

### 5.4 timeline-report
- **Назначение:** Generate timeline of recent activity.
- **Когда:** Rare. Sprint retrospective.

### 5.5 make-plan / do
- **SKIP** — overlap с superpowers L3.

### 5.6 smart-explore
- **Назначение:** Structural search через mem corpus.
- **Когда:** CONDITIONAL — если Grep/Glob недостаточно.

---

## 6. Caveman Plugin (5) — `~/.claude/plugins/cache/caveman/`

L4b style/compression layer.

### 6.1 caveman (mode toggle)
- **Назначение:** Activate caveman-mode (drop articles/filler/pleasantries). Persist throughout session.
- **Levels:** lite / full / ultra
- **Когда:** Каждая сессия (auto-active per current config). Switch: `/caveman lite|full|ultra`. Off: "stop caveman".

### 6.2 caveman:compress
- **Назначение:** Compress markdown files (CLAUDE.md, prompts, docs) в caveman-speak. ~47% token saving.
- **Когда:** ONE-TIME setup per file. После significant CLAUDE.md OR agent prompt updates.
- **Invoke:** `/caveman:compress <filepath>`

### 6.3 caveman-commit
- **Назначение:** Commit messages в caveman style (compact).
- **Когда:** Optional — обычно нормальный conventional commits preferred (per CLAUDE.md "Code/commits/PRs: write normal").

### 6.4 caveman-help
- **Назначение:** Help text для caveman commands.

### 6.5 caveman-review
- **Назначение:** Code review в caveman style.

---

## 7. MCP Servers

External tool integrations.

### 7.1 plugin_claude-mem_mcp-search (claude-mem)
- **Tools:** smart_search, query_corpus, get_observations, list_corpora, build_corpus, prime_corpus, etc.
- **Назначение:** Semantic search по past sessions.
- **Когда:** Старт задачи — verify "did we solve X?" до full file reads.

### 7.2 ccd_session
- **Tools:**
  - `mark_chapter` — divider в session transcript для navigation (TOC)
  - `spawn_task` — out-of-scope task chip (spawn separate session)
  - `request_directory` — request access к specific directory
- **Когда:**
  - `mark_chapter` — phase transitions / major milestones (3-8 chapters per session)
  - `spawn_task` — observed bug/improvement не в scope текущего task

### 7.3 scheduled-tasks
- **Tools:** create / list / update scheduled tasks
- **Когда:** Defer task до specific time (rare — обычно not used в нашем sequential workflow).

### 7.4 mcp-registry
- **Tools:** list/search/suggest connectors
- **Когда:** Discover MCP servers (rare).

### 7.5 computer-use
- **Tools:** screenshot, mouse/keyboard control, app launching, etc.
- **Когда:** UI walkthrough / Mac native apps (Notes, Maps, Finder, System Settings). NOT для trading work.
- **Restriction:** Browsers tier="read" (visible но clicks blocked — use Claude_in_Chrome для browser automation). Terminals/IDEs tier="click" (typing blocked — use Bash вместо).

### 7.6 Claude_in_Chrome
- **Tools:** navigate, click, find, form_input, get_page_text, JavaScript execution, etc.
- **Когда:** Web automation (если dashboard требует UI test). Browser-based workflows.
- **Не использовать для:** Trading bot CLI — используй Bash directly.

### 7.7 sqlite-trading 🆕 (S32b — project-level `.mcp.json`)
- **Command:** `uvx mcp-server-sqlite --db-path /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot/data/bot.db`
- **Tools:** list_tables, describe_table, read_query, write_query, create_table, append_insight
- **Когда:** Direct SQLite queries → execution_states / fills / halts / audit_log / circuit_breakers debugging. 10× быстрее vs `sqlite3 data/bot.db "SELECT..."` через bash.
- **Activation:** Operator approve prompt at session start (one-time).

### 7.8 fetch 🆕 (S32c — project-level `.mcp.json`)
- **Command:** `uvx mcp-server-fetch`
- **Tools:** fetch (HTTP GET с user-agent customization, robots.txt respect, optional proxy)
- **Когда:**
  - Bybit V5 API docs lookup (https://bybit-exchange.github.io/docs/v5/)
  - PyPI package version checks (https://pypi.org/pypi/<pkg>/json)
  - GitHub releases / CHANGELOG fetch
  - Anthropic best practices docs
- **Не использовать для:** Trading data fetch — используй pybit V5 client (proper rate limiting + auth).
- **Activation:** Operator approve prompt at session start (one-time, same as sqlite-trading).

---

## 8. Hooks — `~/.claude/hooks/`

Mechanical enforcement, не optional reminders.

### 8.1 adr-agent-sync-check.sh
- **Trigger:** PreToolUse on git push
- **Block если:** ADR `wiki/project/decisions/*.md` changed BUT ни один `~/.claude/agents/*.md` updated
- **Fix:** `touch ~/.claude/agents/<reviewer>.md` (или Python `os.utime` для force mtime ahead)

### 8.2 adr-index-sync-check.sh
- **Trigger:** PreToolUse on git push
- **Block если:** New ADR (`wiki/project/decisions/NNNN-*.md`) BUT не в `wiki/index.md`
- **Fix:** Add ADR entry к index.md "Project — Decisions" section

### 8.3 sprint-flow-check.sh (S28+)
- **Trigger:** PreToolUse on git push
- **Block если:** Branch matches `feature/sprint-NN-*` BUT нет plan file в `wiki/project/plans/<YYYY-MM-DD>-sprint-NN-*.md`
- **Fix:** Invoke `superpowers:writing-plans` skill, create plan file

### 8.6 phase-advance.sh (S30+) 🆕
- **Trigger:** PreToolUse on `gh pr merge`
- **Block если:** Branch `feature/sprint-NN-*` AND SPRINT_STATE Phase 5 status != "done" AND != "skipped (...)"
- **Fix:** Run `superpowers:verification-before-completion` checklist (pytest + mypy + canonical counts) → update SPRINT_STATE Phase 5 → "done"
- **Mechanism:** Parses Phase tracking table (S28 template) → extracts Phase 5 status (2nd column)
- **Tested:** positive (Phase 5 done → exit 0), negative (Phase 5 pending → exit 2 + helpful error с required action checklist)

### 8.4 wiki-broken-link-check.sh
- **Trigger:** PreToolUse on git push
- **Block если:** Broken `[[wiki-link]]` в touched files
- **Fix:** Resolve link (file exists / typo / etc)

### 8.5 caveman-* hooks
- **Trigger:** Various — caveman mode lifecycle
- **Назначение:** Persist caveman state across sessions

---

## 9. Token economy rules

| Принцип | Правило | Выигрыш |
|---------|---------|---------|
| Wiki-first | `wiki/components/` → `wiki/decisions/` → raw ADR только при несоответствии | 4-7× меньше токенов |
| Model dispatch | haiku=mechanical, sonnet=standard, opus=judgment-heavy | до 50× экономия |
| mem-search first | До чтения файлов — verify "did we solve X?" | секунды vs minutes |
| Parallel reviewers | trading-logic + python-reviewer в одном message (multiple Agent calls) | 2-3× быстрее |
| caveman-compress | One-time CLAUDE.md + agent prompts compress | ~47% per session |
| context-engineering | AS skill для subagent briefs > 200 слов | меньше re-dispatches |
| Read tool guard | Files > 50KB — Read с offset+limit OR Grep first | избегаем 25k token overflow |

---

## 10. Curated agent set rationale (ADR 0017)

**Active 6 (per ADR 0017):** trader-expert + 4 reviewers + architecture-reviewer.

**Не установлены (рекомендованы):**
- `security-auditor` (opus) — для override.py / API keys / S5+ stack hardening. Установить если real money paths появятся.

**Rejected packages + cleanup history:** [[methodology-rejected]]

---

## 11. Anti-patterns

- ❌ Использовать `Agent` directly вместо skill (skill encodes process — bypassing = drift)
- ❌ Skip `mem-search` потому что "помню" (memory не reliable across compactions)
- ❌ Использовать opus где hailku/sonnet работает (cost waste)
- ❌ Sequential reviewers где parallel possible (2-3× slower)
- ❌ caveman-compress на code files (только markdown/prose)
- ❌ Ignore hook block — fix root cause, не bypass
- ❌ MCP computer-use для browser — использовать Claude_in_Chrome
- ❌ Read large file без offset/limit — 25k token overflow

## 12. Skills × Phase integration map (S29)

Полная карта 26 skills × kit flow phases. Source of truth для "какой skill в какой фазе":

| Skill | Type | Phase | Trigger | Status |
|-------|------|-------|---------|--------|
| `sprint-orient` | project | 1 | Session start / `/clear` | ✅ |
| `brainstorm-init` | project | 2 | Trading scope questions | ✅ |
| `superpowers:brainstorming` | superpowers | 2 | Non-trading scope (process/infra) | 🆕 S29 |
| `superpowers:writing-plans` | superpowers | 3 | Plan creation (HARD-GATE hook) | ✅ |
| `agent-skills:planning-and-task-breakdown` | agent-skills | 3 | DEPTH ref task decomposition | ✅ |
| `superpowers:subagent-driven-development` | superpowers | 4 | Code-heavy execute | ✅ |
| `superpowers:executing-plans` | superpowers | 4 | Docs-heavy execute | ✅ |
| `superpowers:test-driven-development` | superpowers | 4 | Каждая code task | ✅ |
| `superpowers:systematic-debugging` | superpowers | 4 sub-flow | Bug encountered | 🆕 S29 |
| `superpowers:dispatching-parallel-agents` | superpowers | 4+6 | Parallel reviewers/research | 🆕 S29 |
| `agent-skills:test-driven-development` | agent-skills | 4 | DEPTH ref TDD anti-patterns | ✅ |
| `agent-skills:context-engineering` | agent-skills | 4 | Subagent briefs > 200 слов | ✅ |
| `agent-skills:incremental-implementation` | agent-skills | 4 | DEPTH ref slices | ✅ |
| `superpowers:verification-before-completion` | superpowers | 5 | Pre-completion checklist | 🆕 S29 |
| `superpowers:requesting-code-review` | superpowers | 6 | Format reviewer brief | 🆕 S29 |
| `superpowers:receiving-code-review` | superpowers | 6 | Process reviewer feedback | 🆕 S29 |
| `agent-skills:code-review-and-quality` | agent-skills | 6 | DEPTH ref five-axis review | ✅ |
| `agent-skills:security-and-hardening` | agent-skills | 6 | Money/API/override changes | ✅ |
| `wiki-update` | project | 7 | After src/ change | ✅ |
| `sprint-finish` | project | 8 | Sprint complete (HARD-GATEs) | ✅ |
| `superpowers:finishing-a-development-branch` | superpowers | 8 | Delegated by sprint-finish | ✅ |
| `agent-skills:git-workflow-and-versioning` | agent-skills | 8 | DEPTH ref atomic commits | ✅ |
| `agent-skills:shipping-and-launch` | agent-skills | 8 | DEPTH ref pre-launch checklist | ✅ |
| `superpowers:using-git-worktrees` | superpowers | cross | Sandbox/parallel sprint | 🆕 S29 |
| `superpowers:writing-skills` | superpowers | cross | New project skill creation | 🆕 S29 |
| `superpowers:using-superpowers` | superpowers | meta | Session start auto-load | ✅ |

**Total integration: 26 skills (13 superpowers + 5 project + 8 agent-skills).**

S29 added 7 NEW superpowers skills к existing 6 = full 13 superpowers integrated.

## 13. LLMWiki ↔ Claude-mem cascade rule (S30 ADR 0043)

Two systems target token economy + context delivery:
- **llmwiki** — structured curated wiki/ (frontmatter + cross-links + sources tracking). 4-7× compression vs raw files. Strengths: organized, current, sourced.
- **claude-mem** — semantic search past sessions (mem-search). "Did we solve X?" в seconds. Strengths: cross-session memory, semantic, fast.

### Cascade order (token-optimal lookup)

ВСЕГДА следуй cascade order для context lookups (NOT random pick):

```
Query → check sequence:
  STEP 1: wiki/index.md → wiki/<page>.md (curated structured, tagged)
            ↓ if not found / insufficient
  STEP 2: mem-search smart_search "<query>" (past session observations)
            ↓ if not found
  STEP 3: Grep raw src/ + Docs/ (current code state)
            ↓ if needed
  STEP 4: Read raw file с offset+limit (full content)
```

### Rationale

| Step | Source | Token cost | Coverage | When best |
|------|--------|-----------|----------|-----------|
| 1 wiki | `wiki/components/`, `wiki/decisions/`, `wiki/architecture/` | LOW (curated) | High-value compressed | Architecture / decisions / patterns |
| 2 mem | `mcp__plugin_claude-mem_mcp-search__smart_search` | LOW (semantic) | Past sessions | "Did we solve X?" / "Did we decide Y?" |
| 3 grep | `src/`, `Docs/` raw via Grep tool | MEDIUM | Current code | Symbol / function lookup |
| 4 read | Read с offset+limit | HIGH | Authoritative | Full implementation needed |

### Examples

**Query: "Как работает Wilder smoothing для RSI?"**
```
STEP 1 wiki: wiki/trading/indicators/rsi.md → найден (strength: curated formula)
DONE — не lookup mem/grep/raw.
```

**Query: "Did we decide об multi-symbol scope для S15?"**
```
STEP 1 wiki: wiki/project/decisions/0030-sprint-15-*.md → найден ADR
DONE.
```

**Query: "Как S22 решил T5 floor reachability?"**
```
STEP 1 wiki: wiki/project/sprints/sprint-22-4h-test.md → найден sprint page
DONE.
```

**Query: "Когда мы добавили dispatch parallel pattern?"**
```
STEP 1 wiki: search index.md / log.md → не нашёл точно
STEP 2 mem-search: smart_search "dispatch parallel" → returns S29 observations
DONE.
```

**Query: "Где определена calculate_rsi функция?"**
```
STEP 1 wiki: wiki/project/components/strategy.md → пишет про calculate_rsi
STEP 3 grep: grep -rn "def calculate_rsi" src/ → найдено `src/signalgen/indicators.py:50`
DONE.
```

### Anti-patterns (cascade violations)

- ❌ Skip STEP 1 wiki — jump straight к mem-search OR Read raw (loses curation)
- ❌ Use mem-search для current code lookup (mem corpus = past sessions, не current state)
- ❌ Use Read раньше Grep для symbol search (Grep faster + bounded output)
- ❌ Read large file без offset+limit (25k token overflow risk)
- ❌ Use grep на raw `Docs/` files без wiki check first (raw = unstructured)

### Bridges (deferred к S31+)

S30 documents cascade rule. Future bridges (technical implementation):

- **Bridge 2 — wiki-mem-corpus-sync** (S31+): Periodic indexing of wiki/ → claude-mem corpus → unified search. Defer: requires claude-mem API investigation.
- **Bridge 3 — chapter mark auto-link к log.md** (S31+): `mcp__ccd_session__mark_chapter` writes entry в `wiki/log.md`. Defer: requires hook integration.
- **Bridge 4 — frontmatter tags → mem corpus categorization** (S31+): wiki frontmatter (type/tags/sources) feed mem corpus filtering. Defer: requires schema understanding.

**S30 deliverable:** documentation enforcement (cascade rule в этом Section 13 + CLAUDE.md token economy + sprint-flow-ru.md). NO new skill creation.

## 14. Permission modes (per Anthropic best practices)

3 режима permissions для balance interruptions vs safety:

| Mode | Trigger | Когда использовать |
|------|---------|-------------------|
| **default** | каждое write/Bash/MCP — prompt | Default — careful operations, real money paths |
| **auto** (`--permission-mode auto`) | classifier reviews → blocks risky | Long-running tasks, trusted general direction (e.g. `claude --permission-mode auto -p "fix all lint errors"`) |
| **acceptEdits** | auto-accept file edits + common Bash | Mid-execution iterations |
| **dontAsk** | auto-deny prompts (allowed tools работают) | Strict scope enforcement |
| **bypassPermissions** | skip all prompts | DANGEROUS — use very carefully |
| **plan** | read-only exploration | Plan Mode для exploration |

### Sandboxing (`/sandbox`)
OS-level isolation restricts filesystem + network access. Allow Claude work freely в bounded space. Use для:
- Sandbox experiments (corpus indexing test, etc)
- Untrusted code review

Detail: https://docs.claude.com/en/permission-modes + /en/sandboxing

### Permission allowlists (`/permissions`)
Permit specific tools known safe (e.g. `npm run lint`, `git commit`, `pytest`). Reduces interruptions без auto mode.

### Recommendation для нашего kit

| Workflow | Mode | Reason |
|----------|------|--------|
| Sprint code work | **default** | Trade money paths — careful |
| Sprint docs/wiki sprint (S28-S31) | **acceptEdits** | Doc edits безопасны |
| Long-running batch (audit_formulas.py sweep) | **auto** | Background ops, classifier blocks risky |
| Mainnet integration changes | **default** + security-auditor mandatory | Money risk |

## 15. Plugin curation (4 active)

Все plugins установлены через official marketplace. Versions tracked.

| Plugin | Version | Skills count | Rationale |
|--------|---------|--------------|-----------|
| **superpowers** | 5.0.7 | 13 | Process layer — brainstorm/plan/execute/ship. Full integration S29. |
| **addy-agent-skills** | 1.0.0 | 21 | Discipline checklists — TDD/security/perf/code-review. DEPTH refs. |
| **claude-mem** | 12.3.7 | 7 | Memory continuity — mem-search/version-bump. Cascade STEP 2. |
| **caveman** | 84cc3c14fa1e | 5 | Mode/compress utility — token economy ~47% saving (CLAUDE.md compress). |

### Rejected plugins
См. [[methodology-rejected]] для полного списка considered-and-rejected packages.

### Plugin install (reproducibility)
```bash
/plugin install superpowers@claude-plugins-official
/plugin install addy-agent-skills
/plugin install claude-mem
/plugin install caveman
```

### Plugin discovery
- `/plugin` — browse marketplace
- `/plugin list` — installed plugins
- `/agents` — list subagents (включая plugin-provided)

## 16. CLI tools (explicit list)

Per best practices: "CLI tools = most context-efficient way to interact с external services."

| Tool | Использование |
|------|--------------|
| `gh` | GitHub: PR create/merge/view, issues, releases. ALWAYS prefer над unauthenticated GitHub API (rate limits). |
| `git` | Version control: branch / commit / push / log / diff |
| `pytest` | Testing: `pytest tests/unit -x -q`, `--cov`, `-m property`, `-m integration` |
| `mypy --strict` | Type checking |
| `ruff` | Linter (replaces flake8/black/isort) |
| `bash -n <script>` | Syntax check после editing `~/.claude/hooks/*.sh` (MANDATORY per CLAUDE.md anti-patterns) |
| `wc -l <file>` | Line count check для CLAUDE.md size discipline |
| `python3 -m scripts.<module>` | Run script с virtualenv |
| `source .venv/bin/activate` | Activate venv (Python 3.12 required per pyproject.toml) |

### Trading-specific scripts
- `python scripts/audit_formulas.py --sweep` — comprehensive formula audit (30 experiments)
- `python -m src wfa --symbols BTCUSDT --start 2023-01-01 --end 2026-04-26 --interval 60` — single WFA run
- `python -m src backfill --symbols BTCUSDT --start 2023-01-01 --end 2026-04-26 --interval 60` — backfill OHLCV

### Discovery pattern (per best practices)
```
"Use 'foo-cli-tool --help' to learn about foo tool, then use it to solve A, B, C."
```
Claude эффективно учит CLI tools которые не знает.

## 17. Status line + context tracking (`/statusline`)

Per best practices: "Track context usage continuously with a custom status line. Context window = #1 constraint."

### Configure (interactive)
```
/statusline
```
Auto-generates Bash script отображать metrics в terminal status line.

### Recommended displayed fields
- Sprint number / phase (read SPRINT_STATE.md)
- Current branch (`git branch --show-current`)
- Last commit SHA (`git log --oneline -1`)
- Context fill % (если accessible через CLI hooks)

### Manual config
Edit `~/.claude/settings.json` или create `~/.claude/scripts/statusline.sh`. Reference: https://docs.claude.com/en/statusline

### Skill для config: `statusline-setup` (built-in)
Automatically invoked when `/statusline` runs.

## 18. Token-saver commands (BINDING — best practices)

Per best practices: "Context window = most important resource to manage. Performance degrades as context fills."

| Command | Когда использовать | Что делает |
|---------|-------------------|-----------|
| **`/btw <question>`** | Side question не относящийся к main task | Answer в dismissible overlay — НЕ enters conversation history |
| **`/rewind` (Esc+Esc)** | Wrong direction / experimental approach | Restore previous conversation+code state OR summarize from message |
| **`/clear`** | Switching между unrelated tasks | Reset context window entirely |
| **`/compact <instructions>`** | Approaching context limit | Controlled summarization preserving critical info |
| **Esc** | Stop Claude mid-action | Preserves context, redirect |
| **`claude --continue`** | Resume последнюю session | Load conversation state |
| **`claude --resume`** | Choose из recent sessions | Interactive session picker |
| **`/rename <name>`** | Sessions span days | Descriptive name для later find |

### Discipline (BINDING)
- `/clear` ОБЯЗАТЕЛЕН между unrelated tasks (kitchen sink session anti-pattern)
- `/btw` для quick lookups (вместо full Read)
- `/rewind` для experimental approaches вместо careful planning каждый шаг
- `claude --continue` для multi-session sprints (preserve state across breaks)

### Anti-patterns (token waste)
- ❌ Long session с irrelevant accumulation (kitchen sink)
- ❌ Correcting same issue 3+ times — `/clear` + better prompt лучше
- ❌ Read full file где Grep + offset Read достаточно
- ❌ Side question в main thread — pollutes context

## 19. Non-interactive mode + fan-out patterns

Per best practices: "Once effective с one Claude, multiply output с parallel sessions, non-interactive mode, fan-out."

### Non-interactive mode (`claude -p`)

```bash
# One-off query
claude -p "Explain what this project does"

# Structured output (parseable)
claude -p "List all API endpoints" --output-format json

# Streaming для real-time processing
claude -p "Analyze this log file" --output-format stream-json
```

Useful для:
- CI/CD pipelines
- Pre-commit hooks
- Automated workflows
- Batch operations

### Fan-out across files

Pattern для bulk operations (migrations, audits):

```bash
# 1. Generate task list
claude -p "list all 200 files needing migration" > files.txt

# 2. Loop с scoped permissions
for file in $(cat files.txt); do
  claude -p "Migrate $file from React to Vue. Return OK or FAIL." \
    --allowedTools "Edit,Bash(git commit *)"
done

# 3. Test on few files first → refine prompt → run at scale
```

### `--allowedTools` flag
Restrict tools для batch operations. Critical для unattended runs:

```bash
--allowedTools "Read,Grep,Bash(pytest *)"
```

### `--verbose` flag
Debugging during development. Off в production.

### Pipe data input

```bash
cat error.log | claude -p "Find root cause"
```

### Combined с auto mode (long-running)

```bash
claude --permission-mode auto -p "fix all lint errors"
```
Auto mode classifier reviews commands в background. Aborts если repeatedly blocked (no fallback в non-interactive).

### Multiple parallel sessions

3 ways:
1. **Claude Code desktop app** — manage multiple local sessions visually (each isolated worktree)
2. **Claude Code on the web** — Anthropic cloud VMs
3. **Agent teams** — coordinated multi-session с shared tasks/messaging/team lead

### Writer/Reviewer pattern (parallel sessions)
| Session A (Writer) | Session B (Reviewer) |
|--------------------|---------------------|
| Implement rate limiter | (waits) |
| (waits) | Review @src/middleware/rateLimiter.ts. Look for edge cases, race conditions. |
| Address review feedback | (done) |

Fresh context в Session B = unbiased review.

## 22. Memory corpus categorization scheme (S32c — partial bridge 4 design)

**Status:** Documentation-only design. Implementation script deferred к S32d (research carry-over from S30 + S31 bridges 2-4).

### Problem

claude-mem MCP corpus (currently ~17 observations) flat — no semantic partitioning. mem-search returns noisy results когда обрабатывая queries spanning multiple domains (trading vs process vs debug).

Cascade STEP 2 (`mem-search`) текущая precision low когда:
- Query "did we solve formula bug" → returns mix of formula + process + debug observations
- Query "trader verdict ESC" → returns mix of trading-decisions + general kit observations

После 5-10 спринтов = corpus 50+ observations → noise compounding.

### Proposed scheme — 4 partitions

| Partition | What goes here | Source frontmatter tags |
|-----------|----------------|-------------------------|
| **trading-decisions** | Strategy verdicts (trader-expert), ESC items, ADR rationale, hypothesis test outcomes, MVP acceptance criteria changes | `trading`, `strategy`, `hypothesis`, `esc`, `trader-verdict`, `mvp`, `acceptance-criteria`, `regime`, `dsr-trial` |
| **formula-knowledge** | Math correctness (DSR, Sortino, Kelly, MC, Sharpe), audit findings, formula bug fixes | `formula`, `dsr`, `kelly`, `mc`, `sortino`, `sharpe`, `math`, `audit`, `bug-fix-formula`, `wfa` |
| **process-patterns** | Kit violations, HARD-GATE learnings, sprint-flow improvements, hook bug fixes | `process`, `kit`, `hard-gate`, `sprint-flow`, `hook`, `violation`, `lesson`, `phase-advance` |
| **debug-knowledge** | Past bug → fix patterns, debugging session outputs, error → solution mappings | `debug`, `bug`, `fix`, `error`, `troubleshoot`, `ci-fix`, `regression` |

Орхans (no matching tag) → `uncategorized` partition (fallback).

### Frontmatter tag → partition mapping (pseudo-code)

claude-mem ingest hook должен read frontmatter tags из committed wiki/sprint pages и categorize observations по primary tag intersect.

```python
# pseudo-code (S32d implementation candidate)
PARTITION_MAP = {
    "trading-decisions": {
        "trading", "strategy", "hypothesis", "esc", "trader-verdict",
        "mvp", "acceptance-criteria", "regime", "dsr-trial"
    },
    "formula-knowledge": {
        "formula", "dsr", "kelly", "mc", "sortino", "sharpe",
        "math", "audit", "bug-fix-formula", "wfa"
    },
    "process-patterns": {
        "process", "kit", "hard-gate", "sprint-flow", "hook",
        "violation", "lesson", "phase-advance"
    },
    "debug-knowledge": {
        "debug", "bug", "fix", "error", "troubleshoot",
        "ci-fix", "regression"
    },
}

def categorize(observation_frontmatter: dict) -> str:
    """Return partition name for observation based on frontmatter tags.

    Uses primary intersect — first partition с non-empty tag overlap wins.
    Order matters: trading > formula > process > debug (most specific to least).
    """
    tags = set(observation_frontmatter.get("tags", []))
    for partition in ["trading-decisions", "formula-knowledge",
                      "process-patterns", "debug-knowledge"]:
        if tags & PARTITION_MAP[partition]:
            return partition
    return "uncategorized"
```

### Cascade STEP 2 enhanced (post-implementation)

After bridge 4 implemented, cascade STEP 2 mem-search supports `category:` filter:

```
STEP 2: mem-search                          ← current S32: flat search (noisy)
   ↓ AFTER S32d bridge 4
STEP 2: mem-search category:trading-decisions  ← scoped search, 3-5× higher precision
```

Forecast precision improvement:
- Flat search: ~30% relevant results in top 5
- Categorized search: ~80% relevant results in top 5 (3× improvement)

### Bridges 2-4 status (S30 deferred → S32d candidate)

- **Bridge 2 (corpus periodic sync)** — auto-rebuild corpus от wiki/log.md новых entries
- **Bridge 3 (chapter mark auto-link)** — `mark_chapter` MCP tool creates linked log.md entry
- **Bridge 4 (frontmatter tags → partition)** — этот scheme implemented as ingest hook

### Why scheme docs S32c но script S32d?

- **Scheme** = stable design choice (partition labels + tag mappings) — committable now, no implementation risk
- **Implementation** = needs claude-mem internal API research (ingest hook framework, corpus partition support, search filter syntax) — research scope + new infrastructure dependency
- Splitting scheme ↔ script allows operator review tag mapping before lock-in
- S32c locks scheme в wiki = future implementation has clear target

### How operator can validate scheme

Test scheme manually на existing 17 observations:
```bash
mcp__plugin_claude-mem_mcp-search__list_corpora
# Read each observation's frontmatter
# Manually map к partition per PARTITION_MAP
# Verify majority match expected partition (no orphans за 30%)
```

## Связанные документы

- [[kit-overview-ru]] — single source of truth gateway (S31)
- [[sprint-flow-ru]] — обязательный sprint процесс (9 фаз)
- [[../decisions/0017-review-agent-harness]] — review agents matrix policy
- [[../decisions/0041-sprint-28-process-enforcement]] — process enforcement ADR
- [[../decisions/0042-sprint-29-superpowers-integration]] — full superpowers integration ADR (S29)
- [[../decisions/0043-sprint-30-tier-2-agents-mem-wiki-merge]] — tier-2 agents + cascade ADR (S30) — bridges 2-4 origin
- [[../decisions/0044-sprint-31-kit-revision-best-practices]] — best practices revision (S31)
- [[../decisions/0045-sprint-32-kit-phase-0-improvements]] — Kit Phase 0 (S32)
- [[../decisions/0046-sprint-32b-kit-phase-1-improvements]] — Kit Phase 1 (S32b)
- [[../decisions/0047-sprint-32c-kit-phase-2-improvements]] — Kit Phase 2 (S32c — этот scheme)
- [[methodology-rejected]] — rejected packages + cleanup
- `llm-wiki/CLAUDE.md` — Skills hierarchy & integration
- `~/.claude/CLAUDE.md` — global rules + token economy
- https://docs.claude.com/en/code/best-practices — Anthropic Claude Code best practices
- https://github.com/obra/superpowers — superpowers skills source repo
- https://github.com/thedotmack/claude-mem — claude-mem source repo
