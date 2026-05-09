---
name: Project test patterns
description: Observed patterns across sprints — fixtures, timeframes, property tests, naming
type: project
---

# Project Test Patterns

## Timeframe parametrization (S27 T1 lesson)
- `bars_per_year` values: 8760 (1H), 2190 (4H), 365 (1D), 35040 (15M), 17520 (30M)
- ANY formula involving `bars_per_year` must be parametrized over these values
- Pattern confirmed: S33 T1 added `test_bars_per_year_integration.py` — 5 tests verifying 4H vs 1H ratio = sqrt(2190/8760)=0.5
- Use `@pytest.mark.parametrize("bars_per_year", [8760, 2190, 35040])` for timeframe-sensitive tests

## Clock injection pattern (S37 T4, ADR 0057 SD-5)
- `RuntimeManager.__init__` accepts `clock: Callable[[], datetime] = lambda: datetime.now(UTC)`
- Test pattern: `rm, _ = _runtime(tmp_path, clock=lambda: fixed_now)`
- Then seed `state_repo.set_signed(...)` with activation matching injected time
- `coord.request_halt.assert_called_once_with(ReasonCode.X)` verifies halt trigger
- Mirrors `RiskManager.__init__(clock=...)` S8a precedent

## HMAC integrity test pattern (S37 T3, ADR 0057 SD-4 / ADR 0018 H2)
- Round-trip: `set_signed → get_signed → assert payload ==`
- Tamper: `set(key, {payload: ..., sig: "0"*64})` → `get_signed` raises `ValueError("HMAC")`
- Missing envelope: `set(key, {"value": "raw"})` → `get_signed` raises `ValueError("HMAC envelope")`
- Wrong key: different HMAC key → `ValueError("HMAC")`
- Always 6 cases: round-trip + persist-check + missing-key + tamper + missing-envelope + wrong-key

## Symbol whitelist test pattern (S37 T2)
- 8 test cases: default whitelist content + unknown symbol halts + None symbol halts + whitelisted proceeds + custom whitelist + demo_inactive skip + case normalize + lowercase-input-uppercase-symbol
- `trading-logic-reviewer C2` explicitly required: s35_demo_active=False bypasses whitelist
- `security-auditor HIGH`: lowercase normalization

## DSR boundary parametrize pattern (S37 T6)
- Test n=9 (below threshold) → UNDERPOWERED/NaN
- Test n=10 (at boundary) → normal calculation 
- Test n=29 (just below 30)
- Test n=30 (at 30 boundary)
- `@pytest.mark.parametrize("n,expected_status", [(9, "UNDERPOWERED"), (10, ".."), (29, ...), (30, ..)])`

## RiskSharedDeps pattern (S38 T4)
- NamedTuple exposes 3 fields: equity_tracker + trade_repo + state_repo
- `RiskManager.shared_deps` property returns bundle
- `RuntimeManager` accepts BOTH `shared_deps=RiskSharedDeps(...)` AND individual kwargs (backward-compat)
- Test must verify: bundle path works + individual kwarg path works + neither path raises ValueError

## pnl_pct vs pnl_quote Sharpe test (S38 T2 F2)
- Key invariant: trades with identical pnl_pct but different pnl_quote (varying position size) → SAME Sharpe
- Test: `assert sharpe_small == pytest.approx(sharpe_large, abs=1e-9)`
- Also: constant pnl_pct → DEGENERATE_VARIANCE status
- Also: n<30 → UNDERPOWERED status (regardless of Sharpe sign)

## Fixture factory pattern (S37-38 tests)
- All S37-38 test files use `_settings(tmp_path, **overrides)` + `_runtime(tmp_path, **kwargs)` factory helpers
- `init_db(settings.db_path, _MIGRATIONS)` in every integration-level test fixture
- `coord = MagicMock(); coord.symbol = "BTCUSDT"` — coordinator mock pattern
- `coord.request_halt.assert_called_once_with(ReasonCode.X)` — halt assertion pattern

## ReasonCode coverage test
- `test_risk_models.py` maintains exhaustive list of all ReasonCode string values
- Any new ReasonCode (e.g. HALT_UNKNOWN_SYMBOL in S37) must appear in this test
- Pattern: `assert "HALT_UNKNOWN_SYMBOL" in {r.value for r in ReasonCode}`
