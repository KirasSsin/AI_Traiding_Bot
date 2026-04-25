---
title: MarketData — BybitRESTClient
type: component
tags: [marketdata, bybit, rest, v5, anti-corruption-layer]
created: 2026-04-21
updated: 2026-04-21
sources: [src/marketdata/bybit/rest.py, tests/unit/test_bybit_rest.py]
status: stable
---

# MarketData — BybitRESTClient

**TL;DR:** Тонкий wrapper над `pybit.unified_trading.HTTP` для public Bybit V5 endpoints. Возвращает domain-friendly типы (`datetime` UTC, `list[Bar]`, `BybitFilters`).

## Definition / Purpose

`src/marketdata/bybit/rest.py` экспортирует `BybitRESTClient` — единственную точку входа в REST API Bybit V5 для маркет-даты. Всё остальное в `src/marketdata/` получает типизированные объекты, не зная про pybit / V5 / retCode.

### Методы

- `get_server_time() -> datetime` — `GET /v5/market/time` → UTC datetime (s precision). Для clock-drift check.
- `get_filters(symbol: str) -> BybitFilters` — `GET /v5/market/instruments-info?category=spot&symbol=X` → `BybitFilters` (defined в `src/marketdata/filters.py`, dedicated page TBD S3+).
- `get_klines(symbol, interval, start_ms, end_ms) -> list[Bar]` — `GET /v5/market/kline?category=spot` с пагинацией (max 1000 per call). Возвращает ascending по `close_time`, `data_quality=OK`.

### Обработка ошибок

- `retCode != 0` → `BybitAPIError(ret_code, ret_msg)`.
- В execution-слое (`BybitMarketAdapter`) ошибки маппятся через `map_error()` → `ReasonCode`.

## Key properties

- **Sync (не async).** pybit V5 REST — синхронный; все вызовы блокирующие.
- **Typed returns.** Вход — V5 JSON; выход — pydantic-модели (`Bar`, `BybitFilters`).
- **Pagination прозрачна** для `get_klines` — вызываем пока не выберем `[start, end)` полностью.
- **UTC everywhere** — timestamps конвертятся в UTC datetime на границе.

## Related

- [[../decisions/0016-bybit-spot-supersedes-binance]] — ADR выбора venue.
- [[bybit-ws]] — WS consumer (отдельный канал).
- [[models]] — Bar domain model.
- `BybitFilters` — defined в `src/marketdata/filters.py` (dedicated component page TBD S3+).

## Sources

- `src/marketdata/bybit/rest.py` (~120 LOC).
- Тесты: `tests/unit/test_bybit_rest.py` (6: init, server_time ok/err, filters, klines single/multi-page).
