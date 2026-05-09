# BACKLOG — AI Trading Bot v0.1

> Статус: S39 phase 0-prep. Последний тег: `v0.1.0-alpha.38`. Ветка: `main`.
> Последнее обновление: 2026-05-09.

---

## Критично (блокеры S39)

Следующие задачи блокируют прогресс — необходимо закрыть до или в рамках S39.

| ID | Задача | Источник | Риск при пропуске |
|----|--------|----------|-------------------|
| **H1** | Rate-limit backoff отсутствует в `src/execution/bybit/rest.py` | T3 bybit-api-reviewer (S38) | Бан IP Bybit при >600 req/min; бот падает без recovery |
| **H2** | WS reconnect при дропе соединения не покрыт тестами | T3 bybit-api-reviewer (S38) | Потеря тиков → пропуск сигнала или застывший стейт |
| **Item #10** | DD_MULTIDAY / NO_TRADE_TIMEOUT сценарии отсутствуют в property tests | pre-s38-backlog | HaltGate не валидирован на граничных случаях — риск ложного halt или пропуска halt |

---

## Sprint 39 scope (рекомендуемый)

Рекомендуемый объём S39 выводится из SPRINT_STATE.md и pre-s38-backlog.

### Обязательные задачи

| Задача | Описание |
|--------|----------|
| **H1 fix** | Добавить exponential backoff с jitter в REST-адаптер; тест: `pytest -m bybit_rest` должен пройти при 429 response |
| **H2 тесты** | Property tests для WS reconnect: оборвать соединение → проверить восстановление < 5 сек, стейт FLAT preserved |
| **Item #10** | Расширить `tests/property/test_halt_gate.py` для DD_MULTIDAY и NO_TRADE_TIMEOUT с реальными trade fixtures |
| **Item #7 shim** | Убрать backward-compat shim в `RiskSharedDeps` (все вызывающие мигрированы в S38); после удаления — smoke test |
| **F8 block_size** | Унифицировать `_MC_BLOCK_SIZE` (20 vs 30) — принять одно значение, зафиксировать в `src/backtest/mc_permutation.py` |

### Опциональные задачи (если влезают в объём)

| Задача | Описание |
|--------|----------|
| **12mo MAINNET ADR** | Набросок ADR для автоматического перехода TESTNET → MAINNET при достижении n=10 непустых DSR. Только черновик — не активировать. |
| **M1-M4 + 3 LOW** | Косметические правки bybit-api-reviewer: retCode taxonomy, pybit response-shape, WS isinstance, `__repr__` secret redaction |

---

## Отложено из S37-S38

Закрыто в предыдущих спринтах, но часть задач оставила хвосты — зафиксировано для истории.

| ID | Статус | Примечание |
|----|--------|------------|
| F2 pnl_pct fix | ✅ ЗАКРЫТО S38 T2 | `compute_live_sharpe` теперь использует `pnl_pct` |
| F3 bybit-api-reviewer invocation | ✅ ЗАКРЫТО S38 T3 | 0 BLOCKER, 3 HIGH выявлено и триажировано → H1/H2 |
| Item #7 RiskSharedDeps DI refactor | ✅ ЗАКРЫТО S38 T4 | DI wiring only; shim-cleanup — см. S39 |
| Playbook F4-F7 gates | ✅ ЗАКРЫТО S38 T6 | 5 новых ворот в delta-activation-playbook.md |
| ADR 0057 amendment (months_since) | ✅ ЗАКРЫТО S38 T5 | Truncation semantics задокументировано |
| Item #6 months_since doc | ✅ ЗАКРЫТО S38 T5 | |
| Item #9 Sharpe semantics ADR doc | ✅ ЗАКРЫТО S38 T5 | |

---

## Найдено при ревью (open issues)

Выявлено bybit-api-reviewer в S38 T3, не вошло в S38 scope.

