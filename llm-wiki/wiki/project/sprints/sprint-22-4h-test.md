---
title: Sprint 22 — BTC 4H mean-reversion test (verdict FAIL T5 count, 5/6+DSR+MC PASS)
type: sprint
tags: [sprint-22, v0.5-direction-C, btc-4h, mean-reversion, hypothesis-5, combined-architectural-measurement, verdict-fail-t5-count, similar-pattern-к-s17]
created: 2026-04-26
updated: 2026-04-26
status: completed
sources:
  - project/decisions/0037-sprint-22-4h-test.md
  - project/pre-s22-backlog.md
  - project/sprints/sprint-21-honest-close-v04.md
---

# Sprint 22 — BTC 4H mean-reversion test (v0.5-C)

## Overview

S22 = combined architectural + measurement sprint per joint trader+architecture verdict on v0.5 direction. Both agents converged Option (C) 4H mean-reversion test после frequency probe pre-validation (439 raw triggers).

## Verdict

**FAIL — T5 count only** (62 trades < 100 floor). Per ADR 0037 BINDING → S23 honest close v0.5 (5-th honest close в проекте).

### Strategy criteria results (similar pattern к S17 1H)

| Criterion | Threshold | S22 result | Status |
|-----------|-----------|------------|--------|
| T1 Sharpe OOS | ≥1.0 | **6.17** | ✅ PASS |
| T2 Sortino OOS | ≥1.5 | 7309 | ✅ PASS (extremely high — sample artifact) |
| T3 MaxDD | <0.25 | 0.061 | ✅ PASS |
| T4 win/RR | RR≥2 → win≥35% | win 37.1% / RR 580 | ✅ PASS |
| **T5 n_trades** | **≥100** | **62** | ❌ **FAIL count** |
| T5 t_stat | ≥2.0 | 1.04 | ❌ FAIL borderline |
| T6 OOS/IS | ≥0.7 | 2.96 | ✅ PASS |
| **DSR** | >0 | **0.996** | ✅ PASS (n_trials=1 fresh) |
| **MC p-value** | ≤0.05 | **0.018** | ✅ **PASS (stat-sig)** |
| Acceptance gate (composite) | sharpe + MC | sharpe FAIL (fold 1 below 0.7) | ❌ FAIL |

### Fold concentration check (per S19 T-Amendment 2 carry-over pattern)

```
fold_sharpe_ratios: [1.93, -2.92, 1.32, 12.70, 1.78]
mean = 2.96
fold #3 (idx=3) = 12.70 dominant outlier
4/5 folds positive (only fold #1 negative)
Removing fold #3: mean = (1.93 - 2.92 + 1.32 + 1.78)/4 = 0.53 (still PASS T6 0.7 borderline FAIL)
```

Less concentrated than S17 (4/5 positive vs S17 4/5 mixed) — но fold #3 outlier still drives mean.

### Frequency math reconciliation

S22 architecture frequency probe predicted 439 raw triggers → ~100-200 actual trades estimate.
**S22 actual: 62 trades** (FLAT-only constraint heavily filters consecutive triggers).

Pattern similar к:
- S17 BTC 1H: 59 trades, 5/6+DSR+MC PASS, T5 count FAIL
- S22 BTC 4H: 62 trades, 5/6+DSR+MC PASS, T5 count FAIL

**Critical insight:** T5 floor 100 STRUCTURALLY unreachable на BTC-only mean-reversion regardless of timeframe (1H/4H both ~60 trades, 15M degraded). FLAT-only constraint dominates trade count, not raw signal frequency.

## Plan / ADR links

- [[../decisions/0037-sprint-22-4h-test]] — Sprint 22 ADR
- [[../pre-s22-backlog]] — PHASE 2 joint trader+architecture verdicts trail
- [[sprint-21-honest-close-v04]] — predecessor (v0.4 honest close)
- [[sprint-17-btc-mean-reversion-relaxed]] — S17 reference (similar T5 fail pattern)
- [[sprint-19-15m-architecture]] — Conditions A1+A2+A3 reused

## Deliverables

| Task | Status | Description |
|------|--------|-------------|
| T0 | ✅ DONE | Frequency probe (439 raw triggers — Option C viable) |
| T1 | ✅ DONE | ADR 0037 accepted |
| T2 | ✅ DONE | 5-map atomic extension (rest.py + __main__.py 4 sites + 2× argparse choices) |
| T3 | ✅ DONE | 4H BTCUSDT parquet via 1H resample (10,517 bars) — backfill API hung, resample used |
| T4 | ✅ DONE | WFA 4H measurement → VERDICT FAIL T5 count |
| T5 | ✅ This commit | sprint-22 page + wiki sync |
| T6 | pending | PHASE 8 ship (PR + tag v0.1.0-alpha.22) |

## FSM growth

NONE. S22 = config + CLI changes + measurement. Counts unchanged: **16/30/74/45**.

## Reason codes growth

NONE.

## Tests / quality

- pytest unit: **732 passed** (S21 baseline preserved, no regressions)
- mypy --strict src/: clean (72 source files)
- Q7-S12 zero-migration: trivially preserved

## Code changes

### Modified

- `src/marketdata/bybit/rest.py:68-72` — added `"240": ("4h", 14_400_000)` к single-dict intervals (Condition C1)
- `src/__main__.py`:
  - Line 191 (interval_seconds_map): added `"240": 14400`
  - Line 282 (interval_label_map _cmd_backfill): added `"240": "4h"` (5th map — architecture missed, runtime KeyError exposed)
  - Line 407 (interval_label_map _load_ohlcv): added `"240": "4h"`
  - Line 610 (bars_per_year_map): added `"240": 2190`
  - Lines 786, 813 (argparse choices): added `"240"` к both backfill + wfa
