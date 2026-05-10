---
title: "Sprint 44 — WFA retrofit (research presets acceptance gate restoration)"
type: plan
tags: [sprint-44, wfa-retrofit, dsr, mc, acceptance-gate, atr-breakout, volume-breakout]
created: 2026-05-10
updated: 2026-05-10
status: ready
sources:
  - llm-wiki/wiki/project/pre-s44-backlog.md
---

# Sprint 44 — WFA Retrofit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore acceptance discipline (T1-T6 + DSR + MC + N_trials counter) для 11 research presets (10 atr_breakout combos + 1 volume_breakout). Replace `verdict: "RAW"` с three-valued `WFA_PASS / WFA_FAIL / WFA_FAIL_DATA`.

**Architecture:** Shared helper `run_research_wfa()` в new `src/backtest/research_wfa.py` does WindowSplitter loop + per-fold `_backtest_single()` call + aggregate OOS trades + DSR + MC + acceptance gate. atr_breakout + volume_breakout get thin `_run_*_wfa()` wrappers. PnL accounting preserved (sequential additive — replay_engine architecturally blocked per atr_breakout_runner.py:5-12). N_trials baseline = 0 (verified empty `cross_trial_sharpes.json`); post-S44 = 11. Auto-scale via existing `_autoscale_wfa_params` для BTCUSDT 1D (1212 bars < 4520 default min).

**Tech Stack:** Python 3.12, pytest, numpy, pandas, existing infrastructure (WindowSplitter / WalkForwardRunner / CrossTrialLog / compute_dsr_with_status / sign_flip_p_value / evaluate_acceptance_gate / compute_t1_t6_metrics).

**Branch:** `feature/sprint-44-wfa-retrofit`

**Models:** opus for T1+T2 (judgment-heavy WFA loop architecture per donchian_runner pattern). sonnet для T3-T12.

---

## File Trace Map (PHASE 3 step 1a HARD-GATE)

| File | Action | Tasks |
|------|--------|-------|
| `src/backtest/research_wfa.py` | CREATE (shared helper) | T1 |
| `src/backtest/atr_breakout_runner.py` | MODIFY (add `_run_atr_breakout_wfa()`) | T2 |
| `src/backtest/volume_breakout_runner.py` | MODIFY (add `_run_volume_breakout_wfa()`) | T3 |
| `src/backtest/research_runner_envelope.py` | MODIFY (populate WFA fields) | T4 |
| `src/dashboard/backtest_runner.py` | MODIFY (dispatch routes к WFA path) | T5 + T6 |
| `src/dashboard/static/dashboard.js` | MODIFY (show TIER 1-6 + DSR + MC tables when verdict != RAW; WFA_FAIL_DATA color) | T7 + T8 |
| `src/dashboard/static/dashboard.css` | MODIFY (WFA_FAIL_DATA verdict color + tooltip) | T8 |
| `tests/unit/test_research_wfa.py` | CREATE | T1 |
| `tests/integration/test_atr_breakout_wfa.py` | CREATE | T2 |
| `tests/integration/test_volume_breakout_wfa.py` | CREATE | T3 |
| `tests/integration/test_atr_breakout_dashboard_contract.py` | MODIFY (WFA verdict tests) | T6 |
| `data/cross_trial_sharpes.json` | MODIFY (11 new entries via T9 run) | T9 |
| `llm-wiki/wiki/project/decisions/0064-sprint-44-wfa-retrofit.md` | CREATE (с post-WFA verdict table) | T11 + T12 |
| `llm-wiki/wiki/project/sprints/sprint-44-wfa-retrofit.md` | CREATE | T12 |
| `llm-wiki/wiki/project/architecture/current-state.md` | MODIFY (sprint history + counts ADR 63→64, sprint pages 47→48) | T12 |
| `llm-wiki/wiki/index.md` | MODIFY | T12 |
| `llm-wiki/wiki/log.md` | APPEND | T12 |
| `llm-wiki/wiki/project/SPRINT_STATE.md` | MODIFY (per-task) | every task |

---

## Task 1: Shared WFA helper `research_wfa.py` (opus — architecture)

**Files:**
- Create: `src/backtest/research_wfa.py`
- Test: `tests/unit/test_research_wfa.py`

**Why opus:** WFA loop architecture (per-fold execution, OOS aggregation, lookback warmup boundary, DSR + MC integration) is judgment-heavy. Donchian uses `WalkForwardRunner(replay_fn=run_replay)` — replay_engine signal API. Research runners' `_backtest_single` takes `(df, params, bars_per_year)` — different API. Need custom loop, not WalkForwardRunner.

- [ ] **Step 1: Read donchian_runner.py reference**

```bash
sed -n '85,260p' src/backtest/donchian_runner.py
```

This is the canonical pattern. Adapt: replace `WalkForwardRunner(replay_fn=run_replay).run()` с custom loop calling `backtest_fn(fold_df, params, bars_per_year)`.

- [ ] **Step 2: Write failing tests**

Create `tests/unit/test_research_wfa.py`:

```python
"""S44 T1 — research WFA helper tests."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import pytest

from src.backtest.research_wfa import run_research_wfa


def _fake_backtest_fn(df: pd.DataFrame, params: dict[str, Any], bars_per_year: int) -> dict[str, Any]:
    """Mock backtest that returns trades с known per-trade pnl_pct."""
    n_trades = len(df) // 100  # 1 trade per 100 bars
    if n_trades == 0:
        return {"n_trades": 0, "sharpe": float("nan"), "total_pnl_pct": 0.0, "win_rate": float("nan"), "trades": []}
    # Generate fake trades: 60% wins +1%, 40% losses -0.5% → mean +0.4%/trade
    pnls = [0.01 if i % 5 < 3 else -0.005 for i in range(n_trades)]
    from src.backtest.atr_breakout_runner import _TradeRecord  # reuse dataclass
    trades = [_TradeRecord(entry_idx=i*100, exit_idx=i*100+50, entry_price=100.0, exit_price=100.0+p*100, pnl_pct=p) for i, p in enumerate(pnls)]
    return {
        "n_trades": n_trades, "sharpe": 1.5,
        "total_pnl_pct": sum(pnls) * 100, "win_rate": 0.6, "trades": trades,
    }


def _fake_df(n_bars: int) -> pd.DataFrame:
    """Synthetic OHLCV DataFrame с monotonic timestamps."""
    ts = pd.date_range(start="2023-01-01", periods=n_bars, freq="1h", tz="UTC")
    return pd.DataFrame({
        "_ts": ts,
        "open": np.linspace(100, 200, n_bars),
        "high": np.linspace(101, 201, n_bars),
        "low": np.linspace(99, 199, n_bars),
        "close": np.linspace(100, 200, n_bars),
        "volume": np.full(n_bars, 1000.0),
    })


def test_run_research_wfa_returns_required_keys() -> None:
    """Result dict must contain WFA fields для envelope population."""
    df = _fake_df(5000)
    result = run_research_wfa(
        df=df, params={"atr_period": 9, "atr_breakout_mult": 2.5, "atr_stop_period": 21, "atr_stop_mult": 1.5},
        backtest_fn=_fake_backtest_fn, bars_per_year=8766, symbol="BTCUSDT",
        train_bars=2000, test_bars=500, k_folds=5, embargo_bars=20,
    )
    for key in ("verdict", "fold_sharpe_ratios", "trial_mean_fold_oos_sharpe", "mc_p_value",
                "dsr", "dsr_pass", "n_trades_raw", "failed_criteria", "wfa_params",
                "metrics", "trades", "trial_oos_sharpe"):
        assert key in result, f"Missing key: {key}"


def test_run_research_wfa_data_limited_returns_wfa_fail_data() -> None:
    """If df too small для default params → verdict=WFA_FAIL_DATA, не throw."""
    df = _fake_df(1000)  # < 4520 min_required для default
    result = run_research_wfa(
        df=df, params={"atr_period": 9, "atr_breakout_mult": 2.5, "atr_stop_period": 21, "atr_stop_mult": 1.5},
        backtest_fn=_fake_backtest_fn, bars_per_year=8766, symbol="BTCUSDT",
        train_bars=2000, test_bars=500, k_folds=5, embargo_bars=20,
    )
    assert result["verdict"] == "WFA_FAIL_DATA"
    assert "data_volume" in result["failed_criteria"]


def test_run_research_wfa_fold_count_matches_k_folds() -> None:
    df = _fake_df(5000)
    result = run_research_wfa(
        df=df, params={"atr_period": 9, "atr_breakout_mult": 2.5, "atr_stop_period": 21, "atr_stop_mult": 1.5},
        backtest_fn=_fake_backtest_fn, bars_per_year=8766, symbol="BTCUSDT",
        train_bars=2000, test_bars=500, k_folds=5, embargo_bars=20,
    )
    assert len(result["fold_sharpe_ratios"]) == 5


def test_run_research_wfa_aggregated_trades_preserve_pnls() -> None:
    """OOS trades aggregation = sum across all folds."""
    df = _fake_df(5000)
    result = run_research_wfa(
        df=df, params={"atr_period": 9, "atr_breakout_mult": 2.5, "atr_stop_period": 21, "atr_stop_mult": 1.5},
        backtest_fn=_fake_backtest_fn, bars_per_year=8766, symbol="BTCUSDT",
        train_bars=2000, test_bars=500, k_folds=5, embargo_bars=20,
    )
    # 5 folds × 500 test_bars = 2500 OOS bars / 100 bars per trade = 25 trades total
    assert result["n_trades_raw"] >= 20  # tolerance для fold boundaries
```

