---
title: Sprint 20 — BTC 15M WFA measurement (verdict FAIL, T5 failthrough triggered)
type: sprint
tags: [sprint-20, btc-15m, mean-reversion, measurement-sprint, verdict-fail, t5-failthrough-triggered, hypothesis-4-tested, hudson-urquhart-validated]
created: 2026-04-26
updated: 2026-04-26
status: completed
sources:
  - project/decisions/0035-sprint-20-15m-measurement.md
  - project/decisions/0034-sprint-19-15m-architecture.md
  - project/sprints/sprint-19-15m-architecture.md
---

# Sprint 20 — BTC 15M WFA measurement

## Overview

S20 = pre-registered measurement sprint per ADR 0034 BINDING. Executed pre-registered command from S19:
```bash
SPRINT_N=20 .venv/bin/python -m src wfa --symbol BTCUSDT --interval 15 \
  --start 2021-07-15 --end 2026-04-26
```

User confirm "T5 ≥ 150" before measurement → T-Amendment 1 binding accepted.

## Verdict

**FAIL — T5 count failthrough triggered + 4 critical T-criteria fail.**

Per ADR 0034 amendment 3 BINDING → S21 = honest close v0.4 (4 hypotheses tested).

### Strategy criteria results (4-th hypothesis)

| Criterion | Threshold | S20 result | Status |
|-----------|-----------|------------|--------|
| T1 Sharpe OOS | ≥1.0 | **-45.57** | ❌ FAIL |
| T2 Sortino OOS | ≥1.5 | -345.70 | ❌ FAIL |
| T3 MaxDD | <0.25 | 0.021 | ✅ PASS |
| T4 win/RR | RR≥1.5 → win≥45% | win 30.1% / RR 1.39 | ❌ FAIL (RR<1.5) |
| **T5 n_trades** | **≥150 (T-Amendment 1)** | **73** | ❌ **FAIL count** |
| T5 t_stat | ≥2.0 | -2.08 | ❌ FAIL |
| T6 OOS/IS sharpe ratio | ≥0.7 | **-37.13** | ❌ FAIL |
| **DSR** | >0 | 0.030 | ✅ PASS (n_trials=1 single-trial low bar) |
| **MC p-value** | ≤0.05 | 0.044 | ✅ PASS (borderline) |

### Fold concentration check (T-Amendment 2 BINDING)

```
fold_sharpe_ratios: [-0.74, -4.83, -185.21, +2.27, +2.84]
mean = -37.13
fold #2 = -185.21 catastrophic outlier (REGIME CONCENTRATION negative)
```

Removing fold #2: mean ≈ +0.13 (still не ≥0.7 threshold). Strategy fails regardless of outlier removal.

## Plan / ADR links

- [[../decisions/0035-sprint-20-15m-measurement]] — Sprint 20 ADR (verdict FAIL + S21 trigger)
- [[../decisions/0034-sprint-19-15m-architecture]] — S19 ADR (pre-registered binding criteria)
- [[sprint-19-15m-architecture]] — predecessor (architectural prep)
- [[sprint-17-btc-mean-reversion-relaxed]] — S17 partial signal на 1H (contradicted at 15M)

## Deliverables

| Task | Status | Description |
|------|--------|-------------|
| T1 | ✅ DONE | ADR 0035 accepted |
| T2 | ✅ This commit | sprint-20 page |
| T3 | ✅ AUTO | cross_trial_sharpes.json updated (sprint=20, oos_sharpe=-37.13 persisted) |
| T4 | ✅ This commit | wiki sync |
| T5 | pending | PHASE 8 ship (PR + tag v0.1.0-alpha.20) |

## FSM growth

NONE. S20 = measurement only, no code changes.

## Reason codes growth

NONE.

## Tests / quality

NO code changes:
- pytest unit: 732 passed (S19 baseline preserved, no regressions)
- mypy --strict src/: clean (72 source files)
- Q7-S12 zero-migration: preserved

## Frequency math reconciliation (Hudson & Urquhart 2021 empirically validated)

S17 BTC 1H baseline: 59 trades (RSI 35/65 + BB 1.5σ AND-gated).
S20 architecture frequency math 4x prediction: ~236 trades.
**S20 actual: 73 trades.**

AND-gate joint multiplier на 15M ≈ **1.24x baseline** (vs predicted 4x). Hudson & Urquhart 2021 academic prior CONFIRMED EMPIRICALLY: mean-reversion regime degrades sub-hourly. RSI-BB AND-gate correlation pattern weakens на noisier 15M signals — fewer joint trigger events чем pure frequency increase would predict.

## S17 contradiction analysis

