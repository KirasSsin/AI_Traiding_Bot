---
title: Sprint 3 — Strategy port (EMA-crossover + ADX + RSI + ATR via TA-Lib)
type: plan
tags: [plan, sprint-3, strategy, indicators, ta-lib, tdd]
created: 2026-04-22
updated: 2026-04-22
status: ready-to-execute
sources:
  - project/architecture/migration-plan.md §S3
  - project/decisions/0011-wilder-ema-for-adx-rsi-classical-for-crossover.md
  - trading/strategies/ema-crossover-adx-rsi.md
  - trading/indicators/{ema,adx,rsi,atr}.md
  - project/architecture/execution-timing.md
---

# Sprint 3 — Strategy Port Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** портировать стратегию EMA(12)×EMA(26) classical + ADX(14)/RSI(14)/ATR(14) Wilder через TA-Lib, реализовать `on_bar(Bar) -> Signal | None` с enforced look-ahead-free invariants.

**Architecture:** чистый DDD signalgen context — `indicators.py` (stateless функции-обёртки над TA-Lib) + `strategy.py` (stateful класс с rolling buffer и on_bar контрактом). Strategy читает уже-готовый `Bar` (из `MarketData` S2), эмитит pydantic `Signal` (из S1 models). Zero I/O в стратегии.

**Tech Stack:** Python 3.12, TA-Lib 0.4.28+ (native + Python binding), pydantic v2, numpy 1.26+, pytest 8.0+, hypothesis 6.98+.

---

## Scope

### In scope (AC from migration-plan §S3)

- TA-Lib indicator wrappers: `ema(close, n, mode)`, `adx(h, l, c, n)`, `plus_di/minus_di(h, l, c, n)`, `rsi(close, n)`, `atr(h, l, c, n)`.
- `EmaCrossoverAdxRsiStrategy.on_bar(bar) -> Signal | None` контракт.
- Signal несёт `bar_close_time` (look-ahead invariant через pydantic-валидатор S1).
- Entry/exit rules из `trading/strategies/ema-crossover-adx-rsi.md`.
- Duplicate-bar guard (`REJECT_DUPLICATE_SIGNAL` reason).

### Out of scope (explicit)

- **Position sizing** (`qty = f·equity/(1.5·ATR)`) — S4.
- **OCO bracket** (SL/TP placement) — S5.
- **Kelly-фазы / Risk Manager** — S4.
- **Backtest harness** (walk-forward, golden-output CI) — S7. *Но golden-output unit-test на 200 баров делаем уже здесь per AC.*
- **Event Bus integration** — S6.

### Prerequisites

- Python 3.12 venv активен (из Sprint 1).
- `make check` green на `origin/main` (Sprint 2 tag `v0.1.0-alpha.2`).
- **TA-Lib native installed:** `brew install ta-lib` (macOS) или `apt-get install libta-lib0-dev` (Linux).
- TA-Lib Python binding: `pip install TA-Lib` (устанавливается как часть Task 1).

---

## File Structure

### Created

```
src/signalgen/
├── indicators.py       # TA-Lib wrappers — pure functions, numpy in/out
└── strategy.py         # EmaCrossoverAdxRsiStrategy — on_bar contract

tests/unit/
├── test_indicators.py  # golden-value tests per индикатор (6 групп)
└── test_strategy.py    # on_bar scenarios (warm-up, LONG, filter rejects, flip, duplicates)

tests/property/
├── __init__.py
└── test_lookahead.py   # hypothesis property: signal_ts ≥ bar_close_time

llm-wiki/wiki/project/components/
├── indicators.md       # component docs
└── strategy.md         # component docs

llm-wiki/wiki/project/sprints/
└── sprint-03-strategy-port.md   # delivery record
```

### Modified

- `pyproject.toml` — добавить `TA-Lib>=0.4.28` в `dependencies`; `[[tool.mypy.overrides]]` для `talib` stub-missing.
- `src/platform/config.py` — добавить strategy params в `Settings` (см. Task 8).
- `llm-wiki/wiki/index.md` — добавить новые component pages + sprint page + plan page.
- `llm-wiki/wiki/log.md` — append `[2026-04-22] ingest | Sprint 3 completed`.

### Removed

- `src/strategy/` — empty legacy directory (только `__init__.py` осталось от S1 cleanup).

---

## Tasks

### Task 1: TA-Lib dependency + mypy override

**Files:**
- Modify: `pyproject.toml`
- Test: `tests/unit/test_deps.py` (extend existing)

- [ ] **Step 1: Пользователь уже установил `brew install ta-lib` и `pip install TA-Lib` в worktree venv.** Проверка:

```bash
python -c "import talib; print(talib.__version__)"
```
Expected: `0.4.28` (or higher).

- [ ] **Step 2: Extend `tests/unit/test_deps.py` с RED test**

Add to existing file:

```python
def test_talib_importable() -> None:
    """TA-Lib native + Python binding должны быть доступны для indicators."""
    import talib
    assert hasattr(talib, "EMA")
    assert hasattr(talib, "ADX")
    assert hasattr(talib, "RSI")
    assert hasattr(talib, "ATR")
    assert hasattr(talib, "PLUS_DI")
    assert hasattr(talib, "MINUS_DI")
```

- [ ] **Step 3: Run test (should fail if talib missing)**

```bash
pytest tests/unit/test_deps.py::test_talib_importable -v
```
Expected: PASS (если Prereq выполнен) или FAIL `ModuleNotFoundError` (блокер — пользователь не установил).

- [ ] **Step 4: Update `pyproject.toml`**

В `[project]` → `dependencies` добавить строку:

```toml
  "TA-Lib>=0.4.28",
```

В `[[tool.mypy.overrides]]` блок с pybit — добавить `talib` в тот же список:

```toml
[[tool.mypy.overrides]]
module = ["pybit.*", "pyarrow.*", "talib"]
ignore_missing_imports = true
```

- [ ] **Step 5: Verify `make check` green**

```bash
make check
```
Expected: ruff clean, mypy --strict clean, pytest 64/64 passed (63 + new deps test).

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml tests/unit/test_deps.py
git commit -m "chore(deps): add TA-Lib 0.4.28 for indicator wrappers

Source: wiki/project/architecture/migration-plan.md §S3."
```

---

### Task 2: Indicators module — classical EMA wrapper

**Files:**
- Create: `src/signalgen/indicators.py`
- Test: `tests/unit/test_indicators.py`

- [ ] **Step 1: RED — create test file with EMA test**

Create `tests/unit/test_indicators.py`:

```python
"""Unit tests for signalgen.indicators — goldens vs TA-Lib + manual formulas."""

import numpy as np
import pytest

from src.signalgen.indicators import ema


def test_ema_classical_matches_talib_formula() -> None:
    """EMA(n) classical: α = 2/(n+1); seed via SMA первых n баров."""
    close = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0,
                      11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0, 20.0])
    result = ema(close, period=5, mode="classical")

    # Первые 4 значения — NaN (warm-up)
    assert np.all(np.isnan(result[:4]))

    # EMA[4] = SMA(close[0..4]) = 3.0
    assert result[4] == pytest.approx(3.0, abs=1e-12)

    # α = 2/(5+1) = 1/3; EMA[5] = α·close[5] + (1-α)·EMA[4]
    #                         = (1/3)·6 + (2/3)·3 = 4.0
    assert result[5] == pytest.approx(4.0, abs=1e-12)

    # EMA[6] = (1/3)·7 + (2/3)·4 = 5.0
    assert result[6] == pytest.approx(5.0, abs=1e-12)
```

- [ ] **Step 2: Run test — verify RED**

```bash
pytest tests/unit/test_indicators.py::test_ema_classical_matches_talib_formula -v
```
Expected: FAIL с `ModuleNotFoundError: No module named 'src.signalgen.indicators'`.

- [ ] **Step 3: GREEN — create `src/signalgen/indicators.py`**

```python
"""TA-Lib indicator wrappers — stateless, numpy in/out.

ADR 0011: Wilder smoothing for ADX/RSI/ATR; Classical EMA for crossovers.
"""

from typing import Literal

import numpy as np
import talib

EmaMode = Literal["classical", "wilder"]


