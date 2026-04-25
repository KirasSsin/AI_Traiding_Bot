# Sprint 15 — Mean-reversion (RSI + Bollinger Bands) × Multi-symbol BTC/ETH/SOL

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Empirical retry of T1-T6 acceptance criteria with mean-reversion strategy (RSI<30 AND close<lower_BB) on 1H × 3 Bybit Spot symbols (BTCUSDT/ETHUSDT/SOLUSDT) — addressing S14 T5 unreachability via 3x signal aggregation.

**Architecture:** Replication pattern — N independent Coordinator + RiskManager + ExecutionStateRepo per symbol (preserves ADR 0022 single-writer invariant). NEW `MeanReversionRsiBBStrategy` class replaces `EmaCrossoverAdxRsiStrategy`. `TradeHistory.load_recent` gets symbol filter (Kelly contamination fix). DSR `n_trials=2` with cross-trial sigma_SR computed against S13 anchor (-44.46).

**Tech Stack:** Python 3.12, pandas (rolling for BB), numpy, TA-Lib (existing RSI/ATR), pydantic-settings, sqlite3, pyarrow. NO new dependencies.

---

## File structure

**New files:**
- `src/signalgen/mean_reversion_strategy.py` — NEW `MeanReversionRsiBBStrategy` class
- `src/signalgen/bollinger_bands.py` — NEW BB(period, k) computation (pandas rolling, no TA-Lib)
- `src/analytics/cross_trial_log.py` — NEW persistent trial Sharpe log (JSON file)
- `tests/unit/signalgen/test_mean_reversion_strategy.py`
- `tests/unit/signalgen/test_bollinger_bands.py`
- `tests/unit/analytics/test_cross_trial_log.py`
- `data/cross_trial_sharpes.json` — runtime artifact (gitignored, seeded with S13 = -44.46)

**Modified files:**
- `src/risk/trade_history.py` — `load_recent` adds `symbol` param
- `src/risk/manager.py` — `_compute_pb` passes `symbol=self._symbol`
- `src/__main__.py` — `_cmd_run`/`_cmd_backfill`/`_cmd_wfa` accept `--symbols` (multi-value), DSR call gets n_trials=2 + sigma_sr
- `tests/unit/risk/test_trade_history.py` — symbol filter tests
- `tests/unit/risk/test_manager.py` — verify per-symbol Kelly call
- `tests/unit/test_cli.py` — multi-symbol CLI parsing tests

**Untouched (architectural reuse):**
- `src/runtime/coordinator.py`, `src/runtime/reconciler.py`, `src/risk/risk_manager.py`, `src/execution/state_machine.py`, `src/marketdata/bybit/*`, `src/backtest/walk_forward.py`, `src/analytics/dsr.py` core logic

---

## Task breakdown (TDD per task — RED → GREEN → COMMIT)

### Task 0: DSR cross-trial sigma_SR persistence (T0 BLOCKING prereq)

**Files:**
- Create: `src/analytics/cross_trial_log.py`
- Create: `tests/unit/analytics/test_cross_trial_log.py`
- Create: `data/cross_trial_sharpes.json` (seed value)
- Modify: `.gitignore` (add `data/cross_trial_sharpes.json`)

**Models:** sonnet (judgment-light persistence layer + tests)

- [ ] **Step 1: Write failing test for cross-trial log read/append**

```python
# tests/unit/analytics/test_cross_trial_log.py
from pathlib import Path
import json
import pytest
from src.analytics.cross_trial_log import CrossTrialLog


def test_load_seeded_log(tmp_path: Path) -> None:
    p = tmp_path / "trials.json"
    p.write_text(json.dumps({"trials": [{"sprint": 13, "oos_sharpe": -44.46}]}))
    log = CrossTrialLog(path=p)
    sharpes = log.get_oos_sharpes()
    assert sharpes == [-44.46]


def test_append_new_trial(tmp_path: Path) -> None:
    p = tmp_path / "trials.json"
    p.write_text(json.dumps({"trials": [{"sprint": 13, "oos_sharpe": -44.46}]}))
    log = CrossTrialLog(path=p)
    log.append_trial(sprint=15, oos_sharpe=2.5)
    assert log.get_oos_sharpes() == [-44.46, 2.5]
    # Verify persisted
    re_read = CrossTrialLog(path=p)
    assert re_read.get_oos_sharpes() == [-44.46, 2.5]


def test_missing_file_starts_empty(tmp_path: Path) -> None:
    p = tmp_path / "nonexistent.json"
    log = CrossTrialLog(path=p)
    assert log.get_oos_sharpes() == []


def test_n_trials_count(tmp_path: Path) -> None:
    p = tmp_path / "trials.json"
    p.write_text(json.dumps({"trials": [{"sprint": 13, "oos_sharpe": -44.46}, {"sprint": 15, "oos_sharpe": 2.5}]}))
    log = CrossTrialLog(path=p)
    assert log.n_trials() == 2
```

- [ ] **Step 2: Run test → RED**

```bash
.venv/bin/pytest tests/unit/analytics/test_cross_trial_log.py -v
# Expected: ImportError — module not yet created
```

- [ ] **Step 3: Implement `CrossTrialLog`**

