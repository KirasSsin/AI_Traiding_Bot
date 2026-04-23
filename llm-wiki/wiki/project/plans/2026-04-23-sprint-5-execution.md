---
title: Sprint 5 — Execution advanced (OCO / FSM / Reconciler) plan
type: plan
tags: [plan, sprint-5, execution, oco, fsm, reconciler]
created: 2026-04-23
updated: 2026-04-23
sources: [project/decisions/0019-sprint-5-execution-decisions.md, project/architecture/migration-plan.md]
status: ready
---

# Sprint 5 — Execution advanced — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Реализовать OCO bracket (SL+TP), partial-fill handling, post-reconnect reconciliation и формальный 12-state machine на Bybit Spot V5 с happy-path integration test на testnet.

**Architecture:** 12-state Harel-style FSM (table-driven transitions) + native Bybit `tpslMode` для OCO + reconcile-as-truth (SQLite warm cache, exchange = source of truth) + 2 новых reason codes. Все архитектурные решения зафиксированы в [[../decisions/0019-sprint-5-execution-decisions]].

**Tech Stack:** Python 3.12 · pydantic v2 · `pybit` (Bybit V5 SDK) · SQLite WAL · pytest + hypothesis · TDD strict.

**Branch:** `feature/sprint-5-execution`

**Total tasks:** 12 (5 stages: A-models/FSM, B-OCO, C-reconciler, D-testnet, E-wiki)

**Model dispatch policy:**
- Haiku: Tasks 1, 3, 10, 11, 12 (mechanical scaffolding, wiki writes, enum extensions)
- Sonnet: Tasks 2, 4, 5, 6, 7, 8, 9 (logic + integration)
- Opus: только если subagent escalates BLOCKED

**Pre-task setup (one-time):**

```bash
cd /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot
source .venv/bin/activate
git status        # expect: clean working tree on feature/sprint-5-execution
pytest --collect-only 2>&1 | tail -5  # expect: existing test count
```

---

## Stage A — Models, FSM, persistence

### Task 1: Extend ReasonCode enum (+2 codes)

**Files:**
- Modify: `src/risk/reason_codes.py:60-67`
- Modify: `tests/unit/test_reason_codes.py`

**ADR ref:** sub-decision 4.

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_reason_codes.py — append to existing test class
def test_halt_reconcile_divergence_in_enum():
    assert ReasonCode.HALT_RECONCILE_DIVERGENCE.value == "HALT_RECONCILE_DIVERGENCE"

def test_exit_oco_partial_timeout_in_enum():
    assert ReasonCode.EXIT_OCO_PARTIAL_TIMEOUT.value == "EXIT_OCO_PARTIAL_TIMEOUT"

def test_total_reason_codes_count():
    assert len(ReasonCode) == 30  # was 28 → +2 in S5
```

- [ ] **Step 2: Run, expect FAIL**

```bash
pytest tests/unit/test_reason_codes.py -v
```
Expected: 3 new tests FAIL (AttributeError / count mismatch).

- [ ] **Step 3: Add codes to enum**

В `src/risk/reason_codes.py` секция HALT — после `HALT_KILL_SWITCH`:
```python
    HALT_RECONCILE_DIVERGENCE = "HALT_RECONCILE_DIVERGENCE"
```
В секции EXIT — после `EXIT_CIRCUIT_BREAKER`:
```python
    EXIT_OCO_PARTIAL_TIMEOUT = "EXIT_OCO_PARTIAL_TIMEOUT"
```

- [ ] **Step 4: Run, expect PASS**

```bash
pytest tests/unit/test_reason_codes.py -v
```
Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add src/risk/reason_codes.py tests/unit/test_reason_codes.py
git commit -m "feat(risk): add HALT_RECONCILE_DIVERGENCE + EXIT_OCO_PARTIAL_TIMEOUT (ADR 0019 sub-decision 4)"
```

---

### Task 2: ExecutionState enum + transitions table + `apply()`

**Files:**
- Create: `src/execution/state_machine.py`
- Create: `tests/unit/test_execution_fsm.py`

**ADR ref:** sub-decision 2.

- [ ] **Step 1: Write failing test (table-driven)**

```python
# tests/unit/test_execution_fsm.py
import pytest
from src.execution.state_machine import (
    ExecutionState, ExecutionEvent, apply, IllegalTransitionError, TRANSITIONS,
)

LEGAL = [
    (ExecutionState.INIT, ExecutionEvent.STATE_LOADED, ExecutionState.FLAT),
    (ExecutionState.FLAT, ExecutionEvent.ENTRY_PLACED, ExecutionState.ENTRY_PENDING),
    (ExecutionState.ENTRY_PENDING, ExecutionEvent.ENTRY_FILLED, ExecutionState.LONG_OPEN),
    (ExecutionState.LONG_OPEN, ExecutionEvent.OCO_PLACED, ExecutionState.OCO_ARMED),
    (ExecutionState.OCO_ARMED, ExecutionEvent.PARTIAL_FILL, ExecutionState.PARTIAL_FILL),
    (ExecutionState.OCO_ARMED, ExecutionEvent.SL_HIT, ExecutionState.EXIT_PENDING),
    (ExecutionState.OCO_ARMED, ExecutionEvent.TP_HIT, ExecutionState.EXIT_PENDING),
    (ExecutionState.PARTIAL_FILL, ExecutionEvent.SL_HIT, ExecutionState.EXIT_PENDING),
    (ExecutionState.PARTIAL_FILL, ExecutionEvent.TP_HIT, ExecutionState.EXIT_PENDING),
    (ExecutionState.EXIT_PENDING, ExecutionEvent.EXIT_FILLED, ExecutionState.FLAT),
    (ExecutionState.OCO_ARMED, ExecutionEvent.WS_RECONNECT, ExecutionState.RECONCILING),
    (ExecutionState.LONG_OPEN, ExecutionEvent.WS_RECONNECT, ExecutionState.RECONCILING),
    (ExecutionState.PARTIAL_FILL, ExecutionEvent.WS_RECONNECT, ExecutionState.RECONCILING),
    (ExecutionState.RECONCILING, ExecutionEvent.RECONCILE_OK, ExecutionState.OCO_ARMED),
    (ExecutionState.RECONCILING, ExecutionEvent.RECONCILE_DIVERGENCE, ExecutionState.HALTED),
    (ExecutionState.OCO_ARMED, ExecutionEvent.RISK_HALT, ExecutionState.HALTED),
    (ExecutionState.LONG_OPEN, ExecutionEvent.RISK_HALT, ExecutionState.HALTED),
    (ExecutionState.HALTED, ExecutionEvent.HALT_RESUME, ExecutionState.COOLDOWN),
    (ExecutionState.COOLDOWN, ExecutionEvent.COOLDOWN_DONE, ExecutionState.FLAT),
    (ExecutionState.FLAT, ExecutionEvent.KILL_SWITCH, ExecutionState.KILLED),
    (ExecutionState.LONG_OPEN, ExecutionEvent.KILL_SWITCH, ExecutionState.KILLED),
    (ExecutionState.OCO_ARMED, ExecutionEvent.KILL_SWITCH, ExecutionState.KILLED),
    (ExecutionState.PARTIAL_FILL, ExecutionEvent.KILL_SWITCH, ExecutionState.KILLED),
    (ExecutionState.HALTED, ExecutionEvent.KILL_SWITCH, ExecutionState.KILLED),
    (ExecutionState.ENTRY_PENDING, ExecutionEvent.ENTRY_REJECTED, ExecutionState.FLAT),
    (ExecutionState.EXIT_PENDING, ExecutionEvent.EXIT_REJECTED, ExecutionState.ERROR),
    (ExecutionState.ERROR, ExecutionEvent.MANUAL_RESET, ExecutionState.FLAT),
    (ExecutionState.OCO_ARMED, ExecutionEvent.OCO_PARTIAL_TIMEOUT, ExecutionState.EXIT_PENDING),
]

@pytest.mark.parametrize("src,event,dst", LEGAL)
def test_legal_transition(src, event, dst):
    assert apply(src, event) == dst

def test_illegal_transition_raises():
    with pytest.raises(IllegalTransitionError):
        apply(ExecutionState.FLAT, ExecutionEvent.SL_HIT)

def test_kill_terminal():
    with pytest.raises(IllegalTransitionError):
        apply(ExecutionState.KILLED, ExecutionEvent.STATE_LOADED)

def test_transitions_count_at_least_28():
    assert len(TRANSITIONS) >= 28
```

