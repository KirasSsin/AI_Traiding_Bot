# Sprint 12 — Live demo validation 24-72h + production wiring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close `_NoopFillRecorder` + `_load_ohlcv` stubs from S11; ship FillRecorderAdapter с best-effort fill audit; deliver operator playbook for first 48h Bybit demo trading validation cycle.

**Architecture:** S12 = "validation sprint" — adds 2 small code paths (FillRecorderAdapter + Parquet shim) + 3 operator runbooks + ADR/sprint-page wiki sync. Live demo run itself executes post-merge by operator following plan-shipped runbook. Zero new SQL migrations (Q7 hard constraint enables alpha.11 binary rollback).

**Tech Stack:** Python 3.12, pydantic v2, sqlite3 (via Connection), pybit V5 WebSocket, pandas + pyarrow (data_collector reuse), structlog. Bybit demo trading endpoint (`demo.bybit.com` per Q6 verified-correct routing).

---

## Source verdicts trail

- ADR 0027 (status: proposed): `wiki/project/decisions/0027-sprint-12-live-demo-validation.md`
- PHASE 2 brainstorming verdicts: `wiki/project/pre-s12-backlog.md`
- Predecessor sprint: S11 ship `wiki/project/sprints/sprint-11-operator-readiness.md`

## Trace map (PHASE 3 step 1a HARD-GATE)

| Source verdict | Plan task | Reviewer | Tier |
|----------------|-----------|----------|------|
| Q1 CONFIRM (Bybit demo) | T4 runbook validation params | maintainer (operator setup) | docs |
| Q2 CONFIRM (48h duration) | T4 runbook validation params | maintainer | docs |
| Q3 CONFIRM (multi-criteria + zero-trade clause MANDATORY) | T4 runbook success gate section | maintainer | docs |
| Q4 REVISE-additive (Parquet shim) | T2 `_load_ohlcv` shim | python-reviewer | code-medium |
| Q4 follow-up (Gate 5 doc update) | T3 pre-flight Gate 5 update | inline review | docs |
| Q5 REVISE-additive (FillRecorderAdapter) | T1 FillRecorderAdapter | trading-logic + data-integrity (MANDATORY per ADR) | code-judgment-heavy |
| Q6 REVISE-DISAGREE-FACTUAL (NO endpoint change) | NO TASK — current correct, S13+ 3-way enum future | — | NEGATIVE-confirmation (already correct) |
| Q7 CONFIRM (P0-wake + alpha.11 rollback + zero-migration) | T5 halt-response runbook + T1/T2 zero-migration verification | maintainer | docs + verification |
| C1 (Q4+Q5 ordering) | Plan task order T1 → T2 → T3 enforces | — | — |
| C2 (Q5+Q3 zero-trade conditional) | T4 runbook zero-trade clause | — | docs |
| C3 (Q6 SPRINT_STATE corrected) | DONE pre-plan (commit `<pending>`) | — | — |
| C4 (Q7 zero-migration constraint) | Verification step in T1 + T2 (ls migrations/ unchanged) | — | gate |
| Sprint ship | T6 ADR accept + sprint page + wiki sync | sprint-finish skill | wiki |

---

## File Structure

**New files (S12):**
- `src/risk/fill_recorder_adapter.py` — `FillRecorderAdapter` class implementing `_FillRecorderProto`
- `tests/unit/test_fill_recorder_adapter.py` — adapter unit tests
- `wiki/project/runbooks/live-demo-validation.md` — operator playbook (48h Bybit demo run)
- `wiki/project/runbooks/halt-response-protocol.md` — P0 wake + alpha.11 rollback procedure
- `wiki/project/sprints/sprint-12-live-demo-validation.md` — canonical sprint summary (PHASE 8)

**Modified files (S12):**
- `src/__main__.py` — replace `_NoopFillRecorder` с `FillRecorderAdapter` instance в `_cmd_run`; implement Parquet shim в `_load_ohlcv`
- `wiki/project/runbooks/pre-flight.md` — Gate 5 update (Parquet pre-fetch prerequisite documented)
- `wiki/project/runbooks/halt-recovery.md` — P1+OCO_ARMED conditional escalation note
- `wiki/project/decisions/0027-sprint-12-live-demo-validation.md` — status `proposed` → `accepted` (PHASE 8)
- `wiki/project/architecture/current-state.md` — counts (ADR 26→27, sprint pages 13→14)
- `wiki/project/mental-map.md` — runbooks rows + components row для FillRecorderAdapter
- `wiki/index.md` — sprint-12 entry + 2 new runbooks + ADR 0027

**NOT touched (Q7 zero-migration constraint):**
- `migrations/*.sql` — verify unchanged via `git diff --name-only main..HEAD -- migrations/` returns empty

---

### Task 1: FillRecorderAdapter — best-effort fill audit + DB insert

**Files:**
- Create: `src/risk/fill_recorder_adapter.py`
- Create: `tests/unit/test_fill_recorder_adapter.py`
- Modify: `src/__main__.py:69-146` (`_cmd_run` — replace `_NoopFillRecorder` instantiation)

**Architecture rationale:**

Per Q5 trader REVISE: `FillHistoryRepository` cannot drop-in for `_NoopFillRecorder` (interface mismatch). Adapter required. Per Q7 zero-migration: NO new schema. Per current schema: NO direct WS-orderId → trade_id linkage exists (`execution_state` has `bracket_id` + 3 `oco_*_order_id` cols; `trade_history` has `entry_signal_id` UUID; NO bracket_id↔trade_id link).

**Resolution:** Adapter implements 2-layer pattern:
1. **Always-on:** structlog `fill_event_received` audit log (immutable JSON, recovery-safe)
2. **Best-effort DB insert:** Try lookup chain `WS orderId → execution_state row → trade_history (по entry_signal_id если совпадает с какой-то closed trade)`. If unresolved → structlog `fill_event_unresolved_skipping_db` warning. Skip insert.

This honors trader Q5 spec (adapter exists, parses, attempts insert) WITHOUT violating Q7 (zero schema changes) AND WITHOUT touching Coordinator (628-LoC fragile FSM). Full lossless DB persistence with proper bracket_id↔trade_id link deferred к S13+ (post live-demo surfaces real Bybit V5 event format quirks).

- [ ] **Step 1: Write failing test для evt parsing**

Create `tests/unit/test_fill_recorder_adapter.py`:

```python
"""FillRecorderAdapter — bridges Bybit V5 WS execution event → FillHistoryRepository.

S12 Q5 REVISE-additive (per ADR 0027):
- Always-on structlog audit
- Best-effort DB insert via lookup chain
- No new migrations (Q7 zero-migration constraint)
"""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from sqlite3 import Connection
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from src.risk.fill_history import FillHistoryRepository, FillRecord
from src.risk.fill_recorder_adapter import FillRecorderAdapter


def _make_evt(*, order_id: str = "BYBIT-ORD-1", exec_id: str = "EXEC-1") -> dict:
    """Minimal Bybit V5 execution topic item."""
    return {
        "orderId": order_id,
        "execId": exec_id,
        "execQty": "0.001",
        "execPrice": "50000.0",
        "execFee": "0.025",
        "feeRate": "0.001",
        "feeCurrency": "USDT",
        "execTime": "1735689600000",  # ms epoch
        "leavesQty": "0",  # 0 = fully filled (not partial)
    }


def test_adapter_parses_evt_to_fill_record_when_resolvable() -> None:
    """Resolvable orderId → FillRecord constructed with correct fields."""
    repo = MagicMock(spec=FillHistoryRepository)
    state_repo = MagicMock()
    trade_history_repo = MagicMock()

    # Resolve WS orderId → bracket → entry_signal_id → trade_id
    state_repo.find_by_order_id.return_value = MagicMock(
        bracket_id="BR-001",
        entry_signal_id=uuid4(),
    )
    trade_history_repo.find_trade_id_by_signal.return_value = 42  # trade_id

    adapter = FillRecorderAdapter(
        repo=repo,
        state_repo=state_repo,
        trade_history_repo=trade_history_repo,
    )
    adapter.on_fill_event(_make_evt())

    repo.insert_fill.assert_called_once()
    record = repo.insert_fill.call_args[0][0]
    assert record.parent_trade_id == 42
    assert record.exec_id == "EXEC-1"
    assert record.fill_qty == Decimal("0.001")
    assert record.fill_price == Decimal("50000.0")
    assert record.fill_fee == Decimal("0.025")
    assert record.fee_currency == "USDT"
    assert record.is_partial is False  # leavesQty=0


def test_adapter_skips_db_insert_when_orderid_missing(caplog: pytest.LogCaptureFixture) -> None:
    """No orderId → log warning + skip insert (no crash)."""
    repo = MagicMock(spec=FillHistoryRepository)
    adapter = FillRecorderAdapter(
        repo=repo,
        state_repo=MagicMock(),
        trade_history_repo=MagicMock(),
    )
    evt_no_order = _make_evt()
    del evt_no_order["orderId"]

    adapter.on_fill_event(evt_no_order)

    repo.insert_fill.assert_not_called()


def test_adapter_skips_db_insert_when_state_row_not_found() -> None:
    """orderId present but no execution_state row matches → skip insert (race-condition safe)."""
    repo = MagicMock(spec=FillHistoryRepository)
    state_repo = MagicMock()
    state_repo.find_by_order_id.return_value = None  # no match
    adapter = FillRecorderAdapter(
        repo=repo,
        state_repo=state_repo,
        trade_history_repo=MagicMock(),
    )

    adapter.on_fill_event(_make_evt())

    repo.insert_fill.assert_not_called()


def test_adapter_skips_db_insert_when_trade_history_row_not_yet_written() -> None:
    """Bracket resolved but trade not closed yet → trade_id None → skip insert (deferred S13)."""
    repo = MagicMock(spec=FillHistoryRepository)
    state_repo = MagicMock()
    state_repo.find_by_order_id.return_value = MagicMock(
        bracket_id="BR-001",
        entry_signal_id=uuid4(),
    )
    trade_history_repo = MagicMock()
    trade_history_repo.find_trade_id_by_signal.return_value = None  # trade not yet recorded

    adapter = FillRecorderAdapter(
        repo=repo,
        state_repo=state_repo,
        trade_history_repo=trade_history_repo,
    )
    adapter.on_fill_event(_make_evt())

    repo.insert_fill.assert_not_called()


def test_adapter_partial_fill_detected_via_leaves_qty_nonzero() -> None:
    """leavesQty > 0 → is_partial=True."""
    repo = MagicMock(spec=FillHistoryRepository)
    state_repo = MagicMock()
    state_repo.find_by_order_id.return_value = MagicMock(
        bracket_id="BR-001", entry_signal_id=uuid4()
    )
    trade_history_repo = MagicMock()
    trade_history_repo.find_trade_id_by_signal.return_value = 42

    adapter = FillRecorderAdapter(
        repo=repo,
        state_repo=state_repo,
        trade_history_repo=trade_history_repo,
    )
    evt_partial = _make_evt()
    evt_partial["leavesQty"] = "0.0005"

    adapter.on_fill_event(evt_partial)

    record = repo.insert_fill.call_args[0][0]
    assert record.is_partial is True
```

- [ ] **Step 2: Run test to verify FAIL**

```bash
source .venv/bin/activate
pytest tests/unit/test_fill_recorder_adapter.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'src.risk.fill_recorder_adapter'` OR `AttributeError: module ... has no attribute 'FillRecorderAdapter'`.

- [ ] **Step 3: Implement FillRecorderAdapter minimal**

Create `src/risk/fill_recorder_adapter.py`:

```python
"""FillRecorderAdapter — bridges Bybit V5 WS execution events → FillHistoryRepository.

S12 Q5 REVISE-additive (per ADR 0027). Best-effort 2-layer pattern:

1. **Always-on:** structlog audit log (`fill_event_received`).
2. **Best-effort DB insert:** Attempt lookup chain WS orderId → execution_state.bracket_id
   → trade_history.entry_signal_id → trade_id. Skip + warn если ANY step unresolved.

Full lossless persistence with bracket_id↔trade_id schema link deferred к S13+
(needs migration; Q7 hard constraint blocks for S12).

Race condition note: WS execution events MAY arrive before trade_history.insert_closed_trade
(trade still open, exit_ts not yet set). Adapter handles via skip+warn — operator
post-mortem reads structlog audit для unresolved fills.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Protocol

from src.risk.fill_history import FillHistoryRepository, FillRecord

logger = logging.getLogger(__name__)


class _StateRepoProto(Protocol):
    """Subset of ExecutionStateRepo used by adapter."""

    def find_by_order_id(self, order_id: str) -> Any | None: ...


class _TradeHistoryRepoProto(Protocol):
    """Subset of TradeHistoryRepository used by adapter."""

    def find_trade_id_by_signal(self, entry_signal_id: Any) -> int | None: ...


class FillRecorderAdapter:
    """Adapter implementing _FillRecorderProto (src/execution/bybit/ws_private.py).

    See module docstring для design rationale. Key invariant: NEVER crash on
    malformed WS event. Always log; insert only when fully resolved.
    """

    def __init__(
        self,
        *,
        repo: FillHistoryRepository,
        state_repo: _StateRepoProto,
        trade_history_repo: _TradeHistoryRepoProto,
    ) -> None:
        self._repo = repo
        self._state_repo = state_repo
        self._trade_history_repo = trade_history_repo

    def on_fill_event(self, evt: dict[str, Any]) -> None:
        """Parse Bybit V5 execution event → best-effort FillRecord insert.

        Error-swallowing pattern (mirrors ws_private._on_execution_raw): WS thread
        cannot crash on bad data.
        """
        # Layer 1: always-on audit
        logger.info("fill_event_received: evt=%r", evt)

        # Layer 2: best-effort DB insert
        order_id = evt.get("orderId")
        if not order_id:
            logger.warning("fill_event_unresolved_skipping_db: no orderId, evt=%r", evt)
            return

        state_row = self._state_repo.find_by_order_id(order_id)
        if state_row is None:
            logger.warning(
                "fill_event_unresolved_skipping_db: no execution_state for orderId=%s",
                order_id,
            )
            return

        trade_id = self._trade_history_repo.find_trade_id_by_signal(
            state_row.entry_signal_id
        )
        if trade_id is None:
            logger.warning(
                "fill_event_unresolved_skipping_db: trade_history not yet written for entry_signal_id=%s (race condition; deferred к S13)",
                state_row.entry_signal_id,
            )
            return

        # All resolved — build + insert
        try:
            record = self._build_fill_record(evt=evt, parent_trade_id=trade_id)
            self._repo.insert_fill(record)
        except Exception:
            logger.exception("fill_event_insert_failed: evt=%r", evt)

    @staticmethod
    def _build_fill_record(*, evt: dict[str, Any], parent_trade_id: int) -> FillRecord:
        """Map Bybit V5 execution item → FillRecord."""
        leaves_qty = Decimal(str(evt.get("leavesQty", "0")))
        return FillRecord(
            parent_trade_id=parent_trade_id,
            exec_id=str(evt["execId"]),
            fill_qty=Decimal(str(evt["execQty"])),
            fill_price=Decimal(str(evt["execPrice"])),
            fill_fee=Decimal(str(evt["execFee"])),
            fee_currency=str(evt.get("feeCurrency", "USDT")),
            is_partial=leaves_qty > 0,
            fill_ts=datetime.fromtimestamp(int(evt["execTime"]) / 1000, tz=UTC),
            recorded_at=datetime.now(UTC),
        )
```

- [ ] **Step 4: Run test to verify PASS**

```bash
pytest tests/unit/test_fill_recorder_adapter.py -v
```

Expected: 5 tests PASS.

- [ ] **Step 5: Add `find_by_order_id` to ExecutionStateRepo**

Verify method exists; if not, add.

```bash
grep -n "find_by_order_id" src/execution/state_repo.py
```

If missing, add to `src/execution/state_repo.py` (preserve existing API, just add lookup):

```python
def find_by_order_id(self, order_id: str) -> ExecutionStateRow | None:
    """Find execution_state row where any of oco_main/tp/sl_order_id matches.

    S12 Q5 — used by FillRecorderAdapter for WS orderId → bracket_id resolution.
    Returns None if no match (race-condition safe).
    """
    row = self._conn.execute(
        """SELECT * FROM execution_state
           WHERE oco_main_order_id = ? OR oco_tp_order_id = ? OR oco_sl_order_id = ?
           LIMIT 1""",
        (order_id, order_id, order_id),
    ).fetchone()
    return self._row_to_dataclass(row) if row else None
```

(Адаптируй точную сигнатуру к existing `_row_to_dataclass` helper в state_repo.py.)

- [ ] **Step 6: Add `find_trade_id_by_signal` to TradeHistoryRepository**

```bash
grep -n "find_trade_id_by_signal\|def find" src/risk/trade_history.py
```

If missing, add to `src/risk/trade_history.py`:

```python
def find_trade_id_by_signal(self, entry_signal_id: UUID) -> int | None:
    """Find trade_id by entry_signal_id (returns None если trade not yet closed).

    S12 Q5 — used by FillRecorderAdapter для parent_trade_id resolution.
    """
    row = self._conn.execute(
        "SELECT trade_id FROM trade_history WHERE entry_signal_id = ?",
        (str(entry_signal_id),),
    ).fetchone()
    return int(row[0]) if row else None
```

- [ ] **Step 7: Run state_repo + trade_history tests to verify additions don't break existing**

```bash
pytest tests/unit/test_state_repo.py tests/unit/test_trade_history.py -v
```

Expected: ALL existing tests still PASS + new methods coverage (add 1-2 short tests if reviewers request).

- [ ] **Step 8: Wire FillRecorderAdapter into _cmd_run**

Modify `src/__main__.py:69-146` (`_cmd_run` body):

DELETE the `_NoopFillRecorder` inner class (lines 72-81).

REPLACE the wiring section (around line 134-146):

```python
# OLD (DELETE):
# fill_recorder_stub = _NoopFillRecorder()

# NEW:
from src.risk.fill_history import FillHistoryRepository
from src.risk.fill_recorder_adapter import FillRecorderAdapter
from src.risk.trade_history import TradeHistoryRepository

fill_history_repo = FillHistoryRepository(conn)
trade_history_repo = TradeHistoryRepository(conn)
fill_recorder = FillRecorderAdapter(
    repo=fill_history_repo,
    state_repo=repo,  # ExecutionStateRepo already constructed line 110
    trade_history_repo=trade_history_repo,
)
```

THEN update `BybitPrivateWSConsumer(...)` call (line 139-146):

```python
ws_consumer = BybitPrivateWSConsumer(
    api_key=settings.bybit_api_key,
    api_secret=settings.bybit_api_secret,
    endpoint=endpoint,
    coordinator=coordinator,
    reconciler=reconciler,
    fill_recorder=fill_recorder,  # was: fill_recorder_stub
)
```

- [ ] **Step 9: Run _cmd_run wiring tests to verify integration**

```bash
pytest tests/unit/test_main_run_wiring.py -v
```

Expected: existing 3 tests PASS (DI test using MagicMock for adapter is OK).

- [ ] **Step 10: Verify zero new migrations (Q7 constraint)**

```bash
git diff --name-only main..HEAD -- migrations/
```

Expected: empty output (no migration files added/modified).

- [ ] **Step 11: Commit**

