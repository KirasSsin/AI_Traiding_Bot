---
name: override-store-hmac-controls
description: override.py controls verified clean — HMAC compare_digest, atomic write, fail-closed reads
type: project
---

**Verified controls (S35 T2 review):**
- HMAC-SHA256 with `hmac.compare_digest` (override.py:124) — timing-safe.
- `min_length=32` enforced on hmac_key both в Settings.risk_override_hmac_key (config.py:165) AND OverrideStore.__init__ (override.py:56) — defence in depth.
- File mode 0o600, parent 0o700 (override.py:67, 85). Atomic via os.replace (line 91).
- Fail-closed на all error paths (read_active returns None on JSON error, sig mismatch, hash mismatch, expiry).
- config_hash binding prevents replay across config changes (line 134).

**Caveat:** `_HASH_ALLOWLIST` (config.py:22-37) does NOT include s35_demo_active / live_trading / testnet. Override survival across testnet-flip is intentional (only risk thresholds bind override) but worth re-confirming if S35+ adds operator-managed mode toggles.

**Anti-pattern observed (none in this code):** writing override file без atomic temp+rename → partial-write tampering window.
