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

## Манифест (dashboard replay)

`data/kronos_cache/_manifest.json` — sidecar-файл, создаваемый `scripts/run_kronos_s52.py::_write_manifest` после cache-build.

**Схема:**

```json
{
  "schema_version": 1,
  "model_id": "NeoQuasar/Kronos-mini",
  "weights_hash": "<SHA-256 весов>",
  "params_hash":  "<SHA-256 inference params>",
  "device":       "mps",
  "combos": [{"symbol": "BTCUSDT", "timeframe": "1h", ...}, ...]
}
```

**Кто пишет:** `scripts/run_kronos_s52.py` (оффлайн, оператор). Merge-семантика: повторный запуск обновляет key-поля и дополняет `combos` по (symbol, timeframe) — предыдущие комбо не теряются.

**Кто читает:** `src/dashboard/backtest_runner.py::_read_kronos_manifest` при запуске Kronos-пресета в dashboard.

**Зачем:** при воспроизведении backtest dashboard должен строить `CacheKey` с теми же `model_id / weights_hash / params_hash / device`, что использовал cache-build. Без манифеста dashboard подставлял бы захардкоженные дефолты → 100% cache miss (баг B2 PHASE 6 R2). Манифест разрешает двусмысленность двух различных состояний: (а) *кэш не построен* (манифест отсутствует — честный "не построен") и (б) *построен, но bar-level miss* (манифест есть; промахи легитимны — данного бара просто нет в кэше).

**Инвариант:** порог (`threshold`) **не** является полем `CacheKey` — он применяется в `KronosStrategy.on_bar` при сравнении с прогнозом и не влияет на идентификацию cache-артефакта.

## Связанные

- [[./kronos-adapter]] — единственный записывающий источник (оффлайн cache-build)
- [[./kronos-strategy]] — потребитель (только get(), никогда predict())
- [[../decisions/0068-sprint-52-kronos-integration]] — ADR C3 (predict-cache паттерн) + C4 (determinism) + C6 (Decimal boundary) + Поправка PHASE 6 B2 (manifest fix)
- [[../sprints/sprint-52-kronos]] — спринт создания компонента (T3)
