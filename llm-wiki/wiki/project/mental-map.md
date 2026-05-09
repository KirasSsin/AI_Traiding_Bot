---
title: Mental map — "where to look for X" decision tree
type: navigation
tags: [navigation, mental-map, rag, discovery, llm-friendly]
created: 2026-04-25
updated: 2026-05-09
status: stable
sources:
  - project/SPRINT_STATE.md
  - project/architecture/current-state.md
  - index.md
---

# Mental map — где искать X

> **Для LLM-агентов:** этот файл = первый источник для открытых запросов ("как работает X / где находится Y / кто владеет Z"). Укажет, какой wiki-путь читать вместо слепого grep'а. Обновляется при добавлении нового компонента / ADR / спринта.

**TL;DR:** дерево решений, отображающее типовые запросы → канонические wiki-пути. Экономит токены при первичной ориентации. Предпочтительнее `Glob "**/*.md"` + `Grep` вслепую.

## Быстрая таблица поиска

| Запрос / тема | Канонический источник | Порядок чтения |
|---------------|----------------------|----------------|
| Текущий спринт / фаза / состояние | `project/SPRINT_STATE.md` | 1 |
| Живые счётчики (состояния/события/переходы FSM, reason codes, компоненты) | `project/architecture/current-state.md` (таблица canonical-counts) | 1 |
| Последние N событий хронологически | `wiki/log.md` (использовать `tail -100` — файл 51KB запрещён для полного чтения) | 1 |
| Резюме спринта "что было в спринте N" | `project/sprints/sprint-NN-<slug>.md` | 1 |
| План спринта (задачи + trace map) | `project/plans/YYYY-MM-DD-sprint-N-<slug>.md` (планы S6/S7/S8a/S2 запрещены для полного чтения — использовать Grep/offset Read) | 2 |
| ADR (архитектурное решение) | `project/decisions/NNNN-<slug>.md` + `index.md` "## Project — Decisions" | 2 |
| Методология / sprint workflow / определения фаз | `project/architecture/development-workflow.md` (мастер-SOP, 9 фаз) | 1 |
| Правила wiki-мейнтейнера + иерархия 5 слоёв skills | `llm-wiki/CLAUDE.md` (корень, не внутри wiki/) | 1 |
| Соглашения репозитория + Python venv дисциплина + протокол брейнштурма | `CLAUDE.md` (корень репозитория) | 1 |
| Предспринтовый бэклог (пробелы + баги для закрытия) | `wiki/project/pre-s{N}-backlog.md` (если существует) | 2 |

## Поиск по доменам

### FSM / конечный автомат

| Запрос | Путь | Примечания |
|--------|------|------------|
| Текущее число состояний FSM + история роста | `components/execution-state-machine.md` TL;DR | живые счётчики: `.venv/bin/python -c "from src.execution.state_machine import TRANSITIONS, ExecutionState, ExecutionEvent; from src.risk.reason_codes import ReasonCode; print(f'states={len(list(ExecutionState))}, events={len(list(ExecutionEvent))}, transitions={len(TRANSITIONS)}, reason_codes={len(list(ReasonCode))}')"` |
| Логика dispatch FSM (кто вызывает `_transition`) | `components/coordinator.md` "FSM dispatch invariant" + источник `_transition` | |
| Инвариант переходов KILL_SWITCH_REQUESTED | `decisions/0023-halt-code-fsm-event-mapping.md` (инвариант) + `decisions/0022-sprint-8a-live-runtime.md` (введение события) | ADR 0023 — основной источник |
| Граничный случай (FLAT, RISK_HALT) → HALTED | `sprints/sprint-08b-carryover.md` T7 + `decisions/0023` | регрессия поймана property-тестом |
| Дизайн Harel statechart | `architecture/state-machine.md` (верхний уровень) | проектный документ до S5, FSM вырос с тех пор |

### Оперативные процедуры / реагирование на инциденты