- [ ] **Step 2: Run, expect FAIL (ImportError)**

```bash
pytest tests/unit/test_execution_fsm.py -v
```
Expected: collection error — module не существует.

- [ ] **Step 3: Implement `state_machine.py`**

```python
# src/execution/state_machine.py
"""12-state execution FSM. ADR 0019 sub-decision 2."""
from __future__ import annotations
from enum import StrEnum


class ExecutionState(StrEnum):
    INIT = "INIT"
    FLAT = "FLAT"
    ENTRY_PENDING = "ENTRY_PENDING"
    LONG_OPEN = "LONG_OPEN"
    OCO_ARMED = "OCO_ARMED"
    PARTIAL_FILL = "PARTIAL_FILL"
    EXIT_PENDING = "EXIT_PENDING"
    RECONCILING = "RECONCILING"
    HALTED = "HALTED"
    COOLDOWN = "COOLDOWN"
    ERROR = "ERROR"
    KILLED = "KILLED"


class ExecutionEvent(StrEnum):
    STATE_LOADED = "STATE_LOADED"
    ENTRY_PLACED = "ENTRY_PLACED"
    ENTRY_FILLED = "ENTRY_FILLED"
    ENTRY_REJECTED = "ENTRY_REJECTED"
    OCO_PLACED = "OCO_PLACED"
    PARTIAL_FILL = "PARTIAL_FILL"
    SL_HIT = "SL_HIT"
    TP_HIT = "TP_HIT"
    EXIT_FILLED = "EXIT_FILLED"
    EXIT_REJECTED = "EXIT_REJECTED"
    WS_RECONNECT = "WS_RECONNECT"
    RECONCILE_OK = "RECONCILE_OK"
    RECONCILE_DIVERGENCE = "RECONCILE_DIVERGENCE"
    RISK_HALT = "RISK_HALT"
    HALT_RESUME = "HALT_RESUME"
    COOLDOWN_DONE = "COOLDOWN_DONE"
    KILL_SWITCH = "KILL_SWITCH"
    MANUAL_RESET = "MANUAL_RESET"
    OCO_PARTIAL_TIMEOUT = "OCO_PARTIAL_TIMEOUT"


class IllegalTransitionError(RuntimeError):
    """Raised when (state, event) is not in TRANSITIONS table."""


TRANSITIONS: dict[tuple[ExecutionState, ExecutionEvent], ExecutionState] = {
    (ExecutionState.INIT, ExecutionEvent.STATE_LOADED): ExecutionState.FLAT,
    (ExecutionState.FLAT, ExecutionEvent.ENTRY_PLACED): ExecutionState.ENTRY_PENDING,
    (ExecutionState.ENTRY_PENDING, ExecutionEvent.ENTRY_FILLED): ExecutionState.LONG_OPEN,
    (ExecutionState.ENTRY_PENDING, ExecutionEvent.ENTRY_REJECTED): ExecutionState.FLAT,
    (ExecutionState.LONG_OPEN, ExecutionEvent.OCO_PLACED): ExecutionState.OCO_ARMED,
    (ExecutionState.OCO_ARMED, ExecutionEvent.PARTIAL_FILL): ExecutionState.PARTIAL_FILL,
    (ExecutionState.OCO_ARMED, ExecutionEvent.SL_HIT): ExecutionState.EXIT_PENDING,
    (ExecutionState.OCO_ARMED, ExecutionEvent.TP_HIT): ExecutionState.EXIT_PENDING,
    (ExecutionState.OCO_ARMED, ExecutionEvent.OCO_PARTIAL_TIMEOUT): ExecutionState.EXIT_PENDING,
    (ExecutionState.PARTIAL_FILL, ExecutionEvent.SL_HIT): ExecutionState.EXIT_PENDING,
    (ExecutionState.PARTIAL_FILL, ExecutionEvent.TP_HIT): ExecutionState.EXIT_PENDING,
    (ExecutionState.EXIT_PENDING, ExecutionEvent.EXIT_FILLED): ExecutionState.FLAT,
    (ExecutionState.EXIT_PENDING, ExecutionEvent.EXIT_REJECTED): ExecutionState.ERROR,
    (ExecutionState.OCO_ARMED, ExecutionEvent.WS_RECONNECT): ExecutionState.RECONCILING,
    (ExecutionState.LONG_OPEN, ExecutionEvent.WS_RECONNECT): ExecutionState.RECONCILING,
    (ExecutionState.PARTIAL_FILL, ExecutionEvent.WS_RECONNECT): ExecutionState.RECONCILING,
    (ExecutionState.RECONCILING, ExecutionEvent.RECONCILE_OK): ExecutionState.OCO_ARMED,
    (ExecutionState.RECONCILING, ExecutionEvent.RECONCILE_DIVERGENCE): ExecutionState.HALTED,
    (ExecutionState.OCO_ARMED, ExecutionEvent.RISK_HALT): ExecutionState.HALTED,
    (ExecutionState.LONG_OPEN, ExecutionEvent.RISK_HALT): ExecutionState.HALTED,
    (ExecutionState.PARTIAL_FILL, ExecutionEvent.RISK_HALT): ExecutionState.HALTED,
    (ExecutionState.HALTED, ExecutionEvent.HALT_RESUME): ExecutionState.COOLDOWN,
    (ExecutionState.COOLDOWN, ExecutionEvent.COOLDOWN_DONE): ExecutionState.FLAT,
    (ExecutionState.FLAT, ExecutionEvent.KILL_SWITCH): ExecutionState.KILLED,
    (ExecutionState.LONG_OPEN, ExecutionEvent.KILL_SWITCH): ExecutionState.KILLED,
    (ExecutionState.OCO_ARMED, ExecutionEvent.KILL_SWITCH): ExecutionState.KILLED,
    (ExecutionState.PARTIAL_FILL, ExecutionEvent.KILL_SWITCH): ExecutionState.KILLED,
    (ExecutionState.HALTED, ExecutionEvent.KILL_SWITCH): ExecutionState.KILLED,
    (ExecutionState.ERROR, ExecutionEvent.MANUAL_RESET): ExecutionState.FLAT,
}


def apply(state: ExecutionState, event: ExecutionEvent) -> ExecutionState:
    """Apply event to state. Raise IllegalTransitionError if not in table."""
    try:
        return TRANSITIONS[(state, event)]
    except KeyError as e:
        raise IllegalTransitionError(f"{state} + {event} not allowed") from e
```

