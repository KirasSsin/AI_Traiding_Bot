---
title: 0016. Bybit Spot supersedes Binance as initial venue
type: decision
tags: [adr, v0.1, venue, exchange, bybit, supersedes-0004]
created: 2026-04-21
updated: 2026-04-21
sources: [user-directive-2026-04-21]
status: accepted
---

# 0016. Bybit Spot supersedes Binance as initial venue

**Status:** Accepted
**Date:** 2026-04-21
**Supersedes:** [[0004-binance-spot-as-initial-venue]]

## Context

[[0004-binance-spot-as-initial-venue]] зафиксировал Binance Spot для v0.1. До
начала Sprint 2 (Venue Migration) пользователь сменил требование: использовать
Bybit Spot. Мотивация — наличие рабочих testnet-креденшлов и предшествующий
опыт работы с Bybit API у пользователя (legacy/phase1-bybit бот).

Domain-логика (bounded contexts, state-machine, pydantic-модели Bar/Signal/
Order/Fill, event sourcing, circuit breakers, Kelly sizing) — **не завязана
на конкретную биржу**. DDD-граница Anti-Corruption Layer изолирует биржевой
протокол от всех остальных контекстов.

## Options

- **A. Остаться на Binance Spot.** Придерживаться 0004. Риск: нет рабочего
  testnet-доступа, пользователь должен регистрироваться. Аргумент против
  пивота: 0004 аргументировал выбор через ликвидность/документацию.
- **B. Bybit Spot только (scope A обсуждения).** Меняется venue, domain не
  трогается. Pybit>=5.11 вместо python-binance. Весь scope v0.1 сохранён
  (Spot BTC/USDT 1H LONG+FLAT).
- **C. Bybit Spot + Linear perps.** Расширить scope v0.1. Отвергнуто: +4
  спринта на perp edge-cases (funding, liquidation, isolated/cross margin),
  откат упрощения "no SHORT", ADR 0002 нарушен.
- **D. `ccxt` multi-venue wrapper.** Отвергнуто: abstraction-leak (теряем
  venue-specific error codes и filters), +50 MB deps, YAGNI (single venue
  per ADR 0002).

## Decision

Выбираем **B**: переключаемся на **Bybit Spot** через SDK `pybit>=5.11`
(official SDK, V5 Unified Trading API). Testnet (`api-testnet.bybit.com`) —
для paper-trading и integration-smoke-тестов. Mainnet — только после
прохождения всех gates.

### Ключевые параметры дизайна

- **SDK:** `pybit>=5.11` — `HTTP` client (REST) + `WebSocket` (stream).
- **Category:** `spot` (V5 unified endpoint). Готовность к `linear` как v0.2
  extension — не хардкодить category в интерфейсе `BybitRESTClient`.
- **Symbol:** `BTCUSDT` (совпадает с Binance naming).
- **Interval:** `60` (1H, Bybit numeric convention).
- **Public WS stream:** `spot.kline.60.BTCUSDT` на `wss://stream-testnet.bybit.com/v5/public/spot`.
- **Bar closure:** поле `confirm: true` в kline payload = bar closed (аналог Binance `is_closed`).
- **Filters:** `GET /v5/market/instruments-info?category=spot&symbol=BTCUSDT` → `lotSizeFilter` (basePrecision, quotePrecision, minOrderQty, maxOrderQty, minOrderAmt), `priceFilter` (tickSize). Обёртка — single class `BybitFilters` (per brainstorming Q3).
- **Clock drift:** `GET /v5/market/time` → compare к local UTC; threshold 1s → `ClockDriftDetected`.
- **Rate limits:** Bybit UID-based (нет `X-MBX-USED-WEIGHT` как у Binance). Backoff через `Retry-After` header + retCode `10006` → `RateLimitHit`.
- **Auth:** HMAC-SHA256 подпись через pybit автоматически; keys через `Settings.bybit_api_key` / `Settings.bybit_api_secret` / `Settings.testnet: bool`.

### Error code map (Bybit retCode → наш ReasonCode)

| retCode | Bybit message | → ReasonCode |
|---|---|---|
| 10002 | request not valid (timestamp) | `CLOCK_DRIFT` |
| 10003 | api key invalid | `WRONG_API_KEY` |
| 10006 | too many requests | `RATE_LIMIT_HIT` |
| 10016 | service not available | `EXCHANGE_MAINTENANCE` |
| 110007 | insufficient balance | `INSUFFICIENT_BALANCE` |
| 110017 | position size exceeds limit | `FILTER_VIOLATION` |
| 170131 | order would trigger immediately | `FILTER_VIOLATION` |
| 170140 | order amount below min | `FILTER_VIOLATION` |
| 170213 | order price precision | `FILTER_VIOLATION` |

