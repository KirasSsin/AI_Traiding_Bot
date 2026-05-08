---
name: HaltGate S35 — sprint-temporal prefix + allowlist extension pattern
description: Patterns observed in S35 T2 HaltGate introduction; sprint-scoped fields + config_hash allowlist discipline
type: project
---

Sprint-temporal field prefix `s35_*` is acceptable for demo-scoped Settings fields. Signals intent to promote (rename to `risk_halt_*`) or remove post-demo. Precedent established S35.

**Why:** Distinguishes permanent risk thresholds (semantic prefix `risk_*`) from sprint-bounded demo parameters. Prevents premature promotion of demo-only config into permanent API surface.

**How to apply:** When reviewing new Settings fields — if they are sprint/phase-bounded, sprint prefix is a positive signal. If they persist beyond the sprint without rename, flag as tech debt.

---

`_HASH_ALLOWLIST` in `src/platform/config.py` MUST be extended atomically when new risk-decision fields are added to Settings.

**Why:** Omission breaks the override anti-replay invariant (ADR 0018 H1). An operator who changes a halt threshold mid-demo and then issues a CB override would see it accepted with a stale config hash. Found in S35 T2: 4 new `s35_halt_*` fields not added to allowlist.

**How to apply:** Any PR that adds fields influencing halt/sizing decisions → check allowlist extension. Feature flags (`s35_demo_active`, booleans) are excluded from allowlist (not risk thresholds). The pattern: risk threshold fields IN, feature flags OUT.

---

HaltGate vs CircuitBreakerDetector distinction: orthogonal concerns, correct decoupling.
- CircuitBreakerDetector: price-action halt criteria (equity HWM + bar data → L1/L2/L3/Flash)
- HaltGate: session-behavioral halt criteria (DD bounds, loss streaks, trade frequency)
No inheritance needed. Composition at RiskManager level is canonical pattern.

---

State source of truth for HaltGate inputs must be documented before wire-up:
- intraday_dd / multiday_dd: EquityTracker.peak_equity_24h() → (peak - current) / peak
- consecutive_losses: new query or in-memory counter in RiskManager (TradeHistoryRepository has no streak query)
- months_since_last_trade: new query for last closed trade timestamp
All producers owned by Risk bounded context — never pull from Execution or MarketData.
