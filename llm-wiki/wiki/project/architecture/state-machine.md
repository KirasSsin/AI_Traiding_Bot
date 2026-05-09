---
title: State Machine — 12 состояний
type: architecture
tags: [state-machine, statecharts, execution, v0.1]
created: 2026-04-19
updated: 2026-04-19
status: stable
sources: [Docs/MVP + ALL PROJECT/MVP.md §7]
---

# State Machine (12 состояний)

**TL;DR:** Harel statecharts с одним hierarchical state (`EXECUTE`) и orthogonal parallel regions для watchdogs. Паттерны Hohpe & Woolf: Idempotent Receiver на `clientOrderId`, Dead Letter Channel, Correlation Identifier.

## Состояния

| Состояние | Роль |
|-----------|------|
| `IDLE` | Ожидание нового бара; нет активных позиций / ордеров. |
| `ANALYZE` | Получен NewBar; пересчитываем индикаторы. |
| `SIGNAL` | Индикаторы готовы; стратегия эмитит сигнал (или NO_SIGNAL). |
| `RISK_CHK` | Risk context валидирует сигнал (Kelly + filters + drawdown). |
| `EXECUTE` | **Hierarchical**: `SUBMITTING → WORKING → PARTIAL_FILL \| FILLED \| CANCELLING`. |
| `MONITOR` | Позиция открыта; ждём OCO triggering или exit signal. |
| `HALT` | Остановлен circuit breaker, flash crash или manual kill. Требует operator resume. |
| `RECONNECT` | WS dropout; backoff + reconnect + state reconciliation. |
| `STALE_DATA` | Нет нового бара >2·Δ; decisioning остановлен. |
| `CLOCK_DRIFT` | Binance `-1021` или `drift>250ms`; resync через chrony. |
| `RATE_LIMITED` | HTTP 429 или weight bucket >90%; token bucket throttle. |
| `TERMINATED` (implicit) | Graceful shutdown. |

## Ключевые переходы

```
IDLE --NewBar--> ANALYZE --IndicatorsReady--> SIGNAL
SIGNAL --SignalEmitted--> RISK_CHK
SIGNAL --NoSignal--> IDLE
RISK_CHK --RiskApproved--> EXECUTE.SUBMITTING
RISK_CHK --RiskRejected--> IDLE (log reason)
EXECUTE.SUBMITTING --OrderAck--> EXECUTE.WORKING
EXECUTE.WORKING --FILLED--> MONITOR
EXECUTE.WORKING --PARTIAL--> EXECUTE.PARTIAL_FILL
EXECUTE.PARTIAL_FILL --FillTimeout(60s)--> EXECUTE.CANCELLING
EXECUTE.* --ErrCode(-1021)--> CLOCK_DRIFT
EXECUTE.* --HTTP429 | -1003--> RATE_LIMITED
EXECUTE.* --ErrCode(-2010,-1013,-2018)--> IDLE (reject, no retry)
MONITOR --OCOTriggered(TP|SL)--> IDLE
MONITOR --SignalFlip--> EXECUTE (exit)
ANY --WSDisconnect--> RECONNECT --StateReconciled--> previous_state
ANY --NoBarFor(2·Δ)--> STALE_DATA
STALE_DATA --BarResumed+3ValidBars--> IDLE
ANY --CircuitBreakerTriggered | FlashCrash--> HALT
HALT --OperatorResume+Checklist--> IDLE
```

## Orthogonal regions (watchdogs)

Работают параллельно с основным потоком — могут прервать из любого состояния:

- **WS watchdog** — no msg for 30s → `WebSocketReconnect` event, переход в `RECONNECT`.
- **Stale data watchdog** — `now − last_bar_close > 2·Δ` → `StaleDataDetected` → `STALE_DATA`.
- **Clock drift watchdog** — `|drift| > 250ms` (periodic check via `/api/v3/time`) → `CLOCK_DRIFT`.
- **Rate limit watchdog** — header `X-MBX-USED-WEIGHT > 90%` → `RATE_LIMITED`, throttle.
- **Circuit breaker** — drawdown crosses L1/L2/L3 или flash → `HALT`.

## Критические edge-cases

### 1. Reconnect с открытой позицией

После WS resume:
```
GET /api/v3/openOrders?symbol=BTCUSDT
GET /api/v3/account
GET /api/v3/myTrades?fromId=<last_known>
```

Если exchange-position ≠ local-position (qty mismatch) → **HALT, manual review**. Никогда не реконсилировать автоматически при расхождении qty.

### 2. STALE_DATA

- `2·Δ = 7200s` на 1H — threshold для STALE_DATA (tolerant к Binance maintenance).
- `4·Δ = 14400s` → HALT.
- После resume — требовать 3 consecutive валидных бара. Если потеряно >N баров — перезапуск warm-up индикаторов.

### 3. CLOCK_DRIFT

- Binance `-1021` срабатывает при `timestamp > serverTime + 1000ms`.
- Держать `|drift| < 250ms` через chrony с ≥3 stratum-1 peers.
- Offset обновлять через `GET /api/v3/time` каждые 60s.
- При `drift > 1s` — stop подписанных запросов, resync; после 3 неудач — HALT.

### 4. RATE_LIMITED

- Token bucket per rate-limit-bucket: `REQUEST_WEIGHT@1m`, `ORDERS@10s`, `ORDERS@1d`.
- Читать live limits из `/api/v3/exchangeInfo.rateLimits` при старте (не хардкодить 1200 — может быть 6000).
- HTTP 429 → honor `Retry-After` + jitter.
- HTTP 418 (IP-ban) → **HALT, ждать expiry бана (до 3 дней)**.

### 5. PARTIAL_FILL на OCO-leg

Per Binance docs, любой terminal state (включая `PARTIALLY_FILLED`) на одной leg автоматически отменяет sibling. Бот должен детектить `listStatus`-event и **немедленно выпустить новый защитный ордер** на residual qty.

## Invariants для state machine

1. Переход в `HALT` — только через `OperatorResume` event (manual).
2. `EXECUTE.SUBMITTING → WORKING` только при получении `OrderAck` с `exchOrderId`.
3. `MONITOR` держит ровно одну открытую позицию + её OCO bracket.
4. Любой переход логируется в event log с `(aggregate_id, version)`.
5. State persists в SQLite `state` table — восстанавливается после restart через replay + reconciliation.

## Sources

- Harel, D. (1987). "Statecharts: A visual formalism for complex systems."
- Hohpe & Woolf (2003). *Enterprise Integration Patterns*.
- Binance API docs: Rate Limits, Order Flow, OCO.

## Related

- [[bounded-contexts]] — где state machine живёт.
- [[domain-events]] — события-триггеры переходов.
- [[edge-cases]] — полный каталог 24 edge-cases.
- [[../components/execution-state-machine]] — реализация: TRANSITIONS table, ExecutionEvent enum, InvalidTransitionError
- [[../components/coordinator]] — единственный writer FSM-состояний (single-writer invariant)
- [[../components/halt-gate]] — gate для HALT-переходов (S36 δ activation гейтинг)
