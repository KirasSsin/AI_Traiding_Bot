---
title: 0037. Sprint 22 — BTC 4H mean-reversion test (v0.5-C, hypothesis #5)
type: decision
date: 2026-04-26
sprint: 22
tags: [adr, sprint-22, v0.5-direction-C, btc-4h, mean-reversion, hypothesis-5, combined-architectural-measurement, frequency-probe-pre-validated]
sources:
  - project/pre-s22-backlog.md
  - project/decisions/0036-sprint-21-honest-close-v04.md
  - project/decisions/0034-sprint-19-15m-architecture.md
  - project/decisions/0032-sprint-17-btc-mean-reversion-relaxed.md
  - project/architecture/acceptance-criteria.md
status: accepted
---

# 0037. Sprint 22 — BTC 4H mean-reversion test (v0.5 direction C)

**Status:** accepted
**Date:** 2026-04-26

## Контекст

S21 closed v0.4 honest (PR #29, tag `v0.1.0-alpha.21`). 4 hypotheses tested across 4.81y BTC Bybit Spot — all FAIL conjoint. cross_trial_sharpes archived → fresh `[]` для v0.5.

User directive: "Зайди с этими вопросам в агентов трейдеров, пусть они проведут дискуссию и выберут" → joint trader-expert + architecture-reviewer dispatch для v0.5 direction.

**Q1 joint verdict (per pre-s22-backlog.md):**
- **Trader REVISE → (C) 4H test** (NOT maintainer's A ML XGBoost) — 3 decisive arguments: n=59 too small для ML, S17 fold-5-concentrated, 4H cheap falsification
- **Architecture APPROVE_WITH_CONDITIONS (C)** — 100% S19 infrastructure reuse + 4-map atomic extension + frequency probe T0 mandatory
- **Frequency probe PASS:** 439 raw RSI<35 AND lower_BB events на 4H BTCUSDT (vs architecture worry-case 15) — Option (C) viable, не предетерминированный FAIL

ESC resolutions (autonomous mode per "пусть выберут"):
- ESC-1: (C) accepted (trader+architecture converge)
- ESC-2: T5 floor 100 default (frequency probe shows ≥439 raw triggers — не need T-Amendment 1 raise к 150 which was 15M-specific)
- ESC-3: WFA params keep ADR 0014 defaults (calendar coverage 4.81y allows K=5×(2000+500+20) bars × 4h = ~1.16y per fold — fits)

## Решение

### S22 scope: BTC 4H combined architectural + measurement (single sprint)

**Strategy hypothesis #5 (pre-registered binding):**

```
Strategy: MeanReversionRsiBBStrategy (S15 ADR 0030, reused 100%)
Symbol: BTCUSDT only (per ADR 0016 + MVP scope)
Interval: 4H (240) — NEW для v0.5
RSI: 35/65 (S17 relaxed preserved)
BB: (20, 1.5σ) (S17 relaxed preserved)
WFA params: K=5, train=2000, test=500, embargo=20 (ADR 0014, kept)
N_trials: 1 (fresh baseline post-S21 archival)
T5 floor: 100 trades (default per acceptance-criteria.md, NOT T-Amendment 1 150)
```

### 3 Conditions APPLIED (combined в S22)

**Condition C1 — 5-map atomic extension** (architecture HIGH):
- `rest.py:68-72` intervals dict: `"240": ("4h", 14_400_000)` ✅ APPLIED
- `__main__.py:191` interval_seconds_map: `"240": 14400` ✅ APPLIED
- `__main__.py:282` interval_label_map (_cmd_backfill): `"240": "4h"` ✅ APPLIED
- `__main__.py:407` interval_label_map (_load_ohlcv): `"240": "4h"` ✅ APPLIED
- `__main__.py:610` bars_per_year_map: `"240": 2190` ✅ APPLIED
- `__main__.py:786, 813` argparse choices: `"240"` added ✅ APPLIED
- (Architecture identified 4 sites; 5th — interval_label_map _cmd_backfill — discovered via runtime KeyError + fixed)

**Condition C2 — Frequency probe T0 (architecture-mandated)**: ✅ EXECUTED PRE-SPRINT
- Method: 1H BTCUSDT_1h.parquet resampled к 4H (avoids backfill round-trip)
- Result: 439 raw RSI<35 AND close<lower_BB(20, 1.5σ) trigger events на 10,517 4H bars (4.17% trigger rate vs 1H S17 2.36%)
- Estimate actual trades с FLAT-only filter: 100-200 trades
- Verdict: T5 floor 100 reachable, не предетерминированный FAIL

**Condition C3 — WFA params 4H pre-registration** (Bailey 2014 discipline):
- KEEP ADR 0014 defaults (K=5, train=2000, test=500, embargo=20)
- At 4H: train=2000×4h=333 days, test=500×4h=83 days per fold, K=5 total ~1.16y/fold = ~5.8y total (fits в 4.81y с slight overlap acceptable per WFA convention)
- Documented BEFORE measurement run (no post-hoc tuning)

### S22 deliverables (combined architectural + measurement)

- T0 ✅ Frequency probe (439 events confirmed Option C viable)
- T1 ADR 0037 (this document)
- T2 ✅ 5-map atomic extension (Condition C1)
- T3 4H backfill BTCUSDT (~10.5K bars expected from 2021-07-02 OR earliest available)
- T4 WFA 4H measurement (pre-registered config + verdict)
- T5 sprint-22 page + wiki sync
- T6 PHASE 8 ship (tag v0.1.0-alpha.22)

### Verdict criteria (BINDING per pre-registration)

- T5 < 100 → FAIL count alone, t_stat skipped
- T5 ≥ 100 + fold concentration check (T-Amendment 2 carry-over per S19 pattern)
- All T1-T6 + DSR + MC PASS conjoint → MVP DONE strategy criteria → S23+ S1-S6 system criteria + Mainnet pilot
- FAIL → S23 = honest close v0.5 (5 hypotheses tested = 5-th honest close pattern)

### Cross-cutting concerns (binding)

- **CC1 (Frequency probe pre-validated)**: 439 events probe vs architecture worry 15 — Option C viable confirmed empirically before sprint commit
- **CC2 (5-map atomic extension)**: 5 sites consolidated в single sprint (vs S19's 4-map split). Architecture initially identified 4; runtime KeyError exposed 5th — single-dict registry refactor deferred к v0.6+ (YAGNI at 5 entries — single hand-extension OK)
- **CC3 (WFA params pre-registered)**: KEEP ADR 0014 defaults documented (no scale-down)
- **CC4 (T5 floor pre-registered)**: KEEP default 100 (frequency probe supports — 15M-specific T-Amendment 1 150 не applies)
- **CC5 (Hudson & Urquhart 2021 prior)**: 4H mean-reversion academically supported (lower frequencies historically preferred). Counter-evidence к S20 (15M degraded) does NOT extrapolate к 4H direction
- **CC6 (CrossTrialLog dormant)**: single-hypothesis test, n_trials=1 fresh
- **CC7 (Tag semantics)**: `v0.1.0-alpha.22` = combined sprint marker (architectural + measurement)
- **CC8 (No spec amendment)**: acceptance-criteria.md preserved
- **CC9 (Multi-symbol + 15M infrastructure preserved post-MVP)**: S15+S19 work не trash — available для v0.6+ revival

## Последствия

**Plus:**
- 100% S15+S19 infrastructure reuse (MeanReversionRsiBBStrategy + interval_map + heal_max_bars + annualization parameterization)
- Frequency probe T0 prevents wasted sprint (architecture-mandated discipline)
- Combined sprint: cheaper than S19+S20 split (no measurement-only sprint needed since architectural surface tiny)
- Cheap falsification of "lower-frequency mean-reversion better для BTC" hypothesis
- Если PASS → MVP DONE strategy criteria reached на BTCUSDT only (per user constraint)
- Если FAIL → 5 hypotheses tested = even stronger publishable scientific contribution

**Minus:**
- 5-th hypothesis attempt — diminishing returns argument (offset by cheap probe + reused infrastructure)
- 4H lower frequency = ~10.5K bars total → fewer fold-internal samples per WFA (still K=5 viable)
- WFA fold calendar coverage ~1.16y per fold = significant per-fold market regime exposure (more variance per fold expected)

**v0.6+ direction options (if S22 FAIL):**

- (v0.6-A) Hybrid 1H+ML XGBoost — STILL deferred (n still small для ML training, but 4H may give different evidence base if PASS)
- (v0.6-B) HMM regime-switch + mean-reversion — addresses fold concentration patterns
- (v0.6-C) Different strategy class (donchian breakout, regime-detection, mean-reversion с ATR-bands)
- (v0.6-D) Project pause — 5 hypotheses tested

## Связанные документы

- [[../pre-s22-backlog]] — PHASE 2 joint trader+architecture verdicts trail
- [[0036-sprint-21-honest-close-v04]] — v0.4 honest close (predecessor)
- [[0034-sprint-19-15m-architecture]] — Conditions A1+A2+A3 reused
- [[0032-sprint-17-btc-mean-reversion-relaxed]] — S17 partial signal preserved
- [[0030-sprint-15-mean-reversion-multi-symbol]] — MeanReversionRsiBBStrategy (reused)
- [[0014-walk-forward-train2000-test500]] — WFA params (preserved для 4H)
- [[../architecture/acceptance-criteria]] — T1-T6 thresholds (immutable)

## Поправки

- (none yet)
