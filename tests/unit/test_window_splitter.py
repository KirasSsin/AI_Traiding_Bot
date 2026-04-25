"""Tests for WindowSplitter — rolling K-fold WFA window generator.

Sprint 10 Q1 (per pre-s10-backlog.md verdict — bars unit, ADR 0014 explicit).
"""
from __future__ import annotations

import pytest
from src.backtest.walk_forward import WindowSplitter


def test_rolling_windows_no_overlap_per_fold() -> None:
    """Per ADR 0014: train + embargo + test, rolling. Verify no overlap."""
    splitter = WindowSplitter(
        train_bars=2000, test_bars=500, embargo_bars=20, k_folds=5
    )
    folds = list(splitter.split(total_bars=15000))
    assert len(folds) == 5
    for tr_start, tr_end, te_start, te_end in folds:
        assert te_start == tr_end + 20
        assert tr_end - tr_start == 2000
        assert te_end - te_start == 500


def test_K_folds_advance_by_test_window() -> None:  # noqa: N802
    """Each fold advances by test_bars (rolling)."""
    splitter = WindowSplitter(
        train_bars=2000, test_bars=500, embargo_bars=20, k_folds=5
    )
    folds = list(splitter.split(total_bars=15000))
    advances = [folds[i + 1][0] - folds[i][0] for i in range(len(folds) - 1)]
    assert all(adv == 500 for adv in advances)


def test_insufficient_data_raises() -> None:
    """If total_bars < min required, raise."""
    splitter = WindowSplitter(
        train_bars=2000, test_bars=500, embargo_bars=20, k_folds=5
    )
    with pytest.raises(ValueError, match="insufficient data"):
        list(splitter.split(total_bars=4000))


def test_embargo_zero_allowed() -> None:
    """embargo_bars=0 valid (default 20 но allows override)."""
    splitter = WindowSplitter(
        train_bars=100, test_bars=50, embargo_bars=0, k_folds=2
    )
    folds = list(splitter.split(total_bars=300))
    assert folds[0] == (0, 100, 100, 150)
    assert folds[1] == (50, 150, 150, 200)


def test_negative_params_rejected() -> None:
    """Negative train/test/embargo/k rejected at construction."""
    with pytest.raises(ValueError, match="must be positive"):
        WindowSplitter(train_bars=-1, test_bars=500, embargo_bars=20, k_folds=5)
    with pytest.raises(ValueError, match="must be positive"):
        WindowSplitter(train_bars=2000, test_bars=0, embargo_bars=20, k_folds=5)
    with pytest.raises(ValueError, match="must be positive"):
        WindowSplitter(train_bars=2000, test_bars=500, embargo_bars=20, k_folds=0)


def test_default_params_match_adr_0014() -> None:
    """Default params per ADR 0014: train=2000, test=500, embargo=20, K=5."""
    splitter = WindowSplitter()
    assert splitter.train_bars == 2000
    assert splitter.test_bars == 500
    assert splitter.embargo_bars == 20
    assert splitter.k_folds == 5
