---
title: Pre-flight checklist — operator gate before live start
type: runbook
tags: [operator, pre-flight, checklist, sprint-11]
created: 2026-04-25
updated: 2026-04-25
status: stable
sources:
  - src/platform/config.py
  - src/__main__.py
---

# Pre-flight checklist — operator gate

**TL;DR:** Mandatory operator checklist before `python -m src run` on Mainnet (или Bybit demo trading). Verifies config + connectivity + state coherence.

Per S11 PHASE 2 Q3 (operator readiness deliverable 4).

## Critical gates (BLOCK if fail)

### Gate 1: Config validation

```bash
source .venv/bin/activate
python -c "from src.platform.config import Settings; s = Settings(); print(f'testnet={s.testnet}, trading_enabled={s.trading_enabled}, live_trading={s.live_trading}')"
```

**Expected output (testnet/demo):**
```
testnet=True, trading_enabled=False, live_trading=False
```

**Expected output (Mainnet/live):**
```
testnet=False, trading_enabled=True, live_trading=True
```

**FAIL if:** `live_trading=True` AND (`testnet=True` OR `trading_enabled=False`) — `_live_trading_guards` validator должен raise ValueError. Bot не start.

### Gate 2: Database migration check

```bash
python -c "from pathlib import Path; from src.platform.db import init_db; from src.platform.config import Settings; s = Settings(); init_db(s.db_path, Path('migrations')); print('OK')"
```

**Expected:** `OK`. All migrations apply cleanly.

### Gate 3: Reconcile-only smoke test

```bash
python -m src reconcile-only --symbol BTCUSDT
```

**Expected:** `reconcile-only: bootstrap complete для BTCUSDT` + exit 0.

**FAIL if:** REST connectivity error, API key invalid, или reconcile divergence at boot.

### Gate 4: Override gate validation

```bash
python -c "from src.platform.config import Settings; s = Settings(); from src.risk.override import OverrideStore; OverrideStore(s.risk_override_path, hmac_key=s.risk_override_hmac_key); print('OK')"
```

**Expected:** `OK`. HMAC key length ≥ 32 chars, override file path writable.

### Gate 5: WFA baseline (optional но recommended)

```bash
python -m src wfa --symbol BTCUSDT --start 2024-01-01 --end 2024-04-01
```

**Expected:** JSON output с `acceptance_gate.passed`. If `passed: false`, strategy не fit для current data window — investigate before live.

NOTE S11: `_load_ohlcv` is stub (S12 integrates real data path). Empty df returns exit 1 + WARNING.

## Recommended (warn if skipped)

### Recommendation 1: REST connectivity check

```bash
python -c "from src.marketdata.bybit.rest import BybitRESTClient; from src.platform.config import Settings; s = Settings(); rest = BybitRESTClient(api_key=s.bybit_api_key, api_secret=s.bybit_api_secret, testnet=s.testnet); print('REST OK')"
```

### Recommendation 2: Disk space check

```bash
df -h "$(dirname "$(python -c "from src.platform.config import Settings; print(Settings().db_path)")")"
```

**Expected:** ≥ 1 GB free для SQLite WAL + Parquet snapshots.

### Recommendation 3: Kill-switch sentinel cleanup

```bash
ls -la "$(python -c "from src.platform.config import Settings; print(Settings().runtime_kill_switch_path)")" 2>/dev/null
```

**If exists** — remove перед start (otherwise `_maybe_kill_switch` immediately halts):

```bash
rm "$(python -c "from src.platform.config import Settings; print(Settings().runtime_kill_switch_path)")"
```

### Recommendation 4: Log rotation setup

If running long sessions (24h+), redirect к dated log:

```bash
python -m src run --symbol BTCUSDT > "bot_$(date +%Y%m%d_%H%M%S).log" 2>&1 &
```

## Post-start monitoring

Once `python -m src run` is running:

```bash
# Tail logs (separate terminal)
tail -f bot.log | jq 'select(.level == "warning" or .level == "error")'

# Periodic state snapshot (separate terminal, run каждый 5 min)
watch -n 300 'python -m src monitor --symbol BTCUSDT'
```

См. [[log-grep-templates]] для дополнительных filtering recipes.

## Halt response

Если halt fires — см. [[halt-recovery]] priority matrix:
- **P0 (CRITICAL):** wake on-call now, SQL + REST cross-check, manual recovery per runbook
- **P1 (RECOVERABLE):** notification only, resume during business hours
- **P2 (log only):** audit trail, no action

## Related

- [[halt-recovery]] — 19 halt codes + priority matrix + recovery procedures
- [[log-grep-templates]] — operator log filtering recipes
- [[../components/kill-switch-cli]] — operator-initiated halt mechanism
- [[../components/coordinator]] — `request_halt` API consumer

## Sources

- `src/platform/config.py::Settings` — config + `_live_trading_guards` validator
- `src/__main__.py` — CLI subcommands (`run`, `reconcile-only`, `wfa`, `monitor`, `kill`, `backfill`)
- `migrations/` — schema versions
