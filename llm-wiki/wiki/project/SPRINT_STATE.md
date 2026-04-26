---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-04-26
sprint: 15
phase: between-sprints
branch: main
tag: v0.1.0-alpha.15
---

# SPRINT STATE

> Этот файл читается ПЕРВЫМ в каждой сессии. Обновляется после каждого значимого шага.
> Формат намеренно компактный — ≤ 2KB. Не расширяй без причины.

## Текущий статус

**v0.2 retry attempt #1 — FAIL but T5 reached. S15 ready к ship (tag `v0.1.0-alpha.15`).** 17 спринтов завершено: S1-S7 + S8a + S8b + S8c + S9 + S10 + S11 + S12 + S13 + S14 + S15.

**Final v0.1 status:**
- Infrastructure: ✅ COMPLETE (16/30/74/45 + 38 components + 29 ADRs + 16 sprint pages)
- Strategy validation: ❌ NEGATIVE (EMA crossover на 1H BTC = no edge, verified 2 measurements 2.2y + 4.81y)
- MVP DONE per acceptance-criteria.md: NOT achieved (T5 structurally unreachable)
- Tag `v0.1.0-alpha.14` = honest close marker (alpha suffix preserved — NOT MVP final)

## Последний спринт (S15 — Mean-reversion + multi-symbol, v0.2 retry attempt #1)

8 TDD tasks. Verdict: FAIL but T5 reached (108 trades aggregate first time).
- T0 CrossTrialLog (closes S14 Q2 — Bailey eq. 13 cross-trial sigma_SR)
- T1 load_recent symbol filter (HIGH BLOCKER — Kelly contamination fix)
- T2 BB indicator NEW
- T3 MeanReversionRsiBBStrategy NEW (RSI<30 AND close<lower_BB AND-gated)
- T4 _cmd_run wires MeanRev + symbol→RiskManager
- T5 Multi-symbol --symbols CLI for backfill+wfa, DSR cross-trial wiring
- T6 tz-aware parquet filter fix + indicators.py mean_reversion branch + measurement run
- T7 wiki sync (ADR 29→30, sprint pages 16→17)
- T8 PHASE 8 ship — pending

S15 PHASE 2 brainstorm: ESC-1 Option B (trader+architecture converged). ESC-2 pre-registered RSI 30/70 + BB(20, 2σ) AND-gated. Q3 (15M) + Q4 (ML) deferred.

Per-symbol: BTC 44 trades, ETH 29 (one outlier fold), SOL 35. Aggregate T1=9.32 PASS, T5 n=108 PASS but t_stat 1.04 FAIL, T6 mean -12.38 FAIL, MC 0.998 FAIL, DSR 0 FAIL.

## Следующее действие

```
S15 SHIPPED (PR #23 → squash-merged d350bc2, tag v0.1.0-alpha.15).
17 sprints completed. v0.2 retry attempt #1 = FAIL but T5 reached (108 trades).

Operator decides S16 direction:
(B') broader RSI thresholds + variance reduction (more N_trials → harsher DSR)
(C) Q3 15M timeframe — 2 sprints (interval_map + heal_max_age fixes blockers known)
(D) honest close v0.2 (accept 2 strategy attempts both failed, freeze)
(E) Q4 ML XGBoost (deferred — S15 evidence: no partial signal, MC random-equivalent)

No commitment. Operator decides if/when.
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
