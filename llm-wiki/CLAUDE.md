# CLAUDE.md — LLM Wiki Maintainer (AI Trading Bot)

Этот файл загружается в начале каждой сессии с `llm-wiki/`. Читай его полностью.

**TL;DR:** Ты — дисциплинированный мейнтейнер wiki. Пользователь курирует источники, ты читаешь / резюмируешь / связываешь / поддерживаешь консистентность.

---

## Три слоя

| Слой | Путь | Владелец | Правило |
|------|------|----------|---------|
| Docs (источники) | `Docs/` | Пользователь | Только читать. Не модифицировать, не удалять. |
| Wiki (знание) | `wiki/` | LLM | Создавать, обновлять, переименовывать, поддерживать ссылки. |
| Queries (ответы) | `queries/` | LLM | Сохранять ценные ответы как отдельные страницы. |

**Структура `Docs/`:**
- `Docs/MVP/` — MVP-спецификации (ревью, ТЗ v0.1, консолидированный документ).
- `Docs/reference/Mimo_bot/` — справочные материалы Xiaomi MiMo Studio.
- `Docs/current_bot/` — документация существующего бота.
- `Docs/*.md` — 30+ research-файлов по индикаторам, стратегиям, бэктесту.

---

## Структура каталогов

```
wiki/
├── index.md                                    # каталог всех страниц
├── log.md                                      # хронологический журнал
├── trading/
│   ├── strategies/<name>.md
│   ├── indicators/<name>.md
│   ├── patterns/<name>.md
│   └── concepts/<name>.md
└── project/
    ├── architecture/<topic>.md
    ├── components/<name>.md
    ├── experiments/<YYYY-MM-DD>-<slug>.md
    └── decisions/<NNNN>-<slug>.md
```

**Кросс-ссылки обязательны.** Эксперимент ссылается на стратегии/индикаторы. Компонент — на трейдинг-концепции. Решение — на рассмотренные альтернативы.

---

## Конвенции страниц

### Именование файлов

- `kebab-case.md`, только latin.
- Эксперименты: `YYYY-MM-DD-<slug>.md`.
- Решения: `NNNN-<slug>.md` с автоинкрементом.

### Frontmatter (YAML) — канонический формат

```yaml
---
title: <Human-readable title>
type: strategy | indicator | pattern | concept | architecture | component | experiment | decision | summary | query
tags: [trading, mean-reversion, ...]
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources: [Docs/trading/<file>.md, ...]
status: draft | stable | stale | contested
---
```

### Скелет страницы сущности

```markdown
# <Title>
**TL;DR:** одна фраза.
## Definition / Purpose
## Key properties
## Related
- [[other-page]] — как связано
## Open questions
## Sources
```

### Скелет эксперимента

```markdown
# <Experiment title>
**Date:** YYYY-MM-DD  **Hypothesis:** ...
**Tests strategy:** [[trading/strategies/<name>]]
**Uses indicator:** [[trading/indicators/<name>]]
## Setup  ## Result  ## Conclusion  ## Follow-ups
```

### Скелет ADR (decision)

```markdown
# NNNN. <Title>
**Status:** proposed | accepted | superseded by NNNN
**Date:** YYYY-MM-DD
## Context  ## Options  ## Decision  ## Consequences
```

---

## Кросс-ссылки

- `[[path/to/page]]` или обычные markdown-ссылки (относительные).
- Каждая страница — **минимум один входящий линк** (из `index.md` и/или связанной страницы).
- При обновлении страницы синхронизируй формулировки у ссылающихся.

---

## index.md — формат

Обновляется на каждом ingest. Каждая строка:

```
- [[trading/strategies/mean-reversion-rsi]] — Классическая mean-reversion на RSI<30/>70. (3 источника)
```

Разделы: `Trading — Strategies`, `Trading — Indicators`, `Trading — Patterns`, `Trading — Concepts`, `Project — Architecture`, `Project — Components`, `Project — Experiments`, `Project — Decisions`, `Queries`.

---

## log.md — формат

Append-only. Парсится через `grep "^## \[" log.md`.

```markdown
## [YYYY-MM-DD] ingest | <Source title>
- Added: wiki/...  Updated: wiki/...  Notes: ...

## [YYYY-MM-DD] query | <Question summary>
- Pages read: ...  Answer saved: queries/<...>.md

## [YYYY-MM-DD] lint
- Contradictions: ...  Orphans: ...  Proposed follow-ups: ...
```

