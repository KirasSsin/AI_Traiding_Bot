---
name: trade_extractor pnl_pct convention
description: pnl_pct is simple return; DSR consumes via log(1+r). Convention verified correct for S13 T5.
type: project
---

`extract_trade_records` computes `pnl_pct = pnl_quote / (qty * entry_price)` — simple return on notional.

DSR consumer (`src/analytics/dsr.py::compute_returns`) applies `log(1 + pnl_pct)` by default (`use_log=True`). This converts simple return to log return for Sharpe/DSR computation. Convention is correct.

**Why:** Bailey DSR formula operates on log returns for compounding-consistent Sharpe. Simple return stored in TradeRecord; log conversion deferred to analytics layer. This is intentional two-layer design.

**How to apply:** When reviewing any new DSR consumer, verify it uses `use_log=True` (default). Verify no consumer passes `pnl_pct` directly to Sharpe numerator without log conversion. Sprint: S13 T5.
