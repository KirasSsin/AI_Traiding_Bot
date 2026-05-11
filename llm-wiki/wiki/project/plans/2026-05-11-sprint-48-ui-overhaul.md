---
title: "Sprint 48 Plan — UI Overhaul (9 жалоб + Bybit balance + Glossary вкладка)"
type: plan
tags: [sprint-48, ui-overhaul, glossary, bybit-balance, dashboard, plan]
created: 2026-05-11
updated: 2026-05-11
status: locked
sources:
  - llm-wiki/wiki/project/pre-s48-backlog.md
  - llm-wiki/wiki/project/SPRINT_STATE.md
  - llm-wiki/wiki/project/sprints/sprint-47-tech-debt-carryovers.md
---

# Sprint 48 Implementation Plan — UI Overhaul

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (auto-invoked per repo CLAUDE.md operator override 2026-05-10) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 9 operator-surfaced UI complaints (A-I) + integrate Bybit balance fetch как initial backtest capital + add new Glossary tab с RU расшифровкой всех аббревиатур + dynamic per-strategy filter.

**Architecture:** Дополнительный backend layer `account_service.py` для Bybit boundary isolation + new `glossary_data.py` static dict (60-80 entries). Frontend: NEW Glossary tab (section-based, sticky TOC, highlight/dim filter, search) + NEW BalanceBadge + 6 component edits. Cross-tab state via URL query param `?strategy=<id>` (no Context/Zustand). Component subdirs refactor (13→16+ exceeds 15+ threshold).

**Tech Stack:** Python 3.12 + FastAPI + pybit V5 (backend) // React 18 + TypeScript strict + Vite 5 + CSS Modules + uPlot 1.6.31 + Vitest 1.6 + Playwright 1.48 + RTL 16 (frontend).

**Branch:** `feature/sprint-48-ui-overhaul` (создать от main `2e7e7e1`).

**Total tasks:** 24 (6 buckets). Models: opus T1 + T5 + T15 + T16 (judgment-heavy); sonnet others.

**Per-task SPRINT_STATE update protocol (BINDING):** After EACH task complete — edit `llm-wiki/wiki/project/SPRINT_STATE.md` Phase 4 task table + update "Текущий статус" + "Следующее действие" + bump `updated:` frontmatter. Optional commit `docs(sprint): SPRINT_STATE update phase=4 task=Tx done`.

**Architecture binding conditions (per pre-plan validation):**
- **C1 (HIGH):** Bybit balance via `src/dashboard/account_service.py` wrapper. NO direct adapter import в `app.py`.
- **C2 (MEDIUM):** Cross-tab state via URL query param `?strategy=<id>`. NO Context/Zustand/localStorage.
- **C3 (MEDIUM):** Glossary single endpoint `/api/glossary` returns ALL entries с `applies_to: list[str]`. Filter on client.
- **C4 (MEDIUM):** HistoryTab accordion single-open + fetch-on-click + no cache.
- **C5 (MEDIUM):** Component subdirs refactor IN S48 — `components/{tabs,charts,forms,metrics,shared,glossary}/`.

---

## File structure overview

### Files created (NEW)

**Backend:**
- `src/dashboard/account_service.py` — Bybit balance wrapper (T3)
- `src/dashboard/glossary_data.py` — RU glossary dict + STRATEGY_TO_METRICS_MAP (T5)

**Frontend tests + hooks:**
- `src/dashboard_react/src/hooks/useStrategyContext.ts` — URL query param read/write (T18)
- `src/dashboard_react/src/hooks/useBybitBalance.ts` — `/api/bybit/balance` fetch hook (T20)

**Frontend components (subdirs):**
- `src/dashboard_react/src/components/tabs/GlossaryTab.tsx` + `.module.css` (T15)
- `src/dashboard_react/src/components/shared/BalanceBadge.tsx` + `.module.css` (T21)

**Tests:**
- `tests/unit/test_account_service.py` (T3)
- `tests/unit/test_balance_endpoint.py` (T4)
- `tests/unit/test_glossary_data.py` (T5)
- `tests/unit/test_glossary_endpoint.py` (T6)
- `tests/unit/test_replay_engine_equity_curve.py` (T2)
- `src/dashboard_react/src/components/__tests__/HistoryTab.test.tsx` (T14)
- `src/dashboard_react/src/components/__tests__/GlossaryTab.test.tsx` (T15-17)

**Wiki:**
- `llm-wiki/wiki/project/sprints/sprint-48-ui-overhaul.md` (T24)

### Files modified

**Backend:**
- `src/dashboard/app.py` — 2 new endpoints (`/api/bybit/balance` + `/api/glossary`) + remove direct adapter import
- `src/dashboard/backtest_runner.py` — replay engine equity_curve emission (T2) + RunRecord shape verification (T7)

**Frontend (post-refactor paths):**
- `src/dashboard_react/src/components/tabs/HistoryTab.tsx` — accordion expand (T13)
- `src/dashboard_react/src/components/tabs/DocumentationTab.tsx` — remove ▸ prefix (T12)
- `src/dashboard_react/src/components/forms/ConfigureBacktest.tsx` — balance input + badge integration (T22)
- `src/dashboard_react/src/components/charts/EquityChart.tsx` — 3-line tooltip + initialBalance prop (T8)
- `src/dashboard_react/src/components/metrics/MetricsTable.tsx` — divider + grayed informational rows (T10)
- `src/dashboard_react/src/components/shared/FailAnalysisTab.tsx` — chips + Glossary links (T11)
- `src/dashboard_react/src/api/types.ts` — BalanceResponse + GlossaryEntry types
- `src/dashboard_react/src/api/client.ts` — getBalance + getGlossary methods
- `src/dashboard_react/src/App.tsx` — register Glossary tab + 4th nav button (T19)

**Wiki:**
- `llm-wiki/wiki/project/SPRINT_STATE.md` — phase + per-task progress
- `llm-wiki/wiki/index.md` — sprint-48 + glossary references
- `llm-wiki/wiki/log.md` — S48 sprint-end entry
- `llm-wiki/wiki/project/architecture/current-state.md` — header + sprint history row
- `CLAUDE.md` — Language rules update + Bug I anti-pattern table

### Reviewer matrix PHASE 6

| Reviewer | Tasks |
|---|---|
| python-reviewer | T2, T3, T4, T5, T6, T7, T11 (backend) |
| bybit-api-reviewer | T3 (account.get_wallet_balance integration) |
| security-auditor | T3, T4 (Bybit auth + balance fetch — money-adjacent surface, READ-only) |
| frontend-developer | T1, T8-T22 (PRIMARY — все React components + hooks + UX features) |
| architecture-reviewer | T1 (subdirs C5) + T18 (URL query state C2) + T6 (single endpoint C3) + T13 (accordion C4) — verify binding conditions |
| trading-logic-reviewer | T10 (informational distinction per ADR 0014) + T11 (used/not used semantics) + T13 (RU template correctness) |
| test-engineer | T14, T15-17 RTL coverage + new Vitest tests |
| doc-reviewer | T5 (glossary RU content quality) + T24 (sprint page + wiki sync) |
| data-integrity-reviewer | T7 (RunRecord shape extension если applicable) |

NO dashboard-reviewer (superseded by frontend-developer per S46).

---

## Bucket 0 — Component subdirs refactor

## Task 1: Component subdirs refactor (opus)

**Why opus:** Multi-file import path updates across 13 components + tests + Storybook-like consistency. Low margin error — broken import cascades fail tsc + Vitest + Playwright simultaneously.

**Files:**
- Create directories: `src/dashboard_react/src/components/{tabs,charts,forms,metrics,shared,glossary}/`
- Move (use `git mv`): existing 13 components per mapping below
- Modify: every file importing moved components

**Component → subdir mapping:**

| Component | Target subdir |
|---|---|
| App.tsx | (stays at `src/`) |
| HistoryTab.tsx | `tabs/` |
| DocumentationTab.tsx | `tabs/` |
| EquityChart.tsx | `charts/` |
| DrawdownSubchart.tsx | `charts/` |
| MonthlyHeatmap.tsx | `charts/` |
| ConfigureBacktest.tsx | `forms/` |
| MetricsTable.tsx | `metrics/` |
| TradesTable.tsx | `metrics/` |
| VerdictPanel.tsx | `metrics/` |
| WfaFailBanner.tsx | `shared/` |
| WfaFailBadge.tsx | `shared/` |
| StrategyDescription.tsx | `shared/` |
| FailAnalysisTab.tsx | `shared/` |

(GlossaryTab.tsx будет создан в T15 в `tabs/` — структура готова заранее.)

- [ ] **Step 1: Create subdirs**

```bash
cd /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot
git checkout -b feature/sprint-48-ui-overhaul

cd src/dashboard_react/src/components
mkdir -p tabs charts forms metrics shared glossary
```

- [ ] **Step 2: Move components с git mv (preserves history)**

```bash
# Each pair: source + corresponding .module.css
git mv HistoryTab.tsx tabs/HistoryTab.tsx
git mv HistoryTab.module.css tabs/HistoryTab.module.css
git mv DocumentationTab.tsx tabs/DocumentationTab.tsx
git mv DocumentationTab.module.css tabs/DocumentationTab.module.css

git mv EquityChart.tsx charts/EquityChart.tsx
git mv EquityChart.module.css charts/EquityChart.module.css
git mv DrawdownSubchart.tsx charts/DrawdownSubchart.tsx
git mv DrawdownSubchart.module.css charts/DrawdownSubchart.module.css
git mv MonthlyHeatmap.tsx charts/MonthlyHeatmap.tsx
git mv MonthlyHeatmap.module.css charts/MonthlyHeatmap.module.css

git mv ConfigureBacktest.tsx forms/ConfigureBacktest.tsx
git mv ConfigureBacktest.module.css forms/ConfigureBacktest.module.css

git mv MetricsTable.tsx metrics/MetricsTable.tsx
git mv MetricsTable.module.css metrics/MetricsTable.module.css
git mv TradesTable.tsx metrics/TradesTable.tsx
git mv TradesTable.module.css metrics/TradesTable.module.css
git mv VerdictPanel.tsx metrics/VerdictPanel.tsx
git mv VerdictPanel.module.css metrics/VerdictPanel.module.css

git mv WfaFailBanner.tsx shared/WfaFailBanner.tsx
git mv WfaFailBanner.module.css shared/WfaFailBanner.module.css
git mv WfaFailBadge.tsx shared/WfaFailBadge.tsx
git mv WfaFailBadge.module.css shared/WfaFailBadge.module.css
git mv StrategyDescription.tsx shared/StrategyDescription.tsx
git mv StrategyDescription.module.css shared/StrategyDescription.module.css
git mv FailAnalysisTab.tsx shared/FailAnalysisTab.tsx
git mv FailAnalysisTab.module.css shared/FailAnalysisTab.module.css
```

Move tests subdirectory `__tests__/` if present:
```bash
ls __tests__/  # check
# If present:
mkdir -p tabs/__tests__ charts/__tests__ metrics/__tests__ shared/__tests__
# Move per component subdir
```

- [ ] **Step 3: Update App.tsx imports**

Edit `src/dashboard_react/src/App.tsx`:

```typescript
// Before:
import { HistoryTab } from './components/HistoryTab'
// After:
import { HistoryTab } from './components/tabs/HistoryTab'

// Apply same pattern для всех 13 components
```

Сomplete updated `App.tsx` import block:
```typescript
import { ConfigureBacktest } from './components/forms/ConfigureBacktest'
import { VerdictPanel } from './components/metrics/VerdictPanel'
import { EquityChart } from './components/charts/EquityChart'
import { DrawdownSubchart } from './components/charts/DrawdownSubchart'
import { MonthlyHeatmap } from './components/charts/MonthlyHeatmap'
import { MetricsTable } from './components/metrics/MetricsTable'
import { TradesTable } from './components/metrics/TradesTable'
import { HistoryTab } from './components/tabs/HistoryTab'
import { DocumentationTab } from './components/tabs/DocumentationTab'
import { WfaFailBanner } from './components/shared/WfaFailBanner'
import { FailAnalysisTab } from './components/shared/FailAnalysisTab'
```

- [ ] **Step 4: Update cross-component imports**

Find all imports between components:
```bash
grep -rn "from.*components/[A-Z]" src/dashboard_react/src/components/
```

Update each. Example: `ConfigureBacktest.tsx` may import `StrategyDescription`:
```typescript
// Before:
import { StrategyDescription } from './StrategyDescription'
// After:
import { StrategyDescription } from '../shared/StrategyDescription'
```

- [ ] **Step 5: Update test imports**

```bash
grep -rn "from '\.\./[A-Z]\|from '\.\./components/" src/dashboard_react/src/
```

Update `MetricsTable.test.tsx` etc. к correct paths.

- [ ] **Step 6: Verify all gates**

```bash
cd src/dashboard_react
npm run lint
npx tsc -b
npm run build
npm test
```

Expected: 0 warnings / 0 errors / 23 Vitest pass / build clean (235 kB JS unchanged).

- [ ] **Step 7: Commit + SPRINT_STATE T1 done**

```bash
cd /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot
git add src/dashboard_react/src/
git commit -m "refactor(s48): component subdirs C5 (tabs/charts/forms/metrics/shared/glossary) — pre-plan architecture-reviewer Q5"
```

Update SPRINT_STATE: T1 → done.

```bash
git add llm-wiki/wiki/project/SPRINT_STATE.md
git commit -m "docs(sprint): SPRINT_STATE T1 done — component subdirs refactor"
```

---

## Bucket A — Backend

## Task 2: Replay engine equity_curve emission + verify equity_pct semantics (sonnet)

**Why:** Bug B — chart рендерится только на research presets (atr_breakout, volume_breakout). Replay engine path в `backtest_runner.py:1117` не emits `equity_curve.timestamps + equity_pct` arrays. Bug A sign tooltip также depends on equity_pct semantics (cumulative %, не delta).

**Files:**
- Modify: `src/dashboard/backtest_runner.py` (replay engine result building)
- Test: `tests/unit/test_replay_engine_equity_curve.py` (NEW)

- [ ] **Step 1: Verify equity_pct semantics (read-only investigation)**

```bash
grep -nA 3 "equity_curve\|equity_pct" src/dashboard/backtest_runner.py | head -30
grep -nA 3 "equity_curve\|equity_pct" src/backtest/research_runner_envelope.py | head -30
```

Expected output: `equity_pct` is **cumulative percent** (relative to initial capital, e.g. 12.0 means +12% from start). Document finding в commit message.

- [ ] **Step 2: Write failing test for replay path equity_curve**

`tests/unit/test_replay_engine_equity_curve.py`:

```python
"""S48 T2 — replay engine emits equity_curve parallel arrays для legacy presets."""

from __future__ import annotations

import pytest


def test_replay_envelope_includes_equity_curve_arrays() -> None:
    """Bug B fix: legacy WFA presets (ema/mean_reversion/donchian) должны эмитить
    equity_curve.timestamps + equity_pct arrays (как research_runner_envelope path)."""
    from src.dashboard.backtest_runner import _build_replay_envelope  # adjust if name differs

    # Synthetic minimal trades + WFA result
    sample_trades = [
        {"exit_ts": 1700000000, "pnl_pct": 0.05},
        {"exit_ts": 1700100000, "pnl_pct": -0.02},
        {"exit_ts": 1700200000, "pnl_pct": 0.03},
    ]
    sample_wfa = {
        "verdict": "WFA_FAIL",
        "metrics": {"t1_sharpe_oos": 0.5, "t5_n_trades": 3},
        "fold_sharpe_ratios": [0.5],
        "failed_folds": [0],
    }

    envelope = _build_replay_envelope(
        symbol="BTCUSDT",
        interval="60",
        strategy_id="ema_crossover_s13",
        trades=sample_trades,
        wfa_result=sample_wfa,
        initial_balance=10000.0,
    )

    assert "equity_curve" в envelope
    ec = envelope["equity_curve"]
    assert "timestamps" in ec
    assert "equity_pct" in ec
    assert len(ec["timestamps"]) == 3
    assert len(ec["equity_pct"]) == 3
    # Cumulative: trade 1 +5% → 5.0; trade 2 -2% → 3.0; trade 3 +3% → 6.0
    assert ec["equity_pct"] == pytest.approx([5.0, 3.0, 6.0])
```

- [ ] **Step 3: Run test — expect FAIL**

```bash
cd /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot
.venv/bin/pytest tests/unit/test_replay_engine_equity_curve.py -v
```

Expected: FAIL (function `_build_replay_envelope` либо `equity_curve` field не emitted).

- [ ] **Step 4: Find replay envelope build site**

```bash
grep -n '"equity_curve"\|"trade_stats"\|"verdict"' src/dashboard/backtest_runner.py | head -10
```