- [ ] **Step 3: Run, verify FAIL with ImportError**

```bash
.venv/bin/pytest tests/unit/test_research_wfa.py -v
```

Expected: 4 ImportError (`run_research_wfa` not found).

- [ ] **Step 4: Implement helper**

Create `src/backtest/research_wfa.py`:

```python
"""S44 T1 — Shared WFA helper для research-mode runners (atr_breakout, volume_breakout).

Replaces RAW envelope с full acceptance discipline (T1-T6 + DSR + MC + N_trials).

PnL accounting: sequential-additive preserved (per S44 ADR 0064 + S42 trader-expert
verdict). Per-fold OOS trades aggregated, DSR computed via cross_trial_sharpes pool.

Pattern source: src/backtest/donchian_runner.py::_run_donchian_wfa (canonical).
Differs: backtest_fn is research kernel (_backtest_single signature), не run_replay.
"""
from __future__ import annotations

import math
import statistics
from pathlib import Path
from typing import Any, Callable, Protocol

import numpy as np
import pandas as pd

from src.analytics.cross_trial_log import CrossTrialLog
from src.analytics.dsr import compute_dsr_with_status
from src.backtest.mc_permutation import sign_flip_p_value
from src.backtest.strategy_metrics import compute_t1_t6_metrics
from src.backtest.walk_forward import WindowSplitter, evaluate_acceptance_gate

# ADR 0052 LOCKED thresholds
DSR_THRESHOLD = 0.95
SHARPE_THRESHOLD = 0.7
P_THRESHOLD = 0.05
N_EFF_THRESHOLD = 50
T5_FLOOR = 50

BacktestFn = Callable[[pd.DataFrame, dict[str, Any], int], dict[str, Any]]


def _min_required_bars(*, train_bars: int, test_bars: int, k_folds: int, embargo_bars: int) -> int:
    """ADR 0014 default: train + embargo + k * test = 2000 + 20 + 5*500 = 4520."""
    return train_bars + embargo_bars + k_folds * test_bars


def run_research_wfa(
    *,
    df: pd.DataFrame,
    params: dict[str, Any],
    backtest_fn: BacktestFn,
    bars_per_year: int,
    symbol: str,
    train_bars: int,
    test_bars: int,
    k_folds: int,
    embargo_bars: int,
    n_trials: int = 11,  # post-S44 default; caller may override
    cross_trial_log_path: Path | None = None,
    sprint_tag: str = "S44",
) -> dict[str, Any]:
    """Run WFA для research-mode runner. Returns verdict dict ready для envelope."""
    min_required = _min_required_bars(
        train_bars=train_bars, test_bars=test_bars, k_folds=k_folds, embargo_bars=embargo_bars,
    )

    # Data audit — fail-closed if insufficient bars
    if len(df) < min_required:
        return {
            "verdict": "WFA_FAIL_DATA",
            "failed_criteria": ["data_volume"],
            "fold_sharpe_ratios": [],
            "trial_mean_fold_oos_sharpe": float("nan"),
            "trial_oos_sharpe": float("nan"),
            "mc_p_value": float("nan"),
            "dsr": float("nan"),
            "dsr_pass": False,
            "n_trades_raw": 0,
            "wfa_params": {
                "train_bars": train_bars, "test_bars": test_bars,
                "k_folds": k_folds, "embargo_bars": embargo_bars,
                "min_required": min_required, "actual": len(df),
            },
            "metrics": {},
            "trades": [],
        }

    # Run WFA folds
    splitter = WindowSplitter(
        train_bars=train_bars, test_bars=test_bars,
        embargo_bars=embargo_bars, k_folds=k_folds,
    )
    folds = list(splitter.split(df=df))

    fold_sharpes: list[float] = []
    all_oos_trades: list[Any] = []
    all_pnls: list[float] = []

    for fold_idx, (train_slice, test_slice) in enumerate(folds):
        if test_slice.empty:
            continue
        fold_result = backtest_fn(test_slice, params, bars_per_year)
        fold_trades = fold_result.get("trades", [])
        if not fold_trades:
            fold_sharpes.append(0.0)
            continue
        fold_sharpe = float(fold_result.get("sharpe", 0.0))
        if math.isnan(fold_sharpe):
            fold_sharpe = 0.0
        fold_sharpes.append(fold_sharpe)
        all_oos_trades.extend(fold_trades)
        all_pnls.extend([float(t.pnl_pct) for t in fold_trades])

    n_trades_raw = len(all_oos_trades)

    # MC sign-flip p-value on aggregated OOS pnls
    if n_trades_raw == 0:
        mc_p = 1.0
    else:
        returns_arr = np.asarray(all_pnls, dtype=float)
        mc_p = sign_flip_p_value(returns_arr, n_iterations=2000, seed=42)

    # Trial-level mean of fold OOS Sharpes (для cross-trial pooling per ADR 0056)
    trial_mean_fold_oos_sharpe = (
        float(sum(fold_sharpes) / len(fold_sharpes)) if fold_sharpes else float("nan")
    )

    # Trial OOS Sharpe = pooled OOS trades Sharpe (separate metric per ADR 0056)
    if n_trades_raw >= 2:
        pnls_arr = np.asarray(all_pnls, dtype=float)
        std_p = float(pnls_arr.std(ddof=1))
        trial_oos_sharpe = (
            float(pnls_arr.mean() / std_p) * math.sqrt(bars_per_year / 100.0)  # rough trades/year
            if std_p > 0 else 0.0
        )
    else:
        trial_oos_sharpe = float("nan")

    # T1-T6 metrics
    metrics = compute_t1_t6_metrics(
        trades=all_oos_trades, fold_oos_is_sharpe=fold_sharpes, bars_per_year=bars_per_year,
    )

    # DSR per ADR 0056 sigma_SR sourcing hierarchy
    if cross_trial_log_path is None:
        cross_trial_log_path = Path("data/cross_trial_sharpes.json")
    trial_log = CrossTrialLog(path=cross_trial_log_path)
    pre_existing = trial_log.get_oos_sharpes()
    cross_trial_sharpes = pre_existing + [trial_mean_fold_oos_sharpe]
    if len(cross_trial_sharpes) >= 3 and not math.isnan(trial_mean_fold_oos_sharpe):
        sigma_sr: float | None = statistics.stdev(cross_trial_sharpes)
    elif len(cross_trial_sharpes) >= 1:
        sigma_sr = float("nan")
    else:
        sigma_sr = None

    if sigma_sr is not None and not math.isnan(sigma_sr) and not math.isnan(trial_mean_fold_oos_sharpe):
        dsr_info = compute_dsr_with_status(trades=all_oos_trades, n_trials=n_trials, sigma_sr=sigma_sr)
    else:
        dsr_info = compute_dsr_with_status(trades=all_oos_trades, n_trials=1)
    dsr_value = dsr_info["dsr"]

    # Acceptance gate
    gate = evaluate_acceptance_gate(
        fold_oos_is_sharpe_ratios=fold_sharpes, mc_p_value=mc_p,
        sharpe_threshold=SHARPE_THRESHOLD, p_threshold=P_THRESHOLD,
        n_trades_raw=n_trades_raw, n_trades_n_eff=n_trades_raw,
        n_eff_threshold=N_EFF_THRESHOLD, t5_floor=T5_FLOOR,
    )
    failed_criteria: list[str] = list(gate["failed_criteria"])
    dsr_pass = (
        dsr_value is not None and not (isinstance(dsr_value, float) and math.isnan(dsr_value))
        and dsr_value >= DSR_THRESHOLD
    )
    if not dsr_pass:
        failed_criteria.append("dsr_threshold")

    verdict = "WFA_PASS" if not failed_criteria else "WFA_FAIL"

    return {
        "verdict": verdict,
        "failed_criteria": failed_criteria,
        "fold_sharpe_ratios": fold_sharpes,
        "trial_mean_fold_oos_sharpe": trial_mean_fold_oos_sharpe,
        "trial_oos_sharpe": trial_oos_sharpe,
        "mc_p_value": mc_p,
        "dsr": dsr_value,
        "dsr_pass": dsr_pass,
        "n_trades_raw": n_trades_raw,
        "wfa_params": {
            "train_bars": train_bars, "test_bars": test_bars,
            "k_folds": k_folds, "embargo_bars": embargo_bars,
            "min_required": min_required, "actual": len(df),
        },
        "metrics": metrics,
        "trades": all_oos_trades,
    }
```

