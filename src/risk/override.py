"""Manual circuit-breaker override — file-backed, HMAC-signed store.

Security (ADR 0018 sub-decision 9 — Sprint 4 audit):
    H2 (CWE-345/306): Override file is HMAC-SHA256 signed with a key loaded
        from `Settings.risk_override_hmac_key` (separate from API secret).
        Mismatched signature → fail-closed (return None, log warning).
    M1 (CWE-276): File written with mode 0o600; parent dir created 0o700.
    M2 (CWE-367): Write is atomic via temp file + os.replace.
"""

import hashlib
import hmac
import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

OverrideLevel = Literal["L2", "L3", "FLASH"]


class CbOverride(BaseModel):
    """Manual circuit-breaker override record."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    level: OverrideLevel
    reason: str = Field(..., min_length=1, max_length=500)
    config_hash: str = Field(..., min_length=64, max_length=64)  # SHA-256 hex
    created_at: AwareDatetime
    expires_at: AwareDatetime


def _sign(payload: bytes, key: str) -> str:
    """HMAC-SHA256 hex digest of payload bytes with key."""
    return hmac.new(key.encode("utf-8"), payload, hashlib.sha256).hexdigest()


class OverrideStore:
    """File-backed override store with HMAC integrity check.

    On-disk format::

        {"payload": <CbOverride JSON>, "sig": <HMAC-SHA256 hex>}

    The signature is computed over the canonical (sort_keys=True) JSON
    bytes of the payload. Read path verifies via :func:`hmac.compare_digest`.
    """

    def __init__(self, path: Path, *, hmac_key: str) -> None:
        if len(hmac_key) < 32:
            raise ValueError("hmac_key must be at least 32 chars (audit H2)")
        self._path = path
        self._key = hmac_key

    def write(self, *, override: CbOverride) -> None:
        """Atomically write signed override.

        Steps: mkdir parent 0o700 → serialize payload → sign → write tmp
        with mode 0o600 → os.replace (atomic rename).
        """
        self._path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        payload_bytes = override.model_dump_json().encode("utf-8")
        # Canonical form for signing: parse-then-dumps with sort_keys so the
        # signature is stable across pydantic field-order changes.
        canonical = json.dumps(
            json.loads(payload_bytes), sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        sig = _sign(canonical, self._key)
        envelope = json.dumps(
            {"payload": override.model_dump(mode="json"), "sig": sig},
            sort_keys=True,
            indent=2,
            default=str,
        ).encode("utf-8")

        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        # O_EXCL prevents racing with another writer leaving a stale tmp.
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        fd = os.open(tmp, flags, 0o600)
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(envelope)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self._path)
        finally:
            # tmp file is gone after replace; only matters if write raised.
            if tmp.exists():
                tmp.unlink(missing_ok=True)

    def read_active(
        self, *, now: AwareDatetime, expected_config_hash: str
    ) -> CbOverride | None:
        """Return override if file exists, signature valid, hash matches, not expired.

        Failure modes (all return None):
            - file missing
            - JSON malformed / envelope shape wrong
            - HMAC signature mismatch (logs WARNING — possible tampering)
            - config_hash mismatch
            - expired (now >= expires_at)
        """
        if not self._path.exists():
            return None
        try:
            envelope = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(envelope, dict) or "payload" not in envelope or "sig" not in envelope:
            return None

        payload = envelope["payload"]
        sig_provided = envelope["sig"]
        canonical = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), default=str
        ).encode("utf-8")
        sig_expected = _sign(canonical, self._key)
        if not hmac.compare_digest(sig_provided, sig_expected):
            logger.warning(
                "override HMAC mismatch — possible tampering at %s", self._path
            )
            return None

        try:
            override = CbOverride.model_validate(payload)
        except Exception:
            return None
        if override.config_hash != expected_config_hash:
            return None
        if now >= override.expires_at:
            return None
        return override

    def consume(self, *, override: CbOverride) -> None:  # noqa: ARG002 — kwarg kept for caller clarity
        """Move active file to <path-stem>.consumed.<ts>.json."""
        if not self._path.exists():
            return
        consumed = self._path.with_name(
            f"{self._path.stem}.consumed.{int(datetime.now(UTC).timestamp())}.json"
        )
        self._path.rename(consumed)
