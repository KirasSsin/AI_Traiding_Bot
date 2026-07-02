# Глубинное ревью (КОРРЕКТНОСТЬ): main-loop-tick.md

Страница: `docs/01-как-работает-бот/main-loop-tick.md`
Источники сверки: `src/runtime/manager.py`, `src/runtime/bar_source.py`, `src/marketdata/quality.py`, `src/platform/config.py`, `src/execution/coordinator.py`, `src/execution/state_machine.py`, `src/execution/bybit/ws_private.py`.
Дата: 2026-06-27.

**Verdict: REQUEST_CHANGES** — 2 BLOCKER (один — выдуманное поведение на safety-critical kill-switch; один — численная ошибка в 60×). В остальном страница исключительно точна: все ~25 цитат `file:line` byte-exact, все 4 сценария и все формулы пересчитаны и сходятся, все 6 wikilink резолвятся, все сущности существуют.

---

## BLOCKER

### B1. Kill-switch «отправляет бирже команду KILL_SWITCH_REQUESTED» — выдуманное поведение (вводит в заблуждение на safety-странице)

Док, строка 90:
> «Оператор … создаёт файл с таким именем — и бот на следующем тике замечает его, **отправляет бирже команду KILL_SWITCH_REQUESTED** и завершает работу.»

**Факт против кода:**
- `_maybe_kill_switch` (manager.py:286-296) вызывает `self._coordinator.request_halt(ReasonCode.KILL_SWITCH_REQUESTED)` + `self._stopping = True`.
- `request_halt` (coordinator.py:1001-1031) **только** (а) пишет `halt_reason` в локальную БД через `_set_halt`, и (б) делает внутренний FSM-переход → `HALTED` (для KILL — через event `KILL_SWITCH_REQUESTED`). Никаких сетевых вызовов к Bybit.
- `KILL_SWITCH_REQUESTED` — это внутренний `ReasonCode`/`ExecutionEvent`, а НЕ команда/сообщение, отправляемое бирже. В FSM (state_machine.py:174-191) это просто переход «любое состояние → HALTED»; комментарий: «operator HALT (NOT terminal)».
- В `src/runtime/manager.py` НЕТ ни одного `cancel_order`/`cancel_all` (grep пуст). Путь shutdown (`_shutdown` → `ws.stop()` → `self._ws.exit()`, ws_private.py:173-176) лишь закрывает WebSocket-соединение — он НЕ отменяет ордера и НЕ шлёт бирже «kill».

**Почему это важно (не косметика):** читатель-не-программист на странице про безопасность сделает вывод, что стоп-файл активно уведомляет Bybit / снимает позиции. На деле после kill-switch **живые TP/SL-ордера остаются висеть на бирже** — бот просто перестаёт за ними следить и помечает себя HALTED локально. Это опасное заблуждение именно про safety-механизм.

**Фикс:** заменить на формулировку без «отправляет бирже команду», например: «…помечает себя остановленным с причиной `KILL_SWITCH_REQUESTED` (внутренний код), переводит свой конечный автомат в `HALTED` и завершает цикл. Команда бирже при этом НЕ отправляется — уже выставленные на бирже ордера (TP/SL) остаются активными; kill-switch только прекращает работу бота.» (Сослаться на [[kill-switch-emergency-stop]] для деталей.)

