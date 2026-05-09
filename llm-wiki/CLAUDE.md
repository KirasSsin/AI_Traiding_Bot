# CLAUDE.md — LLM Wiki Maintainer (AI Trading Bot)

Этот файл загружается в начале каждой сессии с `llm-wiki/`. Читай полностью.

**TL;DR:** Дисциплинированный мейнтейнер wiki. Пользователь курирует источники, ты читаешь / резюмируешь / связываешь / поддерживаешь консистентность.

**Kit settings single source of truth:** [[wiki/project/architecture/kit-overview-ru]] (S31)

---

## Три слоя

| Слой | Путь | Владелец | Правило |
|------|------|----------|---------|
| Docs (источники) | `Docs/` | Пользователь | Только читать. Не модифицировать, не удалять. |
| Wiki (знание) | `wiki/` | LLM | Создавать, обновлять, переименовывать, поддерживать ссылки. |
| Queries (ответы) | `queries/` | LLM | Сохранять ценные ответы как отдельные страницы. |

**Структура `Docs/`:**
- `Docs/MVP/` — MVP-спецификации.
- `Docs/reference/Mimo_bot/` — справочные материалы.
- `Docs/current_bot/` — документация существующего бота.
- `Docs/*.md` — 30+ research-файлов.

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

**Кросс-ссылки обязательны.** Эксперимент → стратегии/индикаторы. Компонент → trading-концепции. Решение → альтернативы.

---

## Конвенции страниц

### Именование файлов
- `kebab-case.md`, только latin.
- Эксперименты: `YYYY-MM-DD-<slug>.md`.
- Решения: `NNNN-<slug>.md` автоинкрементом.

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

- `[[path/to/page]]` или markdown-ссылки (относительные).
- Каждая страница — **минимум один входящий линк** (из `index.md` и/или связанной страницы).
- При обновлении страницы синхронизируй формулировки у ссылающихся.

---

## index.md — формат

Обновляется на каждом ingest. Формат:

```
- [[trading/strategies/mean-reversion-rsi]] — Классическая mean-reversion на RSI<30/>70. (3 источника)
```

Разделы: Trading — Strategies/Indicators/Patterns/Concepts, Project — Architecture/Components/Experiments/Decisions, Queries.

---

## log.md — формат

Append-only. Парсится через `grep "^## \[" log.md`.

```markdown
## [YYYY-MM-DD] ingest | <Source title>
- Added/Updated/Notes: ...

## [YYYY-MM-DD] query | <Question summary>
- Pages read / Answer saved

## [YYYY-MM-DD] lint
- Contradictions / Orphans / Follow-ups
```

---

## Workflow: Ingest

1. Прочитай источник полностью.
2. Обсуди ключевые выводы (2–5 пунктов).
3. Создай/обнови страницу-резюме источника.
4. Обнови затронутые страницы (1 источник → 5–15 страниц — нормально).
5. Отметь противоречия: добавь секцию `Contested` с обеими позициями + источниками.
6. Обнови `index.md` и `log.md`.

## Workflow: Query

