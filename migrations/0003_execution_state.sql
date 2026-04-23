-- migrations/0003_execution_state.sql
CREATE TABLE IF NOT EXISTS execution_state (
    symbol TEXT PRIMARY KEY,
    state TEXT NOT NULL,
    position_qty TEXT NOT NULL,
    entry_price TEXT,
    oco_main_order_id TEXT,
    updated_at TEXT NOT NULL
);
