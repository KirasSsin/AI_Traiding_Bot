---
title: signalgen.kronos_strategy — KronosStrategy
type: component
tags: [component, signalgen, strategy, ml-strategy, kronos, foundation-model, prediction-cache, s52]
created: 2026-05-30
updated: 2026-05-30
sources:
  - src/signalgen/kronos_strategy.py
  - tests/unit/test_kronos_strategy.py
  - wiki/project/decisions/0068-sprint-52-kronos-integration.md
  - wiki/project/components/prediction-cache.md
  - wiki/project/components/kronos-adapter.md
status: stable
---

# Component: signalgen.kronos_strategy

**TL;DR:** `KronosStrategy.on_bar(bar: Bar) -> Signal | None` — ML-стратегия на основе Kronos foundation model. Читает прогноз из predict-cache (lookup-only, без inference), генерирует сигнал ENTRY_LONG_KRONOS / EXIT_FLAT_KRONOS по правилу predicted_close > current × (1 + threshold).

## Назначение

Первая ML-стратегия проекта (S52). Интегрирует прогнозы Kronos decoder-only AR transformer (K-line forecast) через паттерн offline-predict → cache → replay: inference выполняется заранее оператором via `scripts/run_kronos_s52.py`, on_bar является cache-потребителем. Реализует look-ahead-safe контракт (сигнал на closed bar T, fill на open(T+1)).

## Контракт

```python
from src.signalgen.kronos_strategy import KronosStrategy
from src.ml.prediction_cache import PredictionCache, CacheKey

cache = PredictionCache(cache_dir=Path("data/kronos_cache"))
strategy = KronosStrategy(
    symbol="BTCUSDT",
    timeframe="1h",
    cache=cache,
    model_id="NeoQuasar/Kronos-mini",
    weights_hash="sha256:...",
    threshold=Decimal("0.0025"),  # ≥0.25% (2× round-trip, LOCKED V3)
    horizon=1,
    params_hash="sha256:...",
    device="mps",
)

for bar in market_data_stream:
    sig = strategy.on_bar(bar)
    if sig is not None:
        event_bus.emit(sig)
```

`on_bar` возвращает `Signal | None`. None когда:
- `is_closed=False` (live bar, игнор);
- cache miss (`PredictionCache.get()` вернул None) — стратегия не блокирует;
- wrong symbol или timeframe;
- условие входа/выхода не выполнено.

## Правило сигнала (V3 LOCKED)

На closed bar T с close price `current`:

1. `cache.get(key)` → `pred_close` (float прогноза на bar T+1)
2. **ENTRY_LONG_KRONOS**: если `current_side == FLAT` AND `pred_close > current × (1 + threshold)` (≥0.25%)
3. **EXIT_FLAT_KRONOS**: если `current_side == LONG` AND `pred_close < current` (predicted reversal)
4. cache miss → None (never block)

Long-only. SHORT вне scope v0.1.

## Инварианты (КРИТИЧНЫЕ)

| # | Invariant | Enforcement | Примечание |
|---|-----------|-------------|------------|
| 1 | Look-ahead-free: signal на close(T) only | `is_closed` gate before any logic | ADR 0068 C3 |
| 2 | Cache-lookup ONLY в on_bar; inference NEVER в streaming path | Protocol boundary KronosAdapter | ADR 0068 C2 |
| 3 | Cache miss → None, не блокирует | Explicit check PredictionCache.get() | ADR 0068 C2 |
| 4 | Decimal boundary: pred_close из cache = Decimal | Conversion at cache write boundary | ADR 0068 C6 |
| 5 | `threshold ≥ 0.0025` (2× round-trip cost) | Constructor LOCKED validation | ADR 0068 V3 |

## Reason codes

| Код | Значение | Условие |
|-----|----------|---------|
| `ENTRY_LONG_KRONOS` (65) | Вход LONG по Kronos-прогнозу | pred_close > current × (1 + threshold) |
| `EXIT_FLAT_KRONOS` (66) | Выход в FLAT по Kronos-прогнозу | pred_close < current при LONG |

Reason codes 65→67: +2 в S52.

## Verdict и backtest

Backtest через `src/backtest/kronos_runner.py` (run_kronos_exploratory). Заполнение по `open[i+1]` (стандартный контракт). Verdict = `RAW_PRETRAIN_LEAKAGE_SUSPECTED` — exploratory, НЕ gate. WFA невалиден (pretrain leakage, ADR 0068 GATE 0).

## Поддерживаемые combos (11)

```
BTCUSDT:  5m, 15m, 1h, 4h, 1d
ETHUSDT:  15m, 1h, 4h
SOLUSDT:  15m, 1h, 4h
```

## Связанные

- [[./prediction-cache]] — cache-провайдер (lookup + SHA-256 checksum)
- [[./kronos-adapter]] — ML inference boundary (оффлайн, не в on_bar)
- [[../decisions/0068-sprint-52-kronos-integration]] — ADR + architecture C1-C7 + trader V1-V5
- [[./models]] — Bar (input), Signal (output)
- [[./strategy]] — sister strategy (EmaCrossoverAdxRsiStrategy — тот же FSM SignalSide invariant)
- [[./backtest-harness]] — replayer (on_bar контракт)
- [[../sprints/sprint-52-kronos]] — спринт создания компонента
