---
title: ADR 0054 — Sprint 35 α Donchian Breakout Pre-Registration LOCKED
type: decision
tags: [adr, sprint-35, donchian, breakout, long-only, pre-registration, n-trials-5, locked]
created: 2026-04-27
updated: 2026-04-27
status: accepted
sources:
  - project/decisions/0052-sprint-34-acceptance-criteria-amendment.md
  - project/decisions/0053-sprint-35-testnet-live-demo.md
  - project/pre-s35-backlog.md
---

# ADR 0054 — Sprint 35 α Donchian Breakout Pre-Registration LOCKED

## Status

Accepted (2026-04-27) **BEFORE** any backtest data inspection — anti-snooping discipline per Bailey & López de Prado 2014.

## Context

ROUND 3 consilium voted α (Donchian breakout) as parallel synthetic track:
- 7th hypothesis tested across project lifetime (N_trials counter pooled = 5)
- Orthogonal paradigm к mean-reversion (trend-following breakout)
- Long-only FSM-compatible (no SHORT signals — `long_only=True` invariant per ADR 0009)
- ~280 LoC scope estimate

DSR penalty при N_trials=5 calculated per Bailey 2014 sigma_SR pooling protocol (a) — significant но not prohibitive.

## Decision

Implement Donchian breakout long-only strategy с LOCKED parameters BEFORE backtest run.

### LOCKED Parameters (`DONCHIAN_LONG_ONLY_PARAMS`)

| Param | Value | Justification |
|-------|-------|---------------|
| `lookback_n` | 20 | Classical Donchian (Faber 2007) standard period |
| `exit_lookback_n` | 10 | Half-period exit (Turtle Trading variant) |
| `atr_period` | 14 | Standard Wilder ATR consistent с indicators.atr() |
| `atr_stop_mult` | 2.0 | 2× ATR trailing stop (volatility-adjusted) |
| `signal_side_mode` | "long_only" | FSM SignalSide invariant (no SHORT) |
| `min_atr_filter` | None | No volatility floor — accept all breakouts |

### Symbol + Timeframe LOCKED

- Symbol: BTCUSDT (single-symbol — bypasses correlation deflation per S33 lesson)
- Timeframe: 4H (consistent с δ track для apples-to-apples comparison)

### N_trials Counter

| Sprint | Trials accumulated | Strategy |
|--------|-------------------|----------|
| S13 | 1 | EMA crossover |
| S15 | 2 | Mean-reversion strict |
| S17 | 3 | Mean-reversion relaxed |
| S22 | 4 | Mean-reversion 4H |
| **S35 α** | **5** | **Donchian breakout** |

DSR penalty при N_trials=5: `sigma_SR_pooled = sqrt((1/N) * sum(sharpe_i²))`. Bonferroni alpha-adjusted threshold per Bailey 2014.

### 6 Pre-Committed Acceptance Gates (verbatim per ADR 0052 amended LOCKED)

| Gate | Threshold | Block? |
|------|-----------|--------|
| T5 n_trades raw | >= 50 | YES |
| T5 n_eff (single-symbol → n_eff = n_raw) | >= 50 | YES |
| T6 OOS/IS Sharpe | >= 0.7 | YES |
| MC p-value | <= 0.05 | YES |
| DSR (N_trials=5) | >= 0.95 | YES |
| acceptance_gate.sharpe_gate_passed | per-fold >= 0.7 | YES |

PASS = ALL gates conjoint AND. FAIL conjoint = α direction CLOSED, β fallback (pause) per pre-commit #8.

### NOT permitted без new ADR

- ❌ Post-hoc parameter tuning (snooping)
- ❌ SHORT signals (FSM long_only invariant)
- ❌ Multi-symbol (single-symbol BTCUSDT LOCKED)
- ❌ Different timeframe (4H LOCKED)
- ❌ Reuse OHLCV data вне pre-registered range

## Consequences

**Positive:** Anti-snooping LOCKED before data touch. N_trials properly counted (=5). Long-only FSM-compatible — no engineering blocker.

**Negative:** DSR penalty при N=5 raises threshold harder than N=4. If FAIL → α direction PERMANENTLY CLOSED.

**Neutral:** No production trading impact (synthetic backtest only).

## Related

- ADR 0052 (S34 amendment LOCKED — gates source)
- ADR 0053 (S35 δ TESTNET — paired primary track)
- pre-s35-backlog.md (ROUND 3 binding)
