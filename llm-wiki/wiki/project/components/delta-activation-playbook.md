---
title: δ TESTNET Activation Playbook (S37+ Operator Procedure)
type: component
tags: [component, testnet-demo, operator-playbook, halt-gate, monitoring, sprint-37, ru]
created: 2026-04-27
updated: 2026-05-09
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

## Чеклист перед активацией

Все пункты ОБЯЗАНЫ быть выполнены перед активацией:

- [ ] S37 shipped (тег v0.1.0-alpha.37 или новее)
- [ ] Все 6 критических carry-overs закрыты (security 1-3 + trading-logic 4-5 + quant 8)
- [ ] Понят шаблон подтверждения ADR 0055 (шлюз 12mo MAINNET-promotion, НЕ завершение)
- [ ] Понят ADR 0057 SD-1 (HALT_UNKNOWN_SYMBOL отдельный ReasonCode = сохраняется атрибуция в audit)
- [ ] Понят ADR 0057 SD-3 (Setting whitelist + startup banner)
- [ ] Понят ADR 0057 SD-4 (HMAC-целостность activation_ts — фальсификация вызывает halt)
- [ ] Просмотрены LOCKED-константы `MEAN_REVERSION_S17_RELAXED_PARAMS` (RSI 35/65, BB 1.5σ)
- [ ] Bybit TESTNET API credentials готовы в production .env
- [ ] Настроен `risk_override_hmac_key` (32+ символов)

### S38 ADR 0058 SD-4 — НОВЫЕ шлюзы (после ROUND 6 consilium):

- [ ] **F4 — Верификация scope API ключа Bybit TESTNET**: убедиться, что ключ имеет разрешения Order (read+write) И Position. Pre-flight: `GET /v5/account/info` + проверить доступность `POST /v5/order/create`. Read-only ключ → `retCode=10003` permission denied на первом сигнале (необработанный путь ошибки).
- [ ] **F5 — Проверка отсутствия устаревшей строки `runtime:halt_gate:activation_ts`**: запрос `sqlite3 data/bot.db "SELECT * FROM state WHERE key='runtime:halt_gate:activation_ts';"` — должна быть пустой ИЛИ подписанной текущим `risk_override_hmac_key`. Другая версия HMAC-ключа → tamper halt на первом тике (HALT_UNKNOWN_SYMBOL).
- [ ] **F7 (Шлюз 2) — SQLite WAL mode + дисковое пространство**: убедиться, что свободно > 1GB. halt_log накапливает строки за 12mo TESTNET-окно.
- [ ] **F7 (Шлюз 3) — Инвариант порядка bootstrap**: `coordinator.bootstrap()` ОБЯЗАН завершиться до `ws_consumer.start()`. Текущий код в `src/runtime/manager.py:104-105` имеет корректный порядок. НЕ менять порядок без проверки assertion paths.
- [ ] **T3 H3 — Верификация типа Bybit-аккаунта**: убедиться, что TESTNET-аккаунт типа **UNIFIED**. Код хардкодит `accountType="UNIFIED"` в вызовах Bybit V5 API. Если аккаунт типа **CLASSIC** (non-UNIFIED) → ордера отклоняются с retCode=10001 ИЛИ неверно классифицируются. Pre-flight: `GET /v5/account/info` возвращает `unifiedMarginStatus`. Если non-UNIFIED → эскалировать к мейнтейнеру для config-knob refactor (S38a hotfix ИЛИ pre-s39-backlog).

## Шаги активации

### Шаг 1 — Установить переменную окружения

В production `.env` file:

```bash
S35_DEMO_ACTIVE=true
# Optional: extend whitelist если multi-symbol future:
# S35_DEMO_APPROVED_SYMBOLS=["BTCUSDT","ETHUSDT"]  # JSON list format
```

Whitelist по умолчанию `["BTCUSDT"]` per ADR 0057 SD-3 — δ pre-commit единственного символа.

### Шаг 2 — Проверить инварианты Settings

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

Ожидаемый вывод:
- `s35_demo_active: True`
- `testnet: True` (инвариант MAINNET-exclusion per ADR 0055)
- `live_trading: False` (MAINNET-exclusion)
- `whitelist: ['BTCUSDT']` (нормализован к uppercase per S37 T2)
- Halt thresholds: 0.20 / 0.15 / 5 / 6

При нарушении инварианта → ValueError при конструировании Settings. Исправить .env перед перезапуском.

### Шаг 3 — Перезапустить бот

```bash
# Via systemd / docker / script:
.venv/bin/python -m src run
```

