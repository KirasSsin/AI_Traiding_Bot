---
name: S13 brainstorm Round 1 verdicts
description: Binding verdicts for S13 PHASE 2 brainstorm Q1-Q8 — 2026-04-25 (strategy validation WFA, multi-sprint roadmap, T1-T6 gating, Kelly phases, DSR calibration)
type: project
---

**Date:** 2026-04-25. Sprint S13 brainstorm round 1.

Q1 (existing 2.2y vs backfill 5y): CONFIRM with constraint — use existing Parquet immediately. Statistical case solid (K=5 folds, 19441 bars >> 12600 minimum). Bear-regime gap (no 2022 data) is a real but scoped risk: T6 OOS/IS ratio + PBO are regime-agnostic overfit detectors; monthly revalidation cadence catches regime failure live. MANDATORY: verify "time" column name in data_collector before running K=5 folds. Document data coverage limitation in ADR 0028.

Q2 (WFA period range): REVISE — maintainer said "2024-01-01 → 2026-03-20" but simultaneously said "full existing data (max statistical power)." Self-contradiction: Parquet starts 2023-12-31. Use full Parquet extent (start_date=None, let WindowSplitter handle warmup). Discarding ~365 bars (1.9% of data) with no stated justification contradicts the stated intent. If there is a known quality issue with December 2023 bars, that must be stated explicitly — otherwise use full file.

Q3 (PASS/FAIL contingency): REVISE — accept multi-tier structure but cap PARTIAL FAIL tuning at 1 iteration (not ≤2). Two tuning iterations = gradient descent on OOS data per Bailey (2017). Rule: PARTIAL FAIL → exactly 1 pre-specified tuning sprint → re-measure → any FAIL = HARD FAIL. Parameter variants must be pre-specified BEFORE re-measurement (not selected after seeing partial OOS results). DSR N_trials increments with each measurement. Special rule: T3 MaxDD > 35% OR T1 Sharpe < 0 = automatic HARD FAIL regardless of other criteria count.

Q4 (multi-sprint roadmap): EXPAND — roadmap structure correct but S15-S17 are NOT development sprints. They are calendar-gated monitoring periods. Relabeling matters: calling them sprints implies TDD + ADR cycle that does not apply. Correct framing: S14=setup+launch sprint, S15-S17=Phase 2/3/4 monitoring periods (trigger condition = n≥30/100/200 trades, config update only), S18=concurrent 30d uptime verification, S19=MVP DONE review. Also: roadmap must address regime shift KS-test trigger (acceptance-criteria.md) as a potential sprint generator within monitoring periods. Calendar estimates: optimistic 6-12m (3 trades/week trending), conservative 18-24m (1.5 trades/week ranging) — both must appear in ADR 0028.

Q5 (CoinGecko daily CSV): CONFIRM — skip entirely for S13 and v0.1. ADR 0005 single-timeframe. Multi-timeframe = v0.2+ scope. WFA across 2.2y already captures multiple micro-regimes inherent in OOS test.

Q6 (WFA params on 19K bars): CONFIRM — keep ADR 0014 (train=2000, test=500, K=5, embargo=20). Math correct: 19441/5=3888 bars/fold >> 2520 required. K=10 rejected (insufficient train). 2000-bar window is 77x the longest lookback (EMA26). Pre-flight assertion needed: df.dropna() on indicator columns after warmup must yield ≥90% bars before WFA runs (NaN propagation in December 2023 warmup is a risk).

Q7 (DSR threshold gate): REVISE — compute provisional DSR gate in S13 itself, not defer to S14. The S10 Q2 REVISE deferred because per-fold count 10-40 was too low for reliable DSR. But S13 WFA on 2.2y produces ~240 aggregate OOS trades and ~48/fold, above the 30-trade threshold. All DSR inputs are knowable at S13 end: SR_hat (OOS Sharpe), N_trials=1 (first measurement, no parameter search), T (OOS bars), sigma_SR (cross-fold Sharpe std). DSR > 0 threshold is formula-invariant — it does not need calibration. Report S13 DSR with N_trials=1 label, note "recomputed at N_trials=N if tuning iterations occur."

Q8 (Kelly phase progression): CONFIRM — honest wait, no relaxation. ADR 0012 thresholds are mathematical bounds (Wilson 95% CI), not conservative policy choices. Realistic Phase 4 timeline: ~18-24 months from Mainnet pilot start at 1.5 trades/week (ranging market). The 6-12 month estimate assumes trending conditions with 3 trades/week. Operator briefing must include both scenarios. Mitigation: monthly signal frequency monitoring; if <0.5/week for 3 months, evaluate dormancy vs degradation.

**Critical cross-cutting concerns:**

CC1 — Q3+Q7: N_trials tracking must start at S13. Pre-specification of tuning parameters is the enforcement mechanism for look-ahead protection. If parameters selected AFTER seeing partial OOS results, N_trials is unbounded and DSR correction meaningless.

CC2 — Q1+Q8: Bear-regime gap means T1-T6 PASS does NOT guarantee Phase 3/4 progression. Live trading will test against live regimes including potential bear. Circuit breakers (ADR 0013) provide correct protection. Operators must be explicitly warned.

CC3 — Q4+Q8: ADR 0028 roadmap must include both optimistic (6-12m) and conservative (18-24m) calendar scenarios, not a single estimate.

CC4 — Q2+Q6: WindowSplitter warmup period starts December 2023 (potentially low-activity). NaN assertion must be pre-flight check in S13 implementation.

**User escalations:**
- ESC-1: HARD FAIL path requires user authorization before pivot development. Not engineering decision.
- ESC-2: 18-24 month capital commitment during monitoring phases requires user confirmation of timeline acceptability.
