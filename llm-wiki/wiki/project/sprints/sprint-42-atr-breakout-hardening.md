---
title: "Sprint 42 — atr_breakout production hardening (kit retrofit)"
type: sprint
tags: [sprint-42, retrofit, dashboard, atr-breakout, contract]
created: 2026-05-10
updated: 2026-05-10
status: completed
sources:
  - llm-wiki/wiki/project/decisions/0062-sprint-42-atr-breakout-hardening.md
  - llm-wiki/wiki/project/plans/2026-05-10-sprint-42-atr-breakout-hardening.md
  - llm-wiki/wiki/project/pre-s42-backlog.md
---

# Sprint 42 — atr_breakout production hardening

## Цель

Fix dashboard JS crash при выборе atr_breakout/volume_breakout preset (`Cannot read properties of undefined (reading 'toLocaleString')`), consolidate 10 → 1 atr_breakout preset с (symbol, TF) parametric, добавить honest RAW_FULL_PERIOD label до S43 WFA retrofit. Sprint выполнен через формальный 9-фазовый kit cycle (исправление S40+S41 bypass).

## Доставленная функциональность

### Код

- `src/backtest/research_runner_envelope.py` — НОВЫЙ helper `build_research_runner_envelope()`, returns 17-key dashboard contract dict с null sentinels для acceptance_gate/DSR/MC + high-level "raw_full_period" warning + N/5 sub-period robustness chip.
- `src/backtest/atr_breakout_runner.py` — wrap public `run_atr_breakout_backtest()` через envelope helper. Equity_curve строится из trades. NaN guard для sharpe/win_rate.
- `src/backtest/volume_breakout_runner.py` — same envelope wrap для S39 volume_breakout runner.
- `src/dashboard/backtest_runner.py` — DELETE 10 atr_breakout_* preset entries → INSERT 1 unified `atr_breakout` preset с `supported_combos: list[tuple[str, str]]` (10 combos). Dispatch: envelope merge (base) + run_id/cached/request overlays для atr_breakout AND volume_breakout (раньше cherry-pick 4 keys выбрасывал envelope).
- `src/dashboard/app.py` — НОВЫЙ endpoint `GET /api/strategy/{id}/info` exposes preset metadata + supported_combos. `POST /api/backtest` enforcement: 422 при invalid (symbol, interval) для presets с supported_combos.
- `src/dashboard/static/dashboard.js` — defensive guards (`r.bars_per_year ?? 0`, `r.failed_criteria ?? []`, `r.verdict ?? "—"`). Новые `fetchStrategyInfo()` + `applyComboGates()` функции — greys out invalid sym/TF options dynamically. Wired к stratSel + symSel change events. Initial gating apply on page load.
- `src/dashboard/static/dashboard.css` — `.verdict-raw { color: #f0a000 }` для RAW verdict label.

### Тесты

- `tests/unit/test_research_runner_envelope.py` — 6 unit tests (envelope contract: required keys / RAW verdict / raw_full_period chip / 5/5 robustness / 3/5 robustness / failed_criteria array).
- `tests/unit/test_supported_combos_endpoint.py` — 6 unit tests (endpoint returns combos / 404 unknown / legacy preset empty / 422 invalid combo / valid combo не 422 / metadata fields).
- `tests/integration/test_atr_breakout_dashboard_contract.py` — 14 integration tests (envelope keys / RAW verdict / raw_full_period chip / request shape / PnL regression BTC 4H + 10 parametrized combos / old preset_ids removed / supported_combos field / dispatch envelope merge).
- `tests/integration/test_volume_breakout_dashboard_contract.py` — 4 integration tests (envelope keys / RAW verdict / raw_full_period chip / request shape).
- `tests/integration/test_atr_breakout_baseline_floor.py` — updated preset_id `atr_breakout_iter_endless` → `atr_breakout`.
- `tests/integration/test_atr_breakout_multi_combo.py` — removed preset_id column; updated к unified preset.
- `tests/unit/test_dashboard_atr_breakout_preset.py` — rewritten для unified preset (S42 not S40, supported_combos not locked_*).

### Wiki

- ADR 0062 (THIS sprint): `0062-sprint-42-atr-breakout-hardening.md` accepted.
- ADR 0060 marked superseded by 0062.
- ADR 0061 marked superseded by 0062.
- sprint-42 page (THIS file).
- current-state.md: header date → S42, sprint history row append, ADR count 61→62, sprint pages 45→46.
- index.md: ADR 0062 + sprint-42 entries; 0060/0061 marked superseded.
- log.md: S42 sprint-end entry.
- atr-breakout-strategy component page: preset_id rename `atr_breakout_iter_endless` → `atr_breakout`. Envelope contract reference. RAW_FULL_PERIOD note.

### FSM рост

**0** (UNCHANGED — pure refactor + bug fix).

### Reason codes

**0 новых** (UNCHANGED 56 — pure refactor + bug fix).

### Tests/качество

- Unit: **946 passed** (+41 vs pre-S42 baseline 905)
- Integration: **52 passed** (+19 vs pre-S42 baseline 33)
- mypy --strict: **0 errors** на 84 source files
- ruff/format: чисто
- Canonical: 16/30/74/56 (UNCHANGED)

## Решения и отклонения

- **Q3 EXPAND (trader-expert ROUND 1):** Maintainer recommended Option (a) full WFA retrofit. Trader reframed scope, recommended Option (b) — crash fix + RAW_FULL_PERIOD label в S42, WFA retrofit deferred к S43. Reason: `atr_breakout_runner` использует sequential-additive PnL accounting, replay engine — Kelly-sized compounded PnL. Wrapping WFA folds на incompatible accounting = silent contract violation, PASS verdict было бы structurally misleading. Maintainer accepted.
- **Q5 REVISE (trader-expert ROUND 1):** Maintainer recommended включить S39 volume_breakout в S42 scope полностью. Trader split: S42 = same envelope wrap для volume_breakout (cheap, no structural change); WFA retrofit defer к S43 (same gap reasoning). Maintainer accepted.

Other 5 questions (Q1, Q2, Q4, Q6, Q7) — CONFIRM verdicts, no disagreement.

## Влияние на следующие спринты

**S43 must address (BLOCKING):**
- Resolve atr_breakout_runner structural PnL accounting gap (sequential-additive vs Kelly-compounded).
- Wrap full WFA + DSR + MC + T1-T6 acceptance gate для atr_breakout + volume_breakout.
- N_trials counter increment в cross-trial (S40+S41+S42 = each combo separate hypothesis vs ensemble decision).
- Restore epistemic discipline (currently `verdict: "RAW"` для всех research-mode presets).

## Перенесённые задачи

- Все S38 carry-overs (F8 block_size, M1-M4 bybit-api, Item #7 shim, Item #10) — unaffected by S42, остаются в backlog.

## Связанные

- [[../decisions/0062-sprint-42-atr-breakout-hardening]]
- [[../plans/2026-05-10-sprint-42-atr-breakout-hardening]]
- [[../pre-s42-backlog]]
- [[../decisions/0060-sprint-40-atr-breakout-pre-registration]] (superseded)
- [[../decisions/0061-sprint-41-atr-breakout-multi-combo-presets]] (superseded)
