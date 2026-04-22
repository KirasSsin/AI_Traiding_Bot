---
title: Sprint 4 — Risk & Circuit Breakers — Tasks 14-17
type: plan-part
tags: [plan, sprint-4, risk, kelly, circuit-breakers, tdd]
created: 2026-04-23
updated: 2026-04-23
status: ready-to-execute
part: 3 of 3
parent: 2026-04-23-sprint-4-risk.md
sources:
  - project/architecture/migration-plan.md §S4
  - project/decisions/0012-4-phase-kelly-sizing.md
  - project/decisions/0013-circuit-breakers-l1-l2-l3-flash.md
  - trading/concepts/kelly-phases.md
  - trading/concepts/circuit-breakers.md
---

# Sprint 4 — Tasks 14-17

> **Index:** [2026-04-23-sprint-4-risk.md](2026-04-23-sprint-4-risk.md)

---

### Task 14: Legacy cleanup — remove `src/risk/risk_manager.py`

**Files:**
- Remove: `src/risk/risk_manager.py`
- Modify: `src/risk/__init__.py`

- [ ] **Step 1: Verify no living code imports legacy risk_manager**

```bash
grep -r "from src.risk.risk_manager" src/ tests/ --include="*.py"
grep -r "from src.core.math_engine" src/ tests/ --include="*.py"
```
Expected: empty output. If not empty → fix imports first.

- [ ] **Step 2: Verify `src.core.math_engine` import check**

```bash
grep -r "math_engine" src/ tests/ --include="*.py"
```
Expected: empty output (legacy module used by old risk_manager only).

- [ ] **Step 3: Remove legacy files**

```bash
git rm src/risk/risk_manager.py
```
If `src/core/math_engine.py` exists and has no other importers:
```bash
git rm src/core/math_engine.py
```

- [ ] **Step 4: Update `src/risk/__init__.py`**

Replace contents of `src/risk/__init__.py` with clean re-exports:

```python
"""Risk management context — S4 public API.

Public exports:
    RiskManager    — orchestrator (src.risk.manager)
    RiskAssessment — frozen output value object (src.risk.models)
    HaltState      — circuit breaker state enum (src.risk.models)
    ReasonCode     — 28 canonical audit reason codes (src.risk.reason_codes)
"""

from src.risk.manager import RiskManager
from src.risk.models import HaltState, RiskAssessment
from src.risk.reason_codes import ReasonCode

__all__ = ["RiskManager", "RiskAssessment", "HaltState", "ReasonCode"]
```

- [ ] **Step 5: Run full test suite**

```bash
pytest tests/ -v --tb=short
```
Expected: all tests pass; no import errors from removed legacy modules.

- [ ] **Step 6: Verify grep is clean**

```bash
grep -r "risk_manager" src/ tests/ --include="*.py" | grep -v "__pycache__"
```
Expected: empty output.

- [ ] **Step 7: Commit**

```bash
git add src/risk/__init__.py
git commit -m "feat(risk): remove legacy risk_manager.py + update __init__.py re-exports

Legacy src/risk/risk_manager.py and src/core/math_engine.py removed.
src/risk/__init__.py now exports S4 public API: RiskManager, RiskAssessment,
HaltState, ReasonCode. No from src.core.math_engine imports remain.
Source: wiki/project/plans/2026-04-23-sprint-4-risk.md §Task-14"
```

---

### Task 15: Integration test — `tests/integration/test_risk_flow.py`

**Files:**
- Create: `tests/integration/test_risk_flow.py`

**Scenario:** 50-bar synthetic flow; 5 closed trades recorded; Kelly transitions; CB triggers; override resume.

- [ ] **Step 1: RED — write integration test**

Create `tests/integration/test_risk_flow.py`:

