---
title: "Sprint 42 — atr_breakout production hardening (kit retrofit)"
type: plan
tags: [sprint-42, retrofit, dashboard-bug, atr-breakout]
created: 2026-05-10
updated: 2026-05-10
status: ready
sources:
  - llm-wiki/wiki/project/pre-s42-backlog.md
  - llm-wiki/wiki/project/decisions/0060-sprint-40-atr-breakout-production.md
  - llm-wiki/wiki/project/decisions/0061-sprint-41-multi-combo-presets.md
---

# Sprint 42 — atr_breakout production hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix dashboard crash on atr_breakout/volume_breakout presets, consolidate 10 atr_breakout presets into 1 parametric preset, restore minimal honest UX (RAW_FULL_PERIOD label until S43 WFA retrofit).

**Architecture:** New helper `build_research_runner_envelope()` wraps research runners (atr_breakout, volume_breakout) к dashboard-contract dict (matches replay engine output keys with null sentinels). Single `atr_breakout` preset с `supported_combos: list[tuple[str, str]]` field. Server-side params lookup via `ATR_BREAKOUT_LOCKED_PARAMS_BY_COMBO[(sym, tf)]`. Frontend introspects new `/api/strategy/{id}/info` endpoint к grey out invalid combos. JS defensive guards prevent future crashes от similar contract drift.

**Tech Stack:** Python 3.12, FastAPI, pydantic v2, pytest, vanilla JS (no framework).

**Branch:** `feature/sprint-42-atr-breakout-hardening`

**Models:** sonnet for all 10 tasks (mechanical refactor + dashboard glue, no judgment-heavy decisions).

---

## File Trace Map (PHASE 3 step 1a HARD-GATE)

| File | Action | Tasks |
|------|--------|-------|
| `src/backtest/research_runner_envelope.py` | CREATE | T1 |
| `src/backtest/atr_breakout_runner.py` | MODIFY (return dict) | T2 |
| `src/backtest/volume_breakout_runner.py` | MODIFY (return dict) | T3 |
| `src/dashboard/backtest_runner.py:30-260` | MODIFY (consolidate 10→1 preset) | T4 |
| `src/dashboard/backtest_runner.py:800-900` | MODIFY (dispatch) | T4 |
| `src/dashboard/app.py:96-130` | MODIFY (combo enforcement + info endpoint) | T5 |
| `src/dashboard/static/dashboard.js:180-210` | MODIFY (defensive guards) | T6 |
| `src/dashboard/static/dashboard.js` (intro of fetchStrategyInfo) | ADD | T6 |
| `src/dashboard/templates/index.html` | MODIFY if combo-gate needs DOM hooks | T6 |
| `tests/unit/test_research_runner_envelope.py` | CREATE | T1 |
| `tests/integration/test_atr_breakout_dashboard_contract.py` | CREATE | T8 |
| `tests/integration/test_volume_breakout_dashboard_contract.py` | CREATE | T8 |
| `tests/unit/test_supported_combos_endpoint.py` | CREATE | T8 |
| `tests/integration/test_atr_breakout_baseline_floor.py` | MODIFY (preset_id rename) | T8 |
| `llm-wiki/wiki/project/decisions/0060-sprint-40-atr-breakout-production.md` | MODIFY (status superseded) | T9 |
| `llm-wiki/wiki/project/decisions/0061-sprint-41-multi-combo-presets.md` | MODIFY (status superseded) | T9 |
| `llm-wiki/wiki/project/decisions/0062-sprint-42-atr-breakout-hardening.md` | CREATE | T9 |
| `llm-wiki/wiki/project/sprints/sprint-42-atr-breakout-hardening.md` | CREATE | T10 |
| `llm-wiki/wiki/project/architecture/current-state.md` | MODIFY (sprint history row) | T10 |
| `llm-wiki/wiki/index.md` | MODIFY (ADR + sprint entries) | T10 |
| `llm-wiki/wiki/log.md` | APPEND (S42 ship entry) | T10 |
| `llm-wiki/wiki/project/components/atr-breakout-strategy.md` | MODIFY (preset_id rename) | T10 |
| `llm-wiki/wiki/project/components/dashboard.md` (if exists) | MODIFY (envelope contract) | T10 |
| `llm-wiki/wiki/project/SPRINT_STATE.md` | MODIFY (per-task updates) | every task |

---

## Task 1: Research Runner Envelope helper

**Files:**
- Create: `src/backtest/research_runner_envelope.py`
- Test: `tests/unit/test_research_runner_envelope.py`

**Why this task first:** All other runners depend on shared envelope shape. Defining it once prevents drift между atr_breakout + volume_breakout returns.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_research_runner_envelope.py
"""S42 T1 — research runner envelope contract tests."""
from __future__ import annotations

import pytest

from src.backtest.research_runner_envelope import build_research_runner_envelope


def test_envelope_contains_all_dashboard_required_keys() -> None:
    """Dashboard JS reads bars_per_year, failed_criteria, verdict, warnings, etc.
    Envelope MUST provide all to prevent toLocaleString-style crashes.
    """
    payload = build_research_runner_envelope(
        runner_name="atr_breakout_runner",
        symbol="BTCUSDT",
        interval="240",
        n_trades=69,
        sharpe=1.11,
        win_rate=0.46,
        total_pnl_pct=819.81,
        bars_per_year=2191,
        equity_curve=[0.0, 100.0, 200.0, 300.0, 400.0, 819.81],
        runner_label="ATR breakout (LOCKED)",
    )
    # Required dashboard keys
    for key in (
        "bars_per_year",
        "warnings",
        "failed_criteria",
        "verdict",
        "acceptance_gate",
        "dsr",
        "dsr_pass",
        "mc_p_value",
        "metrics",
        "trade_stats",
        "wfa_params",
        "wfa_total_bars",
        "fold_sharpe_ratios",
        "failed_folds",
        "trades_dump",
    ):
        assert key in payload, f"Missing required dashboard key: {key}"


def test_envelope_warnings_includes_raw_full_period_high() -> None:
    """Honest disclosure — operator sees high warning that acceptance gate skipped."""
    payload = build_research_runner_envelope(
        runner_name="atr_breakout_runner", symbol="BTCUSDT", interval="240",
        n_trades=10, sharpe=1.0, win_rate=0.5, total_pnl_pct=100.0,
        bars_per_year=2191, equity_curve=[0.0, 50.0, 100.0],
        runner_label="x",
    )
    high = [w for w in payload["warnings"] if w["level"] == "high" and w["code"] == "raw_full_period"]
    assert len(high) == 1
    assert "WFA retrofit pending S43" in high[0]["message"]


def test_envelope_subperiod_robustness_5_of_5_emits_ok_chip() -> None:
    """5/5 sub-period positives = ok-level chip in warnings array."""
    # equity_curve monotonically rising — all 5 chunks positive
    payload = build_research_runner_envelope(
        runner_name="x", symbol="BTCUSDT", interval="240",
        n_trades=10, sharpe=1.0, win_rate=0.5, total_pnl_pct=500.0,
        bars_per_year=2191,
        equity_curve=[0.0, 100.0, 200.0, 300.0, 400.0, 500.0],
        runner_label="x",
    )
    chips = [w for w in payload["warnings"] if w["code"] == "subperiod_robustness"]
    assert len(chips) == 1
    assert chips[0]["level"] == "info"
    assert "5/5" in chips[0]["message"]


