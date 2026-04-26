---
name: S25 brainstorm Round 1 verdicts
description: Binding verdicts for S25 PHASE 2 brainstorm Q1-Q3 — 2026-04-26 (dashboard metrics specification)
type: project
---

**Date:** 2026-04-26. Sprint S25 brainstorm round 1. All 3 questions CONFIRMED.

## Q1 — Metrics dashboard MUST display per backtest run

### TIER 1 (verdict-critical, all mandatory)
- t1_sharpe_oos, t2_sortino_oos, t3_max_drawdown, t4_win_rate, t4_avg_rr, t5_t_stat
- t5_n_trades (PROMINENTLY — structural ceiling in all 5 historical runs, must be red if <100)
- t6_oos_is_sharpe_ratio_mean, dsr, mc_p_value_aggregate
- verdict + acceptance_gate.passed (top of display, first thing user sees)
- failed_criteria list (WHY it failed, not just that it failed)
- fold_sharpe_ratios array as per-fold table (fold concentration diagnostic — mandatory)

### TIER 2 (actionable insight)
- Total Return %, Total Commissions (user asked explicitly), profitable/losing trade counts
- avg win/loss (USDT), avg holding time (hours), profit factor
- Equity curve chart (visual narrative, shows fold boundaries)

### TIER 3 (deprioritize for S25 MVP)
- Symbol/timeframe comparison view (requires multiple stored runs)
- RSI distribution histogram (requires signal log)
- Cumulative trade log with timestamps (low cost if trades_df available)

## Q2 — Risk warnings

4 mandatory warnings in severity order:
1. T1 Sharpe > 3.0: "almost certainly overfit" (Hudson-Urquhart 2021). Historical: S17 T1=25.99 flagged.
2. Single fold dominates: max_fold_sharpe > 2× median OR >5. Historical: S17 fold#5=3.50, S22 fold#4=12.70.
3. MC p > 0.10: "indistinguishable from random"
4. DSR ≤ 0: "multiple-testing correction consumed all claimed edge"

Secondary (non-blocking): n_trades < 100, t_stat < 2.0, MaxDD > 10%.

## Q3 — Strategy comparison view

Column order (decision-relevance): VERDICT → Failed criteria → T1 → T5 n_trades → T5 t_stat → T6 OOS/IS → DSR → MC p → max fold Sharpe → MaxDD → Net return (labeled informational).
Color-code each cell against threshold.

## Cross-cutting concerns

- CC1: n_trades must be displayed HIGH in the UI, not buried — it killed all 5 hypotheses.
- CC2: Total Return must be labeled "Raw return (not risk-adjusted)" and shown WITH Sharpe/DD.
- CC3: RSI display = show run config parameters (thresholds) alongside results, not signal distribution.
- CC4: CRITICAL — Sortino=4446/7309 in WFA results is numerically anomalous (near-zero downside_std on tiny sample). Dashboard MUST warn if Sortino > 50 on <100 trades: "unreliable — insufficient losing trades for valid downside deviation estimate." Displaying raw Sortino=4446 without warning is actively misleading.
