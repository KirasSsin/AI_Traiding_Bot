---
title: DSR — Deflated Sharpe Ratio module
type: component
tags: [analytics, statistics, dsr, bailey-lopez-de-prado, sprint-9]
created: 2026-04-25
updated: 2026-04-25
status: stable
sources:
  - src/analytics/dsr.py
  - https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551
---

# DSR (Deflated Sharpe Ratio)

**TL;DR:** Pure-function module computing Bailey & López de Prado (2014) Deflated Sharpe Ratio на `TradeRecord` array. Adjusts vanilla Sharpe для sample length + non-normality (skew + Pearson kurtosis). No look-ahead: only consumes closed trades (`exit_ts` populated). Returns NaN defensively на degenerate inputs (N<2, var=0, denom_inner≤0). `n_trials > 1` raises `NotImplementedError` (требует sigma_SR multiplier — NYI v0.1, defer к S10+).

## Public API

| Symbol | Signature |
|--------|-----------|
| `compute_returns` | `src/analytics/dsr.py::compute_returns(trades: list[TradeRecord], *, use_log: bool = True) -> list[float]` |
| `compute_dsr` | `src/analytics/dsr.py::compute_dsr(trades: list[TradeRecord], *, benchmark_sharpe: float = 0.0, n_trials: int = 1, use_log: bool = True) -> float` |

## Formula (Bailey & López de Prado 2014, eq. 13)

```
DSR = Φ( (SR_obs - SR_star) * √(N - 1) / √(1 - γ̂*SR_obs + ((κ̂-1)/4)*SR_obs²) )

where:
  SR_obs = mean(returns) / std(returns)         -- observed per-trade Sharpe
  γ̂ = sample skewness                           -- Fisher (bias-corrected)
  κ̂ = sample Pearson (total) kurtosis           -- NOT excess; bias-corrected
  SR_star = benchmark_sharpe                    -- v0.1: n_trials=1 only
  Φ = standard normal CDF
```

**CRITICAL:** kurtosis convention = **Pearson** (`scipy.stats.kurtosis(..., fisher=False)`), NOT excess. For Normal distribution Pearson=3 → `(3-1)/4 = 0.5` recovers Lo (2002) Sharpe variance `(1 + SR²/2)/(T-1)`. Using Fisher (excess=0) would give `(0-1)/4 = -0.25` — systematically wrong. Caught by quant-stats-reviewer T9 BLOCKER B1.

## Invariants (CRITICAL)

| # | Invariant | Enforcement | Test |
|---|-----------|-------------|------|
| 1 | NaN на N<2 (variance undefined) | early return math.nan | `tests/unit/test_dsr.py::test_compute_dsr_empty_returns_nan` + `test_compute_dsr_single_trade_returns_nan` |
| 2 | NaN на var=0 (constant returns) | guard `if var <= 0` | `tests/unit/test_dsr.py::test_compute_dsr_constant_returns_nan` |
| 3 | NaN на denom_inner ≤ 0 (DSR undefined) | guard `if denom_inner <= 0` | (implicit — reachable когда skew × sharpe overcomes 1 + kurtosis term) |
| 4 | log returns default (additive compounding) | `use_log=True` default | `tests/unit/test_dsr.py::test_compute_returns_log_default` |
| 5 | No look-ahead — uses only closed TradeRecord (exit_ts populated) | function consumes only `pnl_pct` realized at exit_ts | `tests/unit/test_dsr.py::test_no_look_ahead_uses_only_exit_ts` |
| 6 | Pure function, no I/O, no module-level state | docstring + structure | code review |
| 7 | n_trials > 1 NotImplementedError (NYI v0.1) | explicit raise | `compute_dsr` body |
| 8 | Pearson kurtosis (NOT Fisher excess) | `stats.kurtosis(..., fisher=False)` | quant-stats-reviewer T9 verdict |
| 9 | Total-loss edge case (pnl_pct=-1.0) → log return = -inf, filtered | `if pct <= -1.0: append(-inf)` + `isfinite` filter в compute_dsr | `tests/unit/test_dsr.py::test_total_loss_returns_neg_inf_log` |

## Annualization (NOT applied v0.1)

Per quant-stats-reviewer T9 verdict: per-trade Sharpe без annualization is **internally consistent** для DSR. The Φ() output is unit-free; annualization factor would appear identically в numerator (Sharpe) и denominator (sigma estimate) — cancels. Per-trade basis correct для DSR v0.1.

If annualization needed downstream (e.g. для display vs Sharpe target в WFA acceptance gate per ADR 0014) — apply at consumer layer, not here.

## Multiple-testing penalty (n_trials)

**v0.1: only n_trials=1 supported.** `n_trials > 1` raises `NotImplementedError`. Bailey & López de Prado eq. 12 requires `sigma_SR` (cross-trial Sharpe std) multiplier:

```
E[max SR_n] = mu_SR + sigma_SR × ((1-γ)*Φ⁻¹(1-1/N) + γ*Φ⁻¹(1-1/(N×e)))
```

Implementation NYI — caller would need supply `sigma_sr` separately. Defer к S10+ когда multi-strategy backtest framework available.

## scipy dependency

Uses `scipy.stats.skew`, `scipy.stats.kurtosis`, `scipy.stats.norm.cdf/ppf`. scipy added к mypy `ignore_missing_imports` override (T4 follow-up commit `9f91b8c`).

## Referenced by

- [[wfa-reporter]] — DSR aggregate computed in S10; sigma_sr from per-fold Sharpes fed here
- [[backtest-harness]] — replay engine produces trade data consumed by DSR pipeline

## Related

- [[trade-history]] — input data source (TradeRecord array)
- [[fill-history]] — granular fill data (NOT consumed by DSR — operates на per-trade level only)
- [[../decisions/0014-walk-forward-train2000-test500]] — walk-forward gate uses Sharpe (DSR foundation для S10)
- [[../decisions/0015-sign-flip-mc-permutations-n2000]] — sign-flip MC permutations (companion statistical method)
- [[../decisions/0024-sprint-9-data-quality-types-analytics]] — S9 aggregate ADR
- [[../../trading/concepts/deflated-sharpe-ratio]] — concept page
- [[../sprints/sprint-09-data-quality-types-analytics]] — sprint where dsr module was created
- [[../architecture/acceptance-criteria]] — T2 DSR gate (≥0.95 threshold).

## Sources

- `src/analytics/dsr.py` — implementation
- `tests/unit/test_dsr.py` — 8 tests
- Bailey, D.H., López de Prado, M. (2014) "The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality" — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551
- quant-stats-reviewer T9 verdict (BLOCKER B1 caught Fisher→Pearson kurtosis convention bug)
