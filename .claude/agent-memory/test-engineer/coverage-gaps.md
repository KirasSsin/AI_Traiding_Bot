---
name: Coverage gaps recurring
description: Gaps that appear repeatedly across modules or are explicitly deferred for future sprints
type: project
---

# Coverage Gaps — Recurring and Deferred

## ACTIVE CARRY-OVERS (S39 backlog — confirmed uncovered as of 2026-05-09)

### H1: Rate-limit backoff — `src/execution/bybit/errors.py` + `coordinator.py`
- **Gap:** `map_error(10006, ...) → RATE_LIMIT_HIT` is mapped but NOBODY consumes it for backoff.
  `_try_place_market_sell` / `_best_effort_cancel` have bare `except Exception`, no retry-with-sleep.
- **Tests needed:**
  1. `test_bybit_adapter_rate_limit_backoff`: verify that on retCode=10006, caller receives RATE_LIMIT_HIT ReasonCode (existing `test_bybit_errors.py` covers mapping; missing: coordinator retry path)
  2. If backoff implemented: property test that retry count ≤ MAX and total sleep ≤ MAX_SLEEP
- **File:** `/Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot/tests/unit/test_bybit_errors.py` (extend) + new test for coordinator retry
- **Source:** bybit-api-reviewer H1, S38 T3

### H2: WS reconnect re-subscribe verification — `src/execution/bybit/ws_private.py`
- **Gap:** After `on_disconnect` fires `coordinator.on_ws_reconnect()`, there is no test verifying that `check_alive` is probed AFTER reconnect to confirm WS subscription re-attached.
- **Tests needed:**
  1. `test_ws_private_consumer_reconnect_probe`: simulate disconnect → verify check_alive called twice (initial + post-reconnect verification)
  2. `test_ws_private_consumer_dead_ws_triggers_halt`: check_alive returns False twice → coordinator.request_halt called
- **File:** `/Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot/tests/unit/test_ws_private_consumer.py` (extend)
- **Source:** bybit-api-reviewer H2, S38 T3

### M1: retCode taxonomy gaps — `src/execution/bybit/errors.py`
- **Gap:** `10001` (params error) → UNKNOWN_ERROR (should map to explicit code). `10010` (UID not authorized). `170132` (qty too small — distinct from FILTER_VIOLATION group).
- **Tests needed:** Extend `test_bybit_errors.py` with explicit assertions for 10001, 10010, 170132 → new ReasonCodes when implemented
- **File:** `/Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot/tests/unit/test_bybit_errors.py`
- **Source:** bybit-api-reviewer M1, S38 T3

### M2: pybit response-shape defensive access — `src/execution/bybit/adapter.py`
- **Gap:** `adapter.py:131-134` does `resp["result"]["orderId"]` direct access. No test verifying that malformed response (missing "result" key) raises structured error vs silent KeyError.
- **Tests needed:** `test_bybit_adapter_malformed_response`: fake HTTP response missing "result" → verify BybitAPIError raised (not bare KeyError)
- **File:** `/Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot/tests/unit/test_bybit_adapter.py` (extend)
- **Source:** bybit-api-reviewer M2, S38 T3

### M3: WS data array isinstance guard — `src/execution/bybit/ws_private.py`
- **Gap:** `_on_order_raw` iterates `msg.get("data", [])` but if "data" is a dict (V3 shape regression) it silently iterates keys. No test for this edge case.
- **Tests needed:** `test_ws_private_consumer_data_dict_shape_dropped`: pass WS message with data=dict → verify error logged with structured marker, NOT item processed
- **File:** `/Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot/tests/unit/test_ws_private_consumer.py` (extend)
- **Source:** bybit-api-reviewer M3, S38 T3

### M4: WS consumer __repr__ secret redaction — `src/execution/bybit/ws_private.py`
- **Gap:** `BybitPrivateWSConsumer` doesn't override `__repr__`, so `str(consumer)` could leak api_key/api_secret.
- **Tests needed:** `test_ws_private_consumer_repr_redacts_secrets`: instantiate consumer → `repr(consumer)` does NOT contain api_key or api_secret value
- **File:** `/Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot/tests/unit/test_ws_private_consumer.py` (extend)
- **Source:** bybit-api-reviewer M4, S38 T3

### Item #10: DD_MULTIDAY/NO_TRADE_TIMEOUT extended scenarios — PARTIAL CLOSED (S39 T9)
- **S39 T9 DONE:** Boundary parametrized tests added to `tests/unit/test_halt_gate.py`:
  - `test_dd_multiday_boundary_parametrized` — 4 cases: 0.14/0.15/0.16/0.00 vs DD_MULTIDAY threshold
  - `test_no_trade_timeout_boundary_parametrized` — 4 cases: 5/6/7/0 months vs 6-month threshold
  - Gate logic confirmed `>=` (inclusive) — no source fix needed
  - 8 new cases, halt_gate tests total: 7 → 15, commit 5ce8aa1
- **Remaining gaps (deferred):**
  1. `test_halt_gate_multiday_hwm_resets_daily`: simulate two sessions with equity reset → multiday DD accumulates correctly (HWM logic, if exists in source)
  2. `test_halt_gate_priority_all_triggers_concurrent`: all 4 triggers breached → DD_INTRADAY wins (already covered by existing `test_first_trigger_wins_intraday_priority` — low priority)
- **File:** `/Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot/tests/unit/test_halt_gate.py`
- **Source:** S37+S38 carry-over Item #10

## HISTORICAL GAPS (pre-S37, context only)

### Empty trade list in DSR/MC
- `compute_dsr([])` → NaN (existing test covers)
- `sign_flip_p_value([])` — check exists in test_mc_permutations.py
- Status: COVERED

### Boundary tests n=9/10/29/30 for DSR
- Added in S37 T6 (`test_dsr_sigma_sr_amendment.py` or `test_dsr_status_thresholds.py`)
- Status: COVERED (S37 +5 tests)

### MC p-value floor (1/(N+1) Phipson & Smyth)
- Fixed in S33 T2 + 7 property tests
- Status: COVERED

### pnl_pct vs pnl_quote Sharpe
- Fixed in S38 T2 + 3 tests
- Status: COVERED
