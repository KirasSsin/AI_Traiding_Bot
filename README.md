# AI Trading Bot v0.1

Алгоритмический торговый бот для Bybit Spot. Mean-reversion стратегии (RSI + Bollinger Bands) на BTC/ETH/SOL. Полный walk-forward analysis (WFA) backtest pipeline + DSR + MC permutations + dashboard UI.

**Текущий статус:** v0.1 infrastructure complete. Strategy validation NEGATIVE (5 hypotheses tested, all FAIL conjoint per acceptance-criteria.md). См. [`llm-wiki/wiki/project/architecture/current-state.md`](llm-wiki/wiki/project/architecture/current-state.md).

---

## Установка

### Требования

- macOS / Linux (Windows не testowany)
- Python 3.12 (StrEnum, PEP 604 unions, pydantic v2)
- TA-Lib system library (`brew install ta-lib` на macOS)
- Bybit аккаунт (demo OR mainnet) с API key + secret

### Setup

```bash
# 1. Clone repo
git clone https://github.com/KirasSsin/AI_Traiding_Bot.git
cd AI_Traiding_Bot

# 2. Python venv (требует Python 3.12)
python3.12 -m venv .venv
source .venv/bin/activate  # или: .venv/bin/python для прямого вызова

# 3. Install core dependencies
pip install -e ".[dev]"

# 4. Install dashboard dependencies (опционально, для UI)
pip install -e ".[dashboard]"

# 5. Создай .env (см. шаблон ниже)
cp .env.example .env  # OR создай вручную
# Заполни BYBIT_API_KEY, BYBIT_API_SECRET, RISK_OVERRIDE_HMAC_KEY

# 6. Sanity check
.venv/bin/pytest tests/unit -q  # ожидается 740 passed
.venv/bin/mypy --strict src/    # ожидается clean (75 src files)
```

### .env шаблон

```bash
# Bybit API credentials (demo OR mainnet)
BYBIT_API_KEY=your_key_here
BYBIT_API_SECRET=your_secret_here

# TESTNET=true → Bybit demo (api-testnet.bybit.com, бесплатные fake fills)
# TESTNET=false → Bybit Mainnet (api.bybit.com, РЕАЛЬНЫЕ ДЕНЬГИ)
TESTNET=true

# Risk override HMAC key (REQUIRED, min 32 chars, separate от API secret)
# Generate: python -c "import secrets; print(secrets.token_hex(32))"
RISK_OVERRIDE_HMAC_KEY=your_32_char_hex_key_here
```

---

## Использование

### 1. Dashboard UI (рекомендуется для первого запуска)

Web UI для backtest comparison + visual results display. Demo-only (TESTNET=true), no live trading.

```bash
./scripts/dashboard.sh
# → uvicorn запускается на http://127.0.0.1:8000/
# → браузер открывается автоматически
```

**Что видишь в UI:**
- Dropdown: strategy (3 пресета) / symbol (BTC/ETH/SOL) / timeframe (5M/15M/1H/4H/1D) / date range
- "▶ Запустить backtest" — WFA на исторических данных (~30-60s)
- Результаты:
  - VERDICT (PASS/FAIL — color-coded)
  - 4 risk warnings (если применимо: overfit Sharpe / regime concentration / MC noise / DSR penalty)
  - T1-T6 + DSR + MC table (color-coded по thresholds)
  - Trade-level stats (winners, losers, commissions, avg win/loss, profit factor)
  - Per-fold sharpe ratios (WFA K=5)
- "История запусков" — re-display previous cached runs (instant)

**Стратегии available:**
- `ema_crossover_s13` — EMA 12/26 + RSI 14 + ATR 14 (S13 baseline, FAIL T1+T2+T4+T5)
- `mean_reversion_s15` — RSI 30/70 + BB(20, 2.0σ) AND-gated (S15 original)
- `mean_reversion_s17_relaxed` — RSI 35/65 + BB(20, 1.5σ) AND-gated (S17 relaxed, лучшие результаты по DSR+MC)

См. [`llm-wiki/wiki/project/sprints/sprint-25-dashboard.md`](llm-wiki/wiki/project/sprints/sprint-25-dashboard.md) для деталей.

### 2. CLI: Backfill historical data

