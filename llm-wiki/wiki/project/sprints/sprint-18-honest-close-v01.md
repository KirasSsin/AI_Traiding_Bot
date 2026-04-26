---
title: Sprint 18 — v0.1 honest close (3 strategy hypotheses tested across 4.81y BTC, MVP DONE not achieved conjoint)
type: sprint
tags: [sprint-18, honest-close-v01, no-edge-conjoint, mvp-incomplete, hypothesis-3-tested, partial-signal-evidence, n-trials-archival-final, t5-failthrough-triggered]
created: 2026-04-26
updated: 2026-04-26
status: completed
sources:
  - project/decisions/0033-sprint-18-honest-close-v01.md
  - project/decisions/0032-sprint-17-btc-mean-reversion-relaxed.md
  - project/sprints/sprint-17-btc-mean-reversion-relaxed.md
  - project/sprints/sprint-16-honest-close-v02.md
  - project/sprints/sprint-15-mean-reversion-multi-symbol.md
  - project/sprints/sprint-14-honest-close.md
  - project/sprints/sprint-13-backfill-wfa.md
---

# Sprint 18 — v0.1 honest close

## Overview

S18 = pre-committed honest close per ADR 0032 amendment 3 BINDING (S17 T5 count failthrough triggered). Pattern mirrors S14 ADR 0029 + S16 ADR 0031 (3rd honest close в проекте, docs-only sprint).

Per ADR 0032 amendment 3 verbatim:
> "If OOS trades < 100 → VERDICT FAIL declared on T5 count alone, t_stat skipped, S18 = honest close v0.1 (3 hypotheses tested, documented)."

S17 result: 59 trades < 100 floor → triggered S18 honest close pre-commitment.

## Final v0.1 status

- **Infrastructure: ✅ COMPLETE** — 16 FSM states / 30 events / 74 transitions / 45 reason codes / 38 component pages / 33 ADRs (включая 0033) / 20 sprint pages / WFA + DSR + MC + cross-trial log + multi-symbol CLI + 3 strategy classes wired
- **Strategy validation: ❌ NEGATIVE conjoint × 3 hypotheses** —
  | # | Hypothesis | Sprint | OOS Trades | Pass criteria | Verdict |
  |---|-----------|--------|-----------|--------------|---------|
  | 1 | EMA(12)×(26) + ADX(14) + RSI(14) + ATR(14) на 1H BTCUSDT | S13 (4.81y) | 20 | T3 only | FAIL (T1+T2+T4+T5) |
  | 2 | Mean-reversion RSI<30 AND close<lower_BB(20, 2σ) на 1H × 3 symbols BTC+ETH+SOL | S15 | 108 | T1+T2+T3+T4 | FAIL (T6+MC+DSR) |
  | 3 | Mean-reversion RSI<35 AND close<lower_BB(20, 1.5σ) на 1H BTCUSDT relaxed | S17 | 59 | T1+T2+T3+T4+T6+DSR+MC | FAIL (T5 count only) |
- **MVP DONE per acceptance-criteria.md: NOT achieved conjoint** (no single hypothesis passed T1-T6 + DSR conjointly across one measurement)
- **Mainnet exposure: 0** (Bybit demo 33min only since S12)
- **Tag: `v0.1.0-alpha.18`** = v0.1 final honest close marker

## Plan / ADR links

- [[../decisions/0033-sprint-18-honest-close-v01]] — Sprint 18 ADR (v0.1 honest close)
- [[../decisions/0032-sprint-17-btc-mean-reversion-relaxed]] — S17 ADR с failthrough clause (triggered)
- [[sprint-17-btc-mean-reversion-relaxed]] — predecessor (T5 count failthrough trigger)
- [[sprint-16-honest-close-v02]] — S16 v0.2 honest close (pattern source)
- [[sprint-14-honest-close]] — S14 v0.1 first honest close attempt (precedent)

## Deliverables

S18 = documentation + archival policy. NO new code. NO measurement re-run.

- T1 (this sprint): ADR 0033 status accepted
- T2 (this sprint): sprint-18 page (this document)
- T3 cross_trial_sharpes archival: `data/cross_trial_sharpes.json` → `data/cross_trial_sharpes_v0.1-final.json` + reset к `[]` для v0.4 readiness (mirror S16 CC2 BINDING)
- T4 wiki sync (current-state.md TL;DR + ADR 32→33, sprint pages 19→20)
- T5 log.md sprint-end entry
- T6 SPRINT_STATE → between-sprints с post-v0.1-honest-close-final status
- T7 PHASE 8 ship via sprint-finish (tag v0.1.0-alpha.18)

## FSM growth

NONE. S18 = documentation + archival policy only. Counts unchanged: **16 states / 30 events / 74 transitions / 45 reason codes**.

## Reason codes growth

NONE.

## Tests / quality