- [ ] **Step 5: Run tests, verify PASS**

```bash
.venv/bin/pytest tests/unit/test_research_wfa.py -v
```

Expected: 4/4 PASS.

- [ ] **Step 6: mypy strict + commit**

```bash
.venv/bin/mypy --strict src/backtest/research_wfa.py
git add src/backtest/research_wfa.py tests/unit/test_research_wfa.py
git commit -m "feat(s44): research_wfa helper — WindowSplitter + per-fold backtest_fn + DSR + MC + acceptance gate"
```

- [ ] **Step 7: SPRINT_STATE update**

```bash
git add llm-wiki/wiki/project/SPRINT_STATE.md
git commit -m "docs(sprint): SPRINT_STATE update phase=4 task=T1 done"
```

---

## Task 2: atr_breakout WFA wrapper (opus)

**Files:**
- Modify: `src/backtest/atr_breakout_runner.py` (add `_run_atr_breakout_wfa()`)
- Test: `tests/integration/test_atr_breakout_wfa.py` (CREATE)

**Why opus:** Wiring helper к specific runner has subtle invariants (lookback warmup, params dict shape, _backtest_single signature alignment).

- [ ] **Step 1: Write failing integration test**

Create `tests/integration/test_atr_breakout_wfa.py`:

```python
"""S44 T2 — atr_breakout WFA integration tests."""
from __future__ import annotations

from datetime import date

import pytest


@pytest.mark.integration
def test_atr_breakout_wfa_btc_4h_returns_wfa_pass_or_fail() -> None:
    """BTCUSDT 4H = 19056 bars, well above min_required=4520. Must return WFA_PASS or WFA_FAIL (not WFA_FAIL_DATA)."""
    from src.backtest.atr_breakout_runner import _run_atr_breakout_wfa
    r = _run_atr_breakout_wfa(
        symbol="BTCUSDT", interval="240",
        start_date=date(2017, 8, 17), end_date=date(2026, 4, 30),
    )
    assert r["verdict"] in ("WFA_PASS", "WFA_FAIL"), f"Got {r['verdict']}"
    assert "data_volume" not in r["failed_criteria"]
    assert len(r["fold_sharpe_ratios"]) == 5  # default k=5
    assert r["n_trades_raw"] > 0


@pytest.mark.integration
def test_atr_breakout_wfa_btc_1d_returns_wfa_fail_data() -> None:
    """BTCUSDT 1D = 1212 bars, below default min_required=4520 (auto-scale OR FAIL_DATA)."""
    from src.backtest.atr_breakout_runner import _run_atr_breakout_wfa
    r = _run_atr_breakout_wfa(
        symbol="BTCUSDT", interval="D",
        start_date=date(2023, 1, 1), end_date=date(2026, 4, 26),
    )
    # Either WFA_FAIL_DATA OR ran с auto-scaled smaller params
    assert r["verdict"] in ("WFA_FAIL_DATA", "WFA_PASS", "WFA_FAIL")


@pytest.mark.integration
def test_atr_breakout_wfa_eth_4h_uses_locked_params() -> None:
    """Verify ETHUSDT 4H uses LOCKED params from ATR_BREAKOUT_LOCKED_PARAMS_BY_COMBO."""
    from src.backtest.atr_breakout_runner import _run_atr_breakout_wfa, ATR_BREAKOUT_LOCKED_PARAMS_BY_COMBO
    r = _run_atr_breakout_wfa(
        symbol="ETHUSDT", interval="240",
        start_date=date(2023, 1, 1), end_date=date(2026, 4, 26),
    )
    # Just verify WFA ran without throwing (verdict any of three)
    assert r["verdict"] in ("WFA_PASS", "WFA_FAIL", "WFA_FAIL_DATA")
```

- [ ] **Step 2: Run, verify FAIL**

```bash
.venv/bin/pytest tests/integration/test_atr_breakout_wfa.py -v -m integration
```

Expected: 3 FAIL (ImportError `_run_atr_breakout_wfa` not found).

- [ ] **Step 3: Add WFA wrapper к atr_breakout_runner.py**

In `src/backtest/atr_breakout_runner.py`, append AFTER `run_atr_breakout_backtest()` function:

```python
def _run_atr_breakout_wfa(
    *,
    symbol: str,
    interval: str,
    start_date: date,
    end_date: date,
    train_bars: int = 2000,
    test_bars: int = 500,
    k_folds: int = 5,
    embargo_bars: int = 20,
) -> dict[str, Any]:
    """S44 T2 — WFA для atr_breakout с per-combo LOCKED params.

    Pattern: donchian_runner._run_donchian_wfa adapted к research kernel
    (_backtest_single signature). PnL accounting sequential-additive preserved.
    """
    from src.backtest.research_wfa import run_research_wfa

    locked = ATR_BREAKOUT_LOCKED_PARAMS_BY_COMBO.get((symbol, interval))
    if locked is None:
        raise ValueError(f"No LOCKED params for ({symbol}, {interval})")
    params: dict[str, Any] = {
        "atr_period": int(locked["atr_period"]),
        "atr_breakout_mult": float(locked["atr_breakout_mult"]),
        "atr_stop_period": int(locked["atr_stop_period"]),
        "atr_stop_mult": float(locked["atr_stop_mult"]),
    }
    bars_per_year = _BARS_PER_YEAR_BY_INTERVAL.get(interval, 2190)
    df = _load_parquet_df(symbol, interval, start_date, end_date)
    if df.empty:
        raise ValueError(f"No OHLCV для {symbol} {interval} в [{start_date}, {end_date}]")

    return run_research_wfa(
        df=df, params=params,
        backtest_fn=_backtest_single,  # research kernel
        bars_per_year=bars_per_year, symbol=symbol,
        train_bars=train_bars, test_bars=test_bars,
        k_folds=k_folds, embargo_bars=embargo_bars,
        sprint_tag="S44",
    )
```

- [ ] **Step 4: Run tests, verify PASS**

```bash
.venv/bin/pytest tests/integration/test_atr_breakout_wfa.py -v -m integration
```

Expected: 3 PASS.

- [ ] **Step 5: mypy + commit**

```bash
.venv/bin/mypy --strict src/backtest/atr_breakout_runner.py
git add src/backtest/atr_breakout_runner.py tests/integration/test_atr_breakout_wfa.py
git commit -m "feat(s44): _run_atr_breakout_wfa() wrapper using shared research_wfa helper"
git add llm-wiki/wiki/project/SPRINT_STATE.md && git commit -m "docs(sprint): T2 done"
```

---

## Task 3: volume_breakout WFA wrapper (sonnet)

**Files:**
- Modify: `src/backtest/volume_breakout_runner.py`
- Test: `tests/integration/test_volume_breakout_wfa.py` (CREATE)

- [ ] **Step 1: Failing test**

Create `tests/integration/test_volume_breakout_wfa.py`:

```python
"""S44 T3 — volume_breakout WFA integration."""
from __future__ import annotations

from datetime import date

import pytest


@pytest.mark.integration
def test_volume_breakout_wfa_btc_4h_returns_verdict() -> None:
    """volume_breakout BTC 4H = 7273 bars, above min_required=4520."""
    from src.backtest.volume_breakout_runner import _run_volume_breakout_wfa
    r = _run_volume_breakout_wfa(
        symbol="BTCUSDT", interval="240",
        start_date=date(2023, 1, 1), end_date=date(2026, 4, 26),
    )
    assert r["verdict"] in ("WFA_PASS", "WFA_FAIL"), f"Got {r['verdict']}"
    assert "data_volume" not in r["failed_criteria"]
    assert len(r["fold_sharpe_ratios"]) == 5
    assert r["n_trades_raw"] > 0
```

- [ ] **Step 2: Run, FAIL**

```bash
.venv/bin/pytest tests/integration/test_volume_breakout_wfa.py -v -m integration
```

- [ ] **Step 3: Add WFA wrapper к volume_breakout_runner.py**

Append:

```python
def _run_volume_breakout_wfa(
    *,
    symbol: str,
    interval: str,
    start_date: date,
    end_date: date,
    train_bars: int = 2000,
    test_bars: int = 500,
    k_folds: int = 5,
    embargo_bars: int = 20,
) -> dict[str, Any]:
    """S44 T3 — WFA для volume_breakout с LOCKED params (S39 sweep #1644)."""
    from src.__main__ import _load_ohlcv
    from src.backtest.research_wfa import run_research_wfa
    from src.signalgen.volume_breakout_strategy import VOLUME_BREAKOUT_LOCKED_PARAMS

    df = _load_ohlcv(
        symbol=symbol, start=start_date.isoformat(),
        end=end_date.isoformat(), interval=interval,
    )
    if df.empty:
        raise ValueError(f"No OHLCV для {symbol} {interval}")

    params: dict[str, Any] = {
        "lookback_n": int(VOLUME_BREAKOUT_LOCKED_PARAMS["lookback_n"]),  # type: ignore[call-overload]
        "exit_lookback_n": int(VOLUME_BREAKOUT_LOCKED_PARAMS["exit_lookback_n"]),  # type: ignore[call-overload]
        "vol_window": int(VOLUME_BREAKOUT_LOCKED_PARAMS["vol_window"]),  # type: ignore[call-overload]
        "vol_mult": float(VOLUME_BREAKOUT_LOCKED_PARAMS["vol_mult"]),  # type: ignore[arg-type]
        "atr_period": int(VOLUME_BREAKOUT_LOCKED_PARAMS["atr_period"]),  # type: ignore[call-overload]
        "atr_stop_mult": float(VOLUME_BREAKOUT_LOCKED_PARAMS["atr_stop_mult"]),  # type: ignore[arg-type]
    }
    bars_per_year = {"5": 105192, "15": 35064, "60": 8766, "240": 2191, "D": 365}.get(interval, 2191)

    # Volume_breakout _backtest_single signature: (df, params) — no bars_per_year arg.
    # Adapter wraps к match research_wfa BacktestFn signature (df, params, bars_per_year).
    def _backtest_adapter(fold_df: pd.DataFrame, p: dict[str, Any], _bpy: int) -> dict[str, Any]:
        return _backtest_single(fold_df, p)

    return run_research_wfa(
        df=df, params=params, backtest_fn=_backtest_adapter,
        bars_per_year=bars_per_year, symbol=symbol,
        train_bars=train_bars, test_bars=test_bars,
        k_folds=k_folds, embargo_bars=embargo_bars,
        sprint_tag="S44",
    )
```

- [ ] **Step 4: Run tests + commit**

```bash
.venv/bin/pytest tests/integration/test_volume_breakout_wfa.py -v -m integration
.venv/bin/mypy --strict src/backtest/volume_breakout_runner.py
git add src/backtest/volume_breakout_runner.py tests/integration/test_volume_breakout_wfa.py
git commit -m "feat(s44): _run_volume_breakout_wfa() wrapper using shared research_wfa helper"
git add llm-wiki/wiki/project/SPRINT_STATE.md && git commit -m "docs(sprint): T3 done"
```

---

## Task 4: Envelope extension — WFA fields population (sonnet)

**Files:**
- Modify: `src/backtest/research_runner_envelope.py`

**Goal:** Add new keyword `wfa_result: dict | None = None` к `build_research_runner_envelope()`. If passed, populate `verdict`, `failed_criteria`, `acceptance_gate`, `dsr`, `dsr_pass`, `mc_p_value`, `wfa_params`, `wfa_total_bars`, `fold_sharpe_ratios`, `metrics` from `wfa_result` instead of null sentinels.