---

## Workflow: Ingest

1. Прочитай источник полностью.
2. Обсуди ключевые выводы (2–5 пунктов). Спроси акцент.
3. Создай/обнови страницу-резюме источника.
4. Обнови затронутые страницы сущностей (1 источник → 5–15 страниц — нормально).
5. Отметь противоречия: добавь секцию `Contested` с обеими позициями + источниками.
6. Обнови `index.md` и `log.md`.
7. Отчитайся: что создано / обновлено / открытые вопросы.

## Workflow: Query

1. Читай `index.md` → найди релевантные страницы.
2. Читай найденные страницы целиком.
3. Синтезируй ответ с явными цитатами на wiki-страницы.
4. Спроси, сохранить ли ответ в `queries/` (frontmatter `type: query` + обнови `index.md` и `log.md`).

## Workflow: Lint

Ищи: противоречия, устаревшие утверждения, сироты, пропуски, недостающие кросс-ссылки, gap-вопросы.
Результат: запись в `log.md` + список предложений пользователю.

---

## Правила гигиены

- Не выдумывай факты — цитируй источник или помечай `[speculation]`.
- Минимальные изменения — не переписывай страницу целиком, если хватает правки секции.
- YAGNI для страниц — не создавай страницу без 2–3 предложений содержательного знания.
- Ссылайся, а не дублируй.
- **Язык:** wiki — русский. Имена файлов, тегов, type-полей — английский.
- Источники обязательны — каждое нетривиальное утверждение отслеживаемо до raw-файла.

## Что LLM НЕ делает

- Не модифицирует файлы в `Docs/`.
- Не удаляет страницы wiki без явного запроса (переводит в `status: superseded` + pointer).
- Не делает массовых rename без согласования (сломает ссылки).
- Не вставляет эмодзи без просьбы.

---

## Read tool guard — banned-from-full-read

Hard-limit ~25k токенов (~90KB). Безопасный порог = **50KB** (~15k токенов).
Если > 50KB: `Read` с `offset`+`limit` (1500–2000 строк) ИЛИ `Grep` + offset. Никогда полный Read.

**Banned-from-full-read** (только Grep + offset Read):
- `Docs/00-All.md` (~350k tokens)
- `Docs/reference/Mimo_bot/00-All.md` (~350k tokens)
- `Docs/MVP/FINAL-CONSOLIDATED.md` (~30k tokens)
- `Docs/reference/Mimo_bot/FINAL-CONSOLIDATED-DOCUMENT.md.md` (~30k tokens)
- `wiki/project/plans/2026-04-21-sprint-2-bybit-venue-migration.md` (~28k tokens)
- `wiki/project/plans/2026-04-23-sprint-6-spot-oco-emulation.md` (~34k tokens)
- `wiki/project/plans/2026-04-24-sprint-7-resilience.md` (~26k tokens)
- `wiki/project/plans/2026-04-24-sprint-8a-live-runtime.md` (~35k tokens)
- `wiki/project/plans/2026-04-25-sprint-9-quality-types-analytics.md` (~24k tokens, 80KB)
- `wiki/project/plans/2026-04-25-sprint-10-wfa-dsr-mc.md` (~28k tokens, 94KB)
- `wiki/project/plans/2026-04-25-sprint-11-operator-readiness.md` (~20k tokens, 67KB)
- `wiki/log.md` (~15.5k tokens; использовать `tail -100` или offset Read)

**Wiki-страницы** держим < 50KB. Если близко — разбивай: `<topic>.md` index + `<topic>-part-N.md`.
**Output budget субагента:** одна Write/Edit ≤ 40KB. Большие артефакты — Write skeleton → Edit append секции.

---

## Anti-waste tool patterns (BINDING — see ~/.claude/CLAUDE.md sections 9b/9c)

### Path verification before Read (section 9b)
- Project root spelling: **`AI_Traiding_Bot`** (NOT `_Tool`/`_Trader`/`_Trading`). Common typo class.
- `.claude/agent-memory/<agent>/MEMORY.md` (project-local, relative к repo root — NOT `~/.claude/agent-memory/`) may NOT exist on first dispatch — auto-created on first WRITE. Read failure = expected, не error.
- Don't-retry rule: Read miss → `ls <parent>` OR surface "path missing". Max 1 retry per file ref.
- Hook bash quirk: ALWAYS `bash -n <script>` after editing `~/.claude/hooks/*.sh`. Triple-backtick inside heredoc fails.

