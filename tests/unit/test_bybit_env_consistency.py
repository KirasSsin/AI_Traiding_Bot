"""S55 B0 BLOCKER BYBIT-01 — REST + private-WS MUST resolve to the SAME Bybit env.

The defect (adversarially confirmed): _cmd_run built the private-WS endpoint string
as "demo.bybit.com" whenever settings.testnet=True, and ws_private resolved pybit
flags by substring (`"testnet" in endpoint` → False, `"demo" in endpoint` → True) →
WS connected to MAINNET-demo (stream-demo.bybit.com). MEANWHILE REST built
HTTP(testnet=settings.testnet) with NO demo flag → api-testnet.bybit.com (the
testnet exchange). testnet-exchange and mainnet-demo are SEPARATE account universes:
orders placed via REST on api-testnet NEVER echo back on stream-demo → the FSM never
sees ENTRY_FILLED/Filled events → OCO never arms via the live path.

These tests resolve the ACTUAL pybit host for both clients given Settings flags and
assert they land in the same universe for every supported Settings combination.

Canonical project env (chosen S55 — see commit message + SPRINT_STATE): testnet
exchange (testnet=True, demo=False) for both, honouring ADR 0053 LOCKED pre-commit #1
("δ is TESTNET ONLY. No MAINNET until 12-month evidence") + config.py s35 validator
which forces testnet=True. (ADR 0027 Q6 described Bybit demo-trading for the WS leg,
but that runs on MAINNET infra → conflicts with the later LOCKED #1; reconciled to
testnet-exchange to keep the whole pipeline on testnet infra.)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


def _settings(*, testnet: bool, demo: bool) -> MagicMock:
    s = MagicMock()
    s.bybit_api_key = "test_key_12345"
    s.bybit_api_secret = "test_secret_12345"
    s.testnet = testnet
    s.demo = demo
    return s


def _http_host(testnet: bool, demo: bool) -> str:
    """Resolve the real pybit HTTP endpoint host for the given flags."""
    from pybit.unified_trading import HTTP

    http = HTTP(testnet=testnet, demo=demo, api_key="x" * 8, api_secret="y" * 8)
    return str(http.endpoint)


def _ws_host(testnet: bool, demo: bool) -> str:
    """Resolve the pybit WebSocket endpoint host for the given flags.

    pybit's top-level `WebSocket` defers `endpoint` resolution to the inner
    `_WebSocketManager` built on first `_connect` (network). Rather than open a
    socket, we replicate pybit's documented subdomain branch using its own
    module constants — identical logic to `_WebSocketManager.__init__`.
    """
    from pybit import _websocket_stream as ws_mod

    subdomain = ws_mod.SUBDOMAIN_TESTNET if testnet else ws_mod.SUBDOMAIN_MAINNET
    if demo:
        subdomain = ws_mod.DEMO_SUBDOMAIN_TESTNET if testnet else ws_mod.DEMO_SUBDOMAIN_MAINNET
    return f"wss://{subdomain}.{ws_mod.DOMAIN_MAIN}.{ws_mod.TLD_MAIN}/v5/private"


def _env_universe(host: str) -> str:
    """Collapse a pybit host into its account universe label.

    api-testnet / stream-testnet           → "testnet"
    api-demo-testnet / stream-demo-testnet → "demo-testnet"
    api-demo / stream-demo                 → "mainnet-demo"
    api / stream                           → "mainnet"
    """
    h = host
    if "demo-testnet" in h:
        return "demo-testnet"
    if "demo" in h:
        return "mainnet-demo"
    if "testnet" in h:
        return "testnet"
    return "mainnet"


# Supported Settings combinations the bot may legitimately run with.
# (testnet, demo) — mainnet-live (False, False) excluded from S35 demo path but
# still must be self-consistent.
_COMBOS = [
    (True, False),  # testnet exchange (canonical S35 demo env)
    (False, True),  # Bybit demo-trading on mainnet infra
    (True, True),  # demo on testnet infra
    (False, False),  # mainnet live
]


@pytest.mark.parametrize(("testnet", "demo"), _COMBOS)
def test_rest_and_ws_resolve_same_universe(testnet: bool, demo: bool) -> None:
    """REST host universe == WS host universe for every Settings combo (no split)."""
    rest_universe = _env_universe(_http_host(testnet, demo))
    ws_universe = _env_universe(_ws_host(testnet, demo))
    assert rest_universe == ws_universe, (
        f"ENV SPLIT for testnet={testnet} demo={demo}: "
        f"REST={rest_universe} ({_http_host(testnet, demo)}) "
        f"!= WS={ws_universe} ({_ws_host(testnet, demo)})"
    )


def test_cmd_run_wires_rest_and_ws_to_same_universe() -> None:
    """End-to-end: _cmd_run with settings.testnet=True must NOT split REST(testnet)
    vs WS(mainnet-demo). Captures the flags passed to BOTH clients and asserts the
    resolved universes match.

    This is the regression guard for the original defect: WS endpoint was
    "demo.bybit.com" (→ mainnet-demo) while REST was testnet.
    """
    import argparse

    from src import __main__ as cli

    captured: dict[str, tuple[bool, bool]] = {}

    def _capture_rest(**kwargs: object) -> MagicMock:
        captured["rest"] = (bool(kwargs.get("testnet")), bool(kwargs.get("demo")))
        return MagicMock()

    def _capture_ws(**kwargs: object) -> MagicMock:
        captured["ws"] = (bool(kwargs.get("testnet")), bool(kwargs.get("demo")))
        return MagicMock()

    settings = _settings(testnet=True, demo=False)
    settings.runtime_kill_switch_path = "/tmp/.kill_switch"
    settings.db_path = "/tmp/test.db"
    settings.s35_demo_active = False

    args = argparse.Namespace(symbol="BTCUSDT", func=cli._cmd_run)

    with (
        patch("src.__main__.RuntimeManager") as mock_rm_class,
        patch("src.__main__.Settings", return_value=settings),
        patch("src.__main__.init_db"),
        patch("src.__main__.connect"),
        patch("src.__main__.BybitRESTClient", side_effect=_capture_rest),
        patch("src.__main__.BybitMarketAdapter"),
        patch("src.__main__.BybitFilters"),
        patch("src.__main__.Reconciler"),
        patch("src.__main__.Coordinator"),
        patch("src.__main__.ExecutionStateRepo"),
        patch("src.__main__.BarSource"),
        patch("src.__main__.MeanReversionRsiBBStrategy"),
        patch("src.__main__.RiskManager"),
        patch("src.__main__.FillHistoryRepository"),
        patch("src.__main__.TradeHistoryRepository"),
        patch("src.__main__.FillRecorderAdapter"),
        patch("src.__main__.BybitPrivateWSConsumer", side_effect=_capture_ws),
    ):
        mock_rm = MagicMock()
        mock_rm.run.return_value = None
        mock_rm_class.return_value = mock_rm
        cli._cmd_run(args)

    assert "rest" in captured, "BybitRESTClient not constructed"
    assert "ws" in captured, "BybitPrivateWSConsumer not constructed"
    rest_universe = _env_universe(_http_host(*captured["rest"]))
    ws_universe = _env_universe(_ws_host(*captured["ws"]))
    assert rest_universe == ws_universe, (
        f"_cmd_run ENV SPLIT: REST flags {captured['rest']} -> {rest_universe} "
        f"!= WS flags {captured['ws']} -> {ws_universe}"
    )
    # Canonical: testnet exchange (per ADR 0053 LOCKED).
    assert (
        rest_universe == "testnet"
    ), f"canonical S35 demo env must be testnet exchange, got {rest_universe}"


def test_ws_start_uses_explicit_flags_over_endpoint_substring() -> None:
    """S55 B0 BYBIT-01: when explicit (testnet, demo) are supplied, start() passes
    THOSE to pybit — NOT the substring heuristic on the endpoint string.

    Regression for the defect: endpoint="demo.bybit.com" used to force demo=True
    even when the caller intended the testnet exchange. Here endpoint deliberately
    says "demo" but explicit flags say testnet=True, demo=False → pybit must get
    testnet=True, demo=False.
    """
    from src.execution.bybit.ws_private import BybitPrivateWSConsumer

    consumer = BybitPrivateWSConsumer(
        api_key="k",
        api_secret="s",
        endpoint="wss://stream-demo.bybit.com/v5/private",  # says "demo"...
        coordinator=MagicMock(),
        reconciler=MagicMock(),
        fill_recorder=MagicMock(),
        testnet=True,  # ...but explicit flags win
        demo=False,
    )
    fake_ws_cls = MagicMock()
    fake_ws_cls.return_value = MagicMock()
    with patch("pybit.unified_trading.WebSocket", fake_ws_cls):
        consumer.start()
    _, kwargs = fake_ws_cls.call_args
    assert kwargs["testnet"] is True
    assert kwargs["demo"] is False


def test_all_restclient_sites_pass_demo_flag() -> None:
    """S55 PHASE6 SEC-BYBIT01-INCOMPLETE: EVERY BybitRESTClient(...) construction in
    src/ must pass an explicit ``demo=`` kwarg.

    The S55 B0 BYBIT-01 fix added demo=settings.demo only to _cmd_run; three other
    sites (_cmd backfill, _cmd_reconcile_only, account_service.get_account_balance)
    still omitted it → pybit defaulted demo=False → when settings.demo=True the REST
    client resolved a DIFFERENT account universe than the bot intended (reconcile read
    the wrong account; balance showed the wrong account). AST gate so a future site
    that forgets demo= fails CI regardless of runtime path.
    """
    import ast
    from pathlib import Path

    src_root = Path(__file__).resolve().parent.parent.parent / "src"
    offenders: list[str] = []
    for py in src_root.rglob("*.py"):
        tree = ast.parse(py.read_text(), filename=str(py))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "BybitRESTClient"
            ):
                kw = {k.arg for k in node.keywords}
                if "demo" not in kw:
                    offenders.append(f"{py.relative_to(src_root.parent)}:{node.lineno}")
    assert not offenders, f"BybitRESTClient(...) without demo= kwarg: {offenders}"


def test_ws_legacy_substring_fallback_preserved() -> None:
    """S55 B0 BYBIT-01: legacy callers (no explicit flags) keep substring behaviour.

    endpoint contains "demo" and not "testnet" → pybit demo=True, testnet=False.
    """
    from src.execution.bybit.ws_private import BybitPrivateWSConsumer

    consumer = BybitPrivateWSConsumer(
        api_key="k",
        api_secret="s",
        endpoint="wss://stream-demo.bybit.com/v5/private",
        coordinator=MagicMock(),
        reconciler=MagicMock(),
        fill_recorder=MagicMock(),
        # no testnet / demo supplied → fall back to substring
    )
    fake_ws_cls = MagicMock()
    fake_ws_cls.return_value = MagicMock()
    with patch("pybit.unified_trading.WebSocket", fake_ws_cls):
        consumer.start()
    _, kwargs = fake_ws_cls.call_args
    assert kwargs["testnet"] is False
    assert kwargs["demo"] is True