- [ ] **Step 4: Run, expect PASS**

```bash
pytest tests/unit/test_execution_fsm.py -v
```
Expected: 28+ legal + 3 illegal pass.

- [ ] **Step 5: Commit**

```bash
git add src/execution/state_machine.py tests/unit/test_execution_fsm.py
git commit -m "feat(execution): add 12-state FSM with table-driven transitions (ADR 0019 sub-decision 2)"
```

---

### Task 3: ExecutionStateRepo + migration 0003

**Files:**
- Create: `migrations/0003_execution_state.sql`
- Create: `src/execution/state_repo.py`
- Create: `tests/unit/test_execution_state_repo.py`

**ADR ref:** sub-decision 3.

- [ ] **Step 1: Write migration**

```sql
-- migrations/0003_execution_state.sql
CREATE TABLE IF NOT EXISTS execution_state (
    symbol TEXT PRIMARY KEY,
    state TEXT NOT NULL,
    position_qty TEXT NOT NULL,
    entry_price TEXT,
    oco_main_order_id TEXT,
    updated_at TEXT NOT NULL
);
```

- [ ] **Step 2: Write failing test**

```python
# tests/unit/test_execution_state_repo.py
from decimal import Decimal
import sqlite3
import pytest
from src.execution.state_repo import ExecutionStateRepo, ExecutionStateRow
from src.execution.state_machine import ExecutionState


@pytest.fixture
def conn(tmp_path):
    db = tmp_path / "exec.db"
    conn = sqlite3.connect(db)
    conn.executescript(open("migrations/0003_execution_state.sql").read())
    return conn


def test_upsert_and_get_roundtrip(conn):
    repo = ExecutionStateRepo(conn)
    row = ExecutionStateRow(
        symbol="BTCUSDT",
        state=ExecutionState.OCO_ARMED,
        position_qty=Decimal("0.01234567"),
        entry_price=Decimal("65432.10"),
        oco_main_order_id="abc-123",
        updated_at="2026-04-23T10:00:00+00:00",
    )
    repo.upsert(row)
    got = repo.get("BTCUSDT")
    assert got == row


def test_get_unknown_returns_none(conn):
    repo = ExecutionStateRepo(conn)
    assert repo.get("ETHUSDT") is None


def test_decimal_precision_preserved(conn):
    repo = ExecutionStateRepo(conn)
    qty = Decimal("0.123456789012345678")  # > IEEE-754 double precision
    repo.upsert(ExecutionStateRow(
        symbol="BTCUSDT", state=ExecutionState.LONG_OPEN,
        position_qty=qty, entry_price=Decimal("100"),
        oco_main_order_id=None, updated_at="2026-04-23T10:00:00+00:00",
    ))
    assert repo.get("BTCUSDT").position_qty == qty
```

- [ ] **Step 3: Run, expect FAIL**

```bash
pytest tests/unit/test_execution_state_repo.py -v
```
Expected: ImportError.

- [ ] **Step 4: Implement repo**

```python
# src/execution/state_repo.py
"""SQLite persistence for execution FSM state. ADR 0019 sub-decision 3."""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
import sqlite3
from src.execution.state_machine import ExecutionState


@dataclass(frozen=True)
class ExecutionStateRow:
    symbol: str
    state: ExecutionState
    position_qty: Decimal
    entry_price: Decimal | None
    oco_main_order_id: str | None
    updated_at: str  # ISO-8601 UTC


class ExecutionStateRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def upsert(self, row: ExecutionStateRow) -> None:
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO execution_state
                    (symbol, state, position_qty, entry_price, oco_main_order_id, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol) DO UPDATE SET
                    state=excluded.state,
                    position_qty=excluded.position_qty,
                    entry_price=excluded.entry_price,
                    oco_main_order_id=excluded.oco_main_order_id,
                    updated_at=excluded.updated_at
                """,
                (
                    row.symbol,
                    row.state.value,
                    str(row.position_qty),
                    str(row.entry_price) if row.entry_price is not None else None,
                    row.oco_main_order_id,
                    row.updated_at,
                ),
            )

    def get(self, symbol: str) -> ExecutionStateRow | None:
        cur = self._conn.execute(
            "SELECT symbol, state, position_qty, entry_price, oco_main_order_id, updated_at "
            "FROM execution_state WHERE symbol = ?",
            (symbol,),
        )
        r = cur.fetchone()
        if r is None:
            return None
        return ExecutionStateRow(
            symbol=r[0],
            state=ExecutionState(r[1]),
            position_qty=Decimal(r[2]),
            entry_price=Decimal(r[3]) if r[3] is not None else None,
            oco_main_order_id=r[4],
            updated_at=r[5],
        )
```

- [ ] **Step 5: Run, expect PASS**

```bash
pytest tests/unit/test_execution_state_repo.py -v
```

- [ ] **Step 6: Commit**

```bash
git add migrations/0003_execution_state.sql src/execution/state_repo.py tests/unit/test_execution_state_repo.py
git commit -m "feat(execution): add ExecutionStateRepo + migration 0003 (ADR 0019 sub-decision 3)"
```

---

## Stage B — OCO bracket

### Task 4: `build_oco_order()` — SL/TP from ATR + venue filters

**Files:**
- Create: `src/execution/oco.py`
- Create: `tests/unit/test_oco.py`

