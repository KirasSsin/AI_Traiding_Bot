---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-04-26
sprint: 13
phase: between-sprints
branch: main
tag: v0.1.0-alpha.13
---

# SPRINT STATE

> Этот файл читается ПЕРВЫМ в каждой сессии. Обновляется после каждого значимого шага.
> Формат намеренно компактный — ≤ 2KB. Не расширяй без причины.

## Текущий статус

**Между спринтами. S13 shipped (tag `v0.1.0-alpha.13`).** 15 спринтов завершено: S1-S7 + S8a + S8b + S8c + S9 + S10 + S11 + S12 + S13.

## Последний спринт (S13 — Backfill 5y + WFA T1-T6 measurement)

8 TDD tasks, 12 commits. Verdict: **FAIL** (4/6 criteria failed).
- T1-T3: Bybit data probe + backfill wire + 42098 bars (4.81y)
- T4: NaN pre-flight assertion
- T5: trade_extractor (DataFrame→TradeRecord bridge)
- T6: strategy_metrics (T1-T6 extraction) + BLOCKER fix (MaxDD initial_capital)
- T7: _cmd_wfa measurement wired — verdict=FAIL (T1=-44.46, T2=-101.38, T3=1.27% PASS, T4 RR=0.797 FAIL, T5 n=20 FAIL, T6=1.136 PASS)
- T8: PHASE 8 wiki sync

Tests: 689→712 unit (+23). FSM/counts unchanged (16/30/74/45). Q7-S12 zero-migration preserved.

**Critical finding:** Sample size NOT data-span-bounded. ~1 trade per 10 days regardless of data span. T5 n>=100 unreachable without strategy revision.

## Следующее действие

```
S15 brainstorm (operator decides direction):
- Per ADR 0028 Q7 ESC-1=c: case-by-case at S15
- Possible paths: (a) strategy revision, (b) honest "no edge" close,
  (c) multi-symbol expansion, (d) signal frequency tuning (look-ahead risk)
- S14 = intermediate sprint if needed before S15 brainstorm
```

## Carry-over к S13+

- **F live demo Mainnet validation actual run** — operator-driven post-merge, follows live-demo-validation.md
- **FillRecorderAdapter Layer 2 schema link** — add `entry_signal_id` к `execution_state` migration + wire `Coordinator.start_bracket` к persist signal_id alongside bracket_id (Q7 hard constraint pushed это к S13)
- **3-way endpoint enum (DEMO/TESTNET/MAINNET)** — Q6 future fix (current routing CORRECT for S12 demo)
- **T2 review C3 init_db dual-conn comment** (S11 carry-over) — code comment for two-connection sequence
- **DSR per-fold DataFrame→TradeRecord conversion** (informational, deferred от S10)
- **DSR threshold calibration** (S15+ per Q5 verdict, need 30+ empirical trades)
- **halt_log INSERT order swap в `_set_halt`** (PRE-EXISTING, data-integrity reviewer T1 follow-up — write-ahead invariant per ADR 0021)
- **find_by_order_id ORDER BY explicit** (T1 reviewer follow-up, future-safe для multi-symbol scenarios)
- **fill-history.md component page update** (T1 trading-logic reviewer follow-up — reference FillRecorderAdapter as production impl)
- **execFee vs cumExecFee distinction** в bybit-adapter.md OR ws-private-consumer.md (T1 trading-logic reviewer follow-up)

## Ключевые решения S12

- **Q1 CONFIRM Bybit demo trading endpoint** (zero PnL exposure для first live cycle)
- **Q2 CONFIRM 48h validation duration** (1H bars × 48 = adequate structural sample)
- **Q3 CONFIRM multi-criteria gate + MANDATORY zero-trade clause** (likely 0 trades on EMA crossover during 48h → structural criteria only)
- **Q4 REVISE-additive Parquet shim** (data_collector takes config-dict, not args — verified via grep CC1)
- **Q5 REVISE-additive FillRecorderAdapter** (FillHistoryRepository не drop-in для _FillRecorderProto interface mismatch)
- **Q6 REVISE-DISAGREE-FACTUAL: NO endpoint string change** (S11 carry-over note WAS WRONG — current `"demo.bybit.com"` correctly routes к demo per pybit substring matching; "fix" к testnet substring would BREAK demo connectivity)
- **Q7 CONFIRM P0-wake + alpha.11 rollback + zero-migration constraint** (preserves binary rollback compat)
- **2-layer adapter pattern** (always-on structlog audit + best-effort DB insert via execution_state→trade_history lookup chain)
- **Schema gap acknowledged S13 carry-over:** execution_state has NO entry_signal_id → Layer 2 always-skips during S12 (honest per Q7)

## Как обновлять этот файл

После каждого значимого шага (task complete / phase change / blocker found / session end):
1. Обнови "Текущий статус" (sprint / phase)
2. Перенеси task из "В процессе" → "Завершённые задачи" (checkbox)
3. Обнови "Следующее действие" — конкретное, с командой если применимо
4. Добавь в "Ключевые решения" только нетривиальное
5. Обнови `updated:` в frontmatter
