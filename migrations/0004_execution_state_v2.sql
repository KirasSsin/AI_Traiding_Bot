-- migrations/0004_execution_state_v2.sql
-- Forward-only ALTER ADD COLUMN. ADR 0020 sub-decision 2 (3-order Spot OCO emulation).
-- oco_main_order_id stays in schema (S5 backward-compat); new code writes NULL
-- and reads from oco_tp_order_id + oco_sl_order_id instead.

ALTER TABLE execution_state ADD COLUMN bracket_id TEXT;
ALTER TABLE execution_state ADD COLUMN oco_tp_order_id TEXT;
ALTER TABLE execution_state ADD COLUMN oco_sl_order_id TEXT;
ALTER TABLE execution_state ADD COLUMN expected_oco_qty TEXT;
ALTER TABLE execution_state ADD COLUMN arming_started_at TEXT;
ALTER TABLE execution_state ADD COLUMN last_attempt_num INTEGER NOT NULL DEFAULT 1;
