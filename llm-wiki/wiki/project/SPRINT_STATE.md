---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-04-26
sprint: 22
phase: 8-ship
branch: feature/sprint-22-4h-test
tag: v0.1.0-alpha.22
---

# SPRINT STATE

> Этот файл читается ПЕРВЫМ в каждой сессии. Обновляется после каждого значимого шага.
> Формат намеренно компактный — ≤ 2KB. Не расширяй без причины.

## Текущий статус

**S22 ready к ship (tag `v0.1.0-alpha.22`) — v0.5-C 4H test verdict FAIL T5 count.** 24 спринтов завершено. **5/6 + DSR=0.996 + MC p=0.018 PASS** (similar pattern к S17 1H — strategy edge regime-independent). 62 trades < 100 floor → FAIL count alone. **CRITICAL INSIGHT:** T5 100 STRUCTURALLY UNREACHABLE на BTC-only mean-reversion (4 attempts ~60-73 trades all). Per ADR 0037 BINDING → S23 honest close v0.5.

**Final v0.1 status:**
- Infrastructure: ✅ COMPLETE (16/30/74/45 + 38 components + 29 ADRs + 16 sprint pages)
- Strategy validation: ❌ NEGATIVE (EMA crossover на 1H BTC = no edge, verified 2 measurements 2.2y + 4.81y)
- MVP DONE per acceptance-criteria.md: NOT achieved (T5 structurally unreachable)
- Tag `v0.1.0-alpha.14` = honest close marker (alpha suffix preserved — NOT MVP final)

## Последний спринт (S22 — BTC 4H mean-reversion test, v0.5-C)

Combined architectural + measurement sprint per joint trader+architecture verdict. Frequency probe T0 pre-validated (439 raw triggers).
- T0 ✅ Frequency probe (Option C viable)
- T1 ADR 0037 accepted
- T2 5-map atomic extension (rest.py + __main__.py 4 sites + 2× argparse choices, 5th map runtime-discovered)
- T3 4H BTCUSDT parquet via 1H resample (10,517 bars — Bybit backfill API hung, resample fallback)
- T4 WFA 4H measurement → VERDICT FAIL T5 count (62 < 100), 5/6+DSR+MC PASS
- T5 sprint-22 page + wiki sync (this commit)
- T6 PHASE 8 ship — pending

Strategy criteria: T1=6.17 PASS / T2=7309 PASS / T3=6.1% PASS / T4 win 37%/RR 580 PASS / **T5 62 FAIL** / T6=2.96 PASS / DSR=0.996 PASS / MC p=0.018 PASS stat-sig.

Fold sharpes: [1.93, -2.92, 1.32, 12.70, 1.78] — 4/5 positive, fold #3 dominant (12.70).

CRITICAL INSIGHT: T5 100 structurally unreachable на BTC-only mean-reversion (4 attempts 1H/15M/4H = ~60-73 trades all). FLAT-only constraint dominates trade count. T5 only reachable via multi-symbol aggregation (out of MVP). Per ADR 0037 BINDING → S23 honest close v0.5.

## Следующее действие

```
S22 PHASE 8 ship: gh pr create + squash merge + tag v0.1.0-alpha.22.

S22 verdict FAIL T5 count only (62 < 100), 5/6+DSR+MC PASS pattern similar к S17.
CRITICAL INSIGHT: T5 100 structurally unreachable на BTC-only mean-reversion.
Per ADR 0037 BINDING → S23 honest close v0.5.

Then S23 docs-only sprint:
- ADR 0038 v0.5 honest close (5 hypotheses tested)
- sprint-23-honest-close-v05.md
- Document T5 100 structurally unreachable insight (4 BTC-only attempts ~60-73 trades)
- Archive cross_trial_sharpes.json к _v0.5-final.json (4th archival)
- Tag v0.1.0-alpha.23

After S23: operator decides v0.6 direction (no commitment):
(v0.6-A) Hybrid mean-reversion + ML XGBoost — combined S17+S22 ~120 trades
(v0.6-B) HMM regime-switch
(v0.6-C) Multi-symbol revival post-MVP
(v0.6-D) Different strategy class
(v0.6-E) Project pause
(v0.6-F) MVP T5 floor amendment (operator decides spec amendment justified)
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
