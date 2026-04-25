import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class VectorBacktester:
    """
    Fast, loop-free backtesting engine using Pandas/Numpy.
    Requires a pre-populated DataFrame with OHLCV and Signal columns (1 for Buy, -1 for Sell, 0 for Hold).
    """

    def __init__(
        self, df: pd.DataFrame, initial_capital: float = 10000.0, maker_fee: float = 0.001
    ):
        self.df = df.copy()
        self.initial_capital = initial_capital
        self.maker_fee = maker_fee

    def run(self) -> dict[str, float]:
        """
        Runs the vectorized backtest and returns KPIs.
        Expects self.df to have a 'signal' column.
        """
        if "signal" not in self.df.columns:
            raise ValueError("DataFrame must contain a 'signal' column.")

        # Forward fill the signal to maintain the position (assuming 1 is long, -1 is short)
        # NOTE (S10): pandas 3.x removed `replace(.., method="ffill")` — use replace→ffill chain.
        self.df["position"] = self.df["signal"].replace(0, np.nan).ffill().fillna(0)

        # Calculate logarithmic returns of the asset
        self.df["asset_returns"] = np.log(self.df["close"] / self.df["close"].shift(1))

        # Calculate strategy returns (position shifted by 1 to avoid look-ahead bias)
        self.df["strategy_returns"] = self.df["position"].shift(1) * self.df["asset_returns"]

        # Apply trading fees when position changes
        self.df["trades"] = self.df["position"].diff().fillna(0).abs()
        self.df["strategy_returns"] -= self.df["trades"] * self.maker_fee

        # Calculate cumulative returns
        self.df["cumulative_returns"] = self.df["strategy_returns"].cumsum().apply(np.exp)
        self.df["equity_curve"] = self.initial_capital * self.df["cumulative_returns"]

        # Calculate Drawdowns
        self.df["rolling_max"] = self.df["equity_curve"].cummax()
        self.df["drawdown"] = (self.df["rolling_max"] - self.df["equity_curve"]) / self.df[
            "rolling_max"
        ]

        # Calculate KPIs
        total_return = (self.df["equity_curve"].iloc[-1] / self.initial_capital) - 1
        max_drawdown = self.df["drawdown"].max()

        # N = periods per year for 1H bars: 365 * 24 = 8760
        # NOTE (S10 fix): was sqrt(365*24*60) which assumed 1m bars — wrong для 1H BTCUSDT.
        # Off by sqrt(60) ≈ 7.7×. Aligned с replay_engine._compute_metrics:51 convention.
        returns_mean = self.df["strategy_returns"].mean()
        returns_std = self.df["strategy_returns"].std()
        sharpe_ratio = (
            (returns_mean / returns_std) * np.sqrt(365 * 24) if returns_std != 0 else 0
        )

        kpis = {
            "Total Return (%)": total_return * 100,
            "Max Drawdown (%)": max_drawdown * 100,
            "Sharpe Ratio": sharpe_ratio,
        }

        logger.info(f"Backtest complete: {kpis}")
        return kpis
