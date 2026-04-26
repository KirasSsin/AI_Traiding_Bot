---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-04-26
sprint: 23
phase: 8-ship
branch: feature/sprint-23-honest-close-v05
tag: v0.1.0-alpha.23
---

# SPRINT STATE

> Этот файл читается ПЕРВЫМ в каждой сессии. Обновляется после каждого значимого шага.
> Формат намеренно компактный — ≤ 2KB. Не расширяй без причины.

## Текущий статус

**v0.5 honest close. S23 ready к ship (tag `v0.1.0-alpha.23`).** 25 спринтов завершено. **5 strategy hypotheses tested across 4.81y BTC — all FAIL conjoint per acceptance-criteria.md**. CC1 T5 100 structurally unreachable BINDING (3 timeframes empirical). CC3 Strategy edge regime-INDEPENDENT (S17+S22 both 5/6+DSR+MC PASS — combined ~120 trades для v0.6-A ML training). cross_trial_sharpes archived к v0.5-final.json + reset для v0.6 readiness (4-th archival, mirrors S16/S18/S21). 5-th honest close в проекте (S14+S16+S18+S21+S23).

**Final v0.1 status:**
- Infrastructure: ✅ COMPLETE (16/30/74/45 + 38 components + 29 ADRs + 16 sprint pages)
- Strategy validation: ❌ NEGATIVE (EMA crossover на 1H BTC = no edge, verified 2 measurements 2.2y + 4.81y)
- MVP DONE per acceptance-criteria.md: NOT achieved (T5 structurally unreachable)
- Tag `v0.1.0-alpha.14` = honest close marker (alpha suffix preserved — NOT MVP final)

## Последний спринт (S23 — v0.5 honest close)

Documentation only + cross_trial_sharpes archival. NO code changes. Pre-committed per ADR 0037 BINDING.
- T1 ADR 0038 accepted
- T2 sprint-23-honest-close-v05.md
- T3 cross_trial_sharpes.json → _v0.5-final.json archival + reset (4-th archival)
- T4 wiki sync (current-state TL;DR + ADR 37→38, sprint pages 24→25, +S23 row)
- T5 log.md sprint-end
- T6 SPRINT_STATE → between-sprints, tag alpha.23
- T7 PHASE 8 ship — pending

5 strategy hypotheses tested all FAIL conjoint. T5 100 structurally unreachable insight (3 timeframes empirical). Strategy edge regime-INDEPENDENT (S17+S22 both 5/6+DSR+MC PASS).

5-th honest close в проекте (S14+S16+S18+S21+S23). Pattern: documentation + archival, no measurement re-run.

## Следующее действие

```
S23 PHASE 8 ship: gh pr create + squash merge + tag v0.1.0-alpha.23.

v0.5 closed honest. 5 strategy hypotheses tested. T5 100 structurally unreachable confirmed.
data/cross_trial_sharpes_v0.5-final.json archived, fresh [] для v0.6.

Operator decides v0.6 direction (no commitment):
(v0.6-A) Hybrid mean-reversion + ML XGBoost — combined S17+S22 ~120 trades viable
(v0.6-B) HMM regime-switch — addresses fold concentration
(v0.6-C) Multi-symbol revival post-MVP — ONLY path к T5 ≥100 conjoint pass
(v0.6-D) Different strategy class (donchian, ATR-bands, regime-detection)
(v0.6-E) Project pause — 5 hypotheses + structural insight = strong contribution
(v0.6-F) MVP T5 floor amendment — operator decides spec amendment justified

5-th honest close в проекте (S14+S16+S18+S21+S23). Per Bailey 2014: v0.6 fresh hypothesis resets DSR baseline cleanly.
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
