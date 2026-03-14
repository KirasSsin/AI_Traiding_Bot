import numpy as np
import logging
from src.core.models import Signal
from src.core.math_engine import MathEngine

logger = logging.getLogger(__name__)

class RiskManager:
    """
    Evaluates trading signals against risk parameters.
    Acts as the Kill-Switch for the bot.
    """
    def __init__(self, initial_capital: float, max_risk_per_trade_pct: float = 0.01, max_daily_drawdown_pct: float = 0.05):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.max_risk_per_trade_pct = max_risk_per_trade_pct
        self.max_daily_drawdown_pct = max_daily_drawdown_pct
        
        self.high_water_mark = initial_capital
        self.is_kill_switch_active = False
        self.recent_trade_returns = [] # Track trade PnL for CVaR and Kelly
        self.win_rate = 0.5
        self.win_loss_ratio = 1.0

    def update_capital(self, new_capital: float):
        """Update current capital and check for drawdown breaches."""
        self.current_capital = new_capital
        if new_capital > self.high_water_mark:
            self.high_water_mark = new_capital
            
        drawdown_pct = (self.high_water_mark - new_capital) / self.high_water_mark
        if drawdown_pct >= self.max_daily_drawdown_pct:
            logger.critical(f"KILL-SWITCH ENGAGED! Drawdown {drawdown_pct*100:.2f}% exceeds {self.max_daily_drawdown_pct*100:.2f}% limit.")
            self.is_kill_switch_active = True

    def record_trade_result(self, pnl_pct: float):
        """Record trade result to update Kelly criterion and VaR calculations."""
        self.recent_trade_returns.append(pnl_pct)
        # Keep only the last 100 trades for dynamic sizing
        if len(self.recent_trade_returns) > 100:
            self.recent_trade_returns.pop(0)
            
        wins = [r for r in self.recent_trade_returns if r > 0]
        losses = [abs(r) for r in self.recent_trade_returns if r < 0]
        
        if len(self.recent_trade_returns) > 0:
            self.win_rate = len(wins) / len(self.recent_trade_returns)
            
        avg_win = np.mean(wins) if wins else 0
        avg_loss = np.mean(losses) if losses else 1e-6
        self.win_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 1.0

    def get_cvar(self) -> float:
        """Returns the current Conditional Value at Risk."""
        if len(self.recent_trade_returns) < 10:
            return 0.0
        return MathEngine.calc_cvar(np.array(self.recent_trade_returns))

    def calculate_position_size(self, signal: Signal) -> float:
        """Calculate position size dynamically using Fractional Kelly."""
        if not signal.expected_sl:
            logger.warning("Signal missing expected Stop Loss. Cannot calculate precise risk.")
            return 0.0
            
        risk_per_coin = abs(signal.entry_price - signal.expected_sl)
        if risk_per_coin == 0:
            return 0.0
            
        # 1. Base fixed fractional risk
        risk_capital = self.current_capital * self.max_risk_per_trade_pct
        
        # 2. Dynamic adjustment via Fractional Kelly (Half-Kelly)
        if len(self.recent_trade_returns) >= 10:
            kelly_pct = MathEngine.fractional_kelly(self.win_rate, self.win_loss_ratio, fraction=0.5)
            # Bound the Kelly recommended capital to not exceed our max hardcoded risk
            kelly_capital = self.current_capital * min(kelly_pct, 0.10) # cap kelly risk at 10%
            
            # Use whichever is more conservative until system proves edge
            risk_capital = min(risk_capital, kelly_capital) if kelly_capital > 0 else risk_capital

        position_size = risk_capital / risk_per_coin
        return position_size

    def evaluate_signal(self, signal: Signal) -> bool:
        """
        Check if the signal is valid and within risk limits.
        Returns True if approved, False otherwise.
        """
        if self.is_kill_switch_active:
            logger.warning("Signal rejected: Risk Manager kill-switch is active.")
            return False
            
        position_size = self.calculate_position_size(signal)
        if position_size <= 0:
            logger.warning("Signal rejected: Calculated position size is 0 or invalid.")
            return False
            
        notional_value = position_size * signal.entry_price
        if notional_value > self.current_capital:
             logger.warning(f"Signal rejected: Notional value ({notional_value}) exceeds current capital ({self.current_capital}).")
             return False

        logger.info(f"Signal approved: {signal.direction} {signal.symbol}. Calculated size: {position_size:.6f}")
        return True
