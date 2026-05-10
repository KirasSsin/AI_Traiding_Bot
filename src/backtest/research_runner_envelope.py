"""S42 T1 — Dashboard contract envelope для research-mode runners.

Wraps minimal-output runners (atr_breakout, volume_breakout) к match dashboard
JS contract expected from replay_engine. Until S43 WFA retrofit, returns null
sentinels for acceptance_gate / DSR / MC, plus high-level warning that
acceptance discipline is skipped (RAW_FULL_PERIOD).

Sub-period robustness computed from equity_curve (5 chunks) is surfaced
as info/warn/high chip per N/5 positive periods.
"""

from __future__ import annotations

from typing import Any


def _subperiod_robustness_chunks(equity_curve: list[float], n_chunks: int = 5) -> list[float]:
    """Split equity_curve в n_chunks roughly equal chunks. Return per-chunk PnL delta.

    Replicates autoresearch subperiod_pnls computation.
    """
    if len(equity_curve) < n_chunks + 1:
        return [equity_curve[-1] - equity_curve[0]] if equity_curve else []
    n = len(equity_curve)
    step = n // n_chunks
    deltas: list[float] = []
    for i in range(n_chunks):
        start_idx = i * step
        end_idx = (i + 1) * step if i < n_chunks - 1 else n - 1
        deltas.append(equity_curve[end_idx] - equity_curve[start_idx])
    return deltas


def build_research_runner_envelope(
    *,
    runner_name: str,
    symbol: str,
    interval: str,
    n_trades: int,
    sharpe: float,
    win_rate: float,
    total_pnl_pct: float,
    bars_per_year: int,
    equity_curve: list[float],
    runner_label: str,
    start: str = "",
    end: str = "",
    extra_warnings: list[dict[str, str]] | None = None,
    equity_timestamps: list[int] | None = None,
    wfa_result: dict[str, Any] | None = None,
    trade_markers: dict[str, list[float | int]] | None = None,
) -> dict[str, Any]:
    """Build dashboard-contract envelope от research runner outputs.

    Dashboard JS expects keys from replay_engine: bars_per_year, warnings,
    failed_criteria, verdict, acceptance_gate, dsr, dsr_pass, mc_p_value,
    metrics, trade_stats, wfa_params, wfa_total_bars, fold_sharpe_ratios,
    failed_folds, trades_dump, request.

    Until S43 WFA retrofit:
      - acceptance_gate, dsr, mc_p_value → None (sentinels)
      - failed_criteria → [] (empty list, JS does .length)
      - verdict → "RAW" (not PASS/FAIL — discipline skipped)
      - warnings → high-level "raw_full_period" chip + sub-period robustness chip
    """
    warnings: list[dict[str, str]] = []

    warnings.append(
        {
            "level": "high",
            "code": "raw_full_period",
            "message": (
                "Acceptance gate skipped — WFA retrofit pending S43. "
                "Displayed PnL is full-period training number, NOT OOS-validated."
            ),
        }
    )

    deltas = _subperiod_robustness_chunks(equity_curve)
    n_pos = sum(1 for d in deltas if d > 0)
    n_total = len(deltas)
    if n_total > 0:
        if n_pos == n_total:
            level = "info"
        elif n_pos >= n_total * 0.6:
            level = "warn"
        else:
            level = "high"
        warnings.append(
            {
                "level": level,
                "code": "subperiod_robustness",
                "message": f"Robustness: {n_pos}/{n_total} sub-periods positive.",
            }
        )

    if extra_warnings:
        warnings.extend(extra_warnings)

    # S44 T4 — strip raw_full_period warning if WFA was actually run
    if wfa_result is not None:
        warnings = [w for w in warnings if w.get("code") != "raw_full_period"]

    # S44 T4 — populate from wfa_result when present, else null sentinels (S42 RAW behavior)
    if wfa_result is not None:
        verdict_val = wfa_result.get("verdict", "RAW")
        failed_criteria_val = wfa_result.get("failed_criteria", [])
        acceptance_gate_val = wfa_result.get("verdict")
        dsr_val = wfa_result.get("dsr")
        dsr_pass_val = wfa_result.get("dsr_pass")
        mc_p_val = wfa_result.get("mc_p_value")
        metrics_val = wfa_result.get("metrics", {})
        wfa_params_val = wfa_result.get("wfa_params")
        wfa_total_bars_val = (
            wfa_result.get("wfa_params", {}).get("actual", 0) if wfa_result.get("wfa_params") else 0
        )
        fold_sharpes_val = wfa_result.get("fold_sharpe_ratios", [])
        n_trades_val = wfa_result.get("n_trades_raw", n_trades)
    else:
        verdict_val = "RAW"
        failed_criteria_val = []
        acceptance_gate_val = None
        dsr_val = None
        dsr_pass_val = None
        mc_p_val = None
        metrics_val = {
            "sharpe": sharpe,
            "win_rate": win_rate,
            "total_pnl_pct": total_pnl_pct,
            "n_trades": n_trades,
        }
        wfa_params_val = None
        wfa_total_bars_val = 0
        fold_sharpes_val = []
        n_trades_val = n_trades

    return {
        # S43 T3 — equity_curve parallel arrays для uPlot native API
        # T11 — trade_markers nested under equity_curve (may be None)
        "equity_curve": {
            "timestamps": equity_timestamps if equity_timestamps else [],
            "equity_pct": list(equity_curve),
            "trade_markers": trade_markers,
        },
        "bars_per_year": bars_per_year,
        "warnings": warnings,
        "failed_criteria": failed_criteria_val,
        "verdict": verdict_val,
        "acceptance_gate": acceptance_gate_val,
        "dsr": dsr_val,
        "dsr_pass": dsr_pass_val,
        "mc_p_value": mc_p_val,
        "metrics": metrics_val,
        "trade_stats": {
            "n_trades": n_trades,
            "win_rate": win_rate,
        },
        "wfa_params": wfa_params_val,
        "wfa_total_bars": wfa_total_bars_val,
        "fold_sharpe_ratios": fold_sharpes_val,
        "failed_folds": [],
        "trades_dump": [],
        "request": {
            "strategy_id": runner_name,
            "strategy_label": runner_label,
            "symbol": symbol,
            "interval": interval,
            "interval_label": interval,
            "start": start,
            "end": end,
        },
        "n_trades": n_trades_val,
        "sharpe": sharpe,
        "win_rate": win_rate,
        "total_pnl_pct": total_pnl_pct,
        "runner": runner_name,
    }