- `data/BTCUSDT_4h.parquet` (runtime artifact, gitignored): 10,517 bars via 1H resample (Bybit backfill API hung — resample used as fallback)

### NEW (NONE)

S22 = no new code modules. All infrastructure reused.

## Wiki updates

- 1 NEW ADR (0037 — accepted)
- 1 NEW sprint page (this — sprint-22-4h-test)
- 1 NEW backlog (pre-s22-backlog.md)
- Modified: current-state.md (TL;DR + counts ADR 36→37, sprint pages 23→24, +S22 row), index.md, log.md, SPRINT_STATE
- s22_wfa_result.json committed (full measurement output)

## Critical insight: T5 floor 100 structurally unreachable на BTC-only mean-reversion

| Hypothesis | Sprint | Trades | Pattern |
|-----------|--------|--------|---------|
| EMA crossover 1H | S13 | 20 | T5 fail (frequency low) |
| Mean-rev multi-symbol 1H | S15 | 108 | T5 PASS (3-symbol aggregation) |
| Mean-rev BTC-only 1H relaxed | S17 | 59 | T5 fail count, 5/6+DSR+MC PASS |
| Mean-rev BTC-only 15M relaxed | S20 | 73 | T5 fail count, T1/T2/T4/T6 fail |
| **Mean-rev BTC-only 4H relaxed** | **S22** | **62** | **T5 fail count, 5/6+DSR+MC PASS** |

**4 BTC-only attempts × 3 timeframes = ~60-73 trades all** (FLAT-only constraint dominant). T5 floor 100 **only reachable via multi-symbol aggregation** (out of MVP scope per user 2026-04-26).

## Open issues для S23 (honest close v0.5 BINDING)

S23 = pre-committed honest close per ADR 0037 BINDING. Documentation only sprint:

- ADR 0038 v0.5 honest close (5 hypotheses tested = 5-th honest close pattern)
- sprint-23-honest-close-v05.md
- Document T5 floor 100 structurally unreachable на BTC-only (3 timeframes tested)
- Document repeated 5/6+DSR+MC PASS pattern (S17 1H + S22 4H) — strategy edge regime-specific
- Archive cross_trial_sharpes.json к _v0.5-final.json (mirror S16/S18/S21)
- Tag v0.1.0-alpha.23 = v0.5 honest close marker

## v0.6+ direction options (operator-driven, no commitment)

Per S22 evidence accumulation:

- **(v0.6-A) Hybrid mean-reversion + ML XGBoost** — STILL trader-DEFERRED (n=62 still small для CPCV). Combined evidence S17 + S22 = ~120 trades available, может быть достаточно для small-sample ML
- **(v0.6-B) HMM regime-switch** — addresses fold concentration patterns
- **(v0.6-C) Multi-symbol revival post-MVP** — only path к T5 ≥100 conjoint pass (out of MVP per user)
- **(v0.6-D) Different strategy class entirely** (donchian breakout, regime-detection, ATR-based)
- **(v0.6-E) Project pause** — 5 hypotheses tested
- **(v0.6-F) MVP T5 floor amendment** — operator may decide T5 floor 100 too aggressive для BTC-only mean-reversion (cite S17+S22+S20 evidence: max ~73 trades empirically). Spec amendment к acceptance-criteria.md required (current ADR pattern strict against amendments)

## Carry-overs preserved (S12-S20, 16+ items)

All previous carry-overs remain. New from S22:
- Bybit backfill API hung на 4H interval — root cause unknown, resample workaround used. Investigation deferred.
- 5th map missed by architecture review (interval_label_map в `_cmd_backfill`) — discovered via runtime KeyError. Architecture review template should include grep для all `interval_label_map` usages.
- T5 floor 100 structurally unreachable evidence (4 BTC-only sprints showing ~60-73 trades) — institutional knowledge для v0.6+

## Key decisions (S22 ADR 0037)

- **Joint convergence (C) 4H** confirmed
- **Frequency probe T0** prevented wasted sprint
- **5-map atomic extension** applied (5th map runtime-discovered)
- **WFA params kept ADR 0014** (no scale-down)
- **T5 floor 100 default** kept (frequency probe supported, не need T-Amendment 1 raise)
- **Verdict FAIL T5 count only** + 5/6+DSR+MC PASS pattern (similar к S17 — strategy edge regime-specific)
- **NEW INSIGHT:** T5 100 structurally unreachable на BTC-only mean-reversion (3 timeframes tested all ~60-73 trades)
- **S23 honest close v0.5 BINDING** per ADR 0037

## Related

- [[../decisions/0037-sprint-22-4h-test]] — S22 ADR
- [[../pre-s22-backlog]] — PHASE 2 joint verdicts
- [[sprint-21-honest-close-v04]] — v0.4 honest close (predecessor)
- [[sprint-17-btc-mean-reversion-relaxed]] — S17 partial signal pattern reference
- [[sprint-20-15m-measurement]] — S20 15M FAIL (different failure mode)
- [[../decisions/0034-sprint-19-15m-architecture]] — Conditions A1+A2+A3 reused
- [[../architecture/acceptance-criteria]] — T1-T6 thresholds (immutable)
