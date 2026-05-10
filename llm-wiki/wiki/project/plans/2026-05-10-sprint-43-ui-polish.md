---
title: "Sprint 43 — UI polish (preset rename + descriptions + equity chart)"
type: plan
tags: [sprint-43, ui, dashboard, equity-chart, preset-rename, uplot]
created: 2026-05-10
updated: 2026-05-10
status: ready
sources:
  - llm-wiki/wiki/project/pre-s43-backlog.md
---

# Sprint 43 — UI Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rename preset labels к semantic Russian names с optgroup grouping, add per-strategy description block, add equity curve chart (uPlot) к dashboard backtest results.

**Architecture:** STRATEGY_PRESETS extended с `description` + `optgroup` fields. `/api/strategies` and `/api/strategy/{id}/info` endpoints expose new fields. Frontend rebuilds dropdown с `<optgroup>`, fetches+caches description in existing `_strategyInfoCache`, renders collapsible description block. Envelope helper `build_research_runner_envelope()` adds `equity_curve: {timestamps, equity_pct}` parallel-arrays format. Both research runners (atr_breakout, volume_breakout) compute timestamps from df bar indices and pass к envelope. uPlot vendored locally (`/static/vendor/uPlot.iife.min.js` + `.css`), terminal-themed CSS overrides, `renderResult()` builds chart in `#equity-chart` div with empty-data placeholder для legacy WFA presets.

**Tech Stack:** Python 3.12, FastAPI, pydantic v2, pytest, vanilla JS (no framework), uPlot v1.6.x (~40KB).

**Branch:** `feature/sprint-43-ui-polish`

**Models:** sonnet for all 12 tasks (mechanical UI work + backend glue).

---

## File Trace Map (PHASE 3 step 1a HARD-GATE)

| File | Action | Tasks |
|------|--------|-------|
| `src/dashboard/backtest_runner.py:30-260` | MODIFY (rename labels + add description/optgroup) | T1 |
| `src/dashboard/app.py` | MODIFY (extend /api/strategies + /api/strategy/{id}/info) | T2 |
| `src/backtest/research_runner_envelope.py` | MODIFY (add equity_curve parallel arrays) | T3 |
| `src/backtest/atr_breakout_runner.py` | MODIFY (pass df timestamps к envelope) | T4 |
| `src/backtest/volume_breakout_runner.py` | MODIFY (pass df timestamps к envelope) | T5 |
| `src/dashboard/static/vendor/uPlot.iife.min.js` | CREATE (vendor) | T6 |
| `src/dashboard/static/vendor/uPlot.min.css` | CREATE (vendor) | T6 |
| `src/dashboard/templates/index.html` | MODIFY (description block + equity chart div + uPlot script) | T7 |
| `src/dashboard/static/dashboard.js` | MODIFY (optgroup, description render, equity chart render) | T8, T9, T10 |
| `src/dashboard/static/dashboard.css` | MODIFY (description block + uPlot terminal overrides) | T11 |
| `tests/unit/test_research_runner_envelope.py` | MODIFY (equity_curve format tests) | T3 |
| `tests/unit/test_supported_combos_endpoint.py` | MODIFY (description + optgroup field tests) | T2 |
| `tests/integration/test_atr_breakout_dashboard_contract.py` | MODIFY (equity_curve presence tests) | T4 |
| `tests/integration/test_volume_breakout_dashboard_contract.py` | MODIFY (equity_curve presence test) | T5 |
| `llm-wiki/wiki/project/decisions/0063-sprint-43-ui-polish.md` | CREATE | T12 |
| `llm-wiki/wiki/project/sprints/sprint-43-ui-polish.md` | CREATE | T12 |
| `llm-wiki/wiki/project/architecture/current-state.md` | MODIFY | T12 |
| `llm-wiki/wiki/index.md` | MODIFY | T12 |
| `llm-wiki/wiki/log.md` | APPEND | T12 |
| `llm-wiki/wiki/project/SPRINT_STATE.md` | MODIFY (per-task) | every task |

---

## Task 1: Preset rename + description + optgroup fields

**Files:**
- Modify: `src/dashboard/backtest_runner.py:30-260` (STRATEGY_PRESETS dict)

- [ ] **Step 1: Update each preset с three new fields (`label` rename, `description`, `optgroup`)**

For each of 6 presets in STRATEGY_PRESETS, replace existing label and add description + optgroup fields. Apply EXACTLY this mapping:

```python
# ema_crossover_s13 (line ~30)
"ema_crossover_s13": {
    "label": "Тренд EMA 12/26 + ADX фильтр",
    "optgroup": "Тренд-следование",
    "description": (
        "<p><strong>Подход:</strong> классическая трендовая стратегия на пересечении "
        "быстрой EMA(12) и медленной EMA(26) с фильтром силы тренда ADX и подтверждением "
        "не-перекупленности RSI(14).</p>"
        "<p><strong>Вход long:</strong> EMA12 пересекает EMA26 снизу вверх + ADX > 25 + "
        "RSI < 70.</p>"
        "<p><strong>Выход:</strong> обратное пересечение EMA либо ADX падает ниже 20.</p>"
        "<p><strong>Подходит для:</strong> сильно-трендовых режимов (бычий или медвежий импульс). "
        "Плохо работает в боковике — много ложных пересечений (whipsaw).</p>"
        "<p><strong>Вердикт S13:</strong> FAIL conjoint (T1=−44.46 OOS Sharpe).</p>"
    ),
    "sprint": "S13",
    # ... rest of existing fields unchanged (verdict, type, indicators)
},

# mean_reversion_s15 (line ~41)
"mean_reversion_s15": {
    "label": "Возврат к среднему RSI/Bollinger (классика)",
    "optgroup": "Возврат к среднему",
    "description": (
        "<p><strong>Подход:</strong> классический mean-reversion на экстремумах RSI(14) "
        "с подтверждением через Bollinger Bands (20, 2.0σ). Логика: перепроданность ⇒ возврат вверх, "
        "перекупленность ⇒ возврат вниз.</p>"
        "<p><strong>Вход long:</strong> RSI < 30 AND цена ниже нижней BB.</p>"
        "<p><strong>Выход:</strong> RSI пересекает 50 либо цена возвращается к средней BB.</p>"
        "<p><strong>Подходит для:</strong> боковиков и низковолатильных режимов. "
        "Опасно в трендах — перепроданность может углубляться.</p>"
        "<p><strong>Вердикт S15:</strong> FAIL conjoint (MC p=0.998 — неотличимо от шума).</p>"
    ),
    "sprint": "S15",
    # ... rest unchanged
},

# mean_reversion_s17_relaxed (line ~52)
"mean_reversion_s17_relaxed": {
    "label": "Возврат к среднему RSI/Bollinger (мягкий)",
    "optgroup": "Возврат к среднему",
    "description": (
        "<p><strong>Подход:</strong> релакс-версия классического mean-reversion с "
        "более чувствительными порогами RSI(35/65) и узкими Bollinger Bands (20, 1.5σ). "
        "Больше сигналов чем S15.</p>"
        "<p><strong>Вход long:</strong> RSI < 35 AND цена ниже нижней BB(1.5σ).</p>"
        "<p><strong>Выход:</strong> RSI > 50 либо возврат к средней BB.</p>"
        "<p><strong>Подходит для:</strong> умеренных боковиков, ETH/SOL чаще чем BTC.</p>"
        "<p><strong>Вердикт S17:</strong> 5/6 + DSR + MC PASS, но T5 floor (n≥100) недостижим.</p>"
    ),
    "sprint": "S17",
    # ... rest unchanged
},

# donchian_breakout_s35 (line ~63)
"donchian_breakout_s35": {
    "label": "Канал Дончиана пробой",
    "optgroup": "Прорывы",
    "description": (
        "<p><strong>Подход:</strong> long-only пробой 20-периодного канала Дончиана "
        "(максимум за N баров) с trailing-stop через ATR×2.0.</p>"
        "<p><strong>Вход long:</strong> close > max(high) за последние 20 баров.</p>"
        "<p><strong>Выход:</strong> close < min(low) за последние 10 баров либо ATR-stop.</p>"
        "<p><strong>Подходит для:</strong> начала сильных трендов. Хорошо ловит крупные движения, "
        "но проигрывает в боковиках.</p>"
        "<p><strong>Вердикт S35:</strong> FAIL conjoint (n=21 << 50, α CLOSED per ADR 0054).</p>"
    ),
    "sprint": "S35",
    # ... rest unchanged
},

# volume_breakout_iter10 (line ~73)
"volume_breakout_iter10": {
    "label": "Прорыв с подтверждением объёма",
    "optgroup": "Прорывы",
    "description": (
        "<p><strong>Подход:</strong> Donchian-пробой с подтверждением через всплеск объёма. "
        "Сигнал валиден только если объём бара > среднего × множитель.</p>"
        "<p><strong>Вход long:</strong> close > max(high, lookback=9) AND volume > MA(volume, 10) × 1.456.</p>"
        "<p><strong>Выход:</strong> close < min(low, exit_lookback=8) либо ATR(9) × 2.97 stop.</p>"
        "<p><strong>Подходит для:</strong> BTCUSDT 4H, начала тренда с институциональным объёмом. "
        "LOCKED params (autoresearch sweep #1644). Только эта пара/TF.</p>"
        "<p><strong>Вердикт S39:</strong> 3.3y +122.66% / 8mo held-out +20.42%. RAW (WFA pending S44).</p>"
    ),
    "sprint": "S39",
    # ... rest unchanged
},

# atr_breakout (line ~94)
"atr_breakout": {
    "label": "ATR-адаптивный пробой (multi-combo)",
    "optgroup": "Прорывы",
    "description": (
        "<p><strong>Подход:</strong> long-only пробой адаптивного ATR-канала. Уровень входа "
        "= close + ATR × множитель. Стоп тоже ATR-based, отдельный период и множитель.</p>"
        "<p><strong>Вход long:</strong> close > close[−2] + ATR(period_main) × mult_breakout.</p>"
        "<p><strong>Выход:</strong> ATR(period_stop) × mult_stop trailing-stop либо обратный сигнал.</p>"
        "<p><strong>Подходит для:</strong> 10 (symbol, timeframe) комбинаций — каждая с независимыми LOCKED "
        "параметрами от autoresearch endless. Лучший: BTCUSDT 4H +819.81% за 8.7 года, 5/5 "
        "положительных под-периодов.</p>"
        "<p><strong>Вердикт S40+S41:</strong> RAW per combo (WFA pending S44). Pre-registered LOCKED params.</p>"
    ),
    "sprint": "S42",
    # ... rest unchanged (supported_combos, type, indicators={})
},
```

