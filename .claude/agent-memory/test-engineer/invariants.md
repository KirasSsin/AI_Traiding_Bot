---
name: Property invariants
description: Hypothesis-verified invariants for domain types — DSR, MC, Sharpe, OHLCV
type: project
---

# Property Invariants — Hypothesis

## DSR (Deflated Sharpe Ratio)
- `0 ≤ DSR ≤ 1` always (Bailey & López de Prado)
- `DSR(empty=[]) → NaN` (not 0, not 1)
- `DSR(constant_returns) → NaN` (zero variance → degenerate)
- DSR boundary: n=9 → UNDERPOWERED, n=10 → normal calculation (S37 T6 calibrated)
- Hypothesis strategy: `st.lists(st.decimals(min_value=-1, max_value=1, allow_nan=False), min_size=1)`

## MC p-value
- `p ∈ [1/(N+1), 1]` always — floor is Phipson & Smyth 2010 (NOT 0)
- `sign_flip_p_value(all_positive) → floor ~0.0005 at N=2000` (NOT 0 post-S33 fix)
- `block_bootstrap_p_value(all_positive) → floor ~0.0005` (same fix)
- Hypothesis: `@given(returns=st.lists(st.floats(min_value=-10, max_value=10, allow_nan=False, allow_infinity=False), min_size=1))`

## Live Sharpe
- `compute_live_sharpe(trades_A) == compute_live_sharpe(trades_B)` when `all pnl_pct identical` regardless of pnl_quote (S38 F2 invariant)
- `compute_live_sharpe(n<30) → status="UNDERPOWERED"` 
- `compute_live_sharpe(constant_pct) → status="DEGENERATE_VARIANCE"`
- Key: returns must use pnl_pct (dimensionless), NOT pnl_quote (size-biased)

## OHLCV bar invariants
- `high ≥ low` always
- `high ≥ open ≥ low` (or `high ≥ close ≥ low`)
- `volume ≥ 0`
- `timestamp monotonically increasing` in a sequence

## TradeRecord
- `pnl_quote = (exit_price - entry_price) × qty - fees_paid` (within Decimal tolerance)
- `pnl_pct = pnl_quote / (entry_price × qty)` (fractional return)
- `entry_ts < exit_ts` always
- `qty > 0` always

## HaltGate
- At most ONE trigger per evaluate() call (first-match semantics, DD_INTRADAY wins)
- `evaluate(all_below_threshold) → None` always
- `evaluate(any_above_threshold) → corresponding HaltTrigger` always
- `HaltGate(threshold=0) → ValueError` (all thresholds must be positive)

## FSM transitions
- `TRANSITIONS` table is deterministic: (state, event) → unique next_state
- No state reachable from itself via single event (no self-loops in production states)
- `HALTED` is absorbing EXCEPT for KILL_SWITCH_REQUESTED + HALT_RUNTIME_CRASH + HALT_BAR_POLL_STALL (allow-list per ADR 0023)
- Hypothesis: for all `(state, event)` not in TRANSITIONS → IllegalTransitionError raised
