---
name: S22 brainstorm Round 1 verdicts
description: Binding verdict for S22 PHASE 2 brainstorm Q1 — 2026-04-26 (v0.5 direction post-v0.4-honest-close: 4 options A-D — REVISE, option C chosen over maintainer's option A)
type: project
---

**Date:** 2026-04-26. Sprint S22 brainstorm round 1.

Q1 (v0.5 direction selection): REVISE — option (C) 4H mean-reversion test chosen over maintainer's (A) Hybrid 1H+ML XGBoost.

**Binding verdict summary:**

Option (A) ML XGBoost hybrid: DEFERRED — n=59 is not a viable ML training set. CPCV requires ~300+ effective samples. S17 fold #5 concentration (3.50 sharpe drives aggregate; without fold #5 mean=0.01) means ML will memorize one regime period, not generalize. 5-10 sprint cost on fragile empirical base is wrong sequencing.

Option (B) HMM regime-switch: DEFERRED — same sample-size problem as (A) from different angle. Regime detection trained on one fold's characteristics cannot generalize reliably. Cheaper than (A) but still wrong before establishing larger empirical base.

Option (C) 4H mean-reversion test: CONFIRMED as first move. 1-2 sprint cost. Reuses existing infrastructure (S19 Condition A1 parameterized interval_map, Condition A3 parameterized annualization). Cheap falsification — Hudson & Urquhart 2021 supports lower frequencies for mean-reversion in BTC. If 4H PASS: pursue (A) or (B) from stronger empirical base. If 4H FAIL with few trades: pause. If 4H FAIL with enough trades but bad Sharpe: (B) HMM more defensible.

Option (D) Project pause: DEFERRED pending (C) result. Premature to pause without testing 4H.

**Core analytical argument (REVISE rationale):**

S17 n=59: MC p=0.01 is genuinely informative (permutation-based, distribution-free). T1=25.99 is NOT informative (acceptance-criteria.md: ">3.0 almost certainly overfit"). Fold #5=3.50 drives aggregate — without fold #5, mean=0.01. ML on 59 samples with purging embargo leaves <50 effective training examples. Any XGBoost will memorize fold #5 period regardless of regularization. This is not a "partial signal" sufficient for ML — it is a curiosity requiring larger sample before ML investment.

**Cheap-falsification sequencing principle:**
(C) 1-2 sprints → evaluate → then (A) or (B) or (D)
This dominates (A) directly because:
- If 4H works: stronger empirical base for ML/HMM investment
- If 4H fails with few trades: n<40 → ML unambiguously wrong, pause
- If 4H fails with enough trades but bad Sharpe: HMM more interesting (larger sample base)

**S19 memory context:**
S19 brainstorm rejected 4H as "~15 trades/4.81y" (raw frequency 1H/4 × 59). BUT at 4H, BB(20, 1.5σ) captures 80H lookback vs 20H at 1H — AND-gate dynamics are different. Hudson & Urquhart 2021 supports lower frequencies. The 4H rejection in S19 was contextually correct (we needed 15M baseline) but should not be permanent.

**Pre-conditions for (C) to be valid (must be pre-registered in ADR 0037):**
1. T5 floor for 4H: pre-register 40 trades (conservative). If <40 → FAIL count alone.
2. Annualization: bars_per_year=2190 (8760/4). Condition A3 infrastructure must confirm 4H support.
3. WFA parameter recalibration: train=1000/test=250 bars may be more appropriate at 4H (250 bars = 41 days OOS, similar cadence to 1H 500 bars = 20 days). Architecture-reviewer to confirm.
4. Bybit V5 interval_map: verify `--interval 240` support in S19 Condition A1 refactored dict.

**Escalations:**
ESC-1: T5 floor for 4H (40 vs 30 trades) — operator pre-registers before measurement.
ESC-2: WFA param recalibration at 4H (ADR 0014 deviation approval) — operator decision.

**Source verification (direct reads this session):**
- s17_wfa_result.json: 59 trades, MC p=0.01, fold sharpes [0.96, -1.02, -1.46, 1.58, 3.50], T1=25.99, failed_criteria=["t5"] confirmed.
- s20_wfa_result.json: 73 trades, T1=-45.57, fold sharpes [-0.74, -4.83, -185.21, +2.27, +2.84] confirmed.
- data/cross_trial_sharpes.json: {"trials": []} — fresh baseline confirmed.
- acceptance-criteria.md: ">3.0 almost certainly overfit (Hudson–Urquhart 2021)" confirmed.
- s19_brainstorm.md: Option D (4H) rejected S19 for "~15 trades/4.81y" estimate — NOT permanent rejection.
- sprint-17 page: "T1 Sharpe 25.99 + Sortino 4446 = suspiciously high — possibly overfit indicator" confirmed in sprint page itself.
