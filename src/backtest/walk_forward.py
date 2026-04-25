"""Walk-forward analysis orchestrator — WindowSplitter + WalkForwardRunner.

Sprint 10 Q1+Q4 (per pre-s10-backlog.md verdicts).

WindowSplitter generates rolling (train, test) tuples per ADR 0014:
- train = 2000 bars, test = 500 bars, embargo = 20 bars, K = 5 folds
- Rolling advance: each fold's train_start += test_bars

WalkForwardRunner (T3) consumes splitter + executes run_replay per fold.
"""
from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass


@dataclass(frozen=True)
class WindowSplitter:
    """Rolling K-fold WFA window generator. ADR 0014 defaults."""

    train_bars: int = 2000
    test_bars: int = 500
    embargo_bars: int = 20
    k_folds: int = 5

    def __post_init__(self) -> None:
        if self.train_bars <= 0 or self.test_bars <= 0 or self.k_folds <= 0:
            raise ValueError(
                f"WindowSplitter: all params must be positive, "
                f"got train={self.train_bars}, test={self.test_bars}, k_folds={self.k_folds}"
            )
        if self.embargo_bars < 0:
            raise ValueError(
                f"WindowSplitter: embargo_bars must be >= 0, got {self.embargo_bars}"
            )

    def split(
        self, *, total_bars: int
    ) -> Iterator[tuple[int, int, int, int]]:
        """Yield (train_start, train_end, test_start, test_end) per fold.

        Indices are bar positions [0, total_bars). Half-open intervals:
        bar at index `train_end` is NOT included in train; `test_end` excluded similarly.
        """
        min_required = self.train_bars + self.embargo_bars + self.k_folds * self.test_bars
        if total_bars < min_required:
            raise ValueError(
                f"insufficient data: need {min_required} bars for K={self.k_folds} folds, "
                f"got {total_bars}"
            )
        for k in range(self.k_folds):
            train_start = k * self.test_bars
            train_end = train_start + self.train_bars
            test_start = train_end + self.embargo_bars
            test_end = test_start + self.test_bars
            yield (train_start, train_end, test_start, test_end)