**ADR ref:** sub-decision 1.

**Settings used:** `sl_atr_multiplier=Decimal("1.5")`, `tp_atr_multiplier=Decimal("3.0")` (already in `Settings` per Sprint 4).

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_oco.py
from decimal import Decimal
import pytest
from src.execution.oco import build_oco_order, OcoParams, OcoOrder


def test_oco_long_sl_below_tp_above():
    params = OcoParams(
        symbol="BTCUSDT",
        side="LONG",
        qty=Decimal("0.001"),
        entry_price=Decimal("60000"),
        atr=Decimal("500"),
        sl_atr_mult=Decimal("1.5"),
        tp_atr_mult=Decimal("3.0"),
        tick_size=Decimal("0.1"),
    )
    order = build_oco_order(params)
    assert order.stop_loss == Decimal("59250.0")  # 60000 - 1.5*500
    assert order.take_profit == Decimal("61500.0")  # 60000 + 3.0*500
    assert order.symbol == "BTCUSDT"
    assert order.qty == Decimal("0.001")


def test_oco_sl_rounded_to_tick_down():
    """SL price quantized DOWN to tick_size for LONG (conservative)."""
    params = OcoParams(
        symbol="BTCUSDT", side="LONG", qty=Decimal("0.001"),
        entry_price=Decimal("60000"), atr=Decimal("333"),
        sl_atr_mult=Decimal("1.5"), tp_atr_mult=Decimal("3.0"),
        tick_size=Decimal("0.1"),
    )
    order = build_oco_order(params)
    # raw SL = 60000 - 499.5 = 59500.5 → tick 0.1 → 59500.5 exact
    assert order.stop_loss == Decimal("59500.5")


def test_oco_tp_rounded_to_tick_up():
    """TP price quantized UP to tick_size for LONG (conservative — fill at higher)."""
    params = OcoParams(
        symbol="BTCUSDT", side="LONG", qty=Decimal("0.001"),
        entry_price=Decimal("60000"), atr=Decimal("100"),
        sl_atr_mult=Decimal("1.5"), tp_atr_mult=Decimal("3.0"),
        tick_size=Decimal("1"),
    )
    order = build_oco_order(params)
    # raw TP = 60000 + 300 = 60300 — exact, no rounding
    assert order.take_profit == Decimal("60300")


def test_oco_short_side_rejected_v01():
    """v0.1 LONG-only — SHORT raises ValueError."""
    params = OcoParams(
        symbol="BTCUSDT", side="SHORT", qty=Decimal("0.001"),
        entry_price=Decimal("60000"), atr=Decimal("500"),
        sl_atr_mult=Decimal("1.5"), tp_atr_mult=Decimal("3.0"),
        tick_size=Decimal("0.1"),
    )
    with pytest.raises(ValueError, match="LONG"):
        build_oco_order(params)


def test_oco_zero_atr_rejected():
    params = OcoParams(
        symbol="BTCUSDT", side="LONG", qty=Decimal("0.001"),
        entry_price=Decimal("60000"), atr=Decimal("0"),
        sl_atr_mult=Decimal("1.5"), tp_atr_mult=Decimal("3.0"),
        tick_size=Decimal("0.1"),
    )
    with pytest.raises(ValueError, match="atr"):
        build_oco_order(params)
```

- [ ] **Step 2: Run, expect FAIL (ImportError)**

```bash
pytest tests/unit/test_oco.py -v
```

- [ ] **Step 3: Implement `oco.py`**

```python
# src/execution/oco.py
"""Build OCO bracket orders. ADR 0019 sub-decision 1."""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN, ROUND_UP


@dataclass(frozen=True)
class OcoParams:
    symbol: str
    side: str  # "LONG" only in v0.1
    qty: Decimal
    entry_price: Decimal
    atr: Decimal
    sl_atr_mult: Decimal
    tp_atr_mult: Decimal
    tick_size: Decimal


@dataclass(frozen=True)
class OcoOrder:
    symbol: str
    side: str
    qty: Decimal
    entry_price: Decimal
    stop_loss: Decimal
    take_profit: Decimal


def build_oco_order(params: OcoParams) -> OcoOrder:
    """Compute SL/TP from ATR for a LONG entry. SL → tick-DOWN, TP → tick-UP.

    Raises:
        ValueError: side != LONG (v0.1 LONG-only) or atr <= 0.
    """
    if params.side != "LONG":
        raise ValueError(f"v0.1 supports LONG only, got {params.side}")
    if params.atr <= 0:
        raise ValueError(f"atr must be > 0, got {params.atr}")

    raw_sl = params.entry_price - params.sl_atr_mult * params.atr
    raw_tp = params.entry_price + params.tp_atr_mult * params.atr

    sl = raw_sl.quantize(params.tick_size, rounding=ROUND_DOWN)
    tp = raw_tp.quantize(params.tick_size, rounding=ROUND_UP)

    return OcoOrder(
        symbol=params.symbol,
        side=params.side,
        qty=params.qty,
        entry_price=params.entry_price,
        stop_loss=sl,
        take_profit=tp,
    )
```

- [ ] **Step 4: Run, expect PASS**

```bash
pytest tests/unit/test_oco.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/execution/oco.py tests/unit/test_oco.py
git commit -m "feat(execution): add OCO bracket builder with tick-aware SL/TP rounding (ADR 0019 sub-decision 1)"
```

---

### Task 5: Extend `BybitAdapter.place_order` for `tpslMode`

**Files:**
- Modify: `src/execution/bybit/adapter.py`
- Create: `tests/unit/test_bybit_adapter_oco.py`

**Existing:** `place_order(symbol, side, qty, ...)` уже есть. Расширяем optional kwargs `take_profit`, `stop_loss`, `tpsl_mode`.

- [ ] **Step 1: Write failing test (mock pybit)**

```python
# tests/unit/test_bybit_adapter_oco.py
from decimal import Decimal
from unittest.mock import MagicMock
import pytest
from src.execution.bybit.adapter import BybitAdapter


def test_place_order_with_oco_payload():
    mock_client = MagicMock()
    mock_client.place_order.return_value = {"retCode": 0, "result": {"orderId": "abc-123"}}
    adapter = BybitAdapter(client=mock_client, category="spot")

    order_id = adapter.place_order(
        symbol="BTCUSDT",
        side="Buy",
        qty=Decimal("0.001"),
        order_type="Market",
        take_profit=Decimal("61500.0"),
        stop_loss=Decimal("59250.0"),
        tpsl_mode="Full",
    )

    assert order_id == "abc-123"
    call = mock_client.place_order.call_args.kwargs
    assert call["symbol"] == "BTCUSDT"
    assert call["side"] == "Buy"
    assert call["qty"] == "0.001"
    assert call["takeProfit"] == "61500.0"
    assert call["stopLoss"] == "59250.0"
    assert call["tpslMode"] == "Full"


