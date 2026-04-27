"""JSON KV adapter for the `state` SQLite table."""

import hashlib
import hmac
import json
from datetime import UTC, datetime
from sqlite3 import Connection
from typing import Any


class StateRepository:
    """JSON kv adapter for the existing `state` table.

    Keys for risk:
      - risk:cb:current_level
      - risk:kelly:phase
      - risk:kelly:params
    """

    def __init__(self, conn: Connection) -> None:
        self._conn = conn

    def get(self, key: str) -> dict[str, Any] | None:
        row = self._conn.execute("SELECT value_json FROM state WHERE key = ?", (key,)).fetchone()
        if row is None:
            return None
        result: dict[str, Any] = json.loads(row[0])
        return result

    def set(self, key: str, value: dict[str, Any]) -> None:
        with self._conn:
            self._conn.execute(
                """INSERT INTO state (key, value_json, updated_at)
                   VALUES (?, ?, ?)
                   ON CONFLICT(key) DO UPDATE SET
                     value_json = excluded.value_json,
                     updated_at = excluded.updated_at""",
                (key, json.dumps(value, sort_keys=True), datetime.now(UTC).isoformat()),
            )

    def update_many(self, updates: dict[str, dict[str, Any]]) -> None:
        """Atomic multi-key update (single transaction).

        Used for Kelly+Equity+CB state flush in one tick.
        """
        if not updates:
            return
        ts = datetime.now(UTC).isoformat()
        with self._conn:
            for key, value in updates.items():
                self._conn.execute(
                    """INSERT INTO state (key, value_json, updated_at)
                       VALUES (?, ?, ?)
                       ON CONFLICT(key) DO UPDATE SET
                         value_json = excluded.value_json,
                         updated_at = excluded.updated_at""",
                    (key, json.dumps(value, sort_keys=True), ts),
                )

    def update_many_no_commit(self, updates: dict[str, dict[str, Any]]) -> None:
        """Multi-key update WITHOUT opening a transaction — caller owns commit.

        Used by RiskManager.update_equity to flush equity_snapshot + state
        in one outer ``with conn:`` block.
        """
        if not updates:
            return
        ts = datetime.now(UTC).isoformat()
        for key, value in updates.items():
            self._conn.execute(
                """INSERT INTO state (key, value_json, updated_at)
                   VALUES (?, ?, ?)
                   ON CONFLICT(key) DO UPDATE SET
                     value_json = excluded.value_json,
                     updated_at = excluded.updated_at""",
                (key, json.dumps(value, sort_keys=True), ts),
            )

    def delete(self, key: str) -> None:
        with self._conn:
            self._conn.execute("DELETE FROM state WHERE key = ?", (key,))

    def _canonical_json(self, value: dict[str, Any]) -> bytes:
        """Canonical JSON form для stable signature across dict-order changes.

        Mirrors src/risk/override.py:71-73 pattern (ADR 0018 H2 precedent).
        """
        return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def _hmac_sign(self, value: dict[str, Any], *, hmac_key: str) -> str:
        """HMAC-SHA256 hex digest of canonical JSON. Per ADR 0018 H2 pattern."""
        if len(hmac_key) < 32:
            raise ValueError("hmac_key must be at least 32 chars (audit H2)")
        payload_bytes = self._canonical_json(value)
        return hmac.new(hmac_key.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()

    def set_signed(self, key: str, value: dict[str, Any], *, hmac_key: str) -> None:
        """ADR 0057 SD-4 + ADR 0018 H2 pattern: HMAC-signed value persistence.

        Wraps value в envelope {"payload": value, "sig": HMAC-SHA256(canonical_json)}.
        Signature computed over sort_keys=True canonical JSON bytes.

        Used для activation_ts (S37 T3) preventing rollback attack on multiday HWM window.
        """
        sig = self._hmac_sign(value, hmac_key=hmac_key)
        self.set(key, {"payload": value, "sig": sig})

    def get_signed(self, key: str, *, hmac_key: str) -> dict[str, Any] | None:
        """ADR 0057 SD-4: HMAC-verified read.

        Returns:
            - None если key missing (caller initializes)
            - dict[str, Any] payload если signature valid

        Raises:
            ValueError: signature mismatch (tampered) OR missing envelope fields.
                        Caller must halt — corrupted state means safe defaults unknown.
        """
        record = self.get(key)
        if record is None:
            return None
        if not isinstance(record, dict) or "payload" not in record or "sig" not in record:
            raise ValueError(
                f"state_repo.get_signed: key {key!r} missing HMAC envelope "
                "(expected {'payload': <dict>, 'sig': <hex>})"
            )
        payload = record["payload"]
        if not isinstance(payload, dict):
            raise ValueError(
                f"state_repo.get_signed: key {key!r} payload must be dict, got {type(payload)}"
            )
        expected_sig = self._hmac_sign(payload, hmac_key=hmac_key)
        actual_sig = record["sig"]
        if not isinstance(actual_sig, str):
            raise ValueError(f"state_repo.get_signed: key {key!r} sig must be str")
        if not hmac.compare_digest(actual_sig, expected_sig):
            raise ValueError(
                f"state_repo.get_signed: HMAC mismatch для key {key!r} — tampered value"
            )
        return payload