| Запрос | Путь | Примечания |
|--------|------|------------|
| Восстановление после halt (как возобновить из любого halt-кода) | `project/runbooks/halt-recovery.md` (19 halt-кодов, 5 групп, 2 уровня severity) | Первый источник для production-инцидентов |
| Классификация CRITICAL vs RECOVERABLE halt | `project/runbooks/halt-recovery.md` секция "CRITICAL definition" | CRITICAL = "неверное ручное восстановление может создать или скрыть открытую позицию" |
| SQL-шаблон сброса (execution_state в FLAT) | `project/runbooks/halt-recovery.md` "Common SQL templates" | схема S7 с halt_reason + halt_log |
| Матрица приоритетов halt (цепочка эскалации P0/P1/P2) | `project/runbooks/halt-recovery.md` секция "Priority matrix" + таблица Quick Reference "On-call escalation" | S11 T5 (Q3 REVISE — единственный источник истины, НЕ отдельный dashboard) |
| Предполётный чеклист оператора (перед `python -m src run`) | `project/runbooks/pre-flight.md` (5 критических шлюзов + 4 рекомендации + мониторинг после запуска + halt response) | S11 T8 — обязателен перед Mainnet/demo |
| Рецепты фильтрации логов (structlog jq + halt_log SQL) | `project/runbooks/log-grep-templates.md` | S11 T6 — шаблоны оператора (только ошибки / по брекету / история halt / fill audit) |
| Плейбук live demo validation 48h | `project/runbooks/live-demo-validation.md` | S12 T4 — входные шлюзы + мониторинг + multi-criteria success gate с обязательной оговоркой zero-trade |
| P0 halt response + процедура откатa | `project/runbooks/halt-response-protocol.md` | S12 T5 — дерево решений P0 + откат alpha.11 (Q7 zero-migration safe) + итерация RC-тега |
| CLI снимка состояния только для чтения (`python -m src monitor`) | `components/kill-switch-cli.md` "_cmd_monitor" + `src/__main__.py::_cmd_monitor` | S11 T7, инвариант C2: SQLite `?mode=ro` URI, mtime БД не меняется. Тест проверяет. |
| CLI подкоманда WFA (`python -m src wfa`) | `components/walk-forward.md` + `src/__main__.py::_cmd_wfa` | S11 T4 — WFA orchestrator + MC + acceptance gate. Заглушка `_load_ohlcv` (S12 подключает реальные данные) |

### Механика halt / circuit breaker

| Запрос | Путь |
|--------|------|
| Механика halt (γ persistence, primary-wins) | `components/coordinator.md` "γ Halt persistence" + `decisions/0021-sprint-7-resilience.md` sub-decisions 5+9 |
| API `request_halt(reason: ReasonCode)` | `components/coordinator.md` "request_halt" |
| Halt-коды, освобождённые от guard HALTED→событие (KILL_SWITCH_REQUESTED + HALT_RUNTIME_CRASH + HALT_BAR_POLL_STALL) | `components/coordinator.md` "Allow-list contract" + `decisions/0023` |
| Семантика `HALT_BAR_POLL_STALL` + порог (24 последовательных отказа) | `components/bar-poller.md` "Stall detection" + `decisions/0022` G3 |
| Таблица audit `halt_log` (write-ahead γ persistence) | `decisions/0021` sub-decision 5 + `migrations/0005_halt_persistence.sql` |
| Ручное возобновление CB (HMAC-подписанный override) | `components/risk-override.md` |
| Kill-switch CLI (`python -m src kill`) | `components/kill-switch-cli.md` |
| Circuit breaker L1/L2/L3/flash | `components/circuit-breakers.md` + `decisions/0013` + `trading/concepts/circuit-breakers.md` |

### Reconcile / bootstrap

| Запрос | Путь |
|--------|------|
| 4-значный вердикт (AGREE/HEAL_ENTRY_FILLED/EXITED/DIVERGENCE) | `components/reconciler.md` |
| Инвариант последовательности bootstrap | `components/coordinator.md` "Bootstrap sequencing" + `decisions/0021` sub-decision 1 |
| Путь WS reconnect | `components/coordinator.md` `on_ws_reconnect` + `components/ws-private-consumer.md` |
| Обоснование `heal_max_age=3600s` | `decisions/0021` sub-decision 4 |

### Risk / Kelly / sizing