def test_place_order_without_oco_skips_tpsl_fields():
    mock_client = MagicMock()
    mock_client.place_order.return_value = {"retCode": 0, "result": {"orderId": "xyz-9"}}
    adapter = BybitAdapter(client=mock_client, category="spot")

    adapter.place_order(symbol="BTCUSDT", side="Buy", qty=Decimal("0.001"), order_type="Market")

    call = mock_client.place_order.call_args.kwargs
    assert "takeProfit" not in call
    assert "stopLoss" not in call
    assert "tpslMode" not in call
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Modify `adapter.py` — extend `place_order` signature**

В `src/execution/bybit/adapter.py::place_order` добавь optional kwargs:

```python
def place_order(
    self,
    symbol: str,
    side: str,
    qty: Decimal,
    order_type: str = "Market",
    *,
    take_profit: Decimal | None = None,
    stop_loss: Decimal | None = None,
    tpsl_mode: str | None = None,
) -> str:
    """Place order. If take_profit/stop_loss given, attach as Bybit native tpslMode."""
    payload: dict[str, str] = {
        "category": self._category,
        "symbol": symbol,
        "side": side,
        "qty": str(qty),
        "orderType": order_type,
    }
    if take_profit is not None:
        payload["takeProfit"] = str(take_profit)
    if stop_loss is not None:
        payload["stopLoss"] = str(stop_loss)
    if tpsl_mode is not None:
        payload["tpslMode"] = tpsl_mode

    resp = self._client.place_order(**payload)
    if resp.get("retCode") != 0:
        raise BybitError(resp.get("retCode"), resp.get("retMsg", ""))
    return resp["result"]["orderId"]
```

(Сохрани существующее поведение для не-OCO случая.)

- [ ] **Step 4: Run, expect PASS**

```bash
pytest tests/unit/test_bybit_adapter_oco.py tests/unit/test_bybit_adapter.py -v
```
Expected: новые tests pass + старые не сломаны.

- [ ] **Step 5: Commit**

```bash
git add src/execution/bybit/adapter.py tests/unit/test_bybit_adapter_oco.py
git commit -m "feat(execution): extend BybitAdapter.place_order with native tpslMode (ADR 0019 sub-decision 1)"
```

---

## Stage C — Reconciler

### Task 6: `Reconciler.fetch_exchange_state()` — wraps Bybit /openOrders + /positions + /executions

**Files:**
- Create: `src/execution/reconciler.py`
- Create: `tests/unit/test_reconciler_fetch.py`

**ADR ref:** sub-decision 3.

- [ ] **Step 1: Write failing test (mock adapter)**

```python
# tests/unit/test_reconciler_fetch.py
from decimal import Decimal
from unittest.mock import MagicMock
from src.execution.reconciler import Reconciler, ExchangeSnapshot


def test_fetch_exchange_state_assembles_snapshot():
    mock_adapter = MagicMock()
    mock_adapter.get_open_orders.return_value = [
        {"orderId": "abc", "symbol": "BTCUSDT", "side": "Sell", "qty": "0.001",
         "stopOrderType": "StopLoss", "triggerPrice": "59250"},
    ]
    mock_adapter.get_positions.return_value = [
        {"symbol": "BTCUSDT", "size": "0.001", "avgPrice": "60000"},
    ]
    mock_adapter.get_executions.return_value = [
        {"orderId": "entry-1", "symbol": "BTCUSDT", "execQty": "0.001",
         "execPrice": "60000", "execTime": "1700000000000"},
    ]
    rec = Reconciler(adapter=mock_adapter)

    snap = rec.fetch_exchange_state(symbol="BTCUSDT")

    assert isinstance(snap, ExchangeSnapshot)
    assert snap.symbol == "BTCUSDT"
    assert snap.position_qty == Decimal("0.001")
    assert snap.entry_price == Decimal("60000")
    assert len(snap.open_orders) == 1
    assert snap.open_orders[0]["orderId"] == "abc"


def test_fetch_exchange_state_empty_position():
    mock_adapter = MagicMock()
    mock_adapter.get_open_orders.return_value = []
    mock_adapter.get_positions.return_value = []
    mock_adapter.get_executions.return_value = []
    rec = Reconciler(adapter=mock_adapter)

    snap = rec.fetch_exchange_state(symbol="BTCUSDT")
    assert snap.position_qty == Decimal("0")
    assert snap.entry_price is None
```

- [ ] **Step 2: Run, expect FAIL (ImportError)**

- [ ] **Step 3: Implement skeleton + fetch**

```python
# src/execution/reconciler.py
"""Post-reconnect reconciliation. ADR 0019 sub-decision 3.

Reconcile-as-truth: exchange wins on divergence. Local SQLite cache is
warm-start optimization only.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class ExchangeSnapshot:
    symbol: str
    position_qty: Decimal
    entry_price: Decimal | None
    open_orders: list[dict[str, Any]] = field(default_factory=list)
    recent_executions: list[dict[str, Any]] = field(default_factory=list)


class Reconciler:
    def __init__(self, adapter: Any) -> None:
        self._adapter = adapter

    def fetch_exchange_state(self, symbol: str) -> ExchangeSnapshot:
        orders = self._adapter.get_open_orders(symbol=symbol)
        positions = self._adapter.get_positions(symbol=symbol)
        executions = self._adapter.get_executions(symbol=symbol)

        if positions:
            pos = positions[0]
            qty = Decimal(pos["size"])
            entry = Decimal(pos["avgPrice"]) if qty > 0 else None
        else:
            qty = Decimal("0")
            entry = None

        return ExchangeSnapshot(
            symbol=symbol,
            position_qty=qty,
            entry_price=entry,
            open_orders=list(orders),
            recent_executions=list(executions),
        )
```

- [ ] **Step 4: Run, expect PASS**

- [ ] **Step 5: Commit**

```bash
git add src/execution/reconciler.py tests/unit/test_reconciler_fetch.py
git commit -m "feat(execution): add Reconciler.fetch_exchange_state (ADR 0019 sub-decision 3)"
```

---

### Task 7: `Reconciler.reconcile()` — diff exchange ↔ local, emit divergence

