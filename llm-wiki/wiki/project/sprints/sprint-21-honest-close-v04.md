---
title: Sprint 21 — v0.4 honest close (4 hypotheses tested across 4.81y BTC, MVP DONE not achieved)
type: sprint
tags: [sprint-21, honest-close-v04, no-edge-conjoint, mvp-incomplete, hypothesis-4-tested, hudson-urquhart-validated, partial-signal-preserved, n-trials-archival-final]
created: 2026-04-26
updated: 2026-04-26
status: completed
sources:
  - project/decisions/0036-sprint-21-honest-close-v04.md
  - project/decisions/0035-sprint-20-15m-measurement.md
  - project/decisions/0034-sprint-19-15m-architecture.md
  - project/sprints/sprint-20-15m-measurement.md
  - project/sprints/sprint-19-15m-architecture.md
  - project/sprints/sprint-18-honest-close-v01.md
---

# Sprint 21 — v0.4 honest close

## Overview

S21 = pre-committed honest close per ADR 0034 amendment 3 BINDING (S20 T5 count failthrough triggered). Pattern mirrors S14 ADR 0029 + S16 ADR 0031 + S18 ADR 0033 (4-th honest close в проекте, docs-only sprint).

## Final v0.4 status

- **Infrastructure: ✅ COMPLETE** — 16/30/74/45 + 38 components + 36 ADRs + 23 sprint pages
- **Strategy validation: ❌ NEGATIVE conjoint × 4 hypotheses**
- **MVP DONE: NOT achieved conjoint**
- **Mainnet exposure: 0**
- **Tag: `v0.1.0-alpha.21`** = v0.4 honest close marker

## Verdict

**HONEST CLOSE v0.4** (pre-committed per ADR 0034 BINDING — no new brainstorm).

### 4 hypotheses tested across 4.81y BTC Bybit Spot — all FAIL conjoint

| # | Hypothesis | Sprint | Trades | Pass | Verdict |
|---|-----------|--------|--------|------|---------|
| 1 | EMA crossover trend-following 1H | S13 | 20 | T3 only | FAIL T1+T2+T4+T5 |
| 2 | Mean-reversion multi-symbol 1H | S15 | 108 | T1-T4 | FAIL T6+MC+DSR |
| 3 | Mean-reversion BTC-only relaxed 1H | S17 | 59 | T1-T4+T6+DSR+MC | FAIL T5 count only |
| 4 | Mean-reversion BTC-only relaxed **15M** | S20 | 73 | T3 only | FAIL T1+T2+T4+T5+T6 |

## Plan / ADR links

- [[../decisions/0036-sprint-21-honest-close-v04]] — Sprint 21 ADR (v0.4 honest close)
- [[../decisions/0035-sprint-20-15m-measurement]] — S20 ADR (FAIL trigger)
- [[../decisions/0034-sprint-19-15m-architecture]] — S19 ADR (binding criteria)
- [[sprint-20-15m-measurement]] — predecessor (T5 failthrough triggered)
- [[sprint-18-honest-close-v01]] — S18 v0.1 honest close (precedent pattern)
- [[sprint-16-honest-close-v02]] — S16 v0.2 honest close (precedent)
- [[sprint-14-honest-close]] — S14 first honest close (precedent)

## Deliverables

S21 = documentation + archival policy. NO new code. NO measurement re-run.

| Task | Status | Description |
|------|--------|-------------|
| T1 | ✅ DONE | ADR 0036 accepted |
| T2 | ✅ This commit | sprint-21 page |
| T3 | ✅ DONE | cross_trial_sharpes.json → _v0.4-final.json archival + reset к [] для v0.5 |
| T4 | ✅ This commit | wiki sync (current-state TL;DR + ADR 35→36, sprint pages 22→23, +S21 row) |
| T5 | ✅ This commit | log.md sprint-end |
| T6 | ✅ This commit | SPRINT_STATE → between-sprints, tag alpha.21 |
| T7 | pending | PHASE 8 ship (PR + tag v0.1.0-alpha.21) |

## FSM growth

NONE. S21 = documentation + archival policy only. Counts unchanged: **16/30/74/45**.

## Reason codes growth

NONE.

## Tests / quality

NO code changes. Existing test suite preserved at S20 baseline:
- pytest unit: 732 passed
- mypy --strict src/: clean (72 source files)
- Q7-S12 zero-migration: trivially preserved

## Critical scientific findings (v0.4 institutional knowledge)

### Finding 1 — S17 partial signal на 1H

Mean-reversion RSI+BB AND-gated trigger на BTCUSDT 1H produces statistically significant signal:
- MC p=0.01 (permutation-based, robust к sample size)
- DSR=1.0 (n_trials=1 single-trial formula)
- T1=25.99 + 5/6 criteria PASS на 59 trades

Sample size insufficient на 1H BTC alone — frequency structural limit ~60-70 trades / 4.81y maximum.

### Finding 2 — S20 frequency-dimension hypothesis FALSIFIED

Same RSI 35/65 + BB 1.5σ params at 15M:
- T1=-45.57 (vs 1H +25.99) — opposite direction
- 73 trades (predicted 236, actual ~1.24x baseline vs predicted 4x)

**Hudson & Urquhart 2021 empirically validated** — mean-reversion regime degrades sub-hourly на BTC. Direct empirical contradiction к S15 ADR 0030 frequency hypothesis.

### Finding 3 — S17 signal regime-specific к 1H

