---
title: "0070. Sprint 54 — Kronos UI cached-coverage autofill"
type: decision
tags: [decision, adr, s54, kronos, ui, manifest-v2, coverage-api, autofill, frontend, react]
created: 2026-06-01
updated: 2026-06-01
status: accepted
sources:
  - llm-wiki/wiki/project/plans/2026-06-01-sprint-54-kronos-ui.md
  - llm-wiki/wiki/project/decisions/0069-sprint-53-kronos-enablement.md
  - llm-wiki/wiki/project/decisions/0068-sprint-52-kronos-integration.md
---

# 0070. Sprint 54 — Kronos UI cached-coverage autofill

**Status:** accepted
**Date:** 2026-06-01

## Контекст

S52-S53 поставили Kronos-инфраструктуру и починили real-inference path. После cache-build оператор запустил exploratory backtest: 1h 25 trades -5.61%, 5m 21 trades -10.24% — убыток даже при наличии pretrain leakage-преимущества. Long-only Spot edge отсутствует. Производительность: batch/fp16 = тупик на MPS; `--sample-count` — единственный рычаг (~линейно).

Несмотря на отрицательный результат, оператор хочет корректный UX для дальнейшего исследования:

1. **Manifest v1 не мог выражать per-combo покрытие.** Schema v1 хранила `model_id / weights_hash / params_hash / device` на уровне манифеста целиком — при наличии нескольких комбо с разными `sample_count` или `variant` последний запуск перезаписывал параметры всего манифеста (last-writer-wins). CacheKey строился неверно → 100% cache miss для «старых» комбо.
2. **Нет способа узнать, какой TF построен.** Dashboard не знал, для каких `(symbol, timeframe)` есть реальный кэш → нельзя честно заблокировать непостроенный TF или автозаполнить даты.
3. **UX-проблема:** выбор Kronos+1h открывал форму с пустыми START/END и активной кнопкой EXECUTE, даже если кэш 1h реально построен. Выбор непостроенного 15m давал misleading ошибку вместо явной блокировки.

## Решение

### T1 — Manifest v2: per-combo self-describing

Новая схема манифеста v2 хранит все идентифицирующие параметры на уровне каждого combo-объекта, а не глобально:

```json
{
  "schema_version": 2,
  "combos": [
    {
      "symbol": "BTCUSDT",
      "timeframe": "1h",
      "model_id": "NeoQuasar/Kronos-mini",
      "weights_hash": "<sha256>",
      "params_hash": "<sha256>",
      "device": "mps",
      "first_bar_ts": 1700000000,
      "last_bar_ts":  1748000000,
      "n_entries": 8760
    }
  ]
}
```

Поля `first_bar_ts / last_bar_ts / n_entries` — добавлены S54 для coverage. `model_id / weights_hash / params_hash / device` теперь per-combo: поддерживаются смешанные `sample_count` / `variant` по разным TF.

Функция `rebuild_manifest_v2` (backfill) сканирует `data/kronos_cache/` и реконструирует v2 из существующих JSON-артефактов. Флаг `--rebuild-manifest` в build-скрипте.

**Обратная совместимость:** `_read_kronos_manifest` поддерживает fallback на v1 (top-level `model_id` → все комбо наследуют). Поле `device` в v1 не per-combo → для v2-промоции оператор должен выполнить `--rebuild-manifest`.

### T2 — Dispatch: per-combo CacheKey реконструкция + `/api/kronos/coverage`

`_kronos_dispatch.py` теперь строит `CacheKey` из per-combo полей манифеста v2 для каждого конкретного `(symbol, timeframe)`. Смешанные sample_count/variant поддерживаются корректно.

Новый эндпоинт:

```
GET /api/kronos/coverage
→ {
    "BTCUSDT": {
      "1h": {"start": "2023-11-14", "end": "2024-10-23", "n_entries": 8760},
      ...
    },
    ...
  }
```

Ответ: per-`(symbol, timeframe)` кэшированные ISO-даты. Если манифест отсутствует или v2 не содержит combo — поле отсутствует в ответе (честный «не построен»).

### T3 — Frontend ConfigureBacktest: autofill + block

React-компонент `ConfigureBacktest.tsx` при выборе пресета Kronos вызывает `/api/kronos/coverage` и:

- **Построенный TF (e.g. 1h):** автозаполняет поля START/END из кэшированного окна → кнопка EXECUTE активна → trades + equity отрендерятся из кэша.
- **Непостроенный TF (e.g. 15m):** кнопка EXECUTE заблокирована (`disabled`), под полями появляется RU-сообщение «не построен» — честная блокировка вместо misleading ошибки в рантайме.

### Backfill оператора

Для перехода v1 → v2 оператор выполняет:
```bash
RUN_ML=1 .venv/bin/python scripts/run_kronos_s54.py --rebuild-manifest
```

## Последствия

### Положительные

- Смешанные `sample_count` и `variant` по разным TF поддерживаются корректно (каждый combo self-describing).
- Autofill points at cached window → backtest trades + equity рендерятся без ручного ввода дат.
- Непостроенный TF заблокирован честно — оператор видит причину, не получает runtime-ошибку.
- Exploratory verdict `RAW_PRETRAIN_LEAKAGE_SUSPECTED` и no-cherry-pick правило без изменений (ADR 0068 GATE 0).

### Ограничения

- **Parquet-immutability assumption:** `rebuild_manifest_v2` предполагает, что JSON-артефакты в `data/kronos_cache/` — readonly после cache-build. Если файлы изменялись вручную, `first_bar_ts / last_bar_ts` могут быть неверны. Документировано как follow-up.
- **V1 top-level device fallback:** в v1 `device` не per-combo → fallback берёт `device` из top-level если есть, иначе `"cpu"`. Harmless для v2, но стоит задокументировать при следующем касании `_read_kronos_manifest`.
- Canonical counts без изменений: reason_codes **67**, FSM **16/30/74**.

## Related

- [[../plans/2026-06-01-sprint-54-kronos-ui]] — план T1-T4
- [[0069-sprint-53-kronos-enablement]] — S53 Kronos real-inference enablement (parent)
- [[0068-sprint-52-kronos-integration]] — S52 Kronos foundation (GATE 0 pretrain leakage)
