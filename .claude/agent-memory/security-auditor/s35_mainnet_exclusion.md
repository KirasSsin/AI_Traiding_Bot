---
name: s35-mainnet-exclusion-invariant
description: S35 δ TESTNET-only invariant — pydantic model_validator pattern + known bypass paths
type: project
---

S35 δ pre-commit #1 (pre-s35-backlog ROUND 3 LOCKED): demo MUST stay TESTNET. Any path leading к live_trading=True + s35_demo_active=True = real capital risk.

**Why:** Operator pre-committed before any data — methodology integrity binds к no-MAINNET-without-12mo-evidence.

**How to apply:**
- `_validate_s35_demo_mainnet_exclusion` (config.py:218) covers Settings construction. Sufficient if Settings is constructed once at startup and never mutated.
- pydantic v2 BaseSettings is mutable by default (no `frozen=True` в model_config). Direct attribute mutation (`settings.live_trading = True`) BYPASSES model_validator. Recommend ConfigDict(frozen=True) OR audit all `settings.X =` writes.
- Validator does NOT cover: testnet=False + live_trading=False + s35_demo_active=True. This is "MAINNET-adjacent" (real-money creds loaded but not actively trading) — not a direct bypass but worth flagging if Bybit adapter routes by `testnet` flag rather than `live_trading`.
- Override store (override.py) binds к config_hash() over `_HASH_ALLOWLIST` — does NOT include `s35_demo_active` OR `live_trading` OR `testnet`. Operator override will NOT be invalidated если s35_demo_active flipped. Acceptable: override only bypasses CB levels, not testnet-routing.