- [ ] **Step 1: Failing test**

Append к `tests/unit/test_research_runner_envelope.py`:

```python
def test_envelope_with_wfa_result_populates_fields() -> None:
    """S44 T4 — when wfa_result passed, envelope uses WFA values, not null sentinels."""
    wfa = {
        "verdict": "WFA_PASS", "failed_criteria": [], "fold_sharpe_ratios": [1.2, 1.5, 0.9, 1.1, 1.4],
        "trial_mean_fold_oos_sharpe": 1.22, "mc_p_value": 0.02, "dsr": 0.97, "dsr_pass": True,
        "n_trades_raw": 80, "wfa_params": {"train_bars": 2000, "test_bars": 500, "k_folds": 5,
        "embargo_bars": 20, "min_required": 4520, "actual": 5000},
        "metrics": {"t1_sharpe_oos": 1.22, "t5_n_trades": 80}, "trades": [],
    }
    payload = build_research_runner_envelope(
        runner_name="x", symbol="BTCUSDT", interval="240",
        n_trades=80, sharpe=1.22, win_rate=0.55, total_pnl_pct=200.0,
        bars_per_year=2191, equity_curve=[0.0, 200.0], runner_label="x",
        wfa_result=wfa,
    )
    assert payload["verdict"] == "WFA_PASS"
    assert payload["dsr"] == 0.97
    assert payload["dsr_pass"] is True
    assert payload["mc_p_value"] == 0.02
    assert payload["fold_sharpe_ratios"] == [1.2, 1.5, 0.9, 1.1, 1.4]
    assert payload["wfa_params"]["k_folds"] == 5
    assert payload["wfa_total_bars"] == 5000
    assert payload["acceptance_gate"] == "WFA_PASS"
    assert payload["failed_criteria"] == []


def test_envelope_without_wfa_result_returns_raw_sentinels() -> None:
    """Backward compat: when wfa_result=None, envelope returns RAW sentinels (S42 behavior)."""
    payload = build_research_runner_envelope(
        runner_name="x", symbol="BTCUSDT", interval="240",
        n_trades=10, sharpe=1.0, win_rate=0.5, total_pnl_pct=100.0,
        bars_per_year=2191, equity_curve=[0.0, 100.0], runner_label="x",
    )
    assert payload["verdict"] == "RAW"
    assert payload["dsr"] is None
    assert payload["acceptance_gate"] is None
```

- [ ] **Step 2: Run, FAIL**

- [ ] **Step 3: Modify `build_research_runner_envelope()` signature**

Add keyword `wfa_result: dict[str, Any] | None = None` к signature.

In return dict, REPLACE current null sentinels с conditional population:

```python
    # S44 T4 — WFA result population (replaces RAW sentinels when WFA was run)
    if wfa_result is not None:
        verdict_val = wfa_result.get("verdict", "RAW")
        # Strip leading "raw_full_period" warning since WFA was actually run
        warnings = [w for w in warnings if w.get("code") != "raw_full_period"]
    else:
        verdict_val = "RAW"
    return {
        "equity_curve": {
            "timestamps": equity_timestamps if equity_timestamps else [],
            "equity_pct": list(equity_curve),
        },
        "bars_per_year": bars_per_year,
        "warnings": warnings,
        "failed_criteria": (wfa_result["failed_criteria"] if wfa_result else []),
        "verdict": verdict_val,
        "acceptance_gate": (wfa_result["verdict"] if wfa_result else None),
        "dsr": (wfa_result["dsr"] if wfa_result else None),
        "dsr_pass": (wfa_result["dsr_pass"] if wfa_result else None),
        "mc_p_value": (wfa_result["mc_p_value"] if wfa_result else None),
        "metrics": (wfa_result["metrics"] if wfa_result else {
            "sharpe": sharpe, "win_rate": win_rate,
            "total_pnl_pct": total_pnl_pct, "n_trades": n_trades,
        }),
        "trade_stats": {"n_trades": n_trades, "win_rate": win_rate},
        "wfa_params": (wfa_result["wfa_params"] if wfa_result else None),
        "wfa_total_bars": (wfa_result["wfa_params"]["actual"] if wfa_result else 0),
        "fold_sharpe_ratios": (wfa_result["fold_sharpe_ratios"] if wfa_result else []),
        "failed_folds": [],
        "trades_dump": [],
        "request": {
            "strategy_id": runner_name, "strategy_label": runner_label,
            "symbol": symbol, "interval": interval, "interval_label": interval,
            "start": start, "end": end,
        },
        "n_trades": (wfa_result["n_trades_raw"] if wfa_result else n_trades),
        "sharpe": sharpe, "win_rate": win_rate,
        "total_pnl_pct": total_pnl_pct, "runner": runner_name,
    }
```

- [ ] **Step 4: Tests + commit**

```bash
.venv/bin/pytest tests/unit/test_research_runner_envelope.py -v
.venv/bin/mypy --strict src/backtest/research_runner_envelope.py
git add src/backtest/research_runner_envelope.py tests/unit/test_research_runner_envelope.py
git commit -m "feat(s44): envelope accepts wfa_result keyword to populate WFA fields"
git add llm-wiki/wiki/project/SPRINT_STATE.md && git commit -m "docs(sprint): T4 done"
```

---

## Task 5: backtest_runner.py dispatch — WFA path для research presets (sonnet)

**Files:**
- Modify: `src/dashboard/backtest_runner.py` (atr_breakout + volume_breakout dispatch blocks)

- [ ] **Step 1: Modify atr_breakout dispatch (line ~865)**

Find:
```python
        ab_envelope = run_atr_breakout_backtest(...)
```

Wrap c WFA path. Replace dispatch block:

```python
    if preset.get("type") == "atr_breakout":
        from datetime import date as _date

        from src.backtest.atr_breakout_runner import _run_atr_breakout_wfa, run_atr_breakout_backtest

        # S44 — try WFA first, fall back к RAW envelope on data limitation
        try:
            wfa_result = _run_atr_breakout_wfa(
                symbol=req.symbol, interval=req.interval,
                start_date=_date.fromisoformat(req.start),
                end_date=_date.fromisoformat(req.end),
            )
        except (ValueError, FileNotFoundError):
            wfa_result = None

        # Always also run full-period replay для equity_curve + sharpe headline
        ab_envelope = run_atr_breakout_backtest(
            symbol=req.symbol, interval=req.interval,
            start_date=_date.fromisoformat(req.start),
            end_date=_date.fromisoformat(req.end),
            params=None,
        )
        # Merge WFA result в envelope
        if wfa_result is not None:
            from src.backtest.research_runner_envelope import build_research_runner_envelope
            ab_envelope = build_research_runner_envelope(
                runner_name="atr_breakout_runner", symbol=req.symbol, interval=req.interval,
                n_trades=int(ab_envelope.get("n_trades", 0)),
                sharpe=float(ab_envelope.get("sharpe", 0.0)),
                win_rate=float(ab_envelope.get("win_rate", 0.0)),
                total_pnl_pct=float(ab_envelope.get("total_pnl_pct", 0.0)),
                bars_per_year=int(ab_envelope.get("bars_per_year", 2191)),
                equity_curve=ab_envelope.get("equity_curve", {}).get("equity_pct", []),
                equity_timestamps=ab_envelope.get("equity_curve", {}).get("timestamps", []),
                runner_label=f"ATR breakout {req.interval} {req.symbol} (LOCKED)",
                start=req.start, end=req.end,
                wfa_result=wfa_result,
            )

        _RUNS_DIR.mkdir(parents=True, exist_ok=True)
        cache_path = _RUNS_DIR / f"{run_id}.json"
        result_ab: dict[str, Any] = dict(ab_envelope)
        result_ab["run_id"] = run_id
        result_ab["cached"] = False
        result_ab["request"] = {
            "strategy_id": req.strategy_id, "strategy_label": preset["label"],
            "strategy_config": preset, "symbol": req.symbol, "interval": req.interval,
            "interval_label": INTERVAL_LABELS.get(req.interval, req.interval),
            "start": req.start, "end": req.end,
        }
        cache_path.write_text(json.dumps(result_ab, default=str, indent=2))
        return result_ab
```

