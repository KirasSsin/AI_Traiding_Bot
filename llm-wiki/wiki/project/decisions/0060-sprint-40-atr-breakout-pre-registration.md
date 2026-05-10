---
title: ADR 0060 — Sprint 40 atr_breakout pre-registration LOCKED
type: decision
tags: [adr, sprint-40, atr-breakout, autoresearch-integration, locked, anti-snooping, ru]
created: 2026-05-10
updated: 2026-05-10
status: superseded
sources:
  - src/signalgen/atr_breakout_strategy.py
  - src/backtest/atr_breakout_runner.py
  - scripts/autoresearch_endless.py
---

# ADR 0060. Sprint 40 — atr_breakout pre-registration LOCKED

**Статус:** superseded by [[0062-sprint-42-atr-breakout-hardening]]
**Superseded:** 2026-05-10 (заменён ADR 0062 — preset consolidation + envelope contract retrofit)
**Дата:** 2026-05-10
**Модель:** anti-snooping LOCK по образцу ADR 0054 / ADR 0059

## Контекст

Autoresearch iter 1 (branch `autoresearch/donchian-may8`) завершил sweep BTCUSDT 240 (4H). Стратегия `atr_breakout` показала **+819.81% (8.7y additive PnL, sequential) / Sharpe 1.11 / 69 trades / 5/5 sub-periods positive** — первый в истории проекта результат 5/5 суб-периодов с положительным PnL. Данные Binance OHLCV 4H, 2017-08-17 → 2026-04-30.

Данный ADR фиксирует архитектурные решения S40 и параметры LOCKED ПЕРЕД production integration (anti-snooping — любое post-observation изменение запрещено).

## Решение

### LOCKED параметры verbatim autoresearch iter1 best

```python
ATR_BREAKOUT_LOCKED_PARAMS: dict[str, object] = {
    "atr_period": 9,                     # Wilder ATR для сигнала breakout
    "atr_breakout_mult": Decimal("2.5"), # Multiplier для entry/exit band
    "atr_stop_period": 21,               # Wilder ATR для trailing stop
    "atr_stop_mult": Decimal("1.5"),     # Stop = entry_close - ATR_stop × this
    "signal_side_mode": "long_only",     # FSM invariant — SHORT не генерируется
}
```

Символ: BTCUSDT. Таймфрейм: 4H. **НЕ ИЗМЕНЯТЬ без нового ADR (anti-snooping правило).**

**Source of truth:** `src/signalgen/atr_breakout_strategy.py::ATR_BREAKOUT_LOCKED_PARAMS` (единственная каноническая локация). Production runner и dashboard preset подтягивают параметры отсюда.

### Логика стратегии

**Вход (LONG) — сигнал на bar(T-1), исполнение на open(T):**
```
close[i-1] > close[i-2] + atr_breakout_mult × ATR[i-2]
AND current_side == FLAT
```

**Выход (FLAT) из LONG — приоритет 1 (reverse ATR breakdown):**
```
close[i-1] < close[i-2] - atr_breakout_mult × ATR[i-2]
→ EXIT_FLAT_ATR_REVERSE
```

**Выход (FLAT) из LONG — приоритет 2 (ATR stop intrabar):**
```
bar.low <= entry_close - atr_stop_mult × ATR_stop[-1]
→ EXIT_FLAT_ATR_STOP_AB
```

Warmup gate: `max(atr_period, atr_stop_period) + 3 = 24` bars.

### ATR реализация

Wilder ATR — точный порт `scripts/autoresearch_endless.py::_atr()`:
- `prev_close[0] = close[0]` (TR[0] = H-L)
- Seed = SMA за первые `period` bars
- Smoothing: `ATR[i] = ATR[i-1] × (period-1)/period + TR[i]/period`

**НЕ** EMA ATR, **НЕ** классический ATR с `RMA`. Расхождение = ошибка репликации.

### Production runner

`src/backtest/atr_breakout_runner.py` точно портирует execution модель из research (`scripts/autoresearch_endless.py`):
- (BTCUSDT, 240) → `data/BTCUSDT_4h_binance.parquet` (Binance, с 2017-08-17; Bybit данные с 2023-01-01 недостаточны)
- Sequential additive PnL (NOT compounded, NOT Kelly-sized)
- Комиссии 0.1% + slippage 0.05% на обе стороны

### Dashboard preset

`atr_breakout_iter_endless` — ENFORCED 4H + BTCUSDT. Dispatch через early-return block в `run_backtest()`, bypasses replay_engine (те же структурные gaps что и volume_breakout: sl_atr_mult wiring, long_only suppresses reverse exit, WFA+Kelly sizing).

### Новые ReasonCodes (+3, итого 56)

| Код | Описание | Направление |
|-----|----------|-------------|
| `ENTRY_LONG_ATR_BREAKOUT` | Вход в long (ATR breakout выше band) | → LONG |
| `EXIT_FLAT_ATR_REVERSE` | Выход — противоположный ATR breakdown | → FLAT |
| `EXIT_FLAT_ATR_STOP_AB` | Выход — ATR stop intrabar (atr_breakout специфичный) | → FLAT |

## Evidence

### Backtest (8.7y, 2017-08-17 → 2026-04-30)

| Метрика | Значение | Порог Phase 5 |
|---------|----------|---------------|
| Additive PnL | **+819.81%** | ≥ +819.31% (±0.5%) |
| n_trades | **69** | = 69 (exact) |
| Sharpe (annualized) | **1.11** | ≥ 0.5 |
| Sub-periods positive | **5/5** | 5/5 |

**ВАЖНО:** 8.7y backtest — contaminated estimate (1 implicit comparison, autoresearch iter1). Служит profit invariant и HARD-GATE верификации репликации кода. НЕ является независимым OOS evidence для реального капитала.

