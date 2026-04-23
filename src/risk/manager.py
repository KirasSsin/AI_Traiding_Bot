"""Risk module orchestrator.

Public API: update_equity, assess, on_bar_close, record_closed_trade,
            load_state, persist_state.
"""

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from sqlite3 import Connection

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
from src.signalgen.models import Signal

logger = logging.getLogger(__name__)


class RiskManager:
    """Orchestrates Kelly + CB + sizing + override resume."""

    def __init__(
        self,
        *,
        conn: Connection,
        settings: Settings,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._conn = conn
        self._settings = settings
        self._clock = clock
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
        self._override = OverrideStore(settings.risk_override_path)
        self._current_halt: HaltState = HaltState.L0
        self._prev_close: Decimal | None = None

    # ------------------------------------------------------------------
    # State persistence
    # ------------------------------------------------------------------

    def load_state(self) -> None:
        """Restore halt level from state table."""
        cb = self._state.get("risk:cb:current_level")
        if cb:
            self._current_halt = HaltState(cb["level"])

    # ------------------------------------------------------------------
    # Equity update
    # ------------------------------------------------------------------

    def update_equity(
        self, *, realized: Decimal, unrealized: Decimal, ts: datetime
    ) -> None:
        """Snapshot equity, evaluate drawdown, persist state atomically."""
        self._equity.record(
            realized=realized, unrealized=unrealized, ts=ts, source="BAR_CLOSE"
        )
        peak = self._equity.peak_equity_24h(now=ts) or (realized + unrealized)
        current = realized + unrealized
        new_halt = self._cb.check_drawdown(peak=peak, current=current)

        if self._halt_severity(new_halt) > self._halt_severity(self._current_halt):
            self._current_halt = new_halt
            logger.warning(
                "CB level escalated to %s (peak=%s current=%s)",
                self._current_halt, peak, current,
            )

        # Atomic state flush (Adjustment 4)
        self._state.update_many(
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
        """Store prev_close for flash-CB detection on next assess."""
        close = getattr(bar, "close", None)
        if close is not None:
            self._prev_close = Decimal(str(close))

    # ------------------------------------------------------------------
    # Main decision atom
    # ------------------------------------------------------------------

    def assess(self, signal: Signal, *, mark_price: Decimal) -> RiskAssessment:
        """Return RiskAssessment with atomic snapshot of phase + halt + sizing."""
        assessed_at = self._clock()

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
            if is_flash and self._halt_severity(HaltState.FLASH) > self._halt_severity(self._current_halt):
                self._current_halt = HaltState.FLASH

        # Halt check (Adjustment 3 — correct reason codes)
        if self._current_halt != HaltState.L0:
            if override and override.level == self._current_halt.value:
                pass  # manual override — proceed to sizing
            else:
                return self._reject(
                    signal, assessed_at, self._halt_to_reason(self._current_halt)
                )

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
        # Round to 8 decimal places (Bybit exchange precision)
        qty = qty.quantize(Decimal("0.00000001"))

        # Adjustment 3 — zero-qty after rounding → REJECT_MIN_NOTIONAL
        if qty <= 0:
            return self._reject(
                signal, assessed_at, ReasonCode.REJECT_MIN_NOTIONAL,
                kelly_phase=phase, kelly_fraction=f,
            )

        sl = mark_price - self._settings.risk_sl_atr_multiplier * signal.atr_14
        tp = mark_price + self._settings.risk_tp_atr_multiplier * signal.atr_14

        return RiskAssessment(
            signal_id=signal.signal_id,
            approved=True,
            qty=qty,
            sl_price=sl,
            tp_price=tp,
            kelly_phase=phase,
            kelly_fraction=f,
            halt_state=self._current_halt,
            reason_code=ReasonCode.ENTRY_LONG_TREND_FOLLOWING,
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
        recent = self._trades.load_recent(window_days=90, now=self._clock())
        if len(recent) < 30:
            return (0.5, 1.0)
        wins = [t for t in recent if t.pnl_quote > 0]
        losses = [t for t in recent if t.pnl_quote < 0]
        if not wins or not losses:
            return (0.5, 1.0)
        # Adjustment 2 — Wilson 95% CI lower bound as conservative p estimate
        p_lower, _ = wilson_95_ci(len(wins), len(recent))
        avg_win = sum(t.pnl_quote for t in wins) / len(wins)
        avg_loss = abs(sum(t.pnl_quote for t in losses) / len(losses))
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
            kelly_phase=kelly_phase,  # type: ignore[arg-type]
            kelly_fraction=kelly_fraction or Decimal("0"),
            halt_state=self._current_halt,
            reason_code=reason,
            assessed_at=assessed_at,
        )