- [ ] **Step 2: Verify file syntax**

```bash
.venv/bin/python -c "from src.dashboard.backtest_runner import STRATEGY_PRESETS; assert all('description' in p and 'optgroup' in p for p in STRATEGY_PRESETS.values()); print('OK 6 presets с description+optgroup')"
```

Expected: `OK 6 presets с description+optgroup`

- [ ] **Step 3: Write tests**

Create `tests/unit/test_preset_metadata.py`:

```python
"""S43 T1 — preset metadata fields (description + optgroup) tests."""
from __future__ import annotations

from src.dashboard.backtest_runner import STRATEGY_PRESETS

EXPECTED_OPTGROUPS = {
    "ema_crossover_s13": "Тренд-следование",
    "mean_reversion_s15": "Возврат к среднему",
    "mean_reversion_s17_relaxed": "Возврат к среднему",
    "donchian_breakout_s35": "Прорывы",
    "volume_breakout_iter10": "Прорывы",
    "atr_breakout": "Прорывы",
}

EXPECTED_LABELS = {
    "ema_crossover_s13": "Тренд EMA 12/26 + ADX фильтр",
    "mean_reversion_s15": "Возврат к среднему RSI/Bollinger (классика)",
    "mean_reversion_s17_relaxed": "Возврат к среднему RSI/Bollinger (мягкий)",
    "donchian_breakout_s35": "Канал Дончиана пробой",
    "volume_breakout_iter10": "Прорыв с подтверждением объёма",
    "atr_breakout": "ATR-адаптивный пробой (multi-combo)",
}


def test_all_presets_have_optgroup() -> None:
    for pid, preset in STRATEGY_PRESETS.items():
        assert "optgroup" in preset, f"{pid} missing optgroup"
        assert preset["optgroup"] == EXPECTED_OPTGROUPS[pid]


def test_all_presets_have_description() -> None:
    for pid, preset in STRATEGY_PRESETS.items():
        assert "description" in preset, f"{pid} missing description"
        assert isinstance(preset["description"], str)
        assert len(preset["description"]) > 100, f"{pid} description too short"


def test_descriptions_use_html_strong_tags() -> None:
    """Descriptions use <strong> for term emphasis (no markdown)."""
    for pid, preset in STRATEGY_PRESETS.items():
        assert "<strong>" in preset["description"], f"{pid} description missing <strong> tags"


def test_labels_renamed_к_semantic_russian() -> None:
    for pid, preset in STRATEGY_PRESETS.items():
        assert preset["label"] == EXPECTED_LABELS[pid]
        # Old technical sprint identifier removed from label
        assert "[S" not in preset["label"], f"{pid} label still has [S<N>] tag"
```

- [ ] **Step 4: Run tests, verify PASS**

```bash
.venv/bin/pytest tests/unit/test_preset_metadata.py -v
```

Expected: 4/4 PASS.

- [ ] **Step 5: Verify no regression**

```bash
.venv/bin/pytest tests/unit/test_dashboard_atr_breakout_preset.py tests/unit/test_supported_combos_endpoint.py -v 2>&1 | tail -10
```

Expected: All existing dashboard tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/dashboard/backtest_runner.py tests/unit/test_preset_metadata.py
git commit -m "feat(s43): preset rename к semantic Russian + description + optgroup fields"
```

- [ ] **Step 7: SPRINT_STATE update**

Edit `llm-wiki/wiki/project/SPRINT_STATE.md` Sprint 43 section: T1 done, T2 next. Bump `updated:`.

```bash
git add llm-wiki/wiki/project/SPRINT_STATE.md
git commit -m "docs(sprint): SPRINT_STATE update phase=4 task=T1 done"
```

---

## Task 2: API endpoint extensions (description + optgroup)

**Files:**
- Modify: `src/dashboard/app.py:80-128` (extend /api/strategies + /api/strategy/{id}/info)
- Modify: `tests/unit/test_supported_combos_endpoint.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/unit/test_supported_combos_endpoint.py`:

```python
def test_strategies_endpoint_returns_description_and_optgroup(client: TestClient) -> None:
    """S43 — /api/strategies includes description + optgroup для frontend."""
    r = client.get("/api/strategies")
    assert r.status_code == 200
    data = r.json()
    assert "atr_breakout" in data
    p = data["atr_breakout"]
    assert "description" in p
    assert "optgroup" in p
    assert p["optgroup"] == "Прорывы"
    assert "<strong>" in p["description"]


def test_strategy_info_endpoint_returns_description(client: TestClient) -> None:
    r = client.get("/api/strategy/atr_breakout/info")
    data = r.json()
    assert "description" in data
    assert "optgroup" in data
    assert data["optgroup"] == "Прорывы"
```

- [ ] **Step 2: Run, verify FAIL**

```bash
.venv/bin/pytest tests/unit/test_supported_combos_endpoint.py::test_strategies_endpoint_returns_description_and_optgroup tests/unit/test_supported_combos_endpoint.py::test_strategy_info_endpoint_returns_description -v
```

Expected: 2 FAIL — fields not exposed.

- [ ] **Step 3: Modify `/api/strategies` endpoint в app.py:104-110**

Replace existing block:

```python
    @app.get("/api/strategies")
    async def get_strategies() -> dict[str, dict[str, object]]:
        # Return id → {label, type} only (no nested config exposure)
        return {
            sid: {"id": sid, "label": s["label"], "type": s["type"]}
            for sid, s in STRATEGY_PRESETS.items()
        }
```

With:

```python
    @app.get("/api/strategies")
    async def get_strategies() -> dict[str, dict[str, object]]:
        # S43 T2 — include description + optgroup (frontend dropdown grouping + description block)
        return {
            sid: {
                "id": sid,
                "label": s["label"],
                "type": s["type"],
                "description": s.get("description", ""),
                "optgroup": s.get("optgroup", ""),
            }
            for sid, s in STRATEGY_PRESETS.items()
        }
