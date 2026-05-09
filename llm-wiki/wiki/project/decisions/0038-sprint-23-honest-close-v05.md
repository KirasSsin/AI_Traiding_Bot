---
title: 0038. Sprint 23 — v0.5 honest close (5 hypotheses tested + T5 100 structurally unreachable insight)
type: decision
date: 2026-04-26
sprint: 23
tags: [adr, sprint-23, honest-close-v05, hypothesis-5-tested, t5-100-structurally-unreachable, n-trials-archival, v0.6-readiness]
sources:
  - project/decisions/0037-sprint-22-4h-test.md
  - project/decisions/0036-sprint-21-honest-close-v04.md
  - project/sprints/sprint-22-4h-test.md
  - project/architecture/acceptance-criteria.md
status: accepted
---

# 0038. Sprint 23 — v0.5 honest close

**Status:** accepted
**Date:** 2026-04-26

## Контекст

S22 shipped (PR #30, tag `v0.1.0-alpha.22`). BTC 4H mean-reversion test verdict FAIL T5 count (62 trades < 100 floor) but 5/6+DSR=0.996+MC p=0.018 PASS — similar pattern к S17 1H. Per ADR 0037 BINDING: → S23 honest close v0.5.

S23 = pre-committed honest close per ADR 0037. Pattern mirrors S14/S16/S18/S21 (5-th honest close в проекте, docs-only sprint).

## Решение

### S23 scope: v0.5 honest close ship

**v0.5 final status declaration:**

- **Infrastructure: ✅ COMPLETE** — 16/30/74/45 + 38 components + 38 ADRs + 25 sprint pages
- **Strategy validation: ❌ NEGATIVE conjoint × 5 hypotheses** —
  | # | Hypothesis | Sprint | Trades | Verdict |
  |---|-----------|--------|--------|---------|
  | 1 | EMA crossover 1H | S13 | 20 | FAIL T1+T2+T4+T5 |
  | 2 | Mean-reversion multi-symbol 1H | S15 | 108 | FAIL T6+MC+DSR |
  | 3 | Mean-reversion BTC-only relaxed 1H | S17 | 59 | FAIL T5 count, **5/6+DSR+MC PASS** |
  | 4 | Mean-reversion BTC-only relaxed 15M | S20 | 73 | FAIL T1+T2+T4+T5+T6 |
  | 5 | Mean-reversion BTC-only relaxed 4H | S22 | 62 | FAIL T5 count, **5/6+DSR+MC PASS** |
- **MVP DONE per acceptance-criteria.md: NOT achieved conjoint**
- **Mainnet exposure: 0**
- **Tag: `v0.1.0-alpha.23`** = v0.5 honest close marker

### CRITICAL INSIGHT (S22 institutional knowledge)

**T5 floor 100 structurally unreachable на BTC-only mean-reversion regardless of timeframe.**

Empirical evidence:
- S17 BTC 1H: 59 trades
- S20 BTC 15M: 73 trades
- S22 BTC 4H: 62 trades

3 timeframes tested = ~60-73 trades all. **FLAT-only constraint + AND-gate dominate trade count, NOT raw signal frequency.** T5 100 only reachable via multi-symbol aggregation (S15 108 trades) — **out of MVP scope per user 2026-04-26 BTC-only constraint.**

**Implication для MVP achievement (per acceptance-criteria.md):**
- Single-symbol BTC mean-reversion + T5 floor 100 = mathematically incompatible
- Either MVP scope amendment (T5 floor relaxation OR multi-symbol allowed) OR strategy class change (NOT mean-reversion)

### Repeated 5/6+DSR+MC PASS pattern (S17 + S22)

S17 1H + S22 4H both produced:
- T1/T2/T3/T4/T6 PASS
- DSR PASS (n_trials=1 fresh single-trial formula)
- MC p stat-sig (S17 p=0.01, S22 p=0.018)
- ONLY T5 count fails

**Strategy edge regime-INDEPENDENT (works на 1H AND 4H equally).** Не frequency-bound, не timeframe-bound. Limited by FLAT-only constraint trade count, не signal quality.

### S23 deliverables (docs-only)

**T1: ADR 0038 (this document)** — accepted, status final.

**T2: sprint-23-honest-close-v05 page** — canonical v0.5 final close summary с:
- Final v0.5 status (5 hypotheses tested negative conjoint)
- T5 100 structurally unreachable insight (3 timeframes empirical)
- Repeated 5/6+DSR+MC PASS pattern (S17+S22) preserved
- Cross-trial log archival policy
- All carry-overs preserved (16+ items)

**T3: cross_trial_sharpes archival** (4-th archival, mirror S16/S18/S21):
```bash
mv data/cross_trial_sharpes.json data/cross_trial_sharpes_v0.5-final.json
echo '{"trials": []}' > data/cross_trial_sharpes.json  # v0.6 fresh baseline
```

**T4: Wiki sync** — current-state.md + index.md + counts (ADR 37→38, sprint pages 24→25).

**T5: log.md sprint-end entry**.

**T6: SPRINT_STATE → between-sprints с post-v0.5-honest-close status**.

**T7: PHASE 8 ship** — tag `v0.1.0-alpha.23` (v0.5 honest close marker).

### Cross-cutting concerns (binding)

- **CC1 T5 100 structurally unreachable BINDING institutional knowledge** — 3 timeframes empirical evidence (S17 1H 59 / S20 15M 73 / S22 4H 62). v0.6+ MUST address: multi-symbol revival (out of MVP) OR strategy class change OR MVP T5 floor amendment OR pause.
- **CC2 cross_trial_sharpes archival policy BINDING** (mirror S16/S18/S21) — v0.6 fresh hypothesis archives к `_v0.5-final.json` + reset.
- **CC3 Repeated 5/6+DSR+MC PASS pattern (S17+S22) preserved** — strategy edge regime-INDEPENDENT, не timeframe-bound. v0.6-A hybrid ML может combine S17 (59) + S22 (62) trades для small-sample CPCV (combined ~120 trades).
- **CC4 Hudson & Urquhart 2021 partial-validation** — confirmed для 15M (S20 degradation) but NOT для 4H (S22 PASSES same criteria as 1H S17). 4H result CONTRADICTS hypothesis "mean-reversion better at lower frequencies" — strategy edge timeframe-stable in 1H-4H range.
- **CC5 Tag semantics**: `v0.1.0-alpha.23` = v0.5 honest close marker, NOT MVP DONE.
- **CC6 No spec amendment** — acceptance-criteria.md preserved.
- **CC7 Multi-symbol + 15M + 4H infrastructure preserved post-MVP** — S15+S19+S22 work не trash.

### v0.6+ direction options (deferred к operator)

**(v0.6-A) Hybrid mean-reversion + ML XGBoost filter**
- S17 + S22 combined ~120 trades — small-sample ML potentially viable (vs n=59 alone trader-rejected)
- CPCV framework + feature engineering + model registry
- Cost: 5-10 sprints
- ML evidence: 2 timeframes both showed regime-independent edge — ML may capture context

**(v0.6-B) HMM regime-switch + mean-reversion**
- Addresses fold concentration (S17 fold #5, S22 fold #3, S20 fold #2)
- Cost: 4-6 sprints (architecture-corrected from 3-5)

**(v0.6-C) Multi-symbol revival post-MVP**
- ONLY path к T5 ≥100 conjoint pass per S22 critical insight
- Out of MVP scope per user 2026-04-26 (BTC-only)
- Reconsider если operator decides post-MVP OR amends MVP scope

**(v0.6-D) Different strategy class entirely**
- Donchian breakout, ATR-bands, regime-detection
- Departs from mean-reversion family — fresh hypothesis space

**(v0.6-E) Project pause** — 5 hypotheses tested + T5 structural insight = strong publishable contribution. Cost: 0.

**(v0.6-F) MVP T5 floor amendment** — operator decides если spec amendment justified. Empirical evidence: BTC-only mean-reversion max ~73 trades. T5 floor 100 vs 60-70 = ~30% gap. Either widen T5 floor (to 60? 75?) OR allow multi-symbol в MVP. Spec amendment would update acceptance-criteria.md (currently immutable per ADR pattern).

**Operator decides if/when. No commitment from S23.**

## Последствия

**Plus:**
- 5 empirical measurements documented (S13 + S15 + S17 + S20 + S22 across 4.81y BTC)
- 24 sprints infrastructure preserved + reusable
- T5 100 structurally unreachable evidence = institutional knowledge для v0.6 hypothesis selection
- Strategy edge regime-independent finding (S17+S22 both PASS criteria except T5 count)
- Pre-committed honest close (per ADR 0037 BINDING) — clean failthrough
- 0 capital exposure
- Pattern reuse от S14/S16/S18/S21 (5-th honest close = stable workflow)

**Minus:**
- 5 strategy hypotheses FAIL conjoint per acceptance-criteria.md spec
- T5 100 structural limit constrains future MVP attempts (BTC-only mean-reversion = max ~73 trades)
- All previous carry-overs unaddressed (16+ items)
- ML/HMM/regime-detection frameworks deferred (v0.6+ infrastructure new)
- MVP DONE на BTC-only mean-reversion structurally hard — requires spec amendment OR strategy class pivot

**v0.6+ carry-overs preserved (anticipated):** All previous + new:
- T5 100 structural insight (S17+S20+S22 evidence)
- S17+S22 combined ~120 trades — ML training basis для v0.6-A
- 4H Bybit backfill API hung issue (resample workaround used) — investigation deferred
- 5th map missed by architecture review (S22) — review template improvement

## Связанные документы

- [[../decisions/0037-sprint-22-4h-test]] — S22 ADR (FAIL trigger)
- [[../decisions/0036-sprint-21-honest-close-v04]] — S21 v0.4 honest close (precedent)
- [[../decisions/0033-sprint-18-honest-close-v01]] — S18 v0.1 honest close (precedent)
- [[../decisions/0031-sprint-16-honest-close-v02]] — S16 v0.2 honest close (precedent)
- [[../decisions/0029-sprint-14-honest-close]] — S14 first honest close (precedent pattern)
- [[../sprints/sprint-22-4h-test]] — S22 measurement
- [[../sprints/sprint-17-btc-mean-reversion-relaxed]] — S17 partial signal на 1H (similar к S22 pattern)
- [[../architecture/acceptance-criteria]] — T1-T6 thresholds (immutable)
- [[../sprints/sprint-23-honest-close-v05]] — спринт delivery record

## Поправки

- (none yet)