```python
"""Integration test: 50-bar synthetic risk flow.

Covers: equity snapshots, 5 trade records, Kelly phase transition,
L1 CB trigger, L2 CB trigger, override resume, flash detection.
"""

import sqlite3
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from src.platform.config import Settings
from src.platform.db import connect, init_db
from src.risk.manager import RiskManager
from src.risk.models import HaltState
from src.risk.override import OverrideStore
from src.risk.reason_codes import ReasonCode
from src.risk.trade_history import TradeHistoryRepository, TradeRecord
from src.signalgen.models import Signal, SignalSide

MIGRATIONS_DIR = Path(__file__).parents[2] / "migrations"
BASE_TS = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


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
def db(settings: Settings) -> sqlite3.Connection:
    init_db(settings.db_path, MIGRATIONS_DIR)
    return connect(settings.db_path)


@pytest.fixture()
def manager(settings: Settings, db: sqlite3.Connection) -> RiskManager:
    return RiskManager(
        settings=settings,
        conn=db,
        clock=lambda: BASE_TS,
    )


def _make_signal(ts: datetime, atr: Decimal = Decimal("500")) -> Signal:
    return Signal(
        signal_id=uuid4(),
        symbol="BTCUSDT",
        side=SignalSide.LONG,
        bar_close_time=ts,
        generated_at=ts,
        ema_fast=Decimal("50100"),
        ema_slow=Decimal("50000"),
        adx_14=Decimal("30"),
        plus_di_14=Decimal("28"),
        minus_di_14=Decimal("18"),
        rsi_14=Decimal("45"),
        atr_14=atr,
        reason="EMA cross confirmed",
    )


def _insert_trades(
    repo: TradeHistoryRepository,
    n: int,
    win_rate: float = 0.6,
    kelly_phase: int = 1,
) -> None:
    for i in range(n):
        pnl = Decimal("50") if i / n < win_rate else Decimal("-30")
        repo.insert(
            TradeRecord(
                symbol="BTCUSDT",
                entry_signal_id=str(uuid4()),
                entry_ts=BASE_TS + timedelta(hours=i),
                exit_ts=BASE_TS + timedelta(hours=i + 1),
                qty=Decimal("0.001"),
                entry_price=Decimal("50000"),
                exit_price=Decimal("51000") if pnl > 0 else Decimal("49000"),
                pnl_quote=pnl,
                pnl_pct=pnl / Decimal("50000"),
                fees_paid=Decimal("0.1"),
                reason_code=ReasonCode.EXIT_TP_HIT if pnl > 0 else ReasonCode.EXIT_SL_HIT,
                kelly_phase=kelly_phase,
            )
        )


class TestSyntheticFlow:
    """50-bar synthetic risk flow integration test."""

    def test_initial_phase_is_1(self, manager: RiskManager, db: sqlite3.Connection) -> None:
        """With 0 trades, Kelly phase must be 1 (fixed 1%)."""
        ts = BASE_TS
        manager.update_equity(realized=Decimal("10000"), unrealized=Decimal("0"), ts=ts)
        signal = _make_signal(ts)
        result = manager.assess(signal, mark_price=Decimal("50000"))
        assert result.kelly_phase == 1
        assert result.kelly_fraction == Decimal("0.01")

    def test_5_trades_recorded_count(self, manager: RiskManager, db: sqlite3.Connection) -> None:
        """5 closed trades persisted correctly."""
        repo = TradeHistoryRepository(db)
        _insert_trades(repo, n=5, kelly_phase=1)
        assert repo.count() == 5

    def test_kelly_phase_transition_at_30_trades(
        self, manager: RiskManager, db: sqlite3.Connection
    ) -> None:
        """After 30 trades, phase transitions from 1 → 2."""
        repo = TradeHistoryRepository(db)
        ts = BASE_TS
        manager.update_equity(realized=Decimal("10000"), unrealized=Decimal("0"), ts=ts)
        _insert_trades(repo, n=29, kelly_phase=1)
        signal_29 = _make_signal(ts)
        r29 = manager.assess(signal_29, mark_price=Decimal("50000"))
        assert r29.kelly_phase == 1

        _insert_trades(repo, n=1, kelly_phase=1)  # trade #30
        signal_30 = _make_signal(ts)
        r30 = manager.assess(signal_30, mark_price=Decimal("50000"))
        assert r30.kelly_phase == 2

    def test_l1_cb_triggers_at_15_pct_dd(
        self, manager: RiskManager, db: sqlite3.Connection
    ) -> None:
        """L1 triggers when drawdown reaches 15.1%."""
        peak_ts = BASE_TS
        manager.update_equity(realized=Decimal("10000"), unrealized=Decimal("0"), ts=peak_ts)
        # 15.1% drawdown: 10000 * (1 - 0.151) = 8490
        dd_ts = BASE_TS + timedelta(hours=1)
        manager.update_equity(realized=Decimal("8490"), unrealized=Decimal("0"), ts=dd_ts)
        state = manager._state_repo.get("risk:cb:current_level")
        assert state is not None
        assert state["level"] == "L1"

    def test_l2_cb_triggers_at_22_pct_dd(
        self, manager: RiskManager, db: sqlite3.Connection
    ) -> None:
        """L2 triggers when drawdown reaches 22.1%."""
        peak_ts = BASE_TS
        manager.update_equity(realized=Decimal("10000"), unrealized=Decimal("0"), ts=peak_ts)
        dd_ts = BASE_TS + timedelta(hours=1)
        manager.update_equity(realized=Decimal("7790"), unrealized=Decimal("0"), ts=dd_ts)
        state = manager._state_repo.get("risk:cb:current_level")
        assert state["level"] == "L2"

    def test_l2_rejects_new_signals(self, manager: RiskManager, db: sqlite3.Connection) -> None:
        """After L2, all new signals are rejected."""
        ts = BASE_TS
        manager.update_equity(realized=Decimal("10000"), unrealized=Decimal("0"), ts=ts)
        manager._state_repo.set(
            "risk:cb:current_level",
            {"level": "L2", "triggered_at": ts.isoformat(), "peak_equity": "10000", "dd_pct": "0.221"},
        )
        signal = _make_signal(ts)
        result = manager.assess(signal, mark_price=Decimal("50000"))
        assert result.approved is False
        assert result.reason_code == ReasonCode.HALT_DRAWDOWN_L2

    def test_override_resume_flow(self, settings: Settings, db: sqlite3.Connection) -> None:
        """Full override write → read → consume flow."""
        clock = lambda: datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        store = OverrideStore(override_path=settings.risk_override_path)
        config_hash = settings.config_hash()

        store.write(level=HaltState.L2, reason="Post-reconciliation", config_hash=config_hash, clock=clock)
        override = store.read(config_hash=config_hash, clock=clock)
        assert override["level"] == "L2"

        consumed = store.consume(config_hash=config_hash, clock=clock)
        assert consumed["level"] == "L2"
        assert not settings.risk_override_path.exists()

    def test_flash_cb_detected_on_bar(self, manager: RiskManager) -> None:
        """Flash CB: 10% single-bar move with tiny ATR."""
        from src.risk.circuit_breakers import CircuitBreakerDetector
        detector = CircuitBreakerDetector(settings=manager._settings)
        result = detector.check_flash(
            bar_close=Decimal("45000"),
            prev_close=Decimal("50000"),
            atr=Decimal("100"),
        )
        assert result is True

    def test_sl_tp_prices_correct(self, manager: RiskManager) -> None:
        """SL = mark - 1.5*ATR; TP = mark + 3.0*ATR."""
        ts = BASE_TS
        manager.update_equity(realized=Decimal("10000"), unrealized=Decimal("0"), ts=ts)
        signal = _make_signal(ts, atr=Decimal("500"))
        mark = Decimal("50000")
        result = manager.assess(signal, mark_price=mark)
        if result.approved:
            assert result.sl_price == mark - Decimal("1.5") * Decimal("500")
            assert result.tp_price == mark + Decimal("3.0") * Decimal("500")

    def test_50_bar_flow_no_crash(self, manager: RiskManager, db: sqlite3.Connection) -> None:
        """50 sequential bars: update_equity + assess — no exceptions."""
        for i in range(50):
            ts = BASE_TS + timedelta(hours=i)
            equity = Decimal("10000") - Decimal("10") * i  # gradual decline
            manager.update_equity(realized=equity, unrealized=Decimal("0"), ts=ts)
            signal = _make_signal(ts)
            _result = manager.assess(signal, mark_price=Decimal("50000"))
        # Should have survived all 50 bars
        row = db.execute("SELECT COUNT(*) FROM equity_snapshots").fetchone()
        assert row[0] >= 50
```