```bash
git add src/risk/fill_recorder_adapter.py tests/unit/test_fill_recorder_adapter.py src/__main__.py src/execution/state_repo.py src/risk/trade_history.py
git commit -m "$(cat <<'EOF'
feat(risk): T1 — FillRecorderAdapter (closes _NoopFillRecorder stub) (S12 Q5)

- New: FillRecorderAdapter implements _FillRecorderProto. 2-layer pattern:
  always-on structlog audit + best-effort DB insert via lookup chain
  (WS orderId → execution_state → trade_history → trade_id).
- Skip+warn если any resolution step fails (race-condition safe).
- Full lossless persistence with bracket_id↔trade_id schema link
  deferred к S13+ (Q7 zero-migration constraint).
- Wire в _cmd_run: replaces _NoopFillRecorder; uses existing
  FillHistoryRepository + TradeHistoryRepository.
- Add ExecutionStateRepo.find_by_order_id + TradeHistoryRepository.find_trade_id_by_signal
  helper methods.
- 5 unit tests; existing _cmd_run wiring tests still pass.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 12: Dispatch trading-logic-reviewer + data-integrity-reviewer (MANDATORY per ADR 0027)**

Two reviewers parallel — fresh dispatch each. Provide commit SHA + brief context.

trading-logic-reviewer brief: "S12 T1 commit `<sha>`. Review FillRecorderAdapter for fill event semantics + race conditions. Specifically: (1) WS event format assumptions (Bybit V5 execution topic — execId/execQty/execPrice/execFee/leavesQty); (2) parent_trade_id derivation race when WS event arrives before trade_history insert; (3) skip+warn behavior on unresolved events; (4) idempotency expectations downstream (FillHistoryRepository.insert_fill IDEMPOTENT on exec_id per existing UNIQUE INDEX)."

data-integrity-reviewer brief: "S12 T1 commit `<sha>`. Review FillRecorderAdapter for SQLite write integrity. Specifically: (1) FillHistoryRepository.insert_fill UNIQUE INDEX on exec_id (idempotency); (2) decimal handling (str conversion preserves precision); (3) WAL-mode safety при concurrent _cmd_monitor read-only access (S11 C2); (4) zero-migration verification (no schema changes — confirm via `git diff main..HEAD -- migrations/`)."

If reviewer flags issues → fix inline + new commit.

---

### Task 2: `_load_ohlcv` Parquet shim (closes WFA empty-df stub)

**Files:**
- Modify: `src/__main__.py:260-285` (`_load_ohlcv` function)
- Test: `tests/unit/test_main_wfa_cli.py` (extend existing)

**Architecture rationale:**

Per Q4 trader REVISE-additive: `data_collector.load_market_data(config: Dict[str, Any])` takes config dict, NOT `(symbol, start, end)` args. Shim translates CLI args → config dict. If Parquet missing → improved error message pointing to `python -m src backfill`.

- [ ] **Step 1: Write failing test**

Add to `tests/unit/test_main_wfa_cli.py`:

```python
def test_load_ohlcv_calls_data_collector_with_config_dict(tmp_path, monkeypatch):
    """T2 — _load_ohlcv translates CLI args → data_collector config dict."""
    import pandas as pd
    from unittest.mock import MagicMock, patch
    from src import __main__ as cli

    fake_df = pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=3, freq="1H"),
        "open": [100, 101, 102], "high": [105, 106, 107],
        "low": [99, 100, 101], "close": [103, 104, 105],
        "volume": [1.0, 2.0, 3.0],
    })

    parquet_file = tmp_path / "BTCUSDT_1h.parquet"
    fake_df.to_parquet(parquet_file)

    # Patch data_collector module load_market_data
    with patch("src.__main__.load_market_data") as mock_loader:
        mock_loader.return_value = fake_df
        result = cli._load_ohlcv(
            symbol="BTCUSDT", start="2024-01-01", end="2024-01-02"
        )

    assert not result.empty
    mock_loader.assert_called_once()
    config_arg = mock_loader.call_args[0][0]
    assert config_arg["data"]["source"] == "parquet"
    assert config_arg["data"]["start_date"] == "2024-01-01"
    assert config_arg["data"]["end_date"] == "2024-01-02"


def test_load_ohlcv_raises_helpful_error_when_parquet_missing(tmp_path):
    """T2 — Parquet missing → FileNotFoundError с operator-friendly message."""
    from src import __main__ as cli

    with pytest.raises(FileNotFoundError, match="python -m src backfill"):
        cli._load_ohlcv(
            symbol="BTCUSDT", start="2024-01-01", end="2024-01-02"
        )
```

- [ ] **Step 2: Run test to verify FAIL**

```bash
pytest tests/unit/test_main_wfa_cli.py::test_load_ohlcv_calls_data_collector_with_config_dict -v
pytest tests/unit/test_main_wfa_cli.py::test_load_ohlcv_raises_helpful_error_when_parquet_missing -v
```

Expected: FAIL (current `_load_ohlcv` returns empty DataFrame stub, no `load_market_data` call).

- [ ] **Step 3: Implement Parquet shim**

Modify `src/__main__.py:260` (`_load_ohlcv`):

```python
# OLD signature stays:
def _load_ohlcv(*, symbol: str, start: str, end: str) -> pd.DataFrame:
    """Load OHLCV from Parquet via data_collector.

    S12 T2: closes S11 stub. Reuses existing data_collector pipeline.
    Operator must run `python -m src backfill --symbol <X>` to populate Parquet first.
    """
    parquet_path = f"data/{symbol}_1h.parquet"
    config = {
        "data": {
            "source": "parquet",
            "parquet_path": parquet_path,
            "start_date": start,
            "end_date": end,
        }
    }
    try:
        return load_market_data(config)
    except FileNotFoundError as e:
        raise FileNotFoundError(
            f"OHLCV Parquet missing at {parquet_path}. "
            f"Run 'python -m src backfill --symbol {symbol} --from {start} --to {end}' first. "
            f"Original error: {e}"
        ) from e
```

Add import at top of `src/__main__.py`:

```python
from src.backtest.data_collector import load_market_data
```

- [ ] **Step 4: Run test to verify PASS**

```bash
pytest tests/unit/test_main_wfa_cli.py -v
```

Expected: ALL tests PASS (existing + 2 new).

- [ ] **Step 5: Commit**

```bash
git add src/__main__.py tests/unit/test_main_wfa_cli.py
git commit -m "$(cat <<'EOF'
feat(cli): T2 — _load_ohlcv Parquet shim (closes WFA stub) (S12 Q4)

