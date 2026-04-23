import pandas as pd

from src.backtest.replay_engine import run_replay


def _build_df() -> pd.DataFrame:
    prices = [100, 101, 102, 103, 104, 103, 102, 101, 100]
    rows = []
    for i, p in enumerate(prices):
        rows.append(
            {
                "timestamp": pd.Timestamp("2024-01-01") + pd.Timedelta(hours=i),
                "open": p,
                "high": p + 1,
                "low": p - 1,
                "close": p,
                "volume": 1.0,
            }
        )
    return pd.DataFrame(rows)


def test_entry_executes_on_next_open():
    df = _build_df()
    cfg = {
        "trading": {
            "initial_balance": 10000.0,
            "commission_taker": 0.0,
            "slippage": 0.0,
            "position_size_pct": 10.0,
            "max_drawdown_pct": 99.0,
            "long_only": True,
        },
        "strategy": {
            "indicators": {
                "ema": {"fast_period": 2, "slow_period": 3},
                "rsi": {"period": 2, "overbought": 100, "oversold": 0},
                "atr": {"period": 2, "sl_atr_mult": 100.0, "tp_atr_mult": 100.0},
            }
        },
    }

    replay = run_replay(df, cfg)
    trades = replay["trades_df"]
    assert not trades.empty

    first_trade = trades.iloc[0]
    signal_index = 1  # for this synthetic setup (ema 2/3), first long signal appears on candle 1
    expected_entry_ts = df.iloc[signal_index + 1]["timestamp"]
    expected_entry_price = float(df.iloc[signal_index + 1]["open"])

    assert first_trade["timestamp_open"] == expected_entry_ts
    assert first_trade["entry_price"] == expected_entry_price

