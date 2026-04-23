---
title: Sprint 4 — Risk & Circuit Breakers — Tasks 1-8
type: plan-part
tags: [plan, sprint-4, risk, kelly, circuit-breakers, tdd]
created: 2026-04-23
updated: 2026-04-23
status: ready-to-execute
part: 1 of 2
parent: 2026-04-23-sprint-4-risk.md
sources:
  - project/architecture/migration-plan.md §S4
  - project/decisions/0012-4-phase-kelly-sizing.md
  - project/decisions/0013-circuit-breakers-l1-l2-l3-flash.md
  - trading/concepts/kelly-phases.md
  - trading/concepts/circuit-breakers.md
---

# Sprint 4 — Tasks 1-8

> **Index:** [2026-04-23-sprint-4-risk.md](2026-04-23-sprint-4-risk.md)

---

## Tasks

### Task 1: Migration `002_risk.sql` + idempotency test

**Files:**
- Create: `migrations/002_risk.sql`
- Create: `tests/unit/test_risk_migration.py`

- [ ] **Step 1: RED — write idempotency test**

Create `tests/unit/test_risk_migration.py`:

```python
"""Tests for migrations/002_risk.sql idempotency and schema correctness."""

import sqlite3
from pathlib import Path

import pytest

from src.platform.db import connect, init_db

MIGRATIONS_DIR = Path(__file__).parents[2] / "migrations"


@pytest.fixture()
def db(tmp_path: Path) -> sqlite3.Connection:
    db_path = tmp_path / "test.db"
    init_db(db_path, MIGRATIONS_DIR)
    return connect(db_path)


def test_trade_history_table_exists(db: sqlite3.Connection) -> None:
    rows = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='trade_history'"
    ).fetchall()
    assert len(rows) == 1


def test_equity_snapshots_table_exists(db: sqlite3.Connection) -> None:
    rows = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='equity_snapshots'"
    ).fetchall()
    assert len(rows) == 1


def test_trade_history_columns(db: sqlite3.Connection) -> None:
    cols = {row[1] for row in db.execute("PRAGMA table_info(trade_history)").fetchall()}
    expected = {
        "trade_id", "symbol", "entry_signal_id", "entry_ts", "exit_ts",
        "qty", "entry_price", "exit_price", "pnl_quote", "pnl_pct",
        "fees_paid", "reason_code", "kelly_phase", "recorded_at",
    }
    assert expected <= cols


def test_equity_snapshots_columns(db: sqlite3.Connection) -> None:
    cols = {row[1] for row in db.execute("PRAGMA table_info(equity_snapshots)").fetchall()}
    expected = {
        "snapshot_id", "ts", "realized_equity", "unrealized_pnl",
        "total_equity", "source",
    }
    assert expected <= cols


def test_kelly_phase_check_constraint(db: sqlite3.Connection) -> None:
    """kelly_phase CHECK(IN (1,2,3,4)) должен отклонить 0 и 5."""
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO trade_history VALUES "
            "(NULL,'BTCUSDT','sig-1','2026-01-01T00:00:00','2026-01-01T01:00:00',"
            "'0.001','50000','51000','10','0.02','0.5','ENTRY_LONG_TREND_FOLLOWING',0,'2026-01-01T01:00:00')"
        )


def test_equity_source_check_constraint(db: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO equity_snapshots VALUES "
            "(NULL,'2026-01-01T00:00:00','10000','0','10000','INVALID_SOURCE')"
        )


def test_idempotent_double_init(tmp_path: Path) -> None:
    """Повторный init_db не должен падать."""
    db_path = tmp_path / "idempotent.db"
    init_db(db_path, MIGRATIONS_DIR)
    init_db(db_path, MIGRATIONS_DIR)  # должно пройти без ошибки


def test_state_table_exists(db: sqlite3.Connection) -> None:
    """state таблица из 001_initial.sql должна существовать (реюзается S4)."""
    rows = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='state'"
    ).fetchall()
    assert len(rows) == 1
```

- [ ] **Step 2: Run test — verify RED**

```bash
pytest tests/unit/test_risk_migration.py -v
```
Expected: FAIL — `migrations/002_risk.sql` не существует, поэтому `trade_history` и `equity_snapshots` таблицы отсутствуют.

- [ ] **Step 3: GREEN — create `migrations/002_risk.sql`**

Create `migrations/002_risk.sql`:

```sql
-- Sprint 4 — Risk & Circuit Breakers schema.
-- Source: wiki/project/plans/2026-04-23-sprint-4-risk.md §Q5

CREATE TABLE trade_history (
    trade_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol           TEXT    NOT NULL,
    entry_signal_id  TEXT    NOT NULL,
    entry_ts         TEXT    NOT NULL,
    exit_ts          TEXT    NOT NULL,
    qty              TEXT    NOT NULL,
    entry_price      TEXT    NOT NULL,
    exit_price       TEXT    NOT NULL,
    pnl_quote        TEXT    NOT NULL,
    pnl_pct          TEXT    NOT NULL,
    fees_paid        TEXT    NOT NULL,
    reason_code      TEXT    NOT NULL,
    kelly_phase      INTEGER NOT NULL CHECK(kelly_phase IN (1,2,3,4)),
    recorded_at      TEXT    NOT NULL
);
CREATE INDEX idx_trade_history_exit_ts     ON trade_history(exit_ts);
CREATE INDEX idx_trade_history_symbol_exit ON trade_history(symbol, exit_ts);

CREATE TABLE equity_snapshots (
    snapshot_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    ts               TEXT    NOT NULL,
    realized_equity  TEXT    NOT NULL,
    unrealized_pnl   TEXT    NOT NULL,
    total_equity     TEXT    NOT NULL,
    source           TEXT    NOT NULL CHECK(source IN ('BAR_CLOSE','POSITION_CLOSE','MANUAL'))
);
CREATE INDEX idx_equity_ts ON equity_snapshots(ts);
```

- [ ] **Step 4: Run tests — verify GREEN**

```bash
pytest tests/unit/test_risk_migration.py -v
```
Expected: 8/8 passed.

- [ ] **Step 5: Commit**

```bash
git add migrations/002_risk.sql tests/unit/test_risk_migration.py
git commit -m "feat(risk): add 002_risk.sql migration (trade_history + equity_snapshots)

trade_history stores closed trade records for Kelly stat computation.
equity_snapshots enables 24h HWM rolling drawdown calculation.
Idempotency guaranteed via schema_migrations tracking in init_db().
Source: wiki/project/plans/2026-04-23-sprint-4-risk.md §Task-1"
```

---

### Task 2: Settings additions + `config_hash()`

**Files:**
- Modify: `src/platform/config.py`
- Create: `tests/unit/test_risk_settings.py`

- [ ] **Step 1: RED — write settings tests**

Create `tests/unit/test_risk_settings.py`:

