# AI Trading Bot v0.1

Algorithmic trading bot для **Bybit Spot**. TESTNET-only deployment per ADR 0055 + ADR 0057. Mean-reversion + Donchian breakout strategies на BTC/ETH/SOL. Walk-forward analysis (WFA) + DSR + MC permutations + dashboard UI.

**Текущий статус:** v0.1 infrastructure complete (tag `v0.1.0-alpha.38`). Strategy validation NEGATIVE — **7 hypotheses tested, все FAIL conjoint** per [`acceptance-criteria.md`](llm-wiki/wiki/project/architecture/acceptance-criteria.md). δ TESTNET infrastructure production-ready (S36 wired + S37/S38 hardened).

См. [`current-state.md`](llm-wiki/wiki/project/architecture/current-state.md) для актуальной картины.

---

## Quick start (1 command, локально из любой папки терминала)

```bash
cd /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot && ./scripts/start-bot.sh
```

Что произойдёт:
- Бот стартует на **http://127.0.0.1:8000/**
- **Браузер автоматически открывается** на этой ссылке (через 1.5 сек после старта)
- Ctrl+C в терминале → бот останавливается

В browser выбираешь strategy + symbol + timeframe + date range → "Run Backtest" → результаты с TIER 1+2 metrics + warnings.

### Если репозиторий в другом месте

Замени путь после `cd` на свой:

```bash
cd /path/to/your/AI_Traiding_Bot && ./scripts/start-bot.sh
```

### Other modes

```bash
cd /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot && ./scripts/start-bot.sh --help        # Show usage
cd /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot && ./scripts/start-bot.sh --live        # δ TESTNET live trading (advanced — see playbook)
cd /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot && ./scripts/start-bot.sh --backfill    # Download OHLCV bars
```

**Совет**: если запускаешь часто — добавь alias в `~/.zshrc` OR `~/.bashrc`:

```bash
alias bot='cd /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot && ./scripts/start-bot.sh'
```

После `source ~/.zshrc` (или новый terminal) — просто пишешь `bot` из любой директории.

---

## Setup (one-time)

### Requirements

- macOS / Linux
- Python 3.12 (StrEnum, PEP 604 unions, pydantic v2)
- TA-Lib system library (`brew install ta-lib` на macOS)
- Bybit аккаунт (TESTNET) с API key + secret

### Install

```bash
# 1. Clone repo
git clone https://github.com/KirasSsin/AI_Traiding_Bot.git
cd AI_Traiding_Bot

# 2. Python venv (Python 3.12 required)
python3.12 -m venv .venv

# 3. Install all deps (core + dashboard)
.venv/bin/pip install -e ".[dev,dashboard]"

# 4. Create .env (см. шаблон ниже)
cp .env.example .env  # OR создай вручную
# Edit .env: BYBIT_API_KEY, BYBIT_API_SECRET, RISK_OVERRIDE_HMAC_KEY

# 5. Sanity check (optional)
.venv/bin/pytest tests/unit -q     # 905 passed
.venv/bin/mypy --strict src/       # 0 errors (79 source files)
```

### .env template

```bash
# Bybit TESTNET API credentials (https://testnet.bybit.com → API Management)
BYBIT_API_KEY=your_testnet_key_here
BYBIT_API_SECRET=your_testnet_secret_here

# TESTNET enforcement (per ADR 0055 SD-1 — δ is TESTNET ONLY)
TESTNET=true
LIVE_TRADING=false

# Risk override HMAC key (REQUIRED, min 32 chars, separate от API secret)
# Generate: python -c "import secrets; print(secrets.token_hex(32))"
RISK_OVERRIDE_HMAC_KEY=your_64_char_hex_key_here

# δ TESTNET live demo (set true когда готов к live activation per playbook)
S35_DEMO_ACTIVE=false
```

---

## Что доступно через UI

### Strategy presets (4)

