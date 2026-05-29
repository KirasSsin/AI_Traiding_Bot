"""Risk module orchestrator.

Public API: update_equity, assess, on_bar_close, record_closed_trade,
            load_state, persist_state.
"""

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import ROUND_DOWN, Decimal
from sqlite3 import Connection
from typing import NamedTuple

from src.platform.config import Settings
from src.risk.circuit_breakers import CircuitBreakerConfig, CircuitBreakerDetector
from src.risk.equity_tracker import EquityTracker
from src.risk.kelly import KellyCaps, phase_adjusted_fraction, phase_from_trade_count, wilson_95_ci
from src.risk.models import HaltState, RiskAssessment
from src.risk.override import CbOverride, OverrideStore
from src.risk.reason_codes import ReasonCode
from src.risk.sizing import compute_qty
from src.risk.state_repo import StateRepository
from src.risk.trade_history import TradeHistoryRepository, TradeRecord
from src.signalgen.models import Signal, SignalSide

logger = logging.getLogger(__name__)


class RiskSharedDeps(NamedTuple):
    """S38 T4 ADR 0058 SD-3: shared risk infrastructure bundle для DI.

    Replaces RuntimeManager accessing risk_manager.equity_tracker / trade_repo /
    state_repo properties (Demeter violation per S37 T4 architecture-reviewer).

    Single bundle passed к both RiskManager (internal) и RuntimeManager (DI).
    """

    equity_tracker: EquityTracker
    trade_repo: TradeHistoryRepository
    state_repo: StateRepository


