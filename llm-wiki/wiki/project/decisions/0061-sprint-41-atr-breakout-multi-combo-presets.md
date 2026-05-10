---
title: "ADR 0061: Расширение ATR breakout до 9 дополнительных (symbol, interval) комбо (S41)"
type: decision
status: superseded
created: 2026-05-10
updated: 2026-05-10
tags: [atr-breakout, multi-combo, locked-params, autoresearch, dashboard, sprint-41]
sources: [data/autoresearch_endless/best_per_combo.json]
---

# ADR 0061: Расширение ATR breakout до 9 дополнительных (symbol, interval) комбо (S41)

**Статус:** superseded by [[0062-sprint-42-atr-breakout-hardening]]
**Superseded:** 2026-05-10 (заменён ADR 0062 — preset consolidation + envelope contract retrofit)
**Дата:** 2026-05-10  
**Ссылки:** [[0060-sprint-40-atr-breakout-pre-registration]] (ADR-0060 — исходный BTCUSDT 4H)

## Контекст

S40 интегрировал ATR breakout стратегию для BTCUSDT 4H с заблокированными параметрами
(`atr_period=9, atr_breakout_mult=2.5, atr_stop_period=21, atr_stop_mult=1.5`),
получив +819.81% за 8.7 лет, Sharpe=1.11, 5/5 суб-периодов положительны.

Endless autoresearch (PID 17127) нашёл победителей для 10 (symbol, interval) комбо
(источник: `data/autoresearch_endless/best_per_combo.json`). Оператор хочет добавить
9 новых комбо как dashboard пресеты, чтобы UI показывал фактический PnL per combo.

## Контекст данных

BTCUSDT 4H использует данные Binance (`data/BTCUSDT_4h_binance.parquet`, 8.7 лет с 2017-08-17).
Все 9 новых комбо используют данные Bybit (`data/{SYMBOL}_{interval}.parquet`, 3.3 года с 2023-01-01).

## Решение

### Суб-решение 1: per-combo независимые параметры (Option B)

Каждое комбо имеет независимо заблокированные параметры в `ATR_BREAKOUT_LOCKED_PARAMS_BY_COMBO`
(словарь с ключом `(symbol, interval)`). Это — anti-snooping audit trail: каждый набор параметров
документирован отдельно, что исключает возможность post-hoc оправдания shared-param решений.

Источник: `data/autoresearch_endless/best_per_combo.json` (live JSON от autoresearch процесса).

### Суб-решение 2: обобщение runner

`run_atr_breakout_backtest(*, symbol, interval, start_date, end_date, params=None)`:
- Принимает явный `params=` kwarg для гибкости (тесты, кастомные запуски)
- При `params=None` — fallback к `ATR_BREAKOUT_LOCKED_PARAMS_BY_COMBO[symbol, interval]`
- `PARQUET_BY_COMBO` маппинг 10 комбо → parquet файлы
- `_BARS_PER_YEAR_BY_INTERVAL` per-interval аннуализация (зеркало autoresearch)
- Нормализация схемы: handles `ts` (Binance) и `time` (Bybit) колонки

### Суб-решение 3: 9 dashboard пресетов

В `STRATEGY_PRESETS` (`src/dashboard/backtest_runner.py`) добавлены 9 записей:

| preset_id | symbol | interval | expected_pnl | n_trades |
|-----------|--------|----------|--------------|---------|
| `atr_breakout_sol_4h_s41` | SOLUSDT | 240 | +264.29% | 71 |
| `atr_breakout_eth_1h_s41` | ETHUSDT | 60 | +181.74% | 109 |
| `atr_breakout_btc_15m_s41` | BTCUSDT | 15 | +107.35% | 245 |
| `atr_breakout_btc_1h_s41` | BTCUSDT | 60 | +146.36% | 106 |
| `atr_breakout_sol_1h_s41` | SOLUSDT | 60 | +214.08% | 124 |
| `atr_breakout_eth_4h_s41` | ETHUSDT | 240 | +152.30% | 28 |
| `atr_breakout_sol_15m_s41` | SOLUSDT | 15 | +150.51% | 230 |
| `atr_breakout_btc_1d_s41` | BTCUSDT | D | +167.54% | 32 |
| `atr_breakout_eth_15m_s41` | ETHUSDT | 15 | +35.53% | 240 |

