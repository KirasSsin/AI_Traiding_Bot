"""RuntimeManager — process lifecycle owner.

ADR 0022 sub-decisions 7, 13, 14, 15, 17.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest


def _settings(tmp_path: Path):
    s = MagicMock()
    s.runtime_kill_switch_path = str(tmp_path / ".kill_switch")
    s.runtime_bar_poll_cadence_seconds = 5.0
    s.runtime_bar_poll_stall_threshold = 24
    s.runtime_ws_check_alive_max_silence = 30.0
    s.runtime_warmup_bars = 50
    return s


def test_runtime_manager_ctor_stores_deps(tmp_path):
    from src.runtime.manager import RuntimeManager

    coord = MagicMock()
    rec = MagicMock()
    ws = MagicMock()
    bs = MagicMock()
    strat = MagicMock()
    s = _settings(tmp_path)

    rm = RuntimeManager(
        coordinator=coord,
        reconciler=rec,
        ws_consumer=ws,
        bar_source=bs,
        strategy=strat,
        settings=s,
    )

    assert rm._coordinator is coord
    assert rm._reconciler is rec
    assert rm._ws_consumer is ws
    assert rm._bar_source is bs
    assert rm._strategy is strat
    assert rm._settings is s
    assert rm._stopping is False
    assert rm._kill_switch_path == Path(s.runtime_kill_switch_path)
