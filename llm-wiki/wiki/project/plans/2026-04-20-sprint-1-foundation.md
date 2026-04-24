---
title: Sprint 1 — Foundation Implementation Plan
type: plan
tags: [sprint-1, plan, foundation, ddd, storage, models, platform]
created: 2026-04-20
updated: 2026-04-20
status: completed
---

# Sprint 1 — Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Заложить persistent layer (SQLite WAL + Parquet snappy), pydantic v2 domain-модели, platform-каркас (config/logging/db), и вычистить legacy (ml/, gateway/, hmm_regime, order_flow). Sprint 1 из [[../architecture/migration-plan]].

**Architecture:** Новые DDD каталоги (`marketdata/ signalgen/ risk/ execution/ analytics/ platform/`) создаются параллельно существующим; legacy-код переезжает в branch `legacy/phase1-bybit` и удаляется из main через `git rm` атомарным коммитом. Весь новый код — pydantic v2 + type-strict + TDD.

**Tech Stack:** Python 3.12 · pydantic v2 · pydantic-settings · structlog · sqlite3 (stdlib) · pyarrow · pytest · hypothesis · ruff · mypy strict. (См. [[../architecture/stack-v0.1]].)

**Acceptance Criteria (из migration-plan §S1):**
- `make test` зелёный; `ruff check` + `mypy --strict src/` без ошибок.
- `python -m src.platform.db init` создаёт все 8 таблиц из [[../architecture/storage]].
- pydantic-модели валидируют OHLC (high≥max(open,close), low≤min(open,close), volume≥0).
- Branch `legacy/phase1-bybit` pushed; main очищен от `src/ml/`, `src/gateway/`, `src/strategy/hmm_regime.py`, `src/strategy/order_flow.py`, `src/data/orderbook.py`.

---

### Task 1: Legacy branch freeze

**Files:**
- No file changes; git operations only.

- [ ] **Step 1: Create legacy branch from current HEAD**

Run:
```bash
git checkout -b legacy/phase1-bybit
git push -u origin legacy/phase1-bybit
```
Expected: branch `legacy/phase1-bybit` на origin.

- [ ] **Step 2: Return to main**

Run:
```bash
git checkout main
git pull --ff-only
```

- [ ] **Step 3: Verify legacy accessible**

Run: `git log legacy/phase1-bybit --oneline -5`
Expected: видны 5 последних коммитов.

---

### Task 2: Dev tooling (pyproject.toml, ruff, mypy, pytest)

**Files:**
- Create: `pyproject.toml`
- Create: `.pre-commit-config.yaml`
- Create: `.env.example`
- Modify: `.gitignore`

- [ ] **Step 1: Create `pyproject.toml`**

Content:
```toml
[project]
name = "ai-trading-bot"
version = "0.1.0-alpha.1"
description = "Binance Spot BTC/USDT 1H trading bot (MVP v0.1)"
requires-python = ">=3.12"
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

[project.optional-dependencies]
dev = [
  "pytest>=8.0",
  "pytest-asyncio>=0.23",
  "hypothesis>=6.98",
  "ruff>=0.3",
  "mypy>=1.9",
  "pre-commit>=3.6",
  "types-pyyaml",
]

[tool.ruff]
line-length = 100
target-version = "py312"
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "B", "SIM", "ARG", "RET"]
ignore = ["E501"]  # handled by formatter

[tool.mypy]
python_version = "3.12"
strict = true
packages = ["src"]
plugins = ["pydantic.mypy"]

[[tool.mypy.overrides]]
module = ["binance.*", "pyarrow.*"]
ignore_missing_imports = true

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

- [ ] **Step 2: Create `.pre-commit-config.yaml`**

Content:
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.3.0
    hooks:
      - id: ruff
      - id: ruff-format
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.9.0
    hooks:
      - id: mypy
        args: [--strict, src/]
        additional_dependencies: [pydantic, pydantic-settings]
```

- [ ] **Step 3: Create `.env.example`**

Content:
```
# Binance (testnet для S2-S9, mainnet только в S10)
BINANCE_API_KEY=
BINANCE_API_SECRET=
BINANCE_ENV=testnet

# Runtime flags
TRADING_ENABLED=false
LIVE_TRADING=false

# Paths (relative to repo root)
DATA_DIR=./data
LOG_DIR=./logs
DB_PATH=./data/oltp.db
PARQUET_DIR=./data/parquet

# Observability (optional)
SENTRY_DSN=
LOG_LEVEL=INFO
```

- [ ] **Step 4: Append to `.gitignore`**

Append:
```
# Sprint 1 additions
.env
data/
logs/
.mypy_cache/
.pytest_cache/
.ruff_cache/
__pycache__/
*.egg-info/
.venv/
```

- [ ] **Step 5: Install dev deps + verify**

