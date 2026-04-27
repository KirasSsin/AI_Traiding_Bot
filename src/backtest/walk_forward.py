"""Walk-forward analysis orchestrator — WindowSplitter + WalkForwardRunner.

Sprint 10 Q1+Q4 (per pre-s10-backlog.md verdicts).

WindowSplitter generates rolling (train, test) tuples per ADR 0014:
- train = 2000 bars, test = 500 bars, embargo = 20 bars, K = 5 folds
- Rolling advance: each fold's train_start += test_bars

WalkForwardRunner (T3) consumes splitter + executes run_replay per fold.
"""
from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any

import pandas as pd


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


# Type alias for replay function signature (matches src.backtest.replay_engine.run_replay)
ReplayFn = Callable[[pd.DataFrame, dict[str, Any]], dict[str, Any]]


class WalkForwardRunner:
    """Orchestrate K-fold walk-forward analysis.

    Per ADR 0014 + pre-s10-backlog.md Q4 (revive S2 + dual-Sharpe routing caveat).

    For each fold:
    1. Slice df к train + test windows per WindowSplitter
    2. Invoke replay_fn(train_window) → in-sample (IS) result
    3. Invoke replay_fn(test_window) → out-of-sample (OOS) result
    4. Compute oos/is Sharpe ratio (ADR 0014 acceptance gate input)
    5. Aggregate OOS trades across folds (для DSR + MC в T8 reporter)

    Returns dict with 'folds' list + 'aggregate' OOS data.
    """

    def __init__(self, *, splitter: WindowSplitter, replay_fn: ReplayFn) -> None:
        self._splitter = splitter
        self._replay_fn = replay_fn

    def run(
        self,
        *,
        df: pd.DataFrame,
        config: dict[str, Any],
        symbol: str = "unknown",
    ) -> dict[str, Any]:
        """Execute K-fold WFA. Returns per-fold + aggregate results.

        Args:
            df: OHLCV bars DataFrame (must have train + embargo + k_folds*test bars)
            config: replay engine config (per-fold passed к replay_fn)
            symbol: symbol identifier для error messages (per S33 T4 Item #10 — operator
                visibility into which symbol failed insufficient-data check; SOL Bybit
                listing date may give fewer 4H bars чем BTC, silent fold-skip risk)
        """
        total_bars = len(df)
        folds: list[dict[str, Any]] = []
        all_oos_trades: list[pd.DataFrame] = []

        # S33 T4 Item #10: pre-run validation с symbol context
        min_required = (
            self._splitter.train_bars
            + self._splitter.embargo_bars
            + self._splitter.k_folds * self._splitter.test_bars
        )
        if total_bars < min_required:
            raise ValueError(
                f"Symbol {symbol}: insufficient data {total_bars} bars, WFA needs "
                f"{min_required} (train={self._splitter.train_bars} + embargo="
                f"{self._splitter.embargo_bars} + k_folds={self._splitter.k_folds} × "
                f"test={self._splitter.test_bars})"
            )

        for fold_idx, (tr_start, tr_end, te_start, te_end) in enumerate(
            self._splitter.split(total_bars=total_bars)
        ):
            train_window = df.iloc[tr_start:tr_end].reset_index(drop=True)
            test_window = df.iloc[te_start:te_end].reset_index(drop=True)

            is_result = self._replay_fn(train_window, config)
            oos_result = self._replay_fn(test_window, config)

            is_sharpe = float(is_result.get("metrics", {}).get("Sharpe Ratio", 0.0))
            oos_sharpe = float(oos_result.get("metrics", {}).get("Sharpe Ratio", 0.0))
            ratio = oos_sharpe / is_sharpe if is_sharpe != 0 else 0.0

            folds.append({
                "fold_idx": fold_idx,
                "train_window": (tr_start, tr_end),
                "test_window": (te_start, te_end),
                "is_metrics": is_result.get("metrics", {}),
                "oos_metrics": oos_result.get("metrics", {}),
                "oos_trades_df": oos_result.get("trades_df", pd.DataFrame()),
                "oos_equity_df": oos_result.get("equity_df", pd.DataFrame()),
                "oos_is_sharpe_ratio": ratio,
            })
            all_oos_trades.append(oos_result.get("trades_df", pd.DataFrame()))

        aggregate = {
            "oos_trades_df": pd.concat(all_oos_trades, ignore_index=True)
            if all_oos_trades
            else pd.DataFrame(),
            "k_folds": self._splitter.k_folds,
            "fold_oos_sharpes": [f["oos_metrics"].get("Sharpe Ratio", 0.0) for f in folds],
        }

        return {"folds": folds, "aggregate": aggregate}


def evaluate_acceptance_gate(
    *,
    fold_oos_is_sharpe_ratios: list[float],
    mc_p_value: float,
    sharpe_threshold: float = 0.7,
    p_threshold: float = 0.05,
) -> dict[str, Any]:
    """Evaluate WFA acceptance gate per ADR 0014 + 0015 AND-combined.

    Per pre-s10-backlog.md Q2 verdict (trader REVISE accepted): DSR is
    computed and reported (informational) but NOT в gate decision.

    Gates:
    - L1 (per ADR 0014): every fold's OOS/IS Sharpe ratio >= sharpe_threshold (0.7 default)
    - L2 (per ADR 0015): MC permutation p-value <= p_threshold (0.05 default)
    - PASS = L1 AND L2

    Returns:
        dict с 'passed' bool + per-gate details + failed_folds list.
    """
    failed_folds = [
        idx
        for idx, ratio in enumerate(fold_oos_is_sharpe_ratios)
        if ratio < sharpe_threshold
    ]
    sharpe_gate_passed = len(failed_folds) == 0
    mc_gate_passed = mc_p_value <= p_threshold

    return {
        "passed": sharpe_gate_passed and mc_gate_passed,
        "sharpe_gate_passed": sharpe_gate_passed,
        "mc_gate_passed": mc_gate_passed,
        "failed_folds": failed_folds,
        "fold_sharpe_ratios": list(fold_oos_is_sharpe_ratios),
        "mc_p_value": mc_p_value,
        "thresholds": {
            "sharpe": sharpe_threshold,
            "p_value": p_threshold,
        },
    }
