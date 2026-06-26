"""S55 test-hygiene — cross-trial DSR pool must be env-redirectable.

Root cause: production writers (``_cmd_wfa``, ``research_wfa.run_research_wfa``)
defaulted the cross-trial pool to a cwd-relative ``Path("data/cross_trial_sharpes.json")``.
A test invoking a writer from the repo-root cwd without an isolated path mutated
the TRACKED ``data/cross_trial_sharpes.json`` fixture, leaving a dirty working tree.

Fix (DI via env): ``cross_trial_log.default_pool_path()`` resolves the pool path,
honouring ``CROSS_TRIAL_LOG_PATH``. Production default stays ``data/...``; the
autouse ``_isolate_cross_trial_pool`` fixture (tests/conftest.py) points the env at
a fresh tmp file so no test can ever touch the tracked fixture.
"""

from __future__ import annotations

from pathlib import Path


def test_default_pool_path_production_default(monkeypatch) -> None:
    """With no env override, the default stays the tracked repo path."""
    from src.analytics.cross_trial_log import default_pool_path

    monkeypatch.delenv("CROSS_TRIAL_LOG_PATH", raising=False)
    assert default_pool_path() == Path("data/cross_trial_sharpes.json")


def test_default_pool_path_honors_env_override(monkeypatch, tmp_path) -> None:
    """CROSS_TRIAL_LOG_PATH redirects the default pool — the isolation hook."""
    from src.analytics.cross_trial_log import default_pool_path

    custom = tmp_path / "iso" / "pool.json"
    monkeypatch.setenv("CROSS_TRIAL_LOG_PATH", str(custom))
    assert default_pool_path() == custom


def test_cmd_wfa_resolves_pool_via_default_pool_path() -> None:
    """_cmd_wfa must resolve its pool via default_pool_path (env-redirectable),
    NOT a hardcoded cwd-relative Path that dirties the tracked fixture."""
    import src.__main__ as cli

    src_text = Path(cli.__file__).read_text()
    assert "default_pool_path()" in src_text
    assert 'Path("data/cross_trial_sharpes.json")' not in src_text


def test_research_wfa_resolves_pool_via_default_pool_path() -> None:
    """run_research_wfa's None-default pool path must be env-redirectable."""
    from src.backtest import research_wfa

    src_text = Path(research_wfa.__file__).read_text()
    assert "default_pool_path()" in src_text
    assert 'Path("data/cross_trial_sharpes.json")' not in src_text


def test_autouse_fixture_redirects_env_off_repo_file() -> None:
    """The autouse isolation fixture points the pool env at a tmp file (not the
    tracked repo fixture) for every test."""
    import os

    pool = os.environ.get("CROSS_TRIAL_LOG_PATH")
    assert pool is not None, "autouse _isolate_cross_trial_pool must set the env"
    resolved = Path(pool).resolve()
    repo_file = (Path(__file__).parents[2] / "data" / "cross_trial_sharpes.json").resolve()
    assert resolved != repo_file, "pool env must not point at the tracked repo fixture"