Locate where return dict is constructed (line ~1117 per S47 reference).

- [ ] **Step 5: Add equity_curve emission к replay path**

Edit `src/dashboard/backtest_runner.py` (рядом с return dict):

```python
# S48 T2 (Bug B fix) — emit equity_curve parallel arrays для frontend chart support.
# Cumulative equity_pct relative к initial_balance (consistent с research_runner_envelope).
equity_timestamps: list[int] = []
equity_pct_cumulative: list[float] = []
running_pct = 0.0
for trade in sym_trades:
    running_pct += float(trade.pnl_pct) * 100.0
    equity_timestamps.append(int(trade.exit_ts))
    equity_pct_cumulative.append(running_pct)

# In return dict, add к existing keys:
"equity_curve": {
    "timestamps": equity_timestamps,
    "equity_pct": equity_pct_cumulative,
    "trade_markers": None,  # S46 T11 field; replay path не emits markers (defer S49)
},
```

- [ ] **Step 6: Run test — expect PASS**

```bash
.venv/bin/pytest tests/unit/test_replay_engine_equity_curve.py -v
```

Expected: PASS.

- [ ] **Step 7: Run full backend regression**

```bash
.venv/bin/pytest tests/ -q --ignore=tests/integration 2>&1 | tail -3
.venv/bin/mypy --strict src/dashboard/backtest_runner.py 2>&1 | tail -3
```

Expected: 1037+ pass / 0 mypy issues.

- [ ] **Step 8: Commit + SPRINT_STATE T2 done**

```bash
git add src/dashboard/backtest_runner.py tests/unit/test_replay_engine_equity_curve.py
git commit -m "feat(s48): replay engine equity_curve emission (T2 Bug B fix) — chart support для legacy WFA presets"
```

Update SPRINT_STATE T2 → done.

---

## Task 3: account_service.py + Bybit balance wrapper (sonnet)

**Why:** Bug C — fetch real Bybit account balance вместо hardcoded $10000. Architecture-reviewer C1 BINDING: НЕ direct adapter import в `app.py`, через `account_service.py` wrapper с graceful degradation.

**Files:**
- Create: `src/dashboard/account_service.py`
- Test: `tests/unit/test_account_service.py`

- [ ] **Step 1: Write failing test**

`tests/unit/test_account_service.py`:

```python
"""S48 T3 — Bybit balance wrapper с graceful degradation (architect C1)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.dashboard.account_service import get_account_balance


def test_balance_success_path() -> None:
    """Real Bybit response → returns total_equity_usdt."""
    mock_adapter = MagicMock()
    mock_adapter.get_wallet_balance.return_value = {
        "totalEquity": "10247.83",
        "coin": [{"coin": "USDT", "walletBalance": "10247.83"}],
    }
    with patch("src.dashboard.account_service._get_adapter", return_value=mock_adapter):
        result = get_account_balance()
    assert result["source"] == "bybit_v5"
    assert result["total_equity_usdt"] == 10247.83
    assert "fetched_at_iso" in result
    assert result.get("error") is None


def test_balance_no_keys_fallback() -> None:
    """Missing API keys → fallback $10000 с error message."""
    with patch("src.dashboard.account_service._get_adapter", return_value=None):
        result = get_account_balance()
    assert result["source"] == "fallback"
    assert result["total_equity_usdt"] == 10000.0
    assert result["error"] == "no_api_keys"


def test_balance_bybit_error_fallback() -> None:
    """Bybit API exception → fallback $10000 с error reason."""
    mock_adapter = MagicMock()
    mock_adapter.get_wallet_balance.side_effect = RuntimeError("403 invalid signature")
    with patch("src.dashboard.account_service._get_adapter", return_value=mock_adapter):
        result = get_account_balance()
    assert result["source"] == "fallback"
    assert result["total_equity_usdt"] == 10000.0
    assert "403 invalid signature" in result["error"]


def test_balance_malformed_response_fallback() -> None:
    """Bybit returns dict without totalEquity → fallback."""
    mock_adapter = MagicMock()
    mock_adapter.get_wallet_balance.return_value = {"coin": []}
    with patch("src.dashboard.account_service._get_adapter", return_value=mock_adapter):
        result = get_account_balance()
    assert result["source"] == "fallback"
    assert result["total_equity_usdt"] == 10000.0
    assert "totalEquity" in result["error"]
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
.venv/bin/pytest tests/unit/test_account_service.py -v
```

Expected: FAIL (`account_service` module не exists).

- [ ] **Step 3: Implement `account_service.py`**

`src/dashboard/account_service.py`:

```python
"""S48 T3 — Bybit balance wrapper для dashboard (architect C1 BINDING).

Isolates pybit V5 dependency от FastAPI app.py — graceful degradation на missing keys
OR Bybit unavailability. Returns standardized dict с source/value/error fields.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

FALLBACK_BALANCE_USDT = 10000.0


def _get_adapter() -> Any | None:
    """Lazy adapter instantiation. Returns None if API keys missing OR import fails.
    
    Patched в tests via mock; real path uses BybitMarketAdapter from execution layer.
    """
    try:
        from src.execution.bybit.adapter import BybitMarketAdapter
        from src.platform.config import settings

        if not settings.bybit_api_key or not settings.bybit_api_secret:
            return None
        return BybitMarketAdapter.from_settings(settings)
    except Exception as exc:  # noqa: BLE001
        logger.warning("bybit_adapter_init_failed", extra={"error": str(exc)})
        return None


def get_account_balance() -> dict[str, Any]:
    """Fetch total equity USDT от Bybit V5 account.

    Returns:
        dict с keys:
        - source: "bybit_v5" | "fallback"
        - total_equity_usdt: float
        - fetched_at_iso: str (ISO 8601 UTC)
        - error: str | None (only set если source=fallback)
    """
    now_iso = datetime.now(UTC).isoformat()
    adapter = _get_adapter()

    if adapter is None:
        return {
            "source": "fallback",
            "total_equity_usdt": FALLBACK_BALANCE_USDT,
            "fetched_at_iso": now_iso,
            "error": "no_api_keys",
        }

    try:
        response = adapter.get_wallet_balance()
        total_equity_str = response.get("totalEquity")
        if total_equity_str is None:
            raise ValueError("Bybit response missing 'totalEquity' field")
        total_equity = float(total_equity_str)
        return {
            "source": "bybit_v5",
            "total_equity_usdt": total_equity,
            "fetched_at_iso": now_iso,
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("bybit_balance_fetch_failed", extra={"error": str(exc)})
        return {
            "source": "fallback",
            "total_equity_usdt": FALLBACK_BALANCE_USDT,
            "fetched_at_iso": now_iso,
            "error": str(exc),
        }
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
.venv/bin/pytest tests/unit/test_account_service.py -v
.venv/bin/mypy --strict src/dashboard/account_service.py 2>&1 | tail -3
```

Expected: 4 pass / mypy 0 errors.

- [ ] **Step 5: Commit + SPRINT_STATE T3 done**

```bash
git add src/dashboard/account_service.py tests/unit/test_account_service.py
git commit -m "feat(s48): account_service.py Bybit balance wrapper (T3 architect C1) — graceful degradation"
```

Update SPRINT_STATE T3 → done.

---

## Task 4: /api/bybit/balance endpoint (sonnet)

**Files:**
- Modify: `src/dashboard/app.py` — add endpoint
- Test: `tests/unit/test_balance_endpoint.py`

- [ ] **Step 1: Write failing test**

`tests/unit/test_balance_endpoint.py`:

```python
"""S48 T4 — /api/bybit/balance endpoint integration."""

from __future__ import annotations

from unittest.mock import patch

import pytest

fastapi = pytest.importorskip("fastapi")
httpx = pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from src.dashboard.app import create_app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_balance_endpoint_returns_json(client: TestClient) -> None:
    """GET /api/bybit/balance returns JSON с required fields."""
    fake_balance = {
        "source": "fallback",
        "total_equity_usdt": 10000.0,
        "fetched_at_iso": "2026-05-11T12:00:00+00:00",
        "error": "no_api_keys",
    }
    with patch("src.dashboard.app.get_account_balance", return_value=fake_balance):
        r = client.get("/api/bybit/balance")
    assert r.status_code == 200
    assert r.json() == fake_balance


def test_balance_endpoint_no_cache_header(client: TestClient) -> None:
    """Balance response must NOT cache (live data)."""
    with patch("src.dashboard.app.get_account_balance", return_value={
        "source": "fallback", "total_equity_usdt": 10000.0,
        "fetched_at_iso": "2026-05-11T12:00:00+00:00", "error": None,
    }):
        r = client.get("/api/bybit/balance")
    assert "no-cache" in r.headers.get("Cache-Control", "").lower()
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
.venv/bin/pytest tests/unit/test_balance_endpoint.py -v
```

Expected: FAIL (404 endpoint не exists).

- [ ] **Step 3: Add endpoint к app.py**

В `src/dashboard/app.py`, найти block с другими `/api/*` endpoints. Добавить ПОСЛЕ существующих BUT BEFORE catch-all SPA route (T6 S47):

```python
from src.dashboard.account_service import get_account_balance


@app.get("/api/bybit/balance")
async def bybit_balance() -> dict[str, Any]:
    """S48 T4 — fetch current Bybit account balance (architect C1 — via account_service)."""
    return get_account_balance()
```

(`Any` already imported в app.py per S47 cache headers middleware.)

- [ ] **Step 4: Run tests — expect PASS**

```bash
.venv/bin/pytest tests/unit/test_balance_endpoint.py -v
.venv/bin/pytest tests/unit/test_dashboard_app.py -q
```

Expected: 2 new pass + dashboard tests still pass.

- [ ] **Step 5: Commit + SPRINT_STATE T4 done**

```bash
git add src/dashboard/app.py tests/unit/test_balance_endpoint.py
git commit -m "feat(s48): /api/bybit/balance endpoint (T4) — fetch account balance via account_service"
```

Update SPRINT_STATE T4 → done.

---

## Task 5: glossary_data.py — RU dict + STRATEGY_TO_METRICS_MAP (opus)

**Why opus:** RU content quality + cross-reference accuracy с ADR 0014 + ADR 0056 + S47 wfa_criterion_explanations.py. Hand-curated map (architect C3 — explicit, не auto-sync). Judgment-heavy domain knowledge.

**Files:**
- Create: `src/dashboard/glossary_data.py`
- Test: `tests/unit/test_glossary_data.py`

- [ ] **Step 1: Read existing wfa_criterion_explanations.py для consistency**

```bash
cat src/dashboard/wfa_criterion_explanations.py
```

Glossary content extends explanations + adds non-criterion items (warnings, symbols, finals like PnL/Win rate).

- [ ] **Step 2: Verify STRATEGY_PRESETS keys**

```bash
grep -nE '^\s*"[a-z_]+":\s*\{' src/dashboard/backtest_runner.py | head -10
```

Expected (per S47 verified): `ema_crossover_s13`, `mean_reversion_s15`, `mean_reversion_s17_relaxed`, `donchian_breakout_s35`, `volume_breakout_iter10`, `atr_breakout` — 6 presets.

- [ ] **Step 3: Write failing test**

`tests/unit/test_glossary_data.py`:

```python
"""S48 T5 — glossary_data.py structure + STRATEGY_TO_METRICS_MAP coverage."""

from __future__ import annotations

import pytest

from src.dashboard.glossary_data import (
    GLOSSARY_ENTRIES,
    STRATEGY_TO_METRICS_MAP,
    GlossaryEntry,
    get_glossary,
)


def test_all_entries_have_required_fields() -> None:
    """Each glossary entry has term + section + description_ru + applies_to."""
    for term, entry in GLOSSARY_ENTRIES.items():
        assert isinstance(term, str) and term, f"Empty term: {term!r}"
        assert "section" in entry and entry["section"]
        assert "description_ru" in entry and entry["description_ru"]
        assert "applies_to" in entry and isinstance(entry["applies_to"], list)


def test_minimum_entry_count() -> None:
    """Glossary covers at least core T1-T6 + DSR + MC + 5 finals + 5 warnings + 5 symbols."""
    assert len(GLOSSARY_ENTRIES) >= 30, f"Got {len(GLOSSARY_ENTRIES)}, expected ≥30"


def test_critical_terms_present() -> None:
    """Required terms must exist."""
    required = ["t1_sharpe_oos", "t5_n_trades", "dsr", "mc_p_value",
                "total_pnl_pct", "win_rate", "raw_full_period", "subperiod_robustness"]
    for term in required:
        assert term in GLOSSARY_ENTRIES, f"Missing required term: {term}"


def test_strategy_map_covers_all_presets() -> None:
    """STRATEGY_TO_METRICS_MAP includes all 6 STRATEGY_PRESETS."""
    expected_presets = {
        "ema_crossover_s13", "mean_reversion_s15", "mean_reversion_s17_relaxed",
        "donchian_breakout_s35", "volume_breakout_iter10", "atr_breakout",
    }
    actual = set(STRATEGY_TO_METRICS_MAP.keys())
    assert expected_presets.issubset(actual), f"Missing presets: {expected_presets - actual}"


def test_get_glossary_returns_dict() -> None:
    """Public API returns full glossary + map."""
    result = get_glossary()
    assert "entries" in result
    assert "strategy_to_metrics" in result
    assert len(result["entries"]) >= 30
```

- [ ] **Step 4: Run test — expect FAIL**

```bash
.venv/bin/pytest tests/unit/test_glossary_data.py -v
```

Expected: FAIL (module не exists).

- [ ] **Step 5: Implement `glossary_data.py`**

`src/dashboard/glossary_data.py`:

```python
"""S48 T5 — RU glossary content для GlossaryTab UI page (Bug E core).

Content:
- T1-T6 + DSR + MC criterion explanations (extends wfa_criterion_explanations.py)
- Trade statistics finals (PnL, Win rate, Profit Factor, etc.)
- Warning codes (mc_noise, low_sample, raw_full_period, subperiod_robustness, etc.)
- Symbols (▸ ▲ ⚠ ✓ ✗) UI legend
- Strategy presets short descriptions

STRATEGY_TO_METRICS_MAP — hand-curated (architect C3): explicit per-strategy
applicability instead of auto-sync. 6 presets coverage. Drift OK для small set.
"""

from __future__ import annotations

from typing import TypedDict


class GlossaryEntry(TypedDict):
    section: str           # Section name (matches main-page block order)
    description_ru: str    # Russian description
    applies_to: list[str]  # Strategy preset IDs OR ["*"] для universal terms
    adr_ref: str | None    # Optional ADR cross-reference


# Sections in main-page render order (used by GlossaryTab TOC):
SECTIONS = [
    "verdict_status",       # 1. Verdict + status symbols
    "gate_blocking_metrics",# 2. Gate-blocking metrics (T5_floor, DSR, MC, OOS/IS)
    "informational_metrics",# 3. Informational metrics (T1-T4, T6)
    "trade_statistics",     # 4. Trade stats (PnL, Win rate, Profit Factor, etc.)
    "chart_vocabulary",     # 5. Equity & drawdown chart terms
    "monthly_heatmap",      # 6. Monthly heatmap encoding
    "warnings",             # 7. WFA discipline warnings
    "strategy_presets",     # 8. Strategy preset descriptions
]


# CRITICAL: contents below illustrate structure — full content требует ~60-80 entries.
# Implementer extends per Step 6 — этот dict — minimal viable начальная версия,
# expanded к coverage требованию (test_minimum_entry_count >= 30).
GLOSSARY_ENTRIES: dict[str, GlossaryEntry] = {
    # === Section 1: verdict_status ===
    "verdict_pass": {
        "section": "verdict_status",
        "description_ru": (
            "Стратегия прошла все обязательные acceptance gates (T5_floor + MC + DSR + "
            "fold OOS/IS ≥ 0.7). Pre-registration валиден. Можно использовать для "
            "live/paper trading с пониманием honest validation discipline."
        ),
        "applies_to": ["*"],
        "adr_ref": "ADR 0014",
    },
    "verdict_fail": {
        "section": "verdict_status",
        "description_ru": (
            "Стратегия НЕ прошла как минимум один обязательный gate. Использовать в live "
            "trading НЕ рекомендуется. См. блок ▸ ДЕТАЛЬНЫЙ РАЗБОР для причин."
        ),
        "applies_to": ["*"],
        "adr_ref": "ADR 0014",
    },
    "verdict_wfa_fail_data": {
        "section": "verdict_status",
        "description_ru": (
            "Walk-forward analysis провалена из-за недостатка данных (n_trades < 50 OR "
            "WFA folds < 5). Не статистически значимый результат. Не отражает "
            "performance стратегии в реальных условиях."
        ),
        "applies_to": ["*"],
        "adr_ref": "ADR 0052",
    },
    "verdict_raw": {
        "section": "verdict_status",
        "description_ru": (
            "Полный full-period backtest без WFA discipline. Подвержен look-ahead bias. "
            "Используется только для quick-check exploratory tests. НЕ basis для live decisions."
        ),
        "applies_to": ["atr_breakout", "volume_breakout_iter10"],
        "adr_ref": None,
    },

    # === Section 2: gate_blocking_metrics ===
    "t5_n_trades": {
        "section": "gate_blocking_metrics",
        "description_ru": (
            "Количество OOS-сделок. Bailey 2014 minimum для DSR statistical significance: "
            "n ≥ 50 (S34 ADR 0052 amendment, было 100). Если n < 50 — DSR computation "
            "skipped, верdict WFA_FAIL_DATA."
        ),
        "applies_to": ["*"],
        "adr_ref": "ADR 0052",
    },
    "n_eff_threshold": {
        "section": "gate_blocking_metrics",
        "description_ru": (
            "Effective sample size (Kish 1965) — минимум 50. Учитывает autocorrelation "
            "trades. Hard blocker, независимый от t5_n_trades raw count."
        ),
        "applies_to": ["*"],
        "adr_ref": "ADR 0052",
    },
    "dsr": {
        "section": "gate_blocking_metrics",
        "description_ru": (
            "Deflated Sharpe Ratio (Bailey & López de Prado 2014) — corrected Sharpe "
            "учитывая multiple comparisons + non-normality. Threshold > 0 для PASS. "
            "Использует Pearson kurtosis (fisher=False) per ADR 0056."
        ),
        "applies_to": ["*"],
        "adr_ref": "ADR 0056",
    },
    "mc_p_value": {
        "section": "gate_blocking_metrics",
        "description_ru": (
            "Monte Carlo permutation p-value (sign-flip test, MC_BLOCK_SIZE=20 per ADR "
            "0015). Threshold ≤ 0.05 для PASS (S34 ADR 0052 ужесточил с 0.10). "
            "Если p > 0.05 — returns indistinguishable от random walk."
        ),
        "applies_to": ["*"],
        "adr_ref": "ADR 0015",
    },
    "fold_oos_is_sharpe": {
        "section": "gate_blocking_metrics",
        "description_ru": (
            "Per-fold Sharpe ratio (out-of-sample). Threshold ≥ 0.7 для PASS. Если хотя "
            "бы 1 fold не прошёл — стратегия отклоняется. L1 hard gate в acceptance cascade."
        ),
        "applies_to": ["*"],
        "adr_ref": "ADR 0014",
    },

    # === Section 3: informational_metrics (T1-T4, T6 per ADR 0014) ===
    "t1_sharpe_oos": {
        "section": "informational_metrics",
        "description_ru": (
            "Sharpe Ratio (annualized OOS): mean(per-trade returns) / std × √(bars_per_year ÷ "
            "mean_holding_bars). Threshold ≥ 1.0 (PASS), > 3.0 OVERFIT?. "
            "Информационный per ADR 0014 — НЕ в acceptance gate, но индикатор risk-adjusted return."
        ),
        "applies_to": ["*"],
        "adr_ref": "ADR 0014",
    },
    "t2_sortino_oos": {
        "section": "informational_metrics",
        "description_ru": (
            "Sortino Ratio (downside-only volatility вариант Sharpe). Threshold ≥ 1.5 PASS. "
            "S27 fix preserved (canonical formula). Информационный."
        ),
        "applies_to": ["*"],
        "adr_ref": None,
    },
    "t3_max_drawdown": {
        "section": "informational_metrics",
        "description_ru": (
            "Максимальная просадка equity curve. Threshold < 25% PASS. Прокси-оценка risk-of-ruin. "
            "Информационный — для capital allocation context."
        ),
        "applies_to": ["*"],
        "adr_ref": None,
    },
    "t4_win_rate": {
        "section": "informational_metrics",
        "description_ru": (
            "Win rate (доля прибыльных сделок). Threshold ≥ 45% при RR≥1.5 OR ≥ 35% при "
            "RR≥2.0. Калибровка через payoff ratio. Информационный."
        ),
        "applies_to": ["*"],
        "adr_ref": None,
    },
    "t6_oos_is_sharpe_ratio": {
        "section": "informational_metrics",
        "description_ru": (
            "Соотношение OOS Sharpe / IS Sharpe. Threshold ≥ 0.7 PASS. Overfit detector — "
            "если OOS << IS, значит стратегия curve-fitted к training period."
        ),
        "applies_to": ["*"],
        "adr_ref": None,
    },

    # === Section 4: trade_statistics ===
    "total_pnl_pct": {
        "section": "trade_statistics",
        "description_ru": (
            "Cumulative profit-and-loss в процентах от initial balance. Положительное = profit, "
            "отрицательное = loss. Не annualized."
        ),
        "applies_to": ["*"],
        "adr_ref": None,
    },
    "total_pnl_quote": {
        "section": "trade_statistics",
        "description_ru": (
            "Cumulative PnL в quote currency (USDT). Доступно для replay engine path; "
            "research presets emit None (нет capital basis)."
        ),
        "applies_to": ["*"],
        "adr_ref": None,
    },
    "win_rate": {
        "section": "trade_statistics",
        "description_ru": (
            "Доля прибыльных сделок (n_winners / n_total). Без context payoff ratio "
            "недостаточен для оценки edge."
        ),
        "applies_to": ["*"],
        "adr_ref": None,
    },
    "profit_factor": {
        "section": "trade_statistics",
        "description_ru": (
            "Sum(winners) / |Sum(losers)|. PF > 1 = profitable; PF > 2 strong edge; "
            "PF < 1 losing strategy."
        ),
        "applies_to": ["*"],
        "adr_ref": None,
    },
    "avg_win_quote": {
        "section": "trade_statistics",
        "description_ru": "Средняя величина winning trade в USDT. Replay engine path only.",
        "applies_to": ["*"],
        "adr_ref": None,
    },
    "avg_loss_quote": {
        "section": "trade_statistics",
        "description_ru": "Средняя величина losing trade в USDT. Replay engine path only.",
        "applies_to": ["*"],
        "adr_ref": None,
    },
    "total_commissions_quote": {
        "section": "trade_statistics",
        "description_ru": (
            "Сумма всех комиссий за сделки в USDT (Bybit Spot taker 0.1% per side, "
            "S2 ADR 0008 spec). Critical для real-world expectancy."
        ),
        "applies_to": ["*"],
        "adr_ref": "ADR 0008",
    },

    # === Section 5: chart_vocabulary ===
    "equity_curve": {
        "section": "chart_vocabulary",
        "description_ru": (
            "График кумулятивного equity_pct (% от initial balance) во времени. Показывает "
            "trajectory стратегии. Точки = exit_timestamp каждой trade."
        ),
        "applies_to": ["*"],
        "adr_ref": None,
    },
    "drawdown_subchart": {
        "section": "chart_vocabulary",
        "description_ru": (
            "Drawdown — % просадка от peak equity. Всегда отрицательное OR 0. Sync cursor "
            "с equity chart (S46 CC2 architect binding)."
        ),
        "applies_to": ["*"],
        "adr_ref": None,
    },

    # === Section 6: monthly_heatmap ===
    "monthly_heatmap": {
        "section": "monthly_heatmap",
        "description_ru": (
            "Calendar grid PnL по месяцам. Зелёный = profit, красный = loss, intensity по "
            "magnitude. Помогает визуализировать seasonality + concentration risk."
        ),
        "applies_to": ["*"],
        "adr_ref": None,
    },

    # === Section 7: warnings ===
    "raw_full_period": {
        "section": "warnings",
        "description_ru": (
            "Прогон выполнен на full historical period БЕЗ walk-forward discipline. "
            "Look-ahead bias не контролируется. Не basis для live decisions."
        ),
        "applies_to": ["atr_breakout", "volume_breakout_iter10"],
        "adr_ref": None,
    },
    "subperiod_robustness": {
        "section": "warnings",
        "description_ru": (
            "Sub-period robustness check — стратегия разбита на N (default 5) chunks по "
            "времени. PASS если PnL положителен в большинстве chunks. Catches concentrated "
            "luck (один chunk вытянул total)."
        ),
        "applies_to": ["*"],
        "adr_ref": None,
    },
    "mc_noise": {
        "section": "warnings",
        "description_ru": (
            "Monte Carlo permutation test показал p-value > 0.10 — observed Sharpe не "
            "отличим от random walk на этом sample. Strategy edge не подтверждён статистически."
        ),
        "applies_to": ["*"],
        "adr_ref": "ADR 0015",
    },
    "low_sample": {
        "section": "warnings",
        "description_ru": (
            "n_trades < 100 (Bailey 2014 traditional threshold) — t-test может быть "
            "ненадёжным. См. также n_eff_threshold (Kish 1965) для effective sample size."
        ),
        "applies_to": ["*"],
        "adr_ref": "ADR 0052",
    },
    "look_ahead_bias_warning": {
        "section": "warnings",
        "description_ru": (
            "Detected potential look-ahead bias в strategy logic OR data preparation. "
            "Strategy не валидна для live execution до устранения."
        ),
        "applies_to": ["*"],
        "adr_ref": None,
    },

    # Symbols (Section "symbols" — separate or appended к verdict_status)
    "symbol_triangle_right": {
        "section": "verdict_status",
        "description_ru": "▸ — section heading marker. Выделяет начало основных блоков на странице.",
        "applies_to": ["*"],
        "adr_ref": None,
    },
    "symbol_triangle_warning": {
        "section": "warnings",
        "description_ru": "▲ — warning marker. Внимание к контекстному предупреждению (low severity).",
        "applies_to": ["*"],
        "adr_ref": None,
    },
    "symbol_warning_sign": {
        "section": "warnings",
        "description_ru": "⚠ — high-severity warning. Critical issue требующий внимания оператора.",
        "applies_to": ["*"],
        "adr_ref": None,
    },
    "symbol_check": {
        "section": "verdict_status",
        "description_ru": "✓ — passed indicator. Critical OR informational gate prerequisite met.",
        "applies_to": ["*"],
        "adr_ref": None,
    },
    "symbol_cross": {
        "section": "verdict_status",
        "description_ru": "✗ — failed indicator. Gate prerequisite NOT met.",
        "applies_to": ["*"],
        "adr_ref": None,
    },

    # === Section 8: strategy_presets ===
    "preset_ema_crossover_s13": {
        "section": "strategy_presets",
        "description_ru": (
            "EMA Crossover (S13) — trend-following. Long entry на пересечении EMA(12) > EMA(26) "
            "+ ADX > 25 + RSI < 70. Exit on opposite cross OR ATR-stop. ATR(14) × 1.5 SL, × 3.0 TP."
        ),
        "applies_to": ["ema_crossover_s13"],
        "adr_ref": None,
    },
    "preset_mean_reversion_s15": {
        "section": "strategy_presets",
        "description_ru": (
            "Mean Reversion (S15) — RSI oversold/overbought + Bollinger Bands extremes. "
            "Long на RSI < 30 + price < BB lower(2σ). Exit на RSI ≥ 50 OR BB middle."
        ),
        "applies_to": ["mean_reversion_s15"],
        "adr_ref": None,
    },
    "preset_atr_breakout": {
        "section": "strategy_presets",
        "description_ru": (
            "ATR Breakout — volatility breakout. Long entry на close > close[-2] + ATR × mult_breakout. "
            "Exit на ATR-trailing stop. 10 supported combos. Все WFA_FAIL per S45 honest verdict."
        ),
        "applies_to": ["atr_breakout"],
        "adr_ref": None,
    },
    # ... (Implementer добавляет remaining 3 presets per real STRATEGY_PRESETS dict)
}


# Hand-curated per-strategy applicability map (architect C3: explicit, no auto-sync).
# Lists term keys что highlighted на Glossary tab при выбранной стратегии.
STRATEGY_TO_METRICS_MAP: dict[str, list[str]] = {
    "ema_crossover_s13": [
        # Universal (gate + informational)
        "t5_n_trades", "n_eff_threshold", "dsr", "mc_p_value", "fold_oos_is_sharpe",
        "t1_sharpe_oos", "t2_sortino_oos", "t3_max_drawdown", "t4_win_rate", "t6_oos_is_sharpe_ratio",
        # Trade stats (replay path → quote available)
        "total_pnl_pct", "total_pnl_quote", "win_rate", "profit_factor",
        "avg_win_quote", "avg_loss_quote", "total_commissions_quote",
        # Charts + warnings universal
        "equity_curve", "drawdown_subchart", "monthly_heatmap",
        "subperiod_robustness", "mc_noise", "low_sample",
        # Verdicts
        "verdict_pass", "verdict_fail", "verdict_wfa_fail_data",
        # Strategy preset
        "preset_ema_crossover_s13",
    ],
    "mean_reversion_s15": [
        "t5_n_trades", "n_eff_threshold", "dsr", "mc_p_value", "fold_oos_is_sharpe",
        "t1_sharpe_oos", "t2_sortino_oos", "t3_max_drawdown", "t4_win_rate", "t6_oos_is_sharpe_ratio",
        "total_pnl_pct", "total_pnl_quote", "win_rate", "profit_factor",
        "avg_win_quote", "avg_loss_quote", "total_commissions_quote",
        "equity_curve", "drawdown_subchart", "monthly_heatmap",
        "subperiod_robustness", "mc_noise", "low_sample",
        "verdict_pass", "verdict_fail", "verdict_wfa_fail_data",
        "preset_mean_reversion_s15",
    ],
    "mean_reversion_s17_relaxed": [
        # Same as s15 + additional
        "t5_n_trades", "n_eff_threshold", "dsr", "mc_p_value", "fold_oos_is_sharpe",
        "t1_sharpe_oos", "t2_sortino_oos", "t3_max_drawdown", "t4_win_rate", "t6_oos_is_sharpe_ratio",
        "total_pnl_pct", "total_pnl_quote", "win_rate", "profit_factor",
        "avg_win_quote", "avg_loss_quote", "total_commissions_quote",
        "equity_curve", "drawdown_subchart", "monthly_heatmap",
        "subperiod_robustness", "mc_noise", "low_sample",
        "verdict_pass", "verdict_fail", "verdict_wfa_fail_data",
    ],
    "donchian_breakout_s35": [
        "t5_n_trades", "n_eff_threshold", "dsr", "mc_p_value", "fold_oos_is_sharpe",
        "t1_sharpe_oos", "t2_sortino_oos", "t3_max_drawdown", "t4_win_rate", "t6_oos_is_sharpe_ratio",
        "total_pnl_pct", "total_pnl_quote", "win_rate", "profit_factor",
        "avg_win_quote", "avg_loss_quote", "total_commissions_quote",
        "equity_curve", "drawdown_subchart", "monthly_heatmap",
        "subperiod_robustness", "mc_noise", "low_sample",
        "verdict_pass", "verdict_fail", "verdict_wfa_fail_data",
    ],
    "volume_breakout_iter10": [
        # Research preset — verdict_raw applicable, не verdict_pass
        "t5_n_trades", "n_eff_threshold", "dsr", "mc_p_value",
        "t1_sharpe_oos", "t3_max_drawdown", "win_rate", "total_pnl_pct",
        "equity_curve", "drawdown_subchart", "monthly_heatmap",
        "subperiod_robustness", "mc_noise", "low_sample", "raw_full_period",
        "verdict_raw", "verdict_fail", "verdict_wfa_fail_data",
    ],
    "atr_breakout": [
        "t5_n_trades", "n_eff_threshold", "dsr", "mc_p_value",
        "t1_sharpe_oos", "t3_max_drawdown", "win_rate", "total_pnl_pct",
        "equity_curve", "drawdown_subchart", "monthly_heatmap",
        "subperiod_robustness", "mc_noise", "low_sample", "raw_full_period",
        "verdict_raw", "verdict_fail", "verdict_wfa_fail_data",
        "preset_atr_breakout",
    ],
}


def get_glossary() -> dict[str, object]:
    """Public API — returns full glossary + strategy map для /api/glossary endpoint."""
    return {
        "entries": GLOSSARY_ENTRIES,
        "strategy_to_metrics": STRATEGY_TO_METRICS_MAP,
        "sections": SECTIONS,
    }
```

- [ ] **Step 6: Implementer expands content к ≥30 entries**

Verify test expects 30+:

```bash
.venv/bin/pytest tests/unit/test_glossary_data.py -v
```

If `test_minimum_entry_count` fails — add more entries (target ~50-60 for production quality). 5-7 categories × 5-10 entries each.

- [ ] **Step 7: Run все tests + mypy**

```bash
.venv/bin/pytest tests/unit/test_glossary_data.py -v
.venv/bin/mypy --strict src/dashboard/glossary_data.py
```

Expected: 5 pass / mypy 0 errors.

