import numpy as np
from statsmodels.tsa.stattools import adfuller


class MathEngine:
    """
    Core mathematical functions for Phase 2: Mid-Frequency & ML.
    Implements Hurst Exponent, ADF Test, fractional Kelly, and CVaR.
    """

    @staticmethod
    def hurst_exponent(time_series: np.ndarray, max_lag: int = 20) -> float:
        """
        Calculates the Hurst Exponent to determine if a series is:
        H < 0.5: Mean-reverting
        H = 0.5: Random Walk
        H > 0.5: Trending

        Args:
            time_series: Array of prices.
            max_lag: Maximum lag for R/S analysis.

        Returns:
            float: Hurst exponent H.
        """
        if len(time_series) < max_lag * 2:
            return 0.5  # Not enough data, assume random walk

        lags = range(2, max_lag)
        tau = [np.sqrt(np.std(np.subtract(time_series[lag:], time_series[:-lag]))) for lag in lags]

        # Avoid log(0)
        valid_idx = [i for i, val in enumerate(tau) if val > 0]
        if not valid_idx:
            return 0.5

        lags_valid = np.array(lags)[valid_idx]
        tau_valid = np.array(tau)[valid_idx]

        poly = np.polyfit(np.log(lags_valid), np.log(tau_valid), 1)
        return poly[0] * 2.0

    @staticmethod
    def adf_test(time_series: np.ndarray) -> dict:
        """
        Augmented Dickey-Fuller test for stationarity.
        Used to test if a spread is mean-reverting.

        Returns:
            dict containing adf_stat and p_value.
        """
        if len(time_series) < 30:
            return {"adf_stat": 0.0, "p_value": 1.0, "is_stationary": False}

        result = adfuller(time_series, maxlag=1, autolag=None)
        return {"adf_stat": result[0], "p_value": result[1], "is_stationary": result[1] < 0.05}

    @staticmethod
    def calc_cvar(returns: np.ndarray, confidence_level: float = 0.95) -> float:
        """
        Calculates Conditional Value at Risk (Expected Shortfall).
        Average loss in the worst (1 - confidence_level) cases.
        """
        if len(returns) == 0:
            return 0.0

        cutoff = np.percentile(returns, 100 * (1 - confidence_level))
        tail_losses = returns[returns <= cutoff]

        if len(tail_losses) == 0:
            return 0.0

        return float(np.mean(tail_losses))

    @staticmethod
    def fractional_kelly(win_rate: float, win_loss_ratio: float, fraction: float = 0.5) -> float:
        """
        Calculates the safe Fractional Kelly criterion for position sizing.

        Args:
            win_rate: Percentage of winning trades (0 to 1).
            win_loss_ratio: Average Win / Average Loss.
            fraction: Multiplier (e.g., 0.5 for Half-Kelly).

        Returns:
            Recommended position size as a fraction of total equity.
        """
        if win_loss_ratio <= 0:
            return 0.0

        kelly_pct = win_rate - ((1 - win_rate) / win_loss_ratio)
        safe_kelly = max(0.0, kelly_pct * fraction)
        return safe_kelly
