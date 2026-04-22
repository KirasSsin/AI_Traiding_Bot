---
title: Sprint 4 — Risk & Circuit Breakers — Tasks 9-13
type: plan-part
tags: [plan, sprint-4, risk, kelly, circuit-breakers, tdd]
created: 2026-04-23
updated: 2026-04-23
status: ready-to-execute
part: 2 of 3
parent: 2026-04-23-sprint-4-risk.md
sources:
  - project/architecture/migration-plan.md §S4
  - project/decisions/0012-4-phase-kelly-sizing.md
  - project/decisions/0013-circuit-breakers-l1-l2-l3-flash.md
  - trading/concepts/kelly-phases.md
  - trading/concepts/circuit-breakers.md
---

# Sprint 4 — Tasks 9-13

> **Index:** [2026-04-23-sprint-4-risk.md](2026-04-23-sprint-4-risk.md)

---

### Task 9: `src/risk/circuit_breakers.py` — `CircuitBreakerDetector`

**Files:**
- Create: `src/risk/circuit_breakers.py`
- Create: `tests/unit/test_circuit_breakers.py`

- [ ] **Step 1: RED — write circuit_breakers tests**

Create `tests/unit/test_circuit_breakers.py`:

```python
"""Tests for CircuitBreakerDetector — L1/L2/L3 drawdown + flash."""

from decimal import Decimal

import pytest

from src.platform.config import Settings
from src.risk.circuit_breakers import CircuitBreakerDetector
from src.risk.models import HaltState


@pytest.fixture()
def settings(tmp_path) -> Settings:
    return Settings(
        data_dir=tmp_path / "data",
        log_dir=tmp_path / "logs",
        db_path=tmp_path / "bot.db",
        parquet_dir=tmp_path / "parquet",
        risk_override_path=tmp_path / "state" / "cb_override.json",
    )


@pytest.fixture()
def detector(settings: Settings) -> CircuitBreakerDetector:
    return CircuitBreakerDetector(settings=settings)


# --- Drawdown level tests ---

def test_no_halt_below_l1(detector: CircuitBreakerDetector) -> None:
    state = detector.check_drawdown(peak=Decimal("10000"), current=Decimal("8600"))
    # dd_pct = 0.14 < 0.15 → L0
    assert state == HaltState.L0


def test_l1_triggers_at_threshold(detector: CircuitBreakerDetector) -> None:
    # dd_pct = 0.151 → L1
    state = detector.check_drawdown(peak=Decimal("10000"), current=Decimal("8490"))
    assert state == HaltState.L1


def test_l2_triggers_at_threshold(detector: CircuitBreakerDetector) -> None:
    # dd_pct = 0.221 → L2
    state = detector.check_drawdown(peak=Decimal("10000"), current=Decimal("7790"))
    assert state == HaltState.L2


def test_l3_triggers_at_threshold(detector: CircuitBreakerDetector) -> None:
    # dd_pct = 0.301 → L3
    state = detector.check_drawdown(peak=Decimal("10000"), current=Decimal("6990"))
    assert state == HaltState.L3


def test_fixture_equity_curves(detector: CircuitBreakerDetector) -> None:
    """AC: CB L1/L2/L3 trigger on fixture DD 15.1%/22.1%/30.1%."""
    assert detector.check_drawdown(Decimal("10000"), Decimal("8490")) == HaltState.L1
    assert detector.check_drawdown(Decimal("10000"), Decimal("7790")) == HaltState.L2
    assert detector.check_drawdown(Decimal("10000"), Decimal("6990")) == HaltState.L3


def test_l3_returned_when_exceeds_all(detector: CircuitBreakerDetector) -> None:
    """L3 takes precedence (worst case)."""
    state = detector.check_drawdown(peak=Decimal("10000"), current=Decimal("5000"))
    assert state == HaltState.L3


# --- Flash crash tests ---

def test_no_flash_normal_bar(detector: CircuitBreakerDetector) -> None:
    # bar move = 1%, atr = 3% → threshold = max(8%, 9%) = 9%; 1% < 9% → no flash
    result = detector.check_flash(
        bar_close=Decimal("50500"),
        prev_close=Decimal("50000"),
        atr=Decimal("1500"),  # 3% of price
    )
    assert result is False


def test_flash_abs_threshold(detector: CircuitBreakerDetector) -> None:
    """10% single-bar move → FLASH (exceeds absolute 8% floor)."""
    result = detector.check_flash(
        bar_close=Decimal("45000"),
        prev_close=Decimal("50000"),
        atr=Decimal("100"),  # tiny ATR → threshold = max(8%, ~0.6%) = 8%
    )
    assert result is True


def test_flash_atr_threshold(detector: CircuitBreakerDetector) -> None:
    """3*ATR threshold when > 8%."""
    # atr = 4000 = 8% of 50000 → 3*ATR/prev = 24% → threshold = max(8%, 24%) = 24%
    # bar move = 25% → flash
    result = detector.check_flash(
        bar_close=Decimal("37500"),
        prev_close=Decimal("50000"),
        atr=Decimal("4000"),
    )
    assert result is True


def test_flash_just_below_abs_threshold(detector: CircuitBreakerDetector) -> None:
    # 7.9% move, tiny ATR
    result = detector.check_flash(
        bar_close=Decimal("46050"),
        prev_close=Decimal("50000"),
        atr=Decimal("10"),
    )
    assert result is False


def test_halt_state_from_flash(detector: CircuitBreakerDetector) -> None:
    """check_flash_state returns HaltState.FLASH or HaltState.L0."""
    flash_state = detector.check_flash_state(
        bar_close=Decimal("45000"),
        prev_close=Decimal("50000"),
        atr=Decimal("100"),
    )
    assert flash_state == HaltState.FLASH

    no_flash = detector.check_flash_state(
        bar_close=Decimal("50500"),
        prev_close=Decimal("50000"),
        atr=Decimal("100"),
    )
    assert no_flash == HaltState.L0
```

