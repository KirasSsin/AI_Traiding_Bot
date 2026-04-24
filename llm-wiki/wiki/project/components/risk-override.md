---
title: Risk override — manual CB resume gate (HMAC-signed file + config_hash anti-replay)
type: component
tags: [risk, override, security, hmac, atomic-write, sprint-4, sprint-7, adr-0018]
created: 2026-04-25
updated: 2026-04-25
status: stable
sources:
  - src/risk/override.py
  - src/risk/resume_cb.py
  - wiki/project/decisions/0018-sprint-4-risk-decisions.md
---

# Risk override — manual CB resume gate

**TL;DR:** Operator writes an HMAC-SHA256-signed JSON file binding a specific config snapshot — RiskManager validates it on every `assess()` call to allow single-use manual CB resume at L2/L3/FLASH.

## Definition / Purpose

When a circuit breaker fires (L1 warns + half-sizes; L2 halts for 24h; L3 halts fully; FLASH halts on intrabar drop — per ADR 0013), trading is suspended. The system cannot resume automatically: an operator must take explicit action. That action is writing a `CbOverride` file to a path configured in `Settings.risk_override_path`.

The override mechanism enforces three independent security invariants before allowing resume: (1) HMAC-SHA256 signature proving the file was written by someone holding `Settings.risk_override_hmac_key`, (2) `config_hash` binding the override to the exact risk-threshold snapshot active when it was issued — drift in any risk setting invalidates the override without key rotation, and (3) expiry — `expires_at` bounds the bypass window. After a successful match in `RiskManager.assess()`, the file is immediately **consumed** (renamed to `.consumed.<ts>.json`) — the override is single-use (ADR 0018 sub-decision 9d, CWE-672).

Override applies to levels **L2, L3, FLASH** only. L1 is a warn+size-reduction state, not a halt — no override needed.

## Public API

```python
OverrideLevel = Literal["L2", "L3", "FLASH"]

class CbOverride(BaseModel):
    """Manual circuit-breaker override record. Frozen + extra=forbid."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    level: OverrideLevel
    reason: str = Field(..., min_length=1, max_length=500)
    config_hash: str = Field(..., min_length=64, max_length=64)  # SHA-256 hex
    created_at: AwareDatetime
    expires_at: AwareDatetime


class OverrideStore:
    def __init__(self, path: Path, *, hmac_key: str) -> None: ...
    # hmac_key must be >= 32 chars; raises ValueError otherwise

    def write(self, *, override: CbOverride) -> None: ...
    # Atomic: mkdir 0o700 → sign → os.open 0o600 → fsync → os.replace

    def read_active(
        self, *, now: AwareDatetime, expected_config_hash: str
    ) -> CbOverride | None: ...
    # Fail-closed: any error/mismatch → None (+ WARNING log on HMAC mismatch)

    def consume(self, *, override: CbOverride) -> None: ...
    # Rename active file → <stem>.consumed.<unix-ts>.json (audit trail)
```

Note: the public method is `read_active()` (not `read()` + `is_active()`). Both validity checks — HMAC + config_hash + expiry — are performed inside a single call.

## File format (JSON envelope)

On-disk layout (`risk_override.json`):

```json
{
  "payload": {
    "level": "L2",
    "reason": "operator-investigated, manual approval",
    "config_hash": "<sha256-hex-64-chars>",
    "created_at": "2026-04-25T10:00:00+00:00",
    "expires_at": "2026-04-26T10:00:00+00:00"
  },
  "sig": "<hmac-sha256-hex>"
}
```

Path: `Settings.risk_override_path` (required env var, no default).

The outer envelope `{"payload": ..., "sig": ...}` is what lives on disk. `sig` is **not** inside `payload` — the signature body is the canonical (`sort_keys=True`, `separators=(",",":")`) JSON bytes of `payload` only.

## HMAC signing semantics

- **Key:** `Settings.risk_override_hmac_key` — separate from Bybit API secret (allows API key rotation without invalidating active overrides, and vice versa). Minimum length 32 chars enforced in `OverrideStore.__init__`.
- **Algorithm:** `hmac.new(key.encode("utf-8"), canonical_payload, hashlib.sha256).hexdigest()`
- **Body:** canonical JSON of `payload` dict (`sort_keys=True, separators=(",",":")`) — stable across pydantic field-order changes.
- **Verification:** `hmac.compare_digest(sig_provided, sig_expected)` — constant-time, prevents timing attacks (CWE-345/CWE-306, ADR 0018 sub-decision 9c).
- **Fail-closed:** missing sig / wrong key / tampered payload / malformed JSON → `read_active()` returns `None` and logs `WARNING "override HMAC mismatch — possible tampering at <path>"`.

## Atomic write pattern

```python
# src/risk/override.py:82-95
tmp = self._path.with_suffix(self._path.suffix + ".tmp")
flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
fd = os.open(tmp, flags, 0o600)
try:
    with os.fdopen(fd, "wb") as f:
        f.write(envelope)
        f.flush()
        os.fsync(f.fileno())   # durability: security-critical override
    os.replace(tmp, self._path)
finally:
    if tmp.exists():
        tmp.unlink(missing_ok=True)
```

