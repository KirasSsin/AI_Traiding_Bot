# Depth review — dashboard-overview.md (08-дашборд)

**Ось:** КОРРЕКТНОСТЬ против кода. Дата: 2026-07-01. Ревьюер: doc-reviewer-depth.
**Источники:** src/dashboard/app.py, backtest_runner.py, account_service.py, dashboard_react/src/App.tsx, HistoryTab.tsx, ConfigureBacktest.tsx, scripts/dashboard.sh.

**Вердикт: APPROVE_WITH_CONCERNS** — 0 BLOCKER, 3 WARN, 1 DEEP. Страница почти безупречна по фактам; каждая цитата line-range проверена, каждое число пересчитано.

---

## Пересчитанные числа / проверенные сущности (все совпали)

| Утверждение (строка доки) | Код | Итог |
|---|---|---|
| `max-age=31536000` = 1 год (120) | 365×24×3600 = 31536000 (Bash) | ✓ EXACT |
| `_BALANCE_TTL_SECONDS = 5.0` (132) | account_service.py:38 | ✓ |
| fallback `10 000 USDT` (130) | FALLBACK_BALANCE_USDT=10_000.0 :31; return :142-147 | ✓ |
| sleep 1.5 c до открытия браузера (34,156) | app.py:363 `time.sleep(1.5)` | ✓ |
| 8 пресетов в 5 категориях (136) | grep: 8 ключей; 5 optgroup (Тренд-след/Тренд/Возврат/Прорывы/ML) | ✓ EXACT |
| run_id = sha256[:16] от (strat+sym+interval+start+end) (101) | :858-859 f"{sid}\|{sym}\|{interval}\|{start}\|{end}", `[:16]` | ✓ EXACT (5 полей, тот порядок) |
| таймфреймы 5m/15m/1h/4h/1d (72,148) | INTERVAL_LABELS :291-297 {5,15,60,240,D} | ✓ |
| 30m/2h исключены — Bar не поддерживает (148) | :288-290 комментарий "Bar.interval Literal не supports" | ✓ |
| host 127.0.0.1:8000, снаружи недоступен (42,124) | :353-354, только 127.0.0.1, нет 0.0.0.0 | ✓ |
| symbol regex `\A[A-Z0-9]{1,20}\Z` (126) | :62 точь-в-точь; fullmatch :105 | ✓ EXACT |
| 503 при отсутствии React build (172) | :157-161 HTMLResponse status_code=503 | ✓ |
| 422 при locked/unsupported combo (190) | :224-254 raise HTTPException(422) | ✓ |
| FORCE_RECOMPUTE обходит кеш (103,182) | :919 `if not force and cache_path.exists()`; label в ConfigureBacktest.tsx:313 | ✓ (label реальный) |

## Цитаты line-range — все точны (проверено пофайлово)
- app.py:349–374 (main) ✓; 353–370 (host/uvicorn) ✓; 54–55,144–161 (dist/mount) ✓; 135 (create_app) ✓; 318–330 (middleware) ✓; блок кода 114–118 = :324-327 byte-perfect ✓; 2–4 (no auth docstring) ✓; 57–109 (symbol validator) ✓; 153–161 (503) ✓; 221–254 (locked/combo) ✓; 163–312 (endpoints) ✓.
- backtest_runner.py: 47–286 (STRATEGY_PRESETS) ✓; 291–296 (INTERVAL_LABELS) ✓; 857–921 (run_id + cache) ✓; 919 (force) ✓.
- account_service.py: 110–172 (get_account_balance) ✓; 37–38 (TTL) ✓; 159–162 (cache only success) ✓.
- App.tsx:21–26 (TABS 01-04) ✓ EXACT; 28–99 (App component) ✓.
- HistoryTab.tsx: "Начальный баланс"/"Итоговый баланс"/"Win rate" :123/127/131 ✓; renderSummary RU :61-99 ✓; Escape :183 ✓; "✕ закрыть" :324 ✓.
- dashboard.sh: проверка .venv :9, import fastapi :15, exec -m src.dashboard.app :26 ✓.
- types.ts (source_files) существует ✓.

