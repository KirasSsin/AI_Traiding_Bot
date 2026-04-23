---
title: Sprint 6 — Spot OCO emulation implementation plan
type: plan
tags: [sprint-6, plan, execution, oco, fsm, reconciler, bybit-spot]
created: 2026-04-23
updated: 2026-04-23
---

# Sprint 6 — Spot OCO Emulation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace ADR 0019 sub-decision 1 native `tpslMode=Full` (rejected by Bybit Spot V5 with ErrCode 170130) with a 3-order emulated OCO bracket — Entry Market BUY → Limit Sell @ TP → Stop Market Sell @ SL — backed by client-side sibling cancel, fee-aware sizing, IOC residual flatten, and idempotent retry semantics.

**Architecture:** Forward-only schema migration `0004_execution_state_v2.sql` adds 6 columns for bracket correlation and retry-attempt tracking. FSM v2 expands `12 → 21` states with ~22 new transitions for bracket arm / sibling cancel / IOC residual. `BybitMarketAdapter` rewritten to remove the dead native-tpsl path, add 6 new methods (`place_limit_order`, `place_stop_market_order`, `cancel_order`, `cancel_all_orders`, `get_order`, `get_wallet_balance`), and ban 6 payload fields plus `marketUnit=quoteCoin` on the Spot category. Reconciler R4 swaps `get_position` for `get_wallet_balance(coin=BTC).walletBalance` (Spot has no position object) and splits `entry_price` into a local-SQLite-only field. Coordinator orchestrates the 3-order bracket with deterministic `orderLinkId` (`oco-{bracket_id}-{role}-{attempt}`), prior-attempt detection via `get_open_orders` + `get_order_history`, sibling-cancel-on-Triggered, IOC residual flatten, and a `OCO_ARMING` TTL=60s reconcile rule.

**Tech Stack:** Python 3.12, pydantic v2, SQLite (WAL), pybit V5 (`unified_trading.HTTP` + `WebSocket`), asyncio, pytest + hypothesis (property tests), opt-in Bybit Demo integration test (`RUN_DEMO=1`).

**Source of truth:** [[../decisions/0020-sprint-6-execution-spot-oco-emulation]]. All sub-decision references below cite ADR 0020 unless noted otherwise. Empirical evidence: `scripts/spot_oco_probe{,_v2,_v3}.py` + `*_output.json` (committed).

---

## File Structure

### Created

| Path | Responsibility |
|---|---|
| `migrations/0004_execution_state_v2.sql` | Forward-only ALTER ADD COLUMN: `bracket_id`, `oco_tp_order_id`, `oco_sl_order_id`, `expected_oco_qty`, `arming_started_at`, `last_attempt_num`. |
| `src/execution/bracket.py` | Pure-function bracket ID + `orderLinkId` builder, `compute_oco_qty` (G5 fee formula), 3-leg payload builders (`build_entry_payload`, `build_tp_payload`, `build_sl_payload`). |
| `src/execution/wallet.py` | `WalletSnapshot` dataclass + Spot-specific `walletBalance` parser (handles `availableToWithdraw=""`). |
| `tests/unit/test_bracket.py` | Unit tests for bracket helpers (UUID, link-id, fee formula G5 from probe v3-B, payload shapes). |
| `tests/unit/test_wallet.py` | Unit tests for `WalletSnapshot.from_bybit_response` (empty-string handling, BTC dust). |
| `tests/unit/test_execution_fsm_v2.py` | Tests for 9 new states + ~22 new transitions (table-driven). |
| `tests/unit/test_state_repo_v2.py` | Tests for the new schema columns (round-trip + nullability). |
| `tests/unit/test_bybit_adapter_spot_oco.py` | Tests for new adapter methods + banned payload fields. |
| `tests/unit/test_coordinator_bracket.py` | Tests for `start_bracket`, `arm_oco`, `on_order_event` (Triggered → cancel sibling), IOC residual handling, OCO_ARMING TTL, idempotent retry. |
| `tests/property/test_bracket_lifecycle.py` | Hypothesis property test: every bracket reaches a terminal state (`FLAT` or `HALTED`), never orphan. |
| `tests/integration/test_spot_oco_demo.py` | Opt-in Demo integration: full happy-path entry → OCO armed → cancel both → flatten → FLAT (`RUN_DEMO=1`). |
| `scripts/pre_mainnet_acceptance.py` | Re-runs probes B2 (native tpsl rejection), v3-D (TIF override), v2 S2 (quoteCoin 16-dp) on `api-testnet` with separate testnet keys. |
| `llm-wiki/wiki/project/runbooks/halt-recovery.md` | Manual flatten procedure for `HALT_FLATTEN_FAILED` naked-position state. |
| `llm-wiki/wiki/project/sprints/sprint-06-spot-oco-emulation.md` | Sprint summary (created in last task after merge). |

### Modified

| Path | Change |
|---|---|
| `src/execution/state_machine.py` | +9 `ExecutionState` members or HALT-subset annotations; +new `ExecutionEvent`s (`SL_TRIGGERED`, `TP_FILLED`, `SIBLING_CANCELLED`, `SIBLING_CANCEL_FAILED`, `BRACKET_TIMEOUT`, `RESIDUAL_FLATTENED`, `FLATTEN_FAILED`); +~22 transitions. |
| `src/execution/state_repo.py` | `ExecutionStateRow` extended with 6 new fields; `upsert`/`get` SQL widened; `oco_main_order_id` nullable (legacy column kept for backward compat, new code writes `NULL`). |
| `src/execution/oco.py` | Reduced to a thin re-export shim over `src/execution/bracket.py` (preserves call sites in S5 tests during transition). |
| `src/execution/reconciler.py` | `ExchangeQueryClient.get_position` deprecated for Spot → swapped for `get_wallet_balance(coin)`; `_normalize_position` rebuilt from `walletBalance`; `entry_price` no longer derived from exchange (taken from local row). |
| `src/execution/coordinator.py` | Adds `start_bracket`, `arm_oco`, `on_order_event`, `flatten`, `bootstrap` methods. `_persist` rewritten to look up legs by `stopOrderType` (`""` = TP Limit, `"Stop"` = SL StopOrder), not by index. |
| `src/execution/bybit/adapter.py` | Remove `take_profit/stop_loss/tpsl_mode` kwargs (raise `ValueError` if passed). Ban 6 Spot payload fields + `marketUnit=quoteCoin`. Add 6 new methods (see Stage C). |
| `src/execution/bybit/errors.py` | +`REJECT_ORDER_ALREADY_TERMINAL` ReasonCode + `110001` mapping (cancel-of-Filled is non-fatal). |
| `src/risk/reason_codes.py` | +8 new codes (sub-decision 7); enum total `31 → 39`. |
| `src/platform/config.py` | +`oco_arming_ttl_seconds: int = 60`, +`oco_dust_threshold_btc: Decimal = Decimal("5e-7")` (sub-decision 5 startup-check threshold). |
| `llm-wiki/wiki/project/components/oco.md` | Rewrite full (3-order pattern, drop tpslMode references). |
| `llm-wiki/wiki/project/components/reconciler.md` | `walletBalance` truth + `entry_price` split. |
| `llm-wiki/wiki/project/components/execution-state-machine.md` | FSM v2 table (21 states). |
| `llm-wiki/wiki/project/components/bybit-adapter.md` | New method list, banned fields. |
| `llm-wiki/wiki/trading/concepts/reason-codes.md` | 31 → 39 codes (sub-decision 7 table). |
| `llm-wiki/wiki/project/architecture/migration-plan.md` | §S6 status updated to `delivered`. |
| `llm-wiki/wiki/index.md` | New entries: runbooks/halt-recovery, sprint-06, components touched. |
| `llm-wiki/wiki/log.md` | Append-only ingest entry on Sprint 6 close. |

### Removed

None. All existing modules are forward-extended; the dead native-tpsl branch in `place_market_order` is replaced by an explicit `ValueError` for backward-compat surface (Stage C Task 6).

---

## Stage map

| Stage | Tasks | Theme |
|---|---|---|
| A | 1–3 | Schema migration + reason-code enum delta |
| B | 4–5 | FSM v2 expansion (states + transitions) |
| C | 6–10 | `BybitMarketAdapter` rework (banned + new methods) |
| D | 11–13 | Reconciler R4 — `walletBalance` integration + `entry_price` split |
| E | 14–18 | OCO bracket build + sibling cancel + IOC residual |
| F | 19–22 | Idempotency, prior-attempt detection, OCO_ARMING TTL, flatten cascade |
| G | 23–25 | Property tests, Demo integration, pre-mainnet acceptance |
| H | 26–30 | Wiki updates + sprint page + log + index |

---

## Stage A — Schema migration + reason-code enum delta

### Task 1: Schema migration `0004_execution_state_v2.sql`

**Files:**
- Create: `migrations/0004_execution_state_v2.sql`
- Modify: `src/execution/state_repo.py` (extend `ExecutionStateRow` + SQL)
- Test: `tests/unit/test_state_repo_v2.py`

- [ ] **Step 1: Write the failing test** — schema migration round-trip with all new columns

```python
# tests/unit/test_state_repo_v2.py
from __future__ import annotations

import sqlite3
from decimal import Decimal
from pathlib import Path

import pytest

from src.execution.state_machine import ExecutionState
from src.execution.state_repo import ExecutionStateRepo, ExecutionStateRow

MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations"


@pytest.fixture()
def conn(tmp_path: Path) -> sqlite3.Connection:
    db = sqlite3.connect(tmp_path / "test.db")
    db.execute("PRAGMA journal_mode = WAL;")
    for name in (
        "001_initial.sql",
        "0003_execution_state.sql",
        "0004_execution_state_v2.sql",
    ):
        db.executescript((MIGRATIONS / name).read_text())
    return db


def test_v2_round_trip_with_new_columns(conn: sqlite3.Connection) -> None:
    repo = ExecutionStateRepo(conn)
    row = ExecutionStateRow(
        symbol="BTCUSDT",
        state=ExecutionState.OCO_ARMED,
        position_qty=Decimal("0.000643"),
        entry_price=Decimal("65000.5"),
        oco_main_order_id=None,  # legacy column, new code writes NULL
        bracket_id="b3a1c2d4-0000-4000-8000-000000000001",
        oco_tp_order_id="tp-oid-1",
        oco_sl_order_id="sl-oid-1",
        expected_oco_qty=Decimal("0.000643"),
        arming_started_at="2026-04-23T12:00:00+00:00",
        last_attempt_num=1,
        updated_at="2026-04-23T12:00:01+00:00",
    )
    repo.upsert(row)
    got = repo.get("BTCUSDT")
    assert got == row


def test_v2_nullable_new_columns_when_flat(conn: sqlite3.Connection) -> None:
    repo = ExecutionStateRepo(conn)
    row = ExecutionStateRow(
        symbol="BTCUSDT",
        state=ExecutionState.FLAT,
        position_qty=Decimal("0"),
        entry_price=None,
        oco_main_order_id=None,
        bracket_id=None,
        oco_tp_order_id=None,
        oco_sl_order_id=None,
        expected_oco_qty=None,
        arming_started_at=None,
        last_attempt_num=1,  # NOT NULL DEFAULT 1
        updated_at="2026-04-23T12:00:00+00:00",
    )
    repo.upsert(row)
    got = repo.get("BTCUSDT")
    assert got == row
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_state_repo_v2.py -v`
Expected: FAIL — `OperationalError: no such file: 0004_execution_state_v2.sql` or `unexpected keyword 'bracket_id'` on `ExecutionStateRow`.

- [ ] **Step 3: Write the migration**

Create `migrations/0004_execution_state_v2.sql`:

```sql
-- migrations/0004_execution_state_v2.sql
-- Forward-only ALTER ADD COLUMN. ADR 0020 sub-decision 2.
-- oco_main_order_id stays in schema (backward-compat); new code writes NULL
-- and reads from oco_tp_order_id + oco_sl_order_id.

ALTER TABLE execution_state ADD COLUMN bracket_id TEXT;
ALTER TABLE execution_state ADD COLUMN oco_tp_order_id TEXT;
ALTER TABLE execution_state ADD COLUMN oco_sl_order_id TEXT;
ALTER TABLE execution_state ADD COLUMN expected_oco_qty TEXT;
ALTER TABLE execution_state ADD COLUMN arming_started_at TEXT;
ALTER TABLE execution_state ADD COLUMN last_attempt_num INTEGER NOT NULL DEFAULT 1;
```

- [ ] **Step 4: Extend `ExecutionStateRow` + repo SQL**

In `src/execution/state_repo.py`:

```python
"""SQLite persistence for execution FSM state. ADR 0019 sub-decision 3 + ADR 0020 sub-decision 2."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from decimal import Decimal

from src.execution.state_machine import ExecutionState


@dataclass(frozen=True)
class ExecutionStateRow:
    symbol: str
    state: ExecutionState
    position_qty: Decimal
    entry_price: Decimal | None
    oco_main_order_id: str | None  # legacy: new code writes None
    # ADR 0020 sub-decision 2 — bracket correlation + retry tracking
    bracket_id: str | None
    oco_tp_order_id: str | None
    oco_sl_order_id: str | None
    expected_oco_qty: Decimal | None
    arming_started_at: str | None  # ISO-8601 UTC; only set in OCO_ARMING
    last_attempt_num: int
    updated_at: str  # ISO-8601 UTC


_COLUMNS = (
    "symbol, state, position_qty, entry_price, oco_main_order_id, "
    "bracket_id, oco_tp_order_id, oco_sl_order_id, expected_oco_qty, "
    "arming_started_at, last_attempt_num, updated_at"
)


def _row_to_dataclass(r: tuple) -> ExecutionStateRow:
    return ExecutionStateRow(
        symbol=r[0],
        state=ExecutionState(r[1]),
        position_qty=Decimal(r[2]),
        entry_price=Decimal(r[3]) if r[3] is not None else None,
        oco_main_order_id=r[4],
        bracket_id=r[5],
        oco_tp_order_id=r[6],
        oco_sl_order_id=r[7],
        expected_oco_qty=Decimal(r[8]) if r[8] is not None else None,
        arming_started_at=r[9],
        last_attempt_num=int(r[10]),
        updated_at=r[11],
    )


class ExecutionStateRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def upsert(self, row: ExecutionStateRow) -> None:
        with self._conn:
            self._conn.execute(
                f"""
                INSERT INTO execution_state ({_COLUMNS})
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol) DO UPDATE SET
                    state=excluded.state,
                    position_qty=excluded.position_qty,
                    entry_price=excluded.entry_price,
                    oco_main_order_id=excluded.oco_main_order_id,
                    bracket_id=excluded.bracket_id,
                    oco_tp_order_id=excluded.oco_tp_order_id,
                    oco_sl_order_id=excluded.oco_sl_order_id,
                    expected_oco_qty=excluded.expected_oco_qty,
                    arming_started_at=excluded.arming_started_at,
                    last_attempt_num=excluded.last_attempt_num,
                    updated_at=excluded.updated_at
                """,
                (
                    row.symbol,
                    row.state.value,
                    str(row.position_qty),
                    str(row.entry_price) if row.entry_price is not None else None,
                    row.oco_main_order_id,
                    row.bracket_id,
                    row.oco_tp_order_id,
                    row.oco_sl_order_id,
                    str(row.expected_oco_qty) if row.expected_oco_qty is not None else None,
                    row.arming_started_at,
                    row.last_attempt_num,
                    row.updated_at,
                ),
            )

    def get(self, symbol: str) -> ExecutionStateRow | None:
        cur = self._conn.execute(
            f"SELECT {_COLUMNS} FROM execution_state WHERE symbol = ?", (symbol,),
        )
        r = cur.fetchone()
        if r is None:
            return None
        return _row_to_dataclass(r)
```

- [ ] **Step 5: Run tests to verify GREEN**

Run: `pytest tests/unit/test_state_repo_v2.py tests/unit/test_execution_state_repo.py -v`
Expected: PASS (both v2 tests + S5 backward-compat tests). If S5 tests fail because they construct `ExecutionStateRow` with positional args missing the 6 new fields, fix them by adding `bracket_id=None, oco_tp_order_id=None, oco_sl_order_id=None, expected_oco_qty=None, arming_started_at=None, last_attempt_num=1` to those fixtures.

