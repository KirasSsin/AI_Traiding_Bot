---
title: "Логи и наблюдаемость: как понять, что делает бот"
section: "01-как-работает-бот"
status: filled
money_core: false
updated: 2026-06-26
source_files: src/platform/logging.py, src/runtime/manager.py
---

# Логи и наблюдаемость: как понять, что делает бот

**TL;DR:** Бот ведёт структурированный журнал событий в формате JSON — каждую секунду работы видно, что именно произошло, когда, и почему. Оператор может прочитать лог как газету: каждая строка — отдельное событие с метками.

## Простыми словами

Представьте, что у вашего сотрудника (бота) есть рабочий журнал. Каждый раз, когда он делает что-то важное — получил новую цену, решил отклонить сделку, заметил проблему — он записывает это в журнал. Запись выглядит не как свободный текст («всё нормально»), а как заполненный бланк с чёткими полями: время, тип события, детали.

Такой подход называется **структурированным логированием** (structured logging): каждая запись в журнале — это машинно-читаемый набор полей, а не свободный текст. Это как разница между «произошла сделка» и таблицей с колонками «время», «символ», «цена», «сторона», «причина».

Зачем это нужно?

- **Найти ошибку быстро:** можно отфильтровать только события уровня «ERROR» и увидеть все сбои за последний час.
- **Проследить цепочку:** видно, в какой момент бот получил сигнал, почему [[risk-overview-decision-pipeline|отклонил его]], и что произошло дальше.
- **Автоматический мониторинг:** внешние системы (например, Sentry — сервис для сбора ошибок) могут читать JSON и рассылать уведомления без участия человека.

**JSON** (JavaScript Object Notation) — это стандартный текстовый формат, в котором данные записываются в виде пар «ключ: значение»: `{"event": "bar_tick", "time": "2024-01-15T10:00:00Z"}`. Его одинаково хорошо читают и люди, и программы.

**stdout** (стандартный вывод) — это экран или труба, в которую программа выводит данные. В нашем случае бот пишет туда все логи, а операционная среда (Docker, systemd, терминал) уже решает, куда их дальше направить.

## Как это работает у нас

### Шаг 1. Настройка логирования при запуске

Вся настройка логирования сосредоточена в одной функции `configure_logging()`:

```python
# src/platform/logging.py:10-31
def configure_logging(level: str = "INFO") -> None:
    """Configure structlog + stdlib logging. Idempotent."""
    structlog.reset_defaults()
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level),
    )
    ...
```

Что здесь происходит по шагам:

1. **`structlog.reset_defaults()`** — сбрасывает предыдущие настройки перед повторной конфигурацией. Это делает функцию **идемпотентной** (можно вызвать несколько раз — результат одинаковый, ничего не сломается). `(src/platform/logging.py:12)`
2. **`stream=sys.stdout`** — все сообщения уходят в стандартный вывод. `(src/platform/logging.py:15)`
3. **`level=getattr(logging, level)`** — уровень задаётся параметром, который берётся из настроек. `(src/platform/logging.py:16-17)`

### Шаг 2. Конвейер обработки каждого события

После настройки каждое сообщение проходит через цепочку процессоров — как сборочный конвейер на заводе:

```python
# src/platform/logging.py:20-27
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,      # добавляет контекстные переменные
        structlog.stdlib.add_log_level,                # добавляет поле "level"
        structlog.processors.TimeStamper(fmt="iso", utc=True, key="timestamp"),  # время UTC
        structlog.processors.StackInfoRenderer(),      # трассировка стека (при ошибках)
        structlog.processors.format_exc_info,          # форматирует исключения
        structlog.processors.JSONRenderer(),            # сериализует всё в JSON-строку
    ],
    ...
)
```

Ключевые детали:
- **Временная метка ISO/UTC**: время записывается в международном стандарте ISO 8601 с часовым поясом UTC («Гринвичское время»). Например: `"timestamp": "2024-01-15T10:00:00.123456Z"`. Это позволяет сравнивать события из разных часовых поясов без путаницы. `(src/platform/logging.py:23)`
- **JSON-рендерер**: последний процессор превращает все поля в единую строку JSON. `(src/platform/logging.py:27)`

### Шаг 3. Уровни логирования

**Уровень логирования** (log level) — это фильтр: записывать ли конкретное сообщение. Работает как тумблер громкости:

| Уровень | Что означает | Пример события |
|---------|-------------|----------------|
| `DEBUG` | Детальная отладка (для разработки) | состояние переменной в цикле |
| `INFO` | Штатные события (норма) | бот получил свечу, сделка открыта |
| `WARNING` | Что-то нестандартное, но не сбой | неизвестный код выхода из стратегии |
| `ERROR` | Ошибка, требует внимания | сработал предохранитель, сбой данных |

По умолчанию установлен уровень `INFO` — записываются события уровня INFO, WARNING и ERROR, но не DEBUG. `(src/platform/config.py:109)`

Уровень задаётся в [[configuration-and-settings|настройках]] через переменную окружения `LOG_LEVEL`. Вся цепочка: переменная среды → `settings.log_level` → `configure_logging(level=...)`. `(src/platform/config.py:109, src/platform/logging.py:10)`

### Шаг 4. Как получить логгер в любом модуле

```python
# src/platform/logging.py:34-36
def get_logger(name: str) -> Any:
    """Return a structlog BoundLogger."""
    return structlog.get_logger(name)
```

Каждый модуль создаёт свой логгер, передавая в `name` имя своего модуля через `__name__`. Например, в `manager.py`:

```python
# src/runtime/manager.py:38
logger = get_logger(__name__)
```

`__name__` в Python автоматически принимает значение пути модуля, например `src.runtime.manager`. Это значение используется structlog как внутренняя метка логгера — оно помогает при отладке на уровне Python, но **не попадает в поле JSON-записи**: конвейер `configure_logging()` не включает процессор `add_logger_name` `(src/platform/logging.py:20-26)`, поэтому имя модуля в JSON-строках отсутствует. Чтобы идентифицировать источник события, используйте поле `event` — имя события по соглашению начинается с префикса модуля (`runtime.`, `bybit.` и т.п.).

### Шаг 5. Ключевые события бота в хронологическом порядке

Ниже — все важные события, которые бот пишет в журнал при нормальной работе и в нештатных ситуациях:

#### Запуск

**`bybit.env_resolved`** — первое событие при старте, сразу после [[startup-and-wiring|инициализации]]. Показывает, к какому [[run-modes-testnet-live-reconcile|контуру биржи]] подключился бот (тестовая/боевая) и через какие адреса:

```text
{"event": "bybit.env_resolved", "testnet": false, "demo": false,
 "rest_host": "https://api.bybit.com", "ws_endpoint": "wss://stream.bybit.com/...",
 "level": "info", "timestamp": "2024-01-15T10:00:01.000Z"}
```

Если в этой строке `testnet: false` и `demo: false`, бот работает на реальном рынке с реальными деньгами. Это сделано специально, чтобы ошибку конфигурации можно было заметить в первых же строках лога. `(src/__main__.py:197-203)`

**`runtime.s35_demo_startup_banner`** — баннер старта в демо-режиме. Выводится только если включён режим `s35_demo_active`. Показывает список одобренных символов и [[halt-gate-precommitted-criteria|пороги предохранителей]]. `(src/runtime/manager.py:124-134)`

#### Штатный цикл

**`runtime.bar_tick`** — каждый раз, когда бот в [[main-loop-tick|главном цикле]] получает и принимает новую завершённую свечу (т.е. ценовой бар за период). Содержит `bar_close_ts` — время закрытия свечи в ISO/UTC:

```text
{"event": "runtime.bar_tick", "bar_close_ts": "2024-01-15T10:59:00Z",
 "level": "info", ...}
```

`(src/runtime/manager.py:345)`

**`runtime.signal_rejected`** — сигнал от стратегии отклонён менеджером рисков. Содержит `side` (направление: Long) и [[reason-codes-assessment-output|`reason_code`]] (причина отклонения, например [[position-sizing-kelly|`RISK_KELLY_PHASE_1`]]). Это нормальная ситуация — риск-модуль работает как фильтр:

```text
{"event": "runtime.signal_rejected", "side": "SignalSide.LONG",
 "reason_code": "RISK_KELLY_PHASE_1", "level": "info", ...}
```

`(src/runtime/manager.py:382-386)`

**`runtime.signal_skipped_non_flat_state`** — сигнал пришёл, но бот уже в позиции (не в состоянии «плоском», т.е. без открытых сделок). Пропускается с уровнем DEBUG. `(src/runtime/manager.py:374-378)`

