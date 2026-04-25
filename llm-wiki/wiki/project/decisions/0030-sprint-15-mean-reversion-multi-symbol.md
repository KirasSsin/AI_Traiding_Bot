---
title: 0030. Sprint 15 — Mean-reversion strategy + multi-symbol (BTC/ETH/SOL) v0.2 retry
type: decision
date: 2026-04-26
sprint: 15
tags: [adr, sprint-15, v0.2-retry, mean-reversion, multi-symbol, bollinger-bands, dsr-cross-trial, option-b]
sources:
  - project/pre-s15-backlog.md
  - project/decisions/0029-sprint-14-honest-close.md
  - project/decisions/0028-sprint-13-strategy-validation.md
  - project/decisions/0016-bybit-spot-supersedes-binance.md
  - project/decisions/0022-execution-state-single-writer.md
  - project/architecture/acceptance-criteria.md
status: accepted
---

# 0030. Sprint 15 — Mean-reversion strategy + multi-symbol (BTC/ETH/SOL) v0.2 retry

**Status:** accepted
**Date:** 2026-04-26

## Context

S14 closed v0.1 honest (verdict NEGATIVE, T5 ≥100 trades structurally unreachable for EMA crossover на 1H BTC). Per S14 ADR 0029: future direction options A/B/C/D deferred к operator. Operator chose v0.2 retry path.

S15 PHASE 2 brainstorming (4 questions, see `pre-s15-backlog.md`):
- Q1 most economical retry strategy → trader REVISE-ADDITIVE (mean-reversion correct, NEW class, DSR cross-trial T0)
- Q2 multi-symbol viable → trader CONFIRM + architecture APPROVE_WITH_CONDITIONS (Coordinator-per-symbol replication, `load_recent` BLOCKER)
- Q3 15M timeframe → REVISE-material (architectural blockers identified) → DEFERRED к S16+
- Q4 ML XGBoost → CONFIRM defer к v0.3+

**ESC-1 resolution (combination):** Both trader + architecture recommend Option B (Q1+Q2 = mean-reversion 1H × 3 symbols).

**ESC-2 resolution (RSI threshold pre-registration):** Conservative AND-gated trigger pre-registered binding для S15.

## Decision

### S15 scope: Mean-reversion (RSI + Bollinger Bands) на 1H × 3 symbols

**v0.2 strategy hypothesis:** mean-reversion на crypto 1H bars (BTC/ETH/SOL) achieves T5 ≥100 trades floor через combination of:
- Higher base signal frequency (mean-reversion: ~1 trade per 2-5 days vs EMA crossover: ~1 per 5-10 days)
- 3x aggregation across 3 Bybit Spot symbols (~75-125 OOS trades estimate)

### Pre-registered strategy parameters (BINDING — no post-result tuning)

```
Strategy class: MeanReversionRsiBBStrategy (NEW, src/signalgen/mean_reversion_strategy.py)

LONG entry condition:
    RSI(14) < 30 AND close < lower_BB(20, 2σ)

EXIT condition (any of):
    RSI(14) > 70
    OR close > upper_BB(20, 2σ)
    OR ATR(14) trailing stop hit
    OR signal flip (next entry trigger inverted)

Indicators:
    RSI(14) — existing src/signalgen/indicators.py:47 (Wilder, ADR 0011)
    BB(20, 2σ) — NEW (close.rolling(20).mean() ± 2 * close.rolling(20).std())
    ATR(14) — existing (Wilder, ADR 0011)

Symbols (3): BTCUSDT, ETHUSDT, SOLUSDT (all Bybit Spot per ADR 0016)
Timeframe: 1H (per ADR 0005, no amendment)
WFA params: K=5, train=2000, test=500, embargo=20 (per ADR 0014, unchanged)
```

### S15 deliverables

**T0 (BLOCKING prereq): DSR cross-trial sigma_SR fix**
- Implement persistent cross-trial Sharpe log (JSON or DB row)
- Load S13 anchor Sharpe = -44.46 as trial #1
- Modify `src/__main__.py:443`: `compute_dsr(n_trials=2, sigma_sr=std([-44.46, S15_sharpe]))`
- Address S14 Q2 REVISE carry-over (Bailey eq. 13 cross-trial)

**T1: TradeHistory `load_recent` symbol filter (HIGH BLOCKER)**
- `src/risk/trade_history.py:85-93` add `symbol: str | None = None` param
- Emit `AND symbol = ?` predicate when set
- `RiskManager._compute_pb` passes `symbol=self._symbol`
- Prevents Kelly contamination across symbols (ETH wins inflate BTC Kelly etc)

**T2: NEW MeanReversionRsiBBStrategy class**
- `src/signalgen/mean_reversion_strategy.py` (new file)
- BB(20, 2σ) implementation (pandas rolling, no new TA-Lib func)
- RSI<30 + close<lower_BB AND-gated entry
- RSI>70 OR close>upper_BB OR ATR-stop EXIT
- Implements existing `Strategy` protocol (drop-in replacement)
- Pre-registered params hardcoded (NOT operator-tunable for S15)