Run:
```bash
pip install -e ".[dev]"
ruff --version && mypy --version && pytest --version
```
Expected: все три команды печатают версии без ошибок.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml .pre-commit-config.yaml .env.example .gitignore
git commit -m "chore(tooling): add pyproject.toml, pre-commit, .env.example for v0.1"
```

---

### Task 3: DDD skeleton directories

**Files:**
- Create: `src/marketdata/__init__.py`
- Create: `src/signalgen/__init__.py`
- Create: `src/risk/__init__.py` (exists, verify empty)
- Create: `src/execution/__init__.py` (exists, verify empty)
- Create: `src/analytics/__init__.py`
- Create: `src/platform/__init__.py`
- Create: `tests/unit/__init__.py`
- Create: `tests/integration/__init__.py`
- Create: `tests/property/__init__.py`

- [ ] **Step 1: Create all new package dirs + empty `__init__.py`**

Run:
```bash
mkdir -p src/marketdata src/signalgen src/analytics src/platform
mkdir -p tests/unit tests/integration tests/property
touch src/marketdata/__init__.py src/signalgen/__init__.py src/analytics/__init__.py src/platform/__init__.py
touch tests/unit/__init__.py tests/integration/__init__.py tests/property/__init__.py
```

- [ ] **Step 2: Verify structure**

Run: `find src tests -maxdepth 2 -name "__init__.py" | sort`
Expected: перечислены все 7 новых `__init__.py`.

- [ ] **Step 3: Commit**

```bash
git add src/marketdata src/signalgen src/analytics src/platform tests/unit tests/integration tests/property
git commit -m "feat(scaffold): add DDD package skeleton (marketdata/signalgen/analytics/platform)"
```

---

### Task 4: Platform — Settings (pydantic-settings)

**Files:**
- Create: `src/platform/config.py`
- Create: `tests/unit/test_config.py`

- [ ] **Step 1: Write the failing test**

File `tests/unit/test_config.py`:
```python
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.platform.config import Settings


def test_settings_loads_from_env(monkeypatch, tmp_path):
    monkeypatch.setenv("BINANCE_API_KEY", "test-key")
    monkeypatch.setenv("BINANCE_API_SECRET", "test-secret")
    monkeypatch.setenv("BINANCE_ENV", "testnet")
    monkeypatch.setenv("TRADING_ENABLED", "false")
    monkeypatch.setenv("LIVE_TRADING", "false")
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "data" / "oltp.db"))
    monkeypatch.setenv("PARQUET_DIR", str(tmp_path / "data" / "parquet"))

    s = Settings()

    assert s.binance_api_key == "test-key"
    assert s.binance_env == "testnet"
    assert s.trading_enabled is False
    assert s.live_trading is False
    assert isinstance(s.data_dir, Path)


def test_settings_invalid_env_rejected(monkeypatch, tmp_path):
    monkeypatch.setenv("BINANCE_API_KEY", "k")
    monkeypatch.setenv("BINANCE_API_SECRET", "s")
    monkeypatch.setenv("BINANCE_ENV", "invalid")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("LOG_DIR", str(tmp_path))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "db"))
    monkeypatch.setenv("PARQUET_DIR", str(tmp_path))

    with pytest.raises(ValidationError):
        Settings()


def test_live_trading_requires_trading_enabled(monkeypatch, tmp_path):
    monkeypatch.setenv("BINANCE_API_KEY", "k")
    monkeypatch.setenv("BINANCE_API_SECRET", "s")
    monkeypatch.setenv("BINANCE_ENV", "testnet")
    monkeypatch.setenv("TRADING_ENABLED", "false")
    monkeypatch.setenv("LIVE_TRADING", "true")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("LOG_DIR", str(tmp_path))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "db"))
    monkeypatch.setenv("PARQUET_DIR", str(tmp_path))

    with pytest.raises(ValidationError, match="live_trading"):
        Settings()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_config.py -v`
Expected: FAIL (`ModuleNotFoundError: src.platform.config`).

- [ ] **Step 3: Implement `src/platform/config.py`**

```python
"""Application settings loaded from environment / .env."""
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime-configuration. Все значения из env или .env файла."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # Binance
    binance_api_key: str = Field(..., min_length=1)
    binance_api_secret: str = Field(..., min_length=1)
    binance_env: Literal["testnet", "mainnet"] = "testnet"

    # Runtime flags
    trading_enabled: bool = False
    live_trading: bool = False

    # Paths
    data_dir: Path
    log_dir: Path
    db_path: Path
    parquet_dir: Path

    # Observability
    sentry_dsn: str | None = None
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    @model_validator(mode="after")
    def _live_requires_trading(self) -> "Settings":
        if self.live_trading and not self.trading_enabled:
            raise ValueError("live_trading=true requires trading_enabled=true")
        return self
```

- [ ] **Step 4: Run tests — expect pass**

Run: `pytest tests/unit/test_config.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add src/platform/config.py tests/unit/test_config.py
git commit -m "feat(platform): add Settings with pydantic-settings + env validation"
```

---

### Task 5: Platform — structlog JSON logging

**Files:**
- Create: `src/platform/logging.py`
- Create: `tests/unit/test_logging.py`

- [ ] **Step 1: Write the failing test**

File `tests/unit/test_logging.py`:
```python
import json
import logging

from src.platform.logging import configure_logging, get_logger


def test_logger_emits_json_with_required_keys(caplog):
    configure_logging(level="INFO")
    log = get_logger("test")

    with caplog.at_level(logging.INFO):
        log.info("boot", component="platform", version="0.1.0-alpha.1")

    assert caplog.records, "expected at least one log record"
    record = caplog.records[-1]
    payload = json.loads(record.getMessage())
    assert payload["event"] == "boot"
    assert payload["component"] == "platform"
    assert payload["version"] == "0.1.0-alpha.1"
    assert payload["level"] == "info"
    assert "timestamp" in payload
```

- [ ] **Step 2: Run test — expect fail**

Run: `pytest tests/unit/test_logging.py -v`
Expected: FAIL (ModuleNotFoundError).

- [ ] **Step 3: Implement `src/platform/logging.py`**

```python
"""structlog configuration — JSON output to stdout + rotating file."""
import logging
import sys
from typing import Any