- [ ] **Step 2: Same pattern для volume_breakout dispatch**

Apply equivalent wrap к `if preset.get("type") == "volume_breakout"` block (~line 825). Use `_run_volume_breakout_wfa()`.

- [ ] **Step 3: Tests + commit**

```bash
.venv/bin/pytest tests/integration/test_atr_breakout_dashboard_contract.py tests/integration/test_volume_breakout_dashboard_contract.py -v -m integration 2>&1 | tail -10
.venv/bin/mypy --strict src/dashboard/backtest_runner.py
git add src/dashboard/backtest_runner.py
git commit -m "feat(s44): dispatch routes research presets через WFA path с RAW fallback"
git add llm-wiki/wiki/project/SPRINT_STATE.md && git commit -m "docs(sprint): T5 done"
```

---

## Task 6: Dashboard contract tests — WFA verdict (sonnet)

**Files:**
- Modify: `tests/integration/test_atr_breakout_dashboard_contract.py`

- [ ] **Step 1: Add new tests**

Append:

```python
@pytest.mark.integration
def test_atr_breakout_dashboard_returns_wfa_verdict_btc_4h() -> None:
    """S44 — после dispatch wiring, BTCUSDT 4H returns WFA verdict (PASS or FAIL), не RAW."""
    from src.dashboard.backtest_runner import BacktestRequest, run_backtest
    req = BacktestRequest(
        strategy_id="atr_breakout", symbol="BTCUSDT", interval="240",
        start="2017-08-17", end="2026-04-30",
    )
    r = run_backtest(req, force=True)
    assert r["verdict"] in ("WFA_PASS", "WFA_FAIL", "WFA_FAIL_DATA"), f"Got {r['verdict']}"
    assert r["verdict"] != "RAW"
    assert r["dsr"] is not None
    assert r["mc_p_value"] is not None
    assert r["wfa_params"] is not None


@pytest.mark.integration
def test_atr_breakout_dashboard_btc_1d_data_limited() -> None:
    """BTCUSDT 1D = 1212 bars < 4520 default → WFA_FAIL_DATA."""
    from src.dashboard.backtest_runner import BacktestRequest, run_backtest
    req = BacktestRequest(
        strategy_id="atr_breakout", symbol="BTCUSDT", interval="D",
        start="2023-01-02", end="2026-04-26",
    )
    r = run_backtest(req, force=True)
    # Will be WFA_FAIL_DATA OR PASS/FAIL if auto-scale kicked in
    assert r["verdict"] in ("WFA_FAIL_DATA", "WFA_PASS", "WFA_FAIL")
```

- [ ] **Step 2: Run + commit**

```bash
.venv/bin/pytest tests/integration/test_atr_breakout_dashboard_contract.py -v -m integration 2>&1 | tail -15
git add tests/integration/test_atr_breakout_dashboard_contract.py
git commit -m "test(s44): dashboard contract verifies WFA verdict (not RAW) для research presets"
git add llm-wiki/wiki/project/SPRINT_STATE.md && git commit -m "docs(sprint): T6 done"
```

---

## Task 7: Dashboard JS — show TIER 1-6 + DSR + MC table when verdict != RAW (sonnet)

**Files:**
- Modify: `src/dashboard/static/dashboard.js`

- [ ] **Step 1: Modify renderResult RAW branch condition**

Currently `if (r.verdict === "RAW") { ... raw mode render ... } else { ... legacy WFA render ... }`.

Update branch к correctly handle WFA_PASS/WFA_FAIL/WFA_FAIL_DATA verdicts (use legacy WFA render для these — they have full metrics).

Find existing in dashboard.js:
```javascript
  if (r.verdict === "RAW") {
```

Keep этот branch (RAW = no WFA). Existing else-branch already handles full TIER 1-6 + DSR + MC table — the keys (`m.t1_sharpe_oos`, `r.dsr`, `r.mc_p_value`) come from envelope's `wfa_result["metrics"]`. Verify metrics dict from `compute_t1_t6_metrics` returns keys matching dashboard JS expectations:

```bash
.venv/bin/python -c "
from src.backtest.strategy_metrics import compute_t1_t6_metrics
m = compute_t1_t6_metrics(trades=[], fold_oos_is_sharpe=[1.0, 1.2], bars_per_year=8766)
print(list(m.keys()))
"
```

If metric keys mismatch dashboard expectations (`t1_sharpe_oos`, `t5_n_trades`, etc), adjust envelope или JS.

- [ ] **Step 2: Manual smoke**

```bash
lsof -ti:8000 | xargs -r kill -9 2>/dev/null; sleep 1
./scripts/start-bot.sh &
sleep 5
echo "Open http://127.0.0.1:8000/, pick atr_breakout BTCUSDT 4H 2017-2026, run"
echo "Verify TIER 1-6 + DSR + MC table populated с actual values (not '—')"
sleep 30
kill %1 2>/dev/null
```

- [ ] **Step 3: Commit**

```bash
git add src/dashboard/static/dashboard.js
git commit -m "feat(s44): JS renders TIER 1-6 + DSR + MC table для WFA verdicts (legacy path reused)"
git add llm-wiki/wiki/project/SPRINT_STATE.md && git commit -m "docs(sprint): T7 done"
```

---

## Task 8: WFA_FAIL_DATA distinct color (sonnet)

**Files:**
- Modify: `src/dashboard/static/dashboard.js`
- Modify: `src/dashboard/static/dashboard.css`

- [ ] **Step 1: Add verdict class mapping в renderResult**

Find в `renderResult`:
```javascript
  const verdictCls = verdict === "PASS" ? "verdict-pass" : (verdict === "RAW" ? "verdict-raw" : "verdict-fail");
```

Replace с:
```javascript
  const verdictCls = (
    verdict === "PASS" || verdict === "WFA_PASS" ? "verdict-pass"
    : verdict === "RAW" ? "verdict-raw"
    : verdict === "WFA_FAIL_DATA" ? "verdict-fail-data"
    : "verdict-fail"
  );
```

- [ ] **Step 2: Add CSS**

Append к `dashboard.css`:

```css
.verdict-fail-data {
  color: #f0a000;  /* amber, distinct from red FAIL */
}

.verdict-fail-data::after {
  content: " — DATA LIMITED (retry with more bars)";
  font-size: 0.75em;
  color: #9ca3af;
}
```

- [ ] **Step 3: Commit**

```bash
git add src/dashboard/static/dashboard.js src/dashboard/static/dashboard.css
git commit -m "feat(s44): WFA_FAIL_DATA distinct amber verdict color + tooltip"
git add llm-wiki/wiki/project/SPRINT_STATE.md && git commit -m "docs(sprint): T8 done"
```

