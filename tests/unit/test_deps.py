"""Sanity check: deps align with ADR 0016."""

import importlib


def test_pybit_importable() -> None:
    mod = importlib.import_module("pybit.unified_trading")
    assert hasattr(mod, "HTTP")
    assert hasattr(mod, "WebSocket")


def test_python_binance_not_installed() -> None:
    import importlib.util

    assert importlib.util.find_spec("binance") is None
