# Глубинное ревью (КОРРЕКТНОСТЬ vs код): end-to-end-overview.md

**Страница:** `docs/01-как-работает-бот/end-to-end-overview.md` (money_core: src/__main__.py, src/runtime/manager.py, src/runtime/bar_source.py)
**Дата:** 2026-06-27
**Verdict:** REQUEST_CHANGES
**BLOCKER: 1 | WARN: 3 | DEEP: 1 | recomputed: 3 числовых сверки (ATR SL/TP, stall 24×5=120s, 24>=threshold)**

Эта страница — «брат» startup-and-wiring.md (те же money_core источники), но заметно ЧИЩЕ: она НЕ повторяет два BLOCKER'а startup-and-wiring (Ctrl+C exit=130 и shutdown reason=KILL_SWITCH). Шаг 10 и Сценарий C сформулированы корректно. Единственный фактический BLOCKER — описание персистентности сделок в Шаге 9.

---

## BLOCKER 1 — Шаг 9: «FillRecorderAdapter записывает каждую закрытую сделку в `trade_history`» — неверно по трём пунктам

**Текст (строка 173):**
> «Результат каждой закрытой сделки записывается в таблицу `trade_history` в базе данных — через `FillRecorderAdapter` (`src/risk/fill_recorder_adapter.py`). Это журнал для аудита и расчёта статистики стратегии.»

**Что на самом деле в коде:**

1. **Неверный компонент.** `FillRecorderAdapter` НЕ пишет в `trade_history`. Он лишь ЧИТАЕТ `trade_history_repo.find_trade_id_by_signal(...)` (fill_recorder_adapter.py:128) чтобы получить `parent_trade_id`. Запись он делает через `FillHistoryRepository.insert_fill(...)` (fill_recorder_adapter.py:138).

2. **Неверная таблица.** `insert_fill` пишет в таблицу **`trade_fills`** (`migrations/0006_trade_fills.sql:7 CREATE TABLE trade_fills`), а НЕ в `trade_history` (это отдельная таблица — `migrations/002_risk.sql:4 CREATE TABLE trade_history`). Это per-fill гранулярность (детали каждого частичного исполнения), а не «итог закрытой сделки».

3. **Путь в v0.1 фактически мёртв.** Module docstring fill_recorder_adapter.py:9-17 прямо говорит: `ExecutionStateRow` НЕ имеет колонки `entry_signal_id` (проверены migrations 0003/0004/0005), поэтому цепочка резолва обрывается. В коде fill_recorder_adapter.py:119-126: `entry_signal_id = getattr(state_row, "entry_signal_id", None)` → всегда `None` → всегда `return` с предупреждением `fill_event_unresolved_skipping_db: ... schema link missing (deferred к S13)`. То есть `insert_fill` НИКОГДА не вызывается в текущей схеме. Работает только Layer-1 structlog-аудит (`fill_event_received`, :83). Полная DB-персистентность отложена до S13+.

4. **Реальный писатель `trade_history` не вызывается в live-пути.** `trade_history` пишется через `RiskManager.record_closed_trade → insert_closed_trade` (manager.py:318-319). Но `grep` по всему `src/` показывает: `record_closed_trade` / `insert_closed_trade` НЕ вызываются нигде в live-runtime (только определения + упоминания в docstring; НЕ вызываются из `src/execution/`, координатора, WS). То есть в v0.1 live-runtime закрытые сделки в `trade_history` фактически не попадают по описанному механизму.

**Почему BLOCKER:** не-программист поверит, что каждая закрытая сделка автоматически ложится в `trade_history` через FillRecorderAdapter (для статистики/аудита). Обе половины утверждения ложны (не тот компонент + не та таблица), а сама персистентность в v0.1 не происходит как описано. Это money_core поведение (куда уходят результаты сделок).

**Как чинить (варианты):**
- Если цель — описать что реально происходит: «Каждое исполнение (fill) от биржи логируется в structlog-аудит (`fill_event_received`) через `FillRecorderAdapter`. Полная запись в БД (`trade_fills`) — частичная и в v0.1 отложена (нужна миграция схемы, S13+).»
- Убрать упоминание `trade_history` в связке с FillRecorderAdapter ИЛИ явно пометить как планируемое (deferred S13+), не как текущее поведение.
- Не утверждать «результат каждой закрытой сделки записывается» без оговорки, что в v0.1 этот путь не активен.

