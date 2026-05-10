---
title: "0063. Sprint 43 — UI polish (preset rename + descriptions + equity chart)"
type: decision
tags: [adr, sprint-43, ui, dashboard, equity-chart, uplot]
created: 2026-05-10
updated: 2026-05-10
status: accepted
sources:
  - llm-wiki/wiki/project/pre-s43-backlog.md
  - llm-wiki/wiki/project/plans/2026-05-10-sprint-43-ui-polish.md
---

# 0063. Sprint 43 — UI polish (preset rename + descriptions + equity chart)

**Status:** accepted
**Date:** 2026-05-10

## Контекст

Operator после S42 запросил три UI улучшения для dashboard:
1. Переименовать preset labels к semantic Russian names с группировкой по trading approach (вместо `[S13 baseline] EMA crossover`)
2. Показать ~150-word RU description при выборе стратегии
3. Добавить equity curve chart как на reference screenshots

WFA retrofit (deferred S42→S43→) → moved к S44 (independent, touches PnL accounting).

## Варианты

(a) Принять scope as-is — UI polish only S43, WFA retrofit к S44.
(b) Объединить WFA retrofit + UI polish — heavy sprint, risk delay.
(c) Defer all к S44+.

## Решение

**Option (a) — UI polish only S43, WFA retrofit к S44.**

Verdicts ROUND 1 trader-expert (5 CONFIRM + 2 REVISE):
- Q1 REVISE → `<optgroup>` grouping by trading approach (two-line label rejected: native `<option>` styling unreliable cross-browser)
- Q4 REVISE → parallel arrays format `{timestamps: [unix_int...], equity_pct: [float...]}` (uPlot native API expects this)
- Other 5 questions: CONFIRM

Library choice: uPlot v1.6.31 vendored locally (`src/dashboard/static/vendor/uPlot.iife.min.js` + `uPlot.min.css`), ~50KB JS + ~2KB CSS. Sharp lines + area fill match terminal aesthetic.

Description authoring: inline в `STRATEGY_PRESETS` dict как `description: str` field (HTML, ~150 words RU each). YAGNI — no separate file/wiki dependency. ~6KB total file growth.

## Последствия

**Pros:**
- Dropdown grouped по trading approach (Тренд-следование / Возврат к среднему / Прорывы) — easier navigation для 6 presets.
- Operator видит strategy logic перед running backtest — reduces "blind run" risk.
- Equity chart visualization restores parity с reference screenshots.
- uPlot vendored locally — no CDN dependency, no build step.
- Defensive empty-data guard для legacy WFA presets без envelope (placeholder shown).

**Cons:**
- 6KB STRATEGY_PRESETS file growth (descriptions).
- ~52KB static asset bundle (uPlot js+css).
- Legacy WFA presets (ema_crossover/mean_reversion/donchian) lack equity_curve в response → placeholder.

**Carry-overs к S44:**
- WFA retrofit (PnL accounting fix — sequential-additive vs Kelly-compounded — + DSR + MC + T1-T6 acceptance gate restoration).
- Drawdown subchart, per-trade markers, monthly returns heatmap (deferred from S43 MVP).
- Legacy WFA preset envelope adoption (currently bypasses envelope contract).

## Verification

- Unit tests: ~955 passed (+9 vs S42 baseline 946).
- Integration tests: ~54 passed (+2).
- mypy --strict: 0 errors.
- Canonical counts: 16/30/74/56 unchanged.
- Manual smoke: dropdown shows 3 optgroups + 6 strategies; description block renders на каждый switch; equity chart shows для atr_breakout/volume_breakout, placeholder для legacy presets.

## Связанные

- [[../sprints/sprint-43-ui-polish]]
- [[../plans/2026-05-10-sprint-43-ui-polish]]
- [[../pre-s43-backlog]]
- [[0062-sprint-42-atr-breakout-hardening]]
