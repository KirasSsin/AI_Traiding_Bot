---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-04-25
sprint: 11
phase: between-sprints
branch: main
tag: v0.1.0-alpha.11
---

# SPRINT STATE

> Этот файл читается ПЕРВЫМ в каждой сессии. Обновляется после каждого значимого шага.
> Формат намеренно компактный — ≤ 2KB. Не расширяй без причины.

## Текущий статус

**Между спринтами. S11 shipped (PR #19 → squash-merged, tag `v0.1.0-alpha.11`).** 16 спринтов завершено: S1-S7 + S8a + S8b + S8c + S9 + S10 + S11 + 5 docs/tooling batches (PR #12-#19).

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
Begin S12 brainstorm:
1. mem-search "S12 Live demo Mainnet" + "Bybit demo virtual capital"
2. S12 = F (Live demo Mainnet 24-72h validation) per Q1 trader CONFIRM
3. Q4 params confirmed: Bybit demo + 48h + $1000 virtual + halt criteria
4. Run brainstorm-init skill → trader-expert ROUND 1 questionnaire (focus: data path integration, FillRecorder wiring, monitoring cadence)
```

## Carry-over к S12+

- **F (Live demo Mainnet 24-72h validation)** — main S12 scope
- **FillRecorder production wiring** — currently `_NoopFillRecorder` stub в `_cmd_run`
- **`_load_ohlcv` production integration** в `_cmd_wfa` — currently empty df stub
- **T2 review C1 endpoint string fix** — `"demo.bybit.com"` semantically wrong для testnet (pybit substring match: current sets `demo=True, testnet=False`, correct для S11 demo intent но wrong для actual testnet validation). Fix к contain `"testnet"` substring (e.g., `"stream-testnet.bybit.com"`)
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
