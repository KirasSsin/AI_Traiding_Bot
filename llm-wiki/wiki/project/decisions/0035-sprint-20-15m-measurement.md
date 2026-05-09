---
title: 0035. Sprint 20 — BTC 15M WFA measurement (verdict FAIL, T5 failthrough triggered)
type: decision
date: 2026-04-26
sprint: 20
tags: [adr, sprint-20, btc-15m, mean-reversion, measurement-sprint, verdict-fail, t5-failthrough-triggered, hypothesis-4-tested]
sources:
  - project/pre-s19-backlog.md
  - project/decisions/0034-sprint-19-15m-architecture.md
  - project/sprints/sprint-19-15m-architecture.md
  - project/architecture/acceptance-criteria.md
status: accepted
---

# 0035. Sprint 20 — BTC 15M WFA measurement (verdict FAIL)

**Status:** accepted
**Date:** 2026-04-26

## Контекст

S19 shipped (PR #27, tag `v0.1.0-alpha.19`). Architectural prep complete. 167,383 bars BTCUSDT 15M ready. 7 amendments pre-registered BINDING.

S20 = measurement sprint per pre-registered ADR 0034 command:
```bash
SPRINT_N=20 .venv/bin/python -m src wfa --symbol BTCUSDT --interval 15 \
  --start 2021-07-15 --end 2026-04-26
```

User confirm "T5 ≥ 150" before measurement → T-Amendment 1 binding accepted.

## Решение

### S20 measurement results — VERDICT FAIL

| Criterion | Threshold | S20 result | Status |
|-----------|-----------|------------|--------|
| T1 Sharpe OOS | ≥1.0 | **-45.57** | ❌ FAIL |
| T2 Sortino OOS | ≥1.5 | -345.70 | ❌ FAIL |
| T3 MaxDD | <0.25 | 0.021 | ✅ PASS |
| T4 win/RR | RR≥1.5 → win≥45% OR RR≥2 → win≥35% | win 30.1% / RR 1.39 | ❌ FAIL (RR<1.5) |
| **T5 n_trades** | **≥150 (T-Amendment 1)** | **73** | ❌ **FAIL count** (failthrough triggered) |
| T5 t_stat | ≥2.0 | -2.08 | ❌ FAIL (negative) |
| T6 OOS/IS sharpe ratio | ≥0.7 | **-37.13** | ❌ FAIL |
| DSR | >0 | 0.030 | ✅ PASS (n_trials=1 single-trial low bar) |
| MC p-value | ≤0.05 | 0.044 | ✅ PASS (borderline) |
| **Acceptance gate (composite)** | sharpe + MC | sharpe FAIL (folds 0+1+2 below 0.7) | ❌ FAIL |

### Fold concentration check (T-Amendment 2 BINDING)

```
fold_sharpe_ratios: [-0.74, -4.83, -185.21, +2.27, +2.84]
mean = -37.13
fold #2 = -185.21 catastrophic outlier (REGIME CONCENTRATION negative direction)
```

T-Amendment 2 verdict: **REGIME CONCENTRATION confirmed** — fold #2 (-185.21) drives mean negative. Removing fold #2: mean = (-0.74 - 4.83 + 2.27 + 2.84)/4 ≈ +0.13 (still не ≥0.7 threshold). Strategy fails regardless of outlier removal.

### Frequency math reconciliation

S17 BTC 1H baseline: 59 trades (RSI 35/65 + BB 1.5σ AND-gated).
S20 BTC 15M predicted (architecture frequency math 4x): ~236 trades.
**S20 BTC 15M actual: 73 trades.**

AND-gate joint multiplier на 15M ≈ 1.24x baseline (vs predicted 4x). Hudson & Urquhart 2021 academic prior CONFIRMED empirically: mean-reversion regime degrades sub-hourly. RSI-BB AND-gate correlation pattern weakens на noisier 15M signals — fewer joint trigger events чем pure frequency increase would predict.

### S20 verdict: FAIL

Per ADR 0034 amendment 3 BINDING (T5 count failthrough):
> "If OOS trades < 150 → VERDICT FAIL declared on T5 count alone, t_stat skipped."

T5 count = 73 < 150 → FAIL triggered. Additional failures: T1 (-45.57), T2 (-345), T4 (RR 1.39<1.5), T6 (-37.13).

Hudson & Urquhart 2021 academic prior empirically validated. Fold concentration check (T-Amendment 2) confirms negative regime concentration.

### S21 = honest close v0.4 (pre-committed per ADR 0034 BINDING)

Per ADR 0034 BINDING:
> "FAIL → S21 = honest close v0.4 (4 hypotheses tested = even stronger publishable scientific contribution)"

S21 docs-only sprint mirroring S14/S16/S18 pattern (4-th honest close в проекте).

### S20 deliverables (measurement only)

- T1: ADR 0035 (this document) — accepted
- T2: sprint-20 page documenting verdict + fold breakdown
- T3: cross_trial_sharpes.json updated (S20 trial entry persisted automatically)
- T4: wiki sync (current-state, index, log, SPRINT_STATE)
- T5: PHASE 8 ship (tag v0.1.0-alpha.20)

NO code changes. NO new infrastructure. Pure measurement + documentation.

### Cross-cutting concerns (binding, для S21 honest close)

- **CC1 (Hudson & Urquhart 2021 empirically validated)**: 15M mean-reversion на BTC degrades vs 1H. Frequency increase 4x → actual joint trigger increase 1.24x. Documented для v0.5+ hypothesis selection.
- **CC2 (Annualization parameterization paid off)**: bars_per_year=35040 correctly applied — T1=-45.57 IS the genuine S20 result, не -22 understimate. Architecture Condition A3 prevented false-PASS на 15M.
- **CC3 (Fold concentration negative direction)**: REGIME CONCENTRATION pattern observed — strategy fails on most folds + extreme negative outlier. Different from S17 (positive fold #5 outlier). Both = high-variance failure mode.
- **CC4 (cross_trial_sharpes)**: S20 trial entry persisted (sprint=20, oos_sharpe=-37.13). Per S16/S18 pattern, S21 honest close archives к `_v0.4-final.json` + reset для v0.5.
- **CC5 (Tag semantics)**: `v0.1.0-alpha.20` = measurement sprint marker (FAIL verdict).
- **CC6 (No spec amendment)**: acceptance-criteria.md preserved.
- **CC7 (S17 partial signal contradicted at 15M)**: S17 BTC 1H MC p=0.01 was real signal, но fragile to timeframe shift. v0.5+ hypothesis must consider: 1H regime-specific edge (revisit option B hybrid ML на 1H signal? OR 4H higher-stability test?).

## Последствия

**Plus:**
- Pre-registered binding criteria honored (T5 floor 150, fold concentration check applied)
- Annualization parameterization (Condition A3) paid off — correct T1=-45.57 reported, не false-PASS
- 4-th hypothesis tested = stronger evidence base для honest close v0.4
- Hudson & Urquhart 2021 academic prior empirically validated
- Honest failure mode documentation (negative fold concentration)

**Minus:**
- 4-th strategy hypothesis FAIL — diminishing returns argument для continued investment
- v0.5+ requires reconsidering hypothesis class (mean-reversion 1H worked partially, 15M doesn't)
- All previous carry-overs preserved (16+ items)

**v0.5+ direction options (deferred к operator):**

- **(v0.5-A)** Hybrid 1H mean-reversion + ML XGBoost filter — S17 partial signal на 1H + ML enhancement. Cost: 5-10 sprints CPCV framework. Most evidence-supported.
- **(v0.5-B)** 4H mean-reversion — lower frequency, может cleaner regime-specific edge (S17 evidence на 1H suggests regime-specific). Cost: 1-2 sprints.
- **(v0.5-C)** Regime-switch HMM + mean-reversion — context layer addresses fold #2 catastrophic regime. Cost: 3-5 sprints.
- **(v0.5-D)** Project pause — 4 hypotheses tested, infrastructure preserved.

## Связанные документы

- [[../decisions/0034-sprint-19-15m-architecture]] — S19 ADR (pre-registered amendments triggered)
- [[../sprints/sprint-19-15m-architecture]] — S19 architectural prep
- [[../sprints/sprint-17-btc-mean-reversion-relaxed]] — S17 partial signal (1H, contradicted at 15M)
- [[../architecture/acceptance-criteria]] — T1-T6 thresholds (immutable)
- [[../sprints/sprint-20-15m-measurement]] — спринт delivery record

## Поправки

- (none yet)
