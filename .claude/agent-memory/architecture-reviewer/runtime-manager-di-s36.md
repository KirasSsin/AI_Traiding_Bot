---
name: RuntimeManager DI extension S36 + HaltGate orchestration pattern
description: 10-arg constructor pattern, RiskManager property accessor pattern for DI sharing, HaltGate per-tick orchestration, state_repo namespace convention
type: project
---

**S36 T4 DI pattern (df8edec):**
RuntimeManager now has 10 required kwargs (was 7). Pattern: all keyword-only via `*`.
Constructor helper `_halt_gate_deps()` in tests groups the 3 new MagicMocks — makes future ctor growth 1-line in tests.

**RiskManager property accessor pattern (S36):**
RiskManager exposes `equity_tracker`, `trade_repo`, `state_repo` as `@property` returning private `_equity`, `_trades`, `_state`.
Rationale: avoids duplicate SQLite connection instances (two separate init_db() calls on same file = WAL conflict risk).
This IS a Demeter violation (RuntimeManager reaches into RiskManager's internal repos) but accepted over duplicate connections.
Refactor path (S38+): extract `RiskSharedDeps` dataclass (equity_tracker + trade_repo + state_repo) as first-class DI unit. Pass to both RiskManager and RuntimeManager. Removes property accessor pattern entirely.

**_check_halt_gate() hot-path concern:**
Method issues 3 SQLite reads per tick when s35_demo_active=True:
  - state_repo.get("s35:activation_ts") — once, then cached in activation_ts local
  - equity_tracker.intraday_dd_pct() — in-memory (fast)
  - equity_tracker.hwm_since(since_ts=activation_ts) — SQLite scan of equity_snapshots
  - trade_repo.consecutive_losses(symbol=symbol) — SQLite query
  - trade_repo.last_trade_ts(symbol=symbol) — SQLite query
state_repo.get() is called every tick even after activation_ts is set — redundant read.
Fix: cache activation_ts in instance variable after first successful read (avoid per-tick DB round-trip).

**Namespace key concern — s35: prefix:**
Key "s35:activation_ts" set by src/runtime/manager.py (a Runtime cluster component).
Existing keys: "risk:cb:current_level", "risk:cb:prev_close", "risk:kelly:phase", "risk:kelly:params" — all owned by Risk cluster.
Convention conflict: "s35:" is sprint-prefixed, not domain-prefixed.
Correct domain prefix = "runtime:s36:activation_ts" (Runtime cluster, S36 feature).
Low-impact for v0.1 (single writer, single consumer), but inconsistency will compound as more keys added.

**10-arg constructor threshold:**
At 10 kwargs RuntimeManager is at the "Builder pattern would help" threshold.
For v0.1 single binary: ACCEPTABLE. Constructor is keyword-only (no ordering mistakes possible).
If kwargs exceed 12 OR if multiple call sites emerge → extract RuntimeManagerConfig dataclass.

**_HALT_TRIGGER_TO_REASON module-level constant:**
APPROVED pattern. Static mapping belongs at module scope. HaltGate.evaluate() returns None | HaltTrigger — mapping belongs to dispatch layer (Runtime), not to domain (Risk). Correct separation.

**Test fixture brittleness:**
19 RuntimeManager() call sites in test file. `_halt_gate_deps()` helper correctly groups new mocks — future ctor additions need 1 line in helper. If sites grow beyond 25 → extract `_make_rm(...)` builder fixture. Pre-empt at S38+.

**Why:** Documents accepted Demeter violation (RiskManager properties) + hot-path DB concern + namespace inconsistency for S37+ follow-up.
**How to apply:** Flag per-tick state_repo.get() as MEDIUM concern in any future tick-path review. Flag domain-less namespace keys in state_repo as LOW hygiene. Flag RiskSharedDeps refactor opportunity at S38+.