import structlog


def configure_logging(level: str = "INFO") -> None:
    """Configure structlog + stdlib logging. Idempotent."""
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level),
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True, key="timestamp"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> Any:
    """Return a structlog BoundLogger."""
    return structlog.get_logger(name)
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/unit/test_logging.py -v`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add src/platform/logging.py tests/unit/test_logging.py
git commit -m "feat(platform): add structlog JSON logging configuration"
```

---

### Task 6: Domain model — Bar (pydantic v2)

**Files:**
- Create: `src/marketdata/models.py`
- Create: `tests/unit/test_marketdata_models.py`

- [ ] **Step 1: Write the failing test**

File `tests/unit/test_marketdata_models.py`:
```python
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.marketdata.models import Bar, DataQuality


def _ts(iso: str) -> datetime:
    return datetime.fromisoformat(iso).replace(tzinfo=timezone.utc)


def test_bar_valid():
    bar = Bar(
        symbol="BTCUSDT",
        interval="1h",
        open_time=_ts("2026-04-20T00:00:00"),
        close_time=_ts("2026-04-20T01:00:00"),
        open=Decimal("60000"),
        high=Decimal("60500"),
        low=Decimal("59800"),
        close=Decimal("60200"),
        volume=Decimal("125.5"),
        trade_count=3421,
        is_closed=True,
        data_quality=DataQuality.OK,
    )
    assert bar.symbol == "BTCUSDT"
    assert bar.is_closed is True


def test_bar_high_must_be_max():
    with pytest.raises(ValidationError, match="high"):
        Bar(
            symbol="BTCUSDT",
            interval="1h",
            open_time=_ts("2026-04-20T00:00:00"),
            close_time=_ts("2026-04-20T01:00:00"),
            open=Decimal("60000"),
            high=Decimal("59900"),  # < open
            low=Decimal("59800"),
            close=Decimal("60200"),
            volume=Decimal("1"),
            trade_count=1,
            is_closed=True,
            data_quality=DataQuality.OK,
        )


def test_bar_low_must_be_min():
    with pytest.raises(ValidationError, match="low"):
        Bar(
            symbol="BTCUSDT",
            interval="1h",
            open_time=_ts("2026-04-20T00:00:00"),
            close_time=_ts("2026-04-20T01:00:00"),
            open=Decimal("60000"),
            high=Decimal("60500"),
            low=Decimal("60100"),  # > open
            close=Decimal("60200"),
            volume=Decimal("1"),
            trade_count=1,
            is_closed=True,
            data_quality=DataQuality.OK,
        )


def test_bar_volume_non_negative():
    with pytest.raises(ValidationError):
        Bar(
            symbol="BTCUSDT",
            interval="1h",
            open_time=_ts("2026-04-20T00:00:00"),
            close_time=_ts("2026-04-20T01:00:00"),
            open=Decimal("60000"),
            high=Decimal("60500"),
            low=Decimal("59800"),
            close=Decimal("60200"),
            volume=Decimal("-1"),
            trade_count=1,
            is_closed=True,
            data_quality=DataQuality.OK,
        )


def test_bar_close_time_after_open_time():
    with pytest.raises(ValidationError, match="close_time"):
        Bar(
            symbol="BTCUSDT",
            interval="1h",
            open_time=_ts("2026-04-20T01:00:00"),
            close_time=_ts("2026-04-20T00:00:00"),  # before open
            open=Decimal("60000"),
            high=Decimal("60500"),
            low=Decimal("59800"),
            close=Decimal("60200"),
            volume=Decimal("1"),
            trade_count=1,
            is_closed=True,
            data_quality=DataQuality.OK,
        )
```

- [ ] **Step 2: Run test — expect fail**

Run: `pytest tests/unit/test_marketdata_models.py -v`
Expected: FAIL (ModuleNotFoundError).

- [ ] **Step 3: Implement `src/marketdata/models.py`**

```python
"""Market-data domain models (pydantic v2)."""
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DataQuality(StrEnum):
    OK = "OK"
    GAP = "GAP"
    STALE = "STALE"
    SUSPECT = "SUSPECT"


class Bar(BaseModel):
    """OHLCV bar with strict validation — immutable по convention."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str = Field(..., pattern=r"^[A-Z]+USDT$")
    interval: Literal["1m", "5m", "15m", "1h", "4h", "1d"]
    open_time: datetime
    close_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal = Field(..., ge=0)
    trade_count: int = Field(..., ge=0)
    is_closed: bool
    data_quality: DataQuality = DataQuality.OK

    @model_validator(mode="after")
    def _ohlc_invariants(self) -> "Bar":
        if self.high < max(self.open, self.close):
            raise ValueError("high must be >= max(open, close)")
        if self.low > min(self.open, self.close):
            raise ValueError("low must be <= min(open, close)")
        if self.close_time <= self.open_time:
            raise ValueError("close_time must be > open_time")
        return self
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/unit/test_marketdata_models.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/marketdata/models.py tests/unit/test_marketdata_models.py
git commit -m "feat(marketdata): add Bar pydantic model with OHLC invariant validation"
```

---

### Task 7: Domain models — Signal, Order, Fill

**Files:**
- Create: `src/signalgen/models.py`
- Create: `src/execution/models.py`
- Create: `tests/unit/test_signalgen_models.py`
- Create: `tests/unit/test_execution_models.py`

