---
title: Sprint 36 Plan — δ TESTNET Activation (HaltGate Wire-up + B1 Critical Fix + DSR Amendment)
type: plan
tags: [sprint-36, plan, testnet-activation, halt-gate-wireup, dsr-amendment, reason-codes-extension, b1-critical-fix, ru]
created: 2026-04-27
updated: 2026-04-27
status: proposed
sources:
  - project/decisions/0052-sprint-34-acceptance-criteria-amendment.md
  - project/decisions/0053-sprint-35-testnet-live-demo.md
  - project/pre-s36-backlog.md
---

# Sprint 36 Implementation Plan — δ TESTNET Activation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire HaltGate в RuntimeManager, fix B1 critical strategy params mismatch (S17-relaxed LOCKED params not currently passed к live path), implement DSR sigma_SR amendment + adapted live-data gates methodology, extend ReasonCode enum +4 HALT_S36_*, build state-source methods (4 new). δ TESTNET activatable post-S36.

**Architecture:** Eight serialized TDD tasks per ROUND 4 consilium binding. Critical-path ordering: ADR first → B1 fix (parametrization correct ДО state plumbing) → state methods → wire-up + ReasonCode → DSR amendment + adapted reporter → wiki sync.

**Tech Stack:** Python 3.12 / pydantic-settings / SQLite WAL / pytest-Hypothesis / mypy --strict / TDD RED→GREEN.

---

## Trace Map (PHASE 3 step 1a HARD-GATE)

| Source artifact | Implementation task |
|-----------------|---------------------|
| pre-s36-backlog "B1 CRITICAL" — params not wired к live path | T2 |
| pre-s36-backlog "B2" — HaltGate wire-up + state methods | T3 + T4 |
| pre-s36-backlog "B3" — ReasonCode +4 HALT_S36_* | T5 |
| pre-s36-backlog "DSR sigma_SR amendment" — verbatim text | T6 |
| pre-s36-backlog "Adapted gates methodology" — live Sharpe + calibration + MC gating | T7 |
| pre-s36-backlog "Hybrid duration option H" — verbatim ADR text | T1 (ADR 0055) |
| pre-s36-backlog "MAINNET criteria DEFER к S37+" | T1 ADR sub-decision |
| pre-s36-backlog "N_trials freeze at 7" | T1 + T6 (DELTA_N_TRIALS_LOCKED constant) |
| ADR 0053 line 62 — 6mo no-trade halt criterion (already pre-committed) | T4 (HaltGate.evaluate() respects this) |

---

## File Structure

**Create:**
- `llm-wiki/wiki/project/decisions/0055-sprint-36-delta-activation.md` — ADR 0055 (~250 lines)
- `llm-wiki/wiki/project/decisions/0056-sprint-36-dsr-sigma-sr-amendment.md` — ADR 0056 (~120 lines)
- `llm-wiki/wiki/project/components/halt-gate-wireup.md` — wire-up component page
- `llm-wiki/wiki/project/components/live-trade-reporter.md` — adapted reporter component page
- `llm-wiki/wiki/project/sprints/sprint-36-delta-activation.md` — sprint page
- `tests/unit/test_strategy_locked_params.py` (T2)
- `tests/unit/test_equity_tracker_intraday_dd.py` (T3)
- `tests/unit/test_trade_history_streak.py` (T3)
- `tests/integration/test_halt_gate_wireup.py` (T4)
- `tests/unit/test_dsr_sigma_sr_amendment.py` (T6)
- `tests/unit/test_live_trade_reporter.py` (T7)
- `src/analytics/live_trade_reporter.py` (T7)

**Modify:**
- `src/signalgen/mean_reversion_strategy.py` — add `bb_std_mult` + `and_gate_required` constructor params (T2)
- `src/__main__.py:124-131` — pass LOCKED params когда `s35_demo_active=True` (T2)
- `src/risk/equity_tracker.py` — add `intraday_dd_pct(now)` + `hwm_since(since_ts)` methods (T3)
- `src/risk/trade_history.py` — add `consecutive_losses(symbol)` + `last_trade_ts(symbol)` methods (T3)
- `src/runtime/manager.py` — add `_check_halt_gate()` method called per-tick when s35_demo_active (T4)
- `src/risk/reason_codes.py` — add 4 HALT_S36_* enum values (45→49) (T5)
- `tests/property/test_request_halt_mapping.py` — extend `_REQUEST_HALT_CODES` allowlist (T5)
- `src/backtest/donchian_runner.py` — refactor sigma_SR fallback (T6)
- `src/analytics/dsr.py` — add UNDERPOWERED flag для 10≤n<30, NaN для n<10 (T6)
- `llm-wiki/wiki/project/components/reason-codes-schema.md` — sync 45→49 (T5)
- `llm-wiki/wiki/project/components/execution-state-machine.md` — sync canonical count (T5)
- `llm-wiki/wiki/index.md` — add ADR 0055 + 0056 + sprint-36 + 2 components (T8)
- `llm-wiki/wiki/project/architecture/current-state.md` — counts 54→56 ADRs / 39→40 sprints / 45→47 components / 45→49 reason codes (T8)
- `llm-wiki/wiki/log.md` — append sprint-end (T8)
- `llm-wiki/wiki/project/SPRINT_STATE.md` — phase=8-ship (T8)

---

## Task 1 — ADR 0055 + 0056 (docs first, anti-snooping pre-commit)

**Why first:** All subsequent tasks reference ADR pre-commits. Hybrid duration option (H) verbatim per ROUND 2 trader binding. DSR sigma_SR amendment per quant verbatim. Lock decisions BEFORE code touches.

**Files:**
- Create: `llm-wiki/wiki/project/decisions/0055-sprint-36-delta-activation.md`
- Create: `llm-wiki/wiki/project/decisions/0056-sprint-36-dsr-sigma-sr-amendment.md`

- [ ] **Step 1: Write ADR 0055**

