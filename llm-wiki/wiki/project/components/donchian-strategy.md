---
title: DonchianBreakoutStrategy Component
type: component
tags: [component, signalgen, donchian, breakout, long-only, sprint-35, locked-pre-registration, ru]
created: 2026-04-27
updated: 2026-04-27
status: failed-validation
sources:
  - src/signalgen/donchian_strategy.py
  - src/backtest/donchian_runner.py
  - project/decisions/0054-sprint-35-donchian-pre-registration.md
  - data/donchian_backtest_results.json
---

# DonchianBreakoutStrategy

**TL;DR:** Long-only Donchian breakout strategy (S35 α track per ADR 0054 LOCKED). Backtest verdict S35 = **FAIL conjoint** (n=21<<50, aggregate Sharpe=-0.95, DSR<<0.95, 4/6 acceptance gates fail). α direction CLOSED per ADR 0054 pre-commit #8.

## Назначение

Pre-registered 7th hypothesis (N_trials=5 cumulative: S13/S15/S17/S22/S35) per ADR 0054 — orthogonal paradigm к mean-reversion. Anti-snooping locked params + symbol + timeframe BEFORE backtest run.

## LOCKED-параметры (`DONCHIAN_LONG_ONLY_PARAMS`)

| Param | Value | Justification |
|-------|-------|---------------|
| `lookback_n` | 20 | Classical Donchian (Faber 2007) |
| `exit_lookback_n` | 10 | Half-period exit (Turtle Trading) |
| `atr_period` | 14 | Wilder ATR consistent с indicators.atr() |
| `atr_stop_mult` | 2.0 | 2× ATR stop |
| `signal_side_mode` | "long_only" | FSM SignalSide invariant |

Symbol: BTCUSDT, Timeframe: 4H. **DO NOT modify без new ADR (anti-snooping).**

## Публичный API

- `DonchianBreakoutStrategy.__init__(*, symbol, lookback_n, exit_lookback_n, atr_period, atr_stop_mult)` — keyword-only
- `DonchianBreakoutStrategy.warmup(bar)` — feed historical bars без signal emission
- `DonchianBreakoutStrategy.on_bar(bar) -> Signal | None` — main entry point per bar

## Логика входа/выхода

**Entry (LONG):** close(T) > max(high[T-lookback_n:T]) AND current_side == FLAT
**Exit (FLAT) from LONG:** EITHER:
- close(T) < min(low[T-exit_lookback_n:T]) — channel exit
- close(T) < entry_close - atr_stop_mult × ATR(T) — ATR stop

## S35 Backtest result

Per `data/donchian_backtest_results.json`:

| Gate | S35 actual | Threshold | Pass? |
|------|------------|-----------|-------|
| n_trades raw | 21 | ≥ 50 | ❌ |
| n_eff (single-symbol) | 21 | ≥ 50 | ❌ |
| Aggregate OOS Sharpe | -0.95 | ≥ 0.7 | ❌ |
| MC p-value | 0.014 | ≤ 0.05 | ✅ |
| DSR (N=5) | 1.57e-37 | ≥ 0.95 | ❌ |
| Per-fold Sharpe gate | 1/5 PASS | all ≥ 0.7 | ❌ |

**FAIL conjoint** (4/6 gates fail). Per-fold Sharpe ratios: [-4.96, -4.25, -0.54, +6.26, -1.25].

cross_trial_sharpes.json **NOT appended** per ADR 0052 Item #10 protocol (a) (failed trials tracked separately).

## Известные ограничения (S35 T4 reviewer findings)

1. **Channel exit not exercised в backtest replay path** — `src/backtest/indicators.py` `donchian` branch implements ATR stop only; OOP class implements both ATR + channel exit. Verdict robust к gap (n=21<<50 fail unaffected by exit semantics — adding channel exit increases trade count, doesn't decrease).
2. **DSR sigma_SR fallback** к per-fold OOS Sharpe stdev (4.45) когда cross_trial empty — conservative, doesn't flip verdict но methodology gap. S36+ ADR amendment recommended (DSR=NaN with `dsr_status="insufficient_cross_trial_data"` flag).
3. **Reason codes free-form strings** — `ENTRY_LONG_DONCHIAN_BREAKOUT` / `EXIT_FLAT_ATR_STOP` / `EXIT_FLAT_CHANNEL` not yet в ReasonCode enum (45). Required для live runtime activation. Currently не blocking (α CLOSED, code не runs prod).

## Связанные

- [[../decisions/0054-sprint-35-donchian-pre-registration]] — LOCKED params + acceptance gates ADR
- [[../decisions/0052-sprint-34-acceptance-criteria-amendment]] — gate thresholds source
- [[../sprints/sprint-35-testnet-donchian-risk]] — sprint context
- `src/signalgen/mean_reversion_strategy.py` — sister long-only strategy (S22 partial PASS evidence)
- [[strategy]] — sister EMA-crossover strategy (same FSM SignalSide + on_bar contract)
- [[indicators]] — ATR computation shared via `indicators.atr()` (Wilder, period=14)
- [[sizing]] — ATR-based position sizing via `compute_qty` (same formula, atr_stop_mult=2.0)
