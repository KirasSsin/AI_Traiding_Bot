-- migrations/0005_halt_persistence.sql
-- Forward-only ALTER + CREATE TABLE. ADR 0021 sub-decisions 5 and 9.
-- Persistence of halt_reason / last_exit_reason on execution_state +
-- append-only halt_log audit table for chronological halt trail.

ALTER TABLE execution_state ADD COLUMN halt_reason TEXT;
ALTER TABLE execution_state ADD COLUMN last_exit_reason TEXT;
ALTER TABLE execution_state ADD COLUMN last_reconcile_at TEXT;
ALTER TABLE execution_state ADD COLUMN bootstrap_at TEXT;

CREATE TABLE halt_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol       TEXT    NOT NULL,
    ts           TEXT    NOT NULL,
    reason       TEXT    NOT NULL,
    context_json TEXT    NOT NULL
);

CREATE INDEX halt_log_symbol_ts ON halt_log(symbol, ts);
