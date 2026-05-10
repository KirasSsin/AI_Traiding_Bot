"""S44 T3 — volume_breakout WFA integration."""

from __future__ import annotations

from datetime import date

import pytest


@pytest.mark.integration
def test_volume_breakout_wfa_btc_4h_returns_verdict() -> None:
    """volume_breakout BTC 4H = 7273 bars > 4520 default min."""
    from src.backtest.volume_breakout_runner import _run_volume_breakout_wfa

    r = _run_volume_breakout_wfa(
        symbol="BTCUSDT",
        interval="240",
        start_date=date(2023, 1, 1),
        end_date=date(2026, 4, 26),
    )
    assert r["verdict"] in ("WFA_PASS", "WFA_FAIL"), f"Got {r['verdict']}"
    assert "data_volume" not in r["failed_criteria"]
    assert len(r["fold_sharpe_ratios"]) == 5  # default k=5
    assert r["n_trades_raw"] >= 0  # may be small for slow strategy


@pytest.mark.integration
def test_volume_breakout_wfa_envelope_keys_present() -> None:
    from src.backtest.volume_breakout_runner import _run_volume_breakout_wfa

    r = _run_volume_breakout_wfa(
        symbol="BTCUSDT",
        interval="240",
        start_date=date(2023, 1, 1),
        end_date=date(2026, 4, 26),
    )
    for key in (
        "verdict",
        "fold_sharpe_ratios",
        "trial_mean_fold_oos_sharpe",
        "mc_p_value",
        "dsr",
        "dsr_pass",
        "n_trades_raw",
        "failed_criteria",
        "wfa_params",
        "metrics",
    ):
        assert key in r, f"Missing: {key}"


@pytest.mark.integration
def test_volume_breakout_wfa_uses_n_trials_1() -> None:
    """S45 C1 — volume_breakout = single hypothesis, n_trials=1 explicit."""
    from datetime import date

    import src.backtest.research_wfa as wfa_module

    captured = {}
    orig = wfa_module.run_research_wfa

    def spy(*args, **kwargs):
        captured["n_trials"] = kwargs.get("n_trials")
        return orig(*args, **kwargs)

    wfa_module.run_research_wfa = spy
    try:
        from src.backtest.volume_breakout_runner import _run_volume_breakout_wfa

        _run_volume_breakout_wfa(
            symbol="BTCUSDT",
            interval="240",
            start_date=date(2023, 1, 1),
            end_date=date(2026, 4, 26),
        )
    finally:
        wfa_module.run_research_wfa = orig
    assert captured["n_trials"] == 1, f"Expected n_trials=1, got {captured['n_trials']}"
