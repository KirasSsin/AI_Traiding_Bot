---
title: 0015. Sign-flip MC permutations, N=2000 primary
type: decision
tags: [adr, v0.1, statistics, monte-carlo, significance]
created: 2026-04-19
updated: 2026-04-19
status: accepted
sources: [Docs/MVP + ALL PROJECT/MVP.md]
---

# 0015. Sign-flip MC permutations, N=2000 primary

**Status:** Accepted
**Date:** 2026-04-19

## Context
Walk-forward метрики (Sharpe, profit factor) недостаточны сами по себе: нужна
оценка, является ли результат статистически отличимым от случайного. Метод
должен учитывать автокорреляцию возвратов (block) и сохранять маргинальные
распределения (sign-flip/permutation). Число итераций N прямо определяет
точность p-value: стандартная ошибка `SE(p̂) = sqrt(p(1-p)/N)`; для p = 0.05
и N = 2000 это ≈ 0.005.

## Decision
We will use **sign-flip permutation test** как **primary** метод оценки
значимости стратегии, с **N = 2000** итераций по умолчанию для α = 0.05.
Вторичный/supporting метод — **block bootstrap** с блоком 20–50 баров
(учитывает автокорреляцию).
При **multiple testing** (одновременное тестирование ≥ 5 гипотез/стратегий)
эскалируем до **N = 10,000** и применяем Benjamini–Hochberg FDR-коррекцию.
Acceptance gate: **p ≤ 0.05** на primary-тесте + OOS/IS ≥ 0.7 из walk-forward.

## Consequences
- (+) N = 2000 → SE(p̂) ≈ 0.005 на p = 0.05 — достаточная точность для v0.1.
- (+) Sign-flip сохраняет маргинальные распределения PnL — консервативная null.
- (+) Block-bootstrap ловит автокорреляцию, которую simple permutation ломает.
- (+) Benjamini–Hochberg даёт правильный control для мульти-стратегного отбора.
- (−) N = 2000 × walk-forward folds — заметный CPU, но допустимый на Python
  с numpy-векторизацией.
- (−) Block-size (20–50) сам параметр — фиксируем в конфиге с sensitivity check.
- (0) Для v0.2+ рассмотреть stationary bootstrap (Politis–Romano).

## Alternatives considered
- N = 1000: отвергнуто — SE ≈ 0.007, на границе для α = 0.05.
- N = 10,000 как default: отвергнуто — избыточно для одиночной гипотезы,
  4–5× CPU; резервируем для multiple testing.
- Только Sharpe ratio t-test: отвергнуто — опирается на нормальность, которой
  у крипто-возвратов нет.
- Только bootstrap без sign-flip: отвергнуто — bootstrap не проверяет
  "no edge" null так чисто, как permutation.

## References
- [Docs/MVP + ALL PROJECT/MVP.md](../../../Docs/MVP%20%2B%20ALL%20PROJECT/MVP.md) — §4
- Efron B., Tibshirani R., "An Introduction to the Bootstrap" (1993)
- Politis D., Romano J., "The Stationary Bootstrap" (1994)
- Benjamini Y., Hochberg Y., "Controlling the False Discovery Rate" (1995)
- See [[0014-walk-forward-train2000-test500]]
