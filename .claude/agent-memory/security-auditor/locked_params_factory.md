---
name: locked-params-factory-pattern
description: S36 T2 LOCKED params factory — defensive copy + symbol-agnostic + audit-log clean
type: project
---

S36 T2 wires `MEAN_REVERSION_S17_RELAXED_PARAMS` (LOCKED dict per ADR 0030 + ADR 0053 + pre-commit #7) к live path via `from_locked_s17_params(symbol)` factory invoked under `if settings.s35_demo_active:` branch.

**Why:** B1 critical — pre-fix would silently run S15-noise params despite LOCKED contract когда δ TESTNET activates. Money-path: parameters determine REAL TRADES под δ.

**How to apply (review patterns):**
- Module-level dict NOT frozen → defensive `dict(MEAN_REVERSION_S17_RELAXED_PARAMS)` OR `copy.deepcopy()` inside factory mandatory (test fixture mutation risk).
- Better: `types.MappingProxyType(MEAN_REVERSION_S17_RELAXED_PARAMS)` makes runtime mutation raise TypeError — closes anti-pattern entirely.
- Factory MUST hardcode params from LOCKED dict — must NOT read Settings/env for any rsi/bb/and_gate value (otherwise env-injection bypasses LOCKED contract).
- `if settings.s35_demo_active:` guard — covered by `validate_assignment=True` + S35 model_validator. Initial misconfig still possible если operator sets s35_demo_active=False unintentionally — orthogonal к factory safety, belongs к startup-banner audit.
- Symbol arg trust: factory accepts arbitrary symbol — δ pre-commit specifies BTCUSDT only. Validate symbol whitelist в caller (RiskManager / runtime entrypoint), not в strategy factory (LOCKED params are strategy-shape, not symbol-shape).
- Audit log `params=dict(...)` clean — strategy thresholds non-secret. Reuse pattern OK for future LOCKED constants.
- `# type: ignore [arg-type]` due `dict[str, object]` — acceptable MVP. Cleaner: `TypedDict` or `@dataclass(frozen=True)` strategy params spec.