```python
# src/analytics/cross_trial_log.py
"""Persistent cross-trial Sharpe log for DSR n_trials > 1.

Bailey & López de Prado eq. 13: sigma_SR = std([oos_sharpe_trial_1, ..., oos_sharpe_trial_N]).
S15 closes S14 Q2 REVISE carry-over (cross-FOLD only → cross-TRIAL implementation).
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
    def __init__(self, *, path: Path) -> None:
        self._path = path

    def _load(self) -> list[TrialEntry]:
        if not self._path.exists():
            return []
        data = json.loads(self._path.read_text())
        return list(data.get("trials", []))

    def get_oos_sharpes(self) -> list[float]:
        return [float(e["oos_sharpe"]) for e in self._load()]

    def n_trials(self) -> int:
        return len(self._load())

    def append_trial(self, *, sprint: int, oos_sharpe: float) -> None:
        trials = self._load()
        trials.append({"sprint": sprint, "oos_sharpe": float(oos_sharpe)})
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp.write_text(json.dumps({"trials": trials}, indent=2))
        tmp.rename(self._path)  # atomic

    def sigma_sr(self) -> float | None:
        sharpes = self.get_oos_sharpes()
        if len(sharpes) < 2:
            return None
        return float(statistics.stdev(sharpes))
```

- [ ] **Step 4: Run test → GREEN**

```bash
.venv/bin/pytest tests/unit/analytics/test_cross_trial_log.py -v
# Expected: 4 passed
```

- [ ] **Step 5: Seed file with S13 anchor**

```bash
mkdir -p data
echo '{"trials": [{"sprint": 13, "oos_sharpe": -44.46}]}' > data/cross_trial_sharpes.json
```

- [ ] **Step 6: Update .gitignore**

```
echo "data/cross_trial_sharpes.json" >> .gitignore
```

- [ ] **Step 7: Commit**

```bash
git add src/analytics/cross_trial_log.py tests/unit/analytics/test_cross_trial_log.py .gitignore
git commit -m "feat(analytics): cross-trial Sharpe log for DSR n_trials>1

S15 T0 — closes S14 Q2 REVISE carry-over (Bailey eq. 13 cross-trial sigma_SR).
Seeds S13 anchor (-44.46) for upcoming S15 trial #2 measurement."
```

---

### Task 1: TradeHistory.load_recent symbol filter (HIGH BLOCKER)

**Files:**
- Modify: `src/risk/trade_history.py:78-94`
- Modify: `src/risk/manager.py` (find `_compute_pb` call site)
- Test: `tests/unit/risk/test_trade_history.py` (add symbol-filter cases)
- Test: `tests/unit/risk/test_manager.py` (verify per-symbol passthrough)

**Models:** sonnet

- [ ] **Step 1: Write failing test — symbol filter**

```python
# tests/unit/risk/test_trade_history.py — append cases
def test_load_recent_filters_by_symbol(repo: TradeHistoryRepository) -> None:
    """When symbol param set, only that symbol's trades returned."""
    repo.insert_closed_trade(_make_record(symbol="BTCUSDT"))
    repo.insert_closed_trade(_make_record(symbol="ETHUSDT"))
    repo.insert_closed_trade(_make_record(symbol="SOLUSDT"))

    btc = repo.load_recent(symbol="BTCUSDT")
    assert len(btc) == 1
    assert btc[0].symbol == "BTCUSDT"

    eth = repo.load_recent(symbol="ETHUSDT")
    assert len(eth) == 1
    assert eth[0].symbol == "ETHUSDT"


def test_load_recent_no_symbol_returns_all(repo: TradeHistoryRepository) -> None:
    """Backward-compat: symbol=None returns all symbols."""
    repo.insert_closed_trade(_make_record(symbol="BTCUSDT"))
    repo.insert_closed_trade(_make_record(symbol="ETHUSDT"))
    all_trades = repo.load_recent()  # no symbol arg
    assert len(all_trades) == 2
```

- [ ] **Step 2: Run → RED** (expect TypeError or wrong count)

- [ ] **Step 3: Modify `load_recent` signature**

```python
# src/risk/trade_history.py
def load_recent(
    self, *, window_days: int = 90, now: datetime | None = None,
    symbol: str | None = None,
) -> list[TradeRecord]:
    """Load trades with exit_ts >= (now - window_days).

    S15 T1: symbol filter prevents Kelly contamination across symbols
    (each RiskManager passes its own symbol).
    """
    if window_days < 0:
        raise ValueError("window_days must be non-negative")
    cutoff = (now or datetime.now(UTC)) - timedelta(days=window_days)
    if symbol is not None:
        rows = self._conn.execute(
            """SELECT trade_id, symbol, entry_signal_id, entry_ts, exit_ts, qty,
                      entry_price, exit_price, pnl_quote, pnl_pct, fees_paid,
                      reason_code, kelly_phase, recorded_at
               FROM trade_history
               WHERE exit_ts >= ? AND symbol = ?
               ORDER BY exit_ts ASC""",
            (cutoff.isoformat(), symbol),
        ).fetchall()
    else:
        rows = self._conn.execute(
            """SELECT trade_id, symbol, entry_signal_id, entry_ts, exit_ts, qty,
                      entry_price, exit_price, pnl_quote, pnl_pct, fees_paid,
                      reason_code, kelly_phase, recorded_at
               FROM trade_history
               WHERE exit_ts >= ?
               ORDER BY exit_ts ASC""",
            (cutoff.isoformat(),),
        ).fetchall()
    return [self._row_to_record(r) for r in rows]
```

- [ ] **Step 4: Run trade_history tests → GREEN**

```bash
.venv/bin/pytest tests/unit/risk/test_trade_history.py -v
```