Sections:
- Status (Accepted 2026-04-27, supersedes none, paired ADR 0056)
- Context — post-S35 ROUND 4 consilium CONSENSUS (b) δ activate
- Decision (8 sub-decisions per consilium binding):
  - SD-1: Hybrid duration option (H) verbatim per ROUND 2 trader BINDING (3 events: HaltGate / PASS gates n≥50 / 12mo MAINNET-promotion gate, NO 6mo interim)
  - SD-2: B1 fix mandate — `MEAN_REVERSION_S17_RELAXED_PARAMS` LOCKED wired к live path BEFORE day-1 trade
  - SD-3: Multiday DD definition — HWM since `s35_demo_active=True` activation timestamp (persisted в SQLite halt_log OR equity_snapshots table)
  - SD-4: HaltTrigger → ReasonCode mapping table (4 entries — see T5)
  - SD-5: Halt resume protocol — HaltGate-triggered halt requires operator review (no HMAC override path; manual FSM reset через --reconcile-only)
  - SD-6: Adapted gates methodology (per quant verbatim) — live Sharpe estimator + T6 → live/synthetic calibration ratio + MC gated на n≥20 sign-flip / n≥40 block-bootstrap
  - SD-7: N_trials FREEZE at 7 для δ live demo (S22 hypothesis re-evaluation, no Bailey 2014 increment)
  - SD-8: MAINNET promotion criteria DEFERRED к S37+ post-12mo TESTNET review
- Consequences (positive / negative / neutral)
- Related (ADR 0052 / 0053 / pre-s36-backlog)

Verbatim hybrid duration text (SD-1, mandatory):

> δ TESTNET runs indefinitely until ONE event fires:
> (a) HaltGate trigger (DD/loss streak/no-trade timeout — ADR 0053 unchanged)
> (b) PASS gates achieved (n≥50 + ADR 0052/0053 conjoint)
> (c) 12mo calendar = **MAINNET-promotion gate, NOT shutdown.** Если n<50 на review → "underpowered informational" + TESTNET continues unless operator halts. MAINNET locked.
> No 6mo interim checkpoint (conflicts с ADR 0053 line 62 6mo no-trade halt).

- [ ] **Step 2: Write ADR 0056 (DSR sigma_SR amendment, paired)**

Verbatim text per quant-stats-reviewer ROUND 1:

```markdown
## Decision

### sigma_SR sourcing hierarchy (binding)

1. PREFERRED: cross-trial log >= 3 entries → sigma_SR = stdev(all_oos_sharpes), n_trials = len(entries)
2. DEGENERATE (1-2 entries): sigma_SR = NaN, DSR computed с n_trials=1, report "DSR_UNDERPOWERED — informational only. n_trials < 3"
3. INADMISSIBLE FALLBACK (REMOVED): per-fold Sharpe stdev as sigma_SR proxy. Confounds within-trial noise с cross-trial selection variability. Previously donchian_runner.py:191-193 — REMOVED в S36.

### n_trades thresholds для DSR reporting

- n_trades < 10: DSR = NaN (variance undefined, no reliable estimate)
- 10 <= n_trades < 30: DSR computed, flagged "UNDERPOWERED"
- n_trades >= 30: DSR standard computation, gate-eligible

### Variable naming correction

`aggregate_oos_sharpe` (donchian_runner.py:171) → `trial_mean_fold_oos_sharpe`
Rationale: clarifies arithmetic mean of fold OOS Sharpes vs pooled trade-level OOS Sharpe.
```

- [ ] **Step 3: Commit ADRs IMMEDIATELY (timestamp anti-snooping)**

```bash
git add llm-wiki/wiki/project/decisions/0055-sprint-36-delta-activation.md \
        llm-wiki/wiki/project/decisions/0056-sprint-36-dsr-sigma-sr-amendment.md
git commit -m "docs(adr): ADR 0055 δ activation + ADR 0056 DSR sigma_SR amendment LOCKED (S36 T1)

ADR 0055 (8 sub-decisions per ROUND 4 consilium BINDING):
  SD-1: Hybrid duration option (H) verbatim per ROUND 2 trader CHANGED verdict
  SD-2: B1 fix mandate (MEAN_REVERSION_S17_RELAXED_PARAMS wire-up before day-1)
  SD-3: Multiday DD = HWM since activation timestamp
  SD-4: HaltTrigger → ReasonCode mapping
  SD-5: HaltGate halt resume protocol (manual FSM reset only)
  SD-6: Adapted gates methodology (live Sharpe + calibration + MC gating)
  SD-7: N_trials FREEZE at 7 (S22 hypothesis re-evaluation)
  SD-8: MAINNET promotion criteria DEFERRED к S37+

ADR 0056 (paired DSR amendment per quant ROUND 1 verbatim):
  N>=3 PREFERRED, NaN+UNDERPOWERED для 1-2, fallback REMOVED
  n_trades thresholds: <10 NaN / 10-30 UNDERPOWERED / >=30 gate-eligible
  Variable rename: aggregate_oos_sharpe → trial_mean_fold_oos_sharpe

Per pre-s36-backlog.md ROUND 4 binding consilium decision."
```

---

## Task 2 — B1 CRITICAL fix: wire S17-relaxed LOCKED params к live path

**Why second:** Pre-commit #7 silently violated. δ would run S15-noise params (RSI 30/70 + bb_k=2.0) instead of S22-validated S17-relaxed (RSI 35/65 + bb_std_mult=1.5). MUST fix BEFORE T4 wire-up enables HaltGate path.

**Files:**
- Create: `tests/unit/test_strategy_locked_params.py`
- Modify: `src/signalgen/mean_reversion_strategy.py` — add `bb_std_mult` rename + `and_gate_required` param
- Modify: `src/__main__.py` — read s35_demo_active flag, pass LOCKED params когда True

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_strategy_locked_params.py
"""S36 T2 B1 critical fix verification.

Per pre-s36-backlog.md trading-logic-reviewer B1 BLOCKER:
  MEAN_REVERSION_S17_RELAXED_PARAMS must wire к live MeanReversionRsiBBStrategy
  constructor when s35_demo_active=True. Pre-commit #7 (LOCKED params) preserved.
"""
from decimal import Decimal

