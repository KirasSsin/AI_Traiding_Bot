---
title: 0017. Review-agent harness — three domain reviewers + python-reviewer
type: decision
tags: [adr, agents, review, process, superpowers]
created: 2026-04-22
updated: 2026-04-22
sources: []
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
| `trading-logic-reviewer` | `~/.claude/agents/trading-logic-reviewer.md` | opus | Джон + Илья + Бен | Изменения в `src/signalgen/`, `src/execution/`, `src/backtest/`, `src/risk/`. |
| `quant-stats-reviewer` | `~/.claude/agents/quant-stats-reviewer.md` | opus | Сол + Дон + Лола | Изменения в `src/signalgen/indicators.py`, `src/risk/`, `src/backtest/`, `src/analytics/`. |
| `data-integrity-reviewer` | `~/.claude/agents/data-integrity-reviewer.md` | sonnet | Марина | Изменения в `src/marketdata/`, `src/platform/storage/`, `migrations/`, путях персистенции order/fill. |
| `python-reviewer` (уже есть) | `~/.claude/agents/Python Reviewer.md` | sonnet | (generic) | Любые изменения `*.py`. |

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
- **2026-04-24:** Подтверждён model assignment per file frontmatter после агент audit: `trading-logic-reviewer = opus`, `quant-stats-reviewer = opus`, `data-integrity-reviewer = sonnet`, `python-reviewer = sonnet`, `trader-expert = sonnet`. Drift между ADR и frontmatter устранён (был sonnet в trading-logic-reviewer.md — исправлено на opus).
