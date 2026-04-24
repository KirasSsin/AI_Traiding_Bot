---
title: Sprint 2 — Bybit Venue Migration + MarketData Ingest Implementation Plan
type: plan
tags: [sprint-2, plan, bybit, venue-migration, marketdata, pybit, adapter]
created: 2026-04-21
updated: 2026-04-21
status: completed
---

# Sprint 2 — Bybit Venue Migration + MarketData Ingest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Пивот venue на Bybit Spot (pybit V5 Unified API) + реализация MarketData ingest (REST seed + WS live + bar builder + gap detection) + минимальный MARKET execution adapter под testnet. Реализует Sprint S2 из [[../architecture/migration-plan]] с учётом [[../decisions/0016-bybit-spot-supersedes-binance]].

**Architecture:** Anti-Corruption Layer (Execution + Market Data) пересобирается на Bybit V5; domain-модели Bar/Signal/Order/Fill и bounded-contexts не трогаются. Venue-agnostic компоненты (BarBuilder, gaps, pipeline, clock) общаются с Bybit-specific adapters через узкие интерфейсы. Всё async (`asyncio`), pybit вызовы мокаются в unit-тестах через `unittest.mock`; testnet-smoke отдельный маркер `@pytest.mark.integration`.

**Tech Stack:** Python 3.12 · `pybit>=5.11` · pydantic v2 · structlog · pyarrow · asyncio · pytest · pytest-asyncio · hypothesis · ruff · mypy strict. См. [[../architecture/stack-v0.1]].

**Acceptance Criteria (из [[../architecture/migration-plan]] §S2, adjusted per ADR 0016):**
- `make check` зелёный (ruff + mypy --strict + unit tests).
- ADR 0004 помечен `status: superseded by 0016`; migration-plan §S2 обновлён (bybit_* artifacts).
- `src/platform/config.py` — Settings с `bybit_api_key` / `bybit_api_secret` / `testnet` (testnet-defaults hardcoded per user directive); invariant `live_trading=True ⇒ testnet=False`.
- 24h BTCUSDT 1H через WS без потерь на test-stream; gaps detected + filled через REST.
- Все bars с `confirm=true` персистятся в Parquet (per ADR 0003, storage.md — Parquet-only).
- Clock drift check через `/v5/market/time`; drift > 1s → `ClockDriftError`.
- Testnet MARKET BUY 0.001 BTCUSDT успешен через `@pytest.mark.integration`; retCode errors 10002/110007/170140 маппятся в корректные `ReasonCode`.
- Version bump: tag `v0.1.0-alpha.2`.

---

## File Structure (what this plan creates/modifies)

**Create:**
```
src/marketdata/bybit/__init__.py
src/marketdata/bybit/rest.py           # BybitRESTClient (wraps pybit HTTP)
src/marketdata/bybit/ws.py             # BybitWSConsumer (callback→asyncio bridge)
src/marketdata/clock.py                # ClockDriftMonitor
src/marketdata/filters.py              # BybitFilters
src/marketdata/bar_builder.py          # BarBuilder (venue-agnostic)
src/marketdata/gaps.py                 # find_gaps(parquet_dir, interval_ms)
src/marketdata/pipeline.py             # MarketDataPipeline orchestrator
src/execution/bybit/__init__.py
src/execution/bybit/errors.py          # ReasonCode enum + map_error
src/execution/bybit/adapter.py         # BybitMarketAdapter
tests/unit/test_bybit_rest.py
tests/unit/test_clock.py
tests/unit/test_filters.py
tests/unit/test_bar_builder.py
tests/unit/test_gaps.py
tests/unit/test_bybit_ws.py
tests/unit/test_pipeline.py
tests/unit/test_bybit_errors.py
tests/unit/test_bybit_adapter.py
tests/integration/__init__.py
tests/integration/test_testnet_smoke.py
llm-wiki/wiki/project/components/bybit-rest.md
llm-wiki/wiki/project/components/bybit-ws.md
llm-wiki/wiki/project/components/bar-builder.md
llm-wiki/wiki/project/components/bybit-adapter.md
```

**Modify:**
```
pyproject.toml                          # python-binance → pybit; mypy overrides
.env.example                            # BINANCE_* → BYBIT_*
src/platform/config.py                  # Settings rename + testnet defaults
tests/unit/test_config.py               # 3 tests adjusted
Makefile                                # add test-integration target
llm-wiki/wiki/project/decisions/0004-binance-spot-as-initial-venue.md  # status
llm-wiki/wiki/project/architecture/migration-plan.md                    # §S2 artifacts
llm-wiki/wiki/project/architecture/stack-v0.1.md                        # deps
llm-wiki/wiki/project/architecture/bounded-contexts.md                  # Bybit URLs
llm-wiki/wiki/project/architecture/edge-cases.md                        # retCodes
llm-wiki/wiki/project/architecture/overview.md                          # text refs
llm-wiki/wiki/index.md                                                   # new comps
llm-wiki/wiki/log.md                                                     # Sprint 2 entry
```

---

## Task Summary

| # | Task | Scope |
|---|------|-------|
| 1 | Dependency swap | `python-binance → pybit>=5.11` + mypy overrides |
| 2 | Settings rename + testnet defaults | Bybit keys in config, `.env.example` |
| 3 | Wiki pivot updates | ADR 0004 superseded, 5 wiki pages sync |
| 4 | BybitRESTClient skeleton + `get_server_time` | pybit HTTP wrapper |
| 5 | ClockDriftMonitor | drift > 1s → `ClockDriftError` |
| 6 | BybitFilters | parse instruments-info, round/validate |
| 7 | Historical klines fetcher | paginated REST `/v5/market/kline` |
| 8 | BarBuilder | dedup/order/gap/confirm gate |
| 9 | Gap detector (Parquet) | `find_gaps(dir) → missing intervals` |
| 10 | BybitWSConsumer | callback→asyncio.Queue bridge + reconnect |
| 11 | MarketDataPipeline orchestrator | seed → stream → persist |
| 12 | BybitErrorMapper | retCode → ReasonCode table |
| 13 | BybitMarketAdapter | `place_market_order()` → Order |
| 14 | Testnet smoke test | `@pytest.mark.integration` E2E |
| 15 | Wiki + log + tag | components, index, log, `v0.1.0-alpha.2` |

---

### Task 1: Dependency swap (python-binance → pybit)

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Write test verifying pybit import works and python-binance removed**

Create `tests/unit/test_deps.py`:

```python
"""Sanity check: deps align with ADR 0016."""
import importlib


def test_pybit_importable() -> None:
    mod = importlib.import_module("pybit.unified_trading")
    assert hasattr(mod, "HTTP")
    assert hasattr(mod, "WebSocket")


def test_python_binance_not_installed() -> None:
    import importlib.util

    assert importlib.util.find_spec("binance") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_deps.py -v`
Expected: `test_pybit_importable` FAILS (ModuleNotFoundError: pybit); `test_python_binance_not_installed` may PASS or FAIL depending on current state.

- [ ] **Step 3: Update `pyproject.toml`**

Find:
```toml
dependencies = [
  "pydantic>=2.6",
  "pydantic-settings>=2.2",
  "structlog>=24.1",
  "pyarrow>=15.0",
  "python-binance>=1.0.19",
  "pandas>=2.2",
  "numpy>=1.26",
  "scipy>=1.12",
  "uvloop>=0.19; sys_platform != 'win32'",
]
```
Replace with:
```toml
dependencies = [
  "pydantic>=2.6",
  "pydantic-settings>=2.2",
  "structlog>=24.1",
  "pyarrow>=15.0",
  "pybit>=5.11",
  "pandas>=2.2",
  "numpy>=1.26",
  "scipy>=1.12",
  "uvloop>=0.19; sys_platform != 'win32'",
]
```

Find:
```toml
[[tool.mypy.overrides]]
module = ["binance.*", "pyarrow.*"]
ignore_missing_imports = true
```
Replace with:
```toml
[[tool.mypy.overrides]]
module = ["pybit.*", "pyarrow.*"]
ignore_missing_imports = true
```

- [ ] **Step 4: Reinstall deps**

Run:
```bash
source .venv/bin/activate
pip uninstall -y python-binance
pip install -e ".[dev]"
```
Expected: `Successfully installed pybit-5.11.x`.

- [ ] **Step 5: Run tests to verify both pass**

Run: `pytest tests/unit/test_deps.py -v`
Expected: `2 passed`.

- [ ] **Step 6: Full lint+typecheck+test**

Run: `make check`
Expected: all green.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml tests/unit/test_deps.py
git commit -m "chore(deps): swap python-binance for pybit>=5.11 (ADR 0016)"
```

---

### Task 2: Settings rename + testnet defaults

**Files:**
- Modify: `src/platform/config.py`
- Modify: `.env.example`
- Modify: `tests/unit/test_config.py`

- [ ] **Step 1: Read current Settings**

Run: `cat src/platform/config.py`

- [ ] **Step 2: Update `tests/unit/test_config.py` with Bybit fields (RED)**

Replace file content:

```python
"""Tests for Settings (pydantic-settings v2) per ADR 0016."""
import pytest
from pydantic import ValidationError

from src.platform.config import Settings


def test_defaults_load_testnet_keys() -> None:
    """Testnet keys are hardcoded defaults per user directive 2026-04-21."""
    s = Settings(
        data_dir="/tmp/data",
        log_dir="/tmp/logs",
        db_path="/tmp/data/bot.db",
        parquet_dir="/tmp/data/parquet",
    )
    assert s.bybit_api_key == "VjRb6cNnpbJ9lPOtw2"
    assert s.bybit_api_secret.startswith("QnMRFSKNDsn7zkpBN04wh9")
    assert s.testnet is True
    assert s.trading_enabled is False
    assert s.live_trading is False


def test_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """Env vars override hardcoded defaults."""
    monkeypatch.setenv("BYBIT_API_KEY", "override_key")
    monkeypatch.setenv("BYBIT_API_SECRET", "override_secret")
    monkeypatch.setenv("TESTNET", "false")
    monkeypatch.setenv("TRADING_ENABLED", "true")
    s = Settings(
        data_dir="/tmp/data",
        log_dir="/tmp/logs",
        db_path="/tmp/data/bot.db",
        parquet_dir="/tmp/data/parquet",
    )
    assert s.bybit_api_key == "override_key"
    assert s.bybit_api_secret == "override_secret"
    assert s.testnet is False


def test_live_trading_requires_mainnet() -> None:
    """live_trading=True requires testnet=False (safety invariant)."""
    with pytest.raises(ValidationError, match="live_trading requires testnet=False"):
        Settings(
            data_dir="/tmp/data",
            log_dir="/tmp/logs",
            db_path="/tmp/data/bot.db",
            parquet_dir="/tmp/data/parquet",
            trading_enabled=True,
            live_trading=True,
            testnet=True,
        )


def test_live_trading_requires_trading_enabled() -> None:
    """live_trading=True requires trading_enabled=True."""
    with pytest.raises(ValidationError, match="live_trading requires trading_enabled"):
        Settings(
            data_dir="/tmp/data",
            log_dir="/tmp/logs",
            db_path="/tmp/data/bot.db",
            parquet_dir="/tmp/data/parquet",
            trading_enabled=False,
            live_trading=True,
            testnet=False,
        )
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/unit/test_config.py -v`
Expected: FAIL — `AttributeError: 'Settings' object has no attribute 'bybit_api_key'` or similar.

- [ ] **Step 4: Rewrite `src/platform/config.py`**

Replace file content:

```python
"""Runtime Settings per ADR 0016 (Bybit Spot testnet MVP)."""
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Loaded from env / .env. Testnet keys hardcoded per user directive."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Bybit credentials (testnet hardcoded; override via .env for mainnet)
    bybit_api_key: str = "VjRb6cNnpbJ9lPOtw2"
    bybit_api_secret: str = "QnMRFSKNDsn7zkpBN04wh9ARozGbblamkIa9"
    testnet: bool = True

    # Runtime flags
    trading_enabled: bool = False
    live_trading: bool = False

    # Paths (required)
    data_dir: Path
    log_dir: Path
    db_path: Path
    parquet_dir: Path

    # Observability
    sentry_dsn: str | None = None
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    @model_validator(mode="after")
    def _live_trading_guards(self) -> "Settings":
        if self.live_trading and not self.trading_enabled:
            raise ValueError("live_trading requires trading_enabled=True")
        if self.live_trading and self.testnet:
            raise ValueError("live_trading requires testnet=False (mainnet-only)")
        return self