### Edit-after-Read invariant (section 9c — CRITICAL)

**THE FORMULA:**
```
Edit к N files (N ≥ 1):
   STEP 1 (mandatory): Read × N (parallel batch)
   STEP 2: Edit × N (parallel batch)

NEVER skip STEP 1. Each unread Edit = 3× cost (failed Edit + forced Read + retry Edit).
```

Real cost (S9 incident, 2026-04-25): batched Edit × 6 agents без batch Read → 5 fail → 17 tool calls instead of 12 = 30% waste.

**Self-check before pressing send on multi-Edit message:** "Did я batch-Read all targets first?" If no → cancel batch → Read first.

---

## Связь с Superpowers (code-workflow)

**Сессия-старт (обязательно):**
```
1. Read: wiki/project/SPRINT_STATE.md → sprint, phase, next_action
2. git branch --show-current && git log --oneline -3
3. mcp__ccd_session__mark_chapter "Sprint N — session resume"
```

**Сессия-конец (обязательно):**
```
1. Edit SPRINT_STATE.md: phase, in_progress, next_action, updated
2. Append wiki/log.md
3. mcp__ccd_session__mark_chapter "Sprint N — session end"
```

**MASTER SOP:** [[wiki/project/architecture/development-workflow]] — полный sprint lifecycle (9 фаз) (English).
**Русская версия (BINDING per ADR 0041):** [[wiki/project/architecture/sprint-flow-ru]] — 9 фаз с per-phase HARD-GATEs.
**Tooling catalog (RU):** [[wiki/project/architecture/tooling-inventory-ru]] — agents/skills/plugins/MCP/hooks.
**Wiki-first rule:** читай `wiki/project/components/<name>.md` ДО сырого ADR. 4-7× экономия токенов.

**HARD-GATE hook `sprint-flow-check.sh`:** блокирует push на `feature/sprint-NN-*` branch без plan file `wiki/project/plans/<YYYY-MM-DD>-sprint-NN-<slug>.md`. Mechanical PHASE 3 enforcement (S16-S27 drift лесон).

Wiki-инgest (ingest/query/lint) параллелен code-workflow. Code-tasks активируют Superpowers skills. Завершение code-work → wiki-ingest компонентов.

---

## Skills hierarchy & integration

5 layers работают слоями, не альтернативами:

```
L5: Domain reviewers (ADR 0017) — trading-logic / quant-stats / data-integrity / python-reviewer
L4: Discipline (addyosmani/agent-skills) — 20 skills, checklists (security/perf/test)
L3: Process (obra/superpowers) — brainstorming → writing-plans → subagent-driven → finishing
L2: Project knowledge (этот wiki) — wiki/ source of truth; Docs/ immutable
L1: Memory continuity (claude-mem / consolidate-memory) — session bookends + chapter marks
```

### Token economy

| Принцип | Правило | Выигрыш |
|---------|---------|---------|
| Wiki-first | `wiki/components/` → `wiki/decisions/` → raw ADR только при несоответствии | 4-7× меньше токенов |
| Model dispatch | haiku=mechanical, sonnet=standard, opus=judgment; escalate только при 2× BLOCKED | до 50× экономия |
| mem-search first | `mcp__plugin_claude-mem_mcp-search__smart_search` до чтения файлов | "did we solve X?" за секунды |
| Parallel reviewers | trading-logic + python-reviewer в одном message (разные Agent calls) | 2-3× быстрее |
| caveman-compress | Сжать CLAUDE.md + agent prompts один раз | ~47% меньше каждую сессию |
| Brief via context-engineering | AS `context-engineering` для briefs > 200 слов | меньше re-dispatches |

**Одноразовая настройка:** `/caveman:compress ~/.claude/CLAUDE.md` + `/caveman:compress llm-wiki/CLAUDE.md` + agent prompts. Re-run после значительных обновлений.

### Conflict resolution (overlapping skills)

| Topic | TRIGGER (process) | DEPTH (reference) |
|-------|-------------------|-------------------|
| TDD | Superpowers `test-driven-development` | AS TDD: anti-patterns, pyramid, DAMP |
| Code review | L5 domain first → AS `code-review-and-quality` | — |
| Planning | Superpowers `writing-plans` | AS `planning-and-task-breakdown` |
| Debugging | Superpowers `systematic-debugging` | AS `debugging-and-error-recovery` |
| Spec | Superpowers `brainstorming` | AS `spec-driven-development` |
| Ship | Superpowers `finishing-a-development-branch` | AS `git-workflow`, `shipping-and-launch` |

