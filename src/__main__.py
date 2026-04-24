"""Entry-point: `python -m src <subcommand>` (ADR 0022 sub-decision 9).

Subcommands:
  run             — start RuntimeManager (blocking) — full wiring TODO (see T20 reference)
  backfill        — OHLCV backfill (delegated to existing scripts)
  reconcile-only  — bootstrap + reconcile, no trading loop — full wiring TODO (see T20 reference)
  kill            — write .kill_switch sentinel and exit (body in Task 19)

Note: `_cmd_run` and `_cmd_reconcile_only` bodies are placeholders — full dependency
wiring deferred to T20 integration test (which constructs RuntimeManager directly,
bypassing this CLI). Update these bodies once the T20 wiring pattern is validated.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _cmd_run(args: argparse.Namespace) -> int:
    """Wire all dependencies and start RuntimeManager.

    TODO (T20 follow-up): full DI wiring. Current Coordinator/RuntimeManager
    ctor signatures differ from plan-author assumptions (see plan lines 2166-2215).
    Reference wiring: see tests/integration/test_runtime_smoke.py once T20 lands.
    """
    print(
        "ERROR: `python -m src run` is not yet wired. "
        "Full RuntimeManager DI deferred to T20 integration test reference. "
        f"args={vars(args)}",
        file=sys.stderr,
    )
    return 1


def _cmd_backfill(args: argparse.Namespace) -> int:
    """Delegate to existing backfill script."""
    print(f"backfill --from {args.from_date} --to {args.to_date} (delegate to scripts/backfill.py)")
    return 0


def _cmd_reconcile_only(args: argparse.Namespace) -> int:
    """Run bootstrap + reconcile, no trading loop.

    TODO (T20 follow-up): full DI wiring (same blocker as `_cmd_run`).
    """
    print(
        "ERROR: `python -m src reconcile-only` is not yet wired. "
        "Full bootstrap DI deferred to T20 integration test reference. "
        f"args={vars(args)}",
        file=sys.stderr,
    )
    return 1


def _cmd_kill(args: argparse.Namespace) -> int:
    """Write sentinel-file at configured path. ADR 0022 sub-decision 5."""
    from src.platform.config import Settings

    settings = Settings()
    sentinel = Path(settings.runtime_kill_switch_path)
    sentinel.parent.mkdir(parents=True, exist_ok=True)
    sentinel.write_text("")
    print(f"kill switch written: {sentinel}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m src", description="AI Trading Bot v0.1 — live runtime CLI (ADR 0022).")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="Start RuntimeManager (blocking).")
    p_run.add_argument("--symbol", default="BTCUSDT")
    p_run.set_defaults(func=_cmd_run)

    p_bf = sub.add_parser("backfill", help="OHLCV backfill.")
    p_bf.add_argument("--from", dest="from_date", required=True)
    p_bf.add_argument("--to", dest="to_date", required=True)
    p_bf.set_defaults(func=_cmd_backfill)

    p_rec = sub.add_parser("reconcile-only", help="Bootstrap + reconcile, no trading loop.")
    p_rec.add_argument("--symbol", default="BTCUSDT")
    p_rec.set_defaults(func=_cmd_reconcile_only)

    p_kill = sub.add_parser("kill", help="Write .kill_switch sentinel and exit.")
    p_kill.set_defaults(func=_cmd_kill)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
