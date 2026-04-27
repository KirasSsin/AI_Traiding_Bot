---
title: ADR 0053 — Sprint 35 δ TESTNET Live Demo Activation
type: decision
tags: [adr, sprint-35, testnet-demo, live-demo, halt-criteria, mean-reversion-s17, locked-pre-registration]
created: 2026-04-27
updated: 2026-04-27
status: accepted
sources:
  - project/decisions/0051-sprint-34-honest-close-v06.md
  - project/decisions/0052-sprint-34-acceptance-criteria-amendment.md
  - project/pre-s35-backlog.md
---

# ADR 0053 — Sprint 35 δ TESTNET Live Demo Activation

## Status

Accepted (2026-04-27) — implemented в S35 (`feature/sprint-35-testnet-donchian-risk` → tag `v0.1.0-alpha.35`).

## Context

Post-S34 hybrid (ADR 0051 honest close v0.6 + ADR 0052 amendment LOCKED). Data audit projection: n_eff = 37-41 < 50 amended threshold даже с full Bybit history extension (4.81y). Option (b) backtest-based new measurement = STRUCTURAL IMPOSSIBILITY.

ROUND 3 consilium (3 agents CONSENSUS) → δ (TESTNET live demo) primary. Forward real-time accumulation bypasses T5 structural problem; S17+S22 MC p ≤ 0.02 partial PASS = best available evidence.

## Operator Acknowledgment (verbatim per ADR 0052)

> Statistical evidence as of v0.6 DOES NOT support live deployment; this amendment
> reflects crypto-specific sample-size reality (Hudson & Urquhart 2021), not
> evidence of positive edge. I authorize TESTNET-only live demo using S22-validated
> mean-reversion strategy with halt criteria pre-committed. No real capital.
> n_trials counter remains frozen per Item #10.

## Decision

Activate δ TESTNET live demo с pre-committed gates + halt criteria LOCKED.

### LOCKED Parameters

- Strategy: `MeanReversionRsiBBStrategy` + `MEAN_REVERSION_S17_RELAXED_PARAMS`
- Symbol: BTCUSDT only (single-symbol bypasses correlation deflation)
- Timeframe: 4H (S22 validated)
- Capital: TESTNET only (zero MAINNET — `live_trading=False` invariant)
- N_trials: frozen (uses S22-validated, no new hypothesis)

### Pre-committed PASS gates

| Gate | Threshold | Source |
|------|-----------|--------|
| n trades | ≥ 50 | ADR 0052 amended T5 floor |
| Sharpe | ≥ 0.7 | T6 unchanged |
| Win rate | ≥ 40% | mean-reversion baseline |
| Max DD | ≤ 30% | risk management |
| MC p-value | ≤ 0.05 | ADR 0052 tightened |
| DSR | ≥ 0.95 | T2 unchanged |

### Pre-committed HALT criteria (HaltGate enforced)

- DD ≥ -20% intraday → halt + S36 honest close
- DD ≥ -15% multi-day → halt + S36 honest close
- ≥ 5 consecutive losing trades → operator review
- ≥ 6 months без n ≥ 30 closed trades → halt + S36 honest close

### NOT permitted без new ADR

- ❌ Switch к MAINNET (LOCKED через model_validator + invariant test)
- ❌ Change strategy params (MEAN_REVERSION_S17_RELAXED_PARAMS LOCKED)
- ❌ Multi-symbol (single-symbol BTCUSDT LOCKED — correlation deflation falsified)
- ❌ Lower halt thresholds without S36+ ADR с explicit override

## Consequences

**Positive:** Forward real-time accumulation bypasses T5 structural backtest problem. Halt criteria pre-committed (anti-snooping). 12-month review window allows accumulating ≥ 50 trades natural rate.

**Negative:** Zero MAINNET evidence accumulates. TESTNET fills may differ от mainnet liquidity profile. 6-month no-trade timeout may trigger early halt если signal-frequency assumptions wrong.

**Neutral:** No code regression — all existing tests preserved. HaltGate gated по `s35_demo_active=False` default.

## Related

- ADR 0051 (S34 6-th honest close v0.6)
- ADR 0052 (S34 acceptance-criteria amendment LOCKED)
- ADR 0054 (S35 Donchian pre-registration — paired α track)
- pre-s35-backlog.md (ROUND 3 binding consilium trail)
