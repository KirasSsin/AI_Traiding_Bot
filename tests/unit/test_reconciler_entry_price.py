"""ADR 0020 sub-decision 4: exchange owns qty, local SQLite owns entry_price.
Reconcile MUST preserve entry_price when qtys agree."""
from decimal import Decimal
from src.execution.reconciler import Reconciler, ReconcileResult, LocalState
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


def test_reconcile_preserves_local_entry_price_on_agree():
    fq = FakeQuery(
        wallet=WalletSnapshot(coin="BTC", wallet_balance=Decimal("0.001"),
                              available=Decimal("0"), locked=Decimal("0.001")),
        open_orders=[{"orderLinkId": "oco-abc-tp-1", "orderStatus": "New"},
                     {"orderLinkId": "oco-abc-sl-1", "orderStatus": "Untriggered"}],
    )
    rec = Reconciler(query=fq, base_coin="BTC", symbol="BTCUSDT")
    local = LocalState(state="OCO_ARMED", position_qty=Decimal("0.001"),
                       entry_price=Decimal("65000.00"), bracket_id="abc")
    result = rec.reconcile(local)
    assert result.verdict == "AGREE"
    assert result.entry_price == Decimal("65000.00")  # preserved from local
    assert result.position_qty == Decimal("0.001")    # exchange truth
    assert set(result.open_order_link_ids) == {"oco-abc-tp-1", "oco-abc-sl-1"}
    assert result.recommended_state is None
    assert result.halt_reason is None


def test_reconcile_qty_divergence_triggers_halt():
    fq = FakeQuery(
        wallet=WalletSnapshot(coin="BTC", wallet_balance=Decimal("0.0005"),
                              available=Decimal("0"), locked=Decimal("0.0005")),
        open_orders=[],
    )
    rec = Reconciler(query=fq, base_coin="BTC", symbol="BTCUSDT")
    local = LocalState(state="OCO_ARMED", position_qty=Decimal("0.001"),
                       entry_price=Decimal("65000.00"), bracket_id="abc")
    result = rec.reconcile(local)
    assert result.verdict == "DIVERGENCE"
    assert result.recommended_state == "HALTED"
    assert result.halt_reason == "HALT_RECONCILE_DIVERGENCE"
    assert result.position_qty == Decimal("0.0005")  # exchange truth
    assert result.entry_price is None                 # cleared on divergence


def test_reconcile_flat_agree_when_wallet_dust_and_local_flat():
    fq = FakeQuery(
        wallet=WalletSnapshot(coin="BTC", wallet_balance=Decimal("0.000001"),  # dust
                              available=Decimal("0.000001"), locked=Decimal("0")),
        open_orders=[],
    )
    rec = Reconciler(query=fq, base_coin="BTC", symbol="BTCUSDT",
                     dust_threshold=Decimal("0.00001"))
    local = LocalState(state="FLAT", position_qty=Decimal("0"),
                       entry_price=None, bracket_id=None)
    result = rec.reconcile(local)
    assert result.verdict == "AGREE"
    assert result.position_qty == Decimal("0")
    assert result.entry_price is None