```python
"""Tests for risk-related Settings fields and config_hash()."""

import hashlib
import json
from decimal import Decimal
from pathlib import Path

import pytest

from src.platform.config import Settings


@pytest.fixture()
def settings(tmp_path: Path) -> Settings:
    return Settings(
        data_dir=tmp_path / "data",
        log_dir=tmp_path / "logs",
        db_path=tmp_path / "bot.db",
        parquet_dir=tmp_path / "parquet",
        risk_override_path=tmp_path / "state" / "cb_override.json",
    )


def test_risk_defaults_present(settings: Settings) -> None:
    assert settings.risk_max_position_pct_cap == Decimal("0.05")
    assert settings.risk_sl_atr_multiplier == Decimal("1.5")
    assert settings.risk_tp_atr_multiplier == Decimal("3.0")
    assert settings.risk_cb_l1_dd == Decimal("0.15")
    assert settings.risk_cb_l2_dd == Decimal("0.22")
    assert settings.risk_cb_l3_dd == Decimal("0.30")
    assert settings.risk_cb_flash_abs == Decimal("0.08")
    assert settings.risk_cb_flash_atr_mult == Decimal("3.0")
    assert settings.risk_kelly_phase1_cap == Decimal("0.01")
    assert settings.risk_kelly_phase2_cap == Decimal("0.02")
    assert settings.risk_kelly_phase3_cap == Decimal("0.03")
    assert settings.risk_kelly_phase4_cap == Decimal("0.05")


def test_risk_override_path_type(settings: Settings) -> None:
    assert isinstance(settings.risk_override_path, Path)


def test_config_hash_is_deterministic(settings: Settings) -> None:
    h1 = settings.config_hash()
    h2 = settings.config_hash()
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex


def test_config_hash_changes_with_value(tmp_path: Path) -> None:
    s1 = Settings(
        data_dir=tmp_path / "data",
        log_dir=tmp_path / "logs",
        db_path=tmp_path / "bot.db",
        parquet_dir=tmp_path / "parquet",
        risk_override_path=tmp_path / "state" / "cb_override.json",
        risk_cb_l1_dd=Decimal("0.15"),
    )
    s2 = Settings(
        data_dir=tmp_path / "data",
        log_dir=tmp_path / "logs",
        db_path=tmp_path / "bot.db",
        parquet_dir=tmp_path / "parquet",
        risk_override_path=tmp_path / "state" / "cb_override.json",
        risk_cb_l1_dd=Decimal("0.20"),  # changed
    )
    assert s1.config_hash() != s2.config_hash()
```

- [ ] **Step 2: Run test — verify RED**

```bash
pytest tests/unit/test_risk_settings.py -v
```
Expected: FAIL — `risk_max_position_pct_cap` and other fields not found on `Settings`.

- [ ] **Step 3: GREEN — add risk fields to `src/platform/config.py`**

Append to `Settings` class (after `log_level` field, before `@model_validator`):

```python
    # Risk management parameters (S4)
    risk_max_position_pct_cap: Decimal = Decimal("0.05")
    risk_sl_atr_multiplier: Decimal = Decimal("1.5")
    risk_tp_atr_multiplier: Decimal = Decimal("3.0")
    risk_cb_l1_dd: Decimal = Decimal("0.15")
    risk_cb_l2_dd: Decimal = Decimal("0.22")
    risk_cb_l3_dd: Decimal = Decimal("0.30")
    risk_cb_flash_abs: Decimal = Decimal("0.08")
    risk_cb_flash_atr_mult: Decimal = Decimal("3.0")
    risk_kelly_phase1_cap: Decimal = Decimal("0.01")
    risk_kelly_phase2_cap: Decimal = Decimal("0.02")
    risk_kelly_phase3_cap: Decimal = Decimal("0.03")
    risk_kelly_phase4_cap: Decimal = Decimal("0.05")
    risk_override_path: Path = Path("state/cb_override.json")
```

Add import at top: `import hashlib, json` (add to existing imports block).

Add method to `Settings` class (after `_live_trading_guards`):

```python
    def config_hash(self) -> str:
        """SHA-256 of sorted JSON dump of all settings.

        Used to bind manual CB override to the config that generated the halt.
        Path values serialized as strings.
        """
        raw = self.model_dump(mode="json")
        # Ensure deterministic serialization
        serialized = json.dumps(raw, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()
```

Also add at top of file: `import hashlib` and `import json`.

- [ ] **Step 4: Run tests — verify GREEN**

```bash
pytest tests/unit/test_risk_settings.py -v
```
Expected: 5/5 passed.

- [ ] **Step 5: Verify existing tests still pass**

```bash
pytest tests/unit/ -v --tb=short
```
Expected: all previously passing tests still pass.

- [ ] **Step 6: Commit**

```bash
git add src/platform/config.py tests/unit/test_risk_settings.py
git commit -m "feat(config): add risk settings fields + config_hash() SHA-256

13 risk params (Kelly caps, CB thresholds, SL/TP multipliers).
config_hash() used to bind manual CB override to specific config.
Source: wiki/project/plans/2026-04-23-sprint-4-risk.md §Task-2"
```

---

### Task 3: `src/risk/reason_codes.py` — ReasonCode StrEnum

**Files:**
- Create: `src/risk/reason_codes.py`
- Create: `tests/unit/test_reason_codes.py`

**Critical design note:** The 28-enum from `wiki/trading/concepts/reason-codes.md` does NOT include task-prompt names like `APPROVED`, `RISK_REJECT_HALT_L1`, etc. This plan uses **only canonical 28-enum names**. The relevant risk codes are: `REJECT_RISK_EXCEEDED`, `HALT_DRAWDOWN_L1`, `HALT_DRAWDOWN_L2`, `HALT_DRAWDOWN_L3`, `HALT_FLASH_CRASH`, `HALT_KILL_SWITCH`. See §Decisions & deviations D1/D2 and §Follow-ups.

- [ ] **Step 1: RED — write reason_codes tests**

Create `tests/unit/test_reason_codes.py`:

```python
"""Tests for ReasonCode StrEnum — must contain all 28 canonical codes."""

from src.risk.reason_codes import ReasonCode


def test_all_28_codes_present() -> None:
    """Every code from wiki/trading/concepts/reason-codes.md must exist."""
    expected = {
        # Entry (6)
        "ENTRY_LONG_TREND_FOLLOWING",
        "ENTRY_SHORT_TREND_FOLLOWING",
        "ENTRY_LONG_PULLBACK",
        "ENTRY_SHORT_PULLBACK",
        "SCALE_IN_LONG",
        "SCALE_IN_SHORT",
        # Scale / exits (7)
        "SCALE_OUT_PARTIAL",
        "EXIT_SL_HIT",
        "EXIT_TP_HIT",
        "EXIT_TRAILING_STOP",
        "EXIT_SIGNAL_FLIP",
        "EXIT_TIME_STOP",
        "EXIT_MANUAL_OVERRIDE",
        "EXIT_CIRCUIT_BREAKER",
        # Rejects (8)
        "REJECT_RISK_EXCEEDED",
        "REJECT_INSUFFICIENT_BALANCE",
        "REJECT_STALE_DATA",
        "REJECT_RATE_LIMITED",
        "REJECT_CLOCK_DRIFT",
        "REJECT_MIN_NOTIONAL",
        "REJECT_FILTER_PRICE",
        "REJECT_DUPLICATE_SIGNAL",
        # Halts (7)
        "HALT_DRAWDOWN_L1",
        "HALT_DRAWDOWN_L2",
        "HALT_DRAWDOWN_L3",
        "HALT_FLASH_CRASH",
        "HALT_DATA_QUALITY",
        "HALT_EXCHANGE_OUTAGE",
        "HALT_KILL_SWITCH",
    }
    actual = {code.name for code in ReasonCode}
    assert actual == expected, (
        f"Missing: {expected - actual}; Extra: {actual - expected}"
    )


def test_reason_code_is_str() -> None:
    assert isinstance(ReasonCode.HALT_DRAWDOWN_L1, str)
    assert ReasonCode.HALT_DRAWDOWN_L1 == "HALT_DRAWDOWN_L1"


def test_reason_code_count() -> None:
    assert len(ReasonCode) == 28


def test_risk_relevant_codes_accessible() -> None:
    """Codes used by S4 risk manager must be accessible."""
    _ = ReasonCode.REJECT_RISK_EXCEEDED
    _ = ReasonCode.HALT_DRAWDOWN_L1
    _ = ReasonCode.HALT_DRAWDOWN_L2
    _ = ReasonCode.HALT_DRAWDOWN_L3
    _ = ReasonCode.HALT_FLASH_CRASH
    _ = ReasonCode.HALT_KILL_SWITCH
    _ = ReasonCode.EXIT_CIRCUIT_BREAKER
```

- [ ] **Step 2: Run test — verify RED**

```bash
pytest tests/unit/test_reason_codes.py -v
```
Expected: FAIL — `src.risk.reason_codes` не существует.

- [ ] **Step 3: GREEN — create `src/risk/reason_codes.py`**

```python
"""Canonical 28 reason codes for audit-log and risk events.

Source: wiki/trading/concepts/reason-codes.md
ADR: wiki/project/decisions/ (see reason-codes-schema).

IMMUTABLE: codes are never renamed. New codes added at end per wiki rule.
If a new code is needed that doesn't exist here → open ADR amendment first.
"""

from enum import StrEnum


class ReasonCode(StrEnum):
    # Entry (6)
    ENTRY_LONG_TREND_FOLLOWING = "ENTRY_LONG_TREND_FOLLOWING"
    ENTRY_SHORT_TREND_FOLLOWING = "ENTRY_SHORT_TREND_FOLLOWING"
    ENTRY_LONG_PULLBACK = "ENTRY_LONG_PULLBACK"
    ENTRY_SHORT_PULLBACK = "ENTRY_SHORT_PULLBACK"
    SCALE_IN_LONG = "SCALE_IN_LONG"
    SCALE_IN_SHORT = "SCALE_IN_SHORT"

    # Scale / exits (8)
    SCALE_OUT_PARTIAL = "SCALE_OUT_PARTIAL"
    EXIT_SL_HIT = "EXIT_SL_HIT"
    EXIT_TP_HIT = "EXIT_TP_HIT"
    EXIT_TRAILING_STOP = "EXIT_TRAILING_STOP"
    EXIT_SIGNAL_FLIP = "EXIT_SIGNAL_FLIP"
    EXIT_TIME_STOP = "EXIT_TIME_STOP"
    EXIT_MANUAL_OVERRIDE = "EXIT_MANUAL_OVERRIDE"
    EXIT_CIRCUIT_BREAKER = "EXIT_CIRCUIT_BREAKER"

    # Rejects (8)
    REJECT_RISK_EXCEEDED = "REJECT_RISK_EXCEEDED"
    REJECT_INSUFFICIENT_BALANCE = "REJECT_INSUFFICIENT_BALANCE"
    REJECT_STALE_DATA = "REJECT_STALE_DATA"
    REJECT_RATE_LIMITED = "REJECT_RATE_LIMITED"
    REJECT_CLOCK_DRIFT = "REJECT_CLOCK_DRIFT"
    REJECT_MIN_NOTIONAL = "REJECT_MIN_NOTIONAL"
    REJECT_FILTER_PRICE = "REJECT_FILTER_PRICE"
    REJECT_DUPLICATE_SIGNAL = "REJECT_DUPLICATE_SIGNAL"

    # Halts (7)
    HALT_DRAWDOWN_L1 = "HALT_DRAWDOWN_L1"
    HALT_DRAWDOWN_L2 = "HALT_DRAWDOWN_L2"
    HALT_DRAWDOWN_L3 = "HALT_DRAWDOWN_L3"
    HALT_FLASH_CRASH = "HALT_FLASH_CRASH"
    HALT_DATA_QUALITY = "HALT_DATA_QUALITY"
    HALT_EXCHANGE_OUTAGE = "HALT_EXCHANGE_OUTAGE"
    HALT_KILL_SWITCH = "HALT_KILL_SWITCH"
```

- [ ] **Step 4: Run tests — verify GREEN**

```bash
pytest tests/unit/test_reason_codes.py -v
```
Expected: 4/4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/risk/reason_codes.py tests/unit/test_reason_codes.py
git commit -m "feat(risk): add ReasonCode StrEnum — canonical 28 codes

