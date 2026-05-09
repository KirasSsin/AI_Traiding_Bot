---
title: 0003. SQLite + Parquet for storage
type: decision
tags: [adr, v0.1, storage, database, oltp, olap]
created: 2026-04-19
updated: 2026-04-19
status: accepted
sources: [Docs/MVP + ALL PROJECT/MVP.md]
---

# 0003. SQLite + Parquet for storage

**Status:** Accepted
**Date:** 2026-04-19

## Context
Нужна персистентность для двух разных профилей: (1) транзакционные записи —
ордера, трейды, конфиги, state machine (OLTP, строчно, ACID); (2) рыночные
данные OHLCV для backtest/analytics (OLAP, колоночно, сжатие). 1H таймфрейм →
8760 строк/год/символ → < 100KB в Parquet-snappy. Альтернативы (QuestDB,
TimescaleDB, ClickHouse) избыточны на многие порядки.

## Decision
We will use SQLite (WAL-mode) для OLTP-данных (orders, trades, positions, runs,
config snapshots, risk state) и Apache Parquet (snappy compression,
partitioning by symbol/year) для OHLCV-истории и backtest-артефактов. Доступ —
через sqlalchemy-core (SQLite) и pyarrow/pandas (Parquet).

## Consequences
- (+) Zero-ops: оба хранилища file-based, нет демона, бэкап = `cp`.
- (+) SQLite WAL даёт concurrent reads + single writer — достаточно для v0.1.
- (+) Parquet-snappy: быстрый columnar-скан для vectorbt/walk-forward.
- (+) Простая миграция в Postgres/Timescale при росте (same SQL).
- (−) Нет сетевого доступа из коробки — неважно для single-node MVP.
- (−) SQLite не масштабируется на multi-writer — не требуется для одного бота.
- (0) DuckDB можно добавить для ad-hoc OLAP-запросов поверх Parquet.

## Alternatives considered
- QuestDB: отвергнуто — избыточно на 27 порядков для 8760 rows/year; демон,
  сетевой протокол, дополнительная зависимость.
- TimescaleDB/Postgres: отвергнуто — операционная сложность без выгоды для v0.1.
- ClickHouse: отвергнуто — OLAP-only, heavy, не решает OLTP-задачу.
- CSV-only: отвергнуто — нет ACID для orders/trades, нет сжатия.

## References
- [Docs/MVP + ALL PROJECT/MVP.md](../../../Docs/MVP%20%2B%20ALL%20PROJECT/MVP.md) — §3 (Storage)
- Kleppmann M., "Designing Data-Intensive Applications" (2017), Ch. 3
- SQLite WAL mode documentation

## Связанные

- [[../sprints/sprint-01-foundation]] — спринт, где SQLite + Parquet были реализованы (config/storage компоненты)
- [[../sprints/sprint-02-bybit-venue-migration]] — миграция на Bybit; persistence не менялась
