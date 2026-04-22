---
title: Storage — SQLite + Parquet
type: architecture
tags: [storage, sqlite, parquet, v0.1]
created: 2026-04-19
updated: 2026-04-19
status: stable
sources: [Docs/MVP + ALL PROJECT/MVP.md §3, §14]
---

# Storage

**TL;DR:** OLTP (orders, trades, state, config, events) — **SQLite WAL**. OLAP (OHLCV) — **Parquet (snappy)**. Audit log — **JSONL append-only**. Три отдельных слоя с чёткими границами.

## OLTP — SQLite (WAL-mode)

**Где:** `data/oltp.db` (single-file, WAL journal).

**Таблицы:**

```sql
-- Orders aggregate
CREATE TABLE orders (
  client_order_id TEXT PRIMARY KEY,
  exch_order_id   TEXT UNIQUE,
  symbol          TEXT NOT NULL,
  side            TEXT CHECK(side IN ('BUY','SELL')),
  type            TEXT CHECK(type IN ('MARKET','LIMIT','STOP_MARKET','STOP_LIMIT','TAKE_PROFIT')),
  status          TEXT CHECK(status IN ('NEW','PARTIALLY_FILLED','FILLED','CANCELED','EXPIRED','REJECTED')),
  orig_qty        REAL NOT NULL,
  executed_qty    REAL NOT NULL DEFAULT 0,
  price           REAL,
  created_at      TEXT NOT NULL,
  updated_at      TEXT NOT NULL
);

-- Fills (partials + full)
CREATE TABLE fills (
  fill_id         INTEGER PRIMARY KEY AUTOINCREMENT,
  client_order_id TEXT NOT NULL REFERENCES orders(client_order_id),
  trade_id        INTEGER NOT NULL,    -- Binance trade id
  qty             REAL NOT NULL,
  price           REAL NOT NULL,
  fee             REAL NOT NULL,
  fee_asset       TEXT NOT NULL,
  is_maker        INTEGER NOT NULL,
  filled_at       TEXT NOT NULL,
  UNIQUE(trade_id)
);

-- Position aggregate
CREATE TABLE positions (
  position_id     TEXT PRIMARY KEY,
  symbol          TEXT NOT NULL,
  side            TEXT NOT NULL,
  qty             REAL NOT NULL,
  avg_entry_price REAL NOT NULL,
  opened_at       TEXT NOT NULL,
  closed_at       TEXT,
  realized_pnl    REAL
);

-- Event log (Event Sourcing)
CREATE TABLE events (
  aggregate_id    TEXT NOT NULL,
  version         INTEGER NOT NULL,
  event_type      TEXT NOT NULL,
  occurred_at     TEXT NOT NULL,
  payload_json    TEXT NOT NULL,
  PRIMARY KEY (aggregate_id, version)
);
CREATE INDEX idx_events_occurred ON events(occurred_at);

-- Runs (bot session)
CREATE TABLE runs (
  run_id          TEXT PRIMARY KEY,
  started_at      TEXT NOT NULL,
  ended_at        TEXT,
  git_commit      TEXT NOT NULL,
  config_hash     TEXT NOT NULL,
  strategy_version TEXT NOT NULL
);

-- Config snapshots
CREATE TABLE config (
  config_hash     TEXT PRIMARY KEY,
  config_json     TEXT NOT NULL,
  loaded_at       TEXT NOT NULL
);

-- Persistent state (circuit breaker, Kelly phase counters)
CREATE TABLE state (
  key             TEXT PRIMARY KEY,
  value_json      TEXT NOT NULL,
  updated_at      TEXT NOT NULL
);

-- Audit index (offset в JSONL по trade_id, timestamp)
CREATE TABLE audit_index (
  trade_id        TEXT PRIMARY KEY,
  timestamp       TEXT NOT NULL,
  symbol          TEXT NOT NULL,
  reason_code     TEXT NOT NULL,
  file_path       TEXT NOT NULL,
  file_offset     INTEGER NOT NULL
);
```

**WAL mode:** `PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;`. Конкурентные чтения не блокируют писателя.

## OLAP — Parquet

**Где:** `data/parquet/ohlcv_1h_btcusdt.parquet` (single file, append-only через ParquetDataset).

**Схема:**

```
close_time        TIMESTAMP (UTC ns)   <- row-group partition key
open_time         TIMESTAMP
open              FLOAT64
high              FLOAT64
low               FLOAT64
close             FLOAT64
volume            FLOAT64
trade_count       INT64
data_quality      STRING               <- OK | GAP | STALE | SUSPECT
```

**Compression:** snappy (быстрое compress/decompress, ~40% ratio на float+timestamp).

**Row-group:** по `close_time` с размером group ~1 month (730 rows на 1H) — эффективный pruning при range-scans.

**Размер:** 1 год 1H BTC/USDT = 8760 rows ≈ 90 KB (snappy) или 200 KB (raw).

## Audit log — JSONL append-only

**Где:** `data/audit/audit-YYYY-MM-DD.jsonl.gz` (daily-rotated gzip).

**Формат:** одна JSON-запись на строку по схеме из [[reason-codes-schema]]. Поле `record_hash = SHA-256(prev_record_hash || canonical_json(record))` — tamper-evident chain.

**Вторичный индекс:** SQLite `audit_index` (см. выше) содержит `(trade_id, timestamp, symbol, reason_code, file_path, file_offset)` — O(log n) lookups. **Индекс rebuildable** из JSONL, никогда не source of truth.

**Cold storage (опционально v0.3+):** daily gzip в S3/Glacier с ObjectLock WORM.

**Retention:** 7 years hot + cold (consistent с MiFID II RTS 24 / SEC 17a-4 / CFTC 1.31, хотя формальной обязанности для retail crypto нет). Размер аудит-записи ~1 KB × ~500 сделок/год = ~500 KB/год → хранение бесконечно бесплатно.

## Backup strategy

- **SQLite:** nightly `VACUUM INTO` + gzip + offsite copy (cron).
- **Parquet:** nightly incremental copy (append-only, только новые row-groups).
- **JSONL:** daily gzip, архивируется автоматически (rotation).

## Почему не QuestDB (в v0.1)

OHLCV 1H = 8760 rows/год = <100 KB. QuestDB (4–11M rows/s) избыточен на 27 порядков. См. [[0003-sqlite-parquet-for-storage]] и Kleppmann DDIA Ch.3.

## Sources

- Kleppmann (2017) *Designing Data-Intensive Applications* Ch.3.
- Parquet: Apache Arrow documentation.
- SQLite WAL: [sqlite.org/wal.html](https://sqlite.org/wal.html).

## Related

- [[stack-v0.1]] — общий стек.
- [[domain-events]] — как event log используется.
- [[reason-codes-schema]] — JSON Schema audit records.
- [[0003-sqlite-parquet-for-storage]] — ADR.
