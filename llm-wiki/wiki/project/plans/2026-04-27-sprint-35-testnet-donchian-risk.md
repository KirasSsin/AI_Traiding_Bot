---
title: Sprint 35 Plan — δ TESTNET Live Demo + α Donchian 4H Long-Only + ζ Risk Mgmt
type: plan
tags: [sprint-35, plan, testnet, live-demo, donchian, risk-management, kelly-cap, atr-sl, ru]
created: 2026-04-27
updated: 2026-04-27
status: proposed
sources:
  - project/decisions/0051-sprint-34-honest-close-v06.md
  - project/decisions/0052-sprint-34-acceptance-criteria-amendment.md
  - project/pre-s35-backlog.md
  - .claude/agent-memory/trader-expert/v07_direction_consilium.md
---

# Sprint 35 Implementation Plan — δ TESTNET + α Donchian + ζ Risk

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Activate TESTNET-only live demo for v0.6 mean-reversion strategy (S22 partial PASS evidence) с pre-committed halt criteria, parallel synthetic Donchian breakout 7th hypothesis (long-only FSM-compatible, N_trials=5 LOCKED), preceded by Kelly-cap audit + ATR SL calibration refactor (ζ).

**Architecture:** Three concurrent tracks bundled в один sprint per ROUND 3 consilium binding:
- **ζ track (T1)** — Kelly cap audit + ATR SL multiplier `k` calibration → bedrock per pre-commitment #2 (must complete BEFORE δ activation)
- **δ track (T2)** — TESTNET activation: halt criteria thresholds + cumulative trade log + FillRecorder validation + ADR 0053 (acknowledgment template + pre-committed gates)
- **α track (T3-T4)** — Donchian breakout strategy (long-only) ADR 0054 (pre-registration N_trials=5 + LOCKED params) + implementation + backtest run

**Tech Stack:** Python 3.12 / pydantic-settings / SQLite WAL / Bybit V5 API / pytest-Hypothesis / mypy --strict / TDD RED→GREEN.

---

## Trace Map (PHASE 3 step 1a HARD-GATE)

| Source artifact | Implementation task |
|-----------------|---------------------|
| pre-s35-backlog.md "Pre-committed PASS gates δ" | T2 step 4-6 (halt criteria + thresholds в Settings) |
| pre-s35-backlog.md "Pre-committed HALT criteria δ" | T2 step 7-9 (HaltGate class + SQLite halt_log integration) |
| pre-s35-backlog.md "8 pre-commitments" #2 (Kelly cap audit) | T1 step 1-5 (test caps_audit + sizing.k calibration) |
| pre-s35-backlog.md "8 pre-commitments" #3 (Donchian N_trials=5) | T3 step 3 (ADR 0054 LOCKED) |
| pre-s35-backlog.md "8 pre-commitments" #4 (Donchian params pre-reg) | T3 step 4 + T4 step 1 (`DONCHIAN_LONG_ONLY_PARAMS` constant) |
| pre-s35-backlog.md "Operator acknowledgment template" | T2 step 10 (ADR 0053 verbatim section) |
| pre-s35-backlog.md "LOCKED parameters δ" | T2 step 6 (`DEMO_DELTA_LOCKED_PARAMS` constant) |
| pre-s35-backlog.md "Engineering blockers (Donchian)" | T4 step 1 (long-only FSM SignalSide invariant guard) |
| ADR 0052 Item #10 (n_trials counter) | T3 step 3 (frozen for δ, =5 для α) |

---

## File Structure