| Запрос | Путь |
|--------|------|
| 4-фазный Kelly + Wilson 95% CI | `components/kelly.md` + `decisions/0012` + `trading/concepts/kelly-phases.md` |
| Расчёт объёма позиции (`compute_qty`) | `components/sizing.md` |
| История трейдов (audit log + источник числа трейдов Kelly) | `components/trade-history.md` |
| Конвейер решений RiskManager.assess() | `components/risk-manager.md` |
| Каталог reason codes (всего 45) | `architecture/reason-codes-schema.md` (канонический список) + `src/risk/reason_codes.py` (живой) + `trading/concepts/reason-codes.md` (нарратив) |

### Execution / OCO / bracket

| Запрос | Путь |
|--------|------|
| 3-ордерная эмуляция Spot OCO (Entry Market + TP Limit + SL StopMarket IOC) | `components/oco.md` + `decisions/0020` |
| Bracket builder (`compute_oco_qty`, `make_order_link_id`) | `components/oco.md` секция "bracket.py — чистое API" (охватывает `src/execution/bracket.py`) |
| Bybit V5 адаптер (REST + 6 методов) | `components/bybit-adapter.md` + `components/bybit-rest.md` |
| Специфика Bybit Spot (нет нативного OCO, IOC override, запрещённые поля) | `decisions/0020` sub-decisions + `components/bybit-adapter.md` |
| WS private consumer (события ордеров/кошелька) | `components/ws-private-consumer.md` |

### Runtime / живой процесс

| Запрос | Путь |
|--------|------|
| Жизненный цикл процесса (bootstrap → tick loop → shutdown) | `components/runtime-manager.md` |
| Владение tick pipeline (RuntimeManager → bar_poller → bar_builder → strategy → risk → coordinator) | `components/runtime-manager.md` секция "Tick pipeline" |
| Bar poller (REST kline с кадансом 5с + обнаружение зависания) | `components/bar-poller.md` |
| Политика блокировок потоков (RLock 8 методов Coordinator + Lock 2 Reconciler) | `components/coordinator.md` "Threading lock policy" + `decisions/0022` Task 0 |
| Entry-point CLI (`python -m src run/backfill/reconcile-only/kill`) | `components/kill-switch-cli.md` |

### Storage / persistence

| Запрос | Путь |
|--------|------|
| SQLite WAL + схема Parquet | `components/storage.md` + `architecture/storage.md` + `decisions/0003` |
| Миграции (только вперёд) | `migrations/*.sql` (ls) + `architecture/storage.md` |
| Строка состояния execution (FSM persisted) | `components/coordinator.md` "State persistence" + `migrations/0003_execution_state.sql` + `migrations/0004_execution_state_v2.sql` + `migrations/0005_halt_persistence.sql` |
| Столбцы схемы `execution_state` | то же |
| Таблица audit `halt_log` (S7 γ) | `decisions/0021` sub-decision 5 + migration 0005 |

### Strategy / генерация сигналов

| Запрос | Путь |
|--------|------|
| Стратегия EMA crossover (live S3+) | `components/strategy.md` + `trading/strategies/ema-crossover-adx-rsi.md` |
| Индикаторы (EMA классический, ADX/RSI/ATR Wilder via TA-Lib) | `components/indicators.md` + `trading/indicators/*.md` (4 файла) + `decisions/0011` |
| Контракт сигнала (close(T) → fill open(T+1)) | `architecture/execution-timing.md` + `trading/concepts/look-ahead-bias.md` |

### Backtest

| Запрос | Путь |
|--------|------|
| Replay engine + vector backtest + reporter (6 src-файлов) | `components/backtest-harness.md` |
| WFA (train=2000 / test=500 / K=5 / embargo=20) | `decisions/0014` + `trading/concepts/walk-forward-validation.md` |
| MC permutations (sign-flip N=2000) | `decisions/0015` + `trading/concepts/monte-carlo-permutations.md` |
| DSR (Deflated Sharpe Ratio) | `trading/concepts/deflated-sharpe-ratio.md` (концепция; интеграция отложена к S9+) |
| trade_extractor (DataFrame → мост TradeRecord) | `components/trade-extractor.md` + `src/backtest/trade_extractor.py` (S13 T5) |
| strategy_metrics (извлечение критериев приёмки T1-T6) | `components/strategy-metrics.md` + `src/backtest/strategy_metrics.py` (S13 T6) |

