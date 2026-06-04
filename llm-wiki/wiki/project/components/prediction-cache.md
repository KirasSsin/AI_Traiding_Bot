---
title: ml.prediction_cache — PredictionCache / CacheKey
type: component
tags: [component, ml, prediction-cache, kronos, determinism, sha256, manifest-v2, coverage, s52, s54]
created: 2026-05-30
updated: 2026-06-01
sources:
  - src/ml/prediction_cache.py
  - tests/unit/test_prediction_cache.py
  - wiki/project/decisions/0068-sprint-52-kronos-integration.md
  - wiki/project/decisions/0070-sprint-54-kronos-ui-coverage.md
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

`data/kronos_cache/_manifest.json` — sidecar-файл, создаваемый build-скриптом после cache-build.

### Manifest v2 (S54, актуальная схема)

**Схема v2** (per-combo self-describing):

```json
{
  "schema_version": 2,
  "combos": [
    {
      "symbol": "BTCUSDT",
      "timeframe": "1h",
      "model_id": "NeoQuasar/Kronos-mini",
      "weights_hash": "<SHA-256 весов>",
      "params_hash":  "<SHA-256 inference params>",
      "device":       "mps",
      "first_bar_ts": 1700000000,
      "last_bar_ts":  1748000000,
      "n_entries":    8760
    }
  ]
}
```

Поля `model_id / weights_hash / params_hash / device` — per-combo (в v1 были глобальными). Поля `first_bar_ts / last_bar_ts / n_entries` — новые в S54, нужны для coverage API.

**Почему per-combo (ADR 0070):** v1 last-writer-wins ломал CacheKey при смешанных `sample_count` / `variant` по разным TF. V2 каждый combo self-describing → корректная реконструкция CacheKey для любого combo независимо.

**Backfill:** `rebuild_manifest_v2` (S54) сканирует `data/kronos_cache/` и строит v2 из существующих JSON-артефактов. Запуск: `scripts/run_kronos_s54.py --rebuild-manifest`.

**Back-compat:** `_read_kronos_manifest` поддерживает fallback на v1 (top-level поля → все комбо наследуют).

### Coverage API (S54)

`GET /api/kronos/coverage` → per-(symbol,timeframe) ISO-даты кэша:

```json
{ "BTCUSDT": { "1h": {"start": "2023-11-14", "end": "2024-10-23", "n_entries": 8760} } }
```

Отсутствие combo в ответе = честный «не построен». Используется frontend `ConfigureBacktest.tsx` для autofill START/END и управления доступностью кнопки EXECUTE.

**Кто читает:** `src/dashboard/backtest_runner.py::_read_kronos_manifest` при запуске Kronos-пресета; `GET /api/kronos/coverage` при выборе пресета в frontend.

**Инвариант:** порог (`threshold`) **не** является полем `CacheKey` — он применяется в `KronosStrategy.on_bar` при сравнении с прогнозом и не влияет на идентификацию cache-артефакта.

## Связанные

- [[./kronos-adapter]] — единственный записывающий источник (оффлайн cache-build)
- [[./kronos-strategy]] — потребитель (только get(), никогда predict())
- [[../decisions/0068-sprint-52-kronos-integration]] — ADR C3 (predict-cache паттерн) + C4 (determinism) + C6 (Decimal boundary) + Поправка PHASE 6 B2 (manifest fix)
- [[../decisions/0070-sprint-54-kronos-ui-coverage]] — ADR 0070 (manifest v2 per-combo + coverage API)
- [[../sprints/sprint-52-kronos]] — спринт создания компонента (T3)
- [[../sprints/sprint-54-kronos-ui]] — S54 manifest v2 + coverage autofill