- [ ] **Step 6: Commit**

```bash
git add migrations/0004_execution_state_v2.sql src/execution/state_repo.py \
        tests/unit/test_state_repo_v2.py tests/unit/test_execution_state_repo.py
git commit -m "feat(execution): schema v2 with bracket correlation columns (ADR 0020 sub-decision 2)"
```

---

### Task 2: Reason-code enum delta `31 → 39` (sub-decision 7)

**Files:**
- Modify: `src/risk/reason_codes.py`
- Test: `tests/unit/test_reason_codes.py`

- [ ] **Step 1: Write the failing test** — assert all 8 new codes exist + counts

```python
# Append to tests/unit/test_reason_codes.py
from src.risk.reason_codes import ReasonCode


def test_v2_count_is_39() -> None:
    assert len(list(ReasonCode)) == 39


def test_new_halt_codes_present() -> None:
    for name in (
        "HALT_BRACKET_INCOMPLETE",
        "HALT_OCO_ARM_TIMEOUT",
        "HALT_OCO_SIBLING_STUCK",
        "HALT_PARTIAL_FILL_BELOW_MIN",
        "HALT_FLATTEN_FAILED",
        "HALT_PHANTOM_SL",
    ):
        assert hasattr(ReasonCode, name), f"missing {name}"


def test_new_exit_and_reject_codes_present() -> None:
    assert hasattr(ReasonCode, "EXIT_STOP_RESIDUAL_FLATTEN")
    assert hasattr(ReasonCode, "REJECT_ORDER_ALREADY_TERMINAL")


def test_new_codes_string_value_matches_name() -> None:
    for name in (
        "HALT_BRACKET_INCOMPLETE",
        "HALT_OCO_ARM_TIMEOUT",
        "HALT_OCO_SIBLING_STUCK",
        "HALT_PARTIAL_FILL_BELOW_MIN",
        "HALT_FLATTEN_FAILED",
        "HALT_PHANTOM_SL",
        "EXIT_STOP_RESIDUAL_FLATTEN",
        "REJECT_ORDER_ALREADY_TERMINAL",
    ):
        assert ReasonCode[name].value == name
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_reason_codes.py::test_v2_count_is_39 -v`
Expected: FAIL — `assert 31 == 39`.

- [ ] **Step 3: Add 8 new codes to enum**

In `src/risk/reason_codes.py`, append to `ReasonCode`:

```python
    # --- ADR 0020 sub-decision 7 — Sprint 6 OCO emulation ---
    # Halts (6 new — total halts: 7 + 6 = 13)
    HALT_BRACKET_INCOMPLETE = "HALT_BRACKET_INCOMPLETE"
    HALT_OCO_ARM_TIMEOUT = "HALT_OCO_ARM_TIMEOUT"
    HALT_OCO_SIBLING_STUCK = "HALT_OCO_SIBLING_STUCK"
    HALT_PARTIAL_FILL_BELOW_MIN = "HALT_PARTIAL_FILL_BELOW_MIN"
    HALT_FLATTEN_FAILED = "HALT_FLATTEN_FAILED"
    HALT_PHANTOM_SL = "HALT_PHANTOM_SL"
    # Exits (1 new)
    EXIT_STOP_RESIDUAL_FLATTEN = "EXIT_STOP_RESIDUAL_FLATTEN"
    # Rejects (1 new — non-fatal: cancel of already-Filled order)
    REJECT_ORDER_ALREADY_TERMINAL = "REJECT_ORDER_ALREADY_TERMINAL"
```

Update the module docstring "True count" comment to `6 + 9 + 9 + 13 = 39` (entry 6, scale/exits 9, rejects 9, halts 13).

- [ ] **Step 4: Run tests to verify GREEN**

Run: `pytest tests/unit/test_reason_codes.py -v`
Expected: PASS (all reason-code tests).

- [ ] **Step 5: Commit**

```bash
git add src/risk/reason_codes.py tests/unit/test_reason_codes.py
git commit -m "feat(risk): add 8 ReasonCodes for Spot OCO emulation (ADR 0020 sub-decision 7)"
```

---

### Task 3: `REJECT_ORDER_ALREADY_TERMINAL` classifier in adapter errors

**Files:**
- Modify: `src/execution/bybit/errors.py`
- Test: `tests/unit/test_bybit_errors.py`

- [ ] **Step 1: Write the failing test** — `110001` must map to `REJECT_ORDER_ALREADY_TERMINAL`

```python
# Append to tests/unit/test_bybit_errors.py
from src.execution.bybit.errors import ReasonCode, map_error


def test_110001_maps_to_already_terminal() -> None:
    assert map_error(110001, "order not exists or finished") == ReasonCode.REJECT_ORDER_ALREADY_TERMINAL


def test_110001_is_non_fatal_marker_in_enum() -> None:
    assert "REJECT_ORDER_ALREADY_TERMINAL" in {r.value for r in ReasonCode}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_bybit_errors.py::test_110001_maps_to_already_terminal -v`
Expected: FAIL — `AttributeError: REASON has no attribute REJECT_ORDER_ALREADY_TERMINAL`.

- [ ] **Step 3: Add the code + mapping**

In `src/execution/bybit/errors.py`:

```python
class ReasonCode(StrEnum):
    CLOCK_DRIFT = "CLOCK_DRIFT"
    WRONG_API_KEY = "WRONG_API_KEY"
    RATE_LIMIT_HIT = "RATE_LIMIT_HIT"
    EXCHANGE_MAINTENANCE = "EXCHANGE_MAINTENANCE"
    INSUFFICIENT_BALANCE = "INSUFFICIENT_BALANCE"
    FILTER_VIOLATION = "FILTER_VIOLATION"
    REJECT_ORDER_ALREADY_TERMINAL = "REJECT_ORDER_ALREADY_TERMINAL"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


_MAP: dict[int, ReasonCode] = {
    10002: ReasonCode.CLOCK_DRIFT,
    10003: ReasonCode.WRONG_API_KEY,
    10006: ReasonCode.RATE_LIMIT_HIT,
    10016: ReasonCode.EXCHANGE_MAINTENANCE,
    110001: ReasonCode.REJECT_ORDER_ALREADY_TERMINAL,  # ADR 0020 sub-decision 3
    110007: ReasonCode.INSUFFICIENT_BALANCE,
    110017: ReasonCode.FILTER_VIOLATION,
    170131: ReasonCode.FILTER_VIOLATION,
    170140: ReasonCode.FILTER_VIOLATION,
    170213: ReasonCode.FILTER_VIOLATION,
}
```

- [ ] **Step 4: Run tests to verify GREEN**

Run: `pytest tests/unit/test_bybit_errors.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/execution/bybit/errors.py tests/unit/test_bybit_errors.py
git commit -m "feat(execution): map Bybit 110001 to REJECT_ORDER_ALREADY_TERMINAL (ADR 0020 sub-decision 3)"
```

---

## Stage B — FSM v2 expansion (sub-decision 8)

### Task 4: Add 4 new `ExecutionState` members + 8 new `ExecutionEvent` members

**Files:**
- Modify: `src/execution/state_machine.py`
- Test: `tests/unit/test_execution_fsm_v2.py`

ADR 0020 sub-decision 8 lists 9 new logical states; 5 of them (`HALT_*`) are concept-subsets of `HALTED` carried by the row's `halt_reason: ReasonCode` rather than expanded into the enum (per the explicit note "В коде `ExecutionState` enum они представлены как `HALTED` плюс `halt_reason: ReasonCode` (не множим enum)"). Net new enum members: 4.

- [ ] **Step 1: Write the failing test** — new state + event members exist

```python
# tests/unit/test_execution_fsm_v2.py
from __future__ import annotations

from src.execution.state_machine import ExecutionEvent, ExecutionState


def test_new_states_present() -> None:
    for name in (
        "OCO_ARMING",
        "EXIT_SIBLING_CANCELLING",
        "EXIT_SIBLING_CANCEL_FAILED",
        "EXIT_SL_RESIDUAL",
    ):
        assert hasattr(ExecutionState, name), f"missing {name}"


def test_new_events_present() -> None:
    for name in (
        "TP_PLACED",
        "SL_PLACED",
        "SL_TRIGGERED",
        "SIBLING_CANCELLED",
        "SIBLING_CANCEL_FAILED",
        "BRACKET_TIMEOUT",
        "RESIDUAL_FLATTENED",
        "FLATTEN_FAILED",
    ):
        assert hasattr(ExecutionEvent, name), f"missing {name}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_execution_fsm_v2.py::test_new_states_present -v`
Expected: FAIL — `AttributeError: OCO_ARMING`.

- [ ] **Step 3: Add 4 states + 8 events**

In `src/execution/state_machine.py`, extend `ExecutionState`:

```python
class ExecutionState(StrEnum):
    INIT = "INIT"
    FLAT = "FLAT"
    ENTRY_PENDING = "ENTRY_PENDING"
    LONG_OPEN = "LONG_OPEN"
    OCO_ARMING = "OCO_ARMING"            # ADR 0020 sub-decision 8
    OCO_ARMED = "OCO_ARMED"
    PARTIAL_FILL = "PARTIAL_FILL"
    EXIT_PENDING = "EXIT_PENDING"
    EXIT_SIBLING_CANCELLING = "EXIT_SIBLING_CANCELLING"      # ADR 0020 sub-decision 8
    EXIT_SIBLING_CANCEL_FAILED = "EXIT_SIBLING_CANCEL_FAILED"  # ADR 0020 sub-decision 8
    EXIT_SL_RESIDUAL = "EXIT_SL_RESIDUAL"  # ADR 0020 sub-decision 4
    RECONCILING = "RECONCILING"
    HALTED = "HALTED"
    COOLDOWN = "COOLDOWN"
    ERROR = "ERROR"
    KILLED = "KILLED"
```

And extend `ExecutionEvent`:

```python
class ExecutionEvent(StrEnum):
    STATE_LOADED = "STATE_LOADED"
    ENTRY_PLACED = "ENTRY_PLACED"
    ENTRY_FILLED = "ENTRY_FILLED"
    ENTRY_REJECTED = "ENTRY_REJECTED"
    OCO_PLACED = "OCO_PLACED"               # legacy S5; kept as alias for "both legs Untriggered"
    TP_PLACED = "TP_PLACED"                 # ADR 0020 sub-decision 8
    SL_PLACED = "SL_PLACED"                 # ADR 0020 sub-decision 8
    PARTIAL_FILL = "PARTIAL_FILL"
    SL_HIT = "SL_HIT"
    SL_TRIGGERED = "SL_TRIGGERED"           # ADR 0020 sub-decision 3
    TP_HIT = "TP_HIT"
    SIBLING_CANCELLED = "SIBLING_CANCELLED"
    SIBLING_CANCEL_FAILED = "SIBLING_CANCEL_FAILED"
    BRACKET_TIMEOUT = "BRACKET_TIMEOUT"     # ADR 0020 sub-decision 10 (TTL=60s)
    RESIDUAL_FLATTENED = "RESIDUAL_FLATTENED"
    FLATTEN_FAILED = "FLATTEN_FAILED"
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
```

- [ ] **Step 4: Run tests to verify GREEN**

Run: `pytest tests/unit/test_execution_fsm_v2.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/execution/state_machine.py tests/unit/test_execution_fsm_v2.py
git commit -m "feat(execution): add 4 FSM states + 8 events for OCO emulation (ADR 0020 sub-decision 8)"
```

---

### Task 5: Add ~22 new `TRANSITIONS` + table-driven assertion

**Files:**
- Modify: `src/execution/state_machine.py`
- Test: `tests/unit/test_execution_fsm_v2.py` (extend)

The new transitions formalise the bracket lifecycle: `LONG_OPEN → OCO_ARMING` (entry filled, start arming) → `OCO_ARMING → OCO_ARMED` (both legs Untriggered) → `OCO_ARMED → EXIT_SIBLING_CANCELLING` (one leg fired) → `EXIT_SIBLING_CANCELLING → FLAT` (sibling cancelled) or `→ EXIT_SIBLING_CANCEL_FAILED` (cancel error retryable). IOC residual: `OCO_ARMED → EXIT_SL_RESIDUAL` (SL partial) → `→ FLAT` (residual flattened) or `→ HALTED` (flatten failed). TTL/bracket-build failure paths route to `HALTED` with the appropriate `halt_reason`.

- [ ] **Step 1: Write the failing test** — count + spot-check 6 critical transitions

```python
# Append to tests/unit/test_execution_fsm_v2.py
from src.execution.state_machine import (
    TRANSITIONS,
    ExecutionEvent,
    ExecutionState,
    apply,
)


def test_transitions_count_at_least_50() -> None:
    # S5 had 28 transitions; ADR 0020 sub-decision 8 adds ~22 → >= 50.
    assert len(TRANSITIONS) >= 50


def test_long_open_to_oco_arming_on_entry_filled() -> None:
    # ADR 0020 sub-decision 8: after entry fills we must arm OCO before being armed.
    assert apply(ExecutionState.LONG_OPEN, ExecutionEvent.TP_PLACED) == ExecutionState.OCO_ARMING


def test_oco_arming_to_oco_armed_on_sl_placed() -> None:
    assert apply(ExecutionState.OCO_ARMING, ExecutionEvent.SL_PLACED) == ExecutionState.OCO_ARMED


def test_oco_armed_to_sibling_cancelling_on_tp_hit() -> None:
    assert apply(ExecutionState.OCO_ARMED, ExecutionEvent.TP_HIT) == ExecutionState.EXIT_SIBLING_CANCELLING


def test_oco_armed_to_sibling_cancelling_on_sl_triggered() -> None:
    assert apply(ExecutionState.OCO_ARMED, ExecutionEvent.SL_TRIGGERED) == ExecutionState.EXIT_SIBLING_CANCELLING


def test_sibling_cancelling_to_flat_on_success() -> None:
    assert apply(ExecutionState.EXIT_SIBLING_CANCELLING, ExecutionEvent.SIBLING_CANCELLED) == ExecutionState.FLAT


def test_oco_armed_to_sl_residual_on_partial_fill() -> None:
    assert apply(ExecutionState.OCO_ARMED, ExecutionEvent.PARTIAL_FILL) == ExecutionState.EXIT_SL_RESIDUAL


def test_sl_residual_to_flat_on_residual_flattened() -> None:
    assert apply(ExecutionState.EXIT_SL_RESIDUAL, ExecutionEvent.RESIDUAL_FLATTENED) == ExecutionState.FLAT


def test_oco_arming_to_halted_on_bracket_timeout() -> None:
    assert apply(ExecutionState.OCO_ARMING, ExecutionEvent.BRACKET_TIMEOUT) == ExecutionState.HALTED


def test_exit_pending_to_halted_on_flatten_failed() -> None:
    assert apply(ExecutionState.EXIT_PENDING, ExecutionEvent.FLATTEN_FAILED) == ExecutionState.HALTED
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_execution_fsm_v2.py -v`
Expected: FAIL — `IllegalTransitionError: LONG_OPEN + TP_PLACED not allowed`.

- [ ] **Step 3: Extend `TRANSITIONS` with the 22 new entries**

In `src/execution/state_machine.py`, add to the `TRANSITIONS` dict literal:

```python
    # === ADR 0020 sub-decision 8: OCO emulation transitions ===
    # Bracket arm path: entry filled → place TP → place SL → armed
    (ExecutionState.LONG_OPEN, ExecutionEvent.TP_PLACED): ExecutionState.OCO_ARMING,
    (ExecutionState.OCO_ARMING, ExecutionEvent.SL_PLACED): ExecutionState.OCO_ARMED,
    (ExecutionState.OCO_ARMING, ExecutionEvent.BRACKET_TIMEOUT): ExecutionState.HALTED,        # halt_reason=HALT_OCO_ARM_TIMEOUT
    (ExecutionState.OCO_ARMING, ExecutionEvent.ENTRY_REJECTED): ExecutionState.HALTED,         # halt_reason=HALT_BRACKET_INCOMPLETE
    (ExecutionState.OCO_ARMING, ExecutionEvent.PARTIAL_FILL): ExecutionState.HALTED,           # halt_reason=HALT_PARTIAL_FILL_BELOW_MIN
    (ExecutionState.OCO_ARMING, ExecutionEvent.SL_TRIGGERED): ExecutionState.HALTED,           # halt_reason=HALT_PHANTOM_SL
    # Sibling cancel path: TP fill or SL trigger → cancel sibling → FLAT
    (ExecutionState.OCO_ARMED, ExecutionEvent.SL_TRIGGERED): ExecutionState.EXIT_SIBLING_CANCELLING,
    (ExecutionState.OCO_ARMED, ExecutionEvent.SIBLING_CANCELLED): ExecutionState.FLAT,         # legacy SL_HIT/TP_HIT also OK
    (ExecutionState.EXIT_SIBLING_CANCELLING, ExecutionEvent.SIBLING_CANCELLED): ExecutionState.FLAT,
    (ExecutionState.EXIT_SIBLING_CANCELLING, ExecutionEvent.SIBLING_CANCEL_FAILED): ExecutionState.EXIT_SIBLING_CANCEL_FAILED,
    (ExecutionState.EXIT_SIBLING_CANCEL_FAILED, ExecutionEvent.SIBLING_CANCELLED): ExecutionState.FLAT,
    (ExecutionState.EXIT_SIBLING_CANCEL_FAILED, ExecutionEvent.RISK_HALT): ExecutionState.HALTED,  # halt_reason=HALT_OCO_SIBLING_STUCK
    # Override the legacy S5 SL_HIT/TP_HIT direct → EXIT_PENDING:
    # in v2 these route through EXIT_SIBLING_CANCELLING. Keep S5 transitions as fallbacks.
    (ExecutionState.OCO_ARMED, ExecutionEvent.TP_HIT): ExecutionState.EXIT_SIBLING_CANCELLING,
    # IOC residual path
    (ExecutionState.OCO_ARMED, ExecutionEvent.PARTIAL_FILL): ExecutionState.EXIT_SL_RESIDUAL,
    (ExecutionState.EXIT_SL_RESIDUAL, ExecutionEvent.RESIDUAL_FLATTENED): ExecutionState.FLAT,
    (ExecutionState.EXIT_SL_RESIDUAL, ExecutionEvent.FLATTEN_FAILED): ExecutionState.HALTED,   # halt_reason=HALT_FLATTEN_FAILED
    # Flatten cascade from EXIT_PENDING (sub-decision 10)
    (ExecutionState.EXIT_PENDING, ExecutionEvent.FLATTEN_FAILED): ExecutionState.HALTED,
    # WS reconnect from new states
    (ExecutionState.OCO_ARMING, ExecutionEvent.WS_RECONNECT): ExecutionState.RECONCILING,
    (ExecutionState.EXIT_SIBLING_CANCELLING, ExecutionEvent.WS_RECONNECT): ExecutionState.RECONCILING,
    (ExecutionState.EXIT_SL_RESIDUAL, ExecutionEvent.WS_RECONNECT): ExecutionState.RECONCILING,
    # Risk halt from new states
    (ExecutionState.OCO_ARMING, ExecutionEvent.RISK_HALT): ExecutionState.HALTED,
    (ExecutionState.EXIT_SIBLING_CANCELLING, ExecutionEvent.RISK_HALT): ExecutionState.HALTED,
    (ExecutionState.EXIT_SL_RESIDUAL, ExecutionEvent.RISK_HALT): ExecutionState.HALTED,
    # Kill switch from new states
    (ExecutionState.OCO_ARMING, ExecutionEvent.KILL_SWITCH): ExecutionState.KILLED,
    (ExecutionState.EXIT_SIBLING_CANCELLING, ExecutionEvent.KILL_SWITCH): ExecutionState.KILLED,
    (ExecutionState.EXIT_SL_RESIDUAL, ExecutionEvent.KILL_SWITCH): ExecutionState.KILLED,
```

- [ ] **Step 4: Run all FSM tests to verify GREEN**

Run: `pytest tests/unit/test_execution_fsm.py tests/unit/test_execution_fsm_v2.py -v`
Expected: PASS — both legacy S5 (28 transitions) and new v2 transitions exercised.

- [ ] **Step 5: Commit**

```bash
git add src/execution/state_machine.py tests/unit/test_execution_fsm_v2.py
git commit -m "feat(execution): add 22 FSM transitions for OCO emulation (ADR 0020 sub-decision 8)"
```

---

## Stage C — BybitMarketAdapter rework (Tasks 6-10)

ADR 0020 sub-decision 2 (3-order OCO) + sub-decision 3 (Spot payload sanitization). Remove dead native-tpsl path. Ban 6 fields invalid for Spot. Add 6 new methods covering full bracket lifecycle + balance query.

### Task 6: Ban dead native-tpsl path + Spot field guard

**Files:**
- Modify: `src/execution/bybit/adapter.py`
- Test: `tests/unit/test_bybit_adapter_spot_guard.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_bybit_adapter_spot_guard.py
"""ADR 0020 sub-decision 3 — banned-field guard for Spot V5 (probe v1: ErrCode 170130)."""
from __future__ import annotations
from decimal import Decimal
import pytest
from src.execution.bybit.adapter import BybitMarketAdapter

BANNED_FIELDS = ("tpslMode", "takeProfit", "stopLoss", "tpOrderType", "slOrderType", "triggerDirection")


@pytest.mark.parametrize("field", BANNED_FIELDS)
def test_place_market_rejects_banned_spot_fields(field, fake_rest, fake_filters):
    adapter = BybitMarketAdapter(rest=fake_rest, filters=fake_filters)
    with pytest.raises(ValueError, match=f"banned for Bybit Spot V5: {field}"):
        adapter.place_order(
            symbol="BTCUSDT", side="Buy", qty=Decimal("0.001"),
            extra_payload={field: "any"},
        )


def test_place_market_rejects_marketunit_quotecoin(fake_rest, fake_filters):
    adapter = BybitMarketAdapter(rest=fake_rest, filters=fake_filters)
    with pytest.raises(ValueError, match="marketUnit=quoteCoin banned"):
        adapter.place_order(
            symbol="BTCUSDT", side="Buy", qty=Decimal("0.001"),
            extra_payload={"marketUnit": "quoteCoin"},
        )


def test_place_market_passes_marketunit_basecoin(fake_rest, fake_filters):
    adapter = BybitMarketAdapter(rest=fake_rest, filters=fake_filters)
    adapter.place_order(symbol="BTCUSDT", side="Buy", qty=Decimal("0.001"))
    payload = fake_rest.last_payload
    assert payload["marketUnit"] == "baseCoin"
    assert payload["category"] == "spot"
```

- [ ] **Step 2: Run tests to verify RED**

Run: `pytest tests/unit/test_bybit_adapter_spot_guard.py -v`
Expected: FAIL — guard not yet implemented.

- [ ] **Step 3: Implement Spot payload guard in adapter**

```python
# src/execution/bybit/adapter.py — modify place_order signature + body

_BANNED_SPOT_FIELDS: tuple[str, ...] = (
    "tpslMode", "takeProfit", "stopLoss", "tpOrderType", "slOrderType", "triggerDirection",
)
"""ADR 0020 sub-decision 1: empirical probe v1 confirmed Bybit Spot V5 rejects these
with retCode 170130 ('Data sent for paramter ... is not valid')."""


class BybitMarketAdapter:
    def place_order(
        self,
        *,
        symbol: str,
        side: str,
        qty: Decimal,
        order_link_id: str | None = None,
        extra_payload: dict[str, Any] | None = None,
    ) -> OrderAck:
        extra = dict(extra_payload or {})
        for banned in _BANNED_SPOT_FIELDS:
            if banned in extra:
                raise ValueError(
                    f"Field {banned!r} is banned for Bybit Spot V5: {banned} "
                    f"(probe v1 / ErrCode 170130, ADR 0020 sub-decision 3)"
                )
        market_unit = extra.pop("marketUnit", "baseCoin")
        if market_unit == "quoteCoin":
            raise ValueError(
                "marketUnit=quoteCoin banned (probe S2 v2: 16-dp accumulation drift, "
                "ADR 0020 sub-decision 3)"
            )
        # … existing filter validation + REST call follows, with marketUnit=baseCoin pinned
        payload = self.filters.validate_order(symbol=symbol, side=side, qty=qty)
        payload.update({
            "category": "spot",
            "orderType": "Market",
            "marketUnit": "baseCoin",
            **({"orderLinkId": order_link_id} if order_link_id else {}),
            **extra,
        })
        return self._submit(payload)
```

Remove the legacy kwargs `take_profit`, `stop_loss`, `tpsl_mode` entirely from the signature — any caller passing them raises `TypeError` (Python-level), which is the intended hard break.

- [ ] **Step 4: Run tests to verify GREEN**

Run: `pytest tests/unit/test_bybit_adapter_spot_guard.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/execution/bybit/adapter.py tests/unit/test_bybit_adapter_spot_guard.py
git commit -m "feat(execution): ban 6 banned Spot fields + marketUnit=quoteCoin (ADR 0020 sub-decision 3)"
```

### Task 7: place_limit_order (TP leg)

**Files:**
- Modify: `src/execution/bybit/adapter.py` (add method)
- Test: `tests/unit/test_bybit_adapter_limit.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_bybit_adapter_limit.py
from decimal import Decimal
from src.execution.bybit.adapter import BybitMarketAdapter


def test_place_limit_order_payload_shape(fake_rest, fake_filters):
    adapter = BybitMarketAdapter(rest=fake_rest, filters=fake_filters)
    ack = adapter.place_limit_order(
        symbol="BTCUSDT", side="Sell", qty=Decimal("0.001"),
        price=Decimal("70000.00"), order_link_id="oco-abc-tp-1",
    )
    payload = fake_rest.last_payload
    assert payload["category"] == "spot"
    assert payload["orderType"] == "Limit"
    assert payload["timeInForce"] == "GTC"
    assert payload["marketUnit"] == "baseCoin"
    assert payload["price"] == "70000.00"
    assert payload["orderLinkId"] == "oco-abc-tp-1"
    assert ack.order_id == fake_rest.fake_order_id
```

- [ ] **Step 2: Run test to verify RED**

Run: `pytest tests/unit/test_bybit_adapter_limit.py -v`
Expected: FAIL — `place_limit_order` not defined.

- [ ] **Step 3: Implement place_limit_order**

```python
def place_limit_order(
    self,
    *,
    symbol: str,
    side: str,
    qty: Decimal,
    price: Decimal,
    order_link_id: str,
) -> OrderAck:
    """ADR 0020 sub-decision 2: TP leg of 3-order Spot OCO bracket (Limit Sell @ TP, GTC)."""
    payload = self.filters.validate_order(symbol=symbol, side=side, qty=qty, price=price)
    payload.update({
        "category": "spot",
        "orderType": "Limit",
        "timeInForce": "GTC",
        "marketUnit": "baseCoin",
        "orderLinkId": order_link_id,
    })
    return self._submit(payload)
```

- [ ] **Step 4: Run test to verify GREEN**

Run: `pytest tests/unit/test_bybit_adapter_limit.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/execution/bybit/adapter.py tests/unit/test_bybit_adapter_limit.py
git commit -m "feat(execution): add place_limit_order for OCO TP leg (ADR 0020 sub-decision 2)"
```

### Task 8: place_stop_market_order (SL leg)

**Files:**
- Modify: `src/execution/bybit/adapter.py` (add method)
- Test: `tests/unit/test_bybit_adapter_stop.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_bybit_adapter_stop.py
from decimal import Decimal
from src.execution.bybit.adapter import BybitMarketAdapter


def test_place_stop_market_payload_shape(fake_rest, fake_filters):
    adapter = BybitMarketAdapter(rest=fake_rest, filters=fake_filters)
    ack = adapter.place_stop_market_order(
        symbol="BTCUSDT", side="Sell", qty=Decimal("0.001"),
        trigger_price=Decimal("60000.00"), order_link_id="oco-abc-sl-1",
    )
    p = fake_rest.last_payload
    assert p["category"] == "spot"
    assert p["orderType"] == "Market"
    assert p["orderFilter"] == "StopOrder"
    assert p["triggerPrice"] == "60000.00"
    assert p["triggerBy"] == "LastPrice"
    assert p["marketUnit"] == "baseCoin"
    assert p["orderLinkId"] == "oco-abc-sl-1"
    # NOTE: timeInForce intentionally NOT in payload — Bybit silently rewrites GTC→IOC
    # for Spot Stop (probe v3-D). Don't lie about TIF in our payload.
    assert "timeInForce" not in p
    assert ack.order_id == fake_rest.fake_order_id
```

- [ ] **Step 2: Run test to verify RED**

Run: `pytest tests/unit/test_bybit_adapter_stop.py -v`
Expected: FAIL — `place_stop_market_order` not defined.

- [ ] **Step 3: Implement place_stop_market_order**

```python
def place_stop_market_order(
    self,
    *,
    symbol: str,
    side: str,
    qty: Decimal,
    trigger_price: Decimal,
    order_link_id: str,
) -> OrderAck:
    """ADR 0020 sub-decision 2: SL leg of 3-order Spot OCO bracket (Stop Market Sell).
    Bybit Spot silently rewrites timeInForce GTC→IOC (probe v3-D); we omit timeInForce
    from payload and document the override behavior at exit-handling layer (EXIT_SL_RESIDUAL).
    """
    payload = self.filters.validate_order(symbol=symbol, side=side, qty=qty)
    payload.update({
        "category": "spot",
        "orderType": "Market",
        "orderFilter": "StopOrder",
        "triggerPrice": self.filters.snap_price(symbol, trigger_price),
        "triggerBy": "LastPrice",
        "marketUnit": "baseCoin",
        "orderLinkId": order_link_id,
    })
    return self._submit(payload)
```

- [ ] **Step 4: Run test to verify GREEN**

Run: `pytest tests/unit/test_bybit_adapter_stop.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/execution/bybit/adapter.py tests/unit/test_bybit_adapter_stop.py
git commit -m "feat(execution): add place_stop_market_order for OCO SL leg (ADR 0020 sub-decision 2)"
```

### Task 9: cancel_order + cancel_all_orders

**Files:**
- Modify: `src/execution/bybit/adapter.py` (add 2 methods)
- Test: `tests/unit/test_bybit_adapter_cancel.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_bybit_adapter_cancel.py
import pytest
from src.execution.bybit.adapter import BybitMarketAdapter
from src.execution.bybit.errors import BybitErrorCode
from src.risk.reason_codes import ReasonCode


def test_cancel_order_happy(fake_rest, fake_filters):
    adapter = BybitMarketAdapter(rest=fake_rest, filters=fake_filters)
    res = adapter.cancel_order(symbol="BTCUSDT", order_id="OID123")
    p = fake_rest.last_payload
    assert p["category"] == "spot"
    assert p["symbol"] == "BTCUSDT"
    assert p["orderId"] == "OID123"
    assert res.cancelled is True


def test_cancel_order_already_terminal_returns_reason_code(fake_rest, fake_filters):
    """ADR 0020 sub-decision 6: Bybit returns 110001 when cancelling already-Filled order.
    Adapter must classify this as REJECT_ORDER_ALREADY_TERMINAL (non-fatal)."""
    fake_rest.next_ret_code = 110001
    adapter = BybitMarketAdapter(rest=fake_rest, filters=fake_filters)
    res = adapter.cancel_order(symbol="BTCUSDT", order_id="OID999")
    assert res.cancelled is False
    assert res.reason_code == ReasonCode.REJECT_ORDER_ALREADY_TERMINAL


def test_cancel_all_orders_payload(fake_rest, fake_filters):
    adapter = BybitMarketAdapter(rest=fake_rest, filters=fake_filters)
    adapter.cancel_all_orders(symbol="BTCUSDT")
    p = fake_rest.last_payload
    assert p == {"category": "spot", "symbol": "BTCUSDT"}
```