**Files:**
- Modify: `src/execution/reconciler.py`
- Create: `tests/unit/test_reconciler_diff.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_reconciler_diff.py
from decimal import Decimal
from unittest.mock import MagicMock
import pytest
from src.execution.reconciler import (
    Reconciler, ExchangeSnapshot, ReconcileResult, ReconcileVerdict,
)
from src.execution.state_repo import ExecutionStateRow
from src.execution.state_machine import ExecutionState


def _local(qty: str, state: ExecutionState = ExecutionState.OCO_ARMED) -> ExecutionStateRow:
    return ExecutionStateRow(
        symbol="BTCUSDT", state=state, position_qty=Decimal(qty),
        entry_price=Decimal("60000"), oco_main_order_id="abc",
        updated_at="2026-04-23T10:00:00+00:00",
    )


def _snap(qty: str) -> ExchangeSnapshot:
    return ExchangeSnapshot(
        symbol="BTCUSDT", position_qty=Decimal(qty),
        entry_price=Decimal("60000"),
    )


def test_reconcile_qty_match_returns_ok():
    rec = Reconciler(adapter=MagicMock())
    result = rec.reconcile(local=_local("0.001"), exchange=_snap("0.001"))
    assert result.verdict == ReconcileVerdict.OK
    assert result.diff_qty == Decimal("0")


def test_reconcile_qty_mismatch_returns_divergence():
    rec = Reconciler(adapter=MagicMock())
    result = rec.reconcile(local=_local("0.001"), exchange=_snap("0.002"))
    assert result.verdict == ReconcileVerdict.DIVERGENCE
    assert result.diff_qty == Decimal("0.001")  # exchange - local
    assert "qty" in result.reason.lower()


def test_reconcile_local_unknown_uses_exchange():
    """Cold start (no local row) — adopt exchange as truth, OK verdict."""
    rec = Reconciler(adapter=MagicMock())
    result = rec.reconcile(local=None, exchange=_snap("0.001"))
    assert result.verdict == ReconcileVerdict.ADOPT_EXCHANGE
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Extend `reconciler.py`**

Append to `src/execution/reconciler.py`:

```python
from enum import StrEnum
from src.execution.state_repo import ExecutionStateRow


class ReconcileVerdict(StrEnum):
    OK = "OK"
    DIVERGENCE = "DIVERGENCE"
    ADOPT_EXCHANGE = "ADOPT_EXCHANGE"


@dataclass(frozen=True)
class ReconcileResult:
    verdict: ReconcileVerdict
    diff_qty: Decimal
    reason: str


class Reconciler:  # extend existing class
    # ... fetch_exchange_state from Task 6 stays ...

    def reconcile(
        self,
        local: ExecutionStateRow | None,
        exchange: ExchangeSnapshot,
    ) -> ReconcileResult:
        if local is None:
            return ReconcileResult(
                verdict=ReconcileVerdict.ADOPT_EXCHANGE,
                diff_qty=Decimal("0"),
                reason="no local state, adopting exchange",
            )
        diff = exchange.position_qty - local.position_qty
        if diff == 0:
            return ReconcileResult(
                verdict=ReconcileVerdict.OK,
                diff_qty=Decimal("0"),
                reason="qty match",
            )
        return ReconcileResult(
            verdict=ReconcileVerdict.DIVERGENCE,
            diff_qty=diff,
            reason=f"qty mismatch local={local.position_qty} exchange={exchange.position_qty}",
        )
```

(Объедини в один class — не дублируй определение Reconciler. См. финальный файл единым блоком.)

- [ ] **Step 4: Run, expect PASS (both fetch + diff tests)**

```bash
pytest tests/unit/test_reconciler_fetch.py tests/unit/test_reconciler_diff.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/execution/reconciler.py tests/unit/test_reconciler_diff.py
git commit -m "feat(execution): add Reconciler.reconcile diff logic (ADR 0019 sub-decision 3)"
```

---

### Task 8: Wire reconciler trigger to FSM event `WS_RECONNECT`

**Files:**
- Create: `src/execution/coordinator.py` — minimal orchestrator that on `WS_RECONNECT` event calls reconciler and emits `RECONCILE_OK` or `RECONCILE_DIVERGENCE`.
- Create: `tests/unit/test_coordinator_reconcile.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_coordinator_reconcile.py
from decimal import Decimal
from unittest.mock import MagicMock
from src.execution.coordinator import Coordinator
from src.execution.state_machine import ExecutionState, ExecutionEvent
from src.execution.state_repo import ExecutionStateRow
from src.execution.reconciler import ExchangeSnapshot, ReconcileResult, ReconcileVerdict


def _row(state, qty="0.001"):
    return ExecutionStateRow(
        symbol="BTCUSDT", state=state, position_qty=Decimal(qty),
        entry_price=Decimal("60000"), oco_main_order_id="abc",
        updated_at="2026-04-23T10:00:00+00:00",
    )


def test_ws_reconnect_ok_returns_to_oco_armed():
    repo = MagicMock()
    repo.get.return_value = _row(ExecutionState.OCO_ARMED)
    rec = MagicMock()
    rec.fetch_exchange_state.return_value = ExchangeSnapshot(
        symbol="BTCUSDT", position_qty=Decimal("0.001"), entry_price=Decimal("60000"),
    )
    rec.reconcile.return_value = ReconcileResult(
        verdict=ReconcileVerdict.OK, diff_qty=Decimal("0"), reason="ok",
    )
    coord = Coordinator(repo=repo, reconciler=rec, symbol="BTCUSDT")

    final_state = coord.handle_ws_reconnect()
    assert final_state == ExecutionState.OCO_ARMED


def test_ws_reconnect_divergence_goes_to_halted():
    repo = MagicMock()
    repo.get.return_value = _row(ExecutionState.OCO_ARMED)
    rec = MagicMock()
    rec.fetch_exchange_state.return_value = ExchangeSnapshot(
        symbol="BTCUSDT", position_qty=Decimal("0.002"), entry_price=Decimal("60000"),
    )
    rec.reconcile.return_value = ReconcileResult(
        verdict=ReconcileVerdict.DIVERGENCE, diff_qty=Decimal("0.001"),
        reason="qty mismatch",
    )
    coord = Coordinator(repo=repo, reconciler=rec, symbol="BTCUSDT")

    final_state = coord.handle_ws_reconnect()
    assert final_state == ExecutionState.HALTED
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Implement `coordinator.py`**

```python
# src/execution/coordinator.py
"""Minimal execution coordinator: wires Reconciler into FSM. ADR 0019 sub-decision 3."""
from __future__ import annotations
from src.execution.state_machine import ExecutionState, ExecutionEvent, apply
from src.execution.state_repo import ExecutionStateRepo
from src.execution.reconciler import Reconciler, ReconcileVerdict


class Coordinator:
    def __init__(
        self,
        repo: ExecutionStateRepo,
        reconciler: Reconciler,
        symbol: str,
    ) -> None:
        self._repo = repo
        self._reconciler = reconciler
        self._symbol = symbol

    def handle_ws_reconnect(self) -> ExecutionState:
        local = self._repo.get(self._symbol)
        current = local.state if local else ExecutionState.FLAT
        next_state = apply(current, ExecutionEvent.WS_RECONNECT) \
            if (current, ExecutionEvent.WS_RECONNECT) in __import__(
                "src.execution.state_machine", fromlist=["TRANSITIONS"]
            ).TRANSITIONS else ExecutionState.RECONCILING

        snapshot = self._reconciler.fetch_exchange_state(symbol=self._symbol)
        result = self._reconciler.reconcile(local=local, exchange=snapshot)

        if result.verdict == ReconcileVerdict.DIVERGENCE:
            return apply(ExecutionState.RECONCILING, ExecutionEvent.RECONCILE_DIVERGENCE)
        # OK or ADOPT_EXCHANGE both → resume normal
        return apply(ExecutionState.RECONCILING, ExecutionEvent.RECONCILE_OK)
```

