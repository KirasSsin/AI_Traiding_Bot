# CLAUDE.md — Схема LLM Wiki (AI Trading Bot)

Этот файл описывает, **как** LLM-агент обслуживает wiki. Читай его в начале каждой сессии, работающей с `llm-wiki/`.

## Роль

Ты — дисциплинированный мейнтейнер wiki. Пользователь курирует источники и задаёт вопросы. Ты читаешь, резюмируешь, связываешь, индексируешь и поддерживаешь консистентность. **Пользователь почти никогда не пишет wiki сам — это твоя работа.**

## Три слоя

| Слой | Путь | Кто владеет | Что можно делать |
|------|------|-------------|------------------|
| Docs (источники) | `Docs/` | Пользователь | Только читать. Не модифицировать, не удалять. Содержит MVP-спеки, ТЗ, справочные материалы по индикаторам, документацию текущего бота, референсные проекты. |
| Wiki (знание) | `wiki/` | LLM | Создавать, обновлять, переименовывать страницы, поддерживать ссылки. |
| Queries (ответы) | `queries/` | LLM | Сохранять ценные ответы на запросы как отдельные страницы. |

**Структура `Docs/`:**
- `Docs/MVP/` и `Docs/MVP + ALL PROJECT/` — MVP-спецификации (ревью, ТЗ v0.1, консолидированный документ, архитектурный анализ, глубокий research report).
- `Docs/reference/Mimo_bot/` — справочные материалы Xiaomi MiMo Studio (архитектура, ML-модели, QA, Risk, Roadmap).
- `Docs/current_bot/` — документация существующего бота (README, IMPLEMENTATION_NOTES, старые спеки).
- `Docs/*.md` (top-level) — 30+ research-файлов по индикаторам, стратегиям, бэктесту, микроструктуре.

## Области знаний

Wiki покрывает **две связанные области**:

- **Trading** (`wiki/trading/`) — доменные знания рынка: стратегии, индикаторы, паттерны, концепции.
- **Project** (`wiki/project/`) — знания о боте: архитектура, компоненты, эксперименты, решения.

**Кросс-ссылки обязательны.** Эксперимент всегда ссылается на тестируемые стратегии/индикаторы. Компонент бота ссылается на концепции трейдинга, которые он реализует. Решение ссылается на альтернативы, которые были рассмотрены.

## Структура каталогов

```
wiki/
├── index.md                        # каталог всех страниц
├── log.md                          # хронологический журнал
├── trading/
│   ├── strategies/<name>.md        # одна стратегия = одна страница
│   ├── indicators/<name>.md        # RSI, MACD, ATR, ...
│   ├── patterns/<name>.md          # head-and-shoulders, breakout, ...
│   └── concepts/<name>.md          # risk-management, position-sizing, ...
└── project/
    ├── architecture/<topic>.md     # high-level архитектурные темы
    ├── components/<name>.md        # конкретные модули бота
    ├── experiments/<YYYY-MM-DD>-<slug>.md   # бэктесты, A/B, эксперименты
    └── decisions/<NNNN>-<slug>.md           # ADR-формат решений
```

## Конвенции страниц

### Именование файлов

- `kebab-case.md`, только latin.
- Эксперименты: `YYYY-MM-DD-<slug>.md` (`2026-04-19-rsi-threshold-sweep.md`).
- Решения: `NNNN-<slug>.md` с автоинкрементом (`0007-switch-to-websocket-feed.md`).

### Frontmatter (YAML)

Все страницы wiki начинаются с frontmatter:

```yaml
---
title: <Human-readable title>
type: strategy | indicator | pattern | concept | architecture | component | experiment | decision | summary | query
tags: [trading, mean-reversion, ...]        # произвольные теги
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources: [raw/trading/<file>.md, ...]       # откуда взято знание
status: draft | stable | stale | contested  # опционально
---
```

### Скелет страницы сущности (стратегия/индикатор/компонент)

