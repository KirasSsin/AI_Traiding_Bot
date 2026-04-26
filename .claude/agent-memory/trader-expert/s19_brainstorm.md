---
name: S19 brainstorm Round 1 verdicts
description: Binding verdict for S19 PHASE 2 brainstorm Q1 — 2026-04-26 (v0.4 direction post-v0.1-FINAL: 5 options A-E — EXPAND then CONFIRM-A with 4 mandatory amendments)
type: project
---

**Date:** 2026-04-26. Sprint S19 brainstorm round 1.

Q1 (v0.4 direction selection): EXPAND then CONFIRM (A) — BTC 15M mean-reversion, contingent on ESC-1 user confirmation.

**Binding verdict summary:**

Option (A) BTC 15M mean-reversion: CONFIRMED as best available path. 4 mandatory amendments required in ADR 0034 pre-registration.
Option (B) Hybrid ML XGBoost: DEFERRED to v0.5. Revisit after 15M measurement result. Principle is correct (S17 partial signal reverses ADR 0030 defer rationale) but timing wrong — need 15M baseline first.
Option (C) Multi-symbol: OUT OF SCOPE per user binding constraint (2026-04-26 "торговать будем в mvp только btc/usdt").
Option (D) 4H timeframe: REJECTED — lower frequency than 1H makes T5 count problem worse (estimated ~15 trades/4.81y).
Option (E) Project pause: ESCALATED to user (ESC-1). Technical case for both directions exists; operator preference required.

**Structural reframe (EXPAND component):**

S17 metrics T1=25.99 and Sortino=4446 are small-sample artifacts on n=59. Acceptance-criteria.md states "Sharpe >3.0 almost certainly overfit." 25.99 is 8.7× the "almost certainly overfit" threshold — these numbers carry zero informational weight about strategy quality. MC p=0.01 (permutation test) is the genuinely informative statistic — it's not small-sample-fragile.

Fold concentration is the key structural concern: fold_sharpe_ratios = [0.96, -1.02, -1.46, 1.58, 3.50]. Without fold #5, aggregate mean ≈ 0.01. The edge is regime-concentrated, not distributed. At 15M, 4× more trades come from the same folds (time periods), so effective statistical independence ≈ 5 folds still — not 240 independent observations.

**4 mandatory amendments for ADR 0034:**

1. T5 count failthrough: if OOS trades < 150 (not 100; at 15M frequency, 100 is trivially achievable without edge) → VERDICT FAIL. OR: keep T5 floor at 100 but add autocorrelation-corrected t-stat (Lo 2002). Operator decides in PHASE 3.

2. Fold concentration pre-registration: if fold #5 is the ONLY profitable fold and removing it yields aggregate OOS Sharpe < 0, this is documented as regime concentration risk, not distributed edge.

3. 15M data backfill pre-condition: verify Parquet row count ≥ 150,000 bars before architectural sprint. `python -m src backfill --symbol BTCUSDT --interval 15m --start 2021-07-02 --end 2026-04-26`. Bybit V5 supports interval=15 for Spot. If Bybit returns fewer bars (API oldest timestamp > 2021-07), escalate before committing to 2-sprint roadmap.

4. heal_max_age production safety: ADR 0034 must address this as a first-class architectural decision. At 15M, correct heal window is ≤ 15M (one bar), not 1H. Not a config tweak — needs explicit ADR + testing.

**Critical cross-cutting concerns:**

- sqrt(8760) frequency-agnostic annualization gap (S10 carry-over, CRITICAL for 15M): current implementation likely hardcodes sqrt(8760). At 15M, correct factor is sqrt(35040). If not fixed, T1 Sharpe will be UNDERSTIMATED 2× at 15M — wrong comparison against T1 threshold. Must be fixed in architectural sprint.

- DSR cross-trial sigma_SR implementation gap (S14 Q2 REVISE, unresolved): with n_trials=1 fresh start, this is not immediately triggered. But if S19 attempts multiple 15M sub-hypotheses (e.g., RSI 35/65 fails → try RSI 32/68), n_trials=2 and the gap re-appears. Address in architectural sprint.

- 4 honest close maturity: S14+S16+S18 = 3 closes. A 4th at S20/S21 = 4 documented attempts. Operator should consciously decide if v0.4 is the final commitment or if v0.5 is also authorized.

**Escalations:**
ESC-1: option E (project pause) vs option A (continue) — pure operator product decision. Cannot decide on behalf of operator.
ESC-2: T5 floor for 15M — keep 100 or raise to 150? Must be pre-registered before measurement. Cannot be changed after WFA run.

**Source verification (all direct reads this session):**
- s17_wfa_result.json: 59 trades, MC p=0.01, fold sharpes [0.96, -1.02, -1.46, 1.58, 3.50] confirmed.
- data/cross_trial_sharpes.json: {"trials": []} — fresh reset confirmed.
- acceptance-criteria.md line 31: ">3.0 almost certainly overfit" confirmed.
- SPRINT_STATE.md: between-sprints tag alpha.18 confirmed.
