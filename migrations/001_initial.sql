-- Sprint 1 schema. Source: wiki/project/architecture/storage.md

CREATE TABLE orders (
  client_order_id TEXT PRIMARY KEY,
  exch_order_id   TEXT UNIQUE,
  symbol          TEXT NOT NULL,
  side            TEXT NOT NULL CHECK(side IN ('BUY','SELL')),
  type            TEXT NOT NULL CHECK(type IN ('MARKET','LIMIT','STOP_MARKET','STOP_LIMIT','TAKE_PROFIT')),
  status          TEXT NOT NULL CHECK(status IN ('NEW','PARTIALLY_FILLED','FILLED','CANCELED','EXPIRED','REJECTED')),
  orig_qty        REAL NOT NULL,
  executed_qty    REAL NOT NULL DEFAULT 0,
  price           REAL,
  created_at      TEXT NOT NULL,
  updated_at      TEXT NOT NULL
);

CREATE TABLE fills (
  fill_id         INTEGER PRIMARY KEY AUTOINCREMENT,
  client_order_id TEXT NOT NULL REFERENCES orders(client_order_id),
  trade_id        INTEGER NOT NULL,
  qty             REAL NOT NULL,
  price           REAL NOT NULL,
  fee             REAL NOT NULL,
  fee_asset       TEXT NOT NULL,
  is_maker        INTEGER NOT NULL,
  filled_at       TEXT NOT NULL,
  UNIQUE(trade_id)
);

CREATE TABLE positions (
  position_id     TEXT PRIMARY KEY,
  symbol          TEXT NOT NULL,
  side            TEXT NOT NULL,
  qty             REAL NOT NULL,
  avg_entry_price REAL NOT NULL,
  opened_at       TEXT NOT NULL,
  closed_at       TEXT,
  realized_pnl    REAL
);

CREATE TABLE events (
  aggregate_id    TEXT NOT NULL,
  version         INTEGER NOT NULL,
  event_type      TEXT NOT NULL,
  occurred_at     TEXT NOT NULL,
  payload_json    TEXT NOT NULL,
  PRIMARY KEY (aggregate_id, version)
);
CREATE INDEX idx_events_occurred ON events(occurred_at);

CREATE TABLE runs (
  run_id           TEXT PRIMARY KEY,
  started_at       TEXT NOT NULL,
  ended_at         TEXT,
  git_commit       TEXT NOT NULL,
  config_hash      TEXT NOT NULL,
  strategy_version TEXT NOT NULL
);

CREATE TABLE config (
  config_hash     TEXT PRIMARY KEY,
  config_json     TEXT NOT NULL,
  loaded_at       TEXT NOT NULL
);

CREATE TABLE state (
  key             TEXT PRIMARY KEY,
  value_json      TEXT NOT NULL,
  updated_at      TEXT NOT NULL
);

CREATE TABLE audit_index (
  trade_id        TEXT PRIMARY KEY,
  timestamp       TEXT NOT NULL,
  symbol          TEXT NOT NULL,
  reason_code     TEXT NOT NULL,
  file_path       TEXT NOT NULL,
  file_offset     INTEGER NOT NULL
);
CREATE INDEX idx_audit_timestamp ON audit_index(timestamp);
CREATE INDEX idx_audit_reason ON audit_index(reason_code);