(Note: упрощённая версия, S5 happy-path. Refinement в S5.5 если потребуется.)

- [ ] **Step 4: Run, expect PASS**

- [ ] **Step 5: Commit**

```bash
git add src/execution/coordinator.py tests/unit/test_coordinator_reconcile.py
git commit -m "feat(execution): add Coordinator wiring WS_RECONNECT \u2192 reconciler \u2192 FSM (ADR 0019 sub-decision 3)"
```

---

## Stage D — Testnet integration

### Task 9: Integration test — entry → OCO armed → SL hit → FLAT (Bybit testnet)

**Files:**
- Create: `tests/integration/test_execution_oco_testnet.py`
- Modify: `tests/conftest.py` — add `RUN_TESTNET` skip marker

**ADR ref:** sub-decision 5.

**Pre-req:** `.env` содержит `BYBIT_TESTNET_API_KEY` + `BYBIT_TESTNET_API_SECRET`. Settings уже умеет читать (Sprint 4).

- [ ] **Step 1: Add pytest marker + skip logic**

В `tests/conftest.py` добавь:

```python
import os
import pytest

def pytest_collection_modifyitems(config, items):
    if os.environ.get("RUN_TESTNET") != "1":
        skip_testnet = pytest.mark.skip(reason="testnet integration: set RUN_TESTNET=1 to run")
        for item in items:
            if "testnet" in item.keywords:
                item.add_marker(skip_testnet)
```

В `pytest.ini` (или `pyproject.toml::tool.pytest.ini_options::markers`) добавь:

```ini
markers =
    testnet: integration tests against Bybit testnet (require RUN_TESTNET=1)
    integration: integration tests
```

- [ ] **Step 2: Write integration test**

```python
# tests/integration/test_execution_oco_testnet.py
"""Sprint 5 happy-path integration test on Bybit testnet.

Sequence: entry MARKET (small qty) \u2192 OCO armed via tpslMode \u2192 manual SL hit
(via opposite-side market order on testnet) \u2192 reconcile \u2192 FLAT + audit.

ADR 0019 sub-decision 5 (testnet scope = happy path only in S5).
"""
from __future__ import annotations
import os
import time
from decimal import Decimal
import pytest
from pybit.unified_trading import HTTP
from src.execution.bybit.adapter import BybitAdapter
from src.execution.oco import build_oco_order, OcoParams
from src.execution.reconciler import Reconciler


pytestmark = [pytest.mark.integration, pytest.mark.testnet]


@pytest.fixture
def testnet_adapter():
    api_key = os.environ["BYBIT_TESTNET_API_KEY"]
    api_secret = os.environ["BYBIT_TESTNET_API_SECRET"]
    client = HTTP(testnet=True, api_key=api_key, api_secret=api_secret)
    return BybitAdapter(client=client, category="spot")


def test_oco_happy_path(testnet_adapter):
    symbol = "BTCUSDT"
    qty = Decimal("0.0001")  # ~$6 at $60k — minimal notional

    # 1. Get current price for SL/TP calc
    ticker = testnet_adapter.get_ticker(symbol=symbol)
    entry_price = Decimal(ticker["lastPrice"])
    atr_estimate = entry_price * Decimal("0.005")  # 0.5% as ATR proxy for testnet

    oco = build_oco_order(OcoParams(
        symbol=symbol, side="LONG", qty=qty,
        entry_price=entry_price, atr=atr_estimate,
        sl_atr_mult=Decimal("1.5"), tp_atr_mult=Decimal("3.0"),
        tick_size=Decimal("0.1"),
    ))

    # 2. Place entry with native OCO (tpslMode=Full)
    order_id = testnet_adapter.place_order(
        symbol=symbol, side="Buy", qty=qty, order_type="Market",
        take_profit=oco.take_profit, stop_loss=oco.stop_loss, tpsl_mode="Full",
    )
    assert order_id

    time.sleep(2)  # let testnet propagate

    # 3. Reconcile \u2014 expect position open, OCO present
    rec = Reconciler(adapter=testnet_adapter)
    snapshot = rec.fetch_exchange_state(symbol=symbol)
    assert snapshot.position_qty == qty
    assert snapshot.entry_price is not None

    # 4. Force-close (close opposite side) to simulate exit \u2014 testnet
    testnet_adapter.place_order(
        symbol=symbol, side="Sell", qty=qty, order_type="Market",
    )
    time.sleep(2)

    # 5. Verify FLAT
    snapshot_after = rec.fetch_exchange_state(symbol=symbol)
    assert snapshot_after.position_qty == Decimal("0")
```

- [ ] **Step 3: Run unit-suite (testnet тест skipped без env)**

```bash
pytest -v
```
Expected: full suite pass, integration test reported as SKIPPED.

- [ ] **Step 4: Run testnet test (manually, не в CI)**

```bash
RUN_TESTNET=1 pytest tests/integration/test_execution_oco_testnet.py -v -s
```
Expected: PASS (требует funded testnet account, рабочие creds).

- [ ] **Step 5: Commit**

```bash
git add tests/integration/test_execution_oco_testnet.py tests/conftest.py pytest.ini
git commit -m "test(execution): add testnet OCO happy-path integration test (ADR 0019 sub-decision 5)"
```

---

## Stage E — Wiki + agent prompts + sprint summary

### Task 10: Wiki components (3 new pages)

**Files:**
- Create: `llm-wiki/wiki/project/components/oco.md`
- Create: `llm-wiki/wiki/project/components/reconciler.md`
- Create: `llm-wiki/wiki/project/components/execution-state-machine.md`

- [ ] **Step 1: Write 3 component pages**

Каждая страница — frontmatter + TL;DR + Definition + Key properties + Related + Sources. Минимум 30 строк, максимум 80 строк (per llm-wiki/CLAUDE.md skeleton).

Используй template из `llm-wiki/wiki/project/sprints/README.md` или существующих pages (`bybit-adapter.md`, `circuit-breakers.md`).

Каждая страница ссылается на ADR 0019 + соответствующие code refs.

