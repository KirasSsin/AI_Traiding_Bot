-- Sprint 4 — Risk & Circuit Breakers schema.
-- Source: wiki/project/plans/2026-04-23-sprint-4-risk.md §Q5

CREATE TABLE trade_history (
    trade_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol           TEXT    NOT NULL,
    entry_signal_id  TEXT    NOT NULL,
    entry_ts         TEXT    NOT NULL,
    exit_ts          TEXT    NOT NULL,
    qty              TEXT    NOT NULL,
    entry_price      TEXT    NOT NULL,
    exit_price       TEXT    NOT NULL,
    pnl_quote        TEXT    NOT NULL,
    pnl_pct          TEXT    NOT NULL,
    fees_paid        TEXT    NOT NULL,
    reason_code      TEXT    NOT NULL,
    kelly_phase      INTEGER NOT NULL CHECK(kelly_phase IN (1,2,3,4)),
    recorded_at      TEXT    NOT NULL
);
CREATE INDEX idx_trade_history_exit_ts     ON trade_history(exit_ts);
CREATE INDEX idx_trade_history_symbol_exit ON trade_history(symbol, exit_ts);

CREATE TABLE equity_snapshots (
    snapshot_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    ts               TEXT    NOT NULL,
    realized_equity  TEXT    NOT NULL,
    unrealized_pnl   TEXT    NOT NULL,
    total_equity     TEXT    NOT NULL,
    source           TEXT    NOT NULL CHECK(source IN ('BAR_CLOSE','POSITION_CLOSE','MANUAL'))
);
CREATE INDEX idx_equity_ts ON equity_snapshots(ts);
