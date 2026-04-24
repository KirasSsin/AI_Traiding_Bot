"""src.__main__ — argparse subcommand routing.

ADR 0022 sub-decision 9. Subcommands: run / backfill / reconcile-only / kill.
"""
from __future__ import annotations

import subprocess
import sys


def _run_main(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "src", *args],
        capture_output=True,
        text=True,
    )


def test_main_help_shows_subcommands():
    r = _run_main("--help")
    assert r.returncode == 0
    out = r.stdout + r.stderr
    for sub in ("run", "backfill", "reconcile-only", "kill"):
        assert sub in out, f"subcommand {sub!r} missing from --help"


def test_main_unknown_subcommand_exits_2():
    r = _run_main("nonsense-cmd")
    assert r.returncode == 2  # argparse standard error code


def test_main_no_subcommand_exits_nonzero():
    r = _run_main()
    assert r.returncode != 0  # argparse error: subcommand required
