"""Live-data adapted reporter per ADR 0055 SD-6.

Differences от backtest reporter (src/backtest/wfa_reporter.py):
  - Sharpe computed on per-TradeRecord pnl_pct returns (dimensionless; NOT pnl_quote absolute P&L)
  - T6 OOS/IS → live/synthetic calibration ratio (S22 pre-registered benchmark)
  - MC gated на sample size (sign-flip n>=20, block-bootstrap n>=40)
  - DSR thresholds per ADR 0056 (<10 NaN, 10-30 UNDERPOWERED, >=30 GATE_ELIGIBLE)

N_trials freeze=7 per ADR 0055 SD-7 (mean-reversion family hypothesis re-evaluation,
no Bailey 2014 multi-testing increment).
"""

from __future__ import annotations

import math
import statistics
from typing import Any

import numpy as np

from src.analytics.dsr import compute_dsr_with_status
from src.backtest.mc_permutation import block_bootstrap_p_value, sign_flip_p_value
from src.risk.trade_history import TradeRecord

# S37 T6 ADR 0056 amendment: mean fold Sharpe (conservative) replaces T1 aggregate (extreme).
# Mean of S22 fold_sharpe_ratios [1.93, -2.92, 1.32, 12.70, 1.78] = 2.962
# Original 6.17 was T1 aggregate inflated by fold #4 outlier (Sharpe=12.70 at n≈12 trades).
# Conservative mean fold = realistic calibration ratio target ≥0.7.
S22_SYNTHETIC_SHARPE: float = 2.96

# Cumulative mean-reversion family hypothesis count per ADR 0055 SD-7:
# S13 EMA crossover, S15 mean-reversion strict, S17 mean-reversion relaxed,
# S20 mean-reversion 15M, S22 mean-reversion 4H, S33 multi-symbol mean-reversion,
# S35 Donchian breakout. δ TESTNET = S22 hypothesis re-evaluation (frozen).
DELTA_N_TRIALS_LOCKED: int = 7

# MC gating thresholds per ADR 0055 SD-6
_MC_SIGN_FLIP_MIN_N: int = 20
_MC_BLOCK_BOOTSTRAP_MIN_N: int = 40
# S39 T11 F8 — re-export canonical block size from mc_permutation (single source of truth)
from src.backtest.mc_permutation import MC_BLOCK_SIZE as _MC_BLOCK_SIZE  # noqa: E402

_MC_ITERATIONS: int = 2000
_MC_SEED: int = 42

# 4H bars per year (365.25 * 6 = 2191.5 → 2191; L6 unify on 365.25 family)
_DEFAULT_BARS_PER_YEAR: int = 2191

# M5 (S49): NOMINAL holding-period scale — a PLACEHOLDER, not a measured value.
# Used only to annualize the INFORMATIONAL live Sharpe (never a gate input).
# It is a fixed assumption of ~12 bars (4H × 12 = 2 days) per trade; the real
# holding period is not plumbed through to this reporter. Do NOT treat the
# resulting Sharpe scale as measured — see M5 note in compute_live_sharpe.
_AVG_BARS_PER_TRADE_PLACEHOLDER: float = 12.0


def compute_live_sharpe(
    records: list[TradeRecord],
    *,
    bars_per_year: int = _DEFAULT_BARS_PER_YEAR,
    avg_bars_per_trade: float = _AVG_BARS_PER_TRADE_PLACEHOLDER,
) -> dict[str, Any]:
    """Annualized live Sharpe + status flag per ADR 0056 thresholds.

    Returns dict с keys: sharpe (float, NaN если insufficient), status, n.
    Status: INSUFFICIENT_TRADES (n<10) / DEGENERATE_VARIANCE / UNDERPOWERED (10<=n<30) / GATE_ELIGIBLE (n>=30).

    Per ADR 0056 amendment 2 + S38 F2 HIGH: returns extracted from pnl_pct (dimensionless
    fractional returns), NOT pnl_quote (absolute P&L scales with position size → Kelly bias).

    M5 (S49) WARNING: ``avg_bars_per_trade`` defaults to a NOMINAL PLACEHOLDER
    (~12 bars), NOT the measured holding period — the actual entry→exit bar count
    is not plumbed to this reporter. The annualized Sharpe is INFORMATIONAL (never
    a gate). If a real mean holding becomes available, pass it explicitly; do not
    mistake the default-scaled Sharpe for a measured annualization.
    """
    n = len(records)
    if n < 10:
        return {"sharpe": float("nan"), "status": "INSUFFICIENT_TRADES", "n": n}
    returns = [float(r.pnl_pct) for r in records]
    mean = statistics.mean(returns)
    sd = statistics.stdev(returns) if n > 1 else 0.0
    if sd == 0.0:
        return {"sharpe": float("nan"), "status": "DEGENERATE_VARIANCE", "n": n}
    trades_per_year = bars_per_year / avg_bars_per_trade
    sharpe = (mean / sd) * math.sqrt(trades_per_year)
    status = "UNDERPOWERED" if n < 30 else "GATE_ELIGIBLE"
    return {"sharpe": sharpe, "status": status, "n": n}


