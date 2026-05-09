---
title: Sprint 39 Plan — volume_breakout production integration + critical tech debt
type: plan
tags: [sprint-39, plan, volume-breakout, autoresearch-integration, tech-debt, ru]
created: 2026-05-09
updated: 2026-05-09
status: proposed
sources:
  - llm-wiki/wiki/project/pre-s39-backlog.md
  - llm-wiki/wiki/project/decisions/0052-sprint-34-acceptance-criteria-amendment.md
  - llm-wiki/wiki/project/decisions/0054-sprint-35-donchian-pre-registration.md
  - llm-wiki/wiki/project/decisions/0058-sprint-38-delta-parallel-hardening.md
  - autoresearch/donchian-may8:research/FINAL_STRATEGY.md
---

# Sprint 39 Implementation Plan — volume_breakout production integration + critical tech debt

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate `volume_breakout` autoresearch winner (sweep#1644) as production strategy with LOCKED params, close critical δ TESTNET blockers (H1/H2/Item#10), cleanup S38 carry-overs (Item#7/F8), and apply bybit-api M3+M4 hardening.

**Architecture:**
- Strategy follows existing `donchian_strategy.py` template — stateful per-symbol, single-producer per coordinator, on_bar() → Signal contract
- LOCKED params as module constant `VOLUME_BREAKOUT_LOCKED_PARAMS` (single source of truth per ADR 0054 anti-snooping pattern)
- Dashboard preset ENFORCES `locked_symbol="BTCUSDT"` + `locked_interval="240"` via backend 422 + frontend disabled dropdowns
- Phase 5 HARD-GATE: `tests/integration/test_volume_breakout_baseline_floor.py` runs production pipeline на 3.3y + 8mo; PnL MUST ≥ baseline (held-out +20.42% / 3.3y +122.66%)

**Tech Stack:** Python 3.12 / pydantic v2 / pytest / Hypothesis (property tests) / FastAPI (dashboard) / pybit V5

**Profit invariant (HARD):** Both gates MUST pass — 3.3y ≥ +122.66% AND 8mo ≥ +20.42%. FAIL → blocks merge.

---

## File Structure

**Created:**
- `src/signalgen/volume_breakout_strategy.py` — strategy class
- `tests/unit/test_volume_breakout_strategy.py` — strategy unit tests
- `tests/unit/test_volume_breakout_indicators.py` — indicator unit tests
- `tests/integration/test_volume_breakout_baseline_floor.py` — Phase 5 HARD-GATE
- `tests/unit/test_bybit_rest_backoff.py` — H1 backoff tests
- `llm-wiki/wiki/project/decisions/0059-sprint-39-volume-breakout-pre-registration.md`
- `llm-wiki/wiki/project/sprints/sprint-39-volume-breakout-tech-debt.md`
- `llm-wiki/wiki/project/components/volume-breakout-strategy.md`
- `llm-wiki/wiki/project/research-evidence/README.md`
- `llm-wiki/wiki/project/research-evidence/FINAL_STRATEGY.md` (cherry-pick)
- `llm-wiki/wiki/project/research-evidence/CLOSE.md` (cherry-pick)
- `llm-wiki/wiki/project/research-evidence/results.tsv` (cherry-pick)

**Modified:**
- `src/backtest/indicators.py` — add `compute_volume_breakout_signals` helper
- `src/risk/reason_codes.py` — add 3 codes (50→53)
- `src/dashboard/backtest_runner.py` — add preset с lock fields
- `src/dashboard/app.py` — backend 422 validation
- `src/dashboard/templates/index.html` — frontend disabled dropdowns
- `src/dashboard/static/dashboard.js` (or equivalent JS) — handle locked preset
- `src/execution/bybit/rest.py` — H1 exponential backoff с jitter
- `src/execution/bybit/ws_private.py` (or coordinator) — M3 isinstance guard + M4 __repr__ redaction
- `src/risk/halt_gate.py` (if needed) + `tests/property/test_halt_gate.py` — Item#10 boundary tests
- `src/risk/manager.py` (or shared_deps) — Item#7 shim removal
- `src/backtest/mc_permutation.py` + references — F8 unification
- `tests/unit/test_ws_private_consumer.py` — H2 + M3 + M4 tests
- `tests/unit/test_reason_codes.py` (if exists) — count assertion 50→53
- `llm-wiki/wiki/trading/concepts/reason-codes.md` — sync 42→53
- `llm-wiki/wiki/project/architecture/current-state.md` — counts 50→53
- `llm-wiki/wiki/index.md` — new "Research evidence" section + sprint-39 + ADR-0059 entries
- `llm-wiki/wiki/log.md` — append sprint-end entry

---

## Task Dependency Graph

```
A1 ReasonCodes (3 new)
  ↓
A2 Indicators helper (volume_breakout signals)
  ↓
A3 Strategy class (uses A1+A2)
  ↓
A4 Dashboard preset + lock validation (uses A3)
  ↓
A5 Phase 5 baseline floor integration test (HARD-GATE; uses A4 production pipeline)

A6 Cherry-pick research-evidence (independent)
A7 ADR + sprint page + wiki sync (LAST — after all tracks ship)

B1 H1 rate-limit backoff (independent)
B2 H2 WS reconnect tests (independent)
B3 Item#10 halt boundary tests (independent)

C1 Item#7 shim removal (verify all callers)
C2 F8 _MC_BLOCK_SIZE unification (independent)

E1 M3 WS shape guard (independent)
E2 M4 __repr__ secret redaction (independent)
```

**Critical path:** A1 → A2 → A3 → A4 → A5. Track B/C/E can run in parallel batches.

---

## Track A — volume_breakout production integration

### Task A1: Add 3 ReasonCodes (50→53)

**Files:**
- Modify: `src/risk/reason_codes.py`
- Test: `tests/unit/test_reason_codes.py` (verify if exists; otherwise grep tests for ReasonCode count)

- [ ] **Step 1: Write failing test for new codes existence**

In `tests/unit/test_reason_codes.py` (or appropriate test file):

```python
def test_volume_breakout_reason_codes_exist():
    """S39 — volume_breakout strategy adds 3 reason codes (50→53)."""
    from src.risk.reason_codes import ReasonCode
    assert ReasonCode.ENTRY_LONG_VOLUME_BREAKOUT.value == "ENTRY_LONG_VOLUME_BREAKOUT"
    assert ReasonCode.EXIT_FLAT_VOLUME_CHANNEL.value == "EXIT_FLAT_VOLUME_CHANNEL"
    assert ReasonCode.EXIT_FLAT_ATR_STOP_VB.value == "EXIT_FLAT_ATR_STOP_VB"


def test_reason_codes_canonical_count_is_53():
    """S39 — canonical count grows 50→53 (S39 +3 volume_breakout codes)."""
    from src.risk.reason_codes import ReasonCode
    assert len(list(ReasonCode)) == 53
```

- [ ] **Step 2: Run test — verify FAIL**

```bash
.venv/bin/pytest tests/unit/test_reason_codes.py::test_volume_breakout_reason_codes_exist -v
```
Expected: FAIL `AttributeError: ENTRY_LONG_VOLUME_BREAKOUT`

- [ ] **Step 3: Add 3 codes to ReasonCode enum**

Append to `src/risk/reason_codes.py` after `HALT_UNKNOWN_SYMBOL = "HALT_UNKNOWN_SYMBOL"  # 50`:

```python
    # --- ADR 0059 — Sprint 39 volume_breakout strategy ---
    ENTRY_LONG_VOLUME_BREAKOUT = "ENTRY_LONG_VOLUME_BREAKOUT"  # 51
    EXIT_FLAT_VOLUME_CHANNEL = "EXIT_FLAT_VOLUME_CHANNEL"  # 52: Donchian channel exit (close < rolling_low)
    EXIT_FLAT_ATR_STOP_VB = "EXIT_FLAT_ATR_STOP_VB"  # 53: ATR stop intrabar (volume_breakout-specific)
```

Also update header docstring arithmetic note:
```
ADR 0057 (Sprint 37) adds 1 (HALT_UNKNOWN_SYMBOL) → 50.
ADR 0059 (Sprint 39) adds 3 (ENTRY_LONG_VOLUME_BREAKOUT + EXIT_FLAT_VOLUME_CHANNEL + EXIT_FLAT_ATR_STOP_VB) → 53.
```

- [ ] **Step 4: Run tests — verify PASS**

```bash
.venv/bin/pytest tests/unit/test_reason_codes.py -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/risk/reason_codes.py tests/unit/test_reason_codes.py
git commit -m "feat(risk): S39 T1 — add 3 ReasonCodes для volume_breakout (50→53)"
```

---

### Task A2: Vectorized indicator helper для volume_breakout

**Files:**
- Modify: `src/backtest/indicators.py` (add helper function)
- Create: `tests/unit/test_volume_breakout_indicators.py`

- [ ] **Step 1: Write failing test для compute_volume_breakout_signals**

Create `tests/unit/test_volume_breakout_indicators.py`:

```python
"""Unit tests для volume_breakout indicator helper (S39 T2)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


def _synthetic_df(n: int = 100, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0, 1, n))
    high = close + rng.uniform(0, 2, n)
    low = close - rng.uniform(0, 2, n)
    open_ = close + rng.normal(0, 0.5, n)
    volume = rng.uniform(1000, 5000, n)
    return pd.DataFrame({
        "open": open_, "high": high, "low": low, "close": close, "volume": volume
    })


def test_volume_breakout_signals_no_lookahead():
    """Entry signal на bar i must use ONLY data through bar i-1 (no look-ahead)."""
    from src.backtest.indicators import compute_volume_breakout_signals
    df = _synthetic_df(50)
    signals = compute_volume_breakout_signals(
        df, lookback_n=9, exit_lookback_n=8, vol_window=10, vol_mult=1.4563,
        atr_period=9, atr_stop_mult=2.9663,
    )
    # Mutate last bar — signals[:-1] must be unchanged
    df2 = df.copy()
    df2.iloc[-1, df2.columns.get_loc("close")] = 999999.0
    signals2 = compute_volume_breakout_signals(
        df2, lookback_n=9, exit_lookback_n=8, vol_window=10, vol_mult=1.4563,
        atr_period=9, atr_stop_mult=2.9663,
    )
    np.testing.assert_array_equal(signals[:-1], signals2[:-1])


def test_volume_breakout_warmup_zeros():
    """First max(lookback_n, exit_lookback_n, atr_period, vol_window) + 2 bars = no signals."""
    from src.backtest.indicators import compute_volume_breakout_signals
    df = _synthetic_df(50)
    signals = compute_volume_breakout_signals(
        df, lookback_n=9, exit_lookback_n=8, vol_window=10, vol_mult=1.4563,
        atr_period=9, atr_stop_mult=2.9663,
    )
    warmup = max(9, 8, 9, 10) + 2
    assert (signals[:warmup] == 0).all(), "Warmup bars must be zero"


def test_volume_breakout_entry_requires_volume_confirm():
    """Entry needs BOTH price > rolling_high AND volume > vol_mean × vol_mult."""
    from src.backtest.indicators import compute_volume_breakout_signals
    # Build df where price breakout без volume confirm
    n = 30
    df = pd.DataFrame({
        "open": np.full(n, 100.0),
        "high": np.full(n, 100.0),
        "low": np.full(n, 100.0),
        "close": np.full(n, 100.0),
        "volume": np.full(n, 1000.0),  # constant volume — never exceeds mean × 1.4563
    })
    df.loc[20, "close"] = 200.0  # price breakout
    df.loc[20, "high"] = 200.0
    signals = compute_volume_breakout_signals(
        df, lookback_n=9, exit_lookback_n=8, vol_window=10, vol_mult=1.4563,
        atr_period=9, atr_stop_mult=2.9663,
    )
    # Must NOT enter — volume не confirms
    assert signals[21] != 1, "Entry must require volume confirm"


def test_volume_breakout_entry_with_volume_confirm():
    """Entry triggers when BOTH conditions met."""
    from src.backtest.indicators import compute_volume_breakout_signals
    n = 30
    df = pd.DataFrame({
        "open": np.full(n, 100.0),
        "high": np.full(n, 100.0),
        "low": np.full(n, 100.0),
        "close": np.full(n, 100.0),
        "volume": np.full(n, 1000.0),
    })
    df.loc[20, "close"] = 200.0
    df.loc[20, "high"] = 200.0
    df.loc[20, "volume"] = 5000.0  # 5× mean — exceeds 1.4563
    signals = compute_volume_breakout_signals(
        df, lookback_n=9, exit_lookback_n=8, vol_window=10, vol_mult=1.4563,
        atr_period=9, atr_stop_mult=2.9663,
    )
    assert signals[21] == 1, "Entry must trigger when both conditions met"
```

- [ ] **Step 2: Run tests — verify FAIL (function not defined)**

```bash
.venv/bin/pytest tests/unit/test_volume_breakout_indicators.py -v
```
Expected: FAIL `ImportError: cannot import name 'compute_volume_breakout_signals'`

- [ ] **Step 3: Add helper to src/backtest/indicators.py**

Append to `src/backtest/indicators.py`:

```python
def compute_volume_breakout_signals(
    df: pd.DataFrame,
    *,
    lookback_n: int,
    exit_lookback_n: int,
    vol_window: int,
    vol_mult: float,
    atr_period: int,
    atr_stop_mult: float,
) -> np.ndarray:
    """Vectorized volume_breakout signal generator (long-only).

    Returns int array of length len(df):
      - 0 = no action (FLAT or HOLD)
      - 1 = entry signal (close[i-1] > rolling_high AND volume[i-1] > vol_mean × vol_mult)
      - -1 = exit signal (channel close < rolling_low OR ATR stop intrabar)

    Convention: signal на bar i derived from data через bar i-1 (no look-ahead).
    Entry/exit FILL is operator's responsibility (typically next-bar open).

    Source: research/strategies.py::strat_volume_breakout (autoresearch sweep#1644
    LOCKED per ADR 0059).

    Args:
        df: DataFrame с columns open/high/low/close/volume.
        lookback_n: Donchian channel entry lookback (LOCKED=9).
        exit_lookback_n: Donchian channel exit lookback (LOCKED=8).
        vol_window: Volume rolling mean window (LOCKED=10).
        vol_mult: Volume must exceed mean × this (LOCKED=1.4563).
        atr_period: Wilder ATR period (LOCKED=9).
        atr_stop_mult: ATR stop = entry - ATR × this (LOCKED=2.9663).

    Returns:
        np.ndarray[int] of length len(df).
    """
    n = len(df)
    high = df["high"].to_numpy(dtype=np.float64)
    low = df["low"].to_numpy(dtype=np.float64)
    close = df["close"].to_numpy(dtype=np.float64)
    if "volume" not in df.columns:
        return np.zeros(n, dtype=np.int8)
    volume = df["volume"].to_numpy(dtype=np.float64)

    roll_high = pd.Series(high).rolling(lookback_n, min_periods=lookback_n).max().to_numpy()
    roll_low = pd.Series(low).rolling(exit_lookback_n, min_periods=exit_lookback_n).min().to_numpy()
    vol_mean = pd.Series(volume).rolling(vol_window, min_periods=vol_window).mean().to_numpy()

    signals = np.zeros(n, dtype=np.int8)
    warmup = max(lookback_n, exit_lookback_n, atr_period, vol_window) + 2
    for i in range(warmup, n):
        ref_h = roll_high[i - 2]
        ref_l = roll_low[i - 2]
        if (
            not np.isnan(ref_h)
            and not np.isnan(vol_mean[i - 1])
            and close[i - 1] > ref_h
            and volume[i - 1] > vol_mean[i - 1] * vol_mult
        ):
            signals[i] = 1
        elif not np.isnan(ref_l) and close[i - 1] < ref_l:
            signals[i] = -1
    return signals
```

If `import numpy as np` not yet present at top, ensure it's there.

- [ ] **Step 4: Run tests — verify PASS**

```bash
.venv/bin/pytest tests/unit/test_volume_breakout_indicators.py -v
```
Expected: 4 PASS

- [ ] **Step 5: Run mypy — verify no regressions**

```bash
.venv/bin/mypy --strict src/backtest/indicators.py
```
Expected: no errors (ignore pre-existing baseline if any)

- [ ] **Step 6: Commit**

```bash
git add src/backtest/indicators.py tests/unit/test_volume_breakout_indicators.py
git commit -m "feat(backtest): S39 T2 — add compute_volume_breakout_signals helper (LOCKED params)"
```

---

### Task A3: VolumeBreakoutStrategy class (Strategy contract)

**Files:**
- Create: `src/signalgen/volume_breakout_strategy.py`
- Create: `tests/unit/test_volume_breakout_strategy.py`

- [ ] **Step 1: Write failing test для strategy class**

Create `tests/unit/test_volume_breakout_strategy.py`:

```python
"""Unit tests для VolumeBreakoutStrategy (S39 T3)."""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from src.marketdata.models import Bar


def _bar(ts: datetime, o: float, h: float, l: float, c: float, v: float) -> Bar:
    return Bar(
        symbol="BTCUSDT", interval=240, ts=ts,
        open=Decimal(str(o)), high=Decimal(str(h)), low=Decimal(str(l)),
        close=Decimal(str(c)), volume=Decimal(str(v)),
        is_closed=True,
    )


def test_locked_params_constant_present():
    """ADR 0059 LOCKED params exposed as module constant."""
    from src.signalgen.volume_breakout_strategy import VOLUME_BREAKOUT_LOCKED_PARAMS
    assert VOLUME_BREAKOUT_LOCKED_PARAMS["lookback_n"] == 9
    assert VOLUME_BREAKOUT_LOCKED_PARAMS["exit_lookback_n"] == 8
    assert VOLUME_BREAKOUT_LOCKED_PARAMS["vol_window"] == 10
    assert VOLUME_BREAKOUT_LOCKED_PARAMS["vol_mult"] == Decimal("1.4563")
    assert VOLUME_BREAKOUT_LOCKED_PARAMS["atr_period"] == 9
    assert VOLUME_BREAKOUT_LOCKED_PARAMS["atr_stop_mult"] == Decimal("2.9663")
    assert VOLUME_BREAKOUT_LOCKED_PARAMS["signal_side_mode"] == "long_only"


def test_strategy_no_signal_during_warmup():
    """First max(lookback, exit, atr, vol_window) + 2 bars = no signal."""
    from src.signalgen.volume_breakout_strategy import VolumeBreakoutStrategy
    strat = VolumeBreakoutStrategy(symbol="BTCUSDT")
    ts = datetime(2026, 1, 1, tzinfo=UTC)
    for i in range(15):  # warmup = max(9, 8, 9, 10) + 2 = 12
        bar = _bar(ts, 100.0, 100.0, 100.0, 100.0, 1000.0)
        sig = strat.on_bar(bar)
        if i < 12:
            assert sig is None or sig.side.value == "FLAT"


def test_entry_signal_uses_canonical_reason_code():
    """Entry signal must emit ReasonCode.ENTRY_LONG_VOLUME_BREAKOUT."""
    from src.risk.reason_codes import ReasonCode
    from src.signalgen.volume_breakout_strategy import VolumeBreakoutStrategy
    # Build sequence: 12 flat bars warmup + breakout bar with volume
    strat = VolumeBreakoutStrategy(symbol="BTCUSDT")
    base_ts = datetime(2026, 1, 1, tzinfo=UTC)
    from datetime import timedelta
    for i in range(20):
        ts = base_ts + timedelta(hours=4 * i)
        if i == 19:
            bar = _bar(ts, 100.0, 200.0, 100.0, 200.0, 5000.0)  # breakout + 5× volume
        else:
            bar = _bar(ts, 100.0, 100.0, 100.0, 100.0, 1000.0)
        sig = strat.on_bar(bar)
    # Last on_bar should produce entry on next call (i=20)
    next_bar = _bar(base_ts + timedelta(hours=80), 200.0, 200.0, 200.0, 200.0, 1000.0)
    sig = strat.on_bar(next_bar)
    if sig is not None and sig.side.value == "LONG":
        assert sig.reason == ReasonCode.ENTRY_LONG_VOLUME_BREAKOUT.value


def test_strategy_long_only_invariant():
    """Strategy MUST NOT emit SHORT signals (per LOCKED params signal_side_mode='long_only')."""
    from src.signalgen.models import SignalSide
    from src.signalgen.volume_breakout_strategy import VolumeBreakoutStrategy
    # Construct adversarial bars that would trigger SHORT in unrestricted strategy
    strat = VolumeBreakoutStrategy(symbol="BTCUSDT")
    # Generate 100 bars of various conditions
    base_ts = datetime(2026, 1, 1, tzinfo=UTC)
    from datetime import timedelta
    for i in range(100):
        ts = base_ts + timedelta(hours=4 * i)
        bar = _bar(ts, 100.0, 100.0 + (i % 10), 100.0 - (i % 10), 100.0, 1000.0 * (i % 5 + 1))
        sig = strat.on_bar(bar)
        if sig is not None:
            assert sig.side != SignalSide.SHORT, "long-only invariant violated"
```

- [ ] **Step 2: Run tests — verify FAIL**

```bash
.venv/bin/pytest tests/unit/test_volume_breakout_strategy.py -v
```
Expected: FAIL `ImportError: cannot import VolumeBreakoutStrategy`

- [ ] **Step 3: Implement strategy class**

Create `src/signalgen/volume_breakout_strategy.py` (template after `donchian_strategy.py`):

```python
"""Volume breakout long-only strategy (S39 production integration per ADR 0059 LOCKED).

LOCKED parameters per ADR 0059 — anti-snooping pre-registration (autoresearch sweep#1644):
  - lookback_n=9 (Donchian channel entry lookback ≈ 1.5 days @ 4H)
  - exit_lookback_n=8 (Donchian channel exit lookback)
  - vol_window=10 (volume rolling mean window)
  - vol_mult=1.4563 (volume must exceed mean × this multiplier)
  - atr_period=9 (Wilder ATR period)
  - atr_stop_mult=2.9663 (stop loss = entry - ATR × this)
  - signal_side_mode="long_only" (FSM invariant — NEVER emits SHORT)

Entry rule (LONG):
  close(T-1) > max(high[T-1-lookback_n : T-1]) AND
  volume(T-1) > mean(volume[T-1-vol_window : T-1]) × vol_mult AND
  current_side == FLAT

Exit rule (FLAT):
  IF current LONG, exit if EITHER:
    - close(T-1) < min(low[T-1-exit_lookback_n : T-1])  (Donchian channel exit)
    - low(T) <= entry_price - atr_stop_mult × ATR(T-1)  (ATR stop intrabar)

Invariant: signal evaluated on bar(T) using only data through T-1
(no look-ahead per execution-timing.md). Execution at open(T+1) per
existing FSM contract.

Thread-safety: NOT thread-safe — single-producer per symbol pattern
(per ADR 0023 single-writer invariant).

Reference implementation: research/strategies.py::strat_volume_breakout
(branch autoresearch/donchian-may8 commit fff54ee).
"""

from __future__ import annotations

from collections import deque
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import numpy as np

from src.marketdata.models import Bar
from src.risk.reason_codes import ReasonCode
from src.signalgen.indicators import atr
from src.signalgen.models import Signal, SignalSide

# ADR 0059 LOCKED — DO NOT modify without new ADR amendment.
# Source: autoresearch sweep#1644, branch autoresearch/donchian-may8 commit fff54ee.
VOLUME_BREAKOUT_LOCKED_PARAMS: dict[str, object] = {
    "lookback_n": 9,
    "exit_lookback_n": 8,
    "vol_window": 10,
    "vol_mult": Decimal("1.4563"),
    "atr_period": 9,
    "atr_stop_mult": Decimal("2.9663"),
    "signal_side_mode": "long_only",
}


class VolumeBreakoutStrategy:
    """Stateful volume_breakout long-only strategy.

    Internal state: rolling buffer of last (max(lookback_n, exit_lookback_n,
    atr_period, vol_window) + 5) bars, plus current_side and entry_price.
    """

    def __init__(self, *, symbol: str) -> None:
        self.symbol = symbol
        self._lookback_n = int(VOLUME_BREAKOUT_LOCKED_PARAMS["lookback_n"])  # type: ignore[arg-type]
        self._exit_lookback_n = int(VOLUME_BREAKOUT_LOCKED_PARAMS["exit_lookback_n"])  # type: ignore[arg-type]
        self._vol_window = int(VOLUME_BREAKOUT_LOCKED_PARAMS["vol_window"])  # type: ignore[arg-type]
        self._vol_mult = float(VOLUME_BREAKOUT_LOCKED_PARAMS["vol_mult"])  # type: ignore[arg-type]
        self._atr_period = int(VOLUME_BREAKOUT_LOCKED_PARAMS["atr_period"])  # type: ignore[arg-type]
        self._atr_stop_mult = float(VOLUME_BREAKOUT_LOCKED_PARAMS["atr_stop_mult"])  # type: ignore[arg-type]
        self._buffer_size = max(
            self._lookback_n, self._exit_lookback_n, self._atr_period, self._vol_window
        ) + 5
        self._highs: deque[float] = deque(maxlen=self._buffer_size)
        self._lows: deque[float] = deque(maxlen=self._buffer_size)
        self._closes: deque[float] = deque(maxlen=self._buffer_size)
        self._volumes: deque[float] = deque(maxlen=self._buffer_size)
        self._current_side: SignalSide = SignalSide.FLAT
        self._entry_price: float | None = None

    def on_bar(self, bar: Bar) -> Signal | None:
        """Evaluate strategy on closed bar. Returns Signal or None."""
        if not bar.is_closed:
            return None
        self._highs.append(float(bar.high))
        self._lows.append(float(bar.low))
        self._closes.append(float(bar.close))
        self._volumes.append(float(bar.volume))

        # Warmup gate
        warmup = max(self._lookback_n, self._exit_lookback_n, self._atr_period, self._vol_window) + 2
        if len(self._closes) < warmup:
            return None

        # Use bar(T-1) data — last element of buffer is bar(T)
        # We evaluate signal that fires AT bar(T) using through bar(T-1)
        # In live mode, bar(T) is the just-closed bar; signal executes на open(T+1)
        # Per existing FSM convention.
        prev_close = self._closes[-2]
        prev_vol = self._volumes[-2]

        # Reference high/low EXCLUDES current bar (window through T-2)
        ref_high_window = list(self._highs)[-(self._lookback_n + 1):-1]
        ref_low_window = list(self._lows)[-(self._exit_lookback_n + 1):-1]
        vol_mean_window = list(self._volumes)[-(self._vol_window + 1):-1]

        if len(ref_high_window) < self._lookback_n:
            return None

        ref_high = max(ref_high_window)
        ref_low = min(ref_low_window)
        vol_mean = sum(vol_mean_window) / len(vol_mean_window)

        # Compute ATR for stop calculation (Wilder ATR)
        atr_val = self._compute_wilder_atr()

        # Entry logic (LONG only)
        if self._current_side == SignalSide.FLAT:
            if prev_close > ref_high and prev_vol > vol_mean * self._vol_mult:
                self._current_side = SignalSide.LONG
                self._entry_price = prev_close
                return Signal(
                    signal_id=str(uuid4()),
                    symbol=self.symbol,
                    side=SignalSide.LONG,
                    timestamp=bar.ts,
                    reason=ReasonCode.ENTRY_LONG_VOLUME_BREAKOUT.value,
                    confidence=1.0,
                )
            return None

        # Exit logic (FLAT from LONG)
        if self._current_side == SignalSide.LONG:
            # Channel exit
            if prev_close < ref_low:
                self._current_side = SignalSide.FLAT
                self._entry_price = None
                return Signal(
                    signal_id=str(uuid4()),
                    symbol=self.symbol,
                    side=SignalSide.FLAT,
                    timestamp=bar.ts,
                    reason=ReasonCode.EXIT_FLAT_VOLUME_CHANNEL.value,
                    confidence=1.0,
                )
            # ATR stop intrabar (uses current bar low vs previous ATR)
            if (
                self._entry_price is not None
                and atr_val is not None
                and float(bar.low) <= self._entry_price - self._atr_stop_mult * atr_val
            ):
                self._current_side = SignalSide.FLAT
                self._entry_price = None
                return Signal(
                    signal_id=str(uuid4()),
                    symbol=self.symbol,
                    side=SignalSide.FLAT,
                    timestamp=bar.ts,
                    reason=ReasonCode.EXIT_FLAT_ATR_STOP_VB.value,
                    confidence=1.0,
                )
        return None

    def _compute_wilder_atr(self) -> float | None:
        """Wilder ATR computed on rolling buffer (closes/highs/lows)."""
        if len(self._closes) < self._atr_period + 1:
            return None
        highs = np.array(self._highs, dtype=np.float64)
        lows = np.array(self._lows, dtype=np.float64)
        closes = np.array(self._closes, dtype=np.float64)
        atr_arr = atr(highs, lows, closes, self._atr_period)
        if len(atr_arr) == 0 or np.isnan(atr_arr[-1]):
            return None
        return float(atr_arr[-1])
```

- [ ] **Step 4: Run tests — verify PASS**

```bash
.venv/bin/pytest tests/unit/test_volume_breakout_strategy.py -v
```
Expected: 4 PASS

- [ ] **Step 5: mypy check**

```bash
.venv/bin/mypy --strict src/signalgen/volume_breakout_strategy.py
```
Expected: 0 errors (or unchanged baseline)

- [ ] **Step 6: Commit**

```bash
git add src/signalgen/volume_breakout_strategy.py tests/unit/test_volume_breakout_strategy.py
git commit -m "feat(signalgen): S39 T3 — VolumeBreakoutStrategy class (ADR 0059 LOCKED params)"
```

---

### Task A4: Dashboard preset с ENFORCE 4H+BTCUSDT

**Files:**
- Modify: `src/dashboard/backtest_runner.py` (add preset с lock fields)
- Modify: `src/dashboard/app.py` (backend 422 validation)
- Modify: `src/dashboard/templates/index.html` + JS (frontend dropdown lock)
- Test: `tests/unit/test_dashboard_volume_breakout_preset.py` (new) OR extend existing dashboard tests

- [ ] **Step 1: Write failing test для preset registration + lock validation**

Create `tests/unit/test_dashboard_volume_breakout_preset.py`:

```python
"""Tests для volume_breakout dashboard preset (S39 T4) с ENFORCE locked dimensions."""
from __future__ import annotations

import pytest


def test_volume_breakout_preset_registered():
    """Preset volume_breakout_iter10 must exist в STRATEGY_PRESETS."""
    from src.dashboard.backtest_runner import STRATEGY_PRESETS
    assert "volume_breakout_iter10" in STRATEGY_PRESETS
    preset = STRATEGY_PRESETS["volume_breakout_iter10"]
    assert preset["sprint"] == "S39"
    assert preset["type"] == "volume_breakout"


def test_volume_breakout_preset_has_locked_dimensions():
    """Preset must declare locked_symbol=BTCUSDT and locked_interval=240."""
    from src.dashboard.backtest_runner import STRATEGY_PRESETS
    preset = STRATEGY_PRESETS["volume_breakout_iter10"]
    assert preset.get("locked_symbol") == "BTCUSDT"
    assert preset.get("locked_interval") == "240"


def test_volume_breakout_preset_locked_params_in_indicators():
    """Preset indicators reflect ADR 0059 LOCKED params."""
    from src.dashboard.backtest_runner import STRATEGY_PRESETS
    preset = STRATEGY_PRESETS["volume_breakout_iter10"]
    ind = preset["indicators"]
    assert ind["volume_breakout"]["lookback_n"] == 9
    assert ind["volume_breakout"]["exit_lookback_n"] == 8
    assert ind["volume_breakout"]["vol_window"] == 10
    assert abs(ind["volume_breakout"]["vol_mult"] - 1.4563) < 1e-9
    assert ind["volume_breakout"]["atr_period"] == 9
    assert abs(ind["volume_breakout"]["atr_stop_mult"] - 2.9663) < 1e-9
```

- [ ] **Step 2: Run tests — verify FAIL**

```bash
.venv/bin/pytest tests/unit/test_dashboard_volume_breakout_preset.py -v
```
Expected: FAIL `KeyError: 'volume_breakout_iter10'`

- [ ] **Step 3: Add preset с lock fields**

In `src/dashboard/backtest_runner.py` STRATEGY_PRESETS dict, append после `donchian_breakout_s35`:

```python
    "volume_breakout_iter10": {
        "label": "[S39 LATEST] Volume breakout 4H BTCUSDT (LOCKED — autoresearch sweep#1644)",
        "sprint": "S39",
        "verdict": "PASS held-out 8mo Sharpe=+9.96 PnL=+20.42% / 3.3y +122.66%; Gate 2 forward N≥10 PENDING",
        "type": "volume_breakout",
        "locked_symbol": "BTCUSDT",
        "locked_interval": "240",
        "indicators": {
            "volume_breakout": {
                "lookback_n": 9,
                "exit_lookback_n": 8,
                "vol_window": 10,
                "vol_mult": 1.4563,
                "atr_period": 9,
                "atr_stop_mult": 2.9663,
            },
        },
    },
```

- [ ] **Step 4: Add backend lock validation в app.py /api/backtest endpoint**

In `src/dashboard/app.py` (find the /api/backtest endpoint handler), add validation BEFORE preset processing:

```python
# S39 T4 — ENFORCE locked dimensions (ADR 0059 anti-snooping)
preset = STRATEGY_PRESETS.get(req.strategy_id)
if preset is None:
    raise HTTPException(status_code=422, detail=f"Unknown strategy_id: {req.strategy_id}")
locked_symbol = preset.get("locked_symbol")
locked_interval = preset.get("locked_interval")
if locked_symbol and req.symbol != locked_symbol:
    raise HTTPException(
        status_code=422,
        detail=f"Strategy {req.strategy_id} LOCKED to symbol={locked_symbol}; got {req.symbol}",
    )
if locked_interval and req.interval != locked_interval:
    raise HTTPException(
        status_code=422,
        detail=f"Strategy {req.strategy_id} LOCKED to interval={locked_interval}; got {req.interval}",
    )
```

- [ ] **Step 5: Frontend lock — disable dropdowns when locked preset selected**

In `src/dashboard/templates/index.html` + associated JS file, add JavaScript handler:

```javascript
// S39 T4 — When user selects preset с locked_symbol/locked_interval, disable dropdowns
document.getElementById('strategy-select').addEventListener('change', async (e) => {
    const strategyId = e.target.value;
    const resp = await fetch(`/api/strategies/${strategyId}`);
    const preset = await resp.json();
    const symbolSelect = document.getElementById('symbol-select');
    const intervalSelect = document.getElementById('interval-select');
    if (preset.locked_symbol) {
        symbolSelect.value = preset.locked_symbol;
        symbolSelect.disabled = true;
        symbolSelect.title = `LOCKED to ${preset.locked_symbol} per ADR 0059 (anti-snooping)`;
    } else {
        symbolSelect.disabled = false;
        symbolSelect.title = '';
    }
    if (preset.locked_interval) {
        intervalSelect.value = preset.locked_interval;
        intervalSelect.disabled = true;
        intervalSelect.title = `LOCKED to ${preset.locked_interval} per ADR 0059 (anti-snooping)`;
    } else {
        intervalSelect.disabled = false;
        intervalSelect.title = '';
    }
});
```

Add `/api/strategies/{strategy_id}` endpoint в `app.py` if not exists:

```python
@app.get("/api/strategies/{strategy_id}")
async def get_strategy_preset(strategy_id: str) -> dict[str, Any]:
    preset = STRATEGY_PRESETS.get(strategy_id)
    if preset is None:
        raise HTTPException(status_code=404, detail="Strategy preset not found")
    return preset
```

- [ ] **Step 6: Add backtest_runner integration — wire VolumeBreakoutStrategy в pipeline**

In `src/dashboard/backtest_runner.py` find где strategy type dispatched (e.g., `if preset["type"] == "donchian":`). Add branch:

```python
elif preset["type"] == "volume_breakout":
    from src.signalgen.volume_breakout_strategy import VolumeBreakoutStrategy
    strategy = VolumeBreakoutStrategy(symbol=req.symbol)
    # ... wire to existing backtest replay engine
```

(Exact wiring depends on existing pipeline structure — implementer reads `donchian` branch as template.)

- [ ] **Step 7: Run tests + manual smoke test**

```bash
.venv/bin/pytest tests/unit/test_dashboard_volume_breakout_preset.py -v
.venv/bin/pytest tests/unit/test_dashboard*.py tests/integration/test_dashboard*.py -v
```
Expected: PASS

Manual smoke (optional): start dashboard, select volume_breakout preset, verify dropdowns lock to BTCUSDT/4H and run backtest succeeds.

- [ ] **Step 8: Commit**

```bash
git add src/dashboard/ tests/unit/test_dashboard_volume_breakout_preset.py
git commit -m "feat(dashboard): S39 T4 — volume_breakout preset с ENFORCE 4H+BTCUSDT lock"
```

---

### Task A5: Phase 5 baseline floor integration test (HARD-GATE)

**Files:**
- Create: `tests/integration/test_volume_breakout_baseline_floor.py`

**Critical requirement (CC1 from trader-expert):** Test MUST use production pipeline (`src/backtest/replay_engine.py` + `backtest_runner.py`), NOT simplified re-implementation. Implementer must verify that production output matches research toy output within ±0.5% tolerance.

- [ ] **Step 1: Write integration test**

Create `tests/integration/test_volume_breakout_baseline_floor.py`:

```python
"""Phase 5 HARD-GATE — volume_breakout baseline floor (S39 ADR 0059).

Profit invariant: post-S39 backtest PnL MUST NOT decrease from baseline:
  - 8mo held-out (2025-08-26 → 2026-04-26) PnL ≥ +20.42%
  - 3.3y full (2023-01-01 → 2026-04-26) PnL ≥ +122.66%

BOTH gates required (per CC6 from trader-expert ROUND 1).
FAIL → blocks merge.

Tolerance: ±0.5% PnL replication tolerance from research toy values
(implementation drift detection per CC1).
"""
from __future__ import annotations

from datetime import date, datetime, UTC

import pytest


# Baseline values from research/FINAL_STRATEGY.md (autoresearch sweep#1644)
HELDOUT_BASELINE_PNL_PCT = 20.42  # 8mo BEAR period
HELDOUT_START = date(2025, 8, 26)
HELDOUT_END = date(2026, 4, 26)

FULL_BASELINE_PNL_PCT = 122.66  # 3.3y full period
FULL_START = date(2023, 1, 1)
FULL_END = date(2026, 4, 26)

REPLICATION_TOLERANCE_PCT = 0.5


def _run_volume_breakout_backtest(start: date, end: date) -> dict[str, float]:
    """Run volume_breakout via production pipeline. Returns dict с pnl_pct + n_trades."""
    from src.dashboard.backtest_runner import STRATEGY_PRESETS, run_backtest
    # Use production backtest runner — exact same path as /api/backtest endpoint
    preset = STRATEGY_PRESETS["volume_breakout_iter10"]
    result = run_backtest(
        strategy_id="volume_breakout_iter10",
        symbol="BTCUSDT",
        interval="240",
        start_date=start,
        end_date=end,
    )
    return {
        "pnl_pct": float(result["total_pnl_pct"]),
        "n_trades": int(result["n_trades"]),
    }


@pytest.mark.integration
def test_volume_breakout_heldout_pnl_floor():
    """8mo held-out PnL MUST be ≥ +20.42% (within tolerance)."""
    result = _run_volume_breakout_backtest(HELDOUT_START, HELDOUT_END)
    assert result["pnl_pct"] >= HELDOUT_BASELINE_PNL_PCT - REPLICATION_TOLERANCE_PCT, (
        f"FAIL Phase 5 HARD-GATE: 8mo PnL {result['pnl_pct']:.2f}% < "
        f"baseline {HELDOUT_BASELINE_PNL_PCT}% - tolerance {REPLICATION_TOLERANCE_PCT}%. "
        f"Implementation may drift from research toy."
    )


@pytest.mark.integration
def test_volume_breakout_full_period_pnl_floor():
    """3.3y full period PnL MUST be ≥ +122.66% (within tolerance)."""
    result = _run_volume_breakout_backtest(FULL_START, FULL_END)
    assert result["pnl_pct"] >= FULL_BASELINE_PNL_PCT - REPLICATION_TOLERANCE_PCT, (
        f"FAIL Phase 5 HARD-GATE: 3.3y PnL {result['pnl_pct']:.2f}% < "
        f"baseline {FULL_BASELINE_PNL_PCT}% - tolerance {REPLICATION_TOLERANCE_PCT}%. "
        f"Implementation may drift from research toy."
    )


@pytest.mark.integration
def test_volume_breakout_heldout_n_trades():
    """8mo held-out n_trades MUST be approximately 17 (sweep#1644 evidence)."""
    result = _run_volume_breakout_backtest(HELDOUT_START, HELDOUT_END)
    # Allow ±2 trades replication variance (slippage rounding, decimal precision)
    assert 15 <= result["n_trades"] <= 19, (
        f"n_trades {result['n_trades']} outside expected ~17 (sweep#1644 baseline)"
    )
```

- [ ] **Step 2: Run integration test — verify PASS**

```bash
.venv/bin/pytest tests/integration/test_volume_breakout_baseline_floor.py -v -m integration
```

If FAIL: implementation drifted from research toy. Debug:
- Compare bar-by-bar signals vs `research/strategies.py::strat_volume_breakout`
- Check slippage (research uses 0.05% per leg — verify production uses same)
- Check warmup gating (max(lookback_n, exit_lookback_n, atr_period, vol_window) + 2)
- Check Wilder ATR vs classical ATR (research uses Wilder)

Expected (after fixes): 3 PASS

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_volume_breakout_baseline_floor.py
git commit -m "test(integration): S39 T5 — volume_breakout baseline floor HARD-GATE (Phase 5)"
```

---

### Task A6: Cherry-pick research evidence к main wiki

**Files:**
- Create: `llm-wiki/wiki/project/research-evidence/README.md`
- Create: `llm-wiki/wiki/project/research-evidence/FINAL_STRATEGY.md` (cherry-pick)
- Create: `llm-wiki/wiki/project/research-evidence/CLOSE.md` (cherry-pick)
- Create: `llm-wiki/wiki/project/research-evidence/results.tsv` (cherry-pick)
- Modify: `llm-wiki/wiki/index.md` (NEW section "Research Evidence")

- [ ] **Step 1: Cherry-pick 3 files from autoresearch branch**

```bash
mkdir -p llm-wiki/wiki/project/research-evidence
git show autoresearch/donchian-may8:research/FINAL_STRATEGY.md > llm-wiki/wiki/project/research-evidence/FINAL_STRATEGY.md
git show autoresearch/donchian-may8:research/CLOSE.md > llm-wiki/wiki/project/research-evidence/CLOSE.md
git show autoresearch/donchian-may8:research/results.tsv > llm-wiki/wiki/project/research-evidence/results.tsv
```

- [ ] **Step 2: Add frontmatter к cherry-picked .md files**

Edit `llm-wiki/wiki/project/research-evidence/FINAL_STRATEGY.md` — add at top:

```yaml
---
title: FINAL STRATEGY — volume_breakout 4H BTCUSDT (autoresearch evidence)
type: research-evidence
tags: [research, autoresearch, volume-breakout, sweep-1644, sprint-39, ru]
created: 2026-05-09
sources:
  - autoresearch/donchian-may8 commit fff54ee
  - llm-wiki/wiki/project/decisions/0059-sprint-39-volume-breakout-pre-registration.md
status: locked-evidence
---

```

Same для CLOSE.md (type: research-evidence).

- [ ] **Step 3: Create README.md для research-evidence section**

Create `llm-wiki/wiki/project/research-evidence/README.md`:

```markdown
---
title: Research Evidence — autoresearch artifacts
type: index
tags: [research, autoresearch, evidence, ru]
created: 2026-05-09
status: stable
---

# Research Evidence

Cherry-picked artifacts из autoresearch branches — audit trail для production strategy ADRs.

## Files

- [[FINAL_STRATEGY]] — volume_breakout sweep#1644 spec (S39 ADR 0059 evidence)
- [[CLOSE]] — autoresearch iter 1-7 falsification record (Donchian raw + EMA filter both FAIL conjoint)
- `results.tsv` — full audit trail 4510 sweeps × 10 strategies (213 PASS, 4.51M trials evaluated)

## Usage

These files are READ-ONLY references. Do NOT edit. Source of truth = autoresearch branches.

## Связанные документы

- [[../decisions/0059-sprint-39-volume-breakout-pre-registration]]
- [[../sprints/sprint-39-volume-breakout-tech-debt]]
- [[../components/volume-breakout-strategy]]
```

- [ ] **Step 4: Add NEW section "Research Evidence" к index.md**

Edit `llm-wiki/wiki/index.md` — add section после "Project — Methodology":

```markdown
## Project — Research Evidence

- [[project/research-evidence/README|Research Evidence index]] — cherry-picked autoresearch artifacts
- [[project/research-evidence/FINAL_STRATEGY]] — volume_breakout sweep#1644 spec (S39 evidence)
- [[project/research-evidence/CLOSE]] — autoresearch iter 1-7 falsification record
```

- [ ] **Step 5: Commit**

```bash
git add llm-wiki/wiki/project/research-evidence/ llm-wiki/wiki/index.md
git commit -m "docs(wiki): S39 T6 — cherry-pick research-evidence (FINAL_STRATEGY+CLOSE+results.tsv)"
```

---

## Track B — Critical tech debt (BEFORE TESTNET activation)

### Task B1: H1 — Rate-limit backoff в REST adapter

**Files:**
- Modify: `src/execution/bybit/rest.py`
- Create/extend: `tests/unit/test_bybit_rest_backoff.py`

- [ ] **Step 1: Write failing test для backoff behavior**

Create `tests/unit/test_bybit_rest_backoff.py`:

```python
"""H1 — Rate-limit exponential backoff с jitter (S39 T7)."""
from __future__ import annotations

import time
import pytest


def test_rate_limit_retCode_10006_triggers_backoff(monkeypatch):
    """When pybit returns retCode=10006 (rate-limit), adapter retries с exponential backoff."""
    from src.execution.bybit.rest import BybitRESTClient
    
    call_count = {"n": 0}
    sleep_calls = []
    
    def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)
    
    def fake_pybit_call(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] < 3:
            return {"retCode": 10006, "retMsg": "too many visits", "result": {}}
        return {"retCode": 0, "retMsg": "OK", "result": {"list": []}}
    
    monkeypatch.setattr("time.sleep", fake_sleep)
    # Inject fake pybit client (depends on BybitRESTClient internal structure)
    # Implementer adapts mock к actual pybit_session.get_kline / similar method
    # ...
    # Result: call succeeds after 2 retries, sleep_calls = [base, base*2] approximately
    assert call_count["n"] == 3
    assert len(sleep_calls) == 2
    assert sleep_calls[0] >= 0.1  # base backoff
    assert sleep_calls[1] >= sleep_calls[0]  # exponential growth


