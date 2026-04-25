---
title: strategy-metrics — T1-T6 acceptance criteria extraction
type: component
tags: [backtest, t1-t6, mvp-gating, sprint-13]
created: 2026-04-26
updated: 2026-04-26
status: stable
sources:
  - src/backtest/strategy_metrics.py
  - project/architecture/acceptance-criteria.md
---

# strategy-metrics

**TL;DR:** Computes 6 acceptance criteria metrics (T1-T6) from OOS TradeRecord list. Per ADR 0028 Q5: DSR active S13 separately. S13 T6 (per acceptance-criteria.md gating step 2).

## Purpose

After WFA execution + trade extraction, this module computes the 6 strategy-level acceptance criteria values per `acceptance-criteria.md`:

- T1: Sharpe OOS annualized >= 1.0
- T2: Sortino OOS >= 1.5
- T3: MaxDD < 25%
- T4: Win rate >= 45% при RR>=1.5 OR >=35% при RR>=2.0
- T5: Mean pnl_pct > 0, t-stat > 2.0, n >= 100 OOS
- T6: OOS/IS Sharpe ratio mean >= 0.7

## Public API

```python
from src.backtest.strategy_metrics import compute_t1_t6_metrics

metrics = compute_t1_t6_metrics(
    trades=oos_trades,           # list[TradeRecord] from trade_extractor
    fold_oos_is_sharpe=[...],    # per-fold OOS/IS ratios from WalkForwardRunner
    initial_capital=10000.0,     # WFA config trading.initial_balance
)
# Returns dict с t1_sharpe_oos, t2_sortino_oos, t3_max_drawdown,
# t4_win_rate, t4_avg_rr, t5_mean_pnl_pct, t5_t_stat, t5_n_trades,
# t6_oos_is_sharpe_ratio_mean
```

Empty trades -> all NaN sentinels (no crash).

## Architecture rationale

- **Annualization sqrt(8760):** fixed per ADR 0025 (24/7 crypto 1H bars), NOT trade-frequency-derived. Display convention.
- **T3 MaxDD:** equity = initial + cumsum(pnl_quote), peak-to-trough. Includes initial_capital в running_max start (T6 BLOCKER fix). Total blowout (running_max=0) -> -100%, NOT NaN.
- **T2 Sortino:** `mean / std(losers, ddof=1)` x sqrt(8760). Non-canonical formula (canonical = `sqrt(mean(losers^2))`). Quant-stats noted concern для wiki documentation.
- **T5 t-stat:** one-sample t against zero null, threshold 2.0 (one-tailed approximation).

## Invariants

- Empty trades -> NaN sentinels, n=0
- T3 MaxDD includes drawdown from initial_capital (post T6 BLOCKER fix)
- T6 = arithmetic mean of per-fold OOS/IS ratios

## Known limitations (deferred wiki docs)

- T2 Sortino formula non-canonical (std(losers) vs sqrt(mean(losers^2))) — threshold 1.5 calibration ambiguous
- T1/T2 annualization frequency-agnostic per ADR 0025 Q6 (intentional)
- Boundary tests at exact thresholds (T1=1.0, T2=1.5, T3=0.25, T6=0.7) missing

## Related

- [[walk-forward]] — produces per-fold OOS/IS ratios
- [[trade-extractor]] — produces list[TradeRecord] input
- [[dsr]] — separate DSR computation (informational S13)
- [[../architecture/acceptance-criteria]] — T1-T6 thresholds source-of-truth
- [[../decisions/0028-sprint-13-strategy-validation]] — Q5 verdict, T6 BLOCKER fix

## Sources

- `src/backtest/strategy_metrics.py` (S13 T6, commits 5908682 + 1f7124a)
- `tests/unit/test_strategy_metrics.py` (12 tests)