def test_envelope_subperiod_robustness_3_of_5_emits_warn_chip() -> None:
    """3/5 sub-period positives = warn-level chip."""
    # 5 chunks: +50, -20, +30, -10, -5 → 3 positive
    payload = build_research_runner_envelope(
        runner_name="x", symbol="BTCUSDT", interval="240",
        n_trades=10, sharpe=1.0, win_rate=0.5, total_pnl_pct=45.0,
        bars_per_year=2191,
        equity_curve=[0.0, 50.0, 30.0, 60.0, 50.0, 45.0],
        runner_label="x",
    )
    chips = [w for w in payload["warnings"] if w["code"] == "subperiod_robustness"]
    assert chips[0]["level"] == "warn"
    assert "3/5" in chips[0]["message"]


def test_envelope_request_dict_carries_label_symbol_interval() -> None:
    """request dict mirrors dashboard payload echo."""
    payload = build_research_runner_envelope(
        runner_name="x", symbol="ETHUSDT", interval="60",
        n_trades=109, sharpe=1.5, win_rate=0.4, total_pnl_pct=181.74,
        bars_per_year=8766,
        equity_curve=[0.0, 100.0, 181.74],
        runner_label="ATR breakout 1H ETHUSDT",
        start="2023-01-01", end="2026-04-26",
    )
    assert payload["request"]["symbol"] == "ETHUSDT"
    assert payload["request"]["interval"] == "60"
    assert payload["request"]["start"] == "2023-01-01"
    assert payload["request"]["end"] == "2026-04-26"
    assert payload["request"]["strategy_label"] == "ATR breakout 1H ETHUSDT"


def test_envelope_failed_criteria_is_empty_list_not_none() -> None:
    """JS does r.failed_criteria.length — must be array, not null."""
    payload = build_research_runner_envelope(
        runner_name="x", symbol="BTCUSDT", interval="240",
        n_trades=10, sharpe=1.0, win_rate=0.5, total_pnl_pct=100.0,
        bars_per_year=2191, equity_curve=[0.0, 100.0],
        runner_label="x",
    )
    assert payload["failed_criteria"] == []
    assert payload["fold_sharpe_ratios"] == []
    assert payload["trades_dump"] == []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/bin/pytest tests/unit/test_research_runner_envelope.py -v
```

Expected: ALL FAIL with `ImportError: cannot import name 'build_research_runner_envelope' from 'src.backtest.research_runner_envelope'`

- [ ] **Step 3: Implement helper module**

```python
# src/backtest/research_runner_envelope.py
"""S42 T1 — Dashboard contract envelope для research-mode runners.

Wraps minimal-output runners (atr_breakout, volume_breakout) к match dashboard
JS contract expected from replay_engine. Until S43 WFA retrofit, returns null
sentinels for acceptance_gate / DSR / MC, plus high-level warning that
acceptance discipline is skipped (RAW_FULL_PERIOD).

Sub-period robustness computed from equity_curve (5 chunks) is surfaced
as info/warn/high chip per N/5 positive periods.
"""
from __future__ import annotations

from typing import Any


def _subperiod_robustness_chunks(equity_curve: list[float], n_chunks: int = 5) -> list[float]:
    """Split equity_curve в n_chunks roughly equal chunks. Return per-chunk PnL delta.

    Replicates autoresearch subperiod_pnls computation.
    """
    if len(equity_curve) < n_chunks + 1:
        # Too few points for meaningful split — return single chunk
        return [equity_curve[-1] - equity_curve[0]] if equity_curve else []
    n = len(equity_curve)
    step = n // n_chunks
    deltas: list[float] = []
    for i in range(n_chunks):
        start_idx = i * step
        end_idx = (i + 1) * step if i < n_chunks - 1 else n - 1
        deltas.append(equity_curve[end_idx] - equity_curve[start_idx])
    return deltas