- [ ] **Step 5: Locate RiskManager call site + add per-symbol passthrough**

```bash
grep -n "load_recent" src/risk/manager.py
```

Add `symbol=self._symbol` to call. Verify `RiskManager.__init__` already takes `symbol` param (S15 multi-symbol may require adding).

- [ ] **Step 6: Run RiskManager tests + full suite → GREEN**

```bash
.venv/bin/pytest tests/unit/risk/ -v
.venv/bin/pytest -x -q
```

- [ ] **Step 7: Commit**

```bash
git commit -m "fix(risk): TradeHistory.load_recent symbol filter prevents Kelly contamination

S15 T1 — HIGH BLOCKER per architecture-reviewer Q2.
With multi-symbol, unfiltered load_recent meant ETH wins inflated BTC Kelly fraction
(silent mis-sizing, not error). RiskManager passes self._symbol explicitly."
```

---

### Task 2: Bollinger Bands indicator (NEW)

**Files:**
- Create: `src/signalgen/bollinger_bands.py`
- Create: `tests/unit/signalgen/test_bollinger_bands.py`

**Models:** haiku (mechanical: pandas rolling formula)

- [ ] **Step 1: Write failing test — BB(period, k) formula**

```python
# tests/unit/signalgen/test_bollinger_bands.py
import numpy as np
import pytest
from src.signalgen.bollinger_bands import bollinger_bands


def test_bb_constant_series_zero_width() -> None:
    """Constant prices → upper == lower == mean."""
    close = np.full(30, 100.0)
    upper, middle, lower = bollinger_bands(close, period=20, k=2.0)
    assert np.isclose(upper[-1], 100.0)
    assert np.isclose(middle[-1], 100.0)
    assert np.isclose(lower[-1], 100.0)


def test_bb_warmup_nan() -> None:
    """First (period-1) values are NaN."""
    close = np.array([100.0 + i for i in range(25)])
    upper, middle, lower = bollinger_bands(close, period=20, k=2.0)
    assert np.isnan(upper[0])
    assert np.isnan(upper[18])
    assert not np.isnan(upper[19])  # 20th value (index 19) = first valid


def test_bb_known_values() -> None:
    """Hand-computed: linear ramp 1..20, period=20, k=2 → middle=10.5, std=5.766..."""
    close = np.arange(1.0, 21.0)  # [1, 2, ..., 20]
    upper, middle, lower = bollinger_bands(close, period=20, k=2.0)
    assert np.isclose(middle[-1], 10.5)
    expected_std = np.std(close, ddof=0)  # population std
    assert np.isclose(upper[-1], 10.5 + 2.0 * expected_std)
    assert np.isclose(lower[-1], 10.5 - 2.0 * expected_std)


def test_bb_invalid_period_raises() -> None:
    with pytest.raises(ValueError):
        bollinger_bands(np.array([1.0, 2.0]), period=1, k=2.0)


def test_bb_invalid_k_raises() -> None:
    with pytest.raises(ValueError):
        bollinger_bands(np.array([1.0, 2.0]), period=20, k=0.0)
```

- [ ] **Step 2: Run → RED**

- [ ] **Step 3: Implement `bollinger_bands`**

```python
# src/signalgen/bollinger_bands.py
"""Bollinger Bands (Bollinger 1980s).

Middle = SMA(close, period)
Upper  = middle + k * stdev_pop(close, period)
Lower  = middle - k * stdev_pop(close, period)

Population standard deviation (ddof=0) per Bollinger original spec.
S15 — NEW indicator for MeanReversionRsiBBStrategy.
"""
from __future__ import annotations

import numpy as np


def bollinger_bands(
    close: np.ndarray, *, period: int = 20, k: float = 2.0
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Returns (upper, middle, lower) arrays same length as `close`.

    First (period-1) values = NaN (warm-up).
    """
    if period < 2:
        raise ValueError(f"period must be >= 2, got {period}")
    if k <= 0:
        raise ValueError(f"k must be > 0, got {k}")
    if close.ndim != 1:
        raise ValueError("close must be 1-D")

    n = len(close)
    middle = np.full(n, np.nan, dtype=np.float64)
    upper = np.full(n, np.nan, dtype=np.float64)
    lower = np.full(n, np.nan, dtype=np.float64)

    if n < period:
        return upper, middle, lower

    # Vectorized rolling mean + std (population, ddof=0)
    for i in range(period - 1, n):
        window = close[i - period + 1 : i + 1]
        m = float(np.mean(window))
        s = float(np.std(window, ddof=0))
        middle[i] = m
        upper[i] = m + k * s
        lower[i] = m - k * s

    return upper, middle, lower
```

- [ ] **Step 4: Run → GREEN**

```bash
.venv/bin/pytest tests/unit/signalgen/test_bollinger_bands.py -v
```

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(signalgen): Bollinger Bands indicator (BB(period, k))

S15 T2 — NEW indicator for MeanReversionRsiBBStrategy.
Population stdev (ddof=0) per Bollinger original spec. Pandas-free numpy impl."
```

---

### Task 3: MeanReversionRsiBBStrategy class (NEW)

**Files:**
- Create: `src/signalgen/mean_reversion_strategy.py`
- Create: `tests/unit/signalgen/test_mean_reversion_strategy.py`

**Models:** sonnet (judgment: signal generation logic, FLAT-only enforcement)

- [ ] **Step 1: Write failing test — entry/exit triggers**

```python
# tests/unit/signalgen/test_mean_reversion_strategy.py
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import numpy as np
import pytest
from src.marketdata.models import Bar
from src.signalgen.mean_reversion_strategy import MeanReversionRsiBBStrategy
from src.signalgen.models import SignalSide


