"""S47 T12 — sprint identifier type consistency (S45 quant follow-up).

Ensures sprint number stored consistently as int (NOT str) in metadata blocks
across research_runner_envelope outputs. Guards against future regression where
sprint is accidentally stored as a string key or JSON-decoded as str.
"""

from __future__ import annotations

from src.backtest.research_runner_envelope import build_research_runner_envelope


def test_envelope_sprint_field_is_int_or_absent() -> None:
    """If envelope includes 'sprint' field anywhere — must be int, not str."""
    payload = build_research_runner_envelope(
        runner_name="test_runner",
        symbol="BTCUSDT",
        interval="240",
        n_trades=10,
        sharpe=1.0,
        win_rate=0.5,
        total_pnl_pct=10.0,
        bars_per_year=2191,
        equity_curve=[0.0, 10.0],
        runner_label="x",
    )
    # Top-level 'sprint' field — must be int if present
    if "sprint" in payload:
        assert isinstance(
            payload["sprint"], int
        ), f"envelope['sprint'] type={type(payload['sprint']).__name__}, expected int"
    # Nested metrics 'sprint' field — must be int if present
    if "sprint" in payload.get("metrics", {}):
        assert isinstance(
            payload["metrics"]["sprint"], int
        ), f"envelope['metrics']['sprint'] type={type(payload['metrics']['sprint']).__name__}, expected int"
    # Vacuous pass (no 'sprint' field present) is correct — guards future regressions
