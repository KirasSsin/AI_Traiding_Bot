"""Persistent cross-trial Sharpe log for DSR n_trials > 1.

Bailey & López de Prado eq. 13: sigma_SR = std([oos_sharpe_trial_1, ..., oos_sharpe_trial_N]).
S15 closes S14 Q2 REVISE carry-over (cross-FOLD sigma_SR was insufficient — needs cross-TRIAL).
S33 T3 (Items #6+#7+#9): added `symbol: str` field — multi-symbol DSR support.

Stores trial Sharpe values across measurement sprints (S13, S15, ...) с symbol identifier.
Each call к `_cmd_wfa` appends one trial entry per (sprint, symbol) pair after measurement.

S33 pooling protocol (a): pool ALL (sprint, symbol) entries as independent trials.
n_trials counts entries (3 entries per multi-symbol sprint = 3 trials, NOT 1 sprint).
Methodologically conservative для multi-symbol per Bailey & López de Prado eq. 12.

Format: data/cross_trial_sharpes.json
    {"trials": [{"sprint": 13, "symbol": "BTCUSDT", "oos_sharpe": -44.46}, ...]}

Backward-compat: legacy entries без `symbol` field backfilled к "BTCUSDT" on load
(all pre-S33 trials were single-symbol BTC per acceptance-criteria.md MVP scope).

Atomic write via tmp+rename. JSON для operator readability + git diff transparency.
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import TypedDict


class TrialEntry(TypedDict):
    """Cross-trial log entry per Bailey & López de Prado DSR (2014).

    Schema migrated S33 T3 — added `symbol: str` field для multi-symbol DSR.
    Pre-S33 entries (no symbol) backfilled к "BTCUSDT" via _load() defensive get.
    """

    sprint: int
    symbol: str
    oos_sharpe: float


# Default symbol для backward-compat (all pre-S33 trials were single-symbol BTC)
_DEFAULT_SYMBOL_BACKFILL = "BTCUSDT"


class CrossTrialLog:
    """File-backed list of trial OOS Sharpe values для DSR cross-trial sigma_SR.

    Thread-safety: NOT thread-safe. Single writer (CLI invocation per sprint).

    S33 multi-symbol pooling protocol (a) — pool ALL (sprint, symbol) entries
    as independent trials per consilium Items #6+#7.
    """

    def __init__(self, *, path: Path) -> None:
        self._path = path

    def _load(self) -> list[TrialEntry]:
        """Load entries с backfill default `symbol="BTCUSDT"` для legacy data.

        Per Item #9 schema migration guard: pre-S33 entries lacked `symbol` field.
        Defensive get(`symbol`, default) preserves existing data without explicit migration script.
        """
        if not self._path.exists():
            return []
        data = json.loads(self._path.read_text())
        raw_trials = data.get("trials", [])
        return [
            TrialEntry(
                sprint=int(e["sprint"]),
                symbol=str(e.get("symbol", _DEFAULT_SYMBOL_BACKFILL)),  # backfill
                oos_sharpe=float(e["oos_sharpe"]),
            )
            for e in raw_trials
        ]

    def get_entries(self) -> list[TrialEntry]:
        """Return ordered list of all entries (с symbol field — backfilled if legacy)."""
        return self._load()

    def get_oos_sharpes(self) -> list[float]:
        """Return ordered list of OOS Sharpe values across all persisted trials.

        Backward-compat method (legacy callers don't filter by symbol).
        """
        return [float(e["oos_sharpe"]) for e in self._load()]

    def n_trials(self) -> int:
        """Count of persisted trials (per protocol (a) — entries, NOT unique sprints).

        Multi-symbol sprint adds 3 trials (1 per symbol), n_trials reflects multi-testing
        penalty correctly per Bailey & López de Prado eq. 12.
        """
        return len(self._load())

    def append_trial(
        self,
        *,
        sprint: int,
        oos_sharpe: float,
        symbol: str = _DEFAULT_SYMBOL_BACKFILL,
    ) -> None:
        """Atomically append OR update trial entry. Idempotent on (sprint, symbol).

        S45 B1 — same (sprint, symbol) tuple replaces existing entry's oos_sharpe.
        Prevents log poisoning from dashboard reruns where each render appended duplicate.

        Args:
            sprint: sprint number (S13, S15, S33, ...)
            oos_sharpe: OOS Sharpe ratio for this trial
            symbol: trading pair symbol (default "BTCUSDT" preserves legacy callers)
        """
        trials = self._load()
        new_entry = TrialEntry(sprint=int(sprint), symbol=str(symbol), oos_sharpe=float(oos_sharpe))
        # S45 B1 idempotency guard — find existing matching (sprint, symbol)
        existing_idx = next(
            (
                i
                for i, t in enumerate(trials)
                if t["sprint"] == new_entry["sprint"] and t["symbol"] == new_entry["symbol"]
            ),
            None,
        )
        if existing_idx is not None:
            trials[existing_idx] = new_entry
        else:
            trials.append(new_entry)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp.write_text(json.dumps({"trials": trials}, indent=2))
        tmp.rename(self._path)

    def sigma_sr(self) -> float | None:
        """Sample stdev of OOS Sharpes across trials per ADR 0056 hierarchy.

        Sourcing hierarchy (S36 T6 ADR 0056):
          - N >= 3 entries: PREFERRED — return stdev(oos_sharpes)
          - 1-2 entries:    DEGENERATE — return NaN (df<2 statistically inadmissible)
          - 0 entries:      EMPTY — return None (caller знает использовать n_trials=1)

        ADR 0056 rationale: stdev на N=2 has df=1 (extreme variance) — consilium
        ruled inadmissible per Bailey 2014 eq.12. NaN signals "underpowered" к caller.
        """
        sharpes = self.get_oos_sharpes()
        n = len(sharpes)
        if n == 0:
            return None
        if n < 3:
            return float("nan")
        return float(statistics.stdev(sharpes))
