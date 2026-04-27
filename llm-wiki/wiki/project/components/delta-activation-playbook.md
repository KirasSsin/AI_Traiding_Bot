---
title: δ TESTNET Activation Playbook (S37+ Operator Procedure)
type: component
tags: [component, testnet-demo, operator-playbook, halt-gate, monitoring, sprint-37, ru]
created: 2026-04-27
updated: 2026-04-27
status: stable
sources:
  - project/decisions/0055-sprint-36-delta-activation.md
  - project/decisions/0057-sprint-37-carry-overs-hardening.md
  - project/decisions/0056-sprint-36-dsr-sigma-sr-amendment.md
  - src/runtime/manager.py
  - src/risk/halt_gate.py
---

# δ TESTNET Activation Playbook

**TL;DR:** Step-by-step operator procedure для activation δ TESTNET demo. Pre-checklist + 5 activation steps + monitoring procedure + halt response procedure + DSR status guide + 12mo MAINNET-promotion review checklist. Per ADR 0055 + ADR 0057 binding.

## Pre-activation checklist

Все items MUST be true перед activation:

- [ ] S37 shipped (tag v0.1.0-alpha.37 OR later)
- [ ] All 6 critical carry-overs closed (security 1-3 + trading-logic 4-5 + quant 8)
- [ ] ADR 0055 acknowledgment template understood (12mo MAINNET-promotion gate, NOT shutdown)
- [ ] ADR 0057 SD-1 understood (HALT_UNKNOWN_SYMBOL distinct ReasonCode = audit attribution preserved)
- [ ] ADR 0057 SD-3 understood (whitelist Setting + startup banner)
- [ ] ADR 0057 SD-4 understood (activation_ts HMAC integrity — tamper raises halt)
- [ ] `MEAN_REVERSION_S17_RELAXED_PARAMS` LOCKED constants reviewed (RSI 35/65, BB 1.5σ)
- [ ] Bybit TESTNET API credentials ready в production .env
- [ ] `risk_override_hmac_key` (32+ chars) configured

## Activation steps

### Step 1 — Set environment variable

В production `.env` file:

```bash
S35_DEMO_ACTIVE=true
# Optional: extend whitelist если multi-symbol future:
# S35_DEMO_APPROVED_SYMBOLS=["BTCUSDT","ETHUSDT"]  # JSON list format
```

Default whitelist `["BTCUSDT"]` per ADR 0057 SD-3 — single-symbol δ pre-commit.

### Step 2 — Verify Settings invariants

```bash
.venv/bin/python -c "
from src.platform.config import Settings
s = Settings()
print('s35_demo_active:', s.s35_demo_active)
print('testnet:', s.testnet)
print('live_trading:', s.live_trading)
print('whitelist:', s.s35_demo_approved_symbols)
print('halt_dd_intraday:', s.s35_halt_dd_intraday)
print('halt_dd_multiday:', s.s35_halt_dd_multiday)
print('halt_consecutive_losses:', s.s35_halt_consecutive_losses)
print('halt_no_trade_months:', s.s35_halt_no_trade_months)
"
```

Expected output:
- `s35_demo_active: True`
- `testnet: True` (MAINNET-exclusion invariant per ADR 0055)
- `live_trading: False` (MAINNET-exclusion)
- `whitelist: ['BTCUSDT']` (case-normalized к uppercase per S37 T2)
- Halt thresholds: 0.20 / 0.15 / 5 / 6

Если invariant violation → ValueError raised at Settings construction. Fix .env перед restart.

### Step 3 — Restart bot

```bash
# Via systemd / docker / script:
.venv/bin/python -m src run
```

Bot startup sequence:
1. Coordinator bootstrap
2. **S37 startup banner** — log entry `runtime.s35_demo_startup_banner` displays:
   - approved_symbols list
   - halt_thresholds (4 triggers)
   - fail_closed=True flag
3. WS consumer start
4. Main tick loop begins

