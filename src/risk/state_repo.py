"""JSON KV adapter for the `state` SQLite table."""

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
        row = self._conn.execute(
            "SELECT value_json FROM state WHERE key = ?", (key,)
        ).fetchone()
        if row is None:
            return None
        return json.loads(row[0])

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

    def delete(self, key: str) -> None:
        with self._conn:
            self._conn.execute("DELETE FROM state WHERE key = ?", (key,))