## Проверка на ловушку из памяти (glossary-tab shard)
Shard предупреждал о **architect-C3 misattribution** ("данные в Python не в БД → C3"). На ЭТОЙ странице такого утверждения НЕТ — глоссарий описан нейтрально (строки 78, 200), C3/C1/C4 не приписываются. Ловушка НЕ повторена. ✓

---

## WARN (неточности, не вводят в заблуждение)

### WARN-1 — цитата threading.Lock указывает на docstring, а не на код
Строка 184: "Внутри `run_backtest()` стоит `threading.Lock`... (backtest_runner.py:10)".
- :10 — это строка docstring ("Concurrency: 1 backtest at-a-time... Simple threading.Lock").
- Фактический механизм: `_lock = threading.Lock()` :315, а `with _lock:` :931 (обёртка вокруг `_run_backtest_locked`, DASH-03 single-flight по ВСЕМ путям стратегий).
- Факт ("один расчёт за раз, второй ждёт") — ВЕРНЫЙ. Только цитата ведёт на упоминание в docstring, а не на реализацию (:931). Для точности лучше `:315, 931`.

### WARN-2 — таблица эндпоинтов не полна ("что делает каждый адрес")
Строки 66-82: заголовок "Таблица эндпоинтов (что делает каждый адрес)". Таблица перечисляет 11 из 14 публичных маршрутов. Пропущены:
- `GET /api/strategy/{id}/info` (:177)
- `GET /api/strategy_explanation/{id}` (:291)
- `GET /api/wfa_criterion_explanations` (:299)
(+ внутренний SPA catch-all `/{path:path}` :337 — правомерно опущен.)
Ни одно перечисленное значение не искажено; проблема лишь в слове "каждый" при неполном списке. Для лей-аудитории приемлемо, но формулировку "основные эндпоинты" было бы точнее.

### WARN-3 — семантика баланса упрощена (не искажает)
Строка 130 + таблица (79): "Текущий баланс Bybit-аккаунта". Код возвращает `wallet_balance` (total held, incl. locked) → маппится в `total_equity_usdt` (account_service.py:15, 150-151). Поле называется total_equity, но берётся wallet_balance. Для не-программиста «баланс» — корректное упрощение; отмечаю как нюанс, не ошибку.

---

## DEEP (тонкий нюанс, обычный чеклист не ловит)

### DEEP-1 — run_id НЕ включает `variant`, а страница подаёт хеш как «полный набор параметров»
Строка 101: "run_id — уникальный идентификатор запроса: первые 16 символов SHA-256 от комбинации (стратегия + символ + таймфрейм + дата начала + дата конца)".
- Это верно для 5 полей. НО у `BacktestRequest` есть 6-е поле `variant: str = "base"` (:855, "base"|"mini" для Kronos T6), которое **НЕ входит** в строку хеша (:858).
- Практический смысл: два запуска Kronos с разными variant → **одинаковый run_id** → второй отдаст закешированный результат первого (если не force). Для текущего dashboard-flow variant всегда "base" (в run_backtest не прокидывается), поэтому коллизии на практике сейчас нет — но это скрытая зависимость.
- Для доки это НЕ ошибка (variant не экспонируется в UI). Отмечаю как DEEP, потому что утверждение «уникальный идентификатор запроса» строго говоря неполно: run_id уникален по 5 из 6 полей запроса. Если в будущем variant попадёт в UI без правки run_id() — кеш-коллизия. (Это скорее замечание к КОДУ, см. ниже — но severity низкая, т.к. сейчас недостижимо.)

---

## Итог
Одна из самых чистых страниц: все line-cites точны, все числа сходятся при пересчёте, ловушка C3 из памяти не повторена, выдуманных сущностей нет. Замечания косметические (цитата на docstring вместо :931; неполнота таблицы эндпоинтов) + один архитектурный нюанс run_id/variant, не достижимый из текущего UI.
