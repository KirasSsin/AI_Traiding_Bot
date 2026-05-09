---
title: Стек v0.1 — Python-only
type: architecture
tags: [stack, python, v0.1]
created: 2026-04-19
updated: 2026-04-19
status: stable
sources: [Docs/MVP + ALL PROJECT/MVP.md §3]
---

# Стек v0.1

**TL;DR:** Python 3.12 + asyncio/uvloop + pandas + TA-Lib + pydantic v2 + SQLite + Parquet. Rust/QuestDB/Grafana отложены до v0.2/v0.3 как реакция на измеренные проблемы, а не априорные требования.

## Версии

### v0.1 (MVP, 2–3 месяца работы одного разработчика)

| Категория | Выбор | Обоснование |
|-----------|-------|-------------|
| Язык | Python 3.12 | Structural pattern matching, precise type hints, performance |
| Event loop | asyncio + uvloop | 105K req/s 1 KiB на одном ядре (MagicStack bench) — 5 порядков запаса для 1 msg/s |
| REST + WS | `pybit>=5.11` (official Bybit V5 SDK) | Unified Trading API, sync+async, callback-based WS (см. [[../decisions/0016-bybit-spot-supersedes-binance]]) |
| Данные | pandas 2.x + NumPy | Стандарт |
| Indicators | TA-Lib (C-bindings) | Проверено временем, Wilder + Classical EMA correct (см. [[0011-wilder-ema-for-adx-rsi-classical-for-crossover]]) |
| Domain модели | pydantic v2 | Runtime validation, serialization, type safety |
| Logging | structlog | JSON-logs, ready for Loki/journalctl |
| OLTP | SQLite (WAL-mode) | orders, fills, positions, runs, config, audit_index, events |
| OLAP | Parquet (snappy, row-group по timestamp) | ohlcv_1h_btcusdt |
| Container | Docker-compose | 1 VPS: 2 vCPU, 4 GB RAM |
| Error tracking | Sentry free tier (5K events/мес) | — |
| Liveness | healthchecks.io dead-man's switch | — |

### v0.2 (через 3–6 месяцев, после 200+ реальных сделок)

- **DuckDB поверх Parquet** — ad-hoc исследовательских SQL-запросов (zero-install embedded engine).
- **Rust через PyO3/maturin** (опционально) — **только** если добавляется L2-orderbook стратегия: Rust обрабатывает `@depth@100ms` updates, Python получает агрегированный order-book-imbalance feature.
- **Property-based тесты** через `hypothesis`.
- **Look-ahead detector** в CI (custom script).

### v0.3 (через 6–12 месяцев, при подтверждённом edge + масштабировании)

- **QuestDB** — **только** при устойчивой >10K msg/s (multi-symbol tick archive, полный L2-snapshot store).
- **Grafana + Prometheus exporter** — equity curve, rolling Sharpe, drawdown, per-trade PnL, WS disconnect counter, order reject rate, `X-MBX-USED-WEIGHT` headroom.
- **GitOps деплой** через watchtower или ArgoCD.
- **Secret rotation** через Doppler или SOPS+age.

## Обоснование "почему не Rust"

Binance для одного символа `@kline_1h` пушит ~1 msg/s. Hot path выполняется 8760 раз/год. Измеренный CPU load на современном laptop < 1%. uvloop даёт 105K req/s 1 KiB → 5 порядков запаса.

Knuth (1974) *Computing Surveys* 6(4):261–301: "premature optimization is the root of all evil".

Rust оправдан **только** для sub-10μs tick-to-trade в market-making ([markrbest.github.io/hft-and-rust](https://markrbest.github.io/hft-and-rust)), что не наш случай.

## Обоснование "почему не QuestDB в v0.1"

OHLCV 1H за 1 год = 8760 rows ≈ <100 KB Parquet. QuestDB (4–11M rows/s) на **27 порядков** избыточен для этого workload.

Kleppmann (2017) *DDIA* Ch.3: разделение OLTP (B-tree SQLite) и OLAP (columnar Parquet) — правильная архитектурная граница для этого масштаба.

## Docker-compose скетч

```yaml
version: '3.8'
services:
  bot:
    image: ghcr.io/<user>/bot:${BOT_VERSION:-latest}
    restart: always
    env_file: .env  # chmod 600
    volumes:
      - ./data:/data          # SQLite + Parquet + audit JSONL
      - ./logs:/logs          # structlog output
    environment:
      - TRADING_ENABLED=true
      - BINANCE_ENV=mainnet   # mainnet | testnet
    healthcheck:
      test: ["CMD", "python", "-m", "bot.healthcheck"]
      interval: 60s
      timeout: 10s
      retries: 3
```

## Observability (v0.3 только)

- `prometheus_client` на `/metrics` endpoint
- Grafana dashboards: equity, DD, per-trade PnL, WS disconnects, order rejects, rate-limit headroom
- structlog JSON → journalctl или Loki
- healthchecks.io ping каждые 70 мин → SMS alert

## Sources

- Knuth (1974) "Structured Programming with go to Statements".
- MagicStack uvloop benchmarks.
- Kleppmann (2017) *Designing Data-Intensive Applications*.

## Related

- [[0002-python-only-for-mvp]] — ADR.
- [[0003-sqlite-parquet-for-storage]] — ADR.
- [[0008-event-loop-uvloop]] — ADR.
- [[storage]] — детали схемы БД.
- [[../components/config]] — конфигурация бота (pydantic-settings).
- [[../components/models]] — domain models (pydantic v2).
- [[../components/logging]] — structlog настройка.