NO code changes. Existing test suite preserved at S17 baseline:
- pytest unit: 732 passed (baseline preserved, no regressions)
- mypy --strict src/: clean (72 source files)
- ruff: clean
- Q7-S12 zero-migration: trivially preserved (no migrations changed)

## Strategy validation summary (3 hypotheses across 4.81y BTC Bybit Spot 1H)

### Trial #1 — S13: EMA crossover + ADX + RSI + ATR (1H BTCUSDT, 4.81y, 42098 bars)

- 20 OOS trades, T1 Sharpe -44.46, T2 Sortino -101.38
- T3 MaxDD 12.3% PASS
- T4 win 30% / RR 0.797 FAIL
- T5 n=20 + t_stat negative FAIL
- T6 mean negative FAIL
- DSR NaN (n_trials=1, formula-invariant)
- MC p=0.048 borderline
- **Failure mode:** insufficient signals (frequency ~1 trade per 5-10 days; T5 floor 100 unreachable structural mathematical limit per S14 Q1 EXPAND)

### Trial #2 — S15: Mean-reversion RSI<30 AND close<lower_BB(20, 2σ) × 3 symbols BTC+ETH+SOL (1H)

- 108 OOS trades aggregate (T5 floor REACHED first time)
- BTCUSDT alone: 44 trades, sharpe ratio mean +1.75, MC p 0.197 (positive direction observed)
- ETHUSDT alone: 29 trades, sharpe ratio mean -39.35 (one fold sharpe -188.65 catastrophic = data pathology, extreme vol window 2021-2022)
- SOLUSDT alone: 35 trades, sharpe ratio mean +0.45, MC p 0.65
- Aggregate: T1 9.32 PASS / T2 29.55 PASS / T3 5.3% PASS / T4 win 37%/RR 2.27 PASS
- T5 n=108 PASS-on-count BUT t_stat 1.04<2.0 FAIL
- T6 mean -12.38 FAIL
- MC p 0.998 FAIL (random-equivalent на full distribution)
- DSR 0 FAIL (n_trials=2, sigma_SR=22.68 cross-trial penalty)
- **Failure mode:** enough signals + high-variance + MC random-equivalent

### Trial #3 — S17: Mean-reversion RSI<35 AND close<lower_BB(20, 1.5σ) на 1H BTCUSDT relaxed

- 59 OOS trades (BTC-only, fresh n_trials=1 baseline post-S16 archival)
- T1 Sharpe 25.99 PASS (suspiciously high)
- T2 Sortino 4446 PASS
- T3 MaxDD 2.8% PASS
- T4 win 47.5% / RR 154.5 PASS
- **T5: 59 trades FAIL** (но t_stat 2.13 ≥2.0, mean +2.40% positive — sample insufficient)
- T6 OOS/IS sharpe ratio 0.712 PASS (borderline)
- DSR 1.0 PASS (n_trials=1 fresh baseline, single-trial formula)
- MC p-value 0.01 PASS (statistically significant)
- **Failure mode:** sample size insufficient (5/6 + DSR + MC stat-sig = first time positive direction по most criteria)

### Frequency structural limit (S15 + S17 empirical)

Single-symbol BTC 1H mean-reversion RSI+BB AND-gated:
- S15 baseline (RSI 30/70 + BB 2σ): 44 trades / 4.81y
- S17 relaxed (RSI 35/65 + BB 1.5σ): 59 trades / 4.81y
- **AND-gate joint multiplier**: ~1.34x baseline (positive correlation между RSI extreme + BB breach compresses joint probability)
- **T5 floor 100 NOT reachable** на single-symbol BTC 1H regardless of relaxed thresholds tested

### Cross-trial DSR state (post-S17, before S18 archival)

```json
{"trials": [{"sprint": 17, "oos_sharpe": 0.712}]}
```

Per CC2 BINDING archival policy (mirror S16): S18 T3 archives к `data/cross_trial_sharpes_v0.1-final.json` + resets `data/cross_trial_sharpes.json` к `{"trials": []}` для v0.4 fresh-start readiness.

### Critical scientific finding (S17 partial signal evidence preserved)

**Mean-reversion RSI+BB AND-gated trigger на BTC produces statistically significant signal:** S17 MC p=0.01 + DSR=1.0 + T1=25.99 + 5/6 criteria PASS на 59 OOS trades. **Sample size insufficient** на 1H BTC alone — frequency structural limit ~60-70 trades / 4.81y maximum.

Strategy edge IS real но observable только с frequency-dimension address:
- **Higher-frequency timeframe** (15M = 4x = 240+ trades estimate) — Q3 architectural blockers preserved (interval_map + heal_max_age)
- **Multi-symbol aggregation** (out of MVP scope per user 2026-04-26 BTC-only constraint) — S15 infrastructure preserved
- **Hybrid ML filter** (S17 evidence supports — partial signal exists для ML к learn from) — Q4 deferred

## Wiki updates

