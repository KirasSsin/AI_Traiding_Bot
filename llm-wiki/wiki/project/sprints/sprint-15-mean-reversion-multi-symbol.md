---
title: Sprint 15 — Mean-reversion strategy + multi-symbol BTC/ETH/SOL (v0.2 retry)
type: sprint
tags: [sprint-15, v0.2-retry, mean-reversion, bollinger-bands, multi-symbol, dsr-cross-trial, verdict-fail-with-progress]
created: 2026-04-26
updated: 2026-04-26
status: completed
sources:
  - project/decisions/0030-sprint-15-mean-reversion-multi-symbol.md
  - project/pre-s15-backlog.md
  - project/sprints/sprint-14-honest-close.md
---

# Sprint 15 — Mean-reversion + multi-symbol (v0.2 retry attempt #1)

## Overview

S15 = first v0.2 retry attempt after S14 honest close. Per ADR 0030 + brainstorm Option B (trader+architecture concurrent recommendation): mean-reversion (RSI<30 AND close<lower_BB(20, 2σ)) AND-gated trigger × multi-symbol aggregation BTCUSDT+ETHUSDT+SOLUSDT на 1H Bybit Spot.

Pre-registered binding parameters (per ESC-2): RSI(14) thresholds 30/70, Bollinger Bands(20, 2σ), no operator override post-result. CrossTrialLog implementation (T0) closed S14 Q2 REVISE carry-over (Bailey eq. 13 cross-trial sigma_SR).

## Verdict

**FAIL (4/6 criteria failed: T5, T6, MC, DSR)** — но с **progress vs S13**: T5 ≥100 trades floor REACHED for first time (108 trades aggregate via 3-symbol).

| Criterion | Threshold | S13 (BTC EMA) | S15 (3sym MeanRev) | Status |
|-----------|-----------|---------------|---------------------|--------|
| T1 Sharpe OOS | ≥1.0 | -44.46 | **9.32** | PASS |
| T2 Sortino OOS | ≥1.5 | -101.38 | **29.55** | PASS |
| T3 MaxDD | <0.25 | 0.036 | **0.053** | PASS |
| T4 win/RR | RR≥2 → win≥35% | 30% / 0.797 | 37% / 2.27 | PASS |
| T5 n_trades | ≥100 + t_stat≥2 + mean_pnl>0 | 20 / -3.74 / -0.59% | 108 / 1.04 / +0.53% | **FAIL** (t_stat) |
| T6 OOS/IS sharpe ratio | ≥0.7 | mean(folds) | mean(folds) -12.38 | **FAIL** |
| MC p-value | ≤0.05 | 0.048 | 0.998 | **FAIL** |
| DSR | >0 | NaN (n_trials=1) | 0.0 (n_trials=2, σ_SR=22.68) | **FAIL** |

### Per-symbol breakdown (S15)

| Symbol | Trades | Mean OOS/IS Sharpe | MC p-value | Notes |
|--------|--------|---------------------|------------|-------|
| BTCUSDT | 44 | +1.75 | 0.197 | Best performer |
| ETHUSDT | 29 | -39.35 | 0.998 | One catastrophic fold drives mean |
| SOLUSDT | 35 | +0.45 | 0.65 | Modest performance |
| **Aggregate** | **108** | **-12.38** | **0.998** | Outlier-driven negative aggregate |

**Failure mode different from S13:** S13 = insufficient signals + negative PnL. S15 = enough signals + high-variance PnL + MC indistinguishable from random. T5 floor reached validates ADR 0030 multi-symbol aggregation hypothesis. Edge не demonstrated — но different unknowns surfaced.

## Plan / ADR links

- [[../decisions/0030-sprint-15-mean-reversion-multi-symbol]] — Sprint 15 ADR
- [[../pre-s15-backlog]] — PHASE 2 verdicts trail (trader-expert + architecture-reviewer Option B convergence)
- [[../plans/2026-04-26-sprint-15-mean-reversion-multi-symbol]] — implementation plan (8 TDD tasks)
- [[sprint-14-honest-close]] — predecessor (T5 unreachability constraint inherited)
- [[../decisions/0029-sprint-14-honest-close]] — S14 honest close ADR
- [[../decisions/0028-sprint-13-strategy-validation]] — S13 (-44.46 Sharpe anchor для DSR cross-trial)