- [ ] **Step 1: Write failing tests — Signal**

File `tests/unit/test_signalgen_models.py`:
```python
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.signalgen.models import Signal, SignalSide


def test_signal_valid():
    sig = Signal(
        signal_id=uuid4(),
        symbol="BTCUSDT",
        side=SignalSide.LONG,
        bar_close_time=datetime(2026, 4, 20, 1, 0, tzinfo=timezone.utc),
        generated_at=datetime(2026, 4, 20, 1, 0, 1, tzinfo=timezone.utc),
        ema_fast=Decimal("60100"),
        ema_slow=Decimal("60050"),
        adx_14=Decimal("28"),
        plus_di_14=Decimal("25"),
        minus_di_14=Decimal("15"),
        rsi_14=Decimal("55"),
        atr_14=Decimal("250"),
        reason="EMA_CROSS_UP_WITH_ADX_CONFIRM",
    )
    assert sig.side == SignalSide.LONG


def test_signal_generated_after_bar_close():
    with pytest.raises(ValidationError, match="generated_at"):
        Signal(
            signal_id=uuid4(),
            symbol="BTCUSDT",
            side=SignalSide.LONG,
            bar_close_time=datetime(2026, 4, 20, 1, 0, tzinfo=timezone.utc),
            generated_at=datetime(2026, 4, 20, 0, 59, tzinfo=timezone.utc),  # before close
            ema_fast=Decimal("60100"),
            ema_slow=Decimal("60050"),
            adx_14=Decimal("28"),
            plus_di_14=Decimal("25"),
            minus_di_14=Decimal("15"),
            rsi_14=Decimal("55"),
            atr_14=Decimal("250"),
            reason="X",
        )


def test_signal_flat_side_allowed():
    sig = Signal(
        signal_id=uuid4(),
        symbol="BTCUSDT",
        side=SignalSide.FLAT,
        bar_close_time=datetime(2026, 4, 20, 1, 0, tzinfo=timezone.utc),
        generated_at=datetime(2026, 4, 20, 1, 0, 1, tzinfo=timezone.utc),
        ema_fast=Decimal("60100"),
        ema_slow=Decimal("60050"),
        adx_14=Decimal("18"),
        plus_di_14=Decimal("20"),
        minus_di_14=Decimal("19"),
        rsi_14=Decimal("50"),
        atr_14=Decimal("250"),
        reason="NO_SIGNAL",
    )
    assert sig.side == SignalSide.FLAT
```

- [ ] **Step 2: Implement `src/signalgen/models.py`**

```python
"""Signal-generation domain models."""
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SignalSide(StrEnum):
    LONG = "LONG"
    FLAT = "FLAT"
    # SHORT не используется в v0.1 (spot only)


class Signal(BaseModel):
    """Trading signal emitted on bar close. Immutable."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    signal_id: UUID
    symbol: str = Field(..., pattern=r"^[A-Z]+USDT$")
    side: SignalSide
    bar_close_time: datetime
    generated_at: datetime

    # Indicator snapshot
    ema_fast: Decimal
    ema_slow: Decimal
    adx_14: Decimal = Field(..., ge=0, le=100)
    plus_di_14: Decimal = Field(..., ge=0, le=100)
    minus_di_14: Decimal = Field(..., ge=0, le=100)
    rsi_14: Decimal = Field(..., ge=0, le=100)
    atr_14: Decimal = Field(..., ge=0)

    reason: str = Field(..., max_length=128)

    @model_validator(mode="after")
    def _generated_after_close(self) -> "Signal":
        if self.generated_at < self.bar_close_time:
            raise ValueError(
                "generated_at must be >= bar_close_time (look-ahead invariant)"
            )
        return self
```

- [ ] **Step 3: Write failing tests — Order / Fill**

File `tests/unit/test_execution_models.py`:
```python
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.execution.models import Fill, Order, OrderSide, OrderStatus, OrderType


def test_order_valid():
    o = Order(
        client_order_id="c-abc-123",
        exch_order_id="42",
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        type=OrderType.MARKET,
        status=OrderStatus.NEW,
        orig_qty=Decimal("0.001"),
        executed_qty=Decimal("0"),
        price=None,
        created_at=datetime(2026, 4, 20, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 4, 20, 1, tzinfo=timezone.utc),
    )
    assert o.status == OrderStatus.NEW


def test_order_executed_not_exceed_orig():
    with pytest.raises(ValidationError, match="executed_qty"):
        Order(
            client_order_id="c-1",
            exch_order_id=None,
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            type=OrderType.MARKET,
            status=OrderStatus.PARTIALLY_FILLED,
            orig_qty=Decimal("0.001"),
            executed_qty=Decimal("0.002"),
            price=None,
            created_at=datetime(2026, 4, 20, 1, tzinfo=timezone.utc),
            updated_at=datetime(2026, 4, 20, 1, tzinfo=timezone.utc),
        )


def test_fill_valid():
    f = Fill(
        client_order_id="c-1",
        trade_id=100,
        qty=Decimal("0.001"),
        price=Decimal("60000"),
        fee=Decimal("0.06"),
        fee_asset="USDT",
        is_maker=False,
        filled_at=datetime(2026, 4, 20, 1, tzinfo=timezone.utc),
    )
    assert f.qty == Decimal("0.001")
```

- [ ] **Step 4: Implement `src/execution/models.py`**