- [ ] **Step 2: Run test — verify RED**

```bash
pytest tests/unit/test_circuit_breakers.py -v
```
Expected: FAIL.

- [ ] **Step 3: GREEN — create `src/risk/circuit_breakers.py`**

```python
"""Circuit breaker detection — pure functions, no I/O, no state.

Source: wiki/trading/concepts/circuit-breakers.md
ADR: wiki/project/decisions/0013-circuit-breakers-l1-l2-l3-flash.md
"""

from decimal import Decimal

from src.platform.config import Settings
from src.risk.models import HaltState


class CircuitBreakerDetector:
    """Detects drawdown levels and flash crashes. Stateless — caller manages state."""

    def __init__(self, *, settings: Settings) -> None:
        self._l1 = settings.risk_cb_l1_dd
        self._l2 = settings.risk_cb_l2_dd
        self._l3 = settings.risk_cb_l3_dd
        self._flash_abs = settings.risk_cb_flash_abs
        self._flash_atr_mult = settings.risk_cb_flash_atr_mult

    def check_drawdown(self, peak: Decimal, current: Decimal) -> HaltState:
        """Return halt level based on drawdown from peak.

        dd_pct = (peak - current) / peak.
        Levels: L3 ≥ L2 ≥ L1 ≥ L0. Returns worst applicable level.

        Args:
            peak:    Peak equity (24h HWM).
            current: Current total equity.

        Returns:
            HaltState: L0 (no halt), L1, L2, or L3.
        """
        if peak <= Decimal("0"):
            return HaltState.L0
        dd = (peak - current) / peak
        if dd >= self._l3:
            return HaltState.L3
        if dd >= self._l2:
            return HaltState.L2
        if dd >= self._l1:
            return HaltState.L1
        return HaltState.L0

    def check_flash(
        self,
        *,
        bar_close: Decimal,
        prev_close: Decimal,
        atr: Decimal,
    ) -> bool:
        """Detect flash crash: single-bar return exceeds max(flash_abs, flash_atr_mult * ATR/prev).

        Uses close-to-close (not intrabar ticks) per wiki spec.

        Args:
            bar_close:  Closing price of current bar.
            prev_close: Closing price of previous bar.
            atr:        Current ATR in quote currency.

        Returns:
            True if flash crash detected.
        """
        if prev_close <= Decimal("0"):
            return False
        delta_pct = abs(bar_close - prev_close) / prev_close
        atr_threshold = self._flash_atr_mult * atr / prev_close
        threshold = max(self._flash_abs, atr_threshold)
        return delta_pct > threshold

    def check_flash_state(
        self,
        *,
        bar_close: Decimal,
        prev_close: Decimal,
        atr: Decimal,
    ) -> HaltState:
        """Return HaltState.FLASH if flash detected, else HaltState.L0."""
        if self.check_flash(bar_close=bar_close, prev_close=prev_close, atr=atr):
            return HaltState.FLASH
        return HaltState.L0
```

- [ ] **Step 4: Run tests — verify GREEN**

```bash
pytest tests/unit/test_circuit_breakers.py -v
```
Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add src/risk/circuit_breakers.py tests/unit/test_circuit_breakers.py
git commit -m "feat(risk): add CircuitBreakerDetector (L1/L2/L3 + flash)

