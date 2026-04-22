---
title: 0014. Walk-forward train=2000, test=500, K=5
type: decision
tags: [adr, v0.1, backtest, walk-forward, validation]
created: 2026-04-19
updated: 2026-04-19
status: accepted
sources: [Docs/MVP + ALL PROJECT/MVP.md]
---

# 0014. Walk-forward train=2000, test=500, K=5

**Status:** Accepted
**Date:** 2026-04-19

## Context
Единичный train/test split на криптовалютных данных 1H даёт слишком высокий
риск p-hacking и look-ahead bias. Walk-forward validation — промышленный
стандарт. Параметры окон должны отражать (а) статистическую мощность,
(б) реалистичную частоту re-fit'а, (в) специфику крипторынка (быстрая смена
регимов по сравнению с FX). Калькирование FX-параметров (train=252 дней)
не оправдано для 1H-crypto.

## Decision
We will use walk-forward со следующими параметрами для 1H-таймфрейма:
- **train** = **2000 bars** (~ 12 календарных недель) — достаточно для
  стабильных оценок параметров.
- **test** = **500 bars** (~ 3 недели) — short enough для несколько re-fit'ов
  в год.
- **K** = **5 folds** минимум в OOS-валидации.
- **embargo** = `h = 0.01 · T` ≈ **20 bars** между train и test (López de Prado)
  — предотвращает info leakage через автокорреляцию.
- **Acceptance gate**: **OOS/IS Sharpe ratio ≥ 0.7** на каждом fold;
  падение ниже — стратегия отвергается.

## Consequences
- (+) OOS/IS ≥ 0.7 — строгий фильтр против оверфита.
- (+) Embargo защищает от leakage из-за серий (ATR, rolling features).
- (+) K=5 folds даёт 5 независимых OOS-периодов → достоверная агрегация.
- (−) Ресурс backtest'а растёт ~линейно с K — приемлемо для Python/vectorbt.
- (−) 2000 bars = ~12 недель — стратегия не может зависеть от "сезонности
  длиннее квартала" (приемлемое ограничение для v0.1).
- (0) Параметры в конфиге; v0.2 может ввести nested CV.

## Alternatives considered
- train=252 (FX-калька): отвергнуто — недостаточная мощность для 1H-crypto;
  не отражает специфику volatility clustering.
- train=8760 (весь год), single split: отвергнуто — не walk-forward, не ловит
  regime change.
- Expanding window: рассматривается для v0.2; для v0.1 rolling проще и строже.

## References
- [Docs/MVP + ALL PROJECT/MVP.md](../../../Docs/MVP%20%2B%20ALL%20PROJECT/MVP.md) — §4
- Pardo R., "The Evaluation and Optimization of Trading Strategies" (2008)
- López de Prado M., "Advances in Financial Machine Learning" (2018), Ch. 7
- See [[0015-sign-flip-mc-permutations-n2000]]