### Tooling / hooks / методология

| Запрос | Путь |
|--------|------|
| Обязательный trace map ФАЗА 3 | `architecture/development-workflow.md` ФАЗА 3 шаг 1a |
| Hook синхронизации ADR ↔ Agent prompt | `components/adr-agent-sync-hook.md` + `~/.claude/hooks/adr-agent-sync-check.sh` |
| Hook синхронизации ADR ↔ Index | `components/adr-index-sync-hook.md` + `~/.claude/hooks/adr-index-sync-check.sh` |
| Hook проверки битых ссылок wiki | `components/wiki-broken-link-hook.md` + `~/.claude/hooks/wiki-broken-link-check.sh` (Bucket C7) |
| Детектор качества bar (HALT_DATA_QUALITY) | `components/data-quality.md` + `src/marketdata/quality.py` (S9 Q1, REST-vs-REST) |
| Audit по fill + WS execution topic | `components/fill-history.md` + `src/risk/fill_history.py` (S9 Q3 B1) |
| FillRecorderAdapter (Bybit V5 WS exec → DB best-effort) | `components/fill-recorder-adapter.md` + `src/risk/fill_recorder_adapter.py` (S12 Q5) — паттерн 2 слоя (structlog audit + best-effort DB insert через цепочку execution_state→trade_history). Безопасен к race condition (skip+warn). Перенос S13: добавить `entry_signal_id` в схему `execution_state`. |
| DSR (Deflated Sharpe Ratio, Bailey & López de Prado) | `components/dsr.md` + `src/analytics/dsr.py` (S9 Q3 B2 + S10 sigma_sr extension) |
| Walk-forward analysis (rolling K-folds, OOS/IS Sharpe gate) | `components/walk-forward.md` + `src/backtest/walk_forward.py` (S10 Q1+Q4, ADR 0014+0025) |
| Monte Carlo permutations (sign-flip + block bootstrap) | `components/mc-permutations.md` + `src/backtest/mc_permutation.py` (S10 Q3, ADR 0015) |
| WFA reporter + 3-Sharpe routing | `components/wfa-reporter.md` + `src/backtest/wfa_reporter.py` (S10 Q4+Q6) |
| Orphan-audit grep (включая `tests/`) | `architecture/development-workflow.md` ФАЗА 8 шаг 5b |
| Синхронизация канонических счётчиков HARD-GATE | `architecture/development-workflow.md` ФАЗА 8 шаг 5a |
| Обязательный протокол брейнштурма ФАЗА 2 (trader-expert ROUND 1+2) | `architecture/development-workflow.md` ФАЗА 2 шаг 3 → `.claude/skills/brainstorm-init/SKILL.md` |

### Проектные skills (шаблоны workflow)

| Запрос | Skill |
|--------|-------|
| "где мы остановились?" / возобновление спринта / после `/clear` | `.claude/skills/sprint-orient/SKILL.md` (авто-триггер) |
| "ship sprint" / "финишируем" / HARD-GATE ФАЗА 8 | `.claude/skills/sprint-finish/SKILL.md` (авто-триггер) |
| После изменения src/ → синхронизация документации | `.claude/skills/wiki-update/SKILL.md` (авто-триггер) |
| "брейнштурм" / вопросы scope / ФАЗА 2 binding | `.claude/skills/brainstorm-init/SKILL.md` (авто-триггер) |
| Тестирование PreToolUse hook-скрипта | `.claude/skills/hook-test/SKILL.md` (только явный вызов `/hook-test`) |

Skills заменяют hardcoded inline workflow logic в соответствии с принципом progressive disclosure. Не дублировать процедуры в других документах.

## FAQ по неоднозначным запросам

