---
name: s37-haltgate-unknown-symbol
description: S37 T2 HALT_UNKNOWN_SYMBOL fail-closed pattern + case-normalization HIGH + config_hash carry
type: project
---

S37 T2 (commit 654ef66) closes pre-S37 #1+#2 (S36 fail-skip vulnerability + HALT_UNKNOWN_SYMBOL distinct ReasonCode).

**Pattern (fail-closed symbol whitelist):**
- `_check_halt_gate` (manager.py:172-187) — whitelist check FIRST (BEFORE activation_ts side-effects).
- `s35_demo_active=False` short-circuit untouched (whitelist not consulted on inactive demo).
- `_stopping=True` + `request_halt(HALT_UNKNOWN_SYMBOL)` — terminal exit, operator restart required.
- HALT_UNKNOWN_SYMBOL=50 в reason_codes.py:108 — distinct code (NOT reuse) per audit-log attribution.
- Property test `tests/property/test_request_halt_mapping.py:42` asserts FSM dispatch — generic `request_halt` accepts new code without code change.

**HIGH carry (NOT fixed in T2):**
- `s35_demo_approved_symbols` accepts `list[str]` без BeforeValidator normalization (config.py:134-143). Operator setting `S35_DEMO_APPROVED_SYMBOLS=["btcusdt"]` → permanent halt loop (DoS, not money loss). Fix: `@field_validator(mode="before")` returning `[s.strip().upper() for s in v]`.
- Symbol whitelist NOT в `_HASH_ALLOWLIST` (config.py:22-42). HMAC override cannot lift HALT_UNKNOWN_SYMBOL anyway (Literal["L2","L3","FLASH"] rejects S37 code), so defense-in-depth not exploit.
- `_symbol` private attr access (manager.py:178) carry-over к T5 (coordinator.symbol public property).

**Verified clean (BLOCKER-free):**
- Banner emits NO secrets (manager.py:107-117) — thresholds + symbols + fail_closed flag only.
- `validate_assignment=True` prevents runtime whitelist mutation bypass (re-triggers validators).
- `min_length=1` blocks `S35_DEMO_APPROVED_SYMBOLS=[]`. Empty string env → `[""]` parses but fails comparison → halt fires (fail-closed).
- Audit log `error` level (visibility), `symbol`+`whitelist` clean (no PII / secrets).

**Pattern (для future fail-closed checks):**
- Order: precondition check FIRST → state-mutating side-effects (activation_ts persist) AFTER. Reverse = corrupted state on misconfigured boot.
- Distinct ReasonCode > reuse — audit attribution критична для post-incident analysis.
- Generic `request_halt` dispatch (RISK_HALT event) — new halt code не требует FSM event addition, только enum + property test allowlist.