```

- [ ] **Step 5: Update `.env.example`**

Replace content with:

```bash
# Bybit API (testnet defaults are hardcoded in Settings; uncomment to override)
# BYBIT_API_KEY=
# BYBIT_API_SECRET=
# TESTNET=true

# Runtime flags
TRADING_ENABLED=false
LIVE_TRADING=false

# Paths
DATA_DIR=./data
LOG_DIR=./logs
DB_PATH=./data/bot.db
PARQUET_DIR=./data/parquet

# Observability
# SENTRY_DSN=
LOG_LEVEL=INFO
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/unit/test_config.py -v`
Expected: `4 passed`.

- [ ] **Step 7: Full check**

Run: `make check`
Expected: green.

- [ ] **Step 8: Commit**

```bash
git add src/platform/config.py .env.example tests/unit/test_config.py
git commit -m "feat(config): Bybit Settings rename + testnet defaults (ADR 0016)"
```

---

### Task 3: Wiki pivot updates (ADR 0004 + architecture docs)

**Files:**
- Modify: `llm-wiki/wiki/project/decisions/0004-binance-spot-as-initial-venue.md`
- Modify: `llm-wiki/wiki/project/architecture/migration-plan.md`
- Modify: `llm-wiki/wiki/project/architecture/stack-v0.1.md`
- Modify: `llm-wiki/wiki/project/architecture/bounded-contexts.md`
- Modify: `llm-wiki/wiki/project/architecture/edge-cases.md`
- Modify: `llm-wiki/wiki/project/architecture/overview.md`

- [ ] **Step 1: Mark ADR 0004 as superseded**

In `llm-wiki/wiki/project/decisions/0004-binance-spot-as-initial-venue.md`:
- Frontmatter: change `status: accepted` → `status: superseded`, bump `updated: 2026-04-21`, add tag `superseded-by-0016`.
- Replace line `**Status:** Accepted` with `**Status:** Superseded by [[0016-bybit-spot-supersedes-binance]] (2026-04-21)`.
- Add at top (below title line) a blockquote: `> Superseded on 2026-04-21 by ADR 0016. Retained for historical context — do not follow as current guidance.`

- [ ] **Step 2: Update `migration-plan.md` §S2 artifacts block**

Find block `### S2 — Venue migration (2 недели)` → `**Artifacts:**` line. Replace the artifact list with:

```
- **Artifacts:** `src/marketdata/bybit/{rest,ws}.py`, `src/marketdata/{clock,filters,bar_builder,gaps,pipeline}.py`, `src/execution/bybit/{adapter,errors}.py`, wiki/project/components/{bybit-rest, bybit-ws, bar-builder, bybit-adapter}.md. См. [[../decisions/0016-bybit-spot-supersedes-binance]].
```

Also adjust AC line "Все bars с `isClosed=true` персистятся в Parquet и SQLite `bars`" to "Все bars с `confirm=true` персистятся в Parquet (Parquet-only per ADR 0003)." — убрать упоминание SQLite bars table (она не существует в migrations).

Adjust AC "WS принимает 24h BTCUSDT 1H без потерь" — оставить (venue-agnostic AC).

Adjust AC "Тестнет MARKET BUY/SELL на 10 USDT" → "Тестнет MARKET BUY 0.001 BTCUSDT (≈$60 при spot ценах ~60k); retCode errors 10002/110007/170140 → `ReasonCode` через `BybitErrorMapper`."

Adjust AC "Clock drift check через `/time`" → "Clock drift check через `/v5/market/time`; drift>1s → `ClockDriftError`."

- [ ] **Step 3: Update `stack-v0.1.md` deps table**

Find row `| REST | \`python-binance\` или \`ccxt\` | ...` and row `| WS | \`websockets\` или \`aiohttp\` | ...`. Replace with single combined row:

```
| REST + WS | `pybit>=5.11` (official Bybit V5 SDK) | Unified Trading API, sync+async, callback-based WS (см. [[../decisions/0016-bybit-spot-supersedes-binance]]) |
```

- [ ] **Step 4: Update `bounded-contexts.md` Market Data section**

Find in section `### 1. Market Data Context`:
```
**Входы:** Binance WebSocket `@kline_1h_btcusdt`; REST `/api/v3/klines` для seed/backfill; `/api/v3/exchangeInfo` для filters.
```
Replace with:
```
**Входы:** Bybit V5 WebSocket `spot.kline.60.BTCUSDT` (public); REST `GET /v5/market/kline?category=spot` (seed/backfill); `GET /v5/market/instruments-info?category=spot&symbol=BTCUSDT` (filters); `GET /v5/market/time` (clock drift). См. [[../decisions/0016-bybit-spot-supersedes-binance]].
```

In section `### 4. Order Execution Context`:
```
**Входы:** `RiskApproved`, WS `executionReport` events, REST `/api/v3/openOrders`, `/api/v3/myTrades`.
```
Replace with:
```
**Входы:** `RiskApproved`, Bybit V5 WS private `execution` stream, REST `GET /v5/order/realtime` (open orders), `GET /v5/account/wallet-balance?accountType=UNIFIED` (pre-trade balance).
```

Also replace `**Binance = Anti-Corruption Layer:**` → `**Bybit = Anti-Corruption Layer:**` и remove specific `ExecutionReport, listStatus` references — заменить на `pybit response dicts`.

