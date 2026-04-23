---
title: Reason Codes (31)
type: concept
tags: [audit, reason-codes, v0.1, sprint-5]
created: 2026-04-19
updated: 2026-04-23
status: stable
sources: [Docs/MVP + ALL PROJECT/MVP.md §14, src/risk/reason_codes.py (Sprint 4)]
---

# Reason Codes

**TL;DR:** 31 стандартизированных enum-кодов для audit-log. Каждая сделка/отказ/halt получает один код. Используется в event `RiskRejected.reason`, `OrderCancelled.reason`, `CircuitBreakerTriggered.reason` и `trade_audit.reason_code`. Канонический enum — `src/risk/reason_codes.py::ReasonCode` (StrEnum, immutable).

## Enum

### Entry (6)
- `ENTRY_LONG_TREND_FOLLOWING` — EMA-crossover + ADX confirmed.
- `ENTRY_SHORT_TREND_FOLLOWING` — reserved, не используется в v0.1 (spot only).
- `ENTRY_LONG_PULLBACK` — reserved v0.2+.
- `ENTRY_SHORT_PULLBACK` — reserved v0.2+.
- `SCALE_IN_LONG` — reserved v0.2+ (pyramid).
- `SCALE_IN_SHORT` — reserved v0.2+.

### Scale / exits (9)
- `SCALE_OUT_PARTIAL` — частичное закрытие.
- `EXIT_SL_HIT` — OCO stop-loss leg triggered.
- `EXIT_TP_HIT` — OCO take-profit leg triggered.
- `EXIT_TRAILING_STOP` — reserved v0.2+.
- `EXIT_SIGNAL_FLIP` — противоположный сигнал на close.
- `EXIT_TIME_STOP` — 48 bars timeout (опционально v0.1).
- `EXIT_MANUAL_OVERRIDE` — operator intervention.
- `EXIT_CIRCUIT_BREAKER` — принудительный close через CB L2/L3/flash.
- `EXIT_OCO_PARTIAL_TIMEOUT` — partial OCO fill висит > N сек, force-close оставшегося qty (ADR 0019).

### Rejects (8)
- `REJECT_RISK_EXCEEDED` — Kelly или max position fraction.
- `REJECT_INSUFFICIENT_BALANCE` — `-2010` от Binance.
- `REJECT_STALE_DATA` — последний bar > 1.5·Δ.
- `REJECT_RATE_LIMITED` — HTTP 429 или weight > 90%.
- `REJECT_CLOCK_DRIFT` — `-1021` или drift > 1s.
- `REJECT_MIN_NOTIONAL` — filter violation `NOTIONAL`.
- `REJECT_FILTER_PRICE` — filter violation `PRICE_FILTER` или `LOT_SIZE`.
- `REJECT_DUPLICATE_SIGNAL` — повторный signal на тот же bar.

### Halts (8)
- `HALT_DRAWDOWN_L1` — 15% DD warning.
- `HALT_DRAWDOWN_L2` — 22% DD halt 24h.
- `HALT_DRAWDOWN_L3` — 30% DD full stop.
- `HALT_FLASH_CRASH` — `max(8%, 3·ATR)` one-bar.
- `HALT_DATA_QUALITY` — consecutive missing bars, negative volume, OHLC inconsistency.
- `HALT_EXCHANGE_OUTAGE` — HTTP 418, maintenance window, WS down >N min.
- `HALT_KILL_SWITCH` — operator или `TRADING_ENABLED=false` env var.
- `HALT_RECONCILE_DIVERGENCE` — local FSM state расходится с exchange после reconcile (ADR 0019).

**Итого:** 6 + 9 + 8 + 8 = 31.

**Note (Sprint 4):** до S4 wiki header заявлял 28 (счёт sections был неверен: exits=7→8, halts=6→7). Code в `src/risk/reason_codes.py` всегда был source of truth. Исправлено в Sprint 4 wiki sync (см. ADR 0018).

**Note (Sprint 5):** добавлены 2 новых кода (`HALT_RECONCILE_DIVERGENCE`, `EXIT_OCO_PARTIAL_TIMEOUT`). Total: 29 → 31. См. ADR [[../../project/decisions/0019-sprint-5-execution-decisions]] sub-decision 4.

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
