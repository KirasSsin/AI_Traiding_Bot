---
title: Log grep templates — operator log filtering recipes
type: runbook
tags: [operator, logging, structlog, grep, sprint-11]
created: 2026-04-25
updated: 2026-04-25
status: stable
sources:
  - src/platform/logging.py
  - migrations/0005_halt_persistence.sql
---

# Log grep templates

**TL;DR:** structlog JSON output filtering recipes для live operator monitoring. JSON keys + grep + jq patterns + halt_log SQL view.

Per S11 PHASE 2 Q3 (operator readiness deliverable 2 — log aggregation).

## structlog output format

Все logs JSON-formatted via `structlog`. Each event has obligatory keys: `event`, `level`, `timestamp` + arbitrary structured key=value fields.

Example:
```
{"event": "data_quality.deviation_exceeds_threshold", "level": "warning", "timestamp": "2026-04-25T12:00:00Z", "prior_close": "100000", "current_close": "100600", "deviation_pct": "0.006000", "threshold_pct": "0.005"}
```

## Common operator queries (jq filters)

### Halt events (any class)

```bash
tail -f bot.log | jq 'select(.event | test("halt"))'
```

### Specific halt code (e.g. HALT_DATA_QUALITY)

```bash
tail -f bot.log | jq 'select(.event == "data_quality.deviation_exceeds_threshold")'
```

### All bar ticks (frequency check — should fire 1×/hour для 1H bars)

```bash
tail -f bot.log | jq 'select(.event == "runtime.bar_tick") | {ts: .timestamp, close: .bar_close_ts}'
```

### Reconcile divergence detection

```bash
grep -E "RECONCILE_(DIVERGENCE|HEAL|EXITED)" bot.log | jq .
```

### WS reconnect events

```bash
grep "ws_private" bot.log | jq 'select(.event | test("disconnect|reconnect"))'
```

### Order flow trace (entry through exit)

```bash
jq 'select(.event | test("coordinator|order_event|wallet_event"))' bot.log
```

### Strategy signal emissions

```bash
jq 'select(.event == "strategy.signal_emitted")' bot.log
```

### Risk rejections

```bash
jq 'select(.event == "runtime.signal_rejected")' bot.log
```

## halt_log SQL view (от SQLite)

Halt persistence per ADR 0021 sub-decision 4 — schema `halt_log` table appends каждый halt. Operator queries:

### Last 10 halts с reason

```sql
SELECT halt_ts, halt_reason, context
FROM halt_log
ORDER BY halt_ts DESC
LIMIT 10;
```

### Halt frequency per code (last 7 days)

```sql
SELECT halt_reason, COUNT(*) AS count
FROM halt_log
WHERE halt_ts >= datetime('now', '-7 days')
GROUP BY halt_reason
ORDER BY count DESC;
```

### CRITICAL halts только (per priority matrix P0)

```sql
SELECT halt_ts, halt_reason
FROM halt_log
WHERE halt_reason IN (
    'HALT_DRAWDOWN_L2', 'HALT_DRAWDOWN_L3', 'HALT_FLASH_CRASH',
    'HALT_RECONCILE_DIVERGENCE', 'HALT_BOOTSTRAP_AMBIGUOUS',
    'HALT_EXIT_RECONCILE_DIVERGENCE', 'HALT_BRACKET_INCOMPLETE',
    'HALT_PHANTOM_SL', 'HALT_FLATTEN_FAILED', 'HALT_RUNTIME_CRASH'
)
ORDER BY halt_ts DESC;
```

## execution_state SQL inspection

### Current state (single symbol)

```sql
SELECT symbol, state, halt_reason, last_event, updated_at
FROM execution_state
WHERE symbol = 'BTCUSDT';
```

### Active brackets

```sql
SELECT symbol, state, entry_order_id, tp_order_id, sl_order_id
FROM execution_state
WHERE state IN ('LONG_OPEN', 'OCO_ARMED', 'OCO_ARMING');
```

## trade_history SQL inspection

### Recent closed trades

```sql
SELECT trade_id, symbol, exit_ts, pnl_quote, pnl_pct, reason_code
FROM trade_history
ORDER BY exit_ts DESC
LIMIT 20;
```

### Win rate (last 30 days)

```sql
SELECT
    COUNT(*) AS total,
    SUM(CASE WHEN CAST(pnl_quote AS REAL) > 0 THEN 1 ELSE 0 END) AS wins,
    ROUND(100.0 * SUM(CASE WHEN CAST(pnl_quote AS REAL) > 0 THEN 1 ELSE 0 END) / COUNT(*), 2) AS win_rate_pct
FROM trade_history
WHERE exit_ts >= datetime('now', '-30 days');
```

## Live tail commands

### Bot stdout (assuming `python -m src run > bot.log 2>&1`)

```bash
tail -f bot.log | jq -r '"\(.timestamp) [\(.level | ascii_upcase)] \(.event) \(. | del(.timestamp, .level, .event))"'
```

### Halt-only tail

```bash
tail -f bot.log | jq 'select(.event | test("halt|HALT")) | {ts: .timestamp, event, halt_reason: .halt_reason}'
```

## Related

- [[halt-recovery]] — 19 halt codes + recovery procedures + priority matrix (S11)
- [[pre-flight]] — operator pre-flight checklist (S11)
- [[../components/storage]] — SQLite schema source of truth

## Sources

- `src/platform/logging.py` — structlog setup
- `migrations/0005_halt_persistence.sql` — halt_log table schema
- `migrations/002_risk.sql` — trade_history schema
- `migrations/0003_execution_state.sql` — execution_state schema