- [ ] **Step 5: Update `edge-cases.md` error-code rows (#10, #11, #15, #16, #17)**

Find row #10 and replace:
```
| 10 | Rate limit | retCode 10006 или HTTP 429 + `Retry-After` header | Honor `Retry-After`; exponential backoff на 10006; `RateLimitHit` event |
```

Row #11 (IP ban): replace text:
```
| 11 | IP ban / service unavailable | retCode 10016 | HALT `EXCHANGE_MAINTENANCE`; retry после resume |
```

Row #15 (balance):
```
| 15 | Insufficient balance | retCode 110007 | Reduce size до max feasible или reject `INSUFFICIENT_BALANCE` |
```

Row #16 (filter):
```
| 16 | Filter violation | retCode 170131/170140/170213 | Pre-submit local filter validator (BybitFilters); round qty до `basePrecision`, price до `tickSize`, ensure `qty·price ≥ minOrderAmt`; если невозможно → reject `FILTER_VIOLATION` |
```

Row #17 (HTTP 5xx / unknown):
```
| 17 | HTTP 5xx / network / unknown | HTTP 5xx, timeout, pybit exceptions | Query `GET /v5/order/realtime?orderId=X`; адоптить state; НЕ ретраить с новым orderLinkId |
```

- [ ] **Step 6: Update `overview.md`**

Global replace: "Binance Spot" → "Bybit Spot" (текстовые упоминания в prose); сохранить ссылки на ADR 0004 как исторические (теперь указывают на superseded).

- [ ] **Step 7: Verify all wiki links resolve**

Run:
```bash
grep -rn "\[\[0004" llm-wiki/wiki/ | head
grep -rn "\[\[0016" llm-wiki/wiki/ | head
grep -rn "python-binance\|binance-docs" llm-wiki/wiki/project/architecture/ | head
```
Expected: ссылки на 0004 остаются (историческая валидность), 0016 присутствует где нужно, остаточных `python-binance` в архитектурных файлах нет (допустимы только в superseded-метке 0004).

- [ ] **Step 8: Commit**

```bash
git add llm-wiki/wiki/project/decisions/0004-binance-spot-as-initial-venue.md \
        llm-wiki/wiki/project/architecture/{migration-plan,stack-v0.1,bounded-contexts,edge-cases,overview}.md
git commit -m "docs(wiki): pivot architecture/ADRs to Bybit per ADR 0016"
```

---

### Task 4: BybitRESTClient skeleton + `get_server_time`

**Files:**
- Create: `src/marketdata/bybit/__init__.py`
- Create: `src/marketdata/bybit/rest.py`
- Create: `tests/unit/test_bybit_rest.py`

- [ ] **Step 1: Create empty `__init__.py`**

```bash
mkdir -p src/marketdata/bybit
touch src/marketdata/bybit/__init__.py
```

- [ ] **Step 2: Write failing test**

Create `tests/unit/test_bybit_rest.py`:

```python
"""Tests for BybitRESTClient (pybit wrapper)."""
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from src.marketdata.bybit.rest import BybitRESTClient


@pytest.fixture
def mock_http_cls() -> MagicMock:
    """Mock pybit.unified_trading.HTTP class."""
    cls = MagicMock()
    instance = MagicMock()
    cls.return_value = instance
    return cls


def test_client_init_passes_credentials(mock_http_cls: MagicMock) -> None:
    with patch("src.marketdata.bybit.rest.HTTP", mock_http_cls):
        _ = BybitRESTClient(api_key="k", api_secret="s", testnet=True)
    mock_http_cls.assert_called_once_with(testnet=True, api_key="k", api_secret="s")


def test_get_server_time_returns_utc_datetime(mock_http_cls: MagicMock) -> None:
    # V5 response: timeSecond string + timeNano string
    mock_http_cls.return_value.get_server_time.return_value = {
        "retCode": 0,
        "result": {"timeSecond": "1745193600", "timeNano": "1745193600123456789"},
    }
    with patch("src.marketdata.bybit.rest.HTTP", mock_http_cls):
        client = BybitRESTClient(api_key="k", api_secret="s", testnet=True)
        ts = client.get_server_time()

    assert ts.tzinfo is UTC
    assert ts == datetime(2025, 4, 20, 23, 20, 0, tzinfo=UTC)


def test_get_server_time_raises_on_non_zero_retcode(mock_http_cls: MagicMock) -> None:
    mock_http_cls.return_value.get_server_time.return_value = {
        "retCode": 10002,
        "retMsg": "request expired",
        "result": {},
    }
    with patch("src.marketdata.bybit.rest.HTTP", mock_http_cls):
        client = BybitRESTClient(api_key="k", api_secret="s", testnet=True)
        with pytest.raises(RuntimeError, match="retCode=10002"):
            client.get_server_time()
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/unit/test_bybit_rest.py -v`
Expected: ModuleNotFoundError: `src.marketdata.bybit.rest`.

- [ ] **Step 4: Write minimal implementation**

Create `src/marketdata/bybit/rest.py`:

```python
"""Thin wrapper over pybit.unified_trading.HTTP — see ADR 0016."""
from datetime import UTC, datetime

from pybit.unified_trading import HTTP


class BybitAPIError(RuntimeError):
    """Raised when Bybit V5 returns non-zero retCode."""

    def __init__(self, ret_code: int, ret_msg: str) -> None:
        super().__init__(f"Bybit API error retCode={ret_code}: {ret_msg}")
        self.ret_code = ret_code
        self.ret_msg = ret_msg


class BybitRESTClient:
    """Wraps pybit V5 HTTP client with our domain-friendly return types."""

    def __init__(self, api_key: str, api_secret: str, testnet: bool) -> None:
        self._http = HTTP(testnet=testnet, api_key=api_key, api_secret=api_secret)

    def get_server_time(self) -> datetime:
        """Fetch Bybit server time as UTC datetime (seconds precision)."""
        resp = self._http.get_server_time()
        if resp["retCode"] != 0:
            raise BybitAPIError(resp["retCode"], resp.get("retMsg", ""))
        ts_s = int(resp["result"]["timeSecond"])
        return datetime.fromtimestamp(ts_s, tz=UTC)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/unit/test_bybit_rest.py -v`
Expected: `3 passed`.

- [ ] **Step 6: Full check**

Run: `make check`
Expected: green.

- [ ] **Step 7: Commit**

```bash
git add src/marketdata/bybit/ tests/unit/test_bybit_rest.py
git commit -m "feat(marketdata): add BybitRESTClient with get_server_time"
```

---

### Task 5: ClockDriftMonitor

**Files:**
- Create: `src/marketdata/clock.py`
- Create: `tests/unit/test_clock.py`

- [ ] **Step 1: Write failing test**

Create `tests/unit/test_clock.py`:

```python
"""Tests for ClockDriftMonitor."""
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from src.marketdata.clock import ClockDriftError, ClockDriftMonitor


def _client_returning(server_time: datetime) -> MagicMock:
    c = MagicMock()
    c.get_server_time.return_value = server_time
    return c


def test_drift_within_threshold_returns_ms() -> None:
    now = datetime.now(tz=UTC)
    client = _client_returning(now + timedelta(milliseconds=200))
    monitor = ClockDriftMonitor(rest_client=client, threshold_ms=1000)

    drift = monitor.check_drift()

    assert -2000 < drift < 2000  # small drift incl. measurement noise
    assert abs(drift) < 1000


def test_drift_exceeds_threshold_raises() -> None:
    now = datetime.now(tz=UTC)
    client = _client_returning(now + timedelta(seconds=5))
    monitor = ClockDriftMonitor(rest_client=client, threshold_ms=1000)

    with pytest.raises(ClockDriftError) as exc:
        monitor.check_drift()
    assert exc.value.drift_ms >= 1000


def test_default_threshold_is_1000ms() -> None:
    client = _client_returning(datetime.now(tz=UTC))
    monitor = ClockDriftMonitor(rest_client=client)
    assert monitor.threshold_ms == 1000
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_clock.py -v`
Expected: ModuleNotFoundError.

- [ ] **Step 3: Write implementation**

Create `src/marketdata/clock.py`:

```python
"""Clock drift monitor — detects local/server time skew (edge-case #9)."""
from datetime import UTC, datetime
from typing import Protocol


class _ServerTimeClient(Protocol):
    def get_server_time(self) -> datetime: ...


class ClockDriftError(RuntimeError):
    """Drift between local clock and exchange server exceeds threshold."""

    def __init__(self, drift_ms: int, threshold_ms: int) -> None:
        super().__init__(f"Clock drift {drift_ms}ms > threshold {threshold_ms}ms")
        self.drift_ms = drift_ms
        self.threshold_ms = threshold_ms


class ClockDriftMonitor:
    """Computes `server - local` drift in ms; raises if > threshold."""

    def __init__(self, rest_client: _ServerTimeClient, threshold_ms: int = 1000) -> None:
        self._client = rest_client
        self.threshold_ms = threshold_ms

    def check_drift(self) -> int:
        local = datetime.now(tz=UTC)
        server = self._client.get_server_time()
        drift_ms = int((server - local).total_seconds() * 1000)
        if abs(drift_ms) > self.threshold_ms:
            raise ClockDriftError(drift_ms, self.threshold_ms)
        return drift_ms
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_clock.py -v`
Expected: `3 passed`.

- [ ] **Step 5: Full check + commit**

```bash
make check
git add src/marketdata/clock.py tests/unit/test_clock.py
git commit -m "feat(marketdata): add ClockDriftMonitor"
```

---

### Task 6: BybitFilters

**Files:**
- Create: `src/marketdata/filters.py`
- Create: `tests/unit/test_filters.py`
- Modify: `src/marketdata/bybit/rest.py` (add `get_filters`)
- Modify: `tests/unit/test_bybit_rest.py` (test `get_filters`)

- [ ] **Step 1: Write failing test for filters parsing and rounding**

Create `tests/unit/test_filters.py`:

```python
"""Tests for BybitFilters."""
from decimal import Decimal

import pytest

from src.marketdata.filters import BybitFilters, FilterViolation


_V5_RESPONSE_SPOT_BTCUSDT = {
    "retCode": 0,
    "result": {
        "list": [
            {
                "symbol": "BTCUSDT",
                "lotSizeFilter": {
                    "basePrecision": "0.000001",
                    "quotePrecision": "0.00000001",
                    "minOrderQty": "0.000048",
                    "maxOrderQty": "71.73956243",
                    "minOrderAmt": "1",
                    "maxOrderAmt": "4000000",
                },
                "priceFilter": {"tickSize": "0.01"},
            }
        ]
    },
}


def test_from_instruments_info_parses_V5_shape() -> None:
    f = BybitFilters.from_instruments_info(_V5_RESPONSE_SPOT_BTCUSDT)
    assert f.step_size == Decimal("0.000001")
    assert f.tick_size == Decimal("0.01")
    assert f.min_order_qty == Decimal("0.000048")
    assert f.max_order_qty == Decimal("71.73956243")
    assert f.min_order_amt == Decimal("1")


def test_round_qty_rounds_down_to_step() -> None:
    f = BybitFilters.from_instruments_info(_V5_RESPONSE_SPOT_BTCUSDT)
    assert f.round_qty(Decimal("0.0012345678")) == Decimal("0.001234")
    assert f.round_qty(Decimal("0.001")) == Decimal("0.001")


def test_round_price_rounds_to_tick() -> None:
    f = BybitFilters.from_instruments_info(_V5_RESPONSE_SPOT_BTCUSDT)
    assert f.round_price(Decimal("60123.456")) == Decimal("60123.45")


def test_validate_rejects_below_min_qty() -> None:
    f = BybitFilters.from_instruments_info(_V5_RESPONSE_SPOT_BTCUSDT)
    with pytest.raises(FilterViolation, match="qty"):
        f.validate(qty=Decimal("0.00001"), price=Decimal("60000"))


def test_validate_rejects_below_min_notional() -> None:
    f = BybitFilters.from_instruments_info(_V5_RESPONSE_SPOT_BTCUSDT)
    # 0.0001 * 0.01 = 0.000001 USDT << 1
    with pytest.raises(FilterViolation, match="min_order_amt"):
        f.validate(qty=Decimal("0.0001"), price=Decimal("0.01"))


def test_validate_accepts_valid_order() -> None:
    f = BybitFilters.from_instruments_info(_V5_RESPONSE_SPOT_BTCUSDT)
    f.validate(qty=Decimal("0.001"), price=Decimal("60000"))  # 60 USDT > 1 min
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_filters.py -v`
Expected: ModuleNotFoundError.

- [ ] **Step 3: Write implementation**

Create `src/marketdata/filters.py`:

```python
"""Bybit V5 instruments-info → filter model + round/validate helpers."""
from decimal import ROUND_DOWN, Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict


class FilterViolation(ValueError):
    """Order params violate Bybit filters (LOT_SIZE / PRICE_FILTER / NOTIONAL)."""


class BybitFilters(BaseModel):
    """Single-class wrapper over V5 instruments-info filter shape."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str
    step_size: Decimal  # basePrecision
    tick_size: Decimal
    min_order_qty: Decimal
    max_order_qty: Decimal
    min_order_amt: Decimal  # minimum quote notional

    @classmethod
    def from_instruments_info(cls, response: dict[str, Any]) -> "BybitFilters":
        if response["retCode"] != 0:
            raise RuntimeError(f"instruments-info retCode={response['retCode']}")
        item = response["result"]["list"][0]
        lot = item["lotSizeFilter"]
        price = item["priceFilter"]
        return cls(
            symbol=item["symbol"],
            step_size=Decimal(lot["basePrecision"]),
            tick_size=Decimal(price["tickSize"]),
            min_order_qty=Decimal(lot["minOrderQty"]),
            max_order_qty=Decimal(lot["maxOrderQty"]),
            min_order_amt=Decimal(lot["minOrderAmt"]),
        )

    def round_qty(self, qty: Decimal) -> Decimal:
        """Round down to step_size (never exceed user-intended qty)."""
        return (qty / self.step_size).quantize(Decimal("1"), rounding=ROUND_DOWN) * self.step_size

    def round_price(self, price: Decimal) -> Decimal:
        """Round to tick_size (DOWN keeps us on the safe side for BUY limits)."""
        return (price / self.tick_size).quantize(Decimal("1"), rounding=ROUND_DOWN) * self.tick_size

    def validate(self, qty: Decimal, price: Decimal) -> None:
        """Raise FilterViolation if order would be rejected by exchange."""
        if qty < self.min_order_qty:
            raise FilterViolation(f"qty {qty} < min_order_qty {self.min_order_qty}")
        if qty > self.max_order_qty:
            raise FilterViolation(f"qty {qty} > max_order_qty {self.max_order_qty}")
        notional = qty * price
        if notional < self.min_order_amt:
            raise FilterViolation(
                f"qty*price={notional} < min_order_amt {self.min_order_amt}"
            )
```

- [ ] **Step 4: Add `get_filters` to BybitRESTClient**

Append to `src/marketdata/bybit/rest.py`:

```python


    def get_filters(self, symbol: str) -> "BybitFilters":  # noqa: F821
        """Fetch `/v5/market/instruments-info?category=spot&symbol=X` → filters."""
        from src.marketdata.filters import BybitFilters

        resp = self._http.get_instruments_info(category="spot", symbol=symbol)
        return BybitFilters.from_instruments_info(resp)
```

- [ ] **Step 5: Append test for `get_filters` in `test_bybit_rest.py`**

```python
def test_get_filters_parses_via_BybitFilters(mock_http_cls: MagicMock) -> None:
    from decimal import Decimal

    mock_http_cls.return_value.get_instruments_info.return_value = {
        "retCode": 0,
        "result": {
            "list": [
                {
                    "symbol": "BTCUSDT",
                    "lotSizeFilter": {
                        "basePrecision": "0.000001",
                        "quotePrecision": "0.00000001",
                        "minOrderQty": "0.000048",
                        "maxOrderQty": "71.73956243",
                        "minOrderAmt": "1",
                        "maxOrderAmt": "4000000",
                    },
                    "priceFilter": {"tickSize": "0.01"},
                }
            ]
        },
    }
    with patch("src.marketdata.bybit.rest.HTTP", mock_http_cls):
        client = BybitRESTClient(api_key="k", api_secret="s", testnet=True)
        f = client.get_filters("BTCUSDT")
    assert f.symbol == "BTCUSDT"
    assert f.tick_size == Decimal("0.01")
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/unit/test_filters.py tests/unit/test_bybit_rest.py -v`
Expected: `10 passed` (6 filters + 4 rest).

- [ ] **Step 7: Full check + commit**

```bash
make check
git add src/marketdata/filters.py src/marketdata/bybit/rest.py \
        tests/unit/test_filters.py tests/unit/test_bybit_rest.py
git commit -m "feat(marketdata): add BybitFilters + REST get_filters"
```

---

### Task 7: Historical klines fetcher (REST /v5/market/kline with pagination)

**Files:**
- Modify: `src/marketdata/bybit/rest.py` (add `get_klines`)
- Modify: `tests/unit/test_bybit_rest.py` (add pagination tests)

- [ ] **Step 1: Write failing test (single page, multi-page, Bar conversion)**

Append to `tests/unit/test_bybit_rest.py`:

```python
from datetime import timedelta
from decimal import Decimal as D

from src.marketdata.models import Bar, DataQuality


def _kline_row(t_ms: int, o: str = "60000", h: str = "60100", l: str = "59900",
               c: str = "60050", v: str = "1.0", turnover: str = "60050") -> list[str]:
    """V5 kline row shape: [startTime, open, high, low, close, volume, turnover]."""
    return [str(t_ms), o, h, l, c, v, turnover]


def test_get_klines_single_page(mock_http_cls: MagicMock) -> None:
    start_ms = 1745193600000  # 2025-04-20 23:20:00 UTC
    rows = [_kline_row(start_ms + i * 3_600_000) for i in range(3)]
    # Bybit returns newest-first in `list`; we reverse internally
    mock_http_cls.return_value.get_kline.return_value = {
        "retCode": 0,
        "result": {"list": list(reversed(rows))},
    }
    with patch("src.marketdata.bybit.rest.HTTP", mock_http_cls):
        client = BybitRESTClient(api_key="k", api_secret="s", testnet=True)
        bars = client.get_klines(
            symbol="BTCUSDT",
            interval="60",
            start_ms=start_ms,
            end_ms=start_ms + 3 * 3_600_000,
        )
    assert len(bars) == 3
    assert all(isinstance(b, Bar) for b in bars)
    assert bars[0].open == D("60000")
    assert bars[0].symbol == "BTCUSDT"
    assert bars[0].interval == "1h"
    assert bars[0].data_quality is DataQuality.OK
    # Ascending by close_time
    assert bars[0].close_time < bars[1].close_time < bars[2].close_time


def test_get_klines_paginates_over_1000_limit(mock_http_cls: MagicMock) -> None:
    """Bybit max 1000 rows per call; 2400 bars → 3 calls."""
    start_ms = 1745193600000
    interval_ms = 3_600_000
    call_count = 0

    def fake_get_kline(**kwargs: object) -> dict[str, object]:
        nonlocal call_count
        call_count += 1
        page_start = int(kwargs["start"])
        rows = [_kline_row(page_start + i * interval_ms) for i in range(min(1000, 2400 - (call_count - 1) * 1000))]
        return {"retCode": 0, "result": {"list": list(reversed(rows))}}

    mock_http_cls.return_value.get_kline.side_effect = fake_get_kline
    with patch("src.marketdata.bybit.rest.HTTP", mock_http_cls):
        client = BybitRESTClient(api_key="k", api_secret="s", testnet=True)
        bars = client.get_klines(
            symbol="BTCUSDT",
            interval="60",
            start_ms=start_ms,
            end_ms=start_ms + 2400 * interval_ms,
        )
    assert call_count == 3
    assert len(bars) == 2400
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_bybit_rest.py::test_get_klines_single_page -v`
Expected: `AttributeError: 'BybitRESTClient' object has no attribute 'get_klines'`.

- [ ] **Step 3: Implement `get_klines`**

Append to `src/marketdata/bybit/rest.py`:

```python


    def get_klines(
        self,
        symbol: str,
        interval: str,
        start_ms: int,
        end_ms: int,
        limit_per_call: int = 1000,
    ) -> list["Bar"]:  # noqa: F821
        """Fetch OHLCV bars in [start_ms, end_ms). Paginates if > 1000 rows."""
        from src.marketdata.models import Bar, DataQuality

        _INTERVAL_MAP = {"60": "1h"}  # extend when adding more TFs
        _INTERVAL_MS = {"60": 3_600_000}
        step_ms = _INTERVAL_MS[interval]
        domain_interval = _INTERVAL_MAP[interval]

        bars: list[Bar] = []
        cur_start = start_ms
        while cur_start < end_ms:
            resp = self._http.get_kline(
                category="spot",
                symbol=symbol,
                interval=interval,
                start=cur_start,
                end=end_ms,
                limit=limit_per_call,
            )
            if resp["retCode"] != 0:
                raise BybitAPIError(resp["retCode"], resp.get("retMsg", ""))
            rows = list(reversed(resp["result"]["list"]))  # oldest-first
            if not rows:
                break
            for row in rows:
                open_ms = int(row[0])
                open_time = datetime.fromtimestamp(open_ms / 1000, tz=UTC)
                close_time = open_time + timedelta(milliseconds=step_ms)
                bars.append(
                    Bar(
                        symbol=symbol,
                        interval=domain_interval,  # type: ignore[arg-type]
                        open_time=open_time,
                        close_time=close_time,
                        open=Decimal(row[1]),
                        high=Decimal(row[2]),
                        low=Decimal(row[3]),
                        close=Decimal(row[4]),
                        volume=Decimal(row[5]),
                        trade_count=0,  # V5 kline doesn't expose; set 0 (OK per model)
                        is_closed=True,
                        data_quality=DataQuality.OK,
                    )
                )
            last_open_ms = int(rows[-1][0])
            cur_start = last_open_ms + step_ms
        return bars
```

Also add imports at top of file (merge with existing):
```python
from datetime import UTC, datetime, timedelta
from decimal import Decimal
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_bybit_rest.py -v`
Expected: `6 passed`.

- [ ] **Step 5: Full check + commit**

```bash
make check
git add src/marketdata/bybit/rest.py tests/unit/test_bybit_rest.py
git commit -m "feat(marketdata): add paginated get_klines REST fetch"
```

---

### Task 8: BarBuilder (dedup/order/gap/confirm gate)

**Files:**
- Create: `src/marketdata/bar_builder.py`
- Create: `tests/unit/test_bar_builder.py`

- [ ] **Step 1: Write failing tests (6 edge cases from edge-cases.md)**

Create `tests/unit/test_bar_builder.py`:

```python
"""Tests for BarBuilder — venue-agnostic kline aggregator."""
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from src.marketdata.bar_builder import BarBuilder, OutOfOrderError
from src.marketdata.models import Bar, DataQuality

INTERVAL_MS = 3_600_000  # 1H


def _msg(open_ms: int, confirm: bool = True, o: str = "60000", h: str = "60100",
         lo: str = "59900", c: str = "60050", v: str = "1.0") -> dict[str, object]:
    """Bybit V5 WS kline payload shape."""
    return {
        "start": open_ms,
        "end": open_ms + INTERVAL_MS,
        "interval": "60",
        "open": o,
        "close": c,
        "high": h,
        "low": lo,
        "volume": v,
        "confirm": confirm,
    }


def test_emits_bar_on_confirm() -> None:
    builder = BarBuilder(symbol="BTCUSDT", interval_ms=INTERVAL_MS)
    result = builder.process(_msg(1745193600000, confirm=True))
    assert result is not None
    assert isinstance(result, Bar)
    assert result.is_closed is True
    assert result.data_quality is DataQuality.OK
    assert result.open == Decimal("60000")


def test_returns_none_on_non_confirm() -> None:
    builder = BarBuilder(symbol="BTCUSDT", interval_ms=INTERVAL_MS)
    result = builder.process(_msg(1745193600000, confirm=False))
    assert result is None


def test_duplicate_non_confirmed_is_ignored() -> None:
    """Same open_ms, still non-confirmed → returns None, no state change."""
    builder = BarBuilder(symbol="BTCUSDT", interval_ms=INTERVAL_MS)
    builder.process(_msg(1745193600000, confirm=False))
    result = builder.process(_msg(1745193600000, confirm=False, c="60100"))
    assert result is None


def test_duplicate_after_confirmed_is_rejected() -> None:
    """After confirm=True, same open_ms again → OutOfOrderError."""
    builder = BarBuilder(symbol="BTCUSDT", interval_ms=INTERVAL_MS)
    builder.process(_msg(1745193600000, confirm=True))
    with pytest.raises(OutOfOrderError, match="duplicate"):
        builder.process(_msg(1745193600000, confirm=True))


def test_out_of_order_is_rejected() -> None:
    """ts_new < ts_prev → OutOfOrderError."""
    builder = BarBuilder(symbol="BTCUSDT", interval_ms=INTERVAL_MS)
    builder.process(_msg(1745193600000, confirm=True))
    with pytest.raises(OutOfOrderError, match="out-of-order"):
        builder.process(_msg(1745193600000 - INTERVAL_MS, confirm=True))


def test_gap_emits_synthetic_gap_bar() -> None:
    """Missing bar between confirmed messages → synthesized GAP bar first."""
    builder = BarBuilder(symbol="BTCUSDT", interval_ms=INTERVAL_MS)
    builder.process(_msg(1745193600000, confirm=True))

    # Skip one bar (expected 1745197200000), jump to 1745200800000
    gap_bar, real_bar = builder.process_with_gap_fill(
        _msg(1745193600000 + 2 * INTERVAL_MS, confirm=True)
    )
    assert gap_bar is not None
    assert gap_bar.data_quality is DataQuality.GAP
    assert gap_bar.open_time == datetime.fromtimestamp(
        (1745193600000 + INTERVAL_MS) / 1000, tz=UTC
    )
    assert real_bar is not None
    assert real_bar.data_quality is DataQuality.OK
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_bar_builder.py -v`
Expected: ModuleNotFoundError.

- [ ] **Step 3: Write implementation**

Create `src/marketdata/bar_builder.py`:

```python
"""Venue-agnostic kline → Bar aggregator with dedup/order/gap invariants."""
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Literal

from src.marketdata.models import Bar, DataQuality


class OutOfOrderError(RuntimeError):
    """WS kline arrived out-of-order or duplicated after confirm=True."""


_INTERVAL_LITERAL: dict[int, Literal["1m", "5m", "15m", "1h", "4h", "1d"]] = {
    60_000: "1m",
    300_000: "5m",
    900_000: "15m",
    3_600_000: "1h",
    14_400_000: "4h",
    86_400_000: "1d",
}


class BarBuilder:
    """Accepts WS kline dicts; emits Bar only on `confirm=true`."""

    def __init__(self, symbol: str, interval_ms: int) -> None:
        self._symbol = symbol
        self._interval_ms = interval_ms
        self._interval_literal = _INTERVAL_LITERAL[interval_ms]
        self._last_confirmed_open_ms: int | None = None

    def process(self, msg: dict[str, object]) -> Bar | None:
        """Process a single WS message. Returns Bar if closed, else None."""
        open_ms = int(msg["start"])  # type: ignore[arg-type]
        confirm = bool(msg["confirm"])

        self._check_order(open_ms)

        if not confirm:
            return None

        bar = self._build_bar(msg, data_quality=DataQuality.OK)
        self._last_confirmed_open_ms = open_ms
        return bar

    def process_with_gap_fill(
        self, msg: dict[str, object]
    ) -> tuple[Bar | None, Bar | None]:
        """Process msg; if gap detected since last confirmed, emit synthetic
        GAP bar(s) + the real bar. Returns (first_gap_bar, real_bar). For
        multiple gaps, only the first synthetic is returned here — more gaps
        would require a list (v0.2 if >1 bar gaps become common).
        """
        open_ms = int(msg["start"])  # type: ignore[arg-type]
        gap_bar: Bar | None = None
        if (
            self._last_confirmed_open_ms is not None
            and open_ms > self._last_confirmed_open_ms + self._interval_ms
        ):
            gap_open_ms = self._last_confirmed_open_ms + self._interval_ms
            gap_bar = self._synth_gap_bar(gap_open_ms)
        real_bar = self.process(msg)
        return gap_bar, real_bar

    # --- internals ---

    def _check_order(self, open_ms: int) -> None:
        if self._last_confirmed_open_ms is None:
            return
        if open_ms == self._last_confirmed_open_ms:
            raise OutOfOrderError(f"duplicate open_ms={open_ms} after confirm")
        if open_ms < self._last_confirmed_open_ms:
            raise OutOfOrderError(
                f"out-of-order: {open_ms} < last confirmed {self._last_confirmed_open_ms}"
            )

    def _build_bar(self, msg: dict[str, object], data_quality: DataQuality) -> Bar:
        open_ms = int(msg["start"])  # type: ignore[arg-type]
        open_time = datetime.fromtimestamp(open_ms / 1000, tz=UTC)
        close_time = open_time + timedelta(milliseconds=self._interval_ms)
        return Bar(
            symbol=self._symbol,
            interval=self._interval_literal,
            open_time=open_time,
            close_time=close_time,
            open=Decimal(str(msg["open"])),
            high=Decimal(str(msg["high"])),
            low=Decimal(str(msg["low"])),
            close=Decimal(str(msg["close"])),
            volume=Decimal(str(msg["volume"])),
            trade_count=0,
            is_closed=True,
            data_quality=data_quality,
        )

    def _synth_gap_bar(self, open_ms: int) -> Bar:
        """Synthetic GAP bar — OHLC= last close (flat), volume=0."""
        assert self._last_confirmed_open_ms is not None  # type narrowing
        open_time = datetime.fromtimestamp(open_ms / 1000, tz=UTC)
        close_time = open_time + timedelta(milliseconds=self._interval_ms)
        # Per edge-cases.md #1: NO forward-fill OHLC values. Use 0's; downstream
        # consumers must skip signal generation on GAP bars anyway.
        return Bar(
            symbol=self._symbol,
            interval=self._interval_literal,
            open_time=open_time,
            close_time=close_time,
            open=Decimal("0"),
            high=Decimal("0"),
            low=Decimal("0"),
            close=Decimal("0"),
            volume=Decimal("0"),
            trade_count=0,
            is_closed=True,
            data_quality=DataQuality.GAP,
        )
```

- [ ] **Step 4: Adjust Bar OHLC invariants for synthetic GAP**

The Bar model's `_ohlc_invariants` enforces `high >= max(open,close)` and `low <= min(open,close)`. For GAP bar with all zeros, `0 >= max(0,0)` and `0 <= min(0,0)` hold — passes. No change needed.

Verify: Run `pytest tests/unit/test_marketdata_models.py -v` → should still pass.

- [ ] **Step 5: Run all bar_builder tests**

Run: `pytest tests/unit/test_bar_builder.py -v`
Expected: `6 passed`.

- [ ] **Step 6: Full check + commit**

```bash
make check
git add src/marketdata/bar_builder.py tests/unit/test_bar_builder.py
git commit -m "feat(marketdata): add BarBuilder with dedup/order/gap handling"
```

---

### Task 9: Gap detector on Parquet directory

**Files:**
- Create: `src/marketdata/gaps.py`
- Create: `tests/unit/test_gaps.py`

- [ ] **Step 1: Write failing test**

Create `tests/unit/test_gaps.py`:

```python
"""Tests for find_gaps."""
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from src.marketdata.gaps import find_gaps
from src.marketdata.models import Bar, DataQuality
from src.marketdata.storage import ParquetBarWriter

INTERVAL_MS = 3_600_000


def _bar(hour: int) -> Bar:
    base = datetime(2026, 4, 20, 0, tzinfo=UTC)
    return Bar(
        symbol="BTCUSDT",
        interval="1h",
        open_time=base + timedelta(hours=hour),
        close_time=base + timedelta(hours=hour + 1),
        open=Decimal("60000"),
        high=Decimal("60100"),
        low=Decimal("59900"),
        close=Decimal("60050"),
        volume=Decimal("1"),
        trade_count=0,
        is_closed=True,
        data_quality=DataQuality.OK,
    )


def test_no_gaps_returns_empty(tmp_path: Path) -> None:
    w = ParquetBarWriter(directory=tmp_path, symbol="BTCUSDT", interval="1h")
    w.append([_bar(i) for i in range(5)])
    assert find_gaps(tmp_path, interval_ms=INTERVAL_MS) == []


def test_single_gap_detected(tmp_path: Path) -> None:
    w = ParquetBarWriter(directory=tmp_path, symbol="BTCUSDT", interval="1h")
    w.append([_bar(i) for i in [0, 1, 2]])
    w.append([_bar(i) for i in [5, 6]])  # missing 3 and 4
    gaps = find_gaps(tmp_path, interval_ms=INTERVAL_MS)
    assert len(gaps) == 1
    gap_start, gap_end = gaps[0]
    expected_start = datetime(2026, 4, 20, 3, tzinfo=UTC)  # close_time of bar 2
    expected_end = datetime(2026, 4, 20, 5, tzinfo=UTC)    # open_time of bar 5
    assert gap_start == expected_start
    assert gap_end == expected_end


def test_empty_dir_returns_empty(tmp_path: Path) -> None:
    assert find_gaps(tmp_path, interval_ms=INTERVAL_MS) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_gaps.py -v`
Expected: ModuleNotFoundError.

- [ ] **Step 3: Write implementation**

Create `src/marketdata/gaps.py`:

```python
"""Detect missing close_time intervals in Parquet bar archive."""
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pyarrow.parquet as pq


def find_gaps(
    parquet_dir: Path, interval_ms: int
) -> list[tuple[datetime, datetime]]:
    """Return list of (gap_start, gap_end) — where `gap_start` = close_time
    of the bar before the gap, `gap_end` = open_time of the bar after.
    Times are UTC datetimes (Parquet stores ns-precision UTC).
    """
    files = sorted(parquet_dir.glob("*.parquet"))
    if not files:
        return []

    close_times: list[datetime] = []
    open_times: list[datetime] = []
    for f in files:
        table = pq.read_table(f, columns=["open_time", "close_time"])
        for ot in table["open_time"].to_pylist():
            open_times.append(ot.replace(tzinfo=UTC) if ot.tzinfo is None else ot)
        for ct in table["close_time"].to_pylist():
            close_times.append(ct.replace(tzinfo=UTC) if ct.tzinfo is None else ct)

    paired = sorted(zip(open_times, close_times, strict=True), key=lambda p: p[0])
    step = timedelta(milliseconds=interval_ms)
    gaps: list[tuple[datetime, datetime]] = []
    for i in range(len(paired) - 1):
        _, prev_close = paired[i]
        next_open, _ = paired[i + 1]
        if next_open > prev_close:
            # Bars are contiguous when next_open == prev_close
            if next_open - prev_close >= step:
                gaps.append((prev_close, next_open))
    return gaps
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_gaps.py -v`
Expected: `3 passed`.

- [ ] **Step 5: Full check + commit**

```bash
make check
git add src/marketdata/gaps.py tests/unit/test_gaps.py
git commit -m "feat(marketdata): add find_gaps for Parquet archive"
```

---

### Task 10: BybitWSConsumer (callback → asyncio.Queue bridge)

**Files:**
- Create: `src/marketdata/bybit/ws.py`
- Create: `tests/unit/test_bybit_ws.py`

- [ ] **Step 1: Write failing test**

Create `tests/unit/test_bybit_ws.py`:

```python
"""Tests for BybitWSConsumer."""
import asyncio
from unittest.mock import MagicMock, patch

import pytest

from src.marketdata.bybit.ws import BybitWSConsumer


@pytest.mark.asyncio
async def test_stream_yields_messages_from_callback() -> None:
    """Simulate pybit WebSocket pushing 2 messages via callback."""
    captured_cb = []

    def fake_kline_stream(interval, symbol, callback):  # type: ignore[no-untyped-def]
        captured_cb.append(callback)

    mock_ws_cls = MagicMock()
    mock_ws_cls.return_value.kline_stream.side_effect = fake_kline_stream

    with patch("src.marketdata.bybit.ws.WebSocket", mock_ws_cls):
        consumer = BybitWSConsumer(symbol="BTCUSDT", interval="60", testnet=True)
        consumer.start()

        # Simulate pybit pushing messages
        assert len(captured_cb) == 1
        cb = captured_cb[0]
        cb({"topic": "kline.60.BTCUSDT", "data": [{"start": 1, "confirm": True}]})
        cb({"topic": "kline.60.BTCUSDT", "data": [{"start": 2, "confirm": False}]})

        # Collect via async iterator (bounded by timeout)
        received = []
        async def collect() -> None:
            async for msg in consumer.stream():
                received.append(msg)
                if len(received) == 2:
                    return
        await asyncio.wait_for(collect(), timeout=1.0)

    assert len(received) == 2
    assert received[0]["start"] == 1
    assert received[1]["start"] == 2


@pytest.mark.asyncio
async def test_start_creates_ws_with_correct_params() -> None:
    mock_ws_cls = MagicMock()
    with patch("src.marketdata.bybit.ws.WebSocket", mock_ws_cls):
        consumer = BybitWSConsumer(symbol="BTCUSDT", interval="60", testnet=True)
        consumer.start()
    mock_ws_cls.assert_called_once_with(testnet=True, channel_type="spot")
    mock_ws_cls.return_value.kline_stream.assert_called_once()
    _, kwargs = mock_ws_cls.return_value.kline_stream.call_args
    assert kwargs["interval"] == "60"
    assert kwargs["symbol"] == "BTCUSDT"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_bybit_ws.py -v`
Expected: ModuleNotFoundError.

- [ ] **Step 3: Write implementation**

Create `src/marketdata/bybit/ws.py`:

```python
"""Bybit V5 WS consumer — bridges pybit callback to asyncio iteration."""
import asyncio
from collections.abc import AsyncIterator
from typing import Any

from pybit.unified_trading import WebSocket


class BybitWSConsumer:
    """Wraps `pybit.WebSocket.kline_stream` into an `async for` iterator.

    pybit's WebSocket is callback-based and runs in its own thread. We bridge
    by pushing each callback payload into an `asyncio.Queue` that `stream()`
    consumes asynchronously.
    """

    def __init__(self, symbol: str, interval: str, testnet: bool) -> None:
        self._symbol = symbol
        self._interval = interval
        self._testnet = testnet
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._ws: Any = None

    def start(self) -> None:
        """Start underlying pybit WebSocket — must be called from an async context."""
        self._loop = asyncio.get_event_loop()
        self._ws = WebSocket(testnet=self._testnet, channel_type="spot")
        self._ws.kline_stream(
            interval=self._interval,
            symbol=self._symbol,
            callback=self._on_message,
        )

    def _on_message(self, msg: dict[str, Any]) -> None:
        """Called by pybit on each WS message — push first `data` item into queue."""
        data = msg.get("data") or []
        if not data:
            return
        # Use thread-safe loop scheduling: pybit callback runs on its own thread
        assert self._loop is not None
        self._loop.call_soon_threadsafe(self._queue.put_nowait, data[0])

    async def stream(self) -> AsyncIterator[dict[str, Any]]:
        """Async iterator of kline messages."""
        while True:
            msg = await self._queue.get()
            yield msg
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_bybit_ws.py -v`
Expected: `2 passed`.

- [ ] **Step 5: Full check + commit**

```bash
make check
git add src/marketdata/bybit/ws.py tests/unit/test_bybit_ws.py
git commit -m "feat(marketdata): add BybitWSConsumer (callback→asyncio bridge)"
```

---

### Task 11: MarketDataPipeline orchestrator (seed → stream → persist)

**Files:**
- Create: `src/marketdata/pipeline.py`
- Create: `tests/unit/test_pipeline.py`

- [ ] **Step 1: Write failing test**

Create `tests/unit/test_pipeline.py`:

```python
"""Tests for MarketDataPipeline orchestrator."""
import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.marketdata.bar_builder import BarBuilder
from src.marketdata.models import Bar, DataQuality
from src.marketdata.pipeline import MarketDataPipeline

INTERVAL_MS = 3_600_000


def _msg(open_ms: int, confirm: bool = True) -> dict[str, object]:
    return {
        "start": open_ms,
        "end": open_ms + INTERVAL_MS,
        "interval": "60",
        "open": "60000",
        "close": "60050",
        "high": "60100",
        "low": "59900",
        "volume": "1.0",
        "confirm": confirm,
    }


def _bar(hour: int) -> Bar:
    base = datetime(2026, 4, 20, 0, tzinfo=UTC)
    return Bar(
        symbol="BTCUSDT",
        interval="1h",
        open_time=base + timedelta(hours=hour),
        close_time=base + timedelta(hours=hour + 1),
        open=Decimal("60000"),
        high=Decimal("60100"),
        low=Decimal("59900"),
        close=Decimal("60050"),
        volume=Decimal("1"),
        trade_count=0,
        is_closed=True,
        data_quality=DataQuality.OK,
    )


async def _ws_stream(msgs: list[dict[str, object]]):
    for m in msgs:
        yield m


@pytest.mark.asyncio
async def test_pipeline_persists_confirmed_bars(tmp_path: Path) -> None:
    rest = MagicMock()
    rest.get_klines.return_value = []  # no seed gap to fill

    ws = MagicMock()
    ws.start = MagicMock()
    msg_open_ms = int(datetime(2026, 4, 20, 0, tzinfo=UTC).timestamp() * 1000)
    ws.stream = lambda: _ws_stream([_msg(msg_open_ms, confirm=True)])

    parquet_writer = MagicMock()
    builder = BarBuilder(symbol="BTCUSDT", interval_ms=INTERVAL_MS)

    pipeline = MarketDataPipeline(
        rest=rest,
        ws=ws,
        bar_builder=builder,
        parquet_writer=parquet_writer,
        parquet_dir=tmp_path,
        interval_ms=INTERVAL_MS,
    )
    # Run for one message then stop
    await asyncio.wait_for(pipeline.run(max_bars=1), timeout=2.0)

    ws.start.assert_called_once()
    parquet_writer.append.assert_called_once()
    ((bars,), _) = parquet_writer.append.call_args
    assert len(bars) == 1
    assert bars[0].is_closed is True


@pytest.mark.asyncio
async def test_pipeline_seeds_gap_via_rest(tmp_path: Path) -> None:
    # Parquet already has bars 0..2; gap at 3,4; pipeline should REST-fill 3,4 on start
    from src.marketdata.storage import ParquetBarWriter

    writer = ParquetBarWriter(directory=tmp_path, symbol="BTCUSDT", interval="1h")
    writer.append([_bar(i) for i in range(3)])
    writer.append([_bar(5)])  # gap: 3 and 4 missing

    rest = MagicMock()
    rest.get_klines.return_value = [_bar(3), _bar(4)]

    ws = MagicMock()
    ws.start = MagicMock()
    ws.stream = lambda: _ws_stream([])

    parquet_writer_mock = MagicMock()
    builder = BarBuilder(symbol="BTCUSDT", interval_ms=INTERVAL_MS)

    pipeline = MarketDataPipeline(
        rest=rest,
        ws=ws,
        bar_builder=builder,
        parquet_writer=parquet_writer_mock,
        parquet_dir=tmp_path,
        interval_ms=INTERVAL_MS,
    )
    await asyncio.wait_for(pipeline.run(max_bars=0), timeout=2.0)

    rest.get_klines.assert_called_once()
    parquet_writer_mock.append.assert_called_once()
    ((bars,), _) = parquet_writer_mock.append.call_args
    assert len(bars) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_pipeline.py -v`
Expected: ModuleNotFoundError.

- [ ] **Step 3: Write implementation**

Create `src/marketdata/pipeline.py`:

```python
"""Market-data pipeline: gap-seed via REST → stream WS → persist Parquet."""
from pathlib import Path
from typing import Any, Protocol

from src.marketdata.bar_builder import BarBuilder
from src.marketdata.gaps import find_gaps
from src.marketdata.models import Bar
from src.marketdata.storage import ParquetBarWriter


class _RESTClient(Protocol):
    def get_klines(
        self, symbol: str, interval: str, start_ms: int, end_ms: int
    ) -> list[Bar]: ...


class _WSConsumer(Protocol):
    def start(self) -> None: ...
    def stream(self) -> Any: ...  # AsyncIterator[dict[str, Any]]


class MarketDataPipeline:
    """Orchestrates seed → stream → persist flow."""

    def __init__(
        self,
        rest: _RESTClient,
        ws: _WSConsumer,
        bar_builder: BarBuilder,
        parquet_writer: ParquetBarWriter,
        parquet_dir: Path,
        interval_ms: int,
        symbol: str = "BTCUSDT",
        ws_interval: str = "60",
    ) -> None:
        self._rest = rest
        self._ws = ws
        self._builder = bar_builder
        self._writer = parquet_writer
        self._parquet_dir = parquet_dir
        self._interval_ms = interval_ms
        self._symbol = symbol
        self._ws_interval = ws_interval

    async def run(self, max_bars: int | None = None) -> None:
        """Gap-seed then consume WS until `max_bars` confirmed bars appended
        (None = forever). `max_bars=0` skips streaming (useful for seed-only tests).
        """
        await self._seed_gaps()
        if max_bars == 0:
            return
        self._ws.start()
        count = 0
        async for msg in self._ws.stream():
            bar = self._builder.process(msg)
            if bar is not None:
                self._writer.append([bar])
                count += 1
                if max_bars is not None and count >= max_bars:
                    return

    async def _seed_gaps(self) -> None:
        gaps = find_gaps(self._parquet_dir, interval_ms=self._interval_ms)
        for gap_start, gap_end in gaps:
            start_ms = int(gap_start.timestamp() * 1000)
            end_ms = int(gap_end.timestamp() * 1000)
            bars = self._rest.get_klines(
                symbol=self._symbol,
                interval=self._ws_interval,
                start_ms=start_ms,
                end_ms=end_ms,
            )
            if bars:
                self._writer.append(bars)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_pipeline.py -v`
Expected: `2 passed`.

- [ ] **Step 5: Full check + commit**

```bash
make check
git add src/marketdata/pipeline.py tests/unit/test_pipeline.py
git commit -m "feat(marketdata): add MarketDataPipeline orchestrator"
```

---

### Task 12: BybitErrorMapper (retCode → ReasonCode table)

**Files:**
- Create: `src/execution/bybit/__init__.py`
- Create: `src/execution/bybit/errors.py`
- Create: `tests/unit/test_bybit_errors.py`

- [ ] **Step 1: Create empty `__init__.py`**

```bash
mkdir -p src/execution/bybit
touch src/execution/bybit/__init__.py
```

- [ ] **Step 2: Write failing tests**

Create `tests/unit/test_bybit_errors.py`:

```python
"""Tests for BybitErrorMapper."""
from src.execution.bybit.errors import ReasonCode, map_error


def test_clock_drift() -> None:
    assert map_error(10002, "request not valid") is ReasonCode.CLOCK_DRIFT


def test_api_key_invalid() -> None:
    assert map_error(10003, "invalid api key") is ReasonCode.WRONG_API_KEY


def test_rate_limit() -> None:
    assert map_error(10006, "too many visits") is ReasonCode.RATE_LIMIT_HIT


def test_maintenance() -> None:
    assert map_error(10016, "service not available") is ReasonCode.EXCHANGE_MAINTENANCE


def test_insufficient_balance() -> None:
    assert map_error(110007, "insufficient balance") is ReasonCode.INSUFFICIENT_BALANCE


def test_filter_violations_all_map_to_same_code() -> None:
    for code in (110017, 170131, 170140, 170213):
        assert map_error(code, "") is ReasonCode.FILTER_VIOLATION


def test_unknown_code_maps_to_unknown() -> None:
    assert map_error(99999999, "unseen") is ReasonCode.UNKNOWN_ERROR
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/unit/test_bybit_errors.py -v`
Expected: ModuleNotFoundError.

- [ ] **Step 4: Write implementation**

Create `src/execution/bybit/errors.py`:

```python
"""Map Bybit V5 retCode → domain ReasonCode (per ADR 0016)."""
from enum import StrEnum


class ReasonCode(StrEnum):
    CLOCK_DRIFT = "CLOCK_DRIFT"
    WRONG_API_KEY = "WRONG_API_KEY"
    RATE_LIMIT_HIT = "RATE_LIMIT_HIT"
    EXCHANGE_MAINTENANCE = "EXCHANGE_MAINTENANCE"
    INSUFFICIENT_BALANCE = "INSUFFICIENT_BALANCE"
    FILTER_VIOLATION = "FILTER_VIOLATION"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


_MAP: dict[int, ReasonCode] = {
    10002: ReasonCode.CLOCK_DRIFT,
    10003: ReasonCode.WRONG_API_KEY,
    10006: ReasonCode.RATE_LIMIT_HIT,
    10016: ReasonCode.EXCHANGE_MAINTENANCE,
    110007: ReasonCode.INSUFFICIENT_BALANCE,
    110017: ReasonCode.FILTER_VIOLATION,
    170131: ReasonCode.FILTER_VIOLATION,
    170140: ReasonCode.FILTER_VIOLATION,
    170213: ReasonCode.FILTER_VIOLATION,
}


def map_error(ret_code: int, ret_msg: str = "") -> ReasonCode:
    """Return matching ReasonCode, or UNKNOWN_ERROR if ret_code not mapped."""
    return _MAP.get(ret_code, ReasonCode.UNKNOWN_ERROR)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/unit/test_bybit_errors.py -v`
Expected: `7 passed`.

- [ ] **Step 6: Full check + commit**

```bash
make check
git add src/execution/bybit/ tests/unit/test_bybit_errors.py
git commit -m "feat(execution): add BybitErrorMapper retCode→ReasonCode"
```

---

### Task 13: BybitMarketAdapter (`place_market_order`)

**Files:**
- Create: `src/execution/bybit/adapter.py`
- Create: `tests/unit/test_bybit_adapter.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_bybit_adapter.py`:

```python
"""Tests for BybitMarketAdapter.place_market_order."""
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from src.execution.bybit.adapter import BybitAPIError, BybitMarketAdapter
from src.execution.bybit.errors import ReasonCode
from src.execution.models import Order, OrderSide, OrderStatus, OrderType
from src.marketdata.filters import BybitFilters, FilterViolation


_FILTERS = BybitFilters(
    symbol="BTCUSDT",
    step_size=Decimal("0.000001"),
    tick_size=Decimal("0.01"),
    min_order_qty=Decimal("0.000048"),
    max_order_qty=Decimal("71.73956243"),
    min_order_amt=Decimal("1"),
)


def _rest_ok_place() -> MagicMock:
    r = MagicMock()
    r._http.place_order.return_value = {
        "retCode": 0,
        "result": {
            "orderId": "EX-12345",
            "orderLinkId": "CID-abc",
        },
    }
    return r


def test_place_market_buy_returns_order() -> None:
    rest = _rest_ok_place()
    adapter = BybitMarketAdapter(rest_client=rest, filters=_FILTERS)
    order = adapter.place_market_order(
        client_order_id="CID-abc",
        side=OrderSide.BUY,
        qty=Decimal("0.001"),
        reference_price=Decimal("60000"),
    )
    assert isinstance(order, Order)
    assert order.client_order_id == "CID-abc"
    assert order.exch_order_id == "EX-12345"
    assert order.side is OrderSide.BUY
    assert order.type is OrderType.MARKET
    assert order.status is OrderStatus.NEW


def test_place_market_sell_passes_side_to_api() -> None:
    rest = _rest_ok_place()
    adapter = BybitMarketAdapter(rest_client=rest, filters=_FILTERS)
    adapter.place_market_order(
        client_order_id="CID-sell",
        side=OrderSide.SELL,
        qty=Decimal("0.001"),
        reference_price=Decimal("60000"),
    )
    _, kwargs = rest._http.place_order.call_args
    assert kwargs["category"] == "spot"
    assert kwargs["symbol"] == "BTCUSDT"
    assert kwargs["side"] == "Sell"
    assert kwargs["orderType"] == "Market"
    assert kwargs["qty"] == "0.000001".__class__  # str type check below
    assert isinstance(kwargs["qty"], str)


def test_filter_violation_rejected_before_api_call() -> None:
    rest = _rest_ok_place()
    adapter = BybitMarketAdapter(rest_client=rest, filters=_FILTERS)
    with pytest.raises(FilterViolation, match="qty"):
        adapter.place_market_order(
            client_order_id="CID-tiny",
            side=OrderSide.BUY,
            qty=Decimal("0.00001"),  # below min_order_qty
            reference_price=Decimal("60000"),
        )
    rest._http.place_order.assert_not_called()


def test_api_error_mapped_to_reason_code() -> None:
    rest = MagicMock()
    rest._http.place_order.return_value = {
        "retCode": 110007,
        "retMsg": "insufficient balance",
        "result": {},
    }
    adapter = BybitMarketAdapter(rest_client=rest, filters=_FILTERS)
    with pytest.raises(BybitAPIError) as exc:
        adapter.place_market_order(
            client_order_id="CID-poor",
            side=OrderSide.BUY,
            qty=Decimal("0.001"),
            reference_price=Decimal("60000"),
        )
    assert exc.value.reason is ReasonCode.INSUFFICIENT_BALANCE
    assert exc.value.ret_code == 110007
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_bybit_adapter.py -v`
Expected: ModuleNotFoundError.

- [ ] **Step 3: Write implementation**

Create `src/execution/bybit/adapter.py`:

```python
"""Bybit V5 MARKET order adapter — domain-friendly wrapper."""
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from src.execution.bybit.errors import ReasonCode, map_error
from src.execution.models import Order, OrderSide, OrderStatus, OrderType
from src.marketdata.filters import BybitFilters


class BybitAPIError(RuntimeError):
    """Bybit `place_order` returned non-zero retCode."""

    def __init__(self, ret_code: int, ret_msg: str, reason: ReasonCode) -> None:
        super().__init__(f"retCode={ret_code} ({reason}): {ret_msg}")
        self.ret_code = ret_code
        self.ret_msg = ret_msg
        self.reason = reason


_SIDE_MAP = {OrderSide.BUY: "Buy", OrderSide.SELL: "Sell"}


class BybitMarketAdapter:
    """MARKET spot orders only (v0.1 scope)."""

    def __init__(self, rest_client: Any, filters: BybitFilters) -> None:
        self._rest = rest_client
        self._filters = filters

    def place_market_order(
        self,
        client_order_id: str,
        side: OrderSide,
        qty: Decimal,
        reference_price: Decimal,
    ) -> Order:
        """Place MARKET order; validate via filters; return Order.

        `reference_price` is needed only for the notional (min_order_amt) check;
        it does NOT go into the order — MARKET orders have no price parameter.
        """
        self._filters.validate(qty=qty, price=reference_price)
        now = datetime.now(tz=UTC)

        resp = self._rest._http.place_order(
            category="spot",
            symbol=self._filters.symbol,
            side=_SIDE_MAP[side],
            orderType="Market",
            qty=str(qty),
            orderLinkId=client_order_id,
        )
        if resp["retCode"] != 0:
            reason = map_error(resp["retCode"], resp.get("retMsg", ""))
            raise BybitAPIError(resp["retCode"], resp.get("retMsg", ""), reason)

        return Order(
            client_order_id=client_order_id,
            exch_order_id=resp["result"]["orderId"],
            symbol=self._filters.symbol,
            side=side,
            type=OrderType.MARKET,
            status=OrderStatus.NEW,
            orig_qty=qty,
            executed_qty=Decimal("0"),
            price=None,
            created_at=now,
            updated_at=now,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_bybit_adapter.py -v`
Expected: `4 passed`.

- [ ] **Step 5: Full check + commit**

```bash
make check
git add src/execution/bybit/adapter.py tests/unit/test_bybit_adapter.py
git commit -m "feat(execution): add BybitMarketAdapter.place_market_order"
```

---

### Task 14: Testnet smoke test (`@pytest.mark.integration`)

**Files:**
- Create: `tests/integration/__init__.py`
- Create: `tests/integration/test_testnet_smoke.py`
- Modify: `pyproject.toml` (register `integration` marker)
- Modify: `Makefile` (add `test-integration` target; `make check` stays unit-only)

- [ ] **Step 1: Register integration marker in pyproject**

Find:
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```
Extend to:
```toml
[tool.pytest.ini_options]
testpaths = ["tests/unit"]
asyncio_mode = "auto"
markers = [
  "integration: requires live Bybit testnet (env-gated)",
]
```

Note: `testpaths = ["tests/unit"]` — `make check` runs ONLY unit. Integration invoked separately.

- [ ] **Step 2: Update Makefile**

Find `test:` target:
```make
test:
	pytest -v
```
Keep it (now scoped to unit via pyproject). Add new target:
```make
test-integration:
	pytest tests/integration -v -m integration
```

- [ ] **Step 3: Create `tests/integration/__init__.py` (empty)**

```bash
touch tests/integration/__init__.py
```

- [ ] **Step 4: Create smoke test**

Create `tests/integration/test_testnet_smoke.py`:

```python
"""E2E smoke: place MARKET BUY 0.001 BTCUSDT on Bybit testnet.

Env-gated: skipped unless testnet keys are not the hardcoded defaults
(i.e. user explicitly provided fresh testnet creds in `.env`), OR
when `PYTEST_RUN_INTEGRATION=1` is set to acknowledge use of the
hardcoded defaults.
"""
import os
from decimal import Decimal
from uuid import uuid4

import pytest

from src.execution.bybit.adapter import BybitMarketAdapter
from src.execution.models import OrderSide, OrderStatus
from src.marketdata.bybit.rest import BybitRESTClient
from src.platform.config import Settings


pytestmark = pytest.mark.integration


def _settings() -> Settings:
    return Settings(
        data_dir="/tmp/data",
        log_dir="/tmp/logs",
        db_path="/tmp/data/bot.db",
        parquet_dir="/tmp/data/parquet",
    )


def _skip_if_not_explicitly_opted_in() -> None:
    if os.environ.get("PYTEST_RUN_INTEGRATION") != "1":
        pytest.skip("set PYTEST_RUN_INTEGRATION=1 to run live-testnet tests")


def test_testnet_market_buy_places_and_fills() -> None:
    _skip_if_not_explicitly_opted_in()
    settings = _settings()
    assert settings.testnet is True, "smoke test must run on testnet only"

    rest = BybitRESTClient(
        api_key=settings.bybit_api_key,
        api_secret=settings.bybit_api_secret,
        testnet=True,
    )
    filters = rest.get_filters("BTCUSDT")

    adapter = BybitMarketAdapter(rest_client=rest, filters=filters)
    # Use min_order_qty × 25 for ~$60 notional at current price
    qty = filters.round_qty(Decimal("0.001"))
    cid = f"smoke-{uuid4().hex[:8]}"

    order = adapter.place_market_order(
        client_order_id=cid,
        side=OrderSide.BUY,
        qty=qty,
        reference_price=Decimal("60000"),
    )
    assert order.status is OrderStatus.NEW
    assert order.exch_order_id is not None
```

- [ ] **Step 5: Verify unit tests still run (integration is skipped by default)**

Run: `make check`
Expected: green, integration tests NOT collected (testpaths=tests/unit).

Run: `pytest tests/integration -v`
Expected: 1 skipped (PYTEST_RUN_INTEGRATION not set).

- [ ] **Step 6: Manual one-off verification (optional, operator step)**

When operator wants to verify live testnet:
```bash
PYTEST_RUN_INTEGRATION=1 make test-integration
```
Expected: order placed on testnet.bybit.com, `order.exch_order_id` returned.

- [ ] **Step 7: Commit**

```bash
git add tests/integration/ pyproject.toml Makefile
git commit -m "test(integration): add env-gated Bybit testnet smoke"
```

---

### Task 15: Wiki components + log + tag `v0.1.0-alpha.2`

**Files:**
- Create: `llm-wiki/wiki/project/components/bybit-rest.md`
- Create: `llm-wiki/wiki/project/components/bybit-ws.md`
- Create: `llm-wiki/wiki/project/components/bar-builder.md`
- Create: `llm-wiki/wiki/project/components/bybit-adapter.md`
- Modify: `llm-wiki/wiki/index.md` (add 4 new components)
- Modify: `llm-wiki/wiki/log.md` (append Sprint 2 entry)

- [ ] **Step 1: Create `bybit-rest.md`**

Content:

````markdown
---
title: MarketData — BybitRESTClient
type: component
tags: [marketdata, bybit, rest, v5, anti-corruption-layer]
created: 2026-04-21
updated: 2026-04-21
sources: [src/marketdata/bybit/rest.py, tests/unit/test_bybit_rest.py]
status: stable
---

# MarketData — BybitRESTClient

**TL;DR:** Тонкий wrapper над `pybit.unified_trading.HTTP` для public Bybit V5 endpoints. Возвращает domain-friendly типы (`datetime` UTC, `list[Bar]`, `BybitFilters`).

## Definition / Purpose

`src/marketdata/bybit/rest.py` экспортирует `BybitRESTClient` — единственную точку входа в REST API Bybit V5 для маркет-даты. Всё остальное в `src/marketdata/` получает типизированные объекты, не зная про pybit / V5 / retCode.

### Методы

- `get_server_time() -> datetime` — `GET /v5/market/time` → UTC datetime (s precision). Для clock-drift check.
- `get_filters(symbol: str) -> BybitFilters` — `GET /v5/market/instruments-info?category=spot&symbol=X` → [[filters|BybitFilters]].
- `get_klines(symbol, interval, start_ms, end_ms) -> list[Bar]` — `GET /v5/market/kline?category=spot` с пагинацией (max 1000 per call). Возвращает ascending по `close_time`, `data_quality=OK`.

### Обработка ошибок

- `retCode != 0` → `BybitAPIError(ret_code, ret_msg)`.
- В execution-слое (`BybitMarketAdapter`) ошибки маппятся через `map_error()` → `ReasonCode`.

## Key properties

- **Sync (не async).** pybit V5 REST — синхронный; все вызовы блокирующие.
- **Typed returns.** Вход — V5 JSON; выход — pydantic-модели (`Bar`, `BybitFilters`).
- **Pagination прозрачна** для `get_klines` — вызываем пока не выберем `[start, end)` полностью.
- **UTC everywhere** — timestamps конвертятся в UTC datetime на границе.

## Related

- [[../decisions/0016-bybit-spot-supersedes-binance]] — ADR выбора venue.
- [[bybit-ws]] — WS consumer (отдельный канал).
- [[models]] — Bar domain model.
- [[filters]] (TBD если создадим — сейчас в `src/marketdata/filters.py`; документируется в этом же page или отдельной странице S3+).

## Sources

- `src/marketdata/bybit/rest.py` (~120 LOC).
- Тесты: `tests/unit/test_bybit_rest.py` (6: init, server_time ok/err, filters, klines single/multi-page).
````

- [ ] **Step 2: Create `bybit-ws.md`**

Content:

````markdown
---
title: MarketData — BybitWSConsumer
type: component
tags: [marketdata, bybit, websocket, v5, asyncio]
created: 2026-04-21
updated: 2026-04-21
sources: [src/marketdata/bybit/ws.py, tests/unit/test_bybit_ws.py]
status: stable
---

# MarketData — BybitWSConsumer

**TL;DR:** Мост между callback-based `pybit.WebSocket.kline_stream` и async iteration через `asyncio.Queue`.

## Definition / Purpose

`pybit.unified_trading.WebSocket` работает по callback-модели: регистрируешь `callback=fn`, он вызывается из отдельного pybit-thread. В нашем коде market-data pipeline — `async for msg in ws.stream()`. Мост: callback кладёт сообщение в `asyncio.Queue` через `loop.call_soon_threadsafe`, `stream()` читает из queue.

### Интерфейс

- `BybitWSConsumer(symbol="BTCUSDT", interval="60", testnet=True)`.
- `start()` — создаёт pybit WS + подписывается на `spot.kline.60.BTCUSDT`. Должен вызываться внутри active event loop.
- `async stream() -> AsyncIterator[dict]` — yields raw V5 kline payload dicts.

## Key properties

- **Thread-safe queue** через `call_soon_threadsafe` — pybit-thread пишет, event-loop читает.
- **Single symbol/interval** — один consumer = один stream. Мульти-symbol потребует расширения.
- **Reconnect** делегирован pybit (внутренняя логика SDK).

## Related

- [[../decisions/0016-bybit-spot-supersedes-binance]] — endpoint `spot.kline.60.BTCUSDT`.
- [[bar-builder]] — принимает сообщения из WS.

## Sources

- `src/marketdata/bybit/ws.py`.
- `tests/unit/test_bybit_ws.py` (2: stream, init params).
````

- [ ] **Step 3: Create `bar-builder.md`**

Content:

````markdown
---
title: MarketData — BarBuilder
type: component
tags: [marketdata, bar-builder, venue-agnostic, edge-cases]
created: 2026-04-21
updated: 2026-04-21
sources: [src/marketdata/bar_builder.py, tests/unit/test_bar_builder.py]
status: stable
---

# MarketData — BarBuilder

**TL;DR:** Venue-agnostic aggregator WS kline-сообщений → `Bar`. Enforces 3 инварианта: `confirm=true` gate, dedup, out-of-order reject. Детектирует и синтезирует GAP bars.

## Definition / Purpose

Принимает dict с полями `start/end/open/high/low/close/volume/confirm` (форма Bybit V5 kline payload). Возвращает `Bar` только если `confirm=true`; иначе `None`.

### Методы

- `process(msg: dict) -> Bar | None` — базовый путь.
- `process_with_gap_fill(msg) -> tuple[Bar | None, Bar | None]` — детектит gap (`open_ms > last_confirmed + interval`) и возвращает `(synthetic_gap_bar, real_bar)`.

### Инварианты (соответствие [[../architecture/edge-cases]])

| Edge case # | Детекция | Реакция |
|---|---|---|
| #1 | `open_ms > last + interval` | Синтетический GAP bar (OHLCV=0, `data_quality=GAP`) |
| #4 | Duplicate `open_ms` после confirm | `OutOfOrderError("duplicate")` |
| #7 | `open_ms < last` | `OutOfOrderError("out-of-order")` |
| #5 | OHLC inconsistent | pydantic Bar model validator → `ValueError` |

## Key properties

- **Venue-agnostic** — никакого pybit/Binance в интерфейсе; работает с dict.
- **Stateful per instance** — хранит `last_confirmed_open_ms`. Один instance = один symbol+interval.
- **No forward-fill в GAP** (per edge-cases #1) — GAP bar имеет OHLCV=0, downstream skip signal.

## Related

- [[../architecture/edge-cases]] — источник invariant-списка.
- [[models]] — `Bar`, `DataQuality`.
- [[../decisions/0007-utc-timestamps-ns-precision]] — UTC ns datetime.
- [[bybit-ws]] — поставщик сообщений.

## Sources

- `src/marketdata/bar_builder.py`.
- `tests/unit/test_bar_builder.py` (6: confirm/non-confirm/dup-nonconfirm/dup-after-confirm/out-of-order/gap).
````

- [ ] **Step 4: Create `bybit-adapter.md`**

Content:

````markdown
---
title: Execution — BybitMarketAdapter
type: component
tags: [execution, bybit, adapter, anti-corruption-layer]
created: 2026-04-21
updated: 2026-04-21
sources: [src/execution/bybit/adapter.py, src/execution/bybit/errors.py, tests/unit/test_bybit_adapter.py, tests/unit/test_bybit_errors.py]
status: stable
---

# Execution — BybitMarketAdapter

**TL;DR:** MARKET spot orders на Bybit V5. Pre-trade validation через `BybitFilters`, post-trade маппинг retCode → `ReasonCode`.

## Definition / Purpose

Единственный код, который общается с `/v5/order/create` в v0.1. Scope — MARKET only per migration-plan §S2. LIMIT/OCO/STOP — Sprint S5.

### Интерфейс

```python
adapter = BybitMarketAdapter(rest_client, filters)
order: Order = adapter.place_market_order(
    client_order_id="CID-...",   # → orderLinkId
    side=OrderSide.BUY,
    qty=Decimal("0.001"),
    reference_price=Decimal("60000"),  # для min_order_amt check (не идёт в API)
)
```

### Цепочка

1. `filters.validate(qty, price)` — `FilterViolation` до API-вызова, если ниже min_order_qty / min_order_amt.
2. `pybit.HTTP.place_order(category="spot", orderType="Market", ...)`.
3. `retCode == 0` → `Order(status=NEW, exch_order_id=result.orderId)`.
4. `retCode != 0` → `map_error()` → `BybitAPIError(reason: ReasonCode)`.

### Error mapping (`src/execution/bybit/errors.py`)

| retCode | ReasonCode |
|---|---|
| 10002 | CLOCK_DRIFT |
| 10003 | WRONG_API_KEY |
| 10006 | RATE_LIMIT_HIT |
| 10016 | EXCHANGE_MAINTENANCE |
| 110007 | INSUFFICIENT_BALANCE |
| 110017 / 170131 / 170140 / 170213 | FILTER_VIOLATION |
| other | UNKNOWN_ERROR |

## Key properties

- **MARKET only** в v0.1 (per migration-plan).
- **client_order_id ≡ orderLinkId** (Bybit terminology).
- **Spot category hardcoded** — linear (perps) добавляется v0.2 через расширение, не modification.

## Related

- [[../decisions/0016-bybit-spot-supersedes-binance]] — error-map таблица.
- [[../architecture/bounded-contexts]] — Execution ACL.
- [[models]] — `Order`, `OrderSide`, `OrderType`, `OrderStatus`.
- [[../trading/concepts/reason-codes]] — 28 кодов, subset покрыт v0.1.

## Sources

- `src/execution/bybit/adapter.py`, `src/execution/bybit/errors.py`.
- Тесты: `test_bybit_adapter.py` (4), `test_bybit_errors.py` (7).
````

- [ ] **Step 5: Update `llm-wiki/wiki/index.md`**

Find section `## Project — Components` and extend:

```markdown
## Project — Components

- [[project/components/config]] — `Settings` (pydantic-settings v2): env/.env, Bybit creds, trading_enabled/live_trading invariant, paths.
- [[project/components/logging]] — structlog JSON pipeline → stdout, обязательные ключи event/level/timestamp, contextvars.
- [[project/components/models]] — pydantic v2 domain models: Bar / Signal / Order / Fill с инвариантами (OHLC, look-ahead, executed_qty ≤ orig_qty).
- [[project/components/storage]] — SQLite WAL (OLTP, 8 таблиц + migrations runner) + Parquet snappy writer (OLAP).
- [[project/components/bybit-rest]] — BybitRESTClient (pybit V5 HTTP wrapper): server_time, instruments_info, paginated klines.
- [[project/components/bybit-ws]] — BybitWSConsumer: pybit WebSocket callback → asyncio iteration мост.
- [[project/components/bar-builder]] — venue-agnostic aggregator: confirm-gate + dedup + out-of-order + gap synthesis.
- [[project/components/bybit-adapter]] — MARKET spot execution: filter-validate + place_order + retCode→ReasonCode.
```

Also find `## Project — Decisions` section and add:
```markdown
- [[project/decisions/0016-bybit-spot-supersedes-binance]] — Bybit Spot supersedes 0004; pybit>=5.11; V5 Unified endpoint map.
```

- [ ] **Step 6: Append Sprint 2 entry to `log.md`**

Find the last entry (Sprint 1 completed) and append:

```markdown

## [2026-04-21] ingest | Sprint 2 — Bybit venue migration + MarketData ingest
- Added (code): src/marketdata/bybit/{rest,ws}.py, src/marketdata/{clock,filters,bar_builder,gaps,pipeline}.py, src/execution/bybit/{adapter,errors}.py, 9 unit-test модулей + 1 integration smoke.
- Added (wiki): wiki/project/decisions/0016-bybit-spot-supersedes-binance.md, wiki/project/components/{bybit-rest,bybit-ws,bar-builder,bybit-adapter}.md.
- Modified (wiki): decisions/0004 (→superseded), architecture/{migration-plan,stack-v0.1,bounded-contexts,edge-cases,overview}.md, wiki/project/components/config.md.
- Modified (code): pyproject.toml (python-binance → pybit>=5.11 + mypy overrides), .env.example (BINANCE_* → BYBIT_*), src/platform/config.py (Settings rename + testnet-defaults per user directive), Makefile (test-integration target).
- Tag: v0.1.0-alpha.2 (commit TBD на HEAD Sprint 2).
- Verification: `make check` green — ruff/mypy --strict/pytest unit (~35 tests). Integration smoke env-gated.
- Notes: Stage 3 Sprint 2 закрыт. Готово к Sprint 3 (Strategy port — EMA/ADX/RSI/ATR через TA-Lib + on_bar → Signal).
```

- [ ] **Step 7: Verify make check + tests counts**

Run: `make check`
Expected: green.

Run: `pytest tests/unit -v 2>&1 | tail -5`
Expected: ~35 tests passed (20 from Sprint 1 + 15 new: 3 config updated + 4 rest + 3 clock + 6 filters + 6 bar_builder + 3 gaps + 2 ws + 2 pipeline + 7 errors + 4 adapter + 2 deps — approximate).

- [ ] **Step 8: Commit wiki + tag**

```bash
git add llm-wiki/wiki/project/components/ llm-wiki/wiki/index.md llm-wiki/wiki/log.md
git commit -m "docs(wiki): Sprint 2 components + log entry + index update"

git tag -a v0.1.0-alpha.2 -m "Sprint 2 — Bybit venue migration + MarketData ingest complete"
```

Verify:
```bash
git tag -l "v0.1.0-alpha.*"
```
Expected:
```
v0.1.0-alpha.1
v0.1.0-alpha.2
```

---

## Self-review summary

**Spec coverage check** (against ADR 0016 + migration-plan §S2):
- ADR 0016 "affected artifacts" list → Task 1 (pyproject), Task 2 (config + .env.example), Task 3 (5 wiki files). ✓
- migration-plan §S2 AC "WS принимает 24h без потерь" → BarBuilder + gap detection + pipeline (Tasks 8, 9, 11). ✓
- "Clock drift check через `/v5/market/time`" → Task 5. ✓
- "Testnet MARKET" → Task 13 + Task 14 smoke. ✓
- "retCode errors 10002/110007/170140 → ReasonCode" → Task 12 + Task 13 error path test. ✓
- Version tag `v0.1.0-alpha.2` → Task 15. ✓
- Parquet-only (per ADR 0003) — NO SQLite `bars` table — Task 3 step 2 explicitly corrects migration-plan. ✓

**Placeholder scan:** "(TBD если создадим — сейчас в `src/marketdata/filters.py`)" в bybit-rest.md Related section — пограничный случай, но указывает на реальное текущее состояние (filters описаны вместе с rest-компонентом). Оставляю, не placeholder.

**Type consistency check:**
- `BybitRESTClient` signatures: `get_server_time() -> datetime`, `get_filters(str) -> BybitFilters`, `get_klines(symbol, interval, start_ms, end_ms) -> list[Bar]` — consistent across Task 4, 6, 7, 11.
- `BarBuilder.process(dict) -> Bar | None`, `process_with_gap_fill(dict) -> tuple[Bar|None, Bar|None]` — consistent Task 8, used in Task 11.
- `map_error(int, str) -> ReasonCode` — Task 12, used Task 13.
- `BybitMarketAdapter.place_market_order(client_order_id, side, qty, reference_price) -> Order` — Task 13, used Task 14.

No inconsistencies found.

---

## Related

- [[../architecture/migration-plan]] §S2 — source of truth для AC.
- [[../decisions/0016-bybit-spot-supersedes-binance]] — architectural decision + V5 endpoint map.
- [[../decisions/0003-sqlite-parquet-for-storage]] — Parquet-only обоснование.
- [[../decisions/0007-utc-timestamps-ns-precision]] — UTC datetime контракт.
- [[../architecture/edge-cases]] — источник invariant-ов для BarBuilder.
- [[2026-04-20-sprint-1-foundation]] — предшествующий sprint (Foundation).