def build_research_runner_envelope(
    *,
    runner_name: str,
    symbol: str,
    interval: str,
    n_trades: int,
    sharpe: float,
    win_rate: float,
    total_pnl_pct: float,
    bars_per_year: int,
    equity_curve: list[float],
    runner_label: str,
    start: str = "",
    end: str = "",
    extra_warnings: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Build dashboard-contract envelope от research runner outputs.

    Dashboard JS expects keys from replay_engine: bars_per_year, warnings,
    failed_criteria, verdict, acceptance_gate, dsr, dsr_pass, mc_p_value,
    metrics, trade_stats, wfa_params, wfa_total_bars, fold_sharpe_ratios,
    failed_folds, trades_dump, request.

    Until S43 WFA retrofit:
      - acceptance_gate, dsr, mc_p_value → None (sentinels)
      - failed_criteria → [] (empty list, JS does .length)
      - verdict → "RAW" (not PASS/FAIL — discipline skipped)
      - warnings → high-level "raw_full_period" chip + sub-period robustness chip
    """
    warnings: list[dict[str, str]] = []

    # Mandatory honest-discipline warning
    warnings.append({
        "level": "high",
        "code": "raw_full_period",
        "message": (
            "Acceptance gate skipped — WFA retrofit pending S43. "
            "Displayed PnL is full-period training number, NOT OOS-validated."
        ),
    })

    # Sub-period robustness chip
    deltas = _subperiod_robustness_chunks(equity_curve)
    n_pos = sum(1 for d in deltas if d > 0)
    n_total = len(deltas)
    if n_total > 0:
        if n_pos == n_total:
            level = "info"
        elif n_pos >= n_total * 0.6:  # 3/5 or 4/5
            level = "warn"
        else:
            level = "high"
        warnings.append({
            "level": level,
            "code": "subperiod_robustness",
            "message": f"Robustness: {n_pos}/{n_total} sub-periods positive.",
        })

    if extra_warnings:
        warnings.extend(extra_warnings)

    return {
        # Crash-fix essentials
        "bars_per_year": bars_per_year,
        "warnings": warnings,
        "failed_criteria": [],
        "verdict": "RAW",
        # Acceptance discipline sentinels (S43 will fill)
        "acceptance_gate": None,
        "dsr": None,
        "dsr_pass": None,
        "mc_p_value": None,
        # Metrics dict — mirror minimal subset
        "metrics": {
            "sharpe": sharpe,
            "win_rate": win_rate,
            "total_pnl_pct": total_pnl_pct,
            "n_trades": n_trades,
        },
        "trade_stats": {
            "n_trades": n_trades,
            "win_rate": win_rate,
        },
        # WFA placeholders
        "wfa_params": None,
        "wfa_total_bars": 0,
        "fold_sharpe_ratios": [],
        "failed_folds": [],
        "trades_dump": [],
        # Echo request
        "request": {
            "strategy_id": runner_name,
            "strategy_label": runner_label,
            "symbol": symbol,
            "interval": interval,
            "interval_label": interval,
            "start": start,
            "end": end,
        },
        # Pass-through fields
        "n_trades": n_trades,
        "sharpe": sharpe,
        "win_rate": win_rate,
        "total_pnl_pct": total_pnl_pct,
        "runner": runner_name,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/pytest tests/unit/test_research_runner_envelope.py -v
```

Expected: 6/6 PASS.

- [ ] **Step 5: Commit**

```bash
git add src/backtest/research_runner_envelope.py tests/unit/test_research_runner_envelope.py
git commit -m "feat(s42): research runner envelope helper для dashboard contract"
```

- [ ] **Step 6: Update SPRINT_STATE per-task**

Edit `llm-wiki/wiki/project/SPRINT_STATE.md` Phase 4 task table — mark T1 done. Update "Текущий статус" + "Следующее действие" + `updated:` frontmatter.

```bash
git add llm-wiki/wiki/project/SPRINT_STATE.md
git commit -m "docs(sprint): SPRINT_STATE update phase=4 task=T1 done"
```

---

## Task 2: Wire envelope into atr_breakout_runner

**Files:**
- Modify: `src/backtest/atr_breakout_runner.py:340-385` (return dict construction)
- Test: `tests/integration/test_atr_breakout_dashboard_contract.py` (CREATE)

- [ ] **Step 1: Write the failing test**

```python
# tests/integration/test_atr_breakout_dashboard_contract.py
"""S42 T2 — atr_breakout dashboard envelope contract."""
from __future__ import annotations

import pytest

from src.dashboard.backtest_runner import BacktestRequest, run_backtest


@pytest.mark.integration
def test_atr_breakout_returns_envelope_keys() -> None:
    """Dashboard contract: bars_per_year, warnings, failed_criteria, verdict
    must all be present in atr_breakout result.
    """
    req = BacktestRequest(
        strategy_id="atr_breakout",
        symbol="BTCUSDT",
        interval="240",
        start="2023-01-01",
        end="2026-04-26",
    )
    r = run_backtest(req, force=True)

    for key in (
        "bars_per_year", "warnings", "failed_criteria", "verdict",
        "acceptance_gate", "dsr", "dsr_pass", "mc_p_value",
        "metrics", "trade_stats", "wfa_params", "wfa_total_bars",
        "fold_sharpe_ratios", "failed_folds", "trades_dump",
    ):
        assert key in r, f"S42 contract missing key: {key}"

    assert r["verdict"] == "RAW"
    assert r["failed_criteria"] == []
    high = [w for w in r["warnings"] if w["code"] == "raw_full_period"]
    assert len(high) == 1
```

- [ ] **Step 2: Run test, verify FAIL**

```bash
.venv/bin/pytest tests/integration/test_atr_breakout_dashboard_contract.py -v -m integration
```

Expected: FAIL — old runner returns 8 keys, new keys missing.

- [ ] **Step 3: Modify atr_breakout_runner return**

Locate the result dict в `src/backtest/atr_breakout_runner.py::run_atr_breakout_backtest` (~line 380). Replace return dict construction with envelope wrapper:

```python
# At end of run_atr_breakout_backtest, replace existing `return {...}` block:
from src.backtest.research_runner_envelope import build_research_runner_envelope

bars_per_year_lookup = {
    "5": 105192, "15": 35064, "60": 8766, "240": 2191, "D": 365,
}
bars_per_year = bars_per_year_lookup.get(interval, 2191)

# equity_curve = cumulative pnl_pct array if available, else synthesize
# Existing var name in the runner: trades produce pnl_pct deltas; build equity from sum
equity_curve = [0.0]
for tr in trades:
    equity_curve.append(equity_curve[-1] + (tr.pnl_pct * 100))  # convert to %

return build_research_runner_envelope(
    runner_name="atr_breakout_runner",
    symbol=symbol,
    interval=interval,
    n_trades=len(trades),
    sharpe=sharpe,
    win_rate=win_rate,
    total_pnl_pct=total_pnl_pct,
    bars_per_year=bars_per_year,
    equity_curve=equity_curve,
    runner_label=f"ATR breakout {interval} {symbol} (LOCKED)",
    start=str(start_date),
    end=str(end_date),
)
```

(Note: `trades`, `sharpe`, `win_rate`, `total_pnl_pct`, `interval`, `symbol`, `start_date`, `end_date` are already in scope from existing function. If variable names differ, adjust to match.)

- [ ] **Step 4: Run test to verify PASS**

```bash
.venv/bin/pytest tests/integration/test_atr_breakout_dashboard_contract.py -v -m integration
```

Expected: PASS.

- [ ] **Step 5: Run existing baseline floor test (regression check)**

```bash
.venv/bin/pytest tests/integration/test_atr_breakout_baseline_floor.py -v -m integration
```

Expected: existing PnL replication still passes (819.81% / 264.29% / etc unchanged).

- [ ] **Step 6: Commit**

```bash
git add src/backtest/atr_breakout_runner.py tests/integration/test_atr_breakout_dashboard_contract.py
git commit -m "feat(s42): wire envelope helper into atr_breakout_runner"
```

- [ ] **Step 7: SPRINT_STATE update**

Same pattern as T1 step 6.

---

## Task 3: Wire envelope into volume_breakout_runner

**Files:**
- Modify: `src/backtest/volume_breakout_runner.py:230-265` (return dict)
- Test: `tests/integration/test_volume_breakout_dashboard_contract.py` (CREATE)

- [ ] **Step 1: Write the failing test**

```python
# tests/integration/test_volume_breakout_dashboard_contract.py
"""S42 T3 — volume_breakout dashboard envelope contract."""
from __future__ import annotations

import pytest

from src.dashboard.backtest_runner import BacktestRequest, run_backtest


@pytest.mark.integration
def test_volume_breakout_returns_envelope_keys() -> None:
    req = BacktestRequest(
        strategy_id="volume_breakout_iter10",
        symbol="BTCUSDT",
        interval="240",
        start="2023-01-01",
        end="2026-04-26",
    )
    r = run_backtest(req, force=True)
    for key in (
        "bars_per_year", "warnings", "failed_criteria", "verdict",
        "acceptance_gate", "dsr", "dsr_pass", "mc_p_value",
    ):
        assert key in r
    assert r["verdict"] == "RAW"
    assert r["failed_criteria"] == []
    assert any(w["code"] == "raw_full_period" for w in r["warnings"])
```

- [ ] **Step 2: Run test, verify FAIL**

```bash
.venv/bin/pytest tests/integration/test_volume_breakout_dashboard_contract.py -v -m integration
```

Expected: FAIL.

- [ ] **Step 3: Modify volume_breakout_runner return**

Same envelope-wrap pattern as T2 Step 3, applied к `src/backtest/volume_breakout_runner.py::run_volume_breakout_backtest`. Use `runner_name="volume_breakout_runner"`, `runner_label=f"Volume breakout 4H BTCUSDT (LOCKED — S39)"`. Reuse `bars_per_year_lookup` (move to envelope module if duplication bothers).

- [ ] **Step 4: Run test, verify PASS**

```bash
.venv/bin/pytest tests/integration/test_volume_breakout_dashboard_contract.py -v -m integration
```

- [ ] **Step 5: Commit**

```bash
git add src/backtest/volume_breakout_runner.py tests/integration/test_volume_breakout_dashboard_contract.py
git commit -m "feat(s42): wire envelope helper into volume_breakout_runner"
```

- [ ] **Step 6: SPRINT_STATE update**

---

## Task 4: Consolidate 10 atr_breakout presets → 1 parametric preset

**Files:**
- Modify: `src/dashboard/backtest_runner.py:30-260` (STRATEGY_PRESETS dict)
- Modify: `src/dashboard/backtest_runner.py:800-900` (run_backtest dispatch)
- Test: existing test_atr_breakout_baseline_floor.py — update preset_id

- [ ] **Step 1: Write the failing test (covers preset consolidation contract)**

```python
# Add к tests/integration/test_atr_breakout_dashboard_contract.py
@pytest.mark.integration
@pytest.mark.parametrize("symbol,interval,expected_pnl", [
    ("BTCUSDT", "240", 819.81),
    ("SOLUSDT", "240", 264.29),
    ("ETHUSDT", "60", 181.74),
    ("BTCUSDT", "15", 107.35),
    ("BTCUSDT", "60", 146.36),
    ("SOLUSDT", "60", 214.08),
    ("ETHUSDT", "240", 152.30),
    ("SOLUSDT", "15", 150.51),
    ("BTCUSDT", "D", 167.54),
    ("ETHUSDT", "15", 35.53),
])
def test_consolidated_atr_breakout_replicates_per_combo(
    symbol: str, interval: str, expected_pnl: float,
) -> None:
    """S42 T4 — single 'atr_breakout' preset returns correct PnL для каждого supported combo
    (server-side params lookup от ATR_BREAKOUT_LOCKED_PARAMS_BY_COMBO).
    """
    req = BacktestRequest(
        strategy_id="atr_breakout",
        symbol=symbol, interval=interval,
        start="2023-01-01" if interval != "240" or symbol != "BTCUSDT" else "2017-08-17",
        end="2026-04-30" if interval == "240" and symbol == "BTCUSDT" else "2026-04-26",
    )
    r = run_backtest(req, force=True)
    delta = abs(r["total_pnl_pct"] - expected_pnl)
    assert delta < 2.0, f"PnL drift: {symbol}_{interval} expected {expected_pnl} got {r['total_pnl_pct']} delta {delta}"


@pytest.mark.integration
def test_old_preset_ids_no_longer_exist() -> None:
    """Backward compat (Q4 verdict CONFIRM (a)) — 10 old preset_ids removed."""
    from src.dashboard.backtest_runner import STRATEGY_PRESETS
    old_ids = [
        "atr_breakout_iter_endless",
        "atr_breakout_sol_4h_s41", "atr_breakout_eth_1h_s41", "atr_breakout_btc_15m_s41",
        "atr_breakout_btc_1h_s41", "atr_breakout_sol_1h_s41", "atr_breakout_eth_4h_s41",
        "atr_breakout_sol_15m_s41", "atr_breakout_btc_1d_s41", "atr_breakout_eth_15m_s41",
    ]
    for old in old_ids:
        assert old not in STRATEGY_PRESETS, f"Old preset {old} should be removed (Q4 verdict)"
    assert "atr_breakout" in STRATEGY_PRESETS, "Unified preset missing"


@pytest.mark.integration
def test_atr_breakout_preset_has_supported_combos_field() -> None:
    """Q2 — supported_combos field for frontend gates."""
    from src.dashboard.backtest_runner import STRATEGY_PRESETS
    p = STRATEGY_PRESETS["atr_breakout"]
    assert "supported_combos" in p
    sc = p["supported_combos"]
    assert isinstance(sc, list)
    assert ("BTCUSDT", "240") in sc
    assert len(sc) == 10  # all autoresearch PASS combos
```

- [ ] **Step 2: Run tests, verify FAIL**

```bash
.venv/bin/pytest tests/integration/test_atr_breakout_dashboard_contract.py -v -m integration
```

Expected: FAIL — preset_id `atr_breakout` doesn't exist; old IDs still present.

- [ ] **Step 3: Replace 10 preset entries с 1 unified preset**

In `src/dashboard/backtest_runner.py`, delete entries for preset IDs `atr_breakout_iter_endless`, `atr_breakout_sol_4h_s41`, …, `atr_breakout_eth_15m_s41` (lines 92-254). Insert single preset:

```python
# At line 92 (after donchian_breakout_s35), before volume_breakout_iter10:
"atr_breakout": {
    "label": "[S42] ATR breakout (LOCKED params per autoresearch — symbol+TF parametric)",
    "type": "atr_breakout",
    "wfa": False,  # research-mode: WFA retrofit deferred к S43
    # Frontend introspects supported_combos to gate (sym, tf) options
    "supported_combos": [
        ("BTCUSDT", "15"), ("BTCUSDT", "60"), ("BTCUSDT", "240"), ("BTCUSDT", "D"),
        ("ETHUSDT", "15"), ("ETHUSDT", "60"), ("ETHUSDT", "240"),
        ("SOLUSDT", "15"), ("SOLUSDT", "60"), ("SOLUSDT", "240"),
    ],
    # Server-side dispatch reads ATR_BREAKOUT_LOCKED_PARAMS_BY_COMBO[(sym, tf)] at runtime
    "config": {
        "atr_breakout": {
            "lookup_via": "ATR_BREAKOUT_LOCKED_PARAMS_BY_COMBO",
        },
    },
},
```

In `run_backtest` dispatch (~line 870-900), replace per-preset param lookup. Find existing block:

```python
elif preset["type"] == "atr_breakout":
    preset_ab_params = preset["config"]["atr_breakout"]
    # … existing per-preset hardcoded params dispatch
```

Replace with:

```python
elif preset["type"] == "atr_breakout":
    from src.signalgen.atr_breakout_strategy import ATR_BREAKOUT_LOCKED_PARAMS_BY_COMBO
    combo_key = (req.symbol, req.interval)
    if combo_key not in ATR_BREAKOUT_LOCKED_PARAMS_BY_COMBO:
        raise ValueError(
            f"atr_breakout preset has no LOCKED params для {combo_key}. "
            f"Supported combos: {sorted(ATR_BREAKOUT_LOCKED_PARAMS_BY_COMBO.keys())}"
        )
    preset_ab_params = ATR_BREAKOUT_LOCKED_PARAMS_BY_COMBO[combo_key]
    result = run_atr_breakout_backtest(
        symbol=req.symbol,
        interval=req.interval,
        start_date=date.fromisoformat(req.start),
        end_date=date.fromisoformat(req.end),
        params=preset_ab_params,
    )
    # cache + return …
```

(Match existing exact return/cache code from one of the deleted blocks — preserve cache key derivation pattern.)

- [ ] **Step 4: Run new tests + parametrized PnL replication**

```bash
.venv/bin/pytest tests/integration/test_atr_breakout_dashboard_contract.py -v -m integration
```

Expected: 12+ tests PASS (10 parametrized PnL + envelope contract + supported_combos + old-ids-removed).

- [ ] **Step 5: Update existing baseline floor test к new preset_id**

```bash
grep -l "atr_breakout_iter_endless\|atr_breakout_sol_4h_s41\|atr_breakout_btc_15m_s41" tests/
```

For each match, replace old preset_id → `"atr_breakout"`. Run:

```bash
.venv/bin/pytest tests/integration/test_atr_breakout_baseline_floor.py -v -m integration
```

Expected: PASS (with updated preset_id references).

- [ ] **Step 6: Commit**

```bash
git add src/dashboard/backtest_runner.py tests/
git commit -m "refactor(s42): consolidate 10 atr_breakout presets → 1 parametric preset"
```

- [ ] **Step 7: SPRINT_STATE update**

---

## Task 5: API endpoint /api/strategy/{id}/info + combo enforcement

**Files:**
- Modify: `src/dashboard/app.py:96-130` (combo enforcement)
- Modify: `src/dashboard/app.py` (add new endpoint)
- Test: `tests/unit/test_supported_combos_endpoint.py` (CREATE)

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_supported_combos_endpoint.py
"""S42 T5 — supported_combos endpoint + combo enforcement tests."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.dashboard.app import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_strategy_info_endpoint_returns_supported_combos(client: TestClient) -> None:
    r = client.get("/api/strategy/atr_breakout/info")
    assert r.status_code == 200
    data = r.json()
    assert "supported_combos" in data
    assert ["BTCUSDT", "240"] in data["supported_combos"]
    assert len(data["supported_combos"]) == 10


def test_strategy_info_unknown_strategy_returns_404(client: TestClient) -> None:
    r = client.get("/api/strategy/nonexistent/info")
    assert r.status_code == 404


def test_strategy_info_legacy_preset_omits_supported_combos(client: TestClient) -> None:
    """Legacy presets (ema_crossover_s13) work с любого symbol/TF — no supported_combos field.
    Endpoint returns empty list OR omits field entirely.
    """
    r = client.get("/api/strategy/ema_crossover_s13/info")
    assert r.status_code == 200
    data = r.json()
    # Legacy preset has no combo restriction
    assert data.get("supported_combos") in (None, [])


def test_backtest_invalid_combo_for_atr_breakout_rejected_422(client: TestClient) -> None:
    """Pick BTCUSDT 5m — not в supported_combos. Server rejects 422."""
    r = client.post("/api/backtest", json={
        "strategy_id": "atr_breakout",
        "symbol": "BTCUSDT",
        "interval": "5",
        "start": "2024-01-01",
        "end": "2024-06-01",
    })
    assert r.status_code == 422
    assert "supported_combos" in r.json()["detail"].lower() or "no LOCKED params" in r.json()["detail"]


def test_backtest_valid_combo_for_atr_breakout_accepted(client: TestClient) -> None:
    """BTCUSDT 240 IS в supported_combos."""
    r = client.post("/api/backtest", json={
        "strategy_id": "atr_breakout",
        "symbol": "BTCUSDT",
        "interval": "240",
        "start": "2024-01-01",
        "end": "2024-06-01",
    })
    # 200 OR 500 (data not found) — but NOT 422 (combo accepted)
    assert r.status_code != 422
```

- [ ] **Step 2: Run, verify FAIL**

```bash
.venv/bin/pytest tests/unit/test_supported_combos_endpoint.py -v
```

- [ ] **Step 3: Add endpoint к app.py**

Insert после `/api/strategies` route (~line 87):

```python
    @app.get("/api/strategy/{strategy_id}/info")
    async def get_strategy_info(strategy_id: str) -> dict[str, object]:
        preset = STRATEGY_PRESETS.get(strategy_id)
        if preset is None:
            raise HTTPException(status_code=404, detail=f"Unknown strategy: {strategy_id}")
        # supported_combos is preset-specific (atr_breakout uses it; legacy presets do not)
        # Convert tuple → list for JSON serialization
        sc_raw = preset.get("supported_combos", [])
        sc_serialized: list[list[str]] = [list(combo) for combo in sc_raw]
        return {
            "id": strategy_id,
            "label": preset["label"],
            "type": preset["type"],
            "supported_combos": sc_serialized,
            "locked_symbol": preset.get("locked_symbol"),
            "locked_interval": preset.get("locked_interval"),
        }
```

Modify `/api/backtest` enforcement (~line 96-120) — add supported_combos check after locked_symbol/locked_interval block:

```python
        # S42 T5 — supported_combos enforcement (atr_breakout multi-combo presets)
        supported_combos = preset.get("supported_combos")
        if supported_combos:
            combo_key = (payload.symbol, payload.interval)
            # supported_combos может быть list[tuple] OR list[list] (after JSON round-trip)
            normalized = [tuple(c) for c in supported_combos]
            if combo_key not in normalized:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"Strategy {payload.strategy_id} has no LOCKED params для "
                        f"({payload.symbol}, {payload.interval}). "
                        f"supported_combos: {normalized}"
                    ),
                )
