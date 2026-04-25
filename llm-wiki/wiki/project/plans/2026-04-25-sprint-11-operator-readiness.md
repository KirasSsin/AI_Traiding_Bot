---
title: Sprint 11 — Operator-readiness + pre-flight gap closure
type: plan
tags: [sprint-11, plan, operator-readiness, cli, monitoring, pre-flight, di-wiring]
created: 2026-04-25
updated: 2026-04-25
status: active
sources:
  - project/pre-s11-backlog.md
  - project/decisions/0016-binance-spot-testnet-mvp.md
  - project/decisions/0022-sprint-8a-live-runtime.md
  - project/decisions/0025-sprint-10-wfa-dsr-mc.md
---

# Sprint 11 Implementation Plan — Operator-readiness + pre-flight

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) или `superpowers:executing-plans`. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Close pre-flight gaps blocking live execution (P0: test_risk_flow.py + _cmd_run + _cmd_reconcile_only + WFA CLI) + ship operator infrastructure (A scope: halt priority matrix + log grep templates + monitor CLI + pre-flight checklist) per pre-s11-backlog.md verdicts.

**Architecture:**
- P0 pre-flight: close S4-era test drift + S8a T20 STUB DI wiring + S10 WFA CLI exposure.
- A scope: extend halt-recovery.md (NOT new file per Q3 trader REVISE), new wiki pages для log grep + pre-flight, read-only monitor CLI subcommand.
- All operator deliverables consumed by S12 F (Live demo Mainnet validation).

**Tech Stack:** Python 3.12, argparse CLI, structlog JSON output, mypy --strict (S9 baseline), pytest unit + integration.

---

## Trace map (PHASE 3 step 1a HARD-GATE per dev-workflow.md)

### Files Created (3 wiki + 4 tests)

| Path | Responsibility | Task |
|------|----------------|------|
| `wiki/runbooks/log-grep-templates.md` | structlog grep patterns + halt_log SQL view | T6 |
| `wiki/runbooks/pre-flight.md` | Operator pre-flight checklist (config validate + testnet probe + balance check) | T8 |
| `wiki/project/sprints/sprint-11-operator-readiness.md` | Sprint summary | T10 |
| `tests/unit/test_main_run_wiring.py` | DI wiring smoke tests (4-5 tests) | T2 |
| `tests/unit/test_main_reconcile_only.py` | reconcile-only wiring tests | T3 |
| `tests/unit/test_main_wfa_cli.py` | WFA CLI subcommand tests | T4 |
| `tests/unit/test_main_monitor.py` | _cmd_monitor read-only tests | T7 |

### Files Modified (6 existing)

| Path | What changes | Task |
|------|--------------|------|
| `tests/integration/test_risk_flow.py:191` | Add `hmac_key=settings.risk_override_hmac_key` к OverrideStore ctor | T1 |
| `src/__main__.py:22-37` | Replace `_cmd_run` STUB с full DI wiring | T2 |
| `src/__main__.py:46-56` | Replace `_cmd_reconcile_only` STUB с DI wiring | T3 |
| `src/__main__.py` (append) | NEW `_cmd_wfa` + `_cmd_monitor` subcommands + parser entries | T4, T7 |
| `wiki/project/runbooks/halt-recovery.md` | Add "Priority matrix" section + "On-call escalation" column to Quick Reference Table | T5 |
| `wiki/project/architecture/current-state.md` | Counts 35→36 (sprint pages 12→13) + ADR 25→26 | T10 |

### ADRs

| ADR | Created/Modified | Task |
|-----|------------------|------|
| ADR 0026 (NEW) | Aggregate decisions: A-first scope ordering + DI wiring + monitor CLI read-only invariant + halt priority matrix integration | T9 |

### Wiki dependency map

```
S11 plan
├── PHASE 2 verdicts → pre-s11-backlog.md (already shipped 03f357c)
├── ADR 0026 (T9) — A-first + DI + monitor + priority matrix
├── Component pages: NONE new (per Q3 verdict — extend existing halt-recovery.md)
├── Sprint page (T10) — sprint-11-operator-readiness.md
├── 2 NEW runbook pages (T6+T8) — log-grep-templates + pre-flight
└── Modified: halt-recovery.md (priority matrix), current-state.md (counts)
```

### FSM impact

NONE. CLI subcommands = orchestration layer, не touches FSM. Counts unchanged: 16/30/74/45.

### DI feasibility (per cross-cutting concern C1)

Pre-plan read-pass verified — all constructors aligned:

```
Settings
├── BybitRestAdapter(api_key, api_secret, testnet) — marketdata REST
├── BybitMarketAdapter(rest, filters) — execution wrapper
├── ExecutionStateRepo(connection)
├── Reconciler(query=adapter, base_coin, symbol)
├── Coordinator(adapter, repo, reconciler, symbol, base_coin)
├── BarSource(adapter, symbol, interval)
├── EmaCrossoverAdxRsiStrategy(symbol + 7 strategy_* settings)
├── RiskManager(conn, settings)
├── BybitPrivateWSConsumer(api_key, api_secret, endpoint, coordinator, reconciler, fill_recorder)
└── RuntimeManager(coordinator, reconciler, ws_consumer, bar_source, strategy, risk_manager, settings)
```

Estimated `_cmd_run` LoC: ~80-120 (mostly orchestration). FillRecorder = MagicMock-equivalent stub (production wiring deferred S12+).

---

## Pre-flight verification (run before T1)

```bash
cd /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot
git status  # expect: clean (FULL_PROJECT_DOCUMENTATION.md untracked)
git checkout feature/sprint-11-operator-readiness  # already exists from PHASE 2
source .venv/bin/activate
pytest tests/unit -x -q 2>&1 | tail -3  # expect: 656 passed (S10 baseline)
mypy src/ 2>&1 | tail -2  # expect: Success in 66 source files
python -c "from src.execution.state_machine import TRANSITIONS, ExecutionState, ExecutionEvent; from src.risk.reason_codes import ReasonCode; print(f'states={len(list(ExecutionState))}, events={len(list(ExecutionEvent))}, transitions={len(TRANSITIONS)}, reason_codes={len(list(ReasonCode))}')"
# Expected: states=16, events=30, transitions=74, reason_codes=45
```

---

## P0 — Pre-flight gap closure (4 tasks)

### Task 1: test_risk_flow.py OverrideStore signature fix

**Files:**
- Modify: `tests/integration/test_risk_flow.py:191` (add hmac_key kwarg)
- Modify: `tests/integration/test_risk_flow.py:45` (verify settings fixture has risk_override_hmac_key)

**Steps:**

- [ ] **Step 1: Read existing test fixture**

```bash
source /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot/.venv/bin/activate
sed -n '40,60p' /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot/tests/integration/test_risk_flow.py
```

Identify: does fixture set `risk_override_hmac_key`? If not, add it (32+ chars per Field min_length).

- [ ] **Step 2: Verify RED**

```bash
pytest tests/integration/test_risk_flow.py -v 2>&1 | tail -10
```

Expected: `TypeError: OverrideStore.__init__() missing 1 required keyword-only argument: 'hmac_key'`.

- [ ] **Step 3: Apply fix**

Edit `tests/integration/test_risk_flow.py:191` — replace:

```python
    store = OverrideStore(override_path)
```

С:

```python
    store = OverrideStore(override_path, hmac_key=settings.risk_override_hmac_key)
```

ALSO verify fixture (around line 45) sets `risk_override_hmac_key`. If not, add к Settings construction:

```python
        risk_override_hmac_key="test_key_min_32_chars_for_audit_h2_compliance",
```

- [ ] **Step 4: Audit для other S4-era drift**

```bash
grep -n "OverrideStore\|CbOverride\|risk_override" /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot/tests/integration/test_risk_flow.py
```

Verify each call site matches current signatures. Fix inline if drift detected.

- [ ] **Step 5: Verify GREEN**

```bash
pytest tests/integration/test_risk_flow.py -v 2>&1 | tail -10
```

Expected: 1 passed.

- [ ] **Step 6: Commit**

```bash
cd /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot
git add tests/integration/test_risk_flow.py
git commit -m "fix(test): T1 — restore test_risk_flow.py OverrideStore hmac_key (S4-era drift) (S11 P0)"
```

---

### Task 2: _cmd_run DI wiring

**Files:**
- Modify: `src/__main__.py:22-37` (replace STUB с full wiring)
- Create: `tests/unit/test_main_run_wiring.py`

**architecture-reviewer MANDATORY post-implementation per pre-s11-backlog.md C1.**

**Steps:**

- [ ] **Step 1: Write failing tests (RED)**

Create `tests/unit/test_main_run_wiring.py`:

```python
"""Tests для _cmd_run DI wiring — Sprint 11 P0 (closes S8a T20 STUB).

Per pre-s11-backlog.md C1: architecture-reviewer mandatory post-impl.
"""
from __future__ import annotations

import argparse
from unittest.mock import MagicMock, patch

import pytest


def test_cmd_run_no_longer_stub_returns_zero_on_clean_exit() -> None:
    """_cmd_run no longer returns 1 (STUB error). Wires RuntimeManager."""
    from src import __main__ as cli

    args = argparse.Namespace(symbol="BTCUSDT", func=cli._cmd_run)

    # Patch RuntimeManager construction + run к verify wiring without live API
    with patch("src.__main__.RuntimeManager") as mock_rm_class:
        mock_rm = MagicMock()
        mock_rm.run.return_value = None  # Clean exit
        mock_rm_class.return_value = mock_rm

        # Patch Settings к skip env vars
        with patch("src.__main__.Settings") as mock_settings_class:
            mock_settings = MagicMock()
            mock_settings.bybit_api_key = "test_key_12345"
            mock_settings.bybit_api_secret = "test_secret_12345"
            mock_settings.testnet = True
            mock_settings.trading_symbol = "BTCUSDT"
            mock_settings.base_coin = "USDT"
            mock_settings.runtime_kill_switch_path = "/tmp/.kill_switch"
            mock_settings_class.return_value = mock_settings

            # Patch DI dependencies
            with patch("src.__main__.init_db"), \
                 patch("src.__main__.connect"), \
                 patch("src.__main__.BybitRestAdapter"), \
                 patch("src.__main__.BybitMarketAdapter"), \
                 patch("src.__main__.Reconciler"), \
                 patch("src.__main__.Coordinator"), \
                 patch("src.__main__.BarSource"), \
                 patch("src.__main__.EmaCrossoverAdxRsiStrategy"), \
                 patch("src.__main__.RiskManager"), \
                 patch("src.__main__.BybitPrivateWSConsumer"):

                exit_code = cli._cmd_run(args)
                assert exit_code == 0
                mock_rm.run.assert_called_once()


def test_cmd_run_propagates_keyboard_interrupt() -> None:
    """Ctrl+C during run() exits cleanly с code 130 (SIGINT convention)."""
    from src import __main__ as cli

    args = argparse.Namespace(symbol="BTCUSDT", func=cli._cmd_run)

    with patch("src.__main__.RuntimeManager") as mock_rm_class:
        mock_rm = MagicMock()
        mock_rm.run.side_effect = KeyboardInterrupt()
        mock_rm_class.return_value = mock_rm

        with patch("src.__main__.Settings") as mock_settings_class:
            mock_settings = MagicMock()
            mock_settings.bybit_api_key = "test_key_12345"
            mock_settings.bybit_api_secret = "test_secret_12345"
            mock_settings.testnet = True
            mock_settings.trading_symbol = "BTCUSDT"
            mock_settings.base_coin = "USDT"
            mock_settings.runtime_kill_switch_path = "/tmp/.kill_switch"
            mock_settings_class.return_value = mock_settings

            with patch("src.__main__.init_db"), \
                 patch("src.__main__.connect"), \
                 patch("src.__main__.BybitRestAdapter"), \
                 patch("src.__main__.BybitMarketAdapter"), \
                 patch("src.__main__.Reconciler"), \
                 patch("src.__main__.Coordinator"), \
                 patch("src.__main__.BarSource"), \
                 patch("src.__main__.EmaCrossoverAdxRsiStrategy"), \
                 patch("src.__main__.RiskManager"), \
                 patch("src.__main__.BybitPrivateWSConsumer"):

                exit_code = cli._cmd_run(args)
                assert exit_code == 130  # SIGINT


def test_cmd_run_returns_nonzero_on_runtime_crash() -> None:
    """Generic Exception during run() returns non-zero exit."""
    from src import __main__ as cli

    args = argparse.Namespace(symbol="BTCUSDT", func=cli._cmd_run)

    with patch("src.__main__.RuntimeManager") as mock_rm_class:
        mock_rm = MagicMock()
        mock_rm.run.side_effect = RuntimeError("simulated crash")
        mock_rm_class.return_value = mock_rm

        with patch("src.__main__.Settings") as mock_settings_class:
            mock_settings = MagicMock()
            mock_settings.bybit_api_key = "test_key_12345"
            mock_settings.bybit_api_secret = "test_secret_12345"
            mock_settings.testnet = True
            mock_settings.trading_symbol = "BTCUSDT"
            mock_settings.base_coin = "USDT"
            mock_settings.runtime_kill_switch_path = "/tmp/.kill_switch"
            mock_settings_class.return_value = mock_settings

            with patch("src.__main__.init_db"), \
                 patch("src.__main__.connect"), \
                 patch("src.__main__.BybitRestAdapter"), \
                 patch("src.__main__.BybitMarketAdapter"), \
                 patch("src.__main__.Reconciler"), \
                 patch("src.__main__.Coordinator"), \
                 patch("src.__main__.BarSource"), \
                 patch("src.__main__.EmaCrossoverAdxRsiStrategy"), \
                 patch("src.__main__.RiskManager"), \
                 patch("src.__main__.BybitPrivateWSConsumer"):

                exit_code = cli._cmd_run(args)
                assert exit_code == 1  # crash exit
```

- [ ] **Step 2: Verify RED**

```bash
source /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot/.venv/bin/activate
pytest tests/unit/test_main_run_wiring.py -v 2>&1 | tail -10
```

Expected: 3 fails (current `_cmd_run` returns 1 как STUB error, не wires RuntimeManager).

- [ ] **Step 3: Implement DI wiring**

Edit `src/__main__.py` — replace `_cmd_run` (lines 22-37):

```python
def _cmd_run(args: argparse.Namespace) -> int:
    """Wire all dependencies and start RuntimeManager.

    DI graph (per ADR 0026 + pre-s11-backlog C1):
    Settings → REST adapter → market adapter → DB connection → state repo →
    reconciler → coordinator → bar source → strategy → risk manager →
    WS consumer → RuntimeManager.run().

    FillRecorder = MagicMock-equivalent stub (production wiring S12+).
    """
    from pathlib import Path
    from sqlite3 import Connection
    from unittest.mock import MagicMock

    from src.execution.bybit.adapter import BybitMarketAdapter
    from src.execution.bybit.ws_private import BybitPrivateWSConsumer
    from src.execution.coordinator import Coordinator
    from src.execution.reconciler import Reconciler
    from src.execution.state_repo import ExecutionStateRepo
    from src.marketdata.bybit.rest import BybitRestAdapter
    from src.marketdata.filters import BybitFilters
    from src.platform.config import Settings
    from src.platform.db import connect, init_db
    from src.risk.manager import RiskManager
    from src.runtime.bar_source import BarSource
    from src.runtime.manager import RuntimeManager
    from src.signalgen.strategy import EmaCrossoverAdxRsiStrategy

    settings = Settings()
    symbol = args.symbol or settings.trading_symbol

    # Database
    mig_dir = Path(__file__).resolve().parent.parent / "migrations"
    init_db(settings.db_path, mig_dir)
    conn: Connection = connect(settings.db_path)

    # REST + market adapter (filters loaded via REST instruments-info on first call)
    rest = BybitRestAdapter(
        api_key=settings.bybit_api_key,
        api_secret=settings.bybit_api_secret,
        testnet=settings.testnet,
    )
    # Filters cached after first get_filters call; для now use defaults stub
    filters = BybitFilters(
        symbol=symbol,
        tick_size=Decimal("0.01"),
        qty_step=Decimal("0.000001"),
        min_qty=Decimal("0.00001"),
    )
    adapter = BybitMarketAdapter(rest=rest, filters=filters)

    # State + reconciler + coordinator
    repo = ExecutionStateRepo(conn)
    reconciler = Reconciler(query=adapter, base_coin=settings.base_coin, symbol=symbol)
    coordinator = Coordinator(
        adapter=adapter,
        repo=repo,
        reconciler=reconciler,
        symbol=symbol,
        base_coin=settings.base_coin,
    )

    # Strategy + risk manager
    strategy = EmaCrossoverAdxRsiStrategy(
        symbol=symbol,
        ema_fast=settings.strategy_ema_fast,
        ema_slow=settings.strategy_ema_slow,
        adx_period=settings.strategy_adx_period,
        adx_threshold=settings.strategy_adx_threshold,
        rsi_period=settings.strategy_rsi_period,
        rsi_oversold=settings.strategy_rsi_oversold,
        rsi_overbought=settings.strategy_rsi_overbought,
        atr_period=settings.strategy_atr_period,
    )
    risk_manager = RiskManager(conn=conn, settings=settings)

    # Bar source + WS consumer (FillRecorder stub — production wiring S12+)
    bar_source = BarSource(adapter=rest, symbol=symbol, interval="60")
    fill_recorder_stub = MagicMock()  # _FillRecorderProto-conformant stub
    fill_recorder_stub.on_fill_event = lambda evt: None

    endpoint = "demo.bybit.com" if settings.testnet else "stream.bybit.com"
    ws_consumer = BybitPrivateWSConsumer(
        api_key=settings.bybit_api_key,
        api_secret=settings.bybit_api_secret,
        endpoint=endpoint,
        coordinator=coordinator,
        reconciler=reconciler,
        fill_recorder=fill_recorder_stub,
    )

    # RuntimeManager + run
    rm = RuntimeManager(
        coordinator=coordinator,
        reconciler=reconciler,
        ws_consumer=ws_consumer,
        bar_source=bar_source,
        strategy=strategy,
        risk_manager=risk_manager,
        settings=settings,
    )

    try:
        rm.run()
        return 0
    except KeyboardInterrupt:
        return 130
    except Exception as e:  # noqa: BLE001
        import sys as _sys
        print(f"ERROR: runtime crash: {e}", file=_sys.stderr)
        return 1
```

ALSO add к imports at top of `__main__.py` (move imports к module-top для testability):

```python
from decimal import Decimal
```

(Per test mock requirements: import at module level, not inside function.)