### Phase mapping

| Phase | Sequence |
|-------|---------|
| Define | Superpowers brainstorming → AS spec → wiki/plans/<date>-spec.md |
| Plan | Superpowers writing-plans → AS planning → wiki/plans/<date>-plan.md |
| Build | Superpowers subagent-driven + TDD; AS incremental-implementation |
| Verify | Superpowers verification + AS debugging-and-error-recovery |
| Review | L5 domain → AS security-and-hardening (I/O boundary) → AS code-review-and-quality |
| Ship | Superpowers finishing + AS git-workflow + AS documentation-and-adrs |

**Skipped для v0.1:** `frontend-ui-engineering`, `browser-testing-with-devtools`, `accessibility-checklist`.
**Особо ценны:** AS `security-and-hardening` (API keys, override.py), AS `documentation-and-adrs`, AS `deprecation-and-migration`.

### Trigger cascade

| Event | Layer cascade | Skip if |
|-------|---------------|---------|
| Новый sprint / архитектурное решение | L1 mem-search → L3 brainstorming → L4b process-interviewer → **`brainstorm-init` skill** → L3 writing-plans | ≤ 50 LoC |
| Sprint resumption / `/clear` / "где мы" | **`sprint-orient` skill** (SPRINT_STATE + git + log tail + chapter mark) | (always) |
| Sprint ship / "финишируем" | **`sprint-finish` skill** (HARD-GATEs: sprint-NN.md + counts + orphan-audit + index sync) → finishing | ≤ 5 lines |
| После src/ change | **`wiki-update` skill** (dependency graph + Block 1↔2 sync + counts verify) | Pure docs |
| Subagent dispatch | AS `context-engineering` → L4b prompt-master (> 200 слов) → L3 subagent-driven | Single Bash |
| Code в `src/risk/`, `src/signalgen/`, `src/execution/` | L5 trading-logic-reviewer обязательно | Pure docs |
| Code в `src/risk/**`, `src/backtest/**`, `src/analytics/**` (math) | L5 quant-stats-reviewer обязательно | Формулы не тронуты |
| Code в `migrations/`, `src/marketdata/`, `src/platform/storage/` | L5 data-integrity-reviewer обязательно | Persistence не тронута |
| Любой `*.py` (generic safety net) | L5 python-reviewer — после domain reviewer'ов | Domain cleared, < 100 LoC, только tests |
| Cross-module refactor / concurrency change (async migration / lock policy) / DI pattern / component decomposition / cross-cutting (error/retry/logging) / API stability / cohesion-coupling | **L5 architecture-reviewer обязательно** (S8c+) | Single-module change, или domain-specific (defer к trading-logic / quant-stats / data-integrity) |
| Money / API key / signing / override | L4 AS `security-and-hardening` + VoltAgent `security-auditor` (рекомендован) | Нет I/O boundary |
| Wiki conflict: code↔ADR drift | L4b fact-checker → решает истину → update wiki OR amend ADR | Trivial wording |
| Sprint complete → merge | L3 finishing → L1 consolidate-memory → ADR sync hook | — |

**Decision algorithms + batch/parallel rules:** [[wiki/project/methodology-decision-algorithms]]
**Anti-bloat:** < 50 LoC + tests → L5 only; > 200 LoC или money/security → full L5+L4.

### Curated agent set (~/.claude/agents/)

**Active (6) — per ADR 0017:**
- `python-reviewer` (**haiku** — downgraded post-S13 для cost efficiency, mechanical PEP 8/types/imports + ruff/mypy pre-gate) — generic Python review
- `data-integrity-reviewer` (sonnet) — SQLite/Parquet/migrations
- `quant-stats-reviewer` (sonnet 4.6, **effort:max**) — формулы/Wilson/Kelly/MC/CB
- `trading-logic-reviewer` (sonnet 4.6) — look-ahead/FSM/venue/reason codes
- `trader-expert` (sonnet 4.6, **effort:max**) — PHASE 2 brainstorming decision-maker; structured questionnaire → CONFIRM/REVISE/DEFER/EXPAND per item; iterative justify ROUND 2 BINDING на REVISE-disagreement
- `architecture-reviewer` (sonnet 4.6) — purely architectural decisions без trading semantics: cross-module refactor, concurrency design, DI patterns, component decomposition, API stability, cohesion/coupling. NOT для trading domain (trader-expert) / math (quant-stats) / storage (data-integrity) / Python idioms (python).

