---
title: Walk-Forward Validation — train 2000 / test 500
type: concept
tags: [backtest, walk-forward, cv, v0.1]
created: 2026-04-19
updated: 2026-04-19
status: stable
sources: [Docs/MVP + ALL PROJECT/MVP.md §4]
---

# Walk-Forward Validation

**TL;DR:** Walk-forward с `train=2000 bars (~12 недель), test=500 bars (~3 недели)`, K=5 folds, embargo h=0.01·T ≈ 20 bars, OOS/IS Sharpe ratio ≥0.7 gate, Deflated Sharpe Ratio (DSR) обязателен.

## Параметры (v0.1)

| Параметр | Значение | Обоснование |
|----------|----------|-------------|
| `train_bars` | **2000** (~12 недель 1H) | 24–60 сделок в окне при 2–5 trades/week (статзначимо) |
| `test_bars` | **500** (~3 недели) | Train/test 4:1, стандарт Pardo 70/20–80/20 |
| `K` (folds) | **5** для v0.1, **10** для v0.2+ PKCV | K=3 высокая variance; 10 — AFML стандарт с purging |
| `embargo` | `h = 0.01·T ≈ 20 bars` после каждой test-fold | AFML §7.4.2 — защита от leakage labels |
| `MC permutations` | **N=2000** для α=0.05 | SE(p̂)=0.005 при p̂=0.05; эскалация до 10000 при multiple-testing |
| `OOS/IS Sharpe ratio` | **≥0.7** | Degradation >30% → red flag overfit |
| `DSR` | >0 обязательно | Bailey–López de Prado (2014) |
| `MinBTL bound` | 5 лет BTC ⇒ max ~45 независимых конфигураций | `MinBTL < 2·ln(N) / E[max_N]²` |

## Почему 2000 bars (не 252)

Многие спеки по ошибке используют `train_bars=252` (forex-калька — 1 year daily). На 1H это **10.5 дней** — катастрофически мало.

**Требование:** окно должно содержать **≥30–100 сделок** для статзначимости coverage на binomial CI. При 2–5 trades/week EMA-crossover + ADX:
- 2000 bars ≈ 83 days ≈ 24–60 сделок ✓

## Walk-Forward vs альтернативы

| Подход | Преимущества | Недостатки | Вердикт |
|--------|--------------|-----------|---------|
| Simple Walk-Forward | Интуитивный, прост | Path-dependent; тратит данные; одна историческая траектория | **v0.1 baseline** |
| Purged K-Fold CV (PKCV) | Использует все данные; корректно для labels | Один test-path | v0.2 upgrade |
| Combinatorial Purged CV (CPCV) | Распределение Sharpe по C(N,k) путям; золотой стандарт AFML | Вычислительно дорог | v0.3 при formal reporting |

## Workflow

```
1. Split 5 лет BTC 1H на K=5 folds, каждое ~17500 bars.
2. Для каждой fold i:
   a. train = first 2000 bars of fold
   b. test  = next 500 bars (with h=20 embargo после)
   c. Fit strategy params на train
   d. Evaluate OOS на test → Sharpe_i, Sortino_i, MaxDD_i, ...
3. Aggregate: mean ± SE across K folds.
4. MC Permutation test (sign-flip, N=2000):
   a. Shuffle sign of returns in test period
   b. Compute OOS Sharpe under permutation
   c. p-value = fraction of permutations with Sharpe ≥ observed
   d. Reject H₀ если p < 0.05
5. Apply DSR correction для multiple testing (DSR > 0).
6. Gate: OOS/IS ratio ≥0.7, DSR > 0, PBO < 0.5 → proceed to live.
```

## Embargo — зачем

Когда labels (signals/returns) пересекают train/test границу — происходит leakage. Например, если `return[t+1]` используется как label для `signal[t]`, а test-fold начинается с bar t, то `signal[t-1]` в train-fold видит часть test-fold через label.

Решение: **purge** — удалить из train-fold bars, у которых labels пересекают test-fold. **Embargo h=0.01·T** — дополнительная буферная зона после test-fold, где train-fold не используется.

Детали: López de Prado (2018) AFML §7.4.2.

## Probability of Backtest Overfitting (PBO)

```
PBO = P(IS-best strategy proигрывает в OOS)
```

Считается через CSCV (combinatorially symmetric cross-validation) или bootstrap. PBO < 0.5 означает: IS-winner предпочтителен OOS more than half the time.

`PBO > 0.5` — явный overfit.

## Пример: почему train=252 катастрофичен

```
1H bars, train_bars=252 = 10.5 дней
2-5 trades/week = 3-7 trades в train window
Binomial 95% CI на win-rate при n=5, p̂=0.6: [0.15, 0.95] — useless
Parameter optimization на 5 trades → pure noise fitting
```

## Integration с другими валидациями

1. **Look-ahead detector** (CI gate) — обязательно **до** backtest.
2. **Walk-Forward** — K=5 rolling folds.
3. **Sign-flip MC permutation** — H₀: "направление без edge".
4. **DSR correction** — для N configurations tried.
5. **PBO estimation** — sanity-check для overfit.

Все пять — обязательны для v0.1 gate.

## Sources

- Pardo (2008) *The Evaluation and Optimization of Trading Strategies* Ch.4–5, Ch. Walk-Forward Analysis.
- López de Prado (2018) *Advances in Financial ML* Ch.7 §7.4, Ch.11–12, Ch.14.
- Bailey, Borwein, López de Prado, Zhu (2017) "The probability of backtest overfitting" *J. Comput. Finance* 20(4):39–70.
- Bailey, López de Prado (2014) "The Deflated Sharpe Ratio" *JPM* 40(5):94–107.

## Related

- [[monte-carlo-permutations]] — sign-flip detail.
- [[deflated-sharpe-ratio]] — DSR formula.
- minimum-backtest-length — MinBTL bound (concept stub, page deferred).
- [[../../project/decisions/0014-walk-forward-train2000-test500]] — ADR.
- [[../../project/architecture/acceptance-criteria]] — gating.

## Реализация

- [[../../project/components/walk-forward]] — `WindowSplitter` + `WalkForwardRunner` + `evaluate_acceptance_gate`
- [[../../project/components/wfa-reporter]] — 3-Sharpe routing + DSR aggregate report
- [[../../project/components/backtest-harness]] — base `run_replay()` called per fold (IS + OOS)
