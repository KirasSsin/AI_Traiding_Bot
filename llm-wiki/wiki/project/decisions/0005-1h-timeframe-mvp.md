---
title: 0005. 1-hour timeframe for MVP
type: decision
tags: [adr, v0.1, timeframe, strategy, swing]
created: 2026-04-19
updated: 2026-04-19
status: accepted
sources: [Docs/MVP + ALL PROJECT/MVP.md]
---

# 0005. 1-hour timeframe for MVP

**Status:** Accepted
**Date:** 2026-04-19

## Context
Таймфрейм определяет всё: число событий, требования к latency, rate-limit, объём
исторических данных, статистическую мощность backtest. Нужно выбрать один
рабочий TF для v0.1, который достаточен для swing-style стратегий (trend /
mean-reversion) и не требует HFT-инфраструктуры.

## Decision
We will use 1-hour (1H) bars как основной таймфрейм для v0.1. Все стратегии,
индикаторы (ADX, RSI, ATR, EMA-crossover), walk-forward окна (train=2000,
test=500) и risk-контуры масштабируются к 1H. Поддержка 4H/1D — через
resample в backtest, но не для live v0.1.

## Consequences
- (+) 8760 баров/год/символ — достаточно для годового OOS без переобучения.
- (+) Low-latency не критичен (1 событие в час) → Python + uvloop с запасом.
- (+) Rate-limits Binance легко соблюдаются (<100 req/час на символ).
- (+) Хранение: <100KB/год/символ в Parquet.
- (−) Статистическая мощность ниже, чем у 1m/5m — компенсируем MC N=2000.
- (−) Некоторые micro-structure alpha недоступны — приемлемо для MVP.
- (0) Walk-forward train=2000 ≈ 12 недель — достаточно для adjustment к регимам.

## Alternatives considered
- 1-minute: отвергнуто — требует infra-tier (low-latency, колокация, rate-limits
  на пределе), не соответствует swing-фокусу.
- 15m/5m: отвергнуто — больше шума, короче средняя сделка, выше комиссии.
- 1D: отвергнуто — слишком мало точек для MC-пермутаций (меньше 2000 bars/year).

## References
- [Docs/MVP + ALL PROJECT/MVP.md](../../../Docs/MVP%20%2B%20ALL%20PROJECT/MVP.md) — §3, §4, §11
- See [[0014-walk-forward-train2000-test500]], [[0015-sign-flip-mc-permutations-n2000]]