Скачать OHLCV bars с Bybit для backtest:

```bash
# Demo / public data (no API key required for klines)
TESTNET=false .venv/bin/python -m src backfill \
  --symbol BTCUSDT \
  --interval 60 \
  --from 2023-01-01 \
  --to 2026-04-26
# → data/BTCUSDT_1h.parquet

# Multi-symbol
TESTNET=false .venv/bin/python -m src backfill \
  --symbols BTCUSDT,ETHUSDT,SOLUSDT \
  --interval 60 \
  --from 2023-01-01 \
  --to 2026-04-26
```

**Поддерживаемые intervals:** `5` (5M) / `15` (15M) / `60` (1H) / `240` (4H) / `D` (1D). 30M и 2H пока не supported (Bar.interval Literal limit).

### 3. CLI: Walk-Forward Analysis (WFA)

Запустить backtest без UI:

```bash
SPRINT_N=99 .venv/bin/python -m src wfa \
  --symbol BTCUSDT \
  --interval 60 \
  --start 2023-01-01 \
  --end 2026-04-26
```

Output: JSON в stdout с T1-T6 + DSR + MC + verdict + per-fold sharpes. Trial автоматически persisted в `data/cross_trial_sharpes.json` (для DSR multi-testing penalty).

**Strategy config:** hardcoded mean-reversion S17 (RSI 35/65 + BB 1.5σ). Для смены — edit `src/__main__.py:_default_wfa_config()` OR используй dashboard UI с preset selection.

### 4. CLI: Live demo bot (Bybit testnet)

```bash
.venv/bin/python -m src run --symbol BTCUSDT
```

**Что произойдёт (TESTNET=true):**
- Подключение к `api-testnet.bybit.com`
- WebSocket subscribe `spot.kline.60.BTCUSDT`
- Каждый закрытый 1H бар → MeanReversionRsiBBStrategy.on_bar()
- Если RSI<30 AND close<lower_BB(20, 2σ) → LONG entry (paper order)
- HALT cascade на ошибках (FSM 16-state machine)
- Fills записываются в SQLite `state/bot.db`

⚠️ **Mainnet warning:** Если установишь `TESTNET=false` без MVP DONE — **РЕАЛЬНЫЕ ДЕНЬГИ под угрозой**. Acceptance criteria НЕ met (5 hypotheses tested, all FAIL conjoint). Live trading на Mainnet **НЕ рекомендуется** до достижения MVP DONE.

### 5. CLI: Monitoring (read-only)

```bash
.venv/bin/python -m src monitor --symbol BTCUSDT
```

Показывает: current FSM state / halt status / last 10 trades / last 5 halts. Read-only SQLite (mode=ro), безопасно с running bot (no WAL contention).

### 6. CLI: Kill switch

```bash
.venv/bin/python -m src kill
# → пишет sentinel-file (atomic), бот останавливается с HALT_KILL_SWITCH
```

### 7. CLI: Reconcile-only (bootstrap test)

```bash
.venv/bin/python -m src reconcile-only --symbol BTCUSDT
# → bootstrap + reconcile (без trading loop), exit 0/1
```

Полезно для проверки connectivity + state consistency без рисков.

---

## Архитектура

### Bounded contexts (DDD)

```
src/
├── platform/      # Settings, DB, logging, deps
├── marketdata/    # Bybit REST/WS, OHLCV models, BarSource
├── signalgen/     # Strategies (EMA crossover, MeanReversion), indicators
├── risk/          # Kelly sizing, circuit breakers, override store, FSM helpers
├── execution/     # Coordinator (FSM 16/30/74), Reconciler, OCO emulation
├── runtime/       # RuntimeManager (process lifecycle)
├── backtest/      # WFA, DSR, MC, replay engine, strategy metrics
├── analytics/     # CrossTrialLog (cross-trial sigma_SR persistence)
└── dashboard/     # NEW (S25): FastAPI web UI (Presentation context)
```

### Acceptance criteria (см. `llm-wiki/wiki/project/architecture/acceptance-criteria.md`)

