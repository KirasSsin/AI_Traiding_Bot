---
title: MarketData — BybitWSConsumer
type: component
tags: [marketdata, bybit, websocket, v5, asyncio]
created: 2026-04-21
updated: 2026-04-21
sources: [src/marketdata/bybit/ws.py, tests/unit/test_bybit_ws.py]
status: stable
---

# MarketData — BybitWSConsumer

**TL;DR:** Мост между callback-based `pybit.WebSocket.kline_stream` и async iteration через `asyncio.Queue`.

## Definition / Purpose

`pybit.unified_trading.WebSocket` работает по callback-модели: регистрируешь `callback=fn`, он вызывается из отдельного pybit-thread. В нашем коде market-data pipeline — `async for msg in ws.stream()`. Мост: callback кладёт сообщение в `asyncio.Queue` через `loop.call_soon_threadsafe`, `stream()` читает из queue.

### Интерфейс

- `BybitWSConsumer(symbol="BTCUSDT", interval="60", testnet=True)`.
- `start()` — создаёт pybit WS + подписывается на `spot.kline.60.BTCUSDT`. Должен вызываться внутри active event loop.
- `async stream() -> AsyncIterator[dict]` — yields raw V5 kline payload dicts.

## Key properties

- **Thread-safe queue** через `call_soon_threadsafe` — pybit-thread пишет, event-loop читает.
- **Single symbol/interval** — один consumer = один stream. Мульти-symbol потребует расширения.
- **Reconnect** делегирован pybit (внутренняя логика SDK).

## Связанные

- [[../decisions/0016-bybit-spot-supersedes-binance]] — endpoint `spot.kline.60.BTCUSDT`.
- [[bar-builder]] — принимает сообщения из WS.

## Sources

- `src/marketdata/bybit/ws.py`.
- `tests/unit/test_bybit_ws.py` (2: stream, init params).
