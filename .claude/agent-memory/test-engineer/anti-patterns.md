---
name: Anti-patterns flagged
description: Naming/structure anti-patterns seen in reviews across sprints
type: project
---

# Anti-patterns Flagged in Reviews

## Naming anti-patterns
- `test_function_works()` — too vague. Use `test_<function>_<scenario>` e.g. `test_check_halt_gate_unknown_symbol_halts`
- `test_method_1()` / `test_calc()` — no scenario description, impossible to understand failure
- Example good names from S37-38: `test_unknown_symbol_fails_closed_with_halt`, `test_get_signed_raises_on_tampered_payload`, `test_sharpe_uses_pnl_pct_not_pnl_quote`

## Structure anti-patterns
- Shared setup hiding test differences (over-DRY). S37-38 correct approach: each test file has `_settings()` + `_runtime()` factory with explicit overrides
- Tests without meaningful assertions (only "does not raise"). Every test must have `assert X` or `assert_called_once_with(Y)`
- Mocking everything — S37-38 tests use real SQLite (init_db + connect) for state_repo/trade_repo/equity_tracker, only coordinator/reconciler/ws_consumer as MagicMock
- Test with no docstring explaining WHY — good: `"""ADR 0057 SD-2: unknown symbol → HALT_UNKNOWN_SYMBOL (NOT warn+skip)."""`

## Coverage anti-patterns
- Testing the happy path only — S37 security-auditor flagged missing `s35_demo_active=False bypass` test (C2 gap)
- Boundary tests skipped — S37 T6 explicitly added n=9/10/29/30 parametrized DSR boundary tests
- Property tests not written where invariant exists — MC p-value had no Hypothesis test before S33 T2 (7 tests added)
- Regression test missing after bug fix — S33 T2 CC-D fix added property tests; S38 T2 F2 added 3 specific regression tests

## Integration vs unit balance
- Over-reliance on unit tests — HaltGate unit tests (test_halt_gate.py) exist; S37 clock-injection tests provide integration at RuntimeManager level
- Skipping integration test for refactors — S38 T4 RiskSharedDeps added 5 integration tests: bundle path + individual path + backward-compat + missing-neither raises

## Test isolation
- Using real time in tests for time-sensitive logic (before S37 clock injection) — always inject clock for months_since/activation_ts tests
- Tests that depend on real Bybit API — all tests must use fakes/mocks at boundaries; no network calls in unit tests

## Slow test marking
- Tests using init_db (SQLite in-memory) are fast enough for unit suite (~5ms each)
- Tests with Hypothesis (property tests) may be slow — mark `@pytest.mark.slow` or `@pytest.mark.property`
- Integration tests (real DB, real time) — mark `@pytest.mark.integration`

## S27 lesson (25-sprint regression)
- Bugs survived 25 sprints due weak tests on replay engine (test_replay_long_only fixture only 12 bars — too short for RSI warmup)
- Rule: always verify fixture length ≥ indicator warmup period + 1 signal bar
- RSI warmup at default 14 periods: need ≥ 16 bars for 2 signal bars
