from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from src.backtest.indicators import calculate_indicators


def _to_bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _holding_time_seconds(timestamp_open: Any, timestamp_close: Any) -> float:
    # S49 M3: narrowed from bare `except Exception` to the only failure modes
    # possible here — incompatible/None timestamp types (TypeError), non-numeric
    # delta (ValueError), or missing attribute (AttributeError). A real bug now
    # propagates instead of being swallowed as 0.0.
    try:
        delta = timestamp_close - timestamp_open
        if hasattr(delta, "total_seconds"):
            return float(delta.total_seconds())
        delta_float = float(delta)
        # If timestamps are milliseconds, convert to seconds.
        return delta_float / 1000.0 if abs(delta_float) > 1_000_000 else delta_float
    except (TypeError, ValueError, AttributeError):
        return 0.0


def _compute_metrics(
    equity_df: pd.DataFrame,
    trades_df: pd.DataFrame,
    initial_balance: float,
    bars_per_year: int = 8760,
) -> Dict[str, float]:
    """S27 T1: bars_per_year parameterized — sqrt(bars_per_year) annualization.

    Pre-S27 bug: hardcoded sqrt(24*365)=sqrt(8760) для всех timeframes.
    For 4H bars (bars_per_year=2190): IS Sharpe overstated 2x → corrupts
    fold OOS/IS ratios → artificial acceptance_gate FAIL.
    For 15M/5M (bars_per_year=35040/105120): IS understated → inflated ratios.
    Default 8760 = 1H для backward compat.
    """
    if equity_df.empty:
        return {}

    equity = equity_df["balance"].astype(float)
    returns = equity.pct_change().replace([np.inf, -np.inf], np.nan).dropna()

    wins = trades_df[trades_df["net_pnl"] > 0] if not trades_df.empty else pd.DataFrame()
    losses = trades_df[trades_df["net_pnl"] < 0] if not trades_df.empty else pd.DataFrame()

    gross_profit = float(wins["net_pnl"].sum()) if not wins.empty else 0.0
    gross_loss = abs(float(losses["net_pnl"].sum())) if not losses.empty else 0.0
    net_profit = float(gross_profit - gross_loss)

    rolling_max = equity.cummax()
    drawdown_abs = (rolling_max - equity).fillna(0.0)
    drawdown_pct = drawdown_abs / rolling_max.replace(0, np.nan)

    annualization_factor = float(np.sqrt(bars_per_year))

    sharpe = 0.0
    if not returns.empty and float(returns.std()) > 0:
        sharpe = float((returns.mean() / returns.std()) * annualization_factor)

    # S27 T2: canonical Sortino downside deviation (Sortino & Price 1994).
    # Pre-fix used downside.std() — std of negative returns subset, mean-centered.
    # Canonical: sqrt(mean(min(r, 0)^2)) over ALL returns.
    sortino = 0.0
    if not returns.empty:
        downside = returns.where(returns < 0, 0.0)
        downside_dev = float(np.sqrt((downside**2).mean()))
        if downside_dev > 0:
            sortino = float((returns.mean() / downside_dev) * annualization_factor)

    total_trades = float(len(trades_df))
    win_rate = float(len(wins) / total_trades * 100.0) if total_trades > 0 else 0.0
    loss_rate = float(len(losses) / total_trades * 100.0) if total_trades > 0 else 0.0
    expectancy = float(net_profit / total_trades) if total_trades > 0 else 0.0

    total_commissions = 0.0
    if not trades_df.empty and {"entry_fee", "exit_fee"}.issubset(set(trades_df.columns)):
        total_commissions = float((trades_df["entry_fee"] + trades_df["exit_fee"]).sum())

    avg_holding_hours = 0.0
    if not trades_df.empty:
        if "holding_hours" in trades_df.columns:
            avg_holding_hours = float(trades_df["holding_hours"].mean())
        elif "holding_time_seconds" in trades_df.columns:
            avg_holding_hours = float(trades_df["holding_time_seconds"].mean() / 3600.0)

    avg_win = float(wins["net_pnl"].mean()) if not wins.empty else 0.0
    avg_loss = float(losses["net_pnl"].mean()) if not losses.empty else 0.0

    metrics = {
        "Total Return (%)": float((equity.iloc[-1] / initial_balance - 1.0) * 100.0),
        "Max Drawdown (%)": float(drawdown_pct.max() * 100.0) if not drawdown_pct.empty else 0.0,
        "Sharpe Ratio": sharpe,
        "Win Rate (%)": win_rate,
        "Profit Factor": float(gross_profit / gross_loss) if gross_loss > 0 else 0.0,
        "Total Trades": total_trades,
        "Gross Profit": gross_profit,
        "Gross Loss": gross_loss,
        "Net Profit": net_profit,
        "Net Profit (USDT)": net_profit,
        "Loss Rate (%)": loss_rate,
        "Expectancy": expectancy,
        "Expectancy (USDT)": expectancy,
        "Average Win": avg_win,
        "Average Loss": avg_loss,
        "Sortino Ratio": sortino,
        "Max Drawdown (USDT)": float(drawdown_abs.max()) if not drawdown_abs.empty else 0.0,
        "Total Commissions": total_commissions,
        "Total Commissions (USDT)": total_commissions,
        "Average Holding Time (hours)": avg_holding_hours,
        "Avg Holding Time (hours)": avg_holding_hours,
    }
    return metrics


