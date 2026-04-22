# Техническое Задание: Алготрейдинговый бот BTC/USDT 1H v0.1

---

## 0. Метаданные

| Поле | Значение |
|---|---|
| **Название** | algo-bot — BTC/USDT 1H EMA-Crossover Trading System |
| **Версия ТЗ** | 1.0.0 |
| **Дата** | 17 апреля 2026 |
| **Архитектурный документ** | Консолидированная архитектура v0.1 (17 апреля 2026) |
| **Язык реализации** | Python 3.12 |
| **Стек** | asyncio + uvloop, pandas 2.x, NumPy, TA-Lib, pydantic v2, structlog, SQLite (WAL) + Parquet (snappy) |
| **Биржа** | Binance Spot |
| **Символ** | BTCUSDT |
| **Таймфрейм** | 1H |
| **Режим v0.1** | Paper trading (все ордера в Binance Testnet) |

---

## 🛠️ БЛОК A: Настройка Claude Code для максимального результата

### A.1 CLAUDE.md — системный файл проекта (создать в корне)

Создай файл `CLAUDE.md` в корне репозитория. Claude Code читает его автоматически при старте каждой сессии. Это экономит токены — не нужно повторять контекст.

```markdown
# CLAUDE.md — Project Context for Claude Code

## Project
algo-bot: BTC/USDT 1H algorithmic trading bot, Binance Spot.
Strategy: EMA(20/50) crossover + ADX(14) + RSI(14).
Mode v0.1: Paper trading on Binance Testnet.

## Stack
Python 3.12, asyncio+uvloop, pandas 2.x, TA-Lib, pydantic v2, structlog.
Storage: SQLite (WAL mode) + Parquet (snappy).
Testing: pytest + hypothesis + pytest-asyncio.

## Critical invariants (NEVER violate)
1. Indicators update ONLY on bar.closed == True
2. Signal timestamp < fill timestamp (look-ahead = bug)
3. ALL numbers in config/default.yaml, NEVER hardcoded
4. No bare except. Every exception explicitly typed.
5. Wilder EMA (α=1/n) for ADX/RSI/ATR. Classical EMA (α=2/(n+1)) for crossover.
6. On HTTP 5xx from Binance: query existing order state, NEVER retry with new clientOrderId.

## File structure
See README.md §Repository Structure.

## Current sprint
[Update this line before each Claude Code session]
Sprint N: [description]
Files in scope: [list]

## Testing commands
make test-unit     # pytest tests/unit/ -v
make test-property # pytest tests/property/ -v
make test-integ    # pytest tests/integration/ -v --timeout=30
make lookahead     # python scripts/lookahead_detector.py

## Key formulas (copy-paste ready)
Classical EMA: alpha = 2 / (period + 1); ema = alpha * price + (1 - alpha) * ema_prev
Wilder EMA:    alpha = 1 / period;         ema = alpha * price + (1 - alpha) * ema_prev
ATR(t) = Wilder_EMA(TR(t), 14)
TR(t) = max(high-low, |high-prev_close|, |low-prev_close|)
RSI = 100 - 100/(1 + avg_gain/avg_loss)  [Wilder smoothing]
ADX = Wilder_EMA(|DI+ - DI-| / (DI+ + DI-) * 100, 14)
Kelly f* = (p*b - q) / b   [b = avg_win/avg_loss, q = 1-p]
Half-Kelly = f* / 2, cap at 0.05
```

### A.2 Как работать с Claude Code — экономия токенов

**Правило 1: Один модуль за раз.**
Запускай Claude Code на одном файле/модуле. Не давай весь проект сразу.
```bash
# ХОРОШО
claude "Implement src/indicators/ema.py according to CLAUDE.md and the spec in TZ.md §3.3"

# ПЛОХО
claude "Implement the entire indicators package"
```

**Правило 2: Обновляй `CLAUDE.md → Current sprint` перед каждой сессией.**
Это главная экономия — Claude не переспрашивает что мы делаем.

**Правило 3: Тесты сначала.**
Сначала попроси написать тест (`tests/unit/test_ema.py`), потом реализацию. Тест = спецификация в коде = Claude точно знает что делать.

**Правило 4: Верификация после каждого модуля.**
```bash
make test-unit       # должен быть green
make lookahead       # 0 look-ahead violations
mypy src/indicators/ # 0 errors
```

**Правило 5: Используй `--continue` для длинных задач.**
```bash
claude --continue  # продолжает последнюю сессию без потери контекста
```

**Правило 6: Фиксируй решения в ADR сразу.**
После каждого нетривиального решения:
```bash
claude "Write ADR-NNNN.md for the decision we just made about [topic]"
```

### A.3 Библиотека MD-файлов (живая документация)

Создай папку `docs/` с файлами, которые нужно обновлять при каждом значимом изменении:

```
docs/
├── CLAUDE.md          → корень проекта (копия, source of truth)
├── SPRINT_LOG.md      → что сделано в каждом спринте
├── DECISIONS.md       → краткий лог всех ADR
├── KNOWN_ISSUES.md    → текущие баги и ограничения
├── METRICS_LOG.md     → результаты каждого backtest прогона
└── adr/
    ├── 0001-record-decisions.md
    ├── 0002-python-only-stack.md
    └── ...
```

**Как обновлять после каждого спринта:**
```bash
claude "Update docs/SPRINT_LOG.md with what we completed in Sprint N.
        Update docs/DECISIONS.md if any new ADRs were created.
        Update CLAUDE.md Current sprint to Sprint N+1."
```

---

## 1. Структура репозитория

```
algo-bot/
├── CLAUDE.md                        # Claude Code context (критично!)
├── pyproject.toml                   # PDM deps, ruff, mypy, pytest config
├── Makefile                         # make test, make run, make backtest
├── Dockerfile                       # python:3.12-slim, multi-stage
├── docker-compose.yml               # bot + volumes
├── README.md                        # setup, quickstart
├── CHANGELOG.md                     # keep-a-changelog 1.1.0
├── .env.example                     # шаблон: BINANCE_API_KEY, BINANCE_SECRET
├── .secrets.baseline                # detect-secrets baseline
│
├── config/
│   ├── default.yaml                 # ВСЕ параметры (см §4)
│   └── schema.py                    # pydantic AppConfig модель
│
├── src/
│   ├── __init__.py
│   ├── main.py                      # asyncio entry point
│   │
│   ├── market_data/
│   │   ├── collector.py             # Binance WS kline_1h subscriber
│   │   ├── ring_buffer.py           # deque(maxlen=1000) wrapper
│   │   ├── gap_detector.py          # gap/stale/duplicate rules
│   │   └── models.py                # Bar, DataQuality pydantic models
│   │
│   ├── indicators/
│   │   ├── ema.py                   # Classical EMA α=2/(n+1)
│   │   ├── wilder.py                # Wilder EMA → ADX, RSI, ATR
│   │   └── registry.py              # IndicatorEngine: feeds bars → state dict
│   │
│   ├── signals/
│   │   ├── crossover.py             # EMA cross + ADX + RSI → Signal
│   │   ├── models.py                # Signal, ReasonCode enum (28 кодов)
│   │   └── deduplicator.py          # одна позиция на бар
│   │
│   ├── risk/
│   │   ├── position_sizer.py        # 4-phase Kelly
│   │   ├── circuit_breaker.py       # L1/L2/L3/flash
│   │   └── filter_validator.py      # LOT_SIZE, PRICE_FILTER, NOTIONAL
│   │
│   ├── execution/
│   │   ├── binance_client.py        # REST: HMAC auth, retry, weight tracking
│   │   ├── order_manager.py         # Order aggregate lifecycle
│   │   ├── oco_manager.py           # OCO bracket + partial fill handler
│   │   ├── ws_user_data.py          # executionReport WS stream
│   │   └── models.py                # Order, Fill, Position pydantic
│   │
│   ├── state/
│   │   ├── machine.py               # 12-state FSM (Harel statecharts)
│   │   ├── recovery.py              # boot reconciliation vs Binance
│   │   └── repositories.py          # SQLite CRUD: orders/fills/positions
│   │
│   ├── storage/
│   │   ├── sqlite.py                # WAL connection pool, migrations
│   │   ├── parquet_writer.py        # OHLCV append, snappy compression
│   │   └── audit_log.py             # JSONL tamper-chain
│   │
│   ├── analytics/
│   │   ├── metrics.py               # Sharpe, Sortino, MaxDD, WinRate
│   │   └── reason_codes.py          # 28 ReasonCode + JSON schema
│   │
│   ├── backtest/
│   │   ├── engine.py                # event-driven bar replay
│   │   ├── walk_forward.py          # rolling WF train=2000/test=500/K=5
│   │   ├── mc_permutation.py        # sign-flip N=2000, p-value
│   │   └── lookahead_detector.py    # O(n²) future-bar poison test
│   │
│   ├── dashboard/
│   │   ├── app.py                   # Streamlit entry
│   │   └── pages/
│   │       ├── live.py              # equity curve, positions, P&L
│   │       ├── trades.py            # trade log + reason codes
│   │       ├── backtest.py          # on-demand backtest runner
│   │       └── config_editor.py     # YAML config editor с diff
│   │
│   └── infra/
│       ├── clock.py                 # chrony drift monitor
│       ├── rate_limiter.py          # token bucket per Binance bucket
│       ├── healthcheck.py           # dead-man's switch ping
│       └── config_reload.py         # SIGHUP hot-reload handler
│
├── tests/
│   ├── conftest.py                  # fixtures: mock_ws, sample_bars, config
│   ├── unit/                        # pytest -m unit
│   ├── property/                    # pytest -m property (hypothesis)
│   ├── integration/                 # pytest -m integration
│   └── edge_cases/                  # pytest -m edge_case
│
├── scripts/
│   ├── fetch_binance_history.py     # ETL: klines API pagination → Parquet
│   ├── lookahead_detector.py        # standalone CI gate
│   └── db_migrate.py                # SQLite schema migrations
│
└── data/
    ├── fixtures/                    # test CSV/Parquet (5 лет BTC 1H)
    └── schema/                      # JSON Schema для audit log
```