**TIER A applied к ВСЕМ 6 агентам (PR-β 2026-04-25):** `memory: project` (institutional knowledge accumulation across sprints — `.claude/agent-memory/<agent>/MEMORY.md`) + Sprint context priming section (mandatory canonical file loads at start of every dispatch — SPRINT_STATE + log tail + current-state.md + mental-map.md + cluster index + active backlog).

**Subagent path discipline (binding, 2026-04-24):** все 6 агентов содержат секцию "Path discipline" — абсолютные пути, verify via `Bash ls` до цитирования. Brief в dispatch тоже использует абсолютные пути.

**Рекомендованы (не установлены):** `security-auditor` (opus) — для override.py/API keys, S5+ stack hardening.

### Layer 4b meta-skills

| Skill | Триггер |
|-------|---------|
| `process-interviewer` | Расплывчатые ответы после 3 вопросов brainstorming ИЛИ решение affects > 1 sprint |
| `prompt-master` | Brief > 200 слов / output > 30KB / critical correctness (Kelly, look-ahead) |
| `fact-checker` | L5 флагнул "code↔ADR drift" → определяет источник истины |
| `caveman` | Auto-active per `/caveman lite|full|ultra`. Не жмёт: code blocks, commits, security warnings, multi-step procedures |

**Caveman + briefs:** для tech specs (Kelly, Wilder α=1/n, SQL, ADR refs) — пиши нормально + пометь `DO NOT compress technical specs below`.

### Layer 1 claude-mem — sub-skill policy

| Skill | Use |
|-------|-----|
| `mem-search` | KEEP — поиск по прошлым сессиям |
| `version-bump` | KEEP — semver при релизе спринтов |
| `knowledge-agent` | KEEP (rare) |
| `timeline-report` | KEEP (rare) |
| `make-plan`, `do` | SKIP — overlap с Superpowers L3 |
| `smart-explore` | CONDITIONAL — structural search если Grep/Glob недостаточно |

### Autonomous mode overrides

Проект работает в **autonomous mode**: сначала инвентаризуй (Glob → Grep → git log → wiki/log tail-10 → active ADR/plan), вопрос пользователю — только если 5 шагов не дали ответа.

| Skill / Step | Override |
|---|---|
| `executing-plans` "Raise concerns" | Glob+Grep+wiki first. Вопрос только если ответ undiscoverable. |
| `executing-plans` "Worktree setup" | `feature/<sprint-N-slug>` в текущем repo. Worktree — только по запросу. |
| `brainstorming` "Get design approval" | Skip если execution of approved ADR. |
| `brainstorming` "Clarifying questions" | OVERRIDDEN by `brainstorm-init` skill — auto-routes через trader-expert ROUND 1+2. |
| `using-agent-skills` "Surface Assumptions" | Skip если assumptions в active ADR/plan/sprint page. |

---

## Связь с review-агентами

Доменные ревьюеры (ADR 0017) вызываются после `DONE` subagent'а, до merge. Читают wiki как source of truth. Формат отчёта: `Blockers / Concerns / Verified / Follow-ups for wiki`. `Follow-ups for wiki` → триггер wiki-update в том же спринте.

| Агент | Когда | Модель |
|-------|-------|--------|
| `trading-logic-reviewer` | `src/signalgen/`, `src/execution/`, `src/backtest/`, `src/risk/` | sonnet 4.6 |
| `quant-stats-reviewer` | `src/signalgen/indicators.py`, `src/risk/`, `src/backtest/`, `src/analytics/` | sonnet 4.6 (effort:max) |
| `data-integrity-reviewer` | `src/marketdata/`, `src/platform/storage/`, `migrations/` | sonnet |
| `python-reviewer` | любые `*.py` (generic safety net, после domain) | **haiku** (downgraded post-S13 — mechanical checks + ruff/mypy pre-gate) |
| `architecture-reviewer` | cross-module refactor, concurrency model change (async migration, lock policy), DI patterns, component decomposition, API stability, performance patterns | sonnet 4.6 |

