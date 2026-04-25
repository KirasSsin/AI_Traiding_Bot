---
title: Live demo validation — 48h Bybit demo run protocol
type: runbook
tags: [operator, live-demo, validation, sprint-12, bybit-demo]
created: 2026-04-25
updated: 2026-04-25
status: stable
sources:
  - project/decisions/0027-sprint-12-live-demo-validation.md
  - project/runbooks/pre-flight.md
  - project/runbooks/halt-recovery.md
---

# Live demo validation — 48h Bybit demo run

**TL;DR:** First end-to-end live cycle validation на Bybit demo trading endpoint. Per ADR 0027 verdicts (Q1+Q2+Q3): demo + 48h + multi-criteria gate + zero-trade clause.

## Pre-conditions (HARD-GATE before start)

ALL must pass:

1. ✅ All pre-flight gates pass per [[pre-flight|pre-flight checklist]] (5 critical + 4 recommendations)
2. ✅ Bybit demo API key + secret в `.env` (`BYBIT_API_KEY`, `BYBIT_API_SECRET`) — confirmed demo (not Mainnet)
3. ✅ `settings.testnet=True`, `settings.trading_enabled=False`, `settings.live_trading=False` per Gate 1
4. ✅ Database empty или rolled-back к alpha.11 baseline (Q7 zero-migration constraint preserved)
5. ✅ Operator availability: 5min monitoring cadence × 48h supervised window OR 2-person rotation
6. ✅ Kill-switch sentinel cleaned (Recommendation 3)
7. ✅ Disk space ≥ 1 GB (Recommendation 2)

## Validation params

| Parameter | Value | Source |
|-----------|-------|--------|
| Endpoint | `demo.bybit.com` (auto-routed via `settings.testnet=True`) | Q6 verified |
| Symbol | BTCUSDT | ADR 0026 baseline |
| Timeframe | 1H bars | ADR 0005 |
| Duration | 48h (48 1H bars) | Q2 trader CONFIRM |
| Virtual capital | $1000 USDT (Bybit demo arbitrary) | Q1 trader CONFIRM |
| Strategy | EMA(12)×EMA(26) + ADX + RSI + ATR | live config |

## Start sequence

```bash
# 1. Activate venv + verify config
source .venv/bin/activate
python -c "from src.platform.config import Settings; s = Settings(); print(f'testnet={s.testnet}, trading_enabled={s.trading_enabled}, live_trading={s.live_trading}')"
# Expected: testnet=True, trading_enabled=False, live_trading=False

# 2. Run reconcile-only smoke (last gate)
python -m src reconcile-only --symbol BTCUSDT
# Expected: "reconcile-only: bootstrap complete для BTCUSDT" + exit 0

# 3. Start bot, redirect к dated log
python -m src run --symbol BTCUSDT > "bot_$(date +%Y%m%d_%H%M%S).log" 2>&1 &
echo "Bot PID: $!" > /tmp/bot_pid.txt
```

## Monitoring (every 5 min, 48h)

In separate terminal(s):

```bash
# Terminal 1: tail logs filtered к warnings + errors
tail -f bot_*.log | jq 'select(.level == "warning" or .level == "error")'

# Terminal 2: periodic state snapshot
watch -n 300 'python -m src monitor --symbol BTCUSDT'

# Terminal 3: hourly halt-log SQL check
watch -n 3600 'sqlite3 ~/.ai_trading_bot/bot.db "SELECT halt_code, halted_at FROM halt_log ORDER BY halted_at DESC LIMIT 10"'
```

## Multi-criteria success gate (per Q3 trader CONFIRM)

Validation **PASSED** if ALL hold at end of 48h:

### Structural (always evaluated)

- ✅ **Zero P0 halts** (per [[halt-recovery]] priority matrix)
- ✅ **Reconcile divergence count = 0** (no `HALT_EXIT_RECONCILE_DIVERGENCE` events)
- ✅ **Bootstrap clean** (no `HALT_BOOTSTRAP_AMBIGUOUS`)
- ✅ **WS uptime ≥ 47/48h** (barring P1 outages with auto-resume)

### Trading (conditional on ≥ 1 fill occurring)

- ✅ **Drawdown ≤ 5%** (much tighter than L1 15% warn)
- ✅ **FillRecorder.insert_fill writes successful** (idempotent on duplicate exec_id; DB insert OR structlog audit covers)

### Zero-trade clause (MANDATORY — per Q3 trader concern)

**IF zero fills during 48h** (statistically likely on 1H BTC EMA crossover):
- Structural criteria still apply (P0=0, reconcile=0, bootstrap clean, WS uptime).
- Trading criteria (drawdown, FillRecorder live-path) **WAIVED** with explicit carry-forward к S13.
- Operator records "zero-trade outcome" в sprint-12-live-demo-validation.md + S13 carry-overs.
- This does NOT block S12 ship — S12 = infrastructure validation, NOT trade-edge confirmation.

### Operator sign-off (qualitative)

After 48h:
- Review `bot_*.log` для warnings/errors (non-halt)
- Review halt_log table for any halts
- Review monitor output for FSM state at termination
- Document anomalies even if not breaching criteria

If "no surprises" → sign-off `validation_status: PASSED` в sprint-12 page.

## End sequence

```bash
# 1. Trigger graceful shutdown (kill-switch sentinel)
python -m src kill --reason MANUAL_OPERATOR
# Wait for bot к exit

# 2. Verify clean exit
ps -p $(cat /tmp/bot_pid.txt) > /dev/null && echo "STILL RUNNING — check logs" || echo "exited cleanly"

# 3. Generate validation report
python -m src monitor --symbol BTCUSDT > validation_report_$(date +%Y%m%d_%H%M%S).txt
```

## On halt fire (any class)

См. [[halt-recovery]] priority matrix:
- **P0** → wake on-call immediately. Trigger [[halt-response-protocol]] rollback procedure если irreparable.
- **P1** → notification only. Если HALT_EXCHANGE_OUTAGE + OCO_ARMED + outage > 1h → ESCALATE к P0 (per S12 T3 conditional callout).
- **P2** → log only.

## Related

- [[pre-flight]] — entry criteria gates
- [[halt-recovery]] — halt code reference + priority matrix
- [[halt-response-protocol]] — P0 wake + rollback procedure (created в T5)
- [[../decisions/0027-sprint-12-live-demo-validation]] — ADR + verdicts trail
- [[log-grep-templates]] — log filtering recipes