---

## 2. Спринты — порядок реализации

### Спринт 1: Foundation
**Зависит от:** ничего
**Результат:** `make test-unit` green, конфиг грузится, SQLite инициализируется

**Модули:**
- `config/schema.py` — pydantic AppConfig с валидацией всех секций
- `config/default.yaml` — полный YAML (см §4)
- `src/storage/sqlite.py` — WAL connection pool + migrations
- `src/storage/audit_log.py` — JSONL append + tamper chain
- `src/market_data/models.py` — Bar, DataQuality pydantic models
- `src/execution/models.py` — Order, Fill, Position pydantic models

**Done criteria:**
```bash
python -c "from config.schema import load_config; cfg = load_config(); print('OK')"
python -c "from src.storage.sqlite import init_db; import asyncio; asyncio.run(init_db())"
pytest tests/unit/test_config.py tests/unit/test_storage.py -v  # ALL PASS
```

---

### Спринт 2: Market Data Pipeline
**Зависит от:** Спринт 1
**Результат:** Можно подключиться к Binance Testnet WS и видеть бары в логах

**Модули:**
- `src/market_data/collector.py` — WS kline subscriber
- `src/market_data/ring_buffer.py` — deque wrapper
- `src/market_data/gap_detector.py` — gap/duplicate/stale rules
- `src/infra/rate_limiter.py` — token bucket
- `src/infra/clock.py` — drift monitor
- `scripts/fetch_binance_history.py` — ETL для истории

**Done criteria:**
```bash
pytest tests/unit/test_ring_buffer.py tests/unit/test_gap_detector.py -v
pytest tests/integration/test_ws_collector.py -v  # mock WS
python scripts/fetch_binance_history.py --symbol BTCUSDT --interval 1h --years 5
# → data/fixtures/btcusdt_1h_5y.parquet создан
```

---

### Спринт 3: Indicators
**Зависит от:** Спринт 2
**Результат:** Все индикаторы верифицированы против TA-Lib reference values

**Модули:**
- `src/indicators/ema.py` — Classical EMA
- `src/indicators/wilder.py` — Wilder EMA, ATR, RSI, ADX, +DI, -DI
- `src/indicators/registry.py` — IndicatorEngine

**Done criteria:**
```bash
pytest tests/unit/test_ema.py tests/unit/test_wilder.py -v
# Все значения совпадают с TA-Lib до 6 знаков после запятой
pytest tests/property/test_ohlc_invariant.py -v  # hypothesis
```

---

### Спринт 4: Signals
**Зависит от:** Спринт 3
**Результат:** На тестовых данных сигналы генерируются корректно, без look-ahead

**Модули:**
- `src/signals/models.py` — Signal, ReasonCode enum
- `src/signals/crossover.py` — стратегия
- `src/signals/deduplicator.py`
- `src/analytics/reason_codes.py`

**Done criteria:**
```bash
pytest tests/unit/test_signal_crossover.py tests/unit/test_deduplicator.py -v
python scripts/lookahead_detector.py --data data/fixtures/btcusdt_1h_5y.parquet
# → "0 look-ahead violations detected"
```

---

### Спринт 5: Risk Management
**Зависит от:** Спринт 4
**Результат:** Все фазы Kelly работают, CB корректно переходит в HALT

**Модули:**
- `src/risk/position_sizer.py` — 4-phase Kelly
- `src/risk/circuit_breaker.py` — L1/L2/L3/flash
- `src/risk/filter_validator.py` — pre-trade Binance filters

**Done criteria:**
```bash
pytest tests/unit/test_position_sizer.py tests/unit/test_circuit_breaker.py -v
pytest tests/edge_cases/test_flash_crash.py -v
```

---

### Спринт 6: Execution
**Зависит от:** Спринт 5
**Результат:** OCO ордер успешно размещается в Binance Testnet

**Модули:**
- `src/execution/binance_client.py`
- `src/execution/order_manager.py`
- `src/execution/oco_manager.py`
- `src/execution/ws_user_data.py`

**Done criteria:**
```bash
pytest tests/unit/test_order_manager.py tests/unit/test_oco_manager.py -v
pytest tests/edge_cases/test_partial_fill_oco.py -v
# В Testnet: place + cancel OCO, verify idempotency via clientOrderId
```

---

### Спринт 7: State Machine + Recovery
**Зависит от:** Спринт 6
**Результат:** Полный happy-path цикл в paper mode

**Модули:**
- `src/state/machine.py` — 12 состояний
- `src/state/recovery.py` — boot reconciliation
- `src/state/repositories.py` — SQLite CRUD

**Done criteria:**
```bash
pytest tests/unit/test_state_machine.py -v
pytest tests/edge_cases/test_server_crash_recovery.py -v
pytest tests/integration/test_full_pipeline.py -v
# → bar → indicator → signal → risk → mock_exec → FILLED → position записана
```

---

### Спринт 8: Backtest Engine
**Зависит от:** Спринт 7
**Результат:** Walk-Forward на 5 годах BTC 1H, отчёт с DSR

**Модули:**
- `src/backtest/engine.py`
- `src/backtest/walk_forward.py`
- `src/backtest/mc_permutation.py`
- `src/backtest/lookahead_detector.py`

**Done criteria:**
```bash
pytest tests/integration/test_backtest_regression.py -v
# PnL на fixture совпадает до копейки с baseline
python -m src.backtest.walk_forward --data data/fixtures/btcusdt_1h_5y.parquet
# → WF report: OOS Sharpe, DSR, MC p-value
```

---

### Спринт 9: Analytics + Dashboard
**Зависит от:** Спринт 8

**Модули:**
- `src/analytics/metrics.py`
- `src/dashboard/app.py` и pages/

**Done criteria:**
```bash
pytest tests/unit/test_metrics.py -v
streamlit run src/dashboard/app.py  # открывается, equity curve отображается
```

---

### Спринт 10: CI/CD + Integration
**Зависит от:** Спринт 9

**Done criteria:**
```bash
docker build -t algo-bot:v0.1 .  # build succeeds
docker-compose up -d             # bot starts, logs flow
pytest tests/ -v --cov=src --cov-report=term  # coverage ≥ 80%
# GitHub Actions CI: all jobs green on PR
```

---

## 3. Модульные спецификации

### `config/schema.py`

**Назначение:** pydantic v2 модель для валидации `default.yaml`. Единственный источник правды о допустимых значениях всех параметров.

**Вход:** dict из YAML-файла

**Выход:** `AppConfig` — typed pydantic model, frozen=True

**Логика:**
```python
from pydantic import BaseModel, Field, model_validator
from pathlib import Path
import yaml

class StrategyConfig(BaseModel):
    ema_fast: int = Field(20, ge=5, le=200)
    ema_slow: int = Field(50, ge=10, le=500)
    adx_period: int = Field(14, ge=5, le=50)
    adx_threshold: float = Field(25.0, ge=10.0, le=50.0)
    rsi_period: int = Field(14, ge=5, le=50)
    rsi_overbought: float = Field(70.0, ge=60.0, le=90.0)
    rsi_oversold: float = Field(30.0, ge=10.0, le=40.0)

    @model_validator(mode='after')
    def ema_slow_gt_fast(self) -> 'StrategyConfig':
        if self.ema_slow <= self.ema_fast:
            raise ValueError("ema_slow must be > ema_fast")
        return self

class RiskConfig(BaseModel):
    kelly_phase_thresholds: list[int] = Field([30, 100, 200])
    fixed_fraction_phase0: float = Field(0.01, ge=0.001, le=0.05)
    fixed_fraction_phase1: float = Field(0.02, ge=0.001, le=0.05)
    quarter_kelly_cap: float = Field(0.03, ge=0.01, le=0.10)
    half_kelly_cap: float = Field(0.05, ge=0.01, le=0.15)
    cb_l1_pct: float = Field(0.15, ge=0.05, le=0.30)
    cb_l2_pct: float = Field(0.22, ge=0.10, le=0.40)
    cb_l3_pct: float = Field(0.30, ge=0.15, le=0.50)
    flash_crash_pct: float = Field(0.08, ge=0.03, le=0.20)
    flash_crash_atr_mult: float = Field(3.0, ge=1.0, le=10.0)

# ... BacktestConfig, ExecutionConfig, StorageConfig, InfraConfig

class AppConfig(BaseModel, frozen=True):
    strategy: StrategyConfig
    risk: RiskConfig
    execution: ExecutionConfig
    backtest: BacktestConfig
    storage: StorageConfig
    infra: InfraConfig
    dashboard: DashboardConfig

def load_config(path: str = "config/default.yaml") -> AppConfig:
    with open(path) as f:
        raw = yaml.safe_load(f)
    return AppConfig.model_validate(raw)
```

