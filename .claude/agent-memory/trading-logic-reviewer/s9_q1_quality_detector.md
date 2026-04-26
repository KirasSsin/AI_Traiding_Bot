---
name: S9 Q1 BarPriceQualityDetector wiring — concern logged
description: T3 review findings for RuntimeManager + BarPriceQualityDetector commit 92d4246
type: project
---

**Concern (non-blocking):** `_poll_bar_and_strategy` on quality halt does NOT set `self._stopping = True`. Compare: HALT_BAR_POLL_STALL sets `_stopping=True` (line 146); KILL_SWITCH sets `_stopping=True` (line 119); HALT_DATA_QUALITY only calls `request_halt` then `return` (line 152-153). This means after a quality halt, the main loop (`while not self._stopping`) continues ticking. Each subsequent tick will re-trigger the quality check (detector retains updated baseline) and call `request_halt` again. FSM γ primary-wins rule absorbs repeat halts (halt_log appends, halt_reason unchanged), so this is NOT a safety regression. But it IS noisy and inconsistent with the other halt patterns.

**Test gap:** `test_quality_detector_halts_on_consecutive_bar_deviation` does not assert `strat.on_bar.call_count == 1` (only bar1 consumed strategy, bar2 halted before strategy). The positive test (`within_threshold`) correctly asserts `call_count == 2`, but the halt test is missing the symmetrical negative assertion.

**Verified clean:**
- Tick pipeline ordering: quality fires BEFORE strategy.on_bar (manager.py:151 before :155). Correct.
- Look-ahead: detector compares closed REST bars only. No WS partial bars. No future data.
- Halt routing: HALT_DATA_QUALITY in _REQUEST_HALT_CODES allow-list (property test GREEN).
- HALT_BAR_POLL_STALL fires first (lines 139-147 before line 151). Correct precedence.
- bar=None skips quality check (line 148 guard fires first). Correct.
- Settings field: Decimal, default 0.005, not in _HASH_ALLOWLIST (correct — not a risk-threshold).
- FSM counts: 16/30/74/45 unchanged (verified via python -c).
- Property test test_request_halt_mapping: 4/4 PASS including HALT_DATA_QUALITY.

**Why:** logged for sprint-finish review; _stopping gap should be fixed before S9 ships to avoid noisy log storms post-halt.
