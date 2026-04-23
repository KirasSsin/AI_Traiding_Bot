import pandas as pd

from src.backtest.data_collector import load_market_data
from src.backtest.replay_engine import run_replay


def _sample_ohlcv_df() -> pd.DataFrame:
    prices = [100, 101, 102, 103, 104, 103, 102, 101, 100, 99, 98, 97]
    rows = []
    for i, price in enumerate(prices):
        rows.append(
            {
                "timestamp": pd.Timestamp("2024-01-01") + pd.Timedelta(hours=i),
                "open": price,
                "high": price + 1,
                "low": price - 1,
                "close": price,
                "volume": 1.0,
            }
        )
    return pd.DataFrame(rows)


def test_load_market_data_parquet_source_falls_back_to_csv(tmp_path):
    csv_path = tmp_path / "BTCUSDT_1h.csv"
    df = _sample_ohlcv_df()
    df.to_csv(csv_path, index=False)

    cfg = {
        "data": {
            "source": "parquet",
            "parquet_path": str(tmp_path / "missing.parquet"),
            "csv_path": str(csv_path),
        }
    }

    out = load_market_data(cfg)
    assert not out.empty
    assert list(out.columns) == ["timestamp", "open", "high", "low", "close", "volume"]


def test_replay_outputs_reason_code_and_extended_metrics():
    df = _sample_ohlcv_df()
    config = {
        "trading": {
            "initial_balance": 10000.0,
            "commission_taker": 0.001,
            "slippage": 0.0005,
            "position_size_pct": 15.0,
            "max_drawdown_pct": 20.0,
            "long_only": True,
        },
        "strategy": {
            "indicators": {
                "ema": {"fast_period": 20, "slow_period": 50},
                "rsi": {"period": 14, "overbought": 68, "oversold": 32},
                "atr": {"period": 14, "sl_atr_mult": 2.0, "tp_atr_mult": 6.0},
            }
        },
    }

    replay = run_replay(df, config)
    trades_df = replay["trades_df"]
    metrics = replay["metrics"]

    assert "reason_code" in trades_df.columns

    expected_metric_keys = {
        "Net Profit (USDT)",
        "Loss Rate (%)",
        "Expectancy (USDT)",
        "Sortino Ratio",
        "Max Drawdown (USDT)",
        "Total Commissions (USDT)",
    }
    assert expected_metric_keys.issubset(set(metrics.keys()))

