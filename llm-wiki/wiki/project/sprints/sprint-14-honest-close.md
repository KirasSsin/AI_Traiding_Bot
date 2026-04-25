---
title: Sprint 14 — Honest close (no-edge verdict, v0.1 infrastructure milestone)
type: sprint
tags: [sprint-14, honest-close, no-edge-verdict, v0.1-milestone, mvp-incomplete-honest]
created: 2026-04-26
updated: 2026-04-26
status: completed
sources:
  - project/decisions/0029-sprint-14-honest-close.md
  - project/pre-s14-backlog.md
  - project/sprints/sprint-13-backfill-wfa.md
---

# Sprint 14 — Honest close

## Overview

S14 = honest close ship. Following S13 verdict=FAIL (4/6 criteria failed, 20 OOS trades). PHASE 2 brainstorming surfaced 2 critical issues:

1. **T5 ≥100 trades structurally unreachable** (trader Q1 EXPAND, math verified): EMA crossover на 1H BTC fires ~1 trade per 5-10 days; T5 needs ~1 trade per day = **5x signal frequency gap**. Tuning realistically 2-3x. Не reachable.
2. **DSR cross-trial sigma_SR gap** (trader Q2 REVISE): N_trials=2 needs cross-trial sigma_SR per Bailey eq. 13. Currently `dsr.py` only computes cross-fold (within single run). Real engineering gap.

User chose Option B (skip Option A theatrical re-measurement). S14 = documentation + ship close.

## Final v0.1 status

- **Infrastructure: ✅ COMPLETE** — 16 FSM states / 30 events / 74 transitions / 45 reason codes / 38 component pages / 28 ADRs (29 with this sprint) / 16 sprint pages
- **Strategy validation: ❌ NEGATIVE** — EMA(12)×EMA(26) + ADX(14) + RSI(14) + ATR(14) на 1H BTCUSDT = no measurable edge across 2 measurements
- **MVP DONE per acceptance-criteria.md: NOT achieved** (T5 unreachable for chosen strategy + timeframe)
- **Mainnet exposure: 0** (33min Bybit demo only, no live trading)
- **Tag: `v0.1.0-alpha.14`** = honest close marker, NOT MVP DONE

## Plan / ADR links

- [[../decisions/0029-sprint-14-honest-close]] — Sprint 14 ADR (honest close decision + future direction options)
- [[../pre-s14-backlog]] — PHASE 2 verdicts trail с trader Q1+Q2 source claims verified
- [[sprint-13-backfill-wfa]] — predecessor (verdict=FAIL trigger)

## Deliverables

S14 = documentation only. NO new code. NO measurement re-run.

- T1 (this sprint): ADR 0029 status accepted (already drafted в this sprint pre-ship)
- T2 (this sprint): sprint-14 page created (this document)
- T3: wiki sync (current-state.md + index.md + mental-map.md + counts ADR 28→29, sprint pages 15→16)
- T4: log.md sprint-end entry
- T5: SPRINT_STATE → between-sprints с post-MVP-honest-close status
- T6: PHASE 8 ship via sprint-finish skill (tag v0.1.0-alpha.14)

## FSM growth

NONE. S14 = documentation only. Counts unchanged: 16/30/74/45.

## Reason codes growth

NONE.

## Tests / quality

NO code changes. Existing test suite preserved at S13 baseline:
- pytest unit: 712 passed (baseline preserved, no new tests, no regressions)
- mypy --strict src/: clean (69 source files)
- ruff: clean
- Q7-S12 zero-migration: trivially preserved (no migrations changed)

## Strategy validation summary

### Two empirical measurements (both FAIL)

| Measurement | Data span | OOS trades | T1 Sharpe | T5 status | Verdict |
|-------------|-----------|------------|-----------|-----------|---------|
| Prior S13 attempt (aborted, knowledge preserved) | 2.2y (existing Parquet) | 20 | -44.46 | FAIL (n<100) | HARD_FAIL |
| S13 actual ship measurement | 4.81y (Bybit backfill) | 20 | -44.46 | FAIL (n<100) | FAIL |

**Critical insight:** Sample size NOT data-span-bounded. 2.2y vs 4.81y → identical 20 OOS trades. Strategy fires ~1 trade per 5-10 days regardless of data span. T5 floor structural limit для EMA crossover на 1H BTC.

### T5 unreachability math (trader Q1 EXPAND, verified)

```
WFA K=5 folds × 500 OOS bars/fold = 2500 OOS bars total
T5 ≥100 trades requirement:
  100 trades / 2500 bars = 1 trade per 25 bars (~1 trade per day на 1H)
S13 measured: 20 trades / 2500 bars = 1 trade per 125 bars (~1 trade per 5.2 days)
Gap: 5x signal frequency increase needed
EMA crossover + tuning realistic: 2-3x → ~50-70 trades (still < 100)
```

