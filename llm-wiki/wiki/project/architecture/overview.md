---
title: MVP v0.1 — обзор архитектуры
type: architecture
tags: [mvp, v0.1, overview, ddd]
created: 2026-04-19
updated: 2026-04-19
status: stable
sources: [Docs/MVP + ALL PROJECT/MVP.md]
---

# MVP v0.1 — обзор архитектуры

**TL;DR:** Python-only алготрейдинговый бот для BTC/USDT 1H на Bybit Spot. Стратегия EMA-crossover + ADX + RSI с фиксированным процентом размера позиции в первой фазе. DDD с 5 bounded contexts, 20 domain events, 12-состоятельный state machine, event sourcing.

## Scope

- **Рынок:** Bybit Spot, один символ — BTC/USDT.
- **Таймфрейм:** 1H (один бар в час → 8760 событий/год).
- **Стратегия:** EMA(12)×EMA(26) crossover + ADX(14) filter + RSI(14) filter.
- **Позиционирование:** только LONG + FLAT (spot, без шортов).
- **Размер позиции:** Kelly фазы (см. [[../../trading/concepts/kelly-phases]]).
- **Риск:** фиксированный SL/TP через ATR, circuit breakers L1/L2/L3/flash (см. [[../../trading/concepts/circuit-breakers]]).

## Стек (v0.1)

| Слой | Технология |
|------|------------|
| Язык | Python 3.12 |
| Async | asyncio + uvloop |
| Market data | `pybit>=5.11` (Bybit V5 SDK) |
| Data | pandas 2.x + NumPy |
| Indicators | TA-Lib (C-bindings) |
| Domain models | pydantic v2 |
| OLTP storage | SQLite (WAL-mode) — orders, fills, positions, runs, config, audit index |
| OLAP storage | Parquet (snappy, row-group по timestamp) — OHLCV |
| Logs | structlog (JSON) |
| Container | Docker-compose на 1 VPS (2 vCPU, 4 GB RAM) |
| Monitoring | Sentry free tier + healthchecks.io dead-man's switch |

См. [[stack-v0.1]] для деталей и [[0008-event-loop-uvloop]] / [[0002-python-only-for-mvp]] для решений.

## Bounded Contexts (5)

```
┌─────────────┐   NewBar   ┌─────────────┐  Signal   ┌──────────┐
│ Market Data │ ─────────> │ Signal Gen  │ ────────> │   Risk   │
└─────────────┘            └─────────────┘           └─────┬────┘
                                                            │ RiskApproved
                                                            v
┌──────────────┐   events   ┌───────────────┐  orders   ┌─────────────┐
│  Analytics   │ <───────── │  Execution    │ <──ACL──> │    Bybit    │
└──────────────┘            └───────────────┘           └─────────────┘
```

1. **Market Data** — ingestion, нормализация, gap detection, OHLCV/L2 storage.
2. **Signal Generation** — индикаторы, стратегия, эмиссия сигналов.
3. **Risk Management** — position sizing (Kelly), drawdown monitor, circuit breakers, pre-trade filter validation.
4. **Order Execution** — placement, OCO management, fill handling, reconciliation.
5. **Analytics** — P&L, performance metrics, audit trail, DSR/PBO.

Подробнее: [[bounded-contexts]].

## Канонический timing

`Signal on close of bar T → order placed at open of bar T+1` — единственный вариант, не содержащий look-ahead bias. См. [[execution-timing]].

## Storage

- **OLTP (SQLite WAL):** `orders`, `fills`, `positions`, `runs`, `config`, `audit_index`, `events` (event log).
- **OLAP (Parquet):** `ohlcv_1h_btcusdt.parquet` (snappy, row-group по timestamp).
- **Audit log:** JSONL append-only, daily-rotated gzip, `record_hash` chain (SHA-256).

Подробнее: [[storage]] и [[reason-codes-schema]].

## Event Sourcing

Append-only event log в SQLite с PK `(aggregate_id, version)`. Аггрегаты Order и Position восстанавливаются через replay. Snapshot каждые N=100 events. Outbox pattern: event пишется в локальный лог **до** ack-ответа Bybit.

См. [[domain-events]] для полного каталога 20 событий.

## State Machine

12 состояний: `IDLE`, `ANALYZE`, `SIGNAL`, `RISK_CHK`, `EXECUTE` (композит: `SUBMITTING → WORKING → PARTIAL_FILL | FILLED | CANCELLING`), `MONITOR`, `HALT`, `RECONNECT`, `STALE_DATA`, `CLOCK_DRIFT`, `RATE_LIMITED`. См. [[state-machine]].

## Roadmap

- **v0.1 (MVP):** Python-only, SQLite + Parquet, Bybit Spot, 1H BTC/USDT. **Сейчас.**
- **v0.2 (через 3–6 месяцев, после 200+ реальных сделок):** DuckDB поверх Parquet, опционально Rust через PyO3 для L2-orderbook, property-based тесты, look-ahead-детектор в CI.
- **v0.3 (через 6–12 месяцев, при подтверждённом edge и масштабировании):** QuestDB + Grafana + Prometheus exporter, GitOps-деплой.

## Риски v0.1

- **Статистический** — overfitting; 5 лет BTC 1H позволяют протестировать не более ~45 конфигураций по границе MinBTL Bailey–López de Prado 2014. См. [[../../trading/concepts/minimum-backtest-length]].
- **Рыночный** — режимный сдвиг; Hudson & Urquhart (2021) показывают затухание простых MA-правил на BTC после 2017, OOS-Sharpe отрицателен.
- **Операционный** — неверный API-ключ, rate-limit, IP-бан HTTP 418.

Полный risk register: [[risk-register]].

## Acceptance Criteria

- **System (S1–S6):** uptime ≥99.5%, WS reconnect p99 <5s, P&L reconciliation ≥99.99%, dashboard <2s, config hot-reload, zero API key leaks.
- **Strategy (T1–T6, OOS only):** Sharpe ≥1.0, Sortino ≥1.5, MaxDD <25%, win rate ≥45%@RR≥1.5, per-trade expectation t-stat >2.0, OOS/IS Sharpe ratio ≥0.7.

Подробнее: [[acceptance-criteria]].

## Related

- [[current-state]] — что есть сейчас в репозитории.
- [[gap-analysis]] — чего не хватает до MVP.
- [[migration-plan]] — план перехода (будет создан на Этапе 2).

## Sources

- `Docs/MVP + ALL PROJECT/MVP.md` — консолидированный ревью MVP (основной источник).
- `Docs/MVP + ALL PROJECT/Full Project.md` — ТЗ Алготрейдинг Бот v0.1 (1760 строк, детали).
- `Docs/MVP/Architecture-Analysis.md` — архитектурный анализ.
- `Docs/MVP/Deep-Research-Report.md` — глубокий исследовательский отчёт.
