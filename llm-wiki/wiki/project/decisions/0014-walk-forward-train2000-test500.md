---
title: 0014. Walk-forward train=2000, test=500, K=5
type: decision
tags: [adr, v0.1, backtest, walk-forward, validation]
created: 2026-04-19
updated: 2026-05-10
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

### Gate-blocking vs informational критерии (S49 уточнение — trader-expert verdict + ADR 0052)

Verdict (PASS/FAIL, блокирует mainnet) определяется **ИСКЛЮЧИТЕЛЬНО** gate-blocking критериями:

| Gate-blocking (блокирует verdict) | Порог | Источник |
|-----------------------------------|-------|----------|
| T5 n_trades floor | ≥ 50 | ADR 0052 (raw floor) |
| per-fold OOS/IS Sharpe (`sharpe_gate`) | ≥ 0.7 каждый фолд | этот ADR (L1) |
| MC permutation (`mc_gate`) | p-value ≤ 0.05 | ADR 0015 + ADR 0052 |
| DSR (`dsr_threshold`) | ≥ 0.95 | ADR 0052 |
| n_eff (`n_eff_threshold`) | ≥ 50 (Kish 1965) | ADR 0052 |

**Informational (отображаются в UI, НЕ блокируют verdict):** T1 (Sharpe OOS), T2 (Sortino OOS),
T3 (MaxDD), T4 (Win Rate), T6 (OOS/IS Sharpe ratio aggregate). Они влияют на интерпретацию
результата (risk warnings, контекст), но не на сам PASS/FAIL.

**Rationale (S49):** ранее backend `backtest_runner._compute_verdict` ошибочно включал
T1-T4/T6 в `failed_criteria` (например T3 MaxDD ≥ 25% → FAIL), что противоречило ADR 0052
(T5 floor — primary gate) и UI (FailAnalysisTab / MetricsTable уже разделяли gate-blocking
vs informational). Backend приведён в соответствие. См. также
[[../architecture/acceptance-criteria]] секция «Последовательность проверок».

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

## Поправка S45 (2026-05-10): Low-frequency tier (4H/D crypto)

### Контекст amendment

S44 WFA retrofit раскрыл что default ADR 0014 params (train=2000/test=500/k=5/embargo=20) calibrated для FX 1H — структурно враждебны к 4H/D crypto strategies. Empirical (S44 verdict table): atr_breakout 4H fires 5-10 trades в 500-bar OOS folds vs T5_FLOOR=50 minimum.

### Trade-frequency derivation (anti-snooping pre-commit S45 T6)

Computed на 3.3y window (2023-01-01 → 2026-04-26) per uniform data per S45 ADR 0065:

| Combo | bars/year | 3.3y trades | trades/500bar | trades/250bar |
|-------|-----------|-------------|---------------|---------------|
| BTCUSDT_15 | 35064 | 245 | 1.06 | 0.53 |
| BTCUSDT_60 | 8766 | 106 | 1.83 | 0.92 |
| BTCUSDT_240 | 2191 | 28 | 1.94 | 0.97 |
| BTCUSDT_D | 365 | 32 | 13.28 | 6.64 |
| ETHUSDT_15 | 35064 | 240 | 1.04 | 0.52 |
| ETHUSDT_60 | 8766 | 109 | 1.88 | 0.94 |
| ETHUSDT_240 | 2191 | 28 | 1.94 | 0.97 |
| SOLUSDT_15 | 35064 | 230 | 0.99 | 0.50 |
| SOLUSDT_60 | 8766 | 124 | 2.14 | 1.07 |
| SOLUSDT_240 | 2191 | 71 | 4.91 | 2.45 |

**Conclusion:** 4H/D combos fire 1-3 trades per 500-bar OOS fold = structural T5 floor failure. test_bars=250 doubles density к 0.5-1.5/fold ≈ 5-15 trades pooled across 5 folds. Still likely T5 fail, но honest second look.

### Tier definition

| Tier | Timeframes | train_bars | test_bars | k_folds | embargo | min_required |
|------|------------|------------|-----------|---------|---------|--------------|
| **High-freq (default ADR 0014)** | 5M, 15M, 1H | 2000 | 500 | 5 | 20 | 4520 |
| **Low-freq (S45 amendment)** | 4H, D | 1500 | 250 | 5 | 20 | 2770 |

### Rationale

- test_bars=250 doubles OOS trade density для low-freq strategies (без relaxing T5 floor)
- train_bars=1500 derived from min_required formula: `train + embargo + k*test = 1500 + 20 + 5*250 = 2770`. Train:test ratio = **6:1** (low-freq) vs **4:1** (high-freq 2000:500). Train slice intentionally larger relative к short OOS test windows, но vestigial для LOCKED-params strategies (no per-fold IS fitting per S45 B2 docs).
- k_folds=5 unchanged (cross-fold variance signal preserved)
- embargo=20 unchanged (López de Prado lookback isolation)
- T5_FLOOR=50 LOCKED (Bailey 2014 small-sample T-stat unreliability — не negotiable)

### Anti-snooping clauses

1. **This amendment committed BEFORE S45 recalibration run** (T7). Values derived from trade-frequency analysis above, NOT fitted к pass any combo.
2. **Maximum 1 recalibration iteration** (this ADR). Если post-S45 WFA still FAIL ВСЕ 11 combos → S46 = honest portfolio close per operator ESC-1 (a). НЕ further parameter shopping.
3. **Если хотя бы 1 combo NEW WFA_PASS** post-recalibration → cross_trial_log reset (treats new WFA config as fresh testing event per Bailey 2014).