Drawdown levels: 15%/22%/30% per wiki/trading/concepts/circuit-breakers.md.
Flash: max(8%, 3*ATR/prev_close) close-to-close detection.
Source: wiki/project/plans/2026-04-23-sprint-4-risk.md §Task-9"
```

---

### Task 10: `src/risk/override.py` — `OverrideStore`

**Files:**
- Create: `src/risk/override.py`
- Create: `tests/unit/test_override.py`

- [ ] **Step 1: RED — write override tests**

Create `tests/unit/test_override.py`:

```python
"""Tests for OverrideStore — write/read/consume with config_hash binding."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.risk.models import HaltState
from src.risk.override import ConsumedOverrideError, ExpiredOverrideError, OverrideStore


@pytest.fixture()
def store(tmp_path: Path) -> OverrideStore:
    override_path = tmp_path / "state" / "cb_override.json"
    return OverrideStore(override_path=override_path)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def test_write_creates_file(store: OverrideStore, tmp_path: Path) -> None:
    store.write(
        level=HaltState.L2,
        reason="test resume",
        config_hash="abc123",
        clock=_now,
    )
    path = tmp_path / "state" / "cb_override.json"
    assert path.exists()


def test_read_returns_override(store: OverrideStore) -> None:
    store.write(
        level=HaltState.L2,
        reason="manual resume after reconciliation",
        config_hash="abc123",
        clock=_now,
    )
    override = store.read(config_hash="abc123", clock=_now)
    assert override["level"] == "L2"
    assert override["reason"] == "manual resume after reconciliation"


def test_config_hash_mismatch_raises(store: OverrideStore) -> None:
    store.write(
        level=HaltState.L2,
        reason="test",
        config_hash="original_hash",
        clock=_now,
    )
    with pytest.raises(ValueError, match="config_hash mismatch"):
        store.read(config_hash="different_hash", clock=_now)


def test_consume_renames_file(store: OverrideStore, tmp_path: Path) -> None:
    store.write(level=HaltState.L2, reason="test", config_hash="h1", clock=_now)
    store.consume(config_hash="h1", clock=_now)
    override_path = tmp_path / "state" / "cb_override.json"
    consumed_path = tmp_path / "state" / "cb_override.consumed.json"
    assert not override_path.exists()
    assert consumed_path.exists()


def test_double_consume_raises(store: OverrideStore) -> None:
    store.write(level=HaltState.L2, reason="test", config_hash="h1", clock=_now)
    store.consume(config_hash="h1", clock=_now)
    with pytest.raises(ConsumedOverrideError):
        store.consume(config_hash="h1", clock=_now)


def test_expired_override_raises(store: OverrideStore) -> None:
    past = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    store.write(
        level=HaltState.L2,
        reason="test",
        config_hash="h1",
        clock=lambda: past,
        expires_in=timedelta(hours=1),
    )
    # Read from "now" which is after expiry
    future = datetime(2026, 1, 1, 2, 0, 0, tzinfo=timezone.utc)
    with pytest.raises(ExpiredOverrideError):
        store.read(config_hash="h1", clock=lambda: future)


def test_default_expires_in_1h(store: OverrideStore) -> None:
    t0 = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    store.write(level=HaltState.L2, reason="test", config_hash="h1", clock=lambda: t0)
    override = store.read(config_hash="h1", clock=lambda: t0)
    assert override["expires_at"] is not None
    # Parse and check it's 1h after created_at
    from datetime import datetime as dt
    expires_at = dt.fromisoformat(override["expires_at"])
    created_at = dt.fromisoformat(override["created_at"])
    assert (expires_at - created_at).total_seconds() == 3600


def test_no_override_returns_none(store: OverrideStore) -> None:
    result = store.peek()
    assert result is None
```

- [ ] **Step 2: Run test — verify RED**

```bash
pytest tests/unit/test_override.py -v
```
Expected: FAIL.

- [ ] **Step 3: GREEN — create `src/risk/override.py`**

```python
"""Circuit breaker manual override file store.

CLI writes cb_override.json; RiskManager reads+consumes it on resume.
Config hash binding prevents stale overrides after config changes.

Source: wiki/project/plans/2026-04-23-sprint-4-risk.md §Q3
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from src.risk.models import HaltState


class ConsumedOverrideError(Exception):
    """Override already consumed (renamed to .consumed.json)."""


class ExpiredOverrideError(Exception):
    """Override exists but is past its expires_at timestamp."""


class OverrideStore:
    """File-backed store for manual circuit breaker resume overrides."""

    _DEFAULT_EXPIRES_IN = timedelta(hours=1)

    def __init__(self, *, override_path: Path) -> None:
        self._path = override_path
        self._consumed_path = override_path.with_suffix(".consumed.json")

    def write(
        self,
        *,
        level: HaltState,
        reason: str,
        config_hash: str,
        clock: Callable[[], datetime],
        expires_in: timedelta = _DEFAULT_EXPIRES_IN,
    ) -> None:
        """Write override file. Creates parent directories if needed."""
        now = clock()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "level": str(level),
            "reason": reason,
            "config_hash": config_hash,
            "created_at": now.isoformat(),
            "expires_at": (now + expires_in).isoformat(),
        }
        self._path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def read(
        self,
        *,
        config_hash: str,
        clock: Callable[[], datetime],
    ) -> dict:
        """Read and validate override. Raises on hash mismatch or expiry.

        Does NOT consume (rename) the file — call consume() separately.
        """
        if self._consumed_path.exists() and not self._path.exists():
            raise ConsumedOverrideError("Override already consumed")
        if not self._path.exists():
            raise FileNotFoundError(f"No override file at {self._path}")
        payload = json.loads(self._path.read_text(encoding="utf-8"))
        if payload.get("config_hash") != config_hash:
            raise ValueError(
                f"config_hash mismatch: override has {payload.get('config_hash')!r}, "
                f"expected {config_hash!r}"
            )
        now = clock()
        if payload.get("expires_at"):
            expires_at = datetime.fromisoformat(payload["expires_at"])
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if now > expires_at:
                raise ExpiredOverrideError(
                    f"Override expired at {payload['expires_at']}"
                )
        return payload

    def consume(
        self,
        *,
        config_hash: str,
        clock: Callable[[], datetime],
    ) -> dict:
        """Read, validate, then rename file to .consumed.json."""
        if not self._path.exists():
            raise ConsumedOverrideError(
                f"Override file not found (already consumed?): {self._path}"
            )
        payload = self.read(config_hash=config_hash, clock=clock)
        self._path.rename(self._consumed_path)
        return payload

    def peek(self) -> dict | None:
        """Return raw override dict if file exists, without validation. None otherwise."""
        if not self._path.exists():
            return None
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
```

- [ ] **Step 4: Run tests — verify GREEN**

```bash
pytest tests/unit/test_override.py -v
```
Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add src/risk/override.py tests/unit/test_override.py
git commit -m "feat(risk): add OverrideStore for manual CB resume

File-backed cb_override.json with config_hash binding.
Consume → rename to .consumed.json; expiry after 1h default.
Source: wiki/project/plans/2026-04-23-sprint-4-risk.md §Task-10"
```