- [ ] **Step 2: Run integration test — verify RED**

```bash
pytest tests/integration/test_risk_flow.py -v
```
Expected: FAIL (manager not yet complete or some methods missing).

- [ ] **Step 3: Fix issues and run GREEN**

```bash
pytest tests/integration/test_risk_flow.py -v
```
Expected: all passed.

- [ ] **Step 4: Run full suite**

```bash
pytest tests/ -v --tb=short
```
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add tests/integration/test_risk_flow.py
git commit -m "test(risk): add 50-bar integration test for full risk flow

Covers: equity snapshots, 5 trade records, Kelly transitions (n=29→30),
CB L1/L2 triggers, override resume, flash detection, SL/TP prices.
Source: wiki/project/plans/2026-04-23-sprint-4-risk.md §Task-15"
```

---

### Task 16: Wiki component pages

**Files:**
- Create: `llm-wiki/wiki/project/components/kelly.md`
- Create: `llm-wiki/wiki/project/components/circuit-breakers.md`
- Create: `llm-wiki/wiki/project/components/sizing.md`
- Create: `llm-wiki/wiki/project/components/risk-manager.md`

- [ ] **Step 1: Create `llm-wiki/wiki/project/components/kelly.md`**

```markdown
---
title: Kelly Calculator — Component
type: component
tags: [risk, kelly, position-sizing, component, v0.1]
created: 2026-04-23
updated: 2026-04-23
status: stable
sources:
  - trading/concepts/kelly-phases.md
  - project/decisions/0012-4-phase-kelly-sizing.md
  - project/plans/2026-04-23-sprint-4-risk.md
