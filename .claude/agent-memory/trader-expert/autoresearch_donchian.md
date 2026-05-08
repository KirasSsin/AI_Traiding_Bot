---
name: autoresearch_donchian recommendations
description: Trader-expert recommendations for adapting karpathy/autoresearch to Donchian BTC 4H strategy (research toy mode, May 2026)
type: project
---

# autoresearch_donchian — Research Toy Recommendations

**Date:** 2026-05-08
**Context:** Operator bypassed kit cycle. Pure research toy. Branch `autoresearch/donchian-may8`.
**Baseline (ADR 0054 LOCKED):** lookback=20, exit=10, atr_period=14, atr_mult=2.0 → Sharpe=0.9016, n_trades=17

## Q1 — Composite metric formula
DECIDED: `score = agg_sharpe * log1p(n_trades / 5.0)`
- Simplified 2-factor (win_rate not in evaluate_metric return dict — would require prepare_donchian.py modification)
- Hard floor: n_trades < 10 → score = -999 (not soft penalty)
- If win_rate added: `score = agg_sharpe * log1p(n_trades / 5.0) * max(win_rate, 0.0)`
- Rejected raw PnL: position-size-dependent, unreliable across commits

## Q2 — Search space + sweep order
Sweep order: lookback_n first → atr_stop_mult second → atr_period last

| Param | Range | Initial set |
|-------|-------|-------------|
| lookback_n | 5–80 | [5, 10, 15, 20, 30, 40, 55] |
| exit_lookback_n | 3–40 | derive as int(lookback_n * 0.5), always < lookback_n |
| atr_stop_mult | 0.8–4.0 | [0.8, 1.2, 1.5, 2.0, 3.0] |
| atr_period | 7–21 | [7, 14, 21] (lowest priority) |

10 named priority trials defined for first 10 experiments.

## Q3 — Profit-maximization direction
Baseline folds [0.93, -0.16, -0.90, 1.92, 2.71]: folds 2+3 are the kill zone (ranging regimes).

Priority directions:
1. WIDER ATR stop (2.5-3.0) + LOWER lookback (15) — BTC trend-following failure mode = premature stop-out
2. ATR/volatility filter (min atr/close > 0.5%) to skip low-vol regimes — fixes fold 3
3. Turtle 20-bar exit (exit_lookback=20) — extends winner duration

Avoid: tighter ATR stop (cuts winning folds 4+5), lower lookback alone without vol filter

## Q4 — Stop criterion
`no_improvement_for_30_consecutive_trials OR metric >= 2.5 OR budget_100_exhausted`
- NOT wall-clock time (variable runtime per n_trades)

## Q5 — Anti-overfitting safeguards
- n_trades < 10: hard discard (score = -999)
- Consistency: require 3/5 folds positive (not all-5 — too strict for 2023-2025 BTC)
- MC p-value: informational only, NO hard gate (underpowered at n<=30)
- NO distance-from-baseline penalty (research toy = exploration mode)

## Q6 — Held-out verification threshold
Pass: held-out Sharpe >= 0.5 × best train Sharpe AND held-out n_trades >= 5
Fail: negative held-out Sharpe = discard
Next step on PASS: formal ROUND 7 brainstorm in bot project kit (new ADR, pre-registered N_trials=1)
DOES NOT qualify for: δ TESTNET, MAINNET promotion, N_trials counter carry-over

## Critical finding — fold_sharpes skew risk
evaluate_metric computes aggregate Sharpe as simple arithmetic mean.
A strategy scoring [4.0, -2.0, -2.0, 4.0, 4.0] = avg 1.6 but 2/5 folds negative — passes consistency (3/5 positive) but extreme skew.
Operator/agent should manually verify fold_sharpes for any keep commit with aggregate > 1.5.

## Why/How to apply
- Results NOT promotable to production without full kit cycle
- Autoresearch trial count DOES NOT count toward bot project N_trials sigma_SR pooling (anti-snooping)
- Research toy branch: autoresearch/donchian-may8 (bypass is operator-explicit, documented)
