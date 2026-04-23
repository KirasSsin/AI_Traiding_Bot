"""ADR 0020 sub-decision 4 — Reconciler must call get_wallet_balance, NOT get_position."""
from decimal import Decimal
from src.execution.reconciler import ExchangeQueryClient, ExchangeState
from src.execution.bybit.adapter import WalletSnapshot


class FakeQuery:
    def __init__(self, wallet, open_orders):
        self.wallet = wallet
        self.orders = open_orders
        self.calls: list[str] = []

    def get_wallet_balance(self, *, coin: str) -> WalletSnapshot:
        self.calls.append(f"wallet:{coin}")
        return self.wallet

    def get_open_orders(self, *, symbol: str) -> list[dict]:
        self.calls.append(f"open:{symbol}")
        return self.orders


def test_query_protocol_satisfied_by_wallet_only():
    """ExchangeQueryClient v2 Protocol no longer requires get_position."""
    fq = FakeQuery(
        wallet=WalletSnapshot(coin="BTC", wallet_balance=Decimal("0.001"),
                              available=Decimal("0"), locked=Decimal("0.001")),
        open_orders=[],
    )
    # structural typing: runtime_checkable Protocol test
    assert isinstance(fq, ExchangeQueryClient)
    assert not hasattr(fq, "get_position"), "v2 Protocol must not require get_position"


def test_exchange_state_carries_wallet_not_position():
    """ExchangeState v2 exposes wallet: WalletSnapshot."""
    ws = WalletSnapshot(coin="BTC", wallet_balance=Decimal("0.001"),
                        available=Decimal("0"), locked=Decimal("0.001"))
    state = ExchangeState(wallet=ws, open_orders=())
    assert state.wallet is ws
    assert state.open_orders == ()
    # frozen dataclass
    import dataclasses, pytest as _pt
    with _pt.raises(dataclasses.FrozenInstanceError):
        state.wallet = ws  # type: ignore[misc]