*(Это тот же класс ловушки, что уже зафиксирован в shard'ах: HaltGate `request_halt` НЕ отменяет ордера; kill-switch — внутренний код, не команда бирже.)*

---

### B2. «12 тиков»/«12 раз» в час — ошибка в 60× (при кадансе 5 c в часе 720 тиков)

Док, строка 382 (Подводный камень №2):
> «Без этого за один часовой период **(12 тиков)** стратегия могла бы выдать один и тот же сигнал **12 раз**.»

**Пересчёт:** каданс по умолчанию `runtime_bar_poll_cadence_seconds = 5.0` (config.py:210-211; сам док верно повторяет «тик каждые 5 секунд» на строках 38, 59, 206). За час: `3600 / 5 = 720` тиков. Не 12.

«12» соответствовало бы кадансу 5 **минут** (`3600/300=12`), которого в системе нет. Цифра противоречит и коду, и собственному тексту страницы (строки 38/59/206). → численный BLOCKER.

**Фикс:** «за один часовой период (≈720 тиков при кадансе 5 с) стратегия могла бы выдать один и тот же сигнал сотни раз.»

---

## WARN

### W1. `check_alive` сверяет ping, а не «что-нибудь прислала»
Док строка 108: «проверяет, когда в последний раз биржа Bybit прислала **что-нибудь**…». Код (ws_private.py:154-171) сверяет `self._ws.last_ping_time` (heartbeat-пинги pybit), а не произвольное сообщение/ордер-апдейт. Для не-программиста упрощение приемлемо, но строго это «время последнего ping». Незначительно вводит в заблуждение про то, что именно поддерживает «живость».

### W2. Каданс «несколько секунд» в заголовке/TL;DR vs фикс. 5 c
Заголовок «каждые несколько секунд» — ок как обобщение; тело корректно фиксирует 5.0 c. Не ошибка, отмечено для полноты.

---

## DEEP

### D1. OCO-TTL halt НЕ выставляет `self._stopping=True` (в отличие от kill/stall/quality)
Док строка 151: «Если завис — … бот останавливается (ADR 0020 sub-decision 11)». Поведение подтверждено частично: `reconcile_arming_ttl` (coordinator.py:877-901) при `age > ttl_seconds` делает `_set_halt(HALT_OCO_ARM_TIMEOUT)` + `_transition(BRACKET_TIMEOUT)` → `HALTED`. Но, в отличие от шагов 1/2/5 тика, тут НЕ выставляется `RuntimeManager._stopping`. Т.е. FSM уходит в `HALTED` (торговля фактически прекращается), но главный цикл сам по себе не получает сигнал `_stopping`. Для нарратива страницы «бот останавливается» — допустимо (HALTED = торговли нет), но это тонкое отличие пути OCO-TTL от остальных halt-путей. Не блокер; на случай будущего уточнения.

### D2. Окно `_fetch` = 2 интервала, не гарантированно «ровно 2 свечи»
Док строка 180: «Bybit отдаёт последние 2 свечи за период в 2 часа назад». Код: `start_ms = end_ms - step_ms*2` (bar_source.py:107) — это окно в 2 интервала; в зависимости от выравнивания границ Bybit может вернуть 2 или 3 свечи. Комментарий кода сам говорит «last 2 bars window». Логика отбора (`look-ahead` + dedup) корректна при любом числе. Незначительно; «2 свечи» — упрощение.

---

## Полностью проверено и ВЕРНО (recompute + cite Bash-exact)

**Цитаты `file:line` — все byte-exact:**
- `_main_loop` 153-160; `_tick` 162-178; `_maybe_kill_switch` 286-296; `_check_alive_inline` 298-302; `_exit_reason` 304-317; `should_halt`-блок 327-335; quality-check 341-344; `on_bar` 345-348; FLAT→flatten 363-371; non-flat skip 373-379; risk.assess 380-387; `start_bracket` 403-408; clean-stale-kill 117-118.
- bar_source: poll/failure 62-73; look-ahead 76-87 (код-блок дока 184-191 совпадает по логике, сжат комментарий); dedup 88-92; `_fetch` 105-113.
- config: `runtime_bar_poll_cadence_seconds` 210-213; `runtime_kill_switch_path` 222-225; `runtime_ws_check_alive_max_silence` 226-229; `runtime_bar_poll_stall_threshold` 214-220; `runtime_quality_threshold_pct` 234-241; HaltGate table 132-155; mainnet-exclusion validator 261-285 (реально 261-291, цитата приземляется внутри).
- quality.py: формула 65-67; threshold-rationale 15-18 (док «14-18» — старт на пустой строке 14, контент 15-18); first-bar-passes 58-62.
- manager symbol-whitelist + HALT_UNKNOWN_SYMBOL 199-208.

**Сущности — все существуют:**
- `ReasonCode`: KILL_SWITCH_REQUESTED, HALT_BAR_POLL_STALL, HALT_DATA_QUALITY, HALT_UNKNOWN_SYMBOL, EXIT_SIGNAL_FLIP ✓.
- `ExecutionState`: FLAT, LONG_OPEN, OCO_ARMING, OCO_ARMED ✓; `_FLATTENABLE_STATES` = {LONG_OPEN, OCO_ARMING, OCO_ARMED} (manager.py:54-60) ✓.
- `SignalSide` = {LONG, FLAT} ✓ (нет шортов — pitfall #7 верен).
- coordinator: `current_state` (150), `start_bracket` (336), `flatten` (687), `reconcile_arming_ttl` (877) ✓.
- `_DEFAULT_EXIT_REASON = EXIT_SIGNAL_FLIP` (manager.py:64) ✓.
- `risk_manager.assess(signal, *, mark_price)` (manager.py:380; risk/manager.py:202) ✓.
- ADR 0020 / ADR 0022 существуют ✓.

**Числа/формулы — пересчитаны:**
- Stall: floor 6×5=30 c ✓; ceil 720×5=3600 c=60 мин ✓; default 24×5=120 c=2 мин ✓ (строка 224, формула 366-372). Валидатор `6 ≤ N ≤ 720` (config.py:245) ✓.
- HaltGate пороги: dd_intraday 0.20, dd_multiday 0.15, consec 5, no_trade_months 6 ✓ (config.py:132-155).
- Quality threshold 0.005 = 0.5% ✓; формула `abs(cur-prior)/prior`, строгий `>` (quality.py:65-66) ✓.
- Сценарий B: `|100200-100050|/100050 = 0.1499%` < 0.5% → проходит ✓ (док «0.15%»).
- Сценарий D: `|102000-100050|/100050 = 1.949% ≈ 1.95%` > 0.5% → True ✓ (док «≈1.95%»).
- `should_halt`: `consecutive_failures >= threshold` (bar_source.py:96) — согласуется с «24 сбоя → halt».
- `reconcile_arming_ttl`: `age > ttl_seconds` (строгий) → HALT_OCO_ARM_TIMEOUT + BRACKET_TIMEOUT → HALTED (ADR 0020 sub-decision 11 — docstring подтверждает) ✓; TTL=60 (config.py:177) ✓.

**Поведенческие утверждения — верны:**
- Порядок шагов тика (kill→alive→halt_gate→reconcile→poll) точно по manager.py:171-178 ✓.
- HaltGate активен только при `s35_demo_active=True` (manager.py:175, 193) ✓; на mainnet флаг обязан быть False, валидатор блокирует (config.py:279-290) ✓.
- Вход только из `FLAT` (manager.py:373) ✓; FLAT→flatten только если позиция держится (manager.py:363-371) ✓.
- Дедуп по `_last_close_ts` (bar_source.py:88-91) ✓; первая свеча после рестарта проходит (quality.py:61-62) ✓; counter сбрасывается при успехе (bar_source.py:73) ✓.
- Quality-check размещён под `_poll_bar_and_strategy` (верно: manager.py:341-344) — страница НЕ повторяет ошибку «в _tick» из data-quality shard.

**Wikilinks (6):** startup-and-wiring, safety-stops-and-halts, oco-bracket-emulation, risk-overview-decision-pipeline, execution-state-machine, kill-switch-emergency-stop — все резолвятся (find подтвердил пути в 01/04/05). Footer-указатель на `llm-wiki/.../runtime-manager.md` + ADR 0022 — корректны.

---

## Сводка
- recomputed: 11 (720 тиков/час; B/D отклонения; stall floor/ceil/default; 4 порога HaltGate; quality 0.5%; should_halt оператор).
- BLOCKER: 2 (B1 выдуманное «команда бирже» на kill-switch; B2 «12 тиков» вместо 720).
- WARN: 2. DEEP: 2.
