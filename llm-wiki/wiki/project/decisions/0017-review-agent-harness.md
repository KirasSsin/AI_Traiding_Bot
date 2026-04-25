---
title: 0017. Review-agent harness — three domain reviewers + python-reviewer
type: decision
tags: [adr, agents, review, process, superpowers]
created: 2026-04-22
updated: 2026-04-22
sources: [project/sprints/sprint-03-strategy-port.md, project/sprints/sprint-04-risk.md, project/sprints/sprint-05-execution.md, project/sprints/sprint-06-spot-oco-emulation.md, project/sprints/sprint-07-resilience.md]
status: accepted
---

# 0017. Review-agent harness — three domain reviewers + python-reviewer

**Status:** accepted
**Date:** 2026-04-22

## Context

Sprint 3 завершён. Стек ревью к этому моменту:
- `superpowers:requesting-code-review` — generic code review между задачами.
- `superpowers:verification-before-completion` — gate перед merge.
- `python-reviewer` (downloaded в `~/.claude/agents/`) — общий Python hygiene (PEP 8, type hints, security, performance).

Эти инструменты не покрывают **доменные риски** торгового бота: look-ahead bias, execution timing invariant (close T → open T+1), корректность Wilder vs classical EMA, Kelly phases, walk-forward параметры, OHLCV invariants. Generic Python ревьюер не знает наших ADR и не отличит правильную формулу Wilder от неправильной.

Альтернативный набор из 14 "персон" (Джон/Сол/Дон/Лола/Илья/…) был рассмотрен и отклонён: в Claude Code агент = вызываемый инструмент, не "член команды". 14 agents с пересекающимся scope создают конфликт выбора у главного Claude и расщепляют контекст. Нужны 3-4 агента с **non-overlapping scope** и **чёткими триггерами** в `description`.

## Options

- **A. Не создавать доменных агентов.** Полагаться на superpowers + python-reviewer + ручной контроль через wiki.
  - Минус: реальные доменные баги (look-ahead, неверная формула Wilder, мажик-числа Kelly) проскользнут — generic ревью их не ловит.
- **B. 14 агентов по списку sonnet 4.6 (Джон/Сол/…/Девопс).**
  - Минус: 60-70% overlap (Сол ↔ Дон ↔ Лола ↔ Илья все смотрят одни и те же файлы); главный Claude не сможет надёжно выбрать; контекст-цена × 14.
- **C. 3 консолидированных ревьюера + сохранить python-reviewer.** Каждый = объединение ролей с близким scope. **Выбрано.**

## Decision

Создаём **три** новых агента в `~/.claude/agents/` + оставляем `python-reviewer`:

| Агент | Файл | Модель | Поглощает (из набора 14) | Триггер (description) |
|---|---|---|---|---|
| `trading-logic-reviewer` | `~/.claude/agents/trading-logic-reviewer.md` | sonnet (4.6) | Джон + Илья + Бен | Изменения в `src/signalgen/`, `src/execution/`, `src/backtest/`, `src/risk/`. |
| `quant-stats-reviewer` | `~/.claude/agents/quant-stats-reviewer.md` | sonnet (4.6) | Сол + Дон + Лола | Изменения в `src/signalgen/indicators.py`, `src/risk/`, `src/backtest/`, `src/analytics/`. |
| `data-integrity-reviewer` | `~/.claude/agents/data-integrity-reviewer.md` | sonnet | Марина | Изменения в `src/marketdata/`, `src/platform/storage/`, `migrations/`, путях персистенции order/fill. |
| `python-reviewer` (уже есть) | `~/.claude/agents/Python Reviewer.md` | sonnet | (generic) | Любые изменения `*.py`. |
| `architecture-reviewer` (S8c+) | `~/.claude/agents/architecture-reviewer.md` | sonnet (4.6) | (новая роль) | Cross-module refactor, concurrency design (async migration, lock policy), DI patterns, component decomposition, cross-cutting concerns (error propagation, retry, structured logging), performance patterns, API stability, cohesion/coupling analysis. NOT для trading semantics (trader-expert) / math (quant-stats) / storage (data-integrity) / Python idioms (python). |