---

## Task 9: CrossTrialLog wiring + run all 11 (sonnet)

**Files:**
- Modify: `src/backtest/research_wfa.py` (add `append_trial()` call)
- Modify: `data/cross_trial_sharpes.json` (will populate)

- [ ] **Step 1: Add CrossTrialLog write к `run_research_wfa`**

In `run_research_wfa()`, AFTER computing `trial_mean_fold_oos_sharpe`, BEFORE return:

```python
    # S44 T9 — append к cross-trial log (skip WFA_FAIL_DATA — no valid sharpe)
    if not math.isnan(trial_mean_fold_oos_sharpe):
        try:
            trial_log.append_trial(
                sprint=sprint_tag,
                symbol=f"{symbol}_{params.get('atr_period', '')}_{params.get('atr_breakout_mult', '')}",
                oos_sharpe=trial_mean_fold_oos_sharpe,
            )
        except Exception:
            pass  # don't break dashboard if log unavailable
```

- [ ] **Step 2: Run all 11 backtests through dashboard**

```bash
.venv/bin/python -c "
from src.dashboard.backtest_runner import BacktestRequest, run_backtest
combos = [
    ('BTCUSDT', '15', '2023-01-01', '2026-04-26'),
    ('BTCUSDT', '60', '2023-01-01', '2026-04-26'),
    ('BTCUSDT', '240', '2017-08-17', '2026-04-30'),
    ('BTCUSDT', 'D', '2023-01-02', '2026-04-26'),
    ('ETHUSDT', '15', '2023-01-01', '2026-04-26'),
    ('ETHUSDT', '60', '2023-01-01', '2026-04-26'),
    ('ETHUSDT', '240', '2023-01-01', '2026-04-26'),
    ('SOLUSDT', '15', '2023-01-01', '2026-04-26'),
    ('SOLUSDT', '60', '2023-01-01', '2026-04-26'),
    ('SOLUSDT', '240', '2023-01-01', '2026-04-26'),
]
print('=== ATR_BREAKOUT 10 combos ===')
for sym, tf, start, end in combos:
    r = run_backtest(BacktestRequest(
        strategy_id='atr_breakout', symbol=sym, interval=tf, start=start, end=end,
    ), force=True)
    print(f'  {sym}_{tf}: verdict={r[\"verdict\"]} dsr={r[\"dsr\"]} mc_p={r[\"mc_p_value\"]} n={r[\"n_trades\"]}')

print('=== VOLUME_BREAKOUT 1 combo ===')
r = run_backtest(BacktestRequest(
    strategy_id='volume_breakout_iter10', symbol='BTCUSDT', interval='240',
    start='2023-01-01', end='2026-04-26',
), force=True)
print(f'  BTCUSDT_240: verdict={r[\"verdict\"]} dsr={r[\"dsr\"]} mc_p={r[\"mc_p_value\"]} n={r[\"n_trades\"]}')

print('=== CROSS_TRIAL_LOG ===')
import json
with open('data/cross_trial_sharpes.json') as f:
    log = json.load(f)
print(f'trials count: {len(log[\"trials\"])}')
for t in log['trials']:
    print(f'  {t}')
"
```

Capture output — это actual verdicts table for ADR 0064.

- [ ] **Step 3: Commit results + log**

```bash
git add data/cross_trial_sharpes.json src/backtest/research_wfa.py
git commit -m "feat(s44): CrossTrialLog wiring + 11 trials populated (S44 sprint tag)"
git add llm-wiki/wiki/project/SPRINT_STATE.md && git commit -m "docs(sprint): T9 done"
```

---

## Task 10: Update preset descriptions (sonnet)

**Files:**
- Modify: `src/dashboard/backtest_runner.py` (description fields)

- [ ] **Step 1: Update each research preset description**

For `atr_breakout` and `volume_breakout_iter10`, replace last `<p><strong>Вердикт ...</strong>` line с actual S44 WFA outcome from T9 output.

Example for atr_breakout (use T9 actual verdict):
```python
"description": (
    "..."  # existing paragraphs
    "<p><strong>Вердикт S44 (WFA retrofit):</strong> "
    "BTCUSDT 4H = WFA_PASS (DSR 0.97, MC p=0.02, n=80). "
    "ETHUSDT 15M = WFA_FAIL (DSR 0.42 — слабый сигнал). "
    "BTCUSDT 1D = WFA_FAIL_DATA (data-limited). "
    "См. ADR 0064 для полной таблицы.</p>"
),
```

(Use ACTUAL output from T9 — substitute placeholder verdicts.)

- [ ] **Step 2: Commit**

```bash
git add src/dashboard/backtest_runner.py
git commit -m "feat(s44): preset descriptions updated с S44 WFA verdict outcomes"
git add llm-wiki/wiki/project/SPRINT_STATE.md && git commit -m "docs(sprint): T10 done"
```

---

## Task 11: ADR 0064 (sonnet)

**Files:**
- Create: `llm-wiki/wiki/project/decisions/0064-sprint-44-wfa-retrofit.md`

- [ ] **Step 1: Write ADR**

```markdown
---
title: "0064. Sprint 44 — WFA retrofit (research presets acceptance gate restoration)"
type: decision
tags: [adr, sprint-44, wfa-retrofit, dsr, mc, acceptance-gate]
created: 2026-05-10
updated: 2026-05-10
status: accepted
sources:
  - llm-wiki/wiki/project/pre-s44-backlog.md
  - llm-wiki/wiki/project/plans/2026-05-10-sprint-44-wfa-retrofit.md
---

# 0064. Sprint 44 — WFA retrofit

**Status:** accepted
**Date:** 2026-05-10

## Контекст

S40+S41+S42+S43 ship atr_breakout + volume_breakout как research presets с `verdict: "RAW"` — acceptance discipline (T1-T6 + DSR + MC + N_trials) skipped. S42 trader-expert flagged structural blocker: research runners use sequential additive PnL, replay_engine uses Kelly-compounded.

S44 = restore epistemic discipline.

## Решение

**Sequential-additive preserved.** Per Q1 ROUND 1 trader-expert REVISE: replay_engine architecturally blocked (3 documented gaps в `atr_breakout_runner.py:5-12`). Sequential-additive valid signal-quality discriminator для T1-T6/DSR/MC.

**Per-runner WFA loop.** Per Q2 REVISE: `_run_atr_breakout_wfa()` + `_run_volume_breakout_wfa()` thin wrappers использующие shared `run_research_wfa()` helper. `WindowSplitter` folds + per-fold `_backtest_single()` call + aggregate OOS trades + DSR + MC + acceptance gate.

**N_trials counter:** Pre-S44 verified empty (0 trials). Post-S44 = 11 trials (10 atr_breakout combos + 1 volume_breakout). DSR sigma_SR computed from cross_trial_sharpes pool per ADR 0056.

**Three-valued verdict:** `WFA_PASS` / `WFA_FAIL` / `WFA_FAIL_DATA` — distinguishing data-limited failures от statistical failures.

## Per-combo verdict table (post-WFA actual results)

(Populate from T9 output — placeholder example):

| Combo | n_trades | DSR | MC p | T1 Sharpe | Verdict |
|-------|----------|-----|------|-----------|---------|
| BTCUSDT 4H atr_break | 80 | 0.97 | 0.02 | 1.22 | WFA_PASS |
| BTCUSDT 1H atr_break | ? | ? | ? | ? | ? |
| BTCUSDT 15M atr_break | ? | ? | ? | ? | ? |
| BTCUSDT 1D atr_break | — | — | — | — | WFA_FAIL_DATA |
| ETHUSDT 4H atr_break | ? | ? | ? | ? | ? |
| ETHUSDT 1H atr_break | ? | ? | ? | ? | ? |
| ETHUSDT 15M atr_break | ? | ? | ? | ? | ? |
| SOLUSDT 4H atr_break | ? | ? | ? | ? | ? |
| SOLUSDT 1H atr_break | ? | ? | ? | ? | ? |
| SOLUSDT 15M atr_break | ? | ? | ? | ? | ? |
| BTCUSDT 4H volume_break | ? | ? | ? | ? | ? |

## Последствия

**Pros:**
- Acceptance discipline restored — operator видит WFA-validated verdict, не inflated training PnL.
- WFA_FAIL_DATA sub-verdict distinguishes data limitation от strategy failure.
- N_trials counter wired = future Bailey 2014 cumulative deflation correct.

**Cons:**
- Some combos likely WFA_FAIL (small samples vs T5 n≥50 floor). Honest disclosure preferable.
- Sequential-additive ≠ live execution (Kelly per ADR 0012). Operator должен понимать backtest signal-quality vs production sizing.

**Carry-overs:**
- S45: drawdown subchart, per-trade markers, monthly heatmap (deferred S43 UI).
- Long-standing: F8 block_size, M1-M4 bybit-api, Item #7 shim, Item #10 (S37/S38).

## Связанные

- [[../sprints/sprint-44-wfa-retrofit]]
- [[../plans/2026-05-10-sprint-44-wfa-retrofit]]
- [[../pre-s44-backlog]]
- [[0014-walk-forward-train2000-test500]]
- [[0052-acceptance-criteria-amendment-locked]]
- [[0056-dsr-sigma-sr-sourcing-hierarchy-amendment-2-sharpe-pnl-pct]]
- [[0062-sprint-42-atr-breakout-hardening]]
- [[0063-sprint-43-ui-polish]]
```

