---
title: Pre-S42 Backlog — atr_breakout production hardening (kit retrofit)
type: backlog
tags: [sprint-42, retrofit, dashboard-bug, atr-breakout]
created: 2026-05-10
updated: 2026-05-10
status: active
sources:
  - llm-wiki/wiki/project/decisions/0060-sprint-40-atr-breakout-production.md
  - llm-wiki/wiki/project/decisions/0061-sprint-41-multi-combo-presets.md
  - src/backtest/atr_breakout_runner.py
  - src/dashboard/backtest_runner.py
  - src/dashboard/static/dashboard.js
---

# Pre-S42 Backlog

## Контекст

S40 + S41 shipped через bypass kit (operator overnight rule). Operator затем обнаружил три класса bugs/gaps:

1. **UI crash**: Dashboard JS бросает `Cannot read properties of undefined (reading 'toLocaleString')` при выборе любого atr_breakout preset. `atr_breakout_runner` returns 8 keys, dashboard.js:190 ожидает `r.bars_per_year`.
2. **UX clutter**: 10 separate atr_breakout presets per (symbol, TF) — должен быть 1 preset, symbol+TF parametric.
3. **Acceptance discipline gap**: atr_breakout bypasses WFA + DSR + MC + T1-T6 acceptance. UI показывает inflated raw full-period PnL без OOS validation.

## S42 PHASE 2 Brainstorming Trail

### Q1 — Preset refactoring strategy

- **Verdict ROUND 1:** CONFIRM (a) Single preset `atr_breakout`, UI symbol+TF dropdowns drive params lookup в `ATR_BREAKOUT_LOCKED_PARAMS_BY_COMBO[(sym, tf)]`
- **Final:** Consolidate 10 presets → 1. Server-side params lookup. Matches legacy preset UX (ema_crossover_s13 pattern).

### Q2 — Missing combo handling

- **Verdict ROUND 1:** CONFIRM (a) Frontend gates — disable invalid (sym, TF) per preset. Server returns 422 + reason code as fallback.
- **Final:** New endpoint `/api/strategy/<id>/info` exposes `supported_combos`. UI introspects + greys out disabled options.

### Q3 — Runner contract parity (CRITICAL)

- **Verdict ROUND 1:** EXPAND — trader-expert reframed maintainer's full WFA retrofit (option a) к two-phase plan.
- **Critical insight from trader:** `atr_breakout_runner` uses sequential-additive PnL accounting, replay_engine uses Kelly-sized compounded PnL. Wrapping WFA folds on incompatible PnL accounting = silent contract violation — "PASS" verdict from such a run = structurally misleading.
- **Final (Option D):** 
  - S42 = crash fix + honest `RAW_FULL_PERIOD` warning label. atr_breakout_runner returns minimal extras (`bars_per_year`, `warnings=[{level: 'high', code: 'raw_full_period', message: 'Acceptance gate skipped — WFA retrofit pending S43'}]`, `failed_criteria=[]`, `acceptance_gate=null`, `dsr=null`, `mc_p_value=null`).
  - S43 = WFA retrofit — first resolve structural gaps (atr_breakout_runner.py:6-12 documented gaps), then wrap full WFA + DSR + MC + T1-T6.
- **Maintainer accept reasoning:** Scope containment правильно. Better fix crash + ship honest warning, чем blast through with structurally invalid WFA wrapping.

### Q4 — Backward compat

- **Verdict ROUND 1:** CONFIRM (a) Full replace, no aliases. Project в alpha (v0.1.0-alpha.41), no API stability commitment.
- **Final:** 10 old preset_ids removed. v0.1.0-alpha.42 release notes call out breaking change.

### Q5 — S39 volume_breakout scope

- **Verdict ROUND 1:** REVISE — trader-expert split scope.
- **Final:** S42 = add missing UI keys to volume_breakout branch (same cheap fix as atr_breakout). WFA retrofit deferred к S43 (same structural gap reasoning as Q3).
- **Maintainer accept reasoning:** Sensible scope containment. Single architectural fix S43 covers obboth volume_breakout + atr_breakout WFA retrofit.

### Q6 — Sub-period robustness chip

