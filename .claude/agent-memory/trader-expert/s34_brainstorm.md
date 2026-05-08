---
name: S34 direction consilium verdicts
description: S34 PHASE 2 trader-expert direction vote — 2026-04-27 (post-S33 FAIL conjoint, 6th honest close trigger, 5-option vote + synthesis)
type: project
---

**Date:** 2026-04-27. Sprint S34 direction consilium (trader-expert perspective).

## Context
S33 FAIL conjoint. Multi-symbol BTC+ETH+SOL 4H mean-reversion. n_eff=26 (rho=0.75 Kish deflation) — correlation deflation makes T5=100 structurally unreachable even with 3-symbol expansion. 6 strategy hypotheses tested, all FAIL. Pre-committed failure branch (Item #12) TRIGGERED.

## Key analytical insight (NEW from S33)
n_eff=26 due rho≈0.75 changes the calculus permanently. Multi-symbol expansion is NOT a viable path to T5=100 with correlated assets (BTC/ETH/SOL). Adding a 4th correlated symbol adds ~18 raw trades but ~7 effective (diminishing returns from Kish deflation). Need uncorrelated assets (commodity futures, FX pairs) to escape — outside v0.1 scope.

## Votes

A(a) project pause: APPROVE — epistemically honest, publishable contribution (6 falsifications + structural ceiling proof), 0 cost.

A(b) T5 floor amendment to 50: CONDITIONAL APPROVE — scientifically defensible IF twinned with: (1) tighter MC p≤0.05, (2) n_eff ≥ 50 (not raw n), (3) T6 and acceptance_gate UNCHANGED and independently blocking, (4) explicit operator statement "evidence does NOT support live deployment", (5) new backtest sprint required — S17/S22 results cannot be retroactively re-classified as passing amended spec.

A(c) Donchian/ML/HMM: REJECT — n_trades desert for all variants. Donchian 4H n≈20-40. ML needs ≥500 training trades. 7th hypothesis with no cheap falsification path.

A(d) 1D timeframe: REJECT — 4.81y × 1D ≈ fewer signals than 4H mean-reversion, worsens structural ceiling.

B override gates: REJECT — T6=-2.84 + BTC fold #3 Sharpe=-32.68 = catastrophic OOS failure, not small-sample artifact. Deploying capital against this evidence irresponsible.

## Synthesis
Recommended: A(b) T5 floor amendment — CONDITIONAL on controller's framing being extended with n_eff correction + MC tightening + mandatory new backtest sprint. Controller's framing broadly correct but undersells required caveats.

Final position: CONFIRM (controller A(b) recommendation accepted with mandatory pre-registration extensions listed below).

## 10-item pre-commitments for S34 ADR
1. T5 floor: 100 → 50 (Hudson & Urquhart 2021 justification)
2. n_eff threshold: ≥ 50 (Kish correction mandatory on any multi-symbol run)
3. MC threshold: ≤ 0.05 (tightened from 0.10 — compensates for floor relaxation)
4. T6 OOS/IS: ≥ 0.7 UNCHANGED (independently blocking)
5. acceptance_gate.sharpe_gate_passed: UNCHANGED (fold-level gates remain)
6. Operator written acknowledgment: "Statistical evidence as of v0.6 does NOT support live deployment; amendment reflects crypto-specific sample-size reality"
7. Strategy scope: MEAN_REVERSION_S17_RELAXED_PARAMS named constant — no new parameter search
8. Backtest data: MUST extend beyond S33 date, full available OHLCV history
9. Symbols: n_eff correction mandatory — no raw n substitution
10. N_trials counter increments: n_trials=4+ from current 3

## Critical note
A(b) without a new backtest sprint = post-hoc rationalization, NOT pre-registration discipline. S17/S22 results predated n_eff correction (T3 S33) and MC fix (T2 S33) — cannot be reused as pass evidence.

**Why:** S24 analysis showed acceptance_gate.sharpe_gate_passed=false independently of T5 in both S17 and S22. Floor amendment alone does not unlock MVP DONE.
**How to apply:** S34 ADR must contain all 10 pre-commitments BEFORE any new backtest measurement run.