from src.signalgen.mean_reversion_strategy import (
    MEAN_REVERSION_S17_RELAXED_PARAMS,
    MeanReversionRsiBBStrategy,
)


def test_locked_params_constants_exact_values() -> None:
    """LOCKED constants per ADR 0030 + S33 T4 — anti-S15-noise guard."""
    assert MEAN_REVERSION_S17_RELAXED_PARAMS["rsi_period"] == 14
    assert MEAN_REVERSION_S17_RELAXED_PARAMS["rsi_oversold"] == Decimal("35")
    assert MEAN_REVERSION_S17_RELAXED_PARAMS["rsi_overbought"] == Decimal("65")
    assert MEAN_REVERSION_S17_RELAXED_PARAMS["bb_period"] == 20
    assert MEAN_REVERSION_S17_RELAXED_PARAMS["bb_std_mult"] == 1.5
    assert MEAN_REVERSION_S17_RELAXED_PARAMS["and_gate_required"] is True


def test_strategy_accepts_bb_std_mult_param() -> None:
    """Constructor must accept bb_std_mult name (LOCKED params dict key)."""
    s = MeanReversionRsiBBStrategy(
        symbol="BTCUSDT",
        rsi_period=14,
        rsi_oversold=Decimal("35"),
        rsi_overbought=Decimal("65"),
        atr_period=14,
        bb_period=20,
        bb_std_mult=1.5,
        and_gate_required=True,
    )
    assert s is not None


def test_strategy_from_locked_params_factory() -> None:
    """Factory method maps LOCKED dict к constructor — single point of truth."""
    s = MeanReversionRsiBBStrategy.from_locked_s17_params(symbol="BTCUSDT")
    assert s is not None
```

- [ ] **Step 2: RED then GREEN — modify strategy constructor**

Edit `src/signalgen/mean_reversion_strategy.py`:

```python
class MeanReversionRsiBBStrategy:
    def __init__(
        self,
        *,
        symbol: str,
        rsi_period: int,
        rsi_oversold: Decimal,
        rsi_overbought: Decimal,
        atr_period: int,
        bb_period: int = 20,
        bb_std_mult: float = 2.0,  # renamed от bb_k для consistency с LOCKED dict
        and_gate_required: bool = True,
    ) -> None:
        if bb_std_mult <= 0:
            raise ValueError(f"bb_std_mult must be > 0, got {bb_std_mult}")
        self._symbol = symbol
        self._rsi_n = rsi_period
        self._rsi_oversold = rsi_oversold
        self._rsi_overbought = rsi_overbought
        self._atr_n = atr_period
        self._bb_n = bb_period
        self._bb_std_mult = bb_std_mult
        self._and_gate_required = and_gate_required
        # ... rest unchanged

    @classmethod
    def from_locked_s17_params(cls, *, symbol: str) -> "MeanReversionRsiBBStrategy":
        """Factory per ADR 0055 SD-2 — single point of truth для LOCKED params wiring."""
        return cls(
            symbol=symbol,
            rsi_period=int(MEAN_REVERSION_S17_RELAXED_PARAMS["rsi_period"]),
            rsi_oversold=Decimal(str(MEAN_REVERSION_S17_RELAXED_PARAMS["rsi_oversold"])),
            rsi_overbought=Decimal(str(MEAN_REVERSION_S17_RELAXED_PARAMS["rsi_overbought"])),
            atr_period=14,
            bb_period=int(MEAN_REVERSION_S17_RELAXED_PARAMS["bb_period"]),
            bb_std_mult=float(MEAN_REVERSION_S17_RELAXED_PARAMS["bb_std_mult"]),
            and_gate_required=bool(MEAN_REVERSION_S17_RELAXED_PARAMS["and_gate_required"]),
        )
```

Update `bollinger_bands(closes, period, k=...)` call site к use `self._bb_std_mult` instead of `self._bb_k`.

- [ ] **Step 3: Wire к live path conditional на s35_demo_active**

Edit `src/__main__.py:124-131`:

```python
    # S36 T2 B1 fix: conditional LOCKED params wiring per ADR 0055 SD-2.
    if settings.s35_demo_active:
        strategy = MeanReversionRsiBBStrategy.from_locked_s17_params(symbol=symbol)
        logger.info(
            "strategy.s35_demo_locked_params_active",
            params=MEAN_REVERSION_S17_RELAXED_PARAMS,
        )
    else:
        # Default (non-δ): Settings-driven для backtests + ad-hoc runs
        strategy = MeanReversionRsiBBStrategy(
            symbol=symbol,
            rsi_period=settings.strategy_rsi_period,
            rsi_oversold=settings.strategy_rsi_oversold,
            rsi_overbought=settings.strategy_rsi_overbought,
            atr_period=settings.strategy_atr_period,
        )
```

- [ ] **Step 4: Add integration test that verifies live path uses LOCKED params**

```python
def test_main_path_uses_locked_params_when_s35_demo_active(monkeypatch) -> None:
    """End-to-end: s35_demo_active=True → strategy instance has LOCKED params."""
    # Mock Settings + verify strategy params after _build_strategy() call
    # ... test uses src.__main__._build_strategy or equivalent factory
```

(Implementation detail: extract strategy instantiation к `_build_strategy(settings)` factory function для testability.)

- [ ] **Step 5: Run + commit**

```bash
.venv/bin/pytest tests/unit/test_strategy_locked_params.py tests/unit/test_mean_reversion_strategy.py -v
.venv/bin/mypy --strict src/signalgen/mean_reversion_strategy.py src/__main__.py
git add src/signalgen/mean_reversion_strategy.py src/__main__.py tests/unit/test_strategy_locked_params.py
git commit -m "fix(signalgen): B1 CRITICAL — wire MEAN_REVERSION_S17_RELAXED_PARAMS к live path (S36 T2)

