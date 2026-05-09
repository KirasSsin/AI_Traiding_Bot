---
name: S35 autoresearch iter 5 Round 2 gate threshold
description: Trader-expert ROUND 2 verdict on 15M bar-range gate threshold — CONFIRM_REVISE: strict close stands (median 0.243% < gate 0.25%)
type: project
---

# S35 Autoresearch Iter 5 — Round 2 Gate Threshold Verdict

**Date:** 2026-05-08
**Context:** Pre-check on BTCUSDT_15m.parquet shows median bar range = 0.243% vs pre-registered gate 0.25%. Maintainer disputes strict close, claims 0.7 bps gap is noise + tail-bar argument.

## Verdict: CONFIRM_REVISE

Round 1 close-direction verdict stands. Gate fails. Direction closes.

## Key reasons

1. **Bailey 2014 anti-snooping**: Gate was pre-registered BEFORE seeing data. Changing gate AFTER seeing 0.243% result = post-hoc amendment = snooping, regardless of magnitude of gap.

2. **T vs T+1 distinction**: Donchian signal fires on close(T), fill at open(T+1). Maintainer's "tail-bar" argument applies to signal bar T (breakout bar = high range). But the fill bar T+1 is the follow-through bar, whose range distribution at 15M BTC is unknown and likely lower (mean-reversion regime per Hudson & Urquhart 2021, validated S20/S21). Unconditional q75-q90 distribution does NOT equal conditional distribution of T+1 given breakout at T.

3. **Asymmetric loss**: False positive (run sweep, misleading result, waste DSR budget) >> False negative (close direction, lose 10 min compute). Fail-closed principle applies.

4. **Mean criterion was not pre-registered**: Switching from median to mean post-hoc = different post-hoc snooping path. Even if mean criterion is theoretically better for tail-trading, changing it after seeing the pre-check result violates ADR 0054 discipline.

## What maintainer got right

"10 min compute provides clean held-out evidence either way" — true in isolation. But the gate exists precisely to avoid consuming N_trials budget on marginal cases without clean economic rationale.

## How to apply

If operator overrides and insists on running sweep: it MUST be logged as ESC-1 override with explicit acknowledgment that pre-registered gate was bypassed post-hoc. The DSR penalty applies at higher N_trials count.

If operator accepts close: next hypothesis (different strategy class, different timeframe, δ TESTNET n=10 milestone) proceeds with N_trials budget preserved.