NOTE: Patches в tests use `src.__main__.<Name>` — implementation MUST import names at module top. Refactor accordingly.

Module-top imports:

```python
from src.execution.bybit.adapter import BybitMarketAdapter
from src.execution.bybit.ws_private import BybitPrivateWSConsumer
from src.execution.coordinator import Coordinator
from src.execution.reconciler import Reconciler
from src.execution.state_repo import ExecutionStateRepo
from src.marketdata.bybit.rest import BybitRestAdapter
from src.marketdata.filters import BybitFilters
from src.platform.config import Settings
from src.platform.db import connect, init_db
from src.risk.manager import RiskManager
from src.runtime.bar_source import BarSource
from src.runtime.manager import RuntimeManager
from src.signalgen.strategy import EmaCrossoverAdxRsiStrategy
```

- [ ] **Step 4: Verify GREEN**

```bash
pytest tests/unit/test_main_run_wiring.py -v 2>&1 | tail -10
```

Expected: 3 passed.

- [ ] **Step 5: Verify mypy + ruff + full suite**

```bash
mypy src/__main__.py 2>&1 | tail -3
ruff check src/__main__.py tests/unit/test_main_run_wiring.py 2>&1 | tail -3
pytest tests/unit -x -q 2>&1 | tail -3
```

Expected: clean + 659+ passed (656 baseline + 3).

- [ ] **Step 6: Dispatch architecture-reviewer (MANDATORY per pre-s11-backlog C1)**

Use Agent tool с subagent_type="architecture-reviewer". Brief: verify DI graph correctness + no concurrency violations + Coordinator/Reconciler/RuntimeManager threading model preserved per ADR 0022.

- [ ] **Step 7: Commit (after reviewer approval)**

```bash
git add src/__main__.py tests/unit/test_main_run_wiring.py
git commit -m "feat(cli): T2 — _cmd_run DI wiring (closes S8a T20 STUB) (S11 P0)"
```

---

### Task 3: _cmd_reconcile_only DI wiring

**Files:**
- Modify: `src/__main__.py:46-56` (replace STUB)
- Create: `tests/unit/test_main_reconcile_only.py`

- [ ] **Step 1: Write failing tests (RED)**

Create `tests/unit/test_main_reconcile_only.py`:

```python
"""Tests для _cmd_reconcile_only DI wiring (Sprint 11 P0)."""
from __future__ import annotations

import argparse
from unittest.mock import MagicMock, patch


def test_cmd_reconcile_only_invokes_bootstrap_then_exits() -> None:
    """_cmd_reconcile_only wires Coordinator.bootstrap then exits cleanly без main loop."""
    from src import __main__ as cli

    args = argparse.Namespace(symbol="BTCUSDT", func=cli._cmd_reconcile_only)

    with patch("src.__main__.Coordinator") as mock_coord_class:
        mock_coord = MagicMock()
        mock_coord_class.return_value = mock_coord

        with patch("src.__main__.Settings") as mock_settings_class:
            mock_settings = MagicMock()
            mock_settings.bybit_api_key = "test_key_12345"
            mock_settings.bybit_api_secret = "test_secret_12345"
            mock_settings.testnet = True
            mock_settings.trading_symbol = "BTCUSDT"
            mock_settings.base_coin = "USDT"
            mock_settings_class.return_value = mock_settings

            with patch("src.__main__.init_db"), \
                 patch("src.__main__.connect"), \
                 patch("src.__main__.BybitRestAdapter"), \
                 patch("src.__main__.BybitMarketAdapter"), \
                 patch("src.__main__.Reconciler"), \
                 patch("src.__main__.ExecutionStateRepo"):

                exit_code = cli._cmd_reconcile_only(args)
                assert exit_code == 0
                mock_coord.bootstrap.assert_called_once()
```

- [ ] **Step 2: Verify RED**

```bash
pytest tests/unit/test_main_reconcile_only.py -v 2>&1 | tail -10
```

Expected: FAIL — `_cmd_reconcile_only` returns 1 as STUB.

- [ ] **Step 3: Implement wiring**

Edit `src/__main__.py:46-56` — replace `_cmd_reconcile_only`:

```python
def _cmd_reconcile_only(args: argparse.Namespace) -> int:
    """Run bootstrap + reconcile, no trading loop.

    Subset of _cmd_run DI graph — only Coordinator + Reconciler needed.
    Ships per ADR 0026 (S11 P0 closes S8a T20 STUB).
    """
    from pathlib import Path
    from sqlite3 import Connection

    settings = Settings()
    symbol = args.symbol or settings.trading_symbol

    mig_dir = Path(__file__).resolve().parent.parent / "migrations"
    init_db(settings.db_path, mig_dir)
    conn: Connection = connect(settings.db_path)

    rest = BybitRestAdapter(
        api_key=settings.bybit_api_key,
        api_secret=settings.bybit_api_secret,
        testnet=settings.testnet,
    )
    filters = BybitFilters(
        symbol=symbol,
        tick_size=Decimal("0.01"),
        qty_step=Decimal("0.000001"),
        min_qty=Decimal("0.00001"),
    )
    adapter = BybitMarketAdapter(rest=rest, filters=filters)
    repo = ExecutionStateRepo(conn)
    reconciler = Reconciler(query=adapter, base_coin=settings.base_coin, symbol=symbol)
    coordinator = Coordinator(
        adapter=adapter,
        repo=repo,
        reconciler=reconciler,
        symbol=symbol,
        base_coin=settings.base_coin,
    )

    try:
        coordinator.bootstrap()
        print(f"reconcile-only: bootstrap complete для {symbol}")
        return 0
    except Exception as e:  # noqa: BLE001
        import sys as _sys
        print(f"ERROR: reconcile-only bootstrap failed: {e}", file=_sys.stderr)
        return 1
```

- [ ] **Step 4: Verify GREEN + full suite**

```bash
pytest tests/unit/test_main_reconcile_only.py -v 2>&1 | tail -10
pytest tests/unit -x -q 2>&1 | tail -3
```

Expected: 1 passed + 660+ total.

- [ ] **Step 5: Commit**

```bash
git add src/__main__.py tests/unit/test_main_reconcile_only.py
git commit -m "feat(cli): T3 — _cmd_reconcile_only DI wiring (closes S8a T20 STUB) (S11 P0)"
```

---

### Task 4: WFA CLI subcommand

**Files:**
- Modify: `src/__main__.py` (add `_cmd_wfa` + parser entry)
- Create: `tests/unit/test_main_wfa_cli.py`

- [ ] **Step 1: Write failing tests (RED)**

Create `tests/unit/test_main_wfa_cli.py`:

```python
"""Tests для _cmd_wfa CLI subcommand (Sprint 11 P0)."""
from __future__ import annotations

import argparse
from unittest.mock import MagicMock, patch


def test_cmd_wfa_invokes_walk_forward_runner() -> None:
    """_cmd_wfa wires WindowSplitter + WalkForwardRunner + reporter."""
    from src import __main__ as cli

    args = argparse.Namespace(
        symbol="BTCUSDT", start="2024-01-01", end="2024-04-01", func=cli._cmd_wfa,
    )

    with patch("src.__main__.WalkForwardRunner") as mock_runner_class, \
         patch("src.__main__.WindowSplitter") as mock_splitter_class, \
         patch("src.__main__.format_wfa_report") as mock_reporter, \
         patch("src.__main__.evaluate_acceptance_gate") as mock_gate, \
         patch("src.__main__.run_replay"), \
         patch("src.__main__.sign_flip_p_value") as mock_mc, \
         patch("src.__main__._load_ohlcv") as mock_loader:

        mock_loader.return_value = MagicMock()
        mock_runner = MagicMock()
        mock_runner.run.return_value = {"folds": [], "aggregate": {"oos_trades_df": MagicMock(empty=True), "k_folds": 5, "fold_oos_sharpes": []}}
        mock_runner_class.return_value = mock_runner
        mock_mc.return_value = 0.03
        mock_gate.return_value = {"passed": True}
        mock_reporter.return_value = {"acceptance_gate": {"passed": True}}

        exit_code = cli._cmd_wfa(args)
        assert exit_code == 0
        mock_runner.run.assert_called_once()


def test_cmd_wfa_returns_nonzero_on_gate_failure() -> None:
    """Gate fail → nonzero exit (для CI integration)."""
    from src import __main__ as cli

    args = argparse.Namespace(
        symbol="BTCUSDT", start="2024-01-01", end="2024-04-01", func=cli._cmd_wfa,
    )

    with patch("src.__main__.WalkForwardRunner") as mock_runner_class, \
         patch("src.__main__.WindowSplitter"), \
         patch("src.__main__.format_wfa_report"), \
         patch("src.__main__.evaluate_acceptance_gate") as mock_gate, \
         patch("src.__main__.run_replay"), \
         patch("src.__main__.sign_flip_p_value", return_value=0.5), \
         patch("src.__main__._load_ohlcv") as mock_loader:

        mock_loader.return_value = MagicMock()
        mock_runner = MagicMock()
        mock_runner.run.return_value = {"folds": [], "aggregate": {"oos_trades_df": MagicMock(empty=True), "k_folds": 5, "fold_oos_sharpes": []}}
        mock_runner_class.return_value = mock_runner
        mock_gate.return_value = {"passed": False}

        exit_code = cli._cmd_wfa(args)
        assert exit_code == 2  # gate fail
```