S17 partial signal не frequency-bound. Fragile к timeframe shift. Implications для v0.5+:
- Must preserve 1H timeframe (4H lower-frequency OR 5M higher-frequency без strong hypothesis = unsupported)
- Hybrid ML filter may capture S17 fold #5 positive regime context
- Regime-switch HMM addresses S17 fold #5 + S20 fold #2 catastrophic patterns

### Finding 4 — Annualization parameterization (S19 Condition A3) paid off

S20 T1=-45.57 IS genuine result, не -22.78 understimate. Without Condition A3, false-PASS на T1 может trigger continued investment в failing 15M direction. Architecture investment paid off на first 15M measurement.

## Cross-trial DSR state (post-S20, before S21 archival)

```json
{"trials": [{"sprint": 20, "oos_sharpe": -37.13}]}
```

S21 T3 archives к `data/cross_trial_sharpes_v0.4-final.json` + resets `data/cross_trial_sharpes.json` к `{"trials": []}` для v0.5 fresh-start readiness (mirrors S16/S18 CC2 pattern).

## Wiki updates

- 1 NEW ADR (0036 — accepted)
- 1 NEW sprint page (this — sprint-21-honest-close-v04)
- Modified: current-state.md (TL;DR + S21 row + counts ADR 35→36, sprint pages 22→23), index.md (sprint-21 + ADR 0036), log.md (sprint-end), SPRINT_STATE (between-sprints, tag alpha.21)
- Archival: data/cross_trial_sharpes.json → data/cross_trial_sharpes_v0.4-final.json + reset к {"trials": []}

## Open issues для v0.5+ (operator-driven, no commitment)

### (v0.5-A) Hybrid 1H mean-reversion + ML XGBoost filter — STRONGEST evidence-supported
- S17 partial signal evidence (MC p=0.01) provides ML training basis
- S15 ADR 0030 deferred ML на basis "no partial signal evidence" — S17 CONTRADICTS
- CPCV framework (purged combinatorial cross-validation per López de Prado AFML Ch.7)
- Cost: 5-10 sprints (CPCV + feature engineering + model registry + monitoring + retraining)

### (v0.5-B) Regime-switch HMM + mean-reversion
- Addresses S17 fold #5 + S20 fold #2 catastrophic outliers (regime concentration patterns)
- Context layer detects market regime, applies strategy conditionally
- Cost: 3-5 sprints (HMM training pipeline + regime classification + integration)

### (v0.5-C) 4H mean-reversion test
- Lower frequency может match regime-specific stability
- Counter-evidence: Hudson & Urquhart 2021 typically supports lower frequencies для mean-reversion
- Cost: 1-2 sprints. Cheap test.

### (v0.5-D) Project pause
- 4 hypotheses tested + 1 partial signal observed (S17)
- Infrastructure preserved indefinitely
- Cost: 0 sprints

### Carry-overs preserved (all S12-S20, 16+ items)

All previous + new from S20:
- F live demo Mainnet validation actual run (operator-driven, not run since S12 33min)
- FillRecorderAdapter Layer 2 schema link
- 3-way endpoint enum (DEMO/TESTNET/MAINNET)
- T2 review C3 init_db dual-conn comment
- DSR per-fold DataFrame→TradeRecord conversion
- DSR threshold calibration
- halt_log INSERT order swap
- find_by_order_id ORDER BY explicit
- Component pages updates (fill-history, bybit-adapter, ws-private-consumer)
- T2/T5/T6 quant-stats deferred (Sortino formula docs — sqrt(8760) closed S19 Condition A3 — boundary tests)
- 48h Bybit demo validation
- Multi-symbol live runtime fan-out (S15 deferred)
- Capital allocation cross-symbol caps (S15 deferred — out of MVP)
- S17 partial signal evidence (1H regime-specific) — institutional knowledge для v0.5-A
- Hudson & Urquhart 2021 empirical validation (15M degradation) — institutional knowledge для v0.5+

## Key decisions (S21 ADR 0036)

- **Pre-committed honest close** per ADR 0034 amendment 3 BINDING (S20 T5 failthrough triggered)
- **CC1 S17 partial signal preserved** для v0.5-A (hybrid ML reconsideration)
- **CC2 cross_trial_sharpes archival policy BINDING** (mirror S16/S18 — Bailey 2014 N_trials per hypothesis)
- **CC3 Hudson & Urquhart 2021 empirically validated** — institutional knowledge документация для v0.5+
- **CC4 Frequency-dimension hypothesis FALSIFIED** — limits v0.5 option space (no further timeframe shifts blindly)
- **CC5 Tag semantics**: alpha.21 = v0.4 honest close marker, NOT MVP DONE
- **CC6 No spec amendment**: T1-T6 thresholds preserved
- **CC7 Multi-symbol + 15M infrastructure preserved post-MVP**: S15+S19 work не trash
- **No code changes**: docs only

## Related

- [[../decisions/0036-sprint-21-honest-close-v04]] — S21 ADR
- [[../decisions/0035-sprint-20-15m-measurement]] — S20 ADR (FAIL trigger)
- [[../decisions/0034-sprint-19-15m-architecture]] — S19 ADR (binding criteria)
- [[sprint-20-15m-measurement]] — predecessor
- [[sprint-17-btc-mean-reversion-relaxed]] — S17 partial signal preserved
- [[sprint-18-honest-close-v01]] — S18 v0.1 honest close (precedent)
- [[sprint-16-honest-close-v02]] — S16 v0.2 honest close (precedent)
- [[sprint-14-honest-close]] — S14 first honest close (precedent pattern)
- [[../architecture/acceptance-criteria]] — T1-T6 thresholds (immutable)