Последовательность запуска бота:
1. Coordinator bootstrap
2. **S37 startup banner** — запись в лог `runtime.s35_demo_startup_banner` отображает:
   - список approved_symbols
   - halt_thresholds (4 триггера)
   - флаг fail_closed=True
3. Запуск WS consumer
4. Начало основного tick loop

**Убедиться в наличии banner в выводе лога** (видимый оператору audit при запуске).

### Шаг 4 — Проверить сохранение activation_ts (подписанного)

После первого тика (~5 секунд):

```bash
sqlite3 data/bot.db "SELECT key, value_json FROM state WHERE key='runtime:halt_gate:activation_ts';"
```

Ожидается:
```
runtime:halt_gate:activation_ts | {"payload":{"value":"2026-04-27T..."},"sig":"<64-char hex>"}
```

Если без подписи (нет envelope `payload`/`sig`) → S37 T3 не задеплоен. Проверить ветку + перезапустить.

**НЕ изменять эту строку вручную** — HMAC-верификация упадёт на следующем тике → бот остановится с `HALT_UNKNOWN_SYMBOL` (tamper-detection per ADR 0057 SD-4).

### Шаг 5 — Мониторинг первых 24ч

Убедиться, что бот не останавливается без причины:

```bash
sqlite3 data/bot.db "SELECT halt_ts, halt_reason FROM halt_log ORDER BY halt_ts DESC LIMIT 5;"
```

Ожидается: пусто ИЛИ существующие halt'ы не связаны с S37 (например, KILL_SWITCH_REQUESTED).

Если `HALT_S36_*` ИЛИ `HALT_UNKNOWN_SYMBOL` срабатывает немедленно → расследовать по процедуре "Процедура реагирования на halt" ниже.

## Процедура мониторинга (еженедельно)

Рекомендуемые еженедельные проверки в течение 12mo TESTNET-окна:

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

Ожидаемый базовый уровень (S22 reference): ~13 трейдов/год на BTCUSDT 4H mean-reversion.

### Важно — DSR UNDERPOWERED является ОЖИДАЕМЫМ на всё 12mo-окно

По результатам quant-stats-reviewer ROUND 6:
> При базовом уровне S22 в 13 трейдов/год: ожидается n=13 после 12mo TESTNET.
> Пороги ADR 0056: 10 ≤ n < 30 → статус DSR_UNDERPOWERED.
> Это НЕ сигнал отказа — это ожидаемый режим малой выборки.

НЕ прерывать δ TESTNET только из-за UNDERPOWERED DSR. Halt только если срабатывает HaltGate (DD/streak/timeout) ИЛИ оператор принимает решение об honest close по отдельным критериям.

GATE_ELIGIBLE (n≥30) ожидается примерно через ~28 месяцев при базовом темпе — за пределами 12mo-окна review MAINNET-promotion. 12mo review = вероятно рекомендация "продолжить TESTNET" (per ожидаемый исход quant-stats).

### Немедленный review при halt (добавление trading-logic-reviewer S38)

Еженедельный каданс отслеживает операционное здоровье, НО может пропустить halt в выходные (слепое пятно 3 дня).

**Дополнительный триггер:** если `halt_log` содержит любую запись за последние 24ч → немедленный review (не ждать еженедельного слота).

Команда быстрой проверки:

```bash
sqlite3 data/bot.db "SELECT halt_ts, halt_reason FROM halt_log WHERE halt_ts > datetime('now', '-24 hours');"
```

Если не пусто → немедленно выполнить процедуру реагирования на halt (см. секцию ниже).

## Процедура реагирования на halt

При срабатывании HaltGate (любой из 4 триггеров):

| ReasonCode | Триггер | Действие оператора |
|-----------|---------|-------------------|
| `HALT_S36_DD_INTRADAY` | 24ч DD ≥ 20% | Немедленный review — flash crash ИЛИ коллапс стратегии |
| `HALT_S36_DD_MULTIDAY` | DD от HWM-since-activation ≥ 15% | Review накопленных убытков — рассмотреть honest close |
| `HALT_S36_CONSECUTIVE_LOSSES` | 5 последовательных убыточных трейдов | Review деградации стратегии |
| `HALT_S36_NO_TRADE_TIMEOUT` | 6mo без n≥30 трейдов | Истощение частоты сигналов — рассмотреть смену режима/таймфрейма |
| `HALT_UNKNOWN_SYMBOL` | Несоответствие whitelist ИЛИ фальсификация activation_ts | **Критично** — аудит конфигурации ИЛИ инцидент безопасности |

Процедура (при любом halt):

