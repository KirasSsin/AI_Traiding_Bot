"""Post-reconnect reconciler — ADR 0020 sub-decision 4 (walletBalance truth, no get_position)."""
from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Literal, Protocol, runtime_checkable

from src.execution.bybit.adapter import OrderSnapshot, WalletSnapshot

Verdict = Literal["AGREE", "DIVERGENCE", "HEAL_ENTRY_FILLED", "EXITED"]
_VALID_VERDICTS = ("AGREE", "DIVERGENCE", "HEAL_ENTRY_FILLED", "EXITED")


@runtime_checkable
class ExchangeQueryClient(Protocol):
    """ADR 0020 sub-decision 4: Spot V5 has no get_position. Wallet balance is truth.

    get_order is an optional extension used by the ADR 0021 classifier path; it is
    NOT part of the runtime_checkable check so that S6 adapters without it remain
    compatible. The classifier path calls it via duck-typing (hasattr guard).
    """

    def get_wallet_balance(self, *, coin: str) -> WalletSnapshot: ...
    def get_open_orders(self, *, symbol: str) -> list[dict[str, Any]]: ...


@dataclass(frozen=True, slots=True)
class ExchangeState:
    """Normalized exchange-side snapshot. ADR 0020 sub-decision 4."""
    wallet: WalletSnapshot
    open_orders: tuple[dict[str, Any], ...]


@dataclass(frozen=True, slots=True)
class LocalState:
    state: str = ""                           # FSM state name (str to decouple from ExecutionState enum)
    position_qty: Decimal = Decimal("0")
    entry_price: Decimal | None = None
    bracket_id: str | None = None
    # New fields added for ADR 0021 sub-decision 3 classifier path
    symbol: str | None = None
    entry_order_id: str | None = None
    expected_entry_qty: Decimal | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class ReconcileResult:
    verdict: str                              # "AGREE" | "DIVERGENCE" | "HEAL_ENTRY_FILLED" | "EXITED"
    position_qty: Decimal = Decimal("0")      # exchange truth (primary field)
    entry_price: Decimal | None = None        # preserved from local on AGREE, None on DIVERGENCE
    open_order_link_ids: tuple[str, ...] = ()
    recommended_state: str | None = None      # set on DIVERGENCE → "HALTED"
    halt_reason: str | None = None            # set on DIVERGENCE → "HALT_RECONCILE_DIVERGENCE"
    heal_context: dict[str, Any] | None = None  # populated only for HEAL_ENTRY_FILLED (ADR 0021)
    exch_qty: Decimal | None = None           # alias field; synced with position_qty in __post_init__

    def __post_init__(self) -> None:
        if self.verdict not in _VALID_VERDICTS:
            raise ValueError(f"verdict must be one of {_VALID_VERDICTS}, got {self.verdict!r}")
        # Sync exch_qty ↔ position_qty so both read paths work
        if self.exch_qty is not None and self.position_qty == Decimal("0"):
            object.__setattr__(self, "position_qty", self.exch_qty)
        elif self.exch_qty is None and self.position_qty != Decimal("0"):
            object.__setattr__(self, "exch_qty", self.position_qty)
        elif self.exch_qty is None and self.position_qty == Decimal("0"):
            object.__setattr__(self, "exch_qty", Decimal("0"))


