---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-04-26
sprint: 18
phase: between-sprints
branch: main
tag: v0.1.0-alpha.18
---

# SPRINT STATE

> Этот файл читается ПЕРВЫМ в каждой сессии. Обновляется после каждого значимого шага.
> Формат намеренно компактный — ≤ 2KB. Не расширяй без причины.

## Текущий статус

**v0.1 FINAL honest close. S18 ready к ship (tag `v0.1.0-alpha.18`).** 20 спринтов завершено: S1-S7 + S8a + S8b + S8c + S9 + S10 + S11 + S12 + S13 + S14 + S15 + S16 + S17 + S18. **3 strategy hypotheses tested across 4.81y BTC Bybit Spot 1H — all FAIL conjoint per acceptance-criteria.md**. S17 partial signal evidence preserved (MC p=0.01 stat-sig institutional knowledge). cross_trial_sharpes archived к v0.1-final.json + reset для v0.4 readiness.

**Final v0.1 status:**
- Infrastructure: ✅ COMPLETE (16/30/74/45 + 38 components + 29 ADRs + 16 sprint pages)
- Strategy validation: ❌ NEGATIVE (EMA crossover на 1H BTC = no edge, verified 2 measurements 2.2y + 4.81y)
- MVP DONE per acceptance-criteria.md: NOT achieved (T5 structurally unreachable)
- Tag `v0.1.0-alpha.14` = honest close marker (alpha suffix preserved — NOT MVP final)

## Последний спринт (S18 — v0.1 FINAL honest close)

Documentation only + cross_trial_sharpes archival. NO code changes. Pre-committed per ADR 0032 amendment 3 BINDING.
- T1 ADR 0033 accepted
- T2 sprint-18-honest-close-v01.md
- T3 cross_trial_sharpes.json → _v0.1-final.json archival + reset к [] для v0.4 fresh-start
- T4 wiki sync (current-state TL;DR + ADR 32→33, sprint pages 19→20, +S18 row)
- T5 log.md sprint-end
- T6 SPRINT_STATE → between-sprints, tag alpha.18
- T7 PHASE 8 ship — pending

3 strategy hypotheses tested across 4.81y BTC Bybit Spot 1H — all FAIL conjoint:
- S13 EMA crossover trend-following: 20 trades, FAIL T1+T2+T4+T5
- S15 mean-reversion multi-symbol BTC+ETH+SOL: 108 trades T5 reached, FAIL T6+MC+DSR
- S17 mean-reversion BTC-only relaxed: 59 trades, FAIL T5 count only — но 5/6 + DSR=1.0 + MC p=0.01 stat-sig PASS

Critical scientific finding: strategy edge IS real on BTC mean-reversion regime (S17 partial signal MC p=0.01 stat-sig). Sample insufficient на 1H BTC alone — frequency structural limit ~60-70 trades / 4.81y maximum. v0.4 must address frequency dimension (15M timeframe / hybrid ML / multi-symbol post-MVP).

## Следующее действие

```
S18 PHASE 8 ship: gh pr create + squash merge + tag v0.1.0-alpha.18.

v0.1 closed FINAL honest. 3 strategy hypotheses tested + 1 partial signal observed.
data/cross_trial_sharpes_v0.1-final.json archived locally, fresh [] для v0.4.

Operator decides v0.4 direction (no commitment):
(v0.4-A) BTC 15M mean-reversion — STRONGEST viable per S17 evidence (4x freq = T5 reachable est.)
(v0.4-B) Hybrid mean-reversion + ML XGBoost filter — S17 evidence reverses ADR 0030 ML defer
(v0.4-C) Multi-symbol revival — out of MVP scope per user (post-MVP if MVP-DONE achieved BTC-only first)
(v0.4-D) Different timeframe 4H — НЕ recommended per S17 evidence
(v0.4-E) Project pause — 0 sprints, freeze

3 honest closes в проекте (S14 + S16 + S18). Per Bailey 2014 N_trials per hypothesis: v0.4 fresh strategy resets DSR baseline cleanly.
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