**Edge cases:**
1. `ema_slow <= ema_fast` → `ValueError` с явным сообщением "ema_slow must be > ema_fast"
2. YAML файл не найден → `FileNotFoundError` с путём
3. Числа вне диапазона → pydantic `ValidationError` с полем и диапазоном

**Запреты:**
- Не читать переменные среды напрямую (использовать `.env` через python-dotenv в `main.py`)
- Не мутировать конфиг после загрузки (frozen=True)

**Тесты:** `tests/unit/test_config.py`
- `test_valid_config_loads` — default.yaml грузится без ошибок
- `test_ema_slow_must_exceed_fast` — ema_slow=10, ema_fast=20 → ValidationError
- `test_all_magic_numbers_in_yaml` — проверить что ни одного float/int константы нет в src/ через grep

---

### `src/market_data/models.py`

**Назначение:** pydantic domain models для рыночных данных.

**Модели:**
```python
from enum import Enum
from pydantic import BaseModel, field_validator
from datetime import datetime

class DataQuality(str, Enum):
    OK = "OK"
    GAP = "GAP"           # missing bar(s) before this
    STALE = "STALE"       # bar arrived late
    SUSPECT = "SUSPECT"   # OHLC invariant warning

class Bar(BaseModel, frozen=True):
    symbol: str
    interval: str                     # "1h"
    open_time: datetime               # UTC, tz-aware
    close_time: datetime              # UTC, tz-aware
    open: float
    high: float
    low: float
    close: float
    volume: float
    trade_count: int
    closed: bool                      # True только когда бар закрыт
    data_quality: DataQuality = DataQuality.OK

    @field_validator('high')
    @classmethod
    def high_ge_low(cls, v, info):
        # называется автоматически pydantic при валидации
        return v  # полную проверку делает model_validator below

    @model_validator(mode='after')
    def ohlc_invariant(self) -> 'Bar':
        """low <= min(open,close) <= max(open,close) <= high"""
        if not (self.low <= min(self.open, self.close)
                <= max(self.open, self.close) <= self.high):
            raise ValueError(
                f"OHLC invariant violated: O={self.open} H={self.high} "
                f"L={self.low} C={self.close}"
            )
        if self.volume < 0:
            raise ValueError(f"Negative volume: {self.volume}")
        return self
```

**Тесты:** `tests/property/test_ohlc_invariant.py`
- `test_ohlc_invariant_valid` — корректные данные проходят
- `test_ohlc_invariant_violated` — H < C → ValidationError
- `test_negative_volume_rejected` — volume=-1 → ValidationError
- `test_bar_is_immutable` — попытка мутации → TypeError (frozen=True)

---

### `src/market_data/collector.py`

**Назначение:** Подписка на Binance WS `kline_1h` stream, парсинг событий, публикация закрытых баров в asyncio.Queue.

**Вход:** config: AppConfig, queue: asyncio.Queue[Bar]

**Выход:** Публикует `Bar` (только `closed=True`) в queue

**Логика:**
```python
WS_URL = "wss://testnet.binance.vision/ws/{symbol}@kline_{interval}"

async def run_collector(cfg: AppConfig, queue: asyncio.Queue) -> None:
    url = WS_URL.format(
        symbol=cfg.strategy.symbol.lower(),
        interval=cfg.strategy.interval
    )
    backoff = ExponentialBackoff(base=1.0, max_delay=60.0, jitter=True)

    while True:  # reconnect loop
        try:
            async with websockets.connect(url, ping_interval=20) as ws:
                backoff.reset()
                logger.info("ws_connected", url=url)
                async for raw_msg in ws:
                    bar = _parse_kline_message(raw_msg)
                    if bar is None:
                        continue
                    if bar.closed:  # КРИТИЧНО: только закрытые бары
                        await queue.put(bar)
                        logger.info("bar_published", close_time=bar.close_time)

        except websockets.ConnectionClosed as e:
            delay = backoff.next()
            logger.warning("ws_disconnected", code=e.code, delay=delay)
            await asyncio.sleep(delay)
            # После 3 reconnect за 60s → RECONNECT state (через event)
        except Exception as e:
            logger.error("ws_unexpected_error", exc_info=True)
            await asyncio.sleep(backoff.next())
```

**Парсинг Binance kline message:**
```python
def _parse_kline_message(raw: str) -> Bar | None:
    data = json.loads(raw)
    if data.get("e") != "kline":
        return None
    k = data["k"]
    return Bar(
        symbol=k["s"],
        interval=k["i"],
        open_time=datetime.fromtimestamp(k["t"]/1000, tz=timezone.utc),
        close_time=datetime.fromtimestamp(k["T"]/1000, tz=timezone.utc),
        open=float(k["o"]), high=float(k["h"]),
        low=float(k["l"]),  close=float(k["c"]),
        volume=float(k["v"]), trade_count=k["n"],
        closed=k["x"],  # True = bar is closed
    )
```

**Edge cases:**
1. WS disconnect → exponential backoff 1s→2s→4s…→60s, jitter ±10%
2. 3 reconnect попытки за 60s → emit `WebSocketReconnect` event → state machine переходит в RECONNECT
3. Invalid JSON → log error, skip message, не падать
4. Non-kline message (ping/pong, subscribe response) → skip gracefully

**Запреты:**
- НЕ публиковать бары с `closed=False` (intra-bar ticks)
- НЕ делать reconnect с новым WS URL без изменения конфига
- НЕ блокировать event loop синхронными операциями

**Тесты:** `tests/integration/test_ws_collector.py`
- `test_only_closed_bars_published` — mock WS отправляет open и closed bars → в queue только closed
- `test_reconnect_on_disconnect` — mock WS закрывается → collector reconnects
- `test_invalid_json_skipped` — invalid JSON → no exception, no item in queue

---

### `src/market_data/gap_detector.py`

**Назначение:** Проверка последовательности баров на gap, дубли, stale данные.

**Логика:**
```python
class GapDetector:
    def __init__(self, interval_seconds: int = 3600):
        self._interval = interval_seconds
        self._last_close_time: datetime | None = None
        self._consecutive_gaps = 0

    def check(self, bar: Bar) -> Bar:
        """Returns bar (possibly with updated data_quality), raises GapError if critical."""
        if self._last_close_time is None:
            self._last_close_time = bar.close_time
            return bar

        expected = self._last_close_time + timedelta(seconds=self._interval)
        delta = (bar.open_time - self._last_close_time).total_seconds()

        # Duplicate
        if bar.open_time <= self._last_close_time:
            raise DuplicateBarError(bar.open_time)

        # Gap
        if abs(delta - self._interval) > 5:  # 5s tolerance
            self._consecutive_gaps += 1
            bar = bar.model_copy(update={"data_quality": DataQuality.GAP})
            if self._consecutive_gaps >= 3:
                raise CriticalGapError(self._consecutive_gaps)
        else:
            self._consecutive_gaps = 0

        self._last_close_time = bar.close_time
        return bar
```

**Edge cases:**
1. Missing 1 bar → DataQuality.GAP, consecutive_gaps=1, продолжаем
2. Missing 3+ bars → `CriticalGapError` → HALT_DATA_QUALITY state
3. Duplicate timestamp → `DuplicateBarError` → log + skip (не в queue)
4. Stale bar (arrived > 1.5 * interval late) → DataQuality.STALE, не блокируем
5. Volume=0 → DataQuality оставляем OK (valid для thin market, volume-filter downstream)

**Запреты:**
- НЕ делать forward-fill OHLC для GAP баров
- НЕ генерировать сигналы на барах с DataQuality != OK (проверка в crossover.py)

---

### `src/indicators/ema.py`

**Назначение:** Classical Exponential Moving Average. Используется ТОЛЬКО для EMA crossover сигнала.

**Формула:** `α = 2 / (period + 1)`, `EMA(t) = α × price(t) + (1 − α) × EMA(t−1)`

**Для period=20:** `α = 2/21 ≈ 0.09524`
**Для period=50:** `α = 2/51 ≈ 0.03922`

```python
class ClassicalEMA:
    """Classical EMA: alpha = 2 / (period + 1).
    Used for crossover signals only.
    Wilder-smoothed variants (ADX, RSI, ATR) are in wilder.py.
    """
    def __init__(self, period: int) -> None:
        if period < 1:
            raise ValueError(f"period must be >= 1, got {period}")
        self.period = period
        self.alpha: float = 2.0 / (period + 1)
        self._value: float | None = None
        self._bars_seen: int = 0

    def update(self, price: float) -> float | None:
        """Feed one price. Returns current EMA or None if not yet initialized."""
        self._bars_seen += 1
        if self._value is None:
            self._value = price  # first bar: seed with price
        else:
            self._value = self.alpha * price + (1.0 - self.alpha) * self._value
        return self._value

    @property
    def value(self) -> float | None:
        return self._value

    @property
    def is_ready(self) -> bool:
        # EMA technically usable from bar 1, but 2*period bars for stability
        return self._bars_seen >= 2 * self.period
```

**Верификация против TA-Lib:**
```python
# В тесте:
import talib
import numpy as np
closes = np.array([...])  # 200 цен BTC
talib_ema = talib.EMA(closes, timeperiod=20)
our_ema = [ema.update(p) for p in closes]
# Должны совпадать до 1e-6 начиная с бара 20
```

