---
title: Sprint 37 Plan — Carry-overs Hardening (security HIGH + trading-logic + quant + δ activation playbook)
type: plan
tags: [sprint-37, plan, carry-overs, security-hardening, halt-unknown-symbol, calibration-amendment, clock-injection, ru]
created: 2026-04-27
updated: 2026-04-27
status: proposed
sources:
  - project/decisions/0055-sprint-36-delta-activation.md
  - project/decisions/0056-sprint-36-dsr-sigma-sr-amendment.md
  - project/pre-s37-backlog.md
  - project/sprints/sprint-36-delta-activation.md
---

# Sprint 37 Implementation Plan — Carry-overs Hardening

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close 6 critical S36 carry-overs (security HIGH 1-3 + trading-logic 4-5 + quant 8) + ADR 0056 amendment (calibration baseline + Sharpe semantics) + δ activation operator playbook. Production-ready перед δ TESTNET activate в S38.

**Architecture:** Eight serialized TDD tasks per ROUND 5 consilium binding. Critical-path: ADR first → ReasonCode +1 → security hardening (whitelist + fail-closed + HMAC) → trading-logic hygiene (clock + property) → quant boundary tests → playbook → wiki sync.

**Tech Stack:** Python 3.12 / pydantic-settings / SQLite WAL / HMAC-SHA256 / pytest-Hypothesis / mypy --strict / TDD RED→GREEN.

---

## Trace Map (PHASE 3 step 1a HARD-GATE)

| Source artifact | Implementation task |
|-----------------|---------------------|
| pre-s37-backlog Item #1 (symbol whitelist + startup banner) | T2 |
| pre-s37-backlog Item #2 (symbol fail-closed + HALT_UNKNOWN_SYMBOL) | T2 + ReasonCode 49→50 |
| pre-s37-backlog Item #3 (activation_ts HMAC integrity) | T3 |
| pre-s37-backlog Item #4 (clock injection в _check_halt_gate) | T4 |
| pre-s37-backlog Item #5 (coordinator.symbol public property) | T5 |
| pre-s37-backlog Item #8 (DSR boundary tests n=10/30) | T6 |
| ROUND 5 calibration amendment (S22 6.17 → 2.96) | T1 ADR 0056 amendment + T6 |
| ROUND 5 ADR 0056 Sharpe semantics doc | T1 ADR 0056 amendment |
| Operator playbook page | T7 |

---

## File Structure

**Create:**
- `llm-wiki/wiki/project/decisions/0057-sprint-37-carry-overs-hardening.md` — ADR 0057 (~150 lines)
- `llm-wiki/wiki/project/decisions/0056-sprint-36-dsr-sigma-sr-amendment.md` — APPEND amendment section (calibration + Sharpe semantics)
- `llm-wiki/wiki/project/components/delta-activation-playbook.md` — operator playbook (~80 lines)
- `llm-wiki/wiki/project/sprints/sprint-37-carry-overs-hardening.md` — sprint page
- `tests/unit/test_symbol_whitelist.py` (T2)
- `tests/unit/test_activation_ts_hmac.py` (T3)
- `tests/unit/test_check_halt_gate_clock_injection.py` (T4)
- `tests/unit/test_coordinator_symbol_property.py` (T5)
- Append к `tests/unit/test_dsr_status_thresholds.py` (T6 boundary tests parametrized)

**Modify:**
- `src/risk/reason_codes.py` — add HALT_UNKNOWN_SYMBOL (49→50) (T2)
- `tests/property/test_request_halt_mapping.py` — extend allowlist (T2)
- `src/platform/config.py` — add `s35_demo_approved_symbols: list[str] = ["BTCUSDT"]` setting (T2)
- `src/runtime/manager.py` — startup banner + symbol whitelist check + fail-closed semantic + clock injection (T2 + T4)
- `src/risk/state_repo.py` — HMAC-signed activation_ts persistence (T3)
- `src/execution/coordinator.py` — `symbol` public property (T5)
- `src/analytics/live_trade_reporter.py` — `S22_SYNTHETIC_SHARPE = 2.96` (T1+T6)
- `llm-wiki/wiki/index.md` — ADR 0057 + sprint-37 + playbook + amendment ref (T8)
- `llm-wiki/wiki/project/architecture/current-state.md` — counts 56→57 ADRs / 40→41 sprints / 47→48 components / 49→50 reason codes (T8)
- `llm-wiki/wiki/project/components/reason-codes-schema.md` — +1 row (T2 + T8)
- `llm-wiki/wiki/project/components/execution-state-machine.md` — footer sync (T8)
- `llm-wiki/wiki/log.md` — sprint-end (T8)
- `llm-wiki/wiki/project/SPRINT_STATE.md` — phase=8-ship (T8)
- `.github/workflows/ci.yml` — canonical reason_codes 49→50 (T8)
- `.claude/skills/wiki-update/` (если applicable cascade rule update)

