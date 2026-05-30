---
title: Platform + MarketData — Storage (SQLite + Parquet)
type: component
tags: [platform, storage, sqlite, parquet]
created: 2026-04-20
updated: 2026-05-30
sources: [src/platform/db.py, src/marketdata/storage.py, migrations/001_initial.sql, tests/unit/test_db.py, tests/unit/test_parquet_storage.py]
status: stable
---

# Storage (SQLite + Parquet)

**TL;DR:** SQLite WAL — OLTP (orders, fills, positions, events, runs, config, state, audit_index). Parquet snappy — OLAP (исторические bars).

## Definition / Purpose

Два бэкенда персистенса, реализующие решение [[../decisions/0003-sqlite-parquet-for-storage]]:

### OLTP — `src/platform/db.py`

- `connect(db_path: Path) -> sqlite3.Connection` — PRAGMA `journal_mode=WAL`, `synchronous=NORMAL`, `foreign_keys=ON`.
- `init_db(db_path, migrations_dir) -> None` — применяет `.sql` файлы в лексикографическом порядке, идемпотентно через таблицу `schema_migrations` (filename PK).

Начальная миграция `migrations/001_initial.sql` создаёт 8 prod-таблиц + `schema_migrations`:

- `orders`, `fills` (FK на orders.client_order_id), `positions`
- `events` (event sourcing, PK=(aggregate_id, version))
- `runs`, `config`, `state`, `audit_index` (reason code index)

Все таблицы — с CHECK-ограничениями на enum-колонках (side, type, status).

### OLAP — `src/marketdata/storage.py`

`ParquetBarWriter(directory, symbol, interval)` — пишет OHLCV бары в Parquet snappy. Каждый `append(bars)` создаёт новый файл `{symbol}_{interval}_{first_close}-{last_close}.parquet`. Schema фиксированная: `open_time/close_time` (timestamp[ns, UTC]), OHLCV (float64), `trade_count` (int64), `data_quality` (string).

**SHA-256 sidecar manifest (S51, реализован):** каждый `append()` атомарно записывает сопровождающий файл `{name}.sha256` с hex-дайджестом содержимого parquet-файла. Функция `verify_parquet(path: Path) -> bool` проверяет целостность — возвращает `True` если файл совпадает с sidecar, `False` при отсутствии sidecar или несовпадении хэша. Оба файла (parquet + sidecar) записываются через `.tmp` + `os.replace` (атомарный rename) — сохраняет инвариант S50 B4.

**Hive-партиционирование:** не реализовано. YAGNI: бот single-user read-only OLAP, внешней верификации данных не требуется. Решение пересмотреть при появлении multi-writer или внешнего data-trust сценария.

Консолидация мелких файлов — **out of scope v0.1** (S2+).

## Key properties

- **WAL mode** включён для конкурентного чтения/записи (поддерживает параллельные backtest + live reader).
- **Foreign keys** enforced — оркестратор не может вставить fill без существующего order.
- **Idempotent migrations** — повторный `init_db` не ломается и не дублирует applied migrations.
- **Parquet snappy** — быстрый compression, хорошо читается pandas/pyarrow/DuckDB.

## Инварианты (CRITICAL — verified by tests + code review)

| # | Invariant | Enforcement | Test |
|---|-----------|-------------|------|
| 1 | Forward-only migrations — no `DROP COLUMN`, no destructive backfill | `migrations/*.sql` audit + `src/platform/db.py::init_db` + ADR 0003 | (review rule) |
| 2 | `schema_migrations` table guards idempotent apply | `src/platform/db.py::init_db` | `tests/unit/test_db.py::test_init_db_idempotent` |
| 3 | `journal_mode=WAL` + `synchronous=NORMAL` + `foreign_keys=ON` on every connection | `src/platform/db.py::connect` | `tests/unit/test_db.py::test_wal_mode_enabled` |
| 4 | Parquet schema fixed — `open_time/close_time` timestamp[ns, UTC], OHLCV float64 | `src/marketdata/storage.py::ParquetBarWriter.append` + ADR 0007 | `tests/unit/test_parquet_storage.py::test_writer_creates_file_and_persists_bars` |
| 5 | SHA-256 sidecar written atomically alongside every parquet file | `src/marketdata/storage.py::ParquetBarWriter.append` + `_sha256()` | `tests/unit/test_parquet_storage.py::test_append_creates_sha256_sidecar` |
| 6 | `verify_parquet(path)` returns False on corruption or missing sidecar, True on intact | `src/marketdata/storage.py::verify_parquet` | `tests/unit/test_parquet_storage.py::test_verify_parquet_detects_corruption`, `test_verify_parquet_missing_sidecar` |

## Связанные

- [[../architecture/storage]] — полные SQL-схемы и обоснование выбора.
- [[../decisions/0003-sqlite-parquet-for-storage]] — ADR.
- [[../decisions/0007-utc-timestamps-ns-precision]] — ns-precision UTC для временных полей.
- [[../sprints/sprint-03-strategy-port]] — sprint where storage was significantly expanded

## Sources

- `src/platform/db.py`, `migrations/001_initial.sql`
- `src/marketdata/storage.py`
- Тесты: `tests/unit/test_db.py` (3), `tests/unit/test_parquet_storage.py` (9).
