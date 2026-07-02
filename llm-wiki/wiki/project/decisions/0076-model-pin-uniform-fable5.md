---
title: "0076. Model pin — uniform claude-fable-5 (суперседит 0075 mixed-tier)"
type: decision
status: accepted
created: 2026-07-02
updated: 2026-07-02
---

# 0076. Uniform fable-5 pin-policy

**Status:** accepted (оператор 2026-07-02)
**Date:** 2026-07-02
**Supersedes:** [[0075-model-pin-policy-v2]]

## Контекст

ADR 0075 ввёл смешанные тиры: judgment-heavy → `claude-fable-5`, механическое/low-risk → алиас (`sonnet`/`haiku`/`opus`). Оператор пересмотрел приоритет: **токен-бюджет НЕ ограничен, важна максимальная глубина проработки на каждом агенте** (в т.ч. «дешёвые» consistency/lint/draft роли). Экономия тира больше не цель; качество > дешевизна.

## Решение

**ВСЕ агенты (18) = `claude-fable-5`** — явный версионный пин, без исключений и алиасов.

- Отменяет mixed-tier ADR 0075. Алиасов (`sonnet`/`haiku`/`opus`) в реестре больше нет.
- **Safety-fallback приемлем (директива оператора):** при срабатывании safety-правила `claude-fable-5` → авто-переключение на `claude-opus-4-8` max — это ОК, не деградация.
- Новый агент → `claude-fable-5` по умолчанию.
- 6 money/domain-ревьюеров (trading-logic / quant-stats / data-integrity / bybit-api / dashboard / test-engineer) подняты sonnet-5 → fable-5. Аргумент 0075 «воспроизводимость вердиктов на sonnet» уступает предпочтению оператора «глубже ревью money-кода».

## Последствия

- `kit/PINNED_VERSIONS.md` переписан: 18 строк, все `claude-fable-5`.
- Оба дерева агентов (`kit/agents/` зеркало + живой `~/.claude/agents/`) — `model: claude-fable-5`, `diff -rq` clean.
- kit-auditor (dim-8 pin-registry): ожидание = uniform fable-5; любой не-fable пин = drift.
- **Триггер ревью сохранён из 0075:** при выходе нового платформенного дефолта fable-5 — re-review реестра (пин ≥2 релиза позади = HARD-STALE). `last-reviewed` в реестре.
- Стоимость: выше токен-расход на механических ролях (lint/consistency/draft) — принято осознанно (бюджет не ограничен).

## Связано
[[0075-model-pin-policy-v2]] · [[0074-runtime-tuning]] · [[../architecture/kit-overview-ru]] · `kit/PINNED_VERSIONS.md` · kit-auditor агент