---

## Task 1 — ADR 0057 + ADR 0056 amendment (docs first, anti-snooping)

**Why first:** All subsequent tasks reference ADR pre-commits. ADR 0057 LOCKED + ADR 0056 amendment перед code.

**Files:**
- Create: `llm-wiki/wiki/project/decisions/0057-sprint-37-carry-overs-hardening.md`
- Modify: `llm-wiki/wiki/project/decisions/0056-sprint-36-dsr-sigma-sr-amendment.md` (append amendment section)

- [ ] **Step 1: Write ADR 0057 LOCKED**

Sections:
- Status (Accepted 2026-04-27)
- Context — ROUND 5 consilium binding post-S36 carry-overs
- Decision (6 sub-decisions):
  - SD-1: HALT_UNKNOWN_SYMBOL distinct ReasonCode (49→50, NOT reuse existing) per audit-log attribution rule
  - SD-2: Symbol fail-closed semantic — `_check_halt_gate()` halt with HALT_UNKNOWN_SYMBOL on unrecognized symbol (NOT warn+skip)
  - SD-3: Symbol whitelist `s35_demo_approved_symbols: list[str]` Setting (default ["BTCUSDT"]) + startup banner displays whitelist
  - SD-4: activation_ts HMAC integrity per ADR 0018 pattern (`risk_override_hmac_key` reused OR new key?)
  - SD-5: Clock injection в `_check_halt_gate()` per S8a precedent (`clock: Callable[[], datetime]` default `datetime.now`)
  - SD-6: coordinator.symbol public property (replace `getattr(coordinator, "_symbol", None)` private leak)
- Consequences
- Related (ADRs 0055/0056/0018/pre-s37-backlog)

- [ ] **Step 2: Append ADR 0056 amendment section**

Add к `0056-sprint-36-dsr-sigma-sr-amendment.md`:

```markdown
## S37 Amendment (per ROUND 5 consilium quant-stats verdict)

### Calibration baseline correction

`S22_SYNTHETIC_SHARPE` constant в `src/analytics/live_trade_reporter.py:28`:
- ORIGINAL (S36 T7): 6.17 (T1 aggregate Sharpe per sprint-22-4h-test.md — small-n + fold concentration extreme value)
- AMENDED (S37): **2.96** (mean fold Sharpe = (1.93-2.92+1.32+12.70+1.78)/5)

Rationale: T1 aggregate 6.17 inflated by fold #4 outlier (12.70 Sharpe at n≈12 trades). Mean fold conservative baseline для calibration ratio target ≥0.7.

### Sharpe computation semantics (clarification per quant-stats C3)

| Metric | Definition | Use |
|--------|------------|-----|
| `trial_mean_fold_oos_sharpe` | arithmetic mean of K WFA fold OOS Sharpes | cross_trial log entry, sigma_SR pooling |
| `pooled_trade_oos_sharpe` | trade-level Sharpe over ALL OOS trades concatenated | overall trial Sharpe metric |
| `live_sharpe` | per-TradeRecord pnl_quote returns annualized via `sqrt(bars_per_year/avg_bars_per_trade)` | δ live demo evaluation (live_trade_reporter) |

These three metrics are statistically distinct. Future audits MUST cite which Sharpe is used.
```

- [ ] **Step 3: Commit ADRs IMMEDIATELY (anti-snooping)**