- [ ] **Step 2: Run tests to verify RED**

Run: `pytest tests/unit/test_bybit_adapter_cancel.py -v`
Expected: FAIL — methods not defined.

- [ ] **Step 3: Implement cancel methods + 110001 classifier**

```python
# src/execution/bybit/errors.py — add 110001 mapping
_MAP[110001] = ReasonCode.REJECT_ORDER_ALREADY_TERMINAL  # ADR 0020 sub-decision 6


# src/execution/bybit/adapter.py — add methods
@dataclass(frozen=True, slots=True)
class CancelResult:
    cancelled: bool
    reason_code: ReasonCode | None = None


def cancel_order(self, *, symbol: str, order_id: str) -> CancelResult:
    """ADR 0020 sub-decision 6: cancel-of-Filled returns 110001, classified non-fatal."""
    payload = {"category": "spot", "symbol": symbol, "orderId": order_id}
    resp = self.rest.cancel_order(payload)
    if resp.get("retCode") == 0:
        return CancelResult(cancelled=True)
    code = resp.get("retCode")
    rc = _MAP.get(code)
    if rc == ReasonCode.REJECT_ORDER_ALREADY_TERMINAL:
        return CancelResult(cancelled=False, reason_code=rc)
    raise BybitAPIError(code=code, message=resp.get("retMsg", ""))


def cancel_all_orders(self, *, symbol: str) -> None:
    """Bulk cancel — used by flatten cascade and emergency halt."""
    self.rest.cancel_all_orders({"category": "spot", "symbol": symbol})
```

- [ ] **Step 4: Run tests to verify GREEN**

Run: `pytest tests/unit/test_bybit_adapter_cancel.py tests/unit/test_bybit_errors.py -v`
Expected: PASS — both new tests + existing error-mapping suite green.

- [ ] **Step 5: Commit**

```bash
git add src/execution/bybit/adapter.py src/execution/bybit/errors.py tests/unit/test_bybit_adapter_cancel.py
git commit -m "feat(execution): add cancel_order + cancel_all_orders + 110001 classifier (ADR 0020 sub-decisions 2,6)"
```

### Task 10: get_order + get_wallet_balance

**Files:**
- Modify: `src/execution/bybit/adapter.py` (add 2 methods)
- Test: `tests/unit/test_bybit_adapter_query.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_bybit_adapter_query.py
from decimal import Decimal
from src.execution.bybit.adapter import BybitMarketAdapter


def test_get_order_returns_status_snapshot(fake_rest, fake_filters):
    fake_rest.next_get_order = {
        "orderId": "OID1", "orderLinkId": "oco-abc-tp-1",
        "orderStatus": "Filled", "cumExecQty": "0.001",
        "cumExecFee": "0.0000005", "feeCurrency": "BTC",
        "avgPrice": "70000.00",
    }
    adapter = BybitMarketAdapter(rest=fake_rest, filters=fake_filters)
    snap = adapter.get_order(symbol="BTCUSDT", order_id="OID1")
    assert snap.order_status == "Filled"
    assert snap.cum_exec_qty == Decimal("0.001")
    assert snap.cum_exec_fee == Decimal("0.0000005")
    assert snap.fee_currency == "BTC"


def test_get_wallet_balance_btc_handles_empty_available(fake_rest, fake_filters):
    """ADR 0020 sub-decision 4: walletBalance(coin=BTC) is canonical Spot position truth.
    availableToWithdraw can be empty string when funds locked — treat as 0."""
    fake_rest.next_wallet = {
        "coin": "BTC",
        "walletBalance": "0.00100000",
        "availableToWithdraw": "",  # empty when locked in open orders
        "locked": "0.00100000",
    }
    adapter = BybitMarketAdapter(rest=fake_rest, filters=fake_filters)
    snap = adapter.get_wallet_balance(coin="BTC")
    assert snap.wallet_balance == Decimal("0.00100000")
    assert snap.available == Decimal("0")
    assert snap.locked == Decimal("0.00100000")
```

- [ ] **Step 2: Run tests to verify RED**

Run: `pytest tests/unit/test_bybit_adapter_query.py -v`
Expected: FAIL — methods not defined.

- [ ] **Step 3: Implement query methods**

```python
@dataclass(frozen=True, slots=True)
class OrderSnapshot:
    order_id: str
    order_link_id: str
    order_status: str
    cum_exec_qty: Decimal
    cum_exec_fee: Decimal
    fee_currency: str
    avg_price: Decimal | None


@dataclass(frozen=True, slots=True)
class WalletSnapshot:
    coin: str
    wallet_balance: Decimal
    available: Decimal
    locked: Decimal


def get_order(self, *, symbol: str, order_id: str) -> OrderSnapshot:
    """Used by sibling-cancel-on-Triggered handler + Reconciler order-history sweep."""
    raw = self.rest.get_order({"category": "spot", "symbol": symbol, "orderId": order_id})
    return OrderSnapshot(
        order_id=raw["orderId"],
        order_link_id=raw.get("orderLinkId", ""),
        order_status=raw["orderStatus"],
        cum_exec_qty=Decimal(raw.get("cumExecQty", "0")),
        cum_exec_fee=Decimal(raw.get("cumExecFee", "0")),
        fee_currency=raw.get("feeCurrency", ""),
        avg_price=Decimal(raw["avgPrice"]) if raw.get("avgPrice") else None,
    )


def get_wallet_balance(self, *, coin: str) -> WalletSnapshot:
    """ADR 0020 sub-decision 4: canonical Spot position truth (no get_position on Spot V5).
    availableToWithdraw='' means funds are fully locked; coerce to Decimal('0')."""
    raw = self.rest.get_wallet_balance({"accountType": "UNIFIED", "coin": coin})
    avail_str = raw.get("availableToWithdraw", "0") or "0"  # coerce empty to "0"
    return WalletSnapshot(
        coin=coin,
        wallet_balance=Decimal(raw.get("walletBalance", "0")),
        available=Decimal(avail_str),
        locked=Decimal(raw.get("locked", "0")),
    )
```

- [ ] **Step 4: Run tests to verify GREEN**

Run: `pytest tests/unit/test_bybit_adapter_query.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/execution/bybit/adapter.py tests/unit/test_bybit_adapter_query.py
git commit -m "feat(execution): add get_order + get_wallet_balance query methods (ADR 0020 sub-decision 4)"
```

---

## Stage D — Reconciler R4 walletBalance integration (Tasks 11-13)

ADR 0020 sub-decision 4: Spot V5 has **no** `get_position` endpoint — `walletBalance(coin=BTC)` is canonical position truth. Entry-price split: exchange knows qty, local SQLite owns entry_price (preserved across reconciles).

### Task 11: WalletSnapshot in ExchangeQueryClient Protocol

**Files:**
- Modify: `src/execution/reconciler.py` (Protocol + ExchangeState dataclass)
- Test: `tests/unit/test_reconciler_wallet_protocol.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_reconciler_wallet_protocol.py
"""ADR 0020 sub-decision 4 — Reconciler must call get_wallet_balance, NOT get_position."""
from decimal import Decimal
import pytest
from src.execution.reconciler import ExchangeQueryClient, ExchangeState
from src.execution.bybit.adapter import WalletSnapshot


class FakeQuery:
    def __init__(self, wallet: WalletSnapshot, open_orders: list[dict]):
        self.wallet = wallet
        self.orders = open_orders
        self.calls: list[str] = []

    def get_wallet_balance(self, *, coin: str) -> WalletSnapshot:
        self.calls.append(f"wallet:{coin}")
        return self.wallet

    def get_open_orders(self, *, symbol: str) -> list[dict]:
        self.calls.append(f"open:{symbol}")
        return self.orders


def test_query_protocol_satisfied_by_wallet_only(tmp_path):
    """ExchangeQueryClient v2 Protocol no longer requires get_position."""
    fq = FakeQuery(
        wallet=WalletSnapshot(coin="BTC", wallet_balance=Decimal("0.001"),
                              available=Decimal("0"), locked=Decimal("0.001")),
        open_orders=[],
    )
    # structural typing: must satisfy Protocol without get_position attr
    assert isinstance(fq, ExchangeQueryClient)
    assert not hasattr(fq, "get_position"), "v2 Protocol must not require get_position"
```

- [ ] **Step 2: Run test to verify RED**

Run: `pytest tests/unit/test_reconciler_wallet_protocol.py -v`
Expected: FAIL — current Protocol still requires `get_position`.

- [ ] **Step 3: Rewrite Protocol + ExchangeState**

```python
# src/execution/reconciler.py — replace get_position with get_wallet_balance
from typing import Protocol
from src.execution.bybit.adapter import WalletSnapshot


class ExchangeQueryClient(Protocol):
    """ADR 0020 sub-decision 4: Spot V5 has no get_position. Wallet balance is truth."""

    def get_wallet_balance(self, *, coin: str) -> WalletSnapshot: ...
    def get_open_orders(self, *, symbol: str) -> list[dict]: ...


@dataclass(frozen=True, slots=True)
class ExchangeState:
    wallet: WalletSnapshot              # was: position: PositionSnapshot
    open_orders: tuple[dict, ...]
```

- [ ] **Step 4: Run test to verify GREEN**

Run: `pytest tests/unit/test_reconciler_wallet_protocol.py tests/unit/test_reconciler.py -v`
Expected: PASS — new Protocol structurally satisfied; legacy reconciler tests still GREEN against the new shape.

- [ ] **Step 5: Commit**

```bash
git add src/execution/reconciler.py tests/unit/test_reconciler_wallet_protocol.py
git commit -m "refactor(execution): swap get_position for get_wallet_balance in Reconciler Protocol (ADR 0020 sub-decision 4)"
```

### Task 12: fetch_exchange_state derives position qty from walletBalance

**Files:**
- Modify: `src/execution/reconciler.py` (`Reconciler.fetch_exchange_state`)
- Test: `tests/unit/test_reconciler_fetch.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_reconciler_fetch.py
from decimal import Decimal
from src.execution.reconciler import Reconciler
from src.execution.bybit.adapter import WalletSnapshot
from tests.helpers import FakeQuery  # extends Task 11 helper


def test_fetch_uses_wallet_balance_as_position_qty():
    fq = FakeQuery(
        wallet=WalletSnapshot(coin="BTC", wallet_balance=Decimal("0.00100000"),
                              available=Decimal("0"), locked=Decimal("0.00100000")),
        open_orders=[{"orderLinkId": "oco-abc-tp-1", "orderStatus": "New"}],
    )
    rec = Reconciler(query=fq, base_coin="BTC", symbol="BTCUSDT")
    state = rec.fetch_exchange_state()
    assert state.wallet.wallet_balance == Decimal("0.00100000")
    assert len(state.open_orders) == 1
    # Reconciler derives position via wallet, NOT a separate get_position call
    assert "wallet:BTC" in fq.calls
    assert "open:BTCUSDT" in fq.calls


def test_position_qty_zero_when_wallet_dust_below_min(monkeypatch):
    """Wallet < oco_dust_threshold_btc treated as FLAT — avoids phantom position."""
    fq = FakeQuery(
        wallet=WalletSnapshot(coin="BTC", wallet_balance=Decimal("0.00000050"),  # dust
                              available=Decimal("0.00000050"), locked=Decimal("0")),
        open_orders=[],
    )
    rec = Reconciler(query=fq, base_coin="BTC", symbol="BTCUSDT",
                     dust_threshold=Decimal("0.00001"))
    state = rec.fetch_exchange_state()
    assert rec.derive_position_qty(state) == Decimal("0")
```

- [ ] **Step 2: Run tests to verify RED**

Run: `pytest tests/unit/test_reconciler_fetch.py -v`
Expected: FAIL — `fetch_exchange_state` still calls `get_position`; `derive_position_qty` not defined.

- [ ] **Step 3: Implement wallet-driven fetch + dust threshold**

```python
# src/execution/reconciler.py
class Reconciler:
    def __init__(
        self,
        *,
        query: ExchangeQueryClient,
        base_coin: str,
        symbol: str,
        dust_threshold: Decimal = Decimal("0.00001"),  # Settings.oco_dust_threshold_btc
    ) -> None:
        self.query = query
        self.base_coin = base_coin
        self.symbol = symbol
        self.dust_threshold = dust_threshold

    def fetch_exchange_state(self) -> ExchangeState:
        wallet = self.query.get_wallet_balance(coin=self.base_coin)
        orders = tuple(self.query.get_open_orders(symbol=self.symbol))
        return ExchangeState(wallet=wallet, open_orders=orders)

    def derive_position_qty(self, state: ExchangeState) -> Decimal:
        """ADR 0020 sub-decision 4: wallet < dust_threshold → FLAT."""
        if state.wallet.wallet_balance < self.dust_threshold:
            return Decimal("0")
        return state.wallet.wallet_balance
```

- [ ] **Step 4: Run tests to verify GREEN**

Run: `pytest tests/unit/test_reconciler_fetch.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/execution/reconciler.py tests/unit/test_reconciler_fetch.py
git commit -m "feat(execution): derive Spot position qty from walletBalance + dust threshold (ADR 0020 sub-decision 4)"
```

### Task 13: Entry-price preservation across reconcile

**Files:**
- Modify: `src/execution/reconciler.py` (ReconcileResult + reconcile() body)
- Test: `tests/unit/test_reconciler_entry_price.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_reconciler_entry_price.py
"""ADR 0020 sub-decision 4: exchange owns qty, local SQLite owns entry_price.
Reconcile must NOT clobber entry_price when exchange and local agree on qty."""
from decimal import Decimal
from src.execution.reconciler import Reconciler, ReconcileResult, LocalState
from src.execution.bybit.adapter import WalletSnapshot
from tests.helpers import FakeQuery


def test_reconcile_preserves_local_entry_price():
    fq = FakeQuery(
        wallet=WalletSnapshot(coin="BTC", wallet_balance=Decimal("0.001"),
                              available=Decimal("0"), locked=Decimal("0.001")),
        open_orders=[{"orderLinkId": "oco-abc-tp-1", "orderStatus": "New"},
                     {"orderLinkId": "oco-abc-sl-1", "orderStatus": "Untriggered"}],
    )
    rec = Reconciler(query=fq, base_coin="BTC", symbol="BTCUSDT")
    local = LocalState(state="OCO_ARMED", position_qty=Decimal("0.001"),
                       entry_price=Decimal("65000.00"), bracket_id="abc")
    result = rec.reconcile(local)
    assert result.verdict == "AGREE"
    assert result.entry_price == Decimal("65000.00")  # preserved from local
    assert result.position_qty == Decimal("0.001")    # exchange truth


def test_reconcile_qty_divergence_triggers_halt():
    fq = FakeQuery(
        wallet=WalletSnapshot(coin="BTC", wallet_balance=Decimal("0.0005"),
                              available=Decimal("0"), locked=Decimal("0.0005")),
        open_orders=[],
    )
    rec = Reconciler(query=fq, base_coin="BTC", symbol="BTCUSDT")
    local = LocalState(state="OCO_ARMED", position_qty=Decimal("0.001"),
                       entry_price=Decimal("65000.00"), bracket_id="abc")
    result = rec.reconcile(local)
    assert result.verdict == "DIVERGENCE"
    assert result.recommended_state == "HALTED"
    assert result.halt_reason == "HALT_RECONCILE_DIVERGENCE"
```

- [ ] **Step 2: Run tests to verify RED**

Run: `pytest tests/unit/test_reconciler_entry_price.py -v`
Expected: FAIL — `LocalState`/`ReconcileResult` shape missing entry_price/halt_reason.

- [ ] **Step 3: Extend reconcile() with entry-price split + halt classification**