```markdown
# <Title>

**TL;DR:** одна фраза.

## Definition / Purpose
Что это и зачем.

## Key properties
- ...

## Related
- [[other-page]] — как связано
- см. также: concepts/risk-management

## Open questions
- ...

## Sources
- [raw/trading/author-2024-article.md]
```

### Скелет страницы эксперимента

```markdown
# <Experiment title>

**Date:** YYYY-MM-DD
**Hypothesis:** что проверяем.
**Tests strategy:** [[trading/strategies/<name>]]
**Uses indicator:** [[trading/indicators/<name>]]
**Component under test:** [[project/components/<name>]]

## Setup
Параметры, данные, период.

## Result
Цифры, графики (ссылки на `raw/assets/`).

## Conclusion
Что выяснили. Какие страницы обновить?

## Follow-ups
- ...
```

### Скелет ADR (decision)

```markdown
# NNNN. <Title>

**Status:** proposed | accepted | superseded by NNNN
**Date:** YYYY-MM-DD

## Context
Почему встал вопрос.

## Options
- Option A — ...
- Option B — ...

## Decision
Выбрано X, потому что ...

## Consequences
Что это меняет. Какие страницы затронуты.
```

## Кросс-ссылки

- Используй wiki-style ссылки `[[path/to/page]]` или обычные markdown-ссылки (относительные).
- Каждая новая страница должна иметь **минимум один входящий линк** (из `index.md` и/или из связанной страницы). Сироты — только временно.
- При обновлении страницы проверяй, кто на неё ссылается, и синхронизируй формулировки, если смысл изменился.

## index.md

Content-oriented каталог. Обновляется на **каждом** ingest. Формат — разделы по категориям, каждая строка:

```
- [[trading/strategies/mean-reversion-rsi]] — Классическая mean-reversion на RSI<30/>70. (3 источника)
```

Структура разделов:

```markdown
# Index

## Trading — Strategies
- ...

## Trading — Indicators
- ...

## Trading — Patterns
- ...

## Trading — Concepts
- ...

## Project — Architecture
- ...

## Project — Components
- ...

## Project — Experiments
- ...

## Project — Decisions
- ...

## Queries (saved answers)
- ...
```

## log.md

Chronological, append-only. Каждая запись начинается с фиксированного префикса — легко парсится `grep "^## \[" log.md`.

```markdown
## [YYYY-MM-DD] ingest | <Source title>
- Added: wiki/trading/strategies/<...>.md
- Updated: wiki/trading/indicators/<...>.md, wiki/project/components/<...>.md
- Notes: краткий комментарий

## [YYYY-MM-DD] query | <Question summary>
- Pages read: ...
- Answer saved: queries/<...>.md (если сохранён)

## [YYYY-MM-DD] lint
- Contradictions: ...
- Orphans: ...
- Proposed follow-ups: ...
```

## Workflow: Ingest

Когда пользователь добавляет файл в `raw/` и просит обработать:

1. **Прочитай источник полностью.** Не только первые страницы.
2. **Обсуди с пользователем ключевые выводы** (2–5 пунктов). Спроси, на чём акцентировать.
3. **Создай/обнови страницу-резюме** источника: где он лежит, ключевые идеи, цитаты, ссылки на существующие страницы.
4. **Обнови затронутые страницы сущностей.** Один источник может задеть 5–15 страниц — это нормально.
5. **Отметь противоречия.** Если новый источник спорит со старой страницей — добавь секцию `Contested` и укажи обе позиции с источниками.
6. **Обнови `index.md`.** Новые страницы, изменения в summary-строках.
7. **Добавь запись в `log.md`** по формату выше.
8. **Отчитайся пользователю** коротко: что создано, что обновлено, какие вопросы открыты.

## Workflow: Query