---

## DEEP 1 — Шаг 9: FSM-переход «LONG_OPEN → OCO_ARMED» пропускает промежуточное OCO_ARMING

**Текст (строка 169):** «2. Переводит состояние в LONG_OPEN → OCO_ARMED.»

Реальная цепочка вооружения OCO (state_machine.py):
- `ENTRY_FILLED`: `(ENTRY_PENDING → LONG_OPEN)` (строка 74)
- `TP_PLACED`: `(LONG_OPEN → OCO_ARMING)` (строка 104)
- `SL_PLACED`: `(OCO_ARMING → OCO_ARMED)` (строка 105)

Доковское «LONG_OPEN → OCO_ARMED» схлопывает промежуточное **OCO_ARMING**. Это допустимое упрощение (страница сама перечисляет OCO_ARMING в Шаге 5 как состояние с открытой позицией, и в `_FLATTENABLE_STATES`), но строго говоря пропущено состояние. Не BLOCKER, но точнее было бы «LONG_OPEN → OCO_ARMING → OCO_ARMED».

---

## WARN 1 — Pitfall 2: цитата RLock указывает на docstring, а не на сам lock

**Текст (строка 247):** «...через Coordinator, который защищён блокировкой (RLock)... (`coordinator.py:1-10`).»

`coordinator.py:1-10` — это module docstring, в нём нет упоминания lock. Реальный `threading.RLock` — `coordinator.py:139`. Утверждение верное, цитата промахнулась. Исправить цитату на `coordinator.py:139`.

---

## WARN 2 — мелкие off-by-one в цитатах (всё равно указывают на нужную функцию)

- Шаг 0: `rm.run()` «`__main__.py:219`» → фактически `rm.run()` на строке 220 (219 = `try:`).
- Шаг 8: `start_bracket` «`coordinator.py:336-382`» → `def` на 336, но тело заканчивается на 398 (`return bracket_id`); цитата обрывается на 382 (середина upsert). Лучше `336-398`.
- Сценарий C: `_cmd_kill` «`__main__.py:459-483`» → функция 459-484 (`return 0` на 484).
- Шаг 3: look-ahead «`bar_source.py:79-86`» → сам цикл фильтрации 81-87 (76-80 = комментарий).

Все — косметика, ни одна не вводит в заблуждение по существу.

---

## WARN 3 — Сценарий A неявно предполагает s35_demo_active (LOCKED-параметры)

Сценарий A (строка 221): «RSI = 32 (ниже порога 35)». Порог 35 = `rsi_oversold` из LOCKED-набора `MEAN_REVERSION_S17_RELAXED_PARAMS` (mean_reversion_strategy.py:47), активного только при `s35_demo_active=True`. Дефолт конфига `s35_demo_active=False` → тогда oversold берётся из `settings.strategy_rsi_oversold` (может отличаться). Сценарий иллюстративен и число реальное (35 — реально сконфигурированное значение), так что не BLOCKER; но стоит понимать, что «35» — это demo-LOCKED ветка, а не универсальный дефолт. (Та же неявность, что в startup-wiring Scenario A.)

---

## ПРОВЕРЕНО И КОРРЕКТНО (не перепроверять — тело сильное)

**Цитаты manager.py — ВСЕ точные:**
- `_cmd_run` 70-226 ✓; `run()` 106-151 ✓ (kill-clean 117-118, bootstrap 121, ws.start 135 — все точны); `_main_loop` 153-160 ✓; `_tick` 162-178 ✓; `on_bar` :346 ✓; `current_state` caller :359 ✓; FLAT 363-371 ✓; skip-non-flat 373-379 ✓; `assess` caller :380 ✓; reject 381-387 ✓; `start_bracket` caller 403-408 ✓; stall halt 327-335 (request_halt HALT_BAR_POLL_STALL на :333) ✓; `_shutdown` reasons :140/148/151 ✓.

