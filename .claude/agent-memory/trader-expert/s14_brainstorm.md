---
name: S14 brainstorm Round 1 verdicts
description: Binding verdicts for S14 PHASE 2 brainstorm Q1-Q5 — 2026-04-26 (pre-registered tuning experiment, N_trials DSR, PASS semantics, param wiring, Option B pre-commit)
type: project
---

**Date:** 2026-04-26. Sprint S14 brainstorm round 1.

Q1 (Tuning parameter set): EXPAND — mis-scoped. Core issue: T5 (n_trades >= 100 OOS) is structurally unreachable with any EMA/ADX/RSI parameter set on 1H BTC WFA K=5 (2500 OOS bars). 1 trade per 25 bars = 1/day required — incompatible with EMA crossover. Parameter set moderate (EMA 9/21, ADX 20, RSI 35/65) may be acceptable IF operator explicitly acknowledges T5 will likely FAIL again. CRITICAL: RSI direction error in backlog — "35/65 wider" may be semantically wrong depending on signal logic. Must read src/signalgen/strategy.py RSI filter direction before pre-registering. Operator escalation required before S14 starts.

Q2 (N_trials accounting): REVISE — N_trials=2 is correct per Bailey eq. 13 (one re-measurement event). BUT: at N_trials=2, sigma_SR must be computed cross-trial (using S13 Sharpe=-44.46 and S14 Sharpe as two data points), NOT just cross-fold within a single WFA run. S13 strategy_metrics.py computes sigma_SR from K=5 fold Sharpes within single WFA — this is correct for N_trials=1 but wrong for N_trials=2. sigma_SR ≈ std(-44.46, SR_S14) will be ~30+ for any plausible S14 result, making DSR negative with near-certainty. DSR gate will auto-FAIL even if T1-T6 pass. Code change required in S14 implementation: cross-trial sigma_SR aggregation step.

Q3 (PASS verdict semantics borderline): CONFIRM — strict formula PASS (option a), no operator override, no amber zone. Thresholds are pre-specified; introducing negotiable zones defeats the pre-registration framework. T6 + DSR gate already handle overfit detection. If T1-T6 pass strict formula → PASS, regardless of margin.

Q4 (Strategy parameter wiring): CONFIRM — Settings config (option a). Fields already exist (strategy_ema_fast, strategy_ema_slow, strategy_adx_threshold, strategy_rsi_oversold, strategy_rsi_overbought per S11). Change Settings defaults only. Must include test audit: grep old default values in tests/, update parametrized tests before changing defaults.

Q5 (FAIL fallthrough Option B): CONFIRM — pre-commit binding (option a). User verbatim "Option A → if still FAIL → Option B" = commitment. Third measurement would require N_trials=3 with sigma_SR including -44.46 anchor = DSR penalty lethal. Unbounded iteration = p-hacking. Document considered-but-rejected alternatives (option b aggressive EMA 5/13) in ADR 0029.

**Critical cross-cutting concerns:**
CC-A: T5 structural impossibility — n>=100 OOS trades requires 1 trade/day signal frequency on 1H BTC. EMA crossover cannot plausibly achieve this. ESC to operator BEFORE S14 starts.
CC-B: DSR sigma_SR at N_trials=2 — current implementation is per-fold within single WFA. Must extend to cross-trial for S14. With -44.46 as anchor, DSR FAIL near-certain even if T1-T6 pass.
CC-C: RSI direction ambiguity in backlog — "35/65 wider entry zone" may be wrong label. Read strategy.py signal logic before pre-registering RSI parameter change direction.

**User escalations:**
ESC-1: T5 structural impossibility — operator must choose before S14: (a) proceed knowing T5 FAIL likely, treat it as auto-Option B; (b) amend acceptance-criteria.md T5 (requires ADR); (c) skip S14, go directly to Option B.