class RiskManager:
    """Orchestrates Kelly + CB + sizing + override resume."""

    def __init__(
        self,
        *,
        conn: Connection,
        settings: Settings,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        symbol: str | None = None,
    ) -> None:
        """RiskManager.

        S15 T1: `symbol` (optional, default None) — when set, _compute_p_b
        filters trade history к this symbol only (Kelly per-symbol isolation
        for multi-symbol replication pattern per ADR 0030). None preserves
        v0.1 behavior (single-symbol global Kelly).
        """
        self._conn = conn
        self._settings = settings
        self._clock = clock
        self._symbol = symbol
        self._kelly_caps = KellyCaps(
            phase1=settings.risk_kelly_phase1_cap,
            phase2=settings.risk_kelly_phase2_cap,
            phase3=settings.risk_kelly_phase3_cap,
            phase4=settings.risk_kelly_phase4_cap,
        )
        self._cb = CircuitBreakerDetector(
            CircuitBreakerConfig(
                l1_dd=settings.risk_cb_l1_dd,
                l2_dd=settings.risk_cb_l2_dd,
                l3_dd=settings.risk_cb_l3_dd,
                flash_abs=settings.risk_cb_flash_abs,
                flash_atr_mult=settings.risk_cb_flash_atr_mult,
            )
        )
        self._equity = EquityTracker(conn)
        self._trades = TradeHistoryRepository(conn)
        self._state = StateRepository(conn)
        self._override = OverrideStore(
            settings.risk_override_path,
            hmac_key=settings.risk_override_hmac_key,
        )
        self._current_halt: HaltState = HaltState.L0
        self._prev_close: Decimal | None = None

    # ------------------------------------------------------------------
    # DI accessors (S36 T4) — exposes shared SQLite-backed deps к RuntimeManager
    # для HaltGate wire-up (avoids duplicate connection instances + private attr leak).
    # ------------------------------------------------------------------

    @property
    def equity_tracker(self) -> EquityTracker:
        return self._equity

    @property
    def trade_repo(self) -> TradeHistoryRepository:
        return self._trades

    @property
    def state_repo(self) -> StateRepository:
        return self._state

    @property
    def shared_deps(self) -> RiskSharedDeps:
        """S38 T4 ADR 0058 SD-3: bundle accessor для RuntimeManager DI.

        Returns RiskSharedDeps NamedTuple wrapping все 3 internal repositories.
        Use as `RuntimeManager(shared_deps=risk_manager.shared_deps, ...)`.
        """
        return RiskSharedDeps(
            equity_tracker=self._equity,
            trade_repo=self._trades,
            state_repo=self._state,
        )

    # ------------------------------------------------------------------
    # State persistence
    # ------------------------------------------------------------------

    def load_state(self) -> None:
        """Restore halt level + prev_close from state table.

        Restoring `_prev_close` preserves flash-CB continuity across
        restart (otherwise the first bar after restart would silently
        skip flash detection).
        """
        cb = self._state.get("risk:cb:current_level")
        if cb:
            self._current_halt = HaltState(cb["level"])
        prev = self._state.get("risk:cb:prev_close")
        if prev:
            self._prev_close = Decimal(prev["value"])

    # ------------------------------------------------------------------
    # Equity update
    # ------------------------------------------------------------------

    def update_equity(self, *, realized: Decimal, unrealized: Decimal, ts: datetime) -> None:
        """Snapshot equity, evaluate drawdown, persist state atomically.

        Invariant #5 (risk-manager.md): equity snapshot + CB state are
        flushed in ONE SQLite transaction. If the state write fails, the
        equity snapshot rolls back — preventing stale halt levels against
        a higher peak on restart.
        """
        current = realized + unrealized
        # Compute halt BEFORE opening tx (read-only path uses peak_equity_24h
        # over committed data; new snapshot affects only future ticks).
        peak = self._equity.peak_equity_24h(now=ts) or current
        # Include the about-to-write current snapshot in the peak comparison.
        if current > peak:
            peak = current
        new_halt = self._cb.check_drawdown(peak=peak, current=current)

        if self._halt_severity(new_halt) > self._halt_severity(self._current_halt):
            self._current_halt = new_halt
            logger.warning(
                "CB level escalated to %s (peak=%s current=%s)",
                self._current_halt,
                peak,
                current,
            )

        # Atomic flush — equity snapshot + CB state in ONE transaction.
        with self._conn:
            self._equity.record_no_commit(
                realized=realized, unrealized=unrealized, ts=ts, source="BAR_CLOSE"
            )
            self._state.update_many_no_commit(
                {
                    "risk:cb:current_level": {
                        "level": self._current_halt.value,
                        "triggered_at": ts.isoformat() if new_halt != HaltState.L0 else None,
                        "peak_equity": str(peak),
                        "dd_pct": str((peak - current) / peak) if peak > 0 else "0",
                    },
                }
            )

    # ------------------------------------------------------------------
    # Bar close hook
    # ------------------------------------------------------------------

    def on_bar_close(self, bar: object) -> None:
        """Store prev_close for flash-CB detection on next assess.

        Also persists to state table so restart preserves flash continuity.
        """
        close = getattr(bar, "close", None)
        if close is not None:
            self._prev_close = Decimal(str(close))
            self._state.set("risk:cb:prev_close", {"value": str(self._prev_close)})

    # ------------------------------------------------------------------
    # Main decision atom
    # ------------------------------------------------------------------

    def assess(self, signal: Signal, *, mark_price: Decimal) -> RiskAssessment:
        """Return RiskAssessment with atomic snapshot of phase + halt + sizing.

        Contract: v0.1 FSM is LONG+FLAT only. assess() expects LONG entries;
        FLAT signals are exit semantics handled by the strategy/execution
        layer and must not reach Risk. The SL/TP formulas below
        (mark_price ± k·ATR) are sign-asymmetric and only valid for LONG.
        """
        assessed_at = self._clock()

        # v0.1 LONG-only invariant (ADR 0018 sub-decision 1, FSM contract)
        if signal.side != SignalSide.LONG:
            raise ValueError(
                f"LONG-only contract violated: assess() received "
                f"side={signal.side} (v0.1 FSM is LONG+FLAT, exits handled "
                f"outside Risk)"
            )

        # Adjustment 1 — look-ahead invariant
        if assessed_at < signal.generated_at:
            raise ValueError(
                f"look-ahead violation: assessed_at={assessed_at} "
                f"< signal.generated_at={signal.generated_at}"
            )

        # Override resume check
        override: CbOverride | None = self._override.read_active(
            now=assessed_at,
            expected_config_hash=self._settings.config_hash(),
        )

        # Flash CB check (close-to-close)
        if self._prev_close is not None:
            is_flash = self._cb.check_flash(
                bar_close=mark_price,
                prev_close=self._prev_close,
                atr=signal.atr_14,
            )
            if is_flash and self._halt_severity(HaltState.FLASH) > self._halt_severity(
                self._current_halt
            ):
                self._current_halt = HaltState.FLASH

        # Halt check (Adjustment 3 — correct reason codes)
        if self._current_halt != HaltState.L0:
            if override and override.level == self._current_halt.value:
                # Single-use semantics — consume the bypass token immediately
                # so a forged override (audit H2) cannot authorise more than
                # the trade it was issued for. Operator must reissue for the
                # next attempt. ADR 0018 sub-decision 9 (audit H3, CWE-672).
                self._override.consume(override=override)
                # Bypass succeeded — proceed to sizing.
            else:
                return self._reject(signal, assessed_at, self._halt_to_reason(self._current_halt))

        # Kelly phase + fraction
        trade_count = self._trades.count()
        phase = phase_from_trade_count(trade_count)

        # Adjustment 2 — Wilson lower bound for phases 3/4
        p, b = self._compute_p_b(phase)
        f = phase_adjusted_fraction(phase, p, b, self._kelly_caps)

        # Position sizing
        equity = self._equity.current_total() or Decimal("0")
        qty = compute_qty(
            equity=equity,
            fraction=f,
            atr=signal.atr_14,
            price=mark_price,
            k=self._settings.risk_sl_atr_multiplier,
        )
        # Round DOWN to 8 decimal places — Bybit Spot BUY step-floor
        # (round-up would risk insufficient-balance / oversize rejection).
        qty = qty.quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)

        # Adjustment 3 — zero-qty after rounding → REJECT_MIN_NOTIONAL
        if qty <= 0:
            return self._reject(
                signal,
                assessed_at,
                ReasonCode.REJECT_MIN_NOTIONAL,
                kelly_phase=phase,
                kelly_fraction=f,
            )

        sl = mark_price - self._settings.risk_sl_atr_multiplier * signal.atr_14
        tp = mark_price + self._settings.risk_tp_atr_multiplier * signal.atr_14

        # S39 R3 C4 fix — propagate signal.reason для strategy attribution в audit log.
        # Pre-S39: hardcoded ENTRY_LONG_TREND_FOLLOWING — все strategies теряли attribution.
        # Post-S39: signal.reason is canonical ReasonCode value (per Signal model contract).
        # S49 H6: EMA/meanrev/donchian reason strings registered as ReasonCode members
        # (ADR 0023 amendment), so direct resolution succeeds and attribution is preserved.
        # Fallback к ENTRY_LONG_TREND_FOLLOWING остаётся для genuinely unknown reasons.
        try:
            reason_code = ReasonCode(signal.reason)
        except ValueError:
            reason_code = ReasonCode.ENTRY_LONG_TREND_FOLLOWING
        return RiskAssessment(
            signal_id=signal.signal_id,
            approved=True,
            qty=qty,
            sl_price=sl,
            tp_price=tp,
            kelly_phase=phase,
            kelly_fraction=f,
            halt_state=self._current_halt,
            reason_code=reason_code,
            assessed_at=assessed_at,
        )

    # ------------------------------------------------------------------
    # Trade recording
    # ------------------------------------------------------------------

    def record_closed_trade(self, record: TradeRecord) -> int:
        return self._trades.insert_closed_trade(record)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _compute_p_b(self, phase: int) -> tuple[float, float]:
        """Return (p, b) for Kelly. Uses Wilson lower bound for phases 3/4."""
        if phase < 3:
            return (0.5, 1.0)  # ignored by phase_adjusted_fraction
        recent = self._trades.load_recent(window_days=90, now=self._clock(), symbol=self._symbol)
        if len(recent) < 30:
            return (0.5, 1.0)
        wins = [t for t in recent if t.pnl_quote > 0]
        losses = [t for t in recent if t.pnl_quote < 0]
        if not wins or not losses:
            return (0.5, 1.0)
        # Adjustment 2 — Wilson 95% CI lower bound as conservative p estimate
        p_lower, _ = wilson_95_ci(len(wins), len(recent))
        avg_win = sum((t.pnl_quote for t in wins), start=Decimal(0)) / len(wins)
        avg_loss = abs(sum((t.pnl_quote for t in losses), start=Decimal(0)) / len(losses))
        b = float(avg_win / avg_loss) if avg_loss > 0 else 1.0
        return (p_lower, b)

    @staticmethod
    def _halt_severity(state: HaltState) -> int:
        return {
            HaltState.L0: 0,
            HaltState.L1: 1,
            HaltState.L2: 2,
            HaltState.L3: 3,
            HaltState.FLASH: 4,
        }[state]

    @staticmethod
    def _halt_to_reason(state: HaltState) -> ReasonCode:
        return {
            HaltState.L1: ReasonCode.HALT_DRAWDOWN_L1,
            HaltState.L2: ReasonCode.HALT_DRAWDOWN_L2,
            HaltState.L3: ReasonCode.HALT_DRAWDOWN_L3,
            HaltState.FLASH: ReasonCode.HALT_FLASH_CRASH,
        }[state]

    def _reject(
        self,
        signal: Signal,
        assessed_at: datetime,
        reason: ReasonCode,
        *,
        kelly_phase: int = 1,
        kelly_fraction: Decimal | None = None,
    ) -> RiskAssessment:
        return RiskAssessment(
            signal_id=signal.signal_id,
            approved=False,
            qty=None,
            sl_price=None,
            tp_price=None,
            kelly_phase=kelly_phase,
            kelly_fraction=kelly_fraction or Decimal("0"),
            halt_state=self._current_halt,
            reason_code=reason,
            assessed_at=assessed_at,
        )