### Суб-решение 4: dispatch с per-preset params

`run_backtest()` передаёт `preset["indicators"]["atr_breakout"]` как `params=`
к `run_atr_breakout_backtest()`. Каждый пресет несёт свои locked params,
что даёт audit trail на уровне dashboard.

### Заблокированные параметры по комбо

```python
ATR_BREAKOUT_LOCKED_PARAMS_BY_COMBO = {
    ("BTCUSDT", "240"): {"atr_period": 9,  "atr_breakout_mult": 2.5, "atr_stop_period": 21, "atr_stop_mult": 1.5},
    ("BTCUSDT", "60"):  {"atr_period": 9,  "atr_breakout_mult": 2.5, "atr_stop_period": 21, "atr_stop_mult": 3.0},
    ("BTCUSDT", "15"):  {"atr_period": 9,  "atr_breakout_mult": 3.0, "atr_stop_period": 14, "atr_stop_mult": 3.0},
    ("BTCUSDT", "D"):   {"atr_period": 9,  "atr_breakout_mult": 1.0, "atr_stop_period": 9,  "atr_stop_mult": 3.0},
    ("ETHUSDT", "240"): {"atr_period": 14, "atr_breakout_mult": 2.5, "atr_stop_period": 14, "atr_stop_mult": 1.5},
    ("ETHUSDT", "60"):  {"atr_period": 14, "atr_breakout_mult": 2.5, "atr_stop_period": 21, "atr_stop_mult": 1.5},
    ("ETHUSDT", "15"):  {"atr_period": 9,  "atr_breakout_mult": 3.0, "atr_stop_period": 14, "atr_stop_mult": 2.0},
    ("SOLUSDT", "240"): {"atr_period": 21, "atr_breakout_mult": 1.5, "atr_stop_period": 9,  "atr_stop_mult": 2.0},
    ("SOLUSDT", "60"):  {"atr_period": 9,  "atr_breakout_mult": 2.0, "atr_stop_period": 21, "atr_stop_mult": 3.0},
    ("SOLUSDT", "15"):  {"atr_period": 21, "atr_breakout_mult": 2.5, "atr_stop_period": 9,  "atr_stop_mult": 3.0},
}
```

## Последствия

**Положительные:**
- Dashboard показывает PnL для всех 10 (symbol, interval) комбо из autoresearch
- Каждое комбо изолировано: params, parquet путь, пресет — независимы
- Тесты: 20 новых integration тестов гарантируют PnL floor ±2% для каждого комбо
- Runner обобщён: любое будущее комбо добавляется в 3 словаря (без изменения логики)
- Anti-snooping: параметры зафиксированы ДО публикации ADR

**Ограничения / Осознанные компромиссы:**
- Данные Bybit: только 3.3 года (vs 8.7 лет для BTCUSDT 4H Binance) — меньше статистики
- Толерантность тестов: ±2% (vs ±0.5% для первичного BTCUSDT 4H) — новые комбо не верифицированы в production
- Новые reason codes не добавлены — переиспользуются S40 коды (ENTRY_LONG_ATR_BREAKOUT / EXIT_FLAT_ATR_REVERSE / EXIT_FLAT_ATR_STOP_AB)
- Production runtime: v0.1 поддерживает только BTCUSDT Spot — новые пресеты dashboard-only (backtesting visualization)

## Связанные ADR

- [[0060-sprint-40-atr-breakout-pre-registration]] — первичные locked params BTCUSDT 4H
- [[0014-walk-forward-train2000-test500]] — WFA methodology (не применяется к atr_breakout runner)
- [[0039-sprint-25-dashboard]] — dashboard architecture

## Тесты

- `tests/integration/test_atr_breakout_multi_combo.py` — 20 integration tests:
  - `test_multi_combo_preset_registered` × 9 (each preset in STRATEGY_PRESETS)
  - `test_multi_combo_runner_pnl_floor` × 9 (PnL ±2% floor для каждого комбо)
  - `test_atr_breakout_runner_accepts_params_kwarg` (generalization)
  - `test_atr_breakout_locked_params_by_combo_has_all_combos` (10 combos complete)
