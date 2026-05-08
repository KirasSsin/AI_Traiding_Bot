---
name: Delta TESTNET statistical power profile
description: 12mo TESTNET expected n=13 trades — all stats UNDERPOWERED. SE(SR)~0.31. MC_INSUFFICIENT_N throughout. sigma_SR=NaN (single trial). N_trials frozen at 7 per ADR 0055 SD-7.
type: project
---

Expected δ TESTNET statistical profile (S22 baseline ~13 trades/year):

- n at 12mo: ~13 trades
- DSR status: UNDERPOWERED throughout (10<=n<30 per ADR 0056)
- sigma_SR: NaN (cross_trial_sharpes.json currently empty post-S34 reset; first appended trial = N_entries=1 → NaN per ADR 0056 hierarchy)
- MC gating: sign-flip requires n>=20, block-bootstrap n>=40 → `MC_INSUFFICIENT_N` throughout 12mo
- SE(SR) at n=13: ~0.31 (formula: sqrt((1+SR^2/2)/n)) — 95% CI spans ±0.61, uninformative
- GATE_ELIGIBLE threshold (n=30): reached at ~2.31 years baseline rate
- n_eff gate (n_eff>=50): reached ~3.8 years baseline rate

**How to apply:** When reviewing any claim about δ TESTNET evaluation being statistically meaningful at 12mo, cite: all evaluation at 12mo is informational per ADR 0055 SD-1 option (c). The 12mo checkpoint is a MAINNET-promotion gate decision point, not a statistical pass/fail test. Any Sharpe, calibration ratio, or DSR number at n=13 has error bars that dominate the point estimate.

N_trials frozen at 7 (DELTA_N_TRIALS_LOCKED in live_trade_reporter.py:34) — δ is S22 hypothesis re-evaluation per Bailey 2014, NOT a new trial search. Cross-trial sigma_SR sourcing protocol: N>=3 entries preferred, 1-2 → NaN+UNDERPOWERED, 0 → None (ADR 0056).
