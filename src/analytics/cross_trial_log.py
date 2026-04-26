"""Persistent cross-trial Sharpe log for DSR n_trials > 1.

Bailey & López de Prado eq. 13: sigma_SR = std([oos_sharpe_trial_1, ..., oos_sharpe_trial_N]).
S15 closes S14 Q2 REVISE carry-over (cross-FOLD sigma_SR was insufficient — needs cross-TRIAL).

Stores trial Sharpe values across measurement sprints (S13, S15, ...).
Each call to `_cmd_wfa` appends one trial entry after measurement completes.

Format: data/cross_trial_sharpes.json
    {"trials": [{"sprint": 13, "oos_sharpe": -44.46}, {"sprint": 15, "oos_sharpe": <X>}]}

Atomic write via tmp+rename. JSON for operator readability + git diff transparency.
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import TypedDict


class TrialEntry(TypedDict):
    sprint: int
    oos_sharpe: float


class CrossTrialLog:
    """File-backed list of trial OOS Sharpe values for DSR cross-trial sigma_SR.

    Thread-safety: NOT thread-safe. Single writer (CLI invocation per sprint).
    """

    def __init__(self, *, path: Path) -> None:
        self._path = path

    def _load(self) -> list[TrialEntry]:
        if not self._path.exists():
            return []
        data = json.loads(self._path.read_text())
        return list(data.get("trials", []))

    def get_oos_sharpes(self) -> list[float]:
        """Return ordered list of OOS Sharpe values across all persisted trials."""
        return [float(e["oos_sharpe"]) for e in self._load()]

    def n_trials(self) -> int:
        """Count of persisted trials."""
        return len(self._load())

    def append_trial(self, *, sprint: int, oos_sharpe: float) -> None:
        """Atomically append new trial entry. Creates parent dir if missing."""
        trials = self._load()
        trials.append({"sprint": sprint, "oos_sharpe": float(oos_sharpe)})
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp.write_text(json.dumps({"trials": trials}, indent=2))
        tmp.rename(self._path)

    def sigma_sr(self) -> float | None:
        """Sample stdev of OOS Sharpes across trials. None if < 2 trials."""
        sharpes = self.get_oos_sharpes()
        if len(sharpes) < 2:
            return None
        return float(statistics.stdev(sharpes))
