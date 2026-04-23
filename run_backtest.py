import argparse
import json
import os
import sys
from typing import Any, Dict

from src.backtest.data_collector import load_market_data
from src.backtest.replay_engine import run_replay
from src.backtest.reporter import write_artifacts
from src.config_loader import load_config


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI Trading Bot backtest runner")
    parser.add_argument("--config", default="config.yaml", help="Path to YAML config")
    return parser.parse_args()


def _print_metrics(metrics: Dict[str, Any]) -> None:
    print("\n=== Metrics Summary ===")
    for key, val in metrics.items():
        if isinstance(val, float):
            print(f"{key}: {val:.6f}")
        else:
            print(f"{key}: {val}")


def main() -> int:
    args = _parse_args()
    cfg = load_config(args.config)

    df = load_market_data(cfg)
    if df.empty:
        print("Нет данных. Проверьте настройки data.source/csv_path/parquet_path в config.yaml.")
        return 1

    replay = run_replay(df, cfg)
    equity_df = replay["equity_df"]
    trades_df = replay["trades_df"]
    metrics = replay["metrics"]

    artifacts = write_artifacts(cfg, equity_df, trades_df, metrics)

    _print_metrics(metrics)
    print("\n=== Artifacts ===")
    print(json.dumps(artifacts, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
