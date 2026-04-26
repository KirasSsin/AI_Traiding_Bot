---
name: S16 brainstorm Round 1 verdicts
description: Binding verdict for S16 PHASE 2 brainstorm Q1 — 2026-04-26 (post-S15 FAIL direction: honest close v0.2 vs B'/C/D/E)
type: project
---

**Date:** 2026-04-26. Sprint S16 brainstorm round 1.

Q1 (S16 direction post-S15 FAIL): CONFIRM — Option (D) honest close v0.2.

**Rationale summary:**

1. DSR math: sigma_SR=22.68 from 2 trials (-44.46, -12.38). Any S16 (n_trials=3) requires Sharpe > +20 OOS to pass DSR gate. Not achievable for 1H crypto mean-reversion.

2. BTC signal (+1.75, p=0.197) is the strongest observed in the project but does not pass MC gate (p>0.05). Only 44 BTC trades across 5 folds (~9/fold) — t-stat unreliable. Not decision-reversing.

3. ETH catastrophic fold (-188.65, fold index 7 in acceptance_gate.fold_sharpe_ratios) dragged aggregate. Pathological outlier, but does not rescue strategy conclusion — MC p=0.998 aggregate is clear.

4. Option B' (broader thresholds): N_trials=3 makes DSR harder, not easier. Broader RSI thresholds = more noise, same root-cause problem.

5. Option C (15M): 2 hard blockers (rest.py:66-67 interval_map, config.py:97-102 heal_max_age_seconds) + academic evidence from Hudson & Urquhart 2021 that mean-reversion degrades at sub-1H TF. 2 sprint cost for lower expected payoff.

6. Option D preserves infrastructure + enables clean N_trials=1 reset for v0.3 with new strategy hypothesis.

**Key data verified from files:**
- cross_trial_sharpes.json: trials[-44.46, -12.384], sigma_sr_cross_trial=22.68
- s15_wfa_result.json: BTCUSDT mean_oos_is_sharpe=+1.75, mc_p=0.197; ETHUSDT mc_p=0.998; aggregate mc_p=0.9975

**ADR follow-up:** ADR 0031 = v0.2 honest close. Should note: (a) Q3 15M blockers preserved for future, (b) BTC +1.75 noted but not decision-reversing, (c) ETH outlier fold (-188.65) = data pathology not strategy pathology, (d) cross_trial_sharpes.json should be forked/reset for any genuinely new strategy hypothesis in v0.3 (Bailey 2014: N_trials per hypothesis, not per framework).

**Why:** Maintainer recommendation was correct — 2 strategy families, 5y data, both FAIL empirically. DSR math makes further retries in same framework futile. Honest close is statistically principled stop.
