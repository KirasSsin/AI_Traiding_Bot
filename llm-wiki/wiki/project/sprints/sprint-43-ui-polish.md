---
title: "Sprint 43 — UI polish (preset rename + descriptions + equity chart)"
type: sprint
tags: [sprint-43, ui, dashboard, equity-chart, uplot]
created: 2026-05-10
updated: 2026-05-10
status: completed
sources:
  - llm-wiki/wiki/project/decisions/0063-sprint-43-ui-polish.md
  - llm-wiki/wiki/project/plans/2026-05-10-sprint-43-ui-polish.md
  - llm-wiki/wiki/project/pre-s43-backlog.md
---

# Sprint 43 — UI polish

## Цель

Переименовать presets к semantic Russian names с optgroup grouping, добавить strategy description block, добавить equity curve chart на dashboard.

## Доставленная функциональность

### Код
- `src/dashboard/backtest_runner.py` — STRATEGY_PRESETS rename + description + optgroup fields для всех 6 presets
- `src/dashboard/app.py` — `/api/strategies` + `/api/strategy/{id}/info` extended с description + optgroup
- `src/backtest/research_runner_envelope.py` — equity_curve parallel arrays format `{timestamps, equity_pct}`
- `src/backtest/atr_breakout_runner.py` — passes df timestamps к envelope
- `src/backtest/volume_breakout_runner.py` — same (defensive timestamp column detection)
- `src/dashboard/static/vendor/uPlot.iife.min.js` + `uPlot.min.css` — uPlot v1.6.31 vendored
- `src/dashboard/templates/index.html` — description block + equity chart panel + uPlot script
- `src/dashboard/static/dashboard.js` — optgroup rendering + description toggle + equity chart render
- `src/dashboard/static/dashboard.css` — description styling + uPlot terminal overrides

### Тесты
- `tests/unit/test_preset_metadata.py` (NEW) — 4 tests (description + optgroup fields, rename mapping)
- `tests/unit/test_supported_combos_endpoint.py` — 3 new tests (description + optgroup в endpoints)
- `tests/unit/test_research_runner_envelope.py` — 3 new tests (equity_curve parallel arrays)
- `tests/integration/test_atr_breakout_dashboard_contract.py` — 1 new test (equity_curve timestamps presence)
- `tests/integration/test_volume_breakout_dashboard_contract.py` — 1 new test (equity_curve timestamps presence)

### Wiki
- ADR 0063 (THIS sprint) accepted
- sprint-43 page (THIS file)
- current-state.md sprint history row + ADR count 62→63 + sprint pages 46→47
- index.md ADR 0063 + sprint-43 entries
- log.md S43 sprint-end entry

### FSM рост
**0** (UNCHANGED — pure UI work).

### Reason codes
**0 новых** (UNCHANGED 56).

### Tests/качество
- Unit: 946 → ~955 (+9)
- Integration: 52 → ~54 (+2)
- mypy --strict: 0 errors
- ruff/format: чисто
- Canonical: 16/30/74/56 (UNCHANGED)

## Решения и отклонения

- **Q1 REVISE:** Maintainer recommended two-line label. Trader rejected — native `<option>` styling unreliable между browsers. Final: `<optgroup>` grouping by trading approach.
- **Q4 REVISE:** Maintainer recommended array of `{ts, equity_pct}` objects. Trader rejected — uPlot native API expects parallel arrays, ~30% bytes saved + zero conversion. Final: `{timestamps: [unix_int...], equity_pct: [float...]}`.

Other 5 questions CONFIRM.

## Влияние на следующие спринты

**S44 (BLOCKING):**
- Resolve atr_breakout_runner sequential-additive vs replay engine Kelly-compounded PnL accounting gap.
- Wrap full WFA + DSR + MC + T1-T6 acceptance gate.
- Restore epistemic discipline (currently `verdict: "RAW"` для research presets).
- Adopt legacy WFA presets (ema/mean_reversion/donchian) к envelope contract → enable equity_curve для них too.

**Future polish (deferred):**
- Drawdown subchart pane.
- Per-trade markers (entry/exit dots на equity chart).
- Monthly returns heatmap.

## Перенесённые задачи

Все S38 carry-overs (F8 block_size, M1-M4 bybit-api, Item #7 shim, Item #10) — unaffected, остаются в backlog.

## Связанные

- [[../decisions/0063-sprint-43-ui-polish]]
- [[../plans/2026-05-10-sprint-43-ui-polish]]
- [[../pre-s43-backlog]]
