---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-04-26
sprint: 16
phase: between-sprints
branch: main
tag: v0.1.0-alpha.16
---

# SPRINT STATE

> Этот файл читается ПЕРВЫМ в каждой сессии. Обновляется после каждого значимого шага.
> Формат намеренно компактный — ≤ 2KB. Не расширяй без причины.

## Текущий статус

**v0.2 honest close. S16 ready к ship (tag `v0.1.0-alpha.16`).** 18 спринтов завершено: S1-S7 + S8a + S8b + S8c + S9 + S10 + S11 + S12 + S13 + S14 + S15 + S16. **2 strategy families tested both FAIL** (S13 EMA crossover + S15 mean-reversion). DSR cross-trial state archived к v0.2 file, fresh empty для v0.3 readiness.

**Final v0.1 status:**
- Infrastructure: ✅ COMPLETE (16/30/74/45 + 38 components + 29 ADRs + 16 sprint pages)
- Strategy validation: ❌ NEGATIVE (EMA crossover на 1H BTC = no edge, verified 2 measurements 2.2y + 4.81y)
- MVP DONE per acceptance-criteria.md: NOT achieved (T5 structurally unreachable)
- Tag `v0.1.0-alpha.14` = honest close marker (alpha suffix preserved — NOT MVP final)

## Последний спринт (S16 — v0.2 honest close)

Documentation only + cross_trial_sharpes archival. NO code changes.
- T1 ADR 0031 accepted
- T2 sprint-16-honest-close-v02.md
- T3 wiki sync (current-state TL;DR + ADR 30→31, sprint pages 17→18)
- T4 log.md sprint-end
- T5 SPRINT_STATE → between-sprints, tag alpha.16
- T6 cross_trial_sharpes.json → _v0.2.json archival + reset к [] для v0.3 fresh-start
- T7 PHASE 8 ship via sprint-finish

Trader CONFIRM Option D verified: DSR cross-trial sigma_SR=22.68 с -44.46 anchor → expected max Sharpe gate +21.5 для n_trials=3 unrealistic. BTC +1.75 institutional knowledge preserved для v0.3-A (BTC-only mean-reversion fresh start). ETH outlier fold (-188.65) flagged как data pathology. Q3 15M architectural blockers (interval_map + heal_max_age) preserved для potential future revival.

## Следующее действие

```
S16 SHIPPED (PR #24 → squash-merged 68d2913, tag v0.1.0-alpha.16).
18 sprints completed. v0.2 closed honest. 2 strategy families tested both FAIL.
data/cross_trial_sharpes_v0.2.json archived locally, fresh [] для v0.3.

Operator decides v0.3 direction (no commitment):
(v0.3-A) BTC-only mean-reversion fresh start — strongest signal observed S15
(v0.3-B) Regime-switch HMM — 3-5 sprints
(v0.3-C) ML XGBoost — defer (no partial signal evidence)
(v0.3-D) Different timeframe (15M/4H) — Q3 blockers documented
(v0.3-E) Project pause — 0 sprints

Per Bailey 2014 N_trials per hypothesis: v0.3 fresh strategy resets DSR baseline cleanly.
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
