---
title: "Sprint 54 — Kronos UI cached-coverage autofill"
type: sprint
tags: [sprint-54, kronos, ui, manifest-v2, coverage-api, autofill, frontend, react, s54]
created: 2026-06-01
updated: 2026-06-01
status: completed
sources:
  - llm-wiki/wiki/project/plans/2026-06-01-sprint-54-kronos-ui.md
  - llm-wiki/wiki/project/decisions/0070-sprint-54-kronos-ui-coverage.md
---

# Sprint 54 — Kronos UI cached-coverage autofill

## Обзор

S53 починил real-inference path. Оператор запустил exploratory backtest — результаты отрицательные (1h -5.61%, 5m -10.24%), но UX требует улучшения: dashboard не знал, какие TF реально построены. S54 решает: manifest v1→v2 (per-combo self-describing), coverage API, frontend autofill + честная блокировка непостроенных TF.

**Baseline (post-S53):** pytest 1511–1512 / mypy 0/98 / reason_codes 67 / FSM 16/30/74.
**Post-S54:** pytest **1525** passed / mypy **0**/98 / reason_codes **67** (без изменений) / FSM **16/30/74** (без изменений) / frontend 45 passed + build/lint clean.

## Kronos exploratory результаты (контекст)

| TF | Trades | PnL | Вердикт |
|----|--------|-----|---------|
| 1h | 25 | -5.61% | Long-only Spot — убыток |
| 5m | 21 | -10.24% | Long-only Spot — убыток |

Примечания:
- Убыток даже при pretrain leakage-преимуществе → long-only Spot edge отсутствует.
- batch/fp16 = тупик на MPS (вычислительная оптимизация не помогает).
- `--sample-count` — единственный рычаг скорости (~линейно: 20=8h, 5=2h, 1=26min для 5m/год).
- Результаты **exploratory** (`RAW_PRETRAIN_LEAKAGE_SUSPECTED`). No-cherry-pick правило (ADR 0068 GATE 0) без изменений.

## Задачи (T1-T4)

| Задача | Описание | Статус |
|--------|----------|--------|
| **T1** | Manifest v2: per-combo self-describing (model_id/weights_hash/params_hash/device/first_bar_ts/last_bar_ts/n_entries). `rebuild_manifest_v2` backfill + `--rebuild-manifest` flag | done |
| **T2** | Dispatch: per-combo CacheKey реконструкция + `GET /api/kronos/coverage` endpoint | done |
| **T3** | Frontend ConfigureBacktest: Kronos+построенный-TF → autofill START/END + EXECUTE активна; Kronos+непостроенный-TF → EXECUTE disabled + RU «не построен» | done |
| **T4** | ADR 0070 + wiki sync (PHASE 7) | done |

## Ключевые изменения

### Manifest v2 (T1)

Schema v2 хранит все идентифицирующие параметры per-combo:

| Поле (per-combo) | Суть |
|---------|------|
| `model_id` | "NeoQuasar/Kronos-mini" — per-combo в v2 |
| `weights_hash` | SHA-256 весов — per-combo в v2 |
| `params_hash` | SHA-256 inference params — per-combo в v2 |
| `device` | "mps" / "cpu" — per-combo в v2 |
| `first_bar_ts` | Первый bar unix ts в кэше комбо (NEW S54) |
| `last_bar_ts` | Последний bar unix ts в кэше комбо (NEW S54) |
| `n_entries` | Количество bar-артефактов в кэше комбо (NEW S54) |

`rebuild_manifest_v2` сканирует `data/kronos_cache/` и строит v2 из существующих JSON-артефактов. Back-compat: `_read_kronos_manifest` поддерживает fallback на v1.

### Coverage API (T2)

```
GET /api/kronos/coverage
→ { "BTCUSDT": { "1h": {"start": "2023-11-14", "end": "2024-10-23", "n_entries": 8760}, ... }, ... }
```

Per-`(symbol, timeframe)` ISO-даты из манифеста v2. Отсутствие combo в ответе = честный «не построен».

### Frontend autofill + block (T3)

| Сценарий | Поведение |
|----------|-----------|
| Kronos + построенный TF (e.g. 1h) | START/END автозаполняются из coverage window; EXECUTE активна |
| Kronos + непостроенный TF (e.g. 15m) | EXECUTE disabled; RU-сообщение «не построен» |

## Gates (post-S54)

| Gate | Результат |
|------|-----------|
| pytest unit | **1525** passed (6 «fails» = torch-installed-venv artifacts; CI torch-free → green) |
| mypy --strict | **0** errors (98 файлов) |
| reason_codes | **67** (без изменений vs S53) |
| FSM states/events/transitions | **16/30/74** (без изменений) |
| frontend Vitest | **45** passed |
| frontend build + lint | clean |

## Ревьюеры (PHASE 6)

| Ревьюер | Вердикт | Замечания |
|---------|---------|-----------|
| dashboard-reviewer | APPROVE | — |
| python-reviewer | APPROVE | — |
| data-integrity | APPROVE | Follow-up: parquet-immutability assumption в `rebuild_manifest_v2` (static research-files = low risk); v1 top-level device fallback narrowing (harmless для v2) |

## Deferred / Follow-up

- **Parquet-immutability assumption** — задокументировать явно при следующем касании `rebuild_manifest_v2`.
- **V1 device fallback narrowing** — при следующем касании `_read_kronos_manifest`.
- **Forward paper-trade harness** → S55+ (единственная валидная Kronos-валидация).
- **Track B signal enrichment** (predicted_high/low SL/TP, multi-horizon) — DEFER до forward paper-trade.

## Также в этой ветке (контекст, уже на main)

S53 post-ship perf-флаги (merged к main до S54): `--fast` (single-call mean, ~4x over median), `--sample-count` (lever скорости/качества), `--symbols`/`--timeframes` (фильтр при cache-build). Уже на main, в S54-ветку включены как контекст.

## Related

- [[../decisions/0070-sprint-54-kronos-ui-coverage]] — ADR 0070 (accepted)
- [[../decisions/0069-sprint-53-kronos-enablement]] — ADR 0069 (parent, S53)
- [[../decisions/0068-sprint-52-kronos-integration]] — ADR 0068 (foundation, S52)
- [[../components/prediction-cache]] — обновлён S54 (manifest v2 schema + coverage)
- [[sprint-53-kronos-enablement]] — предыдущий спринт (baseline 1512/0/67)
- [[../plans/2026-06-01-sprint-54-kronos-ui]] — план T1-T4