S17 BTC 1H showed MC p=0.01 stat-sig signal (5/6 + DSR + MC PASS на 59 trades). Same parameters at 15M = T1=-45.57 + T6=-37.13 + MC p=0.044 borderline = strategy fails fundamentally. 

**Conclusion:** S17 partial signal был **regime-specific к 1H timeframe**, не frequency-bound. Frequency-dimension hypothesis (15M = solve T5 sample problem) FALSIFIED. The signal is fragile to timeframe shift — fundamental property of mean-reversion на BTC.

## Cross-cutting concerns (carry-over к S21 honest close)

- **CC1 Hudson & Urquhart 2021 empirically validated**: 15M mean-reversion degrades vs 1H для BTC. Document для v0.5+ hypothesis selection.
- **CC2 Annualization parameterization (Condition A3) paid off**: T1=-45.57 IS genuine result, не -22.78 understimate. Architecture investment justified.
- **CC3 Fold concentration negative direction**: regime concentration pattern observed (fold #2 -185.21 catastrophic). Different from S17 positive fold #5 outlier — both = high-variance failure mode.
- **CC4 cross_trial_sharpes update**: S20 trial entry persisted automatically (sprint=20, oos_sharpe=-37.13). S21 honest close archives к `_v0.4-final.json` + reset для v0.5.
- **CC5 S17 partial signal contradicted at 15M**: regime-specific к 1H, not frequency-bound. v0.5+ hypothesis must reconsider: hybrid ML 1H + ML filter (regime detection) OR 4H stability test OR pause.

## Wiki updates

- 1 NEW ADR (0035 — accepted)
- 1 NEW sprint page (this — sprint-20-15m-measurement)
- Modified: current-state.md (TL;DR post-S20, ADR 34→35, sprint pages 21→22, +S20 row), index.md (sprint-20 + ADR 0035), log.md (sprint-end), SPRINT_STATE (between-sprints, tag alpha.20)
- s20_wfa_result.json committed

## Open issues для S21 (honest close v0.4)

S21 = pre-committed honest close per ADR 0034 BINDING. Documentation only sprint:

- ADR 0036 v0.4 honest close (4 hypotheses tested negative)
- sprint-21-honest-close-v04.md
- Document Hudson & Urquhart 2021 empirical validation (15M mean-reversion degrades)
- Document S17 1H regime-specificity (partial signal не frequency-bound)
- Archive cross_trial_sharpes.json к _v0.4-final.json (mirror S16/S18 pattern)
- Tag v0.1.0-alpha.21 = v0.4 honest close marker

## v0.5+ direction options (operator-driven, no commitment)

Per S20 evidence accumulation:

- **(v0.5-A)** Hybrid 1H mean-reversion + ML XGBoost filter — S17 partial signal preserved, ML filter может capture regime-specificity. Cost: 5-10 sprints CPCV framework.
- **(v0.5-B)** 4H mean-reversion test — lower frequency может match regime-specific stability. Cost: 1-2 sprints.
- **(v0.5-C)** Regime-switch HMM + mean-reversion — addresses fold concentration pattern. Cost: 3-5 sprints.
- **(v0.5-D)** Project pause — 4 hypotheses tested, infrastructure preserved.

## Carry-overs preserved (S12-S19, 16+ items + S20 new)

All previous carry-overs remain. New from S20:
- S17 1H regime-specificity finding — institutional knowledge для v0.5+ hypothesis selection
- Hudson & Urquhart 2021 empirical validation — sub-hourly mean-reversion degradation на BTC documented

## Key decisions (S20 ADR 0035)

- **Pre-registered binding criteria honored**: T5 floor 150, fold concentration check applied
- **T5 failthrough triggered**: 73 < 150 → FAIL count alone per ADR 0034 amendment 3
- **Fold concentration negative regime**: fold #2 -185.21 catastrophic, cleanly identified per T-Amendment 2
- **Annualization Condition A3 paid off**: T1=-45.57 genuine result, не false-PASS understimate
- **Hudson & Urquhart 2021 validated empirically**: 15M mean-reversion degrades for BTC
- **S17 partial signal regime-specific к 1H**: не frequency-bound, fragile к timeframe shift
- **NO code changes**: measurement only sprint
- **S21 = honest close v0.4 BINDING**: pre-committed per ADR 0034

## Related

- [[../decisions/0035-sprint-20-15m-measurement]] — S20 ADR
- [[../decisions/0034-sprint-19-15m-architecture]] — S19 ADR (binding criteria triggered)
- [[sprint-19-15m-architecture]] — S19 architectural prep
- [[sprint-17-btc-mean-reversion-relaxed]] — S17 partial signal на 1H
- [[../architecture/acceptance-criteria]] — T1-T6 thresholds (immutable)