All 28 codes from wiki/trading/concepts/reason-codes.md.
Immutable per wiki rule: new codes require ADR amendment.
Note: prompt-requested APPROVED/RISK_REJECT_HALT_* names are non-canonical;
flagged as Follow-up ADR amendment (see plan §Follow-ups).
Source: wiki/project/plans/2026-04-23-sprint-4-risk.md §Task-3"
```

---

### Task 4: `src/risk/models.py` — `HaltState` + `RiskAssessment`

**Files:**
- Create: `src/risk/models.py`
- Create: `tests/unit/test_risk_models.py`

- [ ] **Step 1: RED — write models tests**

Create `tests/unit/test_risk_models.py`:

```python
"""Tests for HaltState StrEnum and RiskAssessment frozen pydantic model."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.risk.models import HaltState, RiskAssessment
from src.risk.reason_codes import ReasonCode


def _approved_assessment(**overrides) -> RiskAssessment:
    base = dict(
        signal_id=uuid4(),
        approved=True,
        qty=Decimal("0.001"),
        sl_price=Decimal("49000"),
        tp_price=Decimal("53000"),
        kelly_phase=1,
        kelly_fraction=Decimal("0.01"),
        halt_state=HaltState.L0,
        reason_code=ReasonCode.ENTRY_LONG_TREND_FOLLOWING,
        assessed_at=datetime.now(timezone.utc),
    )
    base.update(overrides)
    return RiskAssessment(**base)


def test_halt_state_values() -> None:
    assert set(HaltState) == {
        HaltState.L0, HaltState.L1, HaltState.L2, HaltState.L3, HaltState.FLASH
    }
    assert HaltState.L0 == "L0"
    assert isinstance(HaltState.L1, str)


def test_risk_assessment_approved() -> None:
    ra = _approved_assessment()
    assert ra.approved is True
    assert ra.kelly_phase == 1


def test_risk_assessment_rejected() -> None:
    ra = _approved_assessment(
        approved=False,
        qty=None,
        sl_price=None,
        tp_price=None,
        halt_state=HaltState.L1,
        reason_code=ReasonCode.HALT_DRAWDOWN_L1,
    )
    assert ra.approved is False
    assert ra.qty is None


def test_risk_assessment_is_frozen() -> None:
    ra = _approved_assessment()
    with pytest.raises(Exception):
        ra.approved = False  # type: ignore[misc]


def test_risk_assessment_extra_fields_forbidden() -> None:
    with pytest.raises(ValidationError):
        RiskAssessment(
            signal_id=uuid4(),
            approved=True,
            qty=Decimal("0.001"),
            sl_price=Decimal("49000"),
            tp_price=Decimal("53000"),
            kelly_phase=1,
            kelly_fraction=Decimal("0.01"),
            halt_state=HaltState.L0,
            reason_code=ReasonCode.ENTRY_LONG_TREND_FOLLOWING,
            assessed_at=datetime.now(timezone.utc),
            unknown_field="bad",  # type: ignore[call-arg]
        )


def test_kelly_phase_must_be_literal() -> None:
    with pytest.raises(ValidationError):
        _approved_assessment(kelly_phase=5)  # type: ignore[arg-type]


def test_kelly_fraction_decimal() -> None:
    ra = _approved_assessment(kelly_fraction=Decimal("0.0250"))
    assert isinstance(ra.kelly_fraction, Decimal)
```

- [ ] **Step 2: Run test — verify RED**

```bash
pytest tests/unit/test_risk_models.py -v
```
Expected: FAIL — `src.risk.models` не существует.

- [ ] **Step 3: GREEN — create `src/risk/models.py`**

```python
"""Risk domain models — HaltState and RiskAssessment.

Source: wiki/project/plans/2026-04-23-sprint-4-risk.md §Q4
"""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.risk.reason_codes import ReasonCode


class HaltState(StrEnum):
    """Circuit breaker level. L0 = no halt."""
    L0 = "L0"
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    FLASH = "FLASH"


class RiskAssessment(BaseModel):
    """Immutable output of RiskManager.assess(). One per signal evaluation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    signal_id: UUID
    approved: bool
    qty: Decimal | None
    sl_price: Decimal | None      # mark_price - risk_sl_atr_multiplier * ATR
    tp_price: Decimal | None      # mark_price + risk_tp_atr_multiplier * ATR
    kelly_phase: Literal[1, 2, 3, 4]
    kelly_fraction: Decimal
    halt_state: HaltState
    reason_code: ReasonCode
    assessed_at: datetime
```

- [ ] **Step 4: Run tests — verify GREEN**

```bash
pytest tests/unit/test_risk_models.py -v
```
Expected: 7/7 passed.

- [ ] **Step 5: Commit**

```bash
git add src/risk/models.py tests/unit/test_risk_models.py
git commit -m "feat(risk): add HaltState StrEnum and RiskAssessment frozen model

HaltState: L0|L1|L2|L3|FLASH.
RiskAssessment: frozen pydantic v2, carries kelly_phase/fraction/halt_state/reason_code.
Source: wiki/project/plans/2026-04-23-sprint-4-risk.md §Task-4"
```

---

### Task 5: `src/risk/sizing.py` — `compute_qty()` pure function

**Files:**
- Create: `src/risk/sizing.py`
- Create: `tests/unit/test_sizing.py`

- [ ] **Step 1: RED — write sizing tests including property test**

Create `tests/unit/test_sizing.py`:

```python
"""Tests for compute_qty() pure position sizing function."""

from decimal import Decimal

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from src.risk.sizing import compute_qty


def test_basic_sizing() -> None:
    """qty = (fraction * equity) / (k * atr * price / price) = fraction*equity / (k*atr).

    Simplified: qty = floor((fraction * equity) / (k * atr)) shares,
    but actual formula uses price: qty = (fraction * equity) / (k * atr) in base units.
    """
    # equity=10000, fraction=0.01 → risk_capital=100
    # atr=100 USDT, price=50000, k=1.5
    # qty = 100 / (1.5 * 100) = 100 / 150 = 0.666... → truncated to 8 decimal places
    qty = compute_qty(
        equity=Decimal("10000"),
        fraction=Decimal("0.01"),
        atr=Decimal("100"),
        price=Decimal("50000"),
        k=Decimal("1.5"),
    )
    assert qty >= Decimal("0")
    # risk_capital = 0.01 * 10000 = 100
    # qty = 100 / (1.5 * 100) — note: price not in denominator per sizing formula
    # Formula: qty = (fraction * equity) / (k * atr)
    assert qty == pytest.approx(Decimal("100") / (Decimal("1.5") * Decimal("100")), rel=Decimal("1e-8"))


def test_zero_atr_returns_zero() -> None:
    qty = compute_qty(
        equity=Decimal("10000"),
        fraction=Decimal("0.01"),
        atr=Decimal("0"),
        price=Decimal("50000"),
    )
    assert qty == Decimal("0")


def test_zero_fraction_returns_zero() -> None:
    qty = compute_qty(
        equity=Decimal("10000"),
        fraction=Decimal("0"),
        atr=Decimal("100"),
        price=Decimal("50000"),
    )
    assert qty == Decimal("0")


def test_result_is_decimal() -> None:
    qty = compute_qty(
        equity=Decimal("10000"),
        fraction=Decimal("0.01"),
        atr=Decimal("100"),
        price=Decimal("50000"),
    )
    assert isinstance(qty, Decimal)


def test_qty_non_negative() -> None:
    qty = compute_qty(
        equity=Decimal("5000"),
        fraction=Decimal("0.02"),
        atr=Decimal("200"),
        price=Decimal("30000"),
    )
    assert qty >= Decimal("0")


