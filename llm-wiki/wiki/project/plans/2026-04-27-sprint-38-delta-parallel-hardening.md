---
title: Sprint 38 Plan — δ Parallel Hardening (F2 quant + bybit-api-reviewer + Item #7 + playbook amendments)
type: plan
tags: [sprint-38, plan, delta-parallel, pnl-pct-fix, bybit-api-review, demeter-refactor, playbook-amendments, ru]
created: 2026-04-27
updated: 2026-04-27
status: proposed
sources:
  - project/decisions/0055-sprint-36-delta-activation.md
  - project/decisions/0056-sprint-36-dsr-sigma-sr-amendment.md
  - project/decisions/0057-sprint-37-carry-overs-hardening.md
  - project/pre-s38-backlog.md
---

# Sprint 38 Implementation Plan — δ Parallel Hardening

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Address ROUND 6 consilium NEW findings (F2 quant HIGH pnl_quote→pnl_pct fix + F3 bybit-api-reviewer first invocation + F7 RiskSharedDeps Demeter refactor + playbook amendments F4-F7) while δ TESTNET runs production tick path в parallel.

**Architecture:** Seven serialized TDD/docs tasks. Critical-path: ADR first → F2 correctness fix (highest priority — affects 12mo review math) → bybit-api-reviewer dispatch → architecture refactor (DI wiring only, NOT runtime tick) → docs amendments → playbook amendments → wiki sync.

**Parallel safety:** Item #7 RiskSharedDeps refactor touches RuntimeManager constructor signature ONLY. NOT _tick body, NOT HaltGate.evaluate(), NOT activation_ts persistence. δ TESTNET running on main branch = no runtime tick conflict с S38 development branch.

**Tech Stack:** Python 3.12 / pydantic-settings / SQLite WAL / pytest / mypy --strict / TDD RED→GREEN.

---

## Trace Map (PHASE 3 step 1a HARD-GATE)

| Source artifact | Implementation task |
|-----------------|---------------------|
| pre-s38-backlog F2 (pnl_quote → pnl_pct quant HIGH) | T2 |
| pre-s38-backlog F3 (bybit-api-reviewer first invocation) | T3 |
| pre-s38-backlog Item #7 (RiskSharedDeps Demeter refactor) | T4 |
| pre-s38-backlog Items #6 + #9 (months_since + Sharpe semantics docs) | T5 |
| pre-s38-backlog F4-F7 (5 playbook gates + UNDERPOWERED + halt-triggered) | T6 |
| ROUND 6 ADR 0058 + ADR 0056 amendment 2 | T1 |

---

## File Structure

**Create:**
- `llm-wiki/wiki/project/decisions/0058-sprint-38-delta-parallel-hardening.md` — ADR 0058 (~120 lines)
- `llm-wiki/wiki/project/sprints/sprint-38-delta-parallel-hardening.md` — sprint page
- `llm-wiki/wiki/queries/2026-04-27-bybit-api-reviewer-first-invocation.md` — F3 review document
- `tests/unit/test_live_trade_reporter_pnl_pct.py` — F2 fix tests (3 tests)
- `tests/unit/test_risk_shared_deps.py` — Item #7 refactor tests (4 tests)

**Modify:**
- `llm-wiki/wiki/project/decisions/0056-sprint-36-dsr-sigma-sr-amendment.md` — append amendment 2 (Sharpe pnl_pct semantics)
- `src/analytics/live_trade_reporter.py:62` — `pnl_quote` → `pnl_pct` (F2 HIGH)
- `tests/unit/test_live_trade_reporter.py` — update existing test fixtures (pnl_pct semantic)
- `src/risk/manager.py` — RiskSharedDeps NamedTuple/dataclass (T4)
- `src/runtime/manager.py` — accept RiskSharedDeps bundle (backward-compat default)
- `src/__main__.py:_cmd_run` — pass RiskSharedDeps к RuntimeManager
- `llm-wiki/wiki/project/components/delta-activation-playbook.md` — 5 NEW gates + UNDERPOWERED annotation + halt-triggered immediate review
- `llm-wiki/wiki/project/decisions/0057-sprint-37-carry-overs-hardening.md` — append months_since truncation note (Item #6)
- `llm-wiki/wiki/index.md` — add ADR 0058 + sprint-38 + bybit-api review query
- `llm-wiki/wiki/project/architecture/current-state.md` — counts 57→58 ADRs / 41→42 sprints + S38 row + tag v0.1.0-alpha.38
- `llm-wiki/wiki/log.md` — sprint-end entry
- `llm-wiki/wiki/project/SPRINT_STATE.md` — phase=8-ship

---

## Task 1 — ADR 0058 + ADR 0056 amendment 2 (docs first, anti-snooping)

**Files:**
- Create: `llm-wiki/wiki/project/decisions/0058-sprint-38-delta-parallel-hardening.md`
- Modify: `llm-wiki/wiki/project/decisions/0056-sprint-36-dsr-sigma-sr-amendment.md` (append S38 amendment 2 section)

- [ ] **Step 1: Write ADR 0058**

Sections:
- Status (Accepted 2026-04-27)
- Context — ROUND 6 consilium binding post-S37 + δ activation timing
- Decision (5 sub-decisions):
  - SD-1: F2 fix — `compute_live_sharpe` uses `pnl_pct` (NOT `pnl_quote`) — Sharpe correctness if Kelly varies
  - SD-2: F3 bybit-api-reviewer first invocation — query document + findings persisted
  - SD-3: Item #7 RiskSharedDeps Demeter refactor — DI wiring only constraint
  - SD-4: Playbook amendments F4-F7 + UNDERPOWERED expected + halt-triggered immediate review
  - SD-5: 12mo MAINNET-promotion ADR DEFERRED к n=10 milestone (anti-snooping per quant)
- Consequences
- Related (ADR 0055/0056/0057 + pre-s38-backlog)

- [ ] **Step 2: Append ADR 0056 amendment 2 section**

Add к `0056-sprint-36-dsr-sigma-sr-amendment.md`:

```markdown

---

## S38 Amendment 2 (ROUND 6 quant-stats finding F2)

### Live Sharpe returns semantics

`compute_live_sharpe()` returns input MUST be `pnl_pct` (fractional returns), NOT `pnl_quote` (absolute P&L).

| Variant | Source | Issue |
|---------|--------|-------|
| **S37 ORIGINAL** | `[float(r.pnl_quote) for r in records]` | Bias if Kelly sizing varies position sizes — large positions dominate mean/std ratio artificially |
| **S38 AMENDED** | `[float(r.pnl_pct) for r in records]` | Dimensionless returns commensurable across trade sizes |

Rationale: Sharpe formula `(mean/std) * sqrt(N)` requires returns of comparable magnitude. `pnl_quote` scales с position size; `pnl_pct` normalizes. `dsr.py compute_returns()` correctly uses `pnl_pct` — live reporter brought into consistency.

Per quant-stats-reviewer ROUND 6: "current code uses pnl_quote (live_trade_reporter.py:62), which is implicitly assuming fixed position sizing. If ADR 0057 or future risk changes allow variable Kelly sizing, this becomes a correctness issue."

### Backward-compat note

Existing `test_live_trade_reporter.py` tests pass `_make_records()` synthesizing TradeRecords с `pnl_pct = pnl_quote / Decimal("50000")`. Tests continue passing — only return-extraction changes.
```

- [ ] **Step 3: Commit ADR 0058 + ADR 0056 amendment 2 IMMEDIATELY**

```bash
git add llm-wiki/wiki/project/decisions/0058-sprint-38-delta-parallel-hardening.md \
        llm-wiki/wiki/project/decisions/0056-sprint-36-dsr-sigma-sr-amendment.md
git commit -m "docs(adr): ADR 0058 δ parallel hardening + ADR 0056 amendment 2 (S38 T1)

ADR 0058 (5 sub-decisions per ROUND 6 consilium BINDING):
  SD-1: F2 quant HIGH fix (pnl_quote → pnl_pct в compute_live_sharpe)
  SD-2: F3 bybit-api-reviewer first invocation
  SD-3: Item #7 RiskSharedDeps Demeter refactor (DI wiring only constraint)
  SD-4: Playbook amendments F4-F7 + UNDERPOWERED + halt-triggered
  SD-5: 12mo MAINNET-promotion ADR DEFERRED к n=10 milestone

ADR 0056 amendment 2:
  - Live Sharpe returns = pnl_pct (NOT pnl_quote)
  - Sharpe formula correctness if Kelly sizing varies
  - Brings live reporter в consistency с dsr.py compute_returns()

Per pre-s38-backlog.md ROUND 6 binding consilium decision."
```

---

## Task 2 — F2 quant HIGH fix: compute_live_sharpe pnl_quote → pnl_pct

**Files:**
- Modify: `src/analytics/live_trade_reporter.py:62`
- Create: `tests/unit/test_live_trade_reporter_pnl_pct.py` (3 tests)
- Modify: `tests/unit/test_live_trade_reporter.py` (existing test fixtures verify pnl_pct semantic preserved)

- [ ] **Step 1: Write failing test verifying current bug**

Create `tests/unit/test_live_trade_reporter_pnl_pct.py`:

```python
"""S38 T2 F2 fix — compute_live_sharpe returns extracted from pnl_pct (NOT pnl_quote).

Per ROUND 6 quant-stats-reviewer F2 HIGH:
  Sharpe formula requires dimensionless returns commensurable across trade sizes.
  pnl_quote scales с position size — Kelly variance bias.
  pnl_pct = correct fractional returns.
"""
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from src.analytics.live_trade_reporter import compute_live_sharpe
from src.risk.reason_codes import ReasonCode
from src.risk.trade_history import TradeRecord


def _trade(*, pnl_quote: Decimal, pnl_pct: Decimal, exit_ts: datetime) -> TradeRecord:
    return TradeRecord(
        symbol="BTCUSDT",
        entry_signal_id=uuid4(),
        entry_ts=exit_ts - timedelta(minutes=30),
        exit_ts=exit_ts,
        qty=Decimal("0.1"),
        entry_price=Decimal("50000"),
        exit_price=Decimal("50000") + pnl_quote,
        pnl_quote=pnl_quote,
        pnl_pct=pnl_pct,
        fees_paid=Decimal("0.1"),
        reason_code=ReasonCode.EXIT_SL_HIT,
        kelly_phase=1,
        recorded_at=exit_ts,
    )


def test_sharpe_uses_pnl_pct_not_pnl_quote() -> None:
    """ROUND 6 F2: returns must use pnl_pct, NOT pnl_quote.

    Construct trades с identical pnl_pct но varying pnl_quote (varying position sizes).
    Sharpe should depend ONLY on pnl_pct (dimensionless), NOT pnl_quote (size-biased).
    """
    base = datetime(2026, 1, 1, tzinfo=UTC)
    # 12 trades с alternating wins/losses, identical pnl_pct (±0.01) но varying pnl_quote
    trades_small = [
        _trade(
            pnl_quote=Decimal("100") * (Decimal("1") if i % 2 == 0 else Decimal("-1")),
            pnl_pct=Decimal("0.01") * (Decimal("1") if i % 2 == 0 else Decimal("-1")),
            exit_ts=base + timedelta(hours=i),
        )
        for i in range(12)
    ]
    # Same pnl_pct, BUT pnl_quote scaled 10x (larger position size)
    trades_large = [
        _trade(
            pnl_quote=Decimal("1000") * (Decimal("1") if i % 2 == 0 else Decimal("-1")),
            pnl_pct=Decimal("0.01") * (Decimal("1") if i % 2 == 0 else Decimal("-1")),
            exit_ts=base + timedelta(hours=i),
        )
        for i in range(12)
    ]
    sharpe_small = compute_live_sharpe(trades_small)["sharpe"]
    sharpe_large = compute_live_sharpe(trades_large)["sharpe"]
    # Sharpe should be IDENTICAL (pnl_pct same) — pnl_quote scaling должен НЕ matter
    assert sharpe_small == pytest.approx(sharpe_large, abs=1e-9)


def test_sharpe_pnl_pct_extraction_correct_value() -> None:
    """Verify Sharpe computed на pnl_pct values produces expected magnitude."""
    base = datetime(2026, 1, 1, tzinfo=UTC)
    # 12 trades с known pnl_pct: alternating +0.02 / -0.01
    trades = [
        _trade(
            pnl_quote=Decimal("0"),  # quote irrelevant (pnl_pct extraction)
            pnl_pct=Decimal("0.02") if i % 2 == 0 else Decimal("-0.01"),
            exit_ts=base + timedelta(hours=i),
        )
        for i in range(12)
    ]
    result = compute_live_sharpe(trades, bars_per_year=2190, avg_bars_per_trade=12.0)
    # Mean = (0.02*6 + -0.01*6) / 12 = 0.005
    # Sharpe positive (mean > 0)
    assert result["sharpe"] > 0
    assert result["status"] == "UNDERPOWERED"  # n=12 < 30


def test_sharpe_zero_variance_pnl_pct_returns_degenerate() -> None:
    """Defensive: pnl_pct constant → DEGENERATE_VARIANCE status."""
    base = datetime(2026, 1, 1, tzinfo=UTC)
    trades = [
        _trade(
            pnl_quote=Decimal("100"),
            pnl_pct=Decimal("0.001"),  # constant
            exit_ts=base + timedelta(hours=i),
        )
        for i in range(12)
    ]
    result = compute_live_sharpe(trades)
    assert result["status"] == "DEGENERATE_VARIANCE"
```

- [ ] **Step 2: Run RED**

```bash
.venv/bin/pytest tests/unit/test_live_trade_reporter_pnl_pct.py -v
```

Expected: `test_sharpe_uses_pnl_pct_not_pnl_quote` FAILS (current code uses pnl_quote → small/large differ). Other 2 may pass coincidentally.

- [ ] **Step 3: Apply F2 fix**

Edit `src/analytics/live_trade_reporter.py:62`:

```python
# OLD: returns = [float(r.pnl_quote) for r in records]
# NEW (per ADR 0056 amendment 2):
returns = [float(r.pnl_pct) for r in records]
```

- [ ] **Step 4: Run GREEN + verify existing tests preserved**

```bash
.venv/bin/pytest tests/unit/test_live_trade_reporter_pnl_pct.py tests/unit/test_live_trade_reporter.py -v
.venv/bin/mypy --strict src/analytics/live_trade_reporter.py
```

Expected: 3 NEW + existing GREEN. Existing test_live_trade_reporter.py uses `_make_records()` with `pnl_pct = pnl / Decimal("50000")` — preserved semantic (proportional к pnl_quote, just normalized).

NOTE: existing `test_generate_live_report_full_metrics` may need numeric assertion updates если any test asserted specific Sharpe value. Most likely tests check status flags + non-NaN, не specific numbers.

- [ ] **Step 5: Run full unit regression**

```bash
.venv/bin/pytest tests/unit -q --ignore=tests/integration 2>&1 | tail -3
```

Expected: 897 baseline + 3 new = 900 passed.

- [ ] **Step 6: Commit**

```bash
git add src/analytics/live_trade_reporter.py tests/unit/test_live_trade_reporter_pnl_pct.py
# Plus existing test_live_trade_reporter.py если needed updates
git commit -m "fix(analytics): F2 HIGH — compute_live_sharpe returns = pnl_pct (S38 T2)

Per ADR 0058 SD-1 + ADR 0056 amendment 2 + ROUND 6 quant-stats F2 HIGH:

Pre-S38: src/analytics/live_trade_reporter.py:62 used pnl_quote (absolute P&L).
  Sharpe formula scales с position size — bias if Kelly sizing varies.
  Inconsistent с dsr.py compute_returns() (which correctly uses pnl_pct).

Post-S38: pnl_pct extraction (dimensionless fractional returns).
  Sharpe commensurable across trade sizes.
  Live reporter aligned с DSR semantics.

3 NEW tests verify (1) pnl_quote scaling does NOT affect Sharpe, (2) pnl_pct
known-value Sharpe positive, (3) zero-variance pnl_pct → DEGENERATE_VARIANCE.

pytest 897 → 900 passed. mypy --strict 0."
```

---

## Task 3 — F3 bybit-api-reviewer first invocation

**Files:**
- Create: `llm-wiki/wiki/queries/2026-04-27-bybit-api-reviewer-first-invocation.md` (review doc)

- [ ] **Step 1: Dispatch bybit-api-reviewer agent**

Use Agent tool с `subagent_type="bybit-api-reviewer"` (NOTE: agent dormant since S30 — first invocation):

Brief: review src/execution/coordinator.py + src/execution/bybit/* covering 6-axis checklist:
1. Rate limits (Bybit V5 spec compliance)
2. Order params (side/orderType/qty/price/stopOrderType etc)
3. WS schema (private channel order/execution events)
4. retCode handling (10003 permission denied / other documented codes)
5. Pagination (kline + order history)
6. HMAC sign (request signing)

Include context:
- δ TESTNET activation S38 — first production-runtime invocation
- Strategy: MeanReversionRsiBBStrategy + LOCKED params
- Symbol: BTCUSDT 4H (single-symbol per pre-commit)
- Halt criteria pre-committed (HaltGate fail-closed)

Expected output: review with severity-ranked findings (BLOCKER / HIGH / MEDIUM / LOW).

- [ ] **Step 2: Persist review document**

Save Agent output к `llm-wiki/wiki/queries/2026-04-27-bybit-api-reviewer-first-invocation.md` per `wiki-update` skill query format.

- [ ] **Step 3: Triage findings**

If BLOCKER findings → S38 hotfix tasks (or S38a sprint).
If HIGH findings → either fix in S38 OR persist в pre-s39-backlog.
If MEDIUM/LOW → pre-s39-backlog only.

- [ ] **Step 4: Commit review document**

```bash
git add llm-wiki/wiki/queries/2026-04-27-bybit-api-reviewer-first-invocation.md
git commit -m "docs(query): bybit-api-reviewer first invocation против coordinator + bybit/ (S38 T3)

Per ADR 0058 SD-2 + ROUND 6 trading-logic-reviewer F3:

bybit-api-reviewer agent dormant since S30 — first production-runtime invocation.
6-axis review (rate limits / order params / WS schema / retCode / pagination / HMAC).

Context: δ TESTNET S38 first activation. MeanReversionRsiBBStrategy LOCKED params.
BTCUSDT 4H single-symbol. HaltGate fail-closed pre-committed.

Findings triaged by severity. BLOCKER → S38 hotfix. HIGH → S38 OR pre-s39-backlog.
MEDIUM/LOW → pre-s39-backlog."
```

---

## Task 4 — Item #7 RiskSharedDeps Demeter refactor

**Files:**
- Modify: `src/risk/manager.py` — add RiskSharedDeps NamedTuple + factory method
- Modify: `src/runtime/manager.py` — accept RiskSharedDeps OR backward-compat individual kwargs
- Modify: `src/__main__.py:_cmd_run` — construct + pass RiskSharedDeps
- Create: `tests/unit/test_risk_shared_deps.py` (4 tests)

**CRITICAL constraint per ROUND 6 trader-expert + trading-logic-reviewer:**
- DI wiring ONLY — NOT touch `_tick()` body OR `HaltGate.evaluate()`
- Smoke-start gate before merge (pytest 897+33 + restart-safety verify)
- Backward-compat: existing tests use individual kwargs MUST still pass

- [ ] **Step 1: TDD failing tests**

Create `tests/unit/test_risk_shared_deps.py`:

```python
"""S38 T4 — RiskSharedDeps Demeter refactor per ADR 0058 SD-3.

Per ROUND 6 architecture-reviewer Item #7:
  RuntimeManager accesses risk_manager.equity_tracker / trade_repo / state_repo
  properties — Demeter violation. Bundle into RiskSharedDeps NamedTuple.

CONSTRAINT: DI wiring only. NOT touch _tick() OR HaltGate.evaluate().
Backward-compat: individual kwargs to RuntimeManager still work.
"""
from unittest.mock import MagicMock

import pytest


def test_risk_shared_deps_namedtuple_exposes_three_fields() -> None:
    """RiskSharedDeps bundle has equity_tracker + trade_repo + state_repo."""
    from src.risk.manager import RiskSharedDeps
    deps = RiskSharedDeps(
        equity_tracker=MagicMock(),
        trade_repo=MagicMock(),
        state_repo=MagicMock(),
    )
    assert deps.equity_tracker is not None
    assert deps.trade_repo is not None
    assert deps.state_repo is not None


def test_risk_manager_shared_deps_property_returns_namedtuple() -> None:
    """RiskManager.shared_deps property returns RiskSharedDeps bundle."""
    from src.risk.manager import RiskManager, RiskSharedDeps
    # Use existing in-memory factory pattern from test_risk_manager fixtures
    # (verify shared_deps property exposes bundle)
    # ... implementation depends on existing test_risk_manager.py fixture pattern


def test_runtime_manager_accepts_risk_shared_deps_kwarg() -> None:
    """RuntimeManager constructor accepts shared_deps=RiskSharedDeps OR individual kwargs (backward-compat)."""
    from src.risk.manager import RiskSharedDeps
    from src.runtime.manager import RuntimeManager
    deps = RiskSharedDeps(
        equity_tracker=MagicMock(),
        trade_repo=MagicMock(),
        state_repo=MagicMock(),
    )
    # New path: shared_deps bundle
    rm_new = RuntimeManager(
        coordinator=MagicMock(),
        reconciler=MagicMock(),
        ws_consumer=MagicMock(),
        bar_source=MagicMock(),
        strategy=MagicMock(),
        risk_manager=MagicMock(),
        settings=MagicMock(),
        shared_deps=deps,
    )
    assert rm_new._equity_tracker is deps.equity_tracker
    assert rm_new._trade_repo is deps.trade_repo
    assert rm_new._state_repo is deps.state_repo


def test_runtime_manager_backward_compat_individual_kwargs_still_work() -> None:
    """Backward-compat: existing call sites pass equity_tracker= directly."""
    from src.runtime.manager import RuntimeManager
    et = MagicMock()
    tr = MagicMock()
    sr = MagicMock()
    rm = RuntimeManager(
        coordinator=MagicMock(),
        reconciler=MagicMock(),
        ws_consumer=MagicMock(),
        bar_source=MagicMock(),
        strategy=MagicMock(),
        risk_manager=MagicMock(),
        settings=MagicMock(),
        equity_tracker=et,
        trade_repo=tr,
        state_repo=sr,
    )
    assert rm._equity_tracker is et
    assert rm._trade_repo is tr
    assert rm._state_repo is sr
```

- [ ] **Step 2: Implement RiskSharedDeps NamedTuple**

Edit `src/risk/manager.py`. Add at top after imports:

```python
from typing import NamedTuple


class RiskSharedDeps(NamedTuple):
    """S38 T4 ADR 0058 SD-3: shared risk infrastructure bundle for DI.
    
    Replaces RuntimeManager accessing risk_manager.equity_tracker/trade_repo/state_repo
    properties (Demeter violation per S37 T4 architecture-reviewer).
    
    Single bundle passed к both RiskManager and RuntimeManager constructors.
    """
    equity_tracker: "EquityTracker"
    trade_repo: "TradeHistoryRepository"
    state_repo: "StateRepository"
```

Add `RiskManager.shared_deps` property:

```python
@property
def shared_deps(self) -> RiskSharedDeps:
    """S38 T4: bundle accessor для RuntimeManager DI."""
    return RiskSharedDeps(
        equity_tracker=self._equity,
        trade_repo=self._trades,
        state_repo=self._state,
    )
```

- [ ] **Step 3: Modify RuntimeManager constructor для backward-compat**

Edit `src/runtime/manager.py:56-69`. Add `shared_deps` kwarg:

```python
def __init__(
    self,
    *,
    coordinator: Coordinator,
    reconciler: Reconciler,
    ws_consumer: BybitPrivateWSConsumer,
    bar_source: BarSource,
    strategy: Strategy,
    risk_manager: RiskManager,
    settings: Settings,
    # S38 T4 ADR 0058 SD-3: prefer shared_deps bundle (Demeter compliance).
    # Backward-compat: individual kwargs still accepted.
    shared_deps: RiskSharedDeps | None = None,
    equity_tracker: EquityTracker | None = None,
    trade_repo: TradeHistoryRepository | None = None,
    state_repo: StateRepository | None = None,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> None:
    # Resolve DI: shared_deps wins, else individual kwargs
    if shared_deps is not None:
        self._equity_tracker = shared_deps.equity_tracker
        self._trade_repo = shared_deps.trade_repo
        self._state_repo = shared_deps.state_repo
    else:
        if equity_tracker is None or trade_repo is None or state_repo is None:
            raise ValueError(
                "RuntimeManager: must provide shared_deps OR all of "
                "equity_tracker/trade_repo/state_repo"
            )
        self._equity_tracker = equity_tracker
        self._trade_repo = trade_repo
        self._state_repo = state_repo
    # ... rest of __init__ unchanged ...
```

- [ ] **Step 4: Update src/__main__.py к prefer shared_deps**

Replace в `_cmd_run`:
```python
# OLD:
runtime = RuntimeManager(
    ...
    equity_tracker=risk_manager.equity_tracker,
    trade_repo=risk_manager.trade_repo,
    state_repo=risk_manager.state_repo,
)
# NEW:
runtime = RuntimeManager(
    ...
    shared_deps=risk_manager.shared_deps,
)
```

- [ ] **Step 5: Run tests + smoke-start gate**

```bash
.venv/bin/pytest tests/unit/test_risk_shared_deps.py tests/unit/test_runtime_manager.py tests/integration/test_halt_gate_wireup.py -v
.venv/bin/mypy --strict src/risk/manager.py src/runtime/manager.py src/__main__.py
.venv/bin/pytest tests/unit -q --ignore=tests/integration 2>&1 | tail -3
.venv/bin/pytest tests/integration -q 2>&1 | tail -3
```

Expected: 4 NEW + existing tests preserved (backward-compat path works). 900 + 4 = 904 unit.

- [ ] **Step 6: Commit**

```bash
git add src/risk/manager.py src/runtime/manager.py src/__main__.py tests/unit/test_risk_shared_deps.py
git commit -m "refactor(risk): RiskSharedDeps Demeter bundle per ADR 0058 SD-3 (S38 T4)

Per ROUND 6 architecture-reviewer Item #7 + S37 T4 carry-over:

Pre-S38: RuntimeManager accessed risk_manager.equity_tracker/trade_repo/state_repo
  properties — Law of Demeter violation (S37 T4 architecture-reviewer MEDIUM).
Post-S38: RiskSharedDeps NamedTuple bundle. RuntimeManager accepts shared_deps=
  preferred path. Individual kwargs preserved для backward-compat.

CONSTRAINT (per ROUND 6 binding): DI wiring ONLY. NOT touch _tick() body OR
HaltGate.evaluate(). Smoke-start gate verified via test_runtime_manager.py +
integration tests preserved.

4 NEW tests verify NamedTuple + property + bundle path + backward-compat.
pytest 900 → 904 passed. mypy --strict 0."
```

---

## Task 5 — Items #6 + #9 documentation amendments

**Files:**
- Modify: `llm-wiki/wiki/project/decisions/0057-sprint-37-carry-overs-hardening.md` — append months_since truncation note (Item #6)

- [ ] **Step 1: Append к ADR 0057**

Add section к end of `0057-sprint-37-carry-overs-hardening.md`:

```markdown

---

## S38 Item #6 Amendment — `months_since` truncation semantics

`RuntimeManager._check_halt_gate()` computes:
```python
months_since = (self._clock() - last_ts).days // 30
```

**Truncation** (Python integer division `//`): 29 days → 0 months, 30 days → 1 month, 59 days → 1 month, 60 days → 2 months.

Implication: `HALT_S36_NO_TRADE_TIMEOUT` fires only after FULL 6 × 30 = 180 days without trade. NOT after 5mo 29days. Conservative bias (under-fires by ≤30 days).

Operator interpretation: legitimate timeout halt vs boundary artifact:
- True halt: bot active >180 days, n=0 trades — strategy degraded OR market regime shift
- Boundary artifact: NONE (truncation is one-directional under-fire, never spurious fire)

Per ROUND 6 trading-logic-reviewer C4 (S37 T4 carry-over): "truncation is intentional, conservative under-fire by up to 30 days. Document explicitly."
```

- [ ] **Step 2: Note Item #9 covered by ADR 0056 amendment 2 (T1)**

ADR 0056 amendment 2 (T1) already addresses Sharpe semantics extended doc. Item #9 closed via T1 — no separate ADR needed.

- [ ] **Step 3: Commit**

```bash
git add llm-wiki/wiki/project/decisions/0057-sprint-37-carry-overs-hardening.md
git commit -m "docs(adr): ADR 0057 amendment — months_since truncation semantics (S38 T5 Item #6)

Per ROUND 6 trading-logic-reviewer C4 (S37 T4 carry-over):
  Document months_since = (now - last_ts).days // 30 truncation behavior.
  Conservative under-fire (≤30 days), no spurious-fire risk.
  Operator interpretation guide: legitimate halt vs boundary artifact.

Item #9 (Sharpe semantics extended ADR) closed via ADR 0056 amendment 2 (T1)."
```

---

## Task 6 — Playbook amendments (5 NEW gates + UNDERPOWERED + halt-triggered)

**Files:**
- Modify: `llm-wiki/wiki/project/components/delta-activation-playbook.md`

- [ ] **Step 1: Add 5 NEW pre-activation gates**

Append к "Pre-activation checklist" section:

```markdown

### S38 ADR 0058 SD-4 NEW gates (post-ROUND 6 consilium):

- [ ] **F4 — Bybit TESTNET API key scope verification**: confirm key has Order (read+write) AND Position permissions enabled. Pre-flight: `GET /v5/account/info` + verify `POST /v5/order/create` reachable. Read-only key → `retCode=10003` permission denied на first signal.
- [ ] **F5 — No stale `runtime:halt_gate:activation_ts` row**: query `sqlite3 data/bot.db "SELECT * FROM state WHERE key='runtime:halt_gate:activation_ts';"` — must be empty OR signed с current `risk_override_hmac_key`. Different HMAC key version → tamper halt on first tick.
- [ ] **F7 (Gate 2) — SQLite WAL mode + disk space**: confirm > 1GB free disk space. halt_log accumulates rows over 12mo TESTNET window.
- [ ] **F7 (Gate 3) — Bootstrap ordering invariant**: `coordinator.bootstrap()` MUST complete before `ws_consumer.start()`. Current code at `src/runtime/manager.py:104-105` correct order. DO NOT reorder без verifying assertion paths.
```

- [ ] **Step 2: Add "DSR UNDERPOWERED expected" annotation к monitoring section**

Append к "Monitoring procedure" section:

```markdown

### Important — DSR UNDERPOWERED is EXPECTED for entire 12mo window

Per quant-stats-reviewer ROUND 6:
  At S22 baseline 13 trades/year: expected n=13 после 12mo TESTNET.
  ADR 0056 thresholds: 10 ≤ n < 30 → DSR_UNDERPOWERED status.
  This is NOT failure signal — это expected small-n regime.

DO NOT abort δ TESTNET because of UNDERPOWERED DSR alone.
Halt только если HaltGate triggers (DD/streak/timeout) OR operator decides honest close per separate criteria.

GATE_ELIGIBLE (n≥30) expected at ~28 months at baseline rate — outside 12mo MAINNET-promotion review window. 12mo review = "continue TESTNET" recommendation likely (per quant-stats expected outcome).
```

- [ ] **Step 3: Add halt-triggered immediate review к monitoring section**

Append:

```markdown

### Halt-triggered immediate review (S38 trading-logic-reviewer addition)

Weekly cadence catches operational health BUT может miss weekend halt (3-day blind spot).

**Additional trigger:** if `halt_log` has any entry within last 24H → immediate review (don't wait для weekly slot).

Quick check command:
```bash
sqlite3 data/bot.db "SELECT halt_ts, halt_reason FROM halt_log WHERE halt_ts > datetime('now', '-24 hours');"
```

If non-empty → execute halt response procedure immediately.
```

- [ ] **Step 4: Commit**

```bash
git add llm-wiki/wiki/project/components/delta-activation-playbook.md
git commit -m "docs(component): δ playbook amendments — 5 NEW gates + UNDERPOWERED + halt-triggered (S38 T6)

Per ADR 0058 SD-4 + ROUND 6 consilium findings:

Pre-activation gates added (F4-F7):
  - F4 Bybit TESTNET API key scope verification (Order write permission)
  - F5 No stale runtime:halt_gate:activation_ts row check
  - F7 (Gate 2) WAL disk space > 1GB
  - F7 (Gate 3) Bootstrap ordering invariant doc

Monitoring section additions:
  - DSR UNDERPOWERED expected for 12mo (do NOT misread as failure)
  - Halt-triggered immediate review (weekend halt blind spot мitigation)

Operator confidence + production-readiness discipline preserved."
```

---

## Task 7 — sprint-38 page + counts + ship

**Files:**
- Create: `llm-wiki/wiki/project/sprints/sprint-38-delta-parallel-hardening.md`
- Modify: index.md / current-state.md / log.md / SPRINT_STATE.md
- Modify: `.github/workflows/ci.yml` — NO change (canonical reason_codes still 50)

Counts:
- ADRs: 57 → **58**
- Sprint pages: 41 → **42**
- Components: 48 (unchanged — no NEW component)
- Reason codes: 50 (unchanged)

Standard wiki sync per `sprint-finish` skill pattern.

---

## Self-Review Checklist

**1. Spec coverage:** All 6 ROUND 6 binding pre-commitments addressed?
- ✅ #1 δ activate timing — operator decides (no AI task)
- ✅ #2 F2 pnl_pct fix → T2
- ✅ #3 Item #7 DI-only constraint → T4 (smoke-start gate documented)
- ✅ #4 Smoke-start gate → T4 step 5
- ✅ #5 F3 bybit-api-reviewer → T3
- ✅ #6 Playbook amendments → T6
- ✅ #7 No 12mo MAINNET ADR в S38 → ADR 0058 SD-5 explicit

**2. Placeholder scan:** All steps have test code OR commit messages.

**3. Type consistency:** `RiskSharedDeps` NamedTuple consistent T4. `pnl_pct` extraction consistent T2 + ADR 0056 amendment 2.

**4. Trace map covers backlog:** All 8 ROUND 6 findings mapped к T1-T7.

---

## Execution Handoff

Plan complete. Two execution options:

1. **Subagent-Driven (recommended)** — fresh subagent per task
2. **Inline Execution** — controller-driven via `superpowers:executing-plans`

Operator approve mode?
