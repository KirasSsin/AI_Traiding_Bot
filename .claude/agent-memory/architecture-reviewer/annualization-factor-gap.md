---
name: Annualization factor hardcoding gap
description: sqrt(8760) hardcoded at module level — correct for 1H, 2x wrong at 15M. Pattern for fix.
type: project
---

## The bug

`src/backtest/strategy_metrics.py:28` and `src/backtest/wfa_reporter.py:25`:
`_ANNUALIZATION_FACTOR = float(np.sqrt(8760))` — module-level constant.

At 15M: correct factor = sqrt(35040) ≈ 187.2. Hardcoded returns sqrt(8760) ≈ 93.6.
Effect: T1 Sharpe 2× understimated → false-FAIL risk at 15M for a strategy with real edge.
At 1H (S13/S15/S17): factor was correct — all historical verdicts valid.

## Fix pattern

`bars_per_year = int(365 * 24 * 3600 / bar_seconds)` computed from interval config.
Pass as `annualization_factor: float` argument to `compute_t1_t6_metrics()` and `format_wfa_report()`.
Remove module-level `_ANNUALIZATION_FACTOR` constant.
`vector_backtest.py:64` also hardcodes `np.sqrt(365 * 24)` — same fix needed there.

**Why:** Any future timeframe addition silently inherits wrong factor with no error.
**How to apply:** Flag as Condition A3 (BLOCK merge) on any 15M PR. Quant-stats-reviewer must verify
which of the 3 Sharpe series (bar-returns / per-trade / display) should each use which annualization.
