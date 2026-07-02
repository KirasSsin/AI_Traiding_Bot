---
title: "Настройки бота: что можно менять и какие защиты встроены"
section: "01-как-работает-бот"
status: filled
money_core: true
updated: 2026-06-26
source_files: src/platform/config.py, src/config_loader.py
---

# Настройки бота: что можно менять и какие защиты встроены

**TL;DR:** Все параметры бота живут в переменных окружения (файл `.env`). Три ключа обязательны без каких-либо умолчаний — API-ключ Bybit, API-секрет и HMAC-ключ. Встроенные валидаторы не дают запустить реальные деньги случайно, а логика «отпечатка конфигурации» позволяет оператору убедиться, что риск-настройки не менялись перед ручным вмешательством.

## Простыми словами

Представьте, что бот — это сложное промышленное оборудование с пультом управления. У пульта есть:

- **Красные тумблеры**, которые нельзя щёлкнуть в неправильном порядке — защиты встроены в схему, а не в инструкцию.
- **Числовые регуляторы** с ограничителями-упорами — нельзя выкрутить «на ноль» или «до упора» без ошибки.
- **Пломба** на панели с риск-настройками — перед тем как оператор разблокирует экстренный режим, система проверяет, что пломба не сорвана.

В нашем случае пульт — это файл `.env` в корне проекта. Бот читает его при старте и проверяет, что каждый тумблер стоит в безопасном положении. Если что-то не так — запуск немедленно падает с понятным сообщением об ошибке.

### Что такое переменные окружения и файл `.env`

**Переменные окружения** (environment variables) — это способ передать программе настройки снаружи, не прописывая их в коде. Они похожи на стикеры, прикреплённые к программе перед запуском: «работай в тестовом режиме», «вот пароль к базе данных» и т.д.

**Файл `.env`** — это обычный текстовый файл со строками вида `TESTNET=true` или `BYBIT_API_KEY=abc123...`. Бот читает его при старте и превращает строки в настройки. Важно: этот файл **никогда не попадает в git** (добавлен в `.gitignore`), потому что содержит секретные ключи.

### Что такое API-ключ, API-секрет и HMAC-ключ

**API-ключ (bybit_api_key)** — это ваше имя пользователя на бирже Bybit для программного доступа. Биржа знает, кто вы.

**API-секрет (bybit_api_secret)** — это ваш пароль к этому программному доступу. Каждый запрос к бирже подписывается секретом, чтобы биржа убедилась, что запрос пришёл действительно от вас.

**HMAC-ключ (risk_override_hmac_key)** — это отдельный ключ для защиты файла [[manual-override-resume|ручного вмешательства]] в работу системы (когда оператор хочет снять экстренную остановку). Он отделён от API-секрета намеренно: если вы меняете API-ключи биржи (ротация при компрометации), действующие разрешения оператора не теряют силу. И наоборот (см. ADR 0018, CWE-345 — `src/platform/config.py:203-207`).

---

## Как это работает у нас

### Шаг 1. Как Settings загружает параметры

Класс `Settings` в `src/platform/config.py:45-58` наследуется от `BaseSettings` библиотеки **pydantic-settings**. Готовый объект `Settings` затем собирается в рабочие компоненты бота при [[startup-and-wiring|запуске]]. При создании объекта `Settings()` библиотека автоматически:

1. Ищет файл `.env` в корне проекта.
2. Читает переменные окружения системы.
3. Для каждого параметра — берёт значение из переменной окружения (или `.env`), преобразует в нужный тип (число, путь к файлу, булево) и проверяет ограничения.

Имена переменных окружения совпадают с именами параметров в верхнем регистре. Например, `testnet: bool = True` читается из переменной `TESTNET=true`. Чувствительность к регистру отключена (`case_sensitive=False`, `src/platform/config.py:51`).

### Шаг 2. Обязательные секреты — без умолчаний

Три параметра заданы с `...` (многоточие в Python — знак «обязателен, нет умолчания»):

```python
bybit_api_key: str = Field(..., min_length=8)       # config.py:61
bybit_api_secret: str = Field(..., min_length=8)    # config.py:62
risk_override_hmac_key: str = Field(..., min_length=32)  # config.py:207
```

Если хотя бы один из них не задан в `.env` — бот откажется запускаться. Это сделано намеренно: нельзя случайно запустить бот с «пустым» ключом (CWE-798 — хранение учётных данных в коде).