---

### Task 11: `src/risk/state_repo.py` — JSON kv adapter for `state` table

**Files:**
- Create: `src/risk/state_repo.py`
- Create: `tests/unit/test_state_repo.py`

- [ ] **Step 1: RED — write state_repo tests**

Create `tests/unit/test_state_repo.py`:

```python
"""Tests for StateRepo — JSON kv adapter for the 'state' SQLite table."""

import sqlite3
from pathlib import Path

import pytest

from src.platform.db import connect, init_db
from src.risk.state_repo import StateRepo

MIGRATIONS_DIR = Path(__file__).parents[2] / "migrations"


@pytest.fixture()
def db(tmp_path: Path) -> sqlite3.Connection:
    db_path = tmp_path / "test.db"
    init_db(db_path, MIGRATIONS_DIR)
    return connect(db_path)


@pytest.fixture()
def repo(db: sqlite3.Connection) -> StateRepo:
    return StateRepo(db)


def test_get_missing_key_returns_none(repo: StateRepo) -> None:
    assert repo.get("risk:cb:current_level") is None


def test_set_and_get(repo: StateRepo) -> None:
    repo.set("risk:kelly:phase", {"phase": 1, "trade_count": 0})
    result = repo.get("risk:kelly:phase")
    assert result == {"phase": 1, "trade_count": 0}


def test_overwrite_existing_key(repo: StateRepo) -> None:
    repo.set("risk:kelly:phase", {"phase": 1})
    repo.set("risk:kelly:phase", {"phase": 2})
    result = repo.get("risk:kelly:phase")
    assert result == {"phase": 2}


def test_update_many_atomic(repo: StateRepo, db: sqlite3.Connection) -> None:
    """update_many writes all keys in single transaction."""
    updates = {
        "risk:cb:current_level": {"level": "L1", "dd_pct": 0.16},
        "risk:kelly:phase": {"phase": 2, "trade_count": 35},
        "risk:kelly:params": {"p_hat": 0.55, "b": 1.5},
    }
    repo.update_many(updates)
    for key, expected in updates.items():
        assert repo.get(key) == expected


def test_delete_key(repo: StateRepo) -> None:
    repo.set("risk:cb:current_level", {"level": "L0"})
    repo.delete("risk:cb:current_level")
    assert repo.get("risk:cb:current_level") is None


def test_nested_json_preserved(repo: StateRepo) -> None:
    payload = {
        "level": "L2",
        "triggered_at": "2026-01-01T00:00:00+00:00",
        "peak_equity": "10500.00",
        "dd_pct": "0.221",
    }
    repo.set("risk:cb:current_level", payload)
    assert repo.get("risk:cb:current_level") == payload
```

- [ ] **Step 2: Run test — verify RED**

```bash
pytest tests/unit/test_state_repo.py -v
```
Expected: FAIL.

- [ ] **Step 3: GREEN — create `src/risk/state_repo.py`**

```python
"""JSON key-value adapter for the 'state' SQLite table.

Reuses the 'state' table from migrations/001_initial.sql.
All values stored as JSON strings.

Source: wiki/project/plans/2026-04-23-sprint-4-risk.md §Task-11
"""

import json
import sqlite3
from typing import Any


class StateRepo:
    """Thin kv wrapper over the 'state' table. Values are JSON-serializable dicts."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def get(self, key: str) -> Any | None:
        """Return parsed JSON value for key, or None if not found."""
        row = self._conn.execute(
            "SELECT value_json FROM state WHERE key = ?", (key,)
        ).fetchone()
        if row is None:
            return None
        return json.loads(row[0])

    def set(self, key: str, value: Any) -> None:
        """Upsert key with JSON-serialized value. Updates updated_at."""
        with self._conn:
            self._conn.execute(
                "INSERT INTO state (key, value_json, updated_at) VALUES (?, ?, datetime('now')) "
                "ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, updated_at=datetime('now')",
                (key, json.dumps(value)),
            )

    def delete(self, key: str) -> None:
        """Remove key from state table."""
        with self._conn:
            self._conn.execute("DELETE FROM state WHERE key = ?", (key,))

    def update_many(self, updates: dict[str, Any]) -> None:
        """Atomic batch update — all keys written in single transaction."""
        with self._conn:
            for key, value in updates.items():
                self._conn.execute(
                    "INSERT INTO state (key, value_json, updated_at) VALUES (?, ?, datetime('now')) "
                    "ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, updated_at=datetime('now')",
                    (key, json.dumps(value)),
                )
```

- [ ] **Step 4: Run tests — verify GREEN**

```bash
pytest tests/unit/test_state_repo.py -v
```
Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add src/risk/state_repo.py tests/unit/test_state_repo.py
git commit -m "feat(risk): add StateRepo JSON kv adapter for state table

Atomic update_many() for Kelly phase + equity snapshot + CB level
in single transaction per risk manager requirements.
Source: wiki/project/plans/2026-04-23-sprint-4-risk.md §Task-11"
```

---

### Task 12: `src/risk/manager.py` — `RiskManager` orchestrator

**Files:**
- Create: `src/risk/manager.py`
- Create: `tests/unit/test_risk_manager.py`

- [ ] **Step 1: RED — write risk_manager unit tests**

Create `tests/unit/test_risk_manager.py`:

```python
"""Unit tests for RiskManager orchestrator."""