- _load_ohlcv now delegates к data_collector.load_market_data with translated config dict.
- FileNotFoundError raises с operator-friendly message pointing to backfill cmd.
- 2 new tests: config dict structure + helpful error.
- Existing test_main_wfa_cli.py tests still pass.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 6: python-reviewer dispatch** (inline OK для small task)

Brief: "S12 T2 commit `<sha>`. Review _load_ohlcv shim для config dict translation correctness + import hygiene. Single small change, lightweight review."

---

### Task 3: pre-flight Gate 5 doc update + halt-recovery P1+OCO_ARMED note

**Files:**
- Modify: `wiki/project/runbooks/pre-flight.md` (Gate 5 section)
- Modify: `wiki/project/runbooks/halt-recovery.md` (priority matrix conditional escalation)

**Architecture rationale:**

Per Q4 follow-up: Gate 5 currently says "_load_ohlcv stub returns exit 1". After T2, it actually works — но requires Parquet pre-fetch. Document workflow.

Per Q7 trader concern: P1 `HALT_EXCHANGE_OUTAGE` while OCO_ARMED → escalate к CRITICAL per existing halt-recovery.md text. Make explicit in priority matrix.

- [ ] **Step 1: Read current Gate 5 + halt-recovery priority matrix**

```bash
grep -B 1 -A 12 "Gate 5" llm-wiki/wiki/project/runbooks/pre-flight.md
grep -B 2 -A 15 "Priority matrix" llm-wiki/wiki/project/runbooks/halt-recovery.md | head -40
```

- [ ] **Step 2: Update Gate 5 в pre-flight.md**

Replace existing Gate 5 section с:

```markdown
### Gate 5: WFA baseline (optional но recommended)

**Prerequisite:** Parquet OHLCV file для symbol+range must exist. If missing, run backfill first:

```bash
python -m src backfill --symbol BTCUSDT --from 2024-01-01 --to 2024-04-01
```

THEN run WFA:

```bash
python -m src wfa --symbol BTCUSDT --start 2024-01-01 --end 2024-04-01
```

**Expected:** JSON output с `acceptance_gate.passed`. If `passed: false`, strategy не fit для current data window — investigate before live.

**FAIL if:** `FileNotFoundError: OHLCV Parquet missing` — run backfill (above) and retry.
```

- [ ] **Step 3: Update halt-recovery.md priority matrix conditional**

Find existing `HALT_EXCHANGE_OUTAGE` row в Quick Reference Table. Add note in escalation column:

```markdown
| HALT_EXCHANGE_OUTAGE | Operational | P1 RECOVERABLE¹ | next morning |

¹ **Conditional escalation к P0:** Если bot was в `OCO_ARMED` state when outage fired AND outage > 1 hour
→ treat as CRITICAL: verify exchange state meticulously before restart (open OCO bracket
exposure during downtime).
```

OR add to "Priority matrix" section explicit conditional callout:

```markdown
### Conditional P1→P0 escalation

**HALT_EXCHANGE_OUTAGE + state == OCO_ARMED + outage > 1h:**
The bot may have an open OCO bracket whose TP/SL did not arm before exchange went down.
Risk: position exposed without protection. Operator MUST verify exchange-side state
(open orders + positions) BEFORE restarting bot. Treat as P0 wake (CRITICAL).
```

- [ ] **Step 4: Commit**

```bash
git add llm-wiki/wiki/project/runbooks/pre-flight.md llm-wiki/wiki/project/runbooks/halt-recovery.md
git commit -m "$(cat <<'EOF'
docs(runbook): T3 — pre-flight Gate 5 backfill prerequisite + halt-recovery P1+OCO_ARMED conditional escalation (S12 Q4 + Q7)

- pre-flight.md Gate 5: document Parquet pre-fetch prerequisite (post-T2).
- halt-recovery.md: explicit conditional P1→P0 escalation для HALT_EXCHANGE_OUTAGE
  while OCO_ARMED (per Q7 trader concern).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Live demo validation runbook (operator playbook)

**Files:**
- Create: `wiki/project/runbooks/live-demo-validation.md`

**Architecture rationale:**

Per Q1 + Q2 + Q3: 48h Bybit demo run, multi-criteria gate, zero-trade clause MANDATORY. Operator follows step-by-step playbook post-merge.

- [ ] **Step 1: Write runbook**

Create `wiki/project/runbooks/live-demo-validation.md`:

```markdown
---
title: Live demo validation — 48h Bybit demo run protocol
type: runbook
tags: [operator, live-demo, validation, sprint-12, bybit-demo]
created: 2026-04-25
updated: 2026-04-25
status: stable
sources:
  - project/decisions/0027-sprint-12-live-demo-validation.md
  - project/runbooks/pre-flight.md
  - project/runbooks/halt-recovery.md
---

# Live demo validation — 48h Bybit demo run

**TL;DR:** First end-to-end live cycle validation на Bybit demo trading endpoint. Per ADR 0027 verdicts (Q1+Q2+Q3): demo + 48h + multi-criteria gate + zero-trade clause.

## Pre-conditions (HARD-GATE before start)

ALL must pass:

1. ✅ All pre-flight gates pass per [[pre-flight|pre-flight checklist]] (5 critical + 4 recommendations)
2. ✅ Bybit demo API key + secret в `.env` (`BYBIT_API_KEY`, `BYBIT_API_SECRET`) — confirmed demo (not Mainnet)
3. ✅ `settings.testnet=True`, `settings.trading_enabled=False`, `settings.live_trading=False` per Gate 1
4. ✅ Database empty или rolled-back к alpha.11 baseline (Q7 zero-migration constraint preserved)
5. ✅ Operator availability: 5min monitoring cadence × 48h supervised window OR 2-person rotation
6. ✅ Kill-switch sentinel cleaned (Recommendation 3)
7. ✅ Disk space ≥ 1 GB (Recommendation 2)

## Validation params

| Parameter | Value | Source |
|-----------|-------|--------|
| Endpoint | `demo.bybit.com` (auto-routed via `settings.testnet=True`) | Q6 verified |
| Symbol | BTCUSDT | ADR 0026 baseline |
| Timeframe | 1H bars | ADR 0005 |
| Duration | 48h (48 1H bars) | Q2 trader CONFIRM |
| Virtual capital | $1000 USDT (Bybit demo arbitrary) | Q1 trader CONFIRM |
| Strategy | EMA(12)×EMA(26) + ADX + RSI + ATR | live config |

## Start sequence