---

# Kelly Calculator

**TL;DR:** Stateless calculator implementing 4-phase Kelly fraction with Wilson 95% CI. Phase determined by cumulative trade count.

## Definition / Purpose

`KellyCalculator` в `src/risk/kelly.py` вычисляет Kelly fraction с учётом фазы по числу сделок. Используется `RiskManager` для определения доли equity под риском в каждой сделке.

## Key properties

- **Stateless:** всё состояние (trade_count, p_hat, b) передаётся явно — нет внутреннего состояния.
- **4 фазы:** n<30 → fixed 1%; n<100 → fixed 2%; n<200 → quarter-Kelly, cap 3%; n≥200 → half-Kelly, cap 5%.
- **Wilson 95% CI:** inline formula, z=1.96, без scipy. Результат в Decimal.
- **Clamp:** f* < 0 → returns 0 (не бетим в отрицательный edge).

## API

```python
calc = KellyCalculator()
phase = calc.phase_from_trade_count(trade_count=45)  # → 2
fraction = calc.phase_adjusted_fraction(trade_count=45, p_hat=Decimal("0.55"), b=Decimal("1.5"))  # → 0.02
lo, hi = calc.wilson_95_ci(p_hat=Decimal("0.55"), n=200)  # → (~0.481, ~0.616)
```

## Phase boundaries (tested)

| n | Phase | Cap |
|---|-------|-----|
| 0–29 | 1 | 1% fixed |
| 30–99 | 2 | 2% fixed |
| 100–199 | 3 | quarter-Kelly, cap 3% |
| ≥200 | 4 | half-Kelly, cap 5% |

## Related