- **Verdict ROUND 1:** CONFIRM (a) Add warning chip per combo: "Robustness: N/5 sub-periods positive". Surfaced alongside DSR + MC verdict.
- **Final:** Compute server-side от subperiod_pnls (5 chunks of equity_curve). Cheap. Display: 5/5 = ok chip, 4/5 = warn chip, ≤3/5 = high warn chip.

### Q7 — ADR strategy

- **Verdict ROUND 1:** CONFIRM (a) ADR 0062 "atr_breakout production hardening — kit retrofit" supersedes 0060+0061.
- **Final:** New ADR. Old ADRs marked status=superseded with pointer.

## S42 Scope (locked)

### In-scope (S42)

1. **Bug fix**: atr_breakout_runner returns missing keys: `bars_per_year`, `warnings`, `failed_criteria=[]`, `acceptance_gate=null`, `dsr=null`, `mc_p_value=null`. Same fix для volume_breakout_runner.
2. **Preset consolidation**: 10 atr_breakout_* presets → 1 `atr_breakout`. Server-side params lookup в `ATR_BREAKOUT_LOCKED_PARAMS_BY_COMBO[(sym, tf)]`.
3. **Frontend gates**: New `/api/strategy/<id>/info` endpoint exposes `supported_combos`. UI introspects.
4. **Sub-period robustness**: Compute N/5 chunks от full-period replay equity_curve. Surface as warning chip.
5. **Honest label**: Display `RAW_FULL_PERIOD — WFA retrofit pending S43` warning chip when acceptance_gate=null.
6. **ADR 0062**: Document refactor. Supersede 0060+0061.
7. **Wiki sync**: Update component pages + index.md + log.md + current-state.md.

### Out-of-scope (deferred к S43)

- Full WFA retrofit для atr_breakout_runner + volume_breakout_runner. Requires first resolving structural PnL accounting gap (sequential-additive vs Kelly-compounded). Will re-examine atr_breakout_runner.py:6-12 documented gaps.
- DSR computation для atr_breakout (depends on WFA folds).
- MC permutation tests (depends on WFA folds).
- N_trials counter increment in cross-trial.json (depends on full validation).

### Deferred carry-overs (NOT addressed S42)

- S38 carry-overs: F8 block_size, M1-M4 bybit-api, Item #7 shim, Item #10 — separate scope, не related к dashboard fix.

## Cross-cutting concerns from trader

- **Money path (none in scope):** Refactor touches presentation layer + runner result shape. NO order placement, NO position sizing changes. Security review unnecessary.
- **Acceptance discipline temporary regression:** S42 ships without acceptance gate (RAW_FULL_PERIOD label). S43 must follow within 1-2 sprints to restore epistemic discipline.

## Escalation для user

(None — no product/regulatory choices в this brainstorm.)

## Files identified для edit (PHASE 3 plan input)

- `src/dashboard/backtest_runner.py` — STRATEGY_PRESETS (lines 92-254), dispatch logic
- `src/backtest/atr_breakout_runner.py` — return dict (add 4 keys)
- `src/backtest/volume_breakout_runner.py` — return dict (add 4 keys, same shape)
- `src/dashboard/static/dashboard.js:190+194` — defensive guards для null acceptance_gate / failed_criteria
- `src/dashboard/api.py` — new `/api/strategy/<id>/info` endpoint
- `tests/integration/test_atr_breakout_baseline_floor.py` — adapt к new preset_id `atr_breakout`
- `tests/dashboard/test_backtest_runner.py` — new tests для preset consolidation + supported_combos
- `llm-wiki/wiki/project/decisions/0060-sprint-40-atr-breakout-production.md` — status=superseded by 0062
- `llm-wiki/wiki/project/decisions/0061-sprint-41-multi-combo-presets.md` — status=superseded by 0062
- `llm-wiki/wiki/project/decisions/0062-sprint-42-atr-breakout-production-hardening.md` — NEW
- `llm-wiki/wiki/project/sprints/sprint-42-atr-breakout-hardening.md` — NEW
- `llm-wiki/wiki/project/architecture/current-state.md` — sprint history row + canonical refs
- `llm-wiki/wiki/index.md` — ADR + sprint entries
- `llm-wiki/wiki/log.md` — append S42 ship entry

## Next phase

PHASE 3 — `superpowers:writing-plans` skill creates `2026-05-10-sprint-42-atr-breakout-hardening.md` plan file. ~10 TDD tasks.