**T3: Multi-symbol DI fan-out**
- `src/__main__.py::_cmd_run` accept `--symbols` CLI arg (comma-separated, default = "BTCUSDT")
- Instantiate N independent Coordinator + RiskManager + ExecutionStateRepo per symbol
- Thread management: N threads OR sequential tick loop (architecture-reviewer suggested sequential per Coordinator simplicity)
- Shutdown handler joins all coordinators

**T4: Multi-symbol backfill + WFA wiring**
- `_cmd_backfill --symbols BTCUSDT,ETHUSDT,SOLUSDT` loops backfill per symbol
- Bybit V5 historical kline fetch для ETHUSDT + SOLUSDT (verify start dates ≥ 2021-07-02)
- `_cmd_wfa --symbols BTCUSDT,ETHUSDT,SOLUSDT` aggregates per-symbol WFA results
- Aggregate trade list across symbols for T1-T6 + DSR computation

**T5: Measurement run + verdict**
- Backfill 3 symbols × 4.81y (or available range)
- WFA run aggregated trade list
- T1-T6 verdict (PASS / FAIL per acceptance-criteria.md)
- DSR cross-trial с S13 anchor

**T6: ADR 0030 (this file) + sprint-15 page + wiki sync**

### Cross-cutting concerns (binding)

- **CC1 (T5 floor honesty):** S15 expected ~75-125 OOS trades. T5 borderline. If FAIL → S16 considers Q3 (15M) OR widens RSI thresholds. NO post-result tuning в S15 itself (pre-registration discipline per S13 Q5 CONFIRM)
- **CC2 (DSR multi-testing penalty):** N_trials=2 with sigma_SR = std([-44.46, S15_sharpe]). Severe penalty unless S15 Sharpe dramatically positive (≥+15). Operator aware: each measurement burns DSR budget
- **CC3 (Capital allocation):** Per-symbol Kelly with `load_recent` symbol filter (T1) = natural per-symbol sizing. NO new ADR for cross-symbol exposure caps в S15 — defer к v0.3 if multi-symbol production desired
- **CC4 (ADR 0022 single-writer):** Coordinator-per-symbol replication PRESERVES per-symbol single-writer invariant. Each Coordinator instance holds own RLock. No invariant violation
- **CC5 (Q3 deferred):** 15M timeframe NOT в S15 scope. interval_map + heal_max_age_seconds blockers identified by trader/architecture deferred к S16+ if S15 fails T5
- **CC6 (Q4 deferred):** ML XGBoost NOT в S15 scope. Defer к v0.3+ pending evidence of edge from simpler strategy attempts
- **CC7 (Honest close fallback):** Если S15 verdict=FAIL → operator chooses S16 direction (Q3 15M, broader RSI thresholds, OR honest close v0.2). Pre-commit: max 1 strategy variant per sprint (no p-hacking iteration)

### Acceptance criteria (immutable per S14)

T1-T6 thresholds preserved per `acceptance-criteria.md`. NO spec amendment. S15 = empirical measurement with new strategy hypothesis.

## Consequences

**Plus:**
- Empirical retry с new strategy hypothesis (mean-reversion, theoretically supported для crypto 1H per Hudson & Urquhart 2021)
- 3x signal aggregation directly addresses S14 T5 unreachability constraint
- Bounded architectural changes (replication pattern, не refactor)
- DSR cross-trial fix unblocks future tuning iterations (statistically valid multi-trial measurements)
- Kelly contamination fix (`load_recent`) enables correct per-symbol sizing
- Reuses 95% of v0.1 infrastructure (FSM, execution, risk, backtest pipeline)

**Minus:**
- N_trials=2 DSR penalty severe (-44.46 anchor) — S15 Sharpe must be dramatically positive к pass DSR
- Mean-reversion fails в strong trending regimes (opposite failure mode of EMA crossover)
- T5 borderline expected (~75-125 trades) — может still fail if ETH/SOL data start later than BTC's 2021-07-02
- Pre-registered RSI 30/70 thresholds may be too restrictive (prior S13 Q5 trader concern about wider thresholds)
- Multi-symbol adds capital allocation question (deferred но real)

**v0.3+ carry-overs (deferred):**
- Q3 15M timeframe (interval_map + heal_max_age_seconds fixes)
- Q4 ML XGBoost (CPCV framework + feature engineering pipeline)
- Cross-symbol capital allocation ADR (if multi-symbol production)
- Live demo Mainnet validation (S12 carry-over, never run since 33min)
- FillRecorderAdapter Layer 2 schema link
- 3-way endpoint enum (DEMO/TESTNET/MAINNET)

## Related

- [[../pre-s15-backlog]] — PHASE 2 verdicts trail
- [[0029-sprint-14-honest-close]] — S14 honest close (T5 unreachability constraint inherited)
- [[0028-sprint-13-strategy-validation]] — S13 measurement (-44.46 Sharpe anchor для DSR)
- [[0016-bybit-spot-supersedes-binance]] — venue policy (multi-symbol compatible)
- [[0022-execution-state-single-writer]] — single-writer invariant (preserved under replication)
- [[0011-indicators-wilder-classical]] — RSI/ATR Wilder formulas (reused)
- [[0014-walk-forward-analysis]] — WFA params (unchanged)
- [[0005-1h-timeframe-mvp]] — 1H baseline (no amendment в S15)
- [[../architecture/acceptance-criteria]] — T1-T6 thresholds (immutable)

## Amendments

- (none yet)