def compute_calibration_ratio(
    *,
    live_sharpe: float,
    synthetic_s22_sharpe: float = S22_SYNTHETIC_SHARPE,
) -> float:
    """T6 replacement per ADR 0055 SD-6: live / synthetic Sharpe ratio.

    NaN guards: synthetic_zero OR live_NaN → NaN (defensive).
    PASS = ratio >= 0.7 (caller decides).
    """
    if synthetic_s22_sharpe == 0.0:
        return float("nan")
    if math.isnan(live_sharpe):
        return float("nan")
    return live_sharpe / synthetic_s22_sharpe


def compute_mc_with_gating(returns: list[float]) -> dict[str, Any]:
    """MC permutation с n-gated test selection per ADR 0055 SD-6.

    Returns dict: sign_flip (float|None), block_bootstrap (float|None), status, n.
    Below n=20: both None, status MC_INSUFFICIENT_N.
    20<=n<40: sign-flip only, block_bootstrap None.
    n>=40: both computed.
    """
    n = len(returns)
    if n < _MC_SIGN_FLIP_MIN_N:
        return {
            "sign_flip": None,
            "block_bootstrap": None,
            "status": "MC_INSUFFICIENT_N",
            "n": n,
        }
    arr = np.array(returns, dtype=np.float64)
    sign_flip = sign_flip_p_value(arr, n_iterations=_MC_ITERATIONS, seed=_MC_SEED)
    block_bs: float | None = None
    if n >= _MC_BLOCK_BOOTSTRAP_MIN_N:
        block_bs = block_bootstrap_p_value(
            arr,
            block_size=_MC_BLOCK_SIZE,
            n_iterations=_MC_ITERATIONS,
            seed=_MC_SEED,
        )
    return {
        "sign_flip": sign_flip,
        "block_bootstrap": block_bs,
        "status": "OK",
        "n": n,
    }


def generate_live_report(records: list[TradeRecord]) -> dict[str, Any]:
    """Single entry point — full live demo report per ADR 0055 SD-6 methodology.

    Combines live Sharpe + calibration ratio + MC + DSR с все status flags.
    Used при 12mo TESTNET review OR ad-hoc operator audit.
    """
    sharpe_info = compute_live_sharpe(records)
    calibration = compute_calibration_ratio(live_sharpe=sharpe_info["sharpe"])
    # S38 T2 ADR 0056 amendment 2: MC permutation also requires dimensionless returns.
    # pnl_quote scales с position size — same Kelly variance bias as Sharpe.
    # Mirror compute_live_sharpe extraction для consistency.
    returns = [float(r.pnl_pct) for r in records]
    mc_info = compute_mc_with_gating(returns)
    # DSR с n_trials=1 (single hypothesis re-eval, no cross-trial pooling penalty).
    # Future: pass n_trials=DELTA_N_TRIALS_LOCKED с pooled sigma_sr for full
    # multi-testing correction when cross-trial live data accumulates.
    dsr_info = compute_dsr_with_status(trades=records, n_trials=1)
    return {
        "n_trades": len(records),
        "live_sharpe": sharpe_info,
        "calibration_ratio_to_s22": calibration,
        "mc": mc_info,
        "dsr": dsr_info,
        "n_trials_counter": DELTA_N_TRIALS_LOCKED,
        "methodology": "ADR_0055_SD6_LIVE_ADAPTED",
    }