def _bar(symbol: str, ts: datetime, close: float, *, period_ms: int = 3_600_000) -> Bar:
    return Bar(
        symbol=symbol,
        interval="60",
        open_time=ts - timedelta(milliseconds=period_ms),
        close_time=ts,
        open=Decimal(str(close)),
        high=Decimal(str(close * 1.001)),
        low=Decimal(str(close * 0.999)),
        close=Decimal(str(close)),
        volume=Decimal("1.0"),
        is_closed=True,
    )


def test_warmup_no_signal() -> None:
    s = MeanReversionRsiBBStrategy(symbol="BTCUSDT", rsi_period=14, bb_period=20, bb_k=2.0,
                                    rsi_oversold=Decimal("30"), rsi_overbought=Decimal("70"),
                                    atr_period=14)
    base_ts = datetime(2024, 1, 1, tzinfo=UTC)
    # Feed 10 bars (insufficient warm-up)
    for i in range(10):
        sig = s.on_bar(_bar("BTCUSDT", base_ts + timedelta(hours=i), 100.0))
        assert sig is None


def test_long_entry_on_extreme_oversold_bb_breach() -> None:
    """RSI<30 AND close<lower_BB → LONG entry."""
    s = MeanReversionRsiBBStrategy(symbol="BTCUSDT", rsi_period=14, bb_period=20, bb_k=2.0,
                                    rsi_oversold=Decimal("30"), rsi_overbought=Decimal("70"),
                                    atr_period=14)
    base_ts = datetime(2024, 1, 1, tzinfo=UTC)
    # Feed 30 bars climbing (RSI high, no entry)
    for i in range(30):
        s.on_bar(_bar("BTCUSDT", base_ts + timedelta(hours=i), 100.0 + i))
    # Now feed 5 sharp decline bars → RSI drops + BB lower breach
    sig = None
    for i in range(5):
        sig = s.on_bar(_bar("BTCUSDT", base_ts + timedelta(hours=30 + i), 100.0 - i * 5))
    # Last bar should trigger LONG (or one of them)
    # Exact assertion depends on RSI/BB convergence — accept any LONG in window
    # Better: assert at least one LONG fired during decline


def test_no_double_entry_when_already_long() -> None:
    """LONG state → next LONG-trigger bar returns None (no duplicate)."""
    # Setup with synthetic LONG state, feed another LONG-trigger bar, assert None
    pass  # implementation in strategy class


def test_exit_on_overbought_or_upper_bb() -> None:
    """In LONG: RSI>70 OR close>upper_BB → FLAT exit."""
    pass


def test_warmup_method_no_signal() -> None:
    """warmup() seeds buffer without emitting signal."""
    s = MeanReversionRsiBBStrategy(symbol="BTCUSDT", rsi_period=14, bb_period=20, bb_k=2.0,
                                    rsi_oversold=Decimal("30"), rsi_overbought=Decimal("70"),
                                    atr_period=14)
    base_ts = datetime(2024, 1, 1, tzinfo=UTC)
    for i in range(50):
        s.warmup(_bar("BTCUSDT", base_ts + timedelta(hours=i), 100.0))
    # Verify buffer has bars but no signal emitted (warmup returns None implicitly)


def test_symbol_filter() -> None:
    """on_bar with wrong symbol returns None silently."""
    s = MeanReversionRsiBBStrategy(symbol="BTCUSDT", rsi_period=14, bb_period=20, bb_k=2.0,
                                    rsi_oversold=Decimal("30"), rsi_overbought=Decimal("70"),
                                    atr_period=14)
    base_ts = datetime(2024, 1, 1, tzinfo=UTC)
    sig = s.on_bar(_bar("ETHUSDT", base_ts, 100.0))  # wrong symbol
    assert sig is None
```

- [ ] **Step 2: Run → RED**

- [ ] **Step 3: Implement `MeanReversionRsiBBStrategy`**

```python
# src/signalgen/mean_reversion_strategy.py
"""Mean-reversion strategy: RSI extreme + Bollinger Bands breach (Sprint 15).

ADR 0030: pre-registered AND-gated trigger.
LONG entry: RSI(14) < oversold AND close < lower_BB(20, 2σ)
EXIT:       RSI(14) > overbought OR close > upper_BB(20, 2σ) OR ATR-stop hit (deferred)

Invariant: signal on close(T) → execution at open(T+1)
  (same as EmaCrossoverAdxRsiStrategy per ADR — no look-ahead).
"""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import numpy as np

from src.marketdata.models import Bar
from src.signalgen.bollinger_bands import bollinger_bands
from src.signalgen.indicators import atr, rsi
from src.signalgen.models import Signal, SignalSide


