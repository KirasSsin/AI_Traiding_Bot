---
name: S35 T4 c1fa201 code quality review
description: Donchian breakout strategy — mypy/ruff pass, design consistency verified, API concern tracked for wiki
type: feedback
---

## Summary

**Status:** PASS all CRITICAL gates (mypy strict 0 / ruff 0 / pytest 4 GREEN)

**Commit:** c1fa201 (S35 T4 part 1) — 164 LoC + 103 test LoC + __init__ exports

**Files:** 
- NEW `src/signalgen/donchian_strategy.py` (164 LoC) — DonchianBreakoutStrategy class
- MOD `src/signalgen/__init__.py` — exports
- NEW `tests/unit/test_donchian_strategy.py` (103 LoC) — 4 tests, all GREEN

## Blockers

None. All static analysis gates pass. Code ready for T5 backtest runner.

## Code Quality Findings

### ✅ Type Hints — Strict Compliance
- All public methods fully annotated (no `Any`)
- `Signal | None` return type honored
- `dict[str, object]` for DONCHIAN_LONG_ONLY_PARAMS (intentional pattern-matching flexibility for ADR 0054 LOCKED params)
- mypy --strict: **0 errors**

### ✅ Pythonic Patterns
- StrEnum (SignalSide) correct idiom per project stack (pydantic v2)
- Frozen Signal model via `ConfigDict(frozen=True)` — immutability enforced
- Decimal(str(x)) constructor used for ATR → Decimal conversion (hygiene honored)
- list[Bar] buffer management with slicing `[-self._buffer_size:]` — no index off-by-one errors

### ✅ Error Handling
- Explicit ValueError guards in __init__ (lookback > 0, exit_lookback < lookback, atr_mult > 0)
- NaN checks after indicator computation (`if np.isnan(atr_now)`)
- Bar validation in _append_bar() (is_closed, symbol match, time ordering) — defensive
- Zero placeholder fields in Signal (ema_fast, ema_slow, adx, DI, rsi) annotated in docstring

### ⚠️ API Design — Tracked Concern (Non-blocking)
**Issue:** `DONCHIAN_LONG_ONLY_PARAMS: dict[str, object]` uses runtime dict with string keys instead of TypedDict or frozen dataclass.

**Current state:** Line 32-38 defines dict with mixed types (int, Decimal, str). Pattern matches **mean-reversion-strategy.py** MEAN_REVERSION_S17_RELAXED_PARAMS (same struct).

**Why concern:** 
- Type-unsafe: callers extract values with `int(params["lookback_n"])` + cast chain (visible in test fixture _strategy(), line 36-39)
- No IDE/mypy hover hints on dict keys — loose coupling vs tight API
- Dict keys discovered only by reading code/docstring, not signature

**ADR 0054 Context:** LOCKED parameters may justify pragmatic dict (pre-registration immutable by social contract, not code enforcement). If params ever become mutable OR more strategies added → TypedDict upgrade recommended.

**Follow-up:** Ask trading-logic-reviewer if pattern OK per domain convention (strategy params registry = runtime discovery).

## Tests & Coverage

**pytest:** 4 tests, all GREEN
- test_warmup_no_signal_until_buffer_full — buffer saturation guard ✓
- test_breakout_above_donchian_high_emits_long_signal — entry logic ✓
- test_long_only_invariant_no_short_signals — FSM invariant ✓
- test_atr_stop_exit_when_in_long — exit logic ✓

**Coverage:** Manual fixtures (no Hypothesis) — adequate for deterministic state machine. Slice indexing `[-(n+1):-1]` excludes current bar (correct look-ahead prevention).

## Verified Patterns (Good Pythonic Examples)

1. **Stateful strategy design:** _append_bar() → _build_signal() separation (reused from mean-reversion, consistency ✓)
2. **Numpy boundary safety:** `highs[-(self._lookback_n + 1) : -1]` excludes current bar explicitly (anti-snooping preserved)
3. **Decimal hygiene:** `Decimal(str(atr_now))` on line 162 (correct; never `Decimal(float_value)`)
4. **UTC timezone:** `datetime.now(UTC)` for signal timestamp — naive datetime avoided ✓
5. **Module docstring:** ADR 0054 LOCKED conditions documented at module level (institutional memory)
6. **Keyword-only args:** `def __init__(self, *, symbol: ...)` — prevents positional misuse ✓

## Minor Style Notes (Already Passing Ruff)

- Import grouping correct (stdlib → third-party → local)
- No f-strings in reason codes (string literals) ✓
- Private attributes prefixed `_` consistently
- Docstring format matches project (NumPy-style parameter sections absent but minimal class, acceptable)

## Follow-ups for Wiki

1. **Component page:** Create `wiki/project/components/donchian_strategy.md` — explain S35 α track rationale, ADR 0054 anti-snooping context, why separate from mean-reversion
2. **API design pattern:** If >2 strategies accumulate dict-based params, consider wiki entry on TypedDict upgrade path (not urgent given LOCKED semantics)
3. **Trading-logic-reviewer dispatch:** Validate Donchian math (max/min window slicing) + channel-exit heuristic + ATR stop formula fit domain conventions

---

## Verdict

**Approve for T5 backtest runner.** Code is production-quality: strict types, error handling solid, Decimal hygiene honored, tests deterministic. API design concern noted (tracked, non-blocking) — suitable for wiki discussion post-review.
