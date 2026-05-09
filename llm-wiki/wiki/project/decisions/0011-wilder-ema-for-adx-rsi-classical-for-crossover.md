---
title: 0011. Wilder EMA for ADX/RSI/ATR, Classical EMA for crossovers
type: decision
tags: [adr, v0.1, indicators, ema, wilder, ta-lib]
created: 2026-04-19
updated: 2026-04-19
status: accepted
sources: [Docs/MVP + ALL PROJECT/MVP.md]
---

# 0011. Wilder EMA for ADX/RSI/ATR, Classical EMA for crossovers

**Status:** Accepted
**Date:** 2026-04-19

## Context
EMA имеет две разные конвенции сглаживания: классическая `α = 2/(n+1)` и
Wilder's smoothing `α = 1/n`. Они соотносятся как `Wilder(n) ≈ Classical(2n−1)`.
Wilder 1978 определил ADX/RSI/ATR именно через свою версию. Смешение
конвенций приводит к тому, что backtest-сигнал не воспроизводится в
TradingView/биржевых чартах и в коллегиальных ревью (исторический bug
TA-Lib SourceForge #87).

## Decision
We will use:
- **Wilder's smoothing (α = 1/n)** для **ADX, DI+/-, RSI, ATR** — как в оригинале Wilder 1978.
- **Classical EMA (α = 2/(n+1))** для **EMA-crossover стратегий** и общих
  moving-average фильтров.
Каждый индикатор имеет явный параметр `ema_mode: {wilder, classical}` в конфиге;
default для семейства Wilder-индикаторов — `wilder`, иначе `classical`.

## Consequences
- (+) Значения ADX/RSI/ATR воспроизводятся с TradingView/биржевых чартов.
- (+) EMA-crossover совместим с "классической" литературой (Murphy, Pring).
- (+) Explicit config → невозможно случайно использовать не ту конвенцию.
- (−) Разработчикам нужно знать разницу — документируем в README индикаторов.
- (−) Unit-тесты должны покрывать обе конвенции с известными golden values.
- (0) TA-Lib wrappers используют Wilder автоматически для RSI/ADX/ATR — но мы
  пишем свои реализации, чтобы контролировать numerical edge cases.

## Alternatives considered
- Classical везде: отвергнуто — ADX/RSI не совпадают с биржевыми чартами, теряем
  доверие при code review.
- Wilder везде: отвергнуто — EMA-crossover в литературе и чартах — классический.
- Пользовательский параметр без default: отвергнуто — слишком легко ошибиться.

## References
- [Docs/MVP + ALL PROJECT/MVP.md](../../../Docs/MVP%20%2B%20ALL%20PROJECT/MVP.md) — §2 item 10
- Wilder J. Welles, "New Concepts in Technical Trading Systems" (1978)
- TA-Lib bug #87 (SourceForge): https://sourceforge.net/p/ta-lib/bugs/87/

## Связанные

- [[../sprints/sprint-03-strategy-port]] — sprint where indicators with Wilder/Classical modes were implemented
- [[../components/indicators]] — implementation: `ema(mode="wilder"|"classical")`, `rsi`, `adx`, `atr`
- [[../components/strategy]] — consumer: EMA-crossover uses classical, ADX/RSI/ATR use Wilder
