---
name: S27 brainstorm decisions
description: S27 formula audit verdicts — Q1-Q4 (formula review, parameter optimization, new strategies, sprint plan)
type: project
---

# S27 Brainstorm — Formula/Metrics Audit Verdicts

**Date:** 2026-04-26
**Trigger:** Operator request to revise all trading metrics/formulas to achieve profitability.
**Source artifact:** data/formulas_audit_v1.json (30 experiments, 3 strategies × 11 combos)

## Key findings (institutional knowledge)

### Formulas: NO BUGS FOUND
All 17 formulas are technically correct:
- RSI/ATR Wilder (TA-Lib) — KEEP
- EMA 12/26 classical α=2/(n+1) — KEEP per ADR 0011
- BB pop-stdev ddof=0 — KEEP (Bollinger standard)
- Sharpe OOS Lo 2002 annualization — KEEP
- Commission 0.30% round-trip — KEEP (conservative, correct)

### Root causes of ALL 30 FAIL verdicts (prioritized)
1. T5 n_trades < 100: structurally unreachable at 4H single-symbol (n=30-45 per 3.3y)
2. MC p-value: power insufficient at n<100 (p>0.10 even with positive PnL)
3. Fold concentration: one bull-regime fold drives aggregate Sharpe (e.g. ETH 4H fold 0 = Sharpe 8.03)
4. T4 win_rate: BTC 4H win_rate=0.43 vs required 0.45 for avg_rr 1.5-2.0 band

### Best performers (profitable but structurally T5-blocked)
- mean_reversion_s15 ETH 4H: pnl=+404, T1=7.63, DSR=0.83, MC=0.28, n=45 — ALMOST PASSES (only fold 4 fails at 0.43 Sharpe)
- mean_reversion_s15 BTC 4H: pnl=+155, T1=5.48, DSR=0.70, MC=0.50, n=30 — fold concentration (folds 0/1/2 negative)

### Critical CC5 concern (new)
ALL 30 experiments show reason_code=EXIT_TP_HIT for every trade including losses.
This is suspicious — SL hits should show EXIT_SL_HIT. Requires src/backtest/replay_engine.py audit
before trusting win-rate statistics.

### CC6 concern (new)
BTC 4H and ETH 4H first trades are 2023-12-12 — WFA train=2000 bars at 4H consumes
all 2023 data for IS folds, leaving only 2024-2026 for OOS. Effective backtest = 1.3 years not 3.3.

## Q1 verdict: CONFIRM (no formula fixes needed)
Two ADD items: Profit Factor as informational metric (already in trade_stats, not T-criterion).

## Q2 verdict: REVISE
Parameter tuning cannot fix T5/MC power — structural. Only multi-symbol at 4H solves both.
Within existing trade count: SL tighten (1.0×ATR) could push avg_rr toward 2.0 for BTC 4H.

## Q3 verdict: EXPAND
Ranked hypotheses:
1. Multi-symbol mean_reversion_s15 4H (BTC+ETH+SOL) — HIGH probability, n≈135
2. ADX<25 regime filter + daily SMA50 trend gate — MEDIUM probability (reduces losing trades)
3. MTF confirmation (4H entry + 1D trend) — MEDIUM
4. Partial TP + trailing stop on remainder — MEDIUM (HIGH as addon to H1)
5. Donchian breakout 4H (independent hypothesis, trend-following) — MEDIUM

ML/XGBoost: DEFER (n=45-135 infeasible for ML, need 500+ training trades)

## Q4 sprint plan
S27: Multi-symbol 4H mean-reversion (L effort) — FOUNDATION
S28: Regime filter + MTF trend gate (M effort)
S29: SL/TP calibration + t-stat power analysis (M effort)
S30: Donchian breakout (M effort, independent parallel track)
S31: DSR cross-trial + MC permutation audit (S effort, methodology)

## Operator escalations (ESC-1/2/3)
ESC-1: Multi-symbol expansion requires explicit operator authorization (breaks BTCUSDT MVP scope)
ESC-2: Operator must decide: "trading in profit" (already achieved on ETH 4H) vs "pass acceptance criteria" (requires T5 fix)
ESC-3: 4H multi-symbol requires operator comfort with positions held days, 3 simultaneous positions

**Why:** Operator request framing ("optimize metrics") implied formula bugs — audit falsifies this. True fix = more data (multi-symbol) + regime awareness (filter).
**How to apply:** Future brainstorms on strategy profitability should start from "is T5 reachable?" before any parameter optimization discussion.
