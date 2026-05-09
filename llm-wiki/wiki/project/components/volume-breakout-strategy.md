---
title: VolumeBreakoutStrategy Component
type: component
tags: [component, signalgen, volume-breakout, long-only, sprint-39, locked-pre-registration, autoresearch, ru]
created: 2026-05-09
updated: 2026-05-09
status: active
sources:
  - src/signalgen/volume_breakout_strategy.py
  - src/backtest/volume_breakout_runner.py
  - src/signalgen/indicators.py
  - project/decisions/0059-sprint-39-volume-breakout-pre-registration.md
  - project/research-evidence/FINAL_STRATEGY.md
---

# VolumeBreakoutStrategy

**TL;DR:** Long-only volume breakout стратегия (S39 autoresearch production integration per ADR 0059 LOCKED). Победитель autoresearch iter 10 sweep#1644 из 4510 комбинаций. Backtest verdict = **PASS** — 8mo held-out Sharpe +9.96 / PnL +20.42% (n=17). Gate 2 paper-trade PENDING оператор активации.

## Назначение

Pre-registered 8th hypothesis (N_trials=8 cumulative: S13/S15/S17/S20/S22/S33/S35/S39) per ADR 0059 — volume breakout paradigm. Anti-snooping LOCKED params + symbol + timeframe BEFORE production integration. Первая стратегия проекта с положительным held-out OOS evidence.

## LOCKED параметры (`VOLUME_BREAKOUT_PARAMS`)

| Параметр | Значение | Обоснование |
|----------|----------|-------------|
| `breakout_period` | 20 | Lookback для Donchian-style breakout channel |
| `volume_mult` | 1.5 | Volume surge threshold (1.5× rolling average) |
| `atr_period` | 14 | Wilder ATR consistent с indicators.atr() |
| `atr_stop_mult` | 2.0 | 2× ATR stop loss |
| `signal_side_mode` | `"long_only"` | FSM SignalSide invariant |

Символ: BTCUSDT. Таймфрейм: 4H. **НЕ ИЗМЕНЯТЬ без нового ADR (anti-snooping).** Verbatim из sweep#1644 — округление запрещено.

## Публичный API

### VolumeBreakoutStrategy (src/signalgen/volume_breakout_strategy.py)

```python
class VolumeBreakoutStrategy:
    def __init__(
        self,
        *,
        symbol: str,
        breakout_period: int,
        volume_mult: float,
        atr_period: int,
        atr_stop_mult: float,
    ) -> None: ...

    def warmup(self, bar: Bar) -> None: ...
    """Feed historical bars без signal emission (warm-up period)."""

    def on_bar(self, bar: Bar) -> Signal | None: ...
    """Main entry point per bar. Returns Signal или None."""
```

### compute_volume_breakout_signals (src/signalgen/indicators.py)

```python
def compute_volume_breakout_signals(
    bars: list[Bar],
    breakout_period: int,
    volume_mult: float,
    atr_period: int,
    atr_stop_mult: float,
) -> list[Signal | None]: ...
```

Helper для backtest vectorized computation. Используется в `volume_breakout_runner.py`.

### VolumeBreakoutRunner (src/backtest/volume_breakout_runner.py)

Production runner портирующий research execution model. Entry: `run_volume_breakout_backtest(bars, params) -> BacktestResult`.

## Логика входа/выхода

**Вход (LONG):** `close(T) > max(high[T-breakout_period:T])` AND `volume(T) > volume_mult × mean(volume[T-breakout_period:T])` AND `current_side == FLAT`

**Выход (FLAT) из LONG:** EITHER:
- `close(T) < min(low[T-breakout_period:T])` — channel exit → `EXIT_FLAT_VOLUME_CHANNEL`
- `close(T) < entry_close - atr_stop_mult × ATR(T)` — ATR stop → `EXIT_FLAT_ATR_STOP_VB`

## ReasonCodes (S39 +3)

| Код | Описание | Направление |
|-----|----------|-------------|
| `ENTRY_LONG_VOLUME_BREAKOUT` | Вход в long (breakout + volume confirmation) | → LONG |
| `EXIT_FLAT_VOLUME_CHANNEL` | Выход — channel boundary пробит вниз | → FLAT |
| `EXIT_FLAT_ATR_STOP_VB` | Выход — ATR stop triggered | → FLAT |

## Backtest Evidence (ADR 0059)

### Первичная (held-out OOS, 8 месяцев)