**`runtime.exit_signal_flatten`** — стратегия выдала сигнал на выход, и бот закрывает позицию. Содержит `reason` (код причины выхода) и `current_state` (текущее состояние [[execution-state-machine|FSM]]):

```text
{"event": "runtime.exit_signal_flatten", "reason": "EXIT_FLAT_MEANREV_REVERT",
 "current_state": "LONG_OPEN", "level": "info", ...}
```

`(src/runtime/manager.py:365-370)`

#### Нештатные ситуации

**`runtime.kill_switch_detected`** — обнаружен [[kill-switch-emergency-stop|файл-рубильник]] (sentinel-файл) на диске. Бот немедленно останавливается. Содержит `sentinel_path` — путь к файлу:

```text
{"event": "runtime.kill_switch_detected",
 "sentinel_path": "/var/bot/.kill_switch", "level": "info", ...}
```

`(src/runtime/manager.py:289-292)`

**`runtime.halt_gate_fired`** — сработал [[safety-stops-and-halts|предохранитель]] ([[halt-gate-precommitted-criteria|HaltGate]]). Содержит полную диагностику: `trigger` (что именно сработало), `intraday_dd` ([[circuit-breakers-drawdown-flash|просадка за день]]), `multiday_dd` (просадка за несколько дней), `consecutive_losses` (серия убытков подряд), `months_since` (месяцев без сделок). Уровень ERROR:

```text
{"event": "runtime.halt_gate_fired", "trigger": "DD_INTRADAY",
 "reason": "HALT_S36_DD_INTRADAY", "symbol": "BTCUSDT",
 "intraday_dd": "0.21", "multiday_dd": "0.05",
 "consecutive_losses": 2, "months_since": 0, "level": "error", ...}
```

`(src/runtime/manager.py:272-281)`

**`runtime.halt_gate_unknown_symbol`** — символ, которым торгует бот, не входит в список одобренных. Аварийная остановка. `(src/runtime/manager.py:201-205)`

**`runtime.halt_gate_activation_ts_tampered`** — HMAC-подпись временной метки активации не прошла проверку (файл мог быть изменён вручную). Останавливается по принципу «fail-closed» (при сомнении — остановиться, а не продолжить). `(src/runtime/manager.py:220-224)`

**`runtime.bar_poll_stall`** — бот не может получить данные с биржи несколько раз подряд (см. [[bar-source-live|источник свечей в live-режиме]]). Содержит `consecutive_failures` и `threshold`. Уровень ERROR:

```text
{"event": "runtime.bar_poll_stall", "consecutive_failures": 5,
 "threshold": 5, "level": "error", ...}
```

`(src/runtime/manager.py:328-333)`

**`runtime.crash`** — необработанное исключение в главном цикле. Записывается с уровнем `exception` (содержит полный стек вызовов). Содержит `exc_type` и `exc_msg`. После записи бот запрашивает остановку и пробрасывает исключение дальше:

```text
{"event": "runtime.crash", "exc_type": "ConnectionError",
 "exc_msg": "Connection refused", "level": "error", ...}
```

`(src/runtime/manager.py:142-147)`

#### Завершение

**`runtime.shutdown`** — финальная запись при любом завершении работы. Содержит `reason` (причину: `NORMAL_EXIT`, `KEYBOARD_INTERRUPT`, `HALT_RUNTIME_CRASH`) и `in_flight_orders` (количество ордеров, которые могли быть в процессе исполнения):

```text
{"event": "runtime.shutdown", "reason": "NORMAL_EXIT",
 "in_flight_orders": 0, "level": "info", ...}
```

`(src/runtime/manager.py:441)`

**`runtime.exit_reason_unmapped`** — предупреждение: стратегия передала код выхода, который не зарегистрирован в системе. Бот применяет резервный код `EXIT_SIGNAL_FLIP` и не падает. `(src/runtime/manager.py:316)`

### Sentry как точка расширения

В настройках есть поле `sentry_dsn` (адрес подключения к сервису Sentry). Sentry — это внешняя система, которая собирает ошибки и отправляет уведомления разработчику:

```python
# src/platform/config.py:108
sentry_dsn: str | None = None
```

Значение `None` (по умолчанию) означает, что Sentry не подключён. Если указать DSN (строку подключения к вашему аккаунту Sentry), все события уровня ERROR автоматически начнут туда отправляться. Это точка расширения — интеграция с Sentry в текущей версии требует добавления вызова `sentry_sdk.init()` при старте.