| Неясность | Ответ |
|-----------|-------|
| Dispatch FSM — `coordinator.md` ИЛИ `state-machine.md`? | Оба. **`state-machine.md`** = enum + таблица переходов (данные). **`coordinator.md`** = логика вызовов (кто запускает события). Читайте state-machine для "какие переходы существуют", coordinator для "кто вызывает `_transition`". |
| Halt — где живёт? | Слой хранения = `coordinator._set_halt()` пишет в `execution_state.halt_reason` + таблицу `halt_log`. Dispatch логики = `coordinator.request_halt()` → FSM-событие (инвариант ADR 0023). Триггер оператора = `kill-switch-cli` (sentinel-файл) ИЛИ `risk-override` (HMAC-подписанное ручное возобновление). |
| OCO — `oco.md` ИЛИ `bracket.py`? | `oco.md` документирует ОБА: `src/execution/oco.py` (вычисление уровней, ATR-based TP/SL) И `src/execution/bracket.py` (строитель ордеров, qty с учётом комиссии per ADR 0020 sub-decision 6). Одна страница компонента охватывает всю OCO-эмуляцию. |
| Reason codes — где канонический список? | `src/risk/reason_codes.py` = источник истины (живой, текущее число кодов). `architecture/reason-codes-schema.md` = JSON Schema + формат audit-записи. `trading/concepts/reason-codes.md` = нарратив "почему". Используйте src для "какие коды существуют", schema для "какие поля", concept для "почему". |
| Вопросы по спринтам — `sprints/` ИЛИ `plans/` ИЛИ `decisions/`? | **sprints/sprint-NN.md** = "что было сделано" (запись о поставке, актуальна для завершённых спринтов). **plans/YYYY-MM-DD.md** = "что делать" (задачи, используется при исполнении). **decisions/NNNN.md** = "почему выбрали X" (архитектурное обоснование, неизменно кроме поправок). Сначала читать sprints для контекста. |
| Reconciler vs Coordinator — кто пишет SQLite? | **Reconciler** выдаёт только вердикт (без I/O). **Coordinator.on_ws_reconnect()** действует по вердикту + вызывает `_repo.upsert(...)`. "Биржа — источник истины" per ADR 0019 sub-decision 3 — локальное состояние выравнивается по биржевой правде, путь записи только через Coordinator. |
| Флаг `_bootstrap_done` — зачем нужен? | Guard-предикат в Coordinator. Устанавливается при завершении `bootstrap()`. Проверяется в `start_bracket` + `on_order_event` ДО обработки. Предотвращает обработку WS-эхо от старых ордеров до завершения cold/warm reconcile → защита от split-brain. См. `components/coordinator.md` "Bootstrap sequencing" + `decisions/0021` sub-decision 1. |

## Когда не ясно — fallback

1. `Read llm-wiki/wiki/index.md` (полный каталог ≤ 14KB, быстрое сканирование)
2. `Read llm-wiki/wiki/project/SPRINT_STATE.md` (текущее состояние ≤ 2KB)
3. `Read llm-wiki/wiki/project/architecture/current-state.md` (канонические счётчики + история спринтов)
4. `Grep "<keyword>" llm-wiki/wiki/` (полный поиск)
5. Если по-прежнему не ясно — спроси мейнтейнера, не импровизируй

## Правило поддержки

**Обновлять этот файл когда:**
- Добавлен новый ADR → добавить в соответствующую доменную секцию
- Создана новая страница компонента → добавить в "Поиск по доменам"
- Два документа вызывают путаницу (cross-domain запрос) → добавить в "FAQ по неоднозначным запросам"
- Появился новый канонический источник → обновить быструю таблицу поиска

HARD-GATE ФАЗА 8 шаг 5/5a — следует также включать "если нужна новая доменная секция → обновить mental-map.md" (рекомендуется добавить в kit в следующей итерации).

## Связанное

- [[index|index.md]] — плоский каталог (этот файл — дерево решений, тот — перечисление)
- [[components/README|components/ README]] — тематические кластеры (обратный поиск: "я читаю X — что связано?")
- [[architecture/current-state|current-state.md]] — канонические счётчики + история спринтов
- [[architecture/development-workflow|dev-workflow.md]] — мастер-SOP методологии
- [[SPRINT_STATE]] — живая рабочая память
