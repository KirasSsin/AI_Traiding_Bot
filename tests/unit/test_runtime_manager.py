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


def test_run_bootstraps_then_starts_ws_then_loops(tmp_path, monkeypatch):
    from src.runtime.manager import RuntimeManager

    calls: list[str] = []
    coord = MagicMock()
    coord.bootstrap.side_effect = lambda: calls.append("bootstrap")
    ws = MagicMock()
    ws.start.side_effect = lambda: calls.append("ws.start")

    rm = RuntimeManager(
        coordinator=coord,
        reconciler=MagicMock(),
        ws_consumer=ws,
        bar_source=MagicMock(),
        strategy=MagicMock(),
        settings=_settings(tmp_path),
    )

    # Patch _main_loop so run() exits immediately after bootstrap+ws.start
    monkeypatch.setattr(rm, "_main_loop", lambda: calls.append("main_loop"))
    monkeypatch.setattr(rm, "_shutdown", lambda *, reason: calls.append(f"shutdown:{reason}"))

    rm.run()

    assert calls.index("bootstrap") < calls.index("ws.start")
    assert calls.index("ws.start") < calls.index("main_loop")


def test_run_cleans_stale_kill_switch_before_bootstrap(tmp_path):
    from src.runtime.manager import RuntimeManager

    sentinel = tmp_path / ".kill_switch"
    sentinel.write_text("")
    assert sentinel.exists()

    coord = MagicMock()
    rm = RuntimeManager(
        coordinator=coord,
        reconciler=MagicMock(),
        ws_consumer=MagicMock(),
        bar_source=MagicMock(),
        strategy=MagicMock(),
        settings=_settings(tmp_path),
    )
    rm._main_loop = lambda: None
    rm._shutdown = lambda *, reason: None

    rm.run()
    assert not sentinel.exists(), "stale .kill_switch must be removed before bootstrap"


def test_bootstrap_failure_blocks_ws_start(tmp_path):
    from src.runtime.manager import RuntimeManager

    coord = MagicMock()
    coord.bootstrap.side_effect = RuntimeError("boot failed")
    ws = MagicMock()

    rm = RuntimeManager(
        coordinator=coord,
        reconciler=MagicMock(),
        ws_consumer=ws,
        bar_source=MagicMock(),
        strategy=MagicMock(),
        settings=_settings(tmp_path),
    )
    rm._main_loop = lambda: None
    rm._shutdown = lambda *, reason: None

    with pytest.raises(RuntimeError, match="boot failed"):
        rm.run()
    ws.start.assert_not_called()