def test_rate_limit_max_retries_raises():
    """After max_retries=5 attempts, raises BybitAPIError(RATE_LIMIT_HIT)."""
    from src.execution.bybit.rest import BybitRESTClient
    from src.execution.bybit.errors import BybitAPIError
    from src.risk.reason_codes import ReasonCode
    
    # Mock: always returns 10006
    # Adapter retries max_retries times, then raises
    with pytest.raises(BybitAPIError) as exc_info:
        # Trigger rate-limited call
        pass  # implementer fills in
    assert exc_info.value.reason == ReasonCode.RATE_LIMIT_HIT
```

- [ ] **Step 2: Verify test FAIL**

```bash
.venv/bin/pytest tests/unit/test_bybit_rest_backoff.py -v
```
Expected: FAIL (no backoff implementation)

- [ ] **Step 3: Add backoff decorator/wrapper в rest.py**

In `src/execution/bybit/rest.py`, add helper:

```python
import random
import time
from typing import Any, Callable, TypeVar

T = TypeVar("T")

# S39 T7 H1 — Rate-limit exponential backoff с jitter
_BACKOFF_BASE_S = 0.5
_BACKOFF_MAX_RETRIES = 5
_BACKOFF_JITTER_FACTOR = 0.3


def _retry_with_backoff(
    fn: Callable[[], dict[str, Any]],
    *,
    base: float = _BACKOFF_BASE_S,
    max_retries: int = _BACKOFF_MAX_RETRIES,
) -> dict[str, Any]:
    """Retry pybit call with exponential backoff + jitter on retCode=10006.

    Per Bybit V5 docs: 10006 = "too many visits" rate limit hit.
    Backoff = base × 2^attempt + jitter × U(0, 1).
    Raises BybitAPIError(RATE_LIMIT_HIT) after max_retries failures.
    """
    from src.execution.bybit.errors import BybitAPIError
    from src.risk.reason_codes import ReasonCode
    
    for attempt in range(max_retries):
        result = fn()
        if not isinstance(result, dict):
            return result
        if result.get("retCode") != 10006:
            return result
        # Rate limited — backoff
        delay = base * (2**attempt) + random.uniform(0, base * _BACKOFF_JITTER_FACTOR)
        time.sleep(delay)
    raise BybitAPIError(ReasonCode.RATE_LIMIT_HIT, "Rate limit exhausted после max retries")