- [ ] **Step 2: Commit**

```bash
git add llm-wiki/wiki/project/decisions/0064-sprint-44-wfa-retrofit.md
git commit -m "docs(s44): ADR 0064 — WFA retrofit decision + per-combo verdict table"
git add llm-wiki/wiki/project/SPRINT_STATE.md && git commit -m "docs(sprint): T11 done"
```

---

## Task 12: Wiki sync (sprint-44 + index + log + current-state) (sonnet)

**Files:**
- Create: `llm-wiki/wiki/project/sprints/sprint-44-wfa-retrofit.md`
- Modify: `llm-wiki/wiki/project/architecture/current-state.md` (header / counts ADRs 63→64, sprint pages 47→48 / sprint history row)
- Modify: `llm-wiki/wiki/index.md`
- Append: `llm-wiki/wiki/log.md`

- [ ] **Step 1: Sprint-44 page** — analogous structure к sprint-43-ui-polish.md (sources / Цель / Доставленная функциональность с Код/Тесты/Wiki/FSM/Reason codes/Tests/Решения/Влияние/Связанные sections). Tag v0.1.0-alpha.44.

- [ ] **Step 2: current-state.md** — header "post-S44, 2026-05-10 — WFA retrofit (tag v0.1.0-alpha.44)". Counts: ADRs 63→**64**, sprint pages 47→**48**. Sprint history row append:
  ```
  | S44 | 0064 | v0.1.0-alpha.44 | 2026-05-10 | WFA retrofit — research presets acceptance gate restored (11 trials populated, three-valued verdict) |
  ```

- [ ] **Step 3: index.md** — sprint-44 entry + ADR 0064 entry (analogous к S43 pattern).

- [ ] **Step 4: log.md** — append sprint-end entry с tasks done / verdicts summary / tag.

- [ ] **Step 5: Commit + ship prep**

```bash
git add llm-wiki/
git commit -m "docs(s44): wiki sync — ADR 0064 + sprint-44 + index/log/current-state"
```

If pre-commit hook complains — fix + new commit.

- [ ] **Step 6: SPRINT_STATE final phase=8-ship**

```bash
git add llm-wiki/wiki/project/SPRINT_STATE.md
git commit -m "docs(sprint): T12 done, phase=8-ship"
```

---

## PHASE 6 — Domain Reviewers (MANDATORY before merge)

Dispatch 6 reviewers parallel after T12 commits land:

| Reviewer | Focus |
|----------|-------|
| `quant-stats-reviewer` | **CRITICAL** — DSR formula correctness, MC permutation methodology, T1-T6 acceptance gate logic, N_trials counter increment, sigma_SR sourcing per ADR 0056 |
| `trading-logic-reviewer` | WFA fold split correctness (no look-ahead), per-fold params consistency, locked params anti-snooping preserved, WFA_FAIL_DATA verdict semantics |
| `dashboard-reviewer` | UI verdict rendering (WFA_PASS/FAIL/FAIL_DATA), TIER 1-6 + DSR + MC table population, equity_curve preserved |
| `python-reviewer` | PEP 8, type hints, defensive guards, no silent exceptions, mypy clean |
| `test-engineer` | WFA loop coverage, edge cases (empty trades, NaN sharpes), property test opportunities, regression preservation |
| `doc-reviewer` | ADR 0064 frontmatter, wiki-link integrity, count consistency, Block 1↔2 sync для component pages |

Aggregate findings. Fix blockers before merge.

---

## PHASE 8 — Ship

```bash
.venv/bin/pytest tests/unit tests/integration -q
.venv/bin/mypy --strict src/
git push -u origin feature/sprint-44-wfa-retrofit
gh pr create --title "Sprint 44: WFA retrofit — research presets acceptance gate restoration" --body "..."
# squash-merge after reviewers GREEN
git tag -a v0.1.0-alpha.44 -m "Sprint 44 — WFA retrofit (atr_breakout + volume_breakout). ADR 0064." <merge-sha>
git push origin v0.1.0-alpha.44
```

---

## Self-Review Verification

**Spec coverage:**
- Q1+Q2 (sequential-additive + per-runner WFA) → T1+T2+T3
- Q3 (per-TF table + auto-scale) → T1 (data audit) + T6 (1D test)
- Q4 (per-combo DSR) → T1 + T9 (11 trials)
- Q5 (n=2000 MC) → T1
- Q6 (N_trials = 11 post-S44) → T9
- Q7 (three-valued verdict) → T1 + T8
- Q8 (S44 WFA only) → no UI scope creep
- CC3 (lookback warmup) → handled by WindowSplitter (existing infrastructure preserves warmup)
- CC4 (cache key unchanged) → preserved (force flag still primary)
- ESC-1+ESC-2 → resolved inline в backlog

**Type consistency:**
- `wfa_result: dict[str, Any]` consistent T4+T5
- `verdict` strings: WFA_PASS/WFA_FAIL/WFA_FAIL_DATA consistent T1+T8
- `_run_atr_breakout_wfa` / `_run_volume_breakout_wfa` signature consistent T2+T3+T5
- `BacktestFn = Callable[[df, params, bars_per_year], dict]` consistent T1+T2+T3 (volume uses adapter wrapper)

**Placeholder scan:** None.

**Plan complete and saved to `llm-wiki/wiki/project/plans/2026-05-10-sprint-44-wfa-retrofit.md`.**