import sqlite3
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from src.platform.config import Settings
from src.platform.db import connect, init_db
from src.risk.manager import RiskManager
from src.risk.models import HaltState, RiskAssessment
from src.risk.reason_codes import ReasonCode
from src.signalgen.models import Signal, SignalSide

MIGRATIONS_DIR = Path(__file__).parents[2] / "migrations"


@pytest.fixture()
def settings(tmp_path: Path) -> Settings:
    return Settings(
        data_dir=tmp_path / "data",
        log_dir=tmp_path / "logs",
        db_path=tmp_path / "bot.db",
        parquet_dir=tmp_path / "parquet",
        risk_override_path=tmp_path / "state" / "cb_override.json",
    )


@pytest.fixture()
def db(tmp_path: Path, settings: Settings) -> sqlite3.Connection:
    init_db(settings.db_path, MIGRATIONS_DIR)
    return connect(settings.db_path)


@pytest.fixture()
def manager(settings: Settings, db: sqlite3.Connection) -> RiskManager:
    return RiskManager(
        settings=settings,
        conn=db,
        clock=lambda: datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
    )


def _make_signal(ts: datetime | None = None) -> Signal:
    t = ts or datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    return Signal(
        signal_id=uuid4(),
        symbol="BTCUSDT",
        side=SignalSide.LONG,
        bar_close_time=t,
        generated_at=t,
        ema_fast=Decimal("50100"),
        ema_slow=Decimal("50000"),
        adx_14=Decimal("30"),
        plus_di_14=Decimal("28"),
        minus_di_14=Decimal("18"),
        rsi_14=Decimal("45"),
        atr_14=Decimal("500"),
        reason="EMA cross confirmed",
    )


def test_assess_no_equity_returns_rejected(manager: RiskManager) -> None:
    """No equity snapshot → reject with REJECT_RISK_EXCEEDED."""
    signal = _make_signal()
    result = manager.assess(signal, mark_price=Decimal("50000"))
    assert isinstance(result, RiskAssessment)
    assert result.approved is False


def test_assess_approved_after_equity_update(manager: RiskManager) -> None:
    ts = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    manager.update_equity(realized=Decimal("10000"), unrealized=Decimal("0"), ts=ts)
    signal = _make_signal(ts=ts)
    result = manager.assess(signal, mark_price=Decimal("50000"))
    assert isinstance(result, RiskAssessment)
    assert result.signal_id == signal.signal_id


def test_update_equity_persists_snapshot(manager: RiskManager, db: sqlite3.Connection) -> None:
    ts = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    manager.update_equity(realized=Decimal("10000"), unrealized=Decimal("500"), ts=ts)
    row = db.execute("SELECT total_equity FROM equity_snapshots").fetchone()
    assert row is not None
    assert Decimal(row[0]) == Decimal("10500")


def test_halt_l1_reduces_approval(manager: RiskManager) -> None:
    """L1 halt: signal still approved but with de-levered qty."""
    ts = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    # Set equity with 16% drawdown → L1
    manager.update_equity(realized=Decimal("8400"), unrealized=Decimal("0"), ts=ts)
    # Manually set peak via state
    manager._state_repo.set(
        "risk:cb:current_level",
        {"level": "L1", "triggered_at": ts.isoformat(), "peak_equity": "10000", "dd_pct": "0.16"},
    )
    signal = _make_signal(ts=ts)
    result = manager.assess(signal, mark_price=Decimal("50000"))
    assert result.halt_state == HaltState.L1


def test_halt_l2_rejects_signal(manager: RiskManager) -> None:
    """L2 halt: signal rejected."""
    ts = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    manager.update_equity(realized=Decimal("7800"), unrealized=Decimal("0"), ts=ts)
    manager._state_repo.set(
        "risk:cb:current_level",
        {"level": "L2", "triggered_at": ts.isoformat(), "peak_equity": "10000", "dd_pct": "0.22"},
    )
    signal = _make_signal(ts=ts)
    result = manager.assess(signal, mark_price=Decimal("50000"))
    assert result.approved is False
    assert result.reason_code == ReasonCode.HALT_DRAWDOWN_L2


def test_halt_l3_rejects_signal(manager: RiskManager) -> None:
    ts = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    manager._state_repo.set(
        "risk:cb:current_level",
        {"level": "L3", "triggered_at": ts.isoformat(), "peak_equity": "10000", "dd_pct": "0.31"},
    )
    signal = _make_signal(ts=ts)
    result = manager.assess(signal, mark_price=Decimal("50000"))
    assert result.approved is False
    assert result.reason_code == ReasonCode.HALT_DRAWDOWN_L3


def test_kelly_phase_returned_in_assessment(manager: RiskManager) -> None:
    ts = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    manager.update_equity(realized=Decimal("10000"), unrealized=Decimal("0"), ts=ts)
    signal = _make_signal(ts=ts)
    result = manager.assess(signal, mark_price=Decimal("50000"))
    # 0 trades → phase 1
    assert result.kelly_phase == 1
    assert result.kelly_fraction == Decimal("0.01")