- [ ] **Step 8: Commit + SPRINT_STATE T5 done**

```bash
git add src/dashboard/glossary_data.py tests/unit/test_glossary_data.py
git commit -m "feat(s48): glossary_data.py RU dict + STRATEGY_TO_METRICS_MAP (T5 opus) — Bug E core content

architect C3: hand-curated per-strategy map (no auto-sync). 6 presets coverage.
Sections в main-page render order. ~50 entries: T1-T6 + DSR + MC + finals + warnings + symbols + presets."
```

Update SPRINT_STATE T5 → done.

---

## Task 6: /api/glossary endpoint (sonnet)

**Files:**
- Modify: `src/dashboard/app.py`
- Test: `tests/unit/test_glossary_endpoint.py`

- [ ] **Step 1: Write failing test**

`tests/unit/test_glossary_endpoint.py`:

```python
"""S48 T6 — /api/glossary endpoint integration."""

from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi")
httpx = pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from src.dashboard.app import create_app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_glossary_endpoint_returns_full_payload(client: TestClient) -> None:
    """GET /api/glossary returns entries + strategy_to_metrics + sections."""
    r = client.get("/api/glossary")
    assert r.status_code == 200
    data = r.json()
    assert "entries" in data
    assert "strategy_to_metrics" in data
    assert "sections" in data
    assert len(data["entries"]) >= 30
    assert "ema_crossover_s13" in data["strategy_to_metrics"]


def test_glossary_endpoint_immutable_cache(client: TestClient) -> None:
    """Static content — cacheable for short TTL (1 hour)."""
    r = client.get("/api/glossary")
    cache = r.headers.get("Cache-Control", "").lower()
    # Per S47 cache headers middleware: /api/* → no-cache.
    # Acceptable; glossary content small (~10-30KB JSON).
    assert "no-cache" in cache OR "max-age" in cache
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
.venv/bin/pytest tests/unit/test_glossary_endpoint.py -v
```

Expected: FAIL (404).

- [ ] **Step 3: Add endpoint к app.py**

В `src/dashboard/app.py`, после `/api/bybit/balance` (T4) BUT BEFORE catch-all SPA:

```python
from src.dashboard.glossary_data import get_glossary


@app.get("/api/glossary")
async def glossary() -> dict[str, object]:
    """S48 T6 — RU glossary content + per-strategy applicability map (architect C3)."""
    return get_glossary()
```

- [ ] **Step 4: Run tests — PASS**

```bash
.venv/bin/pytest tests/unit/test_glossary_endpoint.py -v
.venv/bin/pytest tests/unit/test_dashboard_app.py -q
```

Expected: 2 new + dashboard regression pass.

- [ ] **Step 5: Commit + SPRINT_STATE T6 done**

```bash
git add src/dashboard/app.py tests/unit/test_glossary_endpoint.py
git commit -m "feat(s48): /api/glossary endpoint (T6 architect C3) — single endpoint с applies_to client filter"
```

Update SPRINT_STATE T6 → done.

---

## Task 7: RunRecord shape verification + extension if needed (sonnet)

**Why:** Bug H — HistoryTab expand needs initial_balance / final_balance / win_rate / profit_factor per row. Verify if RunRecord уже эти fields содержит, extend если missing.

**Files:**
- Verify: `src/dashboard/backtest_runner.py` `list_runs()` + `get_run()` return shape
- Possibly modify: `src/dashboard/backtest_runner.py`

- [ ] **Step 1: Inspect RunRecord shape**

```bash
grep -nA 15 "def list_runs\|def get_run" src/dashboard/backtest_runner.py | head -40
```

`list_runs()` already (per S47 verified) returns lightweight: `{run_id, request, verdict, metrics, warnings_count, mtime}`. `get_run(id)` returns full BacktestResponse JSON (saved JSON file).

- [ ] **Step 2: Verify full BacktestResponse имеет required fields**

```bash
ls data/runs/ | head -3  # find sample run file
cat data/runs/<sample-run>.json | python3 -m json.tool | head -50
```

Check для:
- `trade_stats.n_winners` / `n_losers` — present (S47 T13)
- `trade_stats.profit_factor` — present
- `trade_stats.win_rate` — present
- `initial_balance_quote` / `final_balance_quote` — **MAY BE MISSING**

- [ ] **Step 3: If missing — extend backtest_runner save logic**

Если `initial_balance_quote` / `final_balance_quote` не в saved RunRecord, добавить к save logic в `backtest_runner.py`:

```python
# In run_backtest() OR similar that builds final response:
result["trade_stats"]["initial_balance_quote"] = initial_balance  # passed from request
result["trade_stats"]["final_balance_quote"] = initial_balance * (1 + total_pnl_pct / 100)
```

- [ ] **Step 4: Add verification test**

`tests/unit/test_run_record_shape.py` (NEW):

```python
"""S48 T7 — RunRecord shape verification для HistoryTab Bug H."""

from __future__ import annotations

from pathlib import Path
import json

import pytest


def test_existing_runs_have_required_fields() -> None:
    """Bug H requires: initial_balance_quote / final_balance_quote / win_rate / profit_factor.
    
    Either present in stored runs OR backend computes on-fly from existing fields.
    """
    runs_dir = Path("data/runs")
    if not runs_dir.exists():
        pytest.skip("no runs/ directory — fresh checkout")

    sample_files = sorted(runs_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:3]
    if not sample_files:
        pytest.skip("no run records yet")

    for path in sample_files:
        data = json.loads(path.read_text())
        ts = data.get("trade_stats", {})
        # win_rate ALWAYS present (research + replay paths)
        assert "win_rate" in ts, f"{path.name}: trade_stats.win_rate missing"
        # profit_factor present для replay path
        # initial_balance_quote / final_balance_quote may be missing — backend extension target
        if "initial_balance_quote" not in ts:
            print(f"S48 T7 NOTE: {path.name} missing initial_balance_quote — backend extension needed")
```

- [ ] **Step 5: Run test, observe gap, decide extension**

```bash
.venv/bin/pytest tests/unit/test_run_record_shape.py -v -s
```

If existing runs missing `initial_balance_quote` — extend save logic per Step 3. If present — skip extension, only document RU summary template's expectations.

- [ ] **Step 6: Если extended — re-test full envelope path**

```bash
.venv/bin/pytest tests/unit/test_research_runner_envelope.py -v
.venv/bin/mypy --strict src/dashboard/backtest_runner.py
```

Expected: GREEN.

- [ ] **Step 7: Commit + SPRINT_STATE T7 done**

```bash
git add src/dashboard/backtest_runner.py tests/unit/test_run_record_shape.py 2>/dev/null
git commit -m "feat(s48): RunRecord shape verification + initial/final balance extension if needed (T7) — Bug H prereq"
```

Update SPRINT_STATE T7 → done.

---

## Bucket B — Frontend bug fixes

## Task 8: EquityChart 3-line tooltip + initialBalance prop (sonnet)

**Why:** Bug A — tooltip всегда `+%` даже на FAIL стратегии + operator wants dynamic balance USDT в tooltip per FE design doc.

**Files:**
- Modify: `src/dashboard_react/src/components/charts/EquityChart.tsx` (post-T1 path)
- Modify: `src/dashboard_react/src/components/charts/EquityChart.module.css`

- [ ] **Step 1: Add `initialBalance` prop к EquityChartProps interface**

В `EquityChart.tsx`:

```typescript
interface EquityChartProps {
  equityCurve: EquityCurve;
  syncKey?: string;
  height?: number;
  onChartReady?: (chart: uPlot) => void;  // @deprecated S46
  initialBalance: number;  // S48 T8 — для balance tooltip computation
}
```

Default value через destructure (если caller не passes — fallback 10000):
```typescript
export function EquityChart({
  equityCurve,
  syncKey,
  height = 320,
  onChartReady,
  initialBalance = 10000,
}: EquityChartProps) {
```

- [ ] **Step 2: Update setCursor hook tooltip к 3-line format**

Find existing setCursor hook (S47 T14). Replace tooltipEl.textContent = ... block:

```typescript
opts.hooks = {
  setCursor: [
    (u: uPlot) => {
      const idx = u.cursor.idx
      const tooltipEl = container.querySelector(
        '[data-tooltip="equity"]',
      ) as HTMLDivElement | null
      if (tooltipEl === null) return
      if (idx === null || idx === undefined || idx < 0) {
        tooltipEl.style.display = 'none'
        return
      }
      const ts = u.data[0]?.[idx]
      const eq = u.data[1]?.[idx]
      if (ts === undefined || ts === null || eq === undefined || eq === null) {
        tooltipEl.style.display = 'none'
        return
      }
      const date = new Date(Number(ts) * 1000).toISOString().slice(0, 10)
      const sign = eq >= 0 ? '+' : ''
      // S48 T8 — 3-line tooltip: date / P&L % / balance USDT
      const balance = initialBalance * (1 + eq / 100)
      const balanceFmt = new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        maximumFractionDigits: 2,
      }).format(balance)
      tooltipEl.innerHTML = `
        <div class="${styles.tooltipDate}">${date}</div>
        <div class="${styles.tooltipPct} ${eq >= 0 ? styles.tooltipPctPos : styles.tooltipPctNeg}">${sign}${eq.toFixed(2)}%</div>
        <div class="${styles.tooltipBalance}">${balanceFmt}</div>
      `
      tooltipEl.style.display = 'block'
      const left = u.cursor.left ?? 0
      tooltipEl.style.left = `${left + 12}px`
    },
  ],
}
```

(Note: switching `textContent` → `innerHTML` adds 3 div elements. Safe — все content controlled, no user input.)

- [ ] **Step 3: Update CSS для 3-line tooltip styles**

В `EquityChart.module.css`, add к existing `.tooltip` block:

```css
.tooltip {
  position: absolute;
  top: 8px;
  background: var(--color-bg-glass);
  backdrop-filter: blur(8px);
  border: 1px solid var(--color-anthropic-orange);
  color: var(--color-text-primary);
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  padding: 6px 10px;
  border-radius: 4px;
  pointer-events: none;
  z-index: 10;
  white-space: nowrap;
  box-shadow: 0 0 8px rgba(204, 120, 92, 0.30);
}

/* S48 T8 — 3-line tooltip sub-elements */
.tooltipDate {
  color: var(--color-text-muted);
  font-size: 10px;
  margin-bottom: 2px;
}

.tooltipPct {
  font-size: 13px;
  font-weight: 700;
  margin-bottom: 2px;
}

.tooltipPctPos {
  color: #00ff88;
}

.tooltipPctNeg {
  color: #ff3366;
}

.tooltipBalance {
  font-size: 12px;
  color: var(--color-text-primary);
}
```

- [ ] **Step 4: Verify build clean**

```bash
cd src/dashboard_react
npm run lint
npx tsc -b
npm run build
```

Expected: 0 warnings / 0 errors / build clean.

- [ ] **Step 5: Update App.tsx pass initialBalance**

В App.tsx где `<EquityChart equityCurve={...} syncKey="equity-dd-sync" />` add `initialBalance` prop. Source — initialBalance из useBybitBalance (T20) OR fallback к 10000.

```tsx
<EquityChart
  equityCurve={result.equity_curve}
  syncKey="equity-dd-sync"
  initialBalance={initialBalance}
/>
```

(`initialBalance` state defined в T22.)

- [ ] **Step 6: Commit + SPRINT_STATE T8 done**

```bash
cd /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot
git add src/dashboard_react/src/components/charts/EquityChart.tsx \
        src/dashboard_react/src/components/charts/EquityChart.module.css \
        src/dashboard_react/src/App.tsx
git commit -m "feat(s48): EquityChart 3-line tooltip + initialBalance prop (T8 Bug A) — date/PnL%/balance USDT"
```

Update SPRINT_STATE T8 → done.

---

## Task 9: Verify Bug B — chart on ALL strategies (sonnet)

**Why:** Bug B — после T2 backend extend replay engine emits equity_curve. Verify frontend renders chart для legacy WFA presets too.

**Files:**
- Test: `src/dashboard_react/tests/e2e/equity-chart-all-presets.spec.ts` (NEW)

- [ ] **Step 1: Write Playwright E2E test**

```typescript
import { test, expect } from '@playwright/test';

test.describe('Bug B verification — equity chart on all preset types', () => {
  test('research preset (atr_breakout) shows chart', async ({ page }) => {
    await page.route('**/api/backtest', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          run_id: 'test_research',
          verdict: 'RAW',
          equity_curve: {
            timestamps: [1700000000, 1700100000, 1700200000],
            equity_pct: [0, 5.0, 3.0],
            trade_markers: null,
          },
          metrics: { n_trades: 2 },
          trade_stats: { n_trades: 2, win_rate: 0.5 },
          warnings: [], failed_criteria: [], fold_sharpe_ratios: [], failed_folds: [],
          dsr: 0, dsr_pass: false, mc_p_value: 0.5, bars_per_year: 8766,
          request: { strategy_id: 'atr_breakout', strategy_label: 'ATR breakout', symbol: 'BTCUSDT', interval: '240', interval_label: '4h', start: '2023-01-01', end: '2023-12-31' },
          n_trades: 2, sharpe: 0.5, win_rate: 0.5, total_pnl_pct: 3.0,
        }),
      })
    })
    await page.goto('/')
    await page.getByRole('button', { name: /EXECUTE/ }).click()
    await expect(page.getByText('▸ EQUITY CURVE')).toBeVisible({ timeout: 10000 })
  });

  test('legacy WFA preset (ema_crossover) shows chart after Bug B fix', async ({ page }) => {
    await page.route('**/api/backtest', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          run_id: 'test_legacy',
          verdict: 'WFA_FAIL',
          equity_curve: {
            timestamps: [1700000000, 1700100000, 1700200000],
            equity_pct: [5.0, -2.0, 6.0],  // S48 T2 backend emits arrays
            trade_markers: null,
          },
          metrics: { t1_sharpe_oos: 0.5 },
          trade_stats: { n_trades: 3, win_rate: 0.66 },
          warnings: [], failed_criteria: ['t1'], fold_sharpe_ratios: [0.5], failed_folds: [0],
          dsr: 0, dsr_pass: false, mc_p_value: 0.3, bars_per_year: 8766,
          request: { strategy_id: 'ema_crossover_s13', strategy_label: 'EMA crossover', symbol: 'BTCUSDT', interval: '60', interval_label: '1h', start: '2023-01-01', end: '2023-12-31' },
          n_trades: 3, sharpe: 0.5, win_rate: 0.66, total_pnl_pct: 6.0,
        }),
      })
    })
    await page.goto('/')
    await page.getByRole('button', { name: /EXECUTE/ }).click()
    await expect(page.getByText('▸ EQUITY CURVE')).toBeVisible({ timeout: 10000 })
  });
});
```

- [ ] **Step 2: Run E2E**

```bash
cd src/dashboard_react
npx playwright test equity-chart-all-presets
```

Expected: 2/2 PASS (after T2 backend extend).

- [ ] **Step 3: Commit + SPRINT_STATE T9 done**

```bash
cd /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot
git add src/dashboard_react/tests/e2e/equity-chart-all-presets.spec.ts
git commit -m "test(s48): equity chart на all preset types E2E (T9 Bug B verify)"
```

Update SPRINT_STATE T9 → done.

---

## Task 10: MetricsTable visual divider + grayed informational rows (sonnet)

**Why:** Bug D — informational T1/T2/T3/T4/T6 показаны как FAIL chips per ADR 0014 они informational. UX confusion.

**Files:**
- Modify: `src/dashboard_react/src/components/metrics/MetricsTable.tsx`
- Modify: `src/dashboard_react/src/components/metrics/MetricsTable.module.css`

- [ ] **Step 1: Restructure WFA path — add section labels + divider**

В `MetricsTable.tsx` WFA path render (≈ line 200-300), restructure rows:

```tsx
{/* S48 T10 Bug D — visual hierarchy: gate-blocking vs informational */}
<tbody>
  <tr className={styles.sectionHeader}>
    <td colSpan={4} className={styles.sectionLabel}>
      GATE-BLOCKING (used by accept/reject decision)
    </td>
  </tr>
  {/* T5 + DSR + MC + fold OOS/IS rows here — full opacity, full chips */}
  <tr>
    <td><strong>T5 · Trade count (n)</strong></td>
    <td className={t5n !== null && t5n !== undefined && t5n >= 50 ? styles.metricPass : styles.metricFail}>
      <strong>{t5n ?? '—'}</strong>
    </td>
    <td>≥ 50 (S34 ADR 0052)</td>
    <td className={t5n !== null && t5n !== undefined && t5n >= 50 ? styles.metricPass : styles.metricFail}>
      {t5n !== null && t5n !== undefined && t5n >= 50 ? 'PASS' : 'FAIL'}
    </td>
  </tr>
  {/* ... DSR + MC rows */}

  <tr className={styles.sectionDivider}>
    <td colSpan={4} className={styles.sectionLabel}>
      INFORMATIONAL (reference only — <a href="?strategy={request.strategy_id}#glossary" className={styles.glossaryLink}>see Glossary</a>)
    </td>
  </tr>
  {/* T1 + T2 + T3 + T4 + T6 rows here — opacity 0.55, em-dash status */}
  <tr className={styles.informationalRow}>
    <td>T1 · Sharpe OOS (annualized)</td>
    <td>{fmt(m.t1_sharpe_oos, 2)}</td>
    <td>≥ 1.0 (informational)</td>
    <td>—</td>
  </tr>
  {/* ... T2/T3/T4/T6 rows */}
</tbody>
```