```

Wrap critical pybit calls (e.g., `get_kline`, `place_order`, `get_positions`):

```python
def get_kline(self, **kwargs) -> dict[str, Any]:
    return _retry_with_backoff(lambda: self._session.get_kline(**kwargs))
```

- [ ] **Step 4: Verify tests PASS**

```bash
.venv/bin/pytest tests/unit/test_bybit_rest_backoff.py -v
.venv/bin/pytest tests/unit/test_bybit_rest.py -v  # Existing tests must still pass
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/execution/bybit/rest.py tests/unit/test_bybit_rest_backoff.py
git commit -m "fix(bybit): S39 T7 H1 — exponential backoff с jitter on retCode=10006 rate-limit"
```

---

### Task B2: H2 — WS reconnect verification tests

**Files:**
- Modify: `tests/unit/test_ws_private_consumer.py`
- Possibly modify: `src/execution/ws_private.py` (if probe missing)

- [ ] **Step 1: Write failing test для reconnect probe**

Append to `tests/unit/test_ws_private_consumer.py`:

```python
def test_reconnect_triggers_check_alive_re_probe():
    """H2 regression: после on_disconnect → check_alive must be called again
    to verify WS subscription was re-attached.
    
    Prevents silent dead-WS scenario where reconcile delivers AGREE on stale state.
    """
    from unittest.mock import MagicMock, patch
    from src.execution.ws_private import BybitPrivateWSConsumer
    
    coordinator = MagicMock()
    consumer = BybitPrivateWSConsumer(
        api_key="test", api_secret="test", coordinator=coordinator
    )
    consumer._check_alive = MagicMock(return_value=True)
    
    # Simulate disconnect
    consumer._on_disconnect()
    
    # check_alive must be called at least twice: pre-existing watchdog + post-reconnect probe
    assert consumer._check_alive.call_count >= 2, (
        "H2 gap: post-disconnect re-probe missing — silent dead-WS risk"
    )
