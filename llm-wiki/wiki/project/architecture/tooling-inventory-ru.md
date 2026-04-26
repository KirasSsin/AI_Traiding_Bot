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
| Новый sprint scope с questions | `brainstorm-init` skill → `trader-expert` agent (если scope/strategy) |
| Plan writing после brainstorm | `superpowers:writing-plans` skill |
| Execute plan | `superpowers:subagent-driven-development` (code) OR `executing-plans` (controller) |
| Code change в `src/risk/`, `src/signalgen/`, `src/execution/`, `src/backtest/` | `trading-logic-reviewer` agent |
| Math формулы (`indicators.py`, `dsr.py`, `mc_permutation.py`, `strategy_metrics.py`) | `quant-stats-reviewer` agent |
| Storage / migrations / parquet / SQLite WAL | `data-integrity-reviewer` agent |
| Cross-module refactor / concurrency / DI | `architecture-reviewer` agent |
| Любой `*.py` (generic) | `python-reviewer` agent (после domain) |
| Sprint complete | `sprint-finish` skill → `superpowers:finishing-a-development-branch` |
| После src/ change | `wiki-update` skill |
| Поиск по прошлым sessions | `mcp__plugin_claude-mem_mcp-search__smart_search` MCP |
| Chapter mark в session | `mcp__ccd_session__mark_chapter` MCP |
| Out-of-scope task chip | `mcp__ccd_session__spawn_task` MCP |
| TDD test + impl + commit | `superpowers:test-driven-development` skill |
| Cleanup CLAUDE.md / agent prompts (one-time) | `caveman:compress` skill |

---

## 1. Domain Reviewer Agents (6) — `~/.claude/agents/`

L5 layer per ADR 0017. Custom agents с project-specific knowledge. Все имеют `memory: project` (institutional knowledge в `.claude/agent-memory/<agent>/MEMORY.md`).

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

### 1.6 architecture-reviewer
- **Назначение:** Senior backend architecture reviewer для AI Trading Bot v0.1. Purely architectural decisions без trading semantics: cross-module refactor, concurrency design (async migration, lock policy), DI patterns, component decomposition, cross-cutting concerns (error/retry/logging), performance patterns (batch vs streaming, caching), API stability + cohesion/coupling.
- **Когда:** MUST BE USED перед любым architectural change spanning multiple modules OR когда concurrency model touched.
- **Не использовать для:** Trading domain semantics (trader-expert), math (quant-stats), storage (data-integrity), Python idioms (python-reviewer).
- **Модель:** sonnet 4.6
- **Memory:** dashboard-context S25, multi-timeframe-multi-symbol S15, concurrency-model, DI-wiring S11, parallel-interval-maps.

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

## 3. Superpowers Plugin Skills (13) — `~/.claude/plugins/cache/claude-plugins-official/superpowers/`

L3 process layer. Brainstorm → plans → execute → ship.

### 3.1 brainstorming
- **Назначение:** Refine vague ideas в fully formed designs через clarifying questions one-at-a-time → propose 2-3 approaches → present design → user approval → spec doc.
- **Когда:** Vague feature/project request. Перед writing-plans.
- **HARD-GATE:** No code/scaffolding до user approves design.

### 3.2 writing-plans
- **Назначение:** Comprehensive implementation plans assuming engineer has zero context. Bite-sized tasks (2-5 min steps), exact file paths, exact commands, complete code в каждом step.
- **Когда:** PHASE 3 plan writing после brainstorm verdicts locked.
- **HARD-GATE:** No "TBD"/"TODO"/"implement later" placeholders. No "similar to Task N".
- **Output:** `wiki/project/plans/<YYYY-MM-DD>-sprint-N-<slug>.md`

### 3.3 subagent-driven-development
- **Назначение:** Execute plan dispatching fresh subagent per task с two-stage review (spec compliance → code quality). Recommended для code-heavy sprints.
- **Когда:** PHASE 4 execute. Plan exists, mostly independent tasks.
- **Pattern:** Implementer subagent → spec reviewer → code quality reviewer → next task.

### 3.4 executing-plans
- **Назначение:** Inline execution of plan tasks (controller-driven). Alternative к subagent-driven для docs-heavy sprints.
- **Когда:** PHASE 4 если subagents excessive overhead.

### 3.5 finishing-a-development-branch
- **Назначение:** Verify tests → present 4 options (merge local / push+PR / keep / discard) → execute choice → cleanup worktree.
- **Когда:** PHASE 8 ship. Called by `sprint-finish` skill.

### 3.6 systematic-debugging
- **Назначение:** Reproduce → localize → fix → guard. Methodical bug isolation.
- **Когда:** Bug found during execution.

### 3.7 test-driven-development
- **Назначение:** Failing test first → minimal implementation → verify → commit. RED → GREEN → COMMIT.
- **Когда:** Каждая task в PHASE 4 с code change.

### 3.8 verification-before-completion
- **Назначение:** Pre-completion verification checklist (tests / linter / runtime check).
- **Когда:** Каждая task done перед mark complete.

### 3.9 dispatching-parallel-agents
- **Назначение:** Multiple Agent calls в одном message для independent work parallel.
- **Когда:** 2+ reviewers / 2+ research questions / parallel implementer subagents (rare — обычно sequential).

### 3.10 receiving-code-review
- **Назначение:** Process code review feedback systematically.
- **Когда:** После reviewer returned blockers/concerns.

### 3.11 requesting-code-review
- **Назначение:** Format request к reviewer с context + diff + specific concerns.
- **Когда:** Перед dispatch reviewer agent.

### 3.12 using-git-worktrees
- **Назначение:** Set up isolated worktree workspace перед sprint start.
- **Когда:** Если parallel sprints / sandbox experiments needed. NOT default для нашего sequential workflow.

### 3.13 using-superpowers
- **Назначение:** Meta-skill — discovers и invokes other superpowers skills based on task type.
- **Когда:** Auto-loaded sessions start.

### 3.14 writing-skills
- **Назначение:** Create new skills following progressive disclosure pattern.
- **Когда:** Adding new project skill к `.claude/skills/`.

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

## Связанные документы

- [[sprint-flow-ru]] — обязательный sprint процесс (9 фаз)
- [[../decisions/0017-review-agent-harness]] — review agents matrix policy
- [[../decisions/0041-sprint-28-process-enforcement]] — этот процесс ADR
- [[methodology-rejected]] — rejected packages + cleanup
- `llm-wiki/CLAUDE.md` — Skills hierarchy & integration
- `~/.claude/CLAUDE.md` — global rules + token economy