### Sub-periods (equal-chunk split, chunk_days = 3178//5 = 635 дней)

| Период | Ожидаемый PnL | Статус |
|--------|--------------|--------|
| 2017-08-17 → 2019-05-14 | +160.9% | PASS |
| 2019-05-14 → 2021-02-07 | +305.96% | PASS |
| 2021-02-07 → 2022-11-04 | +43.1% | PASS |
| 2022-11-04 → 2024-07-31 | +152.05% | PASS |
| 2024-07-31 → 2026-04-30 | +29.41% | PASS |

**5/5 positive — первый результат в истории проекта** (предыдущий лучший: 3/5).

## Acceptance Criteria (HARD-GATE)

Phase 5 gate: `tests/integration/test_atr_breakout_baseline_floor.py`

- Полный период 8.7y: PnL ≥ +819.31% (±0.5%) AND n_trades = 69
- Все 5 sub-periods: PnL > 0 (5/5 positive)
- Каждый sub-period: PnL ≥ expected - 0.5%
- Production runner (`run_atr_breakout_backtest`): PnL ≥ +819.31%, n_trades близко к 69 (±2)
- Sharpe > 0 и ≥ 0.5
- Data coverage ≥ 15000 баров (8.7y Binance данные)

## N_trials Counter

ATR breakout = pre-registered hypothesis #9 проекта.

| Спринт | Гипотеза | N_trials |
|--------|---------|----------|
| S13 | EMA crossover 1H | 1 |
| S15 | Mean-reversion multi-symbol 1H | 2 |
| S17 | Mean-reversion BTC 1H relaxed | 3 |
| S20 | Mean-reversion BTC 15M | 4 |
| S22 | Mean-reversion BTC 4H | 5 |
| S33 | Mean-reversion multi-symbol 4H | 6 |
| S35 | Donchian breakout 4H | 7 |
| S39 | Volume breakout 4H | 8 |
| **S40** | **ATR breakout 4H** | **9** |

## Альтернативы

- **(a) Volume breakout аугментация ATR фильтром (ADR 0059 опция D)** — DEFERRED. Baseline volume_breakout LOCKED, ATR breakout = отдельная гипотеза.
- **(b) Compounding PnL** — REJECTED. Research использует sequential additive — verbatim replication = единственная допустимая форма.
- **(c) Использование Bybit 4H данных** — REJECTED. Bybit данные с 2023-01-01 (3.3y) — insufficient для полного 8.7y baseline.

## Последствия

### Код

- **+3 ReasonCode**: `ENTRY_LONG_ATR_BREAKOUT` / `EXIT_FLAT_ATR_REVERSE` / `EXIT_FLAT_ATR_STOP_AB`
- `ATRBreakoutStrategy` class в `src/signalgen/atr_breakout_strategy.py` (T2)
- `src/backtest/atr_breakout_runner.py` — production runner (T3)
- Dashboard preset `atr_breakout_iter_endless` в `src/dashboard/backtest_runner.py` (T4)

### Инфраструктура качества

- `tests/integration/test_atr_breakout_baseline_floor.py` — Phase 5 HARD-GATE (8 тестов)
- `tests/unit/test_atr_breakout_strategy.py` — unit tests стратегии (8 тестов)
- `tests/unit/test_reason_codes_s40.py` — reason codes unit tests (4 теста)

### Операционные ограничения

- Profit invariant 8.7y HARD-GATE блокирует merge при нарушении ±0.5%
- N_trials=9 учитывается в DSR computation (будущие backtests)
- Dashboard preset ENFORCED к BTCUSDT 4H

## Связанные документы

- [[../components/atr-breakout-strategy]] — компонент страница ATRBreakoutStrategy
- [[../sprints/sprint-40-atr-breakout-production]] — детали реализации S40
- [[0059-sprint-39-volume-breakout-pre-registration]] — предыдущая pre-registration LOCKED (модель)
- [[0054-sprint-35-donchian-pre-registration]] — первая pre-registration LOCKED (образец)

## Поправка S45 (2026-05-10): uniform 3.3y baseline

Per S45 operator decision — uniform 3.3y data для всех combos. `BTCUSDT_4h_binance.parquet` (8.7y, origin unknown — downloaded externally до S40, не git-tracked) removed from `PARQUET_BY_COMBO` registry. Archived в `data/_archive/` для audit (восстановим если operator решит вернуть).

**Recomputed BTC 4H baseline на 3.3y window (2023-01-01 → 2026-04-26):**

| Метрика | 8.7y (исходный) | 3.3y (S45 актуальный) | Дельта |
|---------|-----------------|------------------------|--------|
| Full-period PnL | +819.81% | **+174.29%** | -645.52pp |
| Sharpe | 1.11 | **1.94** | +0.83 |
| n_trades | 69 | **28** | -41 |
| Sub-period robustness | 5/5 positive | (TBD post-S45 WFA) | — |

LOCKED params (`atr_period=9, atr_breakout_mult=2.5, atr_stop_period=21, atr_stop_mult=1.5`) UNCHANGED. Только data window изменён.

**Anti-snooping note:** params LOCKED pre-S40 на 8.7y autoresearch sweep. 3.3y recomputation не fitting events — это honest disclosure что operator standard window даёт different magnitude. 8.7y baseline preserved в archive для historical reference.

**Implications для S45 WFA recalibration (T6+T7):**
- 28 trades full-period 3.3y → ~5-6 trades per 500-bar OOS fold (under default ADR 0014)
- ~10-12 trades per 250-bar fold (under S45 low-freq tier amendment)
- T5 floor (n≥50) likely STILL fails even с recalibration. Honest expected outcome.
