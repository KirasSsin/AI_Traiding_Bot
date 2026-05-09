---
title: Sprint 40 — ATR breakout production integration
type: summary
tags: [sprint-40, atr-breakout, autoresearch-integration, locked, ru]
created: 2026-05-10
updated: 2026-05-10
status: stable
sources:
  - project/decisions/0060-sprint-40-atr-breakout-pre-registration.md
  - src/signalgen/atr_breakout_strategy.py
  - src/backtest/atr_breakout_runner.py
---

# Sprint 40 — ATR breakout production integration

**Тег:** `v0.1.0-alpha.40`
**Дата:** 2026-05-10
**Ветка:** `feature/sprint-40-atr-breakout-production`
**ADR:** [[../decisions/0060-sprint-40-atr-breakout-pre-registration]]

## Резюме

Autoresearch iter 1 нашёл победителя `atr_breakout` на BTCUSDT 4H с результатом **+819.81% (8.7y) / Sharpe 1.11 / 5/5 sub-periods positive** — первый 5/5 в истории проекта. Sprint 40 реализует production integration 7 задач (T1-T7) per ADR 0060.

## Выполненные задачи

### T1 — ReasonCode enum (+3 кода, 53→56)

`src/risk/reason_codes.py`:
- `ENTRY_LONG_ATR_BREAKOUT` (#54)
- `EXIT_FLAT_ATR_REVERSE` (#55)
- `EXIT_FLAT_ATR_STOP_AB` (#56)

Тесты: `tests/unit/test_reason_codes_s40.py` (4 теста). Обновлены count assertions в `test_reason_codes.py`, `test_reason_codes_s8a.py`, `test_reason_codes_s39.py`, `test_risk_models.py`.

### T2 — ATRBreakoutStrategy class

`src/signalgen/atr_breakout_strategy.py`:
- `ATR_BREAKOUT_LOCKED_PARAMS` — canonical constant (source of truth)
- `ATRBreakoutStrategy.on_bar()` — verbatim порт autoresearch logic
- `_wilder_atr()` — exact port `scripts/autoresearch_endless.py::_atr()`
- Warmup gate = `max(9, 21) + 3 = 24` bars
- Приоритет выхода: reverse breakdown (1) → ATR stop (2)

Тесты: `tests/unit/test_atr_breakout_strategy.py` (8 тестов).

### T3 — Production runner + integration baseline floor

`src/backtest/atr_breakout_runner.py`:
- `run_atr_breakout_backtest()` — verbatim порт research kernel
- Обнаруживает `(BTCUSDT, 240)` → загружает Binance parquet напрямую
- Тянет locked params из `ATR_BREAKOUT_LOCKED_PARAMS`

`tests/integration/test_atr_breakout_baseline_floor.py` (8 тестов, `@pytest.mark.integration`):
- Полный период: 819.81% PnL, 69 trades, Sharpe ≥ 0.5
- 5/5 sub-periods positive, каждый в пределах ±0.5% от baseline
- Production runner replication check
- Data coverage check (≥ 15000 баров)

### T4 — Dashboard preset

`src/dashboard/backtest_runner.py`:
- Preset `atr_breakout_iter_endless` со LOCKED параметрами ADR 0060
- Early-return dispatch `preset.type == "atr_breakout"` → `atr_breakout_runner`
- ENFORCED BTCUSDT + 4H (как volume_breakout_iter10)

Тесты: `tests/unit/test_dashboard_atr_breakout_preset.py` (4 теста).

### T5 — Wiki docs

- ADR 0060: `wiki/project/decisions/0060-sprint-40-atr-breakout-pre-registration.md`
- Component page: `wiki/project/components/atr-breakout-strategy.md`
- Sprint page: `wiki/project/sprints/sprint-40-atr-breakout-production.md` (этот файл)
- Обновлён `wiki/trading/concepts/reason-codes.md` (53→56, +3 кода, таблица изменений)
- Обновлён `wiki/project/architecture/current-state.md` (canonical counts + sprint history)
- Обновлён `wiki/index.md` (ADR + sprint + component entries)
- Добавлена запись `wiki/log.md` (sprint-end)

## Ключевые технические решения

### Binance данные вместо Bybit

Bybit OHLCV `data/BTCUSDT_4h.parquet` начинается с 2023-01-01 (3.3y). Autoresearch использовал Binance `data/BTCUSDT_4h_binance.parquet` (2017-08-17, 8.7y). Production runner обнаруживает `(BTCUSDT, 240)` → загружает Binance напрямую, bypassing `_load_ohlcv`.

### Sub-period разбивка

Autoresearch `_build_periods(df, 5)` использует equal-chunk split (`chunk_days = total_days // 5 = 635`), а не календарные годы. Кастомные границы:
- chunk 1: 2017-08-17 → 2019-05-14
- chunk 2: 2019-05-14 → 2021-02-07
- chunk 3: 2021-02-07 → 2022-11-04
- chunk 4: 2022-11-04 → 2024-07-31
- chunk 5: 2024-07-31 → 2026-04-30

Период 4 с календарными датами (2022-01-01→2022-12-31) дал -23.03%; с правильными chunk датами +152.05%.

### Выбор ATR: сигнал vs стоп

Две независимые ATR series:
- `atr_period=9` — для entry/exit band (`atr_arr`)
- `atr_stop_period=21` — для trailing stop (`atr_stop`)

`atr_stop[i-1]` берётся на момент входа (bar T-1 perм entry_signal) и фиксируется в `_entry_atr`. Stop = `entry_price - entry_atr × 1.5`.

## Метрики спринта

- **Тестов до:** ~934
- **Тестов после:** ~952 (unit + integration framework; integration требует парket данных)
- **mypy errors:** 0 (--strict)
- **ruff:** pass
- **Reason codes:** 53 → **56**
- **Component pages:** 47 → **48**
- **ADRs:** 59 → **60**
- **Sprint pages:** 43 → **44**

## Связанные

- [[../decisions/0060-sprint-40-atr-breakout-pre-registration]] — ADR 0060
- [[../components/atr-breakout-strategy]] — компонент
- [[sprint-39-volume-breakout-tech-debt]] — предыдущий спринт (шаблон)