```bash
# 1. Activate venv + verify config
source .venv/bin/activate
python -c "from src.platform.config import Settings; s = Settings(); print(f'testnet={s.testnet}, trading_enabled={s.trading_enabled}, live_trading={s.live_trading}')"
# Expected: testnet=True, trading_enabled=False, live_trading=False

# 2. Run reconcile-only smoke (last gate)
python -m src reconcile-only --symbol BTCUSDT
# Expected: "reconcile-only: bootstrap complete для BTCUSDT" + exit 0

# 3. Start bot, redirect к dated log
python -m src run --symbol BTCUSDT > "bot_$(date +%Y%m%d_%H%M%S).log" 2>&1 &
echo "Bot PID: $!" > /tmp/bot_pid.txt
```

## Monitoring (every 5 min, 48h)

In separate terminal(s):

```bash
# Terminal 1: tail logs filtered к warnings + errors
tail -f bot_*.log | jq 'select(.level == "warning" or .level == "error")'

# Terminal 2: periodic state snapshot
watch -n 300 'python -m src monitor --symbol BTCUSDT'

# Terminal 3: hourly halt-log SQL check
watch -n 3600 'sqlite3 ~/.ai_trading_bot/bot.db "SELECT halt_code, halted_at FROM halt_log ORDER BY halted_at DESC LIMIT 10"'
```

## Multi-criteria success gate (per Q3 trader CONFIRM)

Validation **PASSED** if ALL hold at end of 48h:

### Structural (always evaluated)

- ✅ **Zero P0 halts** (per [[halt-recovery]] priority matrix)
- ✅ **Reconcile divergence count = 0** (no `HALT_EXIT_RECONCILE_DIVERGENCE` events)
- ✅ **Bootstrap clean** (no `HALT_BOOTSTRAP_AMBIGUOUS`)
- ✅ **WS uptime ≥ 47/48h** (barring P1 outages with auto-resume)

### Trading (conditional on ≥ 1 fill occurring)

- ✅ **Drawdown ≤ 5%** (much tighter than L1 15% warn)
- ✅ **FillRecorder.insert_fill writes successful** (idempotent on duplicate exec_id; DB insert OR structlog audit covers)

### Zero-trade clause (MANDATORY — per Q3 trader concern)

**IF zero fills during 48h** (statistically likely on 1H BTC EMA crossover):
- Structural criteria still apply (P0=0, reconcile=0, bootstrap clean, WS uptime).
- Trading criteria (drawdown, FillRecorder live-path) **WAIVED** with explicit carry-forward к S13.
- Operator records "zero-trade outcome" в sprint-12-live-demo-validation.md + S13 carry-overs.
- This does NOT block S12 ship — S12 = infrastructure validation, NOT trade-edge confirmation.

### Operator sign-off (qualitative)

After 48h:
- Review `bot_*.log` для warnings/errors (non-halt)
- Review halt_log table for any halts
- Review monitor output for FSM state at termination
- Document anomalies even if not breaching criteria

If "no surprises" → sign-off `validation_status: PASSED` в sprint-12 page.

## End sequence

```bash
# 1. Trigger graceful shutdown (kill-switch sentinel)
python -m src kill --reason MANUAL_OPERATOR
# Wait for bot к exit

# 2. Verify clean exit
ps -p $(cat /tmp/bot_pid.txt) > /dev/null && echo "STILL RUNNING — check logs" || echo "exited cleanly"

# 3. Generate validation report
python -m src monitor --symbol BTCUSDT > validation_report_$(date +%Y%m%d_%H%M%S).txt
```

## On halt fire (any class)

См. [[halt-recovery]] priority matrix:
- **P0** → wake on-call immediately. Trigger [[halt-response-protocol]] rollback procedure если irreparable.
- **P1** → notification only. Если HALT_EXCHANGE_OUTAGE + OCO_ARMED + outage > 1h → ESCALATE к P0 (per S12 T3 conditional callout).
- **P2** → log only.

## Related

- [[pre-flight]] — entry criteria gates
- [[halt-recovery]] — halt code reference + priority matrix
- [[halt-response-protocol]] — P0 wake + rollback procedure
- [[../decisions/0027-sprint-12-live-demo-validation]] — ADR + verdicts trail
- [[log-grep-templates]] — log filtering recipes
```

- [ ] **Step 2: Commit**

```bash
git add llm-wiki/wiki/project/runbooks/live-demo-validation.md
git commit -m "$(cat <<'EOF'
docs(runbook): T4 — live-demo-validation.md operator playbook (S12 Q1+Q2+Q3)

- 48h Bybit demo BTCUSDT 1H validation protocol.
- Pre-conditions HARD-GATE.
- Multi-criteria success gate с MANDATORY zero-trade clause (per Q3 trader concern):
  если 0 fills during 48h → structural criteria only, FillRecorder live-path
  validation carried forward к S13.
- Start/monitoring/end sequences с explicit commands.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Halt-response operational runbook (P0 wake + rollback procedure)

**Files:**
- Create: `wiki/project/runbooks/halt-response-protocol.md`

**Architecture rationale:**

Per Q7 trader CONFIRM: P0-wake + alpha.11 rollback + RC tag iteration. Operator needs actionable procedure (which commands to run, in what order, decision tree).

- [ ] **Step 1: Write runbook**

Create `wiki/project/runbooks/halt-response-protocol.md`:

```markdown
---
title: Halt response protocol — P0 wake + alpha.11 rollback + RC iteration
type: runbook
tags: [operator, halt-response, rollback, sprint-12, p0-critical]
created: 2026-04-25
updated: 2026-04-25
status: stable
sources:
  - project/decisions/0027-sprint-12-live-demo-validation.md
  - project/runbooks/halt-recovery.md
---

# Halt response protocol — P0 wake + rollback

**TL;DR:** When P0 halt fires (CRITICAL severity per [[halt-recovery]] priority matrix), operator wake immediately, diagnose, decide rollback OR forward-fix. RC tag iteration enables iterative S12 fix attempts WITHOUT contaminating final v0.1.0-alpha.12 release.

## Decision tree

```
P0 halt fires
   │
   ├── Bot still running? → Kill via `python -m src kill --reason P0_RESPONSE`
   │
   ├── Diagnose halt code (см. halt-recovery.md priority matrix entry)
   │
   ├── Recoverable WITH operator action в-place?
   │  ├── YES → Apply recovery procedure от halt-recovery.md
   │  │      → Re-run pre-flight gates → restart bot → continue 48h validation
   │  │
   │  └── NO → Halt is showstopper. Decide rollback OR forward-fix:
   │
   │      ├── Forward-fix viable (< 4h to ship)? → Implement fix, RC tag iteration:
   │      │   git checkout -b fix/s12-rc.N feature/sprint-12-...
   │      │   <implement fix> + commit + test
   │      │   git tag -a v0.1.0-alpha.12-rc.N -m "S12 RC.N: <fix description>"
   │      │   <restart 48h validation от scratch>
   │      │
   │      └── Rollback к alpha.11 (preserve operator infra):
   │          git checkout main
   │          git revert <S12_merge_sha> -m 1  # revert merge commit
   │          git push origin main
   │          # Database safe: Q7 zero-migration constraint preserved binary compat
   │          # Re-tag NOT needed (alpha.11 still ships latest stable)
   │          # File S13 reopen ticket для S12 root cause investigation