## Примеры / сценарии

### Сценарий 1: Нормальный цикл с одной свечой

Бот работает, пришла новая свеча, стратегия выдала сигнал, риск-модуль его одобрил:

```text
{"event": "runtime.bar_tick", "bar_close_ts": "2024-01-15T10:59:00Z", "level": "info", "timestamp": "2024-01-15T11:00:01.023Z"}
```

Следующие события — в модулях [[coordinator-orchestration|coordinator]], bybit — отличаются именем события: `src.execution.coordinator` использует свои имена событий с префиксом `bybit.` или другим, идентифицирующим источник.

### Сценарий 2: Стратегия хочет войти, но риск-модуль отказывает

```text
{"event": "runtime.bar_tick", "bar_close_ts": "2024-01-15T11:59:00Z", "level": "info", ...}
{"event": "runtime.signal_rejected", "side": "SignalSide.LONG", "reason_code": "RISK_KELLY_PHASE_1", "level": "info", ...}
```

Из этой пары строк ясно: свеча пришла, стратегия хотела войти в длинную позицию, но риск-модуль отказал на основании первой фазы Kelly (недостаточно торговой истории для расчёта оптимального размера позиции).

### Сценарий 3: Сработал предохранитель дневной просадки

```text
{"event": "runtime.halt_gate_fired", "trigger": "DD_INTRADAY", "reason": "HALT_S36_DD_INTRADAY", "symbol": "BTCUSDT", "intraday_dd": "0.2100", "multiday_dd": "0.0300", "consecutive_losses": 3, "months_since": 0, "level": "error", ...}
{"event": "runtime.shutdown", "reason": "NORMAL_EXIT", "in_flight_orders": 0, "level": "info", ...}
```

Из первой строки видно: бот превысил дневной лимит просадки (21%), сработал триггер `DD_INTRADAY`. Из второй — бот завершился. Обратите внимание: `reason` равен `"NORMAL_EXIT"`, а не `"HALT"` — предохранитель штатно установил флаг остановки, цикл вышел нормально (без исключения), поэтому `run()` попал в ветку `else`. Реальный код причины (`HALT_S36_DD_INTRADAY`) хранится только в [[storage-and-database|базе данных]] (см. также [[execution-state-persistence-and-halt-audit|журнал аварийных остановок]]).

### Сценарий 4: Первые строки при запуске — сверяем конфигурацию

При каждом запуске первое событие — `bybit.env_resolved`. Это сигнал оператору: «я смотрю именно туда». Если увидите `"testnet": false, "demo": false` — бот работает на боевой бирже. Если `"testnet": true` — на тестовой.

## Подводные камни / что важно понимать

**1. Лог пишется в stdout, а не в файл автоматически.**
По умолчанию `stream=sys.stdout` `(src/platform/logging.py:15)`. Если вы запускаете бота без перенаправления (`python -m src > bot.log`), логи просто пропадут при закрытии терминала. Настройте сохранение через systemd, Docker или явное перенаправление.

**2. Уровень DEBUG показывает пропущенные сигналы.**
Событие `runtime.signal_skipped_non_flat_state` (когда бот уже в позиции) пишется на уровне `DEBUG` `(src/runtime/manager.py:374)`. При стандартном уровне `INFO` его не видно. Если хотите понять, почему бот «молчит», временно переключите на `LOG_LEVEL=DEBUG`.

**3. Идемпотентность — это не случайность.**
`structlog.reset_defaults()` `(src/platform/logging.py:12)` вызывается намеренно перед каждой конфигурацией. Это позволяет тестам вызывать `configure_logging()` несколько раз без побочных эффектов. В тестах `(tests/unit/test_logging.py:8)` именно так и происходит.

**4. В JSON нет поля `logger` с именем модуля.**
Конвейер `configure_logging()` не включает процессор `structlog.stdlib.add_logger_name` `(src/platform/logging.py:20-26)`, поэтому имя модуля (например, `src.runtime.manager`), передаваемое в `get_logger(__name__)`, в JSON-запись **не попадает**. Для фильтрации событий по источнику используйте поле `event`: например, все события `runtime.*` генерируются в `src/runtime/manager.py`. Тест `tests/unit/test_logging.py` явно проверяет наличие только полей `event`, `level`, `timestamp` — поле `logger` в нём отсутствует.

