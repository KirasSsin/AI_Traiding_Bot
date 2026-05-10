---
title: "Sprint 41 — ATR breakout multi-combo dashboard presets"
type: summary
sprint: 41
tag: v0.1.0-alpha.41
created: 2026-05-10
updated: 2026-05-10
status: stable
tags: [sprint-41, atr-breakout, multi-combo, dashboard, autoresearch, locked-params]
---

# Sprint 41 — ATR breakout multi-combo dashboard presets

**Тег:** `v0.1.0-alpha.41`  
**Дата:** 2026-05-10  
**ADR:** [[../decisions/0061-sprint-41-atr-breakout-multi-combo-presets]]  
**Ветка:** `feature/sprint-41-multi-combo-presets` → `main`

## TL;DR

Добавлено 9 новых dashboard пресетов для ATR breakout стратегии по 9 (symbol, interval) комбо,
найденным endless autoresearch (PID 17127). Каждый пресет имеет независимо заблокированные
параметры из `data/autoresearch_endless/best_per_combo.json`.

## Мотивация

S40 интегрировал ATR breakout для BTCUSDT 4H (+819.81% за 8.7 лет).
Endless autoresearch нашёл ещё 9 прибыльных (symbol, interval) комбо.
Оператор хочет видеть PnL для каждого комбо в UI.

## Выполненные задачи

| Задача | Статус | Описание |
|--------|--------|----------|
| T1 | DONE | Обобщение `atr_breakout_runner.py`: params kwarg, PARQUET_BY_COMBO routing, per-interval BARS_PER_YEAR |
| T2 | DONE | `ATR_BREAKOUT_LOCKED_PARAMS_BY_COMBO` — 10 комбо с независимыми params (anti-snooping) |
| T3-T9 | DONE | 9 новых STRATEGY_PRESETS в `src/dashboard/backtest_runner.py` |
| T10 | DONE | ADR 0061 + sprint-41 page + current-state.md + index.md + log.md + SPRINT_STATE |

## Новые пресеты (9)

| preset_id | symbol | interval | PnL (3.3y) | n_trades |
|-----------|--------|----------|------------|---------|
| `atr_breakout_sol_4h_s41` | SOLUSDT | 4H | +264.29% | 71 |
| `atr_breakout_eth_1h_s41` | ETHUSDT | 1H | +181.74% | 109 |
| `atr_breakout_btc_15m_s41` | BTCUSDT | 15M | +107.35% | 245 |
| `atr_breakout_btc_1h_s41` | BTCUSDT | 1H | +146.36% | 106 |
| `atr_breakout_sol_1h_s41` | SOLUSDT | 1H | +214.08% | 124 |
| `atr_breakout_eth_4h_s41` | ETHUSDT | 4H | +152.30% | 28 |
| `atr_breakout_sol_15m_s41` | SOLUSDT | 15M | +150.51% | 230 |
| `atr_breakout_btc_1d_s41` | BTCUSDT | 1D | +167.54% | 32 |
| `atr_breakout_eth_15m_s41` | ETHUSDT | 15M | +35.53% | 240 |

Данные: Bybit parquet 2023-01-01 → 2026-04-26 (3.3 года).

## Тесты

- **20 новых integration tests** в `tests/integration/test_atr_breakout_multi_combo.py`
- Все 20 pass (PnL floor ±2%, n_trades ±5, preset registration)
- S40 regression: 8/8 tests pass
- Unit tests: 934 pass (no regression)
- Pre-commit: ruff + mypy 0 errors

## Canonical counts delta

| Метрика | До (S40) | После (S41) |
|---------|----------|-------------|
| ADRs | 60 | **61** |
| Sprint pages | 44 | **45** |
| Dashboard presets | 5 | **14** |

Reason codes: без изменений (переиспользуются S40 коды, 56 total).

## Примечания

- Production runtime (v0.1) поддерживает только BTCUSDT Spot — новые пресеты dashboard-only
- BTCUSDT 4H использует Binance data (8.7 лет); все 9 новых комбо — Bybit data (3.3 года)
- Gate 2 forward paper-trade для новых комбо: N≥10 trades BLOCKER к real capital

## Связанные страницы

- [[../decisions/0061-sprint-41-atr-breakout-multi-combo-presets]]
- [[sprint-40-atr-breakout-production]]
- [[../components/atr-breakout-strategy]]