| Gate | S39 actual | Threshold | Pass? |
|------|------------|-----------|-------|
| Held-out Sharpe | +9.96 | > 0 (directional) | PASS |
| Held-out PnL | +20.42% | > B&H -30.14% | PASS |
| n_trades | 17 | ≥ 10 (preliminary) | PASS |
| Win rate | 47.06% | — | — |
| B&H Alpha | +50.56pp | > 0 | PASS |

**95% CI Sharpe ±1.5-2.0** (широкий из-за малой выборки n=17). Gate 2 paper-trade необходим для подтверждения.

### Вторичная (3.3y full backtest) ⚠️

PnL +122.66% — **contaminated estimate** (4510 implicit comparisons, Bailey 2014 champion-bias). Используется только как profit invariant (±0.5% проверка при изменениях кода).

## Profit Invariant (HARD-GATE)

Phase 5 gate: `tests/integration/test_volume_breakout_baseline_floor.py`

```
8mo held-out PnL ≥ +20.42% (±0.5%)
3.3y full PnL ≥ +122.66% (±0.5%)
```

Проверяется при любом изменении кода стратегии или runner'а.

## Конфигурация (Settings)

Dashboard preset `volume_breakout_iter10` (src/dashboard/):
- `interval`: 4H (ENFORCED, 422 для других)
- `symbol`: BTCUSDT (ENFORCED, 422 для других)
- `strategy`: volume_breakout_iter10

Параметры стратегии = `VOLUME_BREAKOUT_PARAMS` константа (immutable, не из Settings).

## Инварианты

1. **Long-only** — `signal_side_mode = "long_only"`. SHORT сигналы не генерируются (Spot, FSM SignalSide).
2. **No look-ahead** — `on_bar(bar)` использует только данные bar T и ранее. Volume breakout channel = `max(high[T-period:T])` (исключает T).
3. **Single-producer** — Strategy instance привязан к одному символу/таймфрейму. Coordinator single-writer invariant (ADR 0022).
4. **Immutable params** — `VOLUME_BREAKOUT_PARAMS` = frozen constant. Изменение требует нового ADR + новой pre-registration.
5. **Warm-up required** — `warmup()` должен получить `breakout_period + atr_period` bars до первого `on_bar()`. Ранние bars → `None`.

## Тесты

- `tests/unit/test_volume_breakout_signals.py` — unit signal fidelity (A5)
- `tests/unit/test_volume_breakout_strategy.py` — VolumeBreakoutStrategy class tests (A3)
- `tests/integration/test_volume_breakout_baseline_floor.py` — Phase 5 HARD-GATE profit invariant (A5 + T5b)
- `tests/unit/test_reason_codes.py` — проверяет +3 новых кода (A1)

## Gate 2 — forward paper-trade (PENDING)

Оператор должен активировать на δ TESTNET после tag alpha.39:
1. Set preset `volume_breakout_iter10` в dashboard
2. Мониторинг через `generate_live_report()` при n≥10 signals
3. DSR gate при n≥20 trades (GATE_ELIGIBLE per ADR 0056)
4. IF FAIL Gate 2 → S40 honest close обязателен (fallback clause)

**Real capital allocation BLOCKED до успешного Gate 2.**

## Связанные

- [[../decisions/0059-sprint-39-volume-breakout-pre-registration]] — ADR 0059 LOCKED params + acceptance criteria + Gate 2
- [[../decisions/0052-sprint-34-acceptance-criteria-amendment]] — acceptance gates (T5 floor 50, n_eff threshold)
- [[../sprints/sprint-39-volume-breakout-tech-debt]] — sprint context
- [[../research-evidence/FINAL_STRATEGY]] — sweep#1644 OOS evidence
- [[../research-evidence/CLOSE]] — autoresearch falsification record
- [[donchian-strategy]] — сестринская стратегия (S35, FAIL conjoint, модель для page template)
- [[strategy]] — EmaCrossoverAdxRsiStrategy (сестринская, FSM SignalSide + on_bar контракт)
- [[indicators]] — ATR computation shared via `indicators.atr()` (Wilder, period=14)
- [[sizing]] — ATR-based position sizing via `compute_qty`
- [[halt-gate]] — HaltGate проверяет halt criteria для δ TESTNET (Gate 2 платформа)
- [[live-trade-reporter]] — `generate_live_report()` для live Sharpe monitoring (Gate 2)
- [[delta-activation-playbook]] — оператор playbook для Gate 2 активации
