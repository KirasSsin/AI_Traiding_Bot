---
title: Domain Events — каталог 20 событий
type: architecture
tags: [ddd, event-sourcing, events, v0.1]
created: 2026-04-19
updated: 2026-04-19
status: stable
sources: [Docs/MVP + ALL PROJECT/MVP.md §8]
---

# Domain Events (20 событий)

**TL;DR:** Published language между 5 bounded contexts. Event Sourcing: append-only event log в SQLite с PK `(aggregate_id, version)`. Outbox pattern — запись в локальный лог **до** ack биржи.

## Каталог

| # | Event | Producer | Consumers | Ключевой payload |
|---|-------|----------|-----------|------------------|
| 1 | `NewBar` | MarketData | SignalGen, Analytics | symbol, interval, openTime, closeTime, OHLCV, tradeCount |
| 2 | `SignalGenerated` | SignalGen | Risk, Analytics | signalId, barCloseTime, side, confidence, features dict |
| 3 | `RiskApproved` | Risk | Execution, Analytics | signalId, orderIntentId, qty, stopPrice, tpPrice |
| 4 | `RiskRejected` | Risk | Analytics | signalId, reason (enum) |
| 5 | `OrderPlaced` | Execution | Analytics, Monitor | clientOrderId, exchOrderId, symbol, side, type, qty, price, ts |
| 6 | `OrderFilled` | Execution | Position, Analytics | clientOrderId, fills[{qty,price,fee}], avgPrice |
| 7 | `PartialFill` | Execution | Execution-self, Analytics | clientOrderId, executedQty, cumQuoteQty, remainingQty |
| 8 | `OrderCancelled` | Execution | Analytics | clientOrderId, reason, executedQty |
| 9 | `PositionOpened` | Execution | Risk, Analytics | positionId, symbol, side, qty, avgEntryPrice |
| 10 | `PositionClosed` | Execution | Analytics | positionId, exitQty, avgExitPrice, realizedPnl |
| 11 | `DrawdownWarning` | Risk | Ops | equity, peakEquity, ddPct |
| 12 | `CircuitBreakerTriggered` | Risk | Execution(HALT), Ops | reason, ddPct, level |
| 13 | `WebSocketReconnect` | Infra | All | streamName, lastEventId, downtimeMs |
| 14 | `StaleDataDetected` | MarketData | Signal(HALT), Ops | lastBarCloseTime, ageMs |
| 15 | `ClockDriftDetected` | Infra | Execution(HALT), Ops | localMs, serverMs, driftMs |
| 16 | `RateLimitHit` | Gateway | Execution, Ops | endpoint, usedWeight, limit, retryAfterMs |
| 17 | `ConfigReloaded` | Ops | All | configHash, diff |
| 18 | `HeartbeatMissed` | Infra | Ops, Risk | since, missedCount |
| 19 | `OCOTriggered` | Execution | Position, Analytics | listClientOrderId, triggeredLeg (TP\|SL), qty, price |
| 20 | `FilterViolation` | Gateway | Risk, Ops | filter (LOT_SIZE\|PRICE_FILTER\|NOTIONAL), requested, allowed |

## Sequence паттерны

### Happy path

```
NewBar → SignalGenerated → RiskApproved → OrderPlaced → OrderFilled
      → PositionOpened → [MONITOR] → OCOTriggered → PositionClosed
```

### Error path (rate-limit retry)

```
OrderPlaced → HTTP 429 → RateLimitHit
           → [exponential backoff 2ⁿ·base + jitter, cap 60s, max 5 retries]
           → OrderPlaced(retry) | → CircuitBreakerTriggered(HALT)
```

### Reconnect

```
WSDisconnect → WebSocketReconnect → (reconciliation)
            → если divergence → CircuitBreakerTriggered(HALT)
            → иначе → resume previous state
```

## Event Sourcing mechanics

**Table `events` в SQLite:**

```sql
CREATE TABLE events (
  aggregate_id TEXT NOT NULL,
  version      INTEGER NOT NULL,
  event_type   TEXT NOT NULL,
  occurred_at  TEXT NOT NULL,   -- ISO-8601 UTC ns
  payload_json TEXT NOT NULL,
  PRIMARY KEY (aggregate_id, version)
);
CREATE INDEX idx_events_occurred ON events(occurred_at);
```

**Aggregate replay:** Order и Position reconstructируются чтением events `WHERE aggregate_id = ? ORDER BY version`.

**Snapshots:** каждые N=100 events сохраняется snapshot state в `snapshots` table — bounded replay при восстановлении.

**Outbox pattern:** event пишется в локальный event log **до** отправки запроса на Binance. На `OrderPlaced` — сначала INSERT в events, затем REST call. Если REST упал и неизвестен финальный статус — query `GET /api/v3/order?origClientOrderId=X` и адаптируем state.

**Correlation:** `signalId → orderIntentId → clientOrderId → exchOrderId` — идентификаторы цепочки прослеживаются через Correlation Identifier pattern (Hohpe & Woolf).

## Invariants для events

1. **Append-only.** Никогда не обновляем/удаляем events; corrections через новый event `Corrected<X>`.
2. **Idempotency.** Повторная попытка записи с тем же `(aggregate_id, version)` — no-op.
3. **Ordering.** `version` монотонно возрастает для одного `aggregate_id`.
4. **Market data вне event log.** OHLCV лежат в Parquet, ссылаются через `bar_ref.closeTime`.

## Reason codes

28 кодов для `RiskRejected.reason`, `OrderCancelled.reason`, `CircuitBreakerTriggered.reason` — полный список в [[reason-codes-schema]] и [[../../trading/concepts/reason-codes]].

## Sources

- Vernon (2013) *IDDD* Ch.8 "Domain Events".
- Fowler "Event Sourcing".
- Hohpe & Woolf *EIP* — Idempotent Receiver, Dead Letter Channel, Correlation Identifier.

## Related

- [[bounded-contexts]] — кто кому что публикует.
- [[state-machine]] — как события триггерят переходы.
- [[reason-codes-schema]] — JSON Schema для audit-записей.
- [[../components/coordinator]] — главный emitter ExecutionEvent'ов (FSM transitions)
- [[../components/runtime-manager]] — lifecycle events (START/STOP/RESTART)
- [[../components/ws-private-consumer]] — источник execution events (fill reports с биржи)