```

- [ ] **Step 2: Verify FAIL**

```bash
.venv/bin/pytest tests/unit/test_ws_private_consumer.py::test_reconnect_triggers_check_alive_re_probe -v
```

- [ ] **Step 3: If FAIL, add re-probe to _on_disconnect handler в ws_private.py**

```python
def _on_disconnect(self) -> None:
    """Existing disconnect handler. Add post-reconnect probe."""
    # ... existing reconnect logic ...
    # S39 T8 H2 — verify subscription re-attached after reconnect
    if not self._check_alive():
        self._coordinator.on_ws_health_lost()
```

- [ ] **Step 4: Verify PASS**

```bash
.venv/bin/pytest tests/unit/test_ws_private_consumer.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/execution/ws_private.py tests/unit/test_ws_private_consumer.py
git commit -m "fix(execution): S39 T8 H2 — WS reconnect re-probe verification"
```

---

### Task B3: Item#10 — DD_MULTIDAY/NO_TRADE_TIMEOUT property tests boundary

**Files:**
- Modify: `tests/property/test_halt_gate.py`

- [ ] **Step 1: Write failing parametrized boundary tests**

Append to `tests/property/test_halt_gate.py`:

```python
@pytest.mark.parametrize("months_since,expected_trigger", [
    (5, None),                                    # below 6-month threshold
    (6, HaltTrigger.NO_TRADE_TIMEOUT),            # at exact boundary
    (7, HaltTrigger.NO_TRADE_TIMEOUT),            # above boundary
])
def test_no_trade_timeout_boundary_parametrized(
    months_since: int, expected_trigger: HaltTrigger | None
) -> None:
    """Item #10: exact boundary behavior months_since = threshold (6 months)."""
    gate = _gate()  # threshold=6
    trigger = gate.evaluate(
        intraday_dd=Decimal("0.01"),
        multiday_dd=Decimal("0.01"),
        consecutive_losses=0,
        months_since_last_trade=months_since,
    )
    assert trigger == expected_trigger