Кроме того, для `risk_override_hmac_key` задан минимальная длина 32 символа — достаточно длинный ключ для криптографической стойкости HMAC-SHA256.

Четыре пути также обязательны без умолчаний (`src/platform/config.py:101-105`):

```python
data_dir: Path
log_dir: Path
db_path: Path
parquet_dir: Path
```

### Шаг 3. Группы параметров

#### Учётные данные биржи

| Параметр | Умолчание | Описание |
|---|---|---|
| `bybit_api_key` | — (обязателен) | Ключ API Bybit, мин. 8 символов |
| `bybit_api_secret` | — (обязателен) | Секрет API Bybit, мин. 8 символов |
| `risk_override_hmac_key` | — (обязателен) | HMAC-ключ для файла override, мин. 32 символа |

#### Флаги биржевого контура

Это «тумблеры», которые определяют, куда реально уходят ордера. Подробнее — в `[[run-modes-testnet-live-reconcile]]`.

| Параметр | Умолчание | Описание |
|---|---|---|
| `testnet` | `True` | Использовать тестовую биржу Bybit |
| `demo` | `False` | Использовать Bybit demo-режим (виртуальные деньги на реальной инфраструктуре) |
| `trading_enabled` | `False` | Разрешить отправку ордеров вообще |
| `live_trading` | `False` | Включить режим реальных денег (mainnet) |

**Матрица роутинга** (куда реально уходят ордера, `src/platform/config.py:69-73`):

| testnet | demo | Куда идут ордера |
|---|---|---|
| `True` | `False` | Тестовая биржа Bybit (api-testnet / stream-testnet) |
| `False` | `True` | Mainnet-demo: виртуальные деньги, но реальная инфраструктура (api-demo) |
| `True` | `True` | Demo-testnet (api-demo-testnet) |
| `False` | `False` | Настоящий mainnet, реальные деньги (api / stream) |

Пара `(testnet, demo)` — **единственный источник правды** о том, с какой биржей работает бот. Оба компонента — [[bybit-rest-client-and-backoff|REST-клиент]] и [[bybit-private-websocket|WebSocket]] — строятся из одной и той же пары, иначе ордера уйдут на один эндпоинт, а сообщения о сделках придут с другого, и [[execution-state-machine|FSM]] (машина состояний ордера) никогда не увидит подтверждения исполнения (ADR 0055, BYBIT-01, `src/platform/config.py:64-85`).

#### Параметры стратегии

Стратегия [[02-стратегии/ema-crossover-strategy|EMA-Crossover + ADX + RSI]] управляется этими параметрами (`src/platform/config.py:92-99`). Как из этих индикаторов рождается торговый сигнал — в [[signal-architecture]]:

| Параметр | Умолчание | Что это |
|---|---|---|
| `strategy_ema_fast` | `12` | Период быстрой EMA (скользящей средней) |
| `strategy_ema_slow` | `26` | Период медленной EMA |
| `strategy_adx_period` | `14` | Период ADX (индикатор силы тренда) |
| `strategy_adx_threshold` | `25` | Порог ADX: ниже — рынок «без тренда», сигналы игнорируются |
| `strategy_rsi_period` | `14` | Период RSI (индикатор перекупленности/перепроданности) |
| `strategy_rsi_oversold` | `30` | RSI ниже этого значения — актив «перепродан» (потенциально пора покупать) |
| `strategy_rsi_overbought` | `70` | RSI выше этого значения — актив «перекуплен» |
| `strategy_atr_period` | `14` | Период ATR (средний истинный диапазон) — мера волатильности |

**[[ema-rsi-indicators|EMA]] (Exponential Moving Average)** — скользящая средняя, которая даёт больший вес свежим ценам. «Быстрая» следует за ценой плотнее, «медленная» — более инерционна. Когда быстрая пересекает медленную снизу вверх — сигнал на покупку.

**[[adx-indicator|ADX]] (Average Directional Index)** — индикатор, который показывает не направление тренда, а его силу. Значение ниже порога (25) означает «рынок движется боком», и стратегия в этом случае ордера не открывает.

