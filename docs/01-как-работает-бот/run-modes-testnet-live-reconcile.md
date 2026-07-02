---
title: "Режимы запуска: безопасный TESTNET, демо-мейннет и реальная торговля"
section: "01-как-работает-бот"
status: filled
updated: 2026-06-27
money_core: true
source_files: src/platform/config.py, src/__main__.py
---

# Режимы запуска: безопасный TESTNET, демо-мейннет и реальная торговля

**TL;DR:** Бот из коробки настроен на безопасную тестовую сеть биржи (TESTNET) — там используются ненастоящие монеты. Переключение на реальную торговлю требует явно поменять три флага и пройти несколько встроенных проверок безопасности, которые нельзя обойти.

---

## Простыми словами

Представьте, что вы учитесь водить машину. Сначала тренируются на закрытом полигоне, потом на дорогах общего пользования в сопровождении инструктора, и только потом самостоятельно на реальных дорогах.

У биржи Bybit есть точно такая же система:

- **TESTNET (полигон)** — отдельная площадка биржи, где торгуются «игрушечные» монеты. Ордера настоящие, логика настоящая, но деньги ненастоящие. Это то, где бот работает **по умолчанию**.
- **Демо на мейннете (инструктор)** — реальная инфраструктура биржи, но вместо ваших денег используется виртуальный баланс, предоставленный биржей. Комфортнее по условиям, чем TESTNET, но требует осознанного включения.
- **MAINNET (реальные дороги)** — настоящая биржа с настоящими деньгами. Включается только после того, как оператор явно и сознательно снимает все предохранители.

Принципиально важно понять одну вещь: **контур биржи** — это не просто адрес сервера. Это целая «вселенная» аккаунтов, ордеров и сделок. Ордер, отправленный в TESTNET, и подтверждение о его исполнении, пришедшее из MAINNET — это как написать письмо в Петербург и ожидать ответа из Москвы. Бот «не увидит» свою сделку и зависнет.

Именно поэтому в коде есть жёсткое правило: и ордера (REST-запросы), и уведомления об исполнении (WebSocket) **обязаны** строиться из одной и той же пары флагов.

---

## Как это работает у нас

### Шаг 1. Два флага определяют всё — матрица четырёх контуров

Весь выбор «куда реально уходят ордера» определяется **одной парой флагов** в конфигурации: `testnet` и `demo`.

Вот полная матрица (`src/platform/config.py:69-73`):

| `testnet` | `demo` | Куда уходят ордера | Деньги настоящие? |
|-----------|--------|--------------------|-------------------|
| `True`    | `False` | api-testnet / stream-testnet | НЕТ (тестовые монеты) |
| `False`   | `True`  | api-demo / stream-demo | НЕТ (виртуальный баланс Bybit) |
| `True`    | `True`  | api-demo-testnet / stream-demo-testnet | НЕТ (демо на testnet) |
| `False`   | `False` | api / stream | **ДА — реальный MAINNET** |

По умолчанию в коде: `testnet = True` (строка 63), `demo = False` (строка 76-85). Значит, бот «из коробки» работает в первой строке таблицы — тестовая биржа, ненастоящие деньги.

### Шаг 2. REST и WebSocket обязаны жить в одном контуре (BYBIT-01)

Это важнейшее техническое ограничение, из-за нарушения которого нельзя было бы увидеть свои сделки.

В `_cmd_run()` и `_cmd_reconcile_only()` [[bybit-rest-client-and-backoff|REST-клиент]] и [[bybit-private-websocket|WebSocket-потребитель]] получают **ту же самую пару** `(testnet, demo)` из единого источника — объекта `Settings`:

```python
# REST-клиент (src/__main__.py:108-113)
rest = BybitRESTClient(
    api_key=settings.bybit_api_key,
    api_secret=settings.bybit_api_secret,
    testnet=settings.testnet,
    demo=settings.demo,
)

# WebSocket-потребитель (src/__main__.py:182-191)
ws_consumer = BybitPrivateWSConsumer(
    api_key=settings.bybit_api_key,
    api_secret=settings.bybit_api_secret,
    endpoint=ws_endpoint,
    coordinator=coordinator,
    reconciler=reconciler,
    fill_recorder=fill_recorder,
    testnet=settings.testnet,   # та же пара из Settings
    demo=settings.demo,         # та же пара из Settings
)
```

Никакого ручного задания адреса сервера — библиотека pybit сама выбирает нужный хост по паре флагов. Это исключает возможность случайно «разъехаться» по контурам.

