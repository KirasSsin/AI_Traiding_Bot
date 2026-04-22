---
title: Deflated Sharpe Ratio (DSR)
type: concept
tags: [backtest, sharpe, dsr, multiple-testing, v0.1]
created: 2026-04-19
updated: 2026-04-19
status: stable
sources: [Docs/MVP + ALL PROJECT/MVP.md §4]
---

# Deflated Sharpe Ratio (DSR)

**TL;DR:** DSR "deflates" наблюдаемый Sharpe с учётом (1) skewness/kurtosis returns, (2) серии зависимости, (3) числа протестированных конфигураций N. **DSR > 0** — обязательное условие для v0.1.

## Проблема

Обычный (observed) Sharpe:
```
SR = mean(returns) / std(returns) · √(252 для daily | √8760 для 1H)
```

При повторных тестах N конфигураций — максимальный SR среди них **превышает** истинный edge. Гены: "drew the best fish, не обязательно самую большую рыбу".

Bailey–López de Prado (2014) формализуют: **expected max Sharpe** среди N независимых конфигураций ≈ `SR_true + σ_SR · E[max_N(gumbel)]`.

## Формула DSR

```
DSR = Φ( (ŜR − ŜR_null) · √(T−1) / σ(ŜR) )
```

Где:
- `Φ` — CDF стандартного нормального.
- `ŜR` — observed Sharpe.
- `ŜR_null` = `E[max_N(ŜR)]` под H₀ (no edge) = `σ(ŜR) · ((1−γ)·Φ⁻¹(1−1/N) + γ·Φ⁻¹(1−1/(N·e)))`, где γ≈0.5772 (Euler–Mascheroni).
- `σ(ŜR)` = standard deviation of Sharpe under non-Normal returns:
```
σ(ŜR) = √( (1 − γ_3·ŜR + (γ_4−1)/4·ŜR²) / (T−1) )
```
- `γ_3`, `γ_4` — skewness и kurtosis returns.
- `T` — количество observations.

DSR — это **p-value-like** transformation: DSR=0.95 означает "probability that true SR > SR_null is 95%".

## DSR > 0

Это **минимальный** порог: observed SR больше expected-max-under-null для данного N configurations. Если DSR=0 — observed SR в точности тот, который ожидался бы случайно при N попытках.

`DSR > 0.5` — strong evidence против null.

## MinBTL — максимально допустимое N

Из DSR формулы следует: при target `ŜR_true = 1.0`, `σ(ŜR) = 0.5`, **MinBTL ~ 2·ln(N) / ŜR²**.

Для 5 лет BTC 1H (≈ 43800 bars ≈ 5 years) это даёт **N ≤ 45 независимых конфигураций** при target Sharpe=1.

> При превышении MinBTL любой observed Sharpe ≥1 не отличим от шума.

## Практика

### Шаг 1: зарегистрировать N

Перед backtest — написать hypothesis registry:
```
hypothesis_id | ema_fast | ema_slow | adx_thr | rsi_ob | rsi_os | sl_atr | tp_atr
```

Каждая строка — одна конфигурация, тестируемая ровно один раз.

### Шаг 2: backtest N конфигураций

Run walk-forward CV для каждой. Record observed Sharpe + skewness + kurtosis.

### Шаг 3: вычислить DSR

```python
from scipy.stats import norm

def deflated_sharpe_ratio(sr_observed, sr_std, T, gamma_3, gamma_4, N):
    """
    sr_observed: наблюдаемый Sharpe
    sr_std: stddev of Sharpe across configurations
    T: number of observations (bars)
    gamma_3, gamma_4: skewness, kurtosis of returns
    N: number of configurations tested
    """
    euler = 0.5772156649
    z_N = (1 - euler) * norm.ppf(1 - 1/N) + euler * norm.ppf(1 - 1/(N * 2.71828))
    sr_null = sr_std * z_N

    sr_sigma = ((1 - gamma_3 * sr_observed + (gamma_4 - 1)/4 * sr_observed**2) / (T - 1)) ** 0.5
    dsr = norm.cdf((sr_observed - sr_null) * (T - 1) ** 0.5 / sr_sigma)
    return dsr
```

### Шаг 4: gate

- DSR > 0.5: strong pass → live (Kelly Phase 1).
- 0 < DSR < 0.5: marginal, require supporting evidence (Sortino, t-stat).
- DSR ≤ 0: reject → пересмотр гипотезы.

## Связанные метрики

- **PBO** — probability of backtest overfitting (DSR complement).
- **Haircut Sharpe** — эмпирический "штраф" ≈30-50% к observed SR.

## Почему γ_3, γ_4 важны

BTC returns имеют **fat tails** (kurtosis ≈ 5–8 для 1H, vs 3 для Normal) и **negative skew** при crashes. Non-Normal correction через `σ(ŜR)` даёт реалистичный CI.

Для Normal returns (γ_3=0, γ_4=3): σ(ŜR) = √(1/(T-1)).

Для BTC (γ_3≈-0.5, γ_4≈8): σ(ŜR) примерно в 1.5× больше — Sharpe менее точен.

## Sources

- Bailey, López de Prado (2014) "The Deflated Sharpe Ratio" *JPM* 40(5):94–107.
- Bailey et al. (2014) "Pseudo-mathematics and financial charlatanism" *Notices AMS*.
- López de Prado (2018) *AFML* Ch.14 §14.7.3 p.204.

## Related

- [[walk-forward-validation]] — gating flow.
- [[monte-carlo-permutations]] — complementary test.
- [[../../project/architecture/acceptance-criteria]] — gating.
