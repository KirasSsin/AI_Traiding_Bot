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


@pytest.mark.integration
def test_atr_breakout_wfa_uses_n_trials_10() -> None:
    """S45 C1 — atr_breakout family = 10 hypotheses, n_trials=10 explicit."""
    from datetime import date

    import src.backtest.research_wfa as wfa_module

    captured = {}
    orig = wfa_module.run_research_wfa

    def spy(*args, **kwargs):
        captured["n_trials"] = kwargs.get("n_trials")
        return orig(*args, **kwargs)

    wfa_module.run_research_wfa = spy
    try:
        from src.backtest.atr_breakout_runner import _run_atr_breakout_wfa

        _run_atr_breakout_wfa(
            symbol="BTCUSDT",
            interval="240",
            start_date=date(2023, 1, 1),
            end_date=date(2026, 4, 26),
        )
    finally:
        wfa_module.run_research_wfa = orig
    assert captured["n_trials"] == 10, f"Expected n_trials=10, got {captured['n_trials']}"


@pytest.mark.integration
def test_atr_breakout_wfa_4h_uses_low_freq_tier() -> None:
    """S45 — BTC 4H WFA uses low-freq tier params (test_bars=250, train_bars=1500)."""
    import src.backtest.research_wfa as wfa_module

    captured: dict = {}
    orig = wfa_module.run_research_wfa

    def spy(*args, **kwargs):
        captured.update({k: kwargs.get(k) for k in ("train_bars", "test_bars", "k_folds")})
        return orig(*args, **kwargs)

    wfa_module.run_research_wfa = spy
    try:
        from src.backtest.atr_breakout_runner import _run_atr_breakout_wfa

        _run_atr_breakout_wfa(
            symbol="BTCUSDT",
            interval="240",
            start_date=date(2023, 1, 1),
            end_date=date(2026, 4, 26),
        )
    finally:
        wfa_module.run_research_wfa = orig
    assert (
        captured["train_bars"] == 1500
    ), f"4H expected train_bars=1500, got {captured['train_bars']}"
    assert captured["test_bars"] == 250, f"4H expected test_bars=250, got {captured['test_bars']}"


@pytest.mark.integration
def test_atr_breakout_wfa_15m_uses_high_freq_tier() -> None:
    """S45 — BTC 15M WFA uses high-freq default tier (test_bars=500, train_bars=2000)."""
    import src.backtest.research_wfa as wfa_module

    captured: dict = {}
    orig = wfa_module.run_research_wfa

    def spy(*args, **kwargs):
        captured.update({k: kwargs.get(k) for k in ("train_bars", "test_bars")})
        return orig(*args, **kwargs)

    wfa_module.run_research_wfa = spy
    try:
        from src.backtest.atr_breakout_runner import _run_atr_breakout_wfa

        _run_atr_breakout_wfa(
            symbol="BTCUSDT",
            interval="15",
            start_date=date(2023, 1, 1),
            end_date=date(2026, 4, 26),
        )
    finally:
        wfa_module.run_research_wfa = orig
    assert captured["train_bars"] == 2000
    assert captured["test_bars"] == 500
