"""ADR 0020 sub-decision 4 — fetch_exchange_state derives position from walletBalance + dust."""
from decimal import Decimal
from src.execution.reconciler import Reconciler
from src.execution.bybit.adapter import WalletSnapshot


class FakeQuery:
    def __init__(self, wallet, open_orders):
        self.wallet = wallet
        self.orders = open_orders
        self.calls: list[str] = []

    def get_wallet_balance(self, *, coin):
        self.calls.append(f"wallet:{coin}")
        return self.wallet

    def get_open_orders(self, *, symbol):
        self.calls.append(f"open:{symbol}")
        return self.orders


def test_fetch_uses_wallet_balance_and_open_orders():
    fq = FakeQuery(
        wallet=WalletSnapshot(coin="BTC", wallet_balance=Decimal("0.00100000"),
                              available=Decimal("0"), locked=Decimal("0.00100000")),
        open_orders=[{"orderLinkId": "oco-abc-tp-1", "orderStatus": "New"}],
    )
    rec = Reconciler(query=fq, base_coin="BTC", symbol="BTCUSDT")
    state = rec.fetch_exchange_state()
    assert state.wallet.wallet_balance == Decimal("0.00100000")
    assert len(state.open_orders) == 1
    assert "wallet:BTC" in fq.calls
    assert "open:BTCUSDT" in fq.calls


def test_derive_position_qty_returns_wallet_balance_when_above_dust():
    fq = FakeQuery(
        wallet=WalletSnapshot(coin="BTC", wallet_balance=Decimal("0.001"),
                              available=Decimal("0"), locked=Decimal("0.001")),
        open_orders=[],
    )
    rec = Reconciler(query=fq, base_coin="BTC", symbol="BTCUSDT",
                     dust_threshold=Decimal("0.00001"))
    state = rec.fetch_exchange_state()
    assert rec.derive_position_qty(state) == Decimal("0.001")


def test_derive_position_qty_zero_when_below_dust():
    """Wallet < dust_threshold treated as FLAT — avoids phantom position."""
    fq = FakeQuery(
        wallet=WalletSnapshot(coin="BTC", wallet_balance=Decimal("0.00000050"),
                              available=Decimal("0.00000050"), locked=Decimal("0")),
        open_orders=[],
    )
    rec = Reconciler(query=fq, base_coin="BTC", symbol="BTCUSDT",
                     dust_threshold=Decimal("0.00001"))
    state = rec.fetch_exchange_state()
    assert rec.derive_position_qty(state) == Decimal("0")