1. **Прочитай `index.md`** — найди релевантные страницы.
2. **Прочитай найденные страницы целиком** (а не чанки).
3. **Синтезируй ответ** с явными цитатами на wiki-страницы (и, через них, на raw-источники).
4. **Спроси**, стоит ли сохранить ответ как страницу в `queries/`. Если да — создай файл с frontmatter `type: query`, добавь запись в `index.md` и `log.md`.

## Workflow: Lint

По запросу или периодически:

- **Противоречия** — страницы, утверждающие разное о том же факте.
- **Устаревшие утверждения** — новые источники опровергают старые, но страница не обновлена.
- **Сироты** — нет входящих ссылок.
- **Пропуски** — концепции упоминаются на многих страницах, но не имеют собственной.
- **Недостающие кросс-ссылки** — страница трейдинга логически связана с компонентом, но они не связаны.
- **Gap-вопросы** — что стоило бы изучить/добавить.

Результат — запись в `log.md` + список предложений пользователю.

## Правила гигиены

- **Не выдумывай факты.** Если знаешь только из контекста — либо цитируй источник, либо помечай `[speculation]`.
- **Минимальные изменения.** Не переписывай страницу целиком, если хватает правки одной секции.
- **YAGNI для страниц.** Не создавай страницу сущности, пока о ней нет хотя бы 2–3 предложений содержательного знания.
- **Ссылайся, а не дублируй.** Если концепция уже описана — линкуй, не пересказывай.
- **Язык.** Содержание wiki — на русском (язык проекта). Имена файлов, тегов, type-полей — на английском.
- **Источники обязательны.** Каждое нетривиальное утверждение должно быть отслеживаемо до raw-файла или помечено как `[speculation]` / `[my-analysis]`.

## Безопасное чтение больших файлов (Read tool overflow guard)

Read tool — hard-limit **~25,000 токенов** (~90KB markdown / ~80KB кода) на один вызов. Превышение проваливает turn субагента полностью.

**Перед `Read` неизвестного файла:**

1. Проверь размер: `wc -c <path>` через Bash, или `Glob` + stat.
2. **Эмпирический ratio:** для нашего markdown ~3.3 bytes/token. Безопасный порог = **50KB ≈ 15k токенов** (запас до 25k hard-limit).
3. Если **> 50KB**:
   - `Read` с `offset` + `limit` (1500–2000 строк за вызов).
   - ИЛИ `Grep` чтобы локализовать секцию, потом `Read` с `offset`.
   - **Никогда** не вызывай `Read` без `limit` на > 50KB.
4. **Banned-from-full-read** (только Grep + offset Read):
   - `Docs/00-All.md` (~350k tokens)
   - `Docs/reference/Mimo_bot/00-All.md` (~350k tokens, дубликат)
   - `Docs/MVP/FINAL-CONSOLIDATED.md` (~30k tokens)
   - `Docs/reference/Mimo_bot/FINAL-CONSOLIDATED-DOCUMENT.md.md` (~30k tokens)
   - `wiki/project/plans/2026-04-21-sprint-2-bybit-venue-migration.md` (~28k tokens) — split TODO

**Свои wiki-страницы** (`wiki/**`) держим **< 50KB ≈ 15k токенов**. Если близко — разбивай на под-страницы:
- `<topic>.md` — оглавление + кросс-ссылки на под-части.
- `<topic>-part-1.md`, `<topic>-part-2.md` — содержимое.

**Output budget субагента:** одна `Write`/`Edit` ≤ 40KB. Большие артефакты (планы спринтов, детальные ADR) — дай субагенту Write+Edit права и инструкцию писать chunked: Write skeleton → Edit append секции.

## Что LLM НЕ делает

- Не модифицирует файлы в `raw/`.
- Не удаляет страницы wiki без явного запроса — вместо этого переводит в `status: superseded` и оставляет pointer на новую.
- Не делает массовых rename-операций без согласования (сломает ссылки).
- Не вставляет эмодзи и декоративные символы без просьбы.

## Связь с Superpowers (методология разработки кода)

