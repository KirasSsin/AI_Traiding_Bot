---
title: 0029. Sprint 14 — Honest close (no-edge verdict, v0.1 infrastructure milestone)
type: decision
date: 2026-04-26
sprint: 14
tags: [adr, sprint-14, honest-close, no-edge, v0.1-milestone, mvp-incomplete, strategy-pivot-deferred]
sources:
  - project/pre-s14-backlog.md
  - project/decisions/0028-sprint-13-strategy-validation.md
  - project/sprints/sprint-13-backfill-wfa.md
  - project/architecture/acceptance-criteria.md
status: accepted
---

# 0029. Sprint 14 — Honest close (no-edge verdict, v0.1 infrastructure milestone)

**Status:** accepted
**Date:** 2026-04-26

## Контекст

Sprint 14 follows S13 verdict=FAIL on 4.81y BTCUSDT 1H Bybit Spot data (42098 bars). Per S13 ADR 0028 ESC-1=c (defer pattern preserved): operator decides next sprint scope case-by-case. User chose Option A (pre-registered tuning) initially.

PHASE 2 brainstorming (5 questions, trader-expert ROUND 1) surfaced 2 critical issues:

**Q1 EXPAND — T5 structurally unreachable:**
- S13 measured: 20 OOS trades / 2500 OOS bars = 1 trade per 5.2 days
- T5 threshold (≥100): 100 / 2500 = 1 trade per 25 bars (~1/day)
- Required signal frequency increase: **5x**
- EMA crossover + parameter tuning realistic: **2-3x** (50-70 trades estimate)
- Conclusion: T5 mathematically unreachable с EMA crossover на 1H BTC regardless of tuning

**Q2 REVISE — DSR cross-trial sigma_SR gap:**
- Current `dsr.py:73`: cross-FOLD sigma_SR (within single run)
- N_trials=2 needs cross-TRIAL sigma_SR per Bailey eq. 13
- |S13 Sharpe (-44.46) - S14 Sharpe (?)| → sigma_SR ≈ 30+ → DSR almost certainly FAIL
- Real engineering gap, not yet implemented

**Joint conclusion:** Option A (S14 tuning measurement) would produce theatrical FAIL без statistical meaning — T5 fails on math, DSR fails on cross-trial penalty. Option B (honest close) skips ahead to same end-state, saves 1 sprint.

User verdict (verbatim): "Продолжаем тогда (B) Honest close immediately."

## Решение

### S14 scope: Honest close ship

**v0.1 status declaration:**
- **Infrastructure: COMPLETE** (16 FSM states + 30 events + 74 transitions + 45 reason codes + 38 component pages + 28 ADRs + 14 sprint pages + 4.81y backfilled data + WFA + DSR + MC + verdict pipeline)
- **Strategy validation: NEGATIVE** (EMA(12)×EMA(26) + ADX(14) + RSI(14) + ATR(14) на 1H BTCUSDT = no measurable edge across 2 measurements: 2.2y prior + 4.81y S13)
- **MVP DONE: NOT achieved** per acceptance-criteria.md (T5 ≥100 trades structurally unreachable for chosen strategy + timeframe)
- **Mainnet exposure: 0** (operator validation 33min only, no live trading)

### S14 deliverables

**T1: ADR 0029 (this document)** — accepted, status final.

**T2: Sprint-14 page** — canonical "honest close" summary с:
- Final v0.1 status declaration
- Strategy validation summary (S13 + prior S13 attempt)
- T5 unreachability math (trader Q1 EXPAND verified via grep)
- DSR cross-trial gap acknowledgment (trader Q2 REVISE)
- All carry-overs preserved from S12 + S13 (open issues)

**T3: Wiki sync** — current-state.md updated к "v0.1 infrastructure complete, strategy validation negative" + counts (ADR 28→29, sprint pages 15→16).

**T4: log.md sprint-end entry** — chronological closure event.

**T5: SPRINT_STATE → between-sprints с post-MVP status** — operator decides future direction.

**T6: PHASE 8 ship** — sprint-finish skill: tag `v0.1.0-alpha.14` (ship marker, NOT MVP DONE — explicit "infrastructure milestone, strategy validation negative").

### NO new code, NO measurement re-run

Per Option B framework: skip theatrical FAIL re-measurement. All deliverables = documentation + wiki sync. Zero code changes (Q7-S12 zero-migration constraint preserved trivially).

### Future direction options (deferred к operator)

Documented in sprint-14 page "Open issues for v0.2+":