1. Cascade: wiki/index.md → wiki/<page>.md → mem-search → grep → Read raw (per [[wiki/project/architecture/tooling-inventory-ru#13-llmwiki--claude-mem-cascade-rule-s30-adr-0043]]).
2. Синтезируй ответ с явными цитатами на wiki-страницы.
3. Спроси, сохранить ли в `queries/`.

## Workflow: Lint

Ищи: противоречия, устаревшее, сироты, пропуски, недостающие кросс-ссылки. Результат → запись в `log.md` + предложения.

---

## Правила гигиены

- Не выдумывай — цитируй источник или помечай `[speculation]`.
- Минимальные изменения — не переписывай страницу целиком.
- YAGNI для страниц — без 2–3 предложений содержательного знания не создавай.
- Ссылайся, а не дублируй.
- Источники обязательны.

## Language rules (BINDING per repo CLAUDE.md — пересмотрено 2026-05-09)

**Wiki content → русский язык** (full Russian — headers, body, sections):
- Все ADR в `wiki/project/decisions/*.md` — RU narrative + EN code blocks/anchors/identifiers
- Все component pages `wiki/project/components/*.md` — RU
- Все sprint pages `wiki/project/sprints/*.md` — RU
- Все architecture pages `wiki/project/architecture/*.md` — RU
- Trading strategies / indicators / patterns — RU
- index.md / log.md — RU

**EN-only:**
- File names (kebab-case latin)
- Frontmatter `tags` / `type` / `status` values
- Code blocks (Python / SQL / shell)
- Function/class names в Public API anchors
- File paths
- Library names / API endpoints
- Error string literals (логированы в src/)

**Workflow:**
- Новые wiki pages создавай сразу на русском (с момента 2026-05-09)
- Старые EN/bilingual pages — переводи incremental по мере touch (не bulk migration)
- При создании ADR — section headings на русском (`## Контекст`, `## Решение`, `## Последствия`)

## Что LLM НЕ делает

- Не модифицирует `Docs/`.
- Не удаляет страницы wiki без явного запроса (status: superseded + pointer).
- Не делает массовых rename без согласования.
- Не вставляет эмодзи без просьбы.

---

## Read tool guard

Hard-limit ~25k токенов (~90KB). Безопасный порог = **50KB**.
Если > 50KB: `Read` с `offset`+`limit` (1500–2000 строк) ИЛИ `Grep` + offset.

**Banned-from-full-read** список → `~/.claude/CLAUDE.md` section 9 (10+ files: Docs/00-All.md / sprint plans / log.md).

**Wiki-страницы** держим < 50KB. Если близко — `<topic>.md` index + `<topic>-part-N.md`.
Example (S32e split): `tooling-inventory-ru.md` (60KB) → `tooling-inventory-ru.md` (41KB Sections 1-13) + `tooling-inventory-ru-part-2.md` (24KB Sections 14-24).
**Output budget субагента:** одна Write/Edit ≤ 40KB.

---

## Anti-waste tool patterns (BINDING — detail в `~/.claude/CLAUDE.md` sections 9b/9c)

### Path verification before Read
- Project root spelling: **`AI_Traiding_Bot`** (NOT `_Tool`/`_Trader`/`_Trading`).
- `.claude/agent-memory/<agent>/MEMORY.md` (**project-local**) — auto-created on first WRITE. Read failure = expected.
- Don't-retry rule: Read miss → `ls <parent>` OR surface "path missing". Max 1 retry.
- Hook bash quirk: ALWAYS `bash -n <script>` after editing `~/.claude/hooks/*.sh`.

### Edit-after-Read invariant (CRITICAL)

**THE FORMULA:** Read × N (parallel batch) THEN Edit × N (parallel batch). NEVER skip Read step. Each unread Edit = 3× cost.

---

## Связь с code-workflow

**Сессия-старт (обязательно):**
1. Read `wiki/project/SPRINT_STATE.md` → sprint, phase, next_action
2. `git branch --show-current && git log --oneline -3`
3. `mark_chapter "Sprint N — session resume"`

**Сессия-конец (обязательно):**
1. Edit `SPRINT_STATE.md`: phase, in_progress, next_action, updated
2. Append `wiki/log.md`
3. `mark_chapter "Sprint N — session end"`

**MASTER SOP (English):** [[wiki/project/architecture/development-workflow]]
**Русская версия (BINDING per ADR 0041):** [[wiki/project/architecture/sprint-flow-ru]] — 9 фаз с per-phase HARD-GATEs
**Tooling catalog (RU):** [[wiki/project/architecture/tooling-inventory-ru]] (Sections 1-13) + [[wiki/project/architecture/tooling-inventory-ru-part-2]] (Sections 14-24, S32e split) — 11 agents + 36 skills + 8 MCP + 7+2+1 hooks + cascade
**Kit audit (S32e):** [[wiki/project/architecture/kit-audit-2026-04-27]] — usage analysis: ALL components NEEDED, no removals
**Kit overview (RU):** [[wiki/project/architecture/kit-overview-ru]] — 1-page single source of truth (S31)
**Wiki-first rule:** читай `wiki/project/components/<name>.md` ДО сырого ADR.

**Active hooks (S30+):**
- `sprint-flow-check.sh` — блокирует push на `feature/sprint-NN-*` без plan file
- `phase-advance.sh` — блокирует `gh pr merge` если SPRINT_STATE Phase 5 != "done"/"skipped"

**Cascade rule (BINDING per ADR 0043):** wiki → mem-search → grep → raw. Skip wiki check = anti-pattern. Detail [[wiki/project/architecture/tooling-inventory-ru#13-llmwiki--claude-mem-cascade-rule-s30-adr-0043]].

---

## Skills hierarchy & integration

5 layers (detail в [[wiki/project/architecture/kit-overview-ru]] + [[wiki/project/architecture/tooling-inventory-ru]]):

```
L5: Domain reviewers (9) — trading-logic / quant-stats / data-integrity / python / trader-expert / architecture / security-auditor / test-engineer / doc-reviewer
L4: Discipline (agent-skills 21) + Caveman (compression)
L3: Process (Superpowers 13) — brainstorm/plan/execute/ship
L2: Project knowledge (этот wiki) — wiki/ source of truth; Docs/ immutable
L1: Memory continuity (claude-mem MCP + ccd_session MCP)
```

**Conflict resolution + Phase mapping + Trigger cascade tables:** [[wiki/project/architecture/tooling-inventory-ru#tldr--decision-matrix-сначала-это]]

**Token economy:**
| Принцип | Правило | Выигрыш |
|---------|---------|---------|
| Wiki-first cascade | wiki → mem → grep → raw | 4-7× меньше токенов |
| Model dispatch | haiku=mechanical, sonnet=standard, opus=judgment | до 50× экономия |
| mem-search first (cascade STEP 2) | До чтения файлов — verify "did we solve X?" | секунды vs minutes |
| Parallel reviewers | Multiple Agent calls в одном message | 2-3× быстрее |
| caveman-compress | One-time CLAUDE.md/agent prompts compress | ~47% per session |
| `/btw` для side questions | Side question без context pollution | answer dismissed, не enters history |
| `/clear` между unrelated tasks | Reset context entirely | prevents kitchen-sink session |

---

## Связь с review-агентами

L5 reviewers (9 после S30) вызываются после `DONE` subagent'а, до merge. Формат отчёта: `Blockers / Concerns / Verified / Follow-ups for wiki`. `Follow-ups for wiki` → триггер wiki-update в том же спринте.

Полная матрица "спринт → агенты": [[wiki/project/architecture/tooling-inventory-ru#1-domain-reviewer-agents-9----claudeagents]]

**ADR↔agents sync hook:** `PreToolUse` на `git push` блокирует если ADR изменён без agent prompt update. Spec: [[wiki/project/components/adr-agent-sync-hook]].

---

## Autonomous mode overrides

Проект работает в **autonomous mode**: сначала инвентаризуй (Glob → Grep → git log → wiki/log tail-10 → active ADR/plan), вопрос пользователю — только если 5 шагов не дали ответа.

| Skill / Step | Override |
|---|---|
| `executing-plans` "Raise concerns" | Glob+Grep+wiki first. Вопрос только если ответ undiscoverable. |
| `executing-plans` "Worktree setup" | `feature/<sprint-N-slug>` в текущем repo. Worktree — только по запросу. |
| `brainstorming` "Get design approval" | Skip если execution of approved ADR. |
| `brainstorming` "Clarifying questions" | OVERRIDDEN by `brainstorm-init` skill — auto-routes через trader-expert ROUND 1+2. |
| `using-agent-skills` "Surface Assumptions" | Skip если assumptions в active ADR/plan/sprint page. |

---

## Anthropic best practices alignment (selective adoption)

**Adopted:** 3 CLAUDE.md layers / hooks (6 mechanical) / custom subagents (9) / project-level skills (5) / verify your work / plan-first / specific context / specific MCP / gh CLI / tool restriction.

**Selectively adopted:** AskUserQuestion (trader-expert PHASE 2) / `/clear` discipline / `/btw` (S31) / `/rewind` (S31) / `--continue` (S31) / `verification-before-completion` (S29) / Memory directory subagents (`memory: project`, S30 TIER A all 9 agents).

**NOT adopted (paradigm differs):** Native `/init` / Plan Mode (Superpowers `writing-plans` superior) / Auto mode default (sequential discipline > parallel batch).

Detail + rationale: [[wiki/project/architecture/kit-overview-ru#-best-practices-applied-per-anthropic-claude-code-docs]]
