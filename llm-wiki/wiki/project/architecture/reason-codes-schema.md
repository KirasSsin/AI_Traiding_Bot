---
title: Reason Codes JSON Schema — audit log
type: architecture
tags: [audit, json-schema, storage, v0.1]
created: 2026-04-19
updated: 2026-04-19
status: stable
sources: [Docs/MVP + ALL PROJECT/MVP.md §14]
---

# Reason Codes JSON Schema

**TL;DR:** JSON Schema Draft 2020-12 для audit-record. Append-only JSONL с tamper-evident SHA-256 chain. Secondary SQLite index для O(log n) lookups.

## Schema (v1.0.0)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://algo.local/schemas/trade_audit.v1.json",
  "type": "object",
  "required": ["schema_version","trade_id","timestamp","symbol",
               "signal_inputs","risk_decision","execution","reason_code"],
  "properties": {
    "schema_version": {"const": "1.0.0"},
    "trade_id": {"type": "string", "format": "uuid"},
    "parent_trade_id": {"type": ["string","null"], "format": "uuid"},
    "timestamp": {"type": "string", "format": "date-time", "description": "ISO-8601 UTC ns precision"},
    "symbol": {"type": "string", "pattern": "^[A-Z]+USDT$"},
    "venue": {"const": "BINANCE_SPOT"},
    "strategy_id": {"type": "string"},
    "strategy_version": {"type": "string", "pattern": "^\\d+\\.\\d+\\.\\d+$"},
    "git_commit": {"type": "string", "pattern": "^[a-f0-9]{7,40}$"},
    "config_hash": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
    "bar_closed": {"type": "boolean", "description": "Invariant: must be true for all live decisions"},
    "clock_drift_ms": {"type": "number"},
    "signal_inputs": {
      "type": "object",
      "properties": {
        "bar_timestamp": {"type": "string", "format": "date-time"},
        "bar_ohlcv": {
          "type": "object",
          "properties": {
            "open": {"type": "number"},
            "high": {"type": "number"},
            "low": {"type": "number"},
            "close": {"type": "number"},
            "volume": {"type": "number"}
          }
        },
        "ema_fast": {"type": "number"},
        "ema_slow": {"type": "number"},
        "ema_fast_period": {"type": "integer"},
        "ema_slow_period": {"type": "integer"},
        "adx_14": {"type": "number", "minimum": 0, "maximum": 100},
        "plus_di_14": {"type": "number", "minimum": 0, "maximum": 100},
        "minus_di_14": {"type": "number", "minimum": 0, "maximum": 100},
        "rsi_14": {"type": "number", "minimum": 0, "maximum": 100},
        "atr_14": {"type": "number", "minimum": 0},
        "volume_sma_20": {"type": "number"},
        "data_quality": {"enum": ["OK","STALE","GAP_FILLED","SUSPECT"]},
        "signal_reason": {"type": "string",
          "description": "e.g. EMA_CROSS_UP_WITH_ADX_CONFIRM | NO_SIGNAL"}
      }
    },
    "risk_decision": {
      "type": "object",
      "properties": {
        "account_equity": {"type": "number"},
        "available_balance": {"type": "number"},
        "kelly_phase": {"type": "integer", "minimum": 0, "maximum": 5},
        "position_fraction": {"type": "number", "minimum": 0, "maximum": 1},
        "position_size_quote": {"type": "number"},
        "position_size_base": {"type": "number"},
        "sl_price": {"type": "number"},
        "tp_price": {"type": "number"},
        "sl_distance_atr": {"type": "number"},
        "tp_distance_atr": {"type": "number"},
        "rr_ratio": {"type": "number"},
        "max_risk_quote": {"type": "number"},
        "portfolio_exposure": {"type": "number", "minimum": 0, "maximum": 1},
        "drawdown_pct": {"type": "number", "minimum": 0, "maximum": 1}
      }
    },
    "execution": {
      "type": "object",
      "properties": {
        "order_id_local": {"type": "string"},
        "order_id_exchange": {"type": ["string","null"]},
        "client_order_id": {"type": "string"},
        "order_type": {"enum": ["MARKET","LIMIT","STOP_MARKET","STOP_LIMIT","TAKE_PROFIT"]},
        "side": {"enum": ["BUY","SELL"]},
        "time_in_force": {"enum": ["GTC","IOC","FOK","POST_ONLY"]},
        "intended_price": {"type": "number"},
        "fill_price": {"type": ["number","null"]},
        "fill_qty": {"type": "number"},
        "slippage_bps": {"type": ["number","null"]},
        "fee_quote": {"type": "number"},
        "fee_asset": {"type": "string"},
        "fee_is_maker": {"type": "boolean"},
        "time_submit_ms": {"type": "integer"},
        "time_ack_ms": {"type": "integer"},
        "time_fill_ms": {"type": "integer"},
        "time_to_fill_ms": {"type": "integer"},
        "retry_count": {"type": "integer", "minimum": 0}
      }
    },
    "reason_code": {
      "enum": [
        "ENTRY_LONG_TREND_FOLLOWING","ENTRY_SHORT_TREND_FOLLOWING",
        "ENTRY_LONG_PULLBACK","ENTRY_SHORT_PULLBACK",
        "SCALE_IN_LONG","SCALE_IN_SHORT","SCALE_OUT_PARTIAL",
        "EXIT_SL_HIT","EXIT_TP_HIT","EXIT_TRAILING_STOP",
        "EXIT_SIGNAL_FLIP","EXIT_TIME_STOP",
        "EXIT_CIRCUIT_BREAKER","EXIT_MANUAL_OVERRIDE",
        "REJECT_RISK_EXCEEDED","REJECT_INSUFFICIENT_BALANCE",
        "REJECT_STALE_DATA","REJECT_RATE_LIMITED","REJECT_CLOCK_DRIFT",
        "REJECT_MIN_NOTIONAL","REJECT_FILTER_PRICE","REJECT_DUPLICATE_SIGNAL",
        "HALT_DRAWDOWN_L1","HALT_DRAWDOWN_L2","HALT_DRAWDOWN_L3",
        "HALT_FLASH_CRASH","HALT_DATA_QUALITY","HALT_EXCHANGE_OUTAGE",
        "HALT_KILL_SWITCH",
        "HALT_S36_DD_INTRADAY","HALT_S36_DD_MULTIDAY",
        "HALT_S36_CONSECUTIVE_LOSSES","HALT_S36_NO_TRADE_TIMEOUT",
        "HALT_UNKNOWN_SYMBOL"
      ]
    },
    "notes": {"type": "string", "maxLength": 2048},
    "prev_record_hash": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
    "record_hash": {"type": "string", "pattern": "^[a-f0-9]{64}$"}
  }
}
```

## Storage

- **Primary:** JSONL append-only в `data/audit/audit-YYYY-MM-DD.jsonl.gz` (daily-rotated, gzip).
- **Chain:** `record_hash = SHA-256(prev_record_hash || canonical_json(record))`. Tamper-evident.
- **Index:** SQLite `audit_index` table с `(trade_id, timestamp, symbol, reason_code, file_path, file_offset)`.
- **Cold:** daily gzip в S3/Glacier с ObjectLock WORM (опционально, v0.3+).

## Retention

7 лет (consistent с MiFID II RTS 24 / SEC 17a-4 / CFTC 1.31). ~1 KB × ~500 трейдов/год = ~500 KB/год → хранение бесконечно бесплатно.

## Canonical JSON для hash

Для reproducible hashing используется **canonical JSON**:
- Keys отсортированы lexicographically.
- No whitespace, no trailing newlines.
- Unicode NFC normalization.
- Float `0.1` сериализуется одинаково всегда (use decimal or str).

Python: `json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False)`.

## Chain verification

```python
def verify_chain(jsonl_path):
    prev_hash = "0" * 64  # initial
    with gzip.open(jsonl_path, 'rt') as f:
        for line in f:
            record = json.loads(line)
            expected_prev = record.pop('prev_record_hash')
            actual_hash = record.pop('record_hash')
            if expected_prev != prev_hash:
                raise TamperDetected(f"prev_hash mismatch at {record['trade_id']}")
            canonical = json.dumps(record, sort_keys=True, separators=(',', ':'))
            recomputed = hashlib.sha256((prev_hash + canonical).encode()).hexdigest()
            if recomputed != actual_hash:
                raise TamperDetected(f"record_hash mismatch at {record['trade_id']}")
            prev_hash = actual_hash