```

- [ ] **Step 4: Run tests, verify PASS**

```bash
.venv/bin/pytest tests/unit/test_supported_combos_endpoint.py -v
```

Expected: 5/5 PASS.

- [ ] **Step 5: Commit**

```bash
git add src/dashboard/app.py tests/unit/test_supported_combos_endpoint.py
git commit -m "feat(s42): /api/strategy/{id}/info endpoint + supported_combos enforcement"
```

- [ ] **Step 6: SPRINT_STATE update**

---

## Task 6: Dashboard JS defensive guards + frontend combo gates

**Files:**
- Modify: `src/dashboard/static/dashboard.js:180-210` (renderResult defensive)
- Modify: `src/dashboard/static/dashboard.js` (top — add fetchStrategyInfo + applyComboGates)
- Modify: `src/dashboard/templates/index.html` if DOM hooks needed

- [ ] **Step 1: Write the failing test (browser-level smoke)**

Manual smoke acceptable here — JS does not have unit tests yet. Plan creates an automated test instead via FastAPI:

```python
# Add к tests/integration/test_atr_breakout_dashboard_contract.py
@pytest.mark.integration
def test_atr_breakout_response_renders_without_undefined_fields() -> None:
    """Final guard — every key dashboard.js reads MUST exist on response."""
    req = BacktestRequest(
        strategy_id="atr_breakout", symbol="BTCUSDT", interval="240",
        start="2024-01-01", end="2024-06-01",
    )
    r = run_backtest(req, force=True)
    # Mirror dashboard.js property accesses
    js_accessed_keys = [
        "run_id", "cached", "request", "bars_per_year",
        "verdict", "failed_criteria", "warnings",
    ]
    for k in js_accessed_keys:
        assert k in r, f"dashboard.js will throw — missing {k}"
    # Sub-properties JS accesses
    assert "strategy_label" in r["request"]
    assert "symbol" in r["request"]
    assert "interval_label" in r["request"]
    assert isinstance(r["failed_criteria"], list)  # .length used
    assert isinstance(r["warnings"], list)