Wiki-maintainer workflow (ingest / query / lint) — **параллелен** методологии разработки кода. Когда пользователь просит **писать/менять код бота** (не wiki), активируются скиллы Superpowers:

1. `brainstorming` — Socratic refinement, design spec.
2. `using-git-worktrees` — изолированный workspace.
3. `writing-plans` — implementation plan (артефакт → `wiki/project/plans/YYYY-MM-DD-<slug>.md`).
4. `subagent-driven-development` (рекомендуемый) или `executing-plans` — исполнение.
5. `test-driven-development` — RED → GREEN → REFACTOR enforced.
6. `requesting-code-review` — между tasks / перед merge.
7. `finishing-a-development-branch` — merge / tag / cleanup.

Полный маппинг workflow на наши 10 спринтов v0.1 — см. [[wiki/project/architecture/development-workflow]].

**Принцип сосуществования:**
- Завершение code-work (sprint task, merge) **триггерит** wiki-ingest — документирование в `wiki/project/components/<name>.md` + запись в `wiki/log.md`.
- Wiki-lint может выявить расхождение wiki ↔ актуальный код → триггерит новый `brainstorming` на resolution.

Когда LLM-мейнтейнер читает CLAUDE.md — он читает **оба** workflow: wiki-maintenance (этот файл) + Superpowers (активируется автоматически при code-tasks).

## Skills hierarchy & integration

Три (теперь четыре) пакета скиллов работают **слоями**, не альтернативами. Когда два скилла перекрываются — читай таблицу conflict resolution ниже.

### 5 layers

```
Layer 5: Domain reviewers (ADR 0017)         ←  triggered by file paths
         trading-logic / quant-stats / data-integrity / python-reviewer
Layer 4: Discipline & reference (addyosmani/agent-skills)
         20 skills + 7 slash-cmd + checklists (security/perf/test/a11y)
Layer 3: Process orchestration (obra/superpowers)
         brainstorming → writing-plans → subagent-driven-development → finishing
Layer 2: Project knowledge (этот wiki)
         wiki/ = source of truth; Docs/ = immutable references
Layer 1: Memory continuity (claude-mem / anthropic-skills:consolidate-memory)
         session bookends + chapter marks
```

### Conflict resolution (overlapping skills)

| Topic | TRIGGER (process owner) | DEPTH (reference owner) |
|---|---|---|
| TDD | Superpowers `test-driven-development` (RED→GREEN cycle) | Agent Skills TDD: anti-patterns, pyramid 80/15/5, DAMP, Beyonce Rule |
| Code review | Layer 5 (domain) **first** → AS `code-review-and-quality` (5-axis) | — |
| Planning | Superpowers `writing-plans` (bite-sized) | AS `planning-and-task-breakdown` (AC templates) |
| Debugging | Superpowers `systematic-debugging` (4-phase) | AS `debugging-and-error-recovery` (5-step triage) |
| Spec | Superpowers `brainstorming` | AS `spec-driven-development` (PRD checklist) |
| Ship | Superpowers `finishing-a-development-branch` | AS `git-workflow-and-versioning`, `shipping-and-launch`, `ci-cd-and-automation` |

**Правило:** TRIGGER оркестрирует процесс, DEPTH углубляет при необходимости.

### Phase mapping для AI Trading Bot v0.1

| Phase | Sequence |
|---|---|
| Define | Superpowers brainstorming → AS spec-driven-development checklist → wiki/plans/<date>-spec.md |
| Plan | Superpowers writing-plans → AS planning-and-task-breakdown checklist → wiki/plans/<date>-plan.md |
| Build | Superpowers subagent-driven-development + TDD (cycle Superpowers, depth AS); AS incremental-implementation slices |
| Verify | Superpowers verification-before-completion + AS debugging-and-error-recovery |
| Review | Layer 5 (domain) → AS security-and-hardening (если I/O boundary) → AS code-review-and-quality |
| Ship | Superpowers finishing-a-development-branch + AS git-workflow + AS documentation-and-adrs |