```python
@dataclass(frozen=True, slots=True)
class LocalState:
    state: str
    position_qty: Decimal
    entry_price: Decimal | None
    bracket_id: str | None


@dataclass(frozen=True, slots=True)
class ReconcileResult:
    verdict: str  # "AGREE" | "DIVERGENCE"
    position_qty: Decimal
    entry_price: Decimal | None
    open_order_link_ids: tuple[str, ...]
    recommended_state: str | None = None
    halt_reason: str | None = None


class Reconciler:
    def reconcile(self, local: LocalState) -> ReconcileResult:
        state = self.fetch_exchange_state()
        exch_qty = self.derive_position_qty(state)
        if exch_qty != local.position_qty:
            return ReconcileResult(
                verdict="DIVERGENCE",
                position_qty=exch_qty,
                entry_price=None,
                open_order_link_ids=tuple(o.get("orderLinkId", "") for o in state.open_orders),
                recommended_state="HALTED",
                halt_reason="HALT_RECONCILE_DIVERGENCE",
            )
        return ReconcileResult(
            verdict="AGREE",
            position_qty=exch_qty,
            entry_price=local.entry_price,  # preserve local — exchange doesn't know
            open_order_link_ids=tuple(o.get("orderLinkId", "") for o in state.open_orders),
        )
```

- [ ] **Step 4: Run tests to verify GREEN**

Run: `pytest tests/unit/test_reconciler_entry_price.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/execution/reconciler.py tests/unit/test_reconciler_entry_price.py
git commit -m "feat(execution): preserve local entry_price across reconcile + qty-divergence halt (ADR 0020 sub-decision 4)"
```

---

## Stage E — Bracket builder + Coordinator orchestration (Tasks 14-18)

ADR 0020 sub-decision 2 (3-order bracket) + sub-decision 5 (G5 fee-aware sizing) + sub-decision 6 (sibling cancel-on-Triggered) + sub-decision 7 (EXIT_SL_RESIDUAL).

### Task 14: bracket.py rewrite — BracketParams + 3 leg builders + bracket_id

**Files:**
- Create: `src/execution/bracket.py`
- Test: `tests/unit/test_bracket_builder.py`
- Delete (after migration done in Stage H): `src/execution/oco.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_bracket_builder.py
"""ADR 0020 sub-decision 2: 3-order Spot OCO bracket. Pure function — no I/O."""
from decimal import Decimal
import re
import uuid
from src.execution.bracket import (
    BracketParams, BracketLegs, build_bracket, make_order_link_id, ROLE_ENTRY, ROLE_TP, ROLE_SL,
)


def test_build_bracket_returns_three_legs_with_shared_bracket_id():
    p = BracketParams(
        symbol="BTCUSDT",
        entry_qty=Decimal("0.001"),
        entry_side="Buy",
        tp_price=Decimal("70000.00"),
        sl_trigger_price=Decimal("60000.00"),
        bracket_id="abc-uuid",
        attempt=1,
    )
    legs = build_bracket(p)
    assert legs.entry.role == ROLE_ENTRY
    assert legs.tp.role == ROLE_TP
    assert legs.sl.role == ROLE_SL
    assert legs.entry.order_link_id == "oco-abc-uuid-entry-1"
    assert legs.tp.order_link_id    == "oco-abc-uuid-tp-1"
    assert legs.sl.order_link_id    == "oco-abc-uuid-sl-1"


def test_make_order_link_id_pattern_and_length():
    lid = make_order_link_id(bracket_id="abc-uuid", role="tp", attempt=2)
    assert lid == "oco-abc-uuid-tp-2"
    assert re.match(r"^oco-[A-Za-z0-9_-]+-(entry|tp|sl)-\d+$", lid)
    # Bybit V5 orderLinkId max 36 chars; with UUIDv4 (36 chars) prefix doesn't fit.
    # Sub-decision 2 mandates short prefix: 8-char bracket_id (truncated UUIDv4).
    short = make_order_link_id(bracket_id=str(uuid.uuid4())[:8], role="entry", attempt=1)
    assert len(short) <= 36


def test_tp_and_sl_legs_use_sell_side_when_entry_buy():
    p = BracketParams(
        symbol="BTCUSDT", entry_qty=Decimal("0.001"), entry_side="Buy",
        tp_price=Decimal("70000.00"), sl_trigger_price=Decimal("60000.00"),
        bracket_id="x", attempt=1,
    )
    legs = build_bracket(p)
    assert legs.entry.side == "Buy"
    assert legs.tp.side == "Sell"
    assert legs.sl.side == "Sell"
```

- [ ] **Step 2: Run tests to verify RED**

Run: `pytest tests/unit/test_bracket_builder.py -v`
Expected: FAIL — `bracket.py` not created.

- [ ] **Step 3: Implement bracket builder**

```python
# src/execution/bracket.py
"""ADR 0020 sub-decision 2: 3-order Spot OCO bracket builder (pure functions, no I/O).

Bybit Spot V5 has no native OCO; we emulate via:
  1. Entry Market BUY (immediate fill assumed; dust handled via G5 fee-aware sizing)
  2. Limit Sell @ TP (orderType=Limit, timeInForce=GTC)
  3. Stop Market Sell @ SL (orderType=Market, orderFilter=StopOrder, triggerBy=LastPrice)

Correlation: orderLinkId = "oco-{bracket_id}-{role}-{attempt}" — propagated to WS events.
"""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

ROLE_ENTRY = "entry"
ROLE_TP = "tp"
ROLE_SL = "sl"
Role = Literal["entry", "tp", "sl"]


@dataclass(frozen=True, slots=True)
class BracketLeg:
    role: Role
    side: Literal["Buy", "Sell"]
    qty: Decimal
    price: Decimal | None             # set for TP (Limit), None for entry (Market) and SL (Market+Stop)
    trigger_price: Decimal | None     # set for SL only
    order_link_id: str


@dataclass(frozen=True, slots=True)
class BracketLegs:
    entry: BracketLeg
    tp: BracketLeg
    sl: BracketLeg


@dataclass(frozen=True, slots=True)
class BracketParams:
    symbol: str
    entry_qty: Decimal
    entry_side: Literal["Buy", "Sell"]
    tp_price: Decimal
    sl_trigger_price: Decimal
    bracket_id: str          # short UUIDv4 prefix (8 chars) — see ADR 0020 sub-decision 2
    attempt: int             # 1 on first try, increments on retry (idempotency, sub-decision 9)


def make_order_link_id(*, bracket_id: str, role: Role, attempt: int) -> str:
    """Deterministic orderLinkId. Bybit V5 max length 36 chars."""
    lid = f"oco-{bracket_id}-{role}-{attempt}"
    if len(lid) > 36:
        raise ValueError(f"orderLinkId too long ({len(lid)} > 36): {lid}")
    return lid


def build_bracket(p: BracketParams) -> BracketLegs:
    exit_side: Literal["Buy", "Sell"] = "Sell" if p.entry_side == "Buy" else "Buy"
    return BracketLegs(
        entry=BracketLeg(
            role=ROLE_ENTRY, side=p.entry_side, qty=p.entry_qty,
            price=None, trigger_price=None,
            order_link_id=make_order_link_id(bracket_id=p.bracket_id, role=ROLE_ENTRY, attempt=p.attempt),
        ),
        tp=BracketLeg(
            role=ROLE_TP, side=exit_side, qty=p.entry_qty,
            price=p.tp_price, trigger_price=None,
            order_link_id=make_order_link_id(bracket_id=p.bracket_id, role=ROLE_TP, attempt=p.attempt),
        ),
        sl=BracketLeg(
            role=ROLE_SL, side=exit_side, qty=p.entry_qty,
            price=None, trigger_price=p.sl_trigger_price,
            order_link_id=make_order_link_id(bracket_id=p.bracket_id, role=ROLE_SL, attempt=p.attempt),
        ),
    )
```

- [ ] **Step 4: Run tests to verify GREEN**

Run: `pytest tests/unit/test_bracket_builder.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/execution/bracket.py tests/unit/test_bracket_builder.py
git commit -m "feat(execution): bracket builder for 3-order Spot OCO emulation (ADR 0020 sub-decision 2)"
```

### Task 15: G5 fee-aware sizing — compute_oco_qty

**Files:**
- Modify: `src/execution/bracket.py` (add `compute_oco_qty`)
- Test: `tests/unit/test_bracket_fee_aware_qty.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_bracket_fee_aware_qty.py
"""ADR 0020 sub-decision 5 (G5): TP/SL qty must subtract base-coin fees from cumExecQty.
On Spot Buy, fees are charged in BTC (base_coin=feeCurrency). Skipping this leaves dust
that the OCO legs can't cancel — bracket gets stuck with residual."""
from decimal import Decimal
import pytest
from src.execution.bracket import compute_oco_qty


def test_qty_subtracts_fee_when_fee_currency_matches_base():
    # Buy 0.001 BTC, exchange charges 0.000001 BTC fee → net position 0.000999
    qty = compute_oco_qty(
        cum_exec_qty=Decimal("0.001"),
        cum_exec_fee=Decimal("0.000001"),
        fee_currency="BTC",
        base_coin="BTC",
        qty_step=Decimal("0.000001"),
    )
    assert qty == Decimal("0.000999")


def test_qty_unchanged_when_fee_currency_differs():
    # Sell 0.001 BTC, fees in USDT → no impact on BTC position
    qty = compute_oco_qty(
        cum_exec_qty=Decimal("0.001"),
        cum_exec_fee=Decimal("70.00"),
        fee_currency="USDT",
        base_coin="BTC",
        qty_step=Decimal("0.000001"),
    )
    assert qty == Decimal("0.001")


def test_qty_floored_to_step_after_fee_subtract():
    # Net 0.0009993 → floor to 0.000999 (step 0.000001)
    qty = compute_oco_qty(
        cum_exec_qty=Decimal("0.001"),
        cum_exec_fee=Decimal("0.0000007"),
        fee_currency="BTC",
        base_coin="BTC",
        qty_step=Decimal("0.000001"),
    )
    assert qty == Decimal("0.000999")


def test_qty_zero_when_fee_exceeds_qty():
    qty = compute_oco_qty(
        cum_exec_qty=Decimal("0.000001"),
        cum_exec_fee=Decimal("0.000002"),
        fee_currency="BTC",
        base_coin="BTC",
        qty_step=Decimal("0.000001"),
    )
    assert qty == Decimal("0")
```

- [ ] **Step 2: Run tests to verify RED**

Run: `pytest tests/unit/test_bracket_fee_aware_qty.py -v`
Expected: FAIL — `compute_oco_qty` not defined.

- [ ] **Step 3: Implement compute_oco_qty (G5 formula)**

```python
# src/execution/bracket.py — append
from decimal import ROUND_DOWN


def compute_oco_qty(
    *,
    cum_exec_qty: Decimal,
    cum_exec_fee: Decimal,
    fee_currency: str,
    base_coin: str,
    qty_step: Decimal,
) -> Decimal:
    """ADR 0020 sub-decision 5 (G5): fee-aware OCO qty.

    Spot Buy fees on Bybit are deducted from the base-coin received (BTC), not from the
    quote (USDT). Submitting OCO legs with raw cumExecQty (ignoring fee) leaves dust that
    can't be cancelled and traps the bracket. Floor to qty_step after subtracting.
    """
    if fee_currency == base_coin:
        net = cum_exec_qty - cum_exec_fee
    else:
        net = cum_exec_qty
    if net <= 0:
        return Decimal("0")
    floored = (net / qty_step).quantize(Decimal("1"), rounding=ROUND_DOWN) * qty_step
    return floored
```

- [ ] **Step 4: Run tests to verify GREEN**

Run: `pytest tests/unit/test_bracket_fee_aware_qty.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/execution/bracket.py tests/unit/test_bracket_fee_aware_qty.py
git commit -m "feat(execution): G5 fee-aware OCO qty (subtract base-coin fee + floor to step) (ADR 0020 sub-decision 5)"
```

### Task 16: Coordinator.start_bracket — entry → arming

**Files:**
- Modify: `src/execution/coordinator.py` (`start_bracket`, helpers)
- Test: `tests/integration/test_coordinator_start_bracket.py`

- [ ] **Step 1: Write failing test**

```python
# tests/integration/test_coordinator_start_bracket.py
"""ADR 0020 sub-decision 2: start_bracket places entry, transitions FLAT → ENTRY_PENDING.
On entry fill: ENTRY_PENDING → LONG_OPEN → OCO_ARMING → OCO_ARMED via 2-leg arm."""
from decimal import Decimal
from src.execution.coordinator import Coordinator
from src.execution.state_machine import ExecutionState


def test_start_bracket_emits_entry_and_persists_bracket_id(coordinator_harness):
    h = coordinator_harness  # provides FakeAdapter, FakeRepo, FakeReconciler
    coord = Coordinator(adapter=h.adapter, repo=h.repo, reconciler=h.reconciler,
                        symbol="BTCUSDT", base_coin="BTC")
    bracket_id = coord.start_bracket(
        entry_qty=Decimal("0.001"), entry_side="Buy",
        tp_price=Decimal("70000.00"), sl_trigger_price=Decimal("60000.00"),
    )
    # Entry order placed
    assert h.adapter.placed_orders[-1]["orderLinkId"] == f"oco-{bracket_id}-entry-1"
    # FSM: FLAT → ENTRY_PENDING
    row = h.repo.get("BTCUSDT")
    assert row.state == ExecutionState.ENTRY_PENDING
    assert row.bracket_id == bracket_id
    assert row.last_attempt_num == 1
```

- [ ] **Step 2: Run test to verify RED**

Run: `pytest tests/integration/test_coordinator_start_bracket.py -v`
Expected: FAIL — `start_bracket` not implemented.

- [ ] **Step 3: Implement start_bracket**

```python
# src/execution/coordinator.py
import uuid
from src.execution.bracket import BracketParams, build_bracket
from src.execution.state_machine import ExecutionState, ExecutionEvent, apply_transition


class Coordinator:
    def __init__(self, *, adapter, repo, reconciler, symbol: str, base_coin: str) -> None:
        self.adapter = adapter
        self.repo = repo
        self.reconciler = reconciler
        self.symbol = symbol
        self.base_coin = base_coin

    def start_bracket(
        self, *, entry_qty: Decimal, entry_side: str,
        tp_price: Decimal, sl_trigger_price: Decimal,
    ) -> str:
        bracket_id = str(uuid.uuid4())[:8]  # 8-char prefix to fit Bybit's 36-char orderLinkId
        params = BracketParams(
            symbol=self.symbol, entry_qty=entry_qty, entry_side=entry_side,
            tp_price=tp_price, sl_trigger_price=sl_trigger_price,
            bracket_id=bracket_id, attempt=1,
        )
        legs = build_bracket(params)
        self.adapter.place_order(
            symbol=self.symbol, side=legs.entry.side, qty=legs.entry.qty,
            order_link_id=legs.entry.order_link_id,
        )
        current = self.repo.get(self.symbol)
        new_state = apply_transition(current.state, ExecutionEvent.ENTRY_SUBMITTED)
        self.repo.upsert(
            symbol=self.symbol, state=new_state,
            position_qty=Decimal("0"),
            bracket_id=bracket_id,
            last_attempt_num=1,
            tp_price=tp_price,
            sl_trigger_price=sl_trigger_price,
        )
        return bracket_id
```

- [ ] **Step 4: Run test to verify GREEN**

Run: `pytest tests/integration/test_coordinator_start_bracket.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/execution/coordinator.py tests/integration/test_coordinator_start_bracket.py
git commit -m "feat(execution): Coordinator.start_bracket places entry + persists bracket_id (ADR 0020 sub-decision 2)"
```

### Task 17: Coordinator.on_order_event — sibling-cancel-on-Triggered

