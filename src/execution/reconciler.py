"""Post-reconnect reconciler — ADR 0020 sub-decision 4 (walletBalance truth, no get_position)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Literal, Protocol, runtime_checkable

from src.execution.bybit.adapter import WalletSnapshot

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
    def get_open_orders(self, *, symbol: str) -> list[dict]: ...


@dataclass(frozen=True, slots=True)
class ExchangeState:
    """Normalized exchange-side snapshot. ADR 0020 sub-decision 4."""
    wallet: WalletSnapshot
    open_orders: tuple[dict, ...]


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
    open_order_link_ids: tuple = ()
    recommended_state: str | None = None      # set on DIVERGENCE → "HALTED"
    halt_reason: str | None = None            # set on DIVERGENCE → "HALT_RECONCILE_DIVERGENCE"
    heal_context: dict | None = None          # populated only for HEAL_ENTRY_FILLED (ADR 0021)
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
        self._query = query or adapter
        if self._query is None:
            raise ValueError("Reconciler requires query= or adapter=")
        self._base_coin = base_coin
        self._symbol = symbol
        self._dust_threshold = dust_threshold
        self._heal_max_age_seconds = heal_max_age_seconds

    def fetch_exchange_state(self) -> ExchangeState:
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

    def _classify(self, local: LocalState, expected_state: object,
                  exch_qty: Decimal, open_orders: list[dict],
                  entry_order: dict | None) -> ReconcileResult:
        """Stub classifier for ADR 0021 4-valued path. Tasks 13-15 implement logic."""
        return ReconcileResult(
            verdict="DIVERGENCE",
            position_qty=exch_qty,
            exch_qty=exch_qty,
            entry_price=None,
            halt_reason="HALT_BOOTSTRAP_AMBIGUOUS",
            heal_context=None,
            open_order_link_ids=(),
        )

    def reconcile(self, local: LocalState, *, expected_state: object = None) -> ReconcileResult:
        """ADR 0020 sub-decision 4: exchange owns qty; local owns entry_price.

        If expected_state is None → binary AGREE/DIVERGENCE (S6 behavior, preserved).
        If expected_state is provided → 4-valued with HEAL_ENTRY_FILLED/EXITED possible.
        ADR 0021 sub-decision 3.
        """
        if expected_state is None:
            # S6 binary path: use base_coin/symbol from constructor
            state = self.fetch_exchange_state()
            exch_qty = self.derive_position_qty(state)
            link_ids = tuple(o.get("orderLinkId", "") for o in state.open_orders)
            return self._binary_verdict(local, exch_qty, link_ids)

        # New 4-valued path (ADR 0021)
        sym = local.symbol or self._symbol
        coin = self._base_coin
        wallet = self._query.get_wallet_balance(coin=coin) if coin else None
        if wallet is not None:
            exch_qty = (Decimal("0") if wallet.wallet_balance < self._dust_threshold
                        else wallet.wallet_balance)
        else:
            exch_qty = local.position_qty
        open_orders = self._query.get_open_orders(symbol=sym) if sym else []
        get_order = getattr(self._query, "get_order", None)
        entry_order = (get_order(order_id=local.entry_order_id)
                       if (local.entry_order_id and get_order is not None) else None)
        return self._classify(local, expected_state, exch_qty, open_orders, entry_order)
