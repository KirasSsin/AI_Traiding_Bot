---
title: Pre-S43 Backlog — UI polish (preset rename + descriptions + equity chart)
type: backlog
tags: [sprint-43, ui, dashboard, equity-chart, preset-rename]
created: 2026-05-10
updated: 2026-05-10
status: active
sources:
  - llm-wiki/wiki/project/decisions/0062-sprint-42-atr-breakout-hardening.md
  - src/dashboard/backtest_runner.py
  - src/dashboard/static/dashboard.js
---

# Pre-S43 Backlog

## Контекст

Operator после S42 запросил три UI улучшения:

1. **Переименовать presets** — текущие labels `[S13 baseline] EMA crossover (12/26 + ADX + RSI)` exposing technical sprint identifier. Operator хочет видеть semantic Russian names описывающие торговый подход.
2. **Описание стратегии на странице** — при выборе стратегии должен видеть ~150-word Russian explanation (entry/exit rules, params, suitable regime).
3. **Equity curve chart** — operator показал референсные screenshots (clean line chart + area fill + date axis). Сейчас dashboard только text tables.

WFA retrofit (был deferred S43 from S42) → moved к S44 (independent — touches PnL accounting, not UI).

## S43 PHASE 2 Brainstorming Trail

### Q1 — Naming convention для preset labels

- **Verdict ROUND 1:** REVISE → option (d) `<optgroup>` grouping by trading approach
- **Trader rationale:** `<select><option>` native widget renders OS-controlled. CSS overflow / unicode / multi-line tricks unreliable между browsers (Chrome truncates, Safari ignores `title=` без hover). Audit trail solved by Q2 description block. `<optgroup>` ~10 lines JS, no new API.
- **Maintainer accept reasoning:** Sound — confirmed `<option>` styling limitations. Optgroup grouping clean + mobile-friendly.
- **Preset rename mapping (ratified):**

| Preset ID | Optgroup | Russian semantic name |
|-----------|----------|----------------------|
| `ema_crossover_s13` | Тренд-следование | Тренд EMA 12/26 + ADX фильтр |
| `mean_reversion_s15` | Возврат к среднему | Возврат к среднему RSI/Bollinger (классика) |
| `mean_reversion_s17_relaxed` | Возврат к среднему | Возврат к среднему RSI/Bollinger (мягкий) |
| `donchian_breakout_s35` | Прорывы | Канал Дончиана пробой |
| `volume_breakout_iter10` | Прорывы | Прорыв с подтверждением объёма |
| `atr_breakout` | Прорывы | ATR-адаптивный пробой (multi-combo) |

### Q2 — Description location/format

- **Verdict ROUND 1:** CONFIRM (a) collapsible block с reuse `_strategyInfoCache`
- **Final:** Block между STRATEGY dropdown и SYMBOL dropdown. Default expanded на load для familiarity. Plain HTML strings (no markdown lib needed для ~150 words). Cache leveraged from S42's `applyComboGates()` data path.

### Q3 — Chart library choice

- **Verdict ROUND 1:** CONFIRM (a) uPlot
- **Final:** uPlot v1.6.x, locally bundled (`src/dashboard/static/uPlot.iife.min.js` ~40KB + `uPlot.min.css`). Sharp lines + area fill + axis labels OOTB. Matches terminal aesthetic.

### Q4 — Equity data format

- **Verdict ROUND 1:** REVISE → parallel arrays format
- **Trader rationale:** uPlot native API expects `[[timestamps_unix_seconds...], [series1...], [series2...]]`. Format `[{ts: ISO, equity_pct: float}]` requires per-point parsing (ISO→Date→Unix) + restructuring. Parallel arrays save ~30% bytes + zero conversion overhead.
- **Maintainer accept:** Verified uPlot expects this format.
- **Final envelope addition:**
```python
"equity_curve": {
    "timestamps": [1672531200, 1672534800, ...],  # unix seconds, int
    "equity_pct": [0.0, 1.23, 2.45, ...],          # cumulative PnL %, float
}
```
- **PHASE 3 sub-task:** verify `_TradeRecord.exit_idx` → `df.index[exit_idx].timestamp()` accessible in BOTH runners (atr_breakout, volume_breakout).

### Q5 — Description authoring approach

- **Verdict ROUND 1:** CONFIRM (a) inline в `STRATEGY_PRESETS` dict
- **Final:** Each preset gets `description: str` field (Russian HTML allowed). 6 strategies × ~1KB = ~6KB growth (acceptable). YAGNI — no separate file/wiki dep.

### Q6 — MVP scope