def ema(close: np.ndarray, period: int, mode: EmaMode = "classical") -> np.ndarray:
    """Exponential Moving Average.

    Args:
        close: 1-D float array of close prices.
        period: smoothing period (n ≥ 2).
        mode: "classical" → α=2/(n+1); "wilder" → α=1/n.

    Returns:
        1-D float array same length as `close`; первые (period-1) значений = NaN.

    Notes:
        TA-Lib `EMA` использует classical formula с SMA-seed (per ADR 0011).
        Для Wilder — используем `ta_lib.SMA` seed + рекуррентный пересчёт с α=1/n.
    """
    if period < 2:
        raise ValueError(f"period must be >= 2, got {period}")
    if close.ndim != 1:
        raise ValueError("close must be 1-D")
    if mode == "classical":
        return talib.EMA(close, timeperiod=period)
    # Wilder: α = 1/n; seed = SMA(close[0..n-1]); но EMA classical через TA-Lib
    # не даёт Wilder. Реализуем напрямую.
    raise NotImplementedError(f"mode={mode} implemented in Task 3")
```

- [ ] **Step 4: Run test — verify GREEN**

```bash
pytest tests/unit/test_indicators.py::test_ema_classical_matches_talib_formula -v
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/signalgen/indicators.py tests/unit/test_indicators.py
git commit -m "feat(signalgen): add EMA classical wrapper via TA-Lib

Classical EMA α=2/(n+1) per ADR 0011. Goldens match formula 1e-12.
Wilder mode follows in subsequent task."
```

---

### Task 3: Indicators module — Wilder EMA helper

**Files:**
- Modify: `src/signalgen/indicators.py`
- Modify: `tests/unit/test_indicators.py`

- [ ] **Step 1: RED — add Wilder EMA test**

Append to `tests/unit/test_indicators.py`:

```python
def test_ema_wilder_matches_manual_recurrence() -> None:
    """EMA(n) Wilder: α=1/n; seed = SMA первых n; recurrence на всех t ≥ n."""
    close = np.arange(1.0, 21.0)  # 1..20

    result = ema(close, period=5, mode="wilder")

    # Warm-up: первые 4 значения NaN
    assert np.all(np.isnan(result[:4]))

    # Wilder seed: SMA(1..5) = 3.0
    assert result[4] == pytest.approx(3.0, abs=1e-12)

    # α = 1/5 = 0.2
    # EMA[5] = 0.2·6 + 0.8·3 = 1.2 + 2.4 = 3.6
    assert result[5] == pytest.approx(3.6, abs=1e-12)
    # EMA[6] = 0.2·7 + 0.8·3.6 = 1.4 + 2.88 = 4.28
    assert result[6] == pytest.approx(4.28, abs=1e-12)


def test_ema_rejects_bad_inputs() -> None:
    close = np.arange(1.0, 11.0)
    with pytest.raises(ValueError, match="period must be >= 2"):
        ema(close, period=1)
    with pytest.raises(ValueError, match="1-D"):
        ema(close.reshape(2, 5), period=3)
```

- [ ] **Step 2: Run tests — verify RED**

Expected: `test_ema_wilder_matches_manual_recurrence` FAIL с `NotImplementedError`; `test_ema_rejects_bad_inputs` PASS (уже работает).

- [ ] **Step 3: GREEN — implement Wilder mode**

Replace `raise NotImplementedError(...)` block in `indicators.py`:

```python
    # Wilder: α = 1/period; seed = SMA(close[0..period-1]); recurrence на t ≥ period.
    result = np.full_like(close, np.nan, dtype=np.float64)
    if len(close) < period:
        return result
    seed = np.mean(close[:period])
    result[period - 1] = seed
    alpha = 1.0 / period
    for t in range(period, len(close)):
        result[t] = alpha * close[t] + (1.0 - alpha) * result[t - 1]
    return result
```

- [ ] **Step 4: Run all tests**

```bash
pytest tests/unit/test_indicators.py -v
```
Expected: 3/3 passed.

- [ ] **Step 5: Commit**

```bash
git add src/signalgen/indicators.py tests/unit/test_indicators.py
git commit -m "feat(signalgen): add Wilder EMA mode to indicators.ema

Wilder α=1/n с SMA-seed первых n баров per ADR 0011.
Used internally by ADX/RSI/ATR which require Wilder convention."
```

---

### Task 4: Indicators module — RSI (Wilder)

**Files:**
- Modify: `src/signalgen/indicators.py`
- Modify: `tests/unit/test_indicators.py`

- [ ] **Step 1: RED — RSI test against TA-Lib golden**

Append to `tests/unit/test_indicators.py`:

```python
def test_rsi_wilder_matches_talib() -> None:
    """RSI(14) Wilder: сверяем с прямым вызовом talib.RSI (который использует Wilder)."""
    import talib
    rng = np.random.default_rng(42)
    close = 100 + np.cumsum(rng.standard_normal(100))

    from src.signalgen.indicators import rsi
    result = rsi(close, period=14)
    expected = talib.RSI(close, timeperiod=14)

    # Warm-up: первые 14 NaN
    assert np.all(np.isnan(result[:14]))

    np.testing.assert_allclose(result[14:], expected[14:], rtol=1e-9)


def test_rsi_extremes() -> None:
    """RSI=100 при монотонном росте, RSI=0 при монотонном падении."""
    from src.signalgen.indicators import rsi
    up = np.arange(1.0, 30.0)
    result = rsi(up, period=14)
    assert result[-1] == pytest.approx(100.0, abs=1e-6)

    down = np.arange(30.0, 1.0, -1.0)
    result = rsi(down, period=14)
    assert result[-1] == pytest.approx(0.0, abs=1e-6)
```

- [ ] **Step 2: Run test — verify RED**

Expected: FAIL — `rsi` не существует.

- [ ] **Step 3: GREEN — add rsi wrapper**

Append to `src/signalgen/indicators.py`:

```python
def rsi(close: np.ndarray, period: int = 14) -> np.ndarray:
    """Relative Strength Index (Wilder 1978).

    TA-Lib `RSI` использует Wilder smoothing по умолчанию (α=1/n) per ADR 0011.

    Args:
        close: 1-D float array of close prices.
        period: period (default 14 per Wilder).

    Returns:
        Array same length as `close`, первые `period` значений — NaN.
        Диапазон [0, 100].
    """
    if period < 2:
        raise ValueError(f"period must be >= 2, got {period}")
    if close.ndim != 1:
        raise ValueError("close must be 1-D")
    return talib.RSI(close, timeperiod=period)
```

- [ ] **Step 4: Run tests — verify GREEN**

```bash
pytest tests/unit/test_indicators.py -v
```
Expected: 5/5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/signalgen/indicators.py tests/unit/test_indicators.py
git commit -m "feat(signalgen): add RSI(14) Wilder wrapper

talib.RSI использует Wilder smoothing (α=1/n) per ADR 0011.
Golden tests: RSI→100 при monotone up, RSI→0 при monotone down."
```

---

### Task 5: Indicators module — ATR (Wilder)

**Files:**
- Modify: `src/signalgen/indicators.py`
- Modify: `tests/unit/test_indicators.py`

- [ ] **Step 1: RED — ATR test**

Append to `tests/unit/test_indicators.py`:

```python
def test_atr_wilder_matches_talib() -> None:
    import talib
    rng = np.random.default_rng(7)
    n = 80
    close = 100 + np.cumsum(rng.standard_normal(n))
    high = close + rng.uniform(0.1, 1.0, n)
    low = close - rng.uniform(0.1, 1.0, n)

    from src.signalgen.indicators import atr
    result = atr(high, low, close, period=14)
    expected = talib.ATR(high, low, close, timeperiod=14)

    assert np.all(np.isnan(result[:14]))
    np.testing.assert_allclose(result[14:], expected[14:], rtol=1e-9)


def test_atr_positive() -> None:
    """ATR всегда >= 0 (true range неотрицателен)."""
    from src.signalgen.indicators import atr
    high = np.linspace(100, 110, 30)
    low = np.linspace(99, 109, 30)
    close = np.linspace(99.5, 109.5, 30)
    result = atr(high, low, close, period=14)
    assert np.all(result[~np.isnan(result)] >= 0)
```

- [ ] **Step 2: Run test — verify RED**

Expected: FAIL.

- [ ] **Step 3: GREEN — add atr wrapper**

Append to `src/signalgen/indicators.py`:

```python
def atr(
    high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14
) -> np.ndarray:
    """Average True Range (Wilder 1978).

    TR = max(high-low, |high-prev_close|, |low-prev_close|).
    ATR[t] = Wilder-smooth(TR, period) per ADR 0011.

    Args:
        high, low, close: 1-D arrays same length.
        period: period (default 14).

    Returns:
        Array same length as inputs, первые `period` значений = NaN. Всегда >= 0.
    """
    if not (high.shape == low.shape == close.shape) or high.ndim != 1:
        raise ValueError("high, low, close must be 1-D and same shape")
    if period < 2:
        raise ValueError(f"period must be >= 2, got {period}")
    return talib.ATR(high, low, close, timeperiod=period)
```

- [ ] **Step 4: Run tests — verify GREEN**

```bash
pytest tests/unit/test_indicators.py -v
```
Expected: 7/7 passed.

- [ ] **Step 5: Commit**

```bash
git add src/signalgen/indicators.py tests/unit/test_indicators.py
git commit -m "feat(signalgen): add ATR(14) Wilder wrapper

talib.ATR использует Wilder smoothing (α=1/n) per ADR 0011.
Invariant: ATR >= 0 для всех not-NaN значений."
```

---

### Task 6: Indicators module — ADX + ±DI (Wilder)

**Files:**
- Modify: `src/signalgen/indicators.py`
- Modify: `tests/unit/test_indicators.py`

- [ ] **Step 1: RED — ADX/DI tests**

Append to `tests/unit/test_indicators.py`:

```python
def test_adx_plus_di_minus_di_match_talib() -> None:
    import talib
    rng = np.random.default_rng(11)
    n = 80
    close = 100 + np.cumsum(rng.standard_normal(n))
    high = close + rng.uniform(0.1, 1.0, n)
    low = close - rng.uniform(0.1, 1.0, n)

    from src.signalgen.indicators import adx, minus_di, plus_di

    adx_actual = adx(high, low, close, period=14)
    pdi_actual = plus_di(high, low, close, period=14)
    mdi_actual = minus_di(high, low, close, period=14)

    np.testing.assert_allclose(
        adx_actual[~np.isnan(adx_actual)],
        talib.ADX(high, low, close, timeperiod=14)[~np.isnan(adx_actual)],
        rtol=1e-9,
    )
    np.testing.assert_allclose(
        pdi_actual[~np.isnan(pdi_actual)],
        talib.PLUS_DI(high, low, close, timeperiod=14)[~np.isnan(pdi_actual)],
        rtol=1e-9,
    )
    np.testing.assert_allclose(
        mdi_actual[~np.isnan(mdi_actual)],
        talib.MINUS_DI(high, low, close, timeperiod=14)[~np.isnan(mdi_actual)],
        rtol=1e-9,
    )


def test_adx_bounds_0_100() -> None:
    """ADX ∈ [0, 100] per Wilder 1978."""
    from src.signalgen.indicators import adx
    rng = np.random.default_rng(5)
    n = 60
    close = 100 + np.cumsum(rng.standard_normal(n))
    high = close + 1.0
    low = close - 1.0
    result = adx(high, low, close, period=14)
    non_nan = result[~np.isnan(result)]
    assert np.all((non_nan >= 0) & (non_nan <= 100))
```

- [ ] **Step 2: Run test — verify RED**

Expected: FAIL — `adx`, `plus_di`, `minus_di` отсутствуют.

- [ ] **Step 3: GREEN — add adx/plus_di/minus_di wrappers**

Append to `src/signalgen/indicators.py`:

```python
def adx(
    high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14
) -> np.ndarray:
    """Average Directional Index (Wilder 1978).

    ADX = Wilder-smooth(DX, period); DX = 100 · |+DI - -DI| / (+DI + -DI).
    Range [0, 100]; >25 → trending.

    Returns:
        1-D array; warm-up ≈ 2·period - 1 баров NaN (double-smoothing).
    """
    _validate_hlc(high, low, close, period)
    return talib.ADX(high, low, close, timeperiod=period)


def plus_di(
    high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14
) -> np.ndarray:
    """+DI per Wilder 1978. Range [0, 100]."""
    _validate_hlc(high, low, close, period)
    return talib.PLUS_DI(high, low, close, timeperiod=period)


def minus_di(
    high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14
) -> np.ndarray:
    """-DI per Wilder 1978. Range [0, 100]."""
    _validate_hlc(high, low, close, period)
    return talib.MINUS_DI(high, low, close, timeperiod=period)


def _validate_hlc(
    high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int
) -> None:
    if not (high.shape == low.shape == close.shape) or high.ndim != 1:
        raise ValueError("high, low, close must be 1-D and same shape")
    if period < 2:
        raise ValueError(f"period must be >= 2, got {period}")
```

Также рефакторинг `atr()` — заменить 3-строковую валидацию на вызов `_validate_hlc(high, low, close, period)`.

- [ ] **Step 4: Run all tests**

```bash
pytest tests/unit/test_indicators.py -v
```
Expected: 9/9 passed.

- [ ] **Step 5: Commit**

```bash
git add src/signalgen/indicators.py tests/unit/test_indicators.py
git commit -m "feat(signalgen): add ADX + ±DI Wilder wrappers

talib.ADX/PLUS_DI/MINUS_DI используют Wilder smoothing per ADR 0011.
Shared _validate_hlc helper для DRY."
```

---

### Task 7: Settings — strategy parameters

**Files:**
- Modify: `src/platform/config.py`
- Modify: `tests/unit/test_config.py`

- [ ] **Step 1: RED — test for strategy params in Settings**

Add to `tests/unit/test_config.py`:

```python
def test_settings_strategy_params_defaults() -> None:
    """Strategy params из trading/strategies/ema-crossover-adx-rsi.md v0.1 defaults."""
    from src.platform.config import Settings
    s = Settings(
        bybit_api_key="x", bybit_api_secret="y",
        bybit_testnet=True, trading_enabled=False, live_trading=False,
    )
    assert s.strategy_ema_fast == 12
    assert s.strategy_ema_slow == 26
    assert s.strategy_adx_period == 14
    assert s.strategy_adx_threshold == 25
    assert s.strategy_rsi_period == 14
    assert s.strategy_rsi_oversold == 30
    assert s.strategy_rsi_overbought == 70
    assert s.strategy_atr_period == 14
```

- [ ] **Step 2: Run test — verify RED**

Expected: FAIL — атрибуты отсутствуют.

- [ ] **Step 3: GREEN — extend Settings**

Modify `src/platform/config.py` — add fields under existing Settings class (exact placement: after `live_trading` field):

```python
    # Strategy parameters (v0.1 defaults — см. trading/strategies/ema-crossover-adx-rsi.md)
    strategy_ema_fast: int = 12
    strategy_ema_slow: int = 26
    strategy_adx_period: int = 14
    strategy_adx_threshold: Decimal = Decimal("25")
    strategy_rsi_period: int = 14
    strategy_rsi_oversold: Decimal = Decimal("30")
    strategy_rsi_overbought: Decimal = Decimal("70")
    strategy_atr_period: int = 14
```

Ensure `from decimal import Decimal` есть в импортах.

- [ ] **Step 4: Run tests**

```bash
pytest tests/unit/test_config.py -v
```
Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add src/platform/config.py tests/unit/test_config.py
git commit -m "feat(config): add strategy parameters (EMA/ADX/RSI/ATR) to Settings