- [ ] **Step 2: Verify RED**

```bash
pytest tests/unit/test_main_wfa_cli.py -v 2>&1 | tail -10
```

Expected: AttributeError на `_cmd_wfa`.

- [ ] **Step 3: Implement _cmd_wfa**

Edit `src/__main__.py` — add module-top imports:

```python
from src.analytics.dsr import compute_dsr
from src.backtest.mc_permutation import sign_flip_p_value
from src.backtest.replay_engine import run_replay
from src.backtest.walk_forward import (
    WalkForwardRunner,
    WindowSplitter,
    evaluate_acceptance_gate,
)
from src.backtest.wfa_reporter import format_wfa_report
```

Add helper after `_cmd_kill`:

```python
def _load_ohlcv(*, symbol: str, start: str, end: str) -> "pd.DataFrame":
    """Stub OHLCV loader. Production: read из Parquet OR REST kline.

    For S11 — placeholder. S12 F integrates real backfill data path.
    """
    import pandas as pd
    # Stub: empty DataFrame с required columns
    return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])


def _cmd_wfa(args: argparse.Namespace) -> int:
    """Run Walk-Forward Analysis + report.

    Subcommand: python -m src wfa --symbol BTCUSDT --start 2024-01-01 --end 2024-04-01
    Exit codes: 0 = gate passed, 2 = gate failed, 1 = error.
    """
    settings = Settings()
    symbol = args.symbol or settings.trading_symbol

    df = _load_ohlcv(symbol=symbol, start=args.start, end=args.end)
    if df.empty:
        print("WARNING: OHLCV loader returned empty (S12 will integrate real data)", flush=True)
        return 1

    splitter = WindowSplitter()  # ADR 0014 defaults
    runner = WalkForwardRunner(splitter=splitter, replay_fn=run_replay)
    config = {
        "trading": {
            "initial_balance": 10000.0,
            "commission_taker": 0.001,
            "slippage": 0.0005,
            "position_size_pct": 10.0,
            "max_drawdown_pct": 50.0,
            "long_only": True,
        },
        "strategy": {"indicators": {"atr": {"sl_atr_mult": 1.5, "tp_atr_mult": 3.0}}},
    }
    runner_result = runner.run(df=df, config=config)

    # MC sign-flip on aggregated OOS returns
    oos_trades = runner_result["aggregate"]["oos_trades_df"]
    if oos_trades.empty:
        mc_p = 1.0
    else:
        import numpy as np
        returns_arr = (oos_trades["net_pnl"].astype(float).to_numpy() / 10000.0)
        mc_p = sign_flip_p_value(returns_arr, n_iterations=2000, seed=42)

    fold_ratios = [f["oos_is_sharpe_ratio"] for f in runner_result["folds"]]
    gate = evaluate_acceptance_gate(
        fold_oos_is_sharpe_ratios=fold_ratios,
        mc_p_value=mc_p,
    )

    report = format_wfa_report(
        runner_result=runner_result,
        trades_for_dsr=[],  # Per-fold DataFrame→TradeRecord conversion deferred S12+
        mc_p_value=mc_p,
        gate_result=gate,
    )

    import json
    print(json.dumps({
        "symbol": symbol,
        "k_folds": report.get("k_folds", 0),
        "mc_p_value": report.get("mc_p_value"),
        "acceptance_gate": report.get("acceptance_gate"),
    }, default=str, indent=2))

    return 0 if gate.get("passed") else 2
```

Add parser entry in `_build_parser()` (after `p_rec`):

```python
    p_wfa = sub.add_parser("wfa", help="Run Walk-Forward Analysis + report.")
    p_wfa.add_argument("--symbol", default="BTCUSDT")
    p_wfa.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    p_wfa.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    p_wfa.set_defaults(func=_cmd_wfa)
```

- [ ] **Step 4: Verify GREEN**

```bash
pytest tests/unit/test_main_wfa_cli.py -v 2>&1 | tail -10
```

Expected: 2 passed.

- [ ] **Step 5: Verify full suite + mypy**

```bash
mypy src/__main__.py 2>&1 | tail -3
pytest tests/unit -x -q 2>&1 | tail -3
```

Expected: clean + 662+ passed.

- [ ] **Step 6: Commit**

```bash
git add src/__main__.py tests/unit/test_main_wfa_cli.py
git commit -m "feat(cli): T4 — _cmd_wfa subcommand (WFA orchestrator + MC + gate report) (S11 P0)"
```

---

## A scope — Operator infrastructure (4 tasks)

### Task 5: halt-recovery.md priority matrix extension (Q3 verdict)

**Files:**
- Modify: `wiki/project/runbooks/halt-recovery.md` (add Priority matrix section + escalation column)

- [ ] **Step 1: Read current Quick Reference Table**

```bash
grep -n "Quick Reference\|## Priority\|^| " /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot/llm-wiki/wiki/project/runbooks/halt-recovery.md | head -25
```

- [ ] **Step 2: Add Priority matrix section above Quick Reference Table**

Edit `halt-recovery.md` — insert новая section ПЕРЕД "Quick Reference Table":

```markdown
## Priority matrix (S11 operator readiness)

Per S11 PHASE 2 Q3 (trader REVISE): integrate priority + escalation INTO this runbook (single source of truth, не separate dashboard).

| Priority | Trigger characteristics | Operator action |
|----------|-------------------------|-----------------|
| **P0 — wake now** | CRITICAL severity (any halt where incorrect manual recovery can create OR conceal an open position) | Page on-call immediately. SQL + REST cross-check before resume. |
| **P1 — next morning** | RECOVERABLE severity (halt с automated diagnostic + clear recovery path) | Email/Slack notification. Resume during business hours. |
| **P2 — log only** | Operational halt с auto-resume mechanism (e.g. KILL_SWITCH_REQUESTED user-initiated) | Log to operator audit. No paging. |

### Escalation chain per code

```

Then extend Quick Reference Table — add new column "On-call escalation":

```markdown
| Halt code | Class group | Severity | On-call escalation |
|-----------|-------------|----------|--------------------|
| HALT_DRAWDOWN_L2 | Drawdown | CRITICAL | P0 |
| HALT_DRAWDOWN_L3 | Drawdown | CRITICAL | P0 |
| HALT_FLASH_CRASH | Drawdown | CRITICAL | P0 |
| HALT_RECONCILE_DIVERGENCE | Bootstrap-reconcile | CRITICAL | P0 |
| HALT_BOOTSTRAP_AMBIGUOUS | Bootstrap-reconcile | CRITICAL | P0 |
| HALT_EXIT_RECONCILE_DIVERGENCE | Bootstrap-reconcile | CRITICAL | P0 |
| HALT_BRACKET_INCOMPLETE | OCO-bracket | CRITICAL | P0 |
| HALT_PHANTOM_SL | OCO-bracket | CRITICAL | P0 |
| HALT_FLATTEN_FAILED | OCO-bracket | CRITICAL | P0 |
| HALT_RUNTIME_CRASH | Runtime | CRITICAL | P0 |
| HALT_OCO_ARM_TIMEOUT | OCO-bracket | RECOVERABLE | P1 |
| HALT_OCO_SIBLING_STUCK | OCO-bracket | RECOVERABLE | P1 |
| HALT_PARTIAL_FILL_BELOW_MIN | OCO-bracket | RECOVERABLE | P1 |
| HALT_DATA_QUALITY | Operational | RECOVERABLE | P1 |
| HALT_DATA_QUALITY_OUTLIER | Operational | RECOVERABLE | P1 |
| HALT_EXCHANGE_OUTAGE | Operational | RECOVERABLE | P1 |
| HALT_BAR_POLL_STALL | Operational | RECOVERABLE | P1 |
| KILL_SWITCH_REQUESTED | Operational | RECOVERABLE | P2 |
| EXIT_RECONCILE_DETECTED | Operational | RECOVERABLE | P2 |
```

(NOTE: Replace existing Quick Reference Table со this version. Verify all 19 codes present.)

- [ ] **Step 3: Verify halt-recovery.md still well-formed**

```bash
/usr/bin/wc -l /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot/llm-wiki/wiki/project/runbooks/halt-recovery.md
```

Expected: ~830 lines (~750 baseline + ~30 new lines).

- [ ] **Step 4: Commit**

```bash
git add llm-wiki/wiki/project/runbooks/halt-recovery.md
git commit -m "docs(runbook): T5 — halt-recovery.md priority matrix + escalation chain (S11 Q3)"
```

---

### Task 6: log-grep-templates.md NEW wiki page

**Files:**
- Create: `wiki/runbooks/log-grep-templates.md`

- [ ] **Step 1: Verify directory exists**

```bash
ls /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot/llm-wiki/wiki/runbooks/ 2>/dev/null
```

- [ ] **Step 2: Create page**

Create `llm-wiki/wiki/runbooks/log-grep-templates.md`:

