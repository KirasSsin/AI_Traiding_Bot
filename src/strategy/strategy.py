from abc import ABC, abstractmethod
import pandas as pd
import numpy as np
import logging
from typing import Optional
from src.core.models import Kline, Signal
from src.ml.models import XGBPredictor
from src.strategy.hmm_regime import HMMRegimeModel
from src.strategy.order_flow import OrderFlowAnalyzer
from src.core.math_engine import MathEngine

logger = logging.getLogger(__name__)

class BaseStrategy(ABC):
    """Abstract base class for all trading strategies."""
    
    def __init__(self, symbol: str):
        self.symbol = symbol

    @abstractmethod
    def on_kline(self, df: pd.DataFrame, current_price: float) -> Optional[Signal]:
        pass

class AdvancedStrategy(BaseStrategy):
    """
    Advanced Strategy incorporating EMA Crossovers, RSI for momentum, 
    and ATR (Average True Range) for dynamic Stop Loss sizing.
    Calculated purely with Pandas to avoid dependency issues.
    """
    def __init__(self, symbol: str, fast_ema: int = 12, slow_ema: int = 26, rsi_period: int = 14, atr_period: int = 14):
        super().__init__(symbol)
        self.fast_ema = fast_ema
        self.slow_ema = slow_ema
        self.rsi_period = rsi_period
        self.atr_period = atr_period
        
        # Phase 2 & 3 Machine Learning / Advanced Math Engines
        self.xgb_predictor = XGBPredictor()
        self.hmm_classifier = HMMRegimeModel()
        
        # Keep track of recent historical data for ML inferences
        self.feature_history = []
        
    def _calculate_rsi(self, series: pd.Series, period: int) -> pd.Series:
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/period, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, adjust=False).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def _calculate_atr(self, df: pd.DataFrame, period: int) -> pd.Series:
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        # Wilder's Smoothing for ATR
        return true_range.ewm(alpha=1/period, adjust=False).mean()

    def on_kline(self, df: pd.DataFrame, current_price: float) -> Optional[Signal]:
        if len(df) < max(self.slow_ema, self.rsi_period, self.atr_period) + 1:
            return None

        # Calculate indicators
        df['ema_fast'] = df['close'].ewm(span=self.fast_ema, adjust=False).mean()
        df['ema_slow'] = df['close'].ewm(span=self.slow_ema, adjust=False).mean()
        df['rsi'] = self._calculate_rsi(df['close'], self.rsi_period)
        df['atr'] = self._calculate_atr(df, self.atr_period)

        current_fast_ema = df['ema_fast'].iloc[-1]
        current_slow_ema = df['ema_slow'].iloc[-1]
        prev_fast_ema = df['ema_fast'].iloc[-2]
        prev_slow_ema = df['ema_slow'].iloc[-2]
        
        current_rsi = df['rsi'].iloc[-1]
        current_atr = df['atr'].iloc[-1]

        signal = None

        # Dynamic Stop Loss based on volatility (1.5x ATR)
        sl_distance = current_atr * 1.5
        tp_distance = sl_distance * 2.0 # 1:2 Risk Reward Ratio

        # Calculate Advanced Math (Hurst) & ML Predictions
        # Using the last 30 closes for Hurst
        recent_closes = df['close'].tail(30).to_numpy()
        hurst = MathEngine.hurst_exponent(recent_closes)
        
        # Prepare a simple feature vector for ML: [rsi, atr, fast_ema_diff]
        current_features = np.array([current_rsi, current_atr, current_fast_ema - current_slow_ema])
        self.feature_history.append(current_features)
        
        xgb_prediction = -1
        regime = 0
        if len(self.feature_history) >= 100:
             # In a real situation, we train on historical data periodically.
             # For the live strategy flow, we will predict based on previously loaded models.
             features_array = np.array(self.feature_history[-100:])
             if not self.xgb_predictor.is_fitted:
                 # Dummy train just to enable the pipeline loop for now
                 dummy_y = np.random.randint(0, 2, 100)
                 self.xgb_predictor.train(features_array, dummy_y)
             if not self.hmm_classifier.is_fitted:
                 self.hmm_classifier.fit(features_array)
                 
             xgb_prediction = self.xgb_predictor.predict_direction(current_features)
             regime = self.hmm_classifier.predict_regime(current_features.reshape(1, -1))

        # Alignment Score (Consensus among technicals, XGBoost, and Hurst)
        # We start with base technicals.

        # 1. Bullish Signal: EMA Fast crosses over Slow AND RSI is not overbought (< 70)
        if prev_fast_ema <= prev_slow_ema and current_fast_ema > current_slow_ema:
            if current_rsi < 70:
                alignment_score = 0.5 # base technicals
                if xgb_prediction == 1: alignment_score += 0.25 # ML agrees
                if hurst > 0.5: alignment_score += 0.25 # Trending market agrees
                
                if alignment_score >= 0.75: # Requires at least one advanced confirmation
                    logger.info(f"[{self.symbol}] BUY Signal. EMA Cross. RSI: {current_rsi:.1f}, Align: {alignment_score:.2f}, Regime: {regime}")
                    signal = Signal(
                        symbol=self.symbol,
                        direction='BUY',
                        entry_price=current_price,
                        expected_sl=current_price - sl_distance,
                        expected_tp=current_price + tp_distance,
                        confidence=alignment_score
                    )

        # 2. Bearish Signal: EMA Fast crosses under Slow AND RSI is not oversold (> 30)
        elif prev_fast_ema >= prev_slow_ema and current_fast_ema < current_slow_ema:
            if current_rsi > 30:
                alignment_score = 0.5
                if xgb_prediction == 0: alignment_score += 0.25
                if hurst > 0.5: alignment_score += 0.25 
                
                if alignment_score >= 0.75:
                    logger.info(f"[{self.symbol}] SELL Signal. EMA Cross. RSI: {current_rsi:.1f}, Align: {alignment_score:.2f}, Regime: {regime}")
                    signal = Signal(
                        symbol=self.symbol,
                        direction='SELL',
                        entry_price=current_price,
                        expected_sl=current_price + sl_distance,
                        expected_tp=current_price - tp_distance,
                        confidence=alignment_score
                    )

        return signal
