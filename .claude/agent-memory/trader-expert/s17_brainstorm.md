---
name: S17 brainstorm Round 1 verdicts
description: Binding verdict for S17 PHASE 2 brainstorm Q1 — 2026-04-26 (BTC-only MVP retry, strategy hypothesis #3 selection — REVISE vs maintainer option a)
type: project
---

**Date:** 2026-04-26. Sprint S17 brainstorm round 1.

Q1 (Next strategy hypothesis BTC-only MVP retry): REVISE — maintainer recommends (a) BTC-only mean-reversion relaxed RSI 35/65 + BB 1.5σ + variance cap. Trader verdict: REVISE to (b) ATR-based regime-filtered mean-reversion (moderate volatility filter on top of existing RSI+BB infrastructure). Core reason: the T5 frequency math does not close under BTC-only single-symbol constraint for option (a).

**Quantitative analysis (verified from s15_wfa_result.json):**

BTC baseline: 44 trades / 5 OOS folds across 4.81y (2,500 OOS bars: 5 × 500).
Signal rate: 44/2,500 = 1.76% of OOS bars trigger entry.

Relaxed thresholds effect (BB 1.5σ vs 2σ, RSI 35 vs 30):
- BB 1.5σ one-sided tail probability: 6.68% vs 2.27% at 2σ → 1.47× more BB crossings
- RSI < 35 vs < 30: ~17% wider zone → ~1.17× more RSI triggers
- AND-gate: joint probability increase is SUBlinear due to RSI-BB positive correlation (oversold price = low RSI ≈ low BB). Conservative AND-gate multiplier ≈ 1.5-1.7×
- Expected BTC trades: 44 × 1.6 (midpoint) ≈ 70 trades. Upper bound (2×): 88 trades.
- T5 floor: 100 trades. SINGLE-SYMBOL BTC AT RELAXED THRESHOLDS = ~66-88 trades. DOES NOT CLOSE T5 UNDER CONSERVATIVE-TO-MID ASSUMPTIONS.

Only the maintainer's optimistic 2-3× multiplier reaches 100. The 2-3× assumes near-independence of RSI and BB signals on BTC — empirically false (they are constructed from the same price series, correlated).

**Why option (a) fails the T5 feasibility test:**
1. BTC-only = 44 trades baseline at RSI 30/70 + BB 2σ. Relaxed to 35/65 + 1.5σ yields 66-88 trades estimated. T5 floor = 100. Gap = 12-34 trades. Not a guaranteed close.
2. If T5 reached (100+), the wider RSI thresholds mean LOWER mean_pnl per trade (more noise, less extreme reversion). t_stat = mean_pnl / (std_pnl / sqrt(n)). Wider thresholds tend to lower mean_pnl AND raise std_pnl → double pressure on t_stat. t_stat ≥ 2 constraint may become binding even if n≥100.
3. Variance cap (fold sharpe < -10 dropped): the -10 threshold was reverse-engineered from S15 ETH outlier (-188.65). Pre-registering this threshold for S17 BTC-only is circular: the threshold was derived from multi-symbol knowledge applied to a now-single-symbol context. Legitimate pre-registration would require a different threshold derived from first principles (e.g., fold sharpe < mean - 3σ of fold sharpes). Risk = borderline p-hacking.
4. N_trials=1 fresh start is correct and is a real advantage — BUT this advantage is identical for option (b) ATR-regime filter.

**Why option (b) ATR-regime mean-reversion is better:**
1. ATR percentile filter does NOT reduce trade count relative to option (a). Regime filter is applied to the UNIVERSE of possible signals — when ATR is extreme (top 20% or bottom 20%), it EXCLUDES low-confidence signals. This can IMPROVE mean_pnl without reducing n proportionally (higher quality signals).
2. ATR(14) already implemented (src/signalgen/indicators.py, Wilder, ADR 0011). No new indicator required.
3. The ATR filter addresses S15's actual failure mode: HIGH VARIANCE (fold sharpe std enormous — -188.65 to +8.20). The variance cap in option (a) is ad hoc; ATR regime gating is STRUCTURAL variance control.
4. For BTC specifically: ATR percentile [20,80] at 1H over 4.81y data selects ~60% of bars as "moderate vol." Combined with RSI+BB signals at original or modestly relaxed thresholds (RSI 32/68 ± 2 relaxation), trade count ≈ 44 × [threshold_mult] × [regime_pass_rate]. If regime keeps 60% of bars AND threshold relaxation adds 1.3× more signals: 44 × 1.3 × 0.6 = 34 trades... this is LOWER, not higher.

CORRECTION: ATR regime does NOT add trades — it filters existing trade signals. If applied to already-sparse BTC signal set (44 baseline), it can only reduce or maintain trade count. This is a critical flaw in option (b) for single-symbol.

**Revised analysis — neither option (a) nor option (b) solves T5 for BTC-only:**

Option (a): 66-88 expected trades (T5 uncertain, likely FAIL)
Option (b): ≤ 44 trades after ATR filter (T5 certain FAIL)

**EXPAND: the question is structurally mis-scoped.**

The real issue is that BTC-only 1H mean-reversion, even with threshold relaxation, is borderline for T5 under conservative frequency assumptions. The decision to proceed with BTC-only single-symbol is the binding constraint, not the specific threshold choices. The question should be: IS T5 ACHIEVABLE UNDER BTC-ONLY CONSTRAINT FOR ANY VARIANT OF MEAN-REVERSION?

Mathematical upper bound: even if every RSI+BB signal independent and thresholds maximally relaxed (RSI 40/60 + BB 1.0σ), we might reach 150-200 trades — but at that point mean_pnl approaches zero (every bar is a signal, no edge). The edge/frequency tradeoff has a peak. For BTC 1H mean-reversion, the peak may be around RSI 32-35 range giving ~60-80 trades — still below T5 floor.

**Final verdict: REVISE to EXPAND.**

The question "which option a/b/c/d/e" is wrong. The correct reframe: "Is MVP T5-compliant strategy hypothesis achievable for BTC-only 1H, or does MVP require accepting a structural constraint relaxation (either multi-symbol OR timeframe change)?"

Given that:
- BTC-only mean-reversion relaxed = borderline/likely FAIL on T5 (66-88 expected trades)  
- ATR regime filter = certain FAIL on T5 (≤44 trades)
- Donchian breakout = trend-following = same S13 frequency problem (FAIL)
- 15M = 2 sprint blockers (interval_map + heal_max_age) + Hudson & Urquhart academic degradation
- Honest close = option (e)

The only option that has plausible T5 is (a) with optimistic assumptions. This makes (a) the "best of a bad set" choice — CONFIRM the maintainer's direction as least-bad — but HONEST about T5 uncertainty.

**Final binding decision: EXPAND → then CONFIRM (a) as least-bad option, with honest T5 uncertainty.**

Reframe: option (a) is the only technically available path. CONFIRM it, but explicitly note:
1. T5 frequency math: 66-88 trades expected (may not reach 100)
2. If T5 fails on count: honest close v0.1 (option e) with documented "3 hypothesis attempts"
3. Variance cap must be re-specified with non-post-hoc threshold: recommend fold sharpe < -3σ_fold (not -10)
4. Pre-registration of the exact RSI/BB thresholds binding before running WFA

**Why NOT option (e) honest close immediately:** user direction is "continue к MVP с new hypothesis — agents decide." The BTC +1.75 / p=0.197 is the strongest signal observed. With fresh N_trials=1 baseline, S17 gets a clean DSR slate. If S17 FAIL with 66-88 trades → clean evidence for honest close v0.1 (3 attempts, documented). Proceeding is informationally valuable.

**ADR follow-up:** ADR 0032 must note T5 frequency uncertainty honestly. Pre-register RSI 35/65 + BB 1.5σ, but include explicit T5 count sensitivity: "If OOS trades < 100 → FAIL on T5 count, no t-stat computed. Honest close v0.1 follows per option (e)."