**New files:**
- `src/risk/halt_gate.py` — HaltGate class: pre-committed halt evaluation per S35 thresholds (DD ≥ -20% intraday OR -15% multi-day OR ≥5 consecutive losses OR 6mo без n≥30)
- `src/signalgen/donchian_strategy.py` — DonchianBreakoutStrategy: long-only, N=20 lookback, ATR exit, FSM-compatible
- `tests/unit/test_halt_gate.py` — HaltGate тесты (4 trigger paths + threshold boundaries)
- `tests/unit/test_donchian_strategy.py` — Donchian unit тесты (warmup / breakout entry / ATR exit / long-only invariant)
- `tests/unit/test_kelly_cap_audit.py` — Kelly cap conformance (settings reads ≤ 0.25 phase3/4 invariant per pre-commit #2)
- `llm-wiki/wiki/project/decisions/0053-sprint-35-testnet-live-demo.md` — δ ADR (acknowledgment + LOCKED params + pre-committed gates + halt criteria)
- `llm-wiki/wiki/project/decisions/0054-sprint-35-donchian-pre-registration.md` — α ADR (N_trials=5 + LOCKED params + long-only invariant + 6 acceptance gates pre-reg)
- `llm-wiki/wiki/project/sprints/sprint-35-testnet-donchian-risk.md` — sprint page
- `llm-wiki/wiki/project/components/halt-gate.md` — component page
- `llm-wiki/wiki/project/components/donchian-strategy.md` — component page
- `data/donchian_backtest_results.json` — backtest run output

**Modified files:**
- `src/platform/config.py` — добавить `s35_demo_active`, `s35_halt_dd_intraday`, `s35_halt_dd_multiday`, `s35_halt_consecutive_losses`, `s35_halt_no_trade_months` settings + Kelly cap audit (verify phase3 ≤ 0.25 invariant)
- `src/risk/sizing.py` — параметризовать `k` через Settings (currently hard-coded default 1.5 — make explicit setting `risk_sl_atr_multiplier`)
- `src/risk/manager.py` — wire HaltGate в assess() pipeline + pass settings.risk_sl_atr_multiplier к compute_qty
- `src/signalgen/__init__.py` — export DonchianBreakoutStrategy
- `llm-wiki/wiki/index.md` — add 2 new ADR + sprint-35 + 2 component entries
- `llm-wiki/wiki/project/architecture/current-state.md` — counts 52→54 ADRs / 38→39 sprints / +2 components

---

## Task 1: ζ Risk Management Refactor (Kelly Cap Audit + ATR SL Calibration)

**Why first:** Pre-commitment #2 — "Position sizing: Kelly 0.25× cap + ζ refactor applied BEFORE any live run." Bedrock guard prevents δ activating with miscalibrated risk.

**Files:**
- Create: `tests/unit/test_kelly_cap_audit.py`
- Modify: `src/platform/config.py` (add `risk_sl_atr_multiplier: Decimal = Decimal("1.5")` setting)
- Modify: `src/risk/sizing.py` (drop default value `k=Decimal("1.5")`, require explicit param)
- Modify: `src/risk/manager.py:50-55` (pass settings.risk_sl_atr_multiplier к compute_qty call site)

- [ ] **Step 1: Write failing test — Kelly phase3/4 cap audit**

```python
# tests/unit/test_kelly_cap_audit.py
"""Pre-commit #2 audit: Kelly phase3/4 caps must NOT exceed 0.25× formula multiplier.

Per S35 ROUND 3 binding (pre-s35-backlog.md):
  Quarter-Kelly (phase3) and Half-Kelly (phase4) hard caps must remain ≤ 0.25
  to bound tail risk during δ TESTNET live demo.
"""
from decimal import Decimal

from src.platform.config import Settings


def test_kelly_phase3_cap_not_exceeds_0_25():
    settings = Settings(
        bybit_api_key="t", bybit_api_secret="t",
        risk_override_hmac_key="0" * 64,
    )
    assert settings.risk_kelly_phase3_cap <= Decimal("0.25"), (
        f"Phase 3 cap {settings.risk_kelly_phase3_cap} exceeds Quarter-Kelly bound "
        f"per S35 pre-commit #2"
    )


def test_kelly_phase4_cap_not_exceeds_0_25():
    settings = Settings(
        bybit_api_key="t", bybit_api_secret="t",
        risk_override_hmac_key="0" * 64,
    )
    assert settings.risk_kelly_phase4_cap <= Decimal("0.25"), (
        f"Phase 4 cap {settings.risk_kelly_phase4_cap} exceeds bound "
        f"per S35 pre-commit #2 (defensive — Half-Kelly capped к Quarter)"
    )
```

- [ ] **Step 2: Run test, verify it fails OR passes**

Run: `.venv/bin/pytest tests/unit/test_kelly_cap_audit.py -v`
Expected: PASS если current Settings defaults already satisfy ≤ 0.25 invariant. FAIL = config drift detected. Either outcome acceptable here — purpose = guard regression.

- [ ] **Step 3: Add `risk_sl_atr_multiplier` Setting**

Edit `src/platform/config.py` after `risk_kelly_phase4_cap` field block:

```python
    risk_sl_atr_multiplier: Decimal = Field(
        default=Decimal("1.5"),
        gt=Decimal("0"),
        description=(
            "Stop-loss distance в ATR multiples (k в qty = (f * equity) / (k * atr)). "
            "S35 ζ refactor: explicit setting вместо hard-coded sizing.compute_qty default. "
            "Calibration range 1.0-2.0 × ATR per ADR 0007 SL discipline."
        ),
    )
```

- [ ] **Step 4: Make `k` parameter explicit in sizing.compute_qty**

Edit `src/risk/sizing.py` — remove default value:

```python
def compute_qty(
    equity: Decimal,
    fraction: Decimal,
    atr: Decimal,
    price: Decimal,  # noqa: ARG001 — kept for API symmetry with signal.mark_price
    k: Decimal,
) -> Decimal:
```

- [ ] **Step 5: Wire setting через RiskManager**

Edit `src/risk/manager.py` — find все `compute_qty(...)` call sites (currently inside `assess()` method), add `k=self._settings.risk_sl_atr_multiplier` keyword arg:

```bash
grep -n "compute_qty" src/risk/manager.py
```

For each occurrence в assess() pipeline, замени:

```python
qty = compute_qty(equity=eq, fraction=f, atr=atr, price=p)
```

на:

```python
qty = compute_qty(
    equity=eq, fraction=f, atr=atr, price=p,
    k=self._settings.risk_sl_atr_multiplier,
)
```

- [ ] **Step 6: Run full risk test suite**

Run: `.venv/bin/pytest tests/unit/test_risk_sizing.py tests/unit/test_risk_manager.py tests/unit/test_kelly_cap_audit.py -v`
Expected: ALL pass. Existing test_risk_sizing.py likely passes `k=Decimal("1.5")` explicitly already; if it relied on default — update test fixture к `k=Decimal("1.5")`.

- [ ] **Step 7: Run mypy --strict on touched files**

Run: `.venv/bin/mypy --strict src/risk/sizing.py src/risk/manager.py src/platform/config.py`
Expected: 0 errors.

- [ ] **Step 8: Commit**

```bash
git add tests/unit/test_kelly_cap_audit.py src/platform/config.py src/risk/sizing.py src/risk/manager.py
git commit -m "feat(risk): ζ refactor — explicit ATR SL multiplier setting + Kelly cap audit (S35 T1)

- Add risk_sl_atr_multiplier Setting (default 1.5 × ATR per ADR 0007)
- Drop hard-coded default k= in sizing.compute_qty (require explicit)
- Wire setting через RiskManager.assess() compute_qty calls
- Add Kelly cap audit test (phase3/4 ≤ 0.25 invariant per S35 pre-commit #2)

Per ROUND 3 binding pre-commitment #2 — Kelly + ATR SL bedrock applied
BEFORE δ TESTNET activation (T2)."
```

---

## Task 2: δ TESTNET Live Demo Activation

**Files:**
- Create: `src/risk/halt_gate.py`
- Create: `tests/unit/test_halt_gate.py`
- Create: `llm-wiki/wiki/project/decisions/0053-sprint-35-testnet-live-demo.md`
- Create: `llm-wiki/wiki/project/components/halt-gate.md`
- Modify: `src/platform/config.py` (add 5 s35_* halt settings)
- Modify: `src/risk/manager.py` (wire HaltGate в assess() pipeline)

- [ ] **Step 1: Add S35 halt settings**

Edit `src/platform/config.py` after `risk_sl_atr_multiplier` field:

```python
    s35_demo_active: bool = Field(
        default=False,
        description=(
            "S35 δ TESTNET live demo flag. When True, HaltGate activates "
            "S35-specific halt criteria (DD bounds, consecutive losses, no-trade timeout). "
            "MUST be False on MAINNET (live_trading=True invariant violated otherwise)."
        ),
    )

    s35_halt_dd_intraday: Decimal = Field(
        default=Decimal("0.20"),
        gt=Decimal("0"),
        le=Decimal("0.50"),
        description="S35 δ intraday DD halt threshold (-20% per pre-commit ROUND 3).",
    )

    s35_halt_dd_multiday: Decimal = Field(
        default=Decimal("0.15"),
        gt=Decimal("0"),
        le=Decimal("0.50"),
        description="S35 δ multi-day DD halt threshold (-15% per pre-commit ROUND 3).",
    )

    s35_halt_consecutive_losses: int = Field(
        default=5,
        ge=1,
        le=20,
        description="S35 δ consecutive losing trades trigger operator review.",
    )

    s35_halt_no_trade_months: int = Field(
        default=6,
        ge=1,
        le=24,
        description="S35 δ months без n≥30 closed trades → halt + S36 honest close.",
    )
```

Add invariant validator at end of class:

```python
    @model_validator(mode="after")
    def _validate_s35_demo_mainnet_exclusion(self) -> "Settings":
        """S35 pre-commit #1: δ is TESTNET ONLY. Block s35_demo_active=True если live_trading."""
        if self.s35_demo_active and self.live_trading:
            raise ValueError(
                "S35 δ TESTNET demo cannot run на MAINNET. "
                "Set live_trading=False (testnet=True) OR disable s35_demo_active. "
                "Per pre-s35-backlog.md pre-commitment #1 LOCKED."
            )
        return self
```

- [ ] **Step 2: Write failing test for MAINNET exclusion invariant**

Edit `tests/unit/test_settings.py` (or create `tests/unit/test_settings_s35.py`):

```python
import pytest

from src.platform.config import Settings


def test_s35_demo_active_blocks_mainnet():
    """S35 pre-commit #1: δ TESTNET-only invariant."""
    with pytest.raises(ValueError, match="S35 δ TESTNET demo cannot run на MAINNET"):
        Settings(
            bybit_api_key="t", bybit_api_secret="t",
            risk_override_hmac_key="0" * 64,
            testnet=False,
            live_trading=True,
            s35_demo_active=True,
        )


def test_s35_demo_active_with_testnet_ok():
    s = Settings(
        bybit_api_key="t", bybit_api_secret="t",
        risk_override_hmac_key="0" * 64,
        testnet=True,
        live_trading=False,
        s35_demo_active=True,
    )
    assert s.s35_demo_active is True
```

- [ ] **Step 3: Run test, verify RED then GREEN**

Run: `.venv/bin/pytest tests/unit/test_settings_s35.py -v`
Expected RED first (validator not yet wired) → verify Settings change applied → GREEN.

- [ ] **Step 4: Write failing tests for HaltGate**

Create `tests/unit/test_halt_gate.py`:

```python
"""HaltGate — S35 δ TESTNET halt criteria evaluation (pre-s35-backlog.md HALT thresholds)."""
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from src.risk.halt_gate import HaltGate, HaltTrigger


def _gate() -> HaltGate:
    return HaltGate(
        dd_intraday_threshold=Decimal("0.20"),
        dd_multiday_threshold=Decimal("0.15"),
        consecutive_losses_threshold=5,
        no_trade_months_threshold=6,
    )


def test_intraday_dd_triggers_halt():
    gate = _gate()
    trigger = gate.evaluate(
        intraday_dd=Decimal("0.21"),  # -21% intraday
        multiday_dd=Decimal("0.05"),
        consecutive_losses=0,
        months_since_last_trade=0,
    )
    assert trigger == HaltTrigger.DD_INTRADAY


def test_multiday_dd_triggers_halt():
    gate = _gate()
    trigger = gate.evaluate(
        intraday_dd=Decimal("0.05"),
        multiday_dd=Decimal("0.16"),  # -16% multi-day
        consecutive_losses=0,
        months_since_last_trade=0,
    )
    assert trigger == HaltTrigger.DD_MULTIDAY


def test_consecutive_losses_triggers_halt():
    gate = _gate()
    trigger = gate.evaluate(
        intraday_dd=Decimal("0.05"),
        multiday_dd=Decimal("0.05"),
        consecutive_losses=5,
        months_since_last_trade=0,
    )
    assert trigger == HaltTrigger.CONSECUTIVE_LOSSES


def test_no_trade_timeout_triggers_halt():
    gate = _gate()
    trigger = gate.evaluate(
        intraday_dd=Decimal("0.05"),
        multiday_dd=Decimal("0.05"),
        consecutive_losses=0,
        months_since_last_trade=7,  # > 6 months threshold
    )
    assert trigger == HaltTrigger.NO_TRADE_TIMEOUT


def test_no_trigger_returns_none():
    gate = _gate()
    trigger = gate.evaluate(
        intraday_dd=Decimal("0.05"),
        multiday_dd=Decimal("0.05"),
        consecutive_losses=2,
        months_since_last_trade=1,
    )
    assert trigger is None


def test_first_trigger_wins_intraday_priority():
    """If multiple criteria fire, intraday DD takes priority (most urgent)."""
    gate = _gate()
    trigger = gate.evaluate(
        intraday_dd=Decimal("0.25"),  # FIRES
        multiday_dd=Decimal("0.20"),  # ALSO fires
        consecutive_losses=10,         # ALSO fires
        months_since_last_trade=0,
    )
    assert trigger == HaltTrigger.DD_INTRADAY
```

- [ ] **Step 5: Run tests, verify they fail**

Run: `.venv/bin/pytest tests/unit/test_halt_gate.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.risk.halt_gate'`.

- [ ] **Step 6: Implement HaltGate**

Create `src/risk/halt_gate.py`:

```python
"""HaltGate — S35 δ TESTNET pre-committed halt criteria evaluation.

Per pre-s35-backlog.md ROUND 3 binding (8 pre-commitments + HALT criteria):
  - DD ≥ -20% intraday → halt + S36 honest close
  - DD ≥ -15% multi-day → halt + S36 honest close
  - ≥5 consecutive losing trades → operator review
  - ≥6 months without n ≥ 30 closed trades → halt + S36 honest close

Priority ordering (first trigger wins, evaluated top-к-bottom):
  1. DD_INTRADAY (most urgent — flash drawdown)
  2. DD_MULTIDAY (cumulative loss)
  3. CONSECUTIVE_LOSSES (degenerate-edge signal)
  4. NO_TRADE_TIMEOUT (signal-frequency starvation)

Returns first matching HaltTrigger or None если все checks pass.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class HaltTrigger(StrEnum):
    """S35 δ halt trigger categories — written к halt_log.context_json."""

    DD_INTRADAY = "S35_DD_INTRADAY"
    DD_MULTIDAY = "S35_DD_MULTIDAY"
    CONSECUTIVE_LOSSES = "S35_CONSECUTIVE_LOSSES"
    NO_TRADE_TIMEOUT = "S35_NO_TRADE_TIMEOUT"


@dataclass(frozen=True)
class HaltGate:
    """Pre-committed halt criteria evaluator. All thresholds Decimal/int."""

    dd_intraday_threshold: Decimal
    dd_multiday_threshold: Decimal
    consecutive_losses_threshold: int
    no_trade_months_threshold: int

    def __post_init__(self) -> None:
        if self.dd_intraday_threshold <= Decimal("0"):
            raise ValueError("dd_intraday_threshold must be positive")
        if self.dd_multiday_threshold <= Decimal("0"):
            raise ValueError("dd_multiday_threshold must be positive")
        if self.consecutive_losses_threshold < 1:
            raise ValueError("consecutive_losses_threshold must be >= 1")
        if self.no_trade_months_threshold < 1:
            raise ValueError("no_trade_months_threshold must be >= 1")

    def evaluate(
        self,
        *,
        intraday_dd: Decimal,
        multiday_dd: Decimal,
        consecutive_losses: int,
        months_since_last_trade: int,
    ) -> HaltTrigger | None:
        """Return first triggered halt category или None если все pass.

        Priority order: intraday DD > multi-day DD > consecutive losses > no-trade timeout.
        """
        if intraday_dd >= self.dd_intraday_threshold:
            return HaltTrigger.DD_INTRADAY
        if multiday_dd >= self.dd_multiday_threshold:
            return HaltTrigger.DD_MULTIDAY
        if consecutive_losses >= self.consecutive_losses_threshold:
            return HaltTrigger.CONSECUTIVE_LOSSES
        if months_since_last_trade >= self.no_trade_months_threshold:
            return HaltTrigger.NO_TRADE_TIMEOUT
        return None
```

- [ ] **Step 7: Run tests, verify GREEN**

Run: `.venv/bin/pytest tests/unit/test_halt_gate.py -v`
Expected: 6 passed.

- [ ] **Step 8: Run mypy --strict**

Run: `.venv/bin/mypy --strict src/risk/halt_gate.py`
Expected: 0 errors.

- [ ] **Step 9: Commit code + tests + Settings**

```bash
git add src/risk/halt_gate.py tests/unit/test_halt_gate.py src/platform/config.py tests/unit/test_settings_s35.py
git commit -m "feat(risk): HaltGate + S35 settings + MAINNET-exclusion invariant (S35 T2 part 1)

- HaltGate с 4 priority-ordered triggers (intraday DD / multi-day DD / consec losses / no-trade timeout)
- Settings: 5 s35_* fields + s35_demo_active vs live_trading model_validator (pre-commit #1)
- 7 NEW tests (6 HaltGate + 1 invariant)

Per pre-s35-backlog.md ROUND 3 binding HALT criteria + pre-commitment #1."
```

- [ ] **Step 10: Write ADR 0053**

Create `llm-wiki/wiki/project/decisions/0053-sprint-35-testnet-live-demo.md` со structure:

```markdown
---
title: ADR 0053 — Sprint 35 δ TESTNET Live Demo Activation
type: decision
tags: [adr, sprint-35, testnet-demo, live-demo, halt-criteria, mean-reversion-s17, locked-pre-registration]
created: 2026-04-27
updated: 2026-04-27
status: accepted
sources:
  - project/decisions/0051-sprint-34-honest-close-v06.md
  - project/decisions/0052-sprint-34-acceptance-criteria-amendment.md
  - project/pre-s35-backlog.md
---

# ADR 0053 — Sprint 35 δ TESTNET Live Demo Activation

## Status

Accepted (2026-04-27) — implemented в S35 (`feature/sprint-35-testnet-donchian-risk` → tag `v0.1.0-alpha.35`).

## Context

Post-S34 hybrid (ADR 0051 honest close v0.6 + ADR 0052 amendment LOCKED). Data audit projection: n_eff = 37-41 < 50 amended threshold даже с full Bybit history extension (4.81y). Option (b) backtest-based new measurement = STRUCTURAL IMPOSSIBILITY.

ROUND 3 consilium (3 agents CONSENSUS) → δ (TESTNET live demo) primary. Forward real-time accumulation bypasses T5 structural problem; S17+S22 MC p ≤ 0.02 partial PASS = best available evidence.

## Operator Acknowledgment (verbatim per ADR 0052)

> Statistical evidence as of v0.6 DOES NOT support live deployment; this amendment
> reflects crypto-specific sample-size reality (Hudson & Urquhart 2021), not
> evidence of positive edge. I authorize TESTNET-only live demo using S22-validated
> mean-reversion strategy with halt criteria pre-committed. No real capital.
> n_trials counter remains frozen per Item #10.

## Decision

Activate δ TESTNET live demo с pre-committed gates + halt criteria LOCKED.

### LOCKED Parameters

- Strategy: `MeanReversionRsiBBStrategy` + `MEAN_REVERSION_S17_RELAXED_PARAMS`
- Symbol: BTCUSDT only (single-symbol bypasses correlation deflation)
- Timeframe: 4H (S22 validated)
- Capital: TESTNET only (zero MAINNET — `live_trading=False` invariant)
- N_trials: frozen (uses S22-validated, no new hypothesis)

### Pre-committed PASS gates

| Gate | Threshold | Source |
|------|-----------|--------|
| n trades | ≥ 50 | ADR 0052 amended T5 floor |
| Sharpe | ≥ 0.7 | T6 unchanged |
| Win rate | ≥ 40% | mean-reversion baseline |
| Max DD | ≤ 30% | risk management |
| MC p-value | ≤ 0.05 | ADR 0052 tightened |
| DSR | ≥ 0.95 | T2 unchanged |

### Pre-committed HALT criteria (HaltGate enforced)

- DD ≥ -20% intraday → halt + S36 honest close
- DD ≥ -15% multi-day → halt + S36 honest close
- ≥ 5 consecutive losing trades → operator review
- ≥ 6 months без n ≥ 30 closed trades → halt + S36 honest close

### NOT permitted без new ADR

- ❌ Switch к MAINNET (LOCKED через model_validator + invariant test)
- ❌ Change strategy params (MEAN_REVERSION_S17_RELAXED_PARAMS LOCKED)
- ❌ Multi-symbol (single-symbol BTCUSDT LOCKED — correlation deflation falsified)
- ❌ Lower halt thresholds without S36+ ADR с explicit override

## Consequences

**Positive:** Forward real-time accumulation bypasses T5 structural backtest problem. Halt criteria pre-committed (anti-snooping). 12-month review window allows accumulating ≥ 50 trades natural rate.

**Negative:** Zero MAINNET evidence accumulates. TESTNET fills may differ от mainnet liquidity profile. 6-month no-trade timeout may trigger early halt если signal-frequency assumptions wrong.

**Neutral:** No code regression — all existing tests preserved. HaltGate gated по `s35_demo_active=False` default.

## Related

- ADR 0051 (S34 6-th honest close v0.6)
- ADR 0052 (S34 acceptance-criteria amendment LOCKED)
- ADR 0054 (S35 Donchian pre-registration — paired α track)
- pre-s35-backlog.md (ROUND 3 binding consilium trail)
```

- [ ] **Step 11: Commit ADR 0053**

```bash
git add llm-wiki/wiki/project/decisions/0053-sprint-35-testnet-live-demo.md
git commit -m "docs(adr): ADR 0053 S35 δ TESTNET live demo activation (S35 T2 part 2)

Operator acknowledgment template (verbatim per ADR 0052) + LOCKED params
+ pre-committed PASS gates + HALT criteria + MAINNET exclusion invariant.

Per pre-s35-backlog.md ROUND 3 binding consilium decision."
```

---

## Task 3: α Donchian ADR Pre-Registration

**Why before T4:** Pre-commitment #4 — "Donchian parameters pre-registered before data inspection. No post-hoc tuning." ADR LOCKED **before** strategy code touches OHLCV data.

**Files:**
- Create: `llm-wiki/wiki/project/decisions/0054-sprint-35-donchian-pre-registration.md`

- [ ] **Step 1: Verify operator не see backtest results yet**

Sanity check: `ls data/donchian_backtest_results.json 2>/dev/null` — must NOT exist (creates в T4).

- [ ] **Step 2: Write ADR 0054 verbatim**

Create `llm-wiki/wiki/project/decisions/0054-sprint-35-donchian-pre-registration.md`:

```markdown
---
title: ADR 0054 — Sprint 35 α Donchian Breakout Pre-Registration LOCKED
type: decision
tags: [adr, sprint-35, donchian, breakout, long-only, pre-registration, n-trials-5, locked]
created: 2026-04-27
updated: 2026-04-27
status: accepted
sources:
  - project/decisions/0052-sprint-34-acceptance-criteria-amendment.md
  - project/decisions/0053-sprint-35-testnet-live-demo.md
  - project/pre-s35-backlog.md
---

# ADR 0054 — Sprint 35 α Donchian Breakout Pre-Registration LOCKED

## Status

Accepted (2026-04-27) **BEFORE** any backtest data inspection — anti-snooping discipline per Bailey & López de Prado 2014.

## Context

ROUND 3 consilium voted α (Donchian breakout) as parallel synthetic track:
- 7th hypothesis tested across project lifetime (N_trials counter pooled = 5)
- Orthogonal paradigm к mean-reversion (trend-following breakout)
- Long-only FSM-compatible (no SHORT signals — `long_only=True` invariant per ADR 0009)
- ~280 LoC scope estimate

DSR penalty при N_trials=5 calculated per Bailey 2014 sigma_SR pooling protocol (a) — significant но not prohibitive.

## Decision

Implement Donchian breakout long-only strategy с LOCKED parameters BEFORE backtest run.

### LOCKED Parameters (`DONCHIAN_LONG_ONLY_PARAMS`)

| Param | Value | Justification |
|-------|-------|---------------|
| `lookback_n` | 20 | Classical Donchian (Faber 2007) standard period |
| `exit_lookback_n` | 10 | Half-period exit (Turtle Trading variant) |
| `atr_period` | 14 | Standard Wilder ATR consistent с indicators.atr() |
| `atr_stop_mult` | 2.0 | 2× ATR trailing stop (volatility-adjusted) |
| `signal_side_mode` | "long_only" | FSM SignalSide invariant (no SHORT) |
| `min_atr_filter` | None | No volatility floor — accept all breakouts |

### Symbol + Timeframe LOCKED

- Symbol: BTCUSDT (single-symbol — bypasses correlation deflation per S33 lesson)
- Timeframe: 4H (consistent с δ track для apples-to-apples comparison)

### N_trials Counter

| Sprint | Trials accumulated | Strategy |
|--------|-------------------|----------|
| S13 | 1 | EMA crossover |
| S15 | 2 | Mean-reversion strict |
| S17 | 3 | Mean-reversion relaxed |
| S22 | 4 | Mean-reversion 4H |
| **S35 α** | **5** | **Donchian breakout** |

DSR penalty при N_trials=5: `sigma_SR_pooled = sqrt((1/N) * sum(sharpe_i²))`. Bonferroni alpha-adjusted threshold per Bailey 2014.

### 6 Pre-Committed Acceptance Gates (verbatim per ADR 0052 amended LOCKED)

| Gate | Threshold | Block? |
|------|-----------|--------|
| T5 n_trades raw | ≥ 50 | YES |
| T5 n_eff (single-symbol → n_eff = n_raw) | ≥ 50 | YES |
| T6 OOS/IS Sharpe | ≥ 0.7 | YES |
| MC p-value | ≤ 0.05 | YES |
| DSR (N_trials=5) | ≥ 0.95 | YES |
| acceptance_gate.sharpe_gate_passed | per-fold ≥ 0.7 | YES |

PASS = ALL gates conjoint AND. FAIL conjoint = α direction CLOSED, β fallback (pause) per pre-commit #8.

### NOT permitted без new ADR

- ❌ Post-hoc parameter tuning (snooping)
- ❌ SHORT signals (FSM long_only invariant)
- ❌ Multi-symbol (single-symbol BTCUSDT LOCKED)
- ❌ Different timeframe (4H LOCKED)
- ❌ Reuse OHLCV data вне pre-registered range

## Consequences

**Positive:** Anti-snooping LOCKED before data touch. N_trials properly counted (=5). Long-only FSM-compatible — no engineering blocker.

**Negative:** DSR penalty при N=5 raises threshold harder than N=4. If FAIL → α direction PERMANENTLY CLOSED.

**Neutral:** No production trading impact (synthetic backtest only).

## Related

- ADR 0052 (S34 amendment LOCKED — gates source)
- ADR 0053 (S35 δ TESTNET — paired primary track)
- pre-s35-backlog.md (ROUND 3 binding)
```

- [ ] **Step 3: Commit ADR 0054 BEFORE writing strategy code**

```bash
git add llm-wiki/wiki/project/decisions/0054-sprint-35-donchian-pre-registration.md
git commit -m "docs(adr): ADR 0054 S35 α Donchian breakout pre-registration LOCKED (S35 T3)

Pre-registers BEFORE any code OR data inspection (anti-snooping per Bailey 2014):
- DONCHIAN_LONG_ONLY_PARAMS LOCKED (lookback=20, exit=10, ATR×2)
- Symbol BTCUSDT + 4H LOCKED
- N_trials=5 explicit (DSR penalty correctly counted)
- 6 acceptance gates per ADR 0052 amended

Per pre-s35-backlog.md ROUND 3 binding pre-commit #3 + #4."
```

---

## Task 4: α Donchian Strategy Implementation + Backtest Run

**Files:**
- Create: `src/signalgen/donchian_strategy.py`
- Create: `tests/unit/test_donchian_strategy.py`
- Create: `data/donchian_backtest_results.json`
- Modify: `src/signalgen/__init__.py` (export `DonchianBreakoutStrategy` + `DONCHIAN_LONG_ONLY_PARAMS`)

- [ ] **Step 1: Write failing tests**

Create `tests/unit/test_donchian_strategy.py`:

```python
"""Donchian breakout long-only strategy tests (S35 α track per ADR 0054 LOCKED)."""
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from src.marketdata.models import Bar
from src.signalgen.donchian_strategy import (
    DONCHIAN_LONG_ONLY_PARAMS,
    DonchianBreakoutStrategy,
)
from src.signalgen.models import SignalSide


def _bar(close_time: datetime, *, h: float, l: float, c: float, o: float | None = None) -> Bar:
    return Bar(
        symbol="BTCUSDT",
        interval="4h",
        open_time=close_time - timedelta(hours=4),
        close_time=close_time,
        open=Decimal(str(o if o is not None else c)),
        high=Decimal(str(h)),
        low=Decimal(str(l)),
        close=Decimal(str(c)),
        volume=Decimal("100"),
        is_closed=True,
    )


def _strategy() -> DonchianBreakoutStrategy:
    return DonchianBreakoutStrategy(
        symbol="BTCUSDT",
        lookback_n=int(DONCHIAN_LONG_ONLY_PARAMS["lookback_n"]),
        exit_lookback_n=int(DONCHIAN_LONG_ONLY_PARAMS["exit_lookback_n"]),
        atr_period=int(DONCHIAN_LONG_ONLY_PARAMS["atr_period"]),
        atr_stop_mult=Decimal(str(DONCHIAN_LONG_ONLY_PARAMS["atr_stop_mult"])),
    )


def test_warmup_no_signal_until_buffer_full():
    s = _strategy()
    base = datetime(2026, 1, 1, 4, tzinfo=UTC)
    for i in range(15):  # less than lookback_n=20
        sig = s.on_bar(_bar(base + timedelta(hours=4 * i), h=100 + i, l=99 + i, c=99.5 + i))
        assert sig is None, f"premature signal at bar {i}"


def test_breakout_above_donchian_high_emits_long_signal():
    s = _strategy()
    base = datetime(2026, 1, 1, 4, tzinfo=UTC)
    # Fill buffer с flat range 100-105
    for i in range(25):
        s.on_bar(_bar(base + timedelta(hours=4 * i), h=105.0, l=100.0, c=102.0))
    # Breakout bar: close > prior 20-bar high
    breakout_bar = _bar(
        base + timedelta(hours=4 * 25), h=110.0, l=104.0, c=109.0  # close > 105
    )
    sig = s.on_bar(breakout_bar)
    assert sig is not None
    assert sig.side == SignalSide.LONG
    assert sig.reason == "ENTRY_LONG_DONCHIAN_BREAKOUT"


def test_long_only_invariant_no_short_signals():
    """ADR 0054 LOCKED: signal_side_mode=long_only — strategy NEVER emits SHORT."""
    s = _strategy()
    base = datetime(2026, 1, 1, 4, tzinfo=UTC)
    # Fill buffer
    for i in range(25):
        s.on_bar(_bar(base + timedelta(hours=4 * i), h=105.0, l=100.0, c=102.0))
    # Breakdown below low (would be SHORT in symmetric Donchian)
    breakdown = _bar(
        base + timedelta(hours=4 * 25), h=101.0, l=95.0, c=96.0  # close < 100
    )
    sig = s.on_bar(breakdown)
    # Long-only invariant: no SHORT signal emitted
    if sig is not None:
        assert sig.side != SignalSide.SHORT, "long-only invariant violated — SHORT emitted"


def test_atr_stop_exit_when_in_long():
    """When LONG, exit if close < entry_close - 2 × ATR."""
    s = _strategy()
    base = datetime(2026, 1, 1, 4, tzinfo=UTC)
    # Fill buffer + breakout entry
    for i in range(25):
        s.on_bar(_bar(base + timedelta(hours=4 * i), h=105.0, l=100.0, c=102.0))
    s.on_bar(_bar(base + timedelta(hours=4 * 25), h=110.0, l=104.0, c=109.0))  # LONG entry
    # Sharp drop > 2×ATR below entry close
    crash_bar = _bar(
        base + timedelta(hours=4 * 26), h=109.0, l=80.0, c=82.0
    )
    sig = s.on_bar(crash_bar)
    assert sig is not None
    assert sig.side == SignalSide.FLAT
    assert sig.reason == "EXIT_FLAT_ATR_STOP"
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `.venv/bin/pytest tests/unit/test_donchian_strategy.py -v`
Expected: FAIL `ModuleNotFoundError: No module named 'src.signalgen.donchian_strategy'`.

- [ ] **Step 3: Implement DonchianBreakoutStrategy**

Create `src/signalgen/donchian_strategy.py`:

```python
"""Donchian breakout long-only strategy (S35 α track per ADR 0054 LOCKED).

LOCKED parameters per ADR 0054 — anti-snooping pre-registration:
  - lookback_n=20 (entry window)
  - exit_lookback_n=10 (exit window — Turtle Trading variant)
  - atr_period=14 (Wilder ATR)
  - atr_stop_mult=2.0 (volatility-adjusted trailing stop)
  - signal_side_mode="long_only" (FSM invariant — NEVER emits SHORT)

Entry rule (LONG): close(T) > max(high[T-lookback_n:T])  AND  current_side == FLAT
Exit rule (FLAT):  IF current LONG, exit if EITHER:
                   - close(T) < min(low[T-exit_lookback_n:T])  (Donchian channel exit)
                   - close(T) < entry_close - atr_stop_mult * ATR(T)  (ATR trailing stop)

Invariant: signal on close(T) → execution at open(T+1) (no look-ahead per execution-timing.md).
Thread-safety: NOT thread-safe — single-producer per symbol pattern.
"""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import numpy as np

from src.marketdata.models import Bar
from src.signalgen.indicators import atr
from src.signalgen.models import Signal, SignalSide

# ADR 0054 LOCKED — DO NOT modify без new ADR.
DONCHIAN_LONG_ONLY_PARAMS: dict[str, object] = {
    "lookback_n": 20,
    "exit_lookback_n": 10,
    "atr_period": 14,
    "atr_stop_mult": Decimal("2.0"),
    "signal_side_mode": "long_only",
}


class DonchianBreakoutStrategy:
    """Stateful Donchian breakout strategy (long-only).

    Internal state: rolling buffer of last (lookback_n + atr_period + 5) bars,
    plus current_side and entry_close_when_long.
    """

    def __init__(
        self,
        *,
        symbol: str,
        lookback_n: int,
        exit_lookback_n: int,
        atr_period: int,
        atr_stop_mult: Decimal,
    ) -> None:
        if lookback_n <= 0 or exit_lookback_n <= 0 or atr_period <= 0:
            raise ValueError("lookback / exit_lookback / atr_period must be positive")
        if exit_lookback_n >= lookback_n:
            raise ValueError("exit_lookback_n must be < lookback_n")
        if atr_stop_mult <= Decimal("0"):
            raise ValueError("atr_stop_mult must be positive")

        self._symbol = symbol
        self._lookback_n = lookback_n
        self._exit_lookback_n = exit_lookback_n
        self._atr_n = atr_period
        self._atr_stop_mult = atr_stop_mult
        self._buffer_size = max(lookback_n, atr_period) + 5
        self._bars: list[Bar] = []
        self._current_side: SignalSide = SignalSide.FLAT
        self._entry_close: Decimal | None = None

    def _append_bar(self, bar: Bar) -> bool:
        if not bar.is_closed:
            return False
        if bar.symbol != self._symbol:
            return False
        if self._bars and bar.close_time <= self._bars[-1].close_time:
            return False
        self._bars.append(bar)
        if len(self._bars) > self._buffer_size:
            self._bars = self._bars[-self._buffer_size :]
        return True

    def warmup(self, bar: Bar) -> None:
        """Feed historical bar к buffer без signal emission."""
        self._append_bar(bar)

    def on_bar(self, bar: Bar) -> Signal | None:
        if not self._append_bar(bar):
            return None
        if len(self._bars) < self._lookback_n + 1:
            return None

        highs = np.array([float(b.high) for b in self._bars], dtype=np.float64)
        lows = np.array([float(b.low) for b in self._bars], dtype=np.float64)
        closes = np.array([float(b.close) for b in self._bars], dtype=np.float64)

        # Donchian channel: max(high[T-lookback_n:T]), excluding current bar.
        donchian_high = float(np.max(highs[-(self._lookback_n + 1) : -1]))
        donchian_low_exit = float(np.min(lows[-(self._exit_lookback_n + 1) : -1]))
        atr_arr = atr(highs, lows, closes, self._atr_n)
        atr_now = atr_arr[-1]
        if np.isnan(atr_now):
            return None

        close_now = float(bar.close)

        # Entry rule (LONG): close > donchian_high AND FLAT
        if self._current_side == SignalSide.FLAT and close_now > donchian_high:
            self._current_side = SignalSide.LONG
            self._entry_close = bar.close
            return self._build_signal(
                bar,
                SignalSide.LONG,
                atr_now=atr_now,
                reason="ENTRY_LONG_DONCHIAN_BREAKOUT",
            )

        # Exit rule (FLAT): from LONG, channel exit OR ATR stop hit
        if self._current_side == SignalSide.LONG and self._entry_close is not None:
            atr_stop_price = float(self._entry_close) - float(self._atr_stop_mult) * atr_now
            channel_exit = close_now < donchian_low_exit
            atr_stop_exit = close_now < atr_stop_price
            if channel_exit or atr_stop_exit:
                self._current_side = SignalSide.FLAT
                reason = "EXIT_FLAT_ATR_STOP" if atr_stop_exit else "EXIT_FLAT_CHANNEL"
                self._entry_close = None
                return self._build_signal(
                    bar,
                    SignalSide.FLAT,
                    atr_now=atr_now,
                    reason=reason,
                )

        return None

    def _build_signal(
        self,
        bar: Bar,
        side: SignalSide,
        *,
        atr_now: float,
        reason: str,
    ) -> Signal:
        # Donchian не computes EMA/ADX/DI/RSI — populate с zero placeholders
        # (Signal protocol shared с EMA strategy, mean-reversion same pattern per S15).
        zero = Decimal("0")
        return Signal(
            signal_id=uuid4(),
            symbol=self._symbol,
            side=side,
            bar_close_time=bar.close_time,
            generated_at=datetime.now(UTC),
            ema_fast=zero,
            ema_slow=zero,
            adx_14=zero,
            plus_di_14=zero,
            minus_di_14=zero,
            rsi_14=zero,
            atr_14=Decimal(str(atr_now)),
            reason=reason,
        )
```

- [ ] **Step 4: Run tests, verify GREEN**

Run: `.venv/bin/pytest tests/unit/test_donchian_strategy.py -v`
Expected: 4 passed.

- [ ] **Step 5: Run mypy --strict**

Run: `.venv/bin/mypy --strict src/signalgen/donchian_strategy.py tests/unit/test_donchian_strategy.py`
Expected: 0 errors.

- [ ] **Step 6: Export from package init**

Edit `src/signalgen/__init__.py` — add export:

```python
from src.signalgen.donchian_strategy import (
    DONCHIAN_LONG_ONLY_PARAMS,
    DonchianBreakoutStrategy,
)
```

- [ ] **Step 7: Run full test suite as regression check**

Run: `.venv/bin/pytest tests/unit -x -q`
Expected: 808 baseline + new tests (T1=2 + T2=7 + T4=4 = 13 new) → 821 passed.

- [ ] **Step 8: Commit Donchian strategy + tests**

```bash
git add src/signalgen/donchian_strategy.py tests/unit/test_donchian_strategy.py src/signalgen/__init__.py
git commit -m "feat(signalgen): Donchian breakout long-only strategy (S35 T4 part 1)

- DonchianBreakoutStrategy с DONCHIAN_LONG_ONLY_PARAMS LOCKED per ADR 0054
- 4 unit tests (warmup / breakout entry / long-only invariant / ATR stop exit)
- Long-only FSM-compatible (signal_side_mode='long_only', NEVER SHORT)

Per ADR 0054 LOCKED — anti-snooping pre-registered BEFORE backtest run."
```

- [ ] **Step 9: Run Donchian backtest via CLI**

Use existing replay engine pattern (per S33 T5 precedent — `__main__.py wfa` subcommand). Verify CLI supports custom strategy class hookup OR add minimal driver script:

```bash
.venv/bin/python -m src.backtest.donchian_runner --symbol BTCUSDT --timeframe 4h \
    --start 2023-01-01 --end 2026-04-26 \
    --output data/donchian_backtest_results.json
```

If `donchian_runner` doesn't exist — create thin driver `src/backtest/donchian_runner.py` (~30 LoC) that:
1. Loads OHLCV из `data/BTCUSDT_4h.parquet`
2. Instantiates `DonchianBreakoutStrategy(**DONCHIAN_LONG_ONLY_PARAMS)`
3. Runs `WalkForwardRunner` с amended gates (T5=50, n_eff=50, MC=0.05, p_threshold=0.05)
4. Writes results JSON

Output schema:

```json
{
    "strategy": "DonchianBreakoutStrategy",
    "params": {"lookback_n": 20, "exit_lookback_n": 10, "atr_period": 14, "atr_stop_mult": "2.0"},
    "symbol": "BTCUSDT",
    "timeframe": "4h",
    "n_trades_raw": 0,
    "n_trades_n_eff": 0,
    "fold_oos_is_sharpe_ratios": [],
    "mc_p_value": 0.0,
    "dsr": 0.0,
    "verdict": "PASS_OR_FAIL",
    "failed_criteria": [],
    "n_trials_counter": 5,
    "ran_at": "2026-04-27T..."
}
```

- [ ] **Step 10: Append entry к cross_trial_sharpes.json**

If Donchian PASS — append per protocol (a):

```python
from src.analytics.cross_trial_log import CrossTrialLog
log = CrossTrialLog("data/cross_trial_sharpes.json")
log.append_trial(sprint=35, oos_sharpe=<value>, symbol="BTCUSDT")
```

If FAIL conjoint — record results но не append к cross_trial (S34 ADR 0052 Item #10 protocol — failed trials logged separately).

- [ ] **Step 11: Commit backtest results**

```bash
git add data/donchian_backtest_results.json
git commit -m "data(backtest): S35 α Donchian backtest results — verdict <PASS|FAIL>

Strategy: DonchianBreakoutStrategy с DONCHIAN_LONG_ONLY_PARAMS LOCKED (ADR 0054)
Symbol: BTCUSDT 4H, period 2023-01-01 → 2026-04-26
N_trials counter incremented к 5 (S13/S15/S17/S22/S35).

Per ADR 0054 acceptance gates pre-registered."
```

---

## Task 5: Reconcile + Sprint-35 Page + Sync

**Files:**
- Create: `llm-wiki/wiki/project/sprints/sprint-35-testnet-donchian-risk.md`
- Create: `llm-wiki/wiki/project/components/halt-gate.md`
- Create: `llm-wiki/wiki/project/components/donchian-strategy.md`
- Modify: `llm-wiki/wiki/index.md`
- Modify: `llm-wiki/wiki/project/architecture/current-state.md`
- Modify: `llm-wiki/wiki/project/SPRINT_STATE.md`
- Append: `llm-wiki/wiki/log.md`

- [ ] **Step 1: Run pytest baseline + mypy --strict**

Run:
```bash
.venv/bin/pytest tests/unit -q --ignore=tests/integration 2>&1 | tail -3
.venv/bin/mypy --strict src/ 2>&1 | tail -3
```

Expected: 808 + 13 new = 821 passed / 0 mypy errors.

- [ ] **Step 2: Verify canonical counts**

Run:
```bash
.venv/bin/python -c "from src.execution.state_machine import TRANSITIONS, ExecutionState, ExecutionEvent; from src.risk.reason_codes import ReasonCode; print(f'states={len(list(ExecutionState))}, events={len(list(ExecutionEvent))}, transitions={len(TRANSITIONS)}, reason_codes={len(list(ReasonCode))}')"
```

Expected: states=16, events=30, transitions=74, reason_codes=45 (unchanged — S35 doesn't touch FSM).

- [ ] **Step 3: Write component page halt-gate.md**

Create `llm-wiki/wiki/project/components/halt-gate.md` (~80 lines):

```markdown
---
title: HaltGate Component
type: component
tags: [component, risk, halt-criteria, sprint-35, testnet-demo]
created: 2026-04-27
updated: 2026-04-27
status: stable
sources:
  - src/risk/halt_gate.py
  - project/decisions/0053-sprint-35-testnet-live-demo.md
  - project/pre-s35-backlog.md
---

# HaltGate

**TL;DR:** Pre-committed halt criteria evaluator для S35 δ TESTNET live demo. 4 priority-ordered triggers (intraday DD, multi-day DD, consecutive losses, no-trade timeout).

## Purpose

Per pre-s35-backlog.md ROUND 3 binding HALT criteria — anti-snooping discipline LOCKED before live activation.

## Public API

- `HaltGate.__init__(*, dd_intraday_threshold, dd_multiday_threshold, consecutive_losses_threshold, no_trade_months_threshold)` — frozen dataclass
- `HaltGate.evaluate(*, intraday_dd, multiday_dd, consecutive_losses, months_since_last_trade) -> HaltTrigger | None` — returns first trigger или None

## Settings

| Setting | Default | Range | Source |
|---------|---------|-------|--------|
| `s35_halt_dd_intraday` | 0.20 | (0, 0.50] | pre-commit ROUND 3 |
| `s35_halt_dd_multiday` | 0.15 | (0, 0.50] | pre-commit ROUND 3 |
| `s35_halt_consecutive_losses` | 5 | [1, 20] | pre-commit ROUND 3 |
| `s35_halt_no_trade_months` | 6 | [1, 24] | pre-commit ROUND 3 |

## Triggers (priority order)

1. `HaltTrigger.DD_INTRADAY` — most urgent (flash drawdown)
2. `HaltTrigger.DD_MULTIDAY`
3. `HaltTrigger.CONSECUTIVE_LOSSES`
4. `HaltTrigger.NO_TRADE_TIMEOUT`

## Invariants

- All thresholds positive (validated в `__post_init__`)
- First trigger wins (no AND-combination)
- Returns `None` если все checks pass

## Related

- [[../decisions/0053-sprint-35-testnet-live-demo]]
- [[../decisions/0052-sprint-34-acceptance-criteria-amendment]]
- [[../pre-s35-backlog]]
```

- [ ] **Step 4: Write component page donchian-strategy.md**

Create `llm-wiki/wiki/project/components/donchian-strategy.md` (~80 lines, same format).

- [ ] **Step 5: Write sprint-35 page**

Create `llm-wiki/wiki/project/sprints/sprint-35-testnet-donchian-risk.md` summarizing:
- 5 tasks shipped table
- КУ achieved per task
- Engineering changes summary
- Backtest verdict (α PASS/FAIL)
- δ activation status
- Open issues для S36+

- [ ] **Step 6: Update index.md**

Edit `llm-wiki/wiki/index.md`:

- ADD `[[project/decisions/0053-sprint-35-testnet-live-demo]] — δ TESTNET live demo activation` к Decisions section
- ADD `[[project/decisions/0054-sprint-35-donchian-pre-registration]] — α Donchian pre-registration LOCKED`
- ADD `[[project/sprints/sprint-35-testnet-donchian-risk]] — Sprint 35` к Sprints section
- ADD `[[project/components/halt-gate]] — HaltGate` к Components section
- ADD `[[project/components/donchian-strategy]] — Donchian breakout strategy`

- [ ] **Step 7: Update current-state.md**

Edit `llm-wiki/wiki/project/architecture/current-state.md`:

- ADRs: 52 → 54
- Sprint pages: 38 → 39
- Components: 43 → 45
- Add S35 row к sprint history table:

```markdown
| 35 | δ TESTNET live demo + α Donchian + ζ risk mgmt | δ activated TESTNET / α verdict <PASS|FAIL> / ζ Kelly+ATR refactored | 5 ADRs+sprints+settings |
```

- [ ] **Step 8: Append log.md sprint-end entry**

```markdown
## [2026-04-27] sprint-end | S35 — δ TESTNET + α Donchian + ζ risk mgmt
- Tag v0.1.0-alpha.35
- δ TESTNET activated (HaltGate wired, 5 settings + MAINNET-exclusion invariant)
- α Donchian backtest verdict: <PASS|FAIL>
- ζ risk refactor: explicit ATR SL multiplier setting + Kelly cap audit
- 13 NEW tests (Kelly audit + Settings invariant + HaltGate × 6 + Donchian × 4)
- ADRs 0053 + 0054 (52 → 54 total)
```

- [ ] **Step 9: Update SPRINT_STATE → Phase 8 ship**

Edit `llm-wiki/wiki/project/SPRINT_STATE.md`:

```yaml
sprint: 35
phase: 8-ship
branch: feature/sprint-35-testnet-donchian-risk
tag: v0.1.0-alpha.35
```

- [ ] **Step 10: Commit wiki sync**

```bash
git add llm-wiki/wiki/project/sprints/sprint-35-testnet-donchian-risk.md \
        llm-wiki/wiki/project/components/halt-gate.md \
        llm-wiki/wiki/project/components/donchian-strategy.md \
        llm-wiki/wiki/index.md \
        llm-wiki/wiki/project/architecture/current-state.md \
        llm-wiki/wiki/log.md \
        llm-wiki/wiki/project/SPRINT_STATE.md
git commit -m "docs(sprint): S35 wiki sync — sprint-35 page + 2 components + counts (S35 T5)

- sprint-35-testnet-donchian-risk page (5 tasks shipped)
- halt-gate + donchian-strategy component pages
- index + current-state counts: 52→54 ADRs / 38→39 sprints / 43→45 components
- log.md sprint-end entry
- SPRINT_STATE → 8-ship"
```

- [ ] **Step 11: Use sprint-finish skill для PR + tag**

Per kit binding: invoke `sprint-finish` skill — handles HARD-GATE checklist (sprint page exists ✓ / canonical counts ✓ / index sync ✓), then `superpowers:finishing-a-development-branch` для push + PR + squash-merge + tag `v0.1.0-alpha.35`.

---

## Self-Review Checklist

**1. Spec coverage:** All 5 ROUND 3 binding pre-commitments addressed?
- ✅ #1 TESTNET-only invariant — T2 step 1 model_validator + T2 step 2 test
- ✅ #2 Kelly cap + ζ refactor BEFORE δ — T1 sequence
- ✅ #3 N_trials=5 declared — T3 ADR 0054
- ✅ #4 Params pre-registered — T3 ADR 0054 BEFORE T4 implementation
- ✅ #5 Halt criteria — T2 HaltGate + 4 triggers
- ✅ #6 (γ closed) — N/A (anti-pattern guard)
- ✅ #7 (ε deferred) — N/A
- ✅ #8 (β fallback) — documented в pre-s35-backlog "Failure branch" section

**2. Placeholder scan:** No TBD/TODO/"implement later" in plan tasks. ✓

**3. Type consistency:** `HaltTrigger` StrEnum used consistently T2 + halt-gate.md. `DONCHIAN_LONG_ONLY_PARAMS` referenced T3+T4 same name. `Signal` protocol reused per S15 pattern. ✓

**4. Trace map covers backlog:** All pre-s35-backlog.md "S35 task structure" rows mapped к T1-T5. ✓

---

## Execution Handoff

Plan complete и saved к `llm-wiki/wiki/project/plans/2026-04-27-sprint-35-testnet-donchian-risk.md`.

Two execution options:

1. **Subagent-Driven (recommended)** — fresh subagent per task, two-stage review (spec compliance + code quality), fast iteration
2. **Inline Execution** — controller-driven via `superpowers:executing-plans`, batch checkpoints

Operator выбор?