Defaults из wiki trading/strategies/ema-crossover-adx-rsi.md.
Все — env-overridable через BYBIT_ prefix не нужен — strategy_* не-secret."
```

---

### Task 8: Strategy class — skeleton + warm-up

**Files:**
- Create: `src/signalgen/strategy.py`
- Create: `tests/unit/test_strategy.py`

- [ ] **Step 1: RED — warm-up test (< 26 bars → None)**

Create `tests/unit/test_strategy.py`:

```python
"""Unit tests for signalgen.strategy — on_bar contract scenarios."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from src.marketdata.models import Bar, DataQuality
from src.signalgen.strategy import EmaCrossoverAdxRsiStrategy


def _bar(close: float, idx: int, symbol: str = "BTCUSDT") -> Bar:
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    ot = t0 + timedelta(hours=idx)
    ct = ot + timedelta(hours=1) - timedelta(microseconds=1)
    return Bar(
        symbol=symbol,
        interval="1h",
        open_time=ot,
        close_time=ct,
        open=Decimal(str(close)),
        high=Decimal(str(close + 0.5)),
        low=Decimal(str(close - 0.5)),
        close=Decimal(str(close)),
        volume=Decimal("1.0"),
        trade_count=1,
        is_closed=True,
        data_quality=DataQuality.OK,
    )


def test_strategy_returns_none_during_warmup() -> None:
    """Стратегия требует >= slow_ema + ADX double-smoothing баров для первого сигнала.

    Минимум: max(ema_slow=26, adx_period=14 + ema_slow=26-смешано) — практически 2·slow ≈ 52.
    На первых 30 закрытых барах сигнал = None (не хватает истории).
    """
    strat = EmaCrossoverAdxRsiStrategy(
        ema_fast=12, ema_slow=26,
        adx_period=14, adx_threshold=Decimal("25"),
        rsi_period=14, rsi_overbought=Decimal("70"), rsi_oversold=Decimal("30"),
        atr_period=14, symbol="BTCUSDT",
    )
    for i in range(30):
        result = strat.on_bar(_bar(100.0 + i * 0.1, i))
        assert result is None, f"bar {i}: ожидался warm-up None, получили {result}"


def test_strategy_skips_non_closed_bars() -> None:
    """is_closed=False баров стратегия игнорирует (execution-timing invariant)."""
    strat = EmaCrossoverAdxRsiStrategy(
        ema_fast=12, ema_slow=26,
        adx_period=14, adx_threshold=Decimal("25"),
        rsi_period=14, rsi_overbought=Decimal("70"), rsi_oversold=Decimal("30"),
        atr_period=14, symbol="BTCUSDT",
    )
    live_bar = _bar(100.0, 0).model_copy(update={"is_closed": False})
    assert strat.on_bar(live_bar) is None
    # Internal buffer НЕ должен был ничего добавить:
    assert len(strat._bars) == 0  # type: ignore[attr-defined]
```

- [ ] **Step 2: Run tests — verify RED**

Expected: FAIL — `src.signalgen.strategy` не существует.

- [ ] **Step 3: GREEN — skeleton**

Create `src/signalgen/strategy.py`:

```python
"""EMA-crossover + ADX/RSI/ATR trading strategy (v0.1).

Reference: wiki/trading/strategies/ema-crossover-adx-rsi.md.
ADR: wiki/project/decisions/0011-wilder-ema-for-adx-rsi-classical-for-crossover.md.
Invariant: signal on close(T) → execution at open(T+1)
  (wiki/project/architecture/execution-timing.md).
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import numpy as np

from src.marketdata.models import Bar
from src.signalgen.indicators import adx, atr, ema, minus_di, plus_di, rsi
from src.signalgen.models import Signal, SignalSide


class EmaCrossoverAdxRsiStrategy:
    """Stateful strategy: feed closed bars one-by-one, получай Signal | None.

    Internal state: rolling buffer последних N bars (N = max indicator warm-up + 1).
    Emission rule: emit сигнал **только** на bar с is_closed=True и when all gates pass.

    Thread-safety: **not thread-safe.** Один инстанс — один producer thread (MarketData pipeline).
    """

    def __init__(
        self,
        *,
        symbol: str,
        ema_fast: int,
        ema_slow: int,
        adx_period: int,
        adx_threshold: Decimal,
        rsi_period: int,
        rsi_oversold: Decimal,
        rsi_overbought: Decimal,
        atr_period: int,
    ) -> None:
        if ema_fast >= ema_slow:
            raise ValueError("ema_fast must be < ema_slow")
        self._symbol = symbol
        self._ema_fast_n = ema_fast
        self._ema_slow_n = ema_slow
        self._adx_n = adx_period
        self._adx_threshold = adx_threshold
        self._rsi_n = rsi_period
        self._rsi_oversold = rsi_oversold
        self._rsi_overbought = rsi_overbought
        self._atr_n = atr_period

        # Buffer size: нужно >= slow + 2·adx_period для ADX double-smoothing.
        self._buffer_size = max(ema_slow, 2 * adx_period, atr_period, rsi_period) + 5
        self._bars: list[Bar] = []
        self._last_signal_close_time: datetime | None = None
        self._current_side: SignalSide = SignalSide.FLAT

    def on_bar(self, bar: Bar) -> Signal | None:
        """Main entry point. Called once per closed bar by MarketData pipeline."""
        if not bar.is_closed:
            return None
        if bar.symbol != self._symbol:
            return None

        self._bars.append(bar)
        if len(self._bars) > self._buffer_size:
            self._bars = self._bars[-self._buffer_size:]

        # Warm-up: нужно минимум max(ema_slow, 2·adx_period) закрытых баров.
        min_required = max(self._ema_slow_n, 2 * self._adx_n) + 1
        if len(self._bars) < min_required:
            return None

        # Indicator computation — placeholder, реальная логика в Task 9+.
        return None
```

- [ ] **Step 4: Run tests — verify GREEN**

```bash
pytest tests/unit/test_strategy.py -v
```
Expected: 2/2 passed.

- [ ] **Step 5: Commit**

```bash
git add src/signalgen/strategy.py tests/unit/test_strategy.py
git commit -m "feat(signalgen): strategy skeleton with warm-up + non-closed bar skip

Stateful on_bar(bar) contract; buffer size = max warm-up + 5.
Entry/exit logic в subsequent tasks."
```

---

### Task 9: Strategy — LONG entry happy path

**Files:**
- Modify: `src/signalgen/strategy.py`
- Modify: `tests/unit/test_strategy.py`

- [ ] **Step 1: RED — test LONG entry when all gates pass**

Add to `tests/unit/test_strategy.py`:

```python
def _crafted_bars_for_long_entry() -> list[Bar]:
    """Crafted series: 60 баров нисходящих + 10 восходящих → EMA cross-up на предпоследнем.
    Объём последних 10 достаточно большой чтобы ADX > 25, RSI < 70.
    """
    from datetime import UTC, datetime, timedelta
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    out: list[Bar] = []
    price = 100.0
    # 60 баров downward drift
    for i in range(60):
        price -= 0.2
        ot = t0 + timedelta(hours=i)
        ct = ot + timedelta(hours=1) - timedelta(microseconds=1)
        out.append(Bar(
            symbol="BTCUSDT", interval="1h",
            open_time=ot, close_time=ct,
            open=Decimal(str(price + 0.1)),
            high=Decimal(str(price + 0.3)),
            low=Decimal(str(price - 0.3)),
            close=Decimal(str(price)),
            volume=Decimal("1.0"), trade_count=1,
            is_closed=True, data_quality=DataQuality.OK,
        ))
    # 20 баров strong rally
    for i in range(60, 80):
        price += 1.5
        ot = t0 + timedelta(hours=i)
        ct = ot + timedelta(hours=1) - timedelta(microseconds=1)
        out.append(Bar(
            symbol="BTCUSDT", interval="1h",
            open_time=ot, close_time=ct,
            open=Decimal(str(price - 0.5)),
            high=Decimal(str(price + 0.8)),
            low=Decimal(str(price - 0.8)),
            close=Decimal(str(price)),
            volume=Decimal("1.0"), trade_count=1,
            is_closed=True, data_quality=DataQuality.OK,
        ))
    return out


def test_strategy_emits_long_on_cross_with_gates() -> None:
    """После downtrend→uptrend EMA12 crosses EMA26 up, ADX>25, +DI>-DI, RSI<70 → LONG."""
    strat = EmaCrossoverAdxRsiStrategy(
        ema_fast=12, ema_slow=26,
        adx_period=14, adx_threshold=Decimal("25"),
        rsi_period=14, rsi_overbought=Decimal("70"), rsi_oversold=Decimal("30"),
        atr_period=14, symbol="BTCUSDT",
    )
    bars = _crafted_bars_for_long_entry()
    signals: list[Signal] = []
    for b in bars:
        sig = strat.on_bar(b)
        if sig is not None:
            signals.append(sig)

    longs = [s for s in signals if s.side == SignalSide.LONG]
    assert len(longs) >= 1, f"Ожидался хотя бы один LONG, получили {signals!r}"
    s = longs[0]
    assert s.symbol == "BTCUSDT"
    assert s.adx_14 > Decimal("25")
    assert s.rsi_14 < Decimal("70")
    assert s.plus_di_14 > s.minus_di_14
    assert s.ema_fast > s.ema_slow
    assert s.atr_14 > 0
    assert s.generated_at >= s.bar_close_time  # look-ahead invariant