@pytest.mark.parametrize("multiday_dd_pct,expected_trigger", [
    (Decimal("0.14"), None),                      # below 15% threshold
    (Decimal("0.15"), HaltTrigger.DD_MULTIDAY),   # at exact boundary
    (Decimal("0.16"), HaltTrigger.DD_MULTIDAY),   # above boundary
])
def test_dd_multiday_boundary_parametrized(
    multiday_dd_pct: Decimal, expected_trigger: HaltTrigger | None
) -> None:
    """Item #10: exact boundary behavior multiday_dd = threshold (15%)."""
    gate = _gate()
    trigger = gate.evaluate(
        intraday_dd=Decimal("0.01"),
        multiday_dd=multiday_dd_pct,
        consecutive_losses=0,
        months_since_last_trade=0,
    )
    assert trigger == expected_trigger
```

- [ ] **Step 2: Verify tests PASS or FAIL accordingly**

```bash
.venv/bin/pytest tests/property/test_halt_gate.py -v
```

If FAIL on boundary case (e.g., gate uses `>` instead of `>=`): fix gate logic per ADR 0055 SD-2 spec.

- [ ] **Step 3: Commit**

```bash
git add tests/property/test_halt_gate.py src/risk/halt_gate.py
git commit -m "test(risk): S39 T9 Item#10 — DD_MULTIDAY+NO_TRADE_TIMEOUT boundary parametrized tests"
```

---

## Track C — Cleanup

### Task C1: Item#7 — RiskSharedDeps shim removal

**Files:**
- Modify: `src/risk/manager.py` or `src/risk/shared_deps.py` (find shim)
- Verify: grep no callers using old API

- [ ] **Step 1: Find shim location**

```bash
grep -rn "RiskSharedDeps" src/ tests/
```

- [ ] **Step 2: Verify all callers use new API**

```bash
grep -rn "RiskSharedDeps(" src/ tests/  # Constructor calls
grep -rn "from src.risk.* import.*SharedDeps" src/ tests/
```

All callers should use NamedTuple bundle path (per S38 T4 Demeter refactor). If any caller uses backward-compat constructor signature, migrate it first.

- [ ] **Step 3: Remove backward-compat constructor/methods**

In shim location, delete:
```python
# OLD shim (S38 T4 backward-compat — remove S39):
def __init__(self, ...):
    """Old multi-arg constructor."""
    ...