**Шаг 5 FLATTENABLE-состояния:** doc «LONG_OPEN, OCO_ARMING, OCO_ARMED» == `_FLATTENABLE_STATES` (manager.py:54-60) ТОЧНО.

**Шаг 10 — НЕ повторяет ошибки startup-and-wiring (важно):**
- Таблица: `KEYBOARD_INTERRUPT` / `HALT_RUNTIME_CRASH` / `NORMAL_EXIT` — это ТОЧНЫЕ аргументы `_shutdown(reason=...)` (manager.py:140/148/151). Заголовок «Код» = reason-code, НЕ OS exit code → страница НЕ утверждает «Ctrl+C → exit 130» (в отличие от startup-and-wiring). GOOD.
- Сценарий C НЕ утверждает `shutdown reason=KILL_SWITCH`: говорит `request_halt(KILL_SWITCH_REQUESTED)` + `_stopping=True` → цикл заканчивается → WS закрывается. Это корректно (request_halt reason = KILL_SWITCH_REQUESTED на manager.py:293, _stopping на :294). Избегает BLOCKER'а kill-switch-facts. GOOD.

**Формула и пример ATR (Bash-проверено):**
- `sl = mark − k_sl·ATR`, `tp = mark + k_tp·ATR` == risk/manager.py:288-289 ТОЧНО.
- Пример: 60000 − 1.5·800 = **58800**; 60000 + 2.0·800 = **61600** — пересчитано, ТОЧНО (совпадает и со Сценарием A строка 225).

**Исполнение / bracket:**
- Вход = Market BUY (bracket.py:5 «Entry Market BUY»; entry leg price/trigger = None, :87-88; координатор передаёт только symbol/side/qty/order_link_id без цены → Market). ✓
- 3-плечевой bracket: entry Market + TP Limit GTC + SL Stop-Market triggerBy=LastPrice (bracket.py:4-7). ✓ Доковское «пакет из трёх связанных заявок» корректно.
- FLAT → ENTRY_PENDING через ENTRY_PLACED (state_machine.py:73). ✓
- «TP/SL не размещаются сразу» — docstring start_bracket :346 «TP/SL legs are armed later in on_entry_filled». ✓

**WebSocket (Шаг 9):**
- 3 темы `order`/`wallet`/`execution` — ws_private.py:121-123 (`order_stream`/`wallet_stream`/`execution_stream`). ТОЧНО. Класс `BybitPrivateWSConsumer` :45. ✓

**Данные / BarSource:**
- Bar-модель models.py:17-43 ТОЧНО (OHLCV: open/high/low/close/volume). ✓
- `BarSource.poll()` 60-92 ✓; `_fetch` окно 2 бара (`start_ms = end_ms − step_ms*2`, :107) ✓; look-ahead фильтр (close_time ≤ now) + dedup (`close_ms ≤ last_close_ts → None`, :89-91) ✓.
- Pitfall 1: interval «60» = 1 час (`_INTERVAL_MS["60"] = 3_600_000` мс). ✓
- Stall: дефолт 24 (config.py:214-221); 24×5s = 120s = 2 мин (Bash-проверено); `should_halt` строгий `>=` (:96). ✓

**Конфиг / параметры:**
- cadence 5.0 (config.py:210-212). ✓
- Pitfall 6: LOCKED rsi=14 / oversold=35 / bb=1.5σ == `MEAN_REVERSION_S17_RELAXED_PARAMS` (mean_reversion_strategy.py:43-52); подключаются на `__main__.py:147-163` при `s35_demo_active`. ✓
- LONG-only: risk/manager.py:212-218 (`raise ValueError` на non-LONG). ✓ Pitfall 3 cite корректна.
- AND-шлюз: mean_reversion_strategy.py:3-6 (docstring «RSI(14) < oversold AND close < lower_BB»). ✓
- `assess()` 202-312. ✓

**Прочее:**
- bootstrap (coordinator.py:257) — сверка с биржей при старте (reconcile-on-startup). ✓
- Шаг 7 порядок проверок: код делает flash-check (:234-243) перед halt-rejection (:246-255), а doc перечисляет halt→flash. Но flash лишь эскалирует `_current_halt` до FLASH, а отклонение единое (halt-check). Допустимая абстракция (обе ведут к reject). Не флагую.