- [ ] **Step 2: Add CSS для section header + informational dim**

В `MetricsTable.module.css`:

```css
/* S48 T10 — section header divider */
.sectionHeader td {
  padding: 12px 8px 4px;
}

.sectionLabel {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--color-text-muted);
  border-top: 1px solid rgba(204, 120, 92, 0.40);
}

.sectionDivider td {
  padding-top: 16px;
}

.informationalRow {
  opacity: 0.55;
}

.informationalRow td {
  /* preserve readability на dim */
}

.glossaryLink {
  color: var(--color-anthropic-orange);
  text-decoration: underline;
  text-decoration-style: dotted;
  text-underline-offset: 2px;
}

.glossaryLink:hover {
  color: var(--color-anthropic-orange);
  text-decoration-style: solid;
}
```

- [ ] **Step 3: Update existing test для new structure**

`src/dashboard_react/src/components/metrics/__tests__/MetricsTable.test.tsx` (post-T1 path):

Add test:
```typescript
it('Bug D: informational rows have section header + opacity dim (S48 T10)', () => {
  const r = { ...baseResponse, verdict: 'WFA_FAIL', metrics: {}, dsr: 0.5, dsr_pass: true, mc_p_value: 0.04 } as unknown as BacktestResponse
  render(<MetricsTable result={r} />)
  expect(screen.getByText(/GATE-BLOCKING/)).toBeInTheDocument()
  expect(screen.getByText(/INFORMATIONAL/)).toBeInTheDocument()
  // T1 row should have informationalRow class
  const t1Row = screen.getByText(/T1 · Sharpe OOS/).closest('tr')
  expect(t1Row?.className).toMatch(/informationalRow/)
})
```

- [ ] **Step 4: Build + tests clean**

```bash
cd src/dashboard_react
npm run lint && npx tsc -b && npm test -- MetricsTable
```

Expected: 8 pass (existing 7 + new T10 regression).

- [ ] **Step 5: Commit + SPRINT_STATE T10 done**

```bash
git add src/dashboard_react/src/components/metrics/MetricsTable.tsx \
        src/dashboard_react/src/components/metrics/MetricsTable.module.css \
        src/dashboard_react/src/components/metrics/__tests__/MetricsTable.test.tsx
git commit -m "feat(s48): MetricsTable section divider + grayed informational (T10 Bug D) — gate-blocking vs informational distinction"
```

Update SPRINT_STATE T10 → done.

---

## Task 11: FailAnalysisTab упрощение к chips + Glossary links (sonnet)

**Why:** Bug F — "Неизвестный критерий: t1" UX broken (3-way ID schema mismatch). Operator decision: убрать verbose lines, использовать chips ✓ Используется / ✗ Не используется + ссылки на Glossary tab для деталей.

**Files:**
- Modify: `src/dashboard_react/src/components/shared/FailAnalysisTab.tsx`
- Modify: `src/dashboard_react/src/components/shared/FailAnalysisTab.module.css`

- [ ] **Step 1: Restructure section 2 (per-criterion breakdown)**

Find existing section 2 в FailAnalysisTab.tsx. Replace verbose criterion cards с simple chip list:

```tsx
{/* Section 2 — per-criterion breakdown — S48 T11 simplified к chip list */}
<section className={styles.section}>
  <h3 className={styles.sectionTitle}>2. Применимость критериев</h3>
  <ul className={styles.criteriaList}>
    {ALL_CRITERIA.map((critId) => {
      const isFailed = failedCriteria.includes(critId)
      const chipClass = isFailed ? styles.chipUsed : styles.chipNotUsed
      const chipText = isFailed ? '✓ Используется' : '✗ Не используется'
      const glossaryLink = `?strategy=${result.request.strategy_id}#glossary-${critId}`
      return (
        <li key={critId} className={styles.criterionRow}>
          <span className={styles.criterionName}>{HUMAN_READABLE[critId] ?? critId}</span>
          <span className={chipClass}>{chipText}</span>
          <a href={glossaryLink} className={styles.glossaryLink}>→ glossary</a>
        </li>
      )
    })}
  </ul>
</section>
```

Define helper constants:
```typescript
// S48 T11 — canonical criterion list per ADR 0014 + S47 T15 semantics
const ALL_CRITERIA = ['t5_floor', 'sharpe_gate', 'mc_gate', 'dsr_threshold',
                      't1', 't2', 't3', 't4', 't6']
const HUMAN_READABLE: Record<string, string> = {
  t5_floor: 'T5 · Trade count (gate-blocking)',
  sharpe_gate: 'Fold OOS/IS Sharpe (gate-blocking)',
  mc_gate: 'Monte Carlo p-value (gate-blocking)',
  dsr_threshold: 'DSR (gate-blocking)',
  t1: 'T1 · Sharpe OOS (informational)',
  t2: 'T2 · Sortino OOS (informational)',
  t3: 'T3 · Max Drawdown (informational)',
  t4: 'T4 · Win Rate (informational)',
  t6: 'T6 · OOS/IS Sharpe ratio (informational)',
}
```

- [ ] **Step 2: Update CSS — chips + criterion list**

В `FailAnalysisTab.module.css`:

```css
.criteriaList {
  list-style: none;
  padding: 0;
  margin: 0;
}

.criterionRow {
  display: grid;
  grid-template-columns: 1fr auto auto;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid rgba(156, 163, 175, 0.10);
}

.criterionName {
  color: var(--color-text-primary);
  font-family: 'Inter', sans-serif;
  font-size: 13px;
}

.chipUsed {
  color: #00ff88;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  padding: 2px 8px;
  border: 1px solid rgba(0, 255, 136, 0.30);
  border-radius: 4px;
  background: rgba(0, 255, 136, 0.08);
}

.chipNotUsed {
  color: var(--color-text-muted);
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  padding: 2px 8px;
  border: 1px solid rgba(156, 163, 175, 0.30);
  border-radius: 4px;
  background: rgba(156, 163, 175, 0.08);
  opacity: 0.7;
}

.glossaryLink {
  color: var(--color-anthropic-orange);
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  text-decoration: none;
}

.glossaryLink:hover {
  text-decoration: underline;
}
```

- [ ] **Step 3: Remove verbose criterion-card render block**

Delete old criterion render с "Что измеряет" / "Формула" / "Почему fail" / etc rows. Replace полностью с chip list. Keep section 1 (description) + section 3 (per-fold table) unchanged.

- [ ] **Step 4: Build + lint clean**

```bash
cd src/dashboard_react
npm run lint && npx tsc -b && npm run build
```

Expected: clean.

- [ ] **Step 5: Commit + SPRINT_STATE T11 done**

```bash
git add src/dashboard_react/src/components/shared/FailAnalysisTab.tsx \
        src/dashboard_react/src/components/shared/FailAnalysisTab.module.css
git commit -m "feat(s48): FailAnalysisTab simplified к chip list + glossary links (T11 Bug F) — remove 'Неизвестный критерий' UX"
```

Update SPRINT_STATE T11 → done.

---

## Task 12: Remove ▸ prefix в DocumentationTab cards (sonnet)

**Why:** Bug G — visual hint ▸ (collapsed list indicator) misleading на DocumentationTab cards (нет раскрытия). Operator: убрать полностью.

**Files:**
- Modify: `src/dashboard_react/src/components/tabs/DocumentationTab.tsx` (post-T1 path)

- [ ] **Step 1: Find 4 DocSection title strings**

```bash
grep -n "▸ INDICATORS\|▸ MULTIPLIERS\|▸ STRATEGIES\|▸ METHODOLOGY" src/dashboard_react/src/components/tabs/DocumentationTab.tsx
```

Expected matches: lines ~300-330 (per S47 reference).

- [ ] **Step 2: Remove ▸ prefix**

Edit each:
- `▸ INDICATORS` → `INDICATORS`
- `▸ MULTIPLIERS` → `MULTIPLIERS`
- `▸ STRATEGIES` → `STRATEGIES`
- `▸ METHODOLOGY` → `METHODOLOGY`

(Keep panel-level `▸ DOCUMENTATION` title — это panel title, not card section.)

- [ ] **Step 3: Build + lint clean**

```bash
cd src/dashboard_react
npm run lint && npx tsc -b && npm run build
```

Expected: clean.

- [ ] **Step 4: Commit + SPRINT_STATE T12 done**

```bash
git add src/dashboard_react/src/components/tabs/DocumentationTab.tsx
git commit -m "fix(s48): remove ▸ prefix в DocumentationTab card titles (T12 Bug G) — misleading collapse indicator"
```

Update SPRINT_STATE T12 → done.

---

## Task 13: HistoryTab inline accordion expand (sonnet)

**Why:** Bug H — operator wants per-row expand с initial/final balance + win/lose rate + PnL + RU summary template.

**Files:**
- Modify: `src/dashboard_react/src/components/tabs/HistoryTab.tsx`
- Modify: `src/dashboard_react/src/components/tabs/HistoryTab.module.css`
- Modify: `src/dashboard_react/src/api/client.ts` — add `getRun(id)` method если missing

- [ ] **Step 1: Add `expandedRunId` state + click handler**

В `HistoryTab.tsx`:

```typescript
const [expandedRunId, setExpandedRunId] = useState<string | null>(null)
const [expandedDetails, setExpandedDetails] = useState<Record<string, BacktestResponse>>({})
const [expandError, setExpandError] = useState<Record<string, string>>({})

const handleRowClick = async (runId: string) => {
  if (expandedRunId === runId) {
    setExpandedRunId(null)
    return
  }
  setExpandedRunId(runId)
  if (!(runId in expandedDetails) && !(runId in expandError)) {
    try {
      const details = await api.getRun(runId)
      setExpandedDetails((prev) => ({ ...prev, [runId]: details }))
    } catch (err) {
      setExpandError((prev) => ({ ...prev, [runId]: err instanceof Error ? err.message : 'Fetch failed' }))
    }
  }
}

// ESC closes expand
useEffect(() => {
  const handleEsc = (e: KeyboardEvent) => {
    if (e.key === 'Escape') setExpandedRunId(null)
  }
  document.addEventListener('keydown', handleEsc)
  return () => document.removeEventListener('keydown', handleEsc)
}, [])
```

- [ ] **Step 2: Render row + expand panel**

В table body, replace per-row render с:

```tsx
{runs.map((run) => {
  const isExpanded = expandedRunId === run.run_id
  const details = expandedDetails[run.run_id]
  return (
    <Fragment key={run.run_id}>
      <tr
        onClick={() => handleRowClick(run.run_id)}
        className={`${styles.row} ${isExpanded ? styles.rowExpanded : ''}`}
        aria-expanded={isExpanded}
        aria-controls={`row-detail-${run.run_id}`}
      >
        {/* ... existing cells (Strategy, Symbol, TF, Range, Verdict, Sharpe, n trades, PnL, MC P) */}
        <td className={styles.toggleIcon}>{isExpanded ? '▾' : '▸'}</td>
      </tr>
      {isExpanded && (
        <tr id={`row-detail-${run.run_id}`} role="region" aria-label="Run details">
          <td colSpan={10}>
            <div className={styles.expandPanel}>
              <button
                className={styles.closeButton}
                onClick={() => setExpandedRunId(null)}
                aria-label="Закрыть"
              >
                ✕ закрыть
              </button>
              {expandError[run.run_id] ? (
                <div className={styles.errorMsg}>Ошибка: {expandError[run.run_id]}</div>
              ) : !details ? (
                <div className={styles.loadingMsg}>Загрузка деталей...</div>
              ) : (
                <RunDetailsPanel details={details} />
              )}
            </div>
          </td>
        </tr>
      )}
    </Fragment>
  )
})}
```

- [ ] **Step 3: Add `RunDetailsPanel` sub-component**

В same file (или separate если предпочитаешь):

```tsx
function RunDetailsPanel({ details }: { details: BacktestResponse }) {
  const ts = details.trade_stats ?? {}
  const initialBalance = (ts as any).initial_balance_quote ?? 10000
  const finalBalance = (ts as any).final_balance_quote ?? initialBalance * (1 + (details.total_pnl_pct ?? 0) / 100)
  const winRate = (ts.win_rate ?? 0) * 100
  const loseRate = 100 - winRate
  const pnlUsdt = finalBalance - initialBalance
  const pnlPct = details.total_pnl_pct ?? 0
  const profitFactor = (ts as any).profit_factor

  // S48 T13 — RU summary template branched by verdict
  const summary = renderSummary(details)

  return (
    <div className={styles.detailsBody}>
      <div className={styles.detailsGrid}>
        <div className={styles.detailItem}>
          <span className={styles.detailLabel}>Начальный баланс</span>
          <span className={styles.detailValue}>${initialBalance.toFixed(2)}</span>
        </div>
        <div className={styles.detailItem}>
          <span className={styles.detailLabel}>Итоговый баланс</span>
          <span className={styles.detailValue}>${finalBalance.toFixed(2)}</span>
        </div>
        <div className={styles.detailItem}>
          <span className={styles.detailLabel}>Win rate</span>
          <span className={styles.detailValue}>{winRate.toFixed(1)}%</span>
        </div>
        <div className={styles.detailItem}>
          <span className={styles.detailLabel}>Lose rate</span>
          <span className={styles.detailValue}>{loseRate.toFixed(1)}%</span>
        </div>
        <div className={styles.detailItem}>
          <span className={styles.detailLabel}>Total PnL</span>
          <span className={pnlPct >= 0 ? styles.detailValuePos : styles.detailValueNeg}>
            {pnlPct >= 0 ? '+' : ''}${pnlUsdt.toFixed(2)} ({pnlPct >= 0 ? '+' : ''}{pnlPct.toFixed(2)}%)
          </span>
        </div>
        {profitFactor !== null && profitFactor !== undefined && (
          <div className={styles.detailItem}>
            <span className={styles.detailLabel}>Profit Factor</span>
            <span className={styles.detailValue}>{profitFactor.toFixed(2)}</span>
          </div>
        )}
      </div>
      <hr className={styles.detailsDivider} />
      <p className={styles.summary}>{summary}</p>
    </div>
  )
}

function renderSummary(details: BacktestResponse): string {
  const verdict = details.verdict
  const preset = details.request.strategy_label ?? details.request.strategy_id
  const failedCriteria = details.failed_criteria ?? []
  const metrics = details.metrics ?? {}

  if (verdict === 'WFA_PASS' || verdict === 'PASS') {
    return `Стратегия "${preset}" сработала: пройдены все обязательные acceptance gates. ` +
      `Win rate ${((details.trade_stats?.win_rate ?? 0) * 100).toFixed(1)}%, total PnL ` +
      `${(details.total_pnl_pct ?? 0).toFixed(2)}%. Strategy показала статистически значимый edge.`
  }
  if (verdict === 'WFA_FAIL' || verdict === 'FAIL') {
    const primaryFailed = failedCriteria[0] ?? 'unknown'
    return `Стратегия "${preset}" не прошла WFA discipline. Provoking criterion: ${primaryFailed}. ` +
      `Total PnL ${(details.total_pnl_pct ?? 0).toFixed(2)}%, win rate ${((details.trade_stats?.win_rate ?? 0) * 100).toFixed(1)}%. ` +
      `Использовать в live НЕ рекомендуется — см. Glossary вкладку для деталей.`
  }
  if (verdict === 'WFA_FAIL_DATA') {
    return `Стратегия "${preset}" не прошла из-за недостатка данных (n_trades < 50 OR fold count < 5). ` +
      `Не статистически значимый результат. Требуется больше OOS sample data.`
  }
  if (verdict === 'RAW') {
    return `Стратегия "${preset}" — full-period backtest без WFA discipline. ` +
      `Total PnL ${(details.total_pnl_pct ?? 0).toFixed(2)}%, ` +
      `win rate ${((details.trade_stats?.win_rate ?? 0) * 100).toFixed(1)}%. ` +
      `Подвержен look-ahead bias. Не basis для live decisions.`
  }
  return `Verdict ${verdict ?? '—'}. Total PnL ${(details.total_pnl_pct ?? 0).toFixed(2)}%.`
}
```

- [ ] **Step 4: Add CSS для expand panel**

В `HistoryTab.module.css`:

```css
.row {
  cursor: pointer;
  transition: background-color 150ms ease;
}