**Strategy-level (T1-T6, OOS only):**
- T1 Sharpe ≥ 1.0
- T2 Sortino ≥ 1.5
- T3 MaxDD < 25%
- T4 win rate ≥ 45%@RR≥1.5 OR ≥ 35%@RR≥2.0
- T5 mean expectancy > 0 + t-stat > 2.0 + n_trades ≥ 100
- T6 OOS/IS Sharpe ratio ≥ 0.7
- DSR > 0 (Bailey 2014 multi-testing penalty)

**System-level (S1-S6, infrastructure):**
- S1 Uptime ≥ 99.5% rolling 30d
- S2 WS reconnect p99 < 5s
- S3 P&L reconciliation ≥ 99.99%
- S4 Dashboard p95 < 2s (S25 partial)
- S5 Config hot-reload (deferred)
- S6 Zero API key leaks (gitleaks/trufflehog в CI deferred)

### FSM (execution state machine)

16 states / 30 events / 74 transitions / 45 reason codes. Single-writer per symbol per ADR 0022. См. `src/execution/state_machine.py` + `wiki/project/components/execution-state-machine.md`.

---

## Тестирование

```bash
# Unit tests (740 tests, ~5s)
.venv/bin/pytest tests/unit -q

# С coverage
.venv/bin/pytest tests/unit --cov=src --cov-report=term-missing

# Integration tests (Bybit testnet, env-gated)
.venv/bin/pytest -m integration

# Property-based tests (Hypothesis)
.venv/bin/pytest tests/property -q

# Type check
.venv/bin/mypy --strict src/

# Lint
.venv/bin/ruff check src/ tests/
```

---

## Важные ADR (Architecture Decision Records)

| ADR | Topic |
|-----|-------|
| [0001-0015](llm-wiki/wiki/project/decisions/) | Foundational (S1) — DDD skeleton + platform + storage |
| [0016](llm-wiki/wiki/project/decisions/0016-bybit-spot-supersedes-binance.md) | Bybit Spot venue (BTC-only MVP) |
| [0017](llm-wiki/wiki/project/decisions/0017-review-agent-harness.md) | Review-agent harness (5 reviewers) |
| [0022](llm-wiki/wiki/project/decisions/0022-sprint-8a-live-runtime.md) | Live runtime + FSM single-writer invariant |
| [0030](llm-wiki/wiki/project/decisions/0030-sprint-15-mean-reversion-multi-symbol.md) | Mean-reversion strategy + multi-symbol infrastructure |
| [0034](llm-wiki/wiki/project/decisions/0034-sprint-19-15m-architecture.md) | 15M timeframe architectural prep + 7 amendments |
| [0038](llm-wiki/wiki/project/decisions/0038-sprint-23-honest-close-v05.md) | v0.5 honest close (5 hypotheses tested) |
| [0039](llm-wiki/wiki/project/decisions/0039-sprint-25-dashboard.md) | Dashboard UI (FastAPI + vanilla JS) |

Полный list: `ls llm-wiki/wiki/project/decisions/` (39 ADRs total).

---

## Проектная документация

- [`llm-wiki/wiki/project/SPRINT_STATE.md`](llm-wiki/wiki/project/SPRINT_STATE.md) — current sprint state (≤2KB, читается первым в сессии)
- [`llm-wiki/wiki/project/architecture/current-state.md`](llm-wiki/wiki/project/architecture/current-state.md) — canonical counts + sprint history
- [`llm-wiki/wiki/project/architecture/acceptance-criteria.md`](llm-wiki/wiki/project/architecture/acceptance-criteria.md) — T1-T6 + S1-S6 thresholds
- [`llm-wiki/wiki/project/sprints/`](llm-wiki/wiki/project/sprints/) — 26 sprint pages (S1-S25)
- [`llm-wiki/wiki/log.md`](llm-wiki/wiki/log.md) — chronological journal

---

## Disclaimer

**Этот бот — research project. Не предназначен для production trading с реальными деньгами без MVP DONE achievement.**

5 strategy hypotheses тестировались across 4.81y BTC Bybit Spot — все FAIL conjoint per acceptance-criteria.md spec. T5 floor 100 trades structurally unreachable на BTC-only mean-reversion (см. ADR 0038 institutional knowledge).

**Не financial advice. Используй на свой риск.**

---

## License

(не specified — см. с автором проекта)

## Contributing

См. `CLAUDE.md` для project conventions (sprint workflow, review agent harness, ADR pattern).
