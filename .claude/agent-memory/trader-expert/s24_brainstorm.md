---
name: S24 brainstorm Round 1 verdicts
description: Binding verdict for S24 PHASE 2 brainstorm Q1 — 2026-04-26 (v0.6 direction post-v0.5-honest-close: 6 options A-F — REVISE, Option E recommended over maintainer's Option F)
type: project
---

**Date:** 2026-04-26. Sprint S24 brainstorm round 1.

Q1 (v0.6 direction selection): REVISE — Option E (project pause) recommended over maintainer's Option F (MVP T5 floor amendment).

**Binding verdict summary:**

Option A (ML XGBoost n=120): DEFER — n=120 still below CPCV minimum (~300 effective samples after purging/embargo). Timeframe pooling assumption (S17 1H + S22 4H) is questionable — S20 15M catastrophic degradation shows the process is NOT timeframe-invariant, so pooling 1H+4H trades as IID training examples is unjustified. Fold concentration INCREASED from S17 (fold #5=3.50) to S22 (fold #3=12.70) — ML will memorize outlier folds regardless of regularization.

Option B (HMM): DEFER — same sample size problem, HMM instability on <200 observations, crypto HMM literature unreliable (Bulla & Bulla 2006 equities-derived), 4-6 sprint cost unjustified before larger empirical base.

Option C (multi-symbol revival): ESCALATE to user — contradicts binding user constraint ADR 0016 + 2026-04-26 confirmation. Scientifically defensible (scope change not bar-lowering) but requires explicit operator reversal.

Option D (different strategy class): DEFER — Donchian trend-following similar frequency profile to S13 EMA (20 trades); ATR-bands = mean-reversion variant, same FLAT+AND-gate frequency constraint; no fresh evidence any single-symbol alternative escapes the structural count ceiling.

Option E (project pause): RECOMMENDED — 5 hypotheses + genuine statistical signal (MC p≤0.02 at 1H AND 4H = regime-independent) + T5 structural insight = publishable scientific contribution. Epistemically honest, 0 cost, preserves all infrastructure.

Option F-i (T5 floor relaxation to 60-75): REJECT — Bailey 2014 p-hacking: floor was set as statistical power minimum (n≥100 for t-test validity), not as an operator-default count. Lowering to 60-75 doesn't make S22 t_stat=1.04 pass the t-stat gate anyway. Acceptance_gate (fold-level OOS/IS ≥0.7) also failed in both S17 and S22 independently of T5 — F-i doesn't address this.

Option F-ii (allow multi-symbol in MVP): ESCALATE to user — scientifically defensible, same as C. Requires ADR 0016 reversal.

Option F-iii (document T5 exception for mean-reversion family): REJECT — post-hoc strategy-class exception to statistical power floor is sub-form (i) with extra steps.

**Core analytical argument (REVISE rationale):**

Critical finding from direct data read: acceptance_gate.sharpe_gate_passed=false in BOTH s17_wfa_result.json (failed_folds=[1,2]) AND s22_wfa_result.json (failed_folds=[1]). The maintainer's claim "S17+S22 5/6+DSR+MC PASS" is imprecise — the fold-level sharpe gate also fails. Lowering T5 count floor would still leave the acceptance_gate failure in place. Option F sub-form (i) does not actually unlock MVP DONE.

T1 Sharpe anomaly: S17 T1=25.99 is explicitly flagged as "almost certainly overfit" per acceptance-criteria.md (">3.0 suspicious; >3.0 almost certainly overfit"). S22 T1=6.17 is above threshold but large variance (fold #3=12.70 drives it). Mean PnL 9.5x larger at 4H but t_stat lower = much higher per-trade variance, consistent with fold concentration.

Bailey 2014 discipline: T5 floor 100 was set as minimum for t-test interpretability, not as an operator-default. Observing 59-73 trades over 3 timeframes is evidence the strategy is sparse, not evidence the floor was miscalibrated.

**Source verification (direct reads this session):**
- s17_wfa_result.json: 59 trades, MC p=0.01, fold sharpes [0.96, -1.02, -1.46, 1.58, 3.50], T1=25.99, failed_criteria=["t5"], acceptance_gate.sharpe_gate_passed=false, failed_folds=[1,2] confirmed.
- s22_wfa_result.json: 62 trades, MC p=0.018, fold sharpes [1.93, -2.92, 1.32, 12.70, 1.78], T1=6.17, t_stat=1.04, failed_criteria=["t5"], acceptance_gate.sharpe_gate_passed=false, failed_folds=[1] confirmed.
- data/cross_trial_sharpes.json: {"trials": []} — reset confirmed for v0.6.
- acceptance-criteria.md T5 row: "Guards against random-noise edge; requires n≥100 OOS trades" — floor is statistical power minimum, not arbitrary count.
- acceptance-criteria.md T1 row: ">3.0 almost certainly overfit (Hudson–Urquhart 2021)" — S17 T1=25.99 is flagged overfit.

**Escalations:**
ESC-1: Pause vs Option F-ii (expand MVP scope to multi-symbol) — operator decision.
ESC-2: If F-ii chosen, which parameters — S15 (RSI 30/70, BB 2σ, failed T6+MC+DSR) or S17 relaxed (RSI 35/65, BB 1.5σ, passed T1-T4+T6+DSR+MC on BTC-only)?
ESC-3: F-i T5 floor relaxation — acknowledged as not scientifically defensible; if operator wants it anyway, must document post-observation amendment explicitly.