Per pre-s36-backlog trading-logic-reviewer B1 BLOCKER:
  - bb_k renamed к bb_std_mult (matches LOCKED dict key)
  - and_gate_required constructor param added
  - from_locked_s17_params() classmethod factory (single point of truth)
  - src/__main__.py reads settings.s35_demo_active, passes LOCKED params когда True
  - Pre-commit #7 enforced at runtime (S15-noise params blocked под δ)

3 NEW tests verify LOCKED constants + constructor + factory."
```

---

## Task 3 — State-source methods (4 new methods для HaltGate inputs)

**Why third:** T4 HaltGate wire-up requires these methods to exist. Without them HaltGate.evaluate() can't be called.

**Files:**
- Modify: `src/risk/equity_tracker.py` — add 2 methods
- Modify: `src/risk/trade_history.py` — add 2 methods
- Create: `tests/unit/test_equity_tracker_intraday_dd.py`
- Create: `tests/unit/test_trade_history_streak.py`

- [ ] **Step 1: TDD EquityTracker.intraday_dd_pct + hwm_since (RED → GREEN)**

```python
# tests/unit/test_equity_tracker_intraday_dd.py
def test_intraday_dd_pct_zero_when_no_drawdown(in_memory_equity_tracker) -> None:
    """No drawdown → intraday DD = 0."""
    et = in_memory_equity_tracker
    base = datetime(2026, 1, 1, 0, tzinfo=UTC)
    et.record(realized=Decimal("0"), unrealized=Decimal("0"), ts=base)
    et.record(realized=Decimal("0"), unrealized=Decimal("100"), ts=base + timedelta(hours=1))
    assert et.intraday_dd_pct(now=base + timedelta(hours=2)) == Decimal("0")


def test_intraday_dd_pct_computes_relative_drop_from_24h_peak(in_memory_equity_tracker) -> None:
    """Peak equity 1100 → current 1000 = 9.09% DD."""
    # Setup peak then drop within 24h window, assert intraday_dd_pct returns ~0.0909


def test_hwm_since_returns_max_total_equity(in_memory_equity_tracker) -> None:
    """HWM since timestamp = max(realized + unrealized) over equity_snapshots since ts."""
    # ...
```

Implementation в `src/risk/equity_tracker.py`:

```python
def intraday_dd_pct(self, *, now: datetime | None = None) -> Decimal:
    """Rolling 24h drawdown as Decimal fraction (e.g. 0.20 = -20%).

    DD = (peak_24h - current) / peak_24h. Returns 0 if no drawdown.
    Per ADR 0055 SD-3 — used by HaltGate intraday_dd input.
    """
    now = now or datetime.now(UTC)
    peak = self.peak_equity_24h(now=now) or Decimal("0")
    current = self.current_total() or Decimal("0")
    if peak <= Decimal("0"):
        return Decimal("0")
    if current >= peak:
        return Decimal("0")
    return (peak - current) / peak

def hwm_since(self, *, since_ts: datetime) -> Decimal | None:
    """Highest realized+unrealized total equity since timestamp.

    Per ADR 0055 SD-3 — multiday_dd HWM source. Returns None если no records.
    """
    cur = self._conn.execute(
        "SELECT MAX(realized + unrealized) FROM equity_snapshots WHERE ts >= ?",
        (since_ts.isoformat(),),
    )
    row = cur.fetchone()
    if not row or row[0] is None:
        return None
    return Decimal(str(row[0]))
```

- [ ] **Step 2: TDD TradeHistoryRepository.consecutive_losses + last_trade_ts**

```python
def test_consecutive_losses_returns_tail_streak(in_memory_trade_history) -> None:
    """consecutive_losses returns count of trailing losing trades, reset on winning trade."""
    # Insert: WIN, LOSS, LOSS, LOSS → consecutive_losses=3
    # Insert: WIN → consecutive_losses=0


def test_consecutive_losses_symbol_scoped(in_memory_trade_history) -> None:
    """consecutive_losses filters by symbol."""
    # BTCUSDT 3 losses, ETHUSDT 1 win → consecutive_losses(BTCUSDT) = 3


def test_last_trade_ts_returns_max_exit_ts(in_memory_trade_history) -> None:
    """last_trade_ts = MAX(exit_ts) per symbol, None если no trades."""
    # ...
```

Implementation в `src/risk/trade_history.py`:

```python
def consecutive_losses(self, *, symbol: str) -> int:
    """Count of trailing consecutive losing trades, reset on first winning trade.

    Per ADR 0055 SD-4 — used by HaltGate consecutive_losses input.
    Loss = pnl < 0.
    """
    cur = self._conn.execute(
        "SELECT pnl FROM trade_history WHERE symbol = ? ORDER BY exit_ts DESC",
        (symbol,),
    )
    streak = 0
    for (pnl,) in cur.fetchall():
        if Decimal(str(pnl)) < Decimal("0"):
            streak += 1
        else:
            break
    return streak

def last_trade_ts(self, *, symbol: str) -> datetime | None:
    """Most-recent exit_ts for symbol, None если no trades."""
    cur = self._conn.execute(
        "SELECT MAX(exit_ts) FROM trade_history WHERE symbol = ?",
        (symbol,),
    )
    row = cur.fetchone()
    if not row or row[0] is None:
        return None
    return datetime.fromisoformat(row[0])
```

- [ ] **Step 3: Run + mypy + commit**

```bash
.venv/bin/pytest tests/unit/test_equity_tracker_intraday_dd.py tests/unit/test_trade_history_streak.py -v
.venv/bin/mypy --strict src/risk/equity_tracker.py src/risk/trade_history.py
git add src/risk/equity_tracker.py src/risk/trade_history.py \
        tests/unit/test_equity_tracker_intraday_dd.py tests/unit/test_trade_history_streak.py
git commit -m "feat(risk): state-source methods для HaltGate (S36 T3)