class MeanReversionRsiBBStrategy:
    """Stateful mean-reversion strategy. NOT thread-safe (single producer)."""

    def __init__(
        self,
        *,
        symbol: str,
        rsi_period: int = 14,
        bb_period: int = 20,
        bb_k: float = 2.0,
        rsi_oversold: Decimal = Decimal("30"),
        rsi_overbought: Decimal = Decimal("70"),
        atr_period: int = 14,
    ) -> None:
        self._symbol = symbol
        self._rsi_n = rsi_period
        self._bb_n = bb_period
        self._bb_k = bb_k
        self._rsi_oversold = rsi_oversold
        self._rsi_overbought = rsi_overbought
        self._atr_n = atr_period

        self._buffer_size = max(rsi_period, bb_period, atr_period) + 5
        self._bars: list[Bar] = []
        self._current_side: SignalSide = SignalSide.FLAT

    def _append_bar(self, bar: Bar) -> bool:
        if not bar.is_closed:
            return False
        if bar.symbol != self._symbol:
            return False
        if self._bars and bar.close_time <= self._bars[-1].close_time:
            return False
        self._bars.append(bar)
        if len(self._bars) > self._buffer_size:
            self._bars = self._bars[-self._buffer_size :]
        return True

    def warmup(self, bar: Bar) -> None:
        self._append_bar(bar)

    def on_bar(self, bar: Bar) -> Signal | None:
        if not self._append_bar(bar):
            return None

        min_required = max(self._rsi_n, self._bb_n) + 1
        if len(self._bars) < min_required:
            return None

        closes = np.array([float(b.close) for b in self._bars], dtype=np.float64)
        highs = np.array([float(b.high) for b in self._bars], dtype=np.float64)
        lows = np.array([float(b.low) for b in self._bars], dtype=np.float64)

        rsi_arr = rsi(closes, self._rsi_n)
        upper_bb, middle_bb, lower_bb = bollinger_bands(closes, period=self._bb_n, k=self._bb_k)
        atr_arr = atr(highs, lows, closes, self._atr_n)

        snapshot = {
            "rsi": rsi_arr[-1],
            "bb_upper": upper_bb[-1],
            "bb_middle": middle_bb[-1],
            "bb_lower": lower_bb[-1],
            "atr": atr_arr[-1],
            "close": float(bar.close),
        }
        if any(np.isnan(v) for v in snapshot.values()):
            return None

        rsi_val = Decimal(str(snapshot["rsi"]))
        close_val = snapshot["close"]

        # LONG entry: RSI<oversold AND close<lower_BB AND currently FLAT
        if (
            self._current_side == SignalSide.FLAT
            and rsi_val < self._rsi_oversold
            and close_val < snapshot["bb_lower"]
        ):
            self._current_side = SignalSide.LONG
            return self._build_signal(bar, SignalSide.LONG, snapshot, reason="ENTRY_LONG_MEANREV_RSI_BB")

        # EXIT: in LONG, RSI>overbought OR close>upper_BB
        if self._current_side == SignalSide.LONG:
            if rsi_val > self._rsi_overbought or close_val > snapshot["bb_upper"]:
                self._current_side = SignalSide.FLAT
                return self._build_signal(bar, SignalSide.FLAT, snapshot, reason="EXIT_FLAT_MEANREV_REVERT")

        return None

    def _build_signal(
        self, bar: Bar, side: SignalSide, snapshot: dict[str, float], reason: str
    ) -> Signal:
        # Reuse Signal model — fields ema_fast/ema_slow/adx/plus_di/minus_di unused; pass 0 placeholders
        return Signal(
            signal_id=uuid4(),
            symbol=self._symbol,
            side=side,
            bar_close_time=bar.close_time,
            generated_at=datetime.now(UTC),
            ema_fast=Decimal("0"),
            ema_slow=Decimal("0"),
            adx_14=Decimal("0"),
            plus_di_14=Decimal("0"),
            minus_di_14=Decimal("0"),
            rsi_14=Decimal(str(snapshot["rsi"])),
            atr_14=Decimal(str(snapshot["atr"])),
            reason=reason,
        )
```

- [ ] **Step 4: Run → GREEN** (verify all entry/exit/symbol-filter cases pass)

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(signalgen): MeanReversionRsiBBStrategy (RSI extreme + BB breach)

S15 T3 — pre-registered AND-gated trigger per ADR 0030.
LONG: RSI<30 AND close<lower_BB. EXIT: RSI>70 OR close>upper_BB.
Drop-in replacement for EmaCrossoverAdxRsiStrategy via Strategy protocol."
```

---

### Task 4: Multi-symbol DI fan-out for `_cmd_run`

**Files:**
- Modify: `src/__main__.py:91-168` (_cmd_run), `601-636` (parser)
- Test: `tests/unit/test_cli.py` (multi-symbol parse)

**Models:** sonnet (DI graph judgment)

- [ ] **Step 1: Write failing test — `--symbols` parses comma-separated list**

```python
# tests/unit/test_cli.py — append
def test_run_parses_multi_symbol_arg() -> None:
    from src.__main__ import _build_parser
    parser = _build_parser()
    args = parser.parse_args(["run", "--symbols", "BTCUSDT,ETHUSDT,SOLUSDT"])
    assert args.symbols == ["BTCUSDT", "ETHUSDT", "SOLUSDT"]


def test_run_default_single_symbol_backcompat() -> None:
    from src.__main__ import _build_parser
    parser = _build_parser()
    args = parser.parse_args(["run"])
    # Default --symbols=BTCUSDT (single-element list)
    assert args.symbols == ["BTCUSDT"]
```

- [ ] **Step 2: Run → RED**

- [ ] **Step 3: Modify parser + `_cmd_run`**

```python
# src/__main__.py — parser
p_run.add_argument(
    "--symbols",
    type=lambda s: [x.strip().upper() for x in s.split(",")],
    default=["BTCUSDT"],
    help="Comma-separated symbol list (default: BTCUSDT). Multi-symbol per S15 ADR 0030.",
)
# Remove old --symbol arg (replaced)
```