1. **Бот уже завершил работу** (HaltGate устанавливает `_stopping=True`)
2. Изучить запись в `halt_log` для получения контекста
3. Изучить связанные логи (halt_ts ± 1 час)
4. Дерево решений:
   - Ложный / проблема конфигурации → исправить .env + ручной сброс FSM через `--reconcile-only`
   - Коллапс стратегии / HALT_S36_DD_* → ADR honest close S38+
   - HALT_UNKNOWN_SYMBOL после стабильной работы → инцидент безопасности, аудит halt_log + таблицы state
5. Задокументировать результаты review (файл заметок оператора ИЛИ commit message в репозитории)
6. Перезапустить бот ТОЛЬКО после документированного review

## Руководство по интерпретации статуса DSR (per ADR 0056)

При 12mo review MAINNET-promotion per ADR 0055 SD-8:

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

Интерпретация:

| dsr_status | Значение | Действие |
|------------|---------|---------|
| `INSUFFICIENT_TRADES` (n<10) | DSR=NaN | НЕ является кандидатом для обсуждения MAINNET. Продолжить TESTNET ИЛИ honest close. |
| `UNDERPOWERED` (10≤n<30) | DSR вычислен, но статистически слаб | Только информационно. НЕ является gate-eligible. |
| `GATE_ELIGIBLE` (n≥30) | DSR валиден для оценки | Применить шлюзы ADR 0055 SD-1 PASS (n≥50, Sharpe≥0.7, MC p≤0.05, DSR≥0.95) |

calibration_ratio_to_s22 (live_Sharpe / 2.96):
- ≥ 0.70 → PASS calibration
- < 0.70 → FAIL calibration (live уступает базовому уровню S22 сверх допуска)

## Чеклист review 12mo MAINNET-promotion

Per ADR 0055 SD-8 (критерии MAINNET ОТЛОЖЕНЫ к S37+ после получения 12mo данных):

После 12 месяцев работы в TESTNET:

- [ ] n_trades ≥ 50 (per ADR 0055 SD-1 PASS gate)
- [ ] calibration ratio live_Sharpe / 2.96 ≥ 0.70
- [ ] MC sign_flip p-value ≤ 0.05 (требуется n≥20)
- [ ] DSR ≥ 0.95 + статус GATE_ELIGIBLE
- [ ] Max DD ≤ 30% (устойчивое сохранение эквити)
- [ ] Нет активных триггеров HaltGate за последние 30 дней
- [ ] Шаблон подтверждения оператора verbatim per ADR 0052

Если ВСЕ пункты выполнены → ADR S38+ предварительно регистрирует MAINNET promotion (Bailey 2014 anti-snooping).
Если ЛЮБОЙ пункт не выполнен → продолжить TESTNET ИЛИ honest close (ADR S38+ документирует обоснование).

## Сводка критериев halt (LOCKED per ADR 0055 + ADR 0057)

| Триггер | Порог | Источник |
|---------|-------|---------|
| Intraday DD | ≥ 20% (rolling 24ч) | ADR 0055 SD-3 |
| Multiday DD | ≥ 15% (с HWM activation_ts, подписанного) | ADR 0055 SD-3 + ADR 0057 SD-4 |
| Consecutive losses | ≥ 5 | ADR 0055 SD-3 |
| No-trade timeout | ≥ 6 месяцев без n≥30 трейдов | ADR 0055 SD-3 |
| Unknown symbol (НОВЫЙ S37) | symbol NOT in whitelist ИЛИ None | ADR 0057 SD-2+SD-3 |
| activation_ts tamper (НОВЫЙ S37) | ошибка HMAC-верификации | ADR 0057 SD-4 |

## Переносы к S38+ (не включены в S37)

Per pre-s37-backlog items deferred:
- #6 документация семантики усечения months_since
- #7 рефакторинг RiskSharedDeps (Demeter)
- #9 расширенный ADR doc семантики Sharpe
- #10 расширенные сценарии DD_MULTIDAY/NO_TRADE_TIMEOUT

Операционные пункты S38+:
- ADR 12mo MAINNET-promotion (per ADR 0055 SD-8)
- Архитектурный рефакторинг (Item #7)

## Связанное

- [[../decisions/0055-sprint-36-delta-activation]] — основной ADR δ activation
- [[../decisions/0057-sprint-37-carry-overs-hardening]] — security hardening + whitelist символов
- [[../decisions/0056-sprint-36-dsr-sigma-sr-amendment]] — пороги DSR + calibration baseline
- [[halt-gate-wireup]] — runtime wire-up HaltGate
- [[live-trade-reporter]] — репортер адаптированных live-данных
- [[../sprints/sprint-36-delta-activation]] — ship S36
- [[../sprints/sprint-37-carry-overs-hardening]] — ship S37
- [[../pre-s37-backlog]] — контекст carry-overs