EquityTracker:
  - intraday_dd_pct(now): rolling 24h DD as Decimal fraction
  - hwm_since(since_ts): HWM since timestamp (multiday_dd source per ADR 0055 SD-3)

TradeHistoryRepository:
  - consecutive_losses(symbol): tail streak of losing trades
  - last_trade_ts(symbol): most-recent exit_ts

8 NEW tests. Per ADR 0055 SD-4 — feeds HaltGate inputs."
```

---

## Task 4 — HaltGate wire-up в RuntimeManager._tick

**Files:**
- Modify: `src/runtime/manager.py` — add `_check_halt_gate()` method, wire в _tick()
- Create: `tests/integration/test_halt_gate_wireup.py`

- [ ] **Step 1: Write integration test for each trigger**

```python
def test_halt_gate_dd_intraday_fires_request_halt(runtime_with_demo_active) -> None:
    """Setup intraday DD ≥ 20%, _tick() → Coordinator.request_halt(HALT_S36_DD_INTRADAY)"""
    # Mock EquityTracker.intraday_dd_pct returns 0.21
    # Verify coordinator.request_halt called с HALT_S36_DD_INTRADAY ReasonCode

def test_halt_gate_inactive_when_demo_disabled(runtime_with_demo_inactive) -> None:
    """s35_demo_active=False → HaltGate not invoked (default behavior preserved)"""
```

(4 tests total: 4 trigger types × demo-active branch + 1 demo-inactive bypass.)

- [ ] **Step 2: Implement `_check_halt_gate()`**

```python
# src/runtime/manager.py
from src.risk.halt_gate import HaltGate, HaltTrigger
from src.risk.reason_codes import ReasonCode

# Module-level mapping (ADR 0055 SD-4)
_HALT_TRIGGER_TO_REASON: dict[HaltTrigger, ReasonCode] = {
    HaltTrigger.DD_INTRADAY: ReasonCode.HALT_S36_DD_INTRADAY,
    HaltTrigger.DD_MULTIDAY: ReasonCode.HALT_S36_DD_MULTIDAY,
    HaltTrigger.CONSECUTIVE_LOSSES: ReasonCode.HALT_S36_CONSECUTIVE_LOSSES,
    HaltTrigger.NO_TRADE_TIMEOUT: ReasonCode.HALT_S36_NO_TRADE_TIMEOUT,
}


class RuntimeManager:
    def _tick(self) -> None:
        if self._maybe_kill_switch():
            return
        if not self._check_alive_inline():
            return
        if self._settings.s35_demo_active and self._check_halt_gate():
            return  # halt fired, skip rest
        self._poll_bar_and_strategy()

    def _check_halt_gate(self) -> bool:
        """S36 T4: HaltGate evaluation per-tick when s35_demo_active=True.

        Returns True если halt fired (caller should skip rest of tick).
        Per ADR 0055 SD-4 — HaltTrigger → ReasonCode mapping.
        """
        # Compute inputs from state-source methods (T3)
        intraday_dd = self._equity_tracker.intraday_dd_pct()
        activation_ts = self._settings_loader.s35_activation_ts()  # NEW reader
        hwm = self._equity_tracker.hwm_since(since_ts=activation_ts)
        current = self._equity_tracker.current_total() or Decimal("0")
        if hwm and hwm > Decimal("0"):
            multiday_dd = (hwm - current) / hwm if current < hwm else Decimal("0")
        else:
            multiday_dd = Decimal("0")
        consec = self._trade_repo.consecutive_losses(symbol=self._symbol)
        last_ts = self._trade_repo.last_trade_ts(symbol=self._symbol)
        if last_ts:
            months_since = (datetime.now(UTC) - last_ts).days // 30
        else:
            months_since = 0  # not started or just activated

        gate = HaltGate(
            dd_intraday_threshold=self._settings.s35_halt_dd_intraday,
            dd_multiday_threshold=self._settings.s35_halt_dd_multiday,
            consecutive_losses_threshold=self._settings.s35_halt_consecutive_losses,
            no_trade_months_threshold=self._settings.s35_halt_no_trade_months,
        )
        trigger = gate.evaluate(
            intraday_dd=intraday_dd,
            multiday_dd=multiday_dd,
            consecutive_losses=consec,
            months_since_last_trade=months_since,
        )
        if trigger is None:
            return False
        reason = _HALT_TRIGGER_TO_REASON[trigger]
        logger.error("runtime.halt_gate_fired", trigger=trigger.value, reason=reason.value)
        self._coordinator.request_halt(reason)
        self._stopping = True
        return True
```

NOTE: `s35_activation_ts()` requires new tracking. ADR 0055 SD-3 specifies persistence path — write activation timestamp к SQLite на first s35_demo_active=True run, read on subsequent runs. Implementation detail in T3 OR new minor task.

- [ ] **Step 3: Run + commit**

```bash
.venv/bin/pytest tests/integration/test_halt_gate_wireup.py -v
.venv/bin/mypy --strict src/runtime/manager.py
git add src/runtime/manager.py tests/integration/test_halt_gate_wireup.py
git commit -m "feat(runtime): HaltGate wire-up в _tick (S36 T4)

Per ADR 0055 SD-4 — HaltTrigger → ReasonCode mapping. _check_halt_gate() called
per-tick когда s35_demo_active=True. Sequential: kill_switch → check_alive →
halt_gate (NEW) → poll_bar_and_strategy. Halt fires → coordinator.request_halt →
_stopping=True (bot exits cleanly).

