---
title: Pre-S22 backlog — v0.5 direction selection (post-v0.4-honest-close)
type: backlog
tags: [sprint-22, brainstorm, phase-2, verdicts, trader-expert, architecture-reviewer, v0.5-direction, post-v0.4-final]
created: 2026-04-26
updated: 2026-04-26
status: open
sources:
  - project/decisions/0036-sprint-21-honest-close-v04.md
  - project/decisions/0035-sprint-20-15m-measurement.md
  - project/decisions/0032-sprint-17-btc-mean-reversion-relaxed.md
  - project/sprints/sprint-21-honest-close-v04.md
  - project/sprints/sprint-20-15m-measurement.md
  - project/sprints/sprint-17-btc-mean-reversion-relaxed.md
  - project/architecture/acceptance-criteria.md
---

# Pre-S22 backlog — v0.5 direction selection

## Context (post-S21 v0.4 honest close)

S21 shipped (PR #29, tag `v0.1.0-alpha.21`). v0.4 closed honest. **4 strategy hypotheses tested across 4.81y BTC Bybit Spot — all FAIL conjoint**.

**Critical scientific findings preserved (institutional knowledge):**

1. **S17 partial signal на 1H confirmed real** — MC p=0.01 stat-sig + DSR=1.0 + T1=25.99 + 5/6 PASS на 59 trades. Sample insufficient (frequency structural limit ~60-70 trades / 4.81y maximum на BTC 1H mean-reversion).

2. **S20 frequency-dimension hypothesis FALSIFIED** — same params at 15M produced T1=-45.57 (vs 1H +25.99). AND-gate joint multiplier 1.24x (predicted 4x). **Hudson & Urquhart 2021 empirically validated** — mean-reversion degrades sub-hourly на BTC.

3. **S17 signal regime-specific к 1H** — не frequency-bound. Fragile к timeframe shift.

4. **Fold concentration patterns** — S17 fold #5 +3.50 outlier positive, S20 fold #2 -185.21 outlier negative. Both = high-variance failure mode. Suggests regime-dependence.

**N_trials reset:** cross_trial_sharpes archived к `_v0.4-final.json`, fresh `[]` для v0.5 (per CC2 BINDING archival policy, mirrors S16/S18).

**User constraint (BINDING):** MVP scope = BTCUSDT only per ADR 0016 + 2026-04-26 confirmation.

**User directive 2026-04-26:** "Зайди с этими вопросами в агентов трейдеров, пусть они проведут дискуссию и выберут" → trader-expert + architecture-reviewer joint dispatch.

## S22 PHASE 2 brainstorming question (1 question — v0.5 direction)

### Q1 — v0.5 direction selection

**Question:** Какое v0.5 направление наиболее обоснованно с учётом 4 hypotheses tested + S17 partial signal preserved + Hudson & Urquhart 2021 validated + frequency structural limit?

**Maintainer recommended option:** (A) Hybrid 1H mean-reversion + ML XGBoost filter — STRONGEST evidence-supported per S17 (partial signal exists для ML к learn from).

**4 options considered:**

- (a) **(v0.5-A) Hybrid 1H mean-reversion + ML XGBoost filter** — S17 partial signal evidence (MC p=0.01) reverses ADR 0030 ML defer rationale ("no partial signal"). XGBoost classifier на BTC mean-reversion features captures regime-specificity. CPCV framework new infrastructure (purged combinatorial cross-validation per López de Prado AFML Ch.7). Cost: 5-10 sprints. **Most evidence-supported.**

- (b) **(v0.5-B) HMM regime-switch + mean-reversion** — Hidden Markov Model detects market regime (trending vs ranging vs volatility), applies mean-reversion strategy conditionally. Addresses S17 fold #5 + S20 fold #2 catastrophic outliers (regime concentration patterns). Cost: 3-5 sprints (HMM training pipeline + regime classification + integration).

- (c) **(v0.5-C) 4H mean-reversion test** — lower frequency может match regime-specific stability. Counter-evidence Hudson & Urquhart 2021 (lower frequencies typically work better для mean-reversion). Direct test of "1H regime works" hypothesis at lower frequency. Cost: 1-2 sprints. Cheap test.

- (d) **(v0.5-D) Project pause** — 4 hypotheses tested + 1 partial signal observed (S17). Infrastructure preserved indefinitely (16/30/74/45 + 38 components + 36 ADRs + 23 sprint pages + WFA + DSR + MC + cross-trial log + multi-symbol CLI + 15M timeframe). Reactivate если новый candidate emerges. Cost: 0 sprints.

**Reasoning for recommended (A):**
- S17 partial signal evidence (MC p=0.01) provides ML training basis — direct contradiction к S15 ADR 0030 ML defer rationale
- ML-as-filter best когда base signal partial-edge (S17 confirmed); useless когда no signal exists (S13 confirmed)
- Regime-specificity findings (S17 fold #5 + S20 fold #2) suggest ML may capture regime context
- Most academically supported v0.5 direction per López de Prado AFML
- Если PASS → MVP DONE strategy criteria → S25+ S1-S6 system + Mainnet pilot
- Если FAIL → 5 hypotheses tested + ML attempt = even stronger publishable scientific contribution

**Risk/concern:**
- 5-10 sprint cost = highest among options (vs B 3-5, C 1-2, D 0)
- CPCV framework new infrastructure — risk of poor implementation invalidating measurement
- Look-ahead bias risks в feature engineering (López de Prado AFML Ch.7 purging discipline mandatory)
- Model decay: production ML needs periodic retraining (post-MVP infrastructure)
- HIDDEN: S17 partial signal MC p=0.01 на 59 trades may be sample-fragile (Lo 2002 small-sample bias) — ML trained на few examples = overfit risk

## ROUND 1 verdicts (TRADER-EXPERT + ARCHITECTURE-REVIEWER, complete)

| # | Question | Trader verdict | Architecture verdict | Final accepted |
|---|----------|----------------|----------------------|----------------|
| Q1 | v0.5 direction selection | **REVISE → (C) 4H test** | **APPROVE_WITH_CONDITIONS (C)** | (C) 4H mean-reversion test с amendments |

## Trader REVISE rationale (3 decisive arguments verified)

1. **n=59 too small для ML** (CPCV needs ≥500 per López de Prado AFML Ch.7) — XGBoost memorizes на n=59, не trains
2. **S17 signal fold-5-concentrated** (без fold #5 mean=0.01) — ML trained на overfit pattern bigger overfit
3. **(C) 4H = 1-2 sprint cheap falsification** before 5-10 sprint expensive ML construction

## Architecture verdict с conditions

**Primary verdict:** CONFIRM trader REVISE к (C). 100% infrastructure reuse via S19 Conditions A1/A2/A3 paid off для timeframe shifts.

**HIGH conditions:**
- **4-map atomic extension** (rest.py + __main__.py 3 sites): bars_per_year_map + interval_seconds_map + 2× argparse choices. Partial extension = silent wrong-Sharpe или KeyError crash.
- **WFA params at 4H pre-registration** (Bailey 2014 discipline analogous к T-Amendment 1)
- **AND-gate frequency floor verification** (probe BEFORE sprint commit)

**Secondary verdicts:**
- (A) ML XGBoost: DEFER к v0.6+ confirmed (n=59 statistically infeasible)
- (B) HMM: scope correction 4-6 sprints (vs claimed 3-5) — WFA nested CV adds 1-2 sprints; sequence after (C)

## Frequency probe (architecture-mandated T0, EXECUTED)

Probe via 1H BTCUSDT_1h.parquet resampled к 4H (avoids backfill):
- 1H baseline: 42,098 bars × 4.81y
- 4H resampled: 10,517 bars
- **RSI(14)<35 AND close<lower_BB(20, 1.5σ) trigger events: 439**
- Trigger rate: 4.17% (4H) vs 2.36% (1H S17) — actually MORE per-bar at 4H

**Architecture frequency math overestimated penalty.** Realistic actual trade count estimate (с FLAT-only filter): 100-200 trades. **Comfortably ≥ T5 floor 100 default (или 150 T-Amendment 1).** Option (C) viable, не предетерминированный FAIL.

## Cross-cutting concerns (joint)

- **CC1 4-map atomic extension required** (architecture HIGH) — partial extension catastrophic
- **CC2 WFA params 4H pre-registration BINDING** — keep ADR 0014 defaults documented OR scale-down документировать
- **CC3 T5 floor pre-registration BINDING** — frequency probe shows ≥439 raw triggers → keep T5 floor 100 default (или T-Amendment 1 150 — operator discretion)
- **CC4 AND-gate frequency floor empirically verified** (439 events probe vs architecture worry 15) — Option (C) viable
- **CC5 4H Bybit data availability** — 1H baseline 2021-07-02 confirmed; 4H probe via resample uses same calendar coverage
- **CC6 CrossTrialLog dormant** — single-hypothesis test, n_trials=1 fresh post-S21 archival

## Escalation list для user (resolved autonomously per "пусть выберут")

**ESC-1 (option choice):** Trader REVISE к (C) accepted (3 strong arguments, architecture confirms). Option (A) DEFER к v0.6+, (B) sequence after (C), (D) deferred (continue с (C) cheap test).

**ESC-2 (T5 floor at 4H):** Frequency probe shows 439 raw triggers — KEEP T5 floor 100 default (per acceptance-criteria.md). Не need T-Amendment 1 raise к 150 (was 15M-specific scaling, 4H frequency adequate at 100 floor).

**ESC-3 (WFA params at 4H):** Architecture flags scale-down option (test=125 bars × 4h = 21 days vs default test=500 × 4h = 83 days). Maintainer decision: **KEEP ADR 0014 defaults** — calendar coverage 4.81y allows K=5 × (2000+500+20) bars × 4h = ~1.16y per fold, fits comfortably in 4.81y total. No scale-down needed.

## USER FINAL DECISION (autonomous mode)

S22 = combined architectural + measurement sprint (4-map extension small surface + frequency pre-validated).

**S22 deliverables:**
- T0 ✅ Frequency probe (DONE — 439 events confirmed Option C viable)
- T1 ADR 0037 (joint verdict + 3 amendments + pre-registered config)
- T2 4-map atomic extension (rest.py intervals + __main__.py 3 sites: bars_per_year_map + interval_seconds_map + 2× choices)
- T3 4H backfill BTCUSDT (~10.5K bars expected from 2021-07-02 OR earliest available)
- T4 WFA 4H measurement (pre-registered: RSI 35/65 + BB 1.5σ AND-gated, T5 floor 100, WFA ADR 0014 defaults)
- T5 sprint-22 page + ADR + wiki sync
- T6 PHASE 8 ship (tag v0.1.0-alpha.22)

**Verdict criteria (BINDING per ADR 0037):**
- T5 < 100 → FAIL count alone (default per acceptance-criteria.md, не T-Amendment 1 150)
- T5 ≥ 100 + fold concentration check (T-Amendment 2 carry-over per S19 pattern)
- All T1-T6 + DSR + MC PASS conjoint → MVP DONE strategy criteria → S23+ S1-S6 system + Mainnet pilot
- FAIL → S23 honest close v0.5 (5 hypotheses tested = 5-th honest close, even stronger evidence base)

## Related

- [[decisions/0036-sprint-21-honest-close-v04]] — v0.4 honest close + v0.5 options A-D
- [[decisions/0035-sprint-20-15m-measurement]] — S20 FAIL + Hudson & Urquhart 2021
- [[decisions/0034-sprint-19-15m-architecture]] — Conditions A1+A2+A3 reused для (C)
- [[decisions/0032-sprint-17-btc-mean-reversion-relaxed]] — S17 partial signal evidence
- [[architecture/acceptance-criteria]] — T1-T6 thresholds (immutable)

## Related

- [[decisions/0036-sprint-21-honest-close-v04]] — v0.4 honest close + v0.5 options A-D enumerated
- [[decisions/0035-sprint-20-15m-measurement]] — S20 verdict FAIL + Hudson & Urquhart 2021 validated
- [[decisions/0034-sprint-19-15m-architecture]] — S19 architectural prep (15M infrastructure preserved)
- [[decisions/0032-sprint-17-btc-mean-reversion-relaxed]] — S17 partial signal evidence
- [[sprints/sprint-21-honest-close-v04]] — S21 v0.4 honest close (predecessor)
- [[architecture/acceptance-criteria]] — T1-T6 thresholds (immutable)