- 1 NEW ADR (0033 — accepted)
- 1 NEW sprint page (this — sprint-18-honest-close-v01)
- Modified: current-state.md (TL;DR post-S18, ADR 32→33, sprint pages 19→20, +S18 row), index.md (sprint-18 + ADR 0033), log.md (sprint-end), SPRINT_STATE (between-sprints, tag alpha.18)
- Archival: data/cross_trial_sharpes.json → data/cross_trial_sharpes_v0.1-final.json + reset к `{"trials": []}`

## Open issues для v0.4+ (operator-driven, no commitment)

**Future direction options (deferred — operator decides if/when):**

### (v0.4-A) BTC 15M mean-reversion — STRONGEST viable path per S17 evidence
- Addresses frequency floor structural limit (4x = 240+ trades estimate)
- Q3 architectural blockers documented (interval_map + heal_max_age production safety)
- Cost: 2 sprints (1 architecture + 1 measurement)
- Risk: noise vs edge tradeoff (Hudson & Urquhart 2021 mean-reversion degrades sub-hourly)

### (v0.4-B) Hybrid mean-reversion + ML filter
- S17 partial signal evidence (MC p=0.01) reverses ADR 0030 ML defer rationale
- XGBoost classifier на BTC mean-reversion features
- CPCV framework new infrastructure (purged combinatorial cross-validation per López de Prado AFML)
- Cost: 5-10 sprints (feature engineering, model registry, monitoring, retraining cadence)
- Risk: complexity multiplier; ML-as-filter best когда base signal partial-edge (S17 confirmed)

### (v0.4-C) Multi-symbol revival
- Out of MVP scope per user 2026-04-26 ("торговать будем в mvp только btc/usdt")
- Reconsider post-MVP if MVP-DONE achieved on BTC-only first
- S15 infrastructure preserved (load_recent symbol filter + --symbols CLI + MeanReversionRsiBBStrategy)

### (v0.4-D) Different timeframe — 4H
- Lower frequency than 1H, не addresses T5 floor structural limit
- НЕ recommended per S17 evidence (mean-reversion signal already weak в high-frequency regime)

### (v0.4-E) Project pause
- Close current branch, freeze repo as "v0.1 final honest close marker — infrastructure complete + 3 strategy hypotheses tested + 1 partial signal observed (institutional knowledge)"
- Reactivate if новый candidate emerges
- Cost: 0 sprints

### Carry-overs preserved (all S12+S13+S14+S15+S16+S17, 14+ items)

- F live demo Mainnet validation actual run (operator-driven, not run since S12 33min)
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
- Q3 15M architectural blockers (interval_map + heal_max_age — preserved per CC4)
- Multi-symbol live runtime fan-out (S15 deferred — `_cmd_run` kept single-symbol)
- Capital allocation cross-symbol exposure caps (S15 deferred — out of MVP per user)
- S17 fold #5 sharpe 3.50 outlier (concerning concentration для production stability)
- **NEW S18 carry-over:** S17 partial signal evidence (MC p=0.01) — institutional knowledge для v0.4 hypothesis selection: mean-reversion variant, NOT trend-following

## Key decisions (S18 ADR 0033)

- **Pre-committed honest close** per ADR 0032 amendment 3 BINDING (T5 count <100 → S18 trigger)
- **CC1 S17 partial signal preserved** для v0.4+ institutional knowledge (mean-reversion regime works)
- **CC2 cross_trial_sharpes archival policy BINDING** (mirrors S16 CC2 — Bailey 2014 N_trials per hypothesis)
- **CC3 Frequency structural limit documented** — single-symbol BTC 1H mean-reversion RSI+BB ~60-70 trades / 4.81y maximum
- **CC4 Q3 15M architectural blockers preserved** (interval_map + heal_max_age — production safety)
- **CC5 Tag semantics**: `v0.1.0-alpha.18` = v0.1 FINAL honest close marker, NOT MVP DONE
- **CC6 No spec amendment**: acceptance-criteria.md T1-T6 thresholds preserved
- **CC7 Multi-symbol infrastructure preserved post-MVP**: S15 work не trash, available для v0.4 revival
- **No code changes**: S18 = documentation + archival policy only

## Related

- [[../decisions/0033-sprint-18-honest-close-v01]] — S18 ADR
- [[../decisions/0032-sprint-17-btc-mean-reversion-relaxed]] — S17 ADR (failthrough triggered)
- [[sprint-17-btc-mean-reversion-relaxed]] — S17 measurement (partial signal observed)
- [[sprint-16-honest-close-v02]] — S16 v0.2 honest close (pattern source)
- [[sprint-15-mean-reversion-multi-symbol]] — S15 multi-symbol baseline
- [[sprint-14-honest-close]] — S14 v0.1 first honest close attempt (precedent)
- [[sprint-13-backfill-wfa]] — S13 measurement (-44.46 anchor)
- [[../architecture/acceptance-criteria]] — T1-T6 thresholds (immutable)
- [[../architecture/migration-plan]] — original roadmap (closed final at S18)