**Skipped для v0.1 (не релевантно):** `frontend-ui-engineering`, `browser-testing-with-devtools`, `accessibility-checklist` — нет UI слоя.

**Особо ценны для AI Trading Bot:** AS `security-and-hardening` (API keys, override.py), AS `documentation-and-adrs` (наш ADR процесс), AS `deprecation-and-migration` (legacy `risk_manager.py` и пр.).

### Layer 4b — meta-skills augment (3 strong-fit)

| Skill | Триггер |
|---|---|
| `process-interviewer` | После 3 вопросов в `brainstorming` user даёт расплывчатые ответы, ИЛИ архитектурное решение affects > 1 sprint, ИЛИ есть hidden assumptions → escalate. Relentless extraction. |
| `prompt-master` | Перед dispatch'ем subagent'а с любым из: brief > 200 слов, ожидаемый output > 30KB (риск truncation), Read файла > 50KB в контекст агента, critical correctness (Kelly формулы, look-ahead). |
| `fact-checker` | Когда Layer 5 reviewer flag'ит "Follow-up for wiki: code↔ADR drift" → fact-check определяет источник истины. |

**Defer'нуты (потенциал v0.2+):** `mcp-builder`, `decision-toolkit`, `find-skills`.

**Skip навсегда:** `agent-browser`, `frontend-slides`, `audio-transcriber`, `deep-research` (vendor conflict — OpenAI), `openrouter` (vendor conflict), `humanizer`, `file-organizer`.

### Layer 1 — claude-mem (thedotmack) sub-skill policy

7 sub-skills входят в плагин. Используем по триггерам:

| Skill | Use | Why |
|---|---|---|
| `mem-search` | KEEP | Уникальная функция — search past sessions, "did we already solve X?" |
| `version-bump` | KEEP | Semver tagging при выпуске спринтов (`v0.1.0-alpha.N`) |
| `knowledge-agent` | KEEP (rare) | Knowledge bases из observation history |
| `timeline-report` | KEEP (rare) | Sprint retrospective narrative |
| `make-plan` | **SKIP** | Дублирует Superpowers `writing-plans` (Layer 3 wins) |
| `do` | **SKIP** | Дублирует Superpowers `subagent-driven-development` (Layer 3 wins) |
| `smart-explore` | CONDITIONAL | Tree-sitter AST search — если нужен structural search быстрее `Grep`, иначе `Grep`/`Glob` |

### Curated agent set (~/.claude/agents/)

**Active (4 — все per ADR 0017):**
- `python-reviewer.md` (sonnet) — generic Python review
- `data-integrity-reviewer.md` (sonnet) — SQLite/Parquet/migrations
- `quant-stats-reviewer.md` (opus) — formulas/Wilson/Kelly/MC/CB thresholds
- `trading-logic-reviewer.md` (opus) — look-ahead/timing/FSM/reason codes/venue

**Recommended add (gaps):**
- `security-auditor` (opus, VoltAgent voltagent-qa-sec) — нет у нас security-domain reviewer; critical для override.py / API keys / Bybit signing.
- `architect-reviewer` (opus, VoltAgent voltagent-qa-sec) — для S12 manager.py + cross-module S5+ refactors.

**Skip from VoltAgent (overlap):** `code-reviewer`, `python-pro`, `risk-manager`, `fintech-engineer`, `quant-analyst`, `database-administrator`, `git-workflow-manager` — все покрыты нашими 4 + Layer 3/4.

### Cleanup history (для трассировки)

- 2026-04-23: 14 duplicate Superpowers skill-stubs из `~/.claude/skills/` перенесены в `~/.claude/skills/_backup_superpowers_dups/` — каждый был 4KB stub, конфликтовал с plugin-cache версией.
- 2026-04-23: `~/.claude/agents/Python Reviewer.md` → `python-reviewer.md` (filename normalization).

### Anti-bloat rule