**5. Событие `runtime.crash` не финальное.**
После записи `runtime.crash` бот ещё выполняет `_shutdown()`, которая пишет `runtime.shutdown`. Ищите обе строки при анализе аварий.

**6. `in_flight_orders` в `runtime.shutdown` — снимок, не гарантия.**
Это best-effort счётчик: берётся из FSM-состояния в момент shutdown. Если ордер уже ушёл на биржу, но FSM ещё не обновилась — счётчик покажет 0. Для точного аудита используйте базу данных (таблицу ордеров).

**7. Sentry DSN не активируется автоматически.**
Наличие `sentry_dsn` в конфиге `(src/platform/config.py:108)` — это точка расширения, а не работающая интеграция «из коробки». В текущем коде отсутствует вызов `sentry_sdk.init()`. Для активации нужна дополнительная реализация.

**8. Временная метка — всегда UTC.**
`fmt="iso", utc=True` `(src/platform/logging.py:23)` гарантирует, что время никогда не зависит от системного часового пояса сервера. Всегда сравнивайте события с UTC-временем.

**9. Kill-switch → `reason: "NORMAL_EXIT"` в логе, а не `"KILL_SWITCH"`.**
Это контринтуитивный момент. При срабатывании файла-рубильника `_maybe_kill_switch()` устанавливает флаг остановки, цикл завершается штатно — и `_shutdown()` вызывается из ветки `else:` метода `run()` с `reason="NORMAL_EXIT"`. Строки `"KILL_SWITCH"` как причины завершения в логах не существует. Информация о рубильнике хранится в двух местах: событие `runtime.kill_switch_detected` (с `sentinel_path`) — в логе, и код `KILL_SWITCH_REQUESTED` — в базе данных (колонка `halt_reason`). Ищите пару: `kill_switch_detected` + `shutdown reason=NORMAL_EXIT`, а не одно событие. `(src/runtime/manager.py:286-295, 138-151)`

## Связанные документы

- [[main-loop-tick]] — подробная схема одного тика: в каком порядке возникают события и какие логи за что отвечают
- [[safety-stops-and-halts]] — что происходит после `runtime.halt_gate_fired`: механика предохранителей и коды остановки
- [[kill-switch-emergency-stop]] — как создать файл-рубильник и что именно записывает бот при его обнаружении
- [[startup-and-wiring]] — последовательность событий при старте, включая `bybit.env_resolved`
- [[configuration-and-settings]] — где задаётся `log_level` и `sentry_dsn`, допустимые значения
- [[reason-codes-assessment-output]] — все коды `reason_code` в `runtime.signal_rejected` и `runtime.halt_gate_fired`
- [[end-to-end-overview]] — общая карта потока бота; логи — это её прижизненный след, событие за событием
- [[run-modes-testnet-live-reconcile]] — что означают `testnet`/`demo` в `bybit.env_resolved` и почему это первая строка лога
- [[risk-overview-decision-pipeline]] — почему возникает `runtime.signal_rejected`: путь сигнала через риск-менеджер
- [[position-sizing-kelly]] — расшифровка причины `RISK_KELLY_PHASE_1` из события отклонения сигнала
- [[circuit-breakers-drawdown-flash]] — механизм за полями `intraday_dd`/`multiday_dd` в `runtime.halt_gate_fired`
- [[halt-gate-precommitted-criteria]] — сам HaltGate, чьи срабатывания попадают в лог как `halt_gate_fired` и демо-баннер
- [[execution-state-machine]] — источник поля `current_state` (`LONG_OPEN` и др.) и счётчика `in_flight_orders`
- [[coordinator-orchestration]] — модуль `src.execution.coordinator`, пишущий события исполнения с префиксом `bybit.`
- [[bybit-order-adapter]] — откуда берутся события с префиксом `bybit.` (в т.ч. `bybit.env_resolved`)
- [[bar-source-live]] — что стоит за `runtime.bar_poll_stall`: polling свечей в live и порог зависания фида
- [[bar-model]] — что за объект «завершённая свеча» стоит за `runtime.bar_tick` и полем `bar_close_ts`
- [[storage-and-database]] — контраст: лог = поток событий, а точные коды (`halt_reason`) и аудит сделок — в базе
- [[execution-state-persistence-and-halt-audit]] — журнал аварийных остановок в БД: точный источник истины vs. best-effort `in_flight_orders` в логе

> За техническими деталями structlog-конфигурации: `llm-wiki/wiki/project/components/`
