---
title: Sprint 16 — v0.2 honest close (2 strategy families tested both FAIL)
type: sprint
tags: [sprint-16, honest-close-v02, no-edge, mvp-incomplete, n-trials-archival, v0.3-readiness]
created: 2026-04-26
updated: 2026-04-26
status: completed
sources:
  - project/decisions/0031-sprint-16-honest-close-v02.md
  - project/pre-s16-backlog.md
  - project/sprints/sprint-15-mean-reversion-multi-symbol.md
  - project/sprints/sprint-14-honest-close.md
---

# Sprint 16 — v0.2 honest close

## Overview

S16 = v0.2 honest close ship. Per S16 PHASE 2 brainstorm (1 question delegated к trader-expert per user directive "пусть агенты сами и решат"):

**Trader ROUND 1 verdict: CONFIRM (D) Honest close v0.2.**

Core trader rationale: 2 strategy families empirically tested across 4.81y Bybit Spot 1H data — both FAIL. DSR cross-trial math (sigma_SR=22.68 с -44.46 anchor) makes any S16 retry structurally futile. BTC +1.75 weak signal noted as institutional knowledge для v0.3, не decision-reversing for S16.

User directive: "Пусть агенты сами и решат" + "После того как агенты что-то решат, начинай следующий спринт". S16 = honest close ship.

## Final v0.2 status

- **Infrastructure: ✅ COMPLETE** — 16 FSM states / 30 events / 74 transitions / 45 reason codes / 38 component pages / 31 ADRs (включая 0031) / 18 sprint pages / WFA + DSR + MC + cross-trial log + multi-symbol CLI + 2 strategy classes wired
- **Strategy validation: ❌ NEGATIVE × 2 hypotheses** —
  | Hypothesis | Sprint | OOS Trades | T1 Sharpe | Verdict | Failure mode |
  |-----------|--------|-----------|-----------|---------|--------------|
  | EMA(12)×(26) + ADX(14) + RSI(14) + ATR(14) на 1H BTCUSDT | S13 (4.81y) | 20 | -44.46 | FAIL (T1+T2+T4+T5) | Insufficient signals + negative pnl |
  | Mean-reversion RSI<30 AND close<lower_BB(20, 2σ) на 1H × 3 sym BTC+ETH+SOL | S15 | 108 | 9.32 | FAIL (T5 t_stat + T6 + MC + DSR) | Enough signals + high-variance + MC random-equivalent |
- **MVP DONE per acceptance-criteria.md: NOT achieved** (T1-T6 + DSR + MC не met conjointly)
- **Mainnet exposure: 0** (Bybit demo 33min only)
- **Tag: `v0.1.0-alpha.16`** = v0.2 honest close marker, NOT MVP DONE

## Plan / ADR links

- [[../decisions/0031-sprint-16-honest-close-v02]] — Sprint 16 ADR (v0.2 honest close)
- [[../pre-s16-backlog]] — PHASE 2 verdict (trader CONFIRM Option D)
- [[sprint-15-mean-reversion-multi-symbol]] — predecessor (verdict FAIL but T5 reached trigger)
- [[sprint-14-honest-close]] — precedent honest close pattern (ADR 0029)

## Deliverables

S16 = documentation + archival policy. NO new code. NO measurement re-run.

- T1 (this sprint): ADR 0031 status accepted
- T2 (this sprint): sprint-16 page (this document)
- T3: wiki sync (current-state.md + index.md + counts ADR 30→31, sprint pages 17→18)
- T4: log.md sprint-end entry
- T5: SPRINT_STATE → between-sprints с post-v0.2-honest-close status
- T6: cross_trial_sharpes archival per CC2 (`data/cross_trial_sharpes.json` → `data/cross_trial_sharpes_v0.2.json` + reset к `[]` для v0.3 readiness)
- T7: PHASE 8 ship via sprint-finish skill (tag v0.1.0-alpha.16)

## FSM growth

NONE. S16 = documentation + archival policy only. Counts unchanged: **16 states / 30 events / 74 transitions / 45 reason codes**.

## Reason codes growth

NONE.

