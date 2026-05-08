---
name: s36-haltgate-wireup-controls
description: S36 T4 HaltGate wire-up — verified controls + symbol fail-skip + activation_ts integrity gap
type: project
---

S36 T4 wires HaltGate (previously dead code) к RuntimeManager._tick under `if settings.s35_demo_active:`.
Halt path: HaltGate.evaluate → trigger → `_HALT_TRIGGER_TO_REASON[trigger]` → coordinator.request_halt + _stopping=True.

**Verified clean (BLOCKER-free):**
- HMAC override CANNOT lift HALT_S36_* — OverrideLevel = Literal["L2","L3","FLASH"] (override.py:24); pydantic validation rejects S36 reasons.
- `_HASH_ALLOWLIST` includes 4 `s35_halt_*` keys (config.py:36-40) — operator threshold change invalidates active overrides per config_hash binding.
- `validate_assignment=True` (config.py:57) prevents runtime `settings.s35_demo_active = X` bypass — model_validator re-runs.
- `_stopping=True` forces operator restart, no auto-resume.

**HIGH issues (track для T6+ или next sprint):**
- Symbol resolution fail-SKIP pattern (`if symbol is None: return False` at manager.py:169) — HaltGate silently disabled if `Coordinator._symbol` becomes None. Should be fail-CLOSED (request_halt(HALT_RUNTIME_CRASH)) для money-path. Same anti-pattern at manager.py:273-275 для `_poll_bar_and_strategy` (which IS conditional fail-safe — no symbol = no trading either).
- `s35:activation_ts` stored в StateRepository unsigned. Operator с DB write access can reset multiday DD HWM window via UPDATE на state row. Trust model: "operator с DB ≈ root" — accepted-risk MEDIUM. Future hardening: sign с same HMAC key as override.py OR store in 0o400 file.
- `datetime.fromisoformat(activation_record["value"])` raises на garbage → bubbles к RuntimeManager.run() top-level → HALT_RUNTIME_CRASH + re-raise. Acceptable fail-safe (bot exits) but defensive try/except + halt-with-specific-reason cleaner.

**Pattern (для future halt-gate wire-ups):**
- HaltGate inputs (intraday_dd, multiday_dd, consec, months_since) all derived от authenticated SQLite state — no untrusted-input attack surface.
- Logging clean: financial metrics OK to log, no secret interpolation.
- DI via @property (RiskManager exposes equity_tracker/trade_repo/state_repo) — properties не read-only enforced (Python allows `rm._equity = X`); name-mangling __ alternative для defense-in-depth.

**Test debt:** add negative test "OverrideStore cannot lift HALT_S36_*" to lock invariant.
