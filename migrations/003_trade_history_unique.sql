-- Sprint 4 Task 7 follow-up: add UNIQUE constraint on entry_signal_id
-- to prevent silent double-insert from at-least-once delivery.
CREATE UNIQUE INDEX IF NOT EXISTS uq_trade_history_entry_signal
    ON trade_history(entry_signal_id);
