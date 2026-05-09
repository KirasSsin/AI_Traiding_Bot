---
name: S35 autoresearch iter 3 verdict
description: Trader-expert ROUND 1 verdict on Donchian iter 3 pivot direction — REVISE to paradigm-dead (f) over maintainer's (a) volatility gate
type: project
---

# S35 Autoresearch Iter 3 — Paradigm-Dead Verdict

**Date:** 2026-05-08
**Trigger:** Iter 1 (FAIL Sharpe -3.23) + iter 2 (FAIL Sharpe -2.05) on held-out, maintainer recommending iter 3 volatility regime gate (a).

## Verdict: REVISE — option (f) paradigm-dead NOW

**Maintainer recommendation (a) rejected.** Volatility regime gate will further reduce n_trades (already n=29 held-out in iter 2), worsening the structural ceiling, not fixing it.

## Key evidence chain

- n_trades structural ceiling: BTC 4H Donchian generates ~8-12 trades/year. With 5818 bars (2.66y), max achievable after parameter tuning ≈ 44 train / 29 held-out. Both below ADR 0052 T5≥50 gate.
- Any additional filter (vol gate, EMA gate) reduces n further. EMA filter iter 2 already falsified (monotonic degradation EMA 0→300).
- Sign-flip overfit in BOTH held-out evaluations: iter 1 +1.27 → -3.23; iter 2 +2.50 → -2.05. This is noise-fitting, not regime problem.
- Effective N_trials ≈ 7-8 (base S35 + 31 iter1 trials + 37 iter2 trials). DSR penalty at N=8 makes any iter 3 result harder to pass, not easier.
- ADR 0054 pre-commit #8 specifies: "FAIL conjoint → α direction CLOSED." Protocol already dictates honest close.

## Protocol-compliant action

1. Issue honest close on autoresearch/donchian branch.
2. Archive cross-trial data per ADR 0052 protocol.
3. DO NOT run iter 3 — statistical near-zero probability + worsens DSR budget.
4. Forward profit path = δ TESTNET (S36-S38 live) n=10 milestone.

## If operator overrides (ESC-1)

Only permitted action: 2-line pre-check — count filtered-bar trades in training set for ANY proposed filter. If filtered set yields < 30 trades in training, abort immediately. Do NOT consume 40+ trial search budget.

## Why (a) is wrong

Faber 2007 volatility timing = diversified multi-asset portfolios over months. Does NOT apply to single-asset BTC 4H breakout with n≈20-30. EMA filter failure proved the filter-reduction mechanism empirically.

**Why:** Structural ceiling + sign-flip overfit + N_trials budget exhaustion + δ TESTNET already live.
**How to apply:** Any future autoresearch iteration proposals on single-symbol BTC 4H should start with n_trades projection. If projected n < 50 (ADR 0052 T5 gate) before search, reject proposal without iteration.
