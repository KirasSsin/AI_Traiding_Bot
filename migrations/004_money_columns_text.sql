-- Sprint 49 tech-audit H7: money columns REAL -> TEXT (Decimal-as-TEXT rule).
--
-- orders.orig_qty/executed_qty/price, fills.qty/price/fee,
-- positions.qty/avg_entry_price/realized_pnl were declared REAL (IEEE-754
-- float) in 001_initial.sql -> silent precision loss on monetary values.
-- All other money persistence in this project stores Decimal as TEXT
-- (trade_history, trade_fills, execution_state); these three tables are the
-- only REAL holdouts. They currently have ZERO writers (the live path uses
-- trade_history), so this rebuild is safe and forward-looking: it closes the
-- precision gap before any producer is wired.
--
-- SQLite cannot ALTER a column's type, so each table is rebuilt:
-- CREATE *_new with TEXT money columns -> copy existing rows (CAST REAL->TEXT
-- for safety; tables are expected empty) -> DROP old -> RENAME. The migration
-- runner (src/platform/db.py init_db) wraps this file in a single BEGIN/COMMIT,
-- so the rebuild is atomic; no explicit transaction here (matches 0005/0006).

-- --- orders ---
CREATE TABLE orders_new (
  client_order_id TEXT PRIMARY KEY,
  exch_order_id   TEXT UNIQUE,
  symbol          TEXT NOT NULL,
  side            TEXT NOT NULL CHECK(side IN ('BUY','SELL')),
  type            TEXT NOT NULL CHECK(type IN ('MARKET','LIMIT','STOP_MARKET','STOP_LIMIT','TAKE_PROFIT')),
  status          TEXT NOT NULL CHECK(status IN ('NEW','PARTIALLY_FILLED','FILLED','CANCELED','EXPIRED','REJECTED')),
  orig_qty        TEXT NOT NULL,
  executed_qty    TEXT NOT NULL DEFAULT '0',
  price           TEXT,
  created_at      TEXT NOT NULL,
  updated_at      TEXT NOT NULL
);
INSERT INTO orders_new (
  client_order_id, exch_order_id, symbol, side, type, status,
  orig_qty, executed_qty, price, created_at, updated_at
)
SELECT
  client_order_id, exch_order_id, symbol, side, type, status,
  CAST(orig_qty AS TEXT),
  CAST(executed_qty AS TEXT),
  CASE WHEN price IS NULL THEN NULL ELSE CAST(price AS TEXT) END,
  created_at, updated_at
FROM orders;
DROP TABLE orders;
ALTER TABLE orders_new RENAME TO orders;

-- --- fills ---
CREATE TABLE fills_new (
  fill_id         INTEGER PRIMARY KEY AUTOINCREMENT,
  client_order_id TEXT NOT NULL REFERENCES orders(client_order_id),
  trade_id        INTEGER NOT NULL,
  qty             TEXT NOT NULL,
  price           TEXT NOT NULL,
  fee             TEXT NOT NULL,
  fee_asset       TEXT NOT NULL,
  is_maker        INTEGER NOT NULL,
  filled_at       TEXT NOT NULL,
  UNIQUE(trade_id)
);
INSERT INTO fills_new (
  fill_id, client_order_id, trade_id, qty, price, fee,
  fee_asset, is_maker, filled_at
)
SELECT
  fill_id, client_order_id, trade_id,
  CAST(qty AS TEXT),
  CAST(price AS TEXT),
  CAST(fee AS TEXT),
  fee_asset, is_maker, filled_at
FROM fills;
DROP TABLE fills;
ALTER TABLE fills_new RENAME TO fills;

-- --- positions ---
CREATE TABLE positions_new (
  position_id     TEXT PRIMARY KEY,
  symbol          TEXT NOT NULL,
  side            TEXT NOT NULL,
  qty             TEXT NOT NULL,
  avg_entry_price TEXT NOT NULL,
  opened_at       TEXT NOT NULL,
  closed_at       TEXT,
  realized_pnl    TEXT
);
INSERT INTO positions_new (
  position_id, symbol, side, qty, avg_entry_price,
  opened_at, closed_at, realized_pnl
)
SELECT
  position_id, symbol, side,
  CAST(qty AS TEXT),
  CAST(avg_entry_price AS TEXT),
  opened_at, closed_at,
  CASE WHEN realized_pnl IS NULL THEN NULL ELSE CAST(realized_pnl AS TEXT) END
FROM positions;
DROP TABLE positions;
ALTER TABLE positions_new RENAME TO positions;