**(A) Strategy revision** (different family):
- Mean-reversion (RSI extreme + Bollinger Bands)
- Regime-switch (HMM detection)
- ML-driven (XGBoost classifier per pre-S1 Mimo bot reference)
- Cost: 3-5 sprints + new validation cycle (each new strategy = new N_trials count)

**(B) Multi-symbol expansion** (same strategy):
- ETHUSDT + SOLUSDT venue support
- Aggregated signal frequency ~3x
- Cost: 2-3 sprints, scope expansion vs v0.1 single-symbol

**(C) Different timeframe** (15M / 4H):
- 15M = 4x signal frequency, but noisier
- 4H = lower frequency но cleaner trend signals
- Cost: 1-2 sprints, ADR 0005 amendment needed

**(D) Project pause** — close current branch, freeze repo as "v0.1 infrastructure milestone". Reactivate if new strategy candidate emerges.

**Operator decides (E) at any future point.** No pre-commitment from S14.

### Cross-cutting concerns (binding)

- **CC1 (Tag semantics):** `v0.1.0-alpha.14` = honest close marker, NOT MVP DONE. v0.1.0 (drop alpha) reserved for actual T1-T6 PASS achievement (not currently feasible per Q1 EXPAND).
- **CC2 (Carry-overs preserved):** All S12 + S13 carry-overs explicitly remain open. Future strategy attempts may address (e.g. FillRecorderAdapter Layer 2 schema link useful for any live trading path).
- **CC3 (No spec amendment):** acceptance-criteria.md NOT modified. T1-T6 thresholds stand. Honest close acknowledges threshold не met для chosen strategy + timeframe.
- **CC4 (Documentation completeness):** Sprint page documents trader's Q1 frequency math (verifiable via existing data) + Q2 DSR gap (verifiable via dsr.py source) для future reviewers.

## Последствия

**Plus:**
- Honest closure based on empirical data (2 WFA measurements: 2.2y + 4.81y both FAIL T5 structurally)
- 14 sprints of infrastructure work documented + preserved
- Reusable framework для future strategy attempts (data infra + WFA + DSR + MC + verdict pipeline)
- Avoids p-hacking trap (per Q7-S13 trader concern на defer-defer)
- Saves 1 sprint vs theatrical Option A re-measurement
- 0 capital exposure (no Mainnet)

**Minus:**
- "MVP DONE" not achieved per acceptance-criteria.md spec
- Strategy hypothesis (EMA crossover на 1H crypto = profitable) empirically rejected
- All S12 + S13 carry-overs unaddressed (10+ items)
- DSR cross-trial sigma_SR gap не implemented (deferred S15+ если any future revision)
- No live trading validation (33min only, FillRecorder Layer 2 still placeholder)

**v0.2+ carry-overs (anticipated, deferred):**

All S12 + S13 carry-overs preserved:
- F live demo Mainnet validation actual run (operator-driven, not run since S12)
- FillRecorderAdapter Layer 2 schema link (entry_signal_id к execution_state migration)
- 3-way endpoint enum (DEMO/TESTNET/MAINNET) — Q6 future fix
- T2 review C3 init_db dual-conn comment (S11 carry-over)
- DSR per-fold DataFrame→TradeRecord conversion (S10 informational)
- DSR threshold calibration (S15+ per S11 Q5)
- DSR cross-trial sigma_SR implementation (S14 Q2 REVISE — needed if future revision)
- halt_log INSERT order swap в `_set_halt` (PRE-EXISTING, data-integrity reviewer T1 follow-up)
- find_by_order_id ORDER BY explicit (T1 reviewer follow-up)
- fill-history.md + bybit-adapter.md / ws-private-consumer.md component page updates (T1 trading-logic reviewer follow-up)
- T2/T5/T6 quant-stats deferred concerns (Sortino formula docs, sqrt(8760) frequency-agnostic, boundary tests)
- 48h Bybit demo validation (operator-driven, not run since 33min S12 attempt)
- Strategy revision OR pivot decision (per Option A/B/C/D in sprint-14 page Future Direction)

## Связанные документы

- [[../pre-s14-backlog]] — PHASE 2 verdicts trail с trader Q1+Q2 source claims verified
- [[0028-sprint-13-strategy-validation]] — predecessor sprint (verdict FAIL trigger)
- [[../sprints/sprint-13-backfill-wfa]] — S13 measurement results
- [[../architecture/acceptance-criteria]] — T1-T6 thresholds (immutable, not amended)
- [[../architecture/migration-plan]] — original 10-sprint roadmap (now closed at S14)

## Поправки

- (none yet)