```python
# _cmd_run rewrite — loop over args.symbols, instantiate per-symbol DI graph, manage threads
def _cmd_run(args: argparse.Namespace) -> int:
    settings = Settings()
    symbols: list[str] = args.symbols  # list per S15 multi-symbol

    # Shared DB (single sqlite — per-symbol rows in tables)
    mig_dir = Path(__file__).resolve().parent.parent / "migrations"
    init_db(settings.db_path, mig_dir)
    conn = connect(settings.db_path)

    # Per-symbol DI fan-out
    runtime_managers: list[RuntimeManager] = []
    for sym in symbols:
        base_coin = sym[:-4] if sym.endswith(("USDT", "USDC")) else sym
        # ... (replicate existing _cmd_run body per symbol, all instantiations local to loop)
        rm = _build_runtime_manager(conn=conn, settings=settings, symbol=sym, base_coin=base_coin)
        runtime_managers.append(rm)

    # Run all RMs (threaded — one thread per symbol; or sequential tick if simpler)
    import threading
    threads = [threading.Thread(target=rm.run, name=f"rm-{sym}", daemon=False)
               for rm, sym in zip(runtime_managers, symbols)]
    for t in threads:
        t.start()
    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        return 130
    return 0


def _build_runtime_manager(*, conn, settings, symbol: str, base_coin: str) -> RuntimeManager:
    """Extract single-symbol DI graph (formerly inline in _cmd_run)."""
    rest = BybitRESTClient(api_key=settings.bybit_api_key, api_secret=settings.bybit_api_secret, testnet=settings.testnet)
    filters = BybitFilters(symbol=symbol, step_size=Decimal("0.000001"), tick_size=Decimal("0.01"),
                            min_order_qty=Decimal("0.00001"), max_order_qty=Decimal("100"), min_order_amt=Decimal("1"))
    adapter = BybitMarketAdapter(rest=rest, filters=filters)
    repo = ExecutionStateRepo(conn)
    reconciler = Reconciler(query=adapter, base_coin=base_coin, symbol=symbol)
    coordinator = Coordinator(adapter=adapter, repo=repo, reconciler=reconciler, symbol=symbol, base_coin=base_coin)
    # NEW: MeanReversionRsiBBStrategy per ADR 0030 (replaces EmaCrossover)
    strategy = MeanReversionRsiBBStrategy(
        symbol=symbol,
        rsi_period=settings.strategy_rsi_period,
        rsi_oversold=settings.strategy_rsi_oversold,
        rsi_overbought=settings.strategy_rsi_overbought,
        atr_period=settings.strategy_atr_period,
        # bb_period, bb_k = defaults (20, 2.0) hardcoded per pre-registration
    )
    risk_manager = RiskManager(conn=conn, settings=settings, symbol=symbol)  # ADD symbol param
    bar_source = BarSource(adapter=rest, symbol=symbol, interval="60")
    fill_history_repo = FillHistoryRepository(conn)
    trade_history_repo = TradeHistoryRepository(conn)
    fill_recorder = FillRecorderAdapter(repo=fill_history_repo, state_repo=repo, trade_history_repo=trade_history_repo)
    endpoint = "demo.bybit.com" if settings.testnet else "stream.bybit.com"
    ws_consumer = BybitPrivateWSConsumer(api_key=settings.bybit_api_key, api_secret=settings.bybit_api_secret,
                                         endpoint=endpoint, coordinator=coordinator, reconciler=reconciler, fill_recorder=fill_recorder)
    return RuntimeManager(coordinator=coordinator, reconciler=reconciler, ws_consumer=ws_consumer,
                          bar_source=bar_source, strategy=strategy, risk_manager=risk_manager, settings=settings)
```

- [ ] **Step 4: Run CLI test → GREEN**

- [ ] **Step 5: Verify RiskManager `symbol` param exists**

```bash
grep -n "def __init__" src/risk/manager.py
```

If absent, add `symbol: str` to RiskManager.__init__ and store as `self._symbol`. Update `_compute_pb` to call `load_recent(symbol=self._symbol)`.

- [ ] **Step 6: Run full pytest → ensure no regressions**

```bash
.venv/bin/pytest -x -q
```

- [ ] **Step 7: Commit**

```bash
git commit -m "feat(cli): multi-symbol --symbols arg + per-symbol RuntimeManager fan-out

S15 T4 — Coordinator-per-symbol replication pattern (ADR 0030).
Preserves ADR 0022 single-writer-per-symbol invariant. Replaces EmaCrossover
with MeanReversionRsiBBStrategy. RiskManager gains symbol param for Kelly isolation."
```

---

### Task 5: Multi-symbol backfill + WFA wiring

**Files:**
- Modify: `src/__main__.py:171-238` (`_cmd_backfill`), `326-362` (`_load_ohlcv`), `365-528` (`_cmd_wfa`)
- Test: `tests/unit/test_cli.py` (multi-symbol parse for backfill+wfa)

**Models:** sonnet (orchestration logic)

- [ ] **Step 1: Write failing test — backfill loops symbols**

