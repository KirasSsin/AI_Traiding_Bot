---
title: Sprint 1 — Фундамент
type: sprint
tags: [sprint, sprint-1, foundation, scaffolding, storage, models]
created: 2026-04-22
updated: 2026-04-22
sources: [project/plans/2026-04-20-sprint-1-foundation.md]
status: completed
---

# Sprint 1 — Фундамент

**Dates:** 2026-04-20 → 2026-04-20
**Plan:** [[../plans/2026-04-20-sprint-1-foundation]]
**Tag:** `v0.1.0-alpha.1`
**Commit range:** `fd26417..a0f57f8` (10 коммитов)

## Цель

Заложить DDD-скелет и platform-слой (Settings, logging, storage) для v0.1 — всё, что нужно, чтобы следующие спринты добавляли domain-logic, а не bootstrap. Source: `migration-plan.md §S1`.

## Доставленная функциональность

### Код
- `pyproject.toml` — Python 3.12, ruff + mypy --strict + pytest; editable install.
- `src/platform/config.py` — `Settings` (pydantic-settings v2) с env/.env, Binance credentials (стали Bybit в S2), `trading_enabled` + `live_trading` инвариант.
- `src/platform/logging.py` — structlog JSON pipeline → stdout, обязательные ключи `event/level/timestamp`, `contextvars`.
- `src/platform/db.py` — SQLite WAL connection + migrations runner.
- `src/marketdata/models.py` — `Bar` (pydantic v2) + `DataQuality` enum с OHLC-инвариантами.
- `src/signalgen/models.py` — `Signal` + look-ahead invariant (`generated_at ≥ bar.close_time`).
- `src/execution/models.py` — `Order`, `Fill`, `OrderSide/Status/Type` с инвариантами (`executed_qty ≤ orig_qty`).
- `src/marketdata/storage.py` — `ParquetBarWriter` (snappy compression).
- `migrations/001_initial.sql` — 8 таблиц (instruments / bars / ... / audit_log).
- `Makefile` + `conftest.py` — `make check` orchestration.

### Вики
- Созданы: [[../components/config]], [[../components/logging]], [[../components/models]], [[../components/storage]].
- Обновлён: `index.md` (секция `Project — Components`).

### Удалено / перенесено
- **Удалено:** `src/ml/`, `src/gateway/`, `src/strategy/{hmm_regime,order_flow,strategy}.py`, `src/data/consumer.py`, `src/execution/executor.py`, `src/controller.py`, `main.py`, `test_execution.py`, `tests/test_math.py`, `protos/`, `pybit-master/`, `test_grpc_latency.py` — legacy Phase 1 Bybit-futures код, out of scope v0.1.
- **Сохранено:** ветка `legacy/phase1-bybit` содержит полный старый код как referenсе.

## Решения и отклонения

- **Environment setup:** системный Python 3.9.6 не соответствовал требованиям `pyproject.toml >=3.12`. Блокер. **Rationale:** установили Python 3.12.13 через Homebrew, создали worktree-local `.venv/`, editable install `pip install -e ".[dev]"`. План `.claude/plans/zazzy-gliding-crane.md` зафиксировал процесс.
- **Legacy cleanup перед scaffolding:** `migration-plan.md §S1` предполагал cleanup в финале, но реально удобнее было очистить в середине — после того как pydantic-модели появились и стало ясно, какие каталоги остаются. **Rationale:** subagent-driven-development Task 10.
- **ruff/mypy overrides** для residual legacy-кода (`src/backtest/`, `src/risk/risk_manager.py`) до их замены в S4-S7. **Rationale:** не хотели ломать `make check`, пока соответствующих спринтов нет.
- **ADR 0004** (Binance Spot) принят без изменений. Через 2 дня был superseded ADR 0016 — см. Sprint 2.

## Проверка

- `make check`: **green** — ruff clean, mypy --strict clean (22 files), pytest 20/20 passed.
- Tests: 20 unit tests across 6 модулей (config, logging, marketdata_models, signalgen_models, execution_models, db, parquet_storage).
- Manual: `python -c "from src.platform.config import Settings; ..."` — import chain OK.

## Влияние на следующие спринты

- **S2 (Bybit migration)** получил готовые: `Bar` модель, `ParquetBarWriter`, `Settings` (переименованы Binance→Bybit), SQLite schema, `make check` harness.
- **S3 (Strategy port)** получит: `Signal` модель с look-ahead invariant, `Bar` модель для `on_bar(Bar) -> Signal | None` contract.
- **S4 (Risk)** получит: `Order` модель с invariants, SQLite `positions/halts/audit_log` таблицы.
- **S6 (Event bus)** получит: structlog + contextvars как основа для корреляционных ID.

## Перенесённые задачи

- [ ] `src/backtest/` и `src/risk/risk_manager.py` — остаются под mypy/ruff override до S7 / S4.
- [ ] Python runtime установка задокументирована локально (plan file) — стоит перенести в `architecture/development-workflow.md` как "Prerequisites" секцию.
- [ ] Docker/compose sketch из `stack-v0.1.md` не активирован — явно v0.2 Deploy release.

## Related

- Plan: [[../plans/2026-04-20-sprint-1-foundation]]
- ADRs: [[../decisions/0001-record-architecture-decisions]], [[../decisions/0002-python-only-for-mvp]], [[../decisions/0003-sqlite-parquet-for-storage]], [[../decisions/0006-pydantic-v2-for-domain-models]], [[../decisions/0007-utc-timestamps-ns-precision]]
- Components: [[../components/config]], [[../components/logging]], [[../components/models]], [[../components/storage]]
- Architecture: [[../architecture/stack-v0.1]], [[../architecture/storage]], [[../architecture/migration-plan]]