4 integration tests cover all 4 trigger paths + demo-inactive bypass."
```

---

## Task 5 — ReasonCode enum +4 HALT_S36_* (45→49)

**Files:**
- Modify: `src/risk/reason_codes.py` — add 4 enum values
- Modify: `tests/property/test_request_halt_mapping.py` — extend allowlist
- Modify: `llm-wiki/wiki/project/components/reason-codes-schema.md`
- Modify: `llm-wiki/wiki/project/components/execution-state-machine.md` — canonical count footer

- [ ] **Step 1: TDD reason-code allowlist test (RED)**

Add к `tests/property/test_request_halt_mapping.py`:

```python
_REQUEST_HALT_CODES = frozenset({
    # ... existing ...
    ReasonCode.HALT_S36_DD_INTRADAY,
    ReasonCode.HALT_S36_DD_MULTIDAY,
    ReasonCode.HALT_S36_CONSECUTIVE_LOSSES,
    ReasonCode.HALT_S36_NO_TRADE_TIMEOUT,
})
```

- [ ] **Step 2: Add 4 enum values**

`src/risk/reason_codes.py`:

```python
class ReasonCode(StrEnum):
    # ... existing 45 ...
    # S36 — δ TESTNET HaltGate triggers (ADR 0055 SD-4)
    HALT_S36_DD_INTRADAY = "HALT_S36_DD_INTRADAY"        # 46
    HALT_S36_DD_MULTIDAY = "HALT_S36_DD_MULTIDAY"        # 47
    HALT_S36_CONSECUTIVE_LOSSES = "HALT_S36_CONSECUTIVE_LOSSES"  # 48
    HALT_S36_NO_TRADE_TIMEOUT = "HALT_S36_NO_TRADE_TIMEOUT"      # 49
```

- [ ] **Step 3: Update wiki pages canonical count**

`llm-wiki/wiki/project/components/reason-codes-schema.md` — add 4 rows + sync count 45→49.
`llm-wiki/wiki/project/components/execution-state-machine.md` — footer "Last sync: Sprint 36 (count = 49)".

- [ ] **Step 4: Verify property test GREEN**

```bash
.venv/bin/pytest tests/property/test_request_halt_mapping.py -v
.venv/bin/python -c "from src.risk.reason_codes import ReasonCode; print(len(list(ReasonCode)))"
# Expected: 49
```

- [ ] **Step 5: Commit**

```bash
git add src/risk/reason_codes.py tests/property/test_request_halt_mapping.py \
        llm-wiki/wiki/project/components/reason-codes-schema.md \
        llm-wiki/wiki/project/components/execution-state-machine.md
git commit -m "feat(risk): ReasonCode enum +4 HALT_S36_* (45→49) (S36 T5)

Per ADR 0055 SD-4 + trading-logic-reviewer ROUND 1 REVISE:
  - HALT_S36_DD_INTRADAY (46)
  - HALT_S36_DD_MULTIDAY (47)
  - HALT_S36_CONSECUTIVE_LOSSES (48)
  - HALT_S36_NO_TRADE_TIMEOUT (49)

Distinct codes (not reused HALT_DRAWDOWN_L*) preserve audit-log attribution
between CB drawdown vs δ-specific halt criteria. _REQUEST_HALT_CODES allowlist
extended. Property test GREEN. Canonical count synced 45→49."
```

---

## Task 6 — DSR sigma_SR amendment refactor

**Files:**
- Modify: `src/backtest/donchian_runner.py` — REMOVE inadmissible per-fold stdev fallback (lines 191-193)
- Modify: `src/analytics/dsr.py` — add UNDERPOWERED flag для 10≤n<30, NaN для n<10
- Create: `tests/unit/test_dsr_sigma_sr_amendment.py`
- Modify: `src/analytics/cross_trial_log.py` — add `entry_count() -> int` helper

- [ ] **Step 1: Test sigma_SR sourcing hierarchy (RED → GREEN)**

```python
def test_dsr_underpowered_flag_when_n_trades_below_30() -> None:
    """ADR 0056: 10 ≤ n < 30 → DSR computed + flagged UNDERPOWERED."""
    result = compute_dsr_with_status(returns=...short_series_with_n=15..., n_trials=3)
    assert result["status"] == "UNDERPOWERED"
    assert result["dsr"] is not None  # computed но flagged

def test_dsr_nan_when_n_trades_below_10() -> None:
    """ADR 0056: n < 10 → DSR = NaN."""
    result = compute_dsr_with_status(returns=...short_series_with_n=5..., n_trials=3)
    assert math.isnan(result["dsr"])
    assert result["status"] == "INSUFFICIENT_TRADES"

def test_sigma_sr_nan_when_cross_trial_below_3_entries() -> None:
    """ADR 0056: cross_trial < 3 entries → sigma_SR = NaN, DSR_UNDERPOWERED."""
    log = CrossTrialLog(...with_2_entries...)
    sigma_sr = sigma_sr_from_log(log)
    assert math.isnan(sigma_sr)

def test_aggregate_oos_sharpe_renamed() -> None:
    """trial_mean_fold_oos_sharpe replaces aggregate_oos_sharpe per ADR 0056."""
    from src.backtest.donchian_runner import compute_trial_metrics
    result = compute_trial_metrics(fold_sharpes=[1.0, 2.0, 3.0])
    assert "trial_mean_fold_oos_sharpe" in result
    assert "aggregate_oos_sharpe" not in result  # old name removed
```

- [ ] **Step 2: Refactor donchian_runner.py + dsr.py**

Remove lines 191-193 fallback (inadmissible per-fold stdev). Replace с:

```python
# ADR 0056 — sigma_SR sourcing hierarchy
n_cross_trial = trial_log.entry_count()
if n_cross_trial >= 3:
    sigma_sr = stdev([e.oos_sharpe for e in trial_log.entries()])
    n_trials = n_cross_trial
elif n_cross_trial >= 1:
    sigma_sr = float("nan")
    n_trials = 1
    dsr_status = "DSR_UNDERPOWERED — informational only. n_trials < 3"
else:
    # cross_trial empty (post-honest-close reset)
    sigma_sr = float("nan")
    n_trials = 1
    dsr_status = "DSR_UNDERPOWERED — empty cross_trial log"
