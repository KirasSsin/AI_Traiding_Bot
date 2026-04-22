---
title: Monte Carlo Permutations — sign-flip N=2000
type: concept
tags: [backtest, monte-carlo, permutation, sign-flip, v0.1]
created: 2026-04-19
updated: 2026-04-19
status: stable
sources: [Docs/MVP + ALL PROJECT/MVP.md §2 item 2-2a, §4]
---

# Monte Carlo Permutations

**TL;DR:** Sign-flip permutations (N=2000) — primary MC test для v0.1. Block-bootstrap (block 20-50 bars) — secondary. H₀: "направление без edge".

## Метод: sign-flip

```
1. Observed test: compute strategy Sharpe на OOS test-fold.
2. Для каждой permutation i=1..N:
   a. Shuffle sign of each return in test-period independently
      (i.e., multiply each return by ±1 with p=0.5)
   b. Compute Sharpe_i на flipped returns under strategy
3. p-value = fraction of Sharpe_i ≥ observed Sharpe
4. Reject H₀ если p < 0.05
```

**Что тестируем:** sign-flip сохраняет **тайминг и размер** сделок, но рандомизирует направление (up vs down return). Это ровно H₀ "направление без edge" — т.е. strategy не предсказывает знак будущего движения.

Идеально подходит для EMA-crossover, где основной claim — "cross up → expected positive return".

## Почему N=2000, не 10000

Standard error p̂ под α=0.05:
```
SE(p̂) = √(p·(1-p) / N)
```

| N | SE при p̂=0.05 | Relative error |
|---|---------------|----------------|
| 1,000 | 0.0069 | ~14% |
| **2,000** | **0.0049** | **~10%** |
| 10,000 | 0.0022 | ~4% |

При N=2000 — точность у границы решения достаточна для go/no-go (10% relative error). 10000 — overkill без multiple-testing corrections.

**Эскалация до N=10,000:** когда применяется DSR/Bonferroni correction для N tested configurations > 10.

## Альтернатива: block bootstrap

```
1. Разбить test-period на blocks of length L (20-50 bars).
2. Для каждой permutation:
   a. Sample blocks with replacement.
   b. Concatenate → bootstrapped series of same length.
   c. Re-run strategy на bootstrapped bars.
3. p-value через aggregation across permutations.
```

**L=20-50 bars:** захватывает short-term autocorrelation, которая присутствует в BTC returns (moving averages, momentum).

**Когда использовать:** если strategy chain-зависима (например, trailing stops, pyramid entries) — sign-flip sufficiently не сохраняет структуру сделок.

## Какую MC применять когда

| Strategy type | Primary | Secondary |
|---------------|---------|-----------|
| Simple crossover (v0.1) | **Sign-flip N=2000** | Block bootstrap L=30 |
| Momentum / breakout | Sign-flip | Block bootstrap L=20 |
| Mean reversion | Block bootstrap | Sign-flip |
| Pairs / stat arb | Stationary bootstrap | Block bootstrap |
| L2 / order flow | Synthetic order book (v0.3+) | — |

## Комбинация с walk-forward

```
For each walk-forward fold:
    observed_sr = evaluate_strategy(fold.test)
    p_values = []
    for i in 1..N:
        permuted_sr = evaluate_strategy(sign_flip(fold.test))
        p_values.append(observed_sr <= permuted_sr)
    fold.p = mean(p_values)

aggregate_p = combine(fold.p for fold in folds)  # e.g., Fisher's method
```

`aggregate_p < 0.05` + OOS/IS ≥ 0.7 + DSR > 0 → pass gate.

## Распространённые ошибки

1. **Perturbate OHLCV, не returns.** Shuffling OHLCV ломает structure баров. Правильно — flip/bootstrap **returns** (закрытие-к-закрытию).
2. **N=100.** Слишком мало: SE ≈ 0.022 (44% relative error) — невозможно делать go/no-go decision.
3. **Не применять embargo.** Embargo важен и при permutation tests — иначе leakage через labels.
4. **One-tailed vs two-tailed.** Для EMA-crossover expected `Sharpe > 0` → one-tailed test корректен.

## Implementation skeleton

```python
import numpy as np

def sign_flip_p_value(strategy_fn, returns_oos, N=2000):
    observed_sharpe = sharpe(strategy_fn(returns_oos))
    count_ge = 0
    for _ in range(N):
        signs = np.random.choice([-1, 1], size=len(returns_oos))
        permuted = returns_oos * signs
        permuted_sharpe = sharpe(strategy_fn(permuted))
        if permuted_sharpe >= observed_sharpe:
            count_ge += 1
    return count_ge / N
```

## Sources

- López de Prado (2018) *AFML* Ch.11–12, §12.4 CPCV, Ch.12 sign-flip.
- Politis, Romano (1994) "The stationary bootstrap" *JASA* 89(428):1303–1313.
- Bailey, Borwein, López de Prado, Zhu (2017) *J. Comput. Finance* 20(4):39–70.

## Related

- [[walk-forward-validation]] — framework.
- [[deflated-sharpe-ratio]] — multiple-testing correction.
- [[../../project/decisions/0015-sign-flip-mc-permutations-n2000]] — ADR.