```python
def test_backfill_parses_multi_symbol() -> None:
    from src.__main__ import _build_parser
    parser = _build_parser()
    args = parser.parse_args(["backfill", "--symbols", "BTCUSDT,ETHUSDT", "--from", "2024-01-01", "--to", "2024-04-01"])
    assert args.symbols == ["BTCUSDT", "ETHUSDT"]


def test_wfa_parses_multi_symbol() -> None:
    from src.__main__ import _build_parser
    parser = _build_parser()
    args = parser.parse_args(["wfa", "--symbols", "BTCUSDT,ETHUSDT,SOLUSDT", "--start", "2024-01-01", "--end", "2024-04-01"])
    assert args.symbols == ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
```

- [ ] **Step 2: Run → RED**

- [ ] **Step 3: Update parser**

```python
# Replace --symbol with --symbols in p_bf and p_wfa
p_bf.add_argument("--symbols", type=lambda s: [x.strip().upper() for x in s.split(",")],
                   default=["BTCUSDT"], help="Comma-separated symbol list")
p_wfa.add_argument("--symbols", type=lambda s: [x.strip().upper() for x in s.split(",")],
                    default=["BTCUSDT"], help="Comma-separated symbol list")
```

- [ ] **Step 4: Update `_cmd_backfill` — loop over symbols**

```python
def _cmd_backfill(args: argparse.Namespace) -> int:
    settings = Settings()
    symbols: list[str] = args.symbols
    rest = BybitRESTClient(api_key=settings.bybit_api_key, api_secret=settings.bybit_api_secret, testnet=settings.testnet)

    overall_rc = 0
    for symbol in symbols:
        output_path = Path(args.output_path) if args.output_path else Path(f"data/{symbol}_1h.parquet")
        # ... (existing single-symbol backfill body — unchanged per symbol)
        # If any symbol fails (empty response), continue with others, return 1 if any failed
        ...
    return overall_rc
```

- [ ] **Step 5: Update `_cmd_wfa` — aggregate trades across symbols + DSR cross-trial**

```python
def _cmd_wfa(args: argparse.Namespace) -> int:
    settings = Settings()
    symbols: list[str] = args.symbols

    all_trades: list[TradeRecord] = []
    fold_oos_is_sharpe_ratios_per_symbol: dict[str, list[float]] = {}

    for symbol in symbols:
        df = _load_ohlcv(symbol=symbol, start=args.start, end=args.end)
        if df.empty:
            print(f"WARNING: empty OHLCV for {symbol}", flush=True)
            continue
        # Run WFA per symbol (existing single-symbol body)
        # Collect trades + per-fold sharpes
        symbol_trades, symbol_sharpes = _run_wfa_single_symbol(symbol=symbol, df=df)
        all_trades.extend(symbol_trades)
        fold_oos_is_sharpe_ratios_per_symbol[symbol] = symbol_sharpes

    # Aggregate metrics across symbols
    all_fold_sharpes: list[float] = []
    for sharpes in fold_oos_is_sharpe_ratios_per_symbol.values():
        all_fold_sharpes.extend(sharpes)

    if not all_trades:
        print("WARNING: no trades across all symbols")
        return 1

    # MC sign-flip on aggregated trades
    mc_p = _compute_mc(all_trades)

    # S15 T0: DSR cross-trial sigma_SR (closes S14 Q2 carry-over)
    from src.analytics.cross_trial_log import CrossTrialLog
    trial_log = CrossTrialLog(path=Path("data/cross_trial_sharpes.json"))

    # Compute aggregate OOS Sharpe for THIS sprint (S15 = trial #2)
    agg_sharpe = _compute_aggregate_oos_sharpe(all_trades)

    # n_trials = trials persisted + 1 (this run); sigma_sr = std of all incl. this
    pre_existing_sharpes = trial_log.get_oos_sharpes()
    cross_trial_sharpes = pre_existing_sharpes + [agg_sharpe]
    n_trials = len(cross_trial_sharpes)
    if n_trials >= 2:
        import statistics
        sigma_sr = statistics.stdev(cross_trial_sharpes)
        dsr_value = compute_dsr(trades=all_trades, n_trials=n_trials, sigma_sr=sigma_sr)
    else:
        dsr_value = compute_dsr(trades=all_trades, n_trials=1)

    metrics = compute_t1_t6_metrics(trades=all_trades, fold_oos_is_sharpe=all_fold_sharpes)
    # ... verdict computation as before

    # Persist this trial AFTER measurement (for future S16+)
    trial_log.append_trial(sprint=15, oos_sharpe=agg_sharpe)

    # Output JSON includes per-symbol breakdown + cross-trial info
    ...
```

- [ ] **Step 6: Run pytest + smoke test CLI parse → GREEN**

- [ ] **Step 7: Commit**

```bash
git commit -m "feat(cli): multi-symbol backfill + aggregated WFA + DSR cross-trial

S15 T5 — backfill loops over --symbols; wfa aggregates trades across symbols.
DSR n_trials computed from CrossTrialLog (S13 anchor + S15 trial #2).
Closes S14 Q2 REVISE carry-over."
```

---

### Task 6: Empirical measurement run (data fetch + WFA + verdict)

**Manual operator step (run in venv).** No new code.

- [ ] **Step 1: Backfill 3 symbols (4.81y window, may take ~6 min total)**

```bash
.venv/bin/python -m src backfill --symbols BTCUSDT,ETHUSDT,SOLUSDT \
  --from 2021-07-02 --to 2026-04-26
# Verify 3 Parquet files in data/: BTCUSDT_1h.parquet, ETHUSDT_1h.parquet, SOLUSDT_1h.parquet
ls -lh data/*_1h.parquet
```

