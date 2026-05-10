---
title: "Sprint 44 — WFA retrofit (research presets acceptance gate restoration)"
type: sprint
tags: [sprint-44, wfa-retrofit, dsr, mc, acceptance-gate]
created: 2026-05-10
updated: 2026-05-10
status: completed
sources:
  - llm-wiki/wiki/project/decisions/0064-sprint-44-wfa-retrofit.md
  - llm-wiki/wiki/project/plans/2026-05-10-sprint-44-wfa-retrofit.md
  - llm-wiki/wiki/project/pre-s44-backlog.md
---

# Sprint 44 — WFA retrofit

## Цель

Restore acceptance discipline (T1-T6 + DSR + MC + N_trials counter) для 11 research presets. Replace `verdict: "RAW"` с three-valued WFA_PASS / WFA_FAIL / WFA_FAIL_DATA.

## Доставленная функциональность

### Код
- `src/backtest/research_wfa.py` (NEW) — shared WFA helper, WindowSplitter loop + per-fold backtest_fn + DSR + MC + acceptance gate
- `src/backtest/atr_breakout_runner.py` — добавлен `_run_atr_breakout_wfa()` thin wrapper
- `src/backtest/volume_breakout_runner.py` — добавлен `_run_volume_breakout_wfa()` thin wrapper (с adapter для signature mismatch)
- `src/backtest/research_runner_envelope.py` — extended с `wfa_result: dict | None` keyword
- `src/dashboard/backtest_runner.py` — dispatch routes research presets через WFA path; preset descriptions обновлены с честными S44 verdicts
- `src/dashboard/static/dashboard.js` — verdict mapping для WFA_PASS/WFA_FAIL/WFA_FAIL_DATA
- `src/dashboard/static/dashboard.css` — `.verdict-fail-data` amber color
- `data/cross_trial_sharpes.json` — 10 trials populated (S44 sprint tag)

### Тесты
- `tests/unit/test_research_wfa.py` (NEW) — 4 tests (helper contract)
- `tests/integration/test_atr_breakout_wfa.py` (NEW) — 4 tests (per-runner WFA)
- `tests/integration/test_volume_breakout_wfa.py` (NEW) — 2 tests
- `tests/unit/test_research_runner_envelope.py` — 3 new tests (wfa_result handling)
- `tests/integration/test_atr_breakout_dashboard_contract.py` — 2 new tests (WFA verdict transition)

### Wiki
- ADR 0064 (THIS sprint) accepted
- sprint-44 page (THIS file)
- current-state.md sprint history row + ADR count 63→64 + sprint pages 47→48
- index.md ADR 0064 + sprint-44 entries
- log.md S44 sprint-end entry

### FSM рост
**0** (UNCHANGED — pure validation infrastructure work).

### Reason codes
**0 новых** (UNCHANGED 56).

### Tests/качество
- Unit: ~956 → ~970 (+14)
- Integration: ~54 → ~58 (+4)
- mypy --strict: 0 errors
- Canonical: 16/30/74/56 (UNCHANGED)

## Решения и отклонения

- **Q1 + Q2 REVISE (joint):** Trader rejected Kelly-compounded unification + replay_engine wrap — replay_engine architecturally blocked для research runners (3 documented gaps). Final: sequential-additive preserved + per-runner WFA loop calling _backtest_single per fold.
- **Q3 REVISE → CORRECTED inline:** Trader claim "_autoscale_wfa_params doesn't exist" was wrong (function exists в dashboard/backtest_runner.py:213). ADR 0064 documents per-combo bar count table + auto-scale path для BTC 1D edge case.
- **Q6 EXPAND → verified inline:** Pre-S44 N_trials = **0** (NOT 9 as maintainer claimed). Post-S44 = 10 (1 skipped: WFA_FAIL_DATA имеет sharpe=NaN).
- **Q7 CONFIRM с sub-verdict:** Three-valued verdict — WFA_PASS / WFA_FAIL / WFA_FAIL_DATA distinguishes data-limited от statistical failure.

## Per-combo результаты (см. ADR 0064 для full table)

ВСЕ 11 combos = WFA_FAIL (10 statistical + 1 data-limited). Common root cause = T5 floor (n≥50). Pre-S44 RAW verdicts hid OOS validation failure.

## Влияние на следующие спринты

**S45 candidates:**
- UI deferrals (drawdown chart, per-trade markers, monthly heatmap) — S43 deferred
- WFA params recalibration для low-frequency strategies (e.g. reduced T5 floor OR alternative train/test ratios)
- New strategy hypothesis development (current research portfolio failed WFA — need new approach)

## Перенесённые задачи

S37/S38 long-standing: F8 block_size, M1-M4 bybit-api, Item #7 shim, Item #10 — unaffected.

## Связанные

- [[../decisions/0064-sprint-44-wfa-retrofit]]
- [[../plans/2026-05-10-sprint-44-wfa-retrofit]]
