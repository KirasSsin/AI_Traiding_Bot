import pandas as pd

from src.backtest.replay_engine import run_replay


def _sample_df_for_crosses() -> pd.DataFrame:
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


def test_replay_respects_long_only_flag():
    df = _sample_df_for_crosses()
    config = {
        "trading": {
            "initial_balance": 10000.0,
            "commission_taker": 0.0,
            "slippage": 0.0,
            "position_size_pct": 10.0,
            "max_drawdown_pct": 90.0,
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

    replay = run_replay(df, config)
    trades = replay["trades_df"]

    assert not trades.empty
    assert set(trades["direction"].unique()) <= {"BUY"}


def test_long_only_does_not_exit_on_signal_flip():
    """
    In long_only mode, bearish cross should not force-close longs via SIGNAL_FLIP.
    Position must stay open until TP/SL/EOD.
    """
    df = _sample_df_for_crosses()
    config = {
        "trading": {
            "initial_balance": 10000.0,
            "commission_taker": 0.0,
            "slippage": 0.0,
            "position_size_pct": 10.0,
            "max_drawdown_pct": 90.0,
            "long_only": True,
        },
        "strategy": {
            "indicators": {
                "ema": {"fast_period": 2, "slow_period": 3},
                "rsi": {"period": 2, "overbought": 100, "oversold": 0},
                # Very wide SL/TP so bearish cross is the only potential early exit
                "atr": {"period": 2, "sl_atr_mult": 100.0, "tp_atr_mult": 100.0},
            }
        },
    }

    replay = run_replay(df, config)
    trades = replay["trades_df"]

    assert not trades.empty
    # Should be closed only on EOD in this synthetic setup.
    assert "SIGNAL_FLIP" not in set(trades["exit_reason"].tolist())
