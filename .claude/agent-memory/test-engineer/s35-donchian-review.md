---
name: S35 Donchian coverage review
description: Coverage verdict for DonchianBreakoutStrategy (S35 T4). Gaps ranked, ship decision, deferred list for S36+.
type: project
---

S35 T4 added `src/signalgen/donchian_strategy.py` (~164 LoC) with 4 unit tests.
Backtest verdict FAIL conjoint (α direction CLOSED). Tests are pre-registered ADR 0054 LOCKED.

**Ship verdict: NO new tests required for S35 merge.**

HIGH gaps (add if α direction reopens in S36+):
1. Channel exit path (`EXIT_FLAT_CHANNEL` reason) — completely untested code path
2. Re-entry after exit (LONG → FLAT → LONG state machine cycle) — entry_close reset untested
3. `_append_bar` guards: symbol mismatch / is_closed=False / out-of-order close_time — defensive branches untested

MEDIUM gaps (Hypothesis property tests):
4. `signal.side != SHORT` for any input sequence — property test would be authoritative
5. ATR stop price always < entry_close — invariant testable via Hypothesis
6. `exit_lookback_n < lookback_n` constructor invariant enforced (existing ValueError — zero unit tests verify it)

LOW gaps (boundary):
7. Buffer boundary: exactly `lookback_n + 1` bars → signal emits
8. NaN ATR branch: `return None` on `np.isnan(atr_now)` — currently untested

**Existing 4 tests quality: GOOD.**
- Naming follows test_<func>_<scenario> pattern
- Each test has explicit assertions (no bare exception checks)
- _bar() helper fixture is clean (DAMP — not over-abstracted)
- `test_long_only_invariant` assertion is weak: `if sig is not None` — should be unconditional `assert sig is None`

**Why:** line 86-87 of test file: `if sig is not None: assert sig.side != "SHORT"` — this passes vacuously if sig is None on breakdown bar. The invariant is only half-tested. A breakdown close < donchian_low WHILE FLAT should return None, not a signal. The assertion should be `assert sig is None`.

**How to apply:** if Donchian is revisited, fix this weak assertion first (it's a latent bug in the test, not the code).