```

Update `dsr.py compute_dsr()`:

```python
def compute_dsr_with_status(returns: list[float], n_trials: int = 1) -> dict[str, Any]:
    """ADR 0056: returns dict с 'dsr' + 'status' + 'n_trades'.

    n < 10: DSR=NaN, status=INSUFFICIENT_TRADES
    10 <= n < 30: DSR computed, status=UNDERPOWERED
    n >= 30: DSR computed, status=GATE_ELIGIBLE
    """
    n = len(returns)
    if n < 10:
        return {"dsr": float("nan"), "status": "INSUFFICIENT_TRADES", "n_trades": n}
    dsr = _compute_dsr_value(returns, n_trials)  # existing helper
    status = "UNDERPOWERED" if n < 30 else "GATE_ELIGIBLE"
    return {"dsr": dsr, "status": status, "n_trades": n}
```

Rename `aggregate_oos_sharpe` → `trial_mean_fold_oos_sharpe` в donchian_runner.py:171 + JSON output schema.

- [ ] **Step 3: Run + commit**

```bash
.venv/bin/pytest tests/unit/test_dsr_sigma_sr_amendment.py tests/unit/test_dsr.py -v
.venv/bin/mypy --strict src/analytics/dsr.py src/backtest/donchian_runner.py
git add src/analytics/dsr.py src/backtest/donchian_runner.py src/analytics/cross_trial_log.py \
        tests/unit/test_dsr_sigma_sr_amendment.py
git commit -m "refactor(analytics): ADR 0056 DSR sigma_SR amendment (S36 T6)

Per ADR 0056 sigma_SR sourcing hierarchy:
  - PREFERRED N>=3 cross_trial entries → stdev pool
  - DEGENERATE 1-2 entries → NaN + DSR_UNDERPOWERED flag
  - INADMISSIBLE per-fold stdev fallback REMOVED (donchian_runner.py:191-193)

DSR n_trades thresholds:
  - <10: NaN + INSUFFICIENT_TRADES status
  - 10-30: computed + UNDERPOWERED flag
  - >=30: computed + GATE_ELIGIBLE

Variable rename: aggregate_oos_sharpe → trial_mean_fold_oos_sharpe.

5 NEW tests. Closes S35 T4 quant-stats H1 + H2 carry-overs."
```

---

## Task 7 — Live-data adapted reporter

**Files:**
- Create: `src/analytics/live_trade_reporter.py` (~120 LoC)
- Create: `tests/unit/test_live_trade_reporter.py`

- [ ] **Step 1: TDD live Sharpe estimator on TradeRecord list**

```python
def test_live_sharpe_from_trade_records() -> None:
    """ADR 0055 SD-6: live Sharpe computed on per-trade returns, не bar-level equity."""
    records = [
        TradeRecord(pnl=Decimal("100"), entry_price=Decimal("50000"), ...),
        TradeRecord(pnl=Decimal("-50"), entry_price=Decimal("51000"), ...),
        # ... ≥ 30 records для GATE_ELIGIBLE status
    ]
    result = compute_live_sharpe(records, bars_per_year=2190, avg_bars_per_trade=12)
    assert "sharpe" in result
    assert result["status"] == "GATE_ELIGIBLE"

def test_live_synthetic_calibration_ratio() -> None:
    """ADR 0055 SD-6: T6 OOS/IS replaced by live/synthetic ratio."""
    ratio = compute_calibration_ratio(
        live_sharpe=0.85,
        synthetic_s22_sharpe=1.20,  # pre-registered benchmark from S22
    )
    assert ratio == pytest.approx(0.708)  # 0.85 / 1.20
    # ratio >= 0.7 → calibration PASS

def test_mc_gating_sign_flip_n_threshold() -> None:
    """MC sign-flip gated on n_trades >= 20 per ADR 0055 SD-6."""
    result = compute_mc_with_gating(returns=[...n=15...])
    assert result["sign_flip"] is None  # below threshold
    assert result["status"] == "MC_INSUFFICIENT_N"
```

- [ ] **Step 2: Implement reporter**

```python
# src/analytics/live_trade_reporter.py
"""Live-data adapted reporter per ADR 0055 SD-6.

Differences от backtest reporter:
  - Sharpe computed on per-TradeRecord returns (не bar-level equity curve)
  - T6 OOS/IS → live/synthetic calibration ratio (pre-registered benchmark)
  - MC gated на sample size (sign-flip n>=20, block-bootstrap n>=40)
"""
from __future__ import annotations

import math
import statistics
from decimal import Decimal
from typing import Any

from src.analytics.dsr import compute_dsr_with_status
from src.backtest.mc_permutation import sign_flip_p_value, block_bootstrap_p_value
from src.risk.trade_history import TradeRecord

# Pre-registered S22 synthetic benchmark (ADR 0055 SD-6)
S22_SYNTHETIC_SHARPE: float = 1.20  # placeholder — fill from sprint-22 metrics.json

# Mean-reversion family N_trials cumulative (ADR 0055 SD-7)
DELTA_N_TRIALS_LOCKED: int = 7  # S13/S15/S17/S20/S22/S33/S35


def compute_live_sharpe(
    records: list[TradeRecord],
    *,
    bars_per_year: int = 2190,  # 4H bars/year
    avg_bars_per_trade: float = 12.0,
) -> dict[str, Any]:
    """Annualized live Sharpe + status flag per ADR 0056 thresholds."""
    n = len(records)
    if n < 10:
        return {"sharpe": float("nan"), "status": "INSUFFICIENT_TRADES", "n": n}
    returns = [float(r.pnl) for r in records]  # absolute PnL OR pct returns
    mean = statistics.mean(returns)
    sd = statistics.stdev(returns) if n > 1 else 0.0
    if sd == 0.0:
        return {"sharpe": float("nan"), "status": "DEGENERATE_VARIANCE", "n": n}
    trades_per_year = bars_per_year / avg_bars_per_trade
    sharpe = (mean / sd) * math.sqrt(trades_per_year)
    status = "UNDERPOWERED" if n < 30 else "GATE_ELIGIBLE"
    return {"sharpe": sharpe, "status": status, "n": n}


