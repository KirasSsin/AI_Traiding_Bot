from dataclasses import dataclass


@dataclass
class Kline:
    """Represents a single candlestick (OHLCV) from the exchange."""

    symbol: str
    interval: str
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    is_closed: bool


@dataclass
class Signal:
    """Represents a trading signal outputted by a Strategy."""

    symbol: str
    direction: str  # 'BUY' or 'SELL'
    entry_price: float
    expected_sl: float | None = None
    expected_tp: float | None = None
    timestamp: int | None = None
    confidence: float = 1.0


@dataclass
class Order:
    """Represents an order placed with the exchange."""

    symbol: str
    order_id: int
    client_order_id: str
    direction: str  # 'BUY' or 'SELL'
    type: str  # 'MARKET', 'LIMIT', 'STOP_LOSS', etc.
    price: float
    quantity: float
    status: str  # 'NEW', 'FILLED', 'CANCELED', 'REJECTED'
    timestamp: int