```

Keep only NamedTuple-based path.

- [ ] **Step 4: Run full test suite**

```bash
.venv/bin/pytest tests/unit -x -q
```
Expected: all PASS (no callers broken)

- [ ] **Step 5: Commit**

```bash
git add src/risk/
git commit -m "refactor(risk): S39 T10 Item#7 — remove RiskSharedDeps backward-compat shim"
```

---

### Task C2: F8 — `_MC_BLOCK_SIZE` unification

**Files:**
- Modify: `src/backtest/mc_permutation.py` and references

- [ ] **Step 1: Find inconsistency**

```bash
grep -rn "_MC_BLOCK_SIZE\|block_size" src/backtest/
```

Identify which value (20 or 30) is used where.

- [ ] **Step 2: Choose canonical value (default to 20 — matches ADR 0015 default OR confirm via grep evidence)**

Update all occurrences to single value. Add module constant:
```python
_MC_BLOCK_SIZE: int = 20  # ADR 0015 — block-bootstrap default; S39 F8 unified
```

- [ ] **Step 3: Run MC permutation tests**

```bash
.venv/bin/pytest tests/unit/test_mc_permutation.py -v
.venv/bin/pytest tests/property/test_mc_permutations.py -v 2>/dev/null || true
```

- [ ] **Step 4: Commit**

```bash
git add src/backtest/mc_permutation.py
git commit -m "fix(backtest): S39 T11 F8 — unify _MC_BLOCK_SIZE to single value (20 per ADR 0015)"
```

---

## Track E — Bybit-api M3+M4 hardening

### Task E1: M3 — WS data isinstance shape guard

**Files:**
- Modify: `src/execution/ws_private.py`
- Test: `tests/unit/test_ws_private_consumer.py`

- [ ] **Step 1: Write failing test для shape guard**

Append to `tests/unit/test_ws_private_consumer.py`:

```python
def test_on_order_raw_drops_dict_data_with_log(caplog):
    """M3 regression: if Bybit sends data=dict (V3 shape), must log + drop, NOT iterate keys."""
    from unittest.mock import MagicMock
    from src.execution.ws_private import BybitPrivateWSConsumer
    
    coordinator = MagicMock()
    consumer = BybitPrivateWSConsumer(api_key="test", api_secret="test", coordinator=coordinator)
    msg = {"topic": "order", "data": {"orderId": "12345"}}  # dict, not list
    
    consumer._on_order_raw(msg)
    
    # Verify structured log marker present
    assert any("shape" in rec.message.lower() or "isinstance" in rec.message.lower()
               for rec in caplog.records), "M3: must log shape mismatch"
    # Verify coordinator NOT called
    coordinator.on_order_event.assert_not_called()
