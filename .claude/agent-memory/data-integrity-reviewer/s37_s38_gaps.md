---
name: S37-38 data integrity gaps
description: Data persistence tasks deferred in S37-38, bybit-api rate-limit backoff risk, WAL/SQLite and schema gaps outstanding post-S38
type: project
---

## S37-38 deferred persistence tasks

**S37 data integrity scope:** All persistence tasks in S37 completed — no data tasks skipped. S37 = security hardening (symbol whitelist + activation_ts HMAC + clock injection + DSR boundary tests + operator playbook). No storage schema changes. 897 unit + 33 integration passed.

**S38 data integrity scope:** F2 quant fix (pnl_pct in compute_live_sharpe — analytics read path, not write path). Item #7 RiskSharedDeps = DI wiring only (no schema changes). 905 unit + 33 integration passed. No new migrations.

## bybit-api H1 rate-limit backoff — carry-over risk

**Finding:** bybit-api-reviewer T3 S38 first invocation identified H1 = rate-limit exponential backoff missing on REST client. Specifically `BybitRESTClient.get_klines` paginator does NOT implement exponential backoff on HTTP 429 / retCode 10006. Only retCode != 0 raises `BybitAPIError` with `RATE_LIMIT_HIT` reason, but no retry loop exists.

**Actual risk:** Low at current single-symbol 4H cadence (720 req/hour vs 600 req/min Bybit limit). No production rate-limit incidents reported. However, during REST catch-up after WS reconnect (backfill window), rapid pagination could exhaust rate limit → cascading failures → bar-poller stall → HALT_BAR_POLL_STALL.

**Severity:** HIGH (correctness gap) — operationally safe today, blocker before any multi-symbol or higher-cadence expansion.

**Status:** Deferred to pre-s39-backlog. Not yet implemented.

**Fix pattern per ADR:** Add retry wrapper in `BybitRESTClient` around pybit calls: catch `retCode=10006`, sleep `min(2^attempt, 60)` seconds, retry up to N times, then raise. Same for HTTP 429.

## H2 WS reconnect verification gap

**Finding:** bybit-api-reviewer H2 — `BybitWSConsumer` and `BybitPrivateWSConsumer` reconnect is delegated entirely to pybit SDK. No verification that re-subscription was successful (topic re-subscribe after reconnect). Gap: if pybit silently reconnects but fails to re-subscribe, consumer appears alive but receives no events.

**Risk:** Silent data loss during reconnect window. `check_alive` watchdog only checks ping heartbeat, not topic subscription status.

**Status:** Deferred to pre-s39-backlog.

## WAL/SQLite integrity status post-S38

**Status:** Clean. All invariants preserved:
- WAL mode confirmed active (F7 Gate 2 in playbook)
- No new migrations in S37-38
- Decimal-as-TEXT pattern preserved across all monetary columns
- halt_log write-ahead invariant preserved (S7 ADR 0021 sub-decision 4 unchanged)
- schema_migrations idempotent runner unchanged
- canonical counts: 16 states / 30 events / 74 transitions / 50 reason codes

## Fill-history production wiring gap (carry-over from S12)

**Status:** STILL PENDING as of S38. `__main__.py::_cmd_run` still uses `MagicMock` for `fill_recorder`. `FillHistoryRepository` built but not wired to live runtime. `FillRecorderAdapter.Layer2` always skips (no `entry_signal_id` column in `execution_state`).

**Layer 1 structlog audit fires** — fill events not lost, preserved in JSON log stream.

**Fix chain:** add `entry_signal_id` migration → wire `FillRecorderAdapter` in `_cmd_run` → Layer 2 operational.

**Why:** Q7 zero-migration constraint in S12 deferred this. No subsequent sprint has addressed it.

**How to apply:** Flag as HIGH concern if reviewing any sprint that touches live execution wiring.