**[[ema-rsi-indicators|RSI]] (Relative Strength Index)** — индикатор, который сравнивает размер недавних движений вверх и вниз. Диапазон 0-100. Значение выше 70 означает «цена росла слишком быстро» (перекуплена), ниже 30 — «цена падала слишком быстро» (перепродана).

**[[atr-indicator|ATR]] (Average True Range)** — средний размер колебания цены за период. Используется как «линейка волатильности» для расчёта расстояния до стоп-лосса и тейк-профита. Точные определения и математика каждого индикатора собраны в [[technical-indicators]].

#### Параметры риска

| Параметр | Умолчание | Что это |
|---|---|---|
| `risk_max_position_pct_cap` | `0.05` (5%) | Максимальная доля капитала на одну позицию |
| `risk_sl_atr_multiplier` | `1.5` | Стоп-лосс = 1.5 × ATR от цены входа |
| `risk_tp_atr_multiplier` | `3.0` | Тейк-профит = 3.0 × ATR от цены входа |
| `risk_cb_l1_dd` | `0.15` (15%) | Просадка L1: первое предупреждение |
| `risk_cb_l2_dd` | `0.22` (22%) | Просадка L2: второе предупреждение |
| `risk_cb_l3_dd` | `0.30` (30%) | Просадка L3: остановка (circuit breaker) |
| `risk_cb_flash_abs` | `0.08` (8%) | «Флэш-краш»: падение на 8% за один тик |
| `risk_cb_flash_atr_mult` | `3.0` | «Флэш-краш»: OR-условие — падение > 3 × ATR |
| `risk_kelly_phase1_cap` | `0.01` (1%) | Kelly фаза 1: максимум 1% капитала на сделку |
| `risk_kelly_phase2_cap` | `0.02` (2%) | Kelly фаза 2: максимум 2% |
| `risk_kelly_phase3_cap` | `0.03` (3%) | Kelly фаза 3: максимум 3% |
| `risk_kelly_phase4_cap` | `0.05` (5%) | Kelly фаза 4: максимум 5% |

**Стоп-лосс** — это заранее оговорённая цена выхода из убыточной сделки (на расстоянии `risk_sl_atr_multiplier` × [[atr-indicator|ATR]] от входа). Как страховка: решаем заранее, при каком убытке выходим, чтобы не потерять больше запланированного.

**Тейк-профит** — заранее оговорённая цена фиксации прибыли.

**Просадка ([[equity-tracking|Drawdown]])** — снижение стоимости портфеля от исторического максимума. Просадка 15% означает: «капитал уменьшился на 15% от своего лучшего значения». [[circuit-breakers-drawdown-flash|Circuit breaker]] (прерыватель цепи) — это автоматическая остановка при достижении порога.

**Kelly** — метод расчёта размера позиции. Формула Келли говорит, какую долю капитала ставить исходя из вероятности выигрыша и соотношения выигрыш/проигрыш. У нас 4 фазы с нарастающими лимитами — новая стратегия начинает с 1%, накапливает статистику и постепенно получает право рисковать больше. Подробно — в `[[position-sizing-kelly]]`.

#### Пути к данным и логам

`db_path` указывает на SQLite-базу (см. [[storage-and-database]]), `parquet_dir` — на каталог исторических свечей ([[parquet-storage]]), `log_dir` — на журналы ([[logging-and-observability]]), а `risk_override_path` — на файл ручного снятия остановки ([[manual-override-resume]]).

| Параметр | Умолчание | Назначение |
|---|---|---|
| `data_dir` | — (обязателен) | Каталог для рыночных данных |
| `log_dir` | — (обязателен) | Каталог для лог-файлов |
| `db_path` | — (обязателен) | Путь к SQLite-базе |
| `parquet_dir` | — (обязателен) | Каталог для Parquet-файлов (исторические свечи) |
| `risk_override_path` | `./state/cb_override.json` | Файл ручного override circuit breaker |

#### Наблюдаемость

| Параметр | Умолчание | Назначение |
|---|---|---|
| `sentry_dsn` | `None` (отключено) | URL для отправки ошибок в Sentry (сервис мониторинга ошибок) |
| `log_level` | `"INFO"` | Уровень детализации логов: DEBUG / INFO / WARNING / ERROR |

**Sentry** — облачный сервис, который собирает исключения и трассировки из запущенного приложения. Если не указан `sentry_dsn` — интеграция не включается.