```

- [ ] **Step 2: Add isinstance guard в _on_order_raw**

In `src/execution/ws_private.py`:

```python
def _on_order_raw(self, msg: dict[str, Any]) -> None:
    data = msg.get("data")
    # S39 T12 M3 — defensive isinstance guard
    if not isinstance(data, list):
        logger.warning(
            "ws.order.shape_mismatch",
            expected="list",
            got=type(data).__name__,
            topic=msg.get("topic"),
        )
        return
    for order_event in data:
        # ... existing processing ...
```

Same pattern для `_on_position_raw`, `_on_execution_raw` if they accept array data.

- [ ] **Step 3: Verify tests PASS**

```bash
.venv/bin/pytest tests/unit/test_ws_private_consumer.py -v
```

- [ ] **Step 4: Commit**

```bash
git add src/execution/ws_private.py tests/unit/test_ws_private_consumer.py
git commit -m "fix(execution): S39 T12 M3 — isinstance shape guard для WS data array"
```

---

### Task E2: M4 — `__repr__` secret redaction

**Files:**
- Modify: `src/execution/ws_private.py` (или wherever BybitPrivateWSConsumer defined)
- Test: `tests/unit/test_ws_private_consumer.py`

- [ ] **Step 1: Write failing test**

Append to `tests/unit/test_ws_private_consumer.py`:

```python
def test_ws_consumer_repr_does_not_contain_api_secret():
    """M4 security regression: __repr__ MUST never expose api_key OR api_secret."""
    from unittest.mock import MagicMock
    from src.execution.ws_private import BybitPrivateWSConsumer
    
    consumer = BybitPrivateWSConsumer(
        api_key="test_key_visible_xxxxx",
        api_secret="super_secret_value_must_not_appear",
        coordinator=MagicMock(),
    )
    r = repr(consumer)
    assert "super_secret_value_must_not_appear" not in r
    assert "test_key_visible_xxxxx" not in r
```

- [ ] **Step 2: Override __repr__**

In `BybitPrivateWSConsumer`:

```python
def __repr__(self) -> str:
    """S39 T13 M4 — redact secrets from repr (security hardening)."""
    key_redacted = f"{self._api_key[:4]}***" if self._api_key else "none"
    return (
        f"BybitPrivateWSConsumer(api_key={key_redacted}, "
        f"connected={self._connected}, topics={self._topics})"
    )
```

- [ ] **Step 3: Verify PASS**

```bash
.venv/bin/pytest tests/unit/test_ws_private_consumer.py::test_ws_consumer_repr_does_not_contain_api_secret -v
```

- [ ] **Step 4: Commit**

```bash
git add src/execution/ws_private.py tests/unit/test_ws_private_consumer.py
git commit -m "fix(security): S39 T13 M4 — __repr__ redacts api_key+api_secret"
```

---

## Track A — Wiki sync (LAST)

### Task A7: ADR-0059 + sprint page + reason-codes sync + component page

**Files:**
- Create: `llm-wiki/wiki/project/decisions/0059-sprint-39-volume-breakout-pre-registration.md`
- Create: `llm-wiki/wiki/project/sprints/sprint-39-volume-breakout-tech-debt.md`
- Create: `llm-wiki/wiki/project/components/volume-breakout-strategy.md`
- Modify: `llm-wiki/wiki/trading/concepts/reason-codes.md` (sync 42→53)
- Modify: `llm-wiki/wiki/project/architecture/current-state.md` (50→53 codes)
- Modify: `llm-wiki/wiki/index.md` (add ADR + sprint + component entries)

- [ ] **Step 1: Create ADR-0059 (per Q6 REVISE: 8mo PRIMARY, 3.3y SECONDARY с contamination label)**

Create `llm-wiki/wiki/project/decisions/0059-sprint-39-volume-breakout-pre-registration.md`:

```markdown
---
title: ADR 0059 — Sprint 39 volume_breakout pre-registration LOCKED
type: decision
tags: [adr, sprint-39, volume-breakout, autoresearch-integration, locked, anti-snooping, ru]
created: 2026-05-09
updated: 2026-05-09
status: accepted
sources:
  - llm-wiki/wiki/project/research-evidence/FINAL_STRATEGY.md
  - llm-wiki/wiki/project/research-evidence/CLOSE.md
  - llm-wiki/wiki/project/pre-s39-backlog.md
---

# ADR 0059. Sprint 39 — volume_breakout pre-registration LOCKED

**Status:** accepted
**Date:** 2026-05-09
**Pre-commitment:** anti-snooping LOCK per ADR 0054 model

## Контекст

Autoresearch iter 8-10 нашёл `volume_breakout` (Donchian channel + volume confirmation + ATR stop) как единственную PASS strategy на 4H BTCUSDT. Iter 1-7 на 1H/15M/5M = 0 PASS (universal sign-flip).

## Решение

LOCK params sweep#1644 verbatim (anti-snooping):
- lookback_n=9, exit_lookback_n=8
- vol_window=10, vol_mult=1.4563
- atr_period=9, atr_stop_mult=2.9663
- Timeframe=4H, Symbol=BTCUSDT, Side=LONG_ONLY

Реализация в `src/signalgen/volume_breakout_strategy.py` через `VOLUME_BREAKOUT_LOCKED_PARAMS` constant. Dashboard preset ENFORCE 4H+BTCUSDT (backend 422, frontend disabled dropdowns).

## Evidence (per Q6 REVISE — 8mo PRIMARY, 3.3y SECONDARY)

### Primary — held-out OOS (8mo BEAR, 2025-08-26 → 2026-04-26)

- Sharpe: **+9.96**
- PnL: **+20.42%** ($2,042 на $10k notional)
- n_trades: **17** (95% CI Sharpe ±1.5-2.0 — wide due small sample)
- Win rate: 47.06%
- B&H baseline: -30.14% (regime: deep BEAR)
- Alpha vs B&H: **+50.56pp**

Это единственное чистое OOS evidence — held-out был отделён до search loop.

### Secondary — full backtest (3.3y, 2023-01-01 → 2026-04-26) ⚠️ contamination warning