- [[../../trading/concepts/kelly-phases]] — доменное знание, формулы, обоснование.
- [[risk-manager]] — оркестратор, использует KellyCalculator.
- [[sizing]] — compute_qty(), использует kelly_fraction output.
- [[../../project/decisions/0012-4-phase-kelly-sizing]] — ADR.

## Sources

- `src/risk/kelly.py`
- `tests/unit/test_kelly.py`
```

- [ ] **Step 2: Create `llm-wiki/wiki/project/components/circuit-breakers.md`**

```markdown
---
title: Circuit Breaker Detector — Component
type: component
tags: [risk, circuit-breaker, drawdown, flash, component, v0.1]
created: 2026-04-23
updated: 2026-04-23
status: stable
sources:
  - trading/concepts/circuit-breakers.md
  - project/decisions/0013-circuit-breakers-l1-l2-l3-flash.md
  - project/plans/2026-04-23-sprint-4-risk.md
---

# Circuit Breaker Detector

**TL;DR:** Pure-function detector for drawdown-based halts (L1/L2/L3) and single-bar flash crash. Stateless — RiskManager owns state persistence.

## Definition / Purpose

`CircuitBreakerDetector` в `src/risk/circuit_breakers.py` — stateless детектор. Принимает текущий equity и peak, возвращает `HaltState`. Flash-детектор использует close-to-close change vs max(8%, 3·ATR/prev).

## Key properties

- **Stateless:** никакого состояния; `RiskManager` персистит результат в `state` table.
- **Drawdown thresholds:** L1=15%, L2=22%, L3=30% (из `Settings`).
- **Flash:** `max(risk_cb_flash_abs, risk_cb_flash_atr_mult * atr / prev_close)`.
- **Escalation only:** `RiskManager._refresh_cb_state()` никогда не де-эскалирует L2/L3 автоматически.
- **L1 action:** de-lever×0.5 (fraction×0.5); still approves signals.
- **L2/L3/FLASH action:** reject all signals.

## API

```python
detector = CircuitBreakerDetector(settings=settings)
state = detector.check_drawdown(peak=Decimal("10000"), current=Decimal("8490"))  # → L1
is_flash = detector.check_flash(bar_close=..., prev_close=..., atr=...)  # → bool
halt = detector.check_flash_state(...)  # → HaltState.FLASH | HaltState.L0
```

## Related

- [[../../trading/concepts/circuit-breakers]] — доменное знание, уровни, обоснование.
- [[risk-manager]] — оркестратор, вызывает detector и персистит state.
- [[../../project/decisions/0013-circuit-breakers-l1-l2-l3-flash]] — ADR.

## Sources

- `src/risk/circuit_breakers.py`
- `tests/unit/test_circuit_breakers.py`
```

- [ ] **Step 3: Create `llm-wiki/wiki/project/components/sizing.md`**

```markdown
---
title: Position Sizing — Component
type: component
tags: [risk, position-sizing, kelly, atr, component, v0.1]
created: 2026-04-23
updated: 2026-04-23
status: stable
sources:
  - trading/concepts/kelly-phases.md
  - project/plans/2026-04-23-sprint-4-risk.md
---

# Position Sizing

**TL;DR:** Pure function `compute_qty()` в `src/risk/sizing.py`. Formula: `qty = (fraction * equity) / (k * atr)`. Truncated to 8 decimal places.

## Definition / Purpose

Реализует позиционный sizing: риск на сделку = `fraction * equity`; расстояние до SL = `k * atr`; qty = риск / расстояние.

## Formula

```
qty = (fraction × equity) / (k × atr)
```

где:
- `fraction` — Kelly phase-adjusted fraction (from `KellyCalculator`).
- `equity` — текущий total equity (realized + unrealized).
- `k` — ATR multiplier для SL distance (default `risk_sl_atr_multiplier = 1.5`).
- `atr` — текущий ATR в quote currency (из Signal.atr_14).

Результат truncated до 8 decimal places (`EIGHT_DPS = Decimal("0.00000001")`).

## Key properties

