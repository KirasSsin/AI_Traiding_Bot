---
name: DSR status boundary thresholds n=10/n=30
description: ADR 0056 defines INSUFFICIENT_TRADES at n<10, UNDERPOWERED at 10<=n<30, GATE_ELIGIBLE at n>=30. Boundary tests n=9/10/29/30 missing post-S36 (C2 carry-over).
type: project
---

ADR 0056 N_trades thresholds table:
- n < 10: DSR=NaN, status=INSUFFICIENT_TRADES
- 10 <= n < 30: DSR computed, status=UNDERPOWERED (informational)
- n >= 30: DSR computed, status=GATE_ELIGIBLE

**Why C2 carry-over matters:** At ~13 trades/year baseline (δ TESTNET), the bot spends the entire 12mo evaluation window in the n=10-30 boundary zone. An off-by-one defect in `compute_dsr_with_status()` at `src/analytics/dsr.py` would emit wrong status labels during the only live data accumulation window available, corrupting audit records.

**How to apply:** When reviewing dsr.py or tests for DSR, check that parametrized boundary tests exist for n=9 (INSUFFICIENT), n=10 (UNDERPOWERED), n=29 (UNDERPOWERED), n=30 (GATE_ELIGIBLE). File: `tests/unit/test_dsr_status_thresholds.py` (to be created in S37). This was C2 from S36 T6 quant-stats review; pre-s37-backlog.md Item 8.

S37 consilium ROUND 5: INCLUDE in S37 scope (pre-activation correctness, ~30 min cost).