```

- [ ] **Step 4: Modify `/api/strategy/{strategy_id}/info` endpoint в app.py:112-128**

Replace existing return block с (add description + optgroup fields):

```python
    @app.get("/api/strategy/{strategy_id}/info")
    async def get_strategy_info(strategy_id: str) -> dict[str, object]:
        """S42 T5 — preset metadata + supported_combos for frontend gates.
        S43 T2 — added description + optgroup fields для UI block.
        """
        preset = STRATEGY_PRESETS.get(strategy_id)
        if preset is None:
            raise HTTPException(status_code=404, detail=f"Unknown strategy: {strategy_id}")
        sc_raw = preset.get("supported_combos", [])
        sc_serialized: list[list[str]] = [list(combo) for combo in sc_raw]
        return {
            "id": strategy_id,
            "label": preset["label"],
            "type": preset["type"],
            "supported_combos": sc_serialized,
            "locked_symbol": preset.get("locked_symbol"),
            "locked_interval": preset.get("locked_interval"),
            "description": preset.get("description", ""),
            "optgroup": preset.get("optgroup", ""),
        }
```

- [ ] **Step 5: Run tests, verify PASS**

```bash
.venv/bin/pytest tests/unit/test_supported_combos_endpoint.py -v
```

Expected: 8/8 PASS (6 existing + 2 new).

- [ ] **Step 6: mypy strict**

```bash
.venv/bin/mypy --strict src/dashboard/app.py
```

Expected: 0 errors.

- [ ] **Step 7: Commit + SPRINT_STATE**

```bash
git add src/dashboard/app.py tests/unit/test_supported_combos_endpoint.py
git commit -m "feat(s43): /api/strategies + /api/strategy/{id}/info expose description + optgroup"
git add llm-wiki/wiki/project/SPRINT_STATE.md  # after editing
git commit -m "docs(sprint): SPRINT_STATE update phase=4 task=T2 done"
```

---

## Task 3: Envelope helper — equity_curve parallel arrays

**Files:**
- Modify: `src/backtest/research_runner_envelope.py`
- Modify: `tests/unit/test_research_runner_envelope.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/unit/test_research_runner_envelope.py`:

```python
def test_envelope_equity_curve_parallel_arrays_format() -> None:
    """S43 T3 — envelope returns equity_curve как parallel arrays для uPlot native API.
    Format: {timestamps: [unix_int...], equity_pct: [float...]}.
    Both arrays MUST be same length.
    """
    payload = build_research_runner_envelope(
        runner_name="atr_breakout_runner",
        symbol="BTCUSDT", interval="240",
        n_trades=3, sharpe=1.0, win_rate=0.5,
        total_pnl_pct=15.0,
        bars_per_year=2191,
        equity_curve=[0.0, 5.0, 10.0, 15.0],  # 4 points
        equity_timestamps=[1672531200, 1672617600, 1672704000, 1672790400],  # 4 unix seconds
        runner_label="x",
    )
    ec = payload["equity_curve"]
    assert isinstance(ec, dict)
    assert "timestamps" in ec
    assert "equity_pct" in ec
    assert ec["timestamps"] == [1672531200, 1672617600, 1672704000, 1672790400]
    assert ec["equity_pct"] == [0.0, 5.0, 10.0, 15.0]
    assert all(isinstance(t, int) for t in ec["timestamps"])
    assert all(isinstance(v, float) for v in ec["equity_pct"])


def test_envelope_equity_curve_empty_when_no_trades() -> None:
    """Zero trades → empty arrays (not None) — frontend can safely call .length."""
    payload = build_research_runner_envelope(
        runner_name="x", symbol="BTCUSDT", interval="240",
        n_trades=0, sharpe=0.0, win_rate=0.0, total_pnl_pct=0.0,
        bars_per_year=2191,
        equity_curve=[],
        equity_timestamps=[],
        runner_label="x",
    )
    assert payload["equity_curve"] == {"timestamps": [], "equity_pct": []}


def test_envelope_equity_timestamps_optional_keyword() -> None:
    """equity_timestamps default = empty list (backward-compat для callers еще не updated)."""
    payload = build_research_runner_envelope(
        runner_name="x", symbol="BTCUSDT", interval="240",
        n_trades=2, sharpe=1.0, win_rate=0.5, total_pnl_pct=10.0,
        bars_per_year=2191,
        equity_curve=[0.0, 5.0, 10.0],
        runner_label="x",
        # equity_timestamps not passed
    )
    # Equity curve still present, but timestamps empty
    assert payload["equity_curve"]["equity_pct"] == [0.0, 5.0, 10.0]
    assert payload["equity_curve"]["timestamps"] == []