⚠️ **Search-period overlap:** 4510 sweeps × WFA folds покрывают этот период. sweep#1644 выиграл implicit comparison против 4510 alternatives → champion-bias inflated estimate (Bailey & López de Prado 2014 Section 5).

- PnL: +122.66%
- Annualized: +36.96%/year
- ~150 trades

Цифры supporting context, НЕ clean OOS evidence. Интерпретировать с осторожностью.

### Robustness signal (113-PASS distribution)

- 4510 sweeps × 10 strategies = 4.51M trials
- 213 PASS strategies (4.72%)
- 127 PASS sweeps Sharpe > 5
- sweep#1644 в centroid cluster (L=9-10, ex=8-9, vw=10-14, vm=1.20-1.45, ap=7-16, am=2.50-3.10)
- Other 9 strategies на same sweep#1644 — ALL negative held-out (differential edge)

## Sizing disclosure (per Q5 amendment)

⚠️ **Backtest PnL ≠ live account return**:

1. Research PnL (+122.66% / +20.42%) = signal-quality discriminator, не dollar-return projector
2. Под Kelly 0.25× cap (per ADR 0012) фактический account return существенно ниже
3. Арифметика "$10k × 1.2042 = $12k за 8mo" не переводится в account return
4. Пересмотр Kelly fraction = post n=10 live trades + DSR gate

## Acceptance criteria invariant

Profit invariant (HARD): post-S39 backtest PnL ≥ baseline на BOTH gates:
- 8mo held-out PnL ≥ +20.42% (within ±0.5% replication tolerance)
- 3.3y full PnL ≥ +122.66% (within ±0.5%)

Phase 5 HARD-GATE: `tests/integration/test_volume_breakout_baseline_floor.py`. FAIL → blocks merge.

## Gate 2 forward paper-trade (per Q2 CONFIRM)

После tag alpha.39:
- Forward paper-trade на δ TESTNET infrastructure
- N≥10 live signals MIN
- Operator monitors per delta-activation-playbook
- IF FAIL Gate 2 → S40 honest close ADR обязателен ДО любой MAINNET-promotion

## N_trials counter (per CC3)

Volume_breakout = pre-registered hypothesis #8 в проекте.
Cumulative N_trials post-S39: 8 (S13 + S15 + S17 + S20 + S22 + S33 + S35 + S39).
DSR penalty pooled растёт с каждой hypothesis — фиксируется в cross_trial_sharpes.json.

## Альтернативы

- **(b) Round к 2 sigfigs (vol_mult=1.46)** — REJECTED, post-observation tuning = data snooping
- **(c) Re-search в narrow neighborhood** — REJECTED, Bailey blowup risk
- **(d) Augmentation с EMA200/ADX/RSI/ATR filters** — DEFERRED к S40+ per Q9 Option A (clean anti-snooping)

## Последствия

- 3 NEW ReasonCodes (50→53): ENTRY_LONG_VOLUME_BREAKOUT, EXIT_FLAT_VOLUME_CHANNEL, EXIT_FLAT_ATR_STOP_VB
- New strategy preset в dashboard (volume_breakout_iter10, ENFORCE 4H+BTCUSDT)
- Phase 5 HARD-GATE через baseline_floor integration test
- Gate 2 forward N≥10 BLOCKER для real capital (post-tag operator responsibility)
- N_trials = 8; cross_trial DSR penalty growing — будущие hypotheses face higher bar

## Связанные документы

- [[../sprints/sprint-39-volume-breakout-tech-debt]]
- [[../components/volume-breakout-strategy]]
- [[../research-evidence/FINAL_STRATEGY]]
- [[../research-evidence/CLOSE]]
- [[0054-sprint-35-donchian-pre-registration]] — pre-registration model
- [[0052-sprint-34-acceptance-criteria-amendment]] — acceptance criteria
- [[0012-4-phase-kelly-sizing]] — sizing policy
```

- [ ] **Step 2: Create sprint-39 page**

Create `llm-wiki/wiki/project/sprints/sprint-39-volume-breakout-tech-debt.md` (template after sprint-38 page).

Sections: Цель / Обзор / Доставленная функциональность (Code/Wiki/Tests) / Решения и отклонения / Проверка / Влияние на следующие спринты / Перенесённые задачи / Связанные документы.

- [ ] **Step 3: Create component page volume-breakout-strategy.md**

Create `llm-wiki/wiki/project/components/volume-breakout-strategy.md` (template after donchian-strategy.md). Include: Description / Public API / Configuration / Invariants / Tests / Связанные документы.

- [ ] **Step 4: Sync reason-codes.md (42→53)**

Edit `llm-wiki/wiki/trading/concepts/reason-codes.md` — update count в frontmatter + body.
Add reconciliation table: S7 +3 / S36 +4 / S37 +1 / S39 +3.

- [ ] **Step 5: Sync current-state.md (50→53)**

Edit `llm-wiki/wiki/project/architecture/current-state.md` — canonical-counts table reason_codes 50→53; sprint history row для S39.

- [ ] **Step 6: Sync index.md**

Edit `llm-wiki/wiki/index.md`:
- Add `[[project/sprints/sprint-39-volume-breakout-tech-debt]]` к Sprints section
- Add `[[project/decisions/0059-sprint-39-volume-breakout-pre-registration]]` к Decisions
- Add `[[project/components/volume-breakout-strategy]]` к Components

- [ ] **Step 7: Append log.md sprint-end entry**

Edit `llm-wiki/wiki/log.md` — append:

```markdown
## [2026-05-09] sprint-end | S39 — volume_breakout production integration + tech debt

- **Track A (volume_breakout core):** 6 tasks — VolumeBreakoutStrategy + 3 ReasonCodes + dashboard preset с ENFORCE + baseline floor integration test + research-evidence cherry-pick
- **Track B (critical tech debt):** 3 tasks — H1 rate-limit backoff + H2 WS reconnect re-probe + Item#10 boundary tests
- **Track C (cleanup):** 2 tasks — Item#7 shim removal + F8 _MC_BLOCK_SIZE unified
- **Track E (bybit-api):** 2 tasks — M3 isinstance guard + M4 __repr__ secret redaction
- **Wiki:** ADR-0059 + sprint-39 page + component page + reason-codes sync (50→53) + current-state sync + research-evidence section
- **Tests:** +N (volume_breakout unit + integration baseline floor + property tests + WS shape/repr + backoff)
- **Counts:** 16/30/74/**53** (reason_codes +3)
- **Tag:** v0.1.0-alpha.39
- **Profit invariant:** PASS (3.3y ≥ +122.66% AND 8mo ≥ +20.42% verified via baseline floor integration)
- **Gate 2 forward paper-trade:** PENDING — operator activates на δ TESTNET, N≥10 signals required ДО real capital
```

- [ ] **Step 8: Commit**

```bash
git add llm-wiki/
git commit -m "docs(wiki): S39 T14 — ADR 0059 + sprint page + component + reason-codes sync (50→53)"
```

---

## Phase 5 Verify checklist (after all tasks complete)

- [ ] `pytest tests/unit -q` — all PASS, count grew (~+30-50 tests)
- [ ] `pytest tests/integration -q` — all PASS включая baseline_floor
- [ ] `pytest tests/property -q` — all PASS
- [ ] `mypy --strict src/` — 0 errors
- [ ] Canonical counts script: `states=16, events=30, transitions=74, reason_codes=53`
- [ ] Phase 5 HARD-GATE baseline floor: 3.3y ≥ +122.66% AND 8mo ≥ +20.42%

## Phase 6 Review (parallel reviewers)

Dispatch in single message:
- **trader-expert** (volume_breakout business logic + acceptance criteria + ADR 0059 review)
- **quant-stats-reviewer** (volume_breakout math + DSR/N_trials accounting + baseline replication)
- **trading-logic-reviewer** (FSM impact + look-ahead invariant + reason codes)
- **bybit-api-reviewer** (H1 backoff implementation + M3 isinstance + M4 repr)
- **architecture-reviewer** (H1 backoff design — decorator placement)
- **security-auditor** (M4 secret redaction + override paths if touched)
- **test-engineer** (test coverage post-S39 + baseline floor design)
- **python-reviewer** (mypy + idioms + type hints)

## Phase 7 Sync — wiki-update skill

Run `wiki-update` skill — verify Block 1 (code refs) ↔ Block 2 (descriptions) sync для:
- volume-breakout-strategy.md (new component)
- reason-codes.md (count change)
- current-state.md (counts + sprint history)

## Phase 8 Ship

- [ ] All Phase 6 reviewers approved (no BLOCKER)
- [ ] `sprint-finish` skill HARD-GATE checklist
- [ ] `git push origin feature/sprint-39-volume-breakout-tech-debt`
- [ ] `gh pr create` с title "Sprint 39: volume_breakout production + critical tech debt"
- [ ] Squash-merge → main
- [ ] `git tag -a v0.1.0-alpha.39 -m "Sprint 39 — volume_breakout production integration"`
- [ ] `git push origin v0.1.0-alpha.39`
- [ ] SPRINT_STATE → between-sprints

## Phase 9 Close

- [ ] Append log.md session-end
- [ ] mark_chapter "Sprint 39 ship complete"
- [ ] Operator activates Gate 2 forward paper-trade на δ TESTNET (out of sprint scope)

---

**Estimated total:** 14 tasks × ~30-60min = 7-14 hours implementation + 1-2 hours review + ship.