**Уровень логирования** — фильтр для журнала событий бота. `INFO` — стандартный режим (ключевые события). `DEBUG` — очень подробно (каждый тик, каждое решение). `WARNING`/`ERROR` — только проблемы. Как устроен структурированный журнал и куда он пишется — в [[logging-and-observability]].

#### Параметры устойчивости (resilience)

| Параметр | Умолчание | Назначение |
|---|---|---|
| `heal_max_bars` | `1` | Сколько баров может «состариться» незавершённая сделка при перезапуске |
| `heal_max_age_seconds` | `3600` | То же в секундах (устаревший параметр, используется если `heal_max_bars=None`) |
| `require_mainnet_gate_passed` | `True` | Информационный флаг (зарезервировано — ADR 0021 sub-decision 8, **не активирован в текущей версии**). Сегодня переход на mainnet удерживается исключительно триадой `testnet` / `trading_enabled` / `live_trading` и встроенными валидаторами, описанными в Шаге 4. |
| `oco_arming_ttl_seconds` | `60` | Время жизни «заряженного» OCO-ордера (секунды) |
| `oco_dust_threshold_btc` | `0.00001` | Минимальный остаток BTC, ниже которого позиция считается «пылью» |
| `runtime_bar_poll_cadence_seconds` | `5.0` | Как часто бот спрашивает биржу о новых свечах (секунды) |
| `runtime_bar_poll_stall_threshold` | `24` | После скольких подряд неудачных опросов — аварийная остановка |
| `runtime_kill_switch_path` | `".kill_switch"` | Путь к файлу-сигналу «немедленно остановиться» |
| `runtime_ws_check_alive_max_silence` | `30.0` | Сколько секунд молчания WebSocket допустимо до признания его мёртвым |
| `runtime_warmup_bars` | `50` | Сколько свечей «прогревается» стратегия перед первым сигналом |
| `runtime_quality_threshold_pct` | `0.005` (0.5%) | Максимальное допустимое расхождение цен между соседними свечами |

**OCO (One-Cancels-the-Other)** — тип составного ордера: стоп-лосс + тейк-профит. Когда один срабатывает — второй автоматически отменяется. На Bybit Spot OCO не поддерживается нативно, поэтому бот эмулирует его тремя отдельными ордерами (см. `[[oco-bracket-emulation]]`).

**Heal** — «исцеление»: если бот перезапускается, он проверяет незавершённые позиции в базе данных. Если позиция «старая» (старше `heal_max_bars` баров) — бот переходит в аварийный режим, а не пытается продолжить сделку. Подробно — в `[[reconcile-as-truth]]`.

**Kill switch** — аварийный стоп: оператор создаёт файл `.kill_switch` в корне проекта — бот замечает его при следующем тике и корректно завершает работу. Подробно — в `[[kill-switch-emergency-stop]]`.

**Опрос свечей** (`runtime_bar_poll_cadence_seconds` / `runtime_bar_poll_stall_threshold`) задаёт, как часто [[main-loop-tick|главный цикл]] спрашивает биржу о новой свече и после скольких «пустых» опросов включается аварийная остановка. Механика опроса и защита от look-ahead — в [[bar-source-live]].

**Молчание WebSocket** (`runtime_ws_check_alive_max_silence`) — сколько секунд тишины приватного потока допустимо, прежде чем бот признает соединение мёртвым (см. [[bybit-private-websocket]]).

**Порог качества** (`runtime_quality_threshold_pct`) — максимальный допустимый скачок цены между соседними свечами; его использует [[data-quality-detector|детектор качества данных]].

**Порог «пыли»** (`oco_dust_threshold_btc`) — остаток позиции ниже минимального размера ордера биржи (см. [[bybit-filters]]), который [[emergency-flatten-and-residual|аварийное закрытие]] игнорирует как неторгуемый.

#### Параметры S35 demo-режима

Эти пороги задают «красные линии» демо-запуска, при пересечении которых срабатывает [[halt-gate-precommitted-criteria|HaltGate]] (полная остановка) — часть общей системы [[safety-stops-and-halts|тормозов бота]].