- **Pure function:** никакого состояния, никакого I/O.
- **Zero guard:** если atr ≤ 0 или fraction ≤ 0 → returns 0.
- **Decimal throughout:** ни одного float в финансовых операциях.
- `price` parameter reserved для lot-size rounding (S5).

## Property tests

- `qty >= 0` для всех положительных входов (hypothesis, 200 examples).
- Risk capital `qty * k * atr ≤ fraction * equity` (с rounding tolerance).

## Related

- [[kelly]] — вычисляет fraction.
- [[risk-manager]] — вызывает compute_qty().
- [[../../trading/concepts/kelly-phases]] — обоснование formula.

## Sources

- `src/risk/sizing.py`
- `tests/unit/test_sizing.py`
```

- [ ] **Step 4: Create `llm-wiki/wiki/project/components/risk-manager.md`**

```markdown
---
title: Risk Manager — Component
type: component
tags: [risk, orchestrator, kelly, circuit-breaker, component, v0.1]
created: 2026-04-23
updated: 2026-04-23
status: stable
sources:
  - project/architecture/migration-plan.md §S4
  - project/plans/2026-04-23-sprint-4-risk.md
  - trading/concepts/kelly-phases.md
  - trading/concepts/circuit-breakers.md
---

# Risk Manager

**TL;DR:** Оркестратор S4. Компонует KellyCalculator + CircuitBreakerDetector + EquityTracker + TradeHistoryRepository + StateRepo. Public API: `update_equity()`, `assess()`, `on_bar_close()`.

## Definition / Purpose

`RiskManager` в `src/risk/manager.py` — единственная точка входа в risk context для внешних вызывающих. Не содержит бизнес-логики — делегирует специализированным компонентам.

## Architecture

```
RiskManager
├── KellyCalculator     (stateless — фракция по фазе)
├── CircuitBreakerDetector (stateless — уровень halt)
├── EquityTracker       (SQLite — snapshots, 24h HWM)
├── TradeHistoryRepository (SQLite — trade_history)
└── StateRepo           (SQLite — state kv: CB level, Kelly phase/params)
```

## Public API

```python
manager = RiskManager(settings=settings, conn=conn, clock=clock)

# Вызывается на каждом PositionClosed event
manager.update_equity(realized=Decimal("10500"), unrealized=Decimal("0"), ts=ts)

# Вызывается на каждом сигнале стратегии
assessment: RiskAssessment = manager.assess(signal, mark_price=Decimal("50000"))

# Вызывается на каждом bar close (BAR_CLOSE snapshot)
manager.on_bar_close(bar)
```

## Key invariants

- **Clock injected:** `clock: Callable[[], datetime]` — нет `datetime.now()` в domain logic.
- **Look-ahead safety:** `assess()` использует только equity snapshots с `ts <= signal.generated_at`.
- **Atomic state:** Kelly phase + equity snapshot + CB level в single `with conn:` block через `StateRepo.update_many()`.
- **CB escalation only:** L2/L3 не де-эскалируются автоматически; только вручную через CLI `python -m src.risk.resume_cb`.
- **L1 de-lever:** fraction × 0.5 при L1; сигнал всё равно одобряется.

## Output — RiskAssessment

Frozen pydantic v2 value object. Carries: `approved`, `qty`, `sl_price`, `tp_price`, `kelly_phase`, `kelly_fraction`, `halt_state`, `reason_code`, `assessed_at`.

## State keys (в SQLite `state` table)

| Key | Value |
|-----|-------|
| `risk:cb:current_level` | `{level, triggered_at, peak_equity, dd_pct}` |
| `risk:kelly:phase` | `{phase, trade_count, updated_at}` |
| `risk:kelly:params` | `{p_hat, b, computed_at}` |

## Manual resume flow

```bash
python -m src.risk.resume_cb --level L2 --reason "Post-reconciliation" --expires-in 1h
```
Writes `state/cb_override.json` with `config_hash` binding. Override consumed by `OverrideStore.consume()` → renamed to `.consumed.json`.

## Related