**Verify banner в log output** (operator-visible audit at boot).

### Step 4 — Verify activation_ts persisted (signed)

После first tick (~5 seconds):

```bash
sqlite3 data/bot.db "SELECT key, value_json FROM state WHERE key='runtime:halt_gate:activation_ts';"
```

Expected:
```
runtime:halt_gate:activation_ts | {"payload":{"value":"2026-04-27T..."},"sig":"<64-char hex>"}
```

If unsigned (no `payload`/`sig` envelope) → S37 T3 not deployed. Verify branch + restart.

**DO NOT manually mutate this row** — HMAC verification fails on next tick → bot halts с `HALT_UNKNOWN_SYMBOL` (tamper-detection per ADR 0057 SD-4).

### Step 5 — Monitor first 24h

Verify bot не halts spuriously:

```bash
sqlite3 data/bot.db "SELECT halt_ts, halt_reason FROM halt_log ORDER BY halt_ts DESC LIMIT 5;"
```

Expected: empty OR existing halts unrelated к S37 (e.g. KILL_SWITCH_REQUESTED).

If `HALT_S36_*` OR `HALT_UNKNOWN_SYMBOL` fires immediately → investigate per "Halt response procedure" below.

## Monitoring procedure (weekly)

Recommended weekly checks during 12mo TESTNET window:

```bash
# 1. Halt log activity
sqlite3 data/bot.db "SELECT halt_ts, halt_reason, context FROM halt_log WHERE halt_ts > date('now', '-7 days') ORDER BY halt_ts DESC;"

# 2. Trade history accumulation
sqlite3 data/bot.db "SELECT COUNT(*) AS n_trades, MIN(exit_ts) AS first_trade, MAX(exit_ts) AS last_trade FROM trade_history WHERE symbol='BTCUSDT';"

# 3. Equity snapshot trajectory
sqlite3 data/bot.db "SELECT ts, total_equity FROM equity_snapshots ORDER BY ts DESC LIMIT 10;"

# 4. Cross-trial log (post-12mo evaluation)
cat data/cross_trial_sharpes.json
```

Expected baseline (S22 reference): ~13 trades/year на BTCUSDT 4H mean-reversion.

## Halt response procedure

When HaltGate fires (any of 4 triggers):

| ReasonCode | Trigger | Operator action |
|-----------|---------|-----------------|
| `HALT_S36_DD_INTRADAY` | 24h DD ≥ 20% | Immediate review — flash crash OR strategy collapse |
| `HALT_S36_DD_MULTIDAY` | HWM-since-activation DD ≥ 15% | Cumulative loss review — consider honest close |
| `HALT_S36_CONSECUTIVE_LOSSES` | 5 sequential losing trades | Strategy degradation review |
| `HALT_S36_NO_TRADE_TIMEOUT` | 6mo without n≥30 trades | Signal-frequency starvation — consider regime/timeframe change |
| `HALT_UNKNOWN_SYMBOL` | Whitelist mismatch OR activation_ts tampered | **Critical** — config audit OR security incident |

Procedure (any halt):

1. **Bot already exited** (HaltGate sets `_stopping=True`)
2. Review `halt_log` entry для context
3. Review related logs (halt_ts ± 1 hour)
4. Decision tree:
   - Spurious / config issue → fix .env + manual FSM reset через `--reconcile-only`
   - Strategy collapse / HALT_S36_DD_* → S38+ honest close ADR
   - HALT_UNKNOWN_SYMBOL after stable operation → security incident, audit halt_log + state table
5. Document review findings (operator notes file OR commit message в repo)
6. Restart bot ONLY после documented review

## DSR status interpretation guide (per ADR 0056)

When 12mo MAINNET-promotion review per ADR 0055 SD-8:

```bash
.venv/bin/python -c "
from src.analytics.live_trade_reporter import generate_live_report
from src.risk.trade_history import TradeHistoryRepository
from src.platform.db import connect
conn = connect('data/bot.db')
repo = TradeHistoryRepository(conn)
trades = repo.load_recent(window_days=365, symbol='BTCUSDT')
report = generate_live_report(trades)
print(report)
"
```

Interpretation:

| dsr_status | Meaning | Action |
|------------|---------|--------|
| `INSUFFICIENT_TRADES` (n<10) | DSR=NaN | NOT eligible для MAINNET discussion. Continue TESTNET OR honest close. |
| `UNDERPOWERED` (10≤n<30) | DSR computed но statistically weak | Informational only. NOT gate-eligible. |
| `GATE_ELIGIBLE` (n≥30) | DSR valid evaluation | Apply ADR 0055 SD-1 PASS gates (n≥50, Sharpe≥0.7, MC p≤0.05, DSR≥0.95) |

calibration_ratio_to_s22 (live_Sharpe / 2.96):
- ≥ 0.70 → PASS calibration
- < 0.70 → FAIL calibration (live underperforms S22 baseline beyond tolerance)

## 12mo MAINNET-promotion review checklist

Per ADR 0055 SD-8 (MAINNET criteria DEFERRED к S37+ post-12mo data):

After 12 months TESTNET operation:

- [ ] n_trades ≥ 50 (per ADR 0055 SD-1 PASS gate)
- [ ] live_Sharpe / 2.96 calibration ratio ≥ 0.70
- [ ] MC sign_flip p-value ≤ 0.05 (n≥20 required)
- [ ] DSR ≥ 0.95 + status GATE_ELIGIBLE
- [ ] Max DD ≤ 30% (sustained equity preservation)
- [ ] No active HaltGate trigger в trailing 30 days
- [ ] Operator acknowledgment template verbatim per ADR 0052

If ALL boxes checked → S38+ ADR pre-registers MAINNET promotion (Bailey 2014 anti-snooping).
If ANY fail → continue TESTNET OR honest close (S38+ ADR documents rationale).

## Halt criteria summary (LOCKED per ADR 0055 + ADR 0057)

| Trigger | Threshold | Source |
|---------|-----------|--------|
| Intraday DD | ≥ 20% (24h rolling) | ADR 0055 SD-3 |
| Multiday DD | ≥ 15% (since activation_ts HWM, signed) | ADR 0055 SD-3 + ADR 0057 SD-4 |
| Consecutive losses | ≥ 5 | ADR 0055 SD-3 |
| No-trade timeout | ≥ 6 months without n≥30 trades | ADR 0055 SD-3 |
| Unknown symbol (NEW S37) | symbol NOT in whitelist OR None | ADR 0057 SD-2+SD-3 |
| activation_ts tamper (NEW S37) | HMAC verification fail | ADR 0057 SD-4 |

## Carry-overs к S38+ (NOT in S37)

Per pre-s37-backlog Items deferred:
- #6 months_since truncation documentation
- #7 RiskSharedDeps refactor (Demeter)
- #9 Sharpe semantics extended ADR doc
- #10 DD_MULTIDAY/NO_TRADE_TIMEOUT extended scenarios

S38+ operational items:
- 12mo MAINNET-promotion ADR (per ADR 0055 SD-8)
- Architecture refactor (Item #7)

## Related

- [[../decisions/0055-sprint-36-delta-activation]] — δ activation primary ADR
- [[../decisions/0057-sprint-37-carry-overs-hardening]] — security hardening + symbol whitelist
- [[../decisions/0056-sprint-36-dsr-sigma-sr-amendment]] — DSR thresholds + calibration baseline
- [[halt-gate-wireup]] — HaltGate runtime wire-up
- [[live-trade-reporter]] — live data adapted reporter
- [[../sprints/sprint-36-delta-activation]] — S36 ship
- [[../sprints/sprint-37-carry-overs-hardening]] — S37 ship
- [[../pre-s37-backlog]] — carry-overs context