**Edge cases:**
1. `period=0` → ValueError немедленно
2. Первый бар → value = price (seed), is_ready=False
3. `price=NaN` или `price=inf` → `ValueError("invalid price")`
4. Многократный update одинаковой ценой → EMA сходится к этой цене

**Запреты:**
- НЕ использовать для ADX/RSI/ATR (там нужен Wilder α=1/n)
- НЕ хранить историю всех цен (O(1) памяти)

**Тесты:** `tests/unit/test_ema.py`
- `test_ema_matches_talib_period20` — 200 баров, ошибка < 1e-6
- `test_ema_matches_talib_period50` — аналогично
- `test_ema_seed_on_first_bar` — первый update возвращает price
- `test_ema_convergence` — 100 баров одинаковой цены → EMA = price ± epsilon
- `test_ema_invalid_period` — period=0 → ValueError
- `test_ema_nan_price_raises` — NaN → ValueError

---

### `src/indicators/wilder.py`

**Назначение:** Wilder Exponential Moving Average и все индикаторы на её основе: ATR, RSI, ADX.

**Формула Wilder EMA:** `α = 1 / period`, `WiMA(t) = α × value(t) + (1 − α) × WiMA(t−1)`
**Для period=14:** `α = 1/14 ≈ 0.07143`

**ATR (Average True Range):**
```
TR(t) = max(
    high(t) - low(t),
    |high(t) - close(t-1)|,
    |low(t) - close(t-1)|
)
ATR(t) = WilderEMA(TR(t), period=14)
```
Первые 14 баров: ATR = SMA(TR, 14). Затем Wilder smoothing.

**RSI (Relative Strength Index):**
```
gain(t) = max(close(t) - close(t-1), 0)
loss(t) = max(close(t-1) - close(t), 0)

# Период warmup (первые period bars):
avg_gain = mean(gains[0..period])
avg_loss = mean(losses[0..period])

# После warmup (Wilder smoothing):
avg_gain = (prev_avg_gain * (period-1) + gain) / period
avg_loss = (prev_avg_loss * (period-1) + loss) / period

RS = avg_gain / avg_loss  (if avg_loss == 0: RSI = 100)
RSI = 100 - 100 / (1 + RS)
```

**ADX (Average Directional Index):**
```
+DM(t) = max(high(t) - high(t-1), 0) if > max(low(t-1) - low(t), 0) else 0
-DM(t) = max(low(t-1) - low(t), 0) if > max(high(t) - high(t-1), 0) else 0

+DI = 100 * WilderEMA(+DM, 14) / ATR
-DI = 100 * WilderEMA(-DM, 14) / ATR

DX = 100 * |+DI - -DI| / (+DI + -DI)  (if +DI + -DI == 0: DX = 0)
ADX = WilderEMA(DX, 14)
```

**Запреты:**
- НЕ использовать Classical alpha=2/(n+1) для этих индикаторов
- НЕ делать деление на ноль (защита через `if denom == 0: return 0.0`)
- ATR НЕ должен быть 0 (если 0 → log warning, вернуть last valid ATR)

**Тесты:**
- `test_atr_matches_talib` — 200 баров, ошибка < 1e-6
- `test_rsi_matches_talib` — 200 баров, ошибка < 1e-6
- `test_adx_matches_talib` — 200 баров, ошибка < 1e-6
- `test_rsi_zero_loss_returns_100` — все positive returns → RSI = 100
- `test_atr_nonzero_for_valid_data` — корректные OHLC → ATR > 0

---

### `src/signals/crossover.py`

**Назначение:** Генерация сигнала на основе EMA crossover + ADX фильтр + RSI подтверждение.

**Вход:** закрытый Bar + состояние IndicatorRegistry

**Выход:** `Signal | None`

**Алгоритм:**
```python
def generate_signal(bar: Bar, indicators: IndicatorState, cfg: StrategyConfig) -> Signal | None:
    # Guard: только закрытые бары
    assert bar.closed, "BUG: signal generation on open bar (look-ahead!)"
    assert bar.data_quality == DataQuality.OK, f"Skipping bar: {bar.data_quality}"

    ema_fast = indicators.ema_fast
    ema_slow = indicators.ema_slow
    ema_fast_prev = indicators.ema_fast_prev
    ema_slow_prev = indicators.ema_slow_prev

    # Primary: EMA crossover
    cross_up   = ema_fast_prev <= ema_slow_prev and ema_fast > ema_slow
    cross_down = ema_fast_prev >= ema_slow_prev and ema_fast < ema_slow

    if not (cross_up or cross_down):
        return None  # NO_SIGNAL

    # Filter 1: ADX trend strength
    if indicators.adx < cfg.adx_threshold:
        return Signal(
            side=Side.FLAT,
            reason=ReasonCode.REJECT_ADX_BELOW_THRESHOLD,
            bar_ref=bar,
        )

    # Filter 2: RSI confirmation (не торговать в перекупленность/перепроданность)
    if cross_up and indicators.rsi >= cfg.rsi_overbought:
        return Signal(side=Side.FLAT, reason=ReasonCode.REJECT_RSI_OVERBOUGHT, bar_ref=bar)
    if cross_down and indicators.rsi <= cfg.rsi_oversold:
        return Signal(side=Side.FLAT, reason=ReasonCode.REJECT_RSI_OVERSOLD, bar_ref=bar)

    side = Side.LONG if cross_up else Side.SHORT
    reason = ReasonCode.ENTRY_LONG_TREND_FOLLOWING if side == Side.LONG \
             else ReasonCode.ENTRY_SHORT_TREND_FOLLOWING

    return Signal(
        side=side,
        reason=reason,
        bar_ref=bar,
        confidence=_compute_confidence(indicators, cfg),
        ema_fast=ema_fast,
        ema_slow=ema_slow,
        adx=indicators.adx,
        rsi=indicators.rsi,
        atr=indicators.atr,
    )
```

**Запреты:**
- НЕ генерировать сигнал на `bar.closed=False`
- НЕ генерировать сигнал на `DataQuality != OK`
- НЕ хранить состояние между барами (stateless function, состояние в IndicatorRegistry)

---

### `src/risk/position_sizer.py`

**Назначение:** 4-phase Kelly position sizing.

**Формулы:**
```
f* = (p * b - q) / b     # Kelly fraction
  где p = win_rate, q = 1 - p, b = avg_win / avg_loss

Phase 0 (n < 30):   size = fixed_fraction_phase0 = 0.01
Phase 1 (n < 100):  size = fixed_fraction_phase1 = 0.02
Phase 2 (n < 200):  size = min(f*/4, quarter_kelly_cap) = min(f*/4, 0.03)
Phase 3 (n >= 200): size = min(f*/2, half_kelly_cap)   = min(f*/2, 0.05)

position_qty = (equity * size) / sl_distance_price
```

**Расчёт SL distance:**
```
sl_distance_price = atr * k_sl  # k_sl = 2.0 long, 1.5 short (из конфига)
min_sl = max(2 * atr, 0.005 * entry_price)  # минимальный SL
```

**Edge cases:**
1. `n_trades < 30` → Phase 0, Kelly не вычисляется
2. `f* <= 0` (отрицательный edge) → `ReasonCode.REJECT_KELLY_ZERO`, size=0, no trade
3. `avg_loss == 0` (все wins) → cap размер на Phase maximum
4. `sl_distance == 0` (ATR == 0) → log warning, no trade (`REJECT_ATR_ZERO`)
5. `position_qty * entry_price < min_notional` → `REJECT_MIN_NOTIONAL`

**Тесты:**
- `test_phase0_returns_fixed_fraction` — n=10 → size=0.01
- `test_phase3_kelly_formula` — n=250, p=0.6, b=2.0 → f*=(0.6*2-0.4)/2=0.4, half=0.2, cap=0.05
- `test_negative_kelly_no_trade` — p=0.4, b=1.0 → f*<0 → size=0
- `test_sl_distance_zero_no_trade` — atr=0 → no trade

---

### `src/risk/circuit_breaker.py`

**Назначение:** Многоуровневый circuit breaker. Мониторит equity drawdown, принимает решение о halt.

```python
class CircuitBreaker:
    def __init__(self, cfg: RiskConfig):
        self._high_water_mark: float | None = None
        self._cfg = cfg

    def update(self, equity: float, last_bar_return: float) -> CBDecision:
        """Returns CBDecision: OK | WARN | HALT_L2 | HALT_L3 | HALT_FLASH"""
        # Update HWM
        if self._high_water_mark is None or equity > self._high_water_mark:
            self._high_water_mark = equity

        dd = (self._high_water_mark - equity) / self._high_water_mark

        # Flash crash check (bar-level, close-to-close)
        flash_threshold = max(
            self._cfg.flash_crash_pct,
            self._cfg.flash_crash_atr_mult * last_bar_atr_pct
        )
        if abs(last_bar_return) >= flash_threshold:
            return CBDecision(level=CBLevel.HALT_FLASH,
                              reason=ReasonCode.HALT_FLASH_CRASH, dd=dd)

        if dd >= self._cfg.cb_l3_pct:
            return CBDecision(level=CBLevel.HALT_L3,
                              reason=ReasonCode.HALT_DRAWDOWN_L3, dd=dd)
        if dd >= self._cfg.cb_l2_pct:
            return CBDecision(level=CBLevel.HALT_L2,
                              reason=ReasonCode.HALT_DRAWDOWN_L2, dd=dd)
        if dd >= self._cfg.cb_l1_pct:
            return CBDecision(level=CBLevel.WARN_L1,
                              reason=ReasonCode.HALT_DRAWDOWN_L1, dd=dd)
        return CBDecision(level=CBLevel.OK, reason=None, dd=dd)
```