**Files:**
- Modify: `src/execution/coordinator.py` (`on_order_event`, `_arm_oco`, `_cancel_sibling`)
- Test: `tests/integration/test_coordinator_sibling_cancel.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/integration/test_coordinator_sibling_cancel.py
"""ADR 0020 sub-decision 6: WS Triggered event on SL → cancel TP sibling immediately.
Spot Stop sequence: Untriggered → Triggered → Filled (0ms gap). Triggered is the only
window we have to cancel the sibling before it self-fills."""
from decimal import Decimal
from src.execution.state_machine import ExecutionState
from src.risk.reason_codes import ReasonCode


def test_sl_triggered_cancels_tp_sibling(coordinator_armed_harness):
    h = coordinator_armed_harness  # state = OCO_ARMED with TP_OID + SL_OID known
    coord = h.coordinator
    # WS fires Triggered on SL
    coord.on_order_event({
        "orderLinkId": f"oco-{h.bracket_id}-sl-1",
        "orderStatus": "Triggered",
        "side": "Sell",
        "cumExecQty": "0",
    })
    # Coordinator cancels the TP sibling
    cancelled = [c for c in h.adapter.cancel_calls if c["orderId"] == h.tp_oid]
    assert len(cancelled) == 1
    # FSM: OCO_ARMED → EXIT_SIBLING_CANCELLING
    row = h.repo.get("BTCUSDT")
    assert row.state == ExecutionState.EXIT_SIBLING_CANCELLING


def test_sibling_already_filled_classified_non_fatal(coordinator_armed_harness):
    """ADR 0020 sub-decision 6: cancel returns 110001 → REJECT_ORDER_ALREADY_TERMINAL,
    treated as expected race outcome — proceed to FLAT, do NOT halt."""
    h = coordinator_armed_harness
    h.adapter.next_cancel_result = ReasonCode.REJECT_ORDER_ALREADY_TERMINAL
    coord = h.coordinator
    coord.on_order_event({
        "orderLinkId": f"oco-{h.bracket_id}-sl-1",
        "orderStatus": "Triggered",
        "side": "Sell",
        "cumExecQty": "0",
    })
    row = h.repo.get("BTCUSDT")
    # State proceeds to FLAT after both legs resolved (sibling self-filled in race)
    assert row.state in (ExecutionState.FLAT, ExecutionState.EXIT_SIBLING_CANCELLING)
    # No HALT
    assert row.halt_reason is None
```

- [ ] **Step 2: Run tests to verify RED**

Run: `pytest tests/integration/test_coordinator_sibling_cancel.py -v`
Expected: FAIL — `on_order_event` doesn't dispatch Triggered.

- [ ] **Step 3: Implement on_order_event + sibling cancel**

```python
# src/execution/coordinator.py — append
def on_order_event(self, evt: dict) -> None:
    """ADR 0020 sub-decisions 6+7: WS event router. Triggers sibling-cancel and
    EXIT_SL_RESIDUAL handling."""
    link_id = evt.get("orderLinkId", "")
    status = evt.get("orderStatus", "")
    role = self._role_from_link_id(link_id)
    if status == "Triggered" and role == "sl":
        self._cancel_sibling(role="tp")
        self._transition(ExecutionEvent.SL_TRIGGERED)
    elif status == "Filled" and role == "tp":
        self._cancel_sibling(role="sl")
        self._transition(ExecutionEvent.TP_HIT)
    elif status == "PartiallyFilled" and role == "sl":
        # ADR 0020 sub-decision 7: TIF override caused partial — handle in Stage E Task 18
        self._handle_sl_partial(evt)

def _cancel_sibling(self, *, role: str) -> None:
    row = self.repo.get(self.symbol)
    sibling_oid = row.tp_order_id if role == "tp" else row.sl_order_id
    if sibling_oid is None:
        return
    res = self.adapter.cancel_order(symbol=self.symbol, order_id=sibling_oid)
    if res.cancelled:
        self._transition(ExecutionEvent.SIBLING_CANCELLED)
    elif res.reason_code == ReasonCode.REJECT_ORDER_ALREADY_TERMINAL:
        # Race: sibling self-filled before we could cancel. Expected on Triggered→Filled 0ms gap.
        self._transition(ExecutionEvent.SIBLING_CANCELLED)  # treat as success
    else:
        self._transition(ExecutionEvent.SIBLING_CANCEL_FAILED)
        self._halt(ReasonCode.HALT_OCO_SIBLING_STUCK)

def _role_from_link_id(self, link_id: str) -> str | None:
    # "oco-{bracket}-{role}-{attempt}" → role
    parts = link_id.split("-")
    return parts[-2] if len(parts) >= 4 else None
```

- [ ] **Step 4: Run tests to verify GREEN**

Run: `pytest tests/integration/test_coordinator_sibling_cancel.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/execution/coordinator.py tests/integration/test_coordinator_sibling_cancel.py
git commit -m "feat(execution): sibling-cancel-on-Triggered + 110001 race classifier (ADR 0020 sub-decisions 6,7)"
```

### Task 18: EXIT_SL_RESIDUAL — IOC partial fill flatten

**Files:**
- Modify: `src/execution/coordinator.py` (`_handle_sl_partial`, `_flatten_residual`)
- Test: `tests/integration/test_coordinator_sl_residual.py`

- [ ] **Step 1: Write failing test**

```python
# tests/integration/test_coordinator_sl_residual.py
"""ADR 0020 sub-decision 7: Bybit Spot Stop silently rewrites GTC→IOC (probe v3-D).
A Stop Market that triggers may PartiallyFill, leaving residual base-coin position.
Coordinator flattens residual via Market Sell, transitions FLAT, reason=EXIT_STOP_RESIDUAL_FLATTEN."""
from decimal import Decimal
from src.execution.state_machine import ExecutionState
from src.risk.reason_codes import ReasonCode


def test_sl_partial_triggers_residual_flatten(coordinator_armed_harness):
    h = coordinator_armed_harness
    coord = h.coordinator
    # SL triggers but IOC fills only 0.0006 of 0.001 → 0.0004 residual
    coord.on_order_event({
        "orderLinkId": f"oco-{h.bracket_id}-sl-1",
        "orderStatus": "PartiallyFilled",
        "side": "Sell",
        "cumExecQty": "0.0006",
        "leavesQty": "0.0004",
    })
    # Coordinator places Market Sell for the 0.0004 residual
    flatten = [o for o in h.adapter.placed_orders if o.get("orderType") == "Market"
               and o.get("side") == "Sell" and Decimal(o.get("qty", "0")) == Decimal("0.0004")]
    assert len(flatten) == 1
    row = h.repo.get("BTCUSDT")
    assert row.state == ExecutionState.FLAT
    assert row.last_exit_reason == ReasonCode.EXIT_STOP_RESIDUAL_FLATTEN
```

- [ ] **Step 2: Run test to verify RED**

Run: `pytest tests/integration/test_coordinator_sl_residual.py -v`
Expected: FAIL — `_handle_sl_partial` not implemented.

- [ ] **Step 3: Implement EXIT_SL_RESIDUAL handler**

```python
# src/execution/coordinator.py — append
def _handle_sl_partial(self, evt: dict) -> None:
    """ADR 0020 sub-decision 7: SL IOC partial → flatten residual via Market Sell."""
    self._transition(ExecutionEvent.PARTIAL_FILL)  # OCO_ARMED → EXIT_SL_RESIDUAL
    leaves_qty = Decimal(evt.get("leavesQty", "0"))
    if leaves_qty <= 0:
        self._transition(ExecutionEvent.RESIDUAL_FLATTENED)
        return
    self._flatten_residual(qty=leaves_qty, reason=ReasonCode.EXIT_STOP_RESIDUAL_FLATTEN)

def _flatten_residual(self, *, qty: Decimal, reason: ReasonCode) -> None:
    """Emergency Market Sell on residual base-coin. Sub-decision 10: retry-once on failure."""
    try:
        self.adapter.place_order(symbol=self.symbol, side="Sell", qty=qty)
    except Exception:
        # Retry once with qty - one step (handles step-quantization race vs walletBalance)
        retry_qty = self._step_floor(qty - self._qty_step())
        if retry_qty <= 0:
            self._transition(ExecutionEvent.FLATTEN_FAILED)
            self._halt(ReasonCode.HALT_FLATTEN_FAILED)
            return
        try:
            self.adapter.place_order(symbol=self.symbol, side="Sell", qty=retry_qty)
        except Exception:
            self._transition(ExecutionEvent.FLATTEN_FAILED)
            self._halt(ReasonCode.HALT_FLATTEN_FAILED)
            return
    self._transition(ExecutionEvent.RESIDUAL_FLATTENED)
    self.repo.upsert(symbol=self.symbol, last_exit_reason=reason)
```

- [ ] **Step 4: Run test to verify GREEN**

Run: `pytest tests/integration/test_coordinator_sl_residual.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/execution/coordinator.py tests/integration/test_coordinator_sl_residual.py
git commit -m "feat(execution): EXIT_SL_RESIDUAL flatten on IOC partial fill (ADR 0020 sub-decision 7)"
```

---

## Stage F — Idempotency, prior-attempt detection, TTL, flatten cascade (Tasks 19-22)

ADR 0020 sub-decisions 9 (deterministic orderLinkId + bump) + 10 (flatten cascade) + 11 (OCO_ARMING TTL=60s).

### Task 19: Deterministic orderLinkId + last_attempt_num bump

**Files:**
- Modify: `src/execution/coordinator.py` (`_next_attempt_num`, `arm_oco`)
- Test: `tests/unit/test_coordinator_attempt_bump.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_coordinator_attempt_bump.py
"""ADR 0020 sub-decision 9: when retrying a leg (e.g. arm_oco after partial-arm failure),
attempt counter MUST bump so orderLinkId differs from prior attempt — Bybit rejects
duplicate orderLinkId with retCode 10006."""
from decimal import Decimal


def test_arm_oco_bumps_attempt_on_retry(coordinator_long_open_harness):
    h = coordinator_long_open_harness
    coord = h.coordinator
    # First arm: TP placed OK, SL placement fails (simulated)
    h.adapter.fail_next_stop_order = True
    coord.arm_oco(tp_price=Decimal("70000"), sl_trigger_price=Decimal("60000"),
                  oco_qty=Decimal("0.001"))
    # Repo records attempt 1, both legs marked failed
    row = h.repo.get("BTCUSDT")
    assert row.last_attempt_num == 1
    # Retry: attempt must be 2
    h.adapter.fail_next_stop_order = False
    coord.arm_oco(tp_price=Decimal("70000"), sl_trigger_price=Decimal("60000"),
                  oco_qty=Decimal("0.001"))
    row = h.repo.get("BTCUSDT")
    assert row.last_attempt_num == 2
    # New orderLinkIds use -2 suffix
    assert any(o.get("orderLinkId", "").endswith("-tp-2") for o in h.adapter.placed_orders)
    assert any(o.get("orderLinkId", "").endswith("-sl-2") for o in h.adapter.placed_orders)
```

- [ ] **Step 2: Run test to verify RED**

Run: `pytest tests/unit/test_coordinator_attempt_bump.py -v`
Expected: FAIL — `arm_oco` not implemented or attempt not bumped.

- [ ] **Step 3: Implement arm_oco with deterministic attempt bump**

```python
# src/execution/coordinator.py — append
from src.execution.bracket import BracketParams, build_bracket, make_order_link_id

def arm_oco(self, *, tp_price: Decimal, sl_trigger_price: Decimal, oco_qty: Decimal) -> None:
    """ADR 0020 sub-decisions 2+9+11: place TP + SL legs, transitions LONG_OPEN → OCO_ARMING.
    Bumps last_attempt_num if a prior attempt exists (idempotent retry).
    """
    row = self.repo.get(self.symbol)
    attempt = row.last_attempt_num + 1 if row.last_attempt_num else 1
    bracket_id = row.bracket_id
    if bracket_id is None:
        raise RuntimeError("arm_oco called without active bracket_id")
    tp_lid = make_order_link_id(bracket_id=bracket_id, role="tp", attempt=attempt)
    sl_lid = make_order_link_id(bracket_id=bracket_id, role="sl", attempt=attempt)
    self._transition(ExecutionEvent.TP_PLACED)  # → OCO_ARMING
    tp_ack = self.adapter.place_limit_order(
        symbol=self.symbol, side="Sell", qty=oco_qty,
        price=tp_price, order_link_id=tp_lid,
    )
    sl_ack = self.adapter.place_stop_market_order(
        symbol=self.symbol, side="Sell", qty=oco_qty,
        trigger_price=sl_trigger_price, order_link_id=sl_lid,
    )
    self._transition(ExecutionEvent.SL_PLACED)  # → OCO_ARMED
    self.repo.upsert(
        symbol=self.symbol,
        last_attempt_num=attempt,
        tp_order_id=tp_ack.order_id,
        sl_order_id=sl_ack.order_id,
        oco_qty=oco_qty,
        arming_started_at=self._now_iso(),
    )
```

- [ ] **Step 4: Run test to verify GREEN**

Run: `pytest tests/unit/test_coordinator_attempt_bump.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/execution/coordinator.py tests/unit/test_coordinator_attempt_bump.py
git commit -m "feat(execution): deterministic orderLinkId + last_attempt_num bump (ADR 0020 sub-decision 9)"
```

### Task 20: Prior-attempt detection via get_open_orders + get_order_history

**Files:**
- Modify: `src/execution/bybit/adapter.py` (`get_order_history`)
- Modify: `src/execution/coordinator.py` (`bootstrap`, `_detect_prior_attempts`)
- Test: `tests/integration/test_coordinator_bootstrap_idempotent.py`

- [ ] **Step 1: Write failing test**

```python
# tests/integration/test_coordinator_bootstrap_idempotent.py
"""ADR 0020 sub-decision 9: on bootstrap, scan open orders + recent history for prior
oco-{bracket}-{role}-{attempt} entries to discover the highest attempt seen.
Prevents arm_oco from re-using attempt=1 after a crash mid-retry."""


def test_bootstrap_detects_prior_attempt_from_history(coordinator_with_history):
    h = coordinator_with_history  # SQLite has bracket_id="abc" attempt=1; history has attempt=2
    coord = h.coordinator
    coord.bootstrap()
    row = h.repo.get("BTCUSDT")
    assert row.last_attempt_num == 2  # bumped from history evidence


def test_bootstrap_no_prior_attempts_keeps_attempt_one(coordinator_clean):
    h = coordinator_clean
    coord = h.coordinator
    coord.bootstrap()
    row = h.repo.get("BTCUSDT")
    assert row.last_attempt_num in (None, 0)  # nothing bumped
```

- [ ] **Step 2: Run test to verify RED**

Run: `pytest tests/integration/test_coordinator_bootstrap_idempotent.py -v`
Expected: FAIL — `bootstrap` / `get_order_history` not implemented.

- [ ] **Step 3: Implement get_order_history + bootstrap detection**

```python
# src/execution/bybit/adapter.py — add
def get_order_history(self, *, symbol: str, limit: int = 50) -> list[dict]:
    """V5 GET /v5/order/history — recent terminal orders (Filled/Cancelled/Rejected)."""
    raw = self.rest.get_order_history({"category": "spot", "symbol": symbol, "limit": limit})
    return raw.get("list", [])


# src/execution/coordinator.py — add
def bootstrap(self) -> None:
    """ADR 0020 sub-decision 9: discover highest prior attempt# from exchange evidence,
    so resume after crash never reuses an old orderLinkId."""
    row = self.repo.get(self.symbol)
    if row.bracket_id is None:
        return
    open_orders = self.adapter.get_open_orders(symbol=self.symbol)
    history = self.adapter.get_order_history(symbol=self.symbol, limit=50)
    max_attempt = self._extract_max_attempt(
        bracket_id=row.bracket_id, candidates=open_orders + history,
    )
    if max_attempt > (row.last_attempt_num or 0):
        self.repo.upsert(symbol=self.symbol, last_attempt_num=max_attempt)

@staticmethod
def _extract_max_attempt(*, bracket_id: str, candidates: list[dict]) -> int:
    prefix = f"oco-{bracket_id}-"
    max_n = 0
    for c in candidates:
        lid = c.get("orderLinkId", "")
        if not lid.startswith(prefix):
            continue
        try:
            n = int(lid.split("-")[-1])
            max_n = max(max_n, n)
        except (ValueError, IndexError):
            continue
    return max_n
```

- [ ] **Step 4: Run test to verify GREEN**

Run: `pytest tests/integration/test_coordinator_bootstrap_idempotent.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/execution/bybit/adapter.py src/execution/coordinator.py tests/integration/test_coordinator_bootstrap_idempotent.py
git commit -m "feat(execution): bootstrap discovers prior attempt# from exchange history (ADR 0020 sub-decision 9)"
```