```markdown
---
title: Log grep templates — operator log filtering recipes
type: runbook
tags: [operator, logging, structlog, grep, sprint-11]
created: 2026-04-25
updated: 2026-04-25
status: stable
sources:
  - src/platform/logging.py
  - migrations/0005_halt_persistence.sql
---

# Log grep templates

**TL;DR:** structlog JSON output filtering recipes для live operator monitoring. JSON keys + grep + jq patterns + halt_log SQL view.

Per S11 PHASE 2 Q3 (operator readiness deliverable 2 — log aggregation).

## structlog output format

All logs JSON-formatted via `structlog`. Each event has obligatory keys: `event`, `level`, `timestamp` + arbitrary structured key=value fields.

Example:
```
{"event": "data_quality.deviation_exceeds_threshold", "level": "warning", "timestamp": "2026-04-25T12:00:00Z", "prior_close": "100000", "current_close": "100600", "deviation_pct": "0.006000", "threshold_pct": "0.005"}
```

## Common operator queries (jq filters)

### Halt events (any class)

```bash
tail -f bot.log | jq 'select(.event | test("halt"))'
```

### Specific halt code (e.g. HALT_DATA_QUALITY)

```bash
tail -f bot.log | jq 'select(.event == "data_quality.deviation_exceeds_threshold")'
```

### All bar ticks (frequency check — should fire 1×/hour for 1H bars)

```bash
tail -f bot.log | jq 'select(.event == "runtime.bar_tick") | {ts: .timestamp, close: .bar_close_ts}'
```

### Reconcile divergence detection

```bash
grep -E "RECONCILE_(DIVERGENCE|HEAL|EXITED)" bot.log | jq .
```

### WS reconnect events

```bash
grep "ws_private" bot.log | jq 'select(.event | test("disconnect|reconnect"))'
```

### Order flow trace (entry through exit)

```bash
jq 'select(.event | test("coordinator|order_event|wallet_event"))' bot.log
```

### Strategy signal emissions

```bash
jq 'select(.event == "strategy.signal_emitted")' bot.log
```

### Risk rejections

```bash
jq 'select(.event == "runtime.signal_rejected")' bot.log
```

## halt_log SQL view (от SQLite)

Halt persistence per ADR 0021 sub-decision 4 — schema `halt_log` table appends каждый halt. Operator queries:

### Last 10 halts с reason

```sql
SELECT halt_ts, halt_reason, context
FROM halt_log
ORDER BY halt_ts DESC
LIMIT 10;
```

### Halt frequency per code (last 7 days)

```sql
SELECT halt_reason, COUNT(*) AS count
FROM halt_log
WHERE halt_ts >= datetime('now', '-7 days')
GROUP BY halt_reason
ORDER BY count DESC;
```

### CRITICAL halts only (per priority matrix)

```sql
SELECT halt_ts, halt_reason
FROM halt_log
WHERE halt_reason IN (
    'HALT_DRAWDOWN_L2', 'HALT_DRAWDOWN_L3', 'HALT_FLASH_CRASH',
    'HALT_RECONCILE_DIVERGENCE', 'HALT_BOOTSTRAP_AMBIGUOUS',
    'HALT_EXIT_RECONCILE_DIVERGENCE', 'HALT_BRACKET_INCOMPLETE',
    'HALT_PHANTOM_SL', 'HALT_FLATTEN_FAILED', 'HALT_RUNTIME_CRASH'
)
ORDER BY halt_ts DESC;
```

## execution_state SQL inspection

### Current state (single symbol)

```sql
SELECT symbol, state, halt_reason, last_event, updated_at
FROM execution_state
WHERE symbol = 'BTCUSDT';
```

### Active brackets

```sql
SELECT symbol, state, entry_order_id, tp_order_id, sl_order_id
FROM execution_state
WHERE state IN ('LONG_OPEN', 'OCO_ARMED', 'OCO_ARMING');
```

## trade_history SQL inspection

### Recent closed trades

```sql
SELECT trade_id, symbol, exit_ts, pnl_quote, pnl_pct, reason_code
FROM trade_history
ORDER BY exit_ts DESC
LIMIT 20;
```

### Win rate (last 30 days)

```sql
SELECT
    COUNT(*) AS total,
    SUM(CASE WHEN CAST(pnl_quote AS REAL) > 0 THEN 1 ELSE 0 END) AS wins,
    ROUND(100.0 * SUM(CASE WHEN CAST(pnl_quote AS REAL) > 0 THEN 1 ELSE 0 END) / COUNT(*), 2) AS win_rate_pct
FROM trade_history
WHERE exit_ts >= datetime('now', '-30 days');
```

## Live tail commands

### Bot stdout (assuming `python -m src run > bot.log 2>&1`)

```bash
tail -f bot.log | jq -r '"\(.timestamp) [\(.level | ascii_upcase)] \(.event) \(. | del(.timestamp, .level, .event))"'
```

### Halt-only tail

```bash
tail -f bot.log | jq 'select(.event | test("halt|HALT")) | {ts: .timestamp, event, halt_reason: .halt_reason}'
```

## Related

- [[halt-recovery]] — 19 halt codes + recovery procedures + priority matrix (S11)
- [[pre-flight]] — operator pre-flight checklist (S11)
- [[../project/components/storage]] — SQLite schema source of truth

## Sources

- `src/platform/logging.py` — structlog setup
- `migrations/0005_halt_persistence.sql` — halt_log table schema
- `migrations/002_risk.sql` — trade_history schema
- `migrations/0003_execution_state.sql` — execution_state schema
```

- [ ] **Step 3: Commit**

```bash
git add llm-wiki/wiki/runbooks/log-grep-templates.md
git commit -m "docs(runbook): T6 — log-grep-templates.md operator filtering recipes (S11 A scope)"
```

---

### Task 7: _cmd_monitor CLI subcommand (read-only per C2)

**Files:**
- Modify: `src/__main__.py` (add `_cmd_monitor` + parser entry)
- Create: `tests/unit/test_main_monitor.py`

**Cross-cutting concern C2: STRICTLY read-only. NO SQL writes (SQLite WAL contention с live bot).**

- [ ] **Step 1: Write failing tests (RED)**

Create `tests/unit/test_main_monitor.py`:

```python
"""Tests для _cmd_monitor CLI subcommand (Sprint 11 A scope, read-only per C2)."""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch


def test_cmd_monitor_outputs_state_snapshot(tmp_path: Path, capsys) -> None:
    """_cmd_monitor reads current state + recent trades, prints JSON snapshot."""
    from src import __main__ as cli

    # Synthetic DB с execution_state + trade_history rows
    db_path = tmp_path / "monitor.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        CREATE TABLE execution_state (
            symbol TEXT PRIMARY KEY,
            state TEXT NOT NULL,
            halt_reason TEXT,
            last_event TEXT,
            updated_at TEXT
        );
        INSERT INTO execution_state VALUES ('BTCUSDT', 'FLAT', NULL, 'BOOTSTRAP_OK', '2026-04-25T12:00:00+00:00');
        CREATE TABLE trade_history (
            trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT, entry_signal_id TEXT, entry_ts TEXT, exit_ts TEXT,
            qty TEXT, entry_price TEXT, exit_price TEXT, pnl_quote TEXT,
            pnl_pct TEXT, fees_paid TEXT, reason_code TEXT,
            kelly_phase INTEGER, recorded_at TEXT
        );
    """)
    conn.commit()

    args = argparse.Namespace(symbol="BTCUSDT", func=cli._cmd_monitor)

    with patch("src.__main__.Settings") as mock_settings_class:
        mock_settings = MagicMock()
        mock_settings.db_path = db_path
        mock_settings.trading_symbol = "BTCUSDT"
        mock_settings_class.return_value = mock_settings

        exit_code = cli._cmd_monitor(args)
        assert exit_code == 0

        captured = capsys.readouterr()
        assert "BTCUSDT" in captured.out
        assert "FLAT" in captured.out


def test_cmd_monitor_does_not_write_to_db(tmp_path: Path) -> None:
    """C2 invariant: _cmd_monitor MUST NOT write к DB (WAL contention)."""
    from src import __main__ as cli

    db_path = tmp_path / "readonly.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        CREATE TABLE execution_state (symbol TEXT PRIMARY KEY, state TEXT, halt_reason TEXT, last_event TEXT, updated_at TEXT);
        CREATE TABLE trade_history (trade_id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT, entry_signal_id TEXT, entry_ts TEXT, exit_ts TEXT, qty TEXT, entry_price TEXT, exit_price TEXT, pnl_quote TEXT, pnl_pct TEXT, fees_paid TEXT, reason_code TEXT, kelly_phase INTEGER, recorded_at TEXT);
        INSERT INTO execution_state VALUES ('BTCUSDT', 'FLAT', NULL, 'BOOTSTRAP', '2026-04-25T12:00:00+00:00');
    """)
    conn.commit()

    # Capture mtime before
    import os
    mtime_before = os.path.getmtime(db_path)

    args = argparse.Namespace(symbol="BTCUSDT", func=cli._cmd_monitor)

    with patch("src.__main__.Settings") as mock_settings_class:
        mock_settings = MagicMock()
        mock_settings.db_path = db_path
        mock_settings.trading_symbol = "BTCUSDT"
        mock_settings_class.return_value = mock_settings

        cli._cmd_monitor(args)

    mtime_after = os.path.getmtime(db_path)
    # mtime should be unchanged (no writes)
    assert mtime_before == mtime_after
```

- [ ] **Step 2: Verify RED**

```bash
pytest tests/unit/test_main_monitor.py -v 2>&1 | tail -10
```

Expected: AttributeError на `_cmd_monitor`.

- [ ] **Step 3: Implement _cmd_monitor**

Edit `src/__main__.py` — add after `_cmd_wfa`:

```python
def _cmd_monitor(args: argparse.Namespace) -> int:
    """Read-only state snapshot: FSM state + halt + recent trades.

    Per S11 cross-cutting concern C2: STRICTLY read-only (no SQL writes —
    SQLite WAL contention с live bot).

    Subcommand: python -m src monitor --symbol BTCUSDT
    """
    settings = Settings()
    symbol = args.symbol or settings.trading_symbol

    # Read-only sqlite connection (no writes possible at SQLite level)
    db_uri = f"file:{settings.db_path}?mode=ro"
    conn = sqlite3.connect(db_uri, uri=True)
    try:
        # Current state
        state_row = conn.execute(
            "SELECT symbol, state, halt_reason, last_event, updated_at "
            "FROM execution_state WHERE symbol = ?",
            (symbol,),
        ).fetchone()

        # Recent trades (last 10)
        trade_rows = conn.execute(
            "SELECT trade_id, exit_ts, pnl_pct, reason_code "
            "FROM trade_history WHERE symbol = ? ORDER BY exit_ts DESC LIMIT 10",
            (symbol,),
        ).fetchall()

        # Recent halts (last 5)
        halt_rows: list[tuple[Any, ...]] = []
        try:
            halt_rows = conn.execute(
                "SELECT halt_ts, halt_reason, context FROM halt_log "
                "ORDER BY halt_ts DESC LIMIT 5"
            ).fetchall()
        except sqlite3.OperationalError:
            # halt_log table may not exist в old DBs
            pass

        snapshot = {
            "symbol": symbol,
            "state": {
                "current_state": state_row[1] if state_row else "MISSING",
                "halt_reason": state_row[2] if state_row else None,
                "last_event": state_row[3] if state_row else None,
                "updated_at": state_row[4] if state_row else None,
            },
            "recent_trades": [
                {"trade_id": r[0], "exit_ts": r[1], "pnl_pct": r[2], "reason_code": r[3]}
                for r in trade_rows
            ],
            "recent_halts": [
                {"halt_ts": r[0], "halt_reason": r[1], "context": r[2]}
                for r in halt_rows
            ],
        }

        import json
        print(json.dumps(snapshot, default=str, indent=2))
        return 0
    finally:
        conn.close()
```

ALSO add к module-top imports:

```python
import sqlite3
```

Add parser entry в `_build_parser()`:

```python
    p_mon = sub.add_parser("monitor", help="Read-only state snapshot (FSM + trades + halts).")
    p_mon.add_argument("--symbol", default="BTCUSDT")
    p_mon.set_defaults(func=_cmd_monitor)
```

- [ ] **Step 4: Verify GREEN**

```bash
pytest tests/unit/test_main_monitor.py -v 2>&1 | tail -10
```

Expected: 2 passed.

- [ ] **Step 5: Verify mypy + full suite**

```bash
mypy src/__main__.py 2>&1 | tail -3
pytest tests/unit -x -q 2>&1 | tail -3
```

Expected: clean + 664+ passed.

- [ ] **Step 6: Commit**

```bash
git add src/__main__.py tests/unit/test_main_monitor.py
git commit -m "feat(cli): T7 — _cmd_monitor read-only state snapshot CLI (S11 A scope, C2 invariant)"
```

---

### Task 8: pre-flight.md operator checklist

**Files:**
- Create: `wiki/runbooks/pre-flight.md`

- [ ] **Step 1: Create page**

Create `llm-wiki/wiki/runbooks/pre-flight.md`:

```markdown
---
title: Pre-flight checklist — operator gate before live start
type: runbook
tags: [operator, pre-flight, checklist, sprint-11]
created: 2026-04-25
updated: 2026-04-25
status: stable
sources:
  - src/platform/config.py
  - src/__main__.py
---

# Pre-flight checklist — operator gate

**TL;DR:** Mandatory operator checklist before `python -m src run` on Mainnet (или Bybit demo trading). Verifies config + connectivity + state coherence.

Per S11 PHASE 2 Q3 (operator readiness deliverable 4).

## Critical gates (BLOCK if fail)

### Gate 1: Config validation

```bash
source .venv/bin/activate
python -c "from src.platform.config import Settings; s = Settings(); print(f'testnet={s.testnet}, trading_enabled={s.trading_enabled}, live_trading={s.live_trading}, symbol={s.trading_symbol}')"
```

**Expected output (testnet/demo):**
```
testnet=True, trading_enabled=False, live_trading=False, symbol=BTCUSDT
```

**Expected output (Mainnet/live):**
```
testnet=False, trading_enabled=True, live_trading=True, symbol=BTCUSDT
```

**FAIL if:** `live_trading=True` AND (`testnet=True` OR `trading_enabled=False`) — `_live_trading_guards` validator должен raise ValueError. Bot не start.

### Gate 2: Database migration check

```bash
python -c "from pathlib import Path; from src.platform.db import init_db; from src.platform.config import Settings; s = Settings(); init_db(s.db_path, Path('migrations')); print('OK')"
```

**Expected:** `OK`. All migrations apply cleanly.

### Gate 3: Reconcile-only smoke test

```bash
python -m src reconcile-only --symbol BTCUSDT
```

**Expected:** `reconcile-only: bootstrap complete для BTCUSDT` + exit 0.

**FAIL if:** REST connectivity error, API key invalid, или reconcile divergence at boot.

### Gate 4: Override gate validation

```bash
python -c "from src.platform.config import Settings; s = Settings(); from src.risk.override import OverrideStore; OverrideStore(s.risk_override_path, hmac_key=s.risk_override_hmac_key); print('OK')"
```

**Expected:** `OK`. HMAC key length ≥ 32 chars, override file path writable.

### Gate 5: WFA baseline (optional но recommended)

```bash
python -m src wfa --symbol BTCUSDT --start 2024-01-01 --end 2024-04-01
```

**Expected:** JSON output с `acceptance_gate.passed`. If `passed: false`, strategy не fit для current data window — investigate before live.

## Recommended (warn if skipped)

### Recommendation 1: Balance check

Verify wallet balance before live (Bybit V5 testnet balance reset weekly):

```bash
python -c "from src.marketdata.bybit.rest import BybitRestAdapter; from src.platform.config import Settings; s = Settings(); rest = BybitRestAdapter(api_key=s.bybit_api_key, api_secret=s.bybit_api_secret, testnet=s.testnet); print('REST OK')"
```

### Recommendation 2: Disk space check

```bash
df -h "$(dirname "$(python -c "from src.platform.config import Settings; print(Settings().db_path)")")"
```

**Expected:** ≥ 1 GB free для SQLite WAL + Parquet snapshots.

### Recommendation 3: Kill-switch sentinel cleanup

```bash
ls -la "$(python -c "from src.platform.config import Settings; print(Settings().runtime_kill_switch_path)")" 2>/dev/null
```

**If exists** — remove перед start (otherwise `_maybe_kill_switch` immediately halts):

```bash
rm "$(python -c "from src.platform.config import Settings; print(Settings().runtime_kill_switch_path)")"
```

### Recommendation 4: Log rotation setup

If running long sessions (24h+), set up logrotate OR redirect к dated log:

```bash
python -m src run --symbol BTCUSDT > "bot_$(date +%Y%m%d_%H%M%S).log" 2>&1 &
```

## Post-start monitoring

Once `python -m src run` is running:

```bash
# Tail logs (separate terminal)
tail -f bot.log | jq 'select(.level == "warning" or .level == "error")'

# Periodic state snapshot (separate terminal, run каждый 5 min)
watch -n 300 'python -m src monitor --symbol BTCUSDT'
```

См. [[log-grep-templates]] для дополнительных filtering recipes.

## Halt response

Если halt fires — см. [[halt-recovery]] priority matrix:
- **P0 (CRITICAL):** wake on-call now, SQL + REST cross-check, manual recovery per runbook
- **P1 (RECOVERABLE):** notification only, resume during business hours
- **P2 (log only):** audit trail, no action

## Related

- [[halt-recovery]] — 19 halt codes + priority matrix + recovery procedures
- [[log-grep-templates]] — operator log filtering recipes
- [[../project/components/kill-switch-cli]] — operator-initiated halt mechanism
- [[../project/components/coordinator]] — `request_halt` API consumer

## Sources

- `src/platform/config.py::Settings` — config + `_live_trading_guards` validator
- `src/__main__.py` — CLI subcommands (`run`, `reconcile-only`, `wfa`, `monitor`, `kill`, `backfill`)
- `migrations/` — schema versions
```

- [ ] **Step 2: Commit**

```bash
git add llm-wiki/wiki/runbooks/pre-flight.md
git commit -m "docs(runbook): T8 — pre-flight.md operator checklist (5 gates + 4 recommendations) (S11 A scope)"
```

---

## ADR + wiki sync (2 tasks)

### Task 9: ADR 0026 — S11 aggregate decisions

**Files:**
- Create: `llm-wiki/wiki/project/decisions/0026-sprint-11-operator-readiness.md`
- Modify: `llm-wiki/wiki/index.md` (add ADR 0026 entry)

- [ ] **Step 1: Write ADR**

Create `llm-wiki/wiki/project/decisions/0026-sprint-11-operator-readiness.md`:

```markdown
---
title: 0026. Sprint 11 — Operator-readiness + pre-flight gap closure
type: decision
date: 2026-04-25
sprint: 11
tags: [adr, sprint-11, operator-readiness, cli, monitoring, di-wiring, halt-priority]
sources:
  - project/pre-s11-backlog.md
  - project/decisions/0016-binance-spot-testnet-mvp.md
  - project/decisions/0022-sprint-8a-live-runtime.md
  - project/decisions/0025-sprint-10-wfa-dsr-mc.md
status: accepted
---

# 0026. Sprint 11 — Operator-readiness + pre-flight gap closure

**Status:** accepted
**Date:** 2026-04-25

## Context

Sprint 11 closes pre-flight gaps blocking live execution + ships operator infrastructure:
- `_cmd_run` STUB since S8a T20 deferral — bot не runnable end-to-end через `python -m src run`
- `_cmd_reconcile_only` STUB since same source
- WFA shipped S10 но не exposed как CLI subcommand
- test_risk_flow.py failing с OverrideStore signature drift since S4 era
- halt-recovery.md (S8c PR-γ) covers 19 codes но без priority/escalation index
- No operator-friendly state snapshot tool

PHASE 2 brainstorming verdicts (`pre-s11-backlog.md`):
- Q1 CONFIRM: A-first (operator-readiness), F (Live demo Mainnet) deferred к S12
- Q2 CONFIRM: bundle pre-flight gaps в S11 P0
- Q3 REVISE: integrate halt priority matrix INTO halt-recovery.md (NOT separate dashboard)
- Q4 CONFIRM: F params validated for S12 (Bybit demo + 48h + $1000 virtual)
- Q5 CONFIRM: defer DSR threshold calibration к S15+ (need 30+ trades)
- Q6 CONFIRM: 1-test fix + audit для other S4-era drift
- Q7 CONFIRM + addition: architecture-reviewer MANDATORY для _cmd_run

## Decision

### P0 pre-flight (Q2)

Bundle 3 tasks BEFORE A scope deliverables:
- T1: test_risk_flow.py — restore `OverrideStore(path, hmac_key=settings.risk_override_hmac_key)` signature
- T2: `_cmd_run` DI wiring — Settings → REST adapter → market adapter → state repo → reconciler → coordinator → bar source → strategy → risk manager → WS consumer → RuntimeManager.run(). FillRecorder = MagicMock-equivalent stub (production wiring deferred S12+).
- T3: `_cmd_reconcile_only` wiring — subset of T2 DI graph (Coordinator + Reconciler only).
- T4: `_cmd_wfa` subcommand — wires WindowSplitter + WalkForwardRunner + sign_flip_p_value + evaluate_acceptance_gate + format_wfa_report. Exit code 0 = gate passed, 2 = gate failed, 1 = error.

architecture-reviewer MANDATORY на T2 per cross-cutting concern C1.

### A scope — Operator-readiness (Q3 REVISE)

Per Q3 trader REVISE accepted: integrate priority matrix INTO `halt-recovery.md` (NOT separate file — single source of truth).

- T5: Extend `halt-recovery.md`:
  - NEW "Priority matrix" section (P0/P1/P2 tiers с operator action descriptions)
  - Extend Quick Reference Table с "On-call escalation" column (19 codes mapped к P0/P1/P2)
- T6: NEW `wiki/runbooks/log-grep-templates.md` — structlog jq filters + halt_log SQL queries + execution_state SQL inspection
- T7: `_cmd_monitor` CLI subcommand — read-only state snapshot. STRICTLY read-only per cross-cutting concern C2 (SQLite WAL contention с live bot). Uses `sqlite3.connect(f"file:{path}?mode=ro", uri=True)`.
- T8: NEW `wiki/runbooks/pre-flight.md` — operator checklist (5 critical gates + 4 recommendations + post-start monitoring + halt response).

### Cross-cutting concerns (binding)

- **C1:** `_cmd_run` DI wiring real risk. architecture-reviewer mandatory. Pre-plan DI feasibility read-pass verified constructors aligned (no mini-ADR needed).
- **C2:** `_cmd_monitor` strictly read-only. Implementation MUST use SQLite read-only mode URI. Test enforces no DB mtime change.
- **C3:** WFA CLI bundled с P0 но не blocks A scope parallel.

## Consequences

**Plus:**
- Bot runnable end-to-end через `python -m src run` (closes 8-month-old S8a T20 STUB)
- Operator infrastructure ready для S12 F live demo Mainnet validation
- Single source of truth для halt priority (no dashboard drift)
- Pre-flight checklist enforces config gate validation before live start
- WFA accessible как CLI subcommand для on-demand baseline

**Minus:**
- FillRecorder stub в `_cmd_run` (production wiring deferred S12+) — fills logged but не persisted
- `_load_ohlcv` stub в `_cmd_wfa` (S12 F integrates real data path)
- Per-fold DSR в reporter still NaN (DataFrame→TradeRecord conversion deferred)
- DSR threshold gate calibration deferred к S15+ (need empirical data)

## Related

- [[../pre-s11-backlog]] — PHASE 2 verdicts trail
- [[0016-binance-spot-testnet-mvp]] — testnet MVP gating + Phase G mention
- [[0022-sprint-8a-live-runtime]] — RuntimeManager origin + T20 STUB deferral closed by T2
- [[0025-sprint-10-wfa-dsr-mc]] — WFA components consumed by T4 _cmd_wfa
- [[../runbooks/halt-recovery]] — extended с priority matrix (T5)
- [[../runbooks/log-grep-templates]] — NEW (T6)
- [[../runbooks/pre-flight]] — NEW (T8)
- [[../plans/2026-04-25-sprint-11-operator-readiness]] — implementation plan + trace map

## Amendments

- (none yet)
```

- [ ] **Step 2: Add ADR 0026 к index.md**

Edit `llm-wiki/wiki/index.md` "## Project — Decisions" — add:

```markdown
- [[project/decisions/0026-sprint-11-operator-readiness]] — Sprint 11 aggregate ADR: Pre-flight gap closure (test_risk_flow.py + _cmd_run + _cmd_reconcile_only + _cmd_wfa CLI) + operator-readiness (halt priority matrix integration + log-grep-templates + _cmd_monitor read-only + pre-flight checklist).
```

- [ ] **Step 3: Touch agent prompt (adr-agent-sync hook satisfaction)**

```bash
touch ~/.claude/agents/architecture-reviewer.md
```

(Reviewer used для T2 DI wiring.)

- [ ] **Step 4: Commit**

```bash
git add llm-wiki/wiki/project/decisions/0026-sprint-11-operator-readiness.md llm-wiki/wiki/index.md
git commit -m "docs(adr): T9 — ADR 0026 S11 aggregate decisions (S11)"
```

---

### Task 10: Wiki sync — sprint-11 page + counts + index

**Files:**
- Create: `llm-wiki/wiki/project/sprints/sprint-11-operator-readiness.md`
- Modify: `llm-wiki/wiki/project/architecture/current-state.md` (counts + sprint history)
- Modify: `llm-wiki/wiki/index.md` (add 2 runbooks + sprint-11)
- Modify: `llm-wiki/wiki/project/components/README.md` (если new components — но S11 не creates new, just extends halt-recovery)
- Modify: `llm-wiki/wiki/project/mental-map.md` (add 2 query rows для new runbooks)

- [ ] **Step 1: Create sprint-11 page**

Create `llm-wiki/wiki/project/sprints/sprint-11-operator-readiness.md`:

```markdown
---
title: Sprint 11 — Operator-readiness + pre-flight gap closure
type: sprint
tags: [sprint-11, operator-readiness, cli, monitoring, di-wiring, pre-flight]
created: 2026-04-25
updated: 2026-04-25
status: completed
sources:
  - project/plans/2026-04-25-sprint-11-operator-readiness
  - project/decisions/0026-sprint-11-operator-readiness
  - project/pre-s11-backlog
---

# Sprint 11 — Operator-readiness + pre-flight

## Overview

S11 ships pre-flight gap closure (P0) + operator infrastructure (A scope) per pre-s11-backlog.md verdicts. 10 TDD tasks, ~12-15 commits squash-merged. Tag `v0.1.0-alpha.11`.

**Closes:**
- 8-month-old S8a T20 STUB (`_cmd_run` + `_cmd_reconcile_only` DI wiring)
- S4-era test drift (test_risk_flow.py OverrideStore signature)
- Halt priority indexing gap (operator wouldn't know which halts wake them at 3 AM)
- WFA CLI exposure для on-demand baseline

## Plan / ADR links

- Plan: [[../plans/2026-04-25-sprint-11-operator-readiness]]
- ADR (NEW): [[../decisions/0026-sprint-11-operator-readiness]]
- Brainstorm trail: [[../pre-s11-backlog]]

## Deliverables

10 tasks squash-merged.

### P0 pre-flight (4 tasks)

- T1: test_risk_flow.py OverrideStore hmac_key signature restored
- T2: `_cmd_run` DI wiring (architecture-reviewer APPROVED)
- T3: `_cmd_reconcile_only` DI wiring
- T4: `_cmd_wfa` CLI subcommand (Sharpe + MC gate)

### A scope (4 tasks)

- T5: halt-recovery.md priority matrix + escalation column (Q3 REVISE)
- T6: NEW log-grep-templates.md (structlog jq filters + halt_log SQL)
- T7: `_cmd_monitor` CLI (read-only per C2)
- T8: NEW pre-flight.md operator checklist (5 gates + 4 recommendations)

### Wiki + ADR (2 tasks)

- T9: ADR 0026 + index.md entry
- T10: Sprint page + counts updates + mental-map

## FSM growth

NONE. CLI = orchestration layer. Counts unchanged: 16/30/74/45.

## Reason codes growth

NONE.

## Tests

- pytest unit: ~664 passed (baseline 656 + ~8 new tests for CLI subcommands)
- pytest integration: test_risk_flow.py ✅ (was failing pre-S11)
- mypy --strict src/: clean

## Wiki updates

- 2 NEW runbook pages (log-grep-templates, pre-flight)
- 1 NEW ADR (0026)
- 1 NEW sprint page (this)
- Modified: halt-recovery.md (priority matrix + escalation column)
- current-state.md (counts 35→35 — no new components, ADR 25→26, sprint pages 12→13)
- mental-map.md (2 new query rows для new runbooks)

## Open issues для S12+

- F (Live demo Mainnet 24-72h validation) — main S12 scope
- FillRecorder production wiring (currently MagicMock stub в _cmd_run)
- _load_ohlcv production data integration в _cmd_wfa (currently empty DataFrame stub)
- Per-fold DSR DataFrame→TradeRecord conversion (informational, deferred)
- DSR threshold calibration (S15+ per Q5 verdict)

## Key decisions

- **A-first vs F-first** (Q1) — A wins per architecturally correct sequencing (live Mainnet требует runnable bot, blocked by _cmd_run STUB)
- **halt priority matrix INTO halt-recovery.md** (Q3 REVISE) — single source of truth, prevents drift vs separate dashboard
- **_cmd_monitor strictly read-only** (C2) — SQLite WAL contention prevention via `?mode=ro` URI
- **architecture-reviewer mandatory _cmd_run** (Q7) — DI graph + concurrency implications per ADR 0017 trigger cascade
- **DI feasibility read-pass** (C1) — pre-plan verification confirmed constructors aligned, no mini-ADR needed

## Related

- [[../plans/2026-04-25-sprint-11-operator-readiness]] — full plan + trace map
- [[../decisions/0026-sprint-11-operator-readiness]] — aggregate ADR
- [[../pre-s11-backlog]] — PHASE 2 verdicts trail
- [[sprint-10-wfa-dsr-mc]] — predecessor sprint (WFA components consumed by T4)
- [[../runbooks/halt-recovery]] + [[../runbooks/log-grep-templates]] + [[../runbooks/pre-flight]] — operator runbooks
```

- [ ] **Step 2: Update current-state.md counts**

Edit `llm-wiki/wiki/project/architecture/current-state.md`:

Replace TL;DR line:
```markdown
# Current State (post-S11, 2026-04-25)

**TL;DR:** Live state v0.1 on tag `v0.1.0-alpha.11`. 13 sprints completed (S1-S7 + S8a + S8b + S8c + S9 + S10 + S11). S11 added: pre-flight gap closure (_cmd_run + _cmd_reconcile_only DI wiring closes S8a T20 STUB + _cmd_wfa CLI + test_risk_flow.py fix) + operator-readiness (halt priority matrix + log-grep-templates + _cmd_monitor read-only + pre-flight.md checklist).
```

Update counts table:
```markdown
| ADRs | **26** | `wiki/project/decisions/*.md` (0001-0026) | S11 (ADR 0026 — operator-readiness + pre-flight) |
| Sprint pages | **13** | `wiki/project/sprints/sprint-*.md` (sprint-01..sprint-11 + sprint-08a + sprint-08b + sprint-08c) | S11 (sprint-11-operator-readiness) |
```

(Component pages count unchanged at 35 — S11 не adds new components, just 2 runbook pages в `wiki/runbooks/`.)

- [ ] **Step 3: Add 2 runbooks к index.md**

Edit `llm-wiki/wiki/index.md` "## Project — Runbooks" section (or create if missing):

```markdown
- [[project/runbooks/log-grep-templates]] — structlog jq filters + halt_log/execution_state/trade_history SQL queries для operator monitoring (S11).
- [[project/runbooks/pre-flight]] — Operator pre-flight checklist (5 critical gates + 4 recommendations + post-start monitoring) (S11).
```

Add к sprints section:
```markdown
- [[project/sprints/sprint-11-operator-readiness]] — S11 (2026-04-25): pre-flight gap closure (test_risk_flow + _cmd_run + _cmd_reconcile_only + _cmd_wfa) + operator-readiness (halt priority matrix + log-grep-templates + _cmd_monitor + pre-flight.md). 10 TDD tasks. Tag v0.1.0-alpha.11.
```

- [ ] **Step 4: Update mental-map.md**

Edit `llm-wiki/wiki/project/mental-map.md` "Operator procedures" section — add:

```markdown
| Log filtering / SQL inspection (live monitoring) | `runbooks/log-grep-templates.md` (S11 A scope) |
| Pre-flight checklist (operator gate before live start) | `runbooks/pre-flight.md` (S11 A scope) |
| Halt priority + escalation chain | `runbooks/halt-recovery.md` "Priority matrix" section (S11 Q3) |
| State snapshot CLI (`python -m src monitor`) | `src/__main__.py::_cmd_monitor` (S11, read-only per C2) |
```

- [ ] **Step 5: Verify counts live**

```bash
source /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot/.venv/bin/activate
python -c "from src.execution.state_machine import TRANSITIONS, ExecutionState, ExecutionEvent; from src.risk.reason_codes import ReasonCode; print(f'states={len(list(ExecutionState))}, events={len(list(ExecutionEvent))}, transitions={len(TRANSITIONS)}, reason_codes={len(list(ReasonCode))}')"
ls llm-wiki/wiki/project/decisions/*.md | /usr/bin/wc -l   # expect 26
ls llm-wiki/wiki/project/sprints/sprint-*.md | /usr/bin/wc -l  # expect 13
ls llm-wiki/wiki/runbooks/*.md | /usr/bin/wc -l  # expect 3+ (was 1, +2 new)
```

Expected: counts unchanged 16/30/74/45 + ADRs 26 + sprint pages 13 + runbooks 3+.

- [ ] **Step 6: Commit**

```bash
git add llm-wiki/wiki/project/sprints/sprint-11-operator-readiness.md llm-wiki/wiki/project/architecture/current-state.md llm-wiki/wiki/index.md llm-wiki/wiki/project/mental-map.md
git commit -m "docs(wiki): T10 — S11 wiki sync (sprint page + counts + 2 runbooks к index + mental-map) (S11)"
```

---

## PHASE 8 finishing (after T1-T10 complete)

- [ ] **Step 1: Run pre-validation**

```bash
source /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot/.venv/bin/activate
pytest tests/unit tests/property -x -q 2>&1 | tail -3
pytest tests/integration/test_risk_flow.py tests/integration/test_wfa_pipeline.py -x -q 2>&1 | tail -3
mypy src/ 2>&1 | tail -2
python -c "from src.execution.state_machine import TRANSITIONS, ExecutionState, ExecutionEvent; from src.risk.reason_codes import ReasonCode; print(f'states={len(list(ExecutionState))}, events={len(list(ExecutionEvent))}, transitions={len(TRANSITIONS)}, reason_codes={len(list(ReasonCode))}')"
```

Expected: 664+ unit, 2+ integration (test_risk_flow now ✅), mypy clean, counts 16/30/74/45.

- [ ] **Step 2: Invoke `sprint-finish` skill**

Skill enforces all HARD-GATEs (sprint-NN.md ✓ T10, canonical counts sync ✓ T10, orphan-audit grep includes tests/, Block 1↔Block 2 sync ✓ all NEW pages, index.md ADR sync ✓ T9) → `superpowers:finishing-a-development-branch`.

- [ ] **Step 3: Push + PR + squash-merge + tag v0.1.0-alpha.11**

Per `superpowers:finishing-a-development-branch` skill protocol.

- [ ] **Step 4: SPRINT_STATE update → between-sprints / ready-for-s12**

---

## Self-review checklist

**Spec coverage (per pre-s11-backlog.md verdicts):**
- ✅ Q1 A-first → all S11 tasks A scope (no F)
- ✅ Q2 bundle pre-flight → T1+T2+T3+T4 P0 tasks
- ✅ Q3 priority matrix INTO halt-recovery.md → T5
- ✅ Q4 F params validated for S12 → ADR 0026 references
- ✅ Q5 DSR calibration deferred → noted в open issues
- ✅ Q6 test_risk_flow.py fix → T1
- ✅ Q7 architecture-reviewer mandatory _cmd_run → T2 step 6

**Cross-cutting concerns covered:**
- ✅ C1 (_cmd_run DI risk) — pre-plan read-pass done + architecture-reviewer mandatory T2
- ✅ C2 (_cmd_monitor read-only) — T7 enforces via `?mode=ro` URI + test asserts no DB mtime change
- ✅ C3 (WFA CLI bundle с P0) — T4 in P0 group, NOT blocking A scope parallel

**Placeholder scan:** No TBD / TODO / "implement later". Every code block complete.

**Type consistency:**
- All CLI subcommands signature: `(args: argparse.Namespace) -> int`
- DI imports module-top in `__main__.py` for testability (mock patches use `src.__main__.X`)

---

## Total: 10 tasks, TDD throughout, ~12-15 commits estimated, ~6-8 hours work

Estimated test count delta: +8 tests (3 _cmd_run + 1 _cmd_reconcile_only + 2 _cmd_wfa + 2 _cmd_monitor). Baseline 656 → ~664 passed. test_risk_flow.py integration test fixed.