| Параметр | Умолчание | Назначение |
|---|---|---|
| `s35_demo_active` | `False` | Включить режим тестового запуска δ |
| `s35_halt_dd_intraday` | `0.20` (20%) | Внутридневная просадка → остановка |
| `s35_halt_dd_multiday` | `0.15` (15%) | Многодневная просадка → остановка |
| `s35_halt_consecutive_losses` | `5` | Подряд проигрышных сделок → ревью оператора |
| `s35_halt_no_trade_months` | `6` | Месяцев без 30+ закрытых сделок → остановка |
| `s35_demo_approved_symbols` | `["BTCUSDT"]` | Белый список разрешённых торговых пар |

### Шаг 4. Встроенные валидаторы безопасности (model_validator)

После загрузки всех параметров Pydantic автоматически запускает три проверки. Они выполняются в порядке объявления (`mode="after"`, `src/platform/config.py:243-306`).

#### Валидатор 1: ограничение на runtime_bar_poll_stall_threshold (`src/platform/config.py:243-250`)

```python
if not (6 <= self.runtime_bar_poll_stall_threshold <= 720):
    raise ValueError(...)
```

Порог «застрявшего опроса» должен быть от 6 до 720. Нижняя граница: 6 × 5с = 30с — меньше означает ложные тревоги. Верхняя: 720 × 5с = 3600с = один период свечи 1H.

#### Валидатор 2: защита live_trading (`src/platform/config.py:252-258`)

```python
if self.live_trading and not self.trading_enabled:
    raise ValueError("live_trading requires trading_enabled=True")
if self.live_trading and self.testnet:
    raise ValueError("live_trading requires testnet=False (mainnet-only)")
```

Чтобы включить реальные деньги, нужно одновременно: `trading_enabled=True` И `testnet=False`. Нельзя забыть один из тумблеров.

#### Валидатор 3: S35 demo не может попасть на mainnet (`src/platform/config.py:260-291`)

```python
if self.s35_demo_active and self.live_trading:
    raise ValueError("S35 δ TESTNET demo cannot run на MAINNET...")
if self.s35_demo_active and not self.testnet:
    raise ValueError("S35 δ TESTNET demo requires testnet=True...")
```

Режим тестового запуска (`s35_demo_active=True`) заблокирован на mainnet **двумя независимыми проверками**:
- Явная: `live_trading=True` запрещён.
- Неявная: `testnet=False` **тоже** запрещён — потому что пара `testnet=False` уже маршрутизирует запросы на реальную биржу, даже если `live_trading=False`. Одного флага недостаточно.

Это защита от ошибки, последствия которой — потеря реального капитала.

### Шаг 5. validate_assignment — нельзя обойти проверки «на лету»

