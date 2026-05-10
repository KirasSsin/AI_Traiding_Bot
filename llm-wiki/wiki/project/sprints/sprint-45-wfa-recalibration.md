---
title: "Sprint 45 — WFA recalibration + quant discipline + uniform 3.3y data"
type: sprint
tags: [sprint-45, wfa-recalibration, dsr, cross-trial-log, data-uniform, honest-close]
created: 2026-05-10
updated: 2026-05-10
status: completed
sources:
  - llm-wiki/wiki/project/decisions/0065-sprint-45-wfa-recalibration.md
  - llm-wiki/wiki/project/plans/2026-05-10-sprint-45-wfa-recalibration.md
  - llm-wiki/wiki/project/pre-s45-backlog.md
---

# Sprint 45 — WFA recalibration

## Цель

Исправить quant discipline gaps S44 (B1 cross_trial_log dedup, C1 n_trials per-strategy, B2 train slice docs), унифицировать 3.3y data, выполнить WFA recalibration (1 attempt per ESC-1), получить честный вердикт для S46 decision.

## Доставленная функциональность

### Код
- `src/backtest/atr_breakout_runner.py` — `PARQUET_BY_COMBO[(BTCUSDT,240)]` updated к 3.3y; `_run_atr_breakout_wfa()` n_trials=10 + tier-aware defaults
- `src/backtest/volume_breakout_runner.py` — `_run_volume_breakout_wfa()` n_trials=1 + tier-aware
- `src/backtest/research_wfa.py` — default n_trials 11→1; `get_wfa_tier_params()` helper; B2 train slice docs
- `src/analytics/cross_trial_log.py` — `append_trial()` idempotency guard (B1)
- `data/cross_trial_sharpes.json` — reset к empty
- `data/_archive/BTCUSDT_4h_binance.parquet` — moved 8.7y file out of registry

### Тесты
- `tests/unit/test_cross_trial_log_dedup.py` (NEW) — 5 idempotency tests
- `tests/unit/test_research_wfa.py` — 5 new (4 tier + 1 default n_trials)
- `tests/integration/test_atr_breakout_wfa.py` — 3 new (n_trials assertion + tier wiring)
- `tests/integration/test_volume_breakout_wfa.py` — 1 new (n_trials assertion)
- `tests/integration/test_atr_breakout_baseline_floor.py` — 1 new (3.3y data uniform)

### Wiki
- ADR 0014 amendment (S45 low-freq tier)
- ADR 0060 amendment (3.3y baseline)
- ADR 0065 (THIS sprint)
- sprint-45 page (THIS file)
- current-state.md sprint history + counts ADRs 64→65, sprint pages 48→49
- index.md ADR 0065 + sprint-45 entries
- log.md S45 sprint-end entry

### Рост FSM
**0** (UNCHANGED — pure quant discipline work).

### Reason codes
**0 новых** (UNCHANGED 56).

### Тесты / качество
- Unit: ~956 → ~970 (+14)
- Integration: ~54 → ~58 (+4)
- mypy --strict: 0 errors
- Canonical: 16/30/74/56 (UNCHANGED)

## Решения и отклонения

- **Q1 REVISE:** Pure Path A (recalibration only), не hybrid. Path B (new strategies) excluded по operator.
- **Q2 REVISE:** Universal lever (test_bars 500→250 + train_bars 2000→1500 для 4H/D), не per-strategy config knobs.
- **Q4 REVISE:** Dedup guard в `CrossTrialLog.append_trial()` (architectural), не callers.
- **Q5 amendment:** Default n_trials 11→1 (fail-safe), atr explicit 10, vb explicit 1.
- **Q6 DEFER:** New strategy seed → operator excluded entirely.
- **Q8 REVISE:** 8 tasks final (added uniform data + ADR 0060 amendment as T1-T2).

## Честный вердикт (S45 actual)

**ВСЕ 11 combos WFA_FAIL** (10 statistical + 1 data-limited). Recalibration не unlocked ни одного combo — low-freq tier сделал 4H ХУЖЕ (fewer bars per fold = fewer signals).

**ESC-1 (a) trigger:** confirmed. 0/11 PASS → S46 honest portfolio close.

См. ADR 0065 per-combo verdict table.

## Влияние на следующие спринты

**S46 (BLOCKING):**
- Honest portfolio close — пометить все 11 presets WFA_FAIL definitively
- Operator strategic decision: archive/disable presets, OR keep с persistent warning
- Path B excluded — оператор должен решить future trajectory separately

**S46+ (UI deferrals from S43):**
- Drawdown subchart, per-trade markers, monthly heatmap

**S47+ (S37/S38 long-standing):**
- F8 block_size, M1-M4 bybit-api, Item #7 shim, Item #10

## Перенесённые задачи

S37/S38 long-standing items unaffected — остаются в backlog к S47+.

## Связанные

- [[../decisions/0065-sprint-45-wfa-recalibration]]
- [[../plans/2026-05-10-sprint-45-wfa-recalibration]]
- [[../pre-s45-backlog]]