- [[kelly]] — Kelly fraction computation.
- [[circuit-breakers]] — CB detection logic.
- [[sizing]] — qty computation.
- [[../../trading/concepts/kelly-phases]] — phase rules.
- [[../../trading/concepts/circuit-breakers]] — CB thresholds.
- [[../../trading/concepts/reason-codes]] — ReasonCode enum.

## Open questions

- Regime shift KS-test downgrade (Phase 1 revert) — deferred to S7.
- Async `on_bar_close` integration with Event Bus — deferred to S6.

## Sources

- `src/risk/manager.py`
- `tests/unit/test_risk_manager.py`
- `tests/integration/test_risk_flow.py`
```

- [ ] **Step 5: Commit**

```bash
git add llm-wiki/wiki/project/components/kelly.md \
        llm-wiki/wiki/project/components/circuit-breakers.md \
        llm-wiki/wiki/project/components/sizing.md \
        llm-wiki/wiki/project/components/risk-manager.md
git commit -m "docs(wiki): add S4 component pages (kelly, circuit-breakers, sizing, risk-manager)

Component docs per llm-wiki/CLAUDE.md skeleton format.
Source: wiki/project/plans/2026-04-23-sprint-4-risk.md §Task-16"
```

---

### Task 17: Sprint delivery record + wiki updates

**Files:**
- Create: `llm-wiki/wiki/project/sprints/sprint-04-risk.md`
- Modify: `llm-wiki/wiki/index.md`
- Modify: `llm-wiki/wiki/log.md`

- [ ] **Step 1: Create sprint delivery record**

Create `llm-wiki/wiki/project/sprints/sprint-04-risk.md`:

```markdown
---
title: Sprint 4 — Risk & Circuit Breakers (delivery record)
type: summary
tags: [sprint-4, risk, kelly, circuit-breakers, delivery]
created: 2026-04-23
updated: 2026-04-23
status: stable
---

# Sprint 4 — Risk & Circuit Breakers

**Delivered:** 2026-04-23
**Branch:** feature/sprint-4-risk
**Tag:** v0.1.0-alpha.4 (after merge)

## Goal (achieved)

4-phase Kelly position sizing + L1/L2/L3/flash circuit breakers + drawdown monitoring. Legacy `src/risk/risk_manager.py` removed.

## Artifacts

| File | Purpose |
|------|---------|
| `migrations/002_risk.sql` | trade_history + equity_snapshots tables |
| `src/risk/reason_codes.py` | ReasonCode StrEnum (28 canonical codes) |
| `src/risk/models.py` | HaltState + RiskAssessment |
| `src/risk/sizing.py` | compute_qty() pure function |
| `src/risk/kelly.py` | KellyCalculator (4-phase + Wilson CI) |
| `src/risk/trade_history.py` | TradeHistoryRepository + TradeRecord |
| `src/risk/equity_tracker.py` | EquityTracker (24h HWM) |
| `src/risk/circuit_breakers.py` | CircuitBreakerDetector |
| `src/risk/override.py` | OverrideStore (cb_override.json) |
| `src/risk/state_repo.py` | StateRepo JSON kv adapter |
| `src/risk/manager.py` | RiskManager orchestrator |
| `src/risk/resume_cb.py` | CLI for manual CB resume |
| `src/platform/config.py` | +13 risk settings + config_hash() |
| `tests/integration/test_risk_flow.py` | 50-bar synthetic integration test |

## AC Verification

- [x] Kelly transitions n=29→30, 99→100, 199→200 — `test_kelly.py`.
- [x] CB L1/L2/L3 trigger on DD 15.1%/22.1%/30.1% — `test_circuit_breakers.py` + `test_risk_flow.py`.
- [x] Flash CB: single-bar return > max(8%, 3·ATR) → HALT_FLASH_CRASH — `test_circuit_breakers.py`.
- [x] Manual resume via override file + config_hash binding — `test_override.py` + `test_risk_flow.py`.
- [x] Property test: sizing never exceeds phase cap — `test_sizing.py` hypothesis.
- [x] No datetime.now() in domain logic — clock injected everywhere.
- [x] Legacy risk_manager.py removed — Task 14.