| ID | Sprint | Description | Verdict |
|----|--------|-------------|---------|
| `ema_crossover_s13` | S13 baseline | EMA 12/26 + ADX + RSI 14 | FAIL conjoint (T1=-44.46) |
| `mean_reversion_s15` | S15 original | RSI 30/70 + BB(20, 2.0σ) AND-gated | FAIL conjoint (MC p=0.998 noise) |
| `mean_reversion_s17_relaxed` | S17 relaxed | RSI 35/65 + BB(20, 1.5σ) AND-gated | **5/6+DSR+MC PASS** / T5 floor unreachable |
| `donchian_breakout_s35` | **S35 LATEST** | Donchian 20/10 + ATR 2.0× stop, long-only | FAIL conjoint (n=21<<50, α CLOSED per ADR 0054) |

### Symbols × Timeframes

| Symbol | 5M | 15M | 1H | 4H | 1D |
|--------|---|----|----|----|-----|
| **BTCUSDT** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **ETHUSDT** | — | ✅ | ✅ | ✅ | — |
| **SOLUSDT** | — | ✅ | ✅ | ✅ | — |

Data range: **2023-01-01 → 2026-04-26** (3.31 years).

### WFA auto-scale (S38 dashboard extension)

ADR 0014 default = train 2000 / test 500 / k_folds 5 / embargo 20 = 4520 bars min.

UI auto-scales для small date ranges:
- ≥ 4520 bars: ADR 0014 default (best statistical validity)
- 1000-4520: linear scale (k=5)
- 300-1000: k=3, scaled
- 100-300: k=2 minimum
- < 100: BLOCKED (extend range OR pick finer interval)

Result JSON shows `wfa_params` actual values + warning если auto-scaled below default.

---

## Live δ TESTNET mode (advanced)

**ВНИМАНИЕ:** перед активацией прочитай [`delta-activation-playbook.md`](llm-wiki/wiki/project/components/delta-activation-playbook.md) полностью — 8 pre-activation gates + 5 NEW S38 gates (F4-F7 + T3 H3 accountType).

### Activation procedure

1. Verify pre-activation checklist (8 + 5 NEW gates per playbook)
2. Set `S35_DEMO_ACTIVE=true` в `.env`
3. Restart bot:

```bash
./scripts/start-bot.sh --live
```

Bot:
- Boots с startup banner (whitelist + halt thresholds)
- Persists signed activation_ts (HMAC integrity per ADR 0057 SD-4)
- Streams Bybit WS private + REST kline
- HaltGate evaluates per-tick (4 triggers + tamper detection)
- Trades MeanReversionRsiBBStrategy с MEAN_REVERSION_S17_RELAXED_PARAMS LOCKED

### Halt criteria (LOCKED per ADR 0055 + ADR 0057)

| Trigger | Threshold | Action |
|---------|-----------|--------|
| Intraday DD | ≥ 20% (24h rolling) | halt + bot exit |
| Multi-day DD | ≥ 15% (HWM since activation) | halt + bot exit |
| Consecutive losses | ≥ 5 trades | halt + bot exit |
| No-trade timeout | ≥ 6 months без n≥30 | halt + bot exit |
| Unknown symbol | NOT в whitelist | halt + bot exit (fail-closed) |
| activation_ts tamper | HMAC mismatch | halt + bot exit |

When HaltGate fires → bot exits cleanly. Manual operator restart required (per playbook halt response procedure). NO automatic resume.

---

## CLI commands (advanced)

### Backfill historical data

```bash
TESTNET=false .venv/bin/python -m src backfill \
  --symbol BTCUSDT \
  --interval 60 \
  --start 2023-01-01 \
  --end 2026-04-26
```

### Walk-Forward Analysis (CLI)

```bash
.venv/bin/python -m src wfa \
  --symbols BTCUSDT \
  --interval 240 \
  --strategy mean_reversion \
  --rsi-oversold 35 --rsi-overbought 65 \
  --bb-k 1.5 \
  --wfa-train 2000 --wfa-test 500 --wfa-folds 5 --wfa-embargo 20
```

### Monitoring (read-only)

```bash
.venv/bin/python -m src monitor
```

### Kill switch

```bash
.venv/bin/python -m src kill   # writes .kill_switch sentinel → bot exits cleanly
```

### Reconcile-only (bootstrap test)

```bash
.venv/bin/python -m src reconcile-only
```

---