**Drawdown считается от 24h high-water mark equity (не от session start).**

**Edge cases:**
1. First call → HWM = equity, dd=0 → OK
2. Flash crash: `|bar_return| > max(8%, 3*ATR)` → HALT_FLASH, cancel all, flatten
3. dd=22% → HALT_L2 (не L3), потому что `22 >= 22 and 22 < 30`
4. Recovery после L2: HWM не сбрасывается автоматически (ручной resume)

**Тесты:**
- `test_no_drawdown_ok`
- `test_l1_warn_at_15pct`
- `test_l2_halt_at_22pct`
- `test_l3_halt_at_30pct`
- `test_flash_crash_triggers_halt`
- `test_hwm_updates_on_new_equity_high`

---

### `src/execution/binance_client.py`

**Назначение:** REST API клиент Binance с HMAC auth, rate-limit tracking, retry.

```python
class BinanceClient:
    BASE_URL = "https://testnet.binance.vision"  # testnet для v0.1

    def __init__(self, api_key: str, secret: str, rate_limiter: RateLimiter):
        self._key = api_key
        self._secret = secret.encode()
        self._rl = rate_limiter
        self._session: aiohttp.ClientSession | None = None

    async def place_oco_order(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Decimal,        # limit price (TP leg)
        stop_price: Decimal,   # SL trigger
        stop_limit_price: Decimal,
        client_order_id: str,  # idempotency key
    ) -> dict:
        params = {
            "symbol": symbol,
            "side": side,
            "quantity": str(quantity),
            "price": str(price),
            "stopPrice": str(stop_price),
            "stopLimitPrice": str(stop_limit_price),
            "stopLimitTimeInForce": "GTC",
            "listClientOrderId": client_order_id,
            "timestamp": _timestamp_ms(),
            "recvWindow": 5000,
        }
        return await self._signed_post("/api/v3/orderList/oco", params)

    async def _signed_post(self, path: str, params: dict) -> dict:
        await self._rl.acquire(weight=2)  # OCO = 2 weight
        query = urlencode(params)
        sig = hmac.new(self._secret, query.encode(), hashlib.sha256).hexdigest()
        url = f"{self.BASE_URL}{path}?{query}&signature={sig}"

        for attempt in range(self._max_retries):
            try:
                async with self._session.post(
                    url, headers={"X-MBX-APIKEY": self._key}, timeout=10
                ) as resp:
                    self._rl.update_from_headers(resp.headers)

                    if resp.status == 200:
                        return await resp.json()
                    elif resp.status == 429:
                        raise RateLimitError(retry_after=int(resp.headers.get("Retry-After", 60)))
                    elif resp.status == 418:
                        raise IPBanError()  # do not retry
                    elif resp.status >= 500:
                        # CRITICAL: do NOT retry with new clientOrderId
                        # Instead query existing order state
                        raise ServerError(resp.status, await resp.text())
                    else:
                        body = await resp.json()
                        raise BinanceAPIError(body.get("code"), body.get("msg"))
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt == self._max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)
```

**Идемпотентность: `clientOrderId` формат:**
```python
def make_client_order_id(strategy_id: str, bar_close_epoch: int) -> str:
    suffix = uuid.uuid4().hex[:8]
    return f"{strategy_id}-{bar_close_epoch}-{suffix}"[:36]  # Binance max 36 chars
```

**Edge cases:**
1. HTTP 429 → `RateLimitError`, honor `Retry-After`, не превышать лимит
2. HTTP 418 → `IPBanError`, немедленный HALT (не retry)
3. HTTP 5xx → НЕ retry с новым clientOrderId, query существующий ордер через `GET /api/v3/order?origClientOrderId=X`
4. `-2010 INSUFFICIENT_BALANCE` → `ReasonCode.REJECT_INSUFFICIENT_BALANCE`, no trade
5. `-1021 TIMESTAMP` → `ClockDriftError` → CLOCK_DRIFT state

---

### `src/state/machine.py`

**Назначение:** 12-state Harel statechart machine с orthogonal watchdog regions.

**Состояния:**
```python
class BotState(str, Enum):
    IDLE = "IDLE"
    ANALYZE = "ANALYZE"
    SIGNAL = "SIGNAL"
    RISK_CHK = "RISK_CHK"
    EXECUTE_SUBMITTING = "EXECUTE_SUBMITTING"
    EXECUTE_WORKING = "EXECUTE_WORKING"
    EXECUTE_PARTIAL = "EXECUTE_PARTIAL"
    EXECUTE_CANCELLING = "EXECUTE_CANCELLING"
    MONITOR = "MONITOR"
    HALT = "HALT"
    RECONNECT = "RECONNECT"
    STALE_DATA = "STALE_DATA"
    CLOCK_DRIFT = "CLOCK_DRIFT"
    RATE_LIMITED = "RATE_LIMITED"
```

**Переходы (ключевые):**
```
IDLE           --[NewBar]--------------> ANALYZE
ANALYZE        --[IndicatorsReady]------> SIGNAL
SIGNAL         --[SignalGenerated]-------> RISK_CHK
SIGNAL         --[NoSignal]-------------> IDLE
RISK_CHK       --[RiskApproved]----------> EXECUTE_SUBMITTING
RISK_CHK       --[RiskRejected]----------> IDLE
EXECUTE_SUBMITTING --[OrderAck]----------> EXECUTE_WORKING
EXECUTE_WORKING    --[FILLED]------------> MONITOR
EXECUTE_WORKING    --[PARTIAL_FILL]-------> EXECUTE_PARTIAL
EXECUTE_PARTIAL    --[FillTimeout 60s]---> EXECUTE_CANCELLING
EXECUTE_CANCELLING --[CancelAck]----------> IDLE
MONITOR        --[OCOTriggered]----------> IDLE

# Orthogonal (из ЛЮБОГО состояния кроме HALT/RECONNECT):
ANY            --[WSDisconnect]----------> RECONNECT
ANY            --[NoBarFor2*period]------> STALE_DATA
ANY            --[CircuitBreaker]---------> HALT
ANY            --[ClockDrift>1s]----------> CLOCK_DRIFT
ANY            --[HTTP418 IPBan]-----------> HALT
```

**Запреты:**
- НЕ допускать переход ANALYZE→EXECUTE напрямую (нужно RISK_CHK)
- НЕ автоматически выходить из HALT (только ручной resume)
- НЕ размещать новые ордера в любом EXECUTE_* состоянии

---

### `src/backtest/engine.py`

**Назначение:** Event-driven backtesting engine. Воспроизводит бары из Parquet, прогоняет через полный pipeline.

```python
class BacktestEngine:
    """Event-driven replay backtester.

    Invariant: signal computed on bar[t].close,
               fill simulated at bar[t+1].open + slippage.
    """

    def run(self, bars: list[Bar], cfg: AppConfig) -> BacktestResult:
        indicators = IndicatorRegistry(cfg)
        position_sizer = PositionSizer(cfg.risk)
        circuit_breaker = CircuitBreaker(cfg.risk)
        equity = initial_capital = 10_000.0
        trades: list[Trade] = []
        open_position: Position | None = None
        high_water_mark = equity

        for i, bar in enumerate(bars):
            assert bar.closed, f"BUG: open bar at index {i}"

            indicators.update(bar)
            if not indicators.is_ready:
                continue

            # Check if open position hit SL/TP
            if open_position is not None:
                exit_result = _simulate_exit(open_position, bar, cfg)
                if exit_result is not None:
                    equity += exit_result.pnl
                    trades.append(exit_result)
                    open_position = None

            # Check circuit breaker
            cb = circuit_breaker.update(equity, bar)
            if cb.level != CBLevel.OK:
                # Record halt event, no new entries
                continue

            # Generate signal on CLOSED bar
            signal = generate_signal(bar, indicators.state, cfg.strategy)
            if signal is None or signal.side == Side.FLAT:
                continue

            # Risk: position size
            n_trades = len(trades)
            size = position_sizer.compute(
                equity=equity, n_trades=n_trades,
                atr=indicators.state.atr,
                entry=bar.close, side=signal.side,
            )
            if size.qty == 0:
                continue

            # Fill at NEXT bar open (look-ahead protection)
            if i + 1 >= len(bars):
                break
            next_bar = bars[i + 1]
            fill_price = _simulate_fill(next_bar.open, signal.side, cfg.execution)

            open_position = Position(
                entry_price=fill_price,
                entry_time=next_bar.open_time,
                qty=size.qty,
                side=signal.side,
                sl_price=size.sl_price,
                tp_price=size.tp_price,
                reason=signal.reason,
            )

        return BacktestResult(trades=trades, equity_curve=..., config_hash=...)
```

**Параметры slippage в бэктесте:**
```python
def _simulate_fill(open_price: float, side: Side, cfg: ExecutionConfig) -> float:
    slip = cfg.slippage_bps / 10_000
    fee = cfg.taker_fee
    if side == Side.LONG:
        return open_price * (1 + slip + fee)
    else:
        return open_price * (1 - slip - fee)
```