## Decisions

- D1: ReasonCode uses canonical 28-enum names (HALT_DRAWDOWN_L1, not RISK_REJECT_HALT_L1).
- D2: No APPROVED reason code — entry signals pass through ENTRY_LONG_TREND_FOLLOWING.
- D3: Wilson CI inline (z=1.96 float), no scipy dependency.
- D4: Bar protocol duck-typed (close, high, low, ts, atr_14 attributes).

## Follow-ups (ADR amendments required)

- FA-1: ADR amendment needed if canonical reason codes for risk rejections should use RISK_REJECT_* namespace (currently HALT_* and REJECT_* per 28-enum).
- FA-2: Regime shift KS-test downgrade → Phase 1 revert (deferred S7).
- FA-3: async on_bar_close + Event Bus integration (deferred S6).

## Related

- [[../plans/2026-04-23-sprint-4-risk]] — implementation plan.
- [[../components/risk-manager]] — component doc.
- [[../components/kelly]] — Kelly component doc.
- [[../components/circuit-breakers]] — CB component doc.
- [[../components/sizing]] — sizing component doc.
```

- [ ] **Step 2: Update `llm-wiki/wiki/index.md`**

Add to "Project — Components" section:
```markdown
- [[project/components/kelly]] — KellyCalculator: 4-фазный Kelly с Wilson 95% CI (Sprint 4).
- [[project/components/circuit-breakers]] — CircuitBreakerDetector: L1/L2/L3/flash halt logic (Sprint 4).
- [[project/components/sizing]] — compute_qty(): ATR-based position sizing (Sprint 4).
- [[project/components/risk-manager]] — RiskManager: S4 оркестратор risk context (Sprint 4).
```

Add to "Project — Plans" section:
```markdown
- [[project/plans/2026-04-23-sprint-4-risk]] — Sprint 4 implementation plan: Risk & Circuit Breakers.
```

Add to "Project — Sprints" section (create if not exists):
```markdown
- [[project/sprints/sprint-04-risk]] — Sprint 4 delivery record: Risk & Circuit Breakers.
```

- [ ] **Step 3: Append to `llm-wiki/wiki/log.md`**

```markdown
## [2026-04-23] ingest | Sprint 4 — Risk & Circuit Breakers completed
- Added: wiki/project/plans/2026-04-23-sprint-4-risk.md
- Added: wiki/project/sprints/sprint-04-risk.md
- Added: wiki/project/components/kelly.md
- Added: wiki/project/components/circuit-breakers.md
- Added: wiki/project/components/sizing.md
- Added: wiki/project/components/risk-manager.md
- Updated: wiki/index.md (new component pages + sprint + plan)
- Updated: src/platform/config.py (13 risk fields + config_hash)
- Updated: src/risk/__init__.py (clean re-exports, legacy removed)
- Removed: src/risk/risk_manager.py (replaced by src/risk/manager.py)
- Notes: 4-phase Kelly + L1/L2/L3/flash CB + OverrideStore implemented.
  Reason codes use canonical 28-enum (see Follow-up FA-1 re: RISK_REJECT_* namespace).
```

- [ ] **Step 4: Commit**

```bash
git add llm-wiki/wiki/project/sprints/sprint-04-risk.md \
        llm-wiki/wiki/index.md \
        llm-wiki/wiki/log.md
git commit -m "docs(wiki): Sprint 4 delivery record + index + log update

sprint-04-risk.md delivery record; component pages linked in index.md;
log.md entry appended. Canonical 28 reason codes deviation noted.
Source: wiki/project/plans/2026-04-23-sprint-4-risk.md §Task-17"
```

---

← Back: [Tasks 9-13](2026-04-23-sprint-4-risk-tasks-9-13.md) | [Index](2026-04-23-sprint-4-risk.md)