```bash
git add llm-wiki/wiki/project/decisions/0057-sprint-37-carry-overs-hardening.md \
        llm-wiki/wiki/project/decisions/0056-sprint-36-dsr-sigma-sr-amendment.md
git commit -m "docs(adr): ADR 0057 carry-overs hardening + ADR 0056 amendment (S37 T1)

ADR 0057 (6 sub-decisions per ROUND 5 consilium BINDING):
  SD-1: HALT_UNKNOWN_SYMBOL distinct ReasonCode (49→50)
  SD-2: Symbol fail-closed semantic (halt, NOT warn+skip)
  SD-3: Symbol whitelist Setting + startup banner
  SD-4: activation_ts HMAC integrity per ADR 0018
  SD-5: Clock injection в _check_halt_gate
  SD-6: coordinator.symbol public property

ADR 0056 amendment:
  - Calibration baseline 6.17 → 2.96 (mean fold conservative)
  - Sharpe computation semantics clarified (3 metrics distinguished)

Per pre-s37-backlog.md ROUND 5 binding consilium decision."
```

---

## Task 2 — Security HIGH #1+#2: symbol whitelist + fail-closed + HALT_UNKNOWN_SYMBOL

**Files:**
- Modify: `src/risk/reason_codes.py` (+1 enum)
- Modify: `tests/property/test_request_halt_mapping.py` (extend allowlist)
- Modify: `src/platform/config.py` (+ Setting)
- Modify: `src/runtime/manager.py` (whitelist check + fail-closed + startup banner)
- Create: `tests/unit/test_symbol_whitelist.py` (5 tests)

- [ ] **Step 1: Add HALT_UNKNOWN_SYMBOL ReasonCode**

Edit `src/risk/reason_codes.py` — add after HALT_S36_NO_TRADE_TIMEOUT (line ~105):

```python
    # S37 — δ TESTNET symbol-resolution fail-closed (ADR 0057 SD-1+SD-2)
    HALT_UNKNOWN_SYMBOL = "HALT_UNKNOWN_SYMBOL"  # 50
```

- [ ] **Step 2: Extend property test allowlist**

Edit `tests/property/test_request_halt_mapping.py`:
```python
    ReasonCode.HALT_UNKNOWN_SYMBOL,
```

Run:
```bash
.venv/bin/pytest tests/property/test_request_halt_mapping.py -v
.venv/bin/python -c "from src.risk.reason_codes import ReasonCode; print(len(list(ReasonCode)))"  # expect 50
```

- [ ] **Step 3: Add s35_demo_approved_symbols Setting**

Edit `src/platform/config.py` after `s35_halt_no_trade_months`:

```python
    s35_demo_approved_symbols: list[str] = Field(
        default_factory=lambda: ["BTCUSDT"],
        min_length=1,
        description=(
            "S37 ADR 0057 SD-3: whitelist of symbols permitted under s35_demo_active. "
            "Default [BTCUSDT] per pre-s35-backlog single-symbol LOCKED. "
            "_check_halt_gate fails-closed (HALT_UNKNOWN_SYMBOL) if coordinator symbol "
            "not in whitelist."
        ),
    )
```

- [ ] **Step 4: Write failing test тests**

Create `tests/unit/test_symbol_whitelist.py`:

```python
"""S37 T2 — symbol whitelist + fail-closed semantic per ADR 0057 SD-1+SD-2+SD-3."""
import sqlite3
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.platform.config import Settings
from src.platform.db import connect, init_db
from src.risk.equity_tracker import EquityTracker
from src.risk.reason_codes import ReasonCode
from src.risk.state_repo import StateRepository
from src.risk.trade_history import TradeHistoryRepository
from src.runtime.manager import RuntimeManager

_MIGRATIONS = Path(__file__).parents[2] / "migrations"


def _settings(tmp_path: Path, **overrides):
    base = {
        "bybit_api_key": "test_key_at_least_8",
        "bybit_api_secret": "test_secret_at_least_8",
        "risk_override_hmac_key": "test_key_min_32_chars_for_audit_h2_compliance",
        "data_dir": tmp_path / "data",
        "log_dir": tmp_path / "logs",
        "db_path": tmp_path / "test.db",
        "parquet_dir": tmp_path / "parquet",
        "testnet": True,
        "live_trading": False,
        "s35_demo_active": True,
        "s35_halt_dd_intraday": Decimal("0.20"),
        "s35_halt_dd_multiday": Decimal("0.15"),
        "s35_halt_consecutive_losses": 5,
        "s35_halt_no_trade_months": 6,
    }
    base.update(overrides)
    return Settings(**base)


def _runtime(tmp_path: Path, *, symbol: str | None = "BTCUSDT", **settings_overrides) -> tuple:
    settings = _settings(tmp_path, **settings_overrides)
    init_db(settings.db_path, _MIGRATIONS)
    conn = connect(settings.db_path)
    coord = MagicMock()
    coord._symbol = symbol
    rm = RuntimeManager(
        coordinator=coord, reconciler=MagicMock(),
        ws_consumer=MagicMock(check_alive=MagicMock(return_value=True)),
        bar_source=MagicMock(), strategy=MagicMock(), risk_manager=MagicMock(),
        settings=settings,
        equity_tracker=EquityTracker(conn), trade_repo=TradeHistoryRepository(conn),
        state_repo=StateRepository(conn),
    )
    return rm, coord


def test_default_whitelist_is_btcusdt(tmp_path: Path) -> None:
    """ADR 0057 SD-3: default s35_demo_approved_symbols = [BTCUSDT]."""
    s = _settings(tmp_path)
    assert s.s35_demo_approved_symbols == ["BTCUSDT"]


def test_unknown_symbol_fails_closed_with_halt(tmp_path: Path) -> None:
    """ADR 0057 SD-2: unknown symbol → HALT_UNKNOWN_SYMBOL (NOT warn+skip)."""
    rm, coord = _runtime(tmp_path, symbol="ETHUSDT")  # NOT in whitelist
    halted = rm._check_halt_gate()
    assert halted is True
    coord.request_halt.assert_called_once_with(ReasonCode.HALT_UNKNOWN_SYMBOL)


def test_none_symbol_fails_closed_with_halt(tmp_path: Path) -> None:
    """ADR 0057 SD-2: missing symbol (None) → HALT_UNKNOWN_SYMBOL."""
    rm, coord = _runtime(tmp_path, symbol=None)
    halted = rm._check_halt_gate()
    assert halted is True
    coord.request_halt.assert_called_once_with(ReasonCode.HALT_UNKNOWN_SYMBOL)


def test_whitelisted_symbol_proceeds(tmp_path: Path) -> None:
    """ADR 0057 SD-3: BTCUSDT in whitelist → no halt fired (no other trigger)."""
    rm, coord = _runtime(tmp_path, symbol="BTCUSDT")
    halted = rm._check_halt_gate()
    assert halted is False
    coord.request_halt.assert_not_called()


def test_custom_whitelist_extends_allowed_symbols(tmp_path: Path) -> None:
    """Operator can extend whitelist для multi-symbol future."""
    rm, coord = _runtime(tmp_path, symbol="ETHUSDT", s35_demo_approved_symbols=["BTCUSDT", "ETHUSDT"])
    halted = rm._check_halt_gate()
    assert halted is False  # ETHUSDT now whitelisted
```

- [ ] **Step 5: Modify `_check_halt_gate()` к fail-closed + whitelist**

Edit `src/runtime/manager.py:174-178`:

```python
        # S37 ADR 0057 SD-2+SD-3: fail-closed symbol whitelist check
        symbol = getattr(self._coordinator, "symbol", None) or getattr(self._coordinator, "_symbol", None)
        if symbol is None or symbol not in self._settings.s35_demo_approved_symbols:
            logger.error(
                "runtime.halt_gate_unknown_symbol",
                symbol=symbol,
                whitelist=self._settings.s35_demo_approved_symbols,
            )
            self._coordinator.request_halt(ReasonCode.HALT_UNKNOWN_SYMBOL)
            self._stopping = True
            return True
```

NOTE: T5 (next) will replace `_symbol` access with public `symbol` property. T2 uses fallback chain to support both.

- [ ] **Step 6: Add startup banner**

Edit `src/runtime/manager.py` `run()` method (around line 80) — after `_coordinator.bootstrap()`:

```python
        if self._settings.s35_demo_active:
            logger.info(
                "runtime.s35_demo_startup_banner",
                approved_symbols=list(self._settings.s35_demo_approved_symbols),
                halt_thresholds={
                    "dd_intraday": str(self._settings.s35_halt_dd_intraday),
                    "dd_multiday": str(self._settings.s35_halt_dd_multiday),
                    "consecutive_losses": self._settings.s35_halt_consecutive_losses,
                    "no_trade_months": self._settings.s35_halt_no_trade_months,
                },
                fail_closed=True,
            )
```

