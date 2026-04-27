---
title: ADR 0057 — Sprint 37 Carry-overs Hardening (Security HIGH + Trading-logic + Quant + Playbook)
type: decision
tags: [adr, sprint-37, carry-overs-hardening, halt-unknown-symbol, symbol-whitelist, hmac-integrity, clock-injection, calibration-amendment]
created: 2026-04-27
updated: 2026-04-27
status: accepted
sources:
  - project/decisions/0055-sprint-36-delta-activation.md
  - project/decisions/0056-sprint-36-dsr-sigma-sr-amendment.md
  - project/decisions/0018-config-hash-and-override.md
  - project/pre-s37-backlog.md
---

# ADR 0057 — Sprint 37 Carry-overs Hardening

## Status

Accepted (2026-04-27) — implemented в S37 (`feature/sprint-37-carry-overs-hardening` → tag `v0.1.0-alpha.37`). Paired ADR 0056 amendment (calibration baseline + Sharpe semantics, same sprint).

## Context

Post-S36 ROUND 5 consilium (3 agents — trader-expert + trading-logic-reviewer + quant-stats-reviewer) CONSENSUS on (c) S37 carry-overs sprint first, then (a) δ TESTNET activate в S38. δ infrastructure WIRED LIVE в S36 но 10 carry-overs persisted в pre-s37-backlog.md. 6 critical items selected для S37, 4 deferred к S38+.

ROUND 5 EXPANDED maintainer's original 6-item subset:
- HALT_UNKNOWN_SYMBOL distinct ReasonCode mandatory (NOT reuse existing) per audit-log attribution rule
- Calibration baseline amendment (S22 6.17 → 2.96 mean fold conservative)
- ADR 0056 amendment для Sharpe computation semantics

## Decision (6 sub-decisions)

### SD-1 — HALT_UNKNOWN_SYMBOL distinct ReasonCode

NEW ReasonCode `HALT_UNKNOWN_SYMBOL` (canonical 49 → **50**). Distinct from existing HALT_S36_* codes preserves halt_log audit attribution per γ primary-wins rule.

Rationale (trading-logic-reviewer ROUND 5): reusing HALT_S36_CONSECUTIVE_LOSSES для symbol-resolution failure would mean halt_log permanently records "consecutive losses" when actual root cause was "unknown symbol." Destroys post-mortem attribution.

Property test allowlist (`tests/property/test_request_halt_mapping.py`) extended +1 entry. Canonical count sync 49 → 50 в `current-state.md` + `reason-codes-schema.md` + `execution-state-machine.md` footer + `.github/workflows/ci.yml`.

### SD-2 — Symbol fail-closed semantic

`RuntimeManager._check_halt_gate()` semantic change:

**Pre-S37**: unknown/missing symbol → `logger.warning("runtime.halt_gate_skipped_no_symbol")` + return False (HaltGate inactive — silent bypass).

**Post-S37**: unknown/missing symbol → `logger.error("runtime.halt_gate_unknown_symbol")` + `coordinator.request_halt(HALT_UNKNOWN_SYMBOL)` + `_stopping=True` + return True (fail-closed halt).

Rationale: operator typo в env var → silent skip = HaltGate inactive = bot trades без safety net. Fail-closed prevents production bot running без HaltGate enforcement.

### SD-3 — Symbol whitelist Setting + startup banner

NEW Setting `s35_demo_approved_symbols: list[str]` (default `["BTCUSDT"]` per pre-s35-backlog single-symbol LOCKED).

`_check_halt_gate()` validates: `if symbol not in self._settings.s35_demo_approved_symbols → HALT_UNKNOWN_SYMBOL`.

Startup banner на `RuntimeManager.run()` после `coordinator.bootstrap()` displays (когда `s35_demo_active=True`):
- approved_symbols list
- halt thresholds (4 triggers + values)
- fail_closed=True flag

Operator-visible audit at boot.

### SD-4 — activation_ts HMAC integrity

