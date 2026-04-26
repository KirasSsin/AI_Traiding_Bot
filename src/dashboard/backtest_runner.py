"""Dashboard backtest runner — wraps _run_wfa_single_symbol с caching + result schema.

S25 ADR 0039: dashboard-internal helper. NO new measurement code — pure adapter
к existing WFA pipeline (`src/__main__._run_wfa_single_symbol`).

Caching: results stored к `data/runs/<run_id>.json` где run_id = hash of
(strategy, symbol, interval, start, end). Reuse cached если same params re-requested.
Disk-based, no DB schema change.

Concurrency: 1 backtest at-a-time per architecture verdict. Simple threading.Lock.
"""
from __future__ import annotations

import hashlib
import json
import math
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.analytics.dsr import compute_dsr
from src.backtest.strategy_metrics import compute_t1_t6_metrics
from src.backtest.walk_forward import evaluate_acceptance_gate

# S25: strategy presets. Operator can extend.
STRATEGY_PRESETS: dict[str, dict[str, Any]] = {
    "ema_crossover_s13": {
        "label": "EMA crossover (S13 baseline)",
        "type": "ema_crossover",
        "indicators": {
            "ema": {"fast_period": 12, "slow_period": 26},
            "rsi": {"period": 14, "overbought": 68},
            "atr": {"period": 14, "sl_atr_mult": 1.5, "tp_atr_mult": 3.0},
        },
    },
    "mean_reversion_s15": {
        "label": "Mean-reversion (RSI 30/70 + BB 2.0σ) — S15 original",
        "type": "mean_reversion",
        "indicators": {
            "rsi": {"period": 14, "oversold": 30, "overbought": 70},
            "bb": {"period": 20, "k": 2.0},
            "atr": {"period": 14, "sl_atr_mult": 1.5, "tp_atr_mult": 3.0},
        },
    },
    "mean_reversion_s17_relaxed": {
        "label": "Mean-reversion (RSI 35/65 + BB 1.5σ) — S17 relaxed",
        "type": "mean_reversion",
        "indicators": {
            "rsi": {"period": 14, "oversold": 35, "overbought": 65},
            "bb": {"period": 20, "k": 1.5},
            "atr": {"period": 14, "sl_atr_mult": 1.5, "tp_atr_mult": 3.0},
        },
    },
}

# Supported intervals (per src/marketdata/bybit/rest.py registry + Bar.interval Literal).
# 30M (30) и 2H (120) skipped в dashboard MVP — Bar.interval Literal не supports их
# (pydantic ValidationError при backfill). Future enhancement: extend Bar model.
INTERVAL_LABELS: dict[str, str] = {
    "5": "5 minutes",
    "15": "15 minutes",
    "60": "1 hour",
    "240": "4 hours",
    "D": "1 day",
}

INTERVAL_FILE_LABEL: dict[str, str] = {
    "5": "5m",
    "15": "15m",
    "60": "1h",
    "240": "4h",
    "D": "1d",
}

BARS_PER_YEAR: dict[str, int] = {
    "5": 105120,
    "15": 35040,
    "60": 8760,
    "240": 2190,
    "D": 365,
}

_lock = threading.Lock()
_RUNS_DIR = Path("data/runs")


@dataclass(frozen=True)
class BacktestRequest:
    strategy_id: str
    symbol: str
    interval: str
    start: str  # YYYY-MM-DD
    end: str

    def run_id(self) -> str:
        s = f"{self.strategy_id}|{self.symbol}|{self.interval}|{self.start}|{self.end}"
        return hashlib.sha256(s.encode()).hexdigest()[:16]


