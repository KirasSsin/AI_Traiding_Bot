---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-04-25
sprint: 12
phase: between-sprints
branch: main
tag: v0.1.0-alpha.12
---

# SPRINT STATE

> Этот файл читается ПЕРВЫМ в каждой сессии. Обновляется после каждого значимого шага.
> Формат намеренно компактный — ≤ 2KB. Не расширяй без причины.

## Текущий статус

**Между спринтами. S12 shipped (PR #20 → squash-merged, tag `v0.1.0-alpha.12`).** 14 спринтов завершено: S1-S7 + S8a + S8b + S8c + S9 + S10 + S11 + S12.

## Последний спринт (S12 — Live demo validation 24-72h + production wiring)

6 TDD tasks, 8 commits squash-merged. Closed S11 carry-overs:
- T1 (044dad8) FillRecorderAdapter (closes _NoopFillRecorder stub) — 2-layer pattern (audit + best-effort DB)
- T2 (5d94c1a) `_load_ohlcv` Parquet shim (data_collector config-dict translation)
- T3 (8f4dd1e) pre-flight Gate 5 backfill prerequisite + halt-recovery P1+OCO_ARMED conditional escalation
- T4 (51dc3c4) live-demo-validation.md operator playbook (48h Bybit demo + multi-criteria + zero-trade clause)
- T5 (bd172e1) halt-response-protocol.md (P0 wake + alpha.11 rollback + RC tag iteration)
- T6 (e99c36a) wiki sync (ADR 0027 accepted + sprint-12 page + counts ADR 26→27, sprint pages 13→14, components 35→36 + fill-recorder-adapter component page)

Tests: 680→689 unit (+9). FSM/counts unchanged (16/30/74/45). Q7 zero-migration preserved alpha.11 binary rollback compat.

## Следующее действие

```
S13 brainstorm:
1. mem-search "S13 schema link" + "FillRecorder Layer 2 production"
2. S13 = TBD (post operator-driven 48h validation results)
3. Run brainstorm-init skill → trader-expert ROUND 1 questionnaire
```

**Pre-S13 operator-driven activity:** 48h Bybit demo validation run per `wiki/runbooks/live-demo-validation.md`. Result feeds S13 scope (FillRecorder Layer 2 design, schema link, slippage validation gaps).

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
