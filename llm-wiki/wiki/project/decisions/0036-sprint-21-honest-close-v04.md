---
title: 0036. Sprint 21 — v0.4 honest close (4 hypotheses tested, Hudson & Urquhart 2021 empirically validated)
type: decision
date: 2026-04-26
sprint: 21
tags: [adr, sprint-21, honest-close-v04, hypothesis-4-tested, hudson-urquhart-validated, n-trials-archival, v0.5-readiness, regime-specific-1h]
sources:
  - project/decisions/0035-sprint-20-15m-measurement.md
  - project/decisions/0034-sprint-19-15m-architecture.md
  - project/decisions/0033-sprint-18-honest-close-v01.md
  - project/sprints/sprint-20-15m-measurement.md
  - project/architecture/acceptance-criteria.md
status: accepted
---

# 0036. Sprint 21 — v0.4 honest close (4 hypotheses tested)

**Status:** accepted
**Date:** 2026-04-26

## Context

S20 shipped (PR #28, tag `v0.1.0-alpha.20`). BTC 15M WFA measurement verdict FAIL — T5 count failthrough triggered (73 trades < 150 floor). Per ADR 0034 amendment 3 BINDING:

> "FAIL → S21 = honest close v0.4 (4 hypotheses tested = even stronger publishable scientific contribution)"

S21 = pre-committed honest close, no new brainstorm. Pattern mirrors S14 ADR 0029 / S16 ADR 0031 / S18 ADR 0033 (4-th honest close в проекте).

## Decision

### S21 scope: v0.4 honest close ship

**v0.4 final status declaration:**

- **Infrastructure: ✅ COMPLETE** — 16 FSM states / 30 events / 74 transitions / 45 reason codes / 38 component pages / 36 ADRs (включая 0036) / 23 sprint pages / WFA + DSR + MC + cross-trial log + multi-symbol CLI + 15M timeframe + annualization parameterization + 4 strategy hypotheses tested
- **Strategy validation: ❌ NEGATIVE conjoint × 4 hypotheses** —
  | # | Hypothesis | Sprint | OOS Trades | Pass criteria | Verdict |
  |---|-----------|--------|-----------|--------------|---------|
  | 1 | EMA(12)×(26) + ADX(14) + RSI(14) + ATR(14) на 1H BTCUSDT | S13 (4.81y) | 20 | T3 only | FAIL (T1+T2+T4+T5) |
  | 2 | Mean-reversion RSI<30 AND close<lower_BB(20, 2σ) на 1H × 3 sym BTC+ETH+SOL | S15 | 108 | T1-T4 | FAIL (T6+MC+DSR) |
  | 3 | Mean-reversion RSI<35 AND close<lower_BB(20, 1.5σ) на 1H BTCUSDT relaxed | S17 | 59 | T1-T4+T6+DSR+MC | FAIL (T5 count only) |
  | 4 | Mean-reversion RSI<35 AND close<lower_BB(20, 1.5σ) на **15M** BTCUSDT | S20 | 73 | T3 only (DSR/MC borderline) | FAIL (T1+T2+T4+T5+T6) |
- **MVP DONE per acceptance-criteria.md: NOT achieved conjoint** (no single hypothesis passed T1-T6 + DSR + MC conjointly)
- **Mainnet exposure: 0** (Bybit demo 33min only since S12)
- **Tag: `v0.1.0-alpha.21`** = v0.4 honest close marker

### Critical scientific findings (v0.4 institutional knowledge)

**Finding 1 (S17 partial signal на 1H):** Mean-reversion RSI+BB AND-gated trigger на BTCUSDT 1H produces statistically significant signal (MC p=0.01 + DSR=1.0 + T1=25.99 + 5/6 PASS на 59 trades). Sample size insufficient на 1H BTC alone — frequency structural limit ~60-70 trades / 4.81y maximum.

**Finding 2 (S20 frequency-dimension hypothesis FALSIFIED):** Same RSI 35/65 + BB 1.5σ params at 15M produced T1=-45.57 (vs 1H +25.99). AND-gate joint multiplier ~1.24x baseline (predicted 4x). **Hudson & Urquhart 2021 empirically validated — mean-reversion regime degrades sub-hourly на BTC.**

**Finding 3 (Signal regime-specific к 1H):** S17 partial signal не frequency-bound. Fragile к timeframe shift. Suggests:
- v0.5 must preserve 1H timeframe (not pursue 4H lower-frequency OR 5M higher-frequency без strong hypothesis)
- Hybrid ML filter (S17 evidence supports — partial signal exists для ML к learn from)
- Regime-switch detection may capture S17 fold #5 positive regime context

**Finding 4 (Annualization parameterization paid off):** S20 T1=-45.57 IS genuine result, не -22.78 understimate. Architecture Condition A3 (S19) prevented false-PASS на 15M. Investment в proper annualization paid off на first 15M measurement.

### S21 deliverables (docs-only)

**T1: ADR 0036 (this document)** — accepted, status final.

**T2: sprint-21-honest-close-v04 page** — canonical v0.4 final close summary с:
- Final v0.4 status declaration (4 hypotheses tested negative conjoint)
- All measurement results trail (S13 + S15 + S17 + S20 aggregated)
- S17 partial signal evidence preserved (institutional knowledge для v0.5)
- Hudson & Urquhart 2021 empirical validation documented
- Cross-trial log archival policy
- All carry-overs preserved (16+ items + S20 new)

**T3: cross_trial_sharpes archival**:
```bash
mv data/cross_trial_sharpes.json data/cross_trial_sharpes_v0.4-final.json
echo '{"trials": []}' > data/cross_trial_sharpes.json  # v0.5 fresh baseline
```

**T4: Wiki sync** — current-state.md + index.md updated к "v0.4 closed honest" + counts (ADR 35→36, sprint pages 22→23).

**T5: log.md sprint-end entry** — chronological closure event.

**T6: SPRINT_STATE → between-sprints с post-v0.4-honest-close status** — operator decides v0.5 future direction.

**T7: PHASE 8 ship** — sprint-finish: tag `v0.1.0-alpha.21` (v0.4 honest close marker).

### NO new code, NO measurement re-run

Per pre-committed ADR 0034 BINDING. S21 = documentation + archival policy. Q7-S12 zero-migration constraint preserved trivially.

### Cross-cutting concerns (binding)

- **CC1 (S17 partial signal preserved для v0.5+):** Mean-reversion RSI+BB на 1H BTC = regime-specific signal, MC p=0.01 stat-sig. Documented для v0.5 hypothesis selection (option v0.5-A hybrid ML supports — partial signal exists).
- **CC2 (cross_trial_sharpes archival policy — BINDING, mirrors S16/S18 CC2):** v0.5 fresh hypothesis MUST archive `data/cross_trial_sharpes.json` (containing `[{sprint:20, oos_sharpe:-37.13}]`) к `data/cross_trial_sharpes_v0.4-final.json` + reset к `[]`. Without this policy, future sprint inherits S20 anchor — biases new hypothesis testing. Implemented в S21 T3.
- **CC3 (Hudson & Urquhart 2021 empirically validated — BINDING institutional knowledge):** Document для v0.5+ hypothesis selection. 15M mean-reversion на BTC degrades vs 1H. Future timeframe-shift hypotheses должны cite это finding.
- **CC4 (Frequency-dimension hypothesis FALSIFIED):** S20 = direct empirical test of hypothesis "15M solves T5 sample insufficiency". REJECTED. v0.5 must reconsider hypothesis class (hybrid ML / regime-switch / pause), не pursue further timeframe shifts blindly.
- **CC5 (Tag semantics):** `v0.1.0-alpha.21` = v0.4 honest close marker, NOT MVP DONE.
- **CC6 (No spec amendment):** acceptance-criteria.md NOT modified. T1-T6 thresholds stand. T5 floor 150 (S20 ADR 0034 amendment) was sprint-specific pre-registration, не permanent.
- **CC7 (Multi-symbol + 15M infrastructure preserved post-MVP):** S15+S19 work не trash. Available для v0.5+ revival если needed.

### Future direction options (deferred к operator)

Per S20 evidence accumulation + S17 institutional knowledge:

**(v0.5-A) Hybrid 1H mean-reversion + ML XGBoost filter** — STRONGEST evidence-supported per S17 (partial signal exists для ML к learn from). S15 ADR 0030 deferred ML на basis "no partial signal evidence" — S17 CONTRADICTS this rationale. CPCV framework new infrastructure. Cost: 5-10 sprints. Most academically supported.

**(v0.5-B) Regime-switch HMM + mean-reversion** — addresses S17 fold #5 + S20 fold #2 catastrophic outliers. Context layer detects market regime, applies strategy conditionally. Cost: 3-5 sprints.

**(v0.5-C) 4H mean-reversion test** — lower frequency может match regime-specific stability. Counter-evidence per S17 (1H regime worked partially) + Hudson & Urquhart 2021 (lower frequencies typically work better для mean-reversion). Cost: 1-2 sprints. Cheap test if operator interested.

**(v0.5-D) Project pause** — close current branch, freeze repo as "v0.4 honest close marker — infrastructure complete + 4 strategy hypotheses tested + 1 partial signal observed (institutional knowledge)". Reactivate if новый candidate emerges. Cost: 0 sprints.

**Operator decides if/when. No commitment from S21.**

## Consequences

**Plus:**
- Honest closure based on 4 empirical measurements (S13 + S15 + S17 + S20 across 4.81y BTC Bybit Spot)
- 22 sprints infrastructure preserved + reusable для v0.5 attempts (15M timeframe + annualization parameterization + multi-symbol + cross_trial_sharpes infrastructure all production-ready)
- DSR cross-trial accumulator broken cleanly via archival policy (mirrors S16/S18 pattern — 3rd archival)
- S17 partial signal evidence preserved для v0.5-A (hybrid ML reconsideration)
- Hudson & Urquhart 2021 empirically validated — institutional knowledge для timeframe-shift hypotheses
- Pre-committed honest close (per ADR 0034 BINDING) — clean failthrough execution, no p-hacking pressure
- 0 capital exposure (no Mainnet)
- Pattern reuse от S14 ADR 0029 + S16 ADR 0031 + S18 ADR 0033 (4-th honest close = stable workflow)

**Minus:**
- "MVP DONE" не achieved conjoint per acceptance-criteria.md spec (no spec amendment)
- 4 strategy hypotheses (EMA crossover + multi-symbol mean-reversion + BTC-only mean-reversion 1H + BTC mean-reversion 15M) empirically rejected на conjoint T1-T6 + DSR + MC
- Frequency-dimension hypothesis FALSIFIED — limits v0.5 option space
- All previous carry-overs unaddressed (16+ items remain open)
- ML XGBoost framework remains deferred (CPCV pipeline new infrastructure для v0.5-A)

**v0.5+ carry-overs preserved (anticipated):**

All previous + new from S20:
- F live demo Mainnet validation actual run (operator-driven, not run since S12)
- FillRecorderAdapter Layer 2 schema link
- 3-way endpoint enum (DEMO/TESTNET/MAINNET)
- T2 review C3 init_db dual-conn comment
- DSR per-fold DataFrame→TradeRecord conversion
- DSR threshold calibration
- halt_log INSERT order swap в `_set_halt`
- find_by_order_id ORDER BY explicit
- fill-history.md / bybit-adapter.md / ws-private-consumer.md component page updates
- T2/T5/T6 quant-stats deferred concerns (Sortino formula docs, sqrt(8760) frequency-agnostic — closed S19 Condition A3, boundary tests)
- 48h Bybit demo validation
- Multi-symbol live runtime fan-out (S15 deferred — `_cmd_run` kept single-symbol)
- Capital allocation cross-symbol exposure caps (S15 deferred — out of MVP)
- S17 fold #5 + S20 fold #2 outliers (regime concentration patterns — addresses by v0.5-B HMM if pursued)
- S17 partial signal preserved (mean-reversion 1H institutional knowledge для v0.5-A)
- Hudson & Urquhart 2021 empirical validation (15M degradation на BTC)

## Related

- [[../decisions/0035-sprint-20-15m-measurement]] — S20 ADR (verdict FAIL trigger)
- [[../decisions/0034-sprint-19-15m-architecture]] — S19 ADR (binding criteria triggered)
- [[../decisions/0033-sprint-18-honest-close-v01]] — S18 v0.1 honest close (precedent)
- [[../decisions/0031-sprint-16-honest-close-v02]] — S16 v0.2 honest close (precedent)
- [[../decisions/0029-sprint-14-honest-close]] — S14 v0.1 first honest close (precedent pattern)
- [[../sprints/sprint-20-15m-measurement]] — S20 measurement results
- [[../sprints/sprint-17-btc-mean-reversion-relaxed]] — S17 partial signal на 1H (preserved для v0.5)
- [[../architecture/acceptance-criteria]] — T1-T6 thresholds (immutable)

## Amendments

- (none yet)