### Шаг 3. Метка WS-хоста — как по логам понять контур

Функция `_ws_endpoint_label()` (`src/__main__.py:229-248`) вычисляет человекочитаемую строку с адресом WebSocket-сервера — исключительно для логов. По ней в первых строках лога сразу видно, в каком контуре работает бот:

```python
def _ws_endpoint_label(*, testnet: bool, demo: bool) -> str:
    if demo:
        subdomain = "stream-demo-testnet" if testnet else "stream-demo"
    else:
        subdomain = "stream-testnet" if testnet else "stream"
    return f"wss://{subdomain}.bybit.com/v5/private"
```

Что увидит оператор в логе при старте (по умолчанию, `testnet=True, demo=False`):

```json
{"event": "bybit.env_resolved", "testnet": true, "demo": false, "rest_host": "https://api-testnet.bybit.com", "ws_endpoint": "wss://stream-testnet.bybit.com/v5/private", "level": "info", "timestamp": "2026-06-27T10:00:00Z"}
```

[[logging-and-observability|Логи]] всегда в формате JSON-строки — по одной на событие (`src/platform/logging.py:26`: единственный рендерер `JSONRenderer()`). Поле `rest_host` — это полный URL с `https://`, который возвращает `rest.endpoint` (через `pybit._http_manager`). Поле `ws_endpoint` — строка из `_ws_endpoint_label()`.

Это сделано специально: если оператор увидит `"stream.bybit.com"` (без `-testnet`), значит, бот вышел в реальный MAINNET — и это должно быть заметно сразу. (`src/__main__.py:197-203`)

### Шаг 4. Флаги реальной торговли — двойная блокировка

Помимо пары `(testnet, demo)`, есть ещё два флага: `trading_enabled` и `live_trading`. Оба по умолчанию `False` (`src/platform/config.py:88-89`).

Чтобы включить реальную торговлю, нужны **одновременно** три условия — это жёстко проверяет валидатор `_live_trading_guards()` при каждом создании конфигурации (`src/platform/config.py:252-258`):

```python
@model_validator(mode="after")
def _live_trading_guards(self) -> "Settings":
    if self.live_trading and not self.trading_enabled:
        raise ValueError("live_trading requires trading_enabled=True")
    if self.live_trading and self.testnet:
        raise ValueError("live_trading requires testnet=False (mainnet-only)")
    return self
```

Таблица барьеров:

| Что нужно проверить | Значение для реального MAINNET |
|---------------------|-------------------------------|
| `testnet` | `False` (иначе — тестовая сеть) |
| `trading_enabled` | `True` (основной рубильник) |
| `live_trading` | `True` (явное подтверждение) |

Если попытаться включить `live_trading=True`, но оставить `testnet=True` — конфигурация упадёт с ошибкой ещё на старте. Бот просто не запустится.

**Важный нюанс:** флаг `validate_assignment=True` (`src/platform/config.py:53-57`) означает, что эти проверки срабатывают не только при создании конфигурации, но и при попытке изменить любой флаг «на лету» уже после запуска. Обойти защиту через `settings.live_trading = True` в коде невозможно.

### Шаг 5. Демо-режим S35 — только для TESTNET, с двойным барьером

Флаг `s35_demo_active` — это специальный режим длительного тестирования на тестовой сети (`src/platform/config.py:123-131`). Когда он включён, система активирует дополнительные правила защиты капитала — [[halt-gate-precommitted-criteria|HaltGate]]-пороги просадки и лимиты убытков.

По специальному ADR 0053, этот режим **запрещён на MAINNET** — и запрет защищён двумя независимыми проверками в валидаторе `_validate_s35_demo_mainnet_exclusion()` (`src/platform/config.py:260-291`):

```python
# Проверка 1: запрет live_trading (флаг реального MAINNET)
if self.s35_demo_active and self.live_trading:
    raise ValueError("S35 δ TESTNET demo cannot run на MAINNET (live_trading=True)...")

# Проверка 2: запрет testnet=False (биржевой endpoint MAINNET)
if self.s35_demo_active and not self.testnet:
    raise ValueError("S35 δ TESTNET demo requires testnet=True (Bybit endpoint flag)...")
```

Почему две проверки, а не одна? Потому что `testnet=False` само по себе уже направляет ордера в реальный MAINNET — даже если `live_trading=False`. Обе ситуации блокируются независимо.

### Шаг 6. Флаг require_mainnet_gate_passed — метка-заглушка (не активный блок)

