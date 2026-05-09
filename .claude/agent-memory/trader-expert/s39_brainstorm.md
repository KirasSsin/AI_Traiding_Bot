---
name: S39 brainstorm decisions
description: Trader-expert Round 1 verdicts for Sprint 39 — volume_breakout production integration, Q1-Q9
type: project
---

# S39 Brainstorm — Round 1 Verdicts

**Date:** 2026-05-09
**Scope:** Volume_breakout production integration + critical tech debt + augmentation investigation

## Summary

6 CONFIRM / 1 REVISE / 0 DEFER / 2 notable (Q5 CONFIRM with mandatory amendment, Q9 EXPAND)

## Q1 — Params LOCKED verbatim
**CONFIRM (a).** Lock sweep#1644 verbatim: `lookback_n=9, exit_lookback_n=8, vol_window=10, vol_mult=1.4563, atr_period=9, atr_stop_mult=2.9663`. Any post-observation rounding = snooping per Bailey 2014. Must be a `VOLUME_BREAKOUT_LOCKED_PARAMS` constant in `indicators.py`.

## Q2 — Gate 2 forward paper-trade timing
**CONFIRM (b).** Ship alpha.39, Gate 2 validates on live delta TESTNET forward signals per ADR 0053/0055 pattern. ADR-0059 must include explicit Gate 2 fallback clause: FAIL → honest close S40+.

## Q3 — Track E scope (M1-M4 + MAINNET ADR)
**CONFIRM (partial).** M3+M4 in S39 Track E. M1+M2 + 12mo MAINNET ADR defer to S40+ (n=10 DSR milestone not reached).

## Q4 — llm-wiki/CLAUDE.md 316 lines pruning
**CONFIRM (b) DEFER.** Not a blocker, no observed dysfunction from file length.

## Q5 — Sizing policy for volume_breakout
**CONFIRM (a) Kelly 0.25×** but with mandatory ADR-0059 disclosure section:
1. Research PnL (+122.66%) is signal-quality discriminator, not dollar-return projector.
2. Under 0.25× Kelly, actual account return is materially lower (estimate from strategy win-rate/RR).
3. "$10k → $22k in 8mo" from held-out arithmetic does NOT translate to 0.25× sized account.
4. Kelly fraction revision = post-n=10 live trades with DSR gate.

## Q6 — Statistical evidence ordering in ADR-0059
**REVISE → option (a).** 8mo held-out = PRIMARY (untouched by 4510-sweep search, clean OOS). 3.3y full = SECONDARY with explicit label "search-period overlap — champion-bias contaminated." Maintainer's (c) inverts evidential hierarchy per Bailey 2014: 3.3y was the train period for the sweep; leading with +122.66% anchors operator on the champion-bias inflated number.

## Q7 — UI Dashboard ENFORCE 4H+BTCUSDT
**CONFIRM (a).** Enforce locked_symbol=BTCUSDT + locked_interval=240 in preset schema + backend 422 validation + frontend dropdown lock. Pattern: add `locked_symbol`/`locked_interval` optional fields to `STRATEGY_PRESETS` dict.

## Q8 — Cherry-pick research artifacts into main
**CONFIRM (a).** Cherry-pick FINAL_STRATEGY.md + CLOSE.md + results.tsv into `llm-wiki/wiki/project/research-evidence/`. Keep autoresearch branch until alpha.39 verified.

## Q9 — Profit augmentation investigation
**EXPAND.** Maintainer's 4-candidate investigation model creates hidden multi-comparison penalty. Correct framing: select ONE candidate a priori from theory, pre-register single binary hypothesis, strict PASS/FAIL criterion.

Candidate analysis:
- **EMA200**: FALSIFIED by iter 1-2 (train +2.50 → held-out -2.05). Plus long-bear suppression problem: held-out is bear market, EMA200 filter would suppress entries when BTC below EMA200 for months. REJECT.
- **ADX(14)>25**: Theoretically merit (direction-neutral trend strength), but n=17 → n_trades collapse risk. Borderline.
- **RSI(14)<70**: Theoretically BACKWARDS for breakout strategy (strong breakouts have elevated RSI — that's a feature, not a bug). REJECT.
- **ATR regime filter (ATR > rolling_mean(20))**: STRONGEST candidate. Direction-neutral, aligns with existing atr_period=9 design intent, expands volatility = better post-breakout moves and better stop ratio.

**Three options for operator (ESC-1 BLOCKING):**
- Option A (RECOMMENDED): Baseline LOCK immediately. ATR filter = S40+ separate pre-registered hypothesis with own held-out window.
- Option B: Single ATR filter test. Pre-register BEFORE any code run: exact spec (rolling_mean window=20, no param search), PASS criterion (augmented ≥ baseline on BOTH 3.3y AND 8mo by ≥1% PnL AND n_trades ≥ 12 on held-out), if FAIL → baseline LOCK, no retries in S39. Counts as N_trials+1.
- Option C (maintainer's 4-candidate): REJECT — 4 implicit comparisons regardless of formal backtest counts.

Expert recommendation: Option A (Bailey-correct). Option B defensible if operator accepts N_trials+1 accounting.

## Cross-cutting concerns

- **CC1**: Phase 5 test must use production pipeline (indicators.py + replay_engine), NOT simplified re-implementation. Verify production matches research toy to ±0.5% before writing test.
- **CC2**: reason-codes wiki sync: 42 listed → 50 actual → 53 after S39. Track D must include full reconciliation table.
- **CC3**: N_trials counter — volume_breakout = hypothesis #8 (or higher). ADR-0059 must state count and compute updated DSR penalty.
- **CC4**: Track B (H1+H2+Item#10) must complete BEFORE TESTNET activation of new strategy. Hard ordering constraint in plan.
- **CC5**: 95% CI on n=17 held-out Sharpe ≈ ±1.5-2.0. ADR-0059 must include actual CI, not just point estimate.
- **CC6**: Profit invariant is TWO independent gates: 3.3y ≥ +122.66% AND 8mo ≥ +20.42%. Not averaged.

## Escalations

- **ESC-1 BLOCKING**: Option A vs Option B for augmentation — operator decision required before PHASE 3.
- **ESC-2 INFORMATIONAL**: Research metric vs live return gap — operator must acknowledge before TESTNET activation.