```

## P0 halt response checklist (do in order)

1. **Stop the bot** (если still running):
   ```bash
   python -m src kill --reason P0_RESPONSE_<halt_code>
   sleep 5
   ps -p $(cat /tmp/bot_pid.txt) > /dev/null && echo "STILL RUNNING" || echo "stopped"
   ```

2. **Capture state snapshot** (do BEFORE any further actions):
   ```bash
   python -m src monitor --symbol BTCUSDT > halt_snapshot_$(date +%Y%m%d_%H%M%S).txt
   sqlite3 ~/.ai_trading_bot/bot.db "SELECT * FROM halt_log ORDER BY halted_at DESC LIMIT 5" >> halt_snapshot_*.txt
   sqlite3 ~/.ai_trading_bot/bot.db "SELECT * FROM execution_state" >> halt_snapshot_*.txt
   ```

3. **Cross-check exchange-side state** (Bybit demo console):
   - Open positions: 0 expected (or matches `execution_state.bracket_id` если OCO_ARMED)
   - Open orders: 0 expected (or matches OCO bracket: 1 entry или 2 TP/SL)
   - Account balance: matches `execution_state.equity`?

4. **Diagnose** per [[halt-recovery]] priority matrix entry для specific halt_code.

5. **Decide rollback OR forward-fix:**

   **Forward-fix criteria (RC tag iteration):**
   - Root cause identified within 1h
   - Fix implementable + testable within 4h
   - Test coverage exists OR can be added in same sprint
   - Schema unchanged (Q7 constraint)

   **Rollback criteria (alpha.11):**
   - Root cause unclear after 1h investigation
   - Fix requires schema change (violates Q7)
   - Fix touches > 3 components (architectural concern)
   - 2nd P0 halt within 12h (validation environment unstable)

## Rollback procedure (alpha.11)

Q7 zero-migration constraint enables clean binary rollback:

```bash
# 1. Verify alpha.11 binary compatibility
git log --oneline v0.1.0-alpha.11..HEAD -- migrations/ src/
# Expected: src/ changes ОК (compatible code), migrations/ EMPTY (Q7 constraint)

# 2. Revert merge commit
git checkout main
git pull
git revert <S12_squash_merge_sha> -m 1
git push origin main

# 3. Verify tags unchanged (alpha.11 still latest stable)
git tag --sort=-v:refname | head -3

# 4. Restart pre-flight + validation от scratch на alpha.11
git checkout v0.1.0-alpha.11
source .venv/bin/activate
python -m src reconcile-only --symbol BTCUSDT
# Expected: bootstrap clean

# 5. File S13 reopen ticket
echo "## S13 carry-over: S12 P0 rollback root cause" >> wiki/project/SPRINT_STATE.md
echo "halt_code: <code>, snapshot: halt_snapshot_*.txt" >> wiki/project/SPRINT_STATE.md
```

## RC tag iteration procedure

```bash
# After forward-fix implemented + tested
git add <fixed files>
git commit -m "fix(s12): rc.N — <root cause + fix description>"
git tag -a v0.1.0-alpha.12-rc.N -m "S12 RC.N: <one-line summary>"
git push origin v0.1.0-alpha.12-rc.N

# Restart 48h validation (start counter от 0)
# Document in sprint-12 page: "RC.N attempted, root cause: <X>, fix: <Y>"
```

Iterate RC.1, RC.2, ... до final clean 48h run. Then ship final `v0.1.0-alpha.12` (drop -rc suffix).

## Conditional escalation (P1 → P0)

Per Q7 trader concern: `HALT_EXCHANGE_OUTAGE` (P1 RECOVERABLE) → escalate к **P0 if state == OCO_ARMED + outage > 1h**:
- Bot might have open OCO bracket whose TP/SL не armed before outage
- Position exposed without protection
- Operator MUST verify exchange-side state (positions + open orders) BEFORE restart
- Treat as P0 wake; do not auto-resume

## Related

- [[halt-recovery]] — halt code reference + priority matrix
- [[live-demo-validation]] — entry context для when this runbook fires
- [[pre-flight]] — pre-restart entry gates after rollback
- [[../decisions/0027-sprint-12-live-demo-validation]] — Q7 verdict trail
```

- [ ] **Step 2: Commit**