| Severity | Файл | Проблема |
|----------|------|----------|
| **HIGH** H1 | `src/execution/bybit/rest.py` | Rate-limit backoff отсутствует (см. «Критично» выше) |
| **HIGH** H2 | `src/execution/coordinator.py` | WS reconnect не покрыт тестами (см. «Критично» выше) |
| **HIGH** H3 | `src/execution/coordinator.py` | `accountType` не валидируется при старте (SPOT vs CONTRACT мismatch) — закрыто S38 playbook gate |
| MEDIUM M1 | `src/execution/bybit/rest.py` | retCode taxonomy неполная (10001-170134 range) |
| MEDIUM M2 | `src/execution/bybit/rest.py` | pybit response-shape assertion слабая |
| MEDIUM M3 | `src/execution/coordinator.py` | WS data isinstance check отсутствует |
| MEDIUM M4 | `src/execution/bybit/rest.py` | `__repr__` редактирует secret, но только частично |
| LOW | Разные | 3 косметических замечания (форматирование логов, именование) |

---

## Заморожено (v0.2+)

Не планируется в ближайших спринтах. Вернуться при смене направления.

| Элемент | Причина заморозки |
|---------|-------------------|
| FillRecorderAdapter Layer 2 (entry_signal_id → execution_state) | S12 carry-over; требует schema migration; нет приоритета пока нет Mainnet |
| 3-way endpoint enum (DEMO/TESTNET/MAINNET) | S11 Q6 carry-over; cosmetic; не блокирует δ |
| DSR per-fold DataFrame→TradeRecord conversion | S10 informational; закрыто в S33 T3 на уровне multi-symbol sigma_SR; per-fold path не используется |
| Halt_log INSERT order swap в `_set_halt` | Pre-existing; audit-log ordering cosmetic; не влияет на correctness |
| Multi-symbol live runtime fan-out | S15 deferred; out of MVP scope per ADR 0016 + user BTC-only constraint |
| Capital allocation cross-symbol exposure caps | S15 deferred; out of MVP |
| Bridge 4 corpus partition implementation | S32d research notes: NOT recommended пока corpus < 100 obs (сейчас ~17) |
| Context budget hook exact token counter | S32d: file size proxy достаточен; точный счётчик = 8-12h, marginal ROI |
| ML XGBoost / HMM regime-switch | v0.7+ options per ADR 0051; не pre-registered; требует отдельный ADR |

---

## Рекомендация для S39

### Фокус

S39 должен закрыть инфраструктурные долги в execution path (`H1`, `H2`, `Item #10`) и завершить уборку после S38 (`Item #7 shim`, `F8`). Это создаёт прочную базу для δ TESTNET наблюдений и, при необходимости, будущего autoresearch iter 2.

### Блокеры vs опциональное

`H1` (rate-limit backoff) и `H2` (WS reconnect тесты) являются блокерами δ TESTNET в production-смысле: без них бот не готов к длительной работе в реальной сети. `Item #10` блокирует уверенность в HaltGate — без граничных тестов нельзя утверждать, что защита работает. Остальные задачи (`M1-M4`, `12mo MAINNET ADR`) — опциональные улучшения, которые можно включить если объём позволяет.

### Готовность autoresearch iter 2 к production integration

Autoresearch iter 1 (Donchian, ветка `autoresearch/donchian-may8`) закрыт как overfit: train Sharpe 1.27 → held-out Sharpe -3.23. Trader-expert подтвердил: hyperparameter tuning без trend filter не работает для Donchian на BTC 4H. Iter 2 кандидат — EMA200 trend filter — пока существует только как идея в SPRINT_STATE. До production integration (full kit cycle, ADR, tests, tag alpha.39) необходимо: (а) провести autoresearch R-mode (bypass kit, ~2h, held-out PASS/FAIL verdict); (б) если held-out PASS — инициировать formal kit cycle K-mode с полным brainstorm-init, pre-registration ADR, TDD и phase-advance gate. На текущий момент iter 2 **не готов к production integration** — отсутствует даже базовый held-out результат.
