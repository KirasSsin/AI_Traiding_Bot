"""Pre-mainnet acceptance gate: re-run Spot OCO probes on api-testnet.bybit.com.

ADR 0020 Stage F. Before tagging v0.1.0-alpha.6, re-run:
  - B2   (spot_oco_probe.py)     — tpslMode rejection (expect retCode=170130)
  - v3-D (spot_oco_probe_v3.py)  — Stop TIF GTC->IOC silent override
  - v2-S2(spot_oco_probe_v2.py)  — marketUnit=quoteCoin accumulation drift

Expected outcomes per probe:
  B2   : place_order with tpslMode=Full on Spot must return retCode=170130.
         Any other code (including 0) means testnet diverges from Demo — BLOCK.
  v3-D : Stop order submitted with timeInForce=GTC; after fill the execution
         echo must show IOC (silent override). If it stays GTC — BLOCK.
  v2-S2: marketUnit=quoteCoin entry over multiple buys accumulates a BTC
         delta > 8 decimal places (dust). If drift is absent — BLOCK.

Any divergence from Demo findings blocks mainnet release; escalate to ADR 0020
review before tagging v0.1.0-alpha.6.

Usage:
    export BYBIT_TESTNET_API_KEY=...
    export BYBIT_TESTNET_API_SECRET=...
    python scripts/spot_oco_probe_testnet.py --probe B2
    python scripts/spot_oco_probe_testnet.py --probe v3-D
    python scripts/spot_oco_probe_testnet.py --probe v2-S2

Record results in:
    llm-wiki/wiki/project/sprints/sprint-06-spot-oco-emulation.md (Stage F table).

WARNING: Do NOT use mainnet or Demo API keys here. Testnet has a separate
credential pair (api-testnet.bybit.com). Using wrong keys will fail with
retCode=10003 (invalid API key) — that is expected if keys are wrong, not
a probe finding.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

TESTNET_URL = "https://api-testnet.bybit.com"

PROBES = {
    "B2": "spot_oco_probe",
    "v3-D": "spot_oco_probe_v3",
    "v2-S2": "spot_oco_probe_v2",
}


def _patch_http_for_testnet() -> None:
    """Monkeypatch pybit HTTP so hard-coded testnet=False/demo=True probes hit testnet."""
    import pybit.unified_trading as _pybit

    _OrigHTTP = _pybit.HTTP

    class _TestnetHTTP(_OrigHTTP):
        def __init__(self, *args, **kwargs):  # type: ignore[override]
            kwargs["testnet"] = True
            kwargs["demo"] = False
            super().__init__(*args, **kwargs)

    _pybit.HTTP = _TestnetHTTP  # type: ignore[assignment]


def _patch_ws_for_testnet() -> None:
    """Monkeypatch pybit WebSocket so hard-coded testnet=False/demo=True probes hit testnet."""
    import pybit.unified_trading as _pybit

    _OrigWS = _pybit.WebSocket

    class _TestnetWS(_OrigWS):
        def __init__(self, *args, **kwargs):  # type: ignore[override]
            kwargs["testnet"] = True
            kwargs["demo"] = False
            super().__init__(*args, **kwargs)

    _pybit.WebSocket = _TestnetWS  # type: ignore[assignment]


def _run_b2() -> int:
    """Run B2 probe (spot_oco_probe) against testnet."""
    _patch_http_for_testnet()
    _patch_ws_for_testnet()
    import importlib

    mod = importlib.import_module("scripts.spot_oco_probe")
    if not hasattr(mod, "main"):
        print("ERROR: spot_oco_probe has no main() entry point.", file=sys.stderr)
        return 3
    mod.main()
    return 0


def _run_v3d() -> int:
    """Run v3-D probe (spot_oco_probe_v3) against testnet."""
    _patch_http_for_testnet()
    _patch_ws_for_testnet()
    import importlib

    mod = importlib.import_module("scripts.spot_oco_probe_v3")
    if not hasattr(mod, "main"):
        print("ERROR: spot_oco_probe_v3 has no main() entry point.", file=sys.stderr)
        return 3
    mod.main()
    return 0


def _run_v2s2() -> int:
    """Run v2-S2 scenario (spot_oco_probe_v2.run_testnet) against testnet.

    spot_oco_probe_v2 already has run_testnet(s) which uses HTTP(testnet=True, demo=False).
    We call it directly rather than running the full main() which also runs the demo path.
    """
    import importlib

    mod = importlib.import_module("scripts.spot_oco_probe_v2")
    if not hasattr(mod, "run_testnet"):
        print("ERROR: spot_oco_probe_v2 has no run_testnet() entry point.", file=sys.stderr)
        return 3

    from src.platform.config import Settings

    s = Settings()
    print(f"[probe_testnet] Calling spot_oco_probe_v2.run_testnet() ...")
    result = mod.run_testnet(s)
    import json

    print(json.dumps(result, indent=2, default=str))
    return 0


_PROBE_RUNNERS = {
    "B2": _run_b2,
    "v3-D": _run_v3d,
    "v2-S2": _run_v2s2,
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--probe",
        required=True,
        choices=sorted(PROBES.keys()),
        help="Which probe to re-run on testnet: B2, v2-S2, or v3-D",
    )
    args = parser.parse_args()

    api_key = os.environ.get("BYBIT_TESTNET_API_KEY")
    api_secret = os.environ.get("BYBIT_TESTNET_API_SECRET")
    if not api_key or not api_secret:
        print(
            "ERROR: set BYBIT_TESTNET_API_KEY and BYBIT_TESTNET_API_SECRET before running.",
            file=sys.stderr,
        )
        print("Do NOT use mainnet keys — testnet has separate credentials.", file=sys.stderr)
        return 2

    # Inject testnet credentials into env so pydantic Settings() picks them up
    # as BYBIT_API_KEY / BYBIT_API_SECRET (field names, case_sensitive=False).
    os.environ["BYBIT_API_KEY"] = api_key
    os.environ["BYBIT_API_SECRET"] = api_secret

    module_name = PROBES[args.probe]
    print(f"[probe_testnet] Probe    : {args.probe}")
    print(f"[probe_testnet] Module   : {module_name}")
    print(f"[probe_testnet] Target   : {TESTNET_URL}")
    print(f"[probe_testnet] Key hint : {api_key[:4]}...{api_key[-4:]}")
    print()

    runner = _PROBE_RUNNERS[args.probe]
    return runner()


if __name__ == "__main__":
    sys.exit(main())