```

- [ ] **Step 2: Run, verify FAIL**

```bash
.venv/bin/pytest tests/unit/test_research_runner_envelope.py -v -k "equity_curve_parallel or equity_curve_empty or equity_timestamps_optional"
```

Expected: 3 FAIL.

- [ ] **Step 3: Modify envelope helper signature**

In `src/backtest/research_runner_envelope.py`, modify `build_research_runner_envelope()` signature:

Find:
```python
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
```

Replace с (add `equity_timestamps: list[int] | None = None`):
```python
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
    equity_timestamps: list[int] | None = None,
) -> dict[str, Any]:
```

- [ ] **Step 4: Add `equity_curve` parallel arrays к return dict**

In the return dict body of `build_research_runner_envelope()`, find:

```python
    return {
        # Crash-fix essentials
        "bars_per_year": bars_per_year,
```

Insert IMMEDIATELY after the opening `return {`:

```python
    return {
        # S43 T3 — equity_curve parallel arrays для uPlot
        "equity_curve": {
            "timestamps": equity_timestamps if equity_timestamps else [],
            "equity_pct": list(equity_curve),
        },
        # Crash-fix essentials
        "bars_per_year": bars_per_year,
```

- [ ] **Step 5: Run tests, verify PASS**

```bash
.venv/bin/pytest tests/unit/test_research_runner_envelope.py -v
```

Expected: 9/9 PASS (6 existing + 3 new).

- [ ] **Step 6: mypy strict**

```bash
.venv/bin/mypy --strict src/backtest/research_runner_envelope.py
```

Expected: 0 errors.

- [ ] **Step 7: Commit + SPRINT_STATE**

```bash
git add src/backtest/research_runner_envelope.py tests/unit/test_research_runner_envelope.py
git commit -m "feat(s43): envelope adds equity_curve parallel arrays для uPlot"
git add llm-wiki/wiki/project/SPRINT_STATE.md
git commit -m "docs(sprint): SPRINT_STATE update phase=4 task=T3 done"
```

---

## Task 4: atr_breakout_runner — pass df timestamps к envelope

**Files:**
- Modify: `src/backtest/atr_breakout_runner.py` (function `run_atr_breakout_backtest`)
- Modify: `tests/integration/test_atr_breakout_dashboard_contract.py`

- [ ] **Step 1: Write failing test**

Append к `tests/integration/test_atr_breakout_dashboard_contract.py`:

```python
@pytest.mark.integration
def test_atr_breakout_envelope_includes_equity_curve_timestamps() -> None:
    """S43 T4 — atr_breakout runner passes df timestamps к envelope."""
    from datetime import date
    from src.backtest.atr_breakout_runner import run_atr_breakout_backtest
    r = run_atr_breakout_backtest(
        symbol="BTCUSDT", interval="240",
        start_date=date(2017, 8, 17), end_date=date(2026, 4, 30),
    )
    ec = r["equity_curve"]
    assert isinstance(ec, dict)
    # Must have equal length parallel arrays
    assert len(ec["timestamps"]) == len(ec["equity_pct"])
    # Must contain at least one trade (BTC 4H baseline = 69 trades + 1 starting zero)
    assert len(ec["timestamps"]) >= 70
    # Timestamps must be unix seconds (int, > year 2017 start)
    assert ec["timestamps"][0] >= 1502928000  # 2017-08-17 unix
    assert all(isinstance(t, int) for t in ec["timestamps"])
    # First equity point = 0 (starting balance)
    assert ec["equity_pct"][0] == 0.0
    # Last equity point = +819.81% (BTC 4H S40 baseline)
    assert abs(ec["equity_pct"][-1] - 819.81) < 2.0
```

- [ ] **Step 2: Run, verify FAIL**

```bash
.venv/bin/pytest tests/integration/test_atr_breakout_dashboard_contract.py::test_atr_breakout_envelope_includes_equity_curve_timestamps -v -m integration
```

Expected: FAIL — equity_curve.timestamps empty.

- [ ] **Step 3: Modify `run_atr_breakout_backtest` to compute timestamps**

In `src/backtest/atr_breakout_runner.py::run_atr_breakout_backtest`, find the existing block:

```python
    # Build equity_curve from trades list для sub-period robustness chip
    trades_list = inner.get("trades", [])
    equity_curve: list[float] = [0.0]
    for tr in trades_list:
        equity_curve.append(equity_curve[-1] + (tr.pnl_pct * 100.0))
```

Replace с (add timestamps parallel array):

```python
    # S43 T4 — Build equity_curve + timestamps parallel arrays для uPlot.
    # Each trade closes на bar `exit_idx` — its timestamp = df["_ts"].iloc[exit_idx].
    trades_list = inner.get("trades", [])
    equity_curve: list[float] = [0.0]
    equity_timestamps: list[int] = []
    if trades_list and not df.empty:
        # Starting equity timestamp = first bar в df (before any trades)
        equity_timestamps.append(int(df["_ts"].iloc[0].timestamp()))
        for tr in trades_list:
            equity_curve.append(equity_curve[-1] + (tr.pnl_pct * 100.0))
            # Use exit_idx — trade closes на этот bar
            equity_timestamps.append(int(df["_ts"].iloc[tr.exit_idx].timestamp()))
```

- [ ] **Step 4: Modify the envelope call к pass equity_timestamps**

In the same function, find existing:

```python
    return build_research_runner_envelope(
        runner_name="atr_breakout_runner",
        symbol=symbol,
        interval=interval,
        n_trades=int(inner["n_trades"]),
        sharpe=float(inner["sharpe"]) if inner["sharpe"] == inner["sharpe"] else 0.0,
        win_rate=float(inner["win_rate"]) if inner["win_rate"] == inner["win_rate"] else 0.0,
        total_pnl_pct=float(inner["total_pnl_pct"]),
        bars_per_year=bars_per_year,
        equity_curve=equity_curve,
        runner_label=f"ATR breakout {interval} {symbol} (LOCKED)",
        start=start_date.isoformat(),
        end=end_date.isoformat(),
    )
```

Add `equity_timestamps=equity_timestamps,` keyword (insert anywhere before closing `)`):

```python
    return build_research_runner_envelope(
        runner_name="atr_breakout_runner",
        symbol=symbol,
        interval=interval,
        n_trades=int(inner["n_trades"]),
        sharpe=float(inner["sharpe"]) if inner["sharpe"] == inner["sharpe"] else 0.0,
        win_rate=float(inner["win_rate"]) if inner["win_rate"] == inner["win_rate"] else 0.0,
        total_pnl_pct=float(inner["total_pnl_pct"]),
        bars_per_year=bars_per_year,
        equity_curve=equity_curve,
        equity_timestamps=equity_timestamps,
        runner_label=f"ATR breakout {interval} {symbol} (LOCKED)",
        start=start_date.isoformat(),
        end=end_date.isoformat(),
    )
```

- [ ] **Step 5: Run tests, verify PASS**

```bash
.venv/bin/pytest tests/integration/test_atr_breakout_dashboard_contract.py -v -m integration 2>&1 | tail -10
```

Expected: All PASS (existing + new equity_curve test).

- [ ] **Step 6: mypy strict**

```bash
.venv/bin/mypy --strict src/backtest/atr_breakout_runner.py
```

Expected: 0 errors.

- [ ] **Step 7: Commit + SPRINT_STATE**

```bash
git add src/backtest/atr_breakout_runner.py tests/integration/test_atr_breakout_dashboard_contract.py
git commit -m "feat(s43): atr_breakout_runner passes df timestamps к envelope для equity chart"
git add llm-wiki/wiki/project/SPRINT_STATE.md
git commit -m "docs(sprint): SPRINT_STATE update phase=4 task=T4 done"
```

---

## Task 5: volume_breakout_runner — same timestamps wiring

**Files:**
- Modify: `src/backtest/volume_breakout_runner.py`
- Modify: `tests/integration/test_volume_breakout_dashboard_contract.py`

- [ ] **Step 1: Write failing test**

Append к `tests/integration/test_volume_breakout_dashboard_contract.py`:

```python
@pytest.mark.integration
def test_volume_breakout_envelope_includes_equity_curve_timestamps() -> None:
    """S43 T5 — volume_breakout runner passes df timestamps к envelope."""
    from datetime import date
    from src.backtest.volume_breakout_runner import run_volume_breakout_backtest
    r = run_volume_breakout_backtest(
        symbol="BTCUSDT", interval="240",
        start_date=date(2023, 1, 1), end_date=date(2026, 4, 26),
    )
    ec = r["equity_curve"]
    assert len(ec["timestamps"]) == len(ec["equity_pct"])
    assert len(ec["timestamps"]) >= 100  # ~114 trades + 1 starting zero
    assert ec["timestamps"][0] >= 1672531200  # 2023-01-01 unix
    assert ec["equity_pct"][0] == 0.0
    assert abs(ec["equity_pct"][-1] - 122.66) < 5.0  # S39 baseline
```

- [ ] **Step 2: Run, verify FAIL**

```bash
.venv/bin/pytest tests/integration/test_volume_breakout_dashboard_contract.py::test_volume_breakout_envelope_includes_equity_curve_timestamps -v -m integration
```

Expected: FAIL.

- [ ] **Step 3: Modify `run_volume_breakout_backtest`**

In `src/backtest/volume_breakout_runner.py::run_volume_breakout_backtest`, find existing block:

```python
    # Build equity_curve from trades list для sub-period robustness chip
    trades_list = inner.get("trades", [])
    equity_curve: list[float] = [0.0]
    for tr in trades_list:
        equity_curve.append(equity_curve[-1] + (tr.pnl_pct * 100.0))
```

Replace с (note volume_breakout uses `_load_ohlcv` which may have different timestamp column name — verify before editing):

```python
    # S43 T5 — Build equity_curve + timestamps parallel arrays для uPlot.
    trades_list = inner.get("trades", [])
    equity_curve: list[float] = [0.0]
    equity_timestamps: list[int] = []
    if trades_list and not df.empty:
        # df from _load_ohlcv has datetime index; verify column structure
        # If df has "ts" or "time" column → use it; else use df.index
        ts_col = None
        for candidate in ("_ts", "ts", "time"):
            if candidate in df.columns:
                ts_col = candidate
                break
        if ts_col is not None:
            ts_series = df[ts_col]
        else:
            # Fall back к index (DatetimeIndex)
            ts_series = df.index
        equity_timestamps.append(int(ts_series.iloc[0].timestamp() if hasattr(ts_series, "iloc") else ts_series[0].timestamp()))
        for tr in trades_list:
            equity_curve.append(equity_curve[-1] + (tr.pnl_pct * 100.0))
            ts_value = ts_series.iloc[tr.exit_idx] if hasattr(ts_series, "iloc") else ts_series[tr.exit_idx]
            equity_timestamps.append(int(ts_value.timestamp()))
```

- [ ] **Step 4: Modify envelope call**

In the same function, find existing `build_research_runner_envelope(...)` call. Add `equity_timestamps=equity_timestamps,` keyword (insert anywhere before closing `)`):

```python
    return build_research_runner_envelope(
        runner_name="volume_breakout_runner",
        symbol=symbol,
        interval=interval,
        n_trades=int(inner["n_trades"]),
        sharpe=float(inner["sharpe"]) if inner["sharpe"] == inner["sharpe"] else 0.0,
        win_rate=float(inner["win_rate"]) if inner["win_rate"] == inner["win_rate"] else 0.0,
        total_pnl_pct=float(inner["total_pnl_pct"]),
        bars_per_year=bars_per_year,
        equity_curve=equity_curve,
        equity_timestamps=equity_timestamps,
        runner_label=f"Volume breakout {interval} {symbol} (LOCKED — S39)",
        start=start_date.isoformat(),
        end=end_date.isoformat(),
    )
```

- [ ] **Step 5: Run tests, verify PASS**

```bash
.venv/bin/pytest tests/integration/test_volume_breakout_dashboard_contract.py -v -m integration
```

Expected: All PASS.

- [ ] **Step 6: mypy strict**

```bash
.venv/bin/mypy --strict src/backtest/volume_breakout_runner.py
```

Expected: 0 errors.

- [ ] **Step 7: Commit + SPRINT_STATE**

```bash
git add src/backtest/volume_breakout_runner.py tests/integration/test_volume_breakout_dashboard_contract.py
git commit -m "feat(s43): volume_breakout_runner passes df timestamps к envelope для equity chart"
git add llm-wiki/wiki/project/SPRINT_STATE.md
git commit -m "docs(sprint): SPRINT_STATE update phase=4 task=T5 done"
```

---

## Task 6: Vendor uPlot library

**Files:**
- Create: `src/dashboard/static/vendor/uPlot.iife.min.js`
- Create: `src/dashboard/static/vendor/uPlot.min.css`

- [ ] **Step 1: Create vendor directory and download uPlot v1.6.31**

```bash
mkdir -p src/dashboard/static/vendor
curl -sSL -o src/dashboard/static/vendor/uPlot.iife.min.js \
  https://cdn.jsdelivr.net/npm/uplot@1.6.31/dist/uPlot.iife.min.js
curl -sSL -o src/dashboard/static/vendor/uPlot.min.css \
  https://cdn.jsdelivr.net/npm/uplot@1.6.31/dist/uPlot.min.css
```

- [ ] **Step 2: Verify checksums and file sizes**

```bash
ls -la src/dashboard/static/vendor/
# Expected: uPlot.iife.min.js ~40-45KB, uPlot.min.css ~3-4KB
file src/dashboard/static/vendor/uPlot.iife.min.js
# Expected: ASCII text / JavaScript file
head -c 200 src/dashboard/static/vendor/uPlot.iife.min.js
# Expected: contains "uPlot" identifier и copyright comment
```

- [ ] **Step 3: Verify uPlot loads без error (smoke)**

```bash
.venv/bin/python -c "
from pathlib import Path
js = Path('src/dashboard/static/vendor/uPlot.iife.min.js').read_text()
assert 'uPlot' in js
assert len(js) > 30000  # min plausible size for uPlot
print(f'uPlot.iife.min.js {len(js):,} bytes OK')
css = Path('src/dashboard/static/vendor/uPlot.min.css').read_text()
assert '.uplot' in css OR '.u-' in css
print(f'uPlot.min.css {len(css):,} bytes OK')
"
```

Expected: both files load + size sanity checks pass.

- [ ] **Step 4: Commit**

```bash
git add src/dashboard/static/vendor/
git commit -m "vendor(s43): add uPlot v1.6.31 library (~45KB JS + ~4KB CSS) для equity chart"
```

- [ ] **Step 5: SPRINT_STATE update T6 done**

---

## Task 7: Template — description block + chart div + uPlot script tag

**Files:**
- Modify: `src/dashboard/templates/index.html`

- [ ] **Step 1: Add uPlot CSS link to `<head>`**

Find existing in `src/dashboard/templates/index.html` (line ~10):

```html
  <link rel="stylesheet" href="/static/dashboard.css?v={{ css_v }}">
```

Insert AFTER (above closing `</head>`):

```html
  <link rel="stylesheet" href="/static/vendor/uPlot.min.css">
```

- [ ] **Step 2: Add description block к configure section**

Find existing form в template (line ~58-89). After the `<select>` для STRATEGY (line ~61), and BEFORE the SYMBOL `<label>` (line ~63), insert NEW collapsible block — but actually we want description AFTER the entire form. Insert AFTER the closing `</form>` (line ~88), BEFORE `<div id="data-info">`:

```html
        <div id="strategy-description" class="strategy-description-block">
          <button type="button" id="strategy-description-toggle" class="description-toggle" aria-expanded="true">
            <span class="toggle-arrow">▾</span> STRATEGY LOGIC
          </button>
          <div id="strategy-description-body" class="description-body"></div>
        </div>
```

- [ ] **Step 3: Add equity chart div к results section**

Find existing in template — locate the verdict-panel block (~line 91-95):

```html
        <div class="panel verdict-panel" id="verdict-panel">
          <div class="panel-label">&gt; VERDICT</div>
          <div id="run-meta" class="run-meta"></div>
          <div id="verdict" class="verdict-block"></div>
        </div>
```

Insert IMMEDIATELY AFTER this panel closing `</div>`, BEFORE the next `<div class="panel" id="warnings-panel" ...>`:

```html
        <div class="panel" id="equity-chart-panel">
          <div class="panel-label">&gt; EQUITY CURVE</div>
          <div id="equity-chart-container" class="equity-chart-container">
            <div id="equity-chart"></div>
            <div id="equity-chart-placeholder" class="equity-placeholder" style="display:none;">
              ▸ EQUITY CURVE NOT AVAILABLE — WFA path uses replay engine (no per-trade timestamps).
            </div>
          </div>
        </div>
```

- [ ] **Step 4: Add uPlot script tag**

Find at end of template (line ~184):

```html
  <script src="/static/dashboard.js?v={{ js_v }}"></script>
```

Insert IMMEDIATELY BEFORE (so uPlot loads first):

```html
  <script src="/static/vendor/uPlot.iife.min.js"></script>
```

- [ ] **Step 5: Verify template renders без error**

```bash
.venv/bin/python -c "
from src.dashboard.app import create_app
from fastapi.testclient import TestClient
c = TestClient(create_app())
r = c.get('/')
assert r.status_code == 200
assert 'strategy-description' in r.text
assert 'equity-chart' in r.text
assert 'uPlot.iife.min.js' in r.text
assert 'uPlot.min.css' in r.text
print('Template renders с new blocks OK')
"
```

Expected: prints OK.

- [ ] **Step 6: Commit + SPRINT_STATE**

```bash
git add src/dashboard/templates/index.html
git commit -m "feat(s43): template — strategy description block + equity chart panel + uPlot script"
git add llm-wiki/wiki/project/SPRINT_STATE.md
git commit -m "docs(sprint): SPRINT_STATE update phase=4 task=T7 done"
```

---

## Task 8: JS — optgroup dropdown rendering

**Files:**
- Modify: `src/dashboard/static/dashboard.js` (function `init` lines ~51-95)

- [ ] **Step 1: Read existing `init()` function structure**

Located at `src/dashboard/static/dashboard.js:51`. Specifically the strategy dropdown population (lines 60-66):

```javascript
    const stratSel = $("strategy-select");
    for (const sid in strategies) {
      const opt = document.createElement("option");
      opt.value = sid;
      opt.textContent = strategies[sid].label;
      stratSel.appendChild(opt);
    }
```

- [ ] **Step 2: Replace с optgroup rendering**

Replace lines 60-66 с:

```javascript
    const stratSel = $("strategy-select");
    // S43 T8 — group strategies by `optgroup` field (Тренд-следование / Возврат / Прорывы)
    const groupOrder = ["Тренд-следование", "Возврат к среднему", "Прорывы"];
    const grouped = {};
    for (const sid in strategies) {
      const grp = strategies[sid].optgroup || "Прочие";
      if (!grouped[grp]) grouped[grp] = [];
      grouped[grp].push({ sid, ...strategies[sid] });
    }
    // Render groups в defined order, then any remaining
    const renderedGroups = new Set();
    for (const grp of groupOrder) {
      if (!grouped[grp]) continue;
      const og = document.createElement("optgroup");
      og.label = grp;
      grouped[grp].forEach(({ sid, label }) => {
        const opt = document.createElement("option");
        opt.value = sid;
        opt.textContent = label;
        og.appendChild(opt);
      });
      stratSel.appendChild(og);
      renderedGroups.add(grp);
    }
    // Catch-all для unknown groups (sanity)
    for (const grp in grouped) {
      if (renderedGroups.has(grp)) continue;
      const og = document.createElement("optgroup");
      og.label = grp;
      grouped[grp].forEach(({ sid, label }) => {
        const opt = document.createElement("option");
        opt.value = sid;
        opt.textContent = label;
        og.appendChild(opt);
      });
      stratSel.appendChild(og);
    }
```

- [ ] **Step 3: Manual smoke test**

```bash
lsof -ti:8000 | xargs -r kill -9 2>/dev/null
sleep 1
./scripts/start-bot.sh &
BOT_PID=$!
sleep 5
# Verify HTML page contains optgroup
curl -s http://127.0.0.1:8000/ | grep -c "optgroup\|select" | head
# Verify endpoint returns optgroup field
curl -s http://127.0.0.1:8000/api/strategies | python3 -c "import json,sys; d=json.load(sys.stdin); [print(f\"  {sid}: {p['label']} → {p.get('optgroup','?')}\") for sid,p in d.items()]"
kill $BOT_PID 2>/dev/null
wait 2>/dev/null
```

Expected: 6 strategies listed с groups visible. Operator opens browser → dropdown shows `<optgroup>` headers.

- [ ] **Step 4: Commit + SPRINT_STATE**

```bash
git add src/dashboard/static/dashboard.js
git commit -m "feat(s43): JS optgroup dropdown grouping (Тренд / Возврат / Прорывы)"
git add llm-wiki/wiki/project/SPRINT_STATE.md
git commit -m "docs(sprint): SPRINT_STATE update phase=4 task=T8 done"
```

---

## Task 9: JS — description block render + toggle

**Files:**
- Modify: `src/dashboard/static/dashboard.js` (init() and applyComboGates())

- [ ] **Step 1: Add description render function**

Find existing `applyComboGates()` function (around line 140). After its closing `}` (around line 185), insert NEW function:

```javascript
// ──────────────────────────────────────────────
//  S43 T9 — STRATEGY DESCRIPTION BLOCK
// ──────────────────────────────────────────────
function renderStrategyDescription(strategyId) {
  const body = $("strategy-description-body");
  if (!body) return;
  // Use cached info from applyComboGates flow (S42 T6 cache)
  const info = _strategyInfoCache[strategyId];
  if (!info || !info.description) {
    body.innerHTML = '<div class="description-empty">No description available.</div>';
    return;
  }
  // description is pre-authored HTML (XSS-safe — comes from STRATEGY_PRESETS dict, not user input)
  body.innerHTML = info.description;
}