`os.replace` is an atomic rename on POSIX — a concurrent reader never sees a partial file (CWE-367 TOCTOU, ADR 0018 sub-decision 9f). The `.tmp` cleanup in `finally` runs only if `write` raised before `os.replace`.

**Difference from kill-switch atomic write (S8b T4):** `src/__main__.py` kill sentinel uses the same `os.open + os.replace` pattern but **omits `fsync`** (paper-trade scope; durability not required). `override.py` keeps `fsync` because a lost override on power failure forces re-issue — a security event.

## config_hash anti-replay

`config_hash` = SHA-256 of **12 risk-threshold fields only** (allowlist `_HASH_ALLOWLIST` in `src/platform/config.py`): the CB thresholds, ATR multipliers, Kelly caps. Excluded: API secret, HMAC key, log paths, observability config (ADR 0018 sub-decision 9b, CWE-532).

Consequence: rotating `BYBIT_API_SECRET` does **not** invalidate active overrides. Changing any risk threshold (e.g. `risk_cb_l2_dd`) **does** invalidate — forces operator re-issue after config drift. This is intentional: an override issued under different thresholds should not carry over.

`read_active()` checks `override.config_hash != expected_config_hash` before returning — mismatch → `None` (no log; silent fail-closed is correct because config drift is not tampering).

## CLI integration (`src/risk/resume_cb.py`)

```bash
python -m src.risk.resume_cb \
  --level L2 \
  --reason "manually investigated, no open positions" \
  --expires-in 4h
```

Duration format: `NNh` | `NNm` | `NNd` (default `1h`). CLI computes `settings.config_hash()` at write time, builds `CbOverride`, delegates to `OverrideStore.write()`.

Stdout prints `level` + `expires_at` only — **not** the file path (CWE-532, ADR 0018 sub-decision 9h, L3 audit finding).

## Security invariants (ADR 0018 sub-decision 9, post-merge security audit)

| CWE | Invariant | Enforcement | Test |
|-----|-----------|-------------|------|
| CWE-345/306 | HMAC-SHA256 envelope; verify via `hmac.compare_digest` | `OverrideStore.read_active` | `test_read_with_tampered_signature_returns_none`, `test_read_with_wrong_hmac_key_returns_none`, `test_read_with_tampered_payload_returns_none` |
| CWE-672 | Single-use: `consume()` called before sizing in `RiskManager.assess()` | `src/risk/manager.py::assess` | `test_override_is_consumed_after_bypass` |
| CWE-276 | File mode 0o600; parent dir 0o700 | `os.open(tmp, flags, 0o600)` + `mkdir(mode=0o700)` | `test_write_file_mode_is_0o600`, `test_write_parent_dir_mode_is_0o700` |
| CWE-367 | Atomic write via `os.replace` (no partial file readable) | `os.replace(tmp, path)` + `finally` cleanup | `test_write_does_not_leave_tmp_file`, `test_write_overwrite_is_atomic` |
| CWE-532 | `config_hash()` excludes creds, paths, observability config | `_HASH_ALLOWLIST` frozenset in `src/platform/config.py` | `test_config_hash_excludes_bybit_secret`, `test_config_hash_excludes_hmac_key` |
| CWE-798 | `risk_override_hmac_key` has no committed default; `min_length=32` enforced | `Settings` field definition | `test_missing_hmac_key_raises`, `test_short_hmac_key_raises` |

**No env-flag bypass:** `RiskManager.assess()` always calls `override_store.read_active()` when halt level is L2+. There is no debug/test env variable that skips this path.

## Related

- [[risk-manager]] — consumer: calls `read_active()` on every `assess()` call at L2+; calls `consume()` before sizing on match
- [[circuit-breakers]] — L1/L2/L3/flash detector; override enables manual resume from L2/L3/FLASH
- [[kill-switch-cli]] — same `os.open + os.replace` atomic write pattern (S8b T4 mirror); omits `fsync` per paper-trade scope
- [[config]] — `Settings.risk_override_path` + `Settings.risk_override_hmac_key` + `Settings.config_hash()` + `_HASH_ALLOWLIST`
- [[../decisions/0018-sprint-4-risk-decisions]] — sub-decision 9 (full security audit: C1/H1/H2/H3/M1/M2/L3)

## Open questions

- **Key rotation procedure** — rotating `risk_override_hmac_key` invalidates all active overrides; ops runbook not yet written (deferred v0.2, noted in ADR 0018 consequences).
- **Multi-operator approval** — today single HMAC key = single trust anchor; quorum / dual-control override workflow deferred v0.2+.

## Sources

- `src/risk/override.py` (147 LoC) — `CbOverride` model + `OverrideStore` (write/read_active/consume)
- `src/risk/resume_cb.py` — CLI consumer (argparse + duration parser + Settings integration)
- `wiki/project/decisions/0018-sprint-4-risk-decisions.md` sub-decision 9 — full security audit (C1/H1/H2/H3/M1/M2/I1/L3)