@given(
    equity=st.decimals(min_value="1000", max_value="1000000", allow_nan=False, allow_infinity=False),
    fraction=st.decimals(min_value="0.001", max_value="0.05", allow_nan=False, allow_infinity=False),
    atr=st.decimals(min_value="1", max_value="10000", allow_nan=False, allow_infinity=False),
    price=st.decimals(min_value="100", max_value="200000", allow_nan=False, allow_infinity=False),
)
@settings(max_examples=200)
def test_property_qty_non_negative(
    equity: Decimal, fraction: Decimal, atr: Decimal, price: Decimal
) -> None:
    """Property: qty is always >= 0 for positive inputs."""
    qty = compute_qty(equity=equity, fraction=fraction, atr=atr, price=price)
    assert qty >= Decimal("0")


@given(
    equity=st.decimals(min_value="1000", max_value="1000000", allow_nan=False, allow_infinity=False),
    atr=st.decimals(min_value="1", max_value="10000", allow_nan=False, allow_infinity=False),
    price=st.decimals(min_value="100", max_value="200000", allow_nan=False, allow_infinity=False),
    cap=st.decimals(min_value="0.001", max_value="0.05", allow_nan=False, allow_infinity=False),
)
@settings(max_examples=200)
def test_property_fraction_cap_respected(
    equity: Decimal, atr: Decimal, price: Decimal, cap: Decimal
) -> None:
    """Property: risk capital never exceeds cap * equity."""
    qty = compute_qty(equity=equity, fraction=cap, atr=atr, price=price)
    risk_capital = qty * atr * Decimal("1.5")  # inverse of formula with k=1.5
    assert risk_capital <= equity * cap * (1 + Decimal("1e-8"))  # allow rounding
```

- [ ] **Step 2: Run test — verify RED**

```bash
pytest tests/unit/test_sizing.py -v
```
Expected: FAIL — `src.risk.sizing` не существует.

- [ ] **Step 3: GREEN — create `src/risk/sizing.py`**

```python
"""Position sizing — pure function, no I/O, no state.

Formula: qty = (fraction * equity) / (k * atr)
where:
    fraction — Kelly phase-adjusted fraction of equity to risk
    equity   — current total equity (realized + unrealized)
    k        — ATR multiplier for stop-loss distance (default 1.5)
    atr      — current ATR value in quote currency

Source: wiki/project/plans/2026-04-23-sprint-4-risk.md §Q4
wiki/trading/concepts/kelly-phases.md
"""

from decimal import Decimal

_EIGHT_DPS = Decimal("0.00000001")


def compute_qty(
    *,
    equity: Decimal,
    fraction: Decimal,
    atr: Decimal,
    price: Decimal,  # noqa: ARG001 — reserved for future lot-size rounding
    k: Decimal = Decimal("1.5"),
) -> Decimal:
    """Compute position quantity from Kelly fraction + ATR-based risk.

    Args:
        equity:   Total account equity in quote currency (Decimal).
        fraction: Kelly phase-adjusted fraction (0 < fraction ≤ 0.05).
        atr:      Current ATR in quote currency (Decimal, >= 0).
        price:    Current mark price (reserved for lot-size rounding in S5).
        k:        ATR multiplier for SL distance (default 1.5 per Settings).

    Returns:
        Quantity in base asset, truncated to 8 decimal places. Zero if atr=0 or fraction=0.
    """
    if atr <= Decimal("0") or fraction <= Decimal("0"):
        return Decimal("0")
    denominator = k * atr
    qty = (fraction * equity) / denominator
    return qty.quantize(_EIGHT_DPS)
```

- [ ] **Step 4: Run tests — verify GREEN**

```bash
pytest tests/unit/test_sizing.py -v
```
Expected: all passed (including hypothesis property tests).

- [ ] **Step 5: Commit**

```bash
git add src/risk/sizing.py tests/unit/test_sizing.py
git commit -m "feat(risk): add compute_qty() pure sizing function

qty = (fraction * equity) / (k * atr), truncated to 8dp.
Property tests: result >= 0; risk capital <= cap * equity.
Source: wiki/project/plans/2026-04-23-sprint-4-risk.md §Task-5"
```

---

### Task 6: `src/risk/kelly.py` — `KellyCalculator`

**Files:**
- Create: `src/risk/kelly.py`
- Create: `tests/unit/test_kelly.py`

- [ ] **Step 1: RED — write kelly tests**

Create `tests/unit/test_kelly.py`:

```python
"""Tests for KellyCalculator — phase transitions, Wilson CI, fraction caps."""

from decimal import Decimal

import pytest

from src.risk.kelly import KellyCalculator


@pytest.fixture()
def calc() -> KellyCalculator:
    return KellyCalculator()


def test_phase_boundaries(calc: KellyCalculator) -> None:
    """Phase transitions at n=30, 100, 200."""
    assert calc.phase_from_trade_count(0) == 1
    assert calc.phase_from_trade_count(1) == 1
    assert calc.phase_from_trade_count(29) == 1
    assert calc.phase_from_trade_count(30) == 2
    assert calc.phase_from_trade_count(99) == 2
    assert calc.phase_from_trade_count(100) == 3
    assert calc.phase_from_trade_count(199) == 3
    assert calc.phase_from_trade_count(200) == 4
    assert calc.phase_from_trade_count(500) == 4


def test_phase_transition_29_to_30(calc: KellyCalculator) -> None:
    """n=29 → phase 1 (fixed 1%); n=30 → phase 2 (fixed 2%)."""
    f29 = calc.phase_adjusted_fraction(
        trade_count=29, p_hat=Decimal("0.55"), b=Decimal("1.5")
    )
    f30 = calc.phase_adjusted_fraction(
        trade_count=30, p_hat=Decimal("0.55"), b=Decimal("1.5")
    )
    assert f29 == Decimal("0.01")
    assert f30 == Decimal("0.02")


def test_phase_transition_99_to_100(calc: KellyCalculator) -> None:
    f99 = calc.phase_adjusted_fraction(
        trade_count=99, p_hat=Decimal("0.55"), b=Decimal("1.5")
    )
    f100 = calc.phase_adjusted_fraction(
        trade_count=100, p_hat=Decimal("0.55"), b=Decimal("1.5")
    )
    assert f99 == Decimal("0.02")
    assert f100 <= Decimal("0.03")  # phase 3 = quarter-Kelly, cap 3%


def test_phase_transition_199_to_200(calc: KellyCalculator) -> None:
    f199 = calc.phase_adjusted_fraction(
        trade_count=199, p_hat=Decimal("0.55"), b=Decimal("1.5")
    )
    f200 = calc.phase_adjusted_fraction(
        trade_count=200, p_hat=Decimal("0.55"), b=Decimal("1.5")
    )
    assert f199 <= Decimal("0.03")  # phase 3 cap
    assert f200 <= Decimal("0.05")  # phase 4 cap


def test_phase3_cap_enforced(calc: KellyCalculator) -> None:
    """Phase 3: quarter-Kelly cannot exceed 3%."""
    # Extreme p_hat/b that would give large f*
    fraction = calc.phase_adjusted_fraction(
        trade_count=150, p_hat=Decimal("0.90"), b=Decimal("5.0")
    )
    assert fraction <= Decimal("0.03")


