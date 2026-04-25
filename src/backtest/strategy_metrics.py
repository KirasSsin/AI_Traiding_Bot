"""T1-T6 strategy validation metrics extraction.

Sprint 13 Task 6 (per ADR 0028 Q5). Per acceptance-criteria.md (amended footnotes
S13 PHASE 2 reconciliation):
- T1: Sharpe OOS annualized >= 1.0
- T2: Sortino OOS >= 1.5
- T3: MaxDD < 25%
- T4: Win rate >= 45% при RR>=1.5 OR >=35% при RR>=2.0
- T5: Mean pnl_pct > 0, t-stat > 2.0, n >= 100 OOS
- T6: OOS/IS Sharpe ratio mean >= 0.7

Annualization: sqrt(8760) для 24/7 crypto 1H bars (per ADR 0025).

CC1: N_trials tracking — extractor receives n_trials from caller (consumer
responsibility). DSR consumed via separate compute_dsr call.
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np

from src.risk.trade_history import TradeRecord


# Annualization factor: sqrt(365*24) для 24/7 crypto 1H bars.
_ANNUALIZATION_FACTOR = float(np.sqrt(8760))


def compute_t1_t6_metrics(
    *,
    trades: list[TradeRecord],
    fold_oos_is_sharpe: list[float],
    initial_capital: float = 10000.0,
) -> dict[str, Any]:
    """Compute T1-T6 acceptance criteria metrics from OOS trades.

    Args:
        trades: list of OOS TradeRecord (use trade_extractor for WFA fold output).
        fold_oos_is_sharpe: per-fold OOS/IS Sharpe ratio.
        initial_capital: backtest starting balance (matches WFA config).

    Returns:
        dict с t1-t6 fields. NaN если insufficient data.
    """
    n = len(trades)

    if n == 0:
        return {
            "t1_sharpe_oos": float("nan"),
            "t2_sortino_oos": float("nan"),
            "t3_max_drawdown": float("nan"),
            "t4_win_rate": float("nan"),
            "t4_avg_rr": float("nan"),
            "t5_mean_pnl_pct": float("nan"),
            "t5_t_stat": float("nan"),
            "t5_n_trades": 0,
            "t6_oos_is_sharpe_ratio_mean": (
                float(np.mean(fold_oos_is_sharpe)) if fold_oos_is_sharpe else float("nan")
            ),
        }

    pnl_pcts = np.array([float(t.pnl_pct) for t in trades])
    pnl_quotes = np.array([float(t.pnl_quote) for t in trades])

    # T1: Sharpe OOS annualized
    if pnl_pcts.std(ddof=1) > 0:
        sharpe_per_trade = float(pnl_pcts.mean() / pnl_pcts.std(ddof=1))
        t1_sharpe_oos = sharpe_per_trade * _ANNUALIZATION_FACTOR
    else:
        t1_sharpe_oos = float("nan")

    # T2: Sortino OOS (downside deviation)
    losers = pnl_pcts[pnl_pcts < 0]
    if len(losers) > 0 and losers.std(ddof=1) > 0:
        sortino_per_trade = float(pnl_pcts.mean() / losers.std(ddof=1))
        t2_sortino_oos = sortino_per_trade * _ANNUALIZATION_FACTOR
    else:
        t2_sortino_oos = float("nan")

    # T3: Max Drawdown (peak-to-trough on equity curve)
    equity = np.cumsum(pnl_quotes)
    equity_with_capital = initial_capital + equity
    running_max = np.maximum.accumulate(equity_with_capital)
    # Guard: total blowout (running_max=0) -> -100%, NOT NaN
    drawdowns = np.where(
        running_max > 0,
        (equity_with_capital - running_max) / running_max,
        -1.0,
    )
    t3_max_drawdown = float(abs(drawdowns.min())) if len(drawdowns) > 0 else 0.0

    # T4: Win rate + avg RR
    winners = pnl_pcts[pnl_pcts > 0]
    losers_abs = np.abs(pnl_pcts[pnl_pcts < 0])
    t4_win_rate = len(winners) / n
    if len(winners) > 0 and len(losers_abs) > 0:
        t4_avg_rr = float(winners.mean() / losers_abs.mean())
    else:
        t4_avg_rr = float("nan")

    # T5: Mean pnl_pct + t-stat
    t5_mean_pnl_pct = float(pnl_pcts.mean())
    if pnl_pcts.std(ddof=1) > 0 and n > 1:
        t5_t_stat = float(pnl_pcts.mean() / (pnl_pcts.std(ddof=1) / math.sqrt(n)))
    else:
        t5_t_stat = float("nan")

    # T6: OOS/IS Sharpe ratio mean
    if fold_oos_is_sharpe:
        t6_oos_is_sharpe_ratio_mean = float(np.mean(fold_oos_is_sharpe))
    else:
        t6_oos_is_sharpe_ratio_mean = float("nan")

    return {
        "t1_sharpe_oos": t1_sharpe_oos,
        "t2_sortino_oos": t2_sortino_oos,
        "t3_max_drawdown": t3_max_drawdown,
        "t4_win_rate": t4_win_rate,
        "t4_avg_rr": t4_avg_rr,
        "t5_mean_pnl_pct": t5_mean_pnl_pct,
        "t5_t_stat": t5_t_stat,
        "t5_n_trades": n,
        "t6_oos_is_sharpe_ratio_mean": t6_oos_is_sharpe_ratio_mean,
    }