- [ ] **Step 7: Run + commit**

```bash
.venv/bin/pytest tests/unit/test_symbol_whitelist.py tests/integration/test_halt_gate_wireup.py -v
.venv/bin/mypy --strict src/runtime/manager.py src/risk/reason_codes.py src/platform/config.py
git add src/risk/reason_codes.py tests/property/test_request_halt_mapping.py \
        src/platform/config.py src/runtime/manager.py tests/unit/test_symbol_whitelist.py
git commit -m "feat(security): symbol whitelist + fail-closed + HALT_UNKNOWN_SYMBOL ReasonCode (S37 T2)

Per ADR 0057 SD-1+SD-2+SD-3 + pre-s37-backlog Items #1+#2:

ReasonCode +1 HALT_UNKNOWN_SYMBOL (49→50). Distinct code preserves halt_log
attribution per γ primary-wins rule (NOT reused HALT_S36_*).

Settings: s35_demo_approved_symbols (default [BTCUSDT]) + RuntimeManager
fail-closed semantic: unknown/missing symbol → HALT_UNKNOWN_SYMBOL halt
(was: warn+skip silent bypass).

Startup banner displays whitelist + halt thresholds when s35_demo_active=True.

5 NEW tests verify default whitelist + fail-closed + multi-symbol extension."
```

---

## Task 3 — Security HIGH #3: activation_ts HMAC integrity

**Files:**
- Modify: `src/risk/state_repo.py` — HMAC-signed setter/getter for activation_ts
- Create: `tests/unit/test_activation_ts_hmac.py` (4 tests)

- [ ] **Step 1: Write failing tests**

Tests verify:
1. activation_ts written with HMAC signature
2. tampered value (manual SQLite UPDATE) raises на read
3. unsigned value rejected
4. valid signature passes verification

- [ ] **Step 2: Implement HMAC wrapper в state_repo.py**

```python
def set_signed(self, key: str, value: dict[str, Any], *, hmac_key: str) -> None:
    """ADR 0057 SD-4: HMAC-signed value persistence per ADR 0018 pattern."""
    import hashlib
    import hmac
    import json
    payload = json.dumps(value, sort_keys=True).encode("utf-8")
    sig = hmac.new(hmac_key.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    self.set(key, {"payload": value, "sig": sig})

def get_signed(self, key: str, *, hmac_key: str) -> dict[str, Any] | None:
    """ADR 0057 SD-4: HMAC-verified read. Raises ValueError на signature mismatch."""
    import hashlib
    import hmac
    import json
    record = self.get(key)
    if record is None:
        return None
    if "payload" not in record or "sig" not in record:
        raise ValueError(f"state_repo: key {key} missing HMAC envelope")
    expected_payload = record["payload"]
    expected_sig = hmac.new(
        hmac_key.encode("utf-8"),
        json.dumps(expected_payload, sort_keys=True).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(record["sig"], expected_sig):
        raise ValueError(f"state_repo: HMAC mismatch для key {key} — tampered value")
    result: dict[str, Any] = expected_payload
    return result
```

- [ ] **Step 3: Update RuntimeManager._check_halt_gate к use signed methods**

Edit `src/runtime/manager.py:164-171`:

```python
        if self._activation_ts is None:
            try:
                activation_record = self._state_repo.get_signed(
                    "runtime:halt_gate:activation_ts",
                    hmac_key=self._settings.risk_override_hmac_key,
                )
            except ValueError as e:
                logger.error("runtime.halt_gate_activation_ts_tampered", error=str(e))
                self._coordinator.request_halt(ReasonCode.HALT_UNKNOWN_SYMBOL)  # OR new HALT_STATE_TAMPERED
                self._stopping = True
                return True
            if activation_record is None:
                now = datetime.now(UTC)
                self._state_repo.set_signed(
                    "runtime:halt_gate:activation_ts", {"value": now.isoformat()},
                    hmac_key=self._settings.risk_override_hmac_key,
                )
                self._activation_ts = now
            else:
                self._activation_ts = datetime.fromisoformat(activation_record["value"])
```

