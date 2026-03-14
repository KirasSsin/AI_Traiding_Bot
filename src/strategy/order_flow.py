import numpy as np
import logging

logger = logging.getLogger(__name__)

class OrderFlowAnalyzer:
    """
    Microstructure analysis focusing on Order Book Imbalance (OBI) and Kyle's Lambda.
    """
    
    @staticmethod
    def calculate_obi(bid_vol: float, ask_vol: float) -> float:
        """
        Calculates Order Book Imbalance (OBI). 
        Measures the pressure of limit orders.
        Returns expected range: [-1, 1]. > 0 indicates buying pressure.
        """
        if bid_vol + ask_vol == 0:
             return 0.0
        return (bid_vol - ask_vol) / (bid_vol + ask_vol)

    @staticmethod
    def calculate_kyles_lambda(price_delta: float, volume: float) -> float:
        """
        Kyle's Lambda: Measures market impact (price change per unit volume).
        Higher lambda = lower liquidity/higher slippage.
        """
        if volume == 0:
             return 0.0
        return abs(price_delta) / volume
