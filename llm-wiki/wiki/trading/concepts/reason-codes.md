---
title: Reason Codes (56)
type: concept
tags: [audit, reason-codes, v0.1, sprint-5, sprint-6, sprint-7, sprint-8a, sprint-36, sprint-37, sprint-39, sprint-40]
created: 2026-04-19
updated: 2026-05-10
status: stable
sources: [Docs/MVP + ALL PROJECT/MVP.md §14, src/risk/reason_codes.py (Sprint 4)]
---

# Reason Codes

**TL;DR:** 56 стандартизированных enum-кодов для audit-log. Каждая сделка/отказ/halt получает один код. Используется в event `RiskRejected.reason`, `OrderCancelled.reason`, `CircuitBreakerTriggered.reason` и `trade_audit.reason_code`. Канонический enum — `src/risk/reason_codes.py::ReasonCode` (StrEnum, immutable).

## Enum

### Entry (8)
- `ENTRY_LONG_TREND_FOLLOWING` — EMA-crossover + ADX confirmed.
- `ENTRY_SHORT_TREND_FOLLOWING` — reserved, не используется в v0.1 (spot only).
- `ENTRY_LONG_PULLBACK` — reserved v0.2+.
- `ENTRY_SHORT_PULLBACK` — reserved v0.2+.
- `SCALE_IN_LONG` — reserved v0.2+ (pyramid).
- `SCALE_IN_SHORT` — reserved v0.2+.
- `ENTRY_LONG_VOLUME_BREAKOUT` — Volume breakout + volume surge confirmation (S39 VolumeBreakoutStrategy, ADR 0059 LOCKED).
- `ENTRY_LONG_ATR_BREAKOUT` — ATR breakout выше band (S40 ATRBreakoutStrategy, ADR 0060 LOCKED).

### Scale / exits (15)
- `SCALE_OUT_PARTIAL` — частичное закрытие.
- `EXIT_SL_HIT` — OCO stop-loss leg triggered.
- `EXIT_TP_HIT` — OCO take-profit leg triggered.
- `EXIT_TRAILING_STOP` — reserved v0.2+.
- `EXIT_SIGNAL_FLIP` — противоположный сигнал на close.
- `EXIT_TIME_STOP` — 48 bars timeout (опционально v0.1).
- `EXIT_MANUAL_OVERRIDE` — operator intervention.
- `EXIT_CIRCUIT_BREAKER` — принудительный close через CB L2/L3/flash.
- `EXIT_OCO_PARTIAL_TIMEOUT` — partial OCO fill висит > N сек, force-close оставшегося qty (ADR 0019).
- `EXIT_STOP_RESIDUAL_FLATTEN` — SL Stop filled partially (IOC silent rewrite per probe v3-D); residual closed via Market Sell в обработчике EXIT_SL_RESIDUAL.
- `EXIT_RECONCILE_DETECTED` — reconciler обнаружил завершённый exit на бирже без эха через WS (ADR 0021 sub-decision 3, verdict `EXITED`).
- `EXIT_FLAT_VOLUME_CHANNEL` — Volume breakout channel boundary пробит вниз (S39 VolumeBreakoutStrategy, ADR 0059 LOCKED).
- `EXIT_FLAT_ATR_STOP_VB` — ATR stop triggered для volume breakout позиции (S39 VolumeBreakoutStrategy, ADR 0059 LOCKED).
- `EXIT_FLAT_ATR_REVERSE` — обратный ATR breakdown (S40 ATRBreakoutStrategy, ADR 0060 LOCKED).
- `EXIT_FLAT_ATR_STOP_AB` — ATR stop triggered для atr_breakout позиции (S40 ATRBreakoutStrategy, ADR 0060 LOCKED).

### Rejects (9)
- `REJECT_RISK_EXCEEDED` — Kelly или max position fraction.
- `REJECT_INSUFFICIENT_BALANCE` — `-2010` от Binance.
- `REJECT_STALE_DATA` — последний bar > 1.5·Δ.
- `REJECT_RATE_LIMITED` — HTTP 429 или weight > 90%.
- `REJECT_CLOCK_DRIFT` — `-1021` или drift > 1s.
- `REJECT_MIN_NOTIONAL` — filter violation `NOTIONAL`.
- `REJECT_FILTER_PRICE` — filter violation `PRICE_FILTER` или `LOT_SIZE`.
- `REJECT_DUPLICATE_SIGNAL` — повторный signal на тот же bar.
- `REJECT_ORDER_ALREADY_TERMINAL` — Bybit retCode 110001 при cancel_order (ордер уже Filled/Cancelled) — классифицируется как non-fatal sibling-cancel-Triggered race (ADR 0020 sub-decision 6).