```

- [ ] **Step 2: Run, verify already passes from T1+T2** (sanity check)

- [ ] **Step 3: Add defensive guards к dashboard.js renderResult (lines 188-200)**

Replace lines 188-200 in `src/dashboard/static/dashboard.js` с defensive variants:

```javascript
  $("run-meta").innerHTML = `
    <div class="meta-key">RUN_ID</div><div class="meta-val">${r.run_id}${cachedTag}</div>
    <div class="meta-key">STRATEGY</div><div class="meta-val">${r.request?.strategy_label ?? r.request?.strategy_id ?? "?"}</div>
    <div class="meta-key">SYMBOL · TF</div><div class="meta-val">${r.request?.symbol ?? "?"} · ${r.request?.interval_label ?? r.request?.interval ?? "?"}</div>
    <div class="meta-key">RANGE</div><div class="meta-val">${r.request?.start ?? "?"} → ${r.request?.end ?? "?"} · ${(r.bars_per_year ?? 0).toLocaleString()} bars/year</div>
  `;

  const verdict = r.verdict ?? "—";
  const verdictCls = verdict === "PASS" ? "verdict-pass" : (verdict === "RAW" ? "verdict-raw" : "verdict-fail");
  const failedCriteria = r.failed_criteria ?? [];
  const failedHtml = failedCriteria.length
    ? `<div class="verdict-failed-list">FAILED CRITERIA: ${failedCriteria.map((c) => `<span class="chip">${c.toUpperCase()}</span>`).join(" ")}</div>`
    : "";