```

## Schema evolution

- **Additive changes** (new optional field) → bump patch version `1.0.1`.
- **Required new field** → bump minor version `1.1.0`, provide migration script.
- **Breaking removal / rename** → bump major version `2.0.0`, dual-write during migration period.

Old records остаются immutable; chain NOT regenerated.

## Sources

- Docs/MVP + ALL PROJECT/MVP.md §14.
- JSON Schema Draft 2020-12.
- MiFID II RTS 24, SEC 17a-4, CFTC 1.31 (retention requirements).

## Reason codes count

**Current total: 50** (45 baseline + 4 HALT_S36_* added S36 T5 per ADR 0055 SD-4 + 1 HALT_UNKNOWN_SYMBOL S37 T2 per ADR 0057 SD-1).

| Sprint | Added | Count | Description |
|--------|-------|-------|-------------|
| S1-S6 | +39 | 39 | Foundation codes |
| S7 | +3 | 42 | HALT_BOOTSTRAP_AMBIGUOUS + HALT_EXIT_RECONCILE_DIVERGENCE + EXIT_RECONCILE_DETECTED |
| S8a | +3 | 45 | HALT_RUNTIME_CRASH + HALT_BAR_POLL_STALL + KILL_SWITCH_REQUESTED |
| S36 T5 | +4 | 49 | HALT_S36_DD_INTRADAY(46) + HALT_S36_DD_MULTIDAY(47) + HALT_S36_CONSECUTIVE_LOSSES(48) + HALT_S36_NO_TRADE_TIMEOUT(49) |
| S37 T2 | +1 | **50** | HALT_UNKNOWN_SYMBOL(50) — fail-closed symbol whitelist per ADR 0057 SD-1+SD-2 |

## Related

- [[../../trading/concepts/reason-codes]] — enum enumeration.
- [[storage]] — SQLite `audit_index`.
- [[domain-events]] — events that produce audit records.
- [[../components/halt-gate-wireup]] — S36 wire-up using HALT_S36_* codes.