def test_sl_tp_computed(manager: RiskManager) -> None:
    ts = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    manager.update_equity(realized=Decimal("10000"), unrealized=Decimal("0"), ts=ts)
    signal = _make_signal(ts=ts)
    mark = Decimal("50000")
    result = manager.assess(signal, mark_price=mark)
    # sl = mark - 1.5 * atr_14 = 50000 - 750 = 49250
    # tp = mark + 3.0 * atr_14 = 50000 + 1500 = 51500
    assert result.sl_price == mark - Decimal("1.5") * signal.atr_14
    assert result.tp_price == mark + Decimal("3.0") * signal.atr_14


def test_assess_uses_data_not_newer_than_signal(manager: RiskManager) -> None:
    """Look-ahead safety: assess() only uses data with ts <= signal.generated_at."""
    # Insert future snapshot — should not affect assessment
    future = datetime(2026, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
    manager.update_equity(realized=Decimal("10000"), unrealized=Decimal("0"), ts=future)
    past = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    signal = _make_signal(ts=past)
    # With clock fixed to past, should find no equity snapshot ≤ signal.generated_at
    result = manager.assess(signal, mark_price=Decimal("50000"))
    # No equity at or before signal.generated_at → rejected
    assert result.approved is False
```

- [ ] **Step 2: Run test — verify RED**

```bash
pytest tests/unit/test_risk_manager.py -v
```
Expected: FAIL — `src.risk.manager` не существует.

- [ ] **Step 3: GREEN — create `src/risk/manager.py`**

```python
"""RiskManager orchestrator — composites all S4 risk components.

Source: wiki/project/plans/2026-04-23-sprint-4-risk.md §Q2
"""

import logging
import sqlite3
from datetime import datetime
from decimal import Decimal
from typing import Callable

from src.platform.config import Settings
from src.risk.circuit_breakers import CircuitBreakerDetector
from src.risk.equity_tracker import EquityTracker
from src.risk.kelly import KellyCalculator
from src.risk.models import HaltState, RiskAssessment
from src.risk.reason_codes import ReasonCode
from src.risk.sizing import compute_qty
from src.risk.state_repo import StateRepo
from src.risk.trade_history import TradeHistoryRepository
from src.signalgen.models import Signal

logger = logging.getLogger(__name__)

_CB_KEY = "risk:cb:current_level"
_KELLY_PHASE_KEY = "risk:kelly:phase"
_KELLY_PARAMS_KEY = "risk:kelly:params"


class RiskManager:
    """Orchestrates Kelly sizing, CB detection, and state persistence.

    Deterministic: clock injected, no datetime.now() in domain logic.
    """

    def __init__(
        self,
        *,
        settings: Settings,
        conn: sqlite3.Connection,
        clock: Callable[[], datetime],
    ) -> None:
        self._settings = settings
        self._conn = conn
        self._clock = clock
        self._state_repo = StateRepo(conn)
        self._equity_tracker = EquityTracker(conn)
        self._trade_repo = TradeHistoryRepository(conn)
        self._kelly = KellyCalculator()
        self._cb_detector = CircuitBreakerDetector(settings=settings)

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def update_equity(
        self, *, realized: Decimal, unrealized: Decimal, ts: datetime
    ) -> None:
        """Persist equity snapshot and refresh CB state atomically."""
        self._equity_tracker.snapshot(
            realized=realized,
            unrealized=unrealized,
            ts=ts,
            source="POSITION_CLOSE",
        )
        self._refresh_cb_state(current=realized + unrealized, ts=ts)

    def assess(self, signal: Signal, *, mark_price: Decimal) -> RiskAssessment:
        """Evaluate signal against current risk state. Returns frozen RiskAssessment.

        Look-ahead safety: only uses equity data with ts <= signal.generated_at.
        """
        now = self._clock()
        trade_count = self._trade_repo.count()
        p_hat, b = self._trade_repo.win_rate_and_payoff()
        phase = self._kelly.phase_from_trade_count(trade_count)
        fraction = self._kelly.phase_adjusted_fraction(
            trade_count=trade_count, p_hat=p_hat, b=b
        )

        # Look-ahead-safe equity: only use snapshots up to signal.generated_at
        equity = self._equity_at_or_before(signal.generated_at)
        if equity is None:
            logger.warning("No equity snapshot at or before signal.generated_at; rejecting.")
            return self._reject(
                signal=signal,
                phase=phase,
                fraction=fraction,
                halt_state=HaltState.L0,
                reason=ReasonCode.REJECT_RISK_EXCEEDED,
                now=now,
            )

        # CB state
        halt_state = self._current_halt_state()
        if halt_state in (HaltState.L2, HaltState.L3, HaltState.FLASH):
            reason = {
                HaltState.L2: ReasonCode.HALT_DRAWDOWN_L2,
                HaltState.L3: ReasonCode.HALT_DRAWDOWN_L3,
                HaltState.FLASH: ReasonCode.HALT_FLASH_CRASH,
            }[halt_state]
            return self._reject(
                signal=signal,
                phase=phase,
                fraction=fraction,
                halt_state=halt_state,
                reason=reason,
                now=now,
            )

        # L1: de-lever by 0.5
        effective_fraction = fraction
        if halt_state == HaltState.L1:
            effective_fraction = fraction * Decimal("0.5")

        qty = compute_qty(
            equity=equity,
            fraction=effective_fraction,
            atr=signal.atr_14,
            price=mark_price,
            k=self._settings.risk_sl_atr_multiplier,
        )
        if qty <= Decimal("0"):
            return self._reject(
                signal=signal,
                phase=phase,
                fraction=fraction,
                halt_state=halt_state,
                reason=ReasonCode.REJECT_RISK_EXCEEDED,
                now=now,
            )

        sl_price = mark_price - self._settings.risk_sl_atr_multiplier * signal.atr_14
        tp_price = mark_price + self._settings.risk_tp_atr_multiplier * signal.atr_14

        return RiskAssessment(
            signal_id=signal.signal_id,
            approved=True,
            qty=qty,
            sl_price=sl_price,
            tp_price=tp_price,
            kelly_phase=phase,
            kelly_fraction=fraction,
            halt_state=halt_state,
            reason_code=ReasonCode.ENTRY_LONG_TREND_FOLLOWING,
            assessed_at=now,
        )

    def on_bar_close(self, bar: object) -> None:
        """Update equity snapshot on bar close (BAR_CLOSE source).

        Expects bar to have: close: Decimal, high: Decimal, low: Decimal,
        ts: datetime, atr_14: Decimal.
        """
        ts = getattr(bar, "ts", self._clock())
        close = getattr(bar, "close", None)
        if close is None:
            return
        current = self._equity_tracker.latest_total_equity()
        if current is not None:
            self._equity_tracker.snapshot(
                realized=current,
                unrealized=Decimal("0"),
                ts=ts,
                source="BAR_CLOSE",
            )
        self._refresh_cb_state(current=current or Decimal("0"), ts=ts)

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _equity_at_or_before(self, ts: datetime) -> Decimal | None:
        """Return latest total_equity with snapshot ts <= given ts."""
        row = self._conn.execute(
            "SELECT total_equity FROM equity_snapshots WHERE ts <= ? ORDER BY ts DESC LIMIT 1",
            (ts.isoformat(),),
        ).fetchone()
        if row is None:
            return None
        return Decimal(row[0])

    def _current_halt_state(self) -> HaltState:
        state = self._state_repo.get(_CB_KEY)
        if state is None:
            return HaltState.L0
        try:
            return HaltState(state["level"])
        except (KeyError, ValueError):
            return HaltState.L0

    def _refresh_cb_state(self, *, current: Decimal, ts: datetime) -> None:
        """Recompute CB level from 24h HWM and persist atomically."""
        hwm = self._equity_tracker.hwm_24h(reference_ts=ts)
        if hwm is None:
            return
        new_level = self._cb_detector.check_drawdown(peak=hwm, current=current)
        existing = self._state_repo.get(_CB_KEY)
        existing_level = HaltState((existing or {}).get("level", "L0"))
        # Only escalate, never auto-de-escalate (manual resume required for L2/L3)
        if new_level.value >= existing_level.value or existing_level == HaltState.L0:
            dd_pct = float((hwm - current) / hwm) if hwm > 0 else 0.0
            self._state_repo.set(
                _CB_KEY,
                {
                    "level": str(new_level),
                    "triggered_at": ts.isoformat(),
                    "peak_equity": str(hwm),
                    "dd_pct": str(round(dd_pct, 6)),
                },
            )

    def _reject(
        self,
        *,
        signal: Signal,
        phase: int,
        fraction: Decimal,
        halt_state: HaltState,
        reason: ReasonCode,
        now: datetime,
    ) -> RiskAssessment:
        return RiskAssessment(
            signal_id=signal.signal_id,
            approved=False,
            qty=None,
            sl_price=None,
            tp_price=None,
            kelly_phase=phase,  # type: ignore[arg-type]
            kelly_fraction=fraction,
            halt_state=halt_state,
            reason_code=reason,
            assessed_at=now,
        )
```

- [ ] **Step 4: Run tests — verify GREEN**

```bash
pytest tests/unit/test_risk_manager.py -v
```
Expected: all critical tests pass (look-ahead test may expose minor clock fixture issue — fix inline if needed).

- [ ] **Step 5: Commit**

```bash
git add src/risk/manager.py tests/unit/test_risk_manager.py
git commit -m "feat(risk): add RiskManager orchestrator

Composes KellyCalculator, CircuitBreakerDetector, EquityTracker,
TradeHistoryRepository, StateRepo. Clock injected for determinism.
Look-ahead safety: assess() only uses equity with ts <= signal.generated_at.
Source: wiki/project/plans/2026-04-23-sprint-4-risk.md §Task-12"
```

---

### Task 13: `src/risk/resume_cb.py` + `src/risk/__main__.py` — CLI

**Files:**
- Create: `src/risk/resume_cb.py`
- Create: `src/risk/__main__.py`
- Create: `tests/unit/test_resume_cb.py` (argparse + file-write validation)

- [ ] **Step 1: RED — write CLI tests**

Create `tests/unit/test_resume_cb.py`:

```python
"""Tests for resume_cb CLI argument parsing and override file creation."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.risk.models import HaltState
from src.risk.override import OverrideStore
from src.risk.resume_cb import build_parser, run_resume


@pytest.fixture()
def override_path(tmp_path: Path) -> Path:
    return tmp_path / "state" / "cb_override.json"


def test_parser_accepts_l2(override_path: Path) -> None:
    parser = build_parser()
    args = parser.parse_args(["--level", "L2", "--reason", "Manual after reconciliation"])
    assert args.level == "L2"
    assert args.reason == "Manual after reconciliation"


def test_parser_accepts_all_levels(override_path: Path) -> None:
    parser = build_parser()
    for level in ["L2", "L3", "FLASH"]:
        args = parser.parse_args(["--level", level, "--reason", "test"])
        assert args.level == level


def test_parser_rejects_l1(override_path: Path) -> None:
    """L1 is automatic — cannot manually resume to L1."""
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--level", "L1", "--reason", "test"])


def test_parser_rejects_l0() -> None:
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--level", "L0", "--reason", "test"])


def test_run_resume_creates_file(override_path: Path) -> None:
    t0 = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    run_resume(
        level="L2",
        reason="Post-reconciliation resume",
        config_hash="testhash123",
        override_path=override_path,
        clock=lambda: t0,
    )
    assert override_path.exists()
    payload = json.loads(override_path.read_text())
    assert payload["level"] == "L2"
    assert payload["config_hash"] == "testhash123"
    assert payload["reason"] == "Post-reconciliation resume"


def test_run_resume_default_expires_in_1h(override_path: Path) -> None:
    t0 = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    run_resume(
        level="L3",
        reason="Full stop resume",
        config_hash="h1",
        override_path=override_path,
        clock=lambda: t0,
    )
    payload = json.loads(override_path.read_text())
    created = datetime.fromisoformat(payload["created_at"])
    expires = datetime.fromisoformat(payload["expires_at"])
    assert (expires - created).total_seconds() == 3600


def test_run_resume_custom_expires_in(override_path: Path) -> None:
    from datetime import timedelta
    t0 = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    run_resume(
        level="L2",
        reason="4h override",
        config_hash="h1",
        override_path=override_path,
        clock=lambda: t0,
        expires_in=timedelta(hours=4),
    )
    payload = json.loads(override_path.read_text())
    created = datetime.fromisoformat(payload["created_at"])
    expires = datetime.fromisoformat(payload["expires_at"])
    assert (expires - created).total_seconds() == 14400
```

- [ ] **Step 2: Run test — verify RED**

```bash
pytest tests/unit/test_resume_cb.py -v
```
Expected: FAIL.

- [ ] **Step 3: GREEN — create `src/risk/resume_cb.py`**

```python
"""Manual circuit breaker resume CLI.

Usage:
    python -m src.risk.resume_cb --level L2 --reason "Post-reconciliation" [--expires-in 2h]

Writes state/cb_override.json with config_hash binding.
Config hash is computed from current Settings at invocation time.

Source: wiki/project/plans/2026-04-23-sprint-4-risk.md §Q3 §Task-13
"""

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from src.risk.models import HaltState
from src.risk.override import OverrideStore

_RESUMABLE_LEVELS = ["L2", "L3", "FLASH"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="resume_cb",
        description="Manually resume after a circuit breaker halt.",
    )
    parser.add_argument(
        "--level",
        choices=_RESUMABLE_LEVELS,
        required=True,
        help="CB level to resume from. L1 is automatic and cannot be manually resumed.",
    )
    parser.add_argument(
        "--reason",
        required=True,
        help="Human-readable reason for resuming (logged in override file).",
    )
    parser.add_argument(
        "--expires-in",
        default="1h",
        help="Override validity window (e.g. '1h', '2h', '30m'). Default: 1h.",
    )
    return parser


def _parse_expires_in(s: str) -> timedelta:
    """Parse '1h', '30m', '90m' etc. into timedelta."""
    s = s.strip()
    if s.endswith("h"):
        return timedelta(hours=int(s[:-1]))
    if s.endswith("m"):
        return timedelta(minutes=int(s[:-1]))
    raise ValueError(f"Cannot parse expires_in: {s!r}. Use '1h' or '30m' format.")


def run_resume(
    *,
    level: str,
    reason: str,
    config_hash: str,
    override_path: Path,
    clock: Callable[[], datetime],
    expires_in: timedelta = timedelta(hours=1),
) -> None:
    """Write override file. Separated from CLI for testability."""
    store = OverrideStore(override_path=override_path)
    store.write(
        level=HaltState(level),
        reason=reason,
        config_hash=config_hash,
        clock=clock,
        expires_in=expires_in,
    )
    print(f"Override written: level={level}, expires_in={expires_in}, path={override_path}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    from src.platform.config import Settings

    try:
        settings = Settings()
    except Exception as exc:
        print(f"ERROR: Cannot load Settings: {exc}", file=sys.stderr)
        return 1

    try:
        expires_in = _parse_expires_in(getattr(args, "expires_in", "1h"))
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    run_resume(
        level=args.level,
        reason=args.reason,
        config_hash=settings.config_hash(),
        override_path=settings.risk_override_path,
        clock=lambda: datetime.now(timezone.utc),
        expires_in=expires_in,
    )
    return 0
```

- [ ] **Step 4: Create `src/risk/__main__.py`**

```python
"""Entry point: python -m src.risk.resume_cb"""

import sys

from src.risk.resume_cb import main

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run tests — verify GREEN**

```bash
pytest tests/unit/test_resume_cb.py -v
```
Expected: all passed.

- [ ] **Step 6: Commit**

```bash
git add src/risk/resume_cb.py src/risk/__main__.py tests/unit/test_resume_cb.py
git commit -m "feat(risk): add resume_cb CLI for manual CB resume

python -m src.risk.resume_cb --level L2 --reason '...' [--expires-in 2h]
Writes state/cb_override.json with config_hash binding and expiry.
Source: wiki/project/plans/2026-04-23-sprint-4-risk.md §Task-13"
```

---

→ Continue: [Tasks 14-17](2026-04-23-sprint-4-risk-tasks-14-17.md)
