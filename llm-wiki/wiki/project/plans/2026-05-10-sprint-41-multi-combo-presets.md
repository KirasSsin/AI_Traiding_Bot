---
title: "Sprint 41 Plan — ATR breakout multi-combo dashboard presets"
type: plan
sprint: 41
created: 2026-05-10
status: done
---

# Sprint 41 Plan — ATR breakout multi-combo dashboard presets

## Scope

Добавить 9 новых dashboard пресетов для ATR breakout стратегии по 9 (symbol, interval)
комбо, найденным endless autoresearch (PID 17127).

Source: `data/autoresearch_endless/best_per_combo.json`

## Acceptance criteria

- `run_atr_breakout_backtest` принимает `params=` kwarg (generalization)
- `ATR_BREAKOUT_LOCKED_PARAMS_BY_COMBO` — 10 комбо с независимыми params
- 9 новых `STRATEGY_PRESETS` в `src/dashboard/backtest_runner.py`
- 20 integration tests pass (PnL floor ±2%, preset registration)
- ADR 0061 + sprint-41 page + wiki sync
- Tag v0.1.0-alpha.41

## Tasks

| ID | Описание | Статус |
|----|----------|--------|
| T1 | Generalize `atr_breakout_runner.py`: params kwarg, PARQUET_BY_COMBO routing, per-interval BARS_PER_YEAR | DONE |
| T2 | `ATR_BREAKOUT_LOCKED_PARAMS_BY_COMBO` — 10 комбо (anti-snooping, ADR 0061) | DONE |
| T3-T9 | 9 новых STRATEGY_PRESETS в dashboard | DONE |
| T10 | ADR 0061 + sprint-41 + wiki sync + tag | DONE |

## Ограничения

- Данные Bybit: 3.3 года (2023-01-01 → 2026-04-26) для 9 новых комбо
- Tolerance тестов: ±2% (расширен vs ±0.5% S40 — новые комбо не верифицированы production)
- Production runtime v0.1: только BTCUSDT Spot — новые пресеты dashboard-only
- Reason codes без изменений (реиспользуются S40 коды)