```bash
git add llm-wiki/wiki/project/runbooks/halt-response-protocol.md
git commit -m "$(cat <<'EOF'
docs(runbook): T5 — halt-response-protocol.md (S12 Q7)

- P0 wake decision tree.
- Rollback procedure к v0.1.0-alpha.11 leveraging Q7 zero-migration constraint
  для clean binary compat.
- RC tag iteration procedure для forward-fix attempts.
- Conditional P1→P0 escalation (HALT_EXCHANGE_OUTAGE + OCO_ARMED + outage > 1h)
  per Q7 trader concern.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: ADR 0027 status: accepted + sprint-12 page + wiki sync (PHASE 8)

**Files:**
- Modify: `wiki/project/decisions/0027-sprint-12-live-demo-validation.md` (status: proposed → accepted)
- Create: `wiki/project/sprints/sprint-12-live-demo-validation.md`
- Modify: `wiki/index.md` (sprint-12 + 2 runbooks)
- Modify: `wiki/project/architecture/current-state.md` (counts: ADR 26→27, sprint pages 13→14)
- Modify: `wiki/project/mental-map.md` (operator runbooks rows + FillRecorderAdapter component)

**Architecture rationale:** PHASE 8 sprint-finish skill handles HARD-GATEs. Manual sprint page creation + counts sync.

- [ ] **Step 1: Update ADR 0027 status**

Edit `wiki/project/decisions/0027-sprint-12-live-demo-validation.md` frontmatter:

```yaml
status: accepted
```

- [ ] **Step 2: Verify canonical counts unchanged**

```bash
source .venv/bin/activate
python -c "from src.execution.state_machine import TRANSITIONS, ExecutionState, ExecutionEvent; from src.risk.reason_codes import ReasonCode; print(f'states={len(list(ExecutionState))}, events={len(list(ExecutionEvent))}, transitions={len(TRANSITIONS)}, reason_codes={len(list(ReasonCode))}')"
```

Expected: `states=16, events=30, transitions=74, reason_codes=45` (S12 = orchestration + docs, no FSM growth).

- [ ] **Step 3: Create sprint-12 page**

Create `wiki/project/sprints/sprint-12-live-demo-validation.md` per existing template (sprint-11-operator-readiness.md as reference). Required sections: Overview, Plan/ADR links, Deliverables (T1-T6 commits), FSM growth (NONE), Reason codes growth (NONE), Tests (pytest summary + mypy + ruff), Wiki updates, Open issues для S13+, Key decisions, Related.

- [ ] **Step 4: Update index.md**

Add к "Project — Sprints" section: `sprint-12-live-demo-validation` entry с tag info.

Add к "Project — Runbooks" section: 2 new runbooks (`live-demo-validation`, `halt-response-protocol`).

- [ ] **Step 5: Update current-state.md**

```markdown
| ADRs | **27** | wiki/project/decisions/*.md (0001-0027) | S12 (ADR 0027 — live-demo validation) |
| Sprint pages | **14** | wiki/project/sprints/sprint-*.md | S12 (sprint-12-live-demo-validation) |
```

Add S12 row к "Карта спринтов":

```markdown
| S12 | 0027 | v0.1.0-alpha.12 | 2026-04-XX | Live demo validation 24-72h + production wiring (FillRecorderAdapter + _load_ohlcv shim + 2 operator runbooks) |
```

Update TL;DR post-S12.

- [ ] **Step 6: Update mental-map.md**

Add к "Operator procedures" section:

```markdown
| Live demo validation 48h playbook | `project/runbooks/live-demo-validation.md` | S12 T4 — entry gates + monitoring + multi-criteria success gate с zero-trade clause |
| P0 halt response + rollback procedure | `project/runbooks/halt-response-protocol.md` | S12 T5 — P0 wake decision tree + alpha.11 rollback (Q7 zero-migration safe) + RC tag iteration |
```

Add к "Tooling / hooks / methodology" section:

```markdown
| FillRecorderAdapter (Bybit V5 WS exec → DB best-effort) | `src/risk/fill_recorder_adapter.py` (S12 Q5) — 2-layer pattern (structlog audit + best-effort DB insert via execution_state→trade_history lookup chain). Race-condition safe (skip+warn) |
```

- [ ] **Step 7: Run final pytest + mypy + ruff**

```bash
source .venv/bin/activate
pytest tests/ -q --ignore=tests/integration 2>&1 | tail -5
mypy --strict src/ 2>&1 | tail -3
git diff --name-only main..HEAD -- migrations/   # MUST be empty (Q7 verification)
```

Expected:
- pytest: 0 new failures (S12 adds ~5-7 tests; baseline 680 → ~685-687)
- mypy: clean (66 source files + 1 new = 67)
- migrations diff: empty (Q7 constraint)

- [ ] **Step 8: Commit T6 wiki sync**

```bash
git add wiki/project/decisions/0027-sprint-12-live-demo-validation.md \
        wiki/project/sprints/sprint-12-live-demo-validation.md \
        wiki/index.md \
        wiki/project/architecture/current-state.md \
        wiki/project/mental-map.md
git commit -m "$(cat <<'EOF'
docs(wiki): T6 — S12 wiki sync (ADR accepted + sprint page + counts + runbooks к index + mental-map) (S12)

Sprint 12 ship-ready wiki state:
- ADR 0027 status: proposed → accepted
- NEW: sprint-12-live-demo-validation.md
- index.md: +sprint-12 + 2 runbooks (live-demo-validation, halt-response-protocol)
- current-state.md: ADR 26→27, sprint pages 13→14, +S12 row
- mental-map.md: +operator runbooks rows + FillRecorderAdapter component row

Counts verified:
  states=16, events=30, transitions=74, reason_codes=45 (unchanged — S12 = orchestration + docs)
  ADRs=27, sprint pages=14, component pages=35 (incl. README)

Q7 zero-migration constraint verified: `git diff main..HEAD -- migrations/` empty.

Closes T6 of S12 plan.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 9: Invoke sprint-finish skill (PHASE 8 HARD-GATE checklist)**

Skill auto-trigger via "ship" / "финишируем". Skill handles:
- pre-validation final check (pytest + mypy + counts)
- HARD-GATE: sprint-NN.md exists ✅ (T6)
- HARD-GATE: canonical counts sync ✅ (T6)
- HARD-GATE: Block 1↔Block 2 component sync (FillRecorderAdapter — only Block 1 touched, OK)
- HARD-GATE: index.md ADR sync ✅ (T6)
- Update SPRINT_STATE → 8-ship
- Push + PR + squash-merge + tag v0.1.0-alpha.12

After tag: chapter mark "Sprint 12 ship complete".

---

## Self-review checklist

After plan completion, verify:

**1. Spec coverage:**
- ✅ Q1 (demo) — T4 (validation params)
- ✅ Q2 (48h) — T4
- ✅ Q3 (multi-criteria + zero-trade clause MANDATORY) — T4
- ✅ Q4 (Parquet shim) — T2 + T3 (Gate 5 update)
- ✅ Q5 (FillRecorderAdapter) — T1
- ✅ Q6 (NO endpoint change) — NO TASK (correctly noted в trace map as negative-confirmation)
- ✅ Q7 (P0 wake + alpha.11 rollback + zero-migration) — T5 + T1/T6 verification
- ✅ All 4 cross-cutting concerns mapped в trace map

**2. Placeholder scan:** ALL "TBD" / "TODO" / "implement later" replaced с actual code/commands.

**3. Type consistency:**
- `FillRecorderAdapter.__init__(repo, state_repo, trade_history_repo)` — same signature in test (Step 1) + implementation (Step 3) + wiring (Step 8)
- `_load_ohlcv(*, symbol, start, end)` — preserved from existing signature
- `find_by_order_id` / `find_trade_id_by_signal` — same names в test + implementation + adapter usage

## Execution Handoff

Plan complete + saved к `wiki/project/plans/2026-04-25-sprint-12-live-demo-validation.md`. Two execution options:

1. **Subagent-Driven (recommended)** — fresh subagent per task, two-stage review (spec compliance + code quality) between tasks
2. **Inline Execution** — execute tasks в this session via executing-plans skill, batch checkpoints

**Which approach?**
