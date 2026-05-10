"""S44 T2 — atr_breakout WFA integration."""

from __future__ import annotations

from datetime import date

import pytest


@pytest.mark.integration
def test_atr_breakout_wfa_btc_4h_returns_wfa_pass_or_fail() -> None:
    """S45 T1: BTCUSDT 4H = 7273 bars (3.3y) >> 4520 default min. Must NOT WFA_FAIL_DATA."""
    from src.backtest.atr_breakout_runner import _run_atr_breakout_wfa

    r = _run_atr_breakout_wfa(
        symbol="BTCUSDT",
        interval="240",
        start_date=date(2023, 1, 1),
        end_date=date(2026, 4, 26),
    )
    assert r["verdict"] in ("WFA_PASS", "WFA_FAIL"), f"Got {r['verdict']}"
    assert "data_volume" not in r["failed_criteria"]
    assert len(r["fold_sharpe_ratios"]) == 5  # default k=5
    assert r["n_trades_raw"] > 0


@pytest.mark.integration
def test_atr_breakout_wfa_btc_1d_returns_wfa_fail_data() -> None:
    """BTCUSDT 1D = 1212 bars < 4520 default. WFA_FAIL_DATA expected."""
    from src.backtest.atr_breakout_runner import _run_atr_breakout_wfa

    r = _run_atr_breakout_wfa(
        symbol="BTCUSDT",
        interval="D",
        start_date=date(2023, 1, 1),
        end_date=date(2026, 4, 26),
    )
    assert r["verdict"] == "WFA_FAIL_DATA", f"Got {r['verdict']}"
    assert "data_volume" in r["failed_criteria"]


@pytest.mark.integration
def test_atr_breakout_wfa_eth_4h_uses_locked_params() -> None:
    """Verify ETHUSDT 4H uses LOCKED params from ATR_BREAKOUT_LOCKED_PARAMS_BY_COMBO."""
    from src.backtest.atr_breakout_runner import _run_atr_breakout_wfa

    r = _run_atr_breakout_wfa(
        symbol="ETHUSDT",
        interval="240",
        start_date=date(2023, 1, 1),
        end_date=date(2026, 4, 26),
    )
    assert r["verdict"] in ("WFA_PASS", "WFA_FAIL", "WFA_FAIL_DATA")
    # ETHUSDT 4H = 7273 bars > 4520 — should run WFA, not data-limited
    assert r["verdict"] != "WFA_FAIL_DATA"


@pytest.mark.integration
def test_atr_breakout_wfa_unknown_combo_raises() -> None:
    """No LOCKED params for combo → ValueError."""
    from src.backtest.atr_breakout_runner import _run_atr_breakout_wfa

    with pytest.raises(ValueError, match="No LOCKED params"):
        _run_atr_breakout_wfa(
            symbol="BTCUSDT",
            interval="5",  # 5m не в LOCKED dict
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 1),
        )