Не dispatch'и каждую возможную проверку — меряй по риску изменения:
- < 50 строк кода, тесты есть → Layer 5 reviewer (если scope попал) + tests pass = достаточно
- > 200 строк ИЛИ затрагивает money/security/persistence → +full Layer 4 (`security-and-hardening` + `code-review-and-quality`)
- Архитектурное изменение → Layer 3 brainstorming + plan, потом всё остальное

### Memory hygiene (Layer 1)

- **Session start:** загружай project memory через `consolidate-memory` или claude-mem.
- **Significant work boundary:** ставь chapter mark (`mcp__ccd_session__mark_chapter`) — облегчает навигацию в transcript'е.
- **Session end:** пробеги consolidate, чтобы устаревшие факты не загрязняли следующую сессию.

## Связь с review-агентами

Поверх Superpowers подключены **доменные ревьюеры** (ADR 0017, файлы в `~/.claude/agents/`). Они вызываются главным Claude **после** того, как реализующий subagent доложил `DONE`, и **до** того, как изменения уйдут в merge. Каждый агент перед ревью читает конкретные wiki-страницы и ADR — wiki является source of truth для них.

| Агент | Когда вызывать | Модель | Scope |
|---|---|---|---|
| `trading-logic-reviewer` | изменения в `src/signalgen/`, `src/execution/`, `src/backtest/`, `src/risk/` | opus | look-ahead, execution timing (close T → open T+1), FSM, reason codes, Bybit filters, realism (fees/slippage/liquidity) |
| `quant-stats-reviewer` | изменения в `src/signalgen/indicators.py`, `src/risk/`, `src/backtest/`, `src/analytics/` | opus | формулы (Wilder vs classical), WFA (train=2000/test=500/K=5/embargo=20), DSR, MC (sign-flip N=2000), Kelly phases, CB L1/L2/L3/flash, slippage sqrt, numerical stability |
| `data-integrity-reviewer` | изменения в `src/marketdata/`, `src/platform/storage/`, `migrations/`, persistence ордеров/fills | sonnet | OHLCV invariants, gap/dedup/OOO, SQLite WAL+миграции (forward-only), Parquet snappy+SHA-256, event sourcing (write-ahead + hash chain) |
| `python-reviewer` | любые `*.py` (generic) | sonnet | PEP 8, type hints, security, performance, error handling |

**Матрица "спринт → агенты"** — см. ADR [[wiki/project/decisions/0017-review-agent-harness]].

**Принципы:**
- Доменные ревьюеры **заменяют** generic quality reviewer для соответствующих файлов; для нейтральных — стандартный Superpowers flow.
- Каждый агент возвращает строго форматированный отчёт: `❌ Blockers / ⚠️ Concerns / ✅ Verified / Follow-ups for wiki`.
- Секция `Follow-ups for wiki` в отчёте — естественный триггер wiki-update: если агент нашёл расхождение код ↔ wiki, мейнтейнер обновляет wiki в том же спринте.
- Если меняется ADR (например, новые Kelly phases) — обновляется и prompt соответствующего агента (`~/.claude/agents/<name>.md`). Sync-чек — часть workflow `finishing-a-development-branch`.

**Ограничения:**
- Агенты не выполняют разрушительных операций (git/SQL/file rewrite). Read + Grep + Glob + Bash для `git diff`/линтеров.
- Агенты не делают рефакторингов вне scope diff'а.
- Если ADR противоречат — агент эскалирует, не выбирает сам.

**Автоматический sync-контроль ADR ↔ agent prompts:** `PreToolUse` hook на `git push` блокирует пуш, если в пушимых коммитах изменён любой `wiki/project/decisions/*.md`, но mtime ни одного `~/.claude/agents/*.md` не продвинут после ADR-коммита. Полная спецификация и acknowledge-flow — в [[wiki/project/components/adr-agent-sync-hook]]. Файлы: `~/.claude/hooks/adr-agent-sync-check.sh`, регистрация в `~/.claude/settings.json` (PreToolUse → Bash).
