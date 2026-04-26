---
name: S9 brainstorm Round 1 verdicts
description: Binding verdicts for S9 PHASE 2 brainstorm Q1/Q2/Q3 — 2026-04-25
type: project
---

**Date:** 2026-04-25. Sprint S9 brainstorm round 1.

Q1 (WS+REST price epsilon-halt): REVISE — kline-vs-kline requires WS kline subscription not currently active. REST-vs-REST (two REST calls close together) has its own race window. Recommended: REST snapshot at bar close (T) vs previously stored REST bar close (T-1), pure REST comparison, cadence = per-bar (on new closed bar event). Threshold = 0.5% relative CONFIRMED. No new WS topic required.

Q2 (mypy --strict): REVISE — src.risk.* is NOT dead code under ignore_errors (it's money-path actively maintained). Sequential order should be: core first (smallest, fastest), then risk, then backtest. core is ~50 LoC legacy stub = 1-2 hour fix. Eliminates "risk last" ordering risk. backtest deferred if sprint slots tight.

Q3 (per-fill + DSR): CONFIRM — split B1+B2 is correct. DSR operates on trade-level not fill-level so B2 is independent. B1 per-fill schema uses FK to trade_history (not migration). WS execution topic is required for real-time per-fill (not REST post-hoc for live bot). DSR with 0 trades = vacuous but framework ships for first live trades.

**Why:** These are binding decisions logged as S9 ADR input. If round 2 is triggered on Q1 or Q2, revisit with adversarial self-review.
