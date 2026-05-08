---
name: Three Sharpe metric semantics (live vs fold-mean vs pooled)
description: Three distinct Sharpe metrics in codebase that must not be conflated. ADR 0056 variable rename introduced trial_mean_fold_oos_sharpe. C3 carry-over from S36 T6.
type: project
---

Three distinct Sharpe metrics exist in the codebase post-S36:

1. **live_Sharpe** — computed by `compute_live_sharpe()` in `src/analytics/live_trade_reporter.py`. Uses per-TradeRecord pnl_quote returns (live path only). Annualized via sqrt(bars_per_year / avg_bars_per_trade). This is what `calibration_ratio_to_s22` uses as numerator.

2. **trial_mean_fold_oos_sharpe** — arithmetic mean of K WFA fold OOS Sharpes. Stored in cross_trial_sharpes.json log entries per S33 T3 protocol. ADR 0056 renamed from `aggregate_oos_sharpe` to clarify semantics. Used for cross-trial sigma_SR pooling (N>=3 entries required per ADR 0056 hierarchy).

3. **pooled_trade_oos_sharpe** — trade-level Sharpe computed over ALL OOS trades concatenated across folds. WFA backtest context only. More robust at larger n due to full distribution, not fold-mean.

**Why:** These three can diverge significantly at small n with fold concentration. S22: trial_mean_fold_oos_sharpe=2.96, but aggregate (similar to pooled) = 6.17. An operator reading `calibration_ratio_to_s22` who conflates live_Sharpe with trial_mean_fold_oos_sharpe will misinterpret the reporter output.

**How to apply:** When reviewing any code that computes or reports Sharpe in backtest or live context, verify which of the three metrics is in use. C3 carry-over from S36 T6: ADR 0056 amendment needed to formally document this distinction (Item 9, pre-s37-backlog.md). S37 consilium ROUND 5: defer Item 9 to S38 unless operator playbook references these metrics by name.