`StateRepository` extended с `set_signed()` + `get_signed()` methods per ADR 0018 HMAC pattern. Reuses `risk_override_hmac_key` (separate от API secret per ADR 0018 H2).

Envelope format: `{"payload": <value>, "sig": <HMAC-SHA256 hex>}`.

`_check_halt_gate()` reads activation_ts через `get_signed()` — raises ValueError на signature mismatch. Halt path: tampered value → HALT_UNKNOWN_SYMBOL halt + bot exit (operator review required).

### SD-5 — Clock injection в `_check_halt_gate`

`RuntimeManager.__init__` constructor kwarg: `clock: Callable[[], datetime] = lambda: datetime.now(UTC)`.

Replace direct `datetime.now(UTC)` calls в `_check_halt_gate()` с `self._clock()`. Enables deterministic property tests + future replay scenarios.

Pattern matches S8a `RiskManager.__init__(clock=...)` precedent.

### SD-6 — coordinator.symbol public property

`Coordinator` exposes:
```python
@property
def symbol(self) -> str:
    return self._symbol
```

`RuntimeManager._check_halt_gate()` replaces `getattr(self._coordinator, "_symbol", None)` private leak с `self._coordinator.symbol`.

Cleans Demeter violation. Public API stable contract per ADR 0019.

## Consequences

### Positive
- Symbol fail-closed = production-ready halt path (no silent bypass)
- HMAC integrity = activation_ts tamper-detection (no rollback attack)
- Clock injection = deterministic property tests (testability unlock)
- coordinator.symbol property = clean public API (no private access)
- HALT_UNKNOWN_SYMBOL audit attribution preserved
- δ activate post-S37 = production-readiness discipline + operator confidence

### Negative
- Time cost ~8-10h (delays δ data accumulation by ~2-4 weeks)
- HMAC verification overhead per `_check_halt_gate` call (negligible — sub-millisecond)
- ReasonCode count growth (49 → 50) = future canonical sync overhead

### Neutral
- No FSM state/event/transition changes (canonical 16/30/74 unchanged, only reason codes 49→50)
- ADR 0055 SD-* preserved unchanged
- δ activation operator action unchanged (set env var + restart) per playbook T7

## Implementation

Per S37 plan (`plans/2026-04-27-sprint-37-carry-overs-hardening.md`):
- T1 (this commit): ADR 0057 + ADR 0056 amendment paired
- T2: Security #1+#2 — symbol whitelist + fail-closed + HALT_UNKNOWN_SYMBOL
- T3: Security #3 — activation_ts HMAC integrity
- T4: Trading-logic #4 — clock injection
- T5: Trading-logic #5 — coordinator.symbol property
- T6: Quant #8 — DSR boundary tests + S22 baseline 6.17→2.96
- T7: Operator playbook page
- T8: Wiki sync + counts + ship

## Follow-ups

**Operator action когда S37 ships:**
1. Review ADR 0057 + ADR 0056 amendment + delta-activation-playbook.md
2. Set `S35_DEMO_ACTIVE=true` в production .env (per playbook step 1)
3. Restart bot — first tick records activation_ts (HMAC-signed)
4. Monitor halt_log + trade_history per playbook procedure

## Related

- ADR 0050 (S33 Trading Restart)
- ADR 0051 (S34 6-th honest close v0.6)
- ADR 0052 (S34 acceptance-criteria amendment LOCKED)
- ADR 0053 (S35 δ TESTNET pre-activation infrastructure)
- ADR 0055 (S36 δ activation — predecessor)
- ADR 0056 (S36 DSR sigma_SR amendment + S37 amendment paired)
- ADR 0018 (config_hash + HMAC override pattern — SD-4 source)
- ADR 0019 (coordinator design — SD-6 source)
- ADR 0022 (RuntimeManager lifecycle — SD-5 clock pattern)
- pre-s37-backlog.md ROUND 5 consilium trail
- delta-activation-playbook.md (T7 operator procedure)