## Deliverables

| Task | Description | Status |
|------|-------------|--------|
| T0 | CrossTrialLog persistent JSON (Bailey eq. 13 sigma_SR) — closes S14 Q2 carry-over | ✅ DONE (commit fc8c761) |
| T1 | TradeHistory.load_recent symbol filter — Kelly contamination fix (HIGH BLOCKER per architecture-reviewer Q2) | ✅ DONE (2d3ad70) |
| T2 | Bollinger Bands indicator (NEW, pure numpy, 9 unit tests) | ✅ DONE (d29e004) |
| T3 | MeanReversionRsiBBStrategy class (NEW, 11 unit tests, drop-in Strategy protocol) | ✅ DONE (0b43c10) |
| T4 | _cmd_run wires MeanReversion + symbol→RiskManager (live runtime kept single-symbol) | ✅ DONE (bf9031a) |
| T5 | Multi-symbol --symbols CLI for backfill+wfa, DSR cross-trial wiring, per-symbol JSON output | ✅ DONE (bf9031a) |
| T6 | tz-aware parquet filter fix + indicators.py mean_reversion branch + measurement run | ✅ DONE (ccfbf71) |
| T7 | Sprint-15 page + wiki sync + ADR/index/current-state/log/SPRINT_STATE | ✅ This commit |
| T8 | PHASE 8 ship via sprint-finish (PR + tag v0.1.0-alpha.15) | pending |

## FSM growth

NONE. S15 = strategy + analytics + CLI work. Counts unchanged: **16 states / 30 events / 74 transitions / 45 reason codes**.

## Reason codes growth

NONE. Mean-reversion entry/exit reasons reused string-based pattern (matches existing strategy.py free-form usage). Future ADR may formalize MEANREV reason codes.

## Tests / quality

| Layer | S14 baseline | S15 final | Delta |
|-------|--------------|-----------|-------|
| pytest unit | 712 passed | **732 passed**, 24 skipped | +20 (4 cross_trial_log + 3 trade_history + 9 BB + 11 MeanRev + others; some renames) |
| mypy --strict src/ | clean | **clean** (72 src files) | OK |
| ruff | clean | not re-checked | n/a |
| Q7-S12 zero-migration | preserved | **preserved** (no migrations changed) | OK |

## Key code changes

### NEW files

- `src/analytics/cross_trial_log.py` — JSON-backed trial Sharpe persistence (atomic tmp+rename)
- `src/signalgen/bollinger_bands.py` — BB(period, k) numpy impl (population stdev per Bollinger)
- `src/signalgen/mean_reversion_strategy.py` — drop-in Strategy с RSI+BB AND-gated trigger
- `tests/unit/test_cross_trial_log.py` (7 tests)
- `tests/unit/test_bollinger_bands.py` (9 tests)
- `tests/unit/test_mean_reversion_strategy.py` (11 tests)

### Modified files

- `src/risk/trade_history.py` — `load_recent(symbol=None)` adds optional filter
- `src/risk/manager.py` — `RiskManager(symbol=None)` constructor param + passthrough к `_compute_p_b`
- `src/__main__.py` — `--symbols` CLI arg для backfill+wfa, multi-symbol fan-out + aggregated DSR cross-trial; `_cmd_run` wires MeanReversion + symbol к RiskManager
- `src/runtime/manager.py` — `Strategy = EmaCrossover | MeanReversion` union
- `src/backtest/data_collector.py` — tz-aware date filter (fixes silent CSV fallback bug — root cause of identical-fold-sharpes-across-symbols в S15 first run)
- `src/backtest/indicators.py` — `cfg["strategy"]["type"]` dispatch (`ema_crossover` | `mean_reversion`)

## Wiki updates