Точный список кодов уточняется в Sprint 2 implementation (`src/execution/bybit/errors.py`) по реальным ответам testnet.

### Scope (без изменений vs 0004)

- Spot **only** (никаких perps в v0.1).
- Symbol **only** `BTCUSDT`.
- Timeframe **only** `1h`.
- Side **only** `LONG | FLAT` (никаких SHORT в v0.1 — сохраняется per ADR 0002).

## Consequences

### Положительные (+)

- Рабочие testnet-креденшлы у пользователя → ноль-конфиг smoke test с первого дня Sprint 2.
- Bybit V5 Unified API — чистый консистентный endpoint. Все categories (spot / linear / inverse) через один путь.
- `pybit` SDK знаком (legacy/phase1-bybit futures бот использовал pybit) → short learning curve.
- ACL-граница (bounded-contexts §Execution) — Binance-specific error codes не утекали в domain → замена venue не ломает контексты.

### Отрицательные (−)

- Ликвидность Bybit Spot BTC/USDT меньше чем Binance (~$200M/day vs $500M+/day на 2026). Для MVP размеры ордеров $10-1000 — не критично. Sqrt-slippage-model ([[0010-sqrt-slippage-model]]) применима: наш Q << 0.1% ADV всегда.
- `python-binance` был в deps → снимается. `pybit>=5.11` добавляется.
- **Переделка wiki и кода** (см. "Affected artifacts" ниже). Стоимость: 1 ADR + 5-6 wiki-edits + 1 pyproject edit. Поглощается Sprint 2 task breakdown.

### Нейтральные (0)

- Абстракция `Exchange` port всё равно нужна (как было заявлено в 0004) — замена на третью venue (OKX и т.д.) будет стоить только новый adapter.
- Domain events (`OrderPlaced`, `OrderFilled`, etc.) — не меняются.
- `ClientOrderId` pattern (`{strategy}-{bar_close_epoch}-{uuid4_short}`) — Bybit поддерживает `orderLinkId` до 36 chars → совместимо.

## Affected artifacts (pivot work)

Перед стартом Sprint 2:

| Артефакт | Действие |
|----------|----------|
| `ADR 0004-binance-spot-as-initial-venue.md` | `status: superseded by 0016`, header note |
| `wiki/project/architecture/overview.md` | Text: "Binance Spot" → "Bybit Spot" (3 упоминания) |
| `wiki/project/architecture/stack-v0.1.md` | Deps table: `python-binance` → `pybit>=5.11`; testnet URLs |
| `wiki/project/architecture/bounded-contexts.md` | §Market Data / §Execution: Binance endpoints → Bybit V5 |
| `wiki/project/architecture/edge-cases.md` | Error codes §10/§11/§15/§16/§17 переписать в таблицу retCodes |
| `wiki/project/architecture/migration-plan.md` | §S2 artifacts: `binance_consumer.py` → `bybit/rest.py`+`bybit/ws.py`; `binance_adapter.py` → `bybit/adapter.py` |
| `pyproject.toml` | deps swap |
| `.env.example` | `BINANCE_*` → `BYBIT_*` keys |
| `src/platform/config.py` | Settings: rename fields + hardcode testnet defaults (user directive) |
| `wiki/index.md` | Обновить link на 0016, добавить under Decisions |

## Alternatives rejected (детальнее)

**Scope C (Spot + Linear perps):** пользователь перечислил permissions на
testnet (USDC contracts, Unified, Spot). Расширение scope нарушает ADR 0002
(Python-only MVP для v0.1) и раздувает Sprint 2 на perp-specific риски
(funding rate, liquidation price, cross/isolated margin). Отложено до v0.2.

**`ccxt` мультивенью:** отвергнуто как в 0004 — YAGNI + абстракция-утечка.

## References

- Bybit V5 API docs: https://bybit-exchange.github.io/docs/v5/intro
- `pybit` SDK: https://github.com/bybit-exchange/pybit
- [[0002-python-only-for-mvp]] — scope ограничение на MVP.
- [[0003-sqlite-parquet-for-storage]] — persistence не зависит от venue.
- [[0004-binance-spot-as-initial-venue]] — superseded.
- [[0010-sqrt-slippage-model]] — применимость к Bybit Spot ликвидности.
- [[../architecture/bounded-contexts]] — Execution ACL.
- [[../architecture/migration-plan]] §S2 — Venue migration sprint.
