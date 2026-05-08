---
name: S33 brainstorm Round 1 verdicts
description: Binding verdicts for S33 PHASE 2 brainstorm Q1-Q6 — 2026-04-27 (trading restart: ESC-1/2/3 + formulas + strategy direction + test debt)
type: project
---

**Date:** 2026-04-27. Sprint S33 brainstorm round 1. 3-agent consilium (trader-expert + trading-logic-reviewer + quant-stats-reviewer).

## Q1 — ESC-1 Multi-symbol authorization
**Verdict:** EXPAND then CONFIRM-A

Multi-symbol BTC+ETH+SOL is the only viable path to T5 reachability. Single-symbol = dead end (5 honest closes, 3 timeframes all 59-73 trades). If ESC-1=N → project pause per S24 Option E.

4 binding conditions:
1. S17-relaxed params (RSI 35/65, BB 1.5σ) NOT S15 (RSI 30/70, BB 2σ)
2. Per-symbol independent WFA fold evaluation, not aggregate-pooled
3. CC6 WFA train-window pre-registration for 4H (train=2000 bars = 1.3y OOS only, not 3.3y)
4. Correlated drawdown documentation (BTC/ETH/SOL correlation → 0.90+ in tail events)

## Q2 — ESC-2 Acceptance gate definition
**Verdict:** REVISE → Option A strict T1-T6 only

"In profit" without MC/DSR passing = survivorship bias (S15 had aggregate PnL but MC p=0.998). Live readiness checklist (operational: halt recovery, position sizing, connectivity) supplements but does NOT replace statistical gate. If operator wants to deploy at MC p>0.10, that is an explicit deliberate override requiring documented operator statement.

## Q3 — ESC-3 4H operational model
**Verdict:** CONFIRM Option B — 3 simultaneous positions

3 simultaneous at 4H correct given low signal frequency (~20/year/symbol). 2 binding conditions:
1. Correlation stress documentation (BTC/ETH/SOL approach 0.90+ correlation in tail events — L1/L2/L3 CB is primary protection)
2. Multi-symbol data quality detector verification (S9 REST-vs-REST gap detection must extend to multi-symbol polling)

## Q4 — Formulas correctness post-S27
**Verdict:** EXPAND then CONFIRM

Formulas confirmed correct per S27. But CC6 (WFA train=2000 bars at 4H = 1.3-year OOS only) is unaddressed and must be pre-registered as configuration decision before S33 4H measurement. Not a formula bug but a blocking pre-specification gap.

## Q5 — S33 strategy direction
**Verdict:** REVISE → Option F alone (multi-symbol 4H), defer Option B (regime filter) to S34

S27 Q4 sprint plan already specified F=FOUNDATION, B=S29. Adding regime filter now risks reducing n below T5 floor before establishing multi-symbol baseline. Regime filter is an optimization on top of a working baseline, not a structural fix. Trigger for B in S33 scope: only if post-measurement audit shows ETH/SOL catastrophic fold concentration equivalent to S20 fold #2 (-185.21).

Key param specification: S17-relaxed (RSI 35/65, BB 1.5σ) must be pre-registered in S33 ADR for multi-symbol.

## Q6 — Test debt
**Verdict:** CONFIRM — fix pytest (3 failures) + mypy (1 error) first in S33

Additional concern: read failure tracebacks before coding the fix — failures may be test assertion updates (post-S27 T2/T3 behavior change) rather than code regressions. Fix mypy redef in same commit as multi-symbol __main__.py wiring changes. Defer ruff (~169, CI baseline guard prevents regression on new code).

## Cross-cutting concerns (4)

- CC-A: CC6 WFA train-window affects n estimate for multi-symbol (135 trades may be optimistic if effective OOS = 2024-2026 only)
- CC-B: Q2 REVISE + Q3 CONFIRM consistency — strict T1-T6 means correlated drawdown handled by CB layer, not soft "in profit" gate
- CC-C: Must pre-register S17-relaxed params explicitly in S33 ADR (not S15 params)
- CC6 new (from S27): WFA 4H window is a blocking pre-specification item

## Escalations to operator (4)
- ESC-1: Explicit "BTC+ETH+SOL authorized" statement required (breaks implicit BTCUSDT-only MVP)
- ESC-2: If "deploy at MC p>0.10" is intended → must be explicitly documented as statistical framework override
- ESC-3: Explicit "100% capital exposure during concurrent LONG signals approved" statement required
- CC6/WFA: "WFA train=X/test=Y for 4H pre-approved" statement required before measurement

**Why:** 5 honest closes + S23 binding insight (T5 unreachable single-symbol) + S24 Option E precedent + S27 CC6 unaddressed.
**How to apply:** Future S33+ trading brainstorms assume multi-symbol F (not F+B) as S33 scope, S17-relaxed params, per-symbol WFA gate. B deferred to S34 conditional on F results.
