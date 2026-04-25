-- Sprint 9 Q3 B1: per-fill granularity for analytics + audit.
-- FK to trade_history.trade_id; one trade may have N fills (typically 1 for
-- Spot Market entries, 1-2 for IOC SL StopMarket partial-fills).
--
-- exec_id = Bybit V5 execution-list event identifier (UNIQUE for idempotency
-- under at-least-once WS delivery).
CREATE TABLE IF NOT EXISTS trade_fills (
    fill_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_trade_id  INTEGER NOT NULL,
    exec_id          TEXT    NOT NULL,
    fill_qty         TEXT    NOT NULL,
    fill_price       TEXT    NOT NULL,
    fill_fee         TEXT    NOT NULL,
    fee_currency     TEXT    NOT NULL,
    is_partial       INTEGER NOT NULL CHECK(is_partial IN (0, 1)),
    fill_ts          TEXT    NOT NULL,
    recorded_at      TEXT    NOT NULL,
    FOREIGN KEY (parent_trade_id) REFERENCES trade_history(trade_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_trade_fills_exec_id
    ON trade_fills(exec_id);

CREATE INDEX IF NOT EXISTS idx_trade_fills_parent_ts
    ON trade_fills(parent_trade_id, fill_ts);