## Архитектура

### Bounded contexts (DDD)

- **MarketData** (`src/marketdata/`) — OHLCV ingest (Bybit V5 REST + WS)
- **SignalGen** (`src/signalgen/`) — strategies (EMA crossover, mean-reversion, Donchian)
- **Risk** (`src/risk/`) — Kelly sizing + circuit breakers + HaltGate (S35) + override store
- **Execution** (`src/execution/`) — FSM coordinator + Bybit Spot adapter + reconciler
- **Backtest** (`src/backtest/`) — replay engine + WFA runner + MC permutations + DSR
- **Analytics** (`src/analytics/`) — DSR/Sortino/Sharpe + cross-trial log + live trade reporter
- **Runtime** (`src/runtime/`) — process lifecycle (bootstrap → ws_consumer → main loop)
- **Dashboard** (`src/dashboard/`) — FastAPI + vanilla JS UI (S25)
- **Platform** (`src/platform/`) — Settings + SQLite + logging + DB migrations

### FSM (canonical post-S38)

- 16 states / 30 events / 74 transitions / **50 reason codes**
- Single-writer per ADR 0023
- HaltGate wired в RuntimeManager._tick (S36 + S37 + S38 fail-closed)

### Acceptance criteria (LOCKED per ADR 0052 amended)

- T1 Sharpe ≥ 0.7 / T2 Sortino ≥ 1.5 / T3 Max DD ≤ 25% / T4 win+RR / T5 n ≥ 50 + t-stat ≥ 2.0 / T6 OOS/IS Sharpe ≥ 0.7
- DSR ≥ 0.95 / MC p-value ≤ 0.05
- N_eff ≥ 50 (Kish 1965 — single-symbol n_eff = n_raw)

---

## Тестирование

```bash
.venv/bin/pytest tests/unit -q                    # 905 passed (post-S38)
.venv/bin/pytest tests/integration -q             # 33 passed
.venv/bin/pytest -m property                      # property tests (Hypothesis)
.venv/bin/mypy --strict src/                      # 0 errors (79 source files)
```

---

## Важные ADR (Architecture Decision Records)

| ADR | Тема |
|-----|------|
| 0052 | Acceptance criteria amendment LOCKED (T5 floor 50 + n_eff ≥ 50 + MC ≤ 0.05) |
| 0053 | δ TESTNET pre-activation infrastructure (S35) |
| 0055 | δ TESTNET activation (HaltGate wire-up) |
| 0056 | DSR sigma_SR sourcing hierarchy + amendment 2 (Sharpe pnl_pct) |
| 0057 | Carry-overs hardening (HALT_UNKNOWN_SYMBOL + HMAC integrity + clock injection) |
| 0058 | δ Parallel hardening (F2 quant + bybit-api review + Item #7 Demeter) |

Полный список: [`llm-wiki/wiki/project/decisions/`](llm-wiki/wiki/project/decisions/) (58 ADRs).

---

## Проектная документация

| Файл | Описание |
|------|----------|
| [`current-state.md`](llm-wiki/wiki/project/architecture/current-state.md) | Live state + canonical counts + sprint history |
| [`acceptance-criteria.md`](llm-wiki/wiki/project/architecture/acceptance-criteria.md) | T1-T6 + DSR + MC LOCKED thresholds |
| [`delta-activation-playbook.md`](llm-wiki/wiki/project/components/delta-activation-playbook.md) | Operator procedure для δ TESTNET (S37+S38) |
| [`development-workflow.md`](llm-wiki/wiki/project/architecture/development-workflow.md) | 9-phase sprint lifecycle |
| [`SPRINT_STATE.md`](llm-wiki/wiki/project/SPRINT_STATE.md) | Living sprint state |

---

## Disclaimer

**TESTNET ONLY.** No real capital risked. Не финансовая рекомендация. 7 strategy hypotheses tested — все FAIL conjoint per pre-registered acceptance criteria. Это research project, не production trading system.

MAINNET activation forbidden by code-level invariants (ADR 0055 SD-1) до 12mo TESTNET evidence + new ADR pre-registration.

## License

См. [`LICENSE`](LICENSE).