function setupStrategyDescriptionToggle() {
  const btn = $("strategy-description-toggle");
  const body = $("strategy-description-body");
  if (!btn || !body) return;
  btn.addEventListener("click", () => {
    const expanded = btn.getAttribute("aria-expanded") === "true";
    btn.setAttribute("aria-expanded", String(!expanded));
    body.style.display = expanded ? "none" : "block";
    btn.querySelector(".toggle-arrow").textContent = expanded ? "▸" : "▾";
  });
}
```

- [ ] **Step 2: Wire description rendering к init() + strategy change**

In `init()` function (line ~84-90), find:

```javascript
    stratSel.addEventListener("change", () => {
      applyComboGates(stratSel.value);
    });
```

Replace с (add description render call):

```javascript
    stratSel.addEventListener("change", async () => {
      await applyComboGates(stratSel.value);
      renderStrategyDescription(stratSel.value);
    });
    setupStrategyDescriptionToggle();
```

Also AFTER existing line `applyComboGates(stratSel.value);` (initial call ~line 90), add:

```javascript
    // Initial render description для default selected strategy
    setTimeout(() => renderStrategyDescription(stratSel.value), 100);  // wait for cache populated
```

- [ ] **Step 3: Verify `applyComboGates()` populates cache `_strategyInfoCache` (already does)**

Sanity check — function `fetchStrategyInfo` (line ~125) already caches к `_strategyInfoCache[strategyId]`. No change needed.

- [ ] **Step 4: Manual smoke test**

```bash
lsof -ti:8000 | xargs -r kill -9 2>/dev/null
sleep 1
./scripts/start-bot.sh &
BOT_PID=$!
sleep 5
# Open browser and verify
echo "Open http://127.0.0.1:8000/ in browser"
echo "1. Verify STRATEGY LOGIC block visible by default"
echo "2. Switch dropdown — description updates"
echo "3. Click toggle — block collapses + arrow rotates"
echo "Bot running with PID $BOT_PID — kill when done"
sleep 30  # give operator time к verify
kill $BOT_PID 2>/dev/null
wait 2>/dev/null
```

- [ ] **Step 5: Commit + SPRINT_STATE**

```bash
git add src/dashboard/static/dashboard.js
git commit -m "feat(s43): JS strategy description block render + collapsible toggle"
git add llm-wiki/wiki/project/SPRINT_STATE.md
git commit -m "docs(sprint): SPRINT_STATE update phase=4 task=T9 done"
```

---

## Task 10: JS — equity curve chart render via uPlot

**Files:**
- Modify: `src/dashboard/static/dashboard.js` (renderResult function)

- [ ] **Step 1: Add equity chart render function**

After `renderStrategyDescription()` function (added in T9), insert NEW:

```javascript
// ──────────────────────────────────────────────
//  S43 T10 — EQUITY CURVE CHART (uPlot)
// ──────────────────────────────────────────────
let _equityChart = null;  // module-level uPlot instance (destroy + recreate per backtest)