### Halts (24)
- `HALT_DRAWDOWN_L1` — 15% DD warning.
- `HALT_DRAWDOWN_L2` — 22% DD halt 24h.
- `HALT_DRAWDOWN_L3` — 30% DD full stop.
- `HALT_FLASH_CRASH` — `max(8%, 3·ATR)` one-bar.
- `HALT_DATA_QUALITY` — consecutive missing bars, negative volume, OHLC inconsistency.
- `HALT_EXCHANGE_OUTAGE` — HTTP 418, maintenance window, WS down >N min.
- `HALT_KILL_SWITCH` — operator или `TRADING_ENABLED=false` env var.
- `HALT_RECONCILE_DIVERGENCE` — local FSM state расходится с exchange после reconcile (ADR 0019).
- `HALT_BRACKET_INCOMPLETE` — entry filled, но TP или SL placement failed дважды после attempt bump → halt с открытой позицией. Runbook: `runbooks/halt-recovery`.
- `HALT_OCO_ARM_TIMEOUT` — состояние OCO_ARMING > 60 сек без подтверждения обеих legs (ADR 0020 sub-decision 11 TTL).
- `HALT_OCO_SIBLING_STUCK` — sibling-cancel-on-Triggered failed И retCode != 110001 → требуется ручная отмена sibling-ордера.
- `HALT_PARTIAL_FILL_BELOW_MIN` — entry partial fill ниже `minOrderQty`; невозможно выставить OCO. Flatten residual + halt.
- `HALT_FLATTEN_FAILED` — flatten cascade failed дважды (full + minus-step) → требуется ручной flatten оператора (ADR 0020 sub-decision 10).
- `HALT_PHANTOM_SL` — reconciler обнаружил активный SL-ордер на бирже без соответствующего локального `bracket_id` → расхождение phantom-order.
- `HALT_BOOTSTRAP_AMBIGUOUS` — bootstrap reconcile не смог однозначно классифицировать local↔exchange расхождение (ADR 0021 sub-decision 1). Требуется ручной аудит перед resume.
- `HALT_EXIT_RECONCILE_DIVERGENCE` — exit-фаза reconcile увидела mismatch между local EXIT_PENDING и exchange (ADR 0021 sub-decision 3). Отдельный код от bootstrap-divergence для разделения runbook-процедур.
- `HALT_RUNTIME_CRASH` — unhandled exception в `RuntimeManager.run()` (ADR 0022 sub-decision 6). Persisted ДО re-raise — restart требует MANUAL_RESET.
- `HALT_BAR_POLL_STALL` — N consecutive REST `kline` failures (default N=24 = 120s). Signal-pipeline halt class — НЕ position-safety. См. [[../../project/components/bar-poller]] mid-bar-fill degradation.
- `KILL_SWITCH_REQUESTED` — Sentinel-file `.kill_switch` detected (operator action via `python -m src kill`). Distinct from S7 `KILL_SWITCH` (terminal → KILLED).
- `HALT_S36_DD_INTRADAY` — intraday drawdown exceeded threshold (S36 HaltGate pre-registered criteria, ADR 0055).
- `HALT_S36_DD_MULTIDAY` — multi-day drawdown exceeded threshold (S36 HaltGate, ADR 0055).
- `HALT_S36_CONSECUTIVE_LOSSES` — consecutive losing trades exceeded threshold (S36 HaltGate, ADR 0055).
- `HALT_S36_NO_TRADE_TIMEOUT` — no trades within timeout period (S36 HaltGate, ADR 0055).
- `HALT_UNKNOWN_SYMBOL` — incoming signal for symbol NOT in whitelist; fail-closed (S37 ADR 0057 sub-decision 1).

**Итого:** 8 + 15 + 9 + 24 = **56**.

## Таблица изменений по спринтам