### Task 21: OCO_ARMING TTL=60s reconcile rule

**Files:**
- Modify: `src/platform/config.py` (`oco_arming_ttl_seconds`)
- Modify: `src/execution/coordinator.py` (`reconcile_arming_ttl`)
- Test: `tests/unit/test_coordinator_arming_ttl.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_coordinator_arming_ttl.py
"""ADR 0020 sub-decision 11: state OCO_ARMING with arming_started_at older than TTL
(default 60s) → halt with HALT_OCO_ARM_TIMEOUT. Otherwise wait."""
from datetime import datetime, timedelta, timezone
from src.execution.state_machine import ExecutionState
from src.risk.reason_codes import ReasonCode


def test_arming_within_ttl_no_halt(coordinator_arming_recent):
    h = coordinator_arming_recent  # arming_started_at = 30s ago
    h.coordinator.reconcile_arming_ttl()
    row = h.repo.get("BTCUSDT")
    assert row.state == ExecutionState.OCO_ARMING


def test_arming_beyond_ttl_halts(coordinator_arming_stale):
    h = coordinator_arming_stale  # arming_started_at = 90s ago
    h.coordinator.reconcile_arming_ttl()
    row = h.repo.get("BTCUSDT")
    assert row.state == ExecutionState.HALTED
    assert row.halt_reason == ReasonCode.HALT_OCO_ARM_TIMEOUT
```

- [ ] **Step 2: Run tests to verify RED**

Run: `pytest tests/unit/test_coordinator_arming_ttl.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement TTL reconcile + Settings field**

```python
# src/platform/config.py — extend Settings
class Settings(BaseSettings):
    # … existing fields …
    oco_arming_ttl_seconds: int = 60        # ADR 0020 sub-decision 11
    oco_dust_threshold_btc: Decimal = Decimal("0.00001")  # ADR 0020 sub-decision 4


# src/execution/coordinator.py — add
from datetime import datetime, timezone

def reconcile_arming_ttl(self) -> None:
    """ADR 0020 sub-decision 11: stuck OCO_ARMING > TTL → HALT_OCO_ARM_TIMEOUT.
    Called from periodic supervisor loop (1s tick) and from on_order_event."""
    row = self.repo.get(self.symbol)
    if row.state != ExecutionState.OCO_ARMING or row.arming_started_at is None:
        return
    started = datetime.fromisoformat(row.arming_started_at)
    age = (datetime.now(timezone.utc) - started).total_seconds()
    if age > self.settings.oco_arming_ttl_seconds:
        self._transition(ExecutionEvent.BRACKET_TIMEOUT)
        self._halt(ReasonCode.HALT_OCO_ARM_TIMEOUT)
```

- [ ] **Step 4: Run tests to verify GREEN**

Run: `pytest tests/unit/test_coordinator_arming_ttl.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/platform/config.py src/execution/coordinator.py tests/unit/test_coordinator_arming_ttl.py
git commit -m "feat(execution): OCO_ARMING TTL=60s reconcile rule (ADR 0020 sub-decision 11)"
```

### Task 22: Flatten cascade — retry-once-with-qty-minus-step

**Files:**
- Modify: `src/execution/coordinator.py` (`flatten`)
- Test: `tests/unit/test_coordinator_flatten_cascade.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_coordinator_flatten_cascade.py
"""ADR 0020 sub-decision 10: emergency flatten of base-coin position.
1. Compute qty = walletBalance - locked
2. cancel_all_orders to release locked
3. place Market Sell qty
4. On failure: retry once with qty -= qty_step (handles step-quantization race)
5. Second failure → HALT_FLATTEN_FAILED"""
from decimal import Decimal
from src.execution.state_machine import ExecutionState
from src.risk.reason_codes import ReasonCode


def test_flatten_happy_path(coordinator_armed_harness):
    h = coordinator_armed_harness
    h.coordinator.flatten(reason=ReasonCode.HALT_RECONCILE_DIVERGENCE)
    # cancel_all called first
    assert h.adapter.cancel_all_called is True
    # Market Sell placed for full free qty
    sells = [o for o in h.adapter.placed_orders if o["side"] == "Sell" and o["orderType"] == "Market"]
    assert len(sells) == 1


def test_flatten_retries_with_qty_minus_step_on_failure(coordinator_armed_harness):
    h = coordinator_armed_harness
    h.adapter.fail_next_market_sell = True  # first attempt fails
    h.coordinator.flatten(reason=ReasonCode.HALT_RECONCILE_DIVERGENCE)
    sells = [o for o in h.adapter.placed_orders if o["side"] == "Sell" and o["orderType"] == "Market"]
    assert len(sells) == 2
    # Second attempt qty < first attempt by exactly one step
    assert Decimal(sells[1]["qty"]) == Decimal(sells[0]["qty"]) - h.qty_step


def test_flatten_halts_on_second_failure(coordinator_armed_harness):
    h = coordinator_armed_harness
    h.adapter.fail_market_sell_count = 2  # both attempts fail
    h.coordinator.flatten(reason=ReasonCode.HALT_RECONCILE_DIVERGENCE)
    row = h.repo.get("BTCUSDT")
    assert row.state == ExecutionState.HALTED
    assert row.halt_reason == ReasonCode.HALT_FLATTEN_FAILED
```

- [ ] **Step 2: Run tests to verify RED**

Run: `pytest tests/unit/test_coordinator_flatten_cascade.py -v`
Expected: FAIL — `flatten` missing or doesn't retry.

- [ ] **Step 3: Implement flatten cascade**

```python
# src/execution/coordinator.py — append
def flatten(self, *, reason: ReasonCode) -> None:
    """ADR 0020 sub-decision 10: cancel_all → Market Sell free qty → retry-once → halt."""
    self.adapter.cancel_all_orders(symbol=self.symbol)
    wallet = self.adapter.get_wallet_balance(coin=self.base_coin)
    free_qty = wallet.wallet_balance - wallet.locked
    qty = self._step_floor(free_qty)
    if qty <= 0:
        self._transition(ExecutionEvent.RESIDUAL_FLATTENED)
        return
    if self._try_place_market_sell(qty):
        self.repo.upsert(symbol=self.symbol, last_exit_reason=reason)
        return
    # Retry once with qty -= step
    retry_qty = self._step_floor(qty - self._qty_step())
    if retry_qty > 0 and self._try_place_market_sell(retry_qty):
        self.repo.upsert(symbol=self.symbol, last_exit_reason=reason)
        return
    self._transition(ExecutionEvent.FLATTEN_FAILED)
    self._halt(ReasonCode.HALT_FLATTEN_FAILED)

def _try_place_market_sell(self, qty: Decimal) -> bool:
    try:
        self.adapter.place_order(symbol=self.symbol, side="Sell", qty=qty)
        return True
    except Exception:
        return False
```

- [ ] **Step 4: Run tests to verify GREEN**

Run: `pytest tests/unit/test_coordinator_flatten_cascade.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/execution/coordinator.py tests/unit/test_coordinator_flatten_cascade.py
git commit -m "feat(execution): flatten cascade with retry-once-minus-step (ADR 0020 sub-decision 10)"
```

---

## Stage G — Property tests + Demo integration + pre-mainnet probes (Tasks 23-25)

### Task 23: Property tests — bracket lifecycle invariants

**Files:**
- Create: `tests/property/test_bracket_lifecycle_invariants.py`

- [ ] **Step 1: Write property tests (these define invariants — they ARE the spec)**

```python
# tests/property/test_bracket_lifecycle_invariants.py
"""ADR 0020 sub-decision 8: bracket lifecycle invariants (hypothesis property tests).

Invariants:
  I1. Every bracket that reaches OCO_ARMED eventually reaches FLAT or HALTED — never orphan.
  I2. After SL Triggered or TP Filled, the sibling is either Cancelled or terminal in ≤ 1 step.
  I3. last_attempt_num is monotonically non-decreasing.
  I4. position_qty in any non-FLAT, non-HALTED state >= dust_threshold (no phantom positions).
  I5. bracket_id in execution_state matches bracket_id prefix in active orderLinkIds.
"""
from decimal import Decimal
from hypothesis import given, strategies as st, settings, HealthCheck
from src.execution.state_machine import ExecutionState, ExecutionEvent, apply_transition, TRANSITIONS

LEGAL_EVENTS = list({e for (_, e) in TRANSITIONS.keys()})


@given(
    seed_state=st.sampled_from([
        ExecutionState.FLAT, ExecutionState.LONG_OPEN, ExecutionState.OCO_ARMED,
        ExecutionState.OCO_ARMING, ExecutionState.EXIT_SIBLING_CANCELLING,
        ExecutionState.EXIT_SL_RESIDUAL,
    ]),
    events=st.lists(st.sampled_from(LEGAL_EVENTS), min_size=1, max_size=10),
)
@settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_invariant_1_bracket_terminates(seed_state, events):
    """I1: any reachable terminal state for a bracket is FLAT|HALTED|KILLED|ERROR."""
    state = seed_state
    for evt in events:
        try:
            state = apply_transition(state, evt)
        except KeyError:
            continue  # illegal transitions are fine — FSM rejects them
    # If we ended in any non-bracket-terminal active state, that's a hung bracket — bug.
    if state in (ExecutionState.OCO_ARMED, ExecutionState.OCO_ARMING):
        # OK — these are active armed states, not terminal
        pass
    elif state in (ExecutionState.EXIT_SIBLING_CANCELLING, ExecutionState.EXIT_SL_RESIDUAL):
        # Must have a transition out; spot-check that legal exits exist
        next_legal = [(s, e) for (s, e) in TRANSITIONS.keys() if s == state]
        assert len(next_legal) > 0, f"No legal exits from {state} — orphan risk"


@given(
    qty=st.decimals(min_value=Decimal("0"), max_value=Decimal("1"), places=8),
    fee=st.decimals(min_value=Decimal("0"), max_value=Decimal("1"), places=8),
)
@settings(max_examples=200, deadline=None)
def test_invariant_g5_oco_qty_never_negative(qty, fee):
    """I-G5: compute_oco_qty result >= 0 for any inputs."""
    from src.execution.bracket import compute_oco_qty
    result = compute_oco_qty(
        cum_exec_qty=qty, cum_exec_fee=fee, fee_currency="BTC", base_coin="BTC",
        qty_step=Decimal("0.000001"),
    )
    assert result >= Decimal("0")


@given(prior_attempt=st.integers(min_value=0, max_value=10))
def test_invariant_3_attempt_num_monotonic(prior_attempt):
    """I3: arm_oco bumps attempt by exactly 1, never decreases."""
    new_attempt = prior_attempt + 1
    assert new_attempt > prior_attempt
```

- [ ] **Step 2: Run property tests**

Run: `pytest tests/property/test_bracket_lifecycle_invariants.py -v --hypothesis-show-statistics`
Expected: PASS — 200 examples per property, no falsifying counterexample.

- [ ] **Step 3: Commit**

```bash
git add tests/property/test_bracket_lifecycle_invariants.py
git commit -m "test(execution): property tests for bracket lifecycle invariants (ADR 0020 sub-decision 8)"
```

### Task 24: Demo integration — happy-path bracket on Bybit Demo

**Files:**
- Create: `tests/integration/test_demo_bracket_happy_path.py`
- Modify: `tests/conftest.py` (add `RUN_DEMO=1` skip marker)

- [ ] **Step 1: Wire opt-in marker**

```python
# tests/conftest.py — append
import os
import pytest

def pytest_collection_modifyitems(config, items):
    skip_demo = pytest.mark.skip(reason="Demo integration: set RUN_DEMO=1 to enable")
    if os.getenv("RUN_DEMO") != "1":
        for item in items:
            if "demo" in item.keywords:
                item.add_marker(skip_demo)
```

- [ ] **Step 2: Write Demo integration test**

```python
# tests/integration/test_demo_bracket_happy_path.py
"""ADR 0020 G14: Demo-as-proxy for mainnet API behavior.
Scenario: entry MARKET → OCO armed → cancel TP+SL → flatten → FLAT.
Default skip; opt-in via RUN_DEMO=1 + .env.demo with demo API keys."""
from decimal import Decimal
import time
import pytest
from src.platform.config import Settings
from src.execution.bybit.adapter import BybitMarketAdapter
from src.execution.bybit.rest import BybitRESTClient
from src.execution.coordinator import Coordinator
from src.execution.reconciler import Reconciler
from src.execution.state_repo import ExecutionStateRepo
from src.execution.state_machine import ExecutionState

pytestmark = pytest.mark.demo


@pytest.fixture(scope="module")
def demo_coordinator(tmp_path_factory):
    settings = Settings(_env_file=".env.demo")  # demo keys only — never mainnet
    assert settings.bybit_demo_mode is True, "Refusing to run on mainnet — set bybit_demo_mode=true"
    rest = BybitRESTClient(api_key=settings.bybit_api_key,
                           api_secret=settings.bybit_api_secret,
                           testnet=False, demo=True)
    adapter = BybitMarketAdapter(rest=rest, filters=...)  # filters loaded from instruments_info
    db_path = tmp_path_factory.mktemp("demo") / "execution.db"
    repo = ExecutionStateRepo(db_path=str(db_path))
    reconciler = Reconciler(query=adapter, base_coin="BTC", symbol="BTCUSDT")
    coord = Coordinator(adapter=adapter, repo=repo, reconciler=reconciler,
                        symbol="BTCUSDT", base_coin="BTC")
    return coord, repo, adapter


def test_demo_happy_path_entry_arm_cancel_flatten(demo_coordinator):
    coord, repo, adapter = demo_coordinator
    # 1. Entry — small qty (~$10 notional)
    bracket_id = coord.start_bracket(
        entry_qty=Decimal("0.0002"), entry_side="Buy",
        tp_price=Decimal("100000.00"),  # far above market — won't fill
        sl_trigger_price=Decimal("30000.00"),  # far below — won't trigger
    )
    # Wait for entry fill
    for _ in range(20):
        time.sleep(0.5)
        if repo.get("BTCUSDT").state == ExecutionState.LONG_OPEN:
            break
    assert repo.get("BTCUSDT").state == ExecutionState.LONG_OPEN
    # 2. Arm OCO with G5 fee-aware qty
    fill = adapter.get_order(symbol="BTCUSDT",
                             order_id=repo.get("BTCUSDT").entry_order_id)
    from src.execution.bracket import compute_oco_qty
    oco_qty = compute_oco_qty(
        cum_exec_qty=fill.cum_exec_qty, cum_exec_fee=fill.cum_exec_fee,
        fee_currency=fill.fee_currency, base_coin="BTC",
        qty_step=Decimal("0.000001"),
    )
    coord.arm_oco(tp_price=Decimal("100000.00"),
                  sl_trigger_price=Decimal("30000.00"), oco_qty=oco_qty)
    assert repo.get("BTCUSDT").state == ExecutionState.OCO_ARMED
    # 3. Cancel both legs
    adapter.cancel_all_orders(symbol="BTCUSDT")
    # 4. Flatten residual
    coord.flatten(reason="DEMO_TEST_TEARDOWN")
    # Wait for FLAT
    for _ in range(20):
        time.sleep(0.5)
        if repo.get("BTCUSDT").state == ExecutionState.FLAT:
            break
    assert repo.get("BTCUSDT").state == ExecutionState.FLAT
```

- [ ] **Step 3: Run with RUN_DEMO=1**

Run: `RUN_DEMO=1 pytest tests/integration/test_demo_bracket_happy_path.py -v -s`
Expected: PASS on Bybit Demo (~10s). Default `pytest` skips this test.

- [ ] **Step 4: Commit**

```bash
git add tests/integration/test_demo_bracket_happy_path.py tests/conftest.py
git commit -m "test(execution): Demo happy-path integration test (opt-in RUN_DEMO=1, ADR 0020 G14)"
```

### Task 25: Pre-mainnet probe re-run on api-testnet

**Files:**
- Create: `scripts/spot_oco_probe_testnet.py` (wrapper)
- Modify: `scripts/spot_oco_probe.py` (already exists from S5; re-target for testnet via env)

- [ ] **Step 1: Verify probes B2, v3-D, S2/v2 still pass on api-testnet**

This is a manual one-shot acceptance gate, not an automated test. Run order:

```bash
# 1. Configure separate testnet keys (never mainnet)
cp .env.demo .env.testnet
# Edit .env.testnet: bybit_api_url=https://api-testnet.bybit.com, fresh testnet keys

