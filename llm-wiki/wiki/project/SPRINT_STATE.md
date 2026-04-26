---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-04-26
sprint: 20
phase: 8-ship
branch: feature/sprint-20-15m-measurement
tag: v0.1.0-alpha.20
---

# SPRINT STATE

> Этот файл читается ПЕРВЫМ в каждой сессии. Обновляется после каждого значимого шага.
> Формат намеренно компактный — ≤ 2KB. Не расширяй без причины.

## Текущий статус

**S20 ready к ship (tag `v0.1.0-alpha.20`) — v0.4-A measurement verdict FAIL.** 22 спринтов завершено. **S20 verdict FAIL: T5 73<150 + T1=-45.57 + T2=-345 + T4 RR 1.39 + T6=-37.13** (DSR/MC borderline PASS). Fold #2 -185.21 catastrophic (REGIME CONCENTRATION negative). AND-gate joint multiplier 1.24x на 15M (predicted 4x) — Hudson & Urquhart 2021 empirically validated. S17 partial signal contradicted at 15M = regime-specific к 1H. Per ADR 0034 amendment 3 BINDING → S21 = honest close v0.4 (4 hypotheses tested).

**Final v0.1 status:**
- Infrastructure: ✅ COMPLETE (16/30/74/45 + 38 components + 29 ADRs + 16 sprint pages)
- Strategy validation: ❌ NEGATIVE (EMA crossover на 1H BTC = no edge, verified 2 measurements 2.2y + 4.81y)
- MVP DONE per acceptance-criteria.md: NOT achieved (T5 structurally unreachable)
- Tag `v0.1.0-alpha.14` = honest close marker (alpha suffix preserved — NOT MVP final)

## Последний спринт (S20 — BTC 15M WFA measurement)

Pre-registered measurement per ADR 0034 BINDING. NO code changes.
- T1 ADR 0035 accepted (verdict FAIL + S21 trigger)
- T2 sprint-20-15m-measurement.md
- T3 cross_trial_sharpes auto-persisted (sprint=20, oos_sharpe=-37.13)
- T4 wiki sync (current-state TL;DR + ADR 34→35, sprint pages 21→22, +S20 row)
- T5 PHASE 8 ship — pending

Verdict FAIL multi-criteria:
- T1=-45.57 / T2=-345 / T4 win 30%/RR 1.39 / T5 73<150 / T6=-37.13
- DSR=0.030 PASS / MC p=0.044 PASS borderline
- Fold #2 -185.21 catastrophic (regime concentration negative per T-Amendment 2)
- Frequency multiplier 1.24x (predicted 4x) — Hudson & Urquhart 2021 empirically validated

Critical insight: S17 partial signal на 1H = regime-specific, не frequency-bound. Same params at 15M fundamentally fail. Per ADR 0034 amendment 3 BINDING → S21 honest close v0.4.

## Следующее действие

```
S20 PHASE 8 ship: gh pr create + squash merge + tag v0.1.0-alpha.20.

S20 verdict FAIL: 73 trades < 150 floor + multiple T-criteria fail.
Per ADR 0034 amendment 3 BINDING → S21 = honest close v0.4 (4 hypotheses tested).

Then S21 docs-only sprint:
- ADR 0036 v0.4 honest close
- sprint-21-honest-close-v04.md
- Document Hudson & Urquhart 2021 empirical validation
- Document S17 1H regime-specificity finding (institutional knowledge)
- Archive cross_trial_sharpes.json к _v0.4-final.json + reset для v0.5
- Tag v0.1.0-alpha.21

After S21: operator decides v0.5 direction (no commitment):
(v0.5-A) Hybrid 1H mean-reversion + ML XGBoost — S17 evidence supports
(v0.5-B) 4H mean-reversion test
(v0.5-C) HMM regime-switch + mean-reversion
(v0.5-D) Project pause — 4 hypotheses tested
```

## Carry-over preserved (v0.2+ if any future direction chosen)

All S12 + S13 carry-overs unaddressed (10+ items):

- F live demo Mainnet validation actual run (33min only since S12)
- FillRecorderAdapter Layer 2 schema link (entry_signal_id к execution_state migration)
- 3-way endpoint enum (DEMO/TESTNET/MAINNET) — Q6 future fix
- T2 review C3 init_db dual-conn comment (S11 carry-over)
- DSR per-fold DataFrame→TradeRecord conversion (S10 informational)
- DSR threshold calibration (S15+ per S11 Q5)
- DSR cross-trial sigma_SR implementation (S14 Q2 REVISE — needed для any future revision)
- halt_log INSERT order swap в `_set_halt` (PRE-EXISTING)
- find_by_order_id ORDER BY explicit (T1 reviewer follow-up)
- fill-history.md / bybit-adapter.md / ws-private-consumer.md component page updates
- T2/T5/T6 quant-stats deferred concerns (Sortino formula docs, sqrt(8760) frequency-agnostic, boundary tests)

## Ключевые решения S14

- **Q1 EXPAND** (trader): T5 unreachable verified via grep — 5x signal frequency gap
- **Q2 REVISE** (trader): DSR cross-trial sigma_SR gap — verified via dsr.py:73
- **Option B** (user): honest close immediately, save 1 sprint vs theatrical Option A
- **Tag semantics:** `v0.1.0-alpha.14` = honest close marker, NOT MVP DONE
- **No spec amendment:** acceptance-criteria.md T1-T6 thresholds preserved
- **No code changes:** S14 = documentation only

## Как обновлять этот файл

После каждого значимого шага (task complete / phase change / blocker found / session end):
1. Обнови "Текущий статус" (sprint / phase)
2. Обнови "Следующее действие" — конкретное, с командой если применимо
3. Добавь в "Ключевые решения" только нетривиальное
4. Обнови `updated:` в frontmatter