```

Add `from src.signalgen.models import Signal, SignalSide` to imports at top of test file if not present.

- [ ] **Step 2: Run test — verify RED**

Expected: FAIL — strategy always returns None.

- [ ] **Step 3: GREEN — implement indicator computation + entry rule**

Replace stub `# Indicator computation — placeholder...` block в `strategy.py` с:

```python
        # Compute indicators on full buffer (simple — всё пересчитываем).
        closes = np.array([float(b.close) for b in self._bars], dtype=np.float64)
        highs = np.array([float(b.high) for b in self._bars], dtype=np.float64)
        lows = np.array([float(b.low) for b in self._bars], dtype=np.float64)

        ema_fast_arr = ema(closes, self._ema_fast_n, mode="classical")
        ema_slow_arr = ema(closes, self._ema_slow_n, mode="classical")
        adx_arr = adx(highs, lows, closes, self._adx_n)
        pdi_arr = plus_di(highs, lows, closes, self._adx_n)
        mdi_arr = minus_di(highs, lows, closes, self._adx_n)
        rsi_arr = rsi(closes, self._rsi_n)
        atr_arr = atr(highs, lows, closes, self._atr_n)

        # Любой NaN в последнем значении → warm-up не завершён.
        snapshot = {
            "ema_fast": ema_fast_arr[-1], "ema_slow": ema_slow_arr[-1],
            "adx": adx_arr[-1], "plus_di": pdi_arr[-1], "minus_di": mdi_arr[-1],
            "rsi": rsi_arr[-1], "atr": atr_arr[-1],
        }
        if any(np.isnan(v) for v in snapshot.values()):
            return None

        # Entry rule (LONG): cross up EMA12×EMA26 at -1→0, ADX>threshold,
        # +DI>-DI, RSI<overbought. Cross = fast[T] > slow[T] AND fast[T-1] <= slow[T-1].
        cross_up = (
            ema_fast_arr[-1] > ema_slow_arr[-1]
            and ema_fast_arr[-2] <= ema_slow_arr[-2]
        )
        trend_strong = Decimal(str(snapshot["adx"])) > self._adx_threshold
        bullish_dir = snapshot["plus_di"] > snapshot["minus_di"]
        not_overbought = Decimal(str(snapshot["rsi"])) < self._rsi_overbought

        if (
            cross_up and trend_strong and bullish_dir and not_overbought
            and self._current_side == SignalSide.FLAT
        ):
            self._current_side = SignalSide.LONG
            return self._build_signal(
                bar, SignalSide.LONG, snapshot,
                reason="ENTRY_LONG_EMA_CROSS_UP",
            )

        return None

    def _build_signal(
        self, bar: Bar, side: SignalSide, snapshot: dict[str, float], reason: str
    ) -> Signal:
        return Signal(
            signal_id=uuid4(),
            symbol=self._symbol,
            side=side,
            bar_close_time=bar.close_time,
            generated_at=datetime.now(UTC),
            ema_fast=Decimal(str(snapshot["ema_fast"])),
            ema_slow=Decimal(str(snapshot["ema_slow"])),
            adx_14=Decimal(str(snapshot["adx"])),
            plus_di_14=Decimal(str(snapshot["plus_di"])),
            minus_di_14=Decimal(str(snapshot["minus_di"])),
            rsi_14=Decimal(str(snapshot["rsi"])),
            atr_14=Decimal(str(snapshot["atr"])),
            reason=reason,
        )
```

Убедиться что импорты `import numpy as np`, `from datetime import UTC`, `from uuid import uuid4` есть в файле.

- [ ] **Step 4: Run tests — verify GREEN**

```bash
pytest tests/unit/test_strategy.py -v
```
Expected: 3/3 passed.

- [ ] **Step 5: Commit**

```bash
git add src/signalgen/strategy.py tests/unit/test_strategy.py
git commit -m "feat(signalgen): LONG entry on EMA cross + ADX/RSI/+DI gates

Entry rule: cross_up AND adx>threshold AND +DI>-DI AND rsi<overbought.
current_side FSM (FLAT→LONG) prevents re-entry без выхода."
```

---

### Task 10: Strategy — filter-reject branches

**Files:**
- Modify: `tests/unit/test_strategy.py`

- [ ] **Step 1: RED — 4 rejection scenarios**

Add to `tests/unit/test_strategy.py`:

```python
def test_strategy_rejects_when_adx_below_threshold() -> None:
    """Слабый тренд (ADX<25) — no signal даже при cross up."""
    # Набор с малой волатильностью → ADX < 25.
    strat = EmaCrossoverAdxRsiStrategy(
        ema_fast=12, ema_slow=26,
        adx_period=14, adx_threshold=Decimal("99"),  # искусственно задираем threshold
        rsi_period=14, rsi_overbought=Decimal("70"), rsi_oversold=Decimal("30"),
        atr_period=14, symbol="BTCUSDT",
    )
    bars = _crafted_bars_for_long_entry()
    signals = [s for b in bars if (s := strat.on_bar(b)) is not None]
    assert all(s.side != SignalSide.LONG for s in signals), "ADX>99 никогда не проходит"


def test_strategy_rejects_when_rsi_overbought() -> None:
    strat = EmaCrossoverAdxRsiStrategy(
        ema_fast=12, ema_slow=26,
        adx_period=14, adx_threshold=Decimal("25"),
        rsi_period=14, rsi_overbought=Decimal("10"),  # искусственно задираем до <RSI
        rsi_oversold=Decimal("5"),
        atr_period=14, symbol="BTCUSDT",
    )
    bars = _crafted_bars_for_long_entry()
    signals = [s for b in bars if (s := strat.on_bar(b)) is not None]
    assert all(s.side != SignalSide.LONG for s in signals), "RSI<10 никогда не выполняется"


def test_strategy_ignores_wrong_symbol() -> None:
    strat = EmaCrossoverAdxRsiStrategy(
        ema_fast=12, ema_slow=26,
        adx_period=14, adx_threshold=Decimal("25"),
        rsi_period=14, rsi_overbought=Decimal("70"), rsi_oversold=Decimal("30"),
        atr_period=14, symbol="BTCUSDT",
    )
    eth_bar = _bar(2000.0, 0, symbol="ETHUSDT")
    assert strat.on_bar(eth_bar) is None
    assert len(strat._bars) == 0  # type: ignore[attr-defined]
```

- [ ] **Step 2: Run tests — verify**

```bash
pytest tests/unit/test_strategy.py -v
```
Expected: 6/6 passed (они уже зелёные — логика уже отвергает эти кейсы).

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_strategy.py
git commit -m "test(signalgen): add rejection scenarios for ADX/RSI gates + wrong symbol"
```

---

### Task 11: Strategy — FLAT signal-flip exit

**Files:**
- Modify: `src/signalgen/strategy.py`
- Modify: `tests/unit/test_strategy.py`

- [ ] **Step 1: RED — flip scenario test**

Add to `tests/unit/test_strategy.py`:

```python
def test_strategy_emits_flat_on_signal_flip() -> None:
    """Если открыт LONG и EMA12 < EMA26 AND +DI < -DI → FLAT signal."""
    from datetime import UTC, datetime, timedelta
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    bars: list[Bar] = []
    price = 100.0
    # 60 баров downtrend → 20 rally → 20 reversal down.
    for i in range(60):
        price -= 0.2
        ot = t0 + timedelta(hours=i)
        ct = ot + timedelta(hours=1) - timedelta(microseconds=1)
        bars.append(Bar(
            symbol="BTCUSDT", interval="1h",
            open_time=ot, close_time=ct,
            open=Decimal(str(price + 0.1)), high=Decimal(str(price + 0.3)),
            low=Decimal(str(price - 0.3)), close=Decimal(str(price)),
            volume=Decimal("1.0"), trade_count=1,
            is_closed=True, data_quality=DataQuality.OK,
        ))
    for i in range(60, 80):
        price += 1.5
        ot = t0 + timedelta(hours=i)
        ct = ot + timedelta(hours=1) - timedelta(microseconds=1)
        bars.append(Bar(
            symbol="BTCUSDT", interval="1h",
            open_time=ot, close_time=ct,
            open=Decimal(str(price - 0.5)), high=Decimal(str(price + 0.8)),
            low=Decimal(str(price - 0.8)), close=Decimal(str(price)),
            volume=Decimal("1.0"), trade_count=1,
            is_closed=True, data_quality=DataQuality.OK,
        ))
    for i in range(80, 100):
        price -= 1.5
        ot = t0 + timedelta(hours=i)
        ct = ot + timedelta(hours=1) - timedelta(microseconds=1)
        bars.append(Bar(
            symbol="BTCUSDT", interval="1h",
            open_time=ot, close_time=ct,
            open=Decimal(str(price + 0.5)), high=Decimal(str(price + 0.8)),
            low=Decimal(str(price - 0.8)), close=Decimal(str(price)),
            volume=Decimal("1.0"), trade_count=1,
            is_closed=True, data_quality=DataQuality.OK,
        ))

    strat = EmaCrossoverAdxRsiStrategy(
        ema_fast=12, ema_slow=26,
        adx_period=14, adx_threshold=Decimal("25"),
        rsi_period=14, rsi_overbought=Decimal("70"), rsi_oversold=Decimal("30"),
        atr_period=14, symbol="BTCUSDT",
    )
    signals = [s for b in bars if (s := strat.on_bar(b)) is not None]
    assert any(s.side == SignalSide.LONG for s in signals)
    assert any(s.side == SignalSide.FLAT for s in signals), (
        f"Ожидался FLAT после reversal; сигналы: {[s.side for s in signals]}"
    )