```python
"""Order-execution domain models."""
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class OrderSide(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(StrEnum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_MARKET = "STOP_MARKET"
    STOP_LIMIT = "STOP_LIMIT"
    TAKE_PROFIT = "TAKE_PROFIT"


class OrderStatus(StrEnum):
    NEW = "NEW"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    EXPIRED = "EXPIRED"
    REJECTED = "REJECTED"


class Order(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_order_id: str = Field(..., min_length=1, max_length=64)
    exch_order_id: str | None
    symbol: str = Field(..., pattern=r"^[A-Z]+USDT$")
    side: OrderSide
    type: OrderType
    status: OrderStatus
    orig_qty: Decimal = Field(..., gt=0)
    executed_qty: Decimal = Field(..., ge=0)
    price: Decimal | None = None
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def _exec_not_exceeds_orig(self) -> "Order":
        if self.executed_qty > self.orig_qty:
            raise ValueError("executed_qty must be <= orig_qty")
        return self


class Fill(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    client_order_id: str = Field(..., min_length=1)
    trade_id: int = Field(..., gt=0)
    qty: Decimal = Field(..., gt=0)
    price: Decimal = Field(..., gt=0)
    fee: Decimal = Field(..., ge=0)
    fee_asset: str = Field(..., min_length=1)
    is_maker: bool
    filled_at: datetime
```

- [ ] **Step 5: Run all model tests**

Run: `pytest tests/unit/test_signalgen_models.py tests/unit/test_execution_models.py -v`
Expected: 3 + 3 = 6 passed.

- [ ] **Step 6: Commit**

```bash
git add src/signalgen/models.py src/execution/models.py tests/unit/test_signalgen_models.py tests/unit/test_execution_models.py
git commit -m "feat(domain): add Signal, Order, Fill pydantic models with invariants"
```

---

### Task 8: Platform — SQLite WAL + migrations

**Files:**
- Create: `src/platform/db.py`
- Create: `migrations/001_initial.sql`
- Create: `tests/unit/test_db.py`

- [ ] **Step 1: Write failing test**

File `tests/unit/test_db.py`:
```python
import sqlite3
from pathlib import Path

from src.platform.db import connect, init_db


def test_init_db_creates_all_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "oltp.db"
    migrations_dir = Path(__file__).parent.parent.parent / "migrations"
    init_db(db_path, migrations_dir=migrations_dir)

    conn = connect(db_path)
    try:
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = {row[0] for row in cur.fetchall()}
    finally:
        conn.close()

    expected = {
        "orders", "fills", "positions", "events",
        "runs", "config", "state", "audit_index", "schema_migrations",
    }
    assert expected <= tables, f"missing tables: {expected - tables}"


def test_wal_mode_enabled(tmp_path: Path) -> None:
    db_path = tmp_path / "oltp.db"
    migrations_dir = Path(__file__).parent.parent.parent / "migrations"
    init_db(db_path, migrations_dir=migrations_dir)

    conn = connect(db_path)
    try:
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    finally:
        conn.close()
    assert mode.lower() == "wal"


def test_init_db_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "oltp.db"
    migrations_dir = Path(__file__).parent.parent.parent / "migrations"
    init_db(db_path, migrations_dir=migrations_dir)
    init_db(db_path, migrations_dir=migrations_dir)  # second call must not fail
    conn = connect(db_path)
    try:
        applied = conn.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]
    finally:
        conn.close()
    assert applied == 1
```

- [ ] **Step 2: Run test — expect fail**

Run: `pytest tests/unit/test_db.py -v`
Expected: FAIL (ModuleNotFoundError).

- [ ] **Step 3: Create `migrations/001_initial.sql`**

File `migrations/001_initial.sql`:
```sql
-- Sprint 1 schema. Source: wiki/project/architecture/storage.md

CREATE TABLE orders (
  client_order_id TEXT PRIMARY KEY,
  exch_order_id   TEXT UNIQUE,
  symbol          TEXT NOT NULL,
  side            TEXT NOT NULL CHECK(side IN ('BUY','SELL')),
  type            TEXT NOT NULL CHECK(type IN ('MARKET','LIMIT','STOP_MARKET','STOP_LIMIT','TAKE_PROFIT')),
  status          TEXT NOT NULL CHECK(status IN ('NEW','PARTIALLY_FILLED','FILLED','CANCELED','EXPIRED','REJECTED')),
  orig_qty        REAL NOT NULL,
  executed_qty    REAL NOT NULL DEFAULT 0,
  price           REAL,
  created_at      TEXT NOT NULL,
  updated_at      TEXT NOT NULL
);

CREATE TABLE fills (
  fill_id         INTEGER PRIMARY KEY AUTOINCREMENT,
  client_order_id TEXT NOT NULL REFERENCES orders(client_order_id),
  trade_id        INTEGER NOT NULL,
  qty             REAL NOT NULL,
  price           REAL NOT NULL,
  fee             REAL NOT NULL,
  fee_asset       TEXT NOT NULL,
  is_maker        INTEGER NOT NULL,
  filled_at       TEXT NOT NULL,
  UNIQUE(trade_id)
);

CREATE TABLE positions (
  position_id     TEXT PRIMARY KEY,
  symbol          TEXT NOT NULL,
  side            TEXT NOT NULL,
  qty             REAL NOT NULL,
  avg_entry_price REAL NOT NULL,
  opened_at       TEXT NOT NULL,
  closed_at       TEXT,
  realized_pnl    REAL
);

CREATE TABLE events (
  aggregate_id    TEXT NOT NULL,
  version         INTEGER NOT NULL,
  event_type      TEXT NOT NULL,
  occurred_at     TEXT NOT NULL,
  payload_json    TEXT NOT NULL,
  PRIMARY KEY (aggregate_id, version)
);
CREATE INDEX idx_events_occurred ON events(occurred_at);

CREATE TABLE runs (
  run_id           TEXT PRIMARY KEY,
  started_at       TEXT NOT NULL,
  ended_at         TEXT,
  git_commit       TEXT NOT NULL,
  config_hash      TEXT NOT NULL,
  strategy_version TEXT NOT NULL
);

CREATE TABLE config (
  config_hash     TEXT PRIMARY KEY,
  config_json     TEXT NOT NULL,
  loaded_at       TEXT NOT NULL
);

CREATE TABLE state (
  key             TEXT PRIMARY KEY,
  value_json      TEXT NOT NULL,
  updated_at      TEXT NOT NULL
);

CREATE TABLE audit_index (
  trade_id        TEXT PRIMARY KEY,
  timestamp       TEXT NOT NULL,
  symbol          TEXT NOT NULL,
  reason_code     TEXT NOT NULL,
  file_path       TEXT NOT NULL,
  file_offset     INTEGER NOT NULL
);
CREATE INDEX idx_audit_timestamp ON audit_index(timestamp);
CREATE INDEX idx_audit_reason ON audit_index(reason_code);
```