В конфигурации есть поле `require_mainnet_gate_passed = True` (`src/platform/config.py:198-201`) — с намерением: «пока не пройдены Phase G testnet probes (проверочные прогоны на testnet), переход на MAINNET должен быть заблокирован» (ADR 0021 sub-decision 8).

**Однако этот флаг в текущей версии v0.1 не реализован как блок.** Grep по всему `src/` возвращает ровно одно вхождение — само определение поля. Ни одного валидатора, ни одной runtime-проверки, которая читала бы этот флаг и что-то ограничивала, в коде нет. Когда флаг `True` — он ничего не делает. Когда `False` — тоже ничего не делает.

Единственные реальные барьеры сегодня — это описанные выше тройная блокировка `(testnet, trading_enabled, live_trading)` и двойная проверка `_live_trading_guards()`. Флаг `require_mainnet_gate_passed` — информационная метка, зарезервированная для будущей реализации в v0.2.

---

## Примеры / сценарии

### Сценарий А: обычный запуск «из коробки»

Оператор не менял ни одного флага. В `.env` только ключи API и обязательный HMAC-ключ.

1. Конфигурация создаётся: `testnet=True`, `demo=False`, `trading_enabled=False`, `live_trading=False`.
2. REST-клиент строится с `testnet=True, demo=False` → направлен в `https://api-testnet.bybit.com`.
3. WS-потребитель строится с теми же флагами → `wss://stream-testnet.bybit.com/v5/private`.
4. В логе (JSON-строка): `{"event": "bybit.env_resolved", "testnet": true, "demo": false, "rest_host": "https://api-testnet.bybit.com", "ws_endpoint": "wss://stream-testnet.bybit.com/v5/private", "level": "info", ...}`
5. Бот работает в тестовой сети. Никаких реальных денег.

### Сценарий Б: демо на мейннете (виртуальный баланс, реальная инфраструктура)

Оператор выставил `TESTNET=false` и `DEMO=true` в `.env`.

1. Конфигурация: `testnet=False`, `demo=True`, `trading_enabled=False`, `live_trading=False`.
2. REST-клиент → `api-demo.bybit.com` (MAINNET-demo, виртуальный баланс).
3. WS-потребитель → `wss://stream-demo.bybit.com/v5/private`.
4. В логе (JSON): `{"event": "bybit.env_resolved", "testnet": false, "demo": true, "rest_host": "https://api-demo.bybit.com", "ws_endpoint": "wss://stream-demo.bybit.com/v5/private", "level": "info", ...}`
5. Ордера уходят в Bybit demo-аккаунт — денег не тратится, но условия ближе к реальным.

**Важно:** `s35_demo_active=True` в этом сценарии запрещён — `testnet=False` при включённом S35-демо вызовет ошибку на старте.

### Сценарий В: попытка включить реальную торговлю без снятия testnet

Оператор поставил `LIVE_TRADING=true` и `TRADING_ENABLED=true`, но забыл поменять `TESTNET=false`.

```
ValueError: live_trading requires testnet=False (mainnet-only)
```

Бот не запустится вообще. Это именно то поведение, которое задумано: нельзя «случайно» выйти в MAINNET.

### Сценарий Г: реальный MAINNET (все три предохранителя сняты)

Оператор осознанно выставил `TESTNET=false`, `TRADING_ENABLED=true`, `LIVE_TRADING=true`.

1. Конфигурация проходит все валидаторы.
2. REST-клиент → `api.bybit.com` (реальный MAINNET).
3. WS-потребитель → `wss://stream.bybit.com/v5/private`.
4. В логе (JSON): `{"event": "bybit.env_resolved", "testnet": false, "demo": false, "rest_host": "https://api.bybit.com", "ws_endpoint": "wss://stream.bybit.com/v5/private", "level": "info", ...}`
5. Ордера уходят на реальную биржу с реальными деньгами.

---

## Подводные камни / что важно понимать

**1. `demo=True` с `testnet=False` — это MAINNET-инфраструктура.**
Несмотря на слово «демо» и виртуальный баланс, ордера и WebSocket-соединение идут через реальные серверы MAINNET. Это значит: ключи API в этом режиме проходят аутентификацию на боевой бирже. Убедитесь, что ключи не имеют лишних прав (например, право на вывод средств).

**2. «Разъезд» REST и WS — тихая ошибка, а не падение.**
Если бы ордера уходили в один контур, а подтверждения об исполнении приходили из другого, бот не упал бы с ошибкой — он просто никогда не «увидел» бы свои сделки. Эта ситуация была зафиксирована как BYBIT-01 и закрыта в S55: теперь оба клиента строятся из единого источника `Settings`. Но если кто-то изменит код и сломает эту связку — диагностировать будет крайне сложно. (`src/__main__.py:105-113, 177-191`)

