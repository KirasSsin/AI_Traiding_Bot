---
name: strategy_metrics T3 MaxDD initial_capital bug + T2 Sortino formula variant
description: T3 running_max does not prepend initial_capital, missing drawdown when first trade is a loss. T2 uses std(losers,ddof=1) not canonical RMS. S13 T6 commit 5908682.
type: project
---

## T3 MaxDD: initial_capital not prepended to equity sequence (BLOCKER)

File: `src/backtest/strategy_metrics.py`

Bug: `running_max = np.maximum.accumulate(equity_with_capital)` starts accumulation from
the FIRST TRADE's equity value, not from `initial_capital`. If the first trade is a loss,
the drawdown from initial_capital to first-trade-equity is silently discarded.

**Consequence:** MaxDD is understated for any strategy whose first OOS trade is a loss.
With noisy OOS sequences (which S13 is measuring), first-trade-loss is common.
5% drawdown on first trade -> MaxDD reports 0.0 instead of 5%.

**Correct fix:** prepend initial_capital before accumulate:
```python
equity_full = np.concatenate([[initial_capital], equity_with_capital])
running_max = np.maximum.accumulate(equity_full)
# then compute drawdowns over equity_full
```

**Why existing tests pass:** `test_compute_metrics_t3_max_drawdown_zero_for_monotonic` uses
50 consecutive winners -> equity_with_capital[0] = initial_capital + first_win > initial_capital
-> running_max[0] is already the correct peak. Bug only manifests when first trade is a loss.
`test_compute_metrics_t3_max_drawdown_with_dip` starts with 30 winners before losers,
so same masking applies.

**Blowout guard still works:** pnl = -10000, equity_with_capital[0] = 0, running_max[0] = 0
-> np.where triggers -1.0 -> MaxDD = 1.0. Correct.

Sprint: S13 T6.

## T2 Sortino: std(losers,ddof=1) vs canonical sqrt(mean(losers^2))

File: `src/backtest/strategy_metrics.py`

Code: `sortino = mean(pnl_pcts) / std(losers, ddof=1)`
Canonical Sortino (Sortino & Price 1994, MAR=0): `mean(r) / sqrt(mean(r_negative^2))`

**Difference:**
- `std(losers,ddof=1)` measures dispersion of losers around their mean (not around 0)
- `sqrt(mean(losers^2))` measures average squared loss relative to 0 (MAR)
- Because losers have a negative mean, `std < RMS` always -> code Sortino > canonical Sortino
- Empirical ratio: code inflates by ~40-70% in typical scenarios

**Additional edge case:** all-equal-loss strategy (e.g., fixed stop = -1R): std=0 -> NaN.
Canonical would return a finite positive Sortino.

**T2 threshold concern:** T2 >= 1.5 threshold source (acceptance-criteria.md) does not cite
which Sortino formula was used for calibration. If calibrated against canonical, code's
inflated Sortino will pass strategies that canonically fail T2. This is a non-blocking concern
as long as the threshold is recalibrated to match code's formula, but it must be documented.

Sprint: S13 T6.

**How to apply:** In future reviews of Sortino computations, verify formula is
`sqrt(mean(r_neg^2))` not `std(r_neg, ddof=1)`. Also verify T2 threshold is consistent
with whichever formula the code uses.