- [ ] **Step 4: Implement `src/platform/db.py`**

```python
"""SQLite connection helpers + schema migrations."""
import sqlite3
from pathlib import Path


def connect(db_path: Path) -> sqlite3.Connection:
    """Open SQLite connection with sane defaults (WAL, foreign keys)."""
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(db_path: Path, migrations_dir: Path) -> None:
    """Apply all `.sql` migrations in lexicographic order. Idempotent."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = connect(db_path)
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations "
            "(filename TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
        )
        applied = {
            row[0]
            for row in conn.execute("SELECT filename FROM schema_migrations").fetchall()
        }
        for sql_file in sorted(migrations_dir.glob("*.sql")):
            if sql_file.name in applied:
                continue
            with sql_file.open("r", encoding="utf-8") as f:
                conn.executescript(f.read())
            conn.execute(
                "INSERT INTO schema_migrations (filename, applied_at) "
                "VALUES (?, datetime('now'))",
                (sql_file.name,),
            )
            conn.commit()
    finally:
        conn.close()
```

- [ ] **Step 5: Run tests — expect pass**

Run: `pytest tests/unit/test_db.py -v`
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add src/platform/db.py migrations/001_initial.sql tests/unit/test_db.py
git commit -m "feat(platform): add SQLite WAL connection + migration runner with initial schema"
```

---

### Task 9: MarketData — Parquet writer

**Files:**
- Create: `src/marketdata/storage.py`
- Create: `tests/unit/test_parquet_storage.py`

- [ ] **Step 1: Write failing test**

File `tests/unit/test_parquet_storage.py`:
```python
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pyarrow.parquet as pq

from src.marketdata.models import Bar, DataQuality
from src.marketdata.storage import ParquetBarWriter


def _bar(i: int) -> Bar:
    base = datetime(2026, 4, 20, 0, tzinfo=timezone.utc)
    return Bar(
        symbol="BTCUSDT",
        interval="1h",
        open_time=base + timedelta(hours=i),
        close_time=base + timedelta(hours=i + 1),
        open=Decimal("60000"),
        high=Decimal("60500"),
        low=Decimal("59800"),
        close=Decimal("60200"),
        volume=Decimal("1.5"),
        trade_count=100,
        is_closed=True,
        data_quality=DataQuality.OK,
    )


def test_writer_creates_file_and_persists_bars(tmp_path: Path) -> None:
    writer = ParquetBarWriter(directory=tmp_path, symbol="BTCUSDT", interval="1h")
    bars = [_bar(i) for i in range(3)]

    writer.append(bars)

    files = list(tmp_path.glob("*.parquet"))
    assert len(files) == 1
    table = pq.read_table(files[0])
    assert table.num_rows == 3
    assert set(table.schema.names) >= {
        "open_time", "close_time", "open", "high", "low", "close",
        "volume", "trade_count", "data_quality",
    }


def test_writer_append_is_additive(tmp_path: Path) -> None:
    writer = ParquetBarWriter(directory=tmp_path, symbol="BTCUSDT", interval="1h")
    writer.append([_bar(i) for i in range(2)])
    writer.append([_bar(i) for i in range(2, 5)])

    files = sorted(tmp_path.glob("*.parquet"))
    total = sum(pq.read_table(f).num_rows for f in files)
    assert total == 5
```

- [ ] **Step 2: Run test — expect fail**

Run: `pytest tests/unit/test_parquet_storage.py -v`
Expected: FAIL (ModuleNotFoundError).

- [ ] **Step 3: Implement `src/marketdata/storage.py`**

```python
"""Parquet writer for OHLCV bars (OLAP storage)."""
from datetime import datetime
from pathlib import Path
from typing import Iterable

import pyarrow as pa
import pyarrow.parquet as pq

from src.marketdata.models import Bar

_SCHEMA = pa.schema(
    [
        pa.field("open_time", pa.timestamp("ns", tz="UTC")),
        pa.field("close_time", pa.timestamp("ns", tz="UTC")),
        pa.field("open", pa.float64()),
        pa.field("high", pa.float64()),
        pa.field("low", pa.float64()),
        pa.field("close", pa.float64()),
        pa.field("volume", pa.float64()),
        pa.field("trade_count", pa.int64()),
        pa.field("data_quality", pa.string()),
    ]
)


