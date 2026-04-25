---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-04-25
sprint: between-sprints
phase: ready-for-s11
branch: main
tag: v0.1.0-alpha.10
---

# SPRINT STATE

> Этот файл читается ПЕРВЫМ в каждой сессии. Обновляется после каждого значимого шага.
> Формат намеренно компактный — ≤ 2KB. Не расширяй без причины.

## Текущий статус

**Между спринтами. S10 shipped (PR #18 → `dcb3576`, tag `v0.1.0-alpha.10`).** 15 спринтов завершено: S1-S7 + S8a + S8b + S8c + S9 + S10 + 5 docs/tooling batches (PR #12-#18).

## Последний спринт (S10 — WFA + DSR aggregate + MC permutations)

11 TDD tasks, 14 commits squash-merged. Closed S9 deferred carry-overs:
- DSR `n_trials > 1 NotImplementedError` → sigma_sr param (Bailey eq. 12)
- DSR annualization → fixed sqrt(8760)
- WFA acceptance gate consuming DSR → DSR informational, NOT in gate (per Q2 trader REVISE — N=40-80 trades/fold = high variance)
- Pre-existing bug fixed: vector_backtest.py annualization sqrt(365*24*60) → sqrt(8760)

Tests: 630→656 unit (+26) + 1 integration. FSM/counts unchanged (16/30/74/45). 0 src/ behavioral changes outside backtest scope.

## Следующее действие

```
Begin S11 brainstorm:
1. mem-search "S11 candidate scope" + "live demo Mainnet validation"
2. Per S9 carry-over roadmap: S11 = F (Live demo Mainnet 24-72h validation + trace fail modes)
3. OR alternative: S12 A (Operator-readiness — runbooks + monitoring + alerts dashboard)
4. Run brainstorm-init skill → trader-expert ROUND 1 questionnaire
```

## Carry-over к S11+

- **DSR threshold gate calibration** — TBD post-empirical fold data (deferred S10 Q2)
- **Per-fold DSR в reporter** — NaN placeholder; DataFrame→TradeRecord conversion deferred (informational anyway)
- **WFA wired в `__main__.py` CLI** — defer к operator-readiness sprint
- **Production wiring of FillRecorder** — `__main__.py::_cmd_run` STUB since S8a; defer
- **Pre-existing test_risk_flow.py failure** — `OverrideStore.__init__()` missing hmac_key kwarg (S4 era, Task 15 commit `5b872a6`). NOT S10 regression.

## Ключевые решения S10

- **DSR informational, NOT gate** (Q2 trader REVISE accepted) — N=40-80 trades/fold = DSR variance too high. Calibrate threshold post-empirical.
- **Fixed sqrt(8760) annualization** (Q6 trader REVISE) — derived from trade frequency = circular + breaks IS/OOS comparability.
- **3-Sharpe series trap** (cross-cutting concern #1) — bar-returns / per-trade / display must not conflate. Test-enforced в reporter.
- **sigma_sr external param** (Q7) — closes S9 NotImplementedError. quant-stats T4 added defensive sigma_sr < 0 guard.
- **T6 spec correction** — implementer caught block bootstrap on constant returns yields p=1.0 (correct math).
- **Revive S2 backtest** — existing replay_engine battle-tested, WFA = orchestration layer на top.

## Как обновлять этот файл

После каждого значимого шага (task complete / phase change / blocker found / session end):
1. Обнови "Текущий статус" (sprint / phase)
2. Перенеси task из "В процессе" → "Завершённые задачи" (checkbox)
3. Обнови "Следующее действие" — конкретное, с командой если применимо
4. Добавь в "Ключевые решения" только нетривиальное
5. Обнови `updated:` в frontmatter
