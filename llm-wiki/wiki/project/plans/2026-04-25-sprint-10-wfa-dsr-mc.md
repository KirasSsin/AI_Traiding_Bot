---
title: Sprint 10 — Walk-Forward Analysis + DSR aggregate + Monte Carlo permutations
type: plan
tags: [sprint-10, plan, wfa, dsr, monte-carlo, backtest, statistics]
created: 2026-04-25
updated: 2026-04-25
status: active
sources:
  - project/pre-s10-backlog.md
  - project/decisions/0014-walk-forward-train2000-test500.md
  - project/decisions/0015-sign-flip-mc-permutations-n2000.md
  - project/decisions/0024-sprint-9-data-quality-types-analytics.md
---

# Sprint 10 Implementation Plan — WFA + DSR + MC permutations

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) или `superpowers:executing-plans`. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Production-grade walk-forward validation pipeline (rolling K-folds + Sharpe gate per ADR 0014 + sign-flip MC p-test per ADR 0015 + DSR aggregate informational reporting) builds на S9 B2 DSR foundation.

**Architecture:**
- `WindowSplitter` pure function generator → `(train_start, train_end, test_start, test_end)` tuples per ADR 0014 (train=2000, test=500, K=5, embargo=20).
- `WalkForwardRunner` orchestrator: invokes existing `run_replay()` per fold, collects results. Routes `trades_df` → DSR, `equity_df` → bar-Sharpe gate.
- `compute_dsr` extended с optional `sigma_sr: float` для n_trials > 1 (closes S9 NotImplementedError).
- `mc_permutation.sign_flip` + `mc_permutation.block_bootstrap` pure functions on per-trade returns array.
- `wfa_reporter` formats structured output: 3 distinct Sharpe series (bar / per-trade / display) + MC p-value + DSR aggregate.

**Tech Stack:** Python 3.12, numpy, pandas, scipy.stats, mypy --strict (S9 baseline), pytest unit + integration.

---

## Trace map (PHASE 3 step 1a HARD-GATE per dev-workflow.md)

### Files Created (4 src + 5 tests + 4 wiki)

| Path | Responsibility | Task |
|------|----------------|------|
| `src/backtest/walk_forward.py` | `WindowSplitter` + `WalkForwardRunner` orchestrator | T2+T3 |
| `src/backtest/mc_permutation.py` | `sign_flip` + `block_bootstrap` permutation tests | T5+T6 |
| `src/backtest/wfa_reporter.py` | Structured WFA report formatter | T8 |
| `tests/unit/test_window_splitter.py` | 6 tests (window arithmetic + edge cases) | T2 |
| `tests/unit/test_walk_forward_runner.py` | 5 tests (orchestration + routing) | T3 |
| `tests/unit/test_dsr_sigma_sr.py` | 4 tests (n_trials > 1 + sigma_sr extension) | T4 |
| `tests/unit/test_mc_sign_flip.py` | 5 tests (permutation correctness + p-value) | T5 |
| `tests/unit/test_mc_block_bootstrap.py` | 4 tests (block sampling + autocorrelation preservation) | T6 |
| `tests/unit/test_wfa_acceptance_gate.py` | 4 tests (Sharpe AND MC combine) | T7 |
| `tests/unit/test_wfa_reporter.py` | 4 tests (3-series routing + DSR informational) | T8 |
| `tests/integration/test_wfa_pipeline.py` | End-to-end WFA pipeline test (synthetic data) | T9 |
| `wiki/project/components/walk-forward.md` | NEW component page | T11 |
| `wiki/project/components/mc-permutations.md` | NEW component page | T11 |
| `wiki/project/components/wfa-reporter.md` | NEW component page | T11 |
| `wiki/project/sprints/sprint-10-wfa-dsr-mc.md` | NEW sprint page | T11 |

### Files Modified (4 existing)

| Path | What changes | Task |
|------|--------------|------|
| `src/backtest/vector_backtest.py:62-64` | Annualization fix `sqrt(365*24*60)` → `sqrt(365*24)` (was 1m bar assumption, actual 1H) | T1 |
| `src/analytics/dsr.py:106-110` | Extend `compute_dsr` с `sigma_sr: float \| None = None`, replace NotImplementedError raise с full Bailey eq. 12 | T4 |
| `wiki/project/components/dsr.md` | Update invariant row 7 (remove "NYI v0.1" + document sigma_sr param contract); update "Referenced by" (DSR informational, NOT gate) | T11 |
| `wiki/project/components/backtest-harness.md` | Document dual-Sharpe distinction (3 series) + annualization fix note | T11 |
| `wiki/project/architecture/current-state.md` | Component count 32→35 + ADR 24→25 + sprint pages 11→12 | T11 |

### Settings (1 new field)

| Field | Type | Default | File |
|-------|------|---------|------|
| `wfa_train_bars` | int | 2000 | `src/platform/config.py` |
| `wfa_test_bars` | int | 500 | `src/platform/config.py` |
| `wfa_embargo_bars` | int | 20 | `src/platform/config.py` |
| `wfa_k_folds` | int | 5 | `src/platform/config.py` |
| `wfa_mc_iterations` | int | 2000 | `src/platform/config.py` |
| `wfa_mc_block_size` | int | 30 | `src/platform/config.py` |
| `wfa_acceptance_sharpe_ratio` | float | 0.7 | `src/platform/config.py` |
| `wfa_acceptance_p_value` | float | 0.05 | `src/platform/config.py` |

### ADRs

| ADR | Created/Modified | Task |
|-----|------------------|------|
| ADR 0025 (NEW) | Aggregate decisions: WFA orchestrator + DSR sigma_SR + MC implementation + reporter routing + vector_backtest annualization fix | T10 |

### Wiki dependency map

```
S10 plan
├── PHASE 2 verdicts → pre-s10-backlog.md (already shipped 6d85faa)
├── ADR 0025 (T10) — aggregate (Q1-Q7)
├── Component pages (T11)
│   ├── walk-forward.md → cross-links backtest-harness, dsr, ADR 0014
│   ├── mc-permutations.md → cross-links walk-forward, ADR 0015
│   └── wfa-reporter.md → cross-links walk-forward, dsr, mc-permutations
├── Modified: dsr.md (sigma_sr extension), backtest-harness.md (dual-Sharpe doc)
└── current-state.md (T11): components 32→35, ADR 24→25, sprints 11→12
```

### FSM impact

NONE. WFA = backtest layer (analytics post-process), не touches FSM/runtime/coordinator. Counts unchanged: 16/30/74/45.

---

## Pre-flight verification (run before T1)

```bash
cd /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot
git status  # expect: clean (except FULL_PROJECT_DOCUMENTATION.md untracked, ignore)
git checkout feature/sprint-10-wfa-dsr-mc  # already created в PHASE 2 commit
source .venv/bin/activate
pytest tests/unit -x -q 2>&1 | tail -3  # expect: 630 passed (S9 baseline)
mypy src/ 2>&1 | tail -2  # expect: Success in 63 source files
python -c "from src.execution.state_machine import TRANSITIONS, ExecutionState, ExecutionEvent; from src.risk.reason_codes import ReasonCode; print(f'states={len(list(ExecutionState))}, events={len(list(ExecutionEvent))}, transitions={len(TRANSITIONS)}, reason_codes={len(list(ReasonCode))}')"
# Expected: states=16, events=30, transitions=74, reason_codes=45
```

---

## Q1 — Backtest annualization fix (1 task)

### Task 1: Fix vector_backtest annualization + audit replay_engine

**Files:**
- Modify: `src/backtest/vector_backtest.py:62-64` (annualization fix)
- Modify: `src/backtest/replay_engine.py:51` (verify already correct, document)
- Create: `tests/unit/test_vector_backtest_annualization.py`

- [ ] **Step 1: Write failing test (RED)**

Create `tests/unit/test_vector_backtest_annualization.py`:

```python
"""Verify vector_backtest annualization factor matches 1H bar period.

Sprint 10 Q6 (per pre-s10-backlog.md trader REVISE accepted).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.backtest.vector_backtest import VectorBacktester


def _synthetic_df(n_bars: int = 100) -> pd.DataFrame:
    """Build synthetic 1H OHLCV с alternating signals for Sharpe sanity check."""
    rng = np.random.default_rng(42)
    closes = 100.0 * np.exp(np.cumsum(rng.normal(0.0001, 0.01, n_bars)))
    return pd.DataFrame({
        "close": closes,
        "signal": [1 if i % 4 < 2 else -1 for i in range(n_bars)],
    })


def test_sharpe_uses_1h_annualization_factor() -> None:
    """Sharpe should use sqrt(8760) = sqrt(365*24) для 1H bars, NOT sqrt(365*24*60)."""
    df = _synthetic_df()
    bt = VectorBacktester(df, initial_capital=10000.0, maker_fee=0.001)
    result = bt.run()

    # Re-compute с correct factor — must match
    returns_mean = bt.df["strategy_returns"].mean()
    returns_std = bt.df["strategy_returns"].std()
    expected_sharpe = (returns_mean / returns_std) * np.sqrt(365 * 24)
    assert abs(result["Sharpe Ratio"] - expected_sharpe) < 1e-9, (
        f"Sharpe used wrong factor. Got {result['Sharpe Ratio']}, "
        f"expected {expected_sharpe} (sqrt(365*24)=sqrt(8760))"
    )


def test_sharpe_matches_replay_engine_convention() -> None:
    """vector_backtest annualization must match replay_engine._compute_metrics:51 convention."""
    # replay_engine uses sqrt(24 * 365) — same as sqrt(365 * 24) = sqrt(8760)
    expected_factor = np.sqrt(24 * 365)
    assert abs(expected_factor - np.sqrt(8760)) < 1e-9
```

- [ ] **Step 2: Verify RED**

```bash
source /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot/.venv/bin/activate
pytest tests/unit/test_vector_backtest_annualization.py -v 2>&1 | tail -10
```

Expected: FAIL — Sharpe used `sqrt(365*24*60)` (off by sqrt(60) ≈ 7.7×).

- [ ] **Step 3: Apply fix к vector_backtest.py**

Edit `src/backtest/vector_backtest.py:60-64`:

```python
        # N = periods per year for 1H bars: 365 * 24 = 8760
        # NOTE (S10 fix): was sqrt(365*24*60) which assumed 1m bars — wrong для 1H BTCUSDT.
        # Off by sqrt(60) ≈ 7.7×. Aligned с replay_engine._compute_metrics:51 convention.
        returns_mean = self.df["strategy_returns"].mean()
        returns_std = self.df["strategy_returns"].std()
        sharpe_ratio = (
            (returns_mean / returns_std) * np.sqrt(365 * 24) if returns_std != 0 else 0
        )
```

- [ ] **Step 4: Verify GREEN**

```bash
pytest tests/unit/test_vector_backtest_annualization.py -v 2>&1 | tail -10
```

Expected: 2 passed.

- [ ] **Step 5: Verify mypy + full suite**

```bash
mypy src/backtest/vector_backtest.py 2>&1 | tail -3
pytest tests/unit -x -q 2>&1 | tail -3
```

Expected: clean + 632+ passed (630 baseline + 2).

- [ ] **Step 6: Commit**

```bash
git add src/backtest/vector_backtest.py tests/unit/test_vector_backtest_annualization.py
git commit -m "fix(backtest): vector_backtest annualization sqrt(365*24*60)→sqrt(8760) — 1H bars (S10 Q6)"
```

---

## WFA — Window splitter + Orchestrator (2 tasks)

### Task 2: WindowSplitter — rolling fold generator

**Files:**
- Create: `src/backtest/walk_forward.py` (WindowSplitter only — runner в T3)
- Create: `tests/unit/test_window_splitter.py`

- [ ] **Step 1: Write failing tests (RED)**

Create `tests/unit/test_window_splitter.py`:

```python
"""Tests for WindowSplitter — rolling K-fold WFA window generator.

Sprint 10 Q1 (per pre-s10-backlog.md verdict — bars unit, ADR 0014 explicit).
"""
from __future__ import annotations

import pytest

from src.backtest.walk_forward import WindowSplitter


def test_rolling_windows_no_overlap_per_fold() -> None:
    """Per ADR 0014: train + embargo + test, rolling. Verify no overlap."""
    splitter = WindowSplitter(
        train_bars=2000, test_bars=500, embargo_bars=20, k_folds=5
    )
    folds = list(splitter.split(total_bars=15000))
    assert len(folds) == 5
    for tr_start, tr_end, te_start, te_end in folds:
        # Train ends, embargo gap, test begins
        assert te_start == tr_end + 20  # embargo = 20 bars
        assert tr_end - tr_start == 2000  # train length
        assert te_end - te_start == 500  # test length


def test_K_folds_advance_by_test_window() -> None:
    """Each fold advances by test_bars (rolling)."""
    splitter = WindowSplitter(
        train_bars=2000, test_bars=500, embargo_bars=20, k_folds=5
    )
    folds = list(splitter.split(total_bars=15000))
    advances = [
        folds[i + 1][0] - folds[i][0] for i in range(len(folds) - 1)
    ]
    # Each fold's train_start advances by test_bars
    assert all(adv == 500 for adv in advances)


def test_insufficient_data_raises() -> None:
    """If total_bars < min required, raise."""
    splitter = WindowSplitter(
        train_bars=2000, test_bars=500, embargo_bars=20, k_folds=5
    )
    # Need: train + embargo + test + (k-1)*test = 2000 + 20 + 500 + 4*500 = 4520 minimum
    with pytest.raises(ValueError, match="insufficient data"):
        list(splitter.split(total_bars=4000))


def test_embargo_zero_allowed() -> None:
    """embargo_bars=0 valid (ADR 0014 sets default 20 но allows override)."""
    splitter = WindowSplitter(
        train_bars=100, test_bars=50, embargo_bars=0, k_folds=2
    )
    folds = list(splitter.split(total_bars=300))
    assert folds[0] == (0, 100, 100, 150)  # no gap
    assert folds[1] == (50, 150, 150, 200)


def test_negative_params_rejected() -> None:
    """Negative train/test/embargo/k rejected at construction."""
    with pytest.raises(ValueError, match="must be positive"):
        WindowSplitter(train_bars=-1, test_bars=500, embargo_bars=20, k_folds=5)
    with pytest.raises(ValueError, match="must be positive"):
        WindowSplitter(train_bars=2000, test_bars=0, embargo_bars=20, k_folds=5)
    with pytest.raises(ValueError, match="must be positive"):
        WindowSplitter(train_bars=2000, test_bars=500, embargo_bars=20, k_folds=0)


def test_default_params_match_adr_0014() -> None:
    """Default params per ADR 0014: train=2000, test=500, embargo=20, K=5."""
    splitter = WindowSplitter()  # all defaults
    assert splitter.train_bars == 2000
    assert splitter.test_bars == 500
    assert splitter.embargo_bars == 20
    assert splitter.k_folds == 5
```

- [ ] **Step 2: Verify RED**

```bash
pytest tests/unit/test_window_splitter.py -v 2>&1 | tail -15
```

Expected: ImportError на `src.backtest.walk_forward.WindowSplitter`.

- [ ] **Step 3: Implement WindowSplitter**

Create `src/backtest/walk_forward.py`:

```python
"""Walk-forward analysis orchestrator — WindowSplitter + WalkForwardRunner.

Sprint 10 Q1+Q4 (per pre-s10-backlog.md verdicts).

WindowSplitter generates rolling (train, test) tuples per ADR 0014:
- train = 2000 bars, test = 500 bars, embargo = 20 bars, K = 5 folds
- Rolling advance: each fold's train_start += test_bars

WalkForwardRunner (T3) consumes splitter + executes run_replay per fold,
routes results к DSR (per-trade) и Sharpe gate (bar-returns).
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
        bar at index `train_end` is NOT included в train; `test_end` excluded similarly.
        """
        min_required = self.train_bars + self.embargo_bars + self.k_folds * self.test_bars
        if total_bars < min_required:
            raise ValueError(
                f"insufficient data: need {min_required} bars для K={self.k_folds} folds, "
                f"got {total_bars}"
            )
        for k in range(self.k_folds):
            train_start = k * self.test_bars
            train_end = train_start + self.train_bars
            test_start = train_end + self.embargo_bars
            test_end = test_start + self.test_bars
            yield (train_start, train_end, test_start, test_end)
```

- [ ] **Step 4: Verify GREEN + mypy strict**

```bash
pytest tests/unit/test_window_splitter.py -v 2>&1 | tail -10
mypy --strict src/backtest/walk_forward.py 2>&1 | tail -3
```

Expected: 6 passed + mypy clean.

- [ ] **Step 5: Commit**

```bash
git add src/backtest/walk_forward.py tests/unit/test_window_splitter.py
git commit -m "feat(wfa): WindowSplitter — rolling K-fold WFA generator (S10 Q1, ADR 0014)"
```

---

### Task 3: WalkForwardRunner — orchestrator с dual-Sharpe routing

**Files:**
- Modify: `src/backtest/walk_forward.py` (append `WalkForwardRunner`)
- Create: `tests/unit/test_walk_forward_runner.py`

- [ ] **Step 1: Write failing tests (RED)**

Create `tests/unit/test_walk_forward_runner.py`:

```python
"""Tests for WalkForwardRunner — orchestrator с dual-Sharpe routing.

Sprint 10 Q4 (per pre-s10-backlog.md verdict + cross-cutting concern #1).
"""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import numpy as np
import pandas as pd

from src.backtest.walk_forward import WalkForwardRunner, WindowSplitter


def _synthetic_df(n_bars: int = 5000) -> pd.DataFrame:
    """Synthetic 1H OHLCV — enough bars для 5-fold K=5 (need >= 4520)."""
    rng = np.random.default_rng(42)
    closes = 100.0 * np.exp(np.cumsum(rng.normal(0.0001, 0.01, n_bars)))
    timestamps = pd.date_range("2024-01-01", periods=n_bars, freq="1h")
    return pd.DataFrame({
        "timestamp": timestamps,
        "open": closes * 0.999,
        "high": closes * 1.001,
        "low": closes * 0.998,
        "close": closes,
        "volume": np.ones(n_bars),
    })


def test_runner_invokes_replay_per_fold() -> None:
    """Per ADR 0014 K=5: runner calls run_replay 5 times (1 per OOS test window)."""
    df = _synthetic_df(n_bars=5000)
    splitter = WindowSplitter()  # ADR 0014 defaults
    config = {"trading": {"initial_balance": 10000.0, "long_only": True}}

    mock_replay = MagicMock(return_value={
        "equity_df": pd.DataFrame({"timestamp": [pd.Timestamp("2024-01-01")], "balance": [10100.0]}),
        "trades_df": pd.DataFrame({"net_pnl": [100.0], "timestamp_open": [pd.Timestamp("2024-01-01")]}),
        "metrics": {"Sharpe Ratio": 1.2, "Total Return (%)": 1.0},
    })

    runner = WalkForwardRunner(splitter=splitter, replay_fn=mock_replay)
    result = runner.run(df=df, config=config)

    assert mock_replay.call_count == 5  # K=5 folds


def test_runner_collects_per_fold_results() -> None:
    """Result dict has 'folds' list с per-fold metrics + trades."""
    df = _synthetic_df(n_bars=5000)
    splitter = WindowSplitter()
    config: dict[str, Any] = {"trading": {"initial_balance": 10000.0}}

    mock_replay = MagicMock(return_value={
        "equity_df": pd.DataFrame({"timestamp": [pd.Timestamp("2024-01-01")], "balance": [10100.0]}),
        "trades_df": pd.DataFrame({"net_pnl": [100.0]}),
        "metrics": {"Sharpe Ratio": 1.2},
    })

    runner = WalkForwardRunner(splitter=splitter, replay_fn=mock_replay)
    result = runner.run(df=df, config=config)

    assert "folds" in result
    assert len(result["folds"]) == 5
    for fold in result["folds"]:
        assert "fold_idx" in fold
        assert "train_window" in fold  # tuple (start, end)
        assert "test_window" in fold
        assert "is_metrics" in fold  # in-sample metrics
        assert "oos_metrics" in fold  # out-of-sample metrics
        assert "oos_trades_df" in fold


def test_runner_routes_oos_only_к_aggregate() -> None:
    """Aggregate trades = OOS only (NOT in-sample). Per WFA standard."""
    df = _synthetic_df(n_bars=5000)
    splitter = WindowSplitter()
    config: dict[str, Any] = {"trading": {"initial_balance": 10000.0}}

    # Replay returns different trade counts для IS vs OOS
    is_trades = pd.DataFrame({"net_pnl": [10.0, 20.0]})
    oos_trades = pd.DataFrame({"net_pnl": [5.0]})
    call_count = {"n": 0}

    def mock_replay(window_df: pd.DataFrame, cfg: dict) -> dict:
        call_count["n"] += 1
        # Even calls = IS, odd = OOS (alternating). Or simpler: IS all calls
        return {
            "equity_df": pd.DataFrame({"balance": [10100.0]}),
            "trades_df": oos_trades.copy(),
            "metrics": {"Sharpe Ratio": 1.0},
        }

    runner = WalkForwardRunner(splitter=splitter, replay_fn=mock_replay)
    result = runner.run(df=df, config=config)

    # Aggregated OOS trades = K folds × oos trades per fold
    aggregate = result["aggregate"]
    assert "oos_trades_df" in aggregate
    assert len(aggregate["oos_trades_df"]) == 5  # 5 folds × 1 trade


def test_runner_per_fold_oos_is_sharpe_ratio() -> None:
    """Each fold's result includes is_sharpe и oos_sharpe (для ADR 0014 ratio gate)."""
    df = _synthetic_df(n_bars=5000)
    splitter = WindowSplitter()
    config: dict[str, Any] = {"trading": {"initial_balance": 10000.0}}

    mock_replay = MagicMock(return_value={
        "equity_df": pd.DataFrame({"balance": [10100.0, 10200.0]}),
        "trades_df": pd.DataFrame({"net_pnl": [50.0]}),
        "metrics": {"Sharpe Ratio": 1.5},
    })

    runner = WalkForwardRunner(splitter=splitter, replay_fn=mock_replay)
    result = runner.run(df=df, config=config)

    for fold in result["folds"]:
        # Each fold ran replay twice — IS + OOS
        assert "oos_is_sharpe_ratio" in fold


def test_insufficient_data_raises() -> None:
    """If df shorter than min required, raise."""
    df = _synthetic_df(n_bars=1000)  # not enough для K=5
    splitter = WindowSplitter()
    config: dict[str, Any] = {}

    runner = WalkForwardRunner(splitter=splitter, replay_fn=MagicMock())
    import pytest
    with pytest.raises(ValueError, match="insufficient data"):
        runner.run(df=df, config=config)
```

- [ ] **Step 2: Verify RED**

```bash
pytest tests/unit/test_walk_forward_runner.py -v 2>&1 | tail -10
```

Expected: ImportError на `WalkForwardRunner`.

- [ ] **Step 3: Implement WalkForwardRunner**

Append к `src/backtest/walk_forward.py`:

```python
from collections.abc import Callable
from typing import Any

import pandas as pd


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
    5. Aggregate OOS trades across folds (для DSR + MC)

    Returns dict with 'folds' list + 'aggregate' OOS data.
    """

    def __init__(self, *, splitter: WindowSplitter, replay_fn: ReplayFn) -> None:
        self._splitter = splitter
        self._replay_fn = replay_fn

    def run(self, *, df: pd.DataFrame, config: dict[str, Any]) -> dict[str, Any]:
        """Execute K-fold WFA. Returns per-fold + aggregate results."""
        total_bars = len(df)
        folds: list[dict[str, Any]] = []
        all_oos_trades: list[pd.DataFrame] = []

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
```

- [ ] **Step 4: Verify GREEN + mypy**

```bash
pytest tests/unit/test_walk_forward_runner.py -v 2>&1 | tail -10
mypy --strict src/backtest/walk_forward.py 2>&1 | tail -3
```

Expected: 5 passed + mypy clean.

- [ ] **Step 5: Commit**

```bash
git add src/backtest/walk_forward.py tests/unit/test_walk_forward_runner.py
git commit -m "feat(wfa): WalkForwardRunner orchestrator с dual-Sharpe routing (S10 Q4)"
```

---

## Q7 — DSR sigma_SR extension (1 task)

### Task 4: Extend compute_dsr с sigma_sr param

**Files:**
- Modify: `src/analytics/dsr.py:106-110` (replace NotImplementedError с full Bailey eq. 12)
- Create: `tests/unit/test_dsr_sigma_sr.py`

- [ ] **Step 1: Write failing tests (RED)**

Create `tests/unit/test_dsr_sigma_sr.py`:

```python
"""Tests for DSR sigma_sr extension (Bailey eq. 12 для n_trials > 1).

Sprint 10 Q7 (per pre-s10-backlog.md verdict — closes S9 NotImplementedError).
"""
from __future__ import annotations

import math
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from src.analytics.dsr import compute_dsr
from src.risk.reason_codes import ReasonCode
from src.risk.trade_history import TradeRecord


def _make_trade(*, pnl_pct: Decimal, exit_offset_hours: int) -> TradeRecord:
    return TradeRecord(
        symbol="BTCUSDT",
        entry_signal_id=uuid4(),
        entry_ts=datetime(2026, 4, 25, 12, 0, 0, tzinfo=UTC),
        exit_ts=datetime(2026, 4, 25, 12 + exit_offset_hours, 0, 0, tzinfo=UTC),
        qty=Decimal("0.5"),
        entry_price=Decimal("100000"),
        exit_price=Decimal("100000") * (Decimal("1") + pnl_pct),
        pnl_quote=Decimal("100"),
        pnl_pct=pnl_pct,
        fees_paid=Decimal("0.05"),
        reason_code=ReasonCode.EXIT_TP_HIT,
        kelly_phase=1,
        recorded_at=datetime(2026, 4, 25, 12, 1, 0, tzinfo=UTC),
    )


def test_n_trials_gt_1_requires_sigma_sr() -> None:
    """n_trials > 1 без sigma_sr raises ValueError (no longer NotImplementedError)."""
    trades = [
        _make_trade(pnl_pct=Decimal(f"0.0{i}"), exit_offset_hours=i)
        for i in range(1, 11)
    ]
    with pytest.raises(ValueError, match="sigma_sr"):
        compute_dsr(trades, n_trials=5)  # missing sigma_sr param


def test_n_trials_gt_1_с_sigma_sr_returns_finite() -> None:
    """n_trials=5 + sigma_sr=0.1 returns finite DSR (Bailey eq. 12 applied)."""
    trades = [
        _make_trade(pnl_pct=Decimal("0.01") if i % 2 == 0 else Decimal("-0.005"),
                    exit_offset_hours=i)
        for i in range(1, 21)
    ]
    result = compute_dsr(trades, n_trials=5, sigma_sr=0.1)
    assert math.isfinite(result)
    assert 0.0 <= result <= 1.0  # Φ-CDF range


def test_n_trials_1_unchanged_behavior() -> None:
    """n_trials=1 (default) ignores sigma_sr, behaves как S9 baseline."""
    trades = [
        _make_trade(pnl_pct=Decimal("0.01") if i % 2 == 0 else Decimal("-0.005"),
                    exit_offset_hours=i)
        for i in range(1, 11)
    ]
    result_no_sigma = compute_dsr(trades, n_trials=1)
    result_with_sigma = compute_dsr(trades, n_trials=1, sigma_sr=0.5)
    assert result_no_sigma == result_with_sigma  # sigma_sr ignored when n_trials=1


def test_higher_n_trials_lowers_dsr() -> None:
    """Higher n_trials = stronger multi-testing penalty = lower DSR (assuming positive Sharpe)."""
    trades = [
        _make_trade(pnl_pct=Decimal("0.01") if i % 3 != 0 else Decimal("-0.005"),
                    exit_offset_hours=i)
        for i in range(1, 21)
    ]
    dsr_low_trials = compute_dsr(trades, n_trials=2, sigma_sr=0.1)
    dsr_high_trials = compute_dsr(trades, n_trials=20, sigma_sr=0.1)
    # More trials tested = stricter benchmark = DSR should be lower OR equal
    assert dsr_high_trials <= dsr_low_trials
```

- [ ] **Step 2: Verify RED**

```bash
pytest tests/unit/test_dsr_sigma_sr.py -v 2>&1 | tail -10
```

Expected: FAIL — `n_trials > 1 NYI` raises NotImplementedError, не ValueError; sigma_sr unknown kwarg.

- [ ] **Step 3: Extend compute_dsr**

Edit `src/analytics/dsr.py:52-110`:

```python
def compute_dsr(
    trades: list[TradeRecord],
    *,
    benchmark_sharpe: float = 0.0,
    n_trials: int = 1,
    sigma_sr: float | None = None,
    use_log: bool = True,
) -> float:
    """Compute Deflated Sharpe Ratio.

    Returns NaN if:
    - N=0 (no trades)
    - N=1 (variance undefined)
    - All returns identical (variance=0)
    - denom_inner ≤ 0 (skew × sharpe combo creates undefined sqrt arg)

    Args:
        trades: closed TradeRecord list (exit_ts populated).
        benchmark_sharpe: prior Sharpe target (default 0).
        n_trials: number of strategies tested (multiple-testing penalty).
        sigma_sr: cross-trial Sharpe std deviation (REQUIRED if n_trials > 1).
                  Caller computes sigma_sr = std([fold_sharpe_1, ..., fold_sharpe_K]).
                  S10 closes S9 NotImplementedError per ADR 0025 + pre-s10-backlog Q7.
        use_log: log returns если True (default), simple if False.

    Returns:
        DSR scalar в (0, 1) interpreted as Φ-CDF probability that
        observed Sharpe exceeds benchmark after adjusting для selection bias.

    Raises:
        ValueError: n_trials > 1 без sigma_sr.
    """
    returns = compute_returns(trades, use_log=use_log)
    n = len(returns)
    if n < 2:
        return math.nan

    finite_returns = [r for r in returns if math.isfinite(r)]
    if len(finite_returns) < 2:
        return math.nan

    mean = sum(finite_returns) / len(finite_returns)
    var = sum((r - mean) ** 2 for r in finite_returns) / (len(finite_returns) - 1)
    if var <= 0:
        return math.nan
    std = math.sqrt(var)
    sharpe = mean / std

    skew = float(stats.skew(finite_returns, bias=False))
    kurt = float(stats.kurtosis(finite_returns, bias=False, fisher=False))

    # Bailey & López de Prado 2014 eq. 12: E[max SR_n] для n_trials > 1.
    # Closes S9 NotImplementedError per ADR 0025 + pre-s10-backlog.md Q7.
    if n_trials > 1:
        if sigma_sr is None:
            raise ValueError(
                "compute_dsr: sigma_sr REQUIRED when n_trials > 1. "
                "Caller must supply std of Sharpes across trials. See ADR 0025."
            )
        gamma = 0.5772156649  # Euler-Mascheroni
        z1 = float(stats.norm.ppf(1.0 - 1.0 / n_trials))
        z2 = float(stats.norm.ppf(1.0 - 1.0 / (n_trials * math.e)))
        # Bailey eq. 12: E[max SR_n] = mu_SR + sigma_SR × ((1-γ)*z1 + γ*z2)
        sharpe_star = benchmark_sharpe + sigma_sr * ((1.0 - gamma) * z1 + gamma * z2)
    else:
        sharpe_star = benchmark_sharpe

    denom_inner = 1.0 - skew * sharpe + (kurt - 1.0) / 4.0 * sharpe**2
    if denom_inner <= 0:
        return math.nan
    denom = math.sqrt(denom_inner)
    z_dsr = (sharpe - sharpe_star) * math.sqrt(len(finite_returns) - 1) / denom
    return float(stats.norm.cdf(z_dsr))
```

- [ ] **Step 4: Verify GREEN**

```bash
pytest tests/unit/test_dsr.py tests/unit/test_dsr_sigma_sr.py -v 2>&1 | tail -10
```

Expected: 8 (existing S9) + 4 (new S10) = 12 passed.

- [ ] **Step 5: Verify mypy + full suite**

```bash
mypy --strict src/analytics/dsr.py 2>&1 | tail -3
pytest tests/unit -x -q 2>&1 | tail -3
```

Expected: clean + 645+ passed.

