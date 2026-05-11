"""S47 T13 — research path envelope derives n_winners/n_losers from trades_list."""

from __future__ import annotations

from dataclasses import dataclass

from src.backtest.research_runner_envelope import build_research_runner_envelope


@dataclass
class _TradeStub:
    pnl_pct: float


def test_trade_stats_derived_when_trades_list_passed() -> None:
    trades = [
        _TradeStub(pnl_pct=0.05),  # win
        _TradeStub(pnl_pct=-0.02),  # loss
        _TradeStub(pnl_pct=0.03),  # win
        _TradeStub(pnl_pct=0.0),  # loss (>0 → win, ≤0 → loss; here ≤0 → loss)
    ]
    payload = build_research_runner_envelope(
        runner_name="test",
        symbol="BTCUSDT",
        interval="240",
        n_trades=4,
        sharpe=1.0,
        win_rate=0.5,
        total_pnl_pct=8.0,
        bars_per_year=2191,
        equity_curve=[0.0, 5.0, 3.0, 6.0, 8.0],
        runner_label="x",
        trades_list=trades,
    )
    ts = payload["trade_stats"]
    assert ts["n_winners"] == 2
    assert ts["n_losers"] == 2
    assert ts["total_pnl_pct"] == 8.0
    # Quote fields = None for research path
    assert ts["total_pnl_quote"] is None
    assert ts["avg_win_quote"] is None
    assert ts["profit_factor"] is None


def test_trade_stats_no_trades_list_keeps_n_winners_none() -> None:
    payload = build_research_runner_envelope(
        runner_name="test",
        symbol="BTCUSDT",
        interval="240",
        n_trades=0,
        sharpe=0.0,
        win_rate=0.0,
        total_pnl_pct=0.0,
        bars_per_year=2191,
        equity_curve=[0.0],
        runner_label="x",
    )
    ts = payload["trade_stats"]
    assert ts["n_winners"] is None
    assert ts["n_losers"] is None
