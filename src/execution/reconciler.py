"""Post-reconnect reconciler — ADR 0020 sub-decision 4 (walletBalance truth, no get_position)."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol, runtime_checkable

from src.execution.bybit.adapter import WalletSnapshot


@runtime_checkable
class ExchangeQueryClient(Protocol):
    """ADR 0020 sub-decision 4: Spot V5 has no get_position. Wallet balance is truth."""

    def get_wallet_balance(self, *, coin: str) -> WalletSnapshot: ...
    def get_open_orders(self, *, symbol: str) -> list[dict]: ...


@dataclass(frozen=True, slots=True)
class ExchangeState:
    """Normalized exchange-side snapshot. ADR 0020 sub-decision 4."""
    wallet: WalletSnapshot
    open_orders: tuple[dict, ...]


@dataclass(frozen=True, slots=True)
class LocalState:
    state: str                    # FSM state name (str to decouple from ExecutionState enum)
    position_qty: Decimal
    entry_price: Decimal | None
    bracket_id: str | None


@dataclass(frozen=True, slots=True)
class ReconcileResult:
    verdict: str                              # "AGREE" | "DIVERGENCE"
    position_qty: Decimal                     # exchange truth
    entry_price: Decimal | None               # preserved from local on AGREE, None on DIVERGENCE
    open_order_link_ids: tuple[str, ...]
    recommended_state: str | None = None      # set on DIVERGENCE → "HALTED"
    halt_reason: str | None = None            # set on DIVERGENCE → "HALT_RECONCILE_DIVERGENCE"


class Reconciler:
    """Post-reconnect reconciler — ADR 0020 sub-decision 4."""

    def __init__(self, *, query: ExchangeQueryClient, base_coin: str, symbol: str,
                 dust_threshold: Decimal = Decimal("0.00001")) -> None:
        self._query = query
        self._base_coin = base_coin
        self._symbol = symbol
        self._dust_threshold = dust_threshold

    def fetch_exchange_state(self) -> ExchangeState:
        wallet = self._query.get_wallet_balance(coin=self._base_coin)
        orders = tuple(self._query.get_open_orders(symbol=self._symbol))
        return ExchangeState(wallet=wallet, open_orders=orders)

    def derive_position_qty(self, state: ExchangeState) -> Decimal:
        """ADR 0020 sub-decision 4: wallet < dust_threshold → FLAT (no phantom position)."""
        if state.wallet.wallet_balance < self._dust_threshold:
            return Decimal("0")
        return state.wallet.wallet_balance

    def reconcile(self, local: LocalState) -> ReconcileResult:
        """ADR 0020 sub-decision 4: exchange owns qty; local owns entry_price.
        Preserve entry_price when qtys agree; clear it + halt on divergence.
        """
        state = self.fetch_exchange_state()
        exch_qty = self.derive_position_qty(state)
        link_ids = tuple(o.get("orderLinkId", "") for o in state.open_orders)
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
