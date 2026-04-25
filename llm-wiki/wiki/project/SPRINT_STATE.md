---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-04-25
sprint: 12
phase: 3-planning
branch: main
tag: v0.1.0-alpha.11
---

# SPRINT STATE

> Этот файл читается ПЕРВЫМ в каждой сессии. Обновляется после каждого значимого шага.
> Формат намеренно компактный — ≤ 2KB. Не расширяй без причины.

## Текущий статус

**S12 PHASE 2 завершён, PHASE 3 plan write предстоит.** Trader-expert ROUND 1 verdicts: 4 CONFIRM + 3 REVISE (Q4/Q5 additive, Q6 factual correction). NO ROUND 2 invoked (no engineering disagreement). NO user escalation.

ADR 0027 draft готов (status: proposed). S11 shipped (PR #19 → 48a6bd9, tag v0.1.0-alpha.11). 13 спринтов завершено.

## Последний спринт (S11 — Operator-readiness + pre-flight gap closure)

10 TDD tasks, 13 commits squash-merged. Closed 8-month-old S8a T20 STUB:
- T1 (afb5760) test_risk_flow.py OverrideStore hmac_key signature
- T2 (ead6dca + d7b196f) `_cmd_run` DI wiring (architecture-reviewer SOUND verdict)
- T3 (bb8cba9 + e4df4cd) `_cmd_reconcile_only` DI wiring
- T4 (6e1fff2) `_cmd_wfa` CLI subcommand
- T5 (0b57062) halt-recovery.md priority matrix + escalation
- T6 (26f7b68) NEW log-grep-templates.md
- T7 (281896e) `_cmd_monitor` read-only CLI (C2 invariant)
- T8 (92c37b9) NEW pre-flight.md operator checklist
- T9 (6ba4a41) ADR 0026
- T10 (da7a68f) wiki sync (sprint-11 + counts + index + mental-map)

Tests: 666→680 unit (+14 internal incl. 10 new CLI tests). FSM/counts unchanged (16/30/74/45). Bot runnable end-to-end через `python -m src run`.

## Следующее действие

```
PHASE 3 plan write:
1. Run superpowers:writing-plans skill → output llm-wiki/wiki/project/plans/2026-04-25-sprint-12-live-demo-validation.md
2. Tasks T1-T5 per ADR 0027 + trace map mandatory
3. T1 (FillRecorderAdapter) — code-heavy, judgment for parent_trade_id derivation strategy
4. T2 (_load_ohlcv shim) — code-medium
5. T3-T5 (validation run + protocol) — operational + operator briefing
6. Reviewer matrix per ADR: trading-logic + data-integrity для T1, python-reviewer для T2
7. After plan ready → user choice subagent-driven OR inline execution
```

## Carry-over к S12+

- **F (Live demo Mainnet 24-72h validation)** — main S12 scope
- **FillRecorder production wiring** — currently `_NoopFillRecorder` stub в `_cmd_run`
- **`_load_ohlcv` production integration** в `_cmd_wfa` — currently empty df stub
- **T2 review C1 endpoint string note CORRECTED (S12 PHASE 2 trader REVISE Q6):** current `"demo.bybit.com"` is **CORRECT** for S12 demo trading. Truth table: `settings.testnet=True` → endpoint `"demo.bybit.com"` → pybit `testnet="testnet" in endpoint = False`, `demo="demo" in endpoint = True` → demo trading mode (correct). Originally proposed "fix к stream-testnet.bybit.com" would set `testnet=True, demo=False` = actual Bybit testnet env (NOT demo) — would BREAK demo connectivity. Real future fix: 3-way endpoint enum (DEMO/TESTNET/MAINNET) — deferred к S13+ (NOT P0 for S12).
- **T2 review C3 init_db dual-conn comment** — `init_db` opens internal connection separate от `connect()` returned conn. WAL mode safe но code comment needed
- **Per-fold DSR DataFrame→TradeRecord conversion** (informational, deferred от S10)
- **DSR threshold calibration** (S15+ per Q5 verdict, need 30+ empirical trades)

## Ключевые решения S11

- **A-first vs F-first** (Q1) — A wins per architecturally correct sequencing (live Mainnet требует runnable bot, blocked by `_cmd_run` STUB)
- **Halt priority matrix INTO halt-recovery.md** (Q3 REVISE) — single source of truth, prevents drift vs separate dashboard
- **`_cmd_monitor` strictly read-only** (C2) — SQLite WAL contention prevention via `?mode=ro` URI, T7 test enforces no DB mtime change
- **architecture-reviewer mandatory _cmd_run** (Q7) — DI graph + concurrency implications per ADR 0017 trigger cascade
- **DI feasibility read-pass** (C1) — pre-plan verification confirmed constructors aligned, no mini-ADR needed
- **MagicMock→_NoopFillRecorder** (T2 review C2 fix) — replace test library import в production с simple stub class

## Как обновлять этот файл

После каждого значимого шага (task complete / phase change / blocker found / session end):
1. Обнови "Текущий статус" (sprint / phase)
2. Перенеси task из "В процессе" → "Завершённые задачи" (checkbox)
3. Обнови "Следующее действие" — конкретное, с командой если применимо
4. Добавь в "Ключевые решения" только нетривиальное
5. Обнови `updated:` в frontmatter
