---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-04-26
sprint: 13
phase: 4-execution
branch: feature/sprint-13-backfill-wfa
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
S13 PHASE 4 in flight (per ADR 0028):
- T1 probe ✅ — earliest Bybit 1H BTCUSDT = 2021-07-02 16:00 UTC, target span = ~4.8y
- T2 backfill wire ✅ (commit 4a1b56b с snappy + atomic rename per data-integrity)
- T3 backfill run ✅ — 42098 bars, 2021-07-03→2026-04-25, span 4.81y (ADR 0028 floor 3.5y MET)
  * Span: 2021-07-03 → 2026-04-24 = ~4.8y (ADR 0028 ESC-2: below 5y target, above 3.5y floor)
- T4 NaN preflight ✅ (commit e4439e1)
- T5 trade_extractor ✅, T6 strategy_metrics ✅ (prior commits)
- T7 measurement ✅ verdict=FAIL:
  * T1 Sharpe OOS: -44.46 (< 1.0 threshold) → FAIL
  * T2 Sortino OOS: -101.38 (< 1.5 threshold) → FAIL
  * T3 MaxDD: 1.27% (< 25% threshold) → PASS
  * T4 win_rate=0.30, avg_rr=0.797 (avg_rr < 1.5) → FAIL
  * T5 n_trades=20 (< 100 required) → FAIL
  * T6 OOS/IS Sharpe ratio mean: 1.136 (>= 0.7) → PASS
  * DSR: 0.0445 (N_trials=1, dsr_pass=True — DSR > 0)
  * MC p-value: 0.048 (< 0.05, gate passed)
  * failed_criteria: [t1, t2, t4, t5]
  * Note: only 20 OOS trades across 5 folds (4 trades/fold avg) — strategy generates insufficient signal frequency
- T8 PHASE 8 ship pending (next)
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