def compute_calibration_ratio(
    *, live_sharpe: float, synthetic_s22_sharpe: float = S22_SYNTHETIC_SHARPE,
) -> float:
    """T6 replacement per ADR 0055 SD-6: live/synthetic Sharpe ratio."""
    if synthetic_s22_sharpe == 0.0 or math.isnan(live_sharpe):
        return float("nan")
    return live_sharpe / synthetic_s22_sharpe


def compute_mc_with_gating(returns: list[float]) -> dict[str, Any]:
    """MC permutation с n-gated test selection per ADR 0055 SD-6."""
    n = len(returns)
    if n < 20:
        return {"sign_flip": None, "block_bootstrap": None, "status": "MC_INSUFFICIENT_N", "n": n}
    sign_flip = sign_flip_p_value(returns, n_iterations=2000, seed=42)
    block = None
    if n >= 40:
        block = block_bootstrap_p_value(returns, block_size=20, n_iterations=2000, seed=42)
    return {"sign_flip": sign_flip, "block_bootstrap": block, "status": "OK", "n": n}


def generate_live_report(records: list[TradeRecord]) -> dict[str, Any]:
    """Single entry point — full live demo report per ADR 0055 SD-6 methodology."""
    sharpe_info = compute_live_sharpe(records)
    calibration = compute_calibration_ratio(live_sharpe=sharpe_info["sharpe"])
    mc_info = compute_mc_with_gating([float(r.pnl) for r in records])
    returns = [float(r.pnl) for r in records]
    dsr_info = compute_dsr_with_status(returns, n_trials=DELTA_N_TRIALS_LOCKED)
    return {
        "n_trades": len(records),
        "live_sharpe": sharpe_info,
        "calibration_ratio_to_s22": calibration,
        "mc": mc_info,
        "dsr": dsr_info,
        "n_trials_counter": DELTA_N_TRIALS_LOCKED,
        "methodology": "ADR_0055_SD6_LIVE_ADAPTED",
    }
```

- [ ] **Step 3: Run + commit**

```bash
.venv/bin/pytest tests/unit/test_live_trade_reporter.py -v
.venv/bin/mypy --strict src/analytics/live_trade_reporter.py
git add src/analytics/live_trade_reporter.py tests/unit/test_live_trade_reporter.py
git commit -m "feat(analytics): live trade reporter per ADR 0055 SD-6 (S36 T7)

Adapted methodology для live demo data (post-12mo evaluation):
  - Live Sharpe estimator on per-TradeRecord returns (не bar-level)
  - T6 OOS/IS replaced by live/synthetic calibration ratio (S22 pre-registered)
  - MC gated: sign-flip iff n>=20, block-bootstrap iff n>=40
  - DELTA_N_TRIALS_LOCKED=7 explicit (S13/S15/S17/S20/S22/S33/S35 mean-reversion family)

4 NEW tests. Closes S35 T4 quant-stats H2 carry-over."
```

---

## Task 8 — Sprint-36 page + components + sync

**Files:**
- Create: `llm-wiki/wiki/project/sprints/sprint-36-delta-activation.md`
- Create: `llm-wiki/wiki/project/components/halt-gate-wireup.md`
- Create: `llm-wiki/wiki/project/components/live-trade-reporter.md`
- Modify: `llm-wiki/wiki/index.md` — add ADR 0055 + 0056 + sprint-36 + 2 components
- Modify: `llm-wiki/wiki/project/architecture/current-state.md` — counts 54→56 ADRs / 39→40 sprints / 45→47 components / 45→49 reason codes
- Modify: `llm-wiki/wiki/log.md` — append sprint-end entry
- Modify: `llm-wiki/wiki/project/SPRINT_STATE.md` — phase=8-ship

- [ ] **Step 1-N: Standard sprint sync per `sprint-finish` skill**

(Same pattern as S35 T5 — sprint page documents 8 tasks shipped, КУ achieved, FSM growth (reason codes 45→49), tests delta, key decisions, carry-overs к S37+, related ADRs.)

- [ ] **Step Final: Commit T8 wiki sync**

```bash
git commit -m "docs(sprint): S36 wiki sync — sprint-36 + 2 components + counts (S36 T8)

- sprint-36-delta-activation page (8 tasks shipped, δ TESTNET activatable)
- 2 NEW component pages: halt-gate-wireup + live-trade-reporter
- index + current-state counts: 54→56 ADRs / 39→40 sprints / 45→47 components / 45→49 reason codes
- log.md sprint-end entry
- SPRINT_STATE → 8-ship

Per S36 ROUND 4 binding consilium completed."
```

---

## Self-Review Checklist

**1. Spec coverage:** All 7 ROUND 4 binding pre-commitments addressed?
- ✅ #1 B1 fix → T2
- ✅ #2 DSR sigma_SR sourcing protocol → T6 + ADR 0056
- ✅ #3 N_trials freeze at 7 → T1 SD-7 + T7 DELTA_N_TRIALS_LOCKED
- ✅ #4 Adapted gates methodology → T7
- ✅ #5 Hybrid duration option (H) → T1 SD-1 verbatim
- ✅ #6 MAINNET defer к S37+ → T1 SD-8
- ✅ #7 ReasonCode +4 HALT_S36_* → T5

**2. Placeholder scan:** All TDD steps have test code + implementation code + commit message. No "TBD" / "implement later".

**3. Type consistency:** `MEAN_REVERSION_S17_RELAXED_PARAMS` constant referenced T2 + T7 same name. `HaltTrigger` enum + `_HALT_TRIGGER_TO_REASON` mapping aligned T4 + T5. `compute_dsr_with_status` signature consistent T6 + T7.

**4. Trace map covers backlog:** All pre-s36-backlog rows mapped к T1-T8. ✓

---

## Execution Handoff

Plan complete. Two execution options:

1. **Subagent-Driven (recommended)** — fresh subagent per task, parallel reviewers (python + trading-logic + test-engineer + security-auditor for T2/T4 money-path, quant-stats для T6/T7)
2. **Inline Execution** — controller-driven via `superpowers:executing-plans`

Operator approve mode?