**SL/TP simulation (conservative — assume worst case):**
- Если `bar.low <= sl_price` И `bar.high >= tp_price` в одном баре → assume SL hit (worst case)
- Это намеренно консервативно для бэктеста

---

### `src/backtest/walk_forward.py`

**Назначение:** Rolling Walk-Forward Analysis.

**Параметры (из конфига):**
```yaml
backtest:
  train_bars: 2000    # ~12 недель на 1H
  test_bars: 500      # ~3 недели
  step_bars: 500      # non-overlapping test windows
  k_folds: 5          # минимум 5 фолдов
  oos_is_threshold: 0.7  # OOS Sharpe / IS Sharpe >= 0.7
```

**Алгоритм:**
```
Fold 1: bars[0..2000] train    → bars[2000..2500] test
Fold 2: bars[500..2500] train  → bars[2500..3000] test
...
Fold K: bars[(K-1)*500...(K-1)*500+2000] train → test
```

**Выход:** `WFAResult` — список `FoldResult` с IS/OOS Sharpe, ratio, trades

---

### `src/backtest/lookahead_detector.py`

**Назначение:** O(n²) future-bar poison test. Проверяет что signal(t) не зависит от данных bar(t+1..T).

```python
def detect_lookahead(strategy_fn: Callable, bars: list[Bar]) -> bool:
    """Returns True if look-ahead bias detected."""
    full_signals = strategy_fn(bars)

    for t in range(len(bars)):
        # Mask all future bars
        masked_bars = bars[:t+1] + [Bar.null()] * (len(bars) - t - 1)
        partial_signals = strategy_fn(masked_bars)

        # Signal at t must be identical whether or not future data exists
        if full_signals[t] != partial_signals[t]:
            logger.error("lookahead_detected", bar_index=t,
                        full=full_signals[t], masked=partial_signals[t])
            return True

    return False
```

**CI gate:** `python scripts/lookahead_detector.py --fail-on-detect`

---

### `src/storage/audit_log.py`

**Назначение:** Append-only JSONL audit trail с tamper-evident hash chain.

```python
class AuditLog:
    def append(self, record: dict) -> None:
        """Append record with tamper chain hash."""
        canonical = json.dumps(record, sort_keys=True, ensure_ascii=False)
        record_hash = hashlib.sha256(
            (self._prev_hash + canonical).encode()
        ).hexdigest()

        entry = {**record,
                 "prev_record_hash": self._prev_hash,
                 "record_hash": record_hash}

        self._file.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self._file.flush()
        self._prev_hash = record_hash
```

**Ротация:** ежедневно, файл `audit-YYYY-MM-DD.jsonl.gz`
**Верификация:** `scripts/verify_audit_chain.py` — проверяет хэши по цепочке

---

## 4. Конфигурация `config/default.yaml`

```yaml
# ============================================================
# algo-bot v0.1 Configuration
# ALL numbers live here. NEVER hardcode in src/.
# Types and ranges validated by config/schema.py (pydantic v2).
# ============================================================

bot:
  symbol: "BTCUSDT"           # str, Binance pair
  interval: "1h"              # str, kline interval
  mode: "paper"               # str: paper | live (live only after v0.2 validation)
  strategy_id: "ema-cross-v1" # str, appears in clientOrderId and audit log

strategy:
  ema_fast: 20                # int [5, 200], Classical EMA period for crossover signal
  ema_slow: 50                # int [10, 500], must be > ema_fast
  adx_period: 14              # int [5, 50], Wilder ADX smoothing period
  adx_threshold: 25.0         # float [10, 50], min ADX to confirm trend
  adx_confirm_bars: 3         # int [1, 10], bars ADX must remain above threshold
  rsi_period: 14              # int [5, 50], Wilder RSI period
  rsi_overbought: 70.0        # float [60, 90], RSI level to block LONG entry
  rsi_oversold: 30.0          # float [10, 40], RSI level to block SHORT entry

risk:
  # Kelly phase thresholds (number of completed trades)
  kelly_phase_thresholds: [30, 100, 200]  # list[int]
  fixed_fraction_phase0: 0.010   # float [0.001, 0.05], <30 trades
  fixed_fraction_phase1: 0.020   # float [0.001, 0.05], 30-100 trades
  quarter_kelly_cap: 0.030       # float [0.01, 0.10], max size in Phase 2 (100-200 trades)
  half_kelly_cap: 0.050          # float [0.01, 0.15], max size in Phase 3 (≥200 trades)

  # ATR-based SL/TP multipliers
  k_sl_long: 2.0               # float [1.0, 5.0], SL = entry - k_sl_long * ATR
  k_sl_short: 1.5              # float [1.0, 5.0], SL = entry + k_sl_short * ATR
  k_tp: 3.0                    # float [1.0, 10.0], TP = entry ± k_tp * ATR
  min_sl_distance_pct: 0.005   # float, min SL = max(k_sl*ATR, 0.005*entry)

  # Circuit breaker levels (drawdown from high-water mark)
  cb_l1_pct: 0.15              # float [0.05, 0.30], warn + half-size
  cb_l2_pct: 0.22              # float [0.10, 0.40], halt 24h
  cb_l3_pct: 0.30              # float [0.15, 0.50], full stop, manual restart
  flash_crash_pct: 0.08        # float [0.03, 0.20], flash CB floor
  flash_crash_atr_mult: 3.0    # float [1.0, 10.0], flash = max(floor, mult*ATR%)

  # Risk of Ruin gate (activates after min_trades_for_ror trades)
  min_trades_for_ror: 30       # int, RoR calculation needs ≥30 data points
  max_ror_threshold: 0.05      # float [0.01, 0.20], reject strategy if P(ruin)>5%

execution:
  slippage_bps: 10.0           # float [0, 100], fixed slippage for MVP orders <$10k
  taker_fee: 0.001             # float, Binance spot VIP0 taker fee = 0.1%
  maker_fee: 0.001             # float, Binance spot VIP0 maker fee = 0.1%
  bnb_discount: false          # bool, BNB fee discount (reduces to 0.075%)
  order_timeout_s: 60          # int [10, 300], partial fill timeout
  max_retries: 3               # int [1, 10], REST retry count (excluding 5xx!)
  recv_window_ms: 5000         # int [1000, 60000], Binance recvWindow
  listen_key_refresh_s: 1800   # int, refresh listen key every 30 min (expires 60 min)

backtest:
  initial_capital: 10000.0     # float, USD starting capital
  train_bars: 2000             # int [500, 50000], rolling WF train window
  test_bars: 500               # int [100, 10000], rolling WF test window
  step_bars: 500               # int, WF step (= test_bars for non-overlapping)
  k_folds: 5                   # int [3, 20], minimum WF folds
  oos_is_threshold: 0.70       # float [0.5, 1.0], OOS/IS Sharpe ratio gate
  mc_permutations: 2000        # int [500, 50000], Monte Carlo sign-flip iterations
  mc_method: "sign_flip"       # str: sign_flip | block_bootstrap
  mc_block_size: 20            # int, block size for block_bootstrap
  mc_alpha: 0.05               # float [0.01, 0.20], significance level
  min_trades_for_report: 30    # int, min OOS trades to include fold in report
  min_trades_for_trust: 100    # int, min trades for CI-valid statistics

storage:
  sqlite_path: "data/bot.db"         # str, WAL mode
  parquet_dir: "data/parquet/"       # str, OHLCV files
  audit_log_dir: "data/audit/"       # str, JSONL daily rotation
  audit_retention_days: 2555         # int, 7 years
  parquet_compression: "snappy"      # str: snappy | zstd | gzip

infra:
  ws_url_testnet: "wss://testnet.binance.vision/ws"
  ws_url_prod: "wss://stream.binance.com:9443/ws"
  rest_url_testnet: "https://testnet.binance.vision"
  rest_url_prod: "https://api.binance.com"
  ws_reconnect_base_s: 1.0           # float, backoff base
  ws_reconnect_max_s: 60.0           # float, backoff max
  ws_reconnect_fail_count: 3         # int, halts after N fails in reconnect_window_s
  ws_reconnect_window_s: 60.0        # float, window to count reconnect attempts
  stale_data_warn_s: 5400            # int, 1.5 * 3600 = warn threshold
  stale_data_halt_s: 7200            # int, 2.0 * 3600 = halt threshold
  clock_drift_max_ms: 1000           # int, halt if |drift| > this
  clock_sync_interval_s: 60          # int, sync with Binance /api/v3/time
  rate_limit_headroom_pct: 0.90      # float, use max this fraction of rate limit
  ring_buffer_size: 1000             # int, max bars in memory

dashboard:
  port: 8501                         # int, Streamlit port
  dev_mode: true                     # bool, shows all panels vs live_mode (P&L only)
  refresh_interval_s: 5              # int, auto-refresh
```

---

## 5. State Machine — таблица переходов