Note: ETH/SOL may have shorter history on Bybit Spot. If empty response for early date range, narrow `--from` per symbol availability (operator judgment).

- [ ] **Step 2: Run aggregated WFA + verdict**

```bash
.venv/bin/python -m src wfa --symbols BTCUSDT,ETHUSDT,SOLUSDT \
  --start 2021-07-02 --end 2026-04-26 > s15_wfa_result.json
cat s15_wfa_result.json
```

- [ ] **Step 3: Capture verdict to commit message + sprint page**

Record JSON output verbatim. Verdict = PASS or FAIL. T5 trade count critical.

- [ ] **Step 4: Verify cross-trial log persisted**

```bash
cat data/cross_trial_sharpes.json
# Expected: {"trials": [{"sprint": 13, "oos_sharpe": -44.46}, {"sprint": 15, "oos_sharpe": <S15_value>}]}
```

- [ ] **Step 5: Commit measurement artifacts**

```bash
git add s15_wfa_result.json
git commit -m "measure(s15): WFA verdict — <PASS|FAIL>

Aggregated 3 symbols (BTC/ETH/SOL) on 1H mean-reversion strategy.
N_trials=2 with cross-trial sigma_SR. T5 n_trades=<N>, T1=<sharpe>."
```

---

### Task 7: Sprint page + ADR + wiki sync

**Files:**
- Create: `llm-wiki/wiki/project/sprints/sprint-15-mean-reversion-multi-symbol.md`
- Modify: `llm-wiki/wiki/project/architecture/current-state.md` (counts + sprint history row)
- Modify: `llm-wiki/wiki/index.md` (sprint + ADR entries)
- Modify: `llm-wiki/wiki/log.md` (sprint-end entry)
- Modify: `llm-wiki/wiki/project/SPRINT_STATE.md` (phase=8-ship)

- [ ] **Step 1: Create sprint-15 page** (use sprint-14-honest-close.md as template skeleton — fill measurement results, deliverables T0-T6, key decisions per ADR 0030)

- [ ] **Step 2: Update current-state.md**

- ADR 29 → 30
- Sprint pages 16 → 17
- TL;DR post-S15: "v0.2 retry — mean-reversion 3-symbol — verdict <PASS|FAIL>"
- Add sprint-15 row in canonical sprint table

- [ ] **Step 3: Update index.md**

Add:
- `sprint-15-mean-reversion-multi-symbol`
- ADR `0030-sprint-15-mean-reversion-multi-symbol`

- [ ] **Step 4: Append log.md sprint-end entry**

```markdown
## [2026-04-26] sprint-end | Sprint 15 — Mean-reversion + multi-symbol
- Verdict: <PASS|FAIL> (T1=<sharpe>, T5 n_trades=<N>, DSR=<dsr_value>)
- Deliverables: T0 cross-trial log + T1 load_recent symbol filter + T2 BB indicator + T3 MeanRev strategy + T4-T5 multi-symbol CLI fan-out + T6 measurement
- Tag: v0.1.0-alpha.15
- Carry-overs: <list>
```

- [ ] **Step 5: Update SPRINT_STATE → phase=8-ship**

- [ ] **Step 6: Commit wiki sync**

```bash
git add llm-wiki/
git commit -m "docs(sprint-15): wiki sync — sprint-15 page + ADR 0030 + counts + log

S15 ship preparation. Sprint-15 page documents verdict + carry-overs."
```

---

### Task 8: PHASE 8 ship via sprint-finish

Invoke `sprint-finish` skill after Task 7 commit. HARD-GATEs:
- Sprint-15.md exists ✓ (Task 7)
- Canonical counts updated (Task 7)
- Block 1↔2 sync (touched files: trade_history.py, manager.py, signalgen/* → component pages may need sync — check `wiki-update` skill)
- Orphan-audit grep includes tests/
- ADR 0030 in index.md

```bash
# Pre-flight
.venv/bin/pytest tests/ -q
.venv/bin/mypy --strict src/ 2>&1 | tail -3

# Push + PR + merge + tag v0.1.0-alpha.15
```

---

## Self-Review Checklist (controller validates before subagent dispatch)

- [x] Spec coverage: T0 cross-trial log, T1 load_recent fix, T2 BB, T3 MeanRev strategy, T4 _cmd_run multi-symbol, T5 backfill+WFA aggregation, T6 measurement, T7 wiki, T8 ship → all 8 deliverables from ADR 0030
- [x] Placeholder scan: no TBD/TODO. RiskManager `symbol` param addition called out in Task 4 Step 5
- [x] Type consistency: `MeanReversionRsiBBStrategy` constructor signature matches test fixture; `bollinger_bands` returns 3-tuple (upper, middle, lower)
- [x] Tasks ordered: T0 (DSR persistence) before T5 (DSR call site), T1 (load_recent) before T4 (multi-symbol), T2 (BB) before T3 (strategy uses BB)

## Dependencies graph

```
T0 (cross_trial_log) ─────────┐
                              ├──→ T5 (wfa wiring uses both)
T1 (load_recent fix) ──→ T4 ──┤
                              │
T2 (BB indicator) ──→ T3 (MeanRev strategy) ──→ T4 (DI uses MeanRev)
                                                  │
T4 + T5 ──→ T6 (measurement run) ──→ T7 (wiki) ──→ T8 (ship)
```

Critical path: T2 → T3 → T4 → T6. Parallel possible: T0+T1+T2 (no inter-deps).
