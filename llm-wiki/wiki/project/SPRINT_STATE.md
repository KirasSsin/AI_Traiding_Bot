---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-04-26
sprint: 14
phase: between-sprints-post-mvp-honest-close
branch: main
tag: v0.1.0-alpha.14
---

# SPRINT STATE

> Этот файл читается ПЕРВЫМ в каждой сессии. Обновляется после каждого значимого шага.
> Формат намеренно компактный — ≤ 2KB. Не расширяй без причины.

## Текущий статус

**v0.1 honest close. S14 shipped (PR #22 → squash-merged, tag `v0.1.0-alpha.14`).** 16 спринтов завершено: S1-S7 + S8a + S8b + S8c + S9 + S10 + S11 + S12 + S13 + S14.

**Final v0.1 status:**
- Infrastructure: ✅ COMPLETE (16/30/74/45 + 38 components + 29 ADRs + 16 sprint pages)
- Strategy validation: ❌ NEGATIVE (EMA crossover на 1H BTC = no edge, verified 2 measurements 2.2y + 4.81y)
- MVP DONE per acceptance-criteria.md: NOT achieved (T5 structurally unreachable)
- Tag `v0.1.0-alpha.14` = honest close marker (alpha suffix preserved — NOT MVP final)

## Последний спринт (S14 — Honest close)

Documentation only. NO code changes. NO measurement re-run.
- T1 ADR 0029 accepted
- T2 sprint-14-honest-close.md
- T3 wiki sync (ADR 28→29, sprint pages 15→16)
- T4 log.md sprint-end
- T5 SPRINT_STATE → between-sprints-post-mvp-honest-close
- T6 PHASE 8 ship via sprint-finish

Trader Q1 EXPAND verified: T5 ≥100 trades structurally unreachable (5x signal frequency gap, EMA crossover на 1H fires ~1 trade per 5-10 days). User chose Option B (skip Option A theatrical re-measurement).

## Следующее действие

```
v0.1 closed honest. NO S15 committed.

Operator-driven future direction options (deferred):
(A) Strategy revision (mean-reversion / regime / ML) — 3-5 sprints
(B) Multi-symbol (ETH + SOL) — 2-3 sprints, ~3x signal frequency
(C) Different timeframe (15M / 4H) — 1-2 sprints, ADR 0005 amendment
(D) Project pause — 0 sprints, current freeze

Operator decides if/when. No commitment.
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
