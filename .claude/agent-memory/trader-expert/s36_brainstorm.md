---
name: S36 brainstorm decisions
description: Round 1 verdicts for Q1-Q5 (δ TESTNET activation, HaltGate wire-up, DSR amendment, TESTNET duration, MAINNET promotion criteria)
type: project
---

# S36 brainstorm — Round 1 verdicts

**Date:** 2026-04-27

## Q1 — v0.7+ direction primary
**CONFIRM** (b) δ TESTNET activate.
- ROUND 3 binding unanimous (pre-s35-backlog.md lines 53-55)
- S22 DSR=0.996 / MC p=0.018 = best evidence across 7 hypotheses
- α CLOSED, γ PERMANENTLY CLOSED, β = fallback only
- Non-obvious risk: 12mo ≈ 13 live trades → statistically insufficient for conjoint PASS. Must state in ADR 0055.

## Q2 — S36 scope (given Q1=b)
**CONFIRM** T1-T5 as listed, with scope clarification.
- Code inspection findings:
  - `EquityTracker.peak_equity_24h()` EXISTS (line 70 equity_tracker.py) — intraday DD computable without new method
  - `EquityTracker` LACKS `peak_equity_multiday()` — needs ~10-15 LoC new method
  - `TradeHistoryRepository` LACKS `recent_streak()` — file ends at line 152, no streak method. Needs ~10 LoC
  - `months_since_last_trade` derivable from `load_recent()` most-recent exit_ts — no new method
  - Total wire-up scope: ~80 LoC + tests (NOT 200-400 LoC as maintainer risk note implied)
- Live trade ledger: separate SQLite table `live_trade_ledger`, NOT appended to cross_trial_sharpes.json

## Q3 — DSR sigma_SR ADR amendment timing
**CONFIRM** pre-commit in S36.
- S35 T4 used per-fold proxy (stdev=4.45) flagged by quant-stats as "statistically inadmissible"
- Canon: DSR=NaN + dsr_status="insufficient_cross_trial_data" when N_cross_trial < 2
- NaN branch needed in src/risk/dsr.py + dashboard display guard

## Q4 — TESTNET duration commitment
**REVISE** — reject "12mo + 6mo interim checkpoint."
- Correct formulation: "up to 12mo OR halt-criteria trigger, whichever first — single operator review at trigger/12mo, no separate interim."
- 6mo interim is semantically redundant: HaltGate already fires halt events; interim produces no actionable outcome if no halt fires. Adds process overhead with no decision authority.
- ADR 0055 must make this explicit.

## Q5 — MAINNET promotion criteria timing
**CONFIRM** defer to S37+, with ONE pre-committed floor: MAINNET requires minimum n ≥ 30 live TESTNET trades.
- Full calibration (Sharpe/DSR thresholds) requires actual data context — defer correctly
- n≥30 floor derivable from Bailey 2014 first principles — safe to pre-commit now
- ADR 0052 acknowledgment protocol already provides anti-cherry-pick discipline

## Cross-cutting concerns
- CC1: HaltTrigger → ReasonCode mapping gap. 4 HaltTrigger categories (DD_INTRADAY/DD_MULTIDAY/CONSECUTIVE_LOSSES/NO_TRADE_TIMEOUT) need mapping to ReasonCode enum OR 4 new enum entries + ADR amendment. Blocking for T1.
- CC2: `s35_demo_active=True` must gate HaltGate as conditional in `assess()` — prevent spurious halts in backtest/dashboard paths
- CC3: live_trade_ledger must NOT append to cross_trial_sharpes.json (ADR 0052 anti-snooping)
- CC4: ADR 0055 operator acknowledgment = "TESTNET NOW ACTIVE as of [DATE]" (different from ADR 0053 template which only covers infrastructure-ready)

## ESC to user
- ESC-1: Expected n≈13 trades at 12mo — operator must confirm purpose of TESTNET run (statistical validation vs operational experience vs multi-year accumulation)
- ESC-2: Confirm TESTNET API key is separate from MAINNET credentials (security confirmation)

## Why: S36 is a wire-up sprint enabling the ROUND 3 binding primary path. No new hypothesis. No new strategy. Pure infrastructure activation + 2 critical formal gap closures (DSR ADR + HaltGate wiring).
## How to apply: These verdicts are BINDING. Round 2 will fire only if maintainer disagrees with Q4 REVISE. If operator chooses β pause instead, this entire set is superseded.