class ParquetBarWriter:
    """Writes Bars to Parquet files (snappy compression).

    Each `append()` produces one new `.parquet` file, timestamped.
    Consolidation (merge small files) — out of scope v0.1.
    """

    def __init__(self, directory: Path, symbol: str, interval: str) -> None:
        self._dir = directory
        self._dir.mkdir(parents=True, exist_ok=True)
        self._symbol = symbol
        self._interval = interval

    def append(self, bars: Iterable[Bar]) -> Path:
        bars_list = list(bars)
        if not bars_list:
            raise ValueError("cannot append empty bar list")

        table = pa.table(
            {
                "open_time": [b.open_time for b in bars_list],
                "close_time": [b.close_time for b in bars_list],
                "open": [float(b.open) for b in bars_list],
                "high": [float(b.high) for b in bars_list],
                "low": [float(b.low) for b in bars_list],
                "close": [float(b.close) for b in bars_list],
                "volume": [float(b.volume) for b in bars_list],
                "trade_count": [b.trade_count for b in bars_list],
                "data_quality": [str(b.data_quality) for b in bars_list],
            },
            schema=_SCHEMA,
        )

        fname = (
            f"{self._symbol.lower()}_{self._interval}_"
            f"{bars_list[0].close_time.strftime('%Y%m%d%H%M%S')}"
            f"-{bars_list[-1].close_time.strftime('%Y%m%d%H%M%S')}.parquet"
        )
        path = self._dir / fname
        pq.write_table(table, path, compression="snappy")
        return path
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/unit/test_parquet_storage.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add src/marketdata/storage.py tests/unit/test_parquet_storage.py
git commit -m "feat(marketdata): add ParquetBarWriter with snappy compression"
```

---

### Task 10: Legacy cleanup

**Files:**
- Delete: `src/ml/` (entire directory)
- Delete: `src/gateway/` (entire directory)
- Delete: `src/strategy/hmm_regime.py`
- Delete: `src/strategy/order_flow.py`
- Delete: `src/data/orderbook.py` (L2 features, vне scope v0.1)
- Delete: `protos/` (proto definitions для gateway)
- Delete: `pybit-master/` (vendored Bybit SDK)
- Delete: `test_grpc_latency.py` (top-level; тестирует gRPC)
- Modify: `src/controller.py` (remove imports of deleted modules)
- Modify: `src/strategy/__init__.py` (remove hmm_regime/order_flow exports if any)
- Modify: `src/data/__init__.py` (remove orderbook export if any)

- [ ] **Step 1: Verify nothing non-legacy imports these modules**

Run:
```bash
grep -rE "from src\.(ml|gateway|strategy\.hmm_regime|strategy\.order_flow|data\.orderbook)" src tests --include="*.py" | grep -v "^src/(ml|gateway)/\|^src/strategy/hmm_regime\|^src/strategy/order_flow\|^src/data/orderbook"
```
Expected: вывод пустой ИЛИ только строки из `src/controller.py` (который модифицируем далее).

- [ ] **Step 2: Read `src/controller.py` to identify imports**

Run: `grep -n "ml\|gateway\|hmm_regime\|order_flow\|orderbook" src/controller.py`
Record line numbers of imports/usage. We remove ВСЕ такие строки + референсы.

- [ ] **Step 3: Edit `src/controller.py` to drop legacy imports**

For each matched line: delete import line. If there's usage in methods (e.g. `self.xgb_predictor = XGBPredictor(...)`) — удалить соответствующий блок (эти feature отключены в v0.1, см. ADR 0002). Commit включает только то, что в controller.py.

_(Engineer: читай файл перед редактированием, удаляй минимально — только строки с legacy-референсами. Если метод полностью полагается на legacy — удали метод и все его вызовы.)_

- [ ] **Step 4: Remove legacy files via `git rm`**

Run:
```bash
git rm -r src/ml src/gateway src/strategy/hmm_regime.py src/strategy/order_flow.py src/data/orderbook.py
git rm -r protos pybit-master
git rm test_grpc_latency.py
```

- [ ] **Step 5: Update `src/strategy/__init__.py` and `src/data/__init__.py`**

Read each file; удалить строки вида `from .hmm_regime import ...`, `from .order_flow import ...`, `from .orderbook import ...` если присутствуют.

- [ ] **Step 6: Verify no broken imports**

Run: `python -c "import src.controller; import src.strategy; import src.data"`
Expected: no ImportError.

- [ ] **Step 7: Run full test suite**

Run: `pytest -v`
Expected: все ранее зелёные тесты остаются зелёными; новых fail нет.

Если fail в `tests/test_math.py` или `test_backtest_extensions.py` — это legacy-тесты, which ломаются из-за удалённых импортов. В таком случае: добавить их в `git rm` (если они только тестируют удалённое) или пропатчить (если покрывают живой код).

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "chore(cleanup): remove legacy ml/gateway/hmm_regime/order_flow/orderbook modules (out of scope v0.1)"
```

---

### Task 11: Makefile + green suite verification

**Files:**
- Create: `Makefile`
- Create: `tests/conftest.py` (pytest-wide fixtures if needed — empty for now)

- [ ] **Step 1: Create `Makefile`**

