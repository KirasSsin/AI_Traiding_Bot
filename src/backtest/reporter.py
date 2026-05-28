import json
import os
from typing import Any, Dict

import pandas as pd


def write_artifacts(
    config: Dict[str, Any],
    equity_df: pd.DataFrame,
    trades_df: pd.DataFrame,
    metrics: Dict[str, Any],
) -> Dict[str, str]:
    output_cfg = config.get("output", {})
    output_dir = str(output_cfg.get("directory", "output"))
    os.makedirs(output_dir, exist_ok=True)

    paths: Dict[str, str] = {}
    generate_csv = bool(output_cfg.get("generate_csv", True))
    generate_json = bool(output_cfg.get("generate_json", True))
    generate_html = bool(output_cfg.get("generate_html", True))

    if generate_csv:
        trade_path = os.path.join(output_dir, "trade_log.csv")
        equity_path = os.path.join(output_dir, "equity_curve.csv")
        trades_df.to_csv(trade_path, index=False)
        equity_df.to_csv(equity_path, index=False)
        paths["trade_log.csv"] = os.path.abspath(trade_path)
        paths["equity_curve.csv"] = os.path.abspath(equity_path)

    if generate_json:
        metrics_path = os.path.join(output_dir, "metrics_summary.json")
        with open(metrics_path, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)
        paths["metrics_summary.json"] = os.path.abspath(metrics_path)

    if generate_html:
        report_path = os.path.join(output_dir, "report.html")
        _write_html_report(report_path, equity_df, trades_df, metrics)
        paths["report.html"] = os.path.abspath(report_path)

    return paths


def _write_html_report(
    report_path: str,
    equity_df: pd.DataFrame,
    trades_df: pd.DataFrame,
    metrics: Dict[str, Any],
) -> None:
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots

        fig = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=False,
            subplot_titles=("Equity Curve", "Trade PnL"),
            vertical_spacing=0.12,
        )

        if not equity_df.empty:
            fig.add_trace(
                go.Scatter(
                    x=equity_df["timestamp"],
                    y=equity_df["balance"],
                    mode="lines",
                    name="Balance",
                ),
                row=1,
                col=1,
            )

        if not trades_df.empty:
            fig.add_trace(
                go.Bar(
                    x=trades_df["timestamp_close"],
                    y=trades_df["net_pnl"],
                    name="Net PnL",
                ),
                row=2,
                col=1,
            )

        fig.update_layout(height=900, title_text="AI Trading Bot Backtest Report")
        fig.write_html(report_path, include_plotlyjs="cdn")
    except Exception:  # noqa: BLE001 — plotly optional/unstable; fall back to minimal static HTML
        # Fallback minimal HTML if plotly is missing or chart generation fails
        metrics_rows = "\n".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in metrics.items())
        html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Backtest Report</title></head>
<body>
  <h1>Backtest Report</h1>
  <h2>Metrics</h2>
  <table border="1" cellpadding="6" cellspacing="0">
    <tr><th>Metric</th><th>Value</th></tr>
    {metrics_rows}
  </table>
</body>
</html>
"""
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(html)