| Текущее состояние | Триггер | Guard | Action | Следующее состояние |
|---|---|---|---|---|
| IDLE | NewBar | bar.closed==True AND data_quality==OK | indicators.update(bar) | ANALYZE |
| IDLE | NewBar | data_quality==GAP | log.warn, gap_counter++ | IDLE |
| ANALYZE | IndicatorsReady | indicators.is_ready==True | generate_signal() | SIGNAL |
| ANALYZE | IndicatorsNotReady | is_ready==False | continue warmup | IDLE |
| SIGNAL | SignalEmitted | signal.side != FLAT | risk.check(signal) | RISK_CHK |
| SIGNAL | NoSignal | signal is None or FLAT | - | IDLE |
| RISK_CHK | RiskApproved | size.qty > 0 AND filters OK | prepare order | EXECUTE_SUBMITTING |
| RISK_CHK | RiskRejected | any risk check fails | log ReasonCode | IDLE |
| EXECUTE_SUBMITTING | OrderAck | resp.status==200 | store order | EXECUTE_WORKING |
| EXECUTE_SUBMITTING | HTTP5xx | - | query existing order | EXECUTE_WORKING |
| EXECUTE_SUBMITTING | HTTP418 | - | cancel all, raise IPBanError | HALT |
| EXECUTE_WORKING | FILLED | fill qty == orig qty | record trade | MONITOR |
| EXECUTE_WORKING | PARTIAL_FILL | 0 < exec < orig | start timeout timer | EXECUTE_PARTIAL |
| EXECUTE_PARTIAL | FillComplete | exec == orig | record trade | MONITOR |
| EXECUTE_PARTIAL | Timeout 60s | - | cancel residual | EXECUTE_CANCELLING |
| EXECUTE_CANCELLING | CancelAck | - | record partial trade | IDLE |
| MONITOR | OCOTriggered | TP or SL hit | record PnL, clear position | IDLE |
| HALT | OperatorResume | manual signal | reconcile state | IDLE |
| RECONNECT | StateReconciled | position matches exchange | resume from prev | prev_state |
| RECONNECT | PositionMismatch | local != exchange | - | HALT |
| **ANY (watchdog)** | WSDisconnect | - | stop decisioning | RECONNECT |
| **ANY (watchdog)** | NoBarFor(1.5*Δ) | - | warn | STALE_DATA |
| **ANY (watchdog)** | NoBarFor(2*Δ) | - | halt decisioning | STALE_DATA→HALT |
| **ANY (watchdog)** | CircuitBreaker | CB.level >= L2 | cancel all | HALT |
| **ANY (watchdog)** | ClockDrift >1s | - | stop signed requests | CLOCK_DRIFT |
| **ANY (watchdog)** | HTTP429 | - | token bucket throttle | RATE_LIMITED |

---

## 6. Domain Events — спецификация (ключевые 10 из 20)

### `NewBar`
```python
class NewBarEvent(BaseModel):
    event_type: Literal["NewBar"] = "NewBar"
    symbol: str
    interval: str
    bar: Bar
    received_at: datetime  # UTC ns
    sequence_number: int   # монотонный счётчик
```
- **Producer:** `collector.py`
- **Consumers:** `indicators/registry.py`, `storage/parquet_writer.py`
- **Trigger:** WS kline event с `k.x == true`
- **Persist:** нет (ephemeral event); Bar persist в Parquet

### `SignalGenerated`
```python
class SignalGeneratedEvent(BaseModel):
    event_type: Literal["SignalGenerated"] = "SignalGenerated"
    signal_id: UUID
    bar_ref_close_time: datetime
    side: Side
    reason: ReasonCode
    features: dict[str, float]  # все значения индикаторов
    config_hash: str            # sha256 config
    git_commit: str             # 7-char hex
```
- **Persist:** `events` table SQLite + audit_log JSONL

### `RiskApproved`
```python
class RiskApprovedEvent(BaseModel):
    event_type: Literal["RiskApproved"] = "RiskApproved"
    signal_id: UUID
    order_intent_id: UUID
    qty: Decimal
    entry_price_approx: Decimal
    sl_price: Decimal
    tp_price: Decimal
    kelly_phase: int
    position_fraction: float
```

### `OrderFilled`
```python
class OrderFilledEvent(BaseModel):
    event_type: Literal["OrderFilled"] = "OrderFilled"
    client_order_id: str
    exchange_order_id: int
    fills: list[FillReport]
    avg_price: Decimal
    total_qty: Decimal
    total_fees: Decimal
    fee_asset: str
    filled_at: datetime
```

---

## 7. Edge Case Catalog — конкретные реализации

| # | Edge Case | Обнаружение (код) | Действие | Тест |
|---|---|---|---|---|
| 1 | Missing bar (gap) | `delta > interval + 5s` | DataQuality.GAP, skip signal | `test_gap_single_bar` |
| 2 | 3+ consecutive gaps | `consecutive_gaps >= 3` | `HALT_DATA_QUALITY` event | `test_critical_gap` |
| 3 | Duplicate timestamp | `open_time <= last_close_time` | raise DuplicateBarError, skip | `test_duplicate_bar` |
| 4 | Volume = 0 | `bar.volume == 0` | Accept, log.info (valid stilled market) | `test_zero_volume` |
| 5 | OHLC invariant violated | `low > min(o,c)` или аналог | reject at pydantic validation | `test_ohlc_violation` |
| 6 | Flash crash | `\|bar_return\| >= max(8%, 3*ATR)` | HALT_FLASH, cancel_all, flatten | `test_flash_crash` |
| 7 | WS dropout | no msg > 30s | RECONNECT state, backoff | `test_ws_dropout` |
| 8 | 3 reconnects in 60s | `reconnect_count >= 3 in 60s` | HALT + alert | `test_ws_multiple_dropout` |
| 9 | Stale data 1.5*Δ | `now - last_bar > 5400s` | STALE_DATA, halt decisioning | `test_stale_data` |
| 10 | Clock drift >1s | `\|local - server_ms\| > 1000` | CLOCK_DRIFT, stop signed reqs | `test_clock_drift` |
| 11 | HTTP 429 | status 429 | throttle, honor Retry-After | `test_rate_limit` |
| 12 | HTTP 418 IP ban | status 418 | HALT, wait expiry, alert | `test_ip_ban` |
| 13 | HTTP 5xx unknown | status >= 500 | query order state, NOT retry | `test_server_error` |
| 14 | -2010 insufficient balance | Binance code -2010 | REJECT_INSUFFICIENT_BALANCE | `test_insufficient_balance` |
| 15 | Partial fill timeout 60s | `time_since_partial > 60s` | cancel residual, adopt executed | `test_partial_fill_timeout` |
| 16 | OCO partial fill | `listStatus == PARTIALLY_FILLED` | re-issue protective order on residual | `test_oco_partial_fill` |
| 17 | Duplicate signal same bar | `bar_ref.close_time == prev_signal.bar_ref.close_time` | REJECT_DUPLICATE_SIGNAL | `test_duplicate_signal` |
| 18 | Server crash + reboot | systemd restart | reconcile from `/openOrders` + `/myTrades` | `test_server_crash_recovery` |
| 19 | Position mismatch on reconcile | local qty != exchange qty | HALT, manual review | `test_position_mismatch_halt` |
| 20 | Kelly = 0 (negative edge) | `f* <= 0` | REJECT_KELLY_ZERO, no trade | `test_kelly_zero` |
| 21 | ATR = 0 | `atr == 0` | REJECT_ATR_ZERO (no SL possible) | `test_atr_zero` |
| 22 | SL+TP same 1H bar | `bar.low <= sl AND bar.high >= tp` | assume SL first (conservative backtest) | `test_sl_tp_same_bar` |
| 23 | Config reload with conflict | new ema_slow <= old ema_fast | reject reload, log error, keep old | `test_config_reload_conflict` |
| 24 | Listen key expiry | timer 30min | PUT `/api/v3/userDataStream` | `test_listen_key_refresh` |

---

## 8. Acceptance Criteria

### System-level (infrastructure)
| # | Критерий | Порог | Измерение |
|---|---|---|---|
| S1 | Uptime | ≥99.5% rolling 30d | Heartbeat 1/s → healthchecks.io |
| S2 | WS reconnect | p99 < 5s disconnect→first tick | Timestamps в логах |
| S3 | P&L reconciliation | ≤0.01% расхождение local vs `/account` | Nightly reconcile script |
| S4 | Dashboard latency | p95 < 2s fill→UI | Grafana histogram (v0.3) / logs (v0.1) |
| S5 | Config hot-reload | non-critical: 0s; critical: restart за <10s | SIGHUP test |
| S6 | Zero secrets in git | 0 items detect-secrets + gitleaks | CI pre-commit + PR check |

### Strategy-level (OOS only)
| # | Критерий | Порог | Обоснование |
|---|---|---|---|
| T1 | Sharpe OOS (annualized net of costs) | ≥1.0 | Suspicious if >3.0 (Hudson & Urquhart 2021) |
| T2 | Sortino OOS | ≥1.5 | EMA trend-following = positive skew |
| T3 | MaxDD OOS | <25% | Suspicious if <5% (too good) |
| T4 | Win Rate | ≥45% при RR≥1.5 | Или ≥35% при RR≥2.0 |
| T5 | Math Expectation | >0 с t-stat ≥2.0 (n≥100 OOS trades) | CLT valid от n≥30 |
| T6 | OOS/IS Sharpe | ≥0.70 | <0.5 = overfit (Bailey–López de Prado 2014) |

**Gate для scaling (до Phase 4 Half-Kelly):** T1–T6 AND n_live_trades ≥ 200 AND DSR > 0.