Content (use **TAB** indentation for recipe bodies):
```makefile
.PHONY: test lint typecheck clean install

install:
	pip install -e ".[dev]"
	pre-commit install

test:
	pytest -v

lint:
	ruff check src tests
	ruff format --check src tests

typecheck:
	mypy --strict src

check: lint typecheck test

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
```

- [ ] **Step 2: Create empty `tests/conftest.py`**

Content:
```python
"""Shared pytest fixtures. Populated in later sprints."""
```

- [ ] **Step 3: Run `make check`**

Run: `make check`
Expected: ruff + mypy + pytest все зелёные. Если mypy ругается на уже существующий legacy-код, который мы не удалили (e.g. `src/core/math_engine.py`) — **это OK, так как scope S1 — только platform/marketdata/signalgen/execution slots; existing legacy-код остаётся untouched до S3-S5**. В таком случае: добавить в `pyproject.toml → [tool.mypy.overrides]` блок `module = ["src.core.*", "src.backtest.*", "src.strategy.*", "src.controller", "src.config_loader"]` с `ignore_errors = true`.

- [ ] **Step 4: Commit**

```bash
git add Makefile tests/conftest.py pyproject.toml
git commit -m "chore(build): add Makefile + conftest; green suite verified"
```

- [ ] **Step 5: Tag release candidate**

Run:
```bash
git tag -a v0.1.0-alpha.1 -m "Sprint 1 complete — Foundation (storage + models + cleanup)"
git push origin v0.1.0-alpha.1
```

---

### Task 12: Update wiki + log

**Files:**
- Create: `llm-wiki/wiki/project/components/config.md`
- Create: `llm-wiki/wiki/project/components/logging.md`
- Create: `llm-wiki/wiki/project/components/storage.md`
- Create: `llm-wiki/wiki/project/components/models.md`
- Modify: `llm-wiki/wiki/index.md`
- Modify: `llm-wiki/wiki/log.md`

- [ ] **Step 1: Create 4 component pages**

Each page ~100-200 words, following template from `llm-wiki/CLAUDE.md` "Скелет страницы сущности". Content sources: actual implemented code from `src/platform/` and `src/marketdata/`. Frontmatter fields per `llm-wiki/CLAUDE.md`.

Minimum content per page:
- `config.md`: Settings class, env var list, live_trading invariant, ссылка на [[../architecture/stack-v0.1]].
- `logging.md`: structlog config, JSON renderer, required keys (event, level, timestamp).
- `storage.md` (component): ParquetBarWriter + SQLite connect/init_db, ссылка на [[../architecture/storage]].
- `models.md`: Bar/Signal/Order/Fill с их invariants.

- [ ] **Step 2: Append components to `wiki/index.md`**

Under `## Project — Components`, replace `_(пусто — ...)` with 4 bullet list entries.

- [ ] **Step 3: Append log entry to `wiki/log.md`**

```markdown
## [YYYY-MM-DD] ingest | Sprint 1 — Foundation completed
- Added (code): src/platform/{config,logging,db}.py, src/marketdata/{models,storage}.py, src/signalgen/models.py, src/execution/models.py, migrations/001_initial.sql, Makefile, pyproject.toml.
- Removed: src/ml/, src/gateway/, src/strategy/{hmm_regime,order_flow}.py, src/data/orderbook.py, protos/, pybit-master/, test_grpc_latency.py.
- Added (wiki): wiki/project/components/{config,logging,storage,models}.md.
- Updated (wiki): wiki/index.md.
- Tag: v0.1.0-alpha.1; branch legacy/phase1-bybit preserved.
- Notes: Sprint 1 DoD выполнен. Следующий — Sprint 2 (Binance Spot data consumer).
```

(Engineer: заменить `YYYY-MM-DD` на актуальную дату.)

- [ ] **Step 4: Commit wiki updates**

```bash
git add llm-wiki/wiki/project/components llm-wiki/wiki/index.md llm-wiki/wiki/log.md
git commit -m "docs(wiki): Sprint 1 components + log entry"
```

---

## Sprint 1 Done-Criteria Checklist (финальная проверка)

- [ ] `make check` зелёный (ruff + mypy + pytest).
- [ ] `python -c "from src.platform.db import init_db; from pathlib import Path; init_db(Path('/tmp/s1-check.db'), Path('migrations'))"` создаёт БД без ошибок; `sqlite3 /tmp/s1-check.db ".tables"` показывает 9 таблиц (включая `schema_migrations`).
- [ ] Все 4 pydantic-модели (Bar, Signal, Order, Fill) валидируют invariants — unit tests green.
- [ ] `git branch -r | grep legacy/phase1-bybit` показывает remote branch.
- [ ] `ls src/` не содержит `ml/`, `gateway/`; `src/strategy/` не содержит `hmm_regime.py`, `order_flow.py`; `src/data/` не содержит `orderbook.py`.
- [ ] Tag `v0.1.0-alpha.1` создан.
- [ ] `wiki/project/components/` содержит 4 новые страницы; `wiki/index.md` и `wiki/log.md` обновлены.

## Related

- [[../architecture/migration-plan]] — §S1 (этот план реализует его).
- [[../architecture/storage]] — источник SQL-схемы и Parquet-схемы.
- [[../architecture/stack-v0.1]] — стек и версии.
- [[../architecture/overview]] — общий таргет v0.1.
- ADR: [[../decisions/0003-sqlite-parquet-for-storage]], [[../decisions/0006-pydantic-v2-for-domain-models]], [[../decisions/0007-utc-timestamps-ns-precision]].
