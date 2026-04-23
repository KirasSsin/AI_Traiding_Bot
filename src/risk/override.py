"""Manual circuit-breaker override — file-backed store."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

OverrideLevel = Literal["L2", "L3", "FLASH"]


class CbOverride(BaseModel):
    """Manual circuit-breaker override record."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    level: OverrideLevel
    reason: str = Field(..., min_length=1, max_length=500)
    config_hash: str = Field(..., min_length=64, max_length=64)  # SHA-256 hex
    created_at: AwareDatetime
    expires_at: AwareDatetime


class OverrideStore:
    """File-backed override store. JSON at `path`; consumed → renamed to `<path>.consumed.json`."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def write(self, *, override: CbOverride) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(override.model_dump_json(indent=2), encoding="utf-8")

    def read_active(self, *, now: AwareDatetime, expected_config_hash: str) -> CbOverride | None:
        """Return override if file exists, hash matches, and not expired. Else None.

        Mismatched hash → log warning + return None (do NOT raise).
        Expired → return None (caller may consume to rotate).
        """
        if not self._path.exists():
            return None
        try:
            override = CbOverride.model_validate_json(self._path.read_text(encoding="utf-8"))
        except Exception:
            return None
        if override.config_hash != expected_config_hash:
            return None
        if now >= override.expires_at:
            return None
        return override

    def consume(self, *, override: CbOverride) -> None:  # noqa: ARG002 — API kwarg kept for caller clarity
        """Move active file to <path-stem>.consumed.<ts>.json."""
        if not self._path.exists():
            return
        consumed = self._path.with_name(
            f"{self._path.stem}.consumed.{int(datetime.now(UTC).timestamp())}.json"
        )
        self._path.rename(consumed)