def test_phase4_cap_enforced(calc: KellyCalculator) -> None:
    """Phase 4: half-Kelly cannot exceed 5%."""
    fraction = calc.phase_adjusted_fraction(
        trade_count=300, p_hat=Decimal("0.90"), b=Decimal("5.0")
    )
    assert fraction <= Decimal("0.05")


def test_kelly_fraction_negative_edge(calc: KellyCalculator) -> None:
    """f* negative when p*b < q → returns 0 (no bet)."""
    fraction = calc.kelly_fraction(p_hat=Decimal("0.3"), b=Decimal("1.0"))
    # f* = (0.3*1.0 - 0.7)/1.0 = -0.4 → clamp to 0
    assert fraction == Decimal("0")


def test_wilson_95_ci_shape(calc: KellyCalculator) -> None:
    """Wilson CI: lower < p_hat < upper; width decreases with n."""
    lo, hi = calc.wilson_95_ci(p_hat=Decimal("0.55"), n=100)
    assert lo < Decimal("0.55") < hi
    lo2, hi2 = calc.wilson_95_ci(p_hat=Decimal("0.55"), n=500)
    assert (hi2 - lo2) < (hi - lo)


def test_wilson_ci_at_n200(calc: KellyCalculator) -> None:
    """At n=200, p_hat=0.55: CI per wiki = [0.481, 0.616]."""
    lo, hi = calc.wilson_95_ci(p_hat=Decimal("0.55"), n=200)
    assert abs(float(lo) - 0.481) < 0.002
    assert abs(float(hi) - 0.616) < 0.002


def test_fraction_result_is_decimal(calc: KellyCalculator) -> None:
    fraction = calc.phase_adjusted_fraction(
        trade_count=100, p_hat=Decimal("0.55"), b=Decimal("1.5")
    )
    assert isinstance(fraction, Decimal)
```

- [ ] **Step 2: Run test — verify RED**

```bash
pytest tests/unit/test_kelly.py -v
```
Expected: FAIL — `src.risk.kelly` не существует.

- [ ] **Step 3: GREEN — create `src/risk/kelly.py`**

```python
"""4-phase Kelly position sizing calculator.

Source: wiki/trading/concepts/kelly-phases.md
ADR: wiki/project/decisions/0012-4-phase-kelly-sizing.md
"""

import math
from decimal import Decimal
from typing import Literal


class KellyCalculator:
    """Stateless Kelly calculator. All state (trade_count, p_hat, b) is caller-managed.

    Phase rules (from wiki/trading/concepts/kelly-phases.md):
        Phase 1 (n<30):   fixed 1% — CLT boundary, no edge inference possible.
        Phase 2 (n<100):  fixed 2% — direction of edge plausible, not significant.
        Phase 3 (n<200):  quarter-Kelly, cap 3%.
        Phase 4 (n≥200):  half-Kelly, cap 5%.

    Wilson 95% CI formula (Agresti-Coull 1998):
        CI = [p̂ + z²/(2n) ± z·√(p̂(1−p̂)/n + z²/(4n²))] / (1 + z²/n)
        z = 1.96 for 95%.
    """

    _Z: float = 1.96  # 95% confidence

    def phase_from_trade_count(self, trade_count: int) -> Literal[1, 2, 3, 4]:
        """Map trade count to Kelly phase (1-4)."""
        if trade_count < 30:
            return 1
        if trade_count < 100:
            return 2
        if trade_count < 200:
            return 3
        return 4

    def kelly_fraction(self, *, p_hat: Decimal, b: Decimal) -> Decimal:
        """Full Kelly fraction: f* = (p*b - q) / b. Clamped to [0, 1].

        Args:
            p_hat: Estimated win probability (0 < p_hat < 1).
            b:     Payoff ratio = avg_win / avg_loss (> 0).

        Returns:
            Kelly fraction in [0, 1].
        """
        q = Decimal("1") - p_hat
        f_star = (p_hat * b - q) / b
        return max(Decimal("0"), f_star)

    def wilson_95_ci(
        self, *, p_hat: Decimal, n: int
    ) -> tuple[Decimal, Decimal]:
        """Wilson 95% confidence interval for binomial proportion.

        Formula (Agresti-Coull 1998):
            CI = [p̂ + z²/(2n) ± z·√(p̂(1−p̂)/n + z²/(4n²))] / (1 + z²/n)

        Args:
            p_hat: Observed win proportion.
            n:     Number of trials (trade_count).

        Returns:
            (lower, upper) as Decimal, both in [0, 1].
        """
        if n <= 0:
            return Decimal("0"), Decimal("1")
        p = float(p_hat)
        z = self._Z
        z2 = z * z
        denominator = 1.0 + z2 / n
        center = (p + z2 / (2 * n)) / denominator
        margin = (z / denominator) * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))
        lo = max(0.0, center - margin)
        hi = min(1.0, center + margin)
        return Decimal(str(round(lo, 6))), Decimal(str(round(hi, 6)))

    def phase_adjusted_fraction(
        self, *, trade_count: int, p_hat: Decimal, b: Decimal
    ) -> Decimal:
        """Compute phase-adjusted Kelly fraction with caps.

        Args:
            trade_count: Cumulative number of closed trades.
            p_hat:       Estimated win probability.
            b:           Payoff ratio.

        Returns:
            Fraction as Decimal. Never exceeds phase cap.
        """
        phase = self.phase_from_trade_count(trade_count)
        if phase == 1:
            return Decimal("0.01")
        if phase == 2:
            return Decimal("0.02")
        f_star = self.kelly_fraction(p_hat=p_hat, b=b)
        if phase == 3:
            return min(f_star * Decimal("0.25"), Decimal("0.03"))
        # phase == 4
        return min(f_star * Decimal("0.5"), Decimal("0.05"))
```

- [ ] **Step 4: Run tests — verify GREEN**

```bash
pytest tests/unit/test_kelly.py -v
```
Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add src/risk/kelly.py tests/unit/test_kelly.py
git commit -m "feat(risk): add KellyCalculator with 4-phase sizing and Wilson 95% CI

Phase boundaries n=29→30, 99→100, 199→200 tested.
Wilson CI: inline formula, z=1.96, no scipy dependency (Decision D3).
Source: wiki/project/plans/2026-04-23-sprint-4-risk.md §Task-6"
```

---

### Task 7: `src/risk/trade_history.py` — `TradeHistoryRepository`

**Files:**
- Create: `src/risk/trade_history.py`
- Create: `tests/unit/test_trade_history.py`

- [ ] **Step 1: RED — write trade_history tests**

Create `tests/unit/test_trade_history.py`:

```python
"""Tests for TradeHistoryRepository and TradeRecord."""

import sqlite3
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from src.platform.db import connect, init_db
from src.risk.reason_codes import ReasonCode
from src.risk.trade_history import TradeHistoryRepository, TradeRecord

MIGRATIONS_DIR = Path(__file__).parents[2] / "migrations"


@pytest.fixture()
def db(tmp_path: Path) -> sqlite3.Connection:
    db_path = tmp_path / "test.db"
    init_db(db_path, MIGRATIONS_DIR)
    return connect(db_path)


@pytest.fixture()
def repo(db: sqlite3.Connection) -> TradeHistoryRepository:
    return TradeHistoryRepository(db)


def _make_record(**overrides) -> TradeRecord:
    base = dict(
        symbol="BTCUSDT",
        entry_signal_id=str(uuid4()),
        entry_ts=datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        exit_ts=datetime(2026, 1, 1, 1, 0, 0, tzinfo=timezone.utc),
        qty=Decimal("0.001"),
        entry_price=Decimal("50000"),
        exit_price=Decimal("51000"),
        pnl_quote=Decimal("1"),
        pnl_pct=Decimal("0.02"),
        fees_paid=Decimal("0.1"),
        reason_code=ReasonCode.EXIT_TP_HIT,
        kelly_phase=1,
    )
    base.update(overrides)
    return TradeRecord(**base)


def test_insert_and_count(repo: TradeHistoryRepository) -> None:
    repo.insert(_make_record())
    assert repo.count() == 1


def test_multiple_inserts(repo: TradeHistoryRepository) -> None:
    for _ in range(5):
        repo.insert(_make_record())
    assert repo.count() == 5


def test_count_wins(repo: TradeHistoryRepository) -> None:
    repo.insert(_make_record(pnl_quote=Decimal("10")))
    repo.insert(_make_record(pnl_quote=Decimal("-5")))
    repo.insert(_make_record(pnl_quote=Decimal("3")))
    assert repo.count_wins() == 2


def test_avg_win_loss_ratio(repo: TradeHistoryRepository) -> None:
    repo.insert(_make_record(pnl_quote=Decimal("10")))
    repo.insert(_make_record(pnl_quote=Decimal("20")))
    repo.insert(_make_record(pnl_quote=Decimal("-5")))
    p_hat, b = repo.win_rate_and_payoff()
    assert abs(float(p_hat) - 2 / 3) < 1e-6
    # avg_win=15, avg_loss=5 → b=3.0
    assert abs(float(b) - 3.0) < 1e-6


def test_empty_win_rate_returns_defaults(repo: TradeHistoryRepository) -> None:
    p_hat, b = repo.win_rate_and_payoff()
    assert p_hat == Decimal("0.5")
    assert b == Decimal("1.0")


def test_kelly_phase_stored_correctly(repo: TradeHistoryRepository, db: sqlite3.Connection) -> None:
    repo.insert(_make_record(kelly_phase=3))
    row = db.execute("SELECT kelly_phase FROM trade_history").fetchone()
    assert row[0] == 3
```

- [ ] **Step 2: Run test — verify RED**

```bash
pytest tests/unit/test_trade_history.py -v
```
Expected: FAIL — `src.risk.trade_history` не существует.

- [ ] **Step 3: GREEN — create `src/risk/trade_history.py`**

```python
"""Trade history repository for Kelly statistics computation.

Source: wiki/project/plans/2026-04-23-sprint-4-risk.md §Task-7
"""

import sqlite3
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict

from src.risk.reason_codes import ReasonCode


class TradeRecord(BaseModel):
    """Single closed trade record, persisted to trade_history."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str
    entry_signal_id: str
    entry_ts: datetime
    exit_ts: datetime
    qty: Decimal
    entry_price: Decimal
    exit_price: Decimal
    pnl_quote: Decimal
    pnl_pct: Decimal
    fees_paid: Decimal
    reason_code: ReasonCode
    kelly_phase: Literal[1, 2, 3, 4]


class TradeHistoryRepository:
    """SQLite-backed trade history. All datetimes stored as ISO-8601 UTC strings."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def insert(self, record: TradeRecord) -> None:
        """Insert closed trade. Auto-assigns recorded_at = now."""
        with self._conn:
            self._conn.execute(
                "INSERT INTO trade_history "
                "(symbol, entry_signal_id, entry_ts, exit_ts, qty, entry_price, "
                "exit_price, pnl_quote, pnl_pct, fees_paid, reason_code, kelly_phase, recorded_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))",
                (
                    record.symbol,
                    record.entry_signal_id,
                    record.entry_ts.isoformat(),
                    record.exit_ts.isoformat(),
                    str(record.qty),
                    str(record.entry_price),
                    str(record.exit_price),
                    str(record.pnl_quote),
                    str(record.pnl_pct),
                    str(record.fees_paid),
                    record.reason_code,
                    record.kelly_phase,
                ),
            )

    def count(self) -> int:
        """Total number of closed trades."""
        row = self._conn.execute("SELECT COUNT(*) FROM trade_history").fetchone()
        return int(row[0])

    def count_wins(self) -> int:
        """Number of trades with pnl_quote > 0."""
        row = self._conn.execute(
            "SELECT COUNT(*) FROM trade_history WHERE CAST(pnl_quote AS REAL) > 0"
        ).fetchone()
        return int(row[0])

    def win_rate_and_payoff(self) -> tuple[Decimal, Decimal]:
        """Compute (p_hat, b) for Kelly formula from all trades.

        Returns (0.5, 1.0) if no trades (conservative defaults).
        """
        n = self.count()
        if n == 0:
            return Decimal("0.5"), Decimal("1.0")
        wins = self.count_wins()
        p_hat = Decimal(wins) / Decimal(n)
        # avg_win and avg_loss
        row_w = self._conn.execute(
            "SELECT AVG(CAST(pnl_quote AS REAL)) FROM trade_history "
            "WHERE CAST(pnl_quote AS REAL) > 0"
        ).fetchone()
        row_l = self._conn.execute(
            "SELECT AVG(ABS(CAST(pnl_quote AS REAL))) FROM trade_history "
            "WHERE CAST(pnl_quote AS REAL) < 0"
        ).fetchone()
        avg_win = Decimal(str(row_w[0])) if row_w[0] is not None else Decimal("0")
        avg_loss = Decimal(str(row_l[0])) if row_l[0] is not None else Decimal("1")
        if avg_loss == Decimal("0"):
            avg_loss = Decimal("1")
        b = avg_win / avg_loss
        return p_hat, b
```

- [ ] **Step 4: Run tests — verify GREEN**

```bash
pytest tests/unit/test_trade_history.py -v
```
Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add src/risk/trade_history.py tests/unit/test_trade_history.py
git commit -m "feat(risk): add TradeHistoryRepository + TradeRecord