**3. Защита не даёт обойти её после запуска.**
Благодаря `validate_assignment=True`, попытка изменить любой из флагов конфигурации в runtime (например, через `settings.live_trading = True` в коде) пройдёт через те же самые валидаторы. Это закрывает класс атак «подмени настройку после инициализации». (`src/platform/config.py:53-57`)

**4. Порядок валидаторов важен.**
Валидатор `_validate_s35_demo_mainnet_exclusion` рассчитывает на то, что `_live_trading_guards` уже отработал (внутренний комментарий: `src/platform/config.py:275`). В Pydantic v2 с `mode="after"` валидаторы запускаются в порядке объявления. Перестановка этих методов нарушит инвариант безопасности.

**5. Флаг `require_mainnet_gate_passed` — задокументированное намерение, не реальный блок.**
Поле объявлено в конфигурации (`src/platform/config.py:198-201`) с намерением в будущем (v0.2) заблокировать переход на MAINNET до прохождения тестовых прогонов (ADR 0021 sub-decision 8). В текущем v0.1 флаг нигде не читается и ничего не блокирует — ни один валидатор, ни одна проверка в рантайме с ним не работают. Реальные барьеры перед MAINNET — только тройка `(testnet=False, trading_enabled=True, live_trading=True)`, которую проверяет `_live_trading_guards()`.

**6. S35-демо и `testnet=False` несовместимы, даже если `live_trading=False`.**
Казалось бы, раз реальная торговля выключена, `testnet=False` не страшен. Но библиотека pybit маршрутизирует ордера по паре `(testnet, demo)` независимо от `live_trading`. Поэтому `testnet=False` уже направляет API-вызовы в MAINNET-endpoint, и S35-демо это запрещает двумя отдельными проверками. (`src/platform/config.py:268-291`)

---

## Связанные документы

- [[startup-and-wiring]] — полная картина запуска бота: как из Settings строится всё дерево зависимостей (REST → WS → Coordinator → RuntimeManager)
- [[configuration-and-settings]] — все параметры конфигурации подробно: стратегия, риск, пути, Sentry
- [[safety-stops-and-halts]] — как HaltGate использует пороги S35-демо (dd_intraday, consecutive_losses) для остановки
- [[reconcile-and-monitor-commands]] — команды reconcile-only и monitor, которые тоже строят клиентов из той же пары (testnet, demo)
- [[end-to-end-overview]] — общая схема: как режим запуска влияет на весь жизненный цикл бота
- [[bybit-rest-client-and-backoff]] — REST-клиент, который получает пару `(testnet, demo)` и выбирает боевой/тестовый хост Bybit
- [[bybit-private-websocket]] — приватный WebSocket-потребитель, обязанный жить в том же контуре, что и REST (ядро правила BYBIT-01)
- [[coordinator-orchestration]] — Coordinator, в который вплетаются REST и WS: единый контур критичен, чтобы он «видел» исполнения своих ордеров
- [[reconcile-as-truth]] — принцип «биржа всегда права»: сверка возможна только когда клиенты смотрят в один и тот же контур
- [[halt-gate-precommitted-criteria]] — HaltGate: заранее оговорённые красные линии S35-демо, которые активируются флагом `s35_demo_active`
- [[circuit-breakers-drawdown-flash]] — автоматические предохранители по просадке; работают вместе с S35-демо порогами в тестовом контуре
- [[kill-switch-emergency-stop]] — аварийный стоп-файл: последняя линия защиты независимо от выбранного контура
- [[logging-and-observability]] — как читать JSON-лог `bybit.env_resolved`, по которому виден активный контур биржи
- [[main-loop-tick]] — рабочий цикл, который выполняется внутри выбранного режима запуска
- [[storage-and-database]] — где хранятся данные и сделки при работе бота в любом из контуров
- [[testnet-only-status]] — почему проект сейчас живёт только на TESTNET и не выходит в MAINNET
- [[infrastructure-ready-no-edge]] — контекст: инфраструктура MAINNET готова, но прибыльной стратегии для реального контура не найдено
- [[what-is-this-bot]] — вводная страница: что это за бот и зачем ему разделение контуров биржи

За техническими деталями BYBIT-01 и историей исправления: `llm-wiki/wiki/project/components/bybit-ws-consumer.md`