Каждый агент:
1. Имеет `description` с фразой "MUST BE USED for ..." — это сигнал главному Claude для proactive-вызова.
2. Перед ревью **обязан** прочитать конкретные wiki-страницы и ADR (список в prompt'е). Это превращает агента в продолжение wiki, а не самостоятельный источник правды.
3. Возвращает строго форматированный отчёт: `❌ Blockers / ⚠️ Concerns / ✅ Verified / Follow-ups for wiki`.
4. Не делает разрушительных операций (git/SQL/file rewrite); только Read + Grep + Glob + Bash для `git diff`/линтеров.

**Отклонены роли:**
- **Ольга (QA)** — покрывается `superpowers:verification-before-completion` + `superpowers:requesting-code-review` + `python-reviewer`.
- **Мини (architect)** — одноразовая роль, архитектура зафиксирована в `wiki/project/architecture/`.
- **Диджет (PM)** — продуктовые решения принимает человек.
- **Вика / Девопс / Рустам / Макс** — out of scope для v0.1 (UI, контейнеризация, Rust hot-path, ML — всё v0.2+).

## When to invoke

| Контекст изменений | Обязательные агенты | Опциональные |
|---|---|---|
| Чистый refactor `src/platform/` (config, logging) | `python-reviewer` | — |
| MarketData / storage / migrations | `data-integrity-reviewer`, `python-reviewer` | — |
| Strategy / indicators (S3) | `trading-logic-reviewer`, `quant-stats-reviewer`, `python-reviewer` | — |
| Risk / Kelly / CB (S4) | `quant-stats-reviewer`, `trading-logic-reviewer`, `python-reviewer` | `data-integrity-reviewer` если затронут event store |
| Execution (S5) | `trading-logic-reviewer`, `python-reviewer` | `data-integrity-reviewer` если меняется persistence ордеров/fills |
| Backtest engine (S7) | все три + `python-reviewer` | — |
| Walk-Forward / DSR / MC (S8-S9) | `quant-stats-reviewer`, `python-reviewer` | `trading-logic-reviewer` если касается replay engine |

Главный Claude вызывает агентов **после** того, как реализующий subagent доложил о завершении задачи (этап `subagent-driven-development` → spec review → quality review). Доменные ревьюеры заменяют generic quality reviewer для соответствующих изменений; для нейтральных файлов остаётся стандартный flow.

## Consequences

- **Плюс:** доменные баги (look-ahead, неверный Wilder, magic numbers в Kelly) ловятся до merge, без эскалации к человеку.
- **Плюс:** агенты являются операционализацией wiki — каждое ревью ссылается на конкретные ADR и страницы, что естественно подсвечивает stale wiki.
- **Минус:** дополнительный context cost на спринтах S3-S8 (3 агента × ~8k токенов на review). Компенсируется отсутствием багов на проде.
- **Минус (закрыт):** агенты надо синхронизировать с wiki — если меняется ADR, надо обновить и prompt агента. **Автоматизировано** через `PreToolUse` hook на `git push` — см. [[../components/adr-agent-sync-hook]]. Push блокируется, если ADR изменён в пушимых коммитах, а mtime ни одного `~/.claude/agents/*.md` не продвинут после ADR-коммита.

## Related

- `~/.claude/agents/trading-logic-reviewer.md`
- `~/.claude/agents/quant-stats-reviewer.md`
- `~/.claude/agents/data-integrity-reviewer.md`
- `~/.claude/agents/python-reviewer.md` (renamed from "Python Reviewer.md" 2026-04-23 — filename normalization, см. [[../../CLAUDE]] Cleanup history)
- `~/.claude/agents/trader-expert.md` (S7+ addition — PHASE 2 brainstorming decision-maker, sonnet; не reviewer но входит в curated agent set; полная роль см. [[development-workflow]] PHASE 2 step 3)
- [[../architecture/development-workflow]] — Superpowers pipeline (review гейт интегрирован сюда).
- [[../decisions/0001-record-architecture-decisions]]

## Amendments

- **2026-04-24 (post-S7):** Добавлен `trader-expert` (sonnet) в curated agent set как decision-maker последней инстанции в PHASE 2 brainstorming. Не reviewer (не вызывается в PHASE 5), но обязателен в PHASE 2 если есть unresolved scope/architecture questions перед PHASE 3. Filename: `~/.claude/agents/trader-expert.md`.
- **2026-04-24 (post-S8a):** `trading-logic-reviewer` model `opus` → `sonnet` (4.6 alias). Sonnet 4.5+ имеет встроенный extended thinking, достаточный для review depth (S7+S8a empirically: opus override не дал blockers > sonnet baseline на 3 раундах). Cost reduction ~5×. Dispatch override policy: future Agent calls используют `subagent_type: "trading-logic-reviewer"` БЕЗ `model: "opus"` override — alias auto-routes к latest sonnet. Файл `~/.claude/agents/trading-logic-reviewer.md` frontmatter `model: sonnet` (без изменений; drift был только в ADR + CLAUDE.md аннотации).
- **2026-04-24 (post-S8a, follow-up):** `quant-stats-reviewer` model `opus` → `sonnet` (4.6 alias) — единая политика для всех 5 агентов. Формулы (Wilder/EMA), Wilson CI, Kelly fraction, Monte Carlo permutations, DSR покрываются sonnet 4.5+ extended thinking. Cost reduction ~5×. Файл `~/.claude/agents/quant-stats-reviewer.md` frontmatter `model: opus` → `sonnet`. Escalate обратно к `opus` только если S9+ DSR/MC модули дадут empirical evidence что sonnet пропускает blockers (re-evaluate post-S9 quant suite). Все 5 curated агентов теперь sonnet (`python-reviewer`, `data-integrity-reviewer`, `trading-logic-reviewer`, `quant-stats-reviewer`, `trader-expert`).
- **2026-04-25 (post-S8c PR-β):** Добавлен 6-й агент `architecture-reviewer` (sonnet 4.6) для purely architectural decisions без trading semantics — cross-module refactor, concurrency design (async migration / lock policy), DI patterns, component decomposition, cross-cutting concerns (error propagation / retry / structured logging), performance patterns, API stability, cohesion/coupling analysis. Filename: `~/.claude/agents/architecture-reviewer.md`. Триггер: MUST BE USED before any architectural change spanning multiple modules OR when concurrency model touched. Dispatch policy: NOT для trading domain semantics (defer к trading-logic-reviewer), math correctness (quant-stats-reviewer), storage (data-integrity-reviewer), Python idioms (python-reviewer). Closes long-standing gap (см. llm-wiki/CLAUDE.md "Recommended add" mention since post-S7).
- **2026-04-25 (post-S8c PR-β, TIER A):** Все 6 агентов получили `memory: project` frontmatter field (institutional knowledge accumulation across sprints) + Sprint context priming section (mandatory canonical file loads on every dispatch). Trader-expert + quant-stats-reviewer additionally получили `effort: max` (deeper thinking для critical reasoning paths — trader-expert ROUND 2 iterative justify + quant math). Per Anthropic best practices: persistent memory + lazy-load priming = ~15-20% sprint efficiency gain (drift prevention + repeat-issue detection).