Stores closed trades in trade_history table; computes p_hat and b
for Kelly formula from pnl_quote statistics.
Source: wiki/project/plans/2026-04-23-sprint-4-risk.md §Task-7"
```

---

### Task 8: `src/risk/equity_tracker.py` — `EquityTracker`

**Files:**
- Create: `src/risk/equity_tracker.py`
- Create: `tests/unit/test_equity_tracker.py`

- [ ] **Step 1: RED — write equity_tracker tests**

Create `tests/unit/test_equity_tracker.py`:

```python
"""Tests for EquityTracker — snapshots, 24h HWM, drawdown."""

import sqlite3
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from src.platform.db import connect, init_db
from src.risk.equity_tracker import EquityTracker

MIGRATIONS_DIR = Path(__file__).parents[2] / "migrations"


@pytest.fixture()
def db(tmp_path: Path) -> sqlite3.Connection:
    db_path = tmp_path / "test.db"
    init_db(db_path, MIGRATIONS_DIR)
    return connect(db_path)


@pytest.fixture()
def tracker(db: sqlite3.Connection) -> EquityTracker:
    return EquityTracker(db)


def test_snapshot_inserted(tracker: EquityTracker, db: sqlite3.Connection) -> None:
    ts = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    tracker.snapshot(
        realized=Decimal("10000"),
        unrealized=Decimal("200"),
        ts=ts,
        source="BAR_CLOSE",
    )
    row = db.execute("SELECT COUNT(*) FROM equity_snapshots").fetchone()
    assert row[0] == 1


def test_total_equity_computed(tracker: EquityTracker, db: sqlite3.Connection) -> None:
    ts = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    tracker.snapshot(
        realized=Decimal("9800"),
        unrealized=Decimal("300"),
        ts=ts,
        source="POSITION_CLOSE",
    )
    row = db.execute("SELECT total_equity FROM equity_snapshots").fetchone()
    assert Decimal(row[0]) == Decimal("10100")


def test_hwm_24h(tracker: EquityTracker) -> None:
    """24h HWM returns max total_equity in the last 24 hours."""
    base_ts = datetime(2026, 1, 2, 12, 0, 0, tzinfo=timezone.utc)
    # Insert three snapshots within 24h
    for i, equity in enumerate([10000, 11000, 9000]):
        tracker.snapshot(
            realized=Decimal(str(equity)),
            unrealized=Decimal("0"),
            ts=base_ts - timedelta(hours=i),
            source="BAR_CLOSE",
        )
    # Insert one > 24h ago — should not count
    tracker.snapshot(
        realized=Decimal("15000"),
        unrealized=Decimal("0"),
        ts=base_ts - timedelta(hours=25),
        source="BAR_CLOSE",
    )
    hwm = tracker.hwm_24h(reference_ts=base_ts)
    assert hwm == Decimal("11000")


def test_current_drawdown_pct(tracker: EquityTracker) -> None:
    """dd_pct = (peak - current) / peak."""
    dd = tracker.drawdown_pct(peak=Decimal("10000"), current=Decimal("8500"))
    assert dd == Decimal("0.15")


def test_current_drawdown_zero_at_hwm(tracker: EquityTracker) -> None:
    dd = tracker.drawdown_pct(peak=Decimal("10000"), current=Decimal("10000"))
    assert dd == Decimal("0")


def test_latest_total_equity_none_when_empty(tracker: EquityTracker) -> None:
    assert tracker.latest_total_equity() is None


def test_latest_total_equity(tracker: EquityTracker) -> None:
    ts1 = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    ts2 = datetime(2026, 1, 1, 11, 0, 0, tzinfo=timezone.utc)
    tracker.snapshot(realized=Decimal("10000"), unrealized=Decimal("0"), ts=ts1, source="BAR_CLOSE")
    tracker.snapshot(realized=Decimal("10500"), unrealized=Decimal("0"), ts=ts2, source="BAR_CLOSE")
    assert tracker.latest_total_equity() == Decimal("10500")
```

- [ ] **Step 2: Run test — verify RED**

```bash
pytest tests/unit/test_equity_tracker.py -v
```
Expected: FAIL.

- [ ] **Step 3: GREEN — create `src/risk/equity_tracker.py`**

```python
"""Equity snapshot tracker with 24h high-water mark.

Source: wiki/trading/concepts/circuit-breakers.md — 24h HWM base.
wiki/project/plans/2026-04-23-sprint-4-risk.md §Task-8
"""

import sqlite3
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Literal

SnapshotSource = Literal["BAR_CLOSE", "POSITION_CLOSE", "MANUAL"]


class EquityTracker:
    """Persists equity snapshots and computes rolling 24h high-water mark."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def snapshot(
        self,
        *,
        realized: Decimal,
        unrealized: Decimal,
        ts: datetime,
        source: SnapshotSource,
    ) -> None:
        """Insert equity snapshot. total_equity = realized + unrealized."""
        total = realized + unrealized
        with self._conn:
            self._conn.execute(
                "INSERT INTO equity_snapshots "
                "(ts, realized_equity, unrealized_pnl, total_equity, source) "
                "VALUES (?,?,?,?,?)",
                (
                    ts.isoformat(),
                    str(realized),
                    str(unrealized),
                    str(total),
                    source,
                ),
            )

    def hwm_24h(self, *, reference_ts: datetime) -> Decimal | None:
        """Max total_equity in (reference_ts - 24h, reference_ts].

        Returns None if no snapshots in window.
        """
        cutoff = (reference_ts - timedelta(hours=24)).isoformat()
        ref = reference_ts.isoformat()
        row = self._conn.execute(
            "SELECT MAX(CAST(total_equity AS REAL)) FROM equity_snapshots "
            "WHERE ts >= ? AND ts <= ?",
            (cutoff, ref),
        ).fetchone()
        if row[0] is None:
            return None
        return Decimal(str(row[0]))

    def latest_total_equity(self) -> Decimal | None:
        """Most recent total_equity snapshot. None if no snapshots."""
        row = self._conn.execute(
            "SELECT total_equity FROM equity_snapshots ORDER BY ts DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return None
        return Decimal(row[0])

    @staticmethod
    def drawdown_pct(*, peak: Decimal, current: Decimal) -> Decimal:
        """dd_pct = (peak - current) / peak. Returns 0 if peak <= 0."""
        if peak <= Decimal("0"):
            return Decimal("0")
        return (peak - current) / peak
```

- [ ] **Step 4: Run tests — verify GREEN**

```bash
pytest tests/unit/test_equity_tracker.py -v
```
Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add src/risk/equity_tracker.py tests/unit/test_equity_tracker.py
git commit -m "feat(risk): add EquityTracker with 24h HWM rolling query

Snapshots persisted to equity_snapshots; 24h HWM via MAX(total_equity)
query with ts range filter per circuit-breakers.md spec.
Source: wiki/project/plans/2026-04-23-sprint-4-risk.md §Task-8"
```

---

→ Continue: [Tasks 9-17](2026-04-23-sprint-4-risk-tasks-9-17.md)