function renderEquityChart(r) {
  const container = $("equity-chart");
  const placeholder = $("equity-chart-placeholder");
  const ec = r.equity_curve || {};
  const timestamps = ec.timestamps || [];
  const equity = ec.equity_pct || [];
  // CC3 — empty data guard (legacy WFA presets без envelope)
  if (timestamps.length === 0 || equity.length === 0) {
    container.style.display = "none";
    placeholder.style.display = "block";
    return;
  }
  container.style.display = "block";
  placeholder.style.display = "none";
  // Destroy previous chart instance
  if (_equityChart) {
    _equityChart.destroy();
    _equityChart = null;
  }
  // uPlot data: [timestamps_unix_seconds, series1_values]
  const data = [timestamps, equity];
  const opts = {
    width: container.clientWidth || 800,
    height: 300,
    title: "",
    cursor: { drag: { x: true, y: false } },
    series: [
      { label: "Date" },
      {
        label: "Equity %",
        stroke: "#26ff8c",   // terminal green
        fill: "rgba(38, 255, 140, 0.12)",
        width: 1.5,
        points: { show: false },
      },
    ],
    axes: [
      {
        stroke: "#9ca3af",
        grid: { stroke: "rgba(156, 163, 175, 0.10)", width: 1 },
        ticks: { stroke: "#9ca3af" },
        font: "11px JetBrains Mono, monospace",
      },
      {
        stroke: "#9ca3af",
        grid: { stroke: "rgba(156, 163, 175, 0.10)", width: 1 },
        ticks: { stroke: "#9ca3af" },
        font: "11px JetBrains Mono, monospace",
        values: (u, vals) => vals.map((v) => v.toFixed(0) + "%"),
      },
    ],
    scales: { x: { time: true } },
    legend: { show: false },
  };
  _equityChart = new uPlot(opts, data, container);
}
```

- [ ] **Step 2: Wire renderEquityChart() into renderResult()**

Find existing `renderResult(r)` function (line ~262). At end of function, BEFORE the closing line `$("results-section").scrollIntoView(...)` (~line 359), insert:

```javascript
  // S43 T10 — render equity chart
  renderEquityChart(r);
```

- [ ] **Step 3: Manual smoke test**

```bash
lsof -ti:8000 | xargs -r kill -9 2>/dev/null
sleep 1
./scripts/start-bot.sh &
BOT_PID=$!
sleep 5
echo "Open http://127.0.0.1:8000/"
echo "1. Pick atr_breakout, BTCUSDT, 4 hours, 2017-08-17 → 2026-04-30 → run"
echo "2. Verify equity chart appears с green line + area fill"
echo "3. Pick ema_crossover_s13, BTCUSDT, 1h → run (legacy WFA preset)"
echo "4. Verify placeholder shown 'EQUITY CURVE NOT AVAILABLE — WFA path uses replay engine'"
sleep 60
kill $BOT_PID 2>/dev/null
wait 2>/dev/null
```

- [ ] **Step 4: Commit + SPRINT_STATE**

```bash
git add src/dashboard/static/dashboard.js
git commit -m "feat(s43): JS equity chart render via uPlot + empty-data placeholder для WFA presets"
git add llm-wiki/wiki/project/SPRINT_STATE.md
git commit -m "docs(sprint): SPRINT_STATE update phase=4 task=T10 done"
```

---

## Task 11: CSS — terminal-themed uPlot overrides + description block styling

**Files:**
- Modify: `src/dashboard/static/dashboard.css`

- [ ] **Step 1: Append CSS rules**

Append к END of `src/dashboard/static/dashboard.css`:

```css
/* ─────────────────────────────────────────────────
   S43 T11 — Strategy description block
   ───────────────────────────────────────────────── */
.strategy-description-block {
  margin-top: var(--space-4, 1rem);
  border: 1px solid rgba(156, 163, 175, 0.20);
  background: rgba(0, 0, 0, 0.20);
  padding: var(--space-3, 0.75rem);
  border-radius: 2px;
}