def list_data_availability() -> dict[str, dict[str, Any]]:
    """Scan data/ directory для available parquet files. Returns per-symbol coverage."""
    import pandas as pd

    out: dict[str, dict[str, Any]] = {}
    data_dir = Path("data")
    for parquet in sorted(data_dir.glob("*USDT_*.parquet")):
        name = parquet.stem  # e.g. BTCUSDT_1h
        if name.endswith(".s2-backup"):
            continue
        try:
            symbol, label = name.rsplit("_", 1)
        except ValueError:
            continue
        # Map label → interval
        label_to_interval = {v: k for k, v in INTERVAL_FILE_LABEL.items()}
        interval = label_to_interval.get(label)
        if interval is None:
            continue
        try:
            df = pd.read_parquet(parquet)
            if "time" not in df.columns:
                continue
            ts = pd.to_datetime(df["time"])
            sym_dict = out.setdefault(symbol, {})
            sym_dict[interval] = {
                "interval": interval,
                "label": INTERVAL_LABELS.get(interval, interval),
                "bars": len(df),
                "start": str(ts.iloc[0]),
                "end": str(ts.iloc[-1]),
                "file": str(parquet),
            }
        except Exception as e:  # noqa: BLE001
            continue
    return out


def run_backtest(req: BacktestRequest, *, force: bool = False) -> dict[str, Any]:
    """Run WFA на given request. Cached to disk by run_id.

    Args:
        req: BacktestRequest specification
        force: bypass cache, re-run

    Returns:
        Dict с full WFA result + warnings + metadata.

    Raises:
        ValueError: invalid strategy/interval
        FileNotFoundError: missing parquet for (symbol, interval)
    """
    _RUNS_DIR.mkdir(parents=True, exist_ok=True)
    run_id = req.run_id()
    cache_path = _RUNS_DIR / f"{run_id}.json"
    if not force and cache_path.exists():
        result: dict[str, Any] = json.loads(cache_path.read_text())
        result["cached"] = True
        return result

    if req.strategy_id not in STRATEGY_PRESETS:
        raise ValueError(
            f"Unknown strategy '{req.strategy_id}'. "
            f"Supported: {sorted(STRATEGY_PRESETS.keys())}"
        )
    if req.interval not in BARS_PER_YEAR:
        raise ValueError(
            f"Unknown interval '{req.interval}'. "
            f"Supported: {sorted(BARS_PER_YEAR.keys())}"
        )
    preset = STRATEGY_PRESETS[req.strategy_id]

    with _lock:
        # Lazy import к keep dashboard module loadable без main module side effects
        from src.__main__ import _load_ohlcv, _run_wfa_single_symbol

        df = _load_ohlcv(symbol=req.symbol, start=req.start, end=req.end, interval=req.interval)
        if df.empty:
            raise FileNotFoundError(
                f"No OHLCV data для {req.symbol} {req.interval} в {req.start}..{req.end}"
            )

        # S25: build full WFA config from preset
        strategy_config: dict[str, object] = {
            "trading": {
                "initial_balance": 10000.0,
                "commission_taker": 0.001,
                "slippage": 0.0005,
                "position_size_pct": 10.0,
                "max_drawdown_pct": 50.0,
                "long_only": True,
            },
            "strategy": {
                "type": preset["type"],
                "indicators": preset["indicators"],
            },
        }
        from typing import cast
        from src.risk.trade_history import TradeRecord
        _sym_trades_raw, sym_fold_sharpes, sym_runner_result, sym_mc_p = _run_wfa_single_symbol(
            symbol=req.symbol, df=df, strategy_config=strategy_config,
        )
        sym_trades: list[TradeRecord] = cast(list[TradeRecord], _sym_trades_raw)

    bars_per_year = BARS_PER_YEAR[req.interval]
    metrics = compute_t1_t6_metrics(
        trades=list(sym_trades),
        fold_oos_is_sharpe=sym_fold_sharpes,
        bars_per_year=bars_per_year,
    )
    gate = evaluate_acceptance_gate(
        fold_oos_is_sharpe_ratios=sym_fold_sharpes,
        mc_p_value=sym_mc_p,
    )
    if sym_trades:
        dsr_value = compute_dsr(trades=list(sym_trades), n_trials=1)
    else:
        dsr_value = float("nan")

    def nan_safe(v: Any) -> Any:
        return None if (isinstance(v, float) and math.isnan(v)) else v

    # Apply CC4 hard requirement (Sortino anomaly guard, trader spec)
    sortino_raw = nan_safe(metrics["t2_sortino_oos"])
    n_trades = metrics["t5_n_trades"]
    sortino_display: Any
    sortino_warning: bool
    if isinstance(sortino_raw, (int, float)) and abs(sortino_raw) > 50 and n_trades < 100:
        sortino_display = None
        sortino_warning = True
    else:
        sortino_display = sortino_raw
        sortino_warning = False

    # Compute Tier 2 trade-level stats from sym_trades
    n_winners = sum(1 for t in sym_trades if float(t.pnl_quote) > 0)
    n_losers = sum(1 for t in sym_trades if float(t.pnl_quote) < 0)
    total_commissions = sum(float(t.fees_paid) for t in sym_trades)
    avg_win_quote = (
        sum(float(t.pnl_quote) for t in sym_trades if float(t.pnl_quote) > 0) / n_winners
        if n_winners > 0 else 0.0
    )
    avg_loss_quote = (
        sum(float(t.pnl_quote) for t in sym_trades if float(t.pnl_quote) < 0) / n_losers
        if n_losers > 0 else 0.0
    )
    gross_profit = sum(float(t.pnl_quote) for t in sym_trades if float(t.pnl_quote) > 0)
    gross_loss = abs(sum(float(t.pnl_quote) for t in sym_trades if float(t.pnl_quote) < 0))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else None
    total_pnl = sum(float(t.pnl_quote) for t in sym_trades)
    # Verdict
    failed_criteria: list[str] = []
    t1 = nan_safe(metrics["t1_sharpe_oos"])
    if t1 is None or t1 < 1.0:
        failed_criteria.append("t1")
    if sortino_display is None or (isinstance(sortino_display, float) and sortino_display < 1.5):
        failed_criteria.append("t2")
    t3 = nan_safe(metrics["t3_max_drawdown"])
    if t3 is None or t3 >= 0.25:
        failed_criteria.append("t3")
    t4_win = nan_safe(metrics["t4_win_rate"])
    t4_rr = nan_safe(metrics["t4_avg_rr"])
    t4_fail = (
        t4_win is None or t4_rr is None
        or (t4_rr >= 2.0 and t4_win < 0.35)
        or (1.5 <= t4_rr < 2.0 and t4_win < 0.45)
        or t4_rr < 1.5
    )
    if t4_fail:
        failed_criteria.append("t4")
    t5_t = nan_safe(metrics["t5_t_stat"])
    t5_mean = nan_safe(metrics["t5_mean_pnl_pct"])
    if (
        n_trades < 100
        or t5_mean is None or t5_mean <= 0
        or t5_t is None or t5_t < 2.0
    ):
        failed_criteria.append("t5")
    t6 = nan_safe(metrics["t6_oos_is_sharpe_ratio_mean"])
    if t6 is None or t6 < 0.7:
        failed_criteria.append("t6")
    dsr_pass = nan_safe(dsr_value) is not None and dsr_value > 0
    verdict = "PASS" if not failed_criteria and dsr_pass else "FAIL"

    # Risk warnings (trader spec, 4 mandatory)
    warnings: list[dict[str, str]] = []
    if isinstance(t1, (int, float)) and t1 > 3.0:
        warnings.append({
            "level": "high",
            "code": "overfit_sharpe",
            "message": f"T1 Sharpe={t1:.2f} > 3.0 — почти наверняка overfit (Hudson & Urquhart 2021).",
        })
    fold_max = max(sym_fold_sharpes) if sym_fold_sharpes else 0.0
    positive_folds = [s for s in sym_fold_sharpes if s > 0]
    fold_median_pos = sorted(positive_folds)[len(positive_folds) // 2] if positive_folds else 0.0
    if fold_max > 5 or (positive_folds and fold_max > 2 * fold_median_pos):
        warnings.append({
            "level": "high",
            "code": "regime_concentration",
            "message": f"Fold с Sharpe={fold_max:.2f} drives aggregate — regime-specific signal.",
        })
    if isinstance(sym_mc_p, (int, float)) and sym_mc_p > 0.10:
        warnings.append({
            "level": "high",
            "code": "mc_noise",
            "message": f"MC permutation p={sym_mc_p:.3f} > 0.10 — returns indistinguishable от random.",
        })
    if isinstance(dsr_value, (int, float)) and not math.isnan(dsr_value) and dsr_value <= 0:
        warnings.append({
            "level": "high",
            "code": "dsr_penalty",
            "message": f"DSR={dsr_value:.3f} ≤ 0 — claimed edge не credible after multi-testing adjustment.",
        })
    if sortino_warning:
        warnings.append({
            "level": "info",
            "code": "sortino_anomaly",
            "message": "Sortino > 50 + n_trades < 100 = small-sample artifact (отображено как N/A).",
        })
    if n_trades < 100:
        warnings.append({
            "level": "warn",
            "code": "low_sample",
            "message": f"n_trades={n_trades} < 100 — недостаточно для t-test validity.",
        })

    result = {
        "run_id": run_id,
        "request": {
            "strategy_id": req.strategy_id,
            "strategy_label": preset["label"],
            "strategy_config": preset,
            "symbol": req.symbol,
            "interval": req.interval,
            "interval_label": INTERVAL_LABELS.get(req.interval, req.interval),
            "start": req.start,
            "end": req.end,
        },
        "verdict": verdict,
        "failed_criteria": failed_criteria,
        "metrics": {
            "t1_sharpe_oos": t1,
            "t2_sortino_oos": sortino_display,
            "t2_sortino_raw": sortino_raw,
            "t2_sortino_anomaly_guard": sortino_warning,
            "t3_max_drawdown": t3,
            "t4_win_rate": t4_win,
            "t4_avg_rr": t4_rr,
            "t5_mean_pnl_pct": t5_mean,
            "t5_t_stat": t5_t,
            "t5_n_trades": n_trades,
            "t6_oos_is_sharpe_ratio_mean": t6,
        },
        "trade_stats": {
            "n_winners": n_winners,
            "n_losers": n_losers,
            "total_commissions_quote": total_commissions,
            "avg_win_quote": avg_win_quote,
            "avg_loss_quote": avg_loss_quote,
            "profit_factor": profit_factor,
            "total_pnl_quote": total_pnl,
        },
        "fold_sharpe_ratios": sym_fold_sharpes,
        "failed_folds": gate.get("failed_folds", []),
        "dsr": nan_safe(dsr_value),
        "dsr_pass": dsr_pass,
        "mc_p_value": sym_mc_p,
        "acceptance_gate": gate,
        "bars_per_year": bars_per_year,
        "warnings": warnings,
        "cached": False,
    }

    # Cache к disk
    cache_path.write_text(json.dumps(result, default=str, indent=2))
    return result


def list_runs() -> list[dict[str, Any]]:
    """List previously cached runs (newest first)."""
    if not _RUNS_DIR.exists():
        return []
    entries: list[dict[str, Any]] = []
    for p in sorted(_RUNS_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            data = json.loads(p.read_text())
            entries.append({
                "run_id": data.get("run_id"),
                "request": data.get("request", {}),
                "verdict": data.get("verdict"),
                "metrics": data.get("metrics", {}),
                "warnings_count": len(data.get("warnings", [])),
                "mtime": p.stat().st_mtime,
            })
        except Exception:  # noqa: BLE001
            continue
    return entries


def get_run(run_id: str) -> dict[str, Any] | None:
    """Fetch full run by run_id."""
    p = _RUNS_DIR / f"{run_id}.json"
    if not p.exists():
        return None
    return json.loads(p.read_text())  # type: ignore[no-any-return]