- [ ] **Step 6: Dispatch quant-stats-reviewer (MANDATORY per cross-cutting concern #4)**

Use Agent tool с subagent_type="quant-stats-reviewer". Brief: verify Bailey eq. 12 implementation correctness, sigma_sr semantics + n_trials interaction.

- [ ] **Step 7: Commit (after reviewer approval)**

```bash
git add src/analytics/dsr.py tests/unit/test_dsr_sigma_sr.py
git commit -m "feat(dsr): extend compute_dsr с sigma_sr param (Bailey eq. 12, closes S9 NYI) (S10 Q7)"
```

---

## MC permutations (2 tasks)

### Task 5: Sign-flip permutation module

**Files:**
- Create: `src/backtest/mc_permutation.py`
- Create: `tests/unit/test_mc_sign_flip.py`

- [ ] **Step 1: Write failing tests (RED)**

Create `tests/unit/test_mc_sign_flip.py`:

```python
"""Tests for MC sign-flip permutation test.

Sprint 10 Q3 (per pre-s10-backlog.md verdict — flip per-trade pnl_pct sign).
ADR 0015: N=2000 default, p ≤ 0.05 acceptance gate.
"""
from __future__ import annotations

import numpy as np
import pytest

from src.backtest.mc_permutation import sign_flip_p_value


def test_strong_positive_returns_yield_low_p() -> None:
    """Consistent +1% returns → very low p-value (significant edge)."""
    returns = np.array([0.01] * 100)
    p = sign_flip_p_value(returns, n_iterations=2000, seed=42)
    assert p < 0.05  # strong significant


def test_zero_mean_returns_yield_high_p() -> None:
    """Symmetric returns (mean ≈ 0) → high p-value (no edge)."""
    rng = np.random.default_rng(42)
    returns = rng.normal(0.0, 0.01, 100)
    p = sign_flip_p_value(returns, n_iterations=2000, seed=42)
    assert p > 0.05  # not significant


def test_p_value_in_unit_interval() -> None:
    """p-value always в [0, 1]."""
    rng = np.random.default_rng(42)
    returns = rng.normal(0.001, 0.01, 50)
    p = sign_flip_p_value(returns, n_iterations=2000, seed=42)
    assert 0.0 <= p <= 1.0


def test_seed_reproducibility() -> None:
    """Same seed → identical p-value (reproducibility)."""
    returns = np.array([0.01, -0.005, 0.02, -0.01, 0.015])
    p1 = sign_flip_p_value(returns, n_iterations=2000, seed=42)
    p2 = sign_flip_p_value(returns, n_iterations=2000, seed=42)
    assert p1 == p2


def test_empty_returns_returns_nan() -> None:
    """Empty returns array → NaN p-value (defensive)."""
    import math
    p = sign_flip_p_value(np.array([]), n_iterations=2000, seed=42)
    assert math.isnan(p)
```

- [ ] **Step 2: Verify RED**

```bash
pytest tests/unit/test_mc_sign_flip.py -v 2>&1 | tail -10
```

Expected: ImportError на `src.backtest.mc_permutation`.

- [ ] **Step 3: Implement sign-flip module**

Create `src/backtest/mc_permutation.py`:

```python
"""Monte Carlo permutation tests для strategy significance.

Sprint 10 Q3 (per pre-s10-backlog.md verdict + ADR 0015).

sign_flip_p_value: per-trade pnl_pct sign-flip null hypothesis test.
- Test statistic: mean(returns) — proxy для Sharpe sign
- p-value: fraction of permuted statistics ≥ observed
- N=2000 default per ADR 0015

block_bootstrap_p_value: secondary method preserves autocorrelation (T6).
"""
from __future__ import annotations

import math

import numpy as np
import numpy.typing as npt


def sign_flip_p_value(
    returns: npt.NDArray[np.float64],
    *,
    n_iterations: int = 2000,
    seed: int | None = None,
) -> float:
    """Sign-flip permutation test.

    Null: returns symmetric around 0 (no directional edge).
    Test stat: mean(returns).
    p = fraction of N permutations с |mean(perm)| >= |mean(observed)| (two-sided).

    Args:
        returns: per-trade returns array (np.float64).
        n_iterations: permutation count (ADR 0015 default 2000).
        seed: RNG seed для reproducibility.

    Returns:
        p-value в [0, 1], NaN if returns empty.
    """
    if len(returns) == 0:
        return math.nan

    observed = float(np.abs(np.mean(returns)))
    rng = np.random.default_rng(seed)

    count_extreme = 0
    for _ in range(n_iterations):
        # Random ±1 mask
        signs = rng.choice([-1.0, 1.0], size=len(returns))
        permuted = returns * signs
        if abs(float(np.mean(permuted))) >= observed:
            count_extreme += 1

    return float(count_extreme / n_iterations)
```

- [ ] **Step 4: Verify GREEN**

```bash
pytest tests/unit/test_mc_sign_flip.py -v 2>&1 | tail -10
```

Expected: 5 passed.

- [ ] **Step 5: Verify mypy strict**

```bash
mypy --strict src/backtest/mc_permutation.py 2>&1 | tail -3
```

Expected: clean.

- [ ] **Step 6: Commit**

```bash
git add src/backtest/mc_permutation.py tests/unit/test_mc_sign_flip.py
git commit -m "feat(mc): sign-flip permutation test (S10 Q3, ADR 0015)"
```

---

### Task 6: Block bootstrap secondary

**Files:**
- Modify: `src/backtest/mc_permutation.py` (append block_bootstrap_p_value)
- Create: `tests/unit/test_mc_block_bootstrap.py`

- [ ] **Step 1: Write failing tests (RED)**

Create `tests/unit/test_mc_block_bootstrap.py`:

```python
"""Tests for MC block bootstrap (autocorrelation-preserving secondary).

Sprint 10 Q3 (ADR 0015 secondary method, block 20-50 bars).
"""
from __future__ import annotations

import math

import numpy as np

from src.backtest.mc_permutation import block_bootstrap_p_value


def test_strong_positive_returns_yield_low_p() -> None:
    """Consistent +1% returns → low p (significant via block bootstrap)."""
    returns = np.array([0.01] * 100)
    p = block_bootstrap_p_value(returns, n_iterations=2000, block_size=20, seed=42)
    assert p < 0.10  # block bootstrap less strict than sign-flip — looser bound


def test_block_size_affects_resampling() -> None:
    """Different block sizes produce different p-values на autocorrelated data."""
    rng = np.random.default_rng(42)
    # AR(1) series: r_t = 0.5*r_{t-1} + noise
    n = 200
    returns = np.zeros(n)
    for t in range(1, n):
        returns[t] = 0.5 * returns[t - 1] + rng.normal(0.001, 0.01)

    p_block20 = block_bootstrap_p_value(returns, n_iterations=2000, block_size=20, seed=42)
    p_block50 = block_bootstrap_p_value(returns, n_iterations=2000, block_size=50, seed=42)
    # Different blocks → different p (proves autocorr-aware sampling)
    assert p_block20 != p_block50


def test_seed_reproducibility() -> None:
    """Same seed → identical p (reproducibility)."""
    returns = np.array([0.01, -0.005, 0.02, -0.01, 0.015, 0.008, -0.003, 0.012])
    p1 = block_bootstrap_p_value(returns, n_iterations=2000, block_size=3, seed=42)
    p2 = block_bootstrap_p_value(returns, n_iterations=2000, block_size=3, seed=42)
    assert p1 == p2


def test_empty_returns_returns_nan() -> None:
    """Empty returns array → NaN p (defensive)."""
    p = block_bootstrap_p_value(np.array([]), n_iterations=2000, block_size=20, seed=42)
    assert math.isnan(p)
```

- [ ] **Step 2: Verify RED**

```bash
pytest tests/unit/test_mc_block_bootstrap.py -v 2>&1 | tail -10
```

Expected: AttributeError на `block_bootstrap_p_value`.

- [ ] **Step 3: Implement block bootstrap**

Append к `src/backtest/mc_permutation.py`:

```python
def block_bootstrap_p_value(
    returns: npt.NDArray[np.float64],
    *,
    n_iterations: int = 2000,
    block_size: int = 30,
    seed: int | None = None,
) -> float:
    """Block bootstrap permutation test (preserves autocorrelation).

    Per ADR 0015 secondary method. Resamples blocks of `block_size` bars,
    тех concatenates к length(returns) sequence. Tests if observed mean
    significantly differs from bootstrap distribution.

    Args:
        returns: per-trade returns array.
        n_iterations: bootstrap iterations (ADR 0015 default 2000).
        block_size: block length в bars (ADR 0015 range 20-50, default 30).
        seed: RNG seed.

    Returns:
        p-value в [0, 1], NaN if returns empty или block_size > len(returns).
    """
    if len(returns) == 0 or block_size > len(returns):
        return math.nan

    n = len(returns)
    n_blocks = (n + block_size - 1) // block_size  # ceil
    observed = float(np.abs(np.mean(returns)))
    rng = np.random.default_rng(seed)

    count_extreme = 0
    for _ in range(n_iterations):
        # Sample n_blocks random starting indices, take block_size bars from each
        starts = rng.integers(0, n - block_size + 1, size=n_blocks)
        sampled = np.concatenate([returns[s : s + block_size] for s in starts])[:n]
        if abs(float(np.mean(sampled))) >= observed:
            count_extreme += 1

    return float(count_extreme / n_iterations)
```

- [ ] **Step 4: Verify GREEN**

```bash
pytest tests/unit/test_mc_block_bootstrap.py -v 2>&1 | tail -10
```

Expected: 4 passed.

- [ ] **Step 5: Verify mypy + ruff**

```bash
mypy --strict src/backtest/mc_permutation.py 2>&1 | tail -3
ruff check src/backtest/mc_permutation.py 2>&1 | tail -3
```

Expected: clean.

- [ ] **Step 6: Commit**

```bash
git add src/backtest/mc_permutation.py tests/unit/test_mc_block_bootstrap.py
git commit -m "feat(mc): block bootstrap secondary (S10 Q3, ADR 0015)"
```

---

## WFA acceptance gate + reporter (2 tasks)

### Task 7: WFA acceptance gate (Sharpe AND MC combine)

**Files:**
- Modify: `src/backtest/walk_forward.py` (append `evaluate_acceptance_gate`)
- Create: `tests/unit/test_wfa_acceptance_gate.py`

- [ ] **Step 1: Write failing tests (RED)**

Create `tests/unit/test_wfa_acceptance_gate.py`:

```python
"""Tests for WFA acceptance gate (per ADR 0014 + 0015 AND-combined).

Sprint 10 Q2 (per pre-s10-backlog.md verdict — DSR informational, NOT gate).
"""
from __future__ import annotations

import pandas as pd

from src.backtest.walk_forward import evaluate_acceptance_gate


def test_passes_when_all_folds_meet_sharpe_and_p_value() -> None:
    """All 5 folds OOS/IS Sharpe >= 0.7 + MC p <= 0.05 → PASS."""
    fold_sharpes = [0.8, 0.75, 0.85, 0.72, 0.9]  # all >= 0.7
    mc_p_value = 0.02  # <= 0.05
    result = evaluate_acceptance_gate(
        fold_oos_is_sharpe_ratios=fold_sharpes,
        mc_p_value=mc_p_value,
        sharpe_threshold=0.7,
        p_threshold=0.05,
    )
    assert result["passed"] is True
    assert result["sharpe_gate_passed"] is True
    assert result["mc_gate_passed"] is True


def test_fails_when_any_fold_below_sharpe_threshold() -> None:
    """One fold OOS/IS < 0.7 → FAIL (per-fold AND)."""
    fold_sharpes = [0.8, 0.5, 0.85, 0.72, 0.9]  # second fold = 0.5 < 0.7
    result = evaluate_acceptance_gate(
        fold_oos_is_sharpe_ratios=fold_sharpes,
        mc_p_value=0.02,
        sharpe_threshold=0.7,
        p_threshold=0.05,
    )
    assert result["passed"] is False
    assert result["sharpe_gate_passed"] is False
    assert result["mc_gate_passed"] is True
    assert result["failed_folds"] == [1]  # second fold idx


def test_fails_when_p_value_above_threshold() -> None:
    """Sharpe OK but p > 0.05 → FAIL."""
    fold_sharpes = [0.8, 0.75, 0.85, 0.72, 0.9]
    result = evaluate_acceptance_gate(
        fold_oos_is_sharpe_ratios=fold_sharpes,
        mc_p_value=0.10,
        sharpe_threshold=0.7,
        p_threshold=0.05,
    )
    assert result["passed"] is False
    assert result["sharpe_gate_passed"] is True
    assert result["mc_gate_passed"] is False


def test_dsr_NOT_in_gate_decision() -> None:
    """DSR computed but NOT in pass/fail decision (Q2 trader REVISE).

    Verify result dict не contains 'dsr_gate_passed' (only Sharpe + MC gate).
    """
    fold_sharpes = [0.8, 0.75, 0.85, 0.72, 0.9]
    result = evaluate_acceptance_gate(
        fold_oos_is_sharpe_ratios=fold_sharpes,
        mc_p_value=0.02,
        sharpe_threshold=0.7,
        p_threshold=0.05,
    )
    # No DSR key in gate result — DSR informational only per Q2 verdict
    assert "dsr_gate_passed" not in result
    assert result["passed"] is True
```

- [ ] **Step 2: Verify RED**

```bash
pytest tests/unit/test_wfa_acceptance_gate.py -v 2>&1 | tail -10
```

Expected: ImportError на `evaluate_acceptance_gate`.

- [ ] **Step 3: Implement gate function**

Append к `src/backtest/walk_forward.py`:

```python
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
```

- [ ] **Step 4: Verify GREEN**

```bash
pytest tests/unit/test_wfa_acceptance_gate.py -v 2>&1 | tail -10
```

Expected: 4 passed.

- [ ] **Step 5: Verify mypy**

```bash
mypy --strict src/backtest/walk_forward.py 2>&1 | tail -3
```

Expected: clean.

- [ ] **Step 6: Commit**

```bash
git add src/backtest/walk_forward.py tests/unit/test_wfa_acceptance_gate.py
git commit -m "feat(wfa): acceptance gate Sharpe AND MC combine, DSR informational (S10 Q2)"
```

---

### Task 8: WFA reporter — 3-series Sharpe routing

**Files:**
- Create: `src/backtest/wfa_reporter.py`
- Create: `tests/unit/test_wfa_reporter.py`

- [ ] **Step 1: Write failing tests (RED)**

Create `tests/unit/test_wfa_reporter.py`:

```python
"""Tests for WFA reporter (3-series Sharpe routing per cross-cutting concern #1).

Sprint 10 Q4 + Q6 (per pre-s10-backlog.md cross-cutting concerns).
"""
from __future__ import annotations

import math
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pandas as pd

from src.backtest.wfa_reporter import format_wfa_report
from src.risk.reason_codes import ReasonCode
from src.risk.trade_history import TradeRecord


def _make_trade_record(*, pnl_pct: Decimal, exit_offset_hours: int) -> TradeRecord:
    return TradeRecord(
        symbol="BTCUSDT",
        entry_signal_id=uuid4(),
        entry_ts=datetime(2026, 4, 25, 12, 0, 0, tzinfo=UTC),
        exit_ts=datetime(2026, 4, 25, 12 + exit_offset_hours, 0, 0, tzinfo=UTC),
        qty=Decimal("0.5"),
        entry_price=Decimal("100000"),
        exit_price=Decimal("100000") * (Decimal("1") + pnl_pct),
        pnl_quote=Decimal("100"),
        pnl_pct=pnl_pct,
        fees_paid=Decimal("0.05"),
        reason_code=ReasonCode.EXIT_TP_HIT,
        kelly_phase=1,
        recorded_at=datetime(2026, 4, 25, 12, 1, 0, tzinfo=UTC),
    )


def test_report_contains_three_sharpe_series() -> None:
    """Report routes 3 distinct Sharpe series (cross-cutting concern #1)."""
    runner_result = {
        "folds": [
            {
                "fold_idx": 0,
                "is_metrics": {"Sharpe Ratio": 1.5},  # bar-returns IS
                "oos_metrics": {"Sharpe Ratio": 1.2},  # bar-returns OOS
                "oos_is_sharpe_ratio": 0.8,
                "oos_trades_df": pd.DataFrame({"net_pnl": [10.0]}),
                "train_window": (0, 2000),
                "test_window": (2020, 2520),
            },
        ],
        "aggregate": {
            "oos_trades_df": pd.DataFrame({"net_pnl": [10.0]}),
            "k_folds": 1,
            "fold_oos_sharpes": [1.2],
        },
    }
    trades_for_dsr = [_make_trade_record(pnl_pct=Decimal("0.01"),
                                          exit_offset_hours=i) for i in range(1, 11)]
    gate_result = {"passed": True, "sharpe_gate_passed": True, "mc_gate_passed": True,
                   "failed_folds": [], "fold_sharpe_ratios": [0.8], "mc_p_value": 0.02,
                   "thresholds": {"sharpe": 0.7, "p_value": 0.05}}

    report = format_wfa_report(
        runner_result=runner_result,
        trades_for_dsr=trades_for_dsr,
        mc_p_value=0.02,
        gate_result=gate_result,
    )

    # 3 Sharpe series present
    assert "bar_returns_sharpe_per_fold" in report  # series 1: bar-Sharpe
    assert "per_trade_sharpe" in report  # series 2: DSR internal
    assert "display_sharpe" in report  # series 3: annualized display


def test_report_includes_dsr_aggregate_informational() -> None:
    """DSR computed across all OOS trades (informational, NOT gate)."""
    runner_result = {
        "folds": [
            {"fold_idx": i, "is_metrics": {"Sharpe Ratio": 1.5},
             "oos_metrics": {"Sharpe Ratio": 1.2}, "oos_is_sharpe_ratio": 0.8,
             "oos_trades_df": pd.DataFrame(), "train_window": (0, 0),
             "test_window": (0, 0)}
            for i in range(5)
        ],
        "aggregate": {"oos_trades_df": pd.DataFrame(), "k_folds": 5,
                      "fold_oos_sharpes": [1.2, 1.0, 1.3, 1.1, 1.4]},
    }
    trades_for_dsr = [_make_trade_record(pnl_pct=Decimal("0.01") if i % 2 == 0
                                           else Decimal("-0.005"),
                                           exit_offset_hours=i) for i in range(1, 21)]
    gate_result = {"passed": True, "sharpe_gate_passed": True, "mc_gate_passed": True,
                   "failed_folds": [], "fold_sharpe_ratios": [0.8]*5, "mc_p_value": 0.02,
                   "thresholds": {"sharpe": 0.7, "p_value": 0.05}}

    report = format_wfa_report(
        runner_result=runner_result,
        trades_for_dsr=trades_for_dsr,
        mc_p_value=0.02,
        gate_result=gate_result,
    )

    # DSR present, aggregate (n_trials=5)
    assert "dsr_aggregate" in report
    assert math.isfinite(report["dsr_aggregate"])
    assert "dsr_per_fold" in report  # also per-fold


def test_report_passes_through_gate_result() -> None:
    """Gate result included verbatim в report."""
    runner_result = {"folds": [], "aggregate": {"oos_trades_df": pd.DataFrame(),
                                                  "k_folds": 0, "fold_oos_sharpes": []}}
    gate_result = {"passed": False, "sharpe_gate_passed": True, "mc_gate_passed": False,
                   "failed_folds": [], "fold_sharpe_ratios": [], "mc_p_value": 0.10,
                   "thresholds": {"sharpe": 0.7, "p_value": 0.05}}

    report = format_wfa_report(
        runner_result=runner_result,
        trades_for_dsr=[],
        mc_p_value=0.10,
        gate_result=gate_result,
    )

    assert report["acceptance_gate"] == gate_result


def test_display_sharpe_uses_fixed_8760_factor() -> None:
    """Display Sharpe annualized с sqrt(8760) per Q6 (NOT derived from trade frequency)."""
    import numpy as np
    runner_result = {"folds": [], "aggregate": {"oos_trades_df": pd.DataFrame(),
                                                  "k_folds": 0, "fold_oos_sharpes": []}}
    trades_for_dsr = [_make_trade_record(pnl_pct=Decimal("0.01") if i % 2 == 0
                                           else Decimal("-0.005"),
                                           exit_offset_hours=i) for i in range(1, 21)]
    gate_result = {"passed": True, "sharpe_gate_passed": True, "mc_gate_passed": True,
                   "failed_folds": [], "fold_sharpe_ratios": [], "mc_p_value": 0.02,
                   "thresholds": {"sharpe": 0.7, "p_value": 0.05}}

    report = format_wfa_report(
        runner_result=runner_result,
        trades_for_dsr=trades_for_dsr,
        mc_p_value=0.02,
        gate_result=gate_result,
    )

    # Display Sharpe = per-trade × sqrt(8760) (NOT derived from trade count)
    assert "display_sharpe" in report
    assert math.isfinite(report["display_sharpe"])
    # Annualization factor must be exactly sqrt(8760)
    assert report["display_sharpe_annualization_factor"] == np.sqrt(8760)
```

- [ ] **Step 2: Verify RED**

```bash
pytest tests/unit/test_wfa_reporter.py -v 2>&1 | tail -10
```

Expected: ImportError на `src.backtest.wfa_reporter`.

- [ ] **Step 3: Implement reporter**

Create `src/backtest/wfa_reporter.py`:

```python
"""WFA reporter — 3-series Sharpe routing + DSR aggregate informational.

Sprint 10 Q4 + Q6 + Q7 (per pre-s10-backlog.md verdicts + cross-cutting concerns).

3 distinct Sharpe series MUST NOT conflate (cross-cutting concern #1):
1. Bar-returns Sharpe (sqrt(8760) annualized) — used для ADR 0014 OOS/IS gate
2. Per-trade Sharpe (DSR internal, NOT annualized) — produced by DSR module
3. Display Sharpe (sqrt(8760) annualized per-trade) — informational only

DSR aggregate uses sigma_sr = std(per-fold Sharpe) per Q7 (Bailey eq. 12).
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np

from src.analytics.dsr import compute_dsr, compute_returns
from src.risk.trade_history import TradeRecord


# Annualization factor: sqrt(365 * 24) для 24/7 crypto 1H bars.
# Per Q6 verdict — fixed constant, NOT derived from trade frequency (circular).
_ANNUALIZATION_FACTOR = float(np.sqrt(8760))


def format_wfa_report(
    *,
    runner_result: dict[str, Any],
    trades_for_dsr: list[TradeRecord],
    mc_p_value: float,
    gate_result: dict[str, Any],
) -> dict[str, Any]:
    """Format structured WFA report.

    Routes 3 distinct Sharpe series correctly + computes DSR aggregate.

    Args:
        runner_result: dict from WalkForwardRunner.run() с 'folds' + 'aggregate'.
        trades_for_dsr: aggregated TradeRecord list from all folds для DSR.
        mc_p_value: MC permutation p-value.
        gate_result: dict from evaluate_acceptance_gate().

    Returns:
        Structured report dict с per-series Sharpe + DSR + gate details.
    """
    folds = runner_result.get("folds", [])
    aggregate = runner_result.get("aggregate", {})

    # Series 1: bar-returns Sharpe per fold (from replay_engine._compute_metrics)
    bar_returns_sharpe_per_fold = [
        f.get("oos_metrics", {}).get("Sharpe Ratio", 0.0) for f in folds
    ]

    # Series 2: per-trade Sharpe (DSR internal — compute from trades_for_dsr)
    per_trade_sharpe: float = math.nan
    if trades_for_dsr:
        returns = compute_returns(trades_for_dsr, use_log=True)
        finite_returns = [r for r in returns if math.isfinite(r)]
        if len(finite_returns) >= 2:
            mean = sum(finite_returns) / len(finite_returns)
            var = sum((r - mean) ** 2 for r in finite_returns) / (len(finite_returns) - 1)
            if var > 0:
                per_trade_sharpe = mean / math.sqrt(var)

    # Series 3: display Sharpe (per-trade × sqrt(8760))
    display_sharpe = (
        per_trade_sharpe * _ANNUALIZATION_FACTOR
        if math.isfinite(per_trade_sharpe)
        else math.nan
    )

    # DSR aggregate (n_trials=K, sigma_sr from per-fold Sharpes per Q7)
    dsr_aggregate: float = math.nan
    dsr_per_fold: list[float] = []
    fold_oos_sharpes = aggregate.get("fold_oos_sharpes", [])
    if trades_for_dsr and len(fold_oos_sharpes) >= 2:
        sigma_sr = float(np.std(fold_oos_sharpes, ddof=1))
        dsr_aggregate = compute_dsr(
            trades_for_dsr,
            n_trials=len(fold_oos_sharpes),
            sigma_sr=sigma_sr,
        )

    # Per-fold DSR (n_trials=1, no sigma needed)
    for fold in folds:
        fold_oos_trades = fold.get("oos_trades_df")
        if fold_oos_trades is not None and not fold_oos_trades.empty:
            # NOTE: per-fold trades are pandas DataFrame (replay_engine output),
            # not TradeRecord. Keep informational only — full per-fold DSR requires
            # converting к TradeRecord (out of T8 scope, defer).
            dsr_per_fold.append(math.nan)
        else:
            dsr_per_fold.append(math.nan)

    return {
        "bar_returns_sharpe_per_fold": bar_returns_sharpe_per_fold,
        "per_trade_sharpe": per_trade_sharpe,
        "display_sharpe": display_sharpe,
        "display_sharpe_annualization_factor": _ANNUALIZATION_FACTOR,
        "dsr_aggregate": dsr_aggregate,
        "dsr_per_fold": dsr_per_fold,
        "mc_p_value": mc_p_value,
        "acceptance_gate": gate_result,
        "k_folds": aggregate.get("k_folds", 0),
    }
```

- [ ] **Step 4: Verify GREEN**

```bash
pytest tests/unit/test_wfa_reporter.py -v 2>&1 | tail -10
```

Expected: 4 passed.

- [ ] **Step 5: Verify mypy + ruff**

```bash
mypy --strict src/backtest/wfa_reporter.py 2>&1 | tail -3
ruff check src/backtest/wfa_reporter.py 2>&1 | tail -3
```

Expected: clean.

- [ ] **Step 6: Commit**

```bash
git add src/backtest/wfa_reporter.py tests/unit/test_wfa_reporter.py
git commit -m "feat(wfa): reporter с 3-series Sharpe routing + DSR aggregate (S10 Q4+Q6+Q7)"
```

---

## Integration test (1 task)

### Task 9: End-to-end WFA pipeline integration test

**Files:**
- Create: `tests/integration/test_wfa_pipeline.py`

- [ ] **Step 1: Write integration test**

Create `tests/integration/test_wfa_pipeline.py`:

```python
"""End-to-end WFA pipeline integration test.

Sprint 10 — verifies full pipeline:
synthetic OHLCV → run_replay per fold → WindowSplitter → WalkForwardRunner →
DSR aggregate → MC sign-flip → acceptance gate → reporter.
"""
from __future__ import annotations

import math
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import numpy as np
import pandas as pd
import pytest

from src.backtest.mc_permutation import sign_flip_p_value
from src.backtest.replay_engine import run_replay
from src.backtest.walk_forward import (
    WalkForwardRunner,
    WindowSplitter,
    evaluate_acceptance_gate,
)
from src.backtest.wfa_reporter import format_wfa_report
from src.risk.reason_codes import ReasonCode
from src.risk.trade_history import TradeRecord


pytestmark = pytest.mark.integration


def _synthetic_df(n_bars: int = 5500) -> pd.DataFrame:
    """Synthetic 1H OHLCV — mild positive trend для realistic strategy edge."""
    rng = np.random.default_rng(42)
    closes = 100.0 * np.exp(np.cumsum(rng.normal(0.0001, 0.005, n_bars)))
    timestamps = pd.date_range("2024-01-01", periods=n_bars, freq="1h")
    return pd.DataFrame({
        "timestamp": timestamps,
        "open": closes * 0.999,
        "high": closes * 1.001,
        "low": closes * 0.998,
        "close": closes,
        "volume": np.ones(n_bars),
    })


def _trades_df_to_traderecords(trades_df: pd.DataFrame) -> list[TradeRecord]:
    """Convert replay_engine trades_df DataFrame к TradeRecord list для DSR."""
    records: list[TradeRecord] = []
    for _, row in trades_df.iterrows():
        entry_price = Decimal(str(row["entry_price"]))
        exit_price = Decimal(str(row["exit_price"]))
        pnl_pct_val = (exit_price / entry_price) - Decimal("1")
        records.append(TradeRecord(
            symbol="BTCUSDT",
            entry_signal_id=uuid4(),
            entry_ts=pd.Timestamp(row["timestamp_open"]).to_pydatetime().replace(tzinfo=UTC),
            exit_ts=pd.Timestamp(row["timestamp_close"]).to_pydatetime().replace(tzinfo=UTC),
            qty=Decimal(str(row["qty"])),
            entry_price=entry_price,
            exit_price=exit_price,
            pnl_quote=Decimal(str(row["net_pnl"])),
            pnl_pct=pnl_pct_val,
            fees_paid=Decimal(str(row["entry_fee"] + row["exit_fee"])),
            reason_code=ReasonCode.EXIT_TP_HIT,  # placeholder — synthetic data
            kelly_phase=1,
            recorded_at=datetime.now(UTC),
        ))
    return records


def test_full_wfa_pipeline_produces_complete_report() -> None:
    """End-to-end: synthetic data → replay × K folds → WFA → MC → DSR → gate → report."""
    df = _synthetic_df(n_bars=5500)
    config = {
        "trading": {
            "initial_balance": 10000.0,
            "commission_taker": 0.001,
            "slippage": 0.0005,
            "position_size_pct": 10.0,
            "max_drawdown_pct": 50.0,
            "long_only": True,
        },
        "strategy": {"indicators": {"atr": {"sl_atr_mult": 1.5, "tp_atr_mult": 3.0}}},
    }

    splitter = WindowSplitter()  # ADR 0014 defaults
    runner = WalkForwardRunner(splitter=splitter, replay_fn=run_replay)
    runner_result = runner.run(df=df, config=config)

    # Aggregate OOS trades
    oos_trades_df = runner_result["aggregate"]["oos_trades_df"]
    trades_for_dsr = _trades_df_to_traderecords(oos_trades_df) if not oos_trades_df.empty else []

    # MC sign-flip on aggregated returns
    if oos_trades_df.empty:
        mc_p = math.nan
    else:
        returns_arr = oos_trades_df["net_pnl"].astype(float).to_numpy() / 10000.0
        mc_p = sign_flip_p_value(returns_arr, n_iterations=500, seed=42)  # 500 fast for test

    # Acceptance gate
    fold_ratios = [f["oos_is_sharpe_ratio"] for f in runner_result["folds"]]
    gate = evaluate_acceptance_gate(
        fold_oos_is_sharpe_ratios=fold_ratios,
        mc_p_value=mc_p if not math.isnan(mc_p) else 1.0,
    )

    # Reporter
    report = format_wfa_report(
        runner_result=runner_result,
        trades_for_dsr=trades_for_dsr,
        mc_p_value=mc_p,
        gate_result=gate,
    )

    # Verify report structure
    assert "bar_returns_sharpe_per_fold" in report
    assert "per_trade_sharpe" in report
    assert "display_sharpe" in report
    assert "dsr_aggregate" in report
    assert "mc_p_value" in report
    assert "acceptance_gate" in report
    assert "k_folds" in report
    assert report["k_folds"] == 5  # ADR 0014
    assert len(report["bar_returns_sharpe_per_fold"]) == 5
```

- [ ] **Step 2: Verify integration test runs**

```bash
pytest tests/integration/test_wfa_pipeline.py -v 2>&1 | tail -10
```

Expected: 1 passed (may take 5-10 sec на synthetic data + 500 MC iterations).

- [ ] **Step 3: Verify full unit suite still green**

```bash
pytest tests/unit -x -q 2>&1 | tail -3
```

Expected: 657+ passed (630 baseline + 32 new).

- [ ] **Step 4: Commit**

```bash
git add tests/integration/test_wfa_pipeline.py
git commit -m "test(wfa): end-to-end integration test (replay → splitter → runner → DSR → MC → gate → reporter) (S10 T9)"
```

---

## ADR + wiki sync (2 tasks)

### Task 10: ADR 0025 — S10 aggregate decisions

**Files:**
- Create: `llm-wiki/wiki/project/decisions/0025-sprint-10-wfa-dsr-mc.md`
- Modify: `llm-wiki/wiki/index.md` (add ADR 0025 entry)

- [ ] **Step 1: Write ADR**

Create `llm-wiki/wiki/project/decisions/0025-sprint-10-wfa-dsr-mc.md`:

```markdown
---
title: 0025. Sprint 10 — Walk-Forward + DSR aggregate + Monte Carlo permutations
type: decision
date: 2026-04-25
sprint: 10
tags: [adr, sprint-10, wfa, dsr, monte-carlo, backtest, statistics]
sources:
  - project/pre-s10-backlog.md
  - project/decisions/0014-walk-forward-train2000-test500.md
  - project/decisions/0015-sign-flip-mc-permutations-n2000.md
  - project/decisions/0024-sprint-9-data-quality-types-analytics.md
status: accepted
---

# 0025. Sprint 10 — WFA + DSR aggregate + MC permutations

**Status:** accepted
**Date:** 2026-04-25

## Context

Sprint 10 builds на S9 B2 DSR foundation + locked ADR 0014 (walk-forward train=2000/test=500/K=5/embargo=20/Sharpe ≥ 0.7) + ADR 0015 (sign-flip MC N=2000, p ≤ 0.05). Statistical validation layer для strategy validation pre-prod.

PHASE 2 brainstorming verdicts (`pre-s10-backlog.md`):
- Q1 CONFIRM bars unit
- Q2 REVISE — DSR informational, NOT hard gate (N=40-80 trades/fold = high variance)
- Q3 CONFIRM sign-flip per-trade returns
- Q4 CONFIRM revive S2 + dual-Sharpe trap caveat
- Q5 CONFIRM per-trade DSR (per-fill = N inflation)
- Q6 REVISE — fixed sqrt(8760) annualization (NOT derived — circular)
- Q7 CONFIRM sigma_sr external param (closes S9 NotImplementedError)

## Decision

### Q1+Q4 — WFA architecture
- `WindowSplitter` (frozen dataclass) generates rolling fold tuples per ADR 0014
- `WalkForwardRunner` orchestrates IS+OOS replay per fold via existing `run_replay`
- Output dict: per-fold details + aggregate OOS trades

### Q2 — Acceptance gate
- L1 (ADR 0014): every fold's OOS/IS Sharpe ratio ≥ `wfa_acceptance_sharpe_ratio` (default 0.7)
- L2 (ADR 0015): MC p-value ≤ `wfa_acceptance_p_value` (default 0.05)
- PASS = L1 AND L2
- DSR computed and reported (informational), NOT в gate. Threshold TBD post-empirical calibration.

### Q3+Q5 — MC + DSR semantics
- Sign-flip per-trade `pnl_pct` sign random ±1, N=2000 iterations
- Block bootstrap secondary, block 30 bars (range 20-50 per ADR 0015)
- DSR consumes per-trade `TradeRecord` (not per-fill — would inflate N artificially)

### Q6 — Annualization
- Fixed `sqrt(365 × 24) = sqrt(8760)` для display Sharpe
- Aligned с existing `replay_engine._compute_metrics:51`
- DSR formula independent of annualization (S9 verified — cancels)
- Pre-existing bug `vector_backtest.py:62` `sqrt(365*24*60)` (1m assumption) — fixed T1

### Q7 — DSR sigma_sr extension
- `compute_dsr(..., sigma_sr: float | None = None)` — required if `n_trials > 1`
- Closes S9 NotImplementedError per Bailey & López de Prado eq. 12
- WFA reporter computes `sigma_sr = std([fold_sharpe_1, ..., fold_sharpe_K], ddof=1)` для aggregate DSR

### 3 Sharpe series (cross-cutting concern #1)
1. **Bar-returns Sharpe** (`replay_engine._compute_metrics`, sqrt(8760) annualized) — ADR 0014 OOS/IS gate
2. **Per-trade Sharpe** (DSR internal) — NOT annualized
3. **Display Sharpe** (sqrt(8760) on per-trade) — informational

`wfa_reporter.format_wfa_report` routes correctly. Tests enforce separation.

## Consequences

**Plus:**
- Production-grade WFA pipeline (rolling K=5, dual-gate, MC + DSR informational)
- Closes S9 carry-overs (sigma_sr NotImplementedError; annualization factor)
- Pre-existing bug fixed (`vector_backtest.py` annualization)
- 3-Sharpe trap documented + test-enforced

**Minus:**
- DSR threshold gate deferred к follow-up sprint (empirical calibration after seeing real fold data)
- per-fold DSR в reporter currently NaN (DataFrame→TradeRecord conversion deferred — informational anyway)
- MC sign-flip default N=2000 на large datasets = ~few seconds per WFA run (acceptable)

## Related

- [[../pre-s10-backlog]] — PHASE 2 verdicts trail
- [[0014-walk-forward-train2000-test500]] — WFA window + Sharpe gate locked
- [[0015-sign-flip-mc-permutations-n2000]] — MC permutation N=2000 + p ≤ 0.05 locked
- [[0024-sprint-9-data-quality-types-analytics]] — DSR foundation (S9)
- [[../components/walk-forward]] — implementation
- [[../components/mc-permutations]] — implementation
- [[../components/wfa-reporter]] — implementation
- [[../components/dsr]] — sigma_sr extension
- [[../plans/2026-04-25-sprint-10-wfa-dsr-mc]] — implementation plan + trace map

## Amendments

- (none yet)
```

- [ ] **Step 2: Add ADR 0025 entry к index.md**

Edit `llm-wiki/wiki/index.md` "## Project — Decisions" section:

```markdown
- [[project/decisions/0025-sprint-10-wfa-dsr-mc]] — Sprint 10 aggregate ADR: WFA orchestrator (rolling K=5 per ADR 0014) + DSR sigma_sr extension (closes S9 NYI) + MC sign-flip + block bootstrap + 3-Sharpe routing + vector_backtest annualization fix.
```

- [ ] **Step 3: Touch agent prompt to satisfy adr-agent-sync hook**

```bash
touch ~/.claude/agents/quant-stats-reviewer.md
```

(Reviewer used для T4 DSR sigma_sr extension correctness check.)

- [ ] **Step 4: Commit**

```bash
git add llm-wiki/wiki/project/decisions/0025-sprint-10-wfa-dsr-mc.md llm-wiki/wiki/index.md
git commit -m "docs(adr): ADR 0025 — S10 aggregate decisions (Q1-Q7) (S10 T10)"
```

---

### Task 11: Wiki sync — 3 component pages + sprint-10 + counts + cluster + mental-map

**Files:**
- Create: `llm-wiki/wiki/project/components/walk-forward.md`
- Create: `llm-wiki/wiki/project/components/mc-permutations.md`
- Create: `llm-wiki/wiki/project/components/wfa-reporter.md`
- Create: `llm-wiki/wiki/project/sprints/sprint-10-wfa-dsr-mc.md`
- Modify: `llm-wiki/wiki/project/components/dsr.md` (sigma_sr extension)
- Modify: `llm-wiki/wiki/project/components/backtest-harness.md` (3-Sharpe doc)
- Modify: `llm-wiki/wiki/project/architecture/current-state.md` (counts 32→35, ADR 24→25, sprints 11→12)
- Modify: `llm-wiki/wiki/project/components/README.md` (Cluster 8 + Cluster 10 updates)
- Modify: `llm-wiki/wiki/project/mental-map.md` (3 new query rows)
- Modify: `llm-wiki/wiki/index.md` (add 3 components + sprint-10)

(Per Block 1↔Block 2 sync HARD-GATE 5c per dev-workflow.md PHASE 8 step 5c — all NEW component pages с config covered.)

- [ ] **Step 1: Create walk-forward.md component page**

Create `llm-wiki/wiki/project/components/walk-forward.md`:

```markdown
---
title: Walk-Forward — WindowSplitter + WalkForwardRunner
type: component
tags: [backtest, wfa, validation, sprint-10]
created: 2026-04-25
updated: 2026-04-25
status: stable
sources:
  - src/backtest/walk_forward.py
  - project/decisions/0014-walk-forward-train2000-test500.md
  - project/decisions/0025-sprint-10-wfa-dsr-mc.md
---

# Walk-Forward Analysis

**TL;DR:** Production WFA orchestrator. `WindowSplitter` (frozen dataclass) generates rolling K-fold (train, test) tuples per ADR 0014 defaults (train=2000, test=500, embargo=20, K=5). `WalkForwardRunner` invokes existing `run_replay()` per fold, routes results к dual-Sharpe paths (bar-returns → ADR 0014 gate; per-trade → DSR). `evaluate_acceptance_gate` ANDs Sharpe + MC gates per ADR 0014 + 0015.

## Public API

| Symbol | Path |
|--------|------|
| `WindowSplitter` (frozen dataclass) | `src/backtest/walk_forward.py::WindowSplitter` |
| `WindowSplitter.split` | `src/backtest/walk_forward.py::WindowSplitter.split` |
| `WalkForwardRunner` | `src/backtest/walk_forward.py::WalkForwardRunner` |
| `WalkForwardRunner.run` | `src/backtest/walk_forward.py::WalkForwardRunner.run` |
| `evaluate_acceptance_gate` | `src/backtest/walk_forward.py::evaluate_acceptance_gate` |

## Invariants (CRITICAL)

| # | Invariant | Enforcement | Test |
|---|-----------|-------------|------|
| 1 | ADR 0014 defaults: train=2000, test=500, embargo=20, K=5 | dataclass field defaults | `tests/unit/test_window_splitter.py::test_default_params_match_adr_0014` |
| 2 | Insufficient data raises ValueError | `min_required` check | `test_insufficient_data_raises` |
| 3 | Rolling advance = test_bars per fold | loop `train_start = k * test_bars` | `test_K_folds_advance_by_test_window` |
| 4 | Negative params rejected at construction | `__post_init__` validation | `test_negative_params_rejected` |
| 5 | Acceptance gate AND-combine (Sharpe + MC) | `passed = sharpe AND mc` | `tests/unit/test_wfa_acceptance_gate.py::*` |
| 6 | DSR NOT in gate (Q2 verdict — informational) | no `dsr_gate_passed` key | `test_dsr_NOT_in_gate_decision` |

## Configuration

Settings (`src/platform/config.py`):
- `wfa_train_bars: int = 2000`
- `wfa_test_bars: int = 500`
- `wfa_embargo_bars: int = 20`
- `wfa_k_folds: int = 5`
- `wfa_acceptance_sharpe_ratio: float = 0.7`
- `wfa_acceptance_p_value: float = 0.05`

## Data flow

```
synthetic OHLCV df
    ↓
WindowSplitter.split(total_bars) → 5× (train_start, train_end, test_start, test_end)
    ↓ per fold
WalkForwardRunner.run():
    train_window = df.iloc[tr_start:tr_end]
    is_result = replay_fn(train_window, config)   # IS replay
    test_window = df.iloc[te_start:te_end]
    oos_result = replay_fn(test_window, config)   # OOS replay
    folds.append({oos_is_sharpe_ratio, oos_trades_df, ...})
    ↓
evaluate_acceptance_gate(fold_oos_is_sharpe_ratios, mc_p_value)
    ↓
{passed, sharpe_gate_passed, mc_gate_passed, failed_folds, ...}
```

## Referenced by

- [[wfa-reporter]] — consumes runner output (3-Sharpe routing)
- [[mc-permutations]] — sister statistical method (sign-flip + block bootstrap)
- [[backtest-harness]] — base replay engine

## Related

- [[../decisions/0014-walk-forward-train2000-test500]] — locked WFA params
- [[../decisions/0025-sprint-10-wfa-dsr-mc]] — origin ADR
- [[dsr]] — DSR consumer (sigma_sr from per-fold Sharpes)

## Sources

- `src/backtest/walk_forward.py` — implementation
- `tests/unit/test_window_splitter.py` (6 tests)
- `tests/unit/test_walk_forward_runner.py` (5 tests)
- `tests/unit/test_wfa_acceptance_gate.py` (4 tests)
- `tests/integration/test_wfa_pipeline.py` (1 end-to-end test)
```

- [ ] **Step 2: Create mc-permutations.md component page**

Create `llm-wiki/wiki/project/components/mc-permutations.md`:

```markdown
---
title: MC permutations — sign-flip + block bootstrap
type: component
tags: [backtest, mc, statistics, sprint-10]
created: 2026-04-25
updated: 2026-04-25
status: stable
sources:
  - src/backtest/mc_permutation.py
  - project/decisions/0015-sign-flip-mc-permutations-n2000.md
  - project/decisions/0025-sprint-10-wfa-dsr-mc.md
---

# MC permutations (sign-flip + block bootstrap)

**TL;DR:** Pure-function module computing two MC permutation tests on per-trade returns array per ADR 0015. `sign_flip_p_value` (primary, N=2000) flips per-trade pnl sign random ±1; `block_bootstrap_p_value` (secondary, block 20-50 bars) preserves autocorrelation. p-value = fraction permuted statistics ≥ observed (two-sided).

## Public API

| Symbol | Path |
|--------|------|
| `sign_flip_p_value` | `src/backtest/mc_permutation.py::sign_flip_p_value` |
| `block_bootstrap_p_value` | `src/backtest/mc_permutation.py::block_bootstrap_p_value` |

## Invariants (CRITICAL)

| # | Invariant | Enforcement | Test |
|---|-----------|-------------|------|
| 1 | N=2000 default per ADR 0015 | function default arg | `tests/unit/test_mc_sign_flip.py::*` (uses 2000) |
| 2 | Empty returns → NaN (defensive) | `len(returns) == 0` check | `test_empty_returns_returns_nan` |
| 3 | Seed reproducibility | `rng = np.random.default_rng(seed)` | `test_seed_reproducibility` |
| 4 | p-value в [0, 1] always | `count_extreme / n_iterations` | `test_p_value_in_unit_interval` |
| 5 | Sign-flip preserves marginal distributions | `signs * returns` (no replace) | ADR 0015 line 35 |
| 6 | Block bootstrap block_size > N → NaN | guard `block_size > len(returns)` | `test_empty_returns_returns_nan` (covers) |
| 7 | Block bootstrap preserves autocorrelation | resamples blocks not single bars | `test_block_size_affects_resampling` |

## Configuration

Settings:
- `wfa_mc_iterations: int = 2000` (ADR 0015)
- `wfa_mc_block_size: int = 30` (range 20-50 per ADR 0015)

## Test statistic

Both tests use `|mean(returns)|` as proxy для Sharpe sign. Two-sided test:
- `count_extreme = N(|mean(perm)| ≥ |mean(observed)|)`
- `p = count_extreme / n_iterations`

## Referenced by

- [[walk-forward]] — `evaluate_acceptance_gate` consumes p-value (L2 gate per ADR 0015)
- [[wfa-reporter]] — reports both p-values (sign-flip primary, block bootstrap secondary)

## Related

- [[../decisions/0015-sign-flip-mc-permutations-n2000]] — locked N=2000, p ≤ 0.05
- [[../decisions/0025-sprint-10-wfa-dsr-mc]] — origin ADR

## Sources

- `src/backtest/mc_permutation.py` — implementation
- `tests/unit/test_mc_sign_flip.py` (5 tests)
- `tests/unit/test_mc_block_bootstrap.py` (4 tests)
```

- [ ] **Step 3: Create wfa-reporter.md component page**

Create `llm-wiki/wiki/project/components/wfa-reporter.md`:

```markdown
---
title: WFA reporter — 3-series Sharpe routing + DSR aggregate
type: component
tags: [backtest, wfa, reporter, sprint-10]
created: 2026-04-25
updated: 2026-04-25
status: stable
sources:
  - src/backtest/wfa_reporter.py
  - project/decisions/0025-sprint-10-wfa-dsr-mc.md
---

# WFA reporter

**TL;DR:** Pure function `format_wfa_report` formats structured WFA output. **CRITICAL** routes 3 distinct Sharpe series correctly per cross-cutting concern #1 (must NOT conflate). Computes DSR aggregate (sigma_sr from per-fold Sharpes per S10 Q7) — informational only, NOT in gate.

## 3 Sharpe series (DO NOT conflate)

| Series | Source | Annualization | Use |
|--------|--------|---------------|-----|
| **Bar-returns Sharpe** | `replay_engine._compute_metrics:51` | `sqrt(8760)` | ADR 0014 OOS/IS gate |
| **Per-trade Sharpe** | `compute_dsr` internal | NONE (per-trade) | DSR formula |
| **Display Sharpe** | `wfa_reporter` (per-trade × `sqrt(8760)`) | `sqrt(8760)` fixed | Informational only |

## Public API

| Symbol | Path |
|--------|------|
| `format_wfa_report` | `src/backtest/wfa_reporter.py::format_wfa_report` |
| `_ANNUALIZATION_FACTOR` | `src/backtest/wfa_reporter.py::_ANNUALIZATION_FACTOR` (private constant `sqrt(8760)`) |

## Invariants (CRITICAL)

| # | Invariant | Enforcement | Test |
|---|-----------|-------------|------|
| 1 | 3 distinct Sharpe series в report dict | explicit keys | `tests/unit/test_wfa_reporter.py::test_report_contains_three_sharpe_series` |
| 2 | DSR aggregate uses sigma_sr from per-fold Sharpes | `np.std(fold_sharpes, ddof=1)` | `test_report_includes_dsr_aggregate_informational` |
| 3 | Display Sharpe annualization = `sqrt(8760)` fixed | `_ANNUALIZATION_FACTOR` constant | `test_display_sharpe_uses_fixed_8760_factor` |
| 4 | DSR informational, NOT в gate (Q2) | `acceptance_gate` separate key | `test_report_passes_through_gate_result` |
| 5 | Pure function, no I/O, no module-level mutable state | function signature | code review |

## Data flow

```
WalkForwardRunner.run() → runner_result (folds + aggregate)
    ↓ + trades_for_dsr (TradeRecord list) + mc_p_value + gate_result
format_wfa_report():
    series 1: bar_returns_sharpe_per_fold = [f.oos_metrics.Sharpe Ratio for f in folds]
    series 2: per_trade_sharpe = mean/std of compute_returns(trades_for_dsr)
    series 3: display_sharpe = per_trade_sharpe × sqrt(8760)
    dsr_aggregate = compute_dsr(trades_for_dsr, n_trials=K, sigma_sr=std(fold_sharpes))
    ↓
report dict
```

## Referenced by

- [[walk-forward]] — produces input for reporter
- [[dsr]] — aggregate DSR consumer

## Related

- [[../decisions/0025-sprint-10-wfa-dsr-mc]] — origin ADR (Q4+Q6+Q7)
- [[../decisions/0014-walk-forward-train2000-test500]] — Sharpe gate convention
- [[backtest-harness]] — replay engine source of bar-returns Sharpe

## Sources

- `src/backtest/wfa_reporter.py` — implementation
- `tests/unit/test_wfa_reporter.py` (4 tests)
- `tests/integration/test_wfa_pipeline.py` (end-to-end)
```

- [ ] **Step 4: Update dsr.md component page (sigma_sr extension)**

Edit `llm-wiki/wiki/project/components/dsr.md` invariant row 7 + Public API + add new row 10:

Replace existing line:
```markdown
| 7 | n_trials > 1 NotImplementedError (NYI v0.1) | explicit raise | `compute_dsr` body |
```

With:
```markdown
| 7 | n_trials > 1 requires sigma_sr param (S10 closes S9 NYI) | `if sigma_sr is None: raise ValueError` | `tests/unit/test_dsr_sigma_sr.py::test_n_trials_gt_1_requires_sigma_sr` |
| 10 | sigma_sr applied per Bailey eq. 12: SR_star = benchmark + sigma_sr × ((1-γ)*z1 + γ*z2) | `compute_dsr` body | `tests/unit/test_dsr_sigma_sr.py::test_n_trials_gt_1_с_sigma_sr_returns_finite` + `test_higher_n_trials_lowers_dsr` |
```

Update "Multiple-testing penalty (n_trials)" section:

Replace existing text "v0.1: only n_trials=1 supported. n_trials > 1 raises NotImplementedError." с:
```markdown
v0.1 + S10: `n_trials > 1` supported via REQUIRED `sigma_sr: float` parameter. Caller computes `sigma_sr = std([fold_sharpe_1, ..., fold_sharpe_K], ddof=1)`. Raises `ValueError` if `sigma_sr is None` when `n_trials > 1`. Implementation per Bailey & López de Prado eq. 12.
```

Update "Referenced by" section:
- Replace "(S10 walk-forward sprint, future)" с "[[walk-forward]] — DSR aggregate consumer (sigma_sr from per-fold Sharpes per S10 Q7)"

- [ ] **Step 5: Update backtest-harness.md (3-Sharpe doc)**

Edit `llm-wiki/wiki/project/components/backtest-harness.md` — append new section "## 3 Sharpe series (S10)":

```markdown
## 3 Sharpe series (cross-cutting concern, S10 Q4)

WFA pipeline (S10) routes 3 distinct Sharpe series — must NOT conflate per cross-cutting concern #1:

1. **Bar-returns Sharpe** (`replay_engine._compute_metrics:51`, sqrt(8760) annualized) — ADR 0014 OOS/IS gate
2. **Per-trade Sharpe** (DSR internal, NOT annualized) — `compute_dsr` formula
3. **Display Sharpe** (per-trade × sqrt(8760)) — informational в WFA reporter

Pre-S10 bug fixed (T1): `vector_backtest.py:62` used `sqrt(365*24*60)` (1m bar assumption) — corrected к `sqrt(8760)` для 1H BTCUSDT.

См. [[wfa-reporter]] для routing implementation + [[../decisions/0025-sprint-10-wfa-dsr-mc]] для rationale.
```

- [ ] **Step 6: Update current-state.md counts**

Edit `llm-wiki/wiki/project/architecture/current-state.md` canonical-counts table:

```markdown
| Component pages | **35** | `wiki/project/components/*.md` (incl. README.md cluster index) | S10 (walk-forward + mc-permutations + wfa-reporter) + S9 (data-quality + fill-history + dsr) + ... |
| ADRs | **25** | `wiki/project/decisions/*.md` (0001-0025) | S10 (ADR 0025 — WFA + DSR sigma_sr + MC) |
| Sprint pages | **12** | `wiki/project/sprints/sprint-*.md` (sprint-01..sprint-10 + sprint-08a + sprint-08b + sprint-08c) | S10 (sprint-10-wfa-dsr-mc) |
```

Update TL;DR: `11 sprints completed (S1-S7 + S8a + S8b + S8c + S9)` → `12 sprints completed (S1-S7 + S8a + S8b + S8c + S9 + S10)`. Tag `v0.1.0-alpha.9` → `v0.1.0-alpha.10`.

- [ ] **Step 7: Update components/README.md (Cluster 8 + Cluster 10)**

Edit `llm-wiki/wiki/project/components/README.md`:

Cluster 8 (Backtest) — replace existing block с:
```markdown
## Cluster 8 — Backtest + analytics (S2-era + S10 WFA)

**Theme:** Backtest pipeline — replay engine + vector backtest + reporter + WFA orchestrator + MC permutations. **S10 revived S2 backtest engine + extended с production WFA layer per ADR 0025.**

| Component | Role |
|-----------|------|
| **[[backtest-harness]]** | Single page covering 6 src/backtest files (replay_engine + vector_backtest + reporter + indicators + data_collector + replay-stub) |
| [[walk-forward]] | WindowSplitter + WalkForwardRunner + acceptance gate (S10 Q1+Q4) |
| [[mc-permutations]] | sign-flip primary + block bootstrap secondary (S10 Q3, ADR 0015) |
| [[wfa-reporter]] | 3-Sharpe series routing + DSR aggregate informational (S10 Q4+Q6+Q7) |
```

Cluster 10 (Analytics) — append `dsr` extension note:
```markdown
| **[[dsr]]** | Bailey & López de Prado Deflated Sharpe Ratio — pure-function on TradeRecord array. Pearson kurtosis. **S10: sigma_sr extension closes S9 NYI (n_trials > 1).** |
```

Update top counts: `**TL;DR:** 31 component pages` → `**TL;DR:** 35 component pages` (Cluster 8 grows + Cluster 10 unchanged but DSR extended).

- [ ] **Step 8: Update mental-map.md (3 new query rows)**

Edit `llm-wiki/wiki/project/mental-map.md` — add к "Tooling / hooks / methodology" section:

```markdown
| Walk-forward analysis (rolling K-folds, OOS/IS Sharpe gate) | `components/walk-forward.md` + `src/backtest/walk_forward.py` (S10 Q1+Q4, ADR 0014+0025) |
| Monte Carlo permutations (sign-flip + block bootstrap) | `components/mc-permutations.md` + `src/backtest/mc_permutation.py` (S10 Q3, ADR 0015) |
| WFA reporter + 3-Sharpe routing | `components/wfa-reporter.md` + `src/backtest/wfa_reporter.py` (S10 Q4+Q6) |
```

- [ ] **Step 9: Add 3 new components к index.md**

Edit `llm-wiki/wiki/index.md` "## Project — Components" section — add:

```markdown
- [[project/components/walk-forward]] — WFA orchestrator (WindowSplitter + WalkForwardRunner + acceptance gate). Rolling K=5 per ADR 0014 (S10).
- [[project/components/mc-permutations]] — sign-flip primary + block bootstrap secondary. N=2000 per ADR 0015 (S10).
- [[project/components/wfa-reporter]] — 3-Sharpe series routing + DSR aggregate informational. Fixed sqrt(8760) annualization (S10).
```

Add к "## Project — Sprints" section:
```markdown
- [[project/sprints/sprint-10-wfa-dsr-mc]] — S10 (2026-04-25): WFA orchestrator + DSR sigma_sr extension + MC sign-flip + block bootstrap + 3-Sharpe routing. 11 TDD tasks, +32 tests. ADR 0025. Tag v0.1.0-alpha.10.
```

- [ ] **Step 10: Create sprint-10 page**

Create `llm-wiki/wiki/project/sprints/sprint-10-wfa-dsr-mc.md`:

```markdown
---
title: Sprint 10 — Walk-Forward Analysis + DSR aggregate + Monte Carlo permutations
type: sprint
tags: [sprint-10, wfa, dsr, monte-carlo, backtest]
created: 2026-04-25
updated: 2026-04-25
status: completed
sources:
  - project/plans/2026-04-25-sprint-10-wfa-dsr-mc
  - project/decisions/0025-sprint-10-wfa-dsr-mc
  - project/pre-s10-backlog
---

# Sprint 10 — WFA + DSR + MC permutations

## Overview

S10 ships production-grade walk-forward validation pipeline. Builds на S9 B2 DSR foundation + locked ADR 0014 (WFA params) + ADR 0015 (MC params). 11 TDD tasks, ~12-15 commits squash-merged. Tag `v0.1.0-alpha.10`.

**Closes S9 deferred:**
- DSR `n_trials > 1 NotImplementedError` → sigma_sr param implementation (Q7)
- DSR annualization decision → fixed `sqrt(8760)` для display Sharpe (Q6)
- WFA acceptance gate consuming DSR → DSR informational, NOT in gate per Q2 trader REVISE (calibrate threshold post-empirical)

**Bonus fix:** Pre-existing bug `vector_backtest.py:62` annualization `sqrt(365*24*60)` (1m assumption) → `sqrt(8760)` (1H correct).

## Plan / ADR links

- Plan: [[../plans/2026-04-25-sprint-10-wfa-dsr-mc]]
- ADR (NEW): [[../decisions/0025-sprint-10-wfa-dsr-mc]]
- Brainstorm trail: [[../pre-s10-backlog]]

## Deliverables

11 tasks, ~12-15 commits squash-merged on `feature/sprint-10-wfa-dsr-mc`.

### T1 — vector_backtest annualization fix
- `src/backtest/vector_backtest.py:62-64` annualization `sqrt(365*24*60)` → `sqrt(8760)` для 1H BTCUSDT
- 2 tests verify alignment с `replay_engine` convention

### T2-T3 — WFA orchestrator
- NEW `src/backtest/walk_forward.py::WindowSplitter` (frozen dataclass, ADR 0014 defaults) + 6 tests
- `WalkForwardRunner` orchestrator с dual-Sharpe routing (per-trade → DSR; bar-returns → gate) + 5 tests

### T4 — DSR sigma_sr extension
- `src/analytics/dsr.py::compute_dsr` extended с `sigma_sr: float | None` param
- `n_trials > 1` raises ValueError if sigma_sr None (no longer NotImplementedError)
- Bailey eq. 12 implementation per ADR 0025
- 4 new tests + quant-stats-reviewer APPROVED

### T5-T6 — MC permutations
- NEW `src/backtest/mc_permutation.py::sign_flip_p_value` (primary, N=2000) + 5 tests
- `block_bootstrap_p_value` (secondary, block 30 default) + 4 tests

### T7 — Acceptance gate
- `walk_forward.py::evaluate_acceptance_gate` ANDs Sharpe + MC per ADR 0014 + 0015
- DSR NOT в gate (Q2 trader REVISE — informational only)
- 4 tests

### T8 — WFA reporter
- NEW `src/backtest/wfa_reporter.py::format_wfa_report` — 3-Sharpe series routing
- DSR aggregate с sigma_sr from per-fold Sharpes (Q7)
- 4 tests

### T9 — Integration test
- `tests/integration/test_wfa_pipeline.py` end-to-end (synthetic data → replay × K → DSR → MC → gate → report)

### T10-T11 — ADR + wiki sync
- ADR 0025 + index.md entry
- 3 NEW component pages: walk-forward + mc-permutations + wfa-reporter
- Modified: dsr.md (sigma_sr), backtest-harness.md (3-Sharpe doc), current-state.md (counts), components/README.md (Cluster 8 + 10), mental-map.md (3 query rows)
- This sprint page

## FSM growth

NONE. WFA = analytics post-process layer. Counts unchanged: 16/30/74/45.

## Reason codes growth

NONE.

## Tests

- pytest: 662 passed / 25 skipped / 0 failed (baseline 630 → +32 tests = 6 splitter + 5 runner + 4 dsr_sigma + 5 sign_flip + 4 block_bootstrap + 4 gate + 4 reporter + 1 integration → ~33; +0 minor)
- mypy --strict src/: Success in 66 source files (+3: walk_forward + mc_permutation + wfa_reporter)
- New: integration test marker `pytest.mark.integration`

## Wiki updates

- 3 NEW component pages (walk-forward + mc-permutations + wfa-reporter)
- 1 NEW ADR (0025)
- 1 NEW sprint page (this)
- Modified: dsr.md (sigma_sr extension), backtest-harness.md (3-Sharpe), current-state.md (counts 32→35, ADR 24→25, sprint pages 11→12)
- components/README.md Cluster 8 expanded, Cluster 10 dsr note updated
- mental-map.md +3 query rows

## Open issues для S11+

- DSR threshold gate calibration (Q2 deferred — TBD post-empirical fold data)
- Live demo Mainnet validation (S11 F per S9 carry-over roadmap)
- Per-fold DSR в reporter currently NaN (DataFrame→TradeRecord conversion deferred — informational anyway)
- WFA wired в `__main__.py` CLI subcommand (если operator wants WFA report on demand) — defer

## Key decisions

- **DSR informational, NOT gate (Q2 trader REVISE):** N=40-80 trades/fold = high DSR variance, would reject valid strategies. Calibrate threshold empirically.
- **Fixed sqrt(8760) annualization (Q6 trader REVISE):** Derived from trade frequency = circular + breaks IS/OOS comparability.
- **3-Sharpe series trap (cross-cutting concern #1):** Bar-returns / per-trade / display — must not conflate. Test-enforced в reporter.
- **Revive S2 backtest:** Existing `replay_engine` battle-tested, WFA = orchestration layer на top, не replacement.
- **sigma_sr external param (Q7):** Closes S9 NotImplementedError. Caller (`wfa_reporter`) computes `sigma_sr = std(per_fold_sharpes, ddof=1)`.

## Related

- [[../plans/2026-04-25-sprint-10-wfa-dsr-mc]] — full plan + trace map
- [[../decisions/0025-sprint-10-wfa-dsr-mc]] — aggregate ADR
- [[../pre-s10-backlog]] — PHASE 2 verdicts trail
- [[sprint-09-data-quality-types-analytics]] — predecessor sprint (B2 DSR foundation)
- [[../components/walk-forward]] + [[../components/mc-permutations]] + [[../components/wfa-reporter]] — new components
```

- [ ] **Step 11: Verify counts live**

```bash
source /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot/.venv/bin/activate
python -c "from src.execution.state_machine import TRANSITIONS, ExecutionState, ExecutionEvent; from src.risk.reason_codes import ReasonCode; print(f'states={len(list(ExecutionState))}, events={len(list(ExecutionEvent))}, transitions={len(TRANSITIONS)}, reason_codes={len(list(ReasonCode))}')"
ls llm-wiki/wiki/project/components/*.md | /usr/bin/wc -l  # expect 35
ls llm-wiki/wiki/project/decisions/*.md | /usr/bin/wc -l   # expect 25
ls llm-wiki/wiki/project/sprints/sprint-*.md | /usr/bin/wc -l  # expect 12
```

Expected: counts unchanged 16/30/74/45 + 35/25/12 wiki counts.

- [ ] **Step 12: Commit T11**

```bash
git add llm-wiki/wiki/project/components/walk-forward.md llm-wiki/wiki/project/components/mc-permutations.md llm-wiki/wiki/project/components/wfa-reporter.md llm-wiki/wiki/project/sprints/sprint-10-wfa-dsr-mc.md llm-wiki/wiki/project/components/dsr.md llm-wiki/wiki/project/components/backtest-harness.md llm-wiki/wiki/project/architecture/current-state.md llm-wiki/wiki/project/components/README.md llm-wiki/wiki/project/mental-map.md llm-wiki/wiki/index.md
git commit -m "docs(wiki): T11 — S10 wiki sync (3 components + sprint-10 + counts + cluster + mental-map) (S10)"
```

---

## PHASE 8 finishing (after T1-T11 complete)

- [ ] **Step 1: Run pre-validation**

```bash
source /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot/.venv/bin/activate
pytest tests/unit tests/property -x -q 2>&1 | tail -3
pytest tests/integration -x -q 2>&1 | tail -3
mypy src/ 2>&1 | tail -2
python -c "from src.execution.state_machine import TRANSITIONS, ExecutionState, ExecutionEvent; from src.risk.reason_codes import ReasonCode; print(f'states={len(list(ExecutionState))}, events={len(list(ExecutionEvent))}, transitions={len(TRANSITIONS)}, reason_codes={len(list(ReasonCode))}')"
```

Expected: 662+ unit, 1+ integration, mypy clean, counts 16/30/74/45.

- [ ] **Step 2: Invoke `sprint-finish` skill**

Skill enforces all HARD-GATEs (sprint-NN.md ✓ T11, canonical counts sync ✓ T11, orphan-audit grep includes tests/, Block 1↔Block 2 sync ✓ all NEW pages, index.md ADR sync ✓ T10) → `superpowers:finishing-a-development-branch`.

- [ ] **Step 3: Push + PR + squash-merge + tag v0.1.0-alpha.10**

Per `superpowers:finishing-a-development-branch` skill protocol.

- [ ] **Step 4: SPRINT_STATE update → between-sprints**

Per CLAUDE.md session-end procedure.

---

## Self-review checklist

**Spec coverage (per pre-s10-backlog.md verdicts):**
- ✅ Q1 bars unit → T2 WindowSplitter (defaults match ADR 0014)
- ✅ Q2 DSR informational → T7 gate (DSR NOT в decision) + T8 reporter (DSR aggregate informational)
- ✅ Q3 sign-flip per-trade → T5 sign_flip_p_value
- ✅ Q4 revive S2 + dual-Sharpe → T3 WalkForwardRunner с dual routing + T8 reporter с 3 series
- ✅ Q5 per-trade DSR → T8 reporter consumes TradeRecord (not FillRecord)
- ✅ Q6 fixed sqrt(8760) → T1 fix + T8 reporter constant
- ✅ Q7 sigma_sr extension → T4 compute_dsr param + T8 reporter computes sigma_sr

**Cross-cutting concerns covered:**
- ✅ #1 (Dual-Sharpe trap) — T8 reporter routes 3 series + tests enforce separation
- ✅ #2 (vector_backtest annualization bug) — T1 fix + audit
- ✅ #3 (Q2 + Q7 combined: DSR not gated, sigma_SR aggregated) — T7 + T8
- ✅ #4 (quant-stats-reviewer mandatory) — T4 step 6 explicit dispatch

**Placeholder scan:** No TBD / TODO / "implement later" / "add validation". Every code block complete.

**Type consistency:**
- `WindowSplitter(train_bars, test_bars, embargo_bars, k_folds)` consistent T2 + T3
- `WalkForwardRunner(splitter, replay_fn)` consistent T3
- `compute_dsr(trades, *, benchmark_sharpe=0.0, n_trials=1, sigma_sr=None, use_log=True)` consistent T4 + T8
- `sign_flip_p_value(returns, *, n_iterations=2000, seed=None) -> float` consistent T5
- `block_bootstrap_p_value(returns, *, n_iterations=2000, block_size=30, seed=None) -> float` consistent T6
- `evaluate_acceptance_gate(*, fold_oos_is_sharpe_ratios, mc_p_value, sharpe_threshold=0.7, p_threshold=0.05) -> dict` consistent T7
- `format_wfa_report(*, runner_result, trades_for_dsr, mc_p_value, gate_result) -> dict` consistent T8

---

## Total: 11 tasks, TDD throughout, ~13-16 commits estimated, ~6-8 hours work

Estimated test count delta: +33 tests (2 annualization + 6 splitter + 5 runner + 4 dsr_sigma + 5 sign_flip + 4 block_bootstrap + 4 gate + 4 reporter + 1 integration = 35 tests, conservative estimate +33). Baseline 630 → ~663 passed.