.row:hover {
  background: rgba(204, 120, 92, 0.06);
}

.rowExpanded {
  background: rgba(204, 120, 92, 0.10);
}

.toggleIcon {
  font-family: 'JetBrains Mono', monospace;
  color: var(--color-anthropic-orange);
  text-align: center;
}

.expandPanel {
  position: relative;
  padding: 16px;
  background: rgba(10, 10, 10, 0.40);
  border-left: 3px solid var(--color-anthropic-orange);
  border-radius: 4px;
  margin: 8px 0;
}

.closeButton {
  position: absolute;
  top: 12px;
  right: 12px;
  background: transparent;
  border: 1px solid rgba(156, 163, 175, 0.30);
  color: var(--color-text-muted);
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  padding: 4px 10px;
  border-radius: 4px;
  cursor: pointer;
}

.closeButton:hover {
  border-color: var(--color-anthropic-orange);
  color: var(--color-anthropic-orange);
}

.detailsBody {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.detailsGrid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.detailItem {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detailLabel {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: var(--color-text-muted);
  text-transform: uppercase;
}

.detailValue {
  font-family: 'JetBrains Mono', monospace;
  font-size: 14px;
  color: var(--color-text-primary);
}

.detailValuePos {
  color: #00ff88;
  font-family: 'JetBrains Mono', monospace;
  font-size: 14px;
}

.detailValueNeg {
  color: #ff3366;
  font-family: 'JetBrains Mono', monospace;
  font-size: 14px;
}

.detailsDivider {
  border: none;
  border-top: 1px solid rgba(156, 163, 175, 0.20);
  margin: 8px 0;
}

.summary {
  color: var(--color-text-primary);
  font-family: 'Inter', sans-serif;
  font-size: 13px;
  line-height: 1.5;
}

.loadingMsg, .errorMsg {
  color: var(--color-text-muted);
  font-family: 'Inter', sans-serif;
  font-size: 13px;
  padding: 16px;
  text-align: center;
}

.errorMsg {
  color: #ff3366;
}
```

- [ ] **Step 5: Verify api.getRun method exists**

```bash
grep -n "getRun" src/dashboard_react/src/api/client.ts
```

Если method не exists, add:
```typescript
async getRun(runId: string): Promise<BacktestResponse> {
  return request(`/api/runs/${encodeURIComponent(runId)}`);
}
```

- [ ] **Step 6: Build + lint clean**

```bash
cd src/dashboard_react
npm run lint && npx tsc -b && npm run build
```

Expected: clean.

- [ ] **Step 7: Commit + SPRINT_STATE T13 done**

```bash
git add src/dashboard_react/src/components/tabs/HistoryTab.tsx \
        src/dashboard_react/src/components/tabs/HistoryTab.module.css \
        src/dashboard_react/src/api/client.ts
git commit -m "feat(s48): HistoryTab accordion expand (T13 Bug H) — single-open + ESC close + RU summary"
```

Update SPRINT_STATE T13 → done.

---

## Task 14: HistoryTab RTL tests (sonnet)

**Files:**
- Create: `src/dashboard_react/src/components/tabs/__tests__/HistoryTab.test.tsx`

- [ ] **Step 1: Write tests**

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { HistoryTab } from '../HistoryTab'

vi.mock('@/api/client', () => ({
  api: {
    getRuns: vi.fn().mockResolvedValue([
      {
        run_id: 'run1',
        request: { strategy_id: 'ema_crossover_s13', strategy_label: 'EMA', symbol: 'BTC', interval: '60', interval_label: '1h', start: '2023-01-01', end: '2023-12-31' },
        verdict: 'WFA_FAIL',
        metrics: { t1_sharpe_oos: 0.5, t5_n_trades: 80 },
        warnings_count: 1,
      },
    ]),
    getRun: vi.fn().mockResolvedValue({
      run_id: 'run1',
      verdict: 'WFA_FAIL',
      total_pnl_pct: -5.0,
      trade_stats: { win_rate: 0.4, n_trades: 80, profit_factor: 0.85 },
      failed_criteria: ['t5_floor'],
      request: { strategy_id: 'ema_crossover_s13', strategy_label: 'EMA' },
    }),
  },
}))

describe('HistoryTab — accordion expand (S48 T13)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('row click expands details panel', async () => {
    render(<HistoryTab />)
    await waitFor(() => expect(screen.getByText('EMA')).toBeInTheDocument())

    const row = screen.getByText('EMA').closest('tr')!
    fireEvent.click(row)

    await waitFor(() => expect(screen.getByText(/Начальный баланс/)).toBeInTheDocument())
    expect(screen.getByText(/Итоговый баланс/)).toBeInTheDocument()
    expect(screen.getByText(/Win rate/)).toBeInTheDocument()
  })

  it('ESC key closes expanded row', async () => {
    render(<HistoryTab />)
    await waitFor(() => expect(screen.getByText('EMA')).toBeInTheDocument())

    fireEvent.click(screen.getByText('EMA').closest('tr')!)
    await waitFor(() => expect(screen.getByText(/Начальный баланс/)).toBeInTheDocument())

    fireEvent.keyDown(document, { key: 'Escape' })
    await waitFor(() => expect(screen.queryByText(/Начальный баланс/)).not.toBeInTheDocument())
  })

  it('RU summary text branches by verdict', async () => {
    render(<HistoryTab />)
    await waitFor(() => expect(screen.getByText('EMA')).toBeInTheDocument())
    fireEvent.click(screen.getByText('EMA').closest('tr')!)

    await waitFor(() => expect(screen.getByText(/не прошла WFA discipline/)).toBeInTheDocument())
  })
})
```

- [ ] **Step 2: Run tests**

```bash
cd src/dashboard_react
npm test -- HistoryTab
```

Expected: 3 pass.

- [ ] **Step 3: Commit + SPRINT_STATE T14 done**

```bash
git add src/dashboard_react/src/components/tabs/__tests__/HistoryTab.test.tsx
git commit -m "test(s48): HistoryTab accordion + ESC close + RU summary RTL tests (T14)"
```

Update SPRINT_STATE T14 → done.

---

## Bucket C — Glossary tab (NEW)

## Task 15: GlossaryTab base component (opus)

**Why opus:** Большой новый компонент (~250 lines TSX + ~150 lines CSS). Section-based layout с sticky TOC, anchor-based deeplink, responsive layout decisions. Judgment-heavy info architecture.

**Files:**
- Create: `src/dashboard_react/src/components/tabs/GlossaryTab.tsx`
- Create: `src/dashboard_react/src/components/tabs/GlossaryTab.module.css`
- Modify: `src/dashboard_react/src/api/types.ts` — `GlossaryEntry`, `GlossaryResponse` types
- Modify: `src/dashboard_react/src/api/client.ts` — `getGlossary()` method

- [ ] **Step 1: Add types к types.ts**

```typescript
export interface GlossaryEntry {
  section: string;
  description_ru: string;
  applies_to: string[];
  adr_ref?: string | null;
}

export interface GlossaryResponse {
  entries: Record<string, GlossaryEntry>;
  strategy_to_metrics: Record<string, string[]>;
  sections: string[];
}
```

- [ ] **Step 2: Add API method**

В `client.ts`:
```typescript
async getGlossary(): Promise<GlossaryResponse> {
  return request('/api/glossary');
}
```

- [ ] **Step 3: Create GlossaryTab base — section-based layout с sticky TOC**

`src/dashboard_react/src/components/tabs/GlossaryTab.tsx`:

```tsx
// GlossaryTab — S48 T15-T17 (Bug E core).
// RU расшифровка всех аббревиатур + dynamic per-strategy filter (T16) + search (T17).
// Architecture: section-based с sticky TOC. URL query state per architect C2.

import { useEffect, useState, useMemo } from 'react'
import { api } from '@/api/client'
import type { GlossaryResponse, GlossaryEntry } from '@/api/types'
import { useStrategyContext } from '@/hooks/useStrategyContext'
import styles from './GlossaryTab.module.css'

const SECTION_LABELS: Record<string, string> = {
  verdict_status: 'Вердикты и символы статуса',
  gate_blocking_metrics: 'Gate-blocking metrics',
  informational_metrics: 'Informational metrics',
  trade_statistics: 'Торговая статистика',
  chart_vocabulary: 'Графики',
  monthly_heatmap: 'Heatmap по месяцам',
  warnings: 'Предупреждения',
  strategy_presets: 'Пресеты стратегий',
}

export function GlossaryTab() {
  const [glossary, setGlossary] = useState<GlossaryResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { currentStrategy } = useStrategyContext()

  useEffect(() => {
    let cancelled = false
    api.getGlossary()
      .then((data) => {
        if (cancelled) return
        setGlossary(data)
        setLoading(false)
      })
      .catch((err: Error) => {
        if (cancelled) return
        setError(err.message)
        setLoading(false)
      })
    return () => { cancelled = true }
  }, [])

  // Group entries by section (memoized)
  const entriesBySection = useMemo(() => {
    if (glossary === null) return {}
    const grouped: Record<string, Array<[string, GlossaryEntry]>> = {}
    for (const [term, entry] of Object.entries(glossary.entries)) {
      const section = entry.section
      if (!(section in grouped)) grouped[section] = []
      grouped[section]!.push([term, entry])
    }
    return grouped
  }, [glossary])

  // Applicable terms set per current strategy (T16)
  const applicableTerms = useMemo(() => {
    if (glossary === null || currentStrategy === null) return null
    return new Set(glossary.strategy_to_metrics[currentStrategy] ?? [])
  }, [glossary, currentStrategy])

  // Anchor scroll on mount если location.hash present
  useEffect(() => {
    if (loading || glossary === null) return
    const hash = window.location.hash
    if (!hash.startsWith('#glossary-')) return
    const anchorId = hash.slice(1)
    setTimeout(() => {
      const el = document.getElementById(anchorId)
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'start' })
        el.classList.add(styles.entryHighlightPulse ?? '')
        setTimeout(() => el.classList.remove(styles.entryHighlightPulse ?? ''), 1500)
      }
    }, 200)
  }, [loading, glossary])

  if (loading) return <div className={styles.loading}>Загрузка глоссария...</div>
  if (error !== null) return <div className={styles.error}>Ошибка: {error}</div>
  if (glossary === null) return null

  return (
    <div className={styles.container}>
      <div className={styles.title}>▸ ГЛОССАРИЙ — РУССКИЕ ОБОЗНАЧЕНИЯ</div>

      {currentStrategy !== null && (
        <div className={styles.filterHeader}>
          <span>Filter: <strong>{currentStrategy}</strong> — выделены применимые termы</span>
        </div>
      )}

      <div className={styles.layout}>
        {/* Sticky TOC */}
        <nav className={styles.toc}>
          <h4 className={styles.tocTitle}>Содержание</h4>
          <ul>
            {glossary.sections.map((section) => (
              <li key={section}>
                <a href={`#section-${section}`} className={styles.tocLink}>
                  {SECTION_LABELS[section] ?? section}
                </a>
              </li>
            ))}
          </ul>
        </nav>

        {/* Sections */}
        <div className={styles.sections}>
          {glossary.sections.map((section) => {
            const entries = entriesBySection[section] ?? []
            if (entries.length === 0) return null
            return (
              <section key={section} id={`section-${section}`} className={styles.section}>
                <h3 className={styles.sectionTitle}>{SECTION_LABELS[section] ?? section}</h3>
                {entries.map(([term, entry]) => {
                  const isApplicable = applicableTerms === null OR applicableTerms.has(term)
                  return (
                    <article
                      key={term}
                      id={`glossary-${term}`}
                      className={`${styles.entry} ${isApplicable ? styles.entryApplicable : styles.entryDimmed}`}
                    >
                      <div className={styles.entryHeader}>
                        <span className={styles.entryTerm}>{term}</span>
                        {entry.adr_ref && <span className={styles.entryAdrRef}>{entry.adr_ref}</span>}
                      </div>
                      <p className={styles.entryDescription}>{entry.description_ru}</p>
                      <div className={styles.entryAppliesTo}>
                        Используется в: {entry.applies_to.includes('*') ? 'все стратегии' : entry.applies_to.join(', ')}
                      </div>
                    </article>
                  )
                })}
              </section>
            )
          })}
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Create CSS**

`GlossaryTab.module.css` (~150 lines):

```css
.container {
  background: var(--color-bg-glass);
  border: 1px solid rgba(204, 120, 92, 0.30);
  border-radius: 8px;
  padding: 24px;
  margin-bottom: 24px;
  backdrop-filter: blur(8px);
}

.title {
  color: var(--color-anthropic-orange);
  font-family: 'JetBrains Mono', monospace;
  font-size: 14px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(204, 120, 92, 0.30);
}

.filterHeader {
  background: rgba(204, 120, 92, 0.10);
  border: 1px solid rgba(204, 120, 92, 0.30);
  border-radius: 6px;
  padding: 8px 12px;
  margin-bottom: 16px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  color: var(--color-text-primary);
}

.layout {
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: 24px;
}

.toc {
  position: sticky;
  top: 16px;
  align-self: start;
  border-right: 1px solid rgba(156, 163, 175, 0.20);
  padding-right: 16px;
}

.tocTitle {
  color: var(--color-anthropic-orange);
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  text-transform: uppercase;
  margin-bottom: 12px;
}

.toc ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.tocLink {
  display: block;
  padding: 6px 8px;
  color: var(--color-text-muted);
  font-family: 'Inter', sans-serif;
  font-size: 12px;
  text-decoration: none;
  border-radius: 4px;
  transition: all 150ms ease;
}

.tocLink:hover {
  background: rgba(204, 120, 92, 0.10);
  color: var(--color-anthropic-orange);
}

.sections {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.sectionTitle {
  color: var(--color-anthropic-orange);
  font-family: 'Inter', sans-serif;
  font-size: 16px;
  font-weight: 600;
  border-bottom: 1px solid rgba(204, 120, 92, 0.20);
  padding-bottom: 8px;
}

.entry {
  background: rgba(10, 10, 10, 0.40);
  border: 1px solid rgba(156, 163, 175, 0.15);
  border-radius: 6px;
  padding: 12px 16px;
  transition: all 200ms ease;
}

.entryApplicable {
  border-left: 3px solid var(--color-anthropic-orange);
  background: rgba(204, 120, 92, 0.06);
  box-shadow: 0 0 8px rgba(204, 120, 92, 0.15);
}

.entryDimmed {
  opacity: 0.45;
}

.entryHighlightPulse {
  animation: pulse-orange 1.5s ease-in-out;
}

@keyframes pulse-orange {
  0%, 100% { box-shadow: 0 0 8px rgba(204, 120, 92, 0.15); }
  50% { box-shadow: 0 0 24px rgba(204, 120, 92, 0.60); }
}

.entryHeader {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 6px;
}

.entryTerm {
  color: var(--color-anthropic-orange);
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  font-weight: 700;
}

.entryAdrRef {
  color: var(--color-text-muted);
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
}

.entryDescription {
  color: var(--color-text-primary);
  font-family: 'Inter', sans-serif;
  font-size: 13px;
  line-height: 1.5;
  margin: 0 0 6px;
}

.entryAppliesTo {
  color: var(--color-text-muted);
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
}

.loading, .error {
  color: var(--color-text-muted);
  font-family: 'Inter', sans-serif;
  padding: 16px;
  text-align: center;
}

.error {
  color: #ff3366;
}
```

- [ ] **Step 5: Build verify**

```bash
cd src/dashboard_react
npm run lint && npx tsc -b && npm run build
```

Expected: clean (note useStrategyContext import will fail until T18 — skip lint/tsc here, defer к T19 final integration).

- [ ] **Step 6: Commit + SPRINT_STATE T15 done**

```bash
git add src/dashboard_react/src/components/tabs/GlossaryTab.tsx \
        src/dashboard_react/src/components/tabs/GlossaryTab.module.css \
        src/dashboard_react/src/api/types.ts \
        src/dashboard_react/src/api/client.ts
git commit -m "feat(s48): GlossaryTab base component + types + API method (T15 opus Bug E core)"
```

Update SPRINT_STATE T15 → done.

---

## Task 16: GlossaryTab dynamic filter (T15 уже базу заложил) (opus)

**Note:** Базовая filter logic уже в T15 (`applicableTerms` Set + `entryApplicable`/`entryDimmed` classes). T16 = verify + add tests + edge cases.

**Files:**
- Modify: `src/dashboard_react/src/components/tabs/GlossaryTab.tsx` (refinements)