class Reconciler:
    """Post-reconnect reconciler — ADR 0020 sub-decision 4."""

    def __init__(self, *, query: ExchangeQueryClient | None = None,
                 adapter: ExchangeQueryClient | None = None,
                 base_coin: str | None = None, symbol: str | None = None,
                 dust_threshold: Decimal = Decimal("0.00001"),
                 heal_max_age_seconds: int = 3600) -> None:
        _q = query or adapter
        if _q is None:
            raise ValueError("Reconciler requires query= or adapter=")
        self._query: ExchangeQueryClient = _q
        self._base_coin = base_coin
        self._symbol = symbol
        self._dust_threshold = dust_threshold
        self._heal_max_age_seconds = heal_max_age_seconds
        self._wallet_cache: dict[str, Decimal] = {}
        self._lock: threading.Lock = threading.Lock()  # ADR 0022 sub-decision 1 — non-reentrant

    def on_wallet_event(self, evt: dict[str, Any]) -> None:
        """WS wallet topic event: update cache. ADR 0021 sub-decision 6."""
        with self._lock:
            coin = evt["coin"]
            self._wallet_cache[coin] = Decimal(str(evt["walletBalance"]))

    def _fetch_exch_qty(self, symbol: str | None) -> Decimal:
        """Fetch exchange qty: cache first, REST fallback on miss. ADR 0021 sub-decision 6."""
        coin = self._base_coin or self._derive_base_coin(symbol)
        if coin is not None:
            cached = self._wallet_cache.get(coin)
            if cached is not None:
                return Decimal("0") if cached < self._dust_threshold else cached
            snap = self._query.get_wallet_balance(coin=coin)
            return (Decimal("0") if snap.wallet_balance < self._dust_threshold
                    else snap.wallet_balance)
        return Decimal("0")

    def fetch_exchange_state(self) -> ExchangeState:
        if self._base_coin is None or self._symbol is None:
            raise ValueError(
                "fetch_exchange_state requires base_coin + symbol set in __init__"
            )
        wallet = self._query.get_wallet_balance(coin=self._base_coin)
        orders = tuple(self._query.get_open_orders(symbol=self._symbol))
        return ExchangeState(wallet=wallet, open_orders=orders)

    def derive_position_qty(self, state: ExchangeState) -> Decimal:
        """ADR 0020 sub-decision 4: wallet < dust_threshold → FLAT (no phantom position)."""
        if state.wallet.wallet_balance < self._dust_threshold:
            return Decimal("0")
        return state.wallet.wallet_balance

    def _binary_verdict(self, local: LocalState, exch_qty: Decimal,
                        link_ids: tuple[str, ...]) -> ReconcileResult:
        """S6 binary AGREE/DIVERGENCE path (backward compat)."""
        if exch_qty != local.position_qty:
            return ReconcileResult(
                verdict="DIVERGENCE",
                position_qty=exch_qty,
                entry_price=None,
                open_order_link_ids=link_ids,
                recommended_state="HALTED",
                halt_reason="HALT_RECONCILE_DIVERGENCE",
            )
        return ReconcileResult(
            verdict="AGREE",
            position_qty=exch_qty,
            entry_price=local.entry_price,
            open_order_link_ids=link_ids,
        )

    def _derive_base_coin(self, symbol: str | None) -> str | None:
        """BTCUSDT → BTC. Convention: strip USDT/USDC suffix for spot pairs."""
        if symbol is None:
            return None
        if symbol.endswith("USDT"):
            return symbol[:-4]
        if symbol.endswith("USDC"):
            return symbol[:-4]
        return symbol  # unknown format — pass through

    def _belongs_to_current_bracket(self, o: dict[str, Any], local: LocalState) -> bool:
        """Return True if open order belongs to (or could belong to) current bracket."""
        if local.bracket_id is None:
            # Pre-bootstrap: can't identify bracket membership; any open order is suspect.
            return True
        link_id: str = o.get("orderLinkId", "")
        return link_id.startswith(f"oco-{local.bracket_id}-")

    def _classify(self, local: LocalState, expected_state: object,
                  exch_qty: Decimal, open_orders: list[dict[str, Any]],
                  entry_order: OrderSnapshot | None) -> ReconcileResult:
        """ADR 0021 4-valued path classifier. Tasks 13-15 implement logic."""
        from src.execution.state_machine import ExecutionState  # avoid circular at module level
        if expected_state == ExecutionState.ENTRY_PENDING:
            return self._classify_entry_pending(local, exch_qty, open_orders, entry_order)
        if expected_state == ExecutionState.EXIT_PENDING:
            return self._classify_exit_pending(local, exch_qty, open_orders)
        # Other hint-provided states fall through to binary
        return self._binary_verdict(local, exch_qty, ())

    def _classify_entry_pending(
        self, local: LocalState, exch_qty: Decimal,
        open_orders: list[dict[str, Any]], entry_order: OrderSnapshot | None,
    ) -> ReconcileResult:
        """ADR 0021 sub-decision 3: classify ENTRY_PENDING state."""
        # Precondition: entry order must be Filled
        if entry_order is None or entry_order.order_status != "Filled":
            return ReconcileResult(
                verdict="DIVERGENCE",
                exch_qty=exch_qty,
                entry_price=None,
                recommended_state="HALTED",
                halt_reason="HALT_BOOTSTRAP_AMBIGUOUS",
                heal_context=None,
            )

        # Qty check: exchange must have at least expected qty (minus dust)
        expected_qty = local.expected_entry_qty or Decimal("0")
        if exch_qty < expected_qty - self._dust_threshold:
            return ReconcileResult(
                verdict="DIVERGENCE",
                exch_qty=exch_qty,
                entry_price=None,
                recommended_state="HALTED",
                halt_reason="HALT_BOOTSTRAP_AMBIGUOUS",
                heal_context=None,
            )

        # Orphan bracket orders check
        bracket_orders = [o for o in open_orders if self._belongs_to_current_bracket(o, local)]
        if bracket_orders:
            return ReconcileResult(
                verdict="DIVERGENCE",
                exch_qty=exch_qty,
                entry_price=None,
                recommended_state="HALTED",
                halt_reason="HALT_BOOTSTRAP_AMBIGUOUS",
                heal_context=None,
            )

        # Staleness check (Task 14 adds this)
        if local.updated_at is not None:
            age_seconds = (datetime.now(UTC) - local.updated_at).total_seconds()
            if age_seconds > self._heal_max_age_seconds:
                return ReconcileResult(
                    verdict="DIVERGENCE",
                    exch_qty=exch_qty,
                    entry_price=None,
                    recommended_state="HALTED",
                    halt_reason="HALT_BOOTSTRAP_AMBIGUOUS",
                    heal_context={"sub_reason": "stale_age", "age_seconds": age_seconds},
                )

        # All checks passed → HEAL
        return ReconcileResult(
            verdict="HEAL_ENTRY_FILLED",
            exch_qty=exch_qty,
            entry_price=entry_order.avg_price,
            halt_reason=None,
            heal_context={
                "avg_price": str(entry_order.avg_price) if entry_order.avg_price is not None else None,
                "cum_exec_fee": str(entry_order.cum_exec_fee),
                "fee_currency": entry_order.fee_currency,
            },
        )

    def _classify_exit_pending(
        self, local: LocalState, exch_qty: Decimal, open_orders: list[dict[str, Any]],
    ) -> ReconcileResult:
        """ADR 0021 sub-decision 3: classify EXIT_PENDING state."""
        if exch_qty < self._dust_threshold and len(open_orders) == 0:
            return ReconcileResult(
                verdict="EXITED",
                exch_qty=exch_qty,
                entry_price=None,
                halt_reason=None,
                heal_context=None,
            )
        return ReconcileResult(
            verdict="DIVERGENCE",
            exch_qty=exch_qty,
            entry_price=None,
            recommended_state="HALTED",
            halt_reason="HALT_EXIT_RECONCILE_DIVERGENCE",
            heal_context=None,
        )

    def reconcile(self, local: LocalState, *, expected_state: object = None) -> ReconcileResult:
        """ADR 0020 sub-decision 4: exchange owns qty; local owns entry_price.

        If expected_state is None → binary AGREE/DIVERGENCE (S6 behavior, preserved).
        If expected_state is provided → 4-valued with HEAL_ENTRY_FILLED/EXITED possible.
        ADR 0021 sub-decision 3.
        """
        with self._lock:
            if expected_state is None:
                # S6 binary path: cache-aware fetch, still uses constructor symbol for orders
                sym_bin = local.symbol or self._symbol
                exch_qty = self._fetch_exch_qty(sym_bin)
                open_orders_bin = (self._query.get_open_orders(symbol=sym_bin)
                                   if sym_bin else [])
                link_ids = tuple(o.get("orderLinkId", "") for o in open_orders_bin)
                return self._binary_verdict(local, exch_qty, link_ids)

            # New 4-valued path (ADR 0021)
            sym = local.symbol or self._symbol
            exch_qty = self._fetch_exch_qty(sym)
            open_orders = self._query.get_open_orders(symbol=sym) if sym else []
            get_order = getattr(self._query, "get_order", None)
            entry_order = (get_order(symbol=sym, order_id=local.entry_order_id)
                           if (local.entry_order_id and sym and get_order is not None) else None)
            return self._classify(local, expected_state, exch_qty, open_orders, entry_order)