- **Verdict ROUND 1:** CONFIRM (a)
- **Final:** S43 MVP = equity curve only (line + area fill, date axis, total PnL display). DEFERRED к S44+: drawdown subchart, per-trade markers, monthly returns heatmap, per-fold equity curves для WFA presets.

### Q7 — WFA retrofit к S44

- **Verdict ROUND 1:** CONFIRM (a)
- **Final:** S44 = WFA retrofit (PnL accounting structural fix + DSR + MC + acceptance gate restoration). Independent от UI.

## Cross-cutting concerns

- **CC1:** uPlot default CSS clashes с terminal palette (white grid, blue lines, sans-serif). Override CSS = dedicated task в S43 plan.
- **CC3:** Legacy WFA presets (ema_crossover/mean_reversion/donchian) NOT envelope-wrapped — no `equity_curve` field. `renderResult()` MUST guard: `if (!r.equity_curve?.timestamps?.length) showPlaceholder()`. Don't crash empty uPlot container.
- **CC4:** `/api/strategies` currently returns `{id, label, type}` only. Add `description` field к prevent third fetch roundtrip when populating dropdown + initial description.

## S43 Scope (locked)

### In-scope (S43)

1. **Preset rename** — STRATEGY_PRESETS labels updated к semantic Russian names; add `optgroup` field per preset (Тренд/Возврат/Прорывы).
2. **Strategy description field** — `description: str` per preset (~150 words RU each, plain HTML).
3. **Dashboard optgroup grouping** — JS rebuilds `<select>` с `<optgroup>` per trading approach.
4. **Description block UI** — collapsible expandable block в configure section, hooks к existing `_strategyInfoCache`.
5. **Endpoint extension** — `/api/strategies` returns `description`; `/api/strategy/{id}/info` returns `description` + `optgroup`.
6. **uPlot vendored** — bundle `uPlot.iife.min.js` + `uPlot.min.css` в `src/dashboard/static/vendor/`.
7. **Equity curve в envelope** — `build_research_runner_envelope()` adds `equity_curve: {timestamps, equity_pct}` parallel arrays.
8. **Runners → envelope с timestamps** — atr_breakout + volume_breakout pass df timestamps к envelope helper.
9. **Equity chart render** — `renderResult()` builds uPlot chart in `<div id="equity-chart">`. Empty-data guard для legacy WFA presets (placeholder).
10. **Terminal-themed uPlot CSS** — override default uPlot styling к match terminal aesthetic (green/amber lines, dark grid, monospace axis labels).
11. **ADR 0063** — document UI polish decisions, preset rename mapping, uPlot library choice rationale.
12. **Wiki sync** — sprint-43 page + index.md + log.md + current-state.md.

### Out-of-scope (S43)

- WFA retrofit (S44) — DSR + MC + T1-T6 restoration.
- Drawdown chart subpane.
- Per-trade markers (entry/exit dots на chart).
- Monthly returns heatmap.
- Mobile touch gestures для chart.

## Files identified для edit (PHASE 3 plan input)

- `src/dashboard/backtest_runner.py` — STRATEGY_PRESETS rename + description + optgroup fields
- `src/dashboard/app.py` — `/api/strategies` extended + `/api/strategy/{id}/info` extended
- `src/dashboard/static/dashboard.js` — optgroup rendering, description block, equity chart render, defensive guards
- `src/dashboard/static/dashboard.css` — uPlot terminal overrides, description block styling
- `src/dashboard/static/vendor/uPlot.iife.min.js` (NEW)
- `src/dashboard/static/vendor/uPlot.min.css` (NEW)
- `src/dashboard/templates/index.html` — `<div id="strategy-description">` + `<div id="equity-chart">` + uPlot script tag
- `src/backtest/research_runner_envelope.py` — equity_curve parallel arrays output
- `src/backtest/atr_breakout_runner.py` — pass df timestamps к envelope helper
- `src/backtest/volume_breakout_runner.py` — same
- `tests/unit/test_research_runner_envelope.py` — envelope equity_curve format tests
- `tests/unit/test_supported_combos_endpoint.py` — `description` field в info endpoint test
- `tests/integration/test_atr_breakout_dashboard_contract.py` — equity_curve presence tests
- `llm-wiki/wiki/project/decisions/0063-sprint-43-ui-polish.md` (NEW)
- `llm-wiki/wiki/project/sprints/sprint-43-ui-polish.md` (NEW)

## Next phase

PHASE 3 — `superpowers:writing-plans` skill creates `2026-05-10-sprint-43-ui-polish.md` plan. ~12 TDD tasks.