.description-toggle {
  background: transparent;
  border: none;
  color: var(--text-muted, #9ca3af);
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  cursor: pointer;
  padding: 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  text-align: left;
}

.description-toggle:hover {
  color: #26ff8c;
}

.toggle-arrow {
  display: inline-block;
  transition: transform 0.15s ease;
}

.description-body {
  margin-top: var(--space-3, 0.75rem);
  color: #d1d5db;
  font-size: 0.875rem;
  line-height: 1.6;
  font-family: 'Fraunces', Georgia, serif;  /* readable serif для prose */
}

.description-body p {
  margin: 0 0 var(--space-2, 0.5rem) 0;
}

.description-body strong {
  color: #26ff8c;
  font-weight: 600;
}

.description-empty {
  color: var(--text-muted, #9ca3af);
  font-style: italic;
  font-size: 0.75rem;
}

/* ─────────────────────────────────────────────────
   S43 T11 — Equity chart (uPlot terminal overrides)
   ───────────────────────────────────────────────── */
.equity-chart-container {
  width: 100%;
  min-height: 320px;
  padding: var(--space-3, 0.75rem) 0;
  background: rgba(0, 0, 0, 0.20);
}

.equity-placeholder {
  padding: var(--space-6, 1.5rem);
  text-align: center;
  color: var(--text-muted, #9ca3af);
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  border: 1px dashed rgba(156, 163, 175, 0.30);
}

/* uPlot library overrides — match terminal aesthetic */
.uplot {
  font-family: 'JetBrains Mono', monospace !important;
}

.uplot .u-axis {
  color: #9ca3af;
}

.uplot .u-cursor-x,
.uplot .u-cursor-y {
  background: rgba(38, 255, 140, 0.30) !important;
}

.uplot .u-select {
  background: rgba(38, 255, 140, 0.10) !important;
  border-left: 1px solid #26ff8c;
  border-right: 1px solid #26ff8c;
}

.uplot .u-legend {
  display: none;
}
```

- [ ] **Step 2: Manual smoke verify**

```bash
lsof -ti:8000 | xargs -r kill -9 2>/dev/null
sleep 1
./scripts/start-bot.sh &
sleep 5
echo "Open browser. Verify:"
echo "1. Description block has subtle border + dark background"
echo "2. Toggle button readable, arrow rotates on click"
echo "3. <strong> tags green colored"
echo "4. Equity chart has dark background, green line + area"
echo "5. Hover shows green crosshair"
sleep 30
lsof -ti:8000 | xargs -r kill -9 2>/dev/null
```

- [ ] **Step 3: Commit + SPRINT_STATE**

```bash
git add src/dashboard/static/dashboard.css
git commit -m "feat(s43): CSS — description block styling + uPlot terminal palette overrides"
git add llm-wiki/wiki/project/SPRINT_STATE.md
git commit -m "docs(sprint): SPRINT_STATE update phase=4 task=T11 done"
```

---

## Task 12: ADR 0063 + sprint-43 page + wiki sync

**Files:**
- Create: `llm-wiki/wiki/project/decisions/0063-sprint-43-ui-polish.md`
- Create: `llm-wiki/wiki/project/sprints/sprint-43-ui-polish.md`
- Modify: `llm-wiki/wiki/project/architecture/current-state.md`
- Modify: `llm-wiki/wiki/index.md`
- Append: `llm-wiki/wiki/log.md`

- [ ] **Step 1: Create ADR 0063**

```markdown
---
title: "0063. Sprint 43 — UI polish (preset rename + descriptions + equity chart)"
type: decision
tags: [adr, sprint-43, ui, dashboard, equity-chart, uplot]
created: 2026-05-10
updated: 2026-05-10
status: accepted
sources:
  - llm-wiki/wiki/project/pre-s43-backlog.md
  - llm-wiki/wiki/project/plans/2026-05-10-sprint-43-ui-polish.md
---

# 0063. Sprint 43 — UI polish (preset rename + descriptions + equity chart)

**Status:** accepted
**Date:** 2026-05-10

## Контекст

Operator после S42 запросил три UI улучшения для dashboard: (1) переименовать preset labels к semantic Russian names с группировкой по trading approach (вместо текущих `[S13 baseline] EMA crossover`), (2) показать ~150-word RU description при выборе стратегии, (3) добавить equity curve chart как на reference screenshots.

WFA retrofit (deferred S42→S43→) → moved к S44 (independent, touches PnL accounting).

## Варианты

(a) Принять scope as-is — UI polish only, WFA → S44.
(b) Объединить WFA retrofit + UI polish — heavy sprint, risk delay.
(c) Defer all к S44+.

## Решение

**Option (a) — UI polish only S43, WFA retrofit к S44.**

Verdicts ROUND 1 trader-expert (5 CONFIRM + 2 REVISE):
- Q1 REVISE → `<optgroup>` grouping (a-option two-line label rejected: native `<option>` styling unreliable)
- Q4 REVISE → parallel arrays format `{timestamps: [...], equity_pct: [...]}` (uPlot native API)
- Other 5: CONFIRM

Library choice: uPlot v1.6.31 (vendored locally, ~45KB JS + ~4KB CSS). Sharp lines + area fill match terminal aesthetic.

Description authoring: inline в `STRATEGY_PRESETS` dict (YAGNI, ~6KB total growth).

## Последствия

**Pros:**
- Dropdown grouped по trading approach (Тренд / Возврат / Прорывы) — easier navigation.
- Operator видит strategy logic перед running backtest — reduces "blind run" risk.
- Equity chart visualization restores parity с reference screenshots.
- uPlot vendored locally — no CDN dependency, no build step.

**Cons:**
- 6KB STRATEGY_PRESETS file growth (descriptions).
- ~50KB static asset bundle (uPlot js+css).
- Legacy WFA presets (ema/mean_reversion/donchian) lack equity_curve in envelope → placeholder shown.

**Carry-overs к S44:**
- WFA retrofit (PnL accounting fix + DSR + MC + T1-T6 acceptance gate restoration).
- Drawdown subchart, per-trade markers, monthly returns heatmap (deferred from S43 MVP).
- Legacy WFA preset envelope adoption (currently bypasses envelope contract).

## Verification

- Unit tests: 946+8 = 954 passed.
- Integration tests: 52+2 = 54 passed.
- mypy --strict: 0 errors.
- Canonical counts: 16/30/74/56 unchanged.
- Manual smoke: dropdown shows 3 optgroups + 6 strategies; description block renders на каждый switch; equity chart shows для atr_breakout/volume_breakout, placeholder для legacy presets.

## Связанные

- [[../sprints/sprint-43-ui-polish]]
- [[../plans/2026-05-10-sprint-43-ui-polish]]
- [[../pre-s43-backlog]]
- [[0062-sprint-42-atr-breakout-hardening]]
```

- [ ] **Step 2: Create sprint-43 page**

Create `llm-wiki/wiki/project/sprints/sprint-43-ui-polish.md`:

```markdown
---
title: "Sprint 43 — UI polish (preset rename + descriptions + equity chart)"
type: sprint
tags: [sprint-43, ui, dashboard, equity-chart, uplot]
created: 2026-05-10
updated: 2026-05-10
status: completed
sources:
  - llm-wiki/wiki/project/decisions/0063-sprint-43-ui-polish.md
  - llm-wiki/wiki/project/plans/2026-05-10-sprint-43-ui-polish.md
  - llm-wiki/wiki/project/pre-s43-backlog.md
---

# Sprint 43 — UI polish

## Цель

Переименовать presets к semantic Russian names с optgroup grouping, добавить strategy description block, добавить equity curve chart на dashboard.

## Доставленная функциональность

### Код
- `src/dashboard/backtest_runner.py` — STRATEGY_PRESETS rename + description + optgroup fields для всех 6 presets
- `src/dashboard/app.py` — `/api/strategies` + `/api/strategy/{id}/info` extended с description + optgroup
- `src/backtest/research_runner_envelope.py` — equity_curve parallel arrays format `{timestamps, equity_pct}`
- `src/backtest/atr_breakout_runner.py` — passes df timestamps к envelope
- `src/backtest/volume_breakout_runner.py` — same
- `src/dashboard/static/vendor/uPlot.iife.min.js` + `uPlot.min.css` — uPlot v1.6.31 vendored
- `src/dashboard/templates/index.html` — description block + equity chart panel + uPlot script
- `src/dashboard/static/dashboard.js` — optgroup rendering + description toggle + equity chart render
- `src/dashboard/static/dashboard.css` — description styling + uPlot terminal overrides

### Тесты
- `tests/unit/test_preset_metadata.py` (NEW) — 4 tests (description + optgroup fields, rename mapping)
- `tests/unit/test_supported_combos_endpoint.py` — 2 new tests (description + optgroup в endpoints)
- `tests/unit/test_research_runner_envelope.py` — 3 new tests (equity_curve parallel arrays)
- `tests/integration/test_atr_breakout_dashboard_contract.py` — 1 new test (equity_curve timestamps presence)
- `tests/integration/test_volume_breakout_dashboard_contract.py` — 1 new test (equity_curve timestamps presence)

### Wiki
- ADR 0063 (THIS sprint) accepted
- sprint-43 page (THIS file)
- current-state.md sprint history row + ADR count 62→63 + sprint pages 46→47
- index.md ADR 0063 + sprint-43 entries
- log.md S43 sprint-end entry

### FSM рост
**0** (UNCHANGED — pure UI work).

### Reason codes
**0 новых** (UNCHANGED 56).

### Tests/качество
- Unit: 946 → ~955 (+9: 4 metadata + 2 endpoint + 3 envelope)
- Integration: 52 → ~54 (+2 equity_curve tests)
- mypy --strict: 0 errors
- ruff/format: чисто
- Canonical: 16/30/74/56 (UNCHANGED)

## Решения и отклонения

- **Q1 REVISE:** Maintainer recommended two-line label (semantic + technical). Trader rejected — native `<option>` styling unreliable между browsers. Final: `<optgroup>` grouping by trading approach.
- **Q4 REVISE:** Maintainer recommended array of `{ts, equity_pct}` objects. Trader rejected — uPlot native API expects parallel arrays `[[timestamps], [values]]`, object-of-arrays saves ~30% bytes + zero conversion. Final: `{timestamps: [unix_int...], equity_pct: [float...]}`.

Other 5 questions CONFIRM.

## Влияние на следующие спринты

**S44 (BLOCKING):**
- Resolve atr_breakout_runner sequential-additive vs replay engine Kelly-compounded PnL accounting gap.
- Wrap full WFA + DSR + MC + T1-T6 acceptance gate.
- Restore epistemic discipline (currently `verdict: "RAW"` для research presets).
- Adopt legacy WFA presets (ema/mean_reversion/donchian) к envelope contract → enable equity_curve для них too.

**Future polish (deferred):**
- Drawdown subchart pane.
- Per-trade markers (entry/exit dots на equity chart).
- Monthly returns heatmap.

## Перенесённые задачи

Все S38 carry-overs (F8 block_size, M1-M4 bybit-api, Item #7 shim, Item #10) — unaffected, остаются в backlog.

## Связанные

- [[../decisions/0063-sprint-43-ui-polish]]
- [[../plans/2026-05-10-sprint-43-ui-polish]]
- [[../pre-s43-backlog]]
```

- [ ] **Step 3: Update current-state.md**

In `llm-wiki/wiki/project/architecture/current-state.md`:

- Update header: `# Current State (post-S43, 2026-05-10) — UI polish (preset rename + equity chart, tag v0.1.0-alpha.43)`
- Increment ADR count: `**62**` → `**63**` (S43 = ADR 0063)
- Increment sprint pages: `**46**` → `**47**`
- Append к sprint history table:
  ```
  | S43 | 0063 | v0.1.0-alpha.43 | 2026-05-10 | UI polish — preset rename к semantic RU + optgroup + description block + equity chart (uPlot) |
  ```

Other rows (FSM/reason codes/components) UNCHANGED.

- [ ] **Step 4: Update index.md**

After existing sprint-42 entry, append:
```
- [[project/sprints/sprint-43-ui-polish]] 🆕 (S43, 2026-05-10): **UI polish.** Переименование presets к semantic RU + optgroup grouping (Тренд / Возврат / Прорывы) + per-strategy description block + equity curve chart (uPlot v1.6.31 vendored). 955 unit / 54 integration / mypy 0. Tag v0.1.0-alpha.43.
```

After existing ADR 0062 entry, append:
```
- [[project/decisions/0063-sprint-43-ui-polish]] 🆕 — ADR 0063 S43 UI polish. Preset rename + optgroup + description block + uPlot equity chart. Q1+Q4 REVISE accepted (optgroup over two-line label, parallel arrays over array-of-objects).
```

- [ ] **Step 5: Append к log.md**

```markdown

## [2026-05-10] sprint-end | S43 — UI polish (preset rename + descriptions + equity chart)

- **Sprint:** S43 — feature/sprint-43-ui-polish → main
- **ADR:** ADR 0063
- **Tasks done (12):** T1 preset rename + description + optgroup / T2 endpoint extensions / T3 envelope equity_curve / T4 atr_breakout timestamps / T5 volume_breakout timestamps / T6 vendor uPlot / T7 template / T8 JS optgroup / T9 JS description block / T10 JS equity chart / T11 CSS / T12 wiki sync
- **UI improvements:** dropdown grouped by trading approach, per-strategy description block (~150 words RU), equity curve chart (uPlot, terminal-themed)
- **Tests:** ~955 unit (+9) / ~54 integration (+2) / mypy 0 / ruff 0
- **Canonical counts:** 16/30/74/56 (UNCHANGED)
- **ADRs:** 62 → **63** / **Sprint pages:** 46 → **47**
- **Tag:** v0.1.0-alpha.43
- **Carry к S44:** WFA retrofit (atr_breakout + volume_breakout PnL accounting fix + DSR + MC + T1-T6 acceptance gate). Drawdown chart + per-trade markers + monthly heatmap deferred.
```

- [ ] **Step 6: Commit**

```bash
git add llm-wiki/
git commit -m "docs(s43): wiki sync — ADR 0063 + sprint-43 + index/log/current-state"
```

If pre-commit hook complains (wiki-broken-link, ADR-index-sync) — fix underlying issue, NEW commit.

- [ ] **Step 7: SPRINT_STATE final update phase=8-ship**

Edit `llm-wiki/wiki/project/SPRINT_STATE.md`:
- `phase: 8-ship`
- Mark T12 done
- Phase tracking section с all phases
- Bump `updated:`

```bash
git add llm-wiki/wiki/project/SPRINT_STATE.md
git commit -m "docs(sprint): SPRINT_STATE T12 done, phase=8-ship"
```

---

## PHASE 6 — Domain Reviewers (MANDATORY before merge)

Dispatch 4 reviewers in parallel after T12 commits land:

| Reviewer | Focus |
|----------|-------|
| `dashboard-reviewer` | UI contract compliance, optgroup rendering, description block UX, equity chart accessibility, terminal aesthetic preserved, look-ahead bias prevention, XSS surface для description HTML |
| `python-reviewer` | PEP 8, type hints на envelope changes, defensive guards, no silent exceptions |
| `test-engineer` | Coverage thoroughness, parametrized tests где возможно, regression preserved для existing presets |
| `doc-reviewer` | ADR 0063 wiki-link integrity, frontmatter completeness, current-state count consistency, Block 1↔2 sync |

NO trading-logic-reviewer (pure UI, не trading semantics).

Aggregate findings. Fix blockers before merge.

---

## PHASE 8 — Ship

Use `sprint-finish` skill OR `superpowers:finishing-a-development-branch`:

```bash
.venv/bin/pytest tests/unit tests/integration -q
.venv/bin/mypy --strict src/
git push -u origin feature/sprint-43-ui-polish
gh pr create --title "Sprint 43: UI polish — preset rename + descriptions + equity chart" --body "$(cat <<'EOF'
## Summary
- Rename preset labels к semantic Russian names с optgroup grouping
- Per-strategy description block (~150 words RU each)
- Equity curve chart via uPlot v1.6.31 (vendored)
- ADR 0063 documents Q1+Q4 REVISE rationale

## Test plan
- [ ] All unit + integration tests pass (~955 + 54)
- [ ] Manual smoke: dropdown shows 3 optgroups + 6 strategies
- [ ] Description block toggles, switches на strategy change
- [ ] Equity chart renders для atr_breakout / volume_breakout
- [ ] Placeholder shown для legacy WFA presets (ema/mean_reversion/donchian)
- [ ] No JS console errors
EOF
)"
# squash-merge after reviewer GREEN
git tag -a v0.1.0-alpha.43 -m "Sprint 43 — UI polish (preset rename + descriptions + equity chart)" <merge-sha>
git push origin v0.1.0-alpha.43
```

---

## Self-Review Verification

**Spec coverage:**
- Q1 (optgroup) → T1 + T8
- Q2 (description block) → T1 + T2 + T7 + T9 + T11
- Q3 (uPlot) → T6 + T7 + T10
- Q4 (parallel arrays) → T3 + T4 + T5
- Q5 (inline descriptions) → T1
- Q6 (MVP scope) → T6-T11 (no drawdown/markers)
- Q7 (WFA → S44) → carry-over к S44 noted in ADR + sprint page
- CC1 (uPlot CSS overrides) → T11
- CC3 (empty data guard) → T10
- CC4 (description в /api/strategies) → T2

**Type consistency:**
- `description: str` consistent T1/T2/T9
- `optgroup: str` consistent T1/T2/T8
- `equity_curve: {timestamps: list[int], equity_pct: list[float]}` consistent T3/T4/T5/T10
- `equity_timestamps` keyword consistent T3 (envelope) ↔ T4/T5 (runners)

**Placeholder scan:** None — all code blocks complete.

**Plan complete and saved to `llm-wiki/wiki/project/plans/2026-05-10-sprint-43-ui-polish.md`.**
