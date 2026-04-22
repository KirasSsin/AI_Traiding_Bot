---
title: Reason Codes (28)
type: concept
tags: [audit, reason-codes, v0.1]
created: 2026-04-19
updated: 2026-04-19
status: stable
sources: [Docs/MVP + ALL PROJECT/MVP.md §14]
---

# Reason Codes

**TL;DR:** 28 стандартизированных enum-кодов для audit-log. Каждая сделка/отказ/halt получает один код. Используется в event `RiskRejected.reason`, `OrderCancelled.reason`, `CircuitBreakerTriggered.reason` и `trade_audit.reason_code`.

## Enum

### Entry (6)
- `ENTRY_LONG_TREND_FOLLOWING` — EMA-crossover + ADX confirmed.
- `ENTRY_SHORT_TREND_FOLLOWING` — reserved, не используется в v0.1 (spot only).
- `ENTRY_LONG_PULLBACK` — reserved v0.2+.
- `ENTRY_SHORT_PULLBACK` — reserved v0.2+.
- `SCALE_IN_LONG` — reserved v0.2+ (pyramid).
- `SCALE_IN_SHORT` — reserved v0.2+.

### Scale / exits (7)
- `SCALE_OUT_PARTIAL` — частичное закрытие.
- `EXIT_SL_HIT` — OCO stop-loss leg triggered.
- `EXIT_TP_HIT` — OCO take-profit leg triggered.
- `EXIT_TRAILING_STOP` — reserved v0.2+.
- `EXIT_SIGNAL_FLIP` — противоположный сигнал на close.
- `EXIT_TIME_STOP` — 48 bars timeout (опционально v0.1).
- `EXIT_MANUAL_OVERRIDE` — operator intervention.
- `EXIT_CIRCUIT_BREAKER` — принудительный close через CB L2/L3/flash.

### Rejects (8)
- `REJECT_RISK_EXCEEDED` — Kelly или max position fraction.
- `REJECT_INSUFFICIENT_BALANCE` — `-2010` от Binance.
- `REJECT_STALE_DATA` — последний bar > 1.5·Δ.
- `REJECT_RATE_LIMITED` — HTTP 429 или weight > 90%.
- `REJECT_CLOCK_DRIFT` — `-1021` или drift > 1s.
- `REJECT_MIN_NOTIONAL` — filter violation `NOTIONAL`.
- `REJECT_FILTER_PRICE` — filter violation `PRICE_FILTER` или `LOT_SIZE`.
- `REJECT_DUPLICATE_SIGNAL` — повторный signal на тот же bar.

### Halts (6)
- `HALT_DRAWDOWN_L1` — 15% DD warning.
- `HALT_DRAWDOWN_L2` — 22% DD halt 24h.
- `HALT_DRAWDOWN_L3` — 30% DD full stop.
- `HALT_FLASH_CRASH` — `max(8%, 3·ATR)` one-bar.
- `HALT_DATA_QUALITY` — consecutive missing bars, negative volume, OHLC inconsistency.
- `HALT_EXCHANGE_OUTAGE` — HTTP 418, maintenance window, WS down >N min.
- `HALT_KILL_SWITCH` — operator или `TRADING_ENABLED=false` env var.

**Итого:** 6 + 7 + 8 + 7 = 28.

## Использование

**В domain events:**
```python
# RiskRejected
{"event": "RiskRejected", "signalId": "s-123", "reason": "REJECT_MIN_NOTIONAL"}

# CircuitBreakerTriggered
{"event": "CircuitBreakerTriggered", "level": "L2", "reason": "HALT_DRAWDOWN_L2", "ddPct": 0.223}

# OrderCancelled
{"event": "OrderCancelled", "clientOrderId": "c-456", "reason": "REJECT_STALE_DATA"}
```

**В audit-log:**
```json
{
  "trade_id": "...",
  "reason_code": "ENTRY_LONG_TREND_FOLLOWING",
  "signal_inputs": {"ema_fast": 1.2, "adx_14": 32, ...},
  ...
}
```

## Правила

1. **Один код на event.** Не комбинировать.
2. **Immutable.** Коды не переименовываются — новые добавляются в конец (versioning через `schema_version`).
3. **CI gate.** Pre-commit hook проверяет что любой new code committed — добавлен в этот enum.
4. **Queryability.** Reason code — indexed поле в `audit_index`, позволяет O(log n) выборки по типу сделки.

## Аналитика по reason codes

Готовые метрики (Grafana / reports):
- Distribution ENTRY_* vs EXIT_* vs REJECT_* vs HALT_*.
- Reject rate per-type (REJECT_STALE_DATA counts, REJECT_RATE_LIMITED counts).
- HALT events timeline.
- EXIT_SL_HIT rate vs EXIT_TP_HIT rate (win/loss ratio check).

## Sources

- Docs/MVP + ALL PROJECT/MVP.md §14.

## Related

- [[../../project/architecture/reason-codes-schema]] — JSON Schema для audit records.
- [[../../project/architecture/domain-events]] — где коды используются.
- [[circuit-breakers]] — HALT_* коды.
- [[../../project/architecture/edge-cases]] — REJECT_* коды.
