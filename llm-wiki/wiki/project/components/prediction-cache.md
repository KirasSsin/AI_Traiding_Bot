---
title: ml.prediction_cache — PredictionCache / CacheKey
type: component
tags: [component, ml, prediction-cache, kronos, determinism, sha256, s52]
created: 2026-05-30
updated: 2026-05-30
sources:
  - src/ml/prediction_cache.py
  - tests/unit/test_prediction_cache.py
  - wiki/project/decisions/0068-sprint-52-kronos-integration.md
status: stable
---

# Component: ml.prediction_cache

**TL;DR:** Детерминированный кэш прогнозов Kronos. `CacheKey` = 7-field составной ключ; `PredictionCache` = хранилище (write + get + checksum), полностью torch-free. Центральный компонент паттерна offline predict → cache → replay.

## Назначение

ADR 0068 C3: inference Kronos выполняется оффлайн (один раз, оператором на Mac M4 Pro MPS), результаты сохраняются в `data/kronos_cache/` (gitignored). Во время backtest и live replay `KronosStrategy.on_bar` выполняет только `cache.get(key)` — никакого ML inference в streaming path. Это: (а) устраняет latency проблему (Kronos predict = секунды на bar), (б) обеспечивает детерминированный replay, (в) изолирует torch от production code path.

## CacheKey

```python
@dataclass(frozen=True)
class CacheKey:
    model_id: str          # "NeoQuasar/Kronos-mini"
    weights_hash: str      # SHA-256 хэш скачанных весов (provenance)
    symbol: str            # "BTCUSDT"
    timeframe: str         # "1h"
    bar_close_ts: int      # unix timestamp closed bar
    params_hash: str       # SHA-256 хэш inference params (T/top_p/sample_count/seed)
    device: str            # "mps" | "cpu" | "mock"
```

7 полей гарантируют, что cache artifact привязан к конкретным весам, данным и параметрам. Смена любого поля = cache miss (обязателен перезапуск cache-build).

## Public API

```python
class PredictionCache:
    def __init__(self, cache_dir: Path) -> None: ...

    def write(self, key: CacheKey, predictions: list[float]) -> None:
        """Записывает прогнозы + SHA-256 sidecar .sha256 (атомарный temp+rename)."""
        ...

    def get(self, key: CacheKey) -> Decimal | None:
        """Возвращает median ensemble как Decimal или None при cache miss.
        Верифицирует SHA-256 checksum при чтении."""
        ...
```

`get()` возвращает `Decimal` (не float): конвертация на boundary `src/ml/` (ADR 0068 C6). None при cache miss не блокирует — KronosStrategy.on_bar вернёт None.

## Детерминизм

| Механизм | Деталь |
|----------|--------|
| median ensemble | `predictions` = list[float] из sample_count ≥ 20 семплов; median = canonical aggregate |
| SHA-256 sidecar | `.sha256` файл записывается atomically рядом с кэш-файлом; читается при каждом `get()` |
| torch seed | Устанавливается в `KronosModelAdapter.predict()` перед inference |
| CacheKey | 7 полей полностью идентифицируют источник; смена device = отдельный artifact |

## Хранилище

```
data/kronos_cache/          # gitignored
├── {model_id}/{symbol}/{timeframe}/
│   ├── {bar_ts}_{params_hash}.json
│   └── {bar_ts}_{params_hash}.json.sha256
```

Cache-build запускается `RUN_ML=1 scripts/run_kronos_s52.py` (11 combos, Mac M4 Pro). Обычно занимает часы (одноразово на оператора).

## Связанные

- [[./kronos-adapter]] — единственный записывающий источник (оффлайн cache-build)
- [[./kronos-strategy]] — потребитель (только get(), никогда predict())
- [[../decisions/0068-sprint-52-kronos-integration]] — ADR C3 (predict-cache паттерн) + C4 (determinism) + C6 (Decimal boundary)
- [[../sprints/sprint-52-kronos]] — спринт создания компонента (T3)