```

Add CSS class `.verdict-raw { color: var(--warn-mid, #f0a000); }` к `src/dashboard/static/dashboard.css` (or wherever existing verdict styles live).

- [ ] **Step 4: Add fetchStrategyInfo + combo gating logic (top of dashboard.js or near init)**

```javascript
// S42 T6 — combo gating для atr_breakout-style presets с supported_combos
async function fetchStrategyInfo(strategyId) {
  try {
    const r = await fetch(`/api/strategy/${strategyId}/info`);
    if (!r.ok) return null;
    return await r.json();
  } catch {
    return null;
  }
}

async function applyComboGates(strategyId) {
  const info = await fetchStrategyInfo(strategyId);
  const symSel = $("symbol-select");
  const tfSel = $("interval-select");
  // Reset: enable all options
  for (const sel of [symSel, tfSel]) {
    Array.from(sel.options).forEach(opt => { opt.disabled = false; });
  }
  if (!info || !info.supported_combos || info.supported_combos.length === 0) return;
  const validSymbols = new Set(info.supported_combos.map(c => c[0]));
  const validIntervals = new Set(info.supported_combos.map(c => c[1]));
  // Cross-filter: when sym selected, only valid TFs for that sym remain enabled
  const sym = symSel.value;
  const tfsForSym = new Set(
    info.supported_combos.filter(c => c[0] === sym).map(c => c[1])
  );
  Array.from(symSel.options).forEach(opt => {
    if (!validSymbols.has(opt.value)) opt.disabled = true;
  });
  Array.from(tfSel.options).forEach(opt => {
    if (tfsForSym.size && !tfsForSym.has(opt.value)) opt.disabled = true;
    else if (!tfsForSym.size && !validIntervals.has(opt.value)) opt.disabled = true;
  });
}

// Wire to strategy/symbol change handlers (find existing change listeners)
$("strategy-select").addEventListener("change", () => {
  applyComboGates($("strategy-select").value);
});
$("symbol-select").addEventListener("change", () => {
  applyComboGates($("strategy-select").value);
});
// Initial call
applyComboGates($("strategy-select").value);
```

(If existing event listeners already exist на change — chain rather than overwrite. Read existing handler chain first.)

- [ ] **Step 5: Manual browser test**

```bash
./scripts/start-bot.sh
# Open http://127.0.0.1:8000/
# Select "atr_breakout" preset
# Verify only valid (sym, TF) combinations are selectable
# Run backtest BTCUSDT 240 → verify no JS console errors, page renders
# Run backtest BTCUSDT 5m attempt → if not blocked в UI, server returns 422 with clear message
```

Document results in commit message.

- [ ] **Step 6: Commit**

```bash
git add src/dashboard/static/dashboard.js src/dashboard/static/*.css
git commit -m "feat(s42): JS defensive guards + frontend combo gates для atr_breakout"
```

- [ ] **Step 7: SPRINT_STATE update**

---

## Task 7: Sub-period robustness chip surfacing in UI

**Files:**
- Modify: `src/dashboard/static/dashboard.js` (warnings render block — already shows warnings via existing renderResult code path)
- Verify: warnings array from envelope is automatically rendered

- [ ] **Step 1: Write a manual UI verification step (no new code expected — envelope already pushes chip)**

Sub-period robustness chip is added to `warnings` array by `build_research_runner_envelope` (T1). Existing dashboard.js `warnings-panel` rendering loop (lines ~205-215 — `r.warnings.map(...)`) already handles arbitrary `{level, code, message}` items.

Verification only: confirm chip displays.

- [ ] **Step 2: Manual verification**

```bash
./scripts/start-bot.sh
# Select atr_breakout, BTCUSDT 240, full date range → expect 5/5 chip (info-level)
# Select atr_breakout, ETHUSDT 15, full date range → expect 4/5 OR 3/5 chip (warn-level)
```

Capture screenshot OR document observed chip text in commit message.

- [ ] **Step 3: If existing JS warning render does NOT colour-distinguish by level**

Inspect `src/dashboard/static/dashboard.css` for `.warn-info`, `.warn-mid`, `.warn-high` classes. If absent, add:

```css
.warn-info { color: var(--ok-color, #00b894); }
.warn-mid  { color: var(--warn-color, #f0a000); }
.warn-high { color: var(--err-color, #e74c3c); }
```

- [ ] **Step 4: Commit**

```bash
git add src/dashboard/static/dashboard.css
git commit -m "feat(s42): sub-period robustness chip color levels"
```

(If no CSS edit needed — skip commit, mark task verified-no-change.)

- [ ] **Step 5: SPRINT_STATE update**

---

## Task 8: Test sweep — full pytest run + new test consolidation

**Files:**
- Run: full pytest suite
- Modify: any test file referencing old preset_ids (already done в T4 step 5; sweep again)

- [ ] **Step 1: Sweep tests for stale preset_id references**

```bash
grep -rn "atr_breakout_iter_endless\|atr_breakout_sol_\|atr_breakout_eth_\|atr_breakout_btc_" tests/ src/ llm-wiki/ 2>&1 | grep -v ".original\|.git" | head -20
```

For each hit (excluding wiki ADR pages 0060, 0061, autoresearch artifacts):
- Replace old ID → `"atr_breakout"`
- Verify context is testing dispatch, not historical reference

- [ ] **Step 2: Run full unit + integration suites**

```bash
.venv/bin/pytest tests/unit -q
.venv/bin/pytest tests/integration -q -m integration
.venv/bin/mypy --strict src/
```

Expected:
- Unit: previous baseline + 6 new (T1) + 5 new (T5) = ~945+ pass
- Integration: previous + 12 new (T2 + T3 + T4 + T6) = ~45+ pass
- mypy: 0 errors (no type regressions)

If any failure surfaces — fix inline, do NOT skip.

- [ ] **Step 3: Verify endless autoresearch process still alive (sanity)**

```bash
ps aux | grep autoresearch_endless | grep -v grep
```

Expected: PID 17127 still running (sprint should not interfere with background autoresearch).

- [ ] **Step 4: Commit (if any test edits)**

```bash
git add tests/
git commit -m "test(s42): replace stale preset_id references after consolidation"
```

- [ ] **Step 5: SPRINT_STATE update**

---

## Task 9: ADR 0062 + supersede 0060/0061

**Files:**
- Create: `llm-wiki/wiki/project/decisions/0062-sprint-42-atr-breakout-hardening.md`
- Modify: `llm-wiki/wiki/project/decisions/0060-sprint-40-atr-breakout-production.md` (status: superseded)
- Modify: `llm-wiki/wiki/project/decisions/0061-sprint-41-multi-combo-presets.md` (status: superseded)

- [ ] **Step 1: Create ADR 0062**

```markdown
# 0062. Sprint 42 — atr_breakout production hardening (kit retrofit)

**Status:** accepted
**Date:** 2026-05-10
**Supersedes:** [[0060-sprint-40-atr-breakout-production]], [[0061-sprint-41-multi-combo-presets]]

## Контекст

S40 + S41 поставили atr_breakout strategy в dashboard через bypass kit (operator overnight rule). Operator затем обнаружил три класса проблем:

1. **UI crash:** dashboard.js бросает `Cannot read properties of undefined (reading 'toLocaleString')` при выборе любого atr_breakout preset. Корень: `atr_breakout_runner` returns 8 keys, dashboard ожидает 17 (replay engine contract).
2. **UX clutter:** S41 добавил 9 separate presets per (symbol, TF) — 10 entries в dropdown. Операторы attesto не любят шум.
3. **Acceptance discipline gap:** atr_breakout bypasses WFA + DSR + MC + T1-T6 acceptance. Inflated raw full-period PnL отображается без OOS validation.

## Варианты

(a) **Full WFA retrofit за один sprint** — restore acceptance discipline, fix crash, consolidate presets. Maintainer initial recommendation.

(b) **Crash fix + RAW_FULL_PERIOD honest label, defer WFA к S43** — split в 2 sprints. Acknowledge structural PnL accounting gap (sequential-additive vs Kelly-compounded) перед WFA wrapping. Trader-expert ROUND 1 recommendation.

(c) Ignore — accept current state с manual UI workarounds.

## Решение

**Option (b) — split в S42 (immediate fix) + S43 (WFA retrofit).**

Rationale: trader-expert ROUND 1 highlighted что atr_breakout_runner uses sequential-additive PnL accounting, while replay engine uses Kelly-sized compounded PnL. Wrapping WFA folds на incompatible PnL accounting = silent contract violation. PASS verdict from such a run = structurally misleading. WFA retrofit MUST resolve underlying gap (atr_breakout_runner.py:6-12 documented gaps) перед wrapping.

S42 scope (THIS ADR):
1. Crash fix — `build_research_runner_envelope()` helper wraps research runners к dashboard contract. Returns null sentinels для acceptance_gate / DSR / MC + high-level "raw_full_period" warning chip.
2. Preset consolidation — 10 atr_breakout_* presets → 1 `atr_breakout` с `supported_combos: list[tuple[str, str]]`. Server-side params lookup в `ATR_BREAKOUT_LOCKED_PARAMS_BY_COMBO[(sym, tf)]`.
3. Frontend gates — `/api/strategy/{id}/info` endpoint + UI greys out invalid (sym, TF) options.
4. Sub-period robustness chip — N/5 positive periods displayed alongside warnings.
5. Honest label `RAW_FULL_PERIOD — WFA retrofit pending S43`.
6. Same envelope wrap для volume_breakout (S39).
7. Backward compat — full replace 10 preset_ids, no aliases (project в alpha).

S43 scope (deferred):
- Resolve atr_breakout_runner.py:6-12 structural PnL accounting gaps.
- Wrap full WFA + DSR + MC + T1-T6 acceptance gate.
- Restore epistemic discipline.

## Последствия

**Pros:**
- Crash fixed immediately — operators can use atr_breakout preset.
- UX cleaner (1 preset instead of 10).
- Honest disclosure (`RAW_FULL_PERIOD` chip) prevents over-trust в inflated training PnL.
- Scope contained — single architectural fix S43 covers WFA retrofit для both atr_breakout + volume_breakout.

**Cons:**
- Acceptance discipline temporarily skipped для atr_breakout + volume_breakout. S43 must follow within 1-2 sprints to restore.
- Backward compat broken — bookmarked URLs к old preset_ids will 422. Mitigated: alpha release, not prod.

**Carry-overs к S43:**
- Full WFA retrofit для atr_breakout + volume_breakout runners.
- DSR computation per combo.
- MC permutation tests.
- N_trials counter increment.

## Связанные

- [[../sprints/sprint-42-atr-breakout-hardening]]
- [[../plans/2026-05-10-sprint-42-atr-breakout-hardening]]
- [[../pre-s42-backlog]]
- [[0052-acceptance-criteria-amendment-locked]] (T1-T6 acceptance gate restored S43)
- [[0060-sprint-40-atr-breakout-production]] (superseded)
- [[0061-sprint-41-multi-combo-presets]] (superseded)
```

- [ ] **Step 2: Mark 0060 + 0061 as superseded**

In each file, change `**Status:** accepted` → `**Status:** superseded by [[0062-sprint-42-atr-breakout-hardening]]` plus add `**Superseded:** 2026-05-10` line below.

- [ ] **Step 3: Commit**

```bash
git add llm-wiki/wiki/project/decisions/0062-sprint-42-atr-breakout-hardening.md llm-wiki/wiki/project/decisions/0060-*.md llm-wiki/wiki/project/decisions/0061-*.md
git commit -m "docs(s42): ADR 0062 + supersede ADR 0060 + ADR 0061"
```

- [ ] **Step 4: SPRINT_STATE update**

---

## Task 10: Wiki sync — sprint-42 page + index + log + canonical refs

**Files:**
- Create: `llm-wiki/wiki/project/sprints/sprint-42-atr-breakout-hardening.md`
- Modify: `llm-wiki/wiki/project/architecture/current-state.md` (sprint history row + ADR list)
- Modify: `llm-wiki/wiki/index.md` (ADR + sprint entries)
- Modify: `llm-wiki/wiki/log.md` (append session-end entry)
- Modify: `llm-wiki/wiki/project/components/atr-breakout-strategy.md` (preset_id rename + envelope contract reference)

- [ ] **Step 1: Create sprint-42 page**

```markdown
---
title: "Sprint 42 — atr_breakout production hardening"
type: sprint
tags: [sprint-42, retrofit, atr-breakout, dashboard]
created: 2026-05-10
updated: 2026-05-10
status: completed
sources:
  - llm-wiki/wiki/project/decisions/0062-sprint-42-atr-breakout-hardening.md
  - llm-wiki/wiki/project/plans/2026-05-10-sprint-42-atr-breakout-hardening.md
  - llm-wiki/wiki/project/pre-s42-backlog.md
---

# Sprint 42 — atr_breakout production hardening

## Цель

Fix dashboard crash при выборе atr_breakout/volume_breakout preset, consolidate 10 → 1 atr_breakout preset, добавить honest RAW_FULL_PERIOD label до S43 WFA retrofit.

## Доставленная функциональность

### Код
- `src/backtest/research_runner_envelope.py` — NEW helper `build_research_runner_envelope()`
- `src/backtest/atr_breakout_runner.py` — wired envelope helper
- `src/backtest/volume_breakout_runner.py` — wired envelope helper
- `src/dashboard/backtest_runner.py` — 10 atr_breakout presets → 1 unified `atr_breakout` с `supported_combos`
- `src/dashboard/app.py` — new `/api/strategy/{id}/info` endpoint + supported_combos enforcement в `/api/backtest`
- `src/dashboard/static/dashboard.js` — defensive guards + `applyComboGates()` для UI greying

### Тесты
- `tests/unit/test_research_runner_envelope.py` — 6 tests (envelope contract)
- `tests/unit/test_supported_combos_endpoint.py` — 5 tests (endpoint + enforcement)
- `tests/integration/test_atr_breakout_dashboard_contract.py` — ~12 tests (parametrized PnL replication + envelope keys)
- `tests/integration/test_volume_breakout_dashboard_contract.py` — 1 test (envelope keys)
- Existing `test_atr_breakout_baseline_floor.py` — updated к new preset_id

### Wiki
- ADR 0062 (THIS sprint)
- ADR 0060 + 0061 marked superseded
- sprint-42 page (THIS file)
- current-state.md sprint history row
- index.md entries
- log.md session-end entry
- atr-breakout-strategy component page — preset_id rename

## Решения и отклонения

- Q3 EXPAND: Trader-expert reframed scope. Crash fix + RAW label в S42; WFA retrofit deferred к S43. PnL accounting gap (sequential-additive vs Kelly-compounded) MUST be resolved first.
- Q5 REVISE: volume_breakout (S39) gets same envelope wrap в S42 для unified contract; WFA retrofit deferred к S43.

## Влияние на следующие спринты

- **S43 must address:** Full WFA retrofit (atr_breakout + volume_breakout). Resolve atr_breakout_runner.py:6-12 structural gaps. Restore acceptance discipline (T1-T6 + DSR + MC + N_trials counter).

## Перенесённые задачи

- F8 block_size, M1-M4 bybit-api, Item #7 shim, Item #10 — unaffected by S42, remain в backlog.

## Связанные

- [[../decisions/0062-sprint-42-atr-breakout-hardening]]
- [[../plans/2026-05-10-sprint-42-atr-breakout-hardening]]
- [[../pre-s42-backlog]]
```

- [ ] **Step 2: Update current-state.md**

Locate sprint history table в `current-state.md`. Append row:

```
| S42 | 2026-05-10 | atr_breakout production hardening (kit retrofit) | v0.1.0-alpha.42 | ADR 0062 |
```

Update canonical-counts если изменились (FSM transitions / reason codes / components). Likely unchanged S42 — no FSM impact.

- [ ] **Step 3: Update index.md**

Add ADR 0062 + sprint-42 entries в appropriate sections. Mark 0060 + 0061 as `(superseded by 0062)` в decisions list.

- [ ] **Step 4: Append log.md session-end entry**

```markdown
## [2026-05-10] sprint-end | Sprint 42 — atr_breakout production hardening
- Shipped: research_runner_envelope helper, 1 unified atr_breakout preset (10 → 1), /api/strategy/{id}/info endpoint, JS defensive guards, RAW_FULL_PERIOD honest label
- Tests: ~24 new (6 unit envelope + 5 unit endpoint + ~13 integration). Total pytest GREEN.
- ADR 0062 supersedes 0060 + 0061. Tag v0.1.0-alpha.42.
- Carry к S43: Full WFA retrofit для atr_breakout + volume_breakout. Resolve PnL accounting structural gap.
```

- [ ] **Step 5: Update component pages**

Edit `llm-wiki/wiki/project/components/atr-breakout-strategy.md`:
- Replace references к preset_ids `atr_breakout_iter_endless`, `atr_breakout_sol_4h_s41`, etc → single `atr_breakout` preset с supported_combos table
- Add reference к envelope helper в Public API section
- Add note "Acceptance gate skipped до S43 WFA retrofit (per ADR 0062)"

- [ ] **Step 6: Commit + tag prep**

```bash
git add llm-wiki/
git commit -m "docs(s42): wiki sync — sprint-42 page, ADR 0062, current-state, index, log"
```

- [ ] **Step 7: SPRINT_STATE final update — phase=8-ship**

```yaml
sprint: 42
phase: 8-ship
branch: feature/sprint-42-atr-breakout-hardening
tag: v0.1.0-alpha.42
```

```bash
git add llm-wiki/wiki/project/SPRINT_STATE.md
git commit -m "docs(sprint): SPRINT_STATE phase=8-ship"
```

---

## PHASE 6 — Domain Reviewers (MANDATORY before merge)

Dispatch in parallel after T10 commits land:

| Reviewer | Focus |
|----------|-------|
| `trading-logic-reviewer` | Preset consolidation correctness, no look-ahead introduced, ReasonCode unchanged, FSM unaffected |
| `dashboard-reviewer` | UI contract compliance, JS defensive guards, supported_combos UX, look-ahead bias prevention в dashboard, TIER 1+TIER 2 metrics + 4 mandatory warnings |
| `python-reviewer` | PEP 8, type hints на envelope helper, defensive `??` patterns, no swallowed exceptions |
| `test-engineer` | Coverage gaps, parametrized PnL replication thoroughness, envelope contract test completeness |
| `doc-reviewer` | ADR 0062 wiki-link integrity, supersede markers in 0060+0061, sprint-42 frontmatter completeness, Block 1↔Block 2 sync |

Aggregate findings. Fix blockers before merge.

---

## PHASE 8 — Ship

Use `sprint-finish` skill OR `superpowers:finishing-a-development-branch`:

```bash
.venv/bin/pytest tests/unit tests/integration -q
.venv/bin/mypy --strict src/
git push -u origin feature/sprint-42-atr-breakout-hardening
gh pr create --title "Sprint 42: atr_breakout production hardening (kit retrofit)" --body "$(cat <<'EOF'
## Summary
- Fix dashboard crash on atr_breakout/volume_breakout presets (toLocaleString of undefined)
- Consolidate 10 atr_breakout presets → 1 parametric preset с supported_combos
- Honest RAW_FULL_PERIOD label until S43 WFA retrofit
- ADR 0062 supersedes 0060+0061

## Test plan
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Dashboard loads BTCUSDT 4H atr_breakout — no JS console errors
- [ ] Invalid combo (BTCUSDT 5m) → UI greys out, server returns 422 если bypass
EOF
)"
# squash-merge after reviewer GREEN
git tag -a v0.1.0-alpha.42 -m "Sprint 42 — atr_breakout production hardening" <merge-sha>
git push origin v0.1.0-alpha.42
```

---

## Self-Review Verification

**Spec coverage:**
- Q1 (preset consolidation) → T4
- Q2 (frontend gates + missing combo handling) → T5 + T6
- Q3 (envelope helper + RAW label) → T1 + T2 + T3
- Q4 (backward compat replace) → T4
- Q5 (volume_breakout same fix) → T3
- Q6 (sub-period chip) → T1 + T7
- Q7 (ADR 0062) → T9
- All wiki sync → T10
- All PHASE 6 reviewers MANDATORY (skipped в S40+S41 — operator concern resolved)

**Type consistency:**
- `build_research_runner_envelope()` signature consistent across T1/T2/T3
- `supported_combos: list[tuple[str, str]]` consistent T4/T5/T6
- `RAW` verdict string consistent T1/T9 ADR / T6 CSS class

**Placeholder scan:** None — all code blocks complete.

**Plan complete and saved to `llm-wiki/wiki/project/plans/2026-05-10-sprint-42-atr-breakout-hardening.md`.**
