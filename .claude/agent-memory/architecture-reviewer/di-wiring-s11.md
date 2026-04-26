---
name: DI wiring patterns S11 — _cmd_run + endpoint bug class
description: _cmd_run DI graph order, endpoint string anti-pattern, MagicMock-in-prod concern, FillRecorder stub pattern
type: project
---

**S11 T2 DI graph (verified correct):**
Settings → BybitRESTClient → BybitFilters (placeholders) → BybitMarketAdapter →
init_db + connect → ExecutionStateRepo → Reconciler(query=adapter) →
Coordinator(adapter, repo, reconciler, symbol, base_coin) →
EmaCrossoverAdxRsiStrategy (pure) → RiskManager(conn, settings) →
BarSource(adapter=rest, symbol, interval="60") [NOTE: raw REST not adapter wrapper — intentional, Any-typed] →
FillRecorder stub → BybitPrivateWSConsumer → RuntimeManager

**Symbol/base_coin derivation:** symbol from CLI --symbol arg (default BTCUSDT). base_coin = symbol[:-4] for USDT/USDC suffix — EXACTLY mirrors Reconciler._derive_base_coin.

**ENDPOINT BUG PATTERN (S11 T2 concern):**
`endpoint = "demo.bybit.com" if settings.testnet else "stream.bybit.com"` is WRONG.
pybit._websocket_stream uses testnet=bool + demo=bool flags, NOT endpoint string.
ws_private.py derives: testnet = "testnet" in endpoint, demo = "demo" in endpoint.
- settings.testnet=True → "demo.bybit.com" → testnet=False (no "testnet" substring), demo=True → WRONG: connects to demo-mainnet not testnet
- Correct mapping: testnet=True → endpoint should contain "testnet" (e.g., "stream-testnet.bybit.com")
- Traded concern not blocker for S11 (operator will run testnet=True in demo mode) but must be fixed before S12 Mainnet.

**MagicMock-in-prod anti-pattern:**
`from unittest.mock import MagicMock` inside _cmd_run production function = test library in prod path.
Pattern: use simple stub class (3 lines) or lambda-based named type instead. Not a BLOCK for S11 (FillRecorder production wiring is S12 explicit carry-over) but should be resolved when FillRecorder wired.

**FillRecorder stub:** MagicMock with on_fill_event = lambda: None. Satisfies _FillRecorderProto (structural typing). WS execution events silently dropped — acceptable S11, documented S12+.

**Why:** First full DI wiring since S8a T20 deferral. Each constructor evolved independently. MagicMock in prod and endpoint string are observable when operator runs testnet=True.
**How to apply:** Flag endpoint string pattern as concern (not blocker) in any future __main__.py review. Flag MagicMock imports in src/ as HIGH.