def run_replay(df: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
    if df.empty:
        return {"equity_df": pd.DataFrame(), "trades_df": pd.DataFrame(), "metrics": {}}

    trading = config.get("trading", {})
    indicators_cfg = config.get("strategy", {}).get("indicators", {})
    atr_cfg = indicators_cfg.get("atr", {})

    initial_balance = float(trading.get("initial_balance", 10000.0))
    commission = float(trading.get("commission_taker", 0.001))
    slippage = float(trading.get("slippage", 0.0005))
    pos_pct = float(trading.get("position_size_pct", 10.0)) / 100.0
    max_drawdown = float(trading.get("max_drawdown_pct", 20.0)) / 100.0
    long_only = _to_bool(trading.get("long_only", False))
    bars_per_year = int(config.get("bars_per_year", 8760))  # S27 T1: timeframe annualization
    sl_mult = float(atr_cfg.get("sl_atr_mult", 1.5))
    tp_mult = float(atr_cfg.get("tp_atr_mult", 3.0))

    data = calculate_indicators(df, config)

    balance = initial_balance
    high_water_mark = initial_balance
    position: Optional[Dict[str, Any]] = None
    pending_entry: Optional[Dict[str, Any]] = None
    trades: List[Dict[str, Any]] = []
    equity_rows: List[Dict[str, Any]] = []

    for i in range(len(data)):
        row = data.iloc[i]
        ts = row["timestamp"]
        close_price = float(row["close"])
        low_price = float(row["low"])
        high_price = float(row["high"])
        signal = int(row["signal"])

        if position is None and pending_entry is not None and pending_entry["timestamp_open"] == ts:
            position = pending_entry
            pending_entry = None

        if position is not None:
            side = position["direction"]
            exit_reason = None
            raw_exit_price = None

            if side == "BUY":
                if low_price <= position["sl"]:
                    raw_exit_price = position["sl"]
                    exit_reason = "SL"
                elif high_price >= position["tp"]:
                    raw_exit_price = position["tp"]
                    exit_reason = "TP"
                elif signal == -1 and not long_only:
                    raw_exit_price = close_price
                    exit_reason = "SIGNAL_FLIP"
            else:
                if high_price >= position["sl"]:
                    raw_exit_price = position["sl"]
                    exit_reason = "SL"
                elif low_price <= position["tp"]:
                    raw_exit_price = position["tp"]
                    exit_reason = "TP"
                elif signal == 1 and not long_only:
                    raw_exit_price = close_price
                    exit_reason = "SIGNAL_FLIP"

            if i == len(data) - 1 and raw_exit_price is None:
                raw_exit_price = close_price
                exit_reason = "EOD"

            if raw_exit_price is not None:
                if side == "BUY":
                    exit_price = raw_exit_price * (1.0 - slippage)
                    gross_pnl = (exit_price - position["entry_price"]) * position["qty"]
                else:
                    exit_price = raw_exit_price * (1.0 + slippage)
                    gross_pnl = (position["entry_price"] - exit_price) * position["qty"]

                entry_fee = position["entry_fee"]
                exit_fee = exit_price * position["qty"] * commission
                net_pnl = gross_pnl - entry_fee - exit_fee
                balance += net_pnl

                holding_seconds = _holding_time_seconds(position["timestamp_open"], ts)
                trades.append(
                    {
                        "timestamp_open": position["timestamp_open"],
                        "timestamp_close": ts,
                        "direction": side,
                        "entry_price": position["entry_price"],
                        "exit_price": exit_price,
                        "qty": position["qty"],
                        "spend": position["spend"],
                        "gross_pnl": gross_pnl,
                        "entry_fee": entry_fee,
                        "exit_fee": exit_fee,
                        "net_pnl": net_pnl,
                        "exit_reason": exit_reason,
                        "reason_code": exit_reason,
                        "holding_hours": holding_seconds / 3600.0,
                        "holding_time_seconds": holding_seconds,
                    }
                )
                position = None

        entry_allowed = signal in (1, -1) and not (long_only and signal == -1)
        if position is None and pending_entry is None and entry_allowed and i < len(data) - 1:
            spend = max(0.0, balance * pos_pct)
            if spend > 0:
                next_row = data.iloc[i + 1]
                next_open = float(next_row["open"])
                if signal == 1:
                    entry_price = next_open * (1.0 + slippage)
                    side = "BUY"
                else:
                    entry_price = next_open * (1.0 - slippage)
                    side = "SELL"
                qty = spend / entry_price if entry_price > 0 else 0.0
                atr = float(row["atr"]) if not pd.isna(row["atr"]) else close_price * 0.01

                if side == "BUY":
                    sl = entry_price - sl_mult * atr
                    tp = entry_price + tp_mult * atr
                else:
                    sl = entry_price + sl_mult * atr
                    tp = entry_price - tp_mult * atr

                entry_fee = entry_price * qty * commission
                pending_entry = {
                    "direction": side,
                    "timestamp_open": next_row["timestamp"],
                    "entry_price": entry_price,
                    "qty": qty,
                    "spend": spend,
                    "sl": sl,
                    "tp": tp,
                    "entry_fee": entry_fee,
                }

        high_water_mark = max(high_water_mark, balance)
        drawdown = (high_water_mark - balance) / high_water_mark if high_water_mark > 0 else 0.0

        if drawdown >= max_drawdown:
            if position is not None:
                if position["direction"] == "BUY":
                    exit_price = close_price * (1.0 - slippage)
                    gross_pnl = (exit_price - position["entry_price"]) * position["qty"]
                else:
                    exit_price = close_price * (1.0 + slippage)
                    gross_pnl = (position["entry_price"] - exit_price) * position["qty"]
                entry_fee = position["entry_fee"]
                exit_fee = exit_price * position["qty"] * commission
                net_pnl = gross_pnl - entry_fee - exit_fee
                balance += net_pnl
                holding_seconds = _holding_time_seconds(position["timestamp_open"], ts)
                trades.append(
                    {
                        "timestamp_open": position["timestamp_open"],
                        "timestamp_close": ts,
                        "direction": position["direction"],
                        "entry_price": position["entry_price"],
                        "exit_price": exit_price,
                        "qty": position["qty"],
                        "spend": position["spend"],
                        "gross_pnl": gross_pnl,
                        "entry_fee": entry_fee,
                        "exit_fee": exit_fee,
                        "net_pnl": net_pnl,
                        "exit_reason": "KILL_SWITCH",
                        "reason_code": "KILL_SWITCH",
                        "holding_hours": holding_seconds / 3600.0,
                        "holding_time_seconds": holding_seconds,
                    }
                )
                position = None

            equity_rows.append({"timestamp": ts, "balance": balance})
            break

        mark_to_market = balance
        if position is not None:
            if position["direction"] == "BUY":
                mark_to_market += (close_price - position["entry_price"]) * position["qty"]
            else:
                mark_to_market += (position["entry_price"] - close_price) * position["qty"]
        equity_rows.append({"timestamp": ts, "balance": mark_to_market})

    equity_df = pd.DataFrame(equity_rows)
    trades_df = pd.DataFrame(trades)
    if trades_df.empty:
        trades_df = pd.DataFrame(
            columns=[
                "timestamp_open",
                "timestamp_close",
                "direction",
                "entry_price",
                "exit_price",
                "qty",
                "spend",
                "gross_pnl",
                "entry_fee",
                "exit_fee",
                "net_pnl",
                "exit_reason",
                "reason_code",
                "holding_hours",
                "holding_time_seconds",
            ]
        )
    metrics = _compute_metrics(equity_df, trades_df, initial_balance, bars_per_year=bars_per_year)
    return {"equity_df": equity_df, "trades_df": trades_df, "metrics": metrics}