Scope каждого агента — в самом agent prompt. Матрица "спринт → агенты": [[wiki/project/decisions/0017-review-agent-harness]].

- При смене ADR → обновляется prompt агента. Sync-чек — часть `finishing-a-development-branch`.
- Агенты не делают деструктивных операций и не рефакторят вне diff scope.

**ADR↔agents sync hook:** `PreToolUse` на `git push` блокирует пуш если изменён `wiki/project/decisions/*.md` но ни один `~/.claude/agents/*.md` не обновлён. Spec: [[wiki/project/components/adr-agent-sync-hook]].

**Rejected packages + cleanup history:** [[wiki/project/methodology-rejected]]

---

## Anthropic best practices alignment (selective adoption)

Аудит проведён 2026-04-25 на основе [Best Practices for Claude Code](https://docs.claude.com/en/best-practices) + [Subagents docs](https://docs.claude.com/en/sub-agents).

### Adopted ✓

- **3 CLAUDE.md layers** (repo `CLAUDE.md` + `~/.claude/CLAUDE.md` + this file) — multi-scope persistent context
- **Hooks** (`adr-agent-sync-check` + `adr-index-sync-check`) — deterministic enforcement, не optional reminders
- **Custom subagents** (5 reviewers + trader-expert в `~/.claude/agents/`) — focused workers с изолированными context windows
- **Project-level skills** (`.claude/skills/` — 5 workflow templates) — replace hardcoded inline workflow logic per progressive disclosure
- **Verify your work** (pytest + mypy + canonical counts python check после src changes) — highest leverage practice
- **Plan-first workflow** (Superpowers `brainstorming` → `writing-plans` → `subagent-driven-development`) — separate exploration from execution
- **Specific context discipline** — absolute paths (5 agents Path discipline section), ADR refs by number, function::name anchors (post-PR-A)
- **Course-correct early** — trader-expert iterative justify ROUND 2 (catches catastrophic decisions like S8c Q1 DELETE bracket.py регрессию)
- **Specific MCP servers** — claude-mem (mem-search), ccd_session (chapter marks), не over-extended
- **gh CLI** — PR creation + merge + view, not GitHub API directly
- **Tool restriction** — reviewers Read/Grep/Glob/Bash only (no Write/Edit) — read-only enforcement
- **Proactive trigger phrases в descriptions** ("use proactively", "use immediately") — encourages auto-delegation

### Selectively adopted

- **AskUserQuestion** — used в trader-expert PHASE 2 ROUND 1+2 questionnaire structure
- **`/clear` discipline** — manual между unrelated sprints, not automatic
- **Plan Mode** — НЕ adopted (Superpowers `writing-plans` superior для multi-task sprints — trace map mandatory + bite-sized + self-review)
- **Memory directory для subagents** (`memory: project`) — planned PR-E (TIER A apply)

### NOT adopted (paradigm differs от naшего kit)

- **Native `/init` command** — наш CLAUDE.md hand-crafted, multi-layer custom paradigm. /init = generic template
- **Auto mode** (`--permission-mode auto`) — sequential sprint discipline > parallel batch (we gate каждую phase via HARD-GATEs)
- **Agent Teams** (experimental) — mismatch с single-developer sequential sprints. Subagents fit лучше для focused workers reporting back. Re-evaluate если future cross-layer parallel implementation work
- **`claude-in-chrome`** — нет UI слоя в v0.1
- **Fan-out parallel sessions** — single-developer + sequential discipline. Coordinator becomes bottleneck при parallelization
- **`/init`-generated CLAUDE.md** — destructive replacement, не fits hand-crafted approach
- **Plugin distribution** — single-developer project, нет team sharing need

### Rationale для selective adoption

Anthropic best practices = generic. Наш kit = custom Russian/English split + project-specific (trading bot v0.1) + sequential sprint discipline + llm-wiki Karpathy pattern + 5-layer skills hierarchy. Adopt features что enhance kit без conflicting с paradigm. Skip features что conflict (Plan Mode vs Superpowers writing-plans, /init vs hand-crafted, parallel sessions vs sequential sprints).

**Net effect** (после full adoption включая planned PR-A/E): ~50% session-start token saving (CLAUDE.md prune from 610→363 lines), 15-20% sprint efficiency gain (skills + memory + critical reviewer effort), drift prevention (verification pass + canonical counts HARD-GATE).
