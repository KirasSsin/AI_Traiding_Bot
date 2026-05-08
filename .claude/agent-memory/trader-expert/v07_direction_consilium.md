---
name: v0.7+ direction consilium binding decision
description: Post-S34 ROUND 3 binding (2026-04-27) — data audit triggered pivot: δ TESTNET primary + α Donchian parallel + ζ risk mgmt. (b) eliminated by math projection.
type: project
---

**Date:** 2026-04-27. v0.7+ direction consilium ROUND 3 (trader-expert perspective). Post-audit SUPERSEDES prior ROUND 2 binding.

## Context
S34 shipped hybrid (ADR 0051 honest close v0.6 + ADR 0052 amendment LOCKED). 6 strategy hypotheses tested, all FAIL conjoint. 3-agent consilium BINDING. Data audit completed — triggers my own pre-condition from ROUND 2.

## Data audit result (ROUND 3 trigger)
- BTC/ETH/SOL 4H: 7273 bars / 2023-01-01 → 2026-04-26 (3.31y actual)
- Bybit max history: 2021-07-02 (additional 1.5y dormant)
- **n_eff projection with FULL extension (4.81y): 37-41** (Kish rho=0.75, factor=2.5)
- **n_eff = 37-41 < 50 amended threshold — structural impossibility**
- My ROUND 2 pre-condition triggered: "If n_eff < 50 even with full extension → immediately pivot to (c) as primary"

## ROUND 3 votes

| Option | Vote | Key reason |
|--------|------|------------|
| α (Donchian long-only) | WEAK YES — parallel synthetic track | 7th hypothesis, N_trials=5 DSR penalty, no prior PASS, ~280 LoC, orthogonal paradigm, long-only FSM compatible |
| β (pause v0.7) | CONDITIONAL YES — valid if investment horizon exhausted | 33 sprints, infrastructure mature. Revive if market structure changes OR 3+ more years of data available. |
| γ (extend data try b) | NO — PERMANENTLY CLOSED | n_eff 37-41 < 50 with FULL extension = structural impossibility. Running would waste 1-2 sprints confirming known projection. Bailey 2014 discipline prohibits. |
| δ (TESTNET live demo) | YES — PRIMARY | S12 infrastructure exists. S17+S22 MC p≤0.02 partial PASS = best available evidence. Forward real-time accumulation bypasses T5 structural problem. 85-95 real trades in 12M exceeds T5=50 floor. TESTNET only — no capital risk. |
| ε (pairs/stat arb) | NO — DEFER to v0.8+ | S33 rho=0.75 is NEGATIVE for pairs arb (low spread variance). ~400 LoC + zero prior evidence + N_trials=1. Wrong sequencing. |
| ζ (risk management refactor) | YES — complement bundled into S35 | ~200 LoC. Dynamic Kelly, ATR-based SL calibration. Applies regardless of primary direction. |

## ROUND 3 binding decision
**Primary: δ (TESTNET live demo)**
**Parallel: α (Donchian 4H long-only) — synthetic gates**
**Complement: ζ (risk management refactor) — S35 bundled**
**Failure branch: β (pause) if both δ drawdown ≥15% AND α FAIL within S35-S36 window**

## S35+ plan
- T1: ζ risk management refactor (Kelly 0.25× cap, ATR SL calibration, ~200 LoC)
- T2: δ TESTNET activation (halt criteria ADR, trade log protocol, FillRecorder validation)
- T3: α Donchian ADR pre-registration (N_trials=5 explicit, parameters locked before data)
- T4: α Donchian implementation + backtest run (~280 LoC)
- T5: Results reconcile (δ first-month + α synthetic verdict)

## 8 pre-commitments (ROUND 3 BINDING)
1. δ is TESTNET ONLY. No MAINNET until 12-month TESTNET evidence reviewed by operator.
2. Position sizing: Kelly 0.25× cap + ζ refactor applied BEFORE any live run.
3. α Donchian N_trials=5 declared in ADR before any code.
4. α Donchian parameters pre-registered before data inspection. No post-hoc tuning.
5. Halt criteria for δ: ≥5 consecutive losing trades OR ≥15% equity drawdown → TESTNET halt, operator review.
6. γ (extend data try b) is PERMANENTLY CLOSED.
7. ε (pairs/stat arb) deferred to v0.8+. Not in S35-S37 scope.
8. β (pause) remains valid operator option at any point — no coercion to continue.

## Supersession note
ROUND 2 binding was "(b) primary, (c) failure branch" — contingent on data audit showing n_eff≥50 reachable. Audit delivered opposite. This ROUND 3 supersedes ROUND 2 per my own pre-condition trigger. The pivot from (b) to δ is not a preference change — it is mathematical closure of (b).

**Why δ is epistemically defensible:** Acceptance criteria were designed for historical synthetic validation. Forward real-time trades constitute a different measurement domain with genuine OOS independence (no look-ahead possibility). S17+S22 MC p≤0.02 justifies the experiment. TESTNET = no capital risk.
