"""S27 audit script — comprehensive formula/metric execution dump.

Two modes:
  1. `python scripts/audit_formulas.py --sweep`
     Full sweep: every (strategy × symbol × interval) combination.
     Calls dashboard's run_backtest() (cached если уже прогнан).
     Output: data/formulas_audit_v1.json

  2. `python scripts/audit_formulas.py` (default = rebuild only)
     Reads ALL data/runs/*.json (cached results from past sweeps + dashboard runs)
     → aggregates → emits data/formulas_audit_v1.json.
     NO new computation. Fast.

  3. Auto-refresh hook: dashboard run_backtest() calls rebuild_audit() after
     каждый POST /api/backtest. Audit doc stays current с UI activity.

Output format (optimization-ready для trader-expert subagent):
  - meta (git commit, tag, timestamp)
  - formulas_inventory (which file/function implements RSI/BB/ATR/EMA/Sharpe/DSR/MC)
  - acceptance_criteria thresholds
  - experiments[] — per-run full result + per-trade dump
  - summary — aggregate stats (best/worst, common failures)
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Repo root resolution (scripts/ is one level deep)
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

_RUNS_DIR = _REPO_ROOT / "data" / "runs"
_OUTPUT_PATH = _REPO_ROOT / "data" / "formulas_audit_v1.json"


# Formula provenance — where each formula lives + implementation choice.
# Trader can verify implementation matches expected math, flag discrepancies.
FORMULAS_INVENTORY: dict[str, dict[str, Any]] = {
    "rsi": {
        "name": "Relative Strength Index",
        "impl": "TA-Lib (C) — Wilder smoothing α=1/n",
        "file": "src/signalgen/indicators.py::calculate_rsi (uses talib.RSI)",
        "default_period": 14,
        "alternatives_considered": "classical EMA smoothing rejected per ADR 0011",
        "source": "Wilder, J.W. (1978) New Concepts in Technical Trading Systems",
    },
    "atr": {
        "name": "Average True Range",
        "impl": "TA-Lib (C) — Wilder smoothing",
        "file": "src/signalgen/indicators.py::calculate_atr (uses talib.ATR)",
        "default_period": 14,
        "source": "Wilder (1978)",
    },
    "ema": {
        "name": "Exponential Moving Average",
        "impl": "Classical α=2/(n+1) — pandas.ewm(span=n)",
        "file": "src/signalgen/indicators.py::calculate_ema",
        "default_periods": "fast=12, slow=26",
        "note": "ADR 0011: classical EMA used (NOT Wilder), per Murphy 1999",
    },
    "bb": {
        "name": "Bollinger Bands",
        "impl": "SMA ± k × stdev_pop (population stdev, ddof=0)",
        "file": "src/signalgen/bollinger_bands.py::bollinger_bands",
        "default_params": "period=20, k=2.0 (S15) или k=1.5 (S17)",
        "source": "Bollinger (2001)",
        "note": "stdev_pop choice (ddof=0) standard для BB",
    },
    "adx": {
        "name": "Average Directional Index",
        "impl": "TA-Lib (C)",
        "file": "src/signalgen/indicators.py::calculate_adx (uses talib.ADX)",
        "default_period": 14,
    },
    "sharpe_oos": {
        "name": "Sharpe ratio (out-of-sample)",
        "impl": "mean(returns) / std(returns) × sqrt(bars_per_year)",
        "file": "src/backtest/strategy_metrics.py::compute_t1_t6_metrics",
        "annualization": "sqrt(bars_per_year) per Lo (2002), bars_per_year parameterized in BARS_PER_YEAR map",
        "bars_per_year_table": {"5": 105120, "15": 35040, "60": 8760, "240": 2190, "D": 365},
        "denominator": "sample stdev (ddof=1)",
    },
    "sortino": {
        "name": "Sortino ratio",
        "impl": "mean(returns) / downside_deviation × sqrt(bars_per_year)",
        "file": "src/backtest/strategy_metrics.py::compute_t1_t6_metrics",
        "downside_def": "stdev of returns where r < 0 (target=0)",
        "guard": "if n_trades < 100 AND |sortino| > 50 → display N/A (small-sample artifact)",
    },
    "max_drawdown": {
        "name": "Maximum drawdown",
        "impl": "peak-to-trough on running cumulative pnl",
        "file": "src/backtest/strategy_metrics.py::compute_t1_t6_metrics",
        "formula": "max((peak - current) / peak) over equity curve",
    },
    "win_rate": {
        "name": "Win rate",
        "impl": "n_winners / n_trades (excludes break-even)",
        "file": "src/backtest/strategy_metrics.py::compute_t1_t6_metrics",
    },
    "avg_rr": {
        "name": "Average risk-reward ratio",
        "impl": "mean(|win_pnl| / |loss_pnl|) on trades с both winners + losers",
        "file": "src/backtest/strategy_metrics.py::compute_t1_t6_metrics",
    },
    "t_stat": {
        "name": "T-statistic for mean PnL",
        "impl": "mean / (stdev / sqrt(n))",
        "file": "src/backtest/strategy_metrics.py::compute_t1_t6_metrics",
        "threshold": "≥ 2.0 для T5 acceptance",
    },
    "dsr": {
        "name": "Deflated Sharpe Ratio",
        "impl": "Bailey & López de Prado (2014) — multi-trial penalty",
        "file": "src/analytics/dsr.py::compute_dsr",
        "formula": "Φ((SR_observed - E[max SR_random]) / sigma_SR)",
        "n_trials_input": "n_trials = 1 для single-WFA dashboard runs",
        "cross_trial_log": "data/cross_trial_sharpes.json (currently empty post-S23 archival)",
    },
    "mc_p_value": {
        "name": "Monte Carlo sign-flip p-value",
        "impl": "1000-2000 random sign permutations",
        "file": "src/backtest/mc_permutation.py::sign_flip_p_value",
        "h0": "trade returns from random distribution (no edge)",
        "p_threshold": "≤ 0.05 для acceptance",
    },
    "wfa_window": {
        "name": "Walk-Forward Analysis splitter",
        "impl": "K=5 folds, train=2000, test=500, embargo=20",
        "file": "src/backtest/walk_forward.py::WindowSplitter",
        "adr": "ADR 0014",
    },
    "acceptance_gate": {
        "name": "Per-fold acceptance gate",
        "impl": "ALL folds Sharpe ≥ 0.7 AND MC p ≤ 0.05",
        "file": "src/backtest/walk_forward.py::evaluate_acceptance_gate",
        "note": "Independent failure mode от T1-T6 (per-fold check)",
    },
    "kelly_sizing": {
        "name": "Kelly fractional sizing",
        "impl": "Phase 1-4 graduated (config: phase 1 = 25%, phase 2 = 50%, phase 3 = 75%, phase 4 = 100%)",
        "file": "src/risk/manager.py::RiskManager",
        "note": "Currently fixed phase=4 в WFA replay (no Kelly update)",
    },
    "commission_slippage": {
        "name": "Round-trip cost model",
        "impl": "commission_taker=0.001 × 2 + slippage=0.0005 × 2 = 0.30% per round-trip",
        "file": "src/backtest/replay_engine.py::run_replay",
        "config": "trading.commission_taker, trading.slippage в strategy_config",
    },
}

# Acceptance criteria thresholds — PER llm-wiki/wiki/project/architecture/acceptance-criteria.md
ACCEPTANCE_CRITERIA: dict[str, dict[str, Any]] = {
    "t1_sharpe_oos": {"threshold": 1.0, "operator": "≥", "rationale": "Modest edge claim"},
    "t2_sortino_oos": {"threshold": 1.5, "operator": "≥", "rationale": "Downside-aware Sharpe"},
    "t3_max_drawdown": {"threshold": 0.25, "operator": "<", "rationale": "Capital preservation"},
    "t4_win_rate_with_rr": {
        "rules": [
            "if avg_rr ≥ 2.0: win_rate ≥ 0.35",
            "if 1.5 ≤ avg_rr < 2.0: win_rate ≥ 0.45",
            "if avg_rr < 1.5: FAIL",
        ],
        "rationale": "Edge requires either high RR с low win rate OR moderate RR с good win rate",
    },
    "t5_n_trades": {"threshold": 100, "operator": "≥", "rationale": "Statistical t-test validity"},
    "t5_t_stat": {"threshold": 2.0, "operator": "≥", "rationale": "Mean PnL significantly > 0"},
    "t5_mean_pnl_pct": {"threshold": 0.0, "operator": ">", "rationale": "Edge positive"},
    "t6_oos_is_sharpe_ratio_mean": {"threshold": 0.7, "operator": "≥", "rationale": "Mean OOS/IS Sharpe across folds"},
    "dsr": {"threshold": 0.0, "operator": ">", "rationale": "Edge survives multi-testing penalty"},
    "acceptance_gate_sharpe_per_fold": {"threshold": 0.7, "operator": "≥ ALL folds"},
    "acceptance_gate_mc_p": {"threshold": 0.05, "operator": "≤"},
}


def _git_meta() -> dict[str, str]:
    """Capture git commit + tag (best-effort)."""
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=_REPO_ROOT, capture_output=True, text=True, check=True, timeout=5,
        ).stdout.strip()
    except Exception:  # noqa: BLE001
        commit = "unknown"
    try:
        tag = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            cwd=_REPO_ROOT, capture_output=True, text=True, check=True, timeout=5,
        ).stdout.strip()
    except Exception:  # noqa: BLE001
        tag = "unknown"
    return {"commit": commit, "tag": tag}


def _summarize_trades(trades: list[dict[str, Any]]) -> dict[str, Any]:
    """Best/worst trades + distribution для quick trader inspection."""
    if not trades:
        return {"first_5": [], "last_5": [], "best_3_by_pnl": [], "worst_3_by_pnl": []}
    sorted_by_pnl = sorted(trades, key=lambda t: t["pnl_quote"], reverse=True)
    return {
        "first_5": trades[:5],
        "last_5": trades[-5:],
        "best_3_by_pnl": sorted_by_pnl[:3],
        "worst_3_by_pnl": sorted_by_pnl[-3:][::-1],
    }


def _experiment_from_run(run_data: dict[str, Any]) -> dict[str, Any]:
    """Convert single data/runs/*.json к audit experiment entry."""
    req = run_data.get("request", {})
    trades = run_data.get("trades_dump", [])
    return {
        "experiment_id": run_data.get("run_id", ""),
        "strategy_id": req.get("strategy_id", ""),
        "strategy_label": req.get("strategy_label", ""),
        "strategy_config": req.get("strategy_config", {}),
        "symbol": req.get("symbol", ""),
        "interval": req.get("interval", ""),
        "interval_label": req.get("interval_label", ""),
        "data_window": {"start": req.get("start", ""), "end": req.get("end", "")},
        "verdict": run_data.get("verdict", ""),
        "failed_criteria": run_data.get("failed_criteria", []),
        "metrics": run_data.get("metrics", {}),
        "trade_stats": run_data.get("trade_stats", {}),
        "fold_sharpe_ratios": run_data.get("fold_sharpe_ratios", []),
        "failed_folds": run_data.get("failed_folds", []),
        "dsr": run_data.get("dsr"),
        "dsr_pass": run_data.get("dsr_pass", False),
        "mc_p_value": run_data.get("mc_p_value"),
        "acceptance_gate": run_data.get("acceptance_gate", {}),
        "bars_per_year": run_data.get("bars_per_year", 0),
        "warnings": run_data.get("warnings", []),
        "n_trades_in_dump": len(trades),
        "trades_summary": _summarize_trades(trades),
    }


def _aggregate_summary(experiments: list[dict[str, Any]]) -> dict[str, Any]:
    """Cross-experiment aggregate для quick trader scan."""
    if not experiments:
        return {"total": 0, "passed": 0, "failed": 0}
    passed = [e for e in experiments if e["verdict"] == "PASS"]
    failed = [e for e in experiments if e["verdict"] == "FAIL"]

    # Common failure modes
    failure_counts: dict[str, int] = {}
    for e in failed:
        for crit in e.get("failed_criteria", []):
            failure_counts[crit] = failure_counts.get(crit, 0) + 1

    # Best / worst by total_pnl
    pnls = [
        (e["experiment_id"], e["strategy_id"], e["symbol"], e["interval"],
         e["trade_stats"].get("total_pnl_quote", 0.0))
        for e in experiments if e["trade_stats"]
    ]
    pnls.sort(key=lambda x: x[4], reverse=True)

    # Best / worst by t1_sharpe
    sharpes = [
        (e["experiment_id"], e["strategy_id"], e["symbol"], e["interval"],
         e["metrics"].get("t1_sharpe_oos") or 0.0)
        for e in experiments if e["metrics"]
    ]
    sharpes.sort(key=lambda x: x[4], reverse=True)

    return {
        "total_experiments": len(experiments),
        "passed": len(passed),
        "failed": len(failed),
        "common_failures": dict(sorted(failure_counts.items(), key=lambda kv: kv[1], reverse=True)),
        "best_by_pnl_top5": [
            {"id": x[0], "strategy": x[1], "symbol": x[2], "interval": x[3], "pnl_quote": x[4]}
            for x in pnls[:5]
        ],
        "worst_by_pnl_bottom5": [
            {"id": x[0], "strategy": x[1], "symbol": x[2], "interval": x[3], "pnl_quote": x[4]}
            for x in pnls[-5:][::-1]
        ],
        "best_by_sharpe_top5": [
            {"id": x[0], "strategy": x[1], "symbol": x[2], "interval": x[3], "t1_sharpe": x[4]}
            for x in sharpes[:5]
        ],
        "worst_by_sharpe_bottom5": [
            {"id": x[0], "strategy": x[1], "symbol": x[2], "interval": x[3], "t1_sharpe": x[4]}
            for x in sharpes[-5:][::-1]
        ],
    }


def rebuild_audit(output_path: Path = _OUTPUT_PATH) -> dict[str, Any]:
    """Scan data/runs/*.json → emit aggregated audit doc.

    Idempotent. Called by dashboard hook after каждый backtest.

    Returns:
        Audit doc dict (also written к output_path).
    """
    experiments: list[dict[str, Any]] = []
    if _RUNS_DIR.exists():
        for run_path in sorted(_RUNS_DIR.glob("*.json")):
            try:
                run_data = json.loads(run_path.read_text())
                experiments.append(_experiment_from_run(run_data))
            except Exception:  # noqa: BLE001
                continue

    audit = {
        "meta": {
            "generated_at": datetime.now(UTC).isoformat(),
            **_git_meta(),
            "intent": (
                "Comprehensive trading formula/metric execution dump для trader-expert "
                "optimization. If pnL negative → pass file к trader → review formulas + "
                "calibration → propose sprint plan."
            ),
            "schema_version": "v1",
        },
        "formulas_inventory": FORMULAS_INVENTORY,
        "acceptance_criteria_thresholds": ACCEPTANCE_CRITERIA,
        "experiments": experiments,
        "summary": _aggregate_summary(experiments),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(audit, indent=2, default=str))
    return audit


def run_full_sweep() -> None:
    """Iterate every (strategy × symbol × interval) combination → run_backtest().

    Uses cache. Skips combinations missing data parquet.
    Calls rebuild_audit() at end.
    """
    from src.dashboard.backtest_runner import (
        BacktestRequest,
        STRATEGY_PRESETS,
        BARS_PER_YEAR,
        INTERVAL_FILE_LABEL,
        list_data_availability,
        run_backtest,
    )

    availability = list_data_availability()
    print(f"[sweep] data availability: {sorted(availability.keys())}")

    combos: list[tuple[str, str, str]] = []
    for strategy_id in sorted(STRATEGY_PRESETS.keys()):
        for symbol in sorted(availability.keys()):
            for interval in sorted(BARS_PER_YEAR.keys()):
                if interval not in availability[symbol]:
                    continue
                combos.append((strategy_id, symbol, interval))

    print(f"[sweep] {len(combos)} combinations к run")

    for i, (strategy_id, symbol, interval) in enumerate(combos, 1):
        avail = availability[symbol][interval]
        start = str(avail["start"])[:10]
        end = str(avail["end"])[:10]
        req = BacktestRequest(
            strategy_id=strategy_id, symbol=symbol, interval=interval,
            start=start, end=end,
        )
        print(f"[sweep {i:>2}/{len(combos)}] {strategy_id} {symbol} {interval} ({start}..{end})", flush=True)
        try:
            result = run_backtest(req, force=False)
            verdict = result.get("verdict", "?")
            n_trades = result.get("metrics", {}).get("t5_n_trades", 0)
            pnl = result.get("trade_stats", {}).get("total_pnl_quote", 0.0)
            cached = "(cached)" if result.get("cached") else "(fresh)"
            print(f"             → {verdict} n_trades={n_trades} pnl={pnl:.2f} {cached}", flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"             → ERROR: {type(e).__name__}: {e}", flush=True)

    audit = rebuild_audit()
    print(f"[sweep] complete. Wrote {_OUTPUT_PATH} ({len(audit['experiments'])} experiments)")


def main() -> int:
    parser = argparse.ArgumentParser(description="S27 formula audit")
    parser.add_argument(
        "--sweep", action="store_true",
        help="Run full sweep (3 strategies × all symbols × all intervals). Uses cache.",
    )
    parser.add_argument(
        "--output", type=Path, default=_OUTPUT_PATH,
        help=f"Output path (default {_OUTPUT_PATH})",
    )
    args = parser.parse_args()

    if args.sweep:
        run_full_sweep()
    else:
        audit = rebuild_audit(args.output)
        print(f"Wrote {args.output} ({len(audit['experiments'])} experiments)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