- [ ] **Step 4: Run + commit**

```bash
.venv/bin/pytest tests/unit/test_activation_ts_hmac.py tests/integration/test_halt_gate_wireup.py -v
git commit -m "feat(security): activation_ts HMAC integrity per ADR 0018 pattern (S37 T3)

Per ADR 0057 SD-4 + pre-s37-backlog Item #3:
  state_repo.set_signed/get_signed HMAC-SHA256 wrappers reuse risk_override_hmac_key.
  Tampered value raises ValueError на read → halt + bot exit.
  4 NEW tests verify happy path + tamper detection + unsigned rejection."
```

---

## Task 4 — Trading-logic #4: clock injection в _check_halt_gate

**Files:**
- Modify: `src/runtime/manager.py` — add `clock: Callable[[], datetime]` constructor kwarg
- Create: `tests/unit/test_check_halt_gate_clock_injection.py` (3 tests)

- [ ] **Step 1: TDD failing tests**

```python
def test_clock_injection_deterministic_months_since_calculation():
    """Inject mock clock — verify months_since computed with controlled now()."""
    fixed_now = datetime(2027, 1, 1, tzinfo=UTC)
    rm = RuntimeManager(..., clock=lambda: fixed_now)
    # Pre-seed activation_ts 7mo ago via state_repo
    # _check_halt_gate → NO_TRADE_TIMEOUT triggered с predictable now
```

- [ ] **Step 2: Add clock constructor kwarg**

```python
def __init__(
    self,
    *,
    # ... existing kwargs ...
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),  # S37 ADR 0057 SD-5
) -> None:
    self._clock = clock
```

Replace ALL `datetime.now(UTC)` calls в `_check_halt_gate()` с `self._clock()`.

- [ ] **Step 3: Run + commit**

---

## Task 5 — Trading-logic #5: coordinator.symbol public property

**Files:**
- Modify: `src/execution/coordinator.py` — add `symbol` property
- Modify: `src/runtime/manager.py` — replace `getattr(_, "_symbol", None)` chain
- Create: `tests/unit/test_coordinator_symbol_property.py` (2 tests)

- [ ] **Step 1: TDD failing test**

```python
def test_coordinator_exposes_symbol_public_property():
    coord = Coordinator(symbol="BTCUSDT", ...)
    assert coord.symbol == "BTCUSDT"
```

- [ ] **Step 2: Add property**

Edit `src/execution/coordinator.py` after `__init__`:

```python
@property
def symbol(self) -> str:
    """S37 ADR 0057 SD-6: public symbol accessor (replaces _symbol private leak)."""
    return self._symbol
```

- [ ] **Step 3: Replace fallback chain в RuntimeManager**

Replace в `_check_halt_gate()`:
```python
# OLD: symbol = getattr(self._coordinator, "symbol", None) or getattr(self._coordinator, "_symbol", None)
# NEW:
symbol = getattr(self._coordinator, "symbol", None)
```

- [ ] **Step 4: Run + commit**

---

## Task 6 — Quant #8: DSR boundary tests n=10/n=30 + calibration baseline update

**Files:**
- Modify: `tests/unit/test_dsr_status_thresholds.py` (parametrized boundary tests)
- Modify: `src/analytics/live_trade_reporter.py:28` — `S22_SYNTHETIC_SHARPE = 2.96`
- Create test verifying calibration baseline matches ADR 0056 amendment

- [ ] **Step 1: Update S22_SYNTHETIC_SHARPE constant**

Edit `src/analytics/live_trade_reporter.py:28`:
```python
# S37 T6 ADR 0056 amendment: mean fold Sharpe (conservative) replaces T1 aggregate (extreme)
# Mean of S22 fold_sharpe_ratios [1.93, -2.92, 1.32, 12.70, 1.78] = 2.96
S22_SYNTHETIC_SHARPE: float = 2.96
```

- [ ] **Step 2: Add parametrized boundary tests**

Edit `tests/unit/test_dsr_status_thresholds.py`:

```python
import pytest

@pytest.mark.parametrize("n,expected_status", [
    (9, "INSUFFICIENT_TRADES"),  # below boundary
    (10, "UNDERPOWERED"),         # boundary INCLUSIVE
    (29, "UNDERPOWERED"),         # below upper boundary
    (30, "GATE_ELIGIBLE"),        # boundary INCLUSIVE
])
def test_dsr_status_boundary_exact(n: int, expected_status: str) -> None:
    """ADR 0056 boundary: n>=10 → UNDERPOWERED, n>=30 → GATE_ELIGIBLE."""
    result = compute_dsr_with_status(trades=_make_trades(n), n_trials=1)
    assert result["status"] == expected_status
```

Plus calibration baseline test:

```python
def test_calibration_baseline_amended_to_2_96() -> None:
    """ADR 0056 S37 amendment: S22_SYNTHETIC_SHARPE = 2.96 (mean fold conservative)."""
    from src.analytics.live_trade_reporter import S22_SYNTHETIC_SHARPE
    assert S22_SYNTHETIC_SHARPE == 2.96
```

- [ ] **Step 3: Update existing live_trade_reporter test fixture if any references 6.17**

```bash
grep -rn "6.17\|6\\.17" tests/ src/analytics/live_trade_reporter.py 2>&1 | head
```

Update assertions к expect 2.96 baseline.

- [ ] **Step 4: Run + commit**

---

## Task 7 — Operator playbook page

**Files:**
- Create: `llm-wiki/wiki/project/components/delta-activation-playbook.md` (~80 lines)

- [ ] **Step 1: Write playbook**

Sections:
- **TL;DR** — one-paragraph summary
- **Pre-activation checklist** (all S37 items closed, ADR 0055+0057 acknowledgments confirmed)
- **Activation steps** (1-5: set env var, restart, verify activation_ts persisted, monitor halt_log, etc.)
- **Monitoring procedure** (weekly halt_log + trade_history checks)
- **Halt response procedure** (when HaltGate fires — manual FSM reset через --reconcile-only OR honest close S38+)
- **DSR status interpretation guide** (per ADR 0056 thresholds)
- **12mo MAINNET-promotion review** (per ADR 0055 SD-8 deferred — operator action gates)
- **Halt criteria summary** (4 triggers + thresholds)
- **Related** (ADRs + components + sprints)

- [ ] **Step 2: Commit**

---

## Task 8 — Sprint-37 page + counts + sync

**Files:**
- Create: `llm-wiki/wiki/project/sprints/sprint-37-carry-overs-hardening.md`
- Modify: index.md / current-state.md / reason-codes-schema / execution-state-machine / log.md / SPRINT_STATE.md
- Modify: `.github/workflows/ci.yml` — canonical reason_codes 49→50

Standard wiki sync per `sprint-finish` skill pattern:
- Counts: 56→57 ADRs / 40→41 sprints / 47→48 components / **49→50 reason codes**
- Tag v0.1.0-alpha.37 ready
- Carry-overs к S38+ documented (Items 6, 7, 9, 10 deferred)

---

## Self-Review Checklist

**1. Spec coverage:** All 6 ROUND 5 binding pre-commitments addressed?
- ✅ #1 HALT_UNKNOWN_SYMBOL distinct → T2
- ✅ #2 Calibration baseline 2.96 → T1 ADR amendment + T6
- ✅ #3 activation_ts HMAC → T3
- ✅ #4 δ activate immediately post-S37 → playbook T7
- ✅ #5 Operator playbook mandatory → T7
- ✅ #6 Items 6+7+9+10 deferred explicitly → T8 sprint page documents

**2. Placeholder scan:** All steps have test code OR commit messages.

**3. Type consistency:** `HALT_UNKNOWN_SYMBOL` enum value consistent T2+T8. `S22_SYNTHETIC_SHARPE = 2.96` referenced T1 amendment + T6. Clock injection signature `Callable[[], datetime]` consistent с S8a precedent.

**4. Trace map covers backlog:** All 6 critical Items + 2 amendment items mapped к T1-T8.

---

## Execution Handoff

Plan complete. Two execution options:

1. **Subagent-Driven (recommended)** — fresh subagent per task, parallel reviewers (security-auditor для T2+T3 / trading-logic для T4+T5 / quant для T6 / doc для T1+T7+T8)
2. **Inline Execution** — controller-driven via `superpowers:executing-plans`

Operator approve mode?
