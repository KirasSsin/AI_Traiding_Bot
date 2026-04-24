"""Sprint 8a — full bring-up smoke on Bybit Demo Mainnet (SCAFFOLD).

ADR 0022 sub-decisions 8 + 14.

**Status:** SCAFFOLD — full wiring deferred to manual operator run (T20 followup).

The plan's wiring uses several stale API signatures (see TODO list inside the
test body). Default behavior is SKIP via the `RUN_DEMO=1` opt-in marker, so
this file does not affect the regular suite. When the operator runs
`RUN_DEMO=1 pytest tests/integration/test_runtime_demo_smoke.py -v -m integration`
against real Demo Mainnet keys, they should:

  1. Replace the in-body `pytest.skip(...)` with the actual wiring.
  2. Use real ctor signatures (see TODO list below for current API).
  3. Document the run outcome in `wiki/log.md`.
  4. Address any newly-discovered Coordinator/RuntimeManager/adapter wiring drift.

Acceptance per plan: bootstrap → 1 bar tick → kill switch → graceful shutdown
with `halt_reason == "KILL_SWITCH_REQUESTED"` within 60s.
"""
from __future__ import annotations

import os

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_DEMO") != "1",
        reason="Demo integration test opt-in via RUN_DEMO=1",
    ),
    pytest.mark.skipif(
        not os.getenv("BYBIT_DEMO_API_KEY") or not os.getenv("BYBIT_DEMO_API_SECRET"),
        reason="BYBIT_DEMO_API_KEY / BYBIT_DEMO_API_SECRET required",
    ),
]


def test_runtime_demo_smoke_kill_switch_graceful_shutdown(tmp_path, monkeypatch):
    """Smoke: bootstrap + bar tick + kill switch + graceful shutdown on Bybit Demo.

    TODO (T20 manual followup): Replace this skip + TODO list below with full
    wiring. Plan-author signatures have drifted from current API:

    - `BybitMarketAdapter(*, rest, filters: BybitFilters)` — not `BybitAdapter(rest, settings)`
    - `BybitPrivateWSConsumer(*, api_key, api_secret, endpoint, coordinator, reconciler)` — takes
      endpoint URL + full objects, NOT testnet bool + per-callback args
    - `Reconciler(*, query=adapter, base_coin="BTC", symbol="BTCUSDT", ...)` — no `settings` kwarg
    - `ExecutionStateRepo(conn: sqlite3.Connection)` — pass Connection, not path string;
      use `init_db(db_path, MIG_DIR)` + `sqlite3.connect(...)` + WAL pragma
    - `repo.upsert_initial(symbol=...)` — DOES NOT EXIST; seed with `repo.upsert(ExecutionStateRow(...FLAT...))`
    - `Coordinator(adapter, repo, reconciler, symbol, base_coin)` — no `settings` param
    - `Strategy()` → use `EmaCrossoverAdxRsiStrategy(...)` with 9 settings-driven params,
      e.g. construct via `EmaCrossoverAdxRsiStrategy(ema_fast=settings.ema_fast, ...)`
    - `RuntimeManager(coordinator, reconciler, ws_consumer, bar_source, strategy, settings, risk_manager)` —
      7 deps after T15 fix; plan omits `risk_manager`
    - Verify final `row.halt_reason == "KILL_SWITCH_REQUESTED"` (StrEnum value)

    Reference: see `tests/unit/test_runtime_manager.py` for in-process test pattern.
    """
    pytest.skip(
        "T20 scaffold — manual wiring needed for Demo run; "
        "see docstring TODO list. Run before T30 tag."
    )