```

- [ ] **Step 2: Run test — verify RED**

Expected: FAIL — FLAT signal не эмитится (ещё не реализовано).

- [ ] **Step 3: GREEN — add FLAT flip exit logic**

В `src/signalgen/strategy.py` перед `return None` финальным — добавить FLAT-check:

```python
        # Exit rule (FLAT): если current LONG, и EMA flips down + -DI доминирует → FLAT.
        if self._current_side == SignalSide.LONG:
            flip_down = ema_fast_arr[-1] < ema_slow_arr[-1]
            bearish_dir = snapshot["minus_di"] > snapshot["plus_di"]
            if flip_down and bearish_dir:
                self._current_side = SignalSide.FLAT
                return self._build_signal(
                    bar, SignalSide.FLAT, snapshot,
                    reason="EXIT_FLAT_SIGNAL_FLIP",
                )
```

Место вставки — сразу после блока LONG entry, перед финальным `return None`.

- [ ] **Step 4: Run tests**

```bash
pytest tests/unit/test_strategy.py -v
```
Expected: 7/7 passed.

- [ ] **Step 5: Commit**

```bash
git add src/signalgen/strategy.py tests/unit/test_strategy.py
git commit -m "feat(signalgen): FLAT exit on EMA flip + -DI dominance

Signal-flip exit per wiki/trading/strategies/ema-crossover-adx-rsi.md.
current_side FSM: FLAT→LONG→FLAT."
```

---

### Task 12: Strategy — duplicate bar dedup

**Files:**
- Modify: `src/signalgen/strategy.py`
- Modify: `tests/unit/test_strategy.py`

- [ ] **Step 1: RED — test duplicate bar**

Add to `tests/unit/test_strategy.py`:

```python
def test_strategy_ignores_duplicate_bar() -> None:
    """Дважды одинаковый close_time → второй вызов игнорируется (не добавляется в buffer)."""
    strat = EmaCrossoverAdxRsiStrategy(
        ema_fast=12, ema_slow=26,
        adx_period=14, adx_threshold=Decimal("25"),
        rsi_period=14, rsi_overbought=Decimal("70"), rsi_oversold=Decimal("30"),
        atr_period=14, symbol="BTCUSDT",
    )
    b = _bar(100.0, 0)
    assert strat.on_bar(b) is None
    buf_before = len(strat._bars)  # type: ignore[attr-defined]
    assert strat.on_bar(b) is None
    assert len(strat._bars) == buf_before  # type: ignore[attr-defined]


def test_strategy_rejects_out_of_order_bar() -> None:
    """Bar с close_time <= last close_time → игнор."""
    strat = EmaCrossoverAdxRsiStrategy(
        ema_fast=12, ema_slow=26,
        adx_period=14, adx_threshold=Decimal("25"),
        rsi_period=14, rsi_overbought=Decimal("70"), rsi_oversold=Decimal("30"),
        atr_period=14, symbol="BTCUSDT",
    )
    b0 = _bar(100.0, 5)
    b1 = _bar(101.0, 3)
    strat.on_bar(b0)
    buf_before = len(strat._bars)  # type: ignore[attr-defined]
    strat.on_bar(b1)
    assert len(strat._bars) == buf_before
```

- [ ] **Step 2: Run tests — verify RED**

Expected: FAIL — duplicates добавляются в buffer.

- [ ] **Step 3: GREEN — add dedup/out-of-order guard**

В `src/signalgen/strategy.py` метод `on_bar` — перед `self._bars.append(bar)` вставить:

```python
        # Dedup + out-of-order guard.
        if self._bars and bar.close_time <= self._bars[-1].close_time:
            return None
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/unit/test_strategy.py -v
```
Expected: 9/9 passed.

- [ ] **Step 5: Commit**

```bash
git add src/signalgen/strategy.py tests/unit/test_strategy.py
git commit -m "feat(signalgen): reject duplicate / out-of-order bars in on_bar

