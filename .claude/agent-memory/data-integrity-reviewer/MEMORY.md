# Data Integrity Reviewer — Memory Index

- [WAL + Schema invariants](wal_schema_invariants.md) — SQLite connection pragmas, Decimal-as-TEXT, migration forward-only rules
- [Halt persistence pattern](halt_persistence.md) — write-ahead invariant, primary-wins semantics, halt_log schema
- [FillRecorder adapter pattern](fill_recorder_s12.md) — S12 T1 2-layer pattern, schema gap, UNIQUE INDEX idempotency
- [S37-38 data integrity gaps](s37_s38_gaps.md) — bybit-api H1 rate-limit backoff missing, H2 WS reconnect gap, fill-history wiring PENDING
