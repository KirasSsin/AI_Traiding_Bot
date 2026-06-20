-- migrations/0007_bracket_exit_prices.sql
-- S55 BLOCKER TL-01: persist the bracket's planned TP/SL prices at start_bracket
-- so the entry-Filled handler (on_order_event) can arm the OCO legs after the fill.
-- Before this fix the runtime never armed: arm_oco needs tp_price + sl_trigger_price,
-- which were passed to start_bracket but discarded (not stored on the row).
-- Forward-only ALTER ADD COLUMN; existing rows get NULL (no live bracket carried
-- across the migration in single-symbol v0.1). Money columns are TEXT (Decimal
-- string) per migration 004_money_columns_text.sql.

ALTER TABLE execution_state ADD COLUMN bracket_tp_price TEXT;
ALTER TABLE execution_state ADD COLUMN bracket_sl_trigger_price TEXT;