## Tests / quality

NO code changes. Existing test suite preserved at S15 baseline:
- pytest unit: 732 passed (baseline preserved, no new tests, no regressions)
- mypy --strict src/: clean (72 source files)
- ruff: clean
- Q7-S12 zero-migration: trivially preserved

## Strategy validation summary

### Two strategy families × 5y Bybit Spot 1H = both FAIL

#### S13 — EMA crossover + ADX + RSI + ATR (1H BTCUSDT, 4.81y, 42098 bars)

- 20 OOS trades, T1 Sharpe -44.46
- Failure mode: insufficient signals (frequency ~1 trade per 5-10 days; T5 floor 100 unreachable за structural mathematical limit per S14 Q1 EXPAND)
- Failed: T1, T2, T4, T5

#### S15 — Mean-reversion RSI+BB AND-gated × 3 symbols BTC+ETH+SOL (1H, 4.81y BTC + 3.7y ETH + 3.5y SOL)

- 108 OOS trades aggregate (T5 floor REACHED first time, ADR 0030 hypothesis VALIDATED)
- BTCUSDT: 44 trades, sharpe ratio mean +1.75, MC p 0.197 (best — only positive direction observed в проекте)
- ETHUSDT: 29 trades, sharpe ratio mean -39.35 (one fold sharpe -188.65 catastrophic = data pathology, extreme vol window 2021-2022)
- SOLUSDT: 35 trades, sharpe ratio mean +0.45, MC p 0.65
- Aggregate: T1 9.32 PASS / T2 29.55 PASS / T3 0.053 PASS / T4 win 37%/RR 2.27 PASS / T5 n=108 PASS-on-count BUT t_stat 1.04<2.0 FAIL / T6 mean -12.38 FAIL / MC p 0.998 FAIL / DSR 0 FAIL (n_trials=2, sigma_SR=22.68 cross-trial)
- Failure mode: enough signals + high-variance + MC random-equivalent

### DSR cross-trial state (post-S15, before S16 archival)

```json
{"trials": [{"sprint": 13, "oos_sharpe": -44.46}, {"sprint": 15, "oos_sharpe": -12.384}]}
```

Per Bailey 2014 eq. 13: sigma_SR = 22.681. Expected max Sharpe gate at n_trials=3 ≈ +21.5 — unrealistic for 1H crypto retry. S16 T6 archives к `data/cross_trial_sharpes_v0.2.json` + resets `data/cross_trial_sharpes.json` к `{"trials": []}` для v0.3 fresh-start readiness.

### BTC institutional knowledge (CC1)

BTCUSDT mean-reversion (single-symbol, isolated от ETH/SOL noise) = strongest observed signal в проекте. Sharpe ratio mean +1.75, MC p 0.197 (close к 0.05 threshold). Не decision-reversing для S16 (44 trades / 5 folds = 9 trades/fold = unreliable t-stat per fold), но worth documenting as v0.3 hypothesis: BTC-only mean-reversion с tighter variance control + fresh trial counter.

### ETH fold pathology (CC3)

S15 ETHUSDT fold sharpe -188.65 = data pathology (likely extreme vol window 2021-2022). NOT strategy-attributable failure mode — MC p=0.998 на full distribution = strategy random-equivalent regardless of outlier. Future developers reading S15 results: aggregate FAIL = genuine, не outlier-artifact.

## Wiki updates

- 1 NEW ADR (0031 — accepted)
- 1 NEW sprint page (this — sprint-16-honest-close-v02)
- 1 NEW backlog (pre-s16-backlog.md)
- Modified: current-state.md (TL;DR post-S16, ADR 30→31, sprint pages 17→18, +S16 row), index.md (sprint-16 + ADR 0031), log.md (sprint-end), SPRINT_STATE (between-sprints, tag alpha.16)
- Archival: data/cross_trial_sharpes.json → data/cross_trial_sharpes_v0.2.json + reset к `[]`

## Open issues для v0.3+ (operator-driven, no commitment)

**Future direction options (deferred — operator decides if/when):**