- [ ] **Step 1: Verify behavior — without strategy, all entries applicable (full opacity)**

Если `currentStrategy === null` → `applicableTerms === null` → `isApplicable = true` для all. Verify в коде:

```typescript
const isApplicable = applicableTerms === null OR applicableTerms.has(term)
// → true if applicableTerms is null
// → true if term in applicableTerms
// → false otherwise
```

- [ ] **Step 2: Add edge case — strategy not in map**

Если operator выбрал стратегию но map не содержит её:

```typescript
const applicableTerms = useMemo(() => {
  if (glossary === null || currentStrategy === null) return null
  const list = glossary.strategy_to_metrics[currentStrategy]
  if (list === undefined) {
    console.warn(`Glossary: strategy "${currentStrategy}" not in map — showing all entries`)
    return null  // Treat as no-strategy (show all)
  }
  return new Set(list)
}, [glossary, currentStrategy])
```

- [ ] **Step 3: Build clean (after T18 useStrategyContext exists)**

```bash
cd src/dashboard_react
npm run lint && npx tsc -b
```

- [ ] **Step 4: Commit + SPRINT_STATE T16 done**

```bash
git add src/dashboard_react/src/components/tabs/GlossaryTab.tsx
git commit -m "feat(s48): GlossaryTab dynamic filter edge cases (T16 Bug E filter UX)"
```

Update SPRINT_STATE T16 → done.

---

## Task 17: GlossaryTab search input (sonnet)

**Files:**
- Modify: `src/dashboard_react/src/components/tabs/GlossaryTab.tsx`
- Modify: `GlossaryTab.module.css`

- [ ] **Step 1: Add search state + filter logic**

В GlossaryTab:

```typescript
const [searchQuery, setSearchQuery] = useState('')

const filteredEntries = useMemo(() => {
  if (glossary === null) return {}
  const q = searchQuery.trim().toLowerCase()
  if (q === '') return entriesBySection  // No search → return grouped

  // With search: flat results matching query (in term OR description)
  const results: Array<[string, GlossaryEntry]> = []
  for (const [term, entry] of Object.entries(glossary.entries)) {
    if (term.toLowerCase().includes(q) || entry.description_ru.toLowerCase().includes(q)) {
      results.push([term, entry])
    }
  }
  return { search_results: results }  // Flat single section
}, [glossary, searchQuery, entriesBySection])
```

- [ ] **Step 2: Render search input в filterHeader**

Replace existing filterHeader markup:

```tsx
<div className={styles.filterHeader}>
  <input
    type="search"
    placeholder="Поиск по термам или описанию..."
    value={searchQuery}
    onChange={(e) => setSearchQuery(e.target.value)}
    className={styles.searchInput}
  />
  {currentStrategy !== null && searchQuery === '' && (
    <span className={styles.filterHint}>
      Filter: <strong>{currentStrategy}</strong>
    </span>
  )}
  {searchQuery !== '' && (
    <span className={styles.filterHint}>
      Найдено: {Object.values(filteredEntries).flat().length}
    </span>
  )}
</div>
```

- [ ] **Step 3: Update sections render для filtered entries**

```tsx
{searchQuery !== '' ? (
  // Flat search results
  <section className={styles.section}>
    <h3 className={styles.sectionTitle}>Результаты поиска</h3>
    {(filteredEntries.search_results ?? []).map(([term, entry]) => (
      <article key={term} id={`glossary-${term}`} className={styles.entry}>
        {/* ... entry content same as Step 3 в T15 */}
      </article>
    ))}
  </section>
) : (
  // Default sectioned layout (T15 + T16 logic)
  glossary.sections.map(/* ... */)
)}
```

- [ ] **Step 4: Add search input CSS**

```css
.searchInput {
  flex: 1;
  background: rgba(0, 0, 0, 0.40);
  border: 1px solid rgba(156, 163, 175, 0.30);
  color: var(--color-text-primary);
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  padding: 6px 10px;
  border-radius: 4px;
  outline: none;
  transition: border-color 150ms ease;
}

.searchInput:focus {
  border-color: var(--color-anthropic-orange);
}

.filterHint {
  color: var(--color-text-muted);
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
}

/* Update filterHeader к flex */
.filterHeader {
  display: flex;
  align-items: center;
  gap: 12px;
  /* ... existing styles */
}
```

- [ ] **Step 5: Build clean**

```bash
cd src/dashboard_react
npm run lint && npx tsc -b && npm run build
```

- [ ] **Step 6: Commit + SPRINT_STATE T17 done**

```bash
git add src/dashboard_react/src/components/tabs/GlossaryTab.tsx \
        src/dashboard_react/src/components/tabs/GlossaryTab.module.css
git commit -m "feat(s48): GlossaryTab search input (T17 Bug E search) — case-insensitive substring filter"
```

Update SPRINT_STATE T17 → done.

---

## Task 18: useStrategyContext hook (URL query state) (sonnet)

**Why:** architect C2 BINDING — cross-tab state via URL query param `?strategy=<id>`. NO Context/Zustand/localStorage. ConfigureBacktest writes on selection, GlossaryTab reads.

**Files:**
- Create: `src/dashboard_react/src/hooks/useStrategyContext.ts`

- [ ] **Step 1: Implement hook**

```typescript
// useStrategyContext — S48 T18 (architect C2 BINDING).
// Read/write `?strategy=<id>` URL query param. No Context/Zustand.

import { useState, useEffect, useCallback } from 'react'

const PARAM_NAME = 'strategy'

function readStrategy(): string | null {
  if (typeof window === 'undefined') return null
  const params = new URLSearchParams(window.location.search)
  return params.get(PARAM_NAME)
}

export function useStrategyContext() {
  const [currentStrategy, setCurrentStrategyState] = useState<string | null>(readStrategy)

  // Listen для URL changes (popstate when user navigates back/forward)
  useEffect(() => {
    const handler = () => setCurrentStrategyState(readStrategy())
    window.addEventListener('popstate', handler)
    return () => window.removeEventListener('popstate', handler)
  }, [])

  const setCurrentStrategy = useCallback((strategyId: string | null) => {
    const url = new URL(window.location.href)
    if (strategyId === null) {
      url.searchParams.delete(PARAM_NAME)
    } else {
      url.searchParams.set(PARAM_NAME, strategyId)
    }
    // Use history.replaceState — no entry in browser history (silent update)
    window.history.replaceState({}, '', url.toString())
    setCurrentStrategyState(strategyId)
  }, [])

  return { currentStrategy, setCurrentStrategy }
}
```

- [ ] **Step 2: Add unit tests**

`src/dashboard_react/src/hooks/__tests__/useStrategyContext.test.ts`:

```typescript
import { describe, it, expect, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useStrategyContext } from '../useStrategyContext'

describe('useStrategyContext — URL query param state (S48 T18)', () => {
  beforeEach(() => {
    window.history.replaceState({}, '', '/')
  })

  it('initial state — null when no query param', () => {
    const { result } = renderHook(() => useStrategyContext())
    expect(result.current.currentStrategy).toBeNull()
  })

  it('initial state — reads existing query param', () => {
    window.history.replaceState({}, '', '/?strategy=ema_crossover_s13')
    const { result } = renderHook(() => useStrategyContext())
    expect(result.current.currentStrategy).toBe('ema_crossover_s13')
  })

  it('setCurrentStrategy updates URL + state', () => {
    const { result } = renderHook(() => useStrategyContext())
    act(() => result.current.setCurrentStrategy('mean_reversion_s15'))
    expect(result.current.currentStrategy).toBe('mean_reversion_s15')
    expect(window.location.search).toBe('?strategy=mean_reversion_s15')
  })

  it('setCurrentStrategy(null) clears URL param', () => {
    window.history.replaceState({}, '', '/?strategy=ema_crossover_s13&other=foo')
    const { result } = renderHook(() => useStrategyContext())
    act(() => result.current.setCurrentStrategy(null))
    expect(result.current.currentStrategy).toBeNull()
    expect(window.location.search).toBe('?other=foo')
  })
})
```

- [ ] **Step 3: Run tests**

```bash
cd src/dashboard_react
npm test -- useStrategyContext
```

Expected: 4 pass.

- [ ] **Step 4: Wire ConfigureBacktest к useStrategyContext.setCurrentStrategy**

В `ConfigureBacktest.tsx` (post-T1 path), add при strategy selection:

```typescript
import { useStrategyContext } from '@/hooks/useStrategyContext'

const { setCurrentStrategy } = useStrategyContext()

const handleStrategyChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
  const newStrategy = e.target.value
  setStrategyId(newStrategy)
  setCurrentStrategy(newStrategy)  // S48 T18 — propagate к Glossary via URL
}

// Update select onChange:
<select value={strategyId} onChange={handleStrategyChange} className={styles.select}>
```

- [ ] **Step 5: Build clean**

```bash
cd src/dashboard_react
npm run lint && npx tsc -b && npm run build
```

Expected: clean.

- [ ] **Step 6: Commit + SPRINT_STATE T18 done**

```bash
git add src/dashboard_react/src/hooks/useStrategyContext.ts \
        src/dashboard_react/src/hooks/__tests__/useStrategyContext.test.ts \
        src/dashboard_react/src/components/forms/ConfigureBacktest.tsx
git commit -m "feat(s48): useStrategyContext URL query state hook (T18 architect C2) + ConfigureBacktest wire"
```

Update SPRINT_STATE T18 → done.

---

## Task 19: Register Glossary tab в App.tsx navigation (sonnet)

**Files:**
- Modify: `src/dashboard_react/src/App.tsx`
- Modify: `src/dashboard_react/src/App.module.css`

- [ ] **Step 1: Add 4-th tab к navigation**

В `App.tsx`:

```typescript
import { GlossaryTab } from './components/tabs/GlossaryTab'

type Tab = 'backtest' | 'documentation' | 'history' | 'glossary'

const TABS: { id: Tab; num: string; label: string }[] = [
  { id: 'backtest', num: '01', label: 'BACKTEST' },
  { id: 'documentation', num: '02', label: 'DOCUMENTATION' },
  { id: 'history', num: '03', label: 'HISTORY' },
  { id: 'glossary', num: '04', label: 'GLOSSARY' },  // S48 T19 NEW
]

// In render — add к existing tab content switch:
{activeTab === 'glossary' && <GlossaryTab />}
```

- [ ] **Step 2: Verify nav CSS supports 4 tabs (no hardcoded 3-tab grid)**

```bash
grep -n "tabNav\|gridTemplateColumns" src/dashboard_react/src/App.module.css
```

Likely `flex` or auto-grid — 4 tabs work без CSS change. Verify visually.

- [ ] **Step 3: Build clean**

```bash
cd src/dashboard_react
npm run lint && npx tsc -b && npm run build
```

Expected: clean.

- [ ] **Step 4: Commit + SPRINT_STATE T19 done**

```bash
git add src/dashboard_react/src/App.tsx src/dashboard_react/src/App.module.css
git commit -m "feat(s48): register Glossary tab в App nav (T19) — 4-th tab"
```

Update SPRINT_STATE T19 → done.

---

## Bucket D — Bybit integration

## Task 20: useBybitBalance hook (sonnet)

**Files:**
- Create: `src/dashboard_react/src/hooks/useBybitBalance.ts`

- [ ] **Step 1: Implement hook**

```typescript
// useBybitBalance — S48 T20.
// Fetch /api/bybit/balance с graceful fallback + localStorage cache.

import { useState, useEffect, useCallback } from 'react'
import { api } from '@/api/client'
import type { BalanceResponse } from '@/api/types'

const CACHE_KEY = 'bybit_balance_cache_v1'
const FALLBACK_BALANCE = 10000

export function useBybitBalance() {
  const [balance, setBalance] = useState<number>(FALLBACK_BALANCE)
  const [source, setSource] = useState<string>('fallback')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [fetchedAt, setFetchedAt] = useState<string>('')

  const fetchBalance = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.getBalance()
      setBalance(data.total_equity_usdt)
      setSource(data.source)
      setError(data.error ?? null)
      setFetchedAt(data.fetched_at_iso)
      // Cache successful fetches (not fallback)
      if (data.source === 'bybit_v5') {
        localStorage.setItem(CACHE_KEY, JSON.stringify(data))
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      // Try cache fallback
      const cached = localStorage.getItem(CACHE_KEY)
      if (cached) {
        try {
          const parsed = JSON.parse(cached) as BalanceResponse
          setBalance(parsed.total_equity_usdt)
          setSource('cached')
          setError(`Network error, using cached: ${msg}`)
          setFetchedAt(parsed.fetched_at_iso)
        } catch {
          setError(msg)
        }
      } else {
        setError(msg)
      }
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchBalance()
  }, [fetchBalance])

  return { balance, source, error, loading, fetchedAt, refresh: fetchBalance }
}
```

- [ ] **Step 2: Add `BalanceResponse` type + API method**

`types.ts`:
```typescript
export interface BalanceResponse {
  source: 'bybit_v5' | 'fallback' | 'cached';
  total_equity_usdt: number;
  fetched_at_iso: string;
  error?: string | null;
}
```

`client.ts`:
```typescript
async getBalance(): Promise<BalanceResponse> {
  return request('/api/bybit/balance');
}
```

- [ ] **Step 3: Build clean**

```bash
cd src/dashboard_react
npm run lint && npx tsc -b
```

- [ ] **Step 4: Commit + SPRINT_STATE T20 done**

```bash
git add src/dashboard_react/src/hooks/useBybitBalance.ts \
        src/dashboard_react/src/api/types.ts \
        src/dashboard_react/src/api/client.ts
git commit -m "feat(s48): useBybitBalance hook + BalanceResponse type (T20) — Bybit fetch + localStorage cache"
```

Update SPRINT_STATE T20 → done.

---

## Task 21: BalanceBadge component (sonnet)

**Files:**
- Create: `src/dashboard_react/src/components/shared/BalanceBadge.tsx`
- Create: `src/dashboard_react/src/components/shared/BalanceBadge.module.css`

- [ ] **Step 1: Implement badge component**

```tsx
// BalanceBadge — S48 T21. Visual states для useBybitBalance hook.

import type { BalanceResponse } from '@/api/types'
import styles from './BalanceBadge.module.css'

interface BalanceBadgeProps {
  source: string
  balance: number
  loading: boolean
  error: string | null
}

export function BalanceBadge({ source, balance, loading, error }: BalanceBadgeProps) {
  if (loading) {
    return (
      <div className={`${styles.badge} ${styles.badgeLoading}`}>
        <span className={styles.dot}>◌</span> Fetching balance…
      </div>
    )
  }
  if (source === 'bybit_v5') {
    return (
      <div className={`${styles.badge} ${styles.badgeLive}`}>
        <span className={styles.dot}>●</span> LIVE · Bybit V5
      </div>
    )
  }
  if (source === 'cached') {
    return (
      <div className={`${styles.badge} ${styles.badgeCached}`}>
        <span className={styles.dot}>◐</span> CACHED · last known
      </div>
    )
  }
  // fallback
  return (
    <div className={`${styles.badge} ${styles.badgeFallback}`} title={error ?? 'No API keys'}>
      <span className={styles.dot}>⚠</span> OFFLINE — fallback ${balance.toFixed(0)}
    </div>
  )
}
```

- [ ] **Step 2: CSS**

```css
.badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  font-weight: 600;
  border-radius: 4px;
  border: 1px solid;
}

.dot {
  font-size: 10px;
}

.badgeLive {
  color: #00ff88;
  border-color: rgba(0, 255, 136, 0.40);
  background: rgba(0, 255, 136, 0.08);
}

.badgeLive .dot {
  animation: pulse-green 2s ease-in-out infinite;
}

@keyframes pulse-green {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.badgeCached {
  color: #ffaa00;
  border-color: rgba(255, 170, 0, 0.40);
  background: rgba(255, 170, 0, 0.08);
}

.badgeFallback {
  color: #ff3366;
  border-color: rgba(255, 51, 102, 0.40);
  background: rgba(255, 51, 102, 0.08);
}

.badgeLoading {
  color: var(--color-anthropic-orange);
  border-color: rgba(204, 120, 92, 0.40);
  background: rgba(204, 120, 92, 0.08);
}
```

- [ ] **Step 3: Build clean**

```bash
cd src/dashboard_react
npm run lint && npx tsc -b && npm run build
```

- [ ] **Step 4: Commit + SPRINT_STATE T21 done**

```bash
git add src/dashboard_react/src/components/shared/BalanceBadge.tsx \
        src/dashboard_react/src/components/shared/BalanceBadge.module.css
git commit -m "feat(s48): BalanceBadge component (T21) — LIVE/CACHED/OFFLINE/Loading visual states"
```

Update SPRINT_STATE T21 → done.

---

## Task 22: ConfigureBacktest balance integration (sonnet)

