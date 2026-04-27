import pandas as pd

from src.backtest.replay_engine import run_replay


def _build_df() -> pd.DataFrame:
    """Fixture с cross_up at bar 6 AFTER RSI warm-up.

    Post-S27 T3 (RSI warm-up gating fix): RSI NaN bars 0-4, defined bar 5+.
    Cross_up signal требует RSI defined (NaN < overbought = False suppresses).
    Fixture: 5 bars decline (baseline), rally bar 6 → cross_up + RSI=72 < 100 → signal=1.
    """
    prices = [110, 108, 106, 104, 102, 100, 105, 110, 115, 120, 118, 116]
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
    # Post-S27 T3 RSI warm-up fix: cross_up at bar 6 (RSI defined), entry at bar 7 (next open).
    signal_index = 6
    expected_entry_ts = df.iloc[signal_index + 1]["timestamp"]
    expected_entry_price = float(df.iloc[signal_index + 1]["open"])

    assert first_trade["timestamp_open"] == expected_entry_ts
    assert first_trade["entry_price"] == expected_entry_price

