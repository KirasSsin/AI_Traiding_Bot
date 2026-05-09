---
title: Bounded Contexts (DDD) v0.1
type: architecture
tags: [ddd, bounded-context, v0.1]
created: 2026-04-19
updated: 2026-04-19
status: stable
sources: [Docs/MVP + ALL PROJECT/MVP.md]
---

# Bounded Contexts

**TL;DR:** 5 bounded contexts с явно заданными отношениями (Customer/Supplier, Partner, Anti-Corruption Layer, Conformist). Коммуникация через published domain events.

## Контексты

### 1. Market Data Context

**Ответственность:** ingestion, нормализация, gap detection, persistence OHLCV и L2-снапшотов (v0.2+).

**Входы:** Bybit V5 WebSocket `spot.kline.60.BTCUSDT` (public); REST `GET /v5/market/kline?category=spot` (seed/backfill); `GET /v5/market/instruments-info?category=spot&symbol=BTCUSDT` (filters); `GET /v5/market/time` (clock drift). См. [[../decisions/0016-bybit-spot-supersedes-binance]].

**Выходы:** published event `NewBar` (OHLCV + tradeCount + data_quality).

**Инварианты:**
- Только closed bars передаются в SignalGen (look-ahead protection).
- `low ≤ min(o,c) ≤ max(o,c) ≤ high` (OHLC consistency).
- Timestamps UTC ns precision.

**Persistence:** Parquet (`ohlcv_1h_btcusdt.parquet`, snappy, row-group по `closeTime`).

### 2. Signal Generation Context

**Ответственность:** вычисление индикаторов, стратегийная логика, эмиссия сигналов.

**Входы:** `NewBar` событие; исторические бары из Parquet.

**Выходы:** `SignalGenerated` (side, confidence, features dict, bar_ref).

**Инварианты:**
- Indicator = pure function over bars → scalar/vector (deterministic).
- `Signal.bar_ref.closeTime < now` (не использовать незакрытый бар).
- Один сигнал на бар (`REJECT_DUPLICATE_SIGNAL` при повторе).

**Индикаторы:** EMA(12, classical), EMA(26, classical), ADX(14, Wilder), RSI(14, Wilder), ATR(14, Wilder). См. [[../../trading/indicators/ema]].

### 3. Risk Management Context

**Ответственность:** position sizing (Kelly 4 фазы), drawdown monitoring, circuit breakers, pre-trade validation Binance filters (`LOT_SIZE`, `PRICE_FILTER`, `NOTIONAL`).

**Входы:** `SignalGenerated`, `OrderFilled`, `PositionOpened/Closed` (для equity tracking); account balance periodic refresh.

**Выходы:** `RiskApproved` (qty, SL price, TP price) **или** `RiskRejected` (reason enum); `DrawdownWarning`, `CircuitBreakerTriggered`.

**Инварианты:**
- `qty · price ≥ minNotional`, `qty % stepSize == 0`, `price % tickSize == 0` до отправки.
- Kelly phase determined by `trade_count` counter; cannot skip phases.
- Circuit breaker state persists в SQLite `state` table — восстанавливается при restart.

### 4. Order Execution Context

**Ответственность:** order placement, OCO management, partial fill handling, reconciliation с Binance state.

**Входы:** `RiskApproved`, Bybit V5 WS private `execution` stream, REST `GET /v5/order/realtime` (open orders), `GET /v5/account/wallet-balance?accountType=UNIFIED` (pre-trade balance).

**Выходы:** `OrderPlaced`, `OrderFilled`, `PartialFill`, `OrderCancelled`, `PositionOpened`, `PositionClosed`, `OCOTriggered`, `FilterViolation`.

**Инварианты:**
- `clientOrderId` unique + immutable, pattern `"{strategy}-{bar_close_epoch}-{uuid4_short}"`.
- `executedQty` монотонен (никогда не уменьшается).
- Post-reconnect reconciliation: если local ≠ exchange → HALT, manual review.

**Bybit = Anti-Corruption Layer:** весь REST/WS-протокол transluted в domain events; никакие Bybit-специфичные типы (pybit response dicts) не утекают наружу контекста.

### 5. Analytics Context

**Ответственность:** P&L reporting, performance metrics (Sharpe, Sortino, MaxDD, win rate), audit trail, DSR/PBO computations.

**Входы:** все domain events (Conformist — consumes без обратной связи).

**Выходы:** reports (CSV/Parquet), Grafana/Streamlit dashboard data, audit log (JSONL).

**Инварианты:**
- Никогда не влияет на торговые решения (read-only потребитель).
- Tamper-evident chain: `record_hash = SHA-256(prev_record_hash || canonical_json(record))`.

## Отношения

| От | К | Тип отношения | Published Language |
|----|---|--------------|--------------------|
| Market Data | Signal Gen | Customer / Supplier | `NewBar` |
| Signal Gen | Risk | Customer / Supplier | `SignalGenerated` |
| Risk | Execution | Partner (двусторонний event flow) | `RiskApproved`, `CircuitBreakerTriggered` |
| Execution | Bybit | Anti-Corruption Layer | internal (REST/WS) — не утекает |
| All → Analytics | — | Conformist (всё читает, ничего не публикует обратно) | все events |

## Почему DDD

1. **Изоляция изменений.** Изменение стратегии не трогает Execution; замена биржи не трогает SignalGen.
2. **Явные интерфейсы.** 20 domain events — публичный контракт между контекстами. См. [[domain-events]].
3. **Независимое тестирование.** Каждый контекст тестируется изолированно: Signal gets fake bars → produces signal; Execution gets fake RiskApproved → produces OrderPlaced.
4. **ACL для биржи.** Binance API меняется — адаптер меняется, domain events остаются стабильными.

## Aggregates

- **Order** (Execution) — `clientOrderId` как identity; lifecycle `NEW → PARTIALLY_FILLED → FILLED | CANCELED | EXPIRED | REJECTED`.
- **Position** (Execution) — `positionId` как identity; `qty ≥ 0` (spot only); максимум один entry Order + один OCO bracket active.
- **Run** (Analytics) — сессия бота от start до shutdown; содержит ссылки на config hash, git commit, strategy version.

## Sources

- Evans (2003) *Domain-Driven Design* Ch.14 "Maintaining Model Integrity".
- Vernon (2013) *Implementing DDD* Ch.3, Ch.13.
- Brandolini *Introducing EventStorming*.
- Hohpe & Woolf *Enterprise Integration Patterns* (Idempotent Receiver, Dead Letter Channel, Correlation Identifier).

## Related

- [[overview]] — общий обзор MVP.
- [[domain-events]] — полный каталог 20 событий.
- [[state-machine]] — 12-состоятельный state machine.
- [[../components/coordinator]] — единственный writer FSM (single-writer invariant).
- [[../components/runtime-manager]] — оркестратор tick-loop всех контекстов.
- [[../components/bar-builder]] — Market Data Context: построение баров.
- [[../components/risk-manager]] — Risk Management Context: Kelly + circuit breakers.