- 1 NEW ADR (0030 — accepted)
- 1 NEW sprint page (this — sprint-15-mean-reversion-multi-symbol)
- 1 NEW backlog (pre-s15-backlog.md)
- 1 NEW plan (2026-04-26-sprint-15-mean-reversion-multi-symbol.md)
- Modified: current-state.md (TL;DR, ADR 29→30, sprint pages 16→17, +S15 row), index.md, log.md (sprint-end), SPRINT_STATE (between-sprints, tag alpha.15)

## Open issues для S16+ (operator-driven)

### S15 verdict-FAIL escalation (operator decides)

**Engineering options for S16 (per ADR 0030 CC7 honest close fallback):**

1. **(B') S15 retry с broader thresholds + variance reduction** — RSI 35/65 to dampen outlier folds, position sizing cap on per-fold Sharpe < -10. Risk: more trades = more N_trials = harsher DSR penalty (S13 + S15 + S16 = 3 trials).
2. **(C) Q3 15M timeframe** (per S15 backlog Q3 deferred) — 4x signal frequency. Architecture blockers identified S15 brainstorm: `interval_map` extension (`rest.py:66-67`), `heal_max_age_seconds` semantic refactor (`config.py:97-102`). Estimated 2 sprints.
3. **(D) Honest close v0.2** — accept 2 strategy attempts (EMA crossover S13 + Mean-reversion S15) both failed; freeze project as "infrastructure complete + 2 strategy hypotheses tested".
4. **(E) Q4 ML XGBoost (deferred к v0.3+ per ADR 0030 — confirmed by trader+architecture)** — only viable if simpler strategies show partial signal. S15 mean-reversion did NOT show partial signal (MC p=0.998 = random) → evidence для defer.

### Carry-overs preserved (S12 + S13 + S14)

All previous carry-overs remain open. New addition from S15:
- Multi-symbol live runtime fan-out (`_cmd_run` kept single-symbol; v0.2 needs threading model + per-symbol coordinators if Mainnet pursued)
- Capital allocation cross-symbol exposure caps (deferred per ADR 0030 CC3 — natural per-symbol Kelly was sufficient для S15 measurement scope)
- Q3 15M timeframe blockers (interval_map, heal_max_age_seconds) — surface blockers identified, fixes deferred

## Key decisions (S15 ADR 0030 + verdict)

- **ESC-1 Option B:** Q1+Q2 (mean-reversion 1H × 3 symbols) — both trader-expert + architecture-reviewer converged
- **ESC-2 pre-registered RSI 30/70 + BB(20, 2σ) AND-gated** — binding, no post-result tuning
- **CrossTrialLog implementation:** closes S14 Q2 REVISE carry-over (Bailey eq. 13 cross-trial sigma_SR)
- **Coordinator-per-symbol (replication, not refactor):** preserves ADR 0022 single-writer invariant — verified via architecture-reviewer
- **Q3 (15M) deferred к S16:** 2 hard blockers identified (interval_map KeyError, heal_max_age 1H coupling — production safety bug at 15M)
- **Q4 (ML) deferred к v0.3+:** confirmed by both reviewers (root cause = no edge, not signal noise)
- **Verdict honest:** FAIL but T5 reached for first time (108 trades). Different failure mode vs S13 = useful negative result. No spec amendment.
- **Scope honesty: live `_cmd_run` multi-symbol fan-out NOT implemented** (v0.1 has 0 Mainnet exposure → не critical; deferred к v0.2 production wave if any)

## Related

- [[../decisions/0030-sprint-15-mean-reversion-multi-symbol]] — S15 ADR
- [[../pre-s15-backlog]] — PHASE 2 verdicts (trader + architecture)
- [[../plans/2026-04-26-sprint-15-mean-reversion-multi-symbol]] — 8-task TDD plan
- [[sprint-14-honest-close]] — predecessor (T5 unreachability constraint)
- [[sprint-13-backfill-wfa]] — S13 measurement (-44.46 Sharpe anchor for DSR cross-trial)
- [[../architecture/acceptance-criteria]] — T1-T6 thresholds (immutable, not amended)