Guard: bar.close_time must be > last buffered close_time (monotonicity).
Defense-in-depth — BarBuilder должен гарантировать это upstream."
```

---

### Task 13: Look-ahead property test (hypothesis)

**Files:**
- Create: `tests/property/__init__.py`
- Create: `tests/property/test_lookahead.py`
- Modify: `pyproject.toml` (add `tests/property` to testpaths)

- [ ] **Step 1: RED — hypothesis property test**

Create empty `tests/property/__init__.py`.

Create `tests/property/test_lookahead.py`:

```python
"""Property tests: look-ahead invariants от execution-timing.md."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from src.marketdata.models import Bar, DataQuality
from src.signalgen.models import Signal
from src.signalgen.strategy import EmaCrossoverAdxRsiStrategy


@st.composite
def bar_sequence(draw: st.DrawFn, min_size: int = 80, max_size: int = 200) -> list[Bar]:
    n = draw(st.integers(min_value=min_size, max_value=max_size))
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    prices = draw(
        st.lists(
            st.decimals(min_value="50.0", max_value="200.0", places=2),
            min_size=n, max_size=n,
        )
    )
    bars: list[Bar] = []
    for i, p in enumerate(prices):
        ot = t0 + timedelta(hours=i)
        ct = ot + timedelta(hours=1) - timedelta(microseconds=1)
        # Ensure OHLC invariant.
        high = p + Decimal("0.5")
        low = p - Decimal("0.5")
        bars.append(Bar(
            symbol="BTCUSDT", interval="1h",
            open_time=ot, close_time=ct,
            open=p, high=high, low=low, close=p,
            volume=Decimal("1.0"), trade_count=1,
            is_closed=True, data_quality=DataQuality.OK,
        ))
    return bars


@given(bar_sequence())
@settings(deadline=None, max_examples=30, suppress_health_check=[HealthCheck.too_slow])
def test_signal_generated_at_ge_bar_close_time(bars: list[Bar]) -> None:
    """Look-ahead invariant: signal.generated_at >= signal.bar_close_time для КАЖДОГО signal."""
    strat = EmaCrossoverAdxRsiStrategy(
        ema_fast=12, ema_slow=26,
        adx_period=14, adx_threshold=Decimal("25"),
        rsi_period=14, rsi_overbought=Decimal("70"), rsi_oversold=Decimal("30"),
        atr_period=14, symbol="BTCUSDT",
    )
    signals: list[Signal] = []
    for b in bars:
        sig = strat.on_bar(b)
        if sig is not None:
            signals.append(sig)

    for s in signals:
        assert s.generated_at >= s.bar_close_time, (
            f"look-ahead violation: generated_at={s.generated_at} < "
            f"bar_close_time={s.bar_close_time}"
        )
```

- [ ] **Step 2: Update `pyproject.toml` testpaths**

```toml
[tool.pytest.ini_options]
testpaths = ["tests/unit", "tests/property"]
asyncio_mode = "auto"
```

- [ ] **Step 3: Run property test**

```bash
pytest tests/property/test_lookahead.py -v
```
Expected: PASS (pydantic-validator на Signal.generated_at уже enforces это).

- [ ] **Step 4: Run full suite**

```bash
make check
```
Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add tests/property/ pyproject.toml
git commit -m "test(property): hypothesis-based look-ahead invariant test

Invariant: signal.generated_at >= signal.bar_close_time for all emitted signals.
Enforced by pydantic Signal validator (S1); property test — defense-in-depth."
```

---

### Task 14: Legacy cleanup — remove empty src/strategy/

**Files:**
- Remove: `src/strategy/`

- [ ] **Step 1: Verify src/strategy/ empty**

```bash
ls src/strategy/
```
Expected: `__init__.py  __pycache__`.

- [ ] **Step 2: Remove**

```bash
rm -rf src/strategy/
```

- [ ] **Step 3: `make check` still green**

```bash
make check
```
Expected: 0 regressions.

- [ ] **Step 4: Commit**

```bash
git add -A src/strategy
git commit -m "chore(signalgen): remove empty src/strategy/ (S1 legacy leftover)

All strategy logic ported to src/signalgen/ per migration-plan §S3."
```

---

### Task 15: Wiki — components/indicators.md

**Files:**
- Create: `llm-wiki/wiki/project/components/indicators.md`

- [ ] **Step 1: Create page**

Create `llm-wiki/wiki/project/components/indicators.md`:

```markdown
---
title: signalgen.indicators — TA-Lib wrappers
type: component
tags: [component, signalgen, indicators, ta-lib, ema, adx, rsi, atr]
created: 2026-04-22
updated: 2026-04-22
sources:
  - src/signalgen/indicators.py
  - tests/unit/test_indicators.py
  - wiki/project/decisions/0011-wilder-ema-for-adx-rsi-classical-for-crossover.md
status: stable
---

# Component: signalgen.indicators

**TL;DR:** Тонкие stateless-обёртки над TA-Lib для EMA/ADX/±DI/RSI/ATR; numpy in/out; Classical EMA (α=2/(n+1)) для crossover + Wilder (α=1/n) для oscillators per ADR 0011.

## API

| Function | Signature | Smoothing | Returns |
|----------|-----------|-----------|---------|
| `ema` | `(close, period, mode="classical")` | classical или wilder | 1-D float; NaN на warm-up |
| `rsi` | `(close, period=14)` | Wilder (TA-Lib default) | [0, 100]; NaN на warm-up |
| `atr` | `(high, low, close, period=14)` | Wilder | ≥ 0; NaN на warm-up |
| `adx` | `(high, low, close, period=14)` | Wilder double-smooth | [0, 100]; warm-up ≈ 2n−1 |
| `plus_di` | `(high, low, close, period=14)` | Wilder | [0, 100] |
| `minus_di` | `(high, low, close, period=14)` | Wilder | [0, 100] |

Все функции — pure (no state), numpy-first. Валидация через `_validate_hlc` (shape + period>=2).

## Notes

- TA-Lib `EMA` имеет исторический bug (SF #87) — проверяем `EMA[period-1] == SMA(close[0..period-1])` в unit-tests.
- `ema(..., mode="wilder")` — собственная реализация (TA-Lib native EMA не поддерживает Wilder), seed = SMA(close[0..period-1]), recurrence α=1/period.
- `atr`, `rsi`, `adx`, `plus_di`, `minus_di` — прямые делегаты `talib.*` (Wilder by default).

## Related

- [[../decisions/0011-wilder-ema-for-adx-rsi-classical-for-crossover]] — ADR: почему 2 режима.
- [[./strategy]] — единственный consumer.
- [[../../trading/indicators/ema]], [[../../trading/indicators/adx]], [[../../trading/indicators/rsi]], [[../../trading/indicators/atr]] — theory.
```

- [ ] **Step 2: Commit**

```bash
git add llm-wiki/wiki/project/components/indicators.md
git commit -m "docs(wiki): add signalgen.indicators component page"
```

---

### Task 16: Wiki — components/strategy.md

**Files:**
- Create: `llm-wiki/wiki/project/components/strategy.md`

- [ ] **Step 1: Create page**

Create `llm-wiki/wiki/project/components/strategy.md`:

```markdown
---
title: signalgen.strategy — EmaCrossoverAdxRsiStrategy
type: component
tags: [component, signalgen, strategy, ema-crossover, adx, rsi, v0.1]
created: 2026-04-22
updated: 2026-04-22
sources:
  - src/signalgen/strategy.py
  - tests/unit/test_strategy.py
  - tests/property/test_lookahead.py
  - wiki/trading/strategies/ema-crossover-adx-rsi.md
  - wiki/project/architecture/execution-timing.md
status: stable
---

# Component: signalgen.strategy

**TL;DR:** `EmaCrossoverAdxRsiStrategy.on_bar(bar: Bar) -> Signal | None` — stateful стратегия с internal rolling buffer; эмитит LONG при cross-up + ADX/+DI/RSI gates; FLAT при signal-flip.

## Contract

```python
strat = EmaCrossoverAdxRsiStrategy(
    symbol="BTCUSDT",
    ema_fast=12, ema_slow=26,
    adx_period=14, adx_threshold=Decimal("25"),
    rsi_period=14, rsi_oversold=Decimal("30"), rsi_overbought=Decimal("70"),
    atr_period=14,
)
for bar in market_data_stream:
    sig = strat.on_bar(bar)
    if sig is not None:
        event_bus.emit(sig)   # S6
```

`on_bar` возвращает `Signal | None`. None может означать:
- `is_closed=False` (live bar, игнор);
- wrong symbol;
- warm-up не завершён;
- duplicate или out-of-order bar;
- нет crossing/gate-conditions.

## Entry rule (LONG)

Все условия одновременно на close(T):

1. `EMA12[T] > EMA26[T]` AND `EMA12[T-1] ≤ EMA26[T-1]` — cross up.
2. `ADX[T] > adx_threshold` (default 25).
3. `+DI[T] > -DI[T]` — direction confirmation.
4. `RSI[T] < rsi_overbought` (default 70).
5. `current_side == FLAT` (no re-entry без выхода).

Reason code: `ENTRY_LONG_EMA_CROSS_UP`.

## Exit rule (FLAT — signal flip)

На close(T), если `current_side == LONG`:

- `EMA12[T] < EMA26[T]` AND `-DI[T] > +DI[T]` → FLAT.

Reason code: `EXIT_FLAT_SIGNAL_FLIP`.

*SL/TP и time-stop — в S5 (execution), не здесь.*

## Invariants

- **Look-ahead-free:** `signal.generated_at >= signal.bar_close_time` — enforced через pydantic validator (Signal model) + property test `tests/property/test_lookahead.py`.
- **Closed bars only:** `is_closed=False` — skip.
- **Monotonicity:** out-of-order / duplicate bars → skip.
- **FSM:** `current_side` ∈ {FLAT, LONG}; транзиции FLAT→LONG (entry), LONG→FLAT (flip). SHORT вне scope v0.1.
- **Buffer size:** `max(ema_slow, 2·adx_period, atr_period, rsi_period) + 5`.
- **Thread-safety:** НЕ thread-safe. Один producer thread.

## Performance

- Indicator computation пересчитывается на full buffer каждый bar. Для 1H и buffer ≤ 100 баров это <5ms.
- v0.2 refinement: incremental update (хранить последние EMA/ADX-state) — не требуется на 1H.

## Related

- [[./indicators]] — consumer (EMA/ADX/RSI/ATR).
- [[../../trading/strategies/ema-crossover-adx-rsi]] — reference rules.
- [[../architecture/execution-timing]] — invariants.
- [[./models]] — Bar (input), Signal (output).
- [[../decisions/0011-wilder-ema-for-adx-rsi-classical-for-crossover]] — ADR.
```

- [ ] **Step 2: Commit**

```bash
git add llm-wiki/wiki/project/components/strategy.md
git commit -m "docs(wiki): add signalgen.strategy component page"
```

---

### Task 17: Wiki — sprints/sprint-03-strategy-port.md

**Files:**
- Create: `llm-wiki/wiki/project/sprints/sprint-03-strategy-port.md`

- [ ] **Step 1: Create delivery record**

Per template from `llm-wiki/wiki/project/sprints/README.md`. Заполнить реальные commit range, test counts, deviations, follow-ups. Финальные значения — на этапе финализации; черновик ниже будет обновлён перед commit.

```markdown
---
title: Sprint 3 — Strategy port (EMA + ADX + RSI + ATR via TA-Lib)
type: summary
tags: [sprint, sprint-3, strategy, signalgen, ta-lib, indicators]
created: 2026-04-22
updated: 2026-04-22
sources: [project/plans/2026-04-22-sprint-3-strategy-port.md]
status: done
---

# Sprint 3 — Strategy port

**Dates:** 2026-04-22
**Plan:** [[../plans/2026-04-22-sprint-3-strategy-port]]
**Tag:** `v0.1.0-alpha.3`
**Commit range:** `<base>..<head>`

## Goal
Портировать EMA-crossover + ADX/RSI/ATR стратегию через TA-Lib; реализовать `on_bar(Bar) -> Signal | None` с enforced look-ahead-free invariants. Source: `migration-plan.md §S3`.

## Scope delivered

### Code
- `src/signalgen/indicators.py` — `ema`, `rsi`, `atr`, `adx`, `plus_di`, `minus_di`; Classical + Wilder EMA per ADR 0011.
- `src/signalgen/strategy.py` — `EmaCrossoverAdxRsiStrategy` stateful класс с on_bar контрактом, FLAT/LONG FSM, rolling buffer, dedup/out-of-order guard.
- `src/platform/config.py` — strategy params в `Settings` (ema_fast/slow, adx_*, rsi_*, atr_period).

### Wiki
- Components: [[../components/indicators]], [[../components/strategy]].
- Plan: [[../plans/2026-04-22-sprint-3-strategy-port]].

### Removed
- `src/strategy/` — пустая легаси-директория от S1.

## Decisions & deviations
*(заполнить по факту исполнения — отклонения, новые ADR)*

## Verification
- `make check`: <N> passed — ruff clean, mypy --strict clean.
- Tests: <N> unit + 1 property (hypothesis).

## Impact on downstream
- **S4 (Risk)** получает: `Signal` instance с `atr_14` в snapshot — готово для `qty = f·equity/(1.5·ATR)` sizing.
- **S5 (Execution)** получает: Signal → Order pipeline; `bar_close_time` для SL/TP attach к Entry.
- **S6 (Event Bus)** получает: Signal emission point для `SignalGenerated` event.
- **S7 (Backtest)** получает: deterministic strategy object для replay.

## Follow-ups carried forward
*(заполнить по факту)*

## Related
- Plan: [[../plans/2026-04-22-sprint-3-strategy-port]]
- Components: [[../components/indicators]], [[../components/strategy]], [[../components/models]]
- Architecture: [[../architecture/migration-plan]] §S3, [[../architecture/execution-timing]]
- ADR: [[../decisions/0011-wilder-ema-for-adx-rsi-classical-for-crossover]]
- Prior sprint: [[sprint-02-bybit-venue-migration]]
```

- [ ] **Step 2: Commit (после финализации секций)**

```bash
git add llm-wiki/wiki/project/sprints/sprint-03-strategy-port.md
git commit -m "docs(wiki): Sprint 3 delivery record"
```

---

### Task 18: Wiki — index.md + log.md + finalize

**Files:**
- Modify: `llm-wiki/wiki/index.md`
- Modify: `llm-wiki/wiki/log.md`

- [ ] **Step 1: Update `index.md`**

- Section `Project — Components`: добавить:
  ```
  - [[project/components/indicators]] — TA-Lib wrappers: EMA classical/wilder + ADX/±DI/RSI/ATR Wilder.
  - [[project/components/strategy]] — EmaCrossoverAdxRsiStrategy: on_bar(Bar) → Signal | None, FLAT/LONG FSM.
  ```
- Section `Project — Sprints`: добавить:
  ```
  - [[project/sprints/sprint-03-strategy-port]] — S3 (2026-04-22): EMA crossover + ADX/RSI/ATR через TA-Lib, on_bar контракт; tag `v0.1.0-alpha.3`.
  ```
- Section `Project — Plans`: добавить:
  ```
  - [[project/plans/2026-04-22-sprint-3-strategy-port]] — implementation plan Sprint 3 (strategy port + TA-Lib).
  ```

- [ ] **Step 2: Append to `log.md`**

```markdown
## [2026-04-22] ingest | Sprint 3 — Strategy port completed
- Added (code): src/signalgen/{indicators,strategy}.py, 3 test-modules.
- Added (wiki): wiki/project/components/{indicators,strategy}.md, wiki/project/sprints/sprint-03-strategy-port.md, wiki/project/plans/2026-04-22-sprint-3-strategy-port.md.
- Modified (code): pyproject.toml (+TA-Lib>=0.4.28, mypy override), src/platform/config.py (strategy params).
- Modified (wiki): index.md.
- Removed: src/strategy/ (empty legacy from S1).
- Tag: v0.1.0-alpha.3 (commit TBD).
- Verification: make check green — ruff/mypy/pytest (<N> unit + 1 property).
- Notes: Stage 3 Sprint 3 закрыт. Следующий — Sprint 4 (Risk — 4-phase Kelly + CB L1/L2/L3/flash).
```

- [ ] **Step 3: Update `sprint-03-strategy-port.md`** — заполнить `commit range`, `test count`, deviations (актуальное на момент финализации).

- [ ] **Step 4: Commit**

```bash
git add llm-wiki/wiki/index.md llm-wiki/wiki/log.md llm-wiki/wiki/project/sprints/sprint-03-strategy-port.md
git commit -m "docs(wiki): finalize Sprint 3 — index + log + sprint page"
```

---

### Task 19: Tag v0.1.0-alpha.3 + PR

**Files:** none (git/gh operations only)

- [ ] **Step 1: Final `make check`**

```bash
make check
```
Expected: all green.

- [ ] **Step 2: Create tag**

```bash
git tag -a v0.1.0-alpha.3 -m "Sprint 3 — Strategy port (EMA + ADX + RSI + ATR via TA-Lib)"
```

- [ ] **Step 3: Push branch + tag**

```bash
git push -u origin feature/sprint-3-strategy-port
git push origin v0.1.0-alpha.3
```

- [ ] **Step 4: Create PR**

```bash
gh pr create --title "Sprint 3 — Strategy port (EMA + ADX + RSI + ATR via TA-Lib)" --body "$(cat <<'EOF'
## Summary
- Port EMA-crossover + ADX/RSI/ATR strategy через TA-Lib (migration-plan §S3)
- `EmaCrossoverAdxRsiStrategy.on_bar(Bar) -> Signal | None` с enforced look-ahead-free invariants
- TA-Lib 0.4.28+ added as dependency; Classical EMA (α=2/(n+1)) + Wilder (α=1/n) per ADR 0011

## Test plan
- [x] `make check` green (ruff + mypy --strict + pytest)
- [x] Unit tests: 9 indicator tests + 9 strategy scenario tests
- [x] Property test: hypothesis-based look-ahead invariant
- [x] Legacy cleanup: `src/strategy/` removed

## Artifacts
- Code: `src/signalgen/{indicators,strategy}.py`, `src/platform/config.py`
- Tests: `tests/unit/test_{indicators,strategy}.py`, `tests/property/test_lookahead.py`
- Wiki: `llm-wiki/wiki/project/{components/{indicators,strategy},sprints/sprint-03-strategy-port,plans/2026-04-22-sprint-3-strategy-port}.md`
- Tag: `v0.1.0-alpha.3`
EOF
)"
```

---

## Post-execution

- [ ] Merge PR после ревью.
- [ ] Обновить `sprint-03-strategy-port.md` финальным commit range.
- [ ] Подтвердить `make check` на main после merge.
- [ ] Next sprint: S4 (Risk — 4-phase Kelly + Circuit Breakers).

## Related

- [[../architecture/migration-plan]] §S3 — source of truth.
- [[../decisions/0011-wilder-ema-for-adx-rsi-classical-for-crossover]] — ADR.
- [[../../trading/strategies/ema-crossover-adx-rsi]] — rules reference.
- [[../architecture/execution-timing]] — look-ahead invariants.
- [[../sprints/sprint-02-bybit-venue-migration]] — prior sprint (MarketData + Bar).