| Спринт | Дельта | Коды | Итого |
|--------|--------|------|-------|
| S4 | исходные | (базовый набор 42) | 42 |
| S5 | +2 | `HALT_RECONCILE_DIVERGENCE`, `EXIT_OCO_PARTIAL_TIMEOUT` | → 44 |
| S6 | +8 | 6 HALT + 1 EXIT + 1 REJECT (OCO-emulation) | → 52 |
| S7 | +3 | `HALT_BOOTSTRAP_AMBIGUOUS`, `HALT_EXIT_RECONCILE_DIVERGENCE`, `EXIT_RECONCILE_DETECTED` | → 42 (*сброс счёта после wiki fix S4) |
| S8a | +3 | `HALT_RUNTIME_CRASH`, `HALT_BAR_POLL_STALL`, `KILL_SWITCH_REQUESTED` | → 45 |
| S36 | +4 | `HALT_S36_DD_INTRADAY`, `HALT_S36_DD_MULTIDAY`, `HALT_S36_CONSECUTIVE_LOSSES`, `HALT_S36_NO_TRADE_TIMEOUT` | → 49 |
| S37 | +1 | `HALT_UNKNOWN_SYMBOL` | → 50 |
| S39 | +3 | `ENTRY_LONG_VOLUME_BREAKOUT`, `EXIT_FLAT_VOLUME_CHANNEL`, `EXIT_FLAT_ATR_STOP_VB` | → 53 |
| S40 | +3 | `ENTRY_LONG_ATR_BREAKOUT`, `EXIT_FLAT_ATR_REVERSE`, `EXIT_FLAT_ATR_STOP_AB` | → **56** |

**Note (Sprint 4):** до S4 wiki header заявлял 28 (счёт sections был неверен: exits=7→8, halts=6→7). Code в `src/risk/reason_codes.py` всегда был source of truth. Исправлено в Sprint 4 wiki sync (см. ADR 0018).

**Note (Sprint 5):** добавлены 2 новых кода (`HALT_RECONCILE_DIVERGENCE`, `EXIT_OCO_PARTIAL_TIMEOUT`). Total: 29 → 31. См. ADR [[../../project/decisions/0019-sprint-5-execution-decisions]] sub-decision 4.

**Note (Sprint 6):** добавлены 8 новых кодов OCO-emulation (6 HALT + 1 EXIT + 1 REJECT). Total: 31 → 39. См. ADR 0020 sub-decisions 6-11.

**Note (Sprint 7):** добавлены 3 новых кода resilience (`HALT_BOOTSTRAP_AMBIGUOUS`, `HALT_EXIT_RECONCILE_DIVERGENCE`, `EXIT_RECONCILE_DETECTED`). Total: 39 → 42. См. ADR 0021 sub-decisions 1, 3.

**Note (Sprint 8a):** добавлены 3 новых кода live runtime (`HALT_RUNTIME_CRASH`, `HALT_BAR_POLL_STALL`, `KILL_SWITCH_REQUESTED`). Total: 42 → 45. См. ADR 0022.

**Note (Sprint 36):** добавлены 4 новых кода HaltGate (`HALT_S36_DD_INTRADAY`, `HALT_S36_DD_MULTIDAY`, `HALT_S36_CONSECUTIVE_LOSSES`, `HALT_S36_NO_TRADE_TIMEOUT`). Total: 45 → 49. См. ADR 0055. Реализация: [[../../project/components/halt-gate]].

**Note (Sprint 37):** добавлен 1 код безопасности (`HALT_UNKNOWN_SYMBOL`) — fail-closed symbol whitelist. Total: 49 → 50. См. ADR 0057 sub-decision 1.

**Note (Sprint 39):** добавлены 3 кода VolumeBreakoutStrategy (`ENTRY_LONG_VOLUME_BREAKOUT`, `EXIT_FLAT_VOLUME_CHANNEL`, `EXIT_FLAT_ATR_STOP_VB`). Total: 50 → 53. См. ADR 0059. Реализация: [[../../project/components/volume-breakout-strategy]].

**Note (Sprint 40):** добавлены 3 кода ATRBreakoutStrategy (`ENTRY_LONG_ATR_BREAKOUT`, `EXIT_FLAT_ATR_REVERSE`, `EXIT_FLAT_ATR_STOP_AB`). Total: 53 → **56**. См. ADR 0060. Реализация: [[../../project/components/atr-breakout-strategy]].

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

## Реализация

- [[../../project/components/execution-state-machine]] — FSM transitions emit HALT_* / EXIT_* reason codes; `halt_reason` persisted per ADR 0021
- [[../../project/components/coordinator]] — `request_halt(reason)` dispatches HALT_* codes; `_set_halt` writes to audit log
- [[../../project/components/halt-gate]] — emits HALT_S36_DD_INTRADAY / HALT_S36_DD_MULTIDAY / HALT_S36_CONSECUTIVE_LOSSES / HALT_S36_NO_TRADE_TIMEOUT