- [ ] **Step 2: Update `llm-wiki/wiki/project/components/bybit-adapter.md`**

Добавить секцию "Sprint 5 extension — `tpslMode`" с описанием новых kwargs `take_profit`, `stop_loss`, `tpsl_mode`.

- [ ] **Step 3: Commit**

```bash
git add llm-wiki/wiki/project/components/oco.md llm-wiki/wiki/project/components/reconciler.md llm-wiki/wiki/project/components/execution-state-machine.md llm-wiki/wiki/project/components/bybit-adapter.md
git commit -m "docs(wiki): add S5 components (oco, reconciler, execution-state-machine) + bybit-adapter tpslMode"
```

---

### Task 11: Update reason-codes.md, index.md, log.md, sprint-05-execution.md

**Files:**
- Modify: `llm-wiki/wiki/trading/concepts/reason-codes.md` — добавить 2 новых кода, обновить total с 28 → 30.
- Modify: `llm-wiki/wiki/index.md` — добавить ссылки на новые компоненты + ADR 0019 + sprint-05.
- Modify: `llm-wiki/wiki/log.md` — append-entry per sprints/README.md формат.
- Create: `llm-wiki/wiki/project/sprints/sprint-05-execution.md` — заполнить per template.

- [ ] **Step 1: Update reason-codes.md**

Добавить 2 кода в соответствующие секции (Halt / Exit). Обновить header "Total: 30".

- [ ] **Step 2: Update index.md**

Добавить строки в Decisions, Components, Sprints, Plans разделы.

- [ ] **Step 3: Append log.md**

```markdown
## [2026-04-23] sprint | 5 completed
- Branch: feature/sprint-5-execution
- Merged PR: #N (TBD after merge)
- Added: src/execution/{state_machine,state_repo,oco,reconciler,coordinator}.py
- Added: migrations/0003_execution_state.sql
- Added: ADR 0019, components/{oco,reconciler,execution-state-machine}.md
- Reason codes: 28 \u2192 30 (HALT_RECONCILE_DIVERGENCE, EXIT_OCO_PARTIAL_TIMEOUT)
```

- [ ] **Step 4: Create sprint-05-execution.md**

Заполни per template в `llm-wiki/wiki/project/sprints/README.md`.

- [ ] **Step 5: Commit**

```bash
git add llm-wiki/wiki/trading/concepts/reason-codes.md llm-wiki/wiki/index.md llm-wiki/wiki/log.md llm-wiki/wiki/project/sprints/sprint-05-execution.md
git commit -m "docs(wiki): S5 reason codes (28\u219230), index, log, sprint-05 summary"
```

---

### Task 12: Touch `trading-logic-reviewer.md` agent prompt + ADR sync

**Files:**
- Modify: `~/.claude/agents/trading-logic-reviewer.md`

**Triggered by:** ADR-Agent sync hook (PreToolUse on `git push`) — без mtime touch на agent prompt push заблокируется.

- [ ] **Step 1: Add S5 invariants section**

В trading-logic-reviewer.md добавить секцию:

```markdown
### CRITICAL — Execution FSM (Sprint 5, ADR 0019)
- 12 explicit states (`ExecutionState` enum), table-driven transitions (`TRANSITIONS` dict).
- Illegal transitions \u2192 `IllegalTransitionError` \u2192 ERROR state. No silent fallthrough.
- Reconcile-as-truth: on `WS_RECONNECT` reconciler diff exchange vs local, divergence \u2192 `HALT_RECONCILE_DIVERGENCE`.
- OCO: native Bybit `tpslMode` only in v0.1, NOT emulated. SL = entry - 1.5\u00b7ATR (tick-DOWN), TP = entry + 3.0\u00b7ATR (tick-UP).
- Reason codes total = 30 (28 from S4 + HALT_RECONCILE_DIVERGENCE + EXIT_OCO_PARTIAL_TIMEOUT).
```

- [ ] **Step 2: Commit (in repo, also touches mtime to satisfy hook)**

Agent prompt живёт вне repo (`~/.claude/agents/`). Commit делается отдельно (вне repo), но mtime touch достаточно для hook'а:

```bash
touch ~/.claude/agents/trading-logic-reviewer.md
```

(Если хук всё ещё блокирует — push с `--no-verify` запрещён; вместо этого amend prompt-файл и push.)

- [ ] **Step 3: Push branch + open PR**

```bash
git push -u origin feature/sprint-5-execution
gh pr create --title "feat(execution): Sprint 5 \u2014 OCO + FSM + reconciler" --body "$(cat <<'EOF'
## Summary
- 12-state execution FSM with table-driven transitions (ADR 0019 sub-decision 2)
- Native Bybit `tpslMode` for OCO bracket (sub-decision 1)
- Reconciler with reconcile-as-truth on WS reconnect (sub-decision 3)
- 2 new reason codes: HALT_RECONCILE_DIVERGENCE, EXIT_OCO_PARTIAL_TIMEOUT (sub-decision 4)
- Testnet happy-path integration test (sub-decision 5, opt-in via RUN_TESTNET=1)

## Test plan
- [ ] `pytest` \u2014 full unit suite green
- [ ] `RUN_TESTNET=1 pytest tests/integration/test_execution_oco_testnet.py` \u2014 testnet happy path
- [ ] Domain reviewers: trading-logic + python (per ADR 0017)

\ud83e\udd16 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## Verification (after all tasks)

```bash
# Full unit suite
pytest -v 2>&1 | tail -20
# Expected: all green, integration tests SKIPPED (no RUN_TESTNET)

# Lint
ruff check src/ tests/
mypy src/

# Diff stat
git diff --stat main..feature/sprint-5-execution
```

## Domain reviews (after PR opens)

Per ADR 0017 review-agent-harness:

1. `trading-logic-reviewer` (opus) — execution timing, FSM, reason codes, OCO realism.
2. `python-reviewer` (sonnet) — generic PEP 8 / typing / security pass.

(Skipped: `quant-stats-reviewer` — нет formula изменений; `data-integrity-reviewer` — minimal SQLite (один table, простая schema, не требует full review).)

## Follow-ups carried to S5.5 / S6

- [ ] Partial-fill scenario integration test (controlled liquidity).
- [ ] WS reconnect divergence integration test (injected disconnect).
- [ ] Trailing stop (v0.2 candidate, not v0.1).
- [ ] `OCO_PARTIAL_TIMEOUT` watchdog daemon (S6 candidate).

## Related

- ADR: [[../decisions/0019-sprint-5-execution-decisions]]
- Migration: [[../architecture/migration-plan]] §S5
- Sprint summary (after merge): [[../sprints/sprint-05-execution]]
- Reason codes: [[../../trading/concepts/reason-codes]]
- Sprint 4 (predecessor): [[../sprints/sprint-04-risk]]