**Files:**
- Modify: `src/dashboard_react/src/components/forms/ConfigureBacktest.tsx`
- Modify: `src/dashboard_react/src/components/forms/ConfigureBacktest.module.css`
- Modify: `src/dashboard_react/src/App.tsx` — pass initialBalance к EquityChart

- [ ] **Step 1: Wire useBybitBalance + BalanceBadge в ConfigureBacktest**

```tsx
import { useBybitBalance } from '@/hooks/useBybitBalance'
import { BalanceBadge } from '@/components/shared/BalanceBadge'

// Inside component:
const { balance: bybitBalance, source, loading, error } = useBybitBalance()
const [initialBalance, setInitialBalance] = useState<number>(10000)

// Sync default к fetched balance
useEffect(() => {
  if (!loading && bybitBalance > 0) {
    setInitialBalance(bybitBalance)
  }
}, [loading, bybitBalance])

// Render — add new field в form:
<div className={styles.field}>
  <label className={styles.fieldLabel}>Initial Balance (USDT)</label>
  <div className={styles.balanceRow}>
    <input
      type="number"
      value={initialBalance}
      onChange={(e) => setInitialBalance(Number(e.target.value))}
      step="100"
      min="100"
      className={styles.input}
    />
    <BalanceBadge source={source} balance={bybitBalance} loading={loading} error={error} />
  </div>
</div>

// In handleSubmit, include initial_balance в payload:
const payload: BacktestRequest = {
  strategy_id: strategyId,
  symbol,
  interval,
  start,
  end,
  force,
  initial_balance: initialBalance,  // S48 T22
}
```

- [ ] **Step 2: Add CSS для balance row**

```css
.balanceRow {
  display: flex;
  align-items: center;
  gap: 8px;
}
```

- [ ] **Step 3: Update BacktestRequest type**

`types.ts`:
```typescript
export interface BacktestRequest {
  strategy_id: string;
  symbol: string;
  interval: string;
  start: string;
  end: string;
  force: boolean;
  initial_balance?: number;  // S48 T22 — Bybit balance OR override
}
```

- [ ] **Step 4: App.tsx pass initialBalance к EquityChart**

```tsx
const [initialBalance, setInitialBalance] = useState<number>(10000)

// onResult callback (от ConfigureBacktest), capture initialBalance from request
const handleResult = (response: BacktestResponse) => {
  setResult(response)
  // Extract initial_balance from request OR fallback
  const ib = (response.request as any).initial_balance ?? 10000
  setInitialBalance(ib)
}

// EquityChart:
<EquityChart equityCurve={result.equity_curve} syncKey="equity-dd-sync" initialBalance={initialBalance} />
```

- [ ] **Step 5: Backend POST /api/backtest accepts initial_balance**

В `app.py` (Pydantic model для BacktestPayload):

```python
class BacktestPayload(BaseModel):
    strategy_id: str
    symbol: str
    interval: str
    start: str
    end: str
    force: bool = False
    initial_balance: float = 10000.0  # S48 T22
```

(Если `BacktestPayload` model уже defines все fields — add `initial_balance`. Pass через к backtest runner функция.)

- [ ] **Step 6: Build + test clean**

```bash
cd src/dashboard_react
npm run lint && npx tsc -b && npm run build
.venv/bin/pytest tests/unit/test_dashboard_app.py -q
```

- [ ] **Step 7: Commit + SPRINT_STATE T22 done**

```bash
cd /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot
git add src/dashboard_react/src/components/forms/ConfigureBacktest.tsx \
        src/dashboard_react/src/components/forms/ConfigureBacktest.module.css \
        src/dashboard_react/src/App.tsx \
        src/dashboard_react/src/api/types.ts \
        src/dashboard/app.py
git commit -m "feat(s48): ConfigureBacktest balance integration (T22 Bug C) — useBybitBalance + BalanceBadge + initial_balance к EquityChart"
```

Update SPRINT_STATE T22 → done.

---

## Bucket E — RU language enforcement

## Task 23: Update CLAUDE.md Language rules + Bug I anti-pattern table (sonnet)

**Files:**
- Modify: `CLAUDE.md` — Language rules section + Anti-patterns

- [ ] **Step 1: Update Language rules section**

Find existing "Language rules" table в `CLAUDE.md`. Add after table:

```markdown
### Запрещённые англицизмы → русские эквиваленты (S48 Bug I)

В чате с operator (НЕ inter-agent) использовать русские слова вместо английских non-tech terms:

| ❌ Англицизм (drop) | ✓ Русский эквивалент |
|---|---|
| Bucket | Блок / Группа |
| scope | объём / охват |
| tasks | задачи |
| Recommended / Recommendation | Рекомендация |
| concern / concerns | замечание / замечания |
| split | разделение |
| diff | разница |
| review | ревью / проверка |
| feedback | обратная связь |
| backlog | бэклог (можно оставить — устоявшийся) |
| roadmap | дорожная карта / план |

**Технические термины ОСТАВИТЬ как есть:**
- ADR, PHASE, BLOCKER, WFA, DSR, MC, FSM, RAW, PASS, FAIL, verdict
- File paths (`MetricsTable.tsx`, `wfa_criterion_explanations.py`)
- Function/class names (`get_glossary`, `useStrategyContext`)
- Library names (React, Vite, pybit, FastAPI)
- Error strings exact quote
- Commit messages — English (Conventional Commits standard)
- Code blocks — English

**Anti-пример (S48 brainstorm violation 2026-05-11):**

> "В рамках S48 у нас 22 tasks across 5 buckets. Critical concerns про FailAnalysisTab broken — recommend split: S48 critical bugs + S49 polish."

**Should be:**

> "В рамках S48 у нас 22 задачи в 5 блоках. Критические замечания про сломанный FailAnalysisTab — рекомендую разделение: S48 критичные баги + S49 полировка."
```

- [ ] **Step 2: Add к Anti-patterns table в CLAUDE.md**

Find existing Anti-patterns section. Add row:

```markdown
- ❌ 🆕 (S48 Bug I 2026-05-11) **Англицизмы в чате с operator** ("Bucket", "scope", "Recommended", "concern") — нарушение Language rules CLAUDE.md section. Использовать русские эквиваленты per Запрещённые англицизмы table (CLAUDE.md). Технические термины (ADR/PHASE/file paths/function names) оставить.
```

- [ ] **Step 3: Verify CLAUDE.md syntactically valid markdown**

```bash
python3 -c "
import re
with open('CLAUDE.md') as f:
    content = f.read()
# Check no broken table syntax
for i, line in enumerate(content.split(chr(10)), 1):
    if line.startswith('|') and not (line.endswith('|') OR '---' in line):
        print(f'Line {i}: malformed table row: {line[:80]}')
print('OK')
"
```

- [ ] **Step 4: Commit + SPRINT_STATE T23 done**

```bash
git add CLAUDE.md
git commit -m "docs(s48): Bug I — RU language enforcement в operator chat (T23)

CLAUDE.md Language rules + Anti-patterns: forbidden anglicisms table.
S48 brainstorm violation as anti-example. Tech terms preserved."
```

Update SPRINT_STATE T23 → done.

---

## Bucket F — Wiki sync

## Task 24: Sprint-48 page + index + log + current-state (sonnet)

**Files:**
- Create: `llm-wiki/wiki/project/sprints/sprint-48-ui-overhaul.md`
- Modify: `llm-wiki/wiki/project/architecture/current-state.md`
- Modify: `llm-wiki/wiki/index.md`
- Append: `llm-wiki/wiki/log.md`
- Update: `llm-wiki/wiki/project/SPRINT_STATE.md` — phase=5-verify, all 24/24

- [ ] **Step 1: Create sprint-48 page**

Mirror sprint-47 structure. Frontmatter:

```yaml
---
title: "Sprint 48 — UI Overhaul (9 жалоб + Bybit balance + Glossary вкладка)"
type: sprint
tags: [sprint-48, ui-overhaul, glossary, bybit-balance, dashboard]
created: 2026-05-11
updated: 2026-05-11
status: completed
sources:
  - llm-wiki/wiki/project/decisions/0014-walk-forward-train2000-test500.md
  - llm-wiki/wiki/project/decisions/0017-review-agent-harness.md
  - llm-wiki/wiki/project/plans/2026-05-11-sprint-48-ui-overhaul.md
  - llm-wiki/wiki/project/pre-s48-backlog.md
---
```

Sections (mirror sprint-47):
- Overview — 1 paragraph (UI Overhaul + 9 жалоб + Bybit + Glossary, 24 tasks 6 buckets)
- Plan + ADR links
- Deliverables (Frontend / Backend / Tests / CI / Wiki)
- Operator-surfaced bugs (A-I с per-bug fix detail)
- Architecture binding conditions met (C1-C5)
- Tests
- Wiki updates
- Open issues для S49 (косметика + carry-overs)
- Key decisions
- Related backlinks

- [ ] **Step 2: Update current-state.md**

- Header → `post-S48`
- Sprint pages: 51 → 52
- Components count: 48 → 50 (BalanceBadge + GlossaryTab)
- Sprint history table — add S48 row

- [ ] **Step 3: Update index.md**

Add sprint-48 entry в Sprints section.

- [ ] **Step 4: Append log.md**

```markdown
## [2026-05-11] sprint-end | S48 — UI Overhaul (9 жалоб + Bybit + Glossary)

- **Сценарий:** 24 задачи 6 блоков (subdirs refactor + backend (Bybit balance + Glossary + replay equity_curve + RunRecord) + frontend bugs (A-I) + Glossary tab + Bybit integration + RU language + wiki sync)
- **Frontend:** Component subdirs refactor (tabs/charts/forms/metrics/shared/glossary) per architect C5; EquityChart 3-line tooltip + initialBalance; MetricsTable visual divider gate-blocking vs informational; FailAnalysisTab simplified к chips + Glossary links; HistoryTab accordion expand с RU summary; GlossaryTab NEW (section TOC + filter + search)
- **Backend:** account_service.py wrapper per architect C1; /api/bybit/balance + /api/glossary endpoints; replay engine equity_curve emission (Bug B fix); glossary_data.py с ~50 RU entries + STRATEGY_TO_METRICS_MAP
- **Architect bindings met:** C1 (account_service wrapper) / C2 (URL query state) / C3 (single glossary endpoint) / C4 (HistoryTab accordion single-open) / C5 (component subdirs)
- **Tests:** Vitest +N (HistoryTab + useStrategyContext + glossary) / Playwright +N (equity-chart-all-presets) / pytest +N (account_service + balance endpoint + glossary + run record + replay equity)
- **Operator UI bugs:** A tooltip + balance / B chart все стратегии / C Bybit balance / D informational distinction / E Glossary tab CORE / F chips upсилёние / G triangle remove / H expand с RU / I language enforcement
- **Canonical counts:** UI work, FSM/reason unchanged. Components +2 (BalanceBadge + GlossaryTab) / Sprint pages 51→52
- **Tag:** v0.1.0-alpha.48 (pending PHASE 6 + ship)
- **Carry к S49:** косметика (color tokens / typography / spacing / states / a11y minimum) + S47 carry-overs (Vitest #4-#5 / README npm / F8 / Item #7+#10 / MonthlyHeatmap eslint / typing) + post-S48 buffer
```

- [ ] **Step 5: Update SPRINT_STATE — phase=5-verify**

```yaml
sprint: 48
phase: 5-verify
branch: feature/sprint-48-ui-overhaul
tag: v0.1.0-alpha.48
```

Update Phase tracking table — phase 4-Execute = done. Update Текущий статус + Следующее действие.

- [ ] **Step 6: Verify wiki integrity**

```bash
ls llm-wiki/wiki/project/sprints/sprint-48*
grep "sprint-48" llm-wiki/wiki/index.md
grep "S48 " llm-wiki/wiki/log.md | tail -3
ls llm-wiki/wiki/project/sprints/ | wc -l   # expect 52
```

- [ ] **Step 7: Commit + SPRINT_STATE T24 done + phase=5-verify**

```bash
git add llm-wiki/
git commit -m "docs(s48): wiki sync — sprint-48 page + index + log + current-state (T24)"

git add llm-wiki/wiki/project/SPRINT_STATE.md
git commit -m "docs(sprint): SPRINT_STATE T24 done + phase=5-verify (S48 execution complete 24/24)"
```

---

## PHASE 5 — Verify (after T24 commit)

Run all gates parallel. ALL must GREEN before PHASE 6.

```bash
# Backend
.venv/bin/pytest tests/ -q --ignore=tests/integration 2>&1 | tail -5
.venv/bin/mypy --strict src/ 2>&1 | tail -3

# Frontend
cd src/dashboard_react
npm run lint
npx tsc -b
npm run build
npm test
npx playwright test
```

Expected:
- pytest: previous 1037+ ~10 new = ~1050 pass
- mypy: 0 issues
- Vitest: previous 23 + ~5-7 new (HistoryTab + useStrategyContext + glossary) = ~30
- Playwright: previous 4 + 2 new (equity-chart-all-presets) = 6
- lint+tsc+build: clean

Canonical counts auto-derived per S47 anti-waste fix — no manual bump needed.

## PHASE 6 — Domain reviewers (parallel dispatch)

9 reviewers per matrix at top of plan. **Critical:**
- frontend-developer (PRIMARY — 16 React tasks)
- architecture-reviewer (verify C1-C5 binding conditions met)
- security-auditor (T3+T4 Bybit balance — auth + money-adjacent surface, READ-only)
- bybit-api-reviewer (T3 account.get_wallet_balance integration)

ALL MUST verdict APPROVE / APPROVE_WITH_CONCERNS перед merge. BLOCKER → fix + re-verify before PHASE 8.

## PHASE 8 — Ship

Per `superpowers:finishing-a-development-branch`.

```bash
git push -u origin feature/sprint-48-ui-overhaul
gh pr create --title "Sprint 48: UI Overhaul (9 жалоб + Bybit balance + Glossary вкладка)" --body "..."
# Wait CI green
gh pr merge --squash --delete-branch
git checkout main && git pull
git tag -a v0.1.0-alpha.48 -m "..." <merge-sha>
git push origin v0.1.0-alpha.48
```

Post-ship: SPRINT_STATE → between-sprints, sprint=48, branch=main, tag=v0.1.0-alpha.48. Append log.md ship entry. **HARD-GATE budget:** verify SPRINT_STATE ≤ 6 KB после update; trim если approaching.

---

## Self-Review

**1. Spec coverage** — все 24 tasks per pre-s48-backlog v3 + architecture-reviewer Q1-Q5 + frontend-developer design doc covered:
- Bucket 0 (1): T1 subdirs refactor (architect C5)
- Bucket A (6): T2 replay engine equity / T3 account_service / T4 balance endpoint / T5 glossary_data / T6 glossary endpoint / T7 RunRecord verify
- Bucket B (7): T8 EquityChart tooltip / T9 chart all presets / T10 MetricsTable divider / T11 FailAnalysisTab chips / T12 ▸ remove / T13 HistoryTab accordion / T14 HistoryTab tests
- Bucket C (5): T15 GlossaryTab base / T16 filter / T17 search / T18 useStrategyContext / T19 App.tsx register
- Bucket D (3): T20 useBybitBalance / T21 BalanceBadge / T22 ConfigureBacktest integration
- Bucket E (1): T23 RU language CLAUDE.md
- Bucket F (1): T24 wiki sync

**2. Placeholder scan** — некоторые items marked implementer judgment (acceptable):
- T5 glossary_data.py — 50+ entries (показано ~30 sample, implementer expands к 50-60 production quality)
- T7 RunRecord shape — verify-and-extend-if-missing pattern
- T10 MetricsTable existing test extend (existing test file referenced)

**3. Type consistency** — `BalanceResponse` / `GlossaryEntry` / `GlossaryResponse` / `BacktestRequest.initial_balance` — все defined в T15 + T20 + T22, consumed по shared paths. `useStrategyContext` returns `{ currentStrategy, setCurrentStrategy }` consistent T18 + T22.

**4. Cross-task dependencies:**
- T1 subdirs FIRST (post-T1 paths used везде in T8+)
- T15 GlossaryTab needs T18 useStrategyContext (build break inevitable до T18 — accepted, lint defers)
- T22 ConfigureBacktest needs T20 useBybitBalance + T21 BalanceBadge — sequential
- T24 wiki sync LAST

**5. Files ≤ 50 KB rule** — this plan ~120-140 KB, exceeds budget. Per S47 plan precedent — add к banned-from-full-read list в `~/.claude/CLAUDE.md` after save. Subagent-driven-development reads per-task с offset.

---

**Plan saved.** Per repo CLAUDE.md anti-pattern + autonomous overrides — auto-invoke `superpowers:subagent-driven-development` БЕЗ asking operator (operator decision 2026-05-10).