Параметр `validate_assignment=True` (`src/platform/config.py:57`) означает, что **все валидаторы перезапускаются при каждом изменении любого поля**. Даже если код попытается сделать `settings.live_trading = True` уже после запуска, валидаторы снова сработают и либо заблокируют изменение, либо убедятся в его безопасности. Без этой настройки можно было бы обойти защиту, изменив флаг уже после создания объекта (S35 T2, security-auditor HIGH #1).

### Шаг 6. Нормализация белого списка символов (`src/platform/config.py:293-306`)

```python
normalized = [s.upper() for s in self.s35_demo_approved_symbols]
```

Если оператор написал `btcusdt` вместо `BTCUSDT` — бот молча приводит к верхнему регистру. Без этого произошёл бы тихий сбой: HaltGate отправлял бы бот в аварийный режим при каждом тике с кодом `HALT_UNKNOWN_SYMBOL`, а причина была бы неочевидна.

### Шаг 7. config_hash() — «пломба» на риск-настройках (`src/platform/config.py:308-321`)

```python
def config_hash(self) -> str:
    data = self.model_dump(mode="json")
    risk_only = {k: data[k] for k in sorted(_HASH_ALLOWLIST) if k in data}
    canonical = json.dumps(risk_only, sort_keys=True, ...)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
```

Метод вычисляет SHA-256 хэш **только** риск-параметров из белого списка `_HASH_ALLOWLIST` (`src/platform/config.py:22-42`). В хэш входят:

- `risk_max_position_pct_cap`, `risk_sl_atr_multiplier`, `risk_tp_atr_multiplier`
- Все уровни circuit breaker (`risk_cb_l1_dd`, `risk_cb_l2_dd`, `risk_cb_l3_dd`, `risk_cb_flash_abs`, `risk_cb_flash_atr_mult`)
- Все фазы Kelly (`risk_kelly_phase1_cap` … `risk_kelly_phase4_cap`)
- Параметры S35-остановок (`s35_halt_dd_intraday`, `s35_halt_dd_multiday`, `s35_halt_consecutive_losses`, `s35_halt_no_trade_months`)

**Что сознательно исключено из хэша:**
- Секреты (API-ключи, HMAC-ключ) — их публикация в хэш-сообщении нарушила бы CWE-532.
- Пути к файлам и директориям — они не влияют на торговые решения.
- Флаги наблюдаемости (Sentry, log_level).
- Параметры стратегии (EMA, RSI, ADX, ATR периоды) — оператор не проверяет их при выдаче ручного override.

**Зачем:** когда оператор выдаёт ручное разрешение на снятие аварийной остановки, система проверяет, что хэш в файле override совпадает с текущим. Это гарантирует: «настройки не менялись с момента подписи». Подробно — в `[[manual-override-resume]]`.

### Шаг 8. Диапазоны-ограничители на числовые параметры

Pydantic Field поддерживает ограничения `gt` (больше), `ge` (больше или равно), `le` (меньше или равно). Примеры (`src/platform/config.py:113-155`):

| Параметр | Ограничение | Почему |
|---|---|---|
| `risk_sl_atr_multiplier` | `gt=0` | Нулевой множитель → деление на ноль в формуле размера позиции |
| `s35_halt_dd_intraday` | `gt=0`, `le=0.50` | Не может быть нулём (нет смысла) и не более 50% (нереалистично) |
| `s35_halt_dd_multiday` | `gt=0`, `le=0.50` | Аналогично |
| `s35_halt_consecutive_losses` | `ge=1`, `le=20` | От 1 до 20 подряд проигрышей |
| `s35_halt_no_trade_months` | `ge=1`, `le=24` | От 1 до 24 месяцев |

### Шаг 9. Простой YAML-загрузчик (config_loader.py)

Помимо основного класса `Settings`, в проекте есть маленький вспомогательный модуль `src/config_loader.py` для загрузки конфигов в формате YAML (не переменные окружения, а файлы).

```python
def load_config(config_path: str = "config.yaml") -> dict[str, Any]:
    # config_loader.py:7-15
    with open(config_path) as f:
        data = yaml.safe_load(f) or {}
    return data

def get_nested(cfg: dict, dotted: str, default=None) -> Any:
    # config_loader.py:18-25
    # Пример: get_nested(cfg, "live.enabled") → cfg["live"]["enabled"]
```

Функция `get_nested` позволяет обращаться к вложенным настройкам через точечную нотацию: вместо `cfg["section"]["key"]` пишется `get_nested(cfg, "section.key")`. Если ключ не найден — возвращается `default` (по умолчанию `None`).

Этот загрузчик используется для специфических конфигов, не входящих в основной класс `Settings` (например, параметры исследовательских скриптов).

---

## Примеры / сценарии

### Сценарий А: Стандартный старт в тестовой сети

Файл `.env`:
```text
BYBIT_API_KEY=abc12345xyz
BYBIT_API_SECRET=mysecretkey123
RISK_OVERRIDE_HMAC_KEY=thirtytwocharactersminimumforhmac
TESTNET=true
DEMO=false
TRADING_ENABLED=true
LIVE_TRADING=false
DATA_DIR=/data
LOG_DIR=/logs
DB_PATH=/data/trading.db
PARQUET_DIR=/data/parquet
```

Результат: бот запускается, торгует на тестовой бирже Bybit, без реальных денег. Матрица роутинга: `testnet=True, demo=False` → тестовая биржа.

### Сценарий Б: Попытка запустить с реальными деньгами, но без отключения testnet

```text
TESTNET=true        # <-- забыли поменять
LIVE_TRADING=true
TRADING_ENABLED=true
```

Результат — немедленная ошибка при старте:

```text
ValueError: live_trading requires testnet=False (mainnet-only)
```

Бот не запустится. Валидатор `_live_trading_guards` (`src/platform/config.py:252-258`) сработал.

### Сценарий В: Попытка запустить S35 demo на mainnet

```text
S35_DEMO_ACTIVE=true
TESTNET=false       # mainnet endpoint
LIVE_TRADING=false
```

Результат — ошибка:

```text
ValueError: S35 δ TESTNET demo requires testnet=True (Bybit endpoint flag).
testnet=False routes к MAINNET endpoint regardless of live_trading.
```

Даже без `live_trading=True` пара `testnet=False` уже маршрутизирует на mainnet. Валидатор `_validate_s35_demo_mainnet_exclusion` (`src/platform/config.py:260-291`) заблокировал.

### Сценарий Г: Оператор написал символ строчными буквами

```text
S35_DEMO_APPROVED_SYMBOLS=btcusdt
```

Бот автоматически нормализует `btcusdt` → `BTCUSDT` при старте (`src/platform/config.py:303-305`). Никакой ошибки, тихое исправление.

### Сценарий Д: Запрос хэша конфигурации

```python
from src.platform.config import Settings
settings = Settings()
print(settings.config_hash())
# → "a3f4b2c1d5e6..." (64-символьный SHA-256 хэш)
```

Хэш зависит только от риск-параметров. Если поменять `LOG_LEVEL=DEBUG` — хэш не изменится. Если поменять `RISK_CB_L1_DD=0.10` — хэш изменится, и старый override-файл станет недействительным.

---

## Подводные камни / что важно понимать

**1. Порядок валидаторов имеет значение.**
Pydantic v2 запускает `mode="after"` валидаторы в порядке их объявления. Валидатор `_validate_s35_demo_mainnet_exclusion` зависит от того, что `_live_trading_guards` уже отработал. Если переставить их местами — защитная цепочка сломается. Комментарий в коде явно предупреждает: «DO NOT reorder без verifying invariant chain» (`src/platform/config.py:276-277`).

**2. testnet=False — это уже mainnet, даже без live_trading=True.**
Это самая опасная ловушка. `testnet=False` меняет эндпоинт на реальную биржу. Даже если вы установили `TRADING_ENABLED=false`, HTTP-запросы и WebSocket-соединение уже идут на mainnet с реальными учётными данными. Именно поэтому защита от S35 demo на mainnet проверяет **оба** флага независимо.

**3. Ротация API-ключей не ломает operator-override.**
HMAC-ключ `risk_override_hmac_key` отделён от `bybit_api_secret`. Можно поменять API-ключи биржи (например, при компрометации) — файл `cb_override.json` останется валидным, потому что подписан другим ключом.

**4. Нет `.env` → нет запуска.**
Файл `.env` не создаётся автоматически. Если его нет, или в нём не заданы обязательные параметры (`bybit_api_key`, `bybit_api_secret`, `risk_override_hmac_key`, четыре пути) — бот упадёт с ошибкой валидации Pydantic при старте.

**5. validate_assignment защищает и runtime-мутации.**
Если где-то в коде написать `settings.testnet = False` уже после создания объекта `Settings`, валидаторы снова запустятся. Если это изменение нарушает инварианты (например, `s35_demo_active=True` при новом `testnet=False`), возникнет `ValidationError`. Это намеренная защита от «умных обходов» через прямое изменение атрибутов.

**6. require_mainnet_gate_passed — флаг без действия в текущей версии.**
Несмотря на название, этот флаг **не блокирует** запуск на mainnet и не запускает никаких автоматических проверок. Он объявлен в `src/platform/config.py:198`, но ни один другой файл в `src/` его не читает (проверено `grep -rn require_mainnet_gate_passed src/` — только объявление). Startup-валидатор, запланированный ADR 0021 sub-decision 8, не реализован. Единственная реальная защита mainnet — это цепочка `testnet=False` + `trading_enabled=True` + `live_trading=True` и валидаторы из Шага 4.

**7. config_hash содержит только то, что оператор реально читает при override.**
Параметры стратегии (EMA/RSI/ADX периоды) не входят в хэш — не потому что они неважны, а потому что оператор не проверяет их при принятии решения о снятии аварийной остановки. Хэш — это контрольная пломба именно для той части конфигурации, которую оператор явно авторизует.

---

## Связанные документы

Эта страница — «пульт управления»: почти каждый параметр здесь настраивает какую-то подсистему бота. Ниже — куда ведут эти настройки, сгруппировано по смыслу.

**Где эти настройки применяются (жизненный цикл, 01):**

- `[[startup-and-wiring]]` — как готовый объект `Settings` при старте собирается в рабочие компоненты бота
- `[[main-loop-tick]]` — как `runtime_bar_poll_*` и `runtime_kill_switch_path` проверяются на каждом тике цикла
- `[[end-to-end-overview]]` — общая карта потока: где в пути «свеча → сделка» участвуют эти настройки
- `[[run-modes-testnet-live-reconcile]]` — подробно о матрице режимов (testnet/demo/mainnet) и что реально происходит в каждом

**Флаги контура и учётные данные биржи:**

- `[[bybit-order-adapter]]` — потребитель пары `(testnet, demo)`: куда роутятся ордера, и где API-ключ/секрет подписывают запросы
- `[[bybit-rest-client-and-backoff]]` — REST-клиент, который строится из той же пары флагов контура
- `[[bybit-private-websocket]]` — приватный поток; `runtime_ws_check_alive_max_silence` задаёт его сторожевой таймер тишины
- `[[execution-state-machine]]` — FSM ордера, который не увидит подтверждения, если REST и WS собраны из разных флагов

**Параметры стратегии и индикаторы (`strategy_*`):**

- `[[02-стратегии/ema-crossover-strategy|ema-crossover-strategy]]` — стратегия по умолчанию, которую настраивают `strategy_ema/adx/rsi`-параметры
- `[[signal-architecture]]` — как значения индикаторов превращаются в торговый сигнал
- `[[technical-indicators]]` — справочник математики EMA/RSI/ADX/ATR (код-уровень)
- `[[ema-rsi-indicators]]` — концепт EMA и RSI (`strategy_ema_fast/slow`, `strategy_rsi_*`)
- `[[adx-indicator]]` — концепт ADX (`strategy_adx_period`, `strategy_adx_threshold`)
- `[[atr-indicator]]` — концепт ATR (`strategy_atr_period`); ATR также масштабирует стоп/тейк через `risk_sl/tp_atr_multiplier`

**Параметры риска (`risk_*`):**

- `[[safety-stops-and-halts]]` — как circuit breaker и параметры `risk_cb_*` используются для автоматических остановок
- `[[circuit-breakers-drawdown-flash]]` — механика уровней просадки `risk_cb_l1/l2/l3_dd` и флэш-краша `risk_cb_flash_*`
- `[[position-sizing-kelly]]` — как фазы Kelly и `risk_kelly_phase*_cap` определяют размер позиции
- `[[risk-overview-decision-pipeline]]` — общий конвейер риск-менеджера, который читает эти пороги
- `[[equity-tracking]]` — учёт капитала и просадки, на которую реагируют пороги `risk_cb_*`

**Остановки, override и demo-режим (S35):**

- `[[manual-override-resume]]` — как `config_hash()` и HMAC-ключ используются при ручном снятии аварийной остановки
- `[[kill-switch-emergency-stop]]` — как `runtime_kill_switch_path` используется для аварийной остановки
- `[[halt-gate-precommitted-criteria]]` — «красные линии» демо-запуска: пороги `s35_halt_*` и белый список `s35_demo_approved_symbols`

**Исполнение и устойчивость (`oco_*`, `heal_*`):**

- `[[oco-bracket-emulation]]` — как `oco_arming_ttl_seconds` и `oco_dust_threshold_btc` влияют на эмуляцию bracket-ордеров
- `[[emergency-flatten-and-residual]]` — как порог «пыли» `oco_dust_threshold_btc` определяет неторгуемый остаток
- `[[reconcile-as-truth]]` — как `heal_max_bars`/`heal_max_age_seconds` управляют «исцелением» позиции после перезапуска

**Данные, качество и хранилища (`runtime_*`, пути):**

- `[[bar-source-live]]` — механика опроса свечей: `runtime_bar_poll_cadence_seconds`/`runtime_bar_poll_stall_threshold`, `runtime_warmup_bars`
- `[[data-quality-detector]]` — как `runtime_quality_threshold_pct` ограничивает скачок цены между свечами
- `[[storage-and-database]]` — SQLite-база по пути `db_path`
- `[[parquet-storage]]` — хранилище исторических свечей по пути `parquet_dir`
- `[[logging-and-observability]]` — журнал по `log_dir`, `log_level` и интеграция Sentry (`sentry_dsn`)

За техническими деталями ADR: `llm-wiki/wiki/project/decisions/` (ADR 0016, ADR 0018, ADR 0021, ADR 0053).