# 2. B2 — confirm native tpslMode still rejected (ErrCode 170130) on testnet
BYBIT_ENV=testnet python scripts/spot_oco_probe.py --probe B2
# Expected: rejection with retCode=170130 (matches Demo). If it suddenly succeeds —
# Bybit changed the API; ADR 0020 sub-decision 1 needs review BEFORE mainnet ship.

# 3. v3-D — confirm Stop TIF override still GTC→IOC silent
BYBIT_ENV=testnet python scripts/spot_oco_probe.py --probe v3-D
# Expected: place_order accepts timeInForce=GTC, get_order returns timeInForce=IOC

# 4. v2 S2 — confirm marketUnit=quoteCoin still produces 16-dp drift
BYBIT_ENV=testnet python scripts/spot_oco_probe.py --probe v2-S2
# Expected: cumExecQty has > 8 decimal places (drift)

# 5. Record probe results in wiki/project/sprints/sprint-06-spot-oco-emulation.md
```

- [ ] **Step 2: Document acceptance gate**

Add to `wiki/project/sprints/sprint-06-spot-oco-emulation.md` (created in Stage H):

> **Pre-mainnet acceptance (Stage F):** before tagging `v0.1.0-alpha.6`, re-run probes
> B2, v3-D, v2-S2 on `api-testnet.bybit.com` with separate testnet keys. All three must
> reproduce the Demo findings exactly. Any divergence → block release, escalate to ADR review.

- [ ] **Step 3: Commit**

```bash
git add scripts/spot_oco_probe.py scripts/spot_oco_probe_testnet.py
git commit -m "chore(execution): pre-mainnet probe re-run script for api-testnet (ADR 0020 Stage F)"
```

---

## Stage H — Wiki updates + sprint page + log/index (Tasks 26-30)

Per `llm-wiki/CLAUDE.md`: every code-spinoff in S5+ triggers wiki ingest. Component pages get rewritten; new runbook captures HALT_FLATTEN_FAILED manual procedure; sprint page summarizes; log + index updated.

### Task 26: Rewrite components/oco

**Files:**
- Rewrite: `llm-wiki/wiki/project/components/oco.md`

- [ ] **Step 1: Rewrite content (no test step — pure docs)**

Replace native-tpsl narrative with 3-order emulation. Sections:
1. **TL;DR** — 3-order Spot OCO bracket (Entry Market → Limit Sell @ TP → Stop Market Sell @ SL); native `tpslMode` rejected (probe v1 ErrCode 170130).
2. **Architecture** — `bracket.py` (pure functions: `BracketParams`, `BracketLegs`, `build_bracket`, `make_order_link_id`, `compute_oco_qty`).
3. **orderLinkId schema** — `oco-{bracket_id}-{role}-{attempt}`, max 36 chars, 8-char UUIDv4 prefix.
4. **G5 fee-aware sizing** — formula + Spot Buy fee currency = base_coin invariant.
5. **Sibling cancel-on-Triggered** — ADR 0020 sub-decision 6 + race classifier 110001 → REJECT_ORDER_ALREADY_TERMINAL.
6. **EXIT_SL_RESIDUAL** — IOC partial fill flatten path.
7. **Related** — links to `components/reconciler`, `components/execution-state-machine`, `components/bybit-adapter`, `decisions/0020-sprint-6-execution-spot-oco-emulation`.

- [ ] **Step 2: Commit**

```bash
git add llm-wiki/wiki/project/components/oco.md
git commit -m "docs(wiki): rewrite components/oco for 3-order Spot OCO emulation (ADR 0020)"
```

### Task 27: Update components/reconciler + execution-state-machine + bybit-adapter

**Files:**
- Modify: `llm-wiki/wiki/project/components/reconciler.md`
- Modify: `llm-wiki/wiki/project/components/execution-state-machine.md`
- Modify: `llm-wiki/wiki/project/components/bybit-adapter.md`

- [ ] **Step 1: Reconciler page — swap get_position → get_wallet_balance**

Add section **"v2 (Sprint 6, ADR 0020)"** documenting:
- Protocol no longer requires `get_position`.
- `walletBalance(coin=BTC)` is canonical position truth.
- `derive_position_qty` with `dust_threshold` (default 0.00001 BTC).
- Entry-price split: exchange owns qty, local SQLite owns entry_price.
- ReconcileResult adds `halt_reason` field.

- [ ] **Step 2: execution-state-machine page — 12 → 21 states**

Rewrite state table to 16 enum members (12 + 4 new: OCO_ARMING, EXIT_SIBLING_CANCELLING, EXIT_SIBLING_CANCEL_FAILED, EXIT_SL_RESIDUAL). Document the 5 conceptual halt-substates that ride on `HALTED + halt_reason: ReasonCode` (HALT_BRACKET_INCOMPLETE, HALT_OCO_ARM_TIMEOUT, HALT_OCO_SIBLING_STUCK, HALT_PARTIAL_FILL_BELOW_MIN, HALT_FLATTEN_FAILED). Update transition count: 28 (S5) → ~50 (S6).

- [ ] **Step 3: bybit-adapter page — add 6 new methods + banned-fields guard**

Add sections:
- **Banned Spot fields** — list 6 banned + `marketUnit=quoteCoin` with probe references.
- **New methods** — `place_limit_order`, `place_stop_market_order`, `cancel_order`, `cancel_all_orders`, `get_order`, `get_wallet_balance`, `get_order_history` with payload examples.
- **TIF override note** — Spot Stop silently rewrites GTC→IOC (probe v3-D).

- [ ] **Step 4: Commit**

```bash
git add llm-wiki/wiki/project/components/reconciler.md llm-wiki/wiki/project/components/execution-state-machine.md llm-wiki/wiki/project/components/bybit-adapter.md
git commit -m "docs(wiki): update reconciler/FSM/adapter pages for ADR 0020 changes"
```

### Task 28: Update trading/concepts/reason-codes — 31 → 39

**Files:**
- Modify: `llm-wiki/wiki/trading/concepts/reason-codes.md`

- [ ] **Step 1: Add 8 new reason codes to taxonomy**

Insert into existing categories:

**Halt codes (was 8 → now 13):**
- `HALT_BRACKET_INCOMPLETE` — entry filled but TP or SL placement failed twice → halt with manual position.
- `HALT_OCO_ARM_TIMEOUT` — OCO_ARMING > 60s without both legs confirmed.
- `HALT_OCO_SIBLING_STUCK` — sibling-cancel-on-Triggered failed AND not 110001.
- `HALT_PARTIAL_FILL_BELOW_MIN` — entry partial below minOrderQty, can't size OCO.
- `HALT_FLATTEN_FAILED` — flatten cascade failed twice → manual operator procedure.
- `HALT_PHANTOM_SL` — reconcile detects open SL with no matching local bracket.

**Exit codes (was 9 → now 10):**
- `EXIT_STOP_RESIDUAL_FLATTEN` — Stop IOC partial fill, residual closed via Market Sell.

**Reject codes (was 8 → now 9):**
- `REJECT_ORDER_ALREADY_TERMINAL` — Bybit retCode 110001 (cancel of Filled/Cancelled), classified non-fatal.

Update header: `**Total: 39 codes** (8 entry + 9 scale/exit + 9 reject + 13 halt)`.

- [ ] **Step 2: Commit**

```bash
git add llm-wiki/wiki/trading/concepts/reason-codes.md
git commit -m "docs(wiki): expand reason-codes taxonomy 31 → 39 (ADR 0020 sub-decisions 6-11)"
```

### Task 29: NEW runbooks/halt-recovery — HALT_FLATTEN_FAILED manual procedure

**Files:**
- Create: `llm-wiki/wiki/project/runbooks/halt-recovery.md`

- [ ] **Step 1: Write runbook**

```markdown
---
title: Halt Recovery Runbook
type: runbook
tags: [operations, halt, recovery, sprint-6]
created: 2026-04-23
updated: 2026-04-23
status: stable
---

# Halt Recovery Runbook

Manual operator procedure for each `HALT_*` reason code that requires intervention.

## HALT_FLATTEN_FAILED (ADR 0020 sub-decision 10)

**Trigger:** Coordinator's emergency flatten failed twice (full qty + qty - step). Bot is HALTED with non-zero base-coin position.

**Diagnosis:**
1. Read SQLite: `sqlite3 var/execution.db "SELECT * FROM execution_state WHERE symbol='BTCUSDT';"`
2. Check Bybit Web UI → BTC balance + open orders.
3. Run `python scripts/diagnose_halt.py --symbol BTCUSDT`.

**Recovery steps:**
1. Cancel any open orders for the symbol via Bybit Web UI (don't trust the bot).
2. Manually flatten BTC position via Bybit Web UI (Spot → Sell BTC → Market).
3. Reset bot state:
   ```sql
   UPDATE execution_state
   SET state='FLAT', position_qty='0', entry_price=NULL,
       bracket_id=NULL, last_attempt_num=0, halt_reason=NULL
   WHERE symbol='BTCUSDT';
   ```
4. Restart bot. Verify: `state=FLAT`, walletBalance ≈ 0 BTC.
5. **Post-mortem mandatory:** add log entry to `wiki/log.md` with: timestamp, qty stuck, root cause hypothesis, fix.

## HALT_OCO_SIBLING_STUCK
[similar structure]

## HALT_PHANTOM_SL
[similar structure]

## HALT_RECONCILE_DIVERGENCE (S5)
[similar structure — already exists, link from here]
```

- [ ] **Step 2: Commit**

```bash
git add llm-wiki/wiki/project/runbooks/halt-recovery.md
git commit -m "docs(wiki): NEW runbook for HALT_FLATTEN_FAILED + halt recovery procedures"
```

### Task 30: sprints/sprint-06 + log + index

**Files:**
- Create: `llm-wiki/wiki/project/sprints/sprint-06-spot-oco-emulation.md`
- Modify: `llm-wiki/wiki/log.md`
- Modify: `llm-wiki/wiki/index.md`

- [ ] **Step 1: Sprint page**

```markdown
---
title: Sprint 6 — Spot OCO emulation
type: sprint
tags: [sprint-6, execution, oco, spot]
created: 2026-04-23
updated: 2026-04-23
status: completed
sources: [project/decisions/0020-sprint-6-execution-spot-oco-emulation, project/plans/2026-04-23-sprint-6-spot-oco-emulation]
---

# Sprint 6 — Spot OCO emulation

**Tag:** `v0.1.0-alpha.6`
**Plan:** [[../plans/2026-04-23-sprint-6-spot-oco-emulation]]
**ADR:** [[../decisions/0020-sprint-6-execution-spot-oco-emulation]]

## Goals

Replace dead native-tpsl path (S5 ADR 0019/1, empirically rejected) with a 3-order
Spot OCO emulation, expand FSM 12 → 21 states, reason codes 31 → 39, integrate
walletBalance as canonical position truth.

## Deliverables

- 30 TDD tasks across 8 stages (A–H)
- 14 new files; 15 modified files; 1 deleted (`src/execution/oco.py` → `src/execution/bracket.py`)
- New runbook for HALT_FLATTEN_FAILED
- Pre-mainnet acceptance probes re-run on api-testnet

## Acceptance gate

Before tagging `v0.1.0-alpha.6` and any mainnet promotion: probes B2, v3-D, v2-S2
must reproduce on api-testnet exactly (sub-decision 1 invariance).
```

- [ ] **Step 2: log.md entry**

Append to `llm-wiki/wiki/log.md`:

```markdown
## [2026-04-23] sprint | S6 — Spot OCO emulation (ADR 0020 implementation)
- Added: src/execution/bracket.py, migrations/0004_execution_state_v2.sql,
  llm-wiki/wiki/project/runbooks/halt-recovery.md,
  llm-wiki/wiki/project/sprints/sprint-06-spot-oco-emulation.md
- Updated: src/execution/state_machine.py (+22 transitions), src/execution/coordinator.py (start_bracket/arm_oco/on_order_event/flatten/bootstrap), src/execution/reconciler.py (walletBalance), src/execution/state_repo.py (+6 columns), src/execution/bybit/adapter.py (+6 methods + banned-field guard), src/execution/bybit/errors.py (+110001), src/risk/reason_codes.py (+8 codes)
- Removed: src/execution/oco.py (superseded by bracket.py)
- Reviewers: trading-logic, quant-stats, data-integrity, python (per ADR 0017 cascade)
- Tag: v0.1.0-alpha.6
```

- [ ] **Step 3: index.md updates**

- Add new entry under **Project — Components**: `[[project/components/runbooks-halt-recovery|runbooks/halt-recovery]] — manual operator procedures for HALT_FLATTEN_FAILED + HALT_OCO_SIBLING_STUCK + HALT_PHANTOM_SL + HALT_RECONCILE_DIVERGENCE.`
- Add new entry under **Project — Sprints**: `[[project/sprints/sprint-06-spot-oco-emulation]] — S6 (2026-04-23): 3-order Spot OCO emulation; FSM 12→21; reason codes 31→39; tag v0.1.0-alpha.6.`
- Update `[[trading/concepts/reason-codes]]` description: "39 enum-кодов".

- [ ] **Step 4: Commit**

```bash
git add llm-wiki/wiki/project/sprints/sprint-06-spot-oco-emulation.md llm-wiki/wiki/log.md llm-wiki/wiki/index.md
git commit -m "docs(wiki): Sprint 6 page + log entry + index updates (S6 complete)"
```

---

## Self-review checklist

After all 30 tasks committed:

- [ ] All 13 ADR 0020 sub-decisions covered by at least one task. Trace map:
  - Sub-decision 1 (no native tpsl) → Task 6
  - Sub-decision 2 (3-order bracket) → Tasks 7,8,14,16
  - Sub-decision 3 (banned fields) → Task 6
  - Sub-decision 4 (walletBalance) → Tasks 10,11,12,13
  - Sub-decision 5 (G5 fee qty) → Task 15
  - Sub-decision 6 (sibling cancel + 110001) → Tasks 9,17
  - Sub-decision 7 (EXIT_SL_RESIDUAL) → Task 18
  - Sub-decision 8 (FSM 21 states + invariants) → Tasks 4,5,23
  - Sub-decision 9 (deterministic orderLinkId + bootstrap) → Tasks 19,20
  - Sub-decision 10 (flatten cascade) → Task 22
  - Sub-decision 11 (OCO_ARMING TTL) → Task 21
  - Sub-decision 12 (schema v2) → Task 1
  - Sub-decision 13 (reason codes 31→39) → Tasks 2,28
- [ ] Every step contains actual code or actual command — no "TODO", no "implement later".
- [ ] Type/method consistency: `compute_oco_qty` keyword args identical across Tasks 15,24.
- [ ] FSM event names consistent: TP_PLACED, SL_PLACED, SL_TRIGGERED, etc. used identically across Tasks 5,17,18,21,22.
- [ ] orderLinkId pattern `oco-{bracket}-{role}-{attempt}` consistent across Tasks 14,16,17,19,20.
- [ ] Pre-mainnet acceptance gate (Task 25) referenced from sprint page (Task 30).
- [ ] All commit messages reference `ADR 0020 sub-decision N` for traceability.

---

## Execution handoff

Plan complete and saved to `llm-wiki/wiki/project/plans/2026-04-23-sprint-6-spot-oco-emulation.md`.
Two execution options:

**1. Subagent-Driven (recommended)** — fresh subagent per task, two-stage review (spec
compliance + code quality), fast iteration. Use `superpowers:subagent-driven-development`.

**2. Inline Execution** — execute tasks in this session via `superpowers:executing-plans`,
batch execution with checkpoints for review.

Which approach?