**Conclusion:** T5 ≥100 trades not achievable с EMA crossover на 1H BTC regardless of parameter tuning.

### DSR cross-trial gap (trader Q2 REVISE, verified)

`src/analytics/dsr.py:73`: `sigma_sr = std([fold_sharpe_1, ..., fold_sharpe_K])` — cross-FOLD только.

Bailey & López de Prado eq. 13 для N_trials=2 needs cross-TRIAL std: `std([S13_Sharpe, S14_Sharpe])`. Not implemented.

**Implication:** Any future tuning iteration (S15+) needs DSR cross-trial sigma_SR implementation OR documented caveat.

## Wiki updates

- 1 NEW ADR (0029 — accepted)
- 1 NEW sprint page (this — sprint-14-honest-close)
- 1 NEW backlog (pre-s14-backlog.md committed earlier)
- Modified: current-state.md (TL;DR post-S14, ADR 28→29, sprint pages 15→16, +S14 row), index.md (sprint-14 + ADR 0029), mental-map.md (project status row), log.md (sprint-end), SPRINT_STATE (between-sprints, tag alpha.14)

## Open issues для v0.2+ (operator-driven, no S15 commitment)

**Future direction options (deferred — operator decides if/when):**

### (A) Strategy revision (different family)
- Mean-reversion (RSI extreme + Bollinger Bands)
- Regime-switch (HMM detection on volatility)
- ML-driven (XGBoost classifier per pre-S1 Mimo bot reference)
- Cost: 3-5 sprints + new validation cycle (each new strategy = own N_trials count)

### (B) Multi-symbol expansion (same strategy)
- Add ETHUSDT + SOLUSDT venue support
- Aggregated signal frequency ~3x (~60 trades estimated)
- Cost: 2-3 sprints, scope expansion vs v0.1 single-symbol baseline
- Risk: still может not reach T5 ≥100 floor

### (C) Different timeframe (15M или 4H)
- 15M = 4x signal frequency, но noisier (potentially worse edge)
- 4H = lower frequency но cleaner trend signals
- Cost: 1-2 sprints, ADR 0005 amendment needed

### (D) Project pause (current)
- Close current branch, freeze repo as "v0.1 infrastructure milestone"
- Reactivate if new strategy candidate emerges
- Cost: 0 sprints, current state

### Carry-overs preserved (all S12 + S13 unaddressed)

10+ items still open:
- F live demo Mainnet validation actual run (33min only since S12)
- FillRecorderAdapter Layer 2 schema link (entry_signal_id к execution_state)
- 3-way endpoint enum (DEMO/TESTNET/MAINNET)
- T2 review C3 init_db dual-conn comment
- DSR per-fold DataFrame→TradeRecord conversion (S10 informational)
- DSR threshold calibration (S15+ per S11 Q5)
- DSR cross-trial sigma_SR implementation (S14 Q2 REVISE)
- halt_log INSERT order swap в `_set_halt`
- find_by_order_id ORDER BY explicit
- fill-history.md / bybit-adapter.md / ws-private-consumer.md component page updates
- T2/T5/T6 quant-stats deferred concerns (Sortino formula docs, sqrt(8760) frequency-agnostic, boundary tests)
- 48h Bybit demo validation (operator-driven)

## Key decisions

- **Q1 EXPAND** (trader): T5 structurally unreachable — verified via grep S13 measurement
- **Q2 REVISE** (trader): DSR cross-trial sigma_SR gap — verified via dsr.py:73 source
- **Q3 CONFIRM** (trader): strict formula PASS, no operator override
- **Q4 CONFIRM** (trader): Settings config wiring (moot per Option B)
- **Q5 CONFIRM** (trader): pre-commit FAIL fallthrough — honored, Option B invoked
- **User Option B**: honest close immediately, save 1 sprint vs theatrical Option A
- **Tag semantics:** `v0.1.0-alpha.14` = honest close marker, NOT MVP DONE
- **No spec amendment:** acceptance-criteria.md T1-T6 thresholds preserved
- **No code changes:** S14 = documentation only

## Related

- [[../decisions/0029-sprint-14-honest-close]] — S14 ADR
- [[../pre-s14-backlog]] — PHASE 2 verdicts trail
- [[../sprints/sprint-13-backfill-wfa]] — predecessor (verdict=FAIL trigger)
- [[../sprints/sprint-12-live-demo-validation]] — pre-S13 (live demo infrastructure)
- [[../architecture/acceptance-criteria]] — 12 gating criteria (immutable)
- [[../architecture/migration-plan]] — original roadmap (closed at S14 honest)