### (v0.3-A) BTC-only mean-reversion fresh start
- Strongest observed signal (S15 BTC +1.75 / p 0.197)
- Single-symbol, isolated от ETH/SOL noise
- Fresh `cross_trial_sharpes.json` (S16 T6 archived v0.2)
- Cost: 1-2 sprints

### (v0.3-B) Regime-switch (HMM detection on volatility)
- Context layer + market regime filter
- Cost: 3-5 sprints (HMM training pipeline new)

### (v0.3-C) ML-driven (XGBoost classifier)
- Per ADR 0030 deferred
- NOT recommended per S15 evidence (MC p=0.998 = no partial signal для ML к learn)
- Defer until simpler v0.3 strategy demonstrates partial edge first

### (v0.3-D) Different timeframe (15M / 4H)
- Q3 architectural blockers preserved (interval_map в `rest.py:66-67`, heal_max_age в `config.py:97-102` — production safety bug at 15M)
- 15M: noisier (mean-reversion degrades sub-hourly per Hudson & Urquhart 2021)
- 4H: lower frequency но cleaner trend signals
- Cost: 2 sprints (1 architectural + 1 measurement)

### (v0.3-E) Project pause
- Close current branch, freeze repo as "v0.2 honest close marker"
- Reactivate if new candidate emerges
- Cost: 0 sprints

### Carry-overs preserved (all S12+S13+S14+S15 unaddressed, 12+ items)

- F live demo Mainnet validation actual run (operator-driven, not run since S12)
- FillRecorderAdapter Layer 2 schema link (entry_signal_id к execution_state migration)
- 3-way endpoint enum (DEMO/TESTNET/MAINNET) — Q6 future fix
- T2 review C3 init_db dual-conn comment (S11 carry-over)
- DSR per-fold DataFrame→TradeRecord conversion (S10 informational)
- DSR threshold calibration (S15+ per S11 Q5)
- halt_log INSERT order swap в `_set_halt` (PRE-EXISTING)
- find_by_order_id ORDER BY explicit (T1 reviewer follow-up)
- fill-history.md / bybit-adapter.md / ws-private-consumer.md component page updates
- T2/T5/T6 quant-stats deferred concerns (Sortino formula docs, sqrt(8760) frequency-agnostic, boundary tests)
- 48h Bybit demo validation (operator-driven)
- Q3 15M architectural blockers (interval_map + heal_max_age — preserved per CC6)
- Multi-symbol live runtime fan-out (S15 deferred — `_cmd_run` kept single-symbol)
- Capital allocation cross-symbol exposure caps (S15 deferred — natural per-symbol Kelly suffices)

## Key decisions (S16 ADR 0031)

- **Q1 CONFIRM (trader)**: Option D Honest close v0.2 — DSR cross-trial math + MC p=0.998 evidence + Bailey 2014 N_trials per hypothesis principle
- **CC1 (BTC institutional knowledge)**: documented для v0.3 BTC-only retry hypothesis
- **CC2 (cross_trial_sharpes archival policy)**: BINDING — v0.3 fresh hypothesis archives current + resets к empty
- **CC3 (ETH fold pathology)**: documented к prevent future misattribution
- **CC4 (Tag semantics)**: `v0.1.0-alpha.16` = v0.2 honest close marker, NOT MVP DONE
- **CC5 (No spec amendment)**: acceptance-criteria.md T1-T6 thresholds preserved
- **CC6 (Q3 15M blockers preserved)**: documented для potential future revival
- **No code changes**: S16 = documentation + archival policy only

## Related

- [[../decisions/0031-sprint-16-honest-close-v02]] — S16 ADR
- [[../pre-s16-backlog]] — PHASE 2 verdict
- [[sprint-15-mean-reversion-multi-symbol]] — predecessor
- [[sprint-14-honest-close]] — S14 honest close precedent
- [[sprint-13-backfill-wfa]] — S13 measurement (-44.46 anchor)
- [[../architecture/acceptance-criteria]] — T1-T6 thresholds (immutable)
- [[../architecture/migration-plan]] — original roadmap (closed at S14, v0.2 retry attempted S15, v0.2 closed at S16)