---

## 9. Anti-patterns — что НЕ делать

```python
# ❌ BARE EXCEPT
try:
    result = api_call()
except:  # NEVER
    pass

# ✅ EXPLICIT
try:
    result = await binance.place_order(...)
except RateLimitError as e:
    await asyncio.sleep(e.retry_after)
except IPBanError:
    raise  # propagate to state machine
except BinanceAPIError as e:
    logger.error("order_rejected", code=e.code, msg=e.msg)
```

| Анти-паттерн | Правило |
|---|---|
| Bare `except:` | НЕТ. Каждый except явно типизирован |
| `print()` для логов | НЕТ. Только `structlog.get_logger()` с JSON |
| Хардкод чисел в src/ | НЕТ. Все числа в `config/default.yaml` |
| Global mutable state | НЕТ. Передавать через аргументы, pydantic models |
| Синхронный HTTP в async | НЕТ. Только `aiohttp.ClientSession` |
| `import` между bounded contexts напрямую | НЕТ. Только через domain events |
| Обработка `bar.closed=False` в сигналах | НЕТ. Assert в начале каждого signal-fn |
| Retry с новым clientOrderId на HTTP 5xx | НЕТ. Query существующий ордер по origClientOrderId |
| Auto-reconcile при расхождении position | НЕТ. → HALT, manual review |
| `StandardScaler` на всём датасете в бэктесте | НЕТ. Только rolling/expanding fit на train-only |
| `.shift(-1)` в signal calculation | НЕТ. Это look-ahead bias |
| Накопление неограниченного state в памяти | НЕТ. ring_buffer.maxlen=1000 |
| `asyncio.sleep(0)` вместо правильного backoff | НЕТ. Exponential backoff с jitter |

---

## 10. Сверка с архитектурным документом

| Раздел архитектуры | Реализован в ТЗ |
|---|---|
| §1 Executive Summary | §0 Метаданные, §A.1 CLAUDE.md |
| §2 Discrepancy Table | §4 Config (все resolved values) |
| §3 Tech Stack by version | §A.2, §2 Спринты |
| §4 Validation params | §4 Config: backtest section |
| §5 Kelly phases | §4 Config: risk, §3 position_sizer.py |
| §6 Circuit breakers | §4 Config: risk, §3 circuit_breaker.py |
| §7 State Machine (12 states) | §5 Таблица переходов, §3 machine.py |
| §8 Domain Events (20) | §6 Domain Events |
| §9 Edge Cases (24) | §7 Edge Case Catalog |
| §10 Acceptance Criteria | §8 Acceptance Criteria |
| §11 ADR template | §A.3 Библиотека docs/adr/ |
| §12 Data Dictionary | CLAUDE.md + models.py |
| §13 Risk Register | §9 Anti-patterns (coverage) |
| §14 Reason Codes (28) | §3 signals/models.py, reason_codes.py |
| §15 CI/CD pipeline | §2 Спринт 10 |
| §16 Execution timing | §3 backtest/engine.py + CLAUDE.md |

---

## Appendix: Reason Codes (полный список 28)

```python
class ReasonCode(str, Enum):
    # Entry signals
    ENTRY_LONG_TREND_FOLLOWING   = "ENTRY_LONG_TREND_FOLLOWING"
    ENTRY_SHORT_TREND_FOLLOWING  = "ENTRY_SHORT_TREND_FOLLOWING"
    ENTRY_LONG_PULLBACK          = "ENTRY_LONG_PULLBACK"
    ENTRY_SHORT_PULLBACK         = "ENTRY_SHORT_PULLBACK"
    SCALE_IN_LONG                = "SCALE_IN_LONG"
    SCALE_IN_SHORT               = "SCALE_IN_SHORT"
    SCALE_OUT_PARTIAL            = "SCALE_OUT_PARTIAL"

    # Exit signals
    EXIT_SL_HIT                  = "EXIT_SL_HIT"
    EXIT_TP_HIT                  = "EXIT_TP_HIT"
    EXIT_TRAILING_STOP           = "EXIT_TRAILING_STOP"
    EXIT_SIGNAL_FLIP             = "EXIT_SIGNAL_FLIP"
    EXIT_TIME_STOP               = "EXIT_TIME_STOP"
    EXIT_CIRCUIT_BREAKER         = "EXIT_CIRCUIT_BREAKER"
    EXIT_MANUAL_OVERRIDE         = "EXIT_MANUAL_OVERRIDE"

    # Rejections
    REJECT_ADX_BELOW_THRESHOLD   = "REJECT_ADX_BELOW_THRESHOLD"
    REJECT_RSI_OVERBOUGHT        = "REJECT_RSI_OVERBOUGHT"
    REJECT_RSI_OVERSOLD          = "REJECT_RSI_OVERSOLD"
    REJECT_RISK_EXCEEDED         = "REJECT_RISK_EXCEEDED"
    REJECT_INSUFFICIENT_BALANCE  = "REJECT_INSUFFICIENT_BALANCE"
    REJECT_STALE_DATA            = "REJECT_STALE_DATA"
    REJECT_RATE_LIMITED          = "REJECT_RATE_LIMITED"
    REJECT_CLOCK_DRIFT           = "REJECT_CLOCK_DRIFT"
    REJECT_MIN_NOTIONAL          = "REJECT_MIN_NOTIONAL"
    REJECT_FILTER_PRICE          = "REJECT_FILTER_PRICE"
    REJECT_DUPLICATE_SIGNAL      = "REJECT_DUPLICATE_SIGNAL"
    REJECT_KELLY_ZERO            = "REJECT_KELLY_ZERO"
    REJECT_ATR_ZERO              = "REJECT_ATR_ZERO"

    # Halts
    HALT_DRAWDOWN_L1             = "HALT_DRAWDOWN_L1"
    HALT_DRAWDOWN_L2             = "HALT_DRAWDOWN_L2"
    HALT_DRAWDOWN_L3             = "HALT_DRAWDOWN_L3"
    HALT_FLASH_CRASH             = "HALT_FLASH_CRASH"
    HALT_DATA_QUALITY            = "HALT_DATA_QUALITY"
    HALT_EXCHANGE_OUTAGE         = "HALT_EXCHANGE_OUTAGE"
    HALT_KILL_SWITCH             = "HALT_KILL_SWITCH"
```

---

## Appendix: Пример audit log record

```json
{
  "schema_version": "1.0.0",
  "trade_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-04-17T15:00:00.123456789Z",
  "symbol": "BTCUSDT",
  "venue": "BINANCE_SPOT_TESTNET",
  "strategy_id": "ema-cross-v1",
  "strategy_version": "0.1.0",
  "git_commit": "a3f9d12",
  "config_hash": "sha256:abc123...",
  "bar_closed": true,
  "clock_drift_ms": 42,
  "signal_inputs": {
    "bar_timestamp": "2026-04-17T14:00:00Z",
    "ema_fast": 94234.5,
    "ema_slow": 93891.2,
    "adx_14": 28.4,
    "plus_di_14": 31.2,
    "minus_di_14": 18.5,
    "rsi_14": 58.3,
    "atr_14": 420.5,
    "data_quality": "OK",
    "signal_reason": "ENTRY_LONG_TREND_FOLLOWING"
  },
  "risk_decision": {
    "kelly_phase": 0,
    "position_fraction": 0.01,
    "position_size_usd": 100.0,
    "sl_price": 93393.5,
    "tp_price": 95496.0,
    "sl_distance_atr": 2.0,
    "tp_distance_atr": 3.0,
    "rr_ratio": 1.5,
    "drawdown_pct": 0.023
  },
  "execution": {
    "client_order_id": "ema-cross-v1-1713366000-a3f9d12b",
    "order_type": "OCO",
    "side": "BUY",
    "fill_price": 94256.8,
    "slippage_bps": 2.4,
    "fee_quote": 0.094,
    "fee_asset": "USDT",
    "time_to_fill_ms": 127
  },
  "reason_code": "ENTRY_LONG_TREND_FOLLOWING",
  "prev_record_hash": "sha256:previous...",
  "record_hash": "sha256:this_record..."
}
```

---

## Appendix: Makefile

```makefile
.PHONY: test test-unit test-property test-integ test-edge run backtest lint

test-unit:
	pytest tests/unit/ -v -m unit

test-property:
	pytest tests/property/ -v -m property --hypothesis-seed=42

test-integ:
	pytest tests/integration/ -v -m integration --timeout=30

test-edge:
	pytest tests/edge_cases/ -v -m edge_case

test:
	pytest tests/ -v --cov=src --cov-report=term-missing --cov-fail-under=80

lookahead:
	python scripts/lookahead_detector.py \
		--data data/fixtures/btcusdt_1h_5y.parquet \
		--fail-on-detect

lint:
	ruff check src/ tests/
	mypy src/ --strict

backtest:
	python -m src.backtest.walk_forward \
		--data data/fixtures/btcusdt_1h_5y.parquet \
		--config config/default.yaml

run:
	python -m src.main --config config/default.yaml --mode paper

dashboard:
	streamlit run src/dashboard/app.py --server.port 8501
```

---

*ТЗ версия 1.0.0 | Основано на Консолидированной архитектуре v0.1 (17 апреля 2026)*
*Для Claude Code: начни с `CLAUDE.md` в корне проекта, затем следуй спринтам строго по порядку.*
