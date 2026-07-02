# Глубинное ревью (КОРРЕКТНОСТЬ против кода): coordinator-orchestration.md

**Страница:** `docs/05-исполнение-ордеров/coordinator-orchestration.md`
**Дата:** 2026-06-26
**Ось:** соответствие каждого утверждения/числа/формулы фактическому `src/`
**Источники кода:** `src/execution/coordinator.py`, `src/execution/state_machine.py`, `src/execution/bracket.py`, `src/platform/config.py`, `src/runtime/manager.py`, `src/execution/bybit/errors.py`, `docs/_навигация/inventory.json`

**Verdict:** APPROVE_WITH_CONCERNS
**BLOCKER: 1 | WARN: 3 | DEEP: 0**
**Пересчитано чисел/симуляций: 7** (oco_qty Scenario A; 3 FSM-цепочки сценариев A/B/C через `apply()`; sibling-cancel-failed ветка; counts states=16/events=30/transitions=76; TTL strict-сравнение)

---

## Итог

Содержательная часть страницы **по фактам практически безупречна**. Все поведенческие утверждения, формула `compute_oco_qty`, все три сценария (включая FSM-цепочки), тонкая нумерация попыток (`entry-1` / `tp-2`), и код ошибки дубликата `110072` — **подтверждены кодом и пересчётом**. Писатель не повёлся на устаревший docstring в коде (который говорит «10006» для дубликата) и использовал правильный `110072`.

Единственный материальный дефект — **4 из 6 wikilink в «Связанных документах» битые** (указывают на несуществующие slug). Плюс косметика: систематический off-by-one в цитатах строк (`def` на строку ниже цитаты) и устаревшая фраза «65+ переходов» (реально 76).

---

## BLOCKER

### B1. Четыре битых wikilink в «Связанные документы» (строки 265–268)

Канонические slug подтверждены реестром `docs/_навигация/inventory.json` (генерация «S56 WF-1») + соглашением «slug = имя файла без расширения». Frontmatter не содержит `slug:`/`aliases:` → резолюция строго по имени файла.

| Wikilink в доке | Slug в доке | Реальный файл / канонический slug | inventory.json |
|---|---|---|---|
| `[[05-исполнение-ордеров/state-machine]]` | state-machine | `execution-state-machine.md` | строка 1290 |
| `[[05-исполнение-ордеров/bracket-legs]]` | bracket-legs | `oco-bracket-emulation.md` (нет `bracket-legs.md`) | строка 1251 |
| `[[05-исполнение-ордеров/bybit-adapter]]` | bybit-adapter | `bybit-order-adapter.md` | строка 1441 |
| `[[05-исполнение-ордеров/reconciler]]` | reconciler | `reconcile-as-truth.md` (нет `reconciler.md`) | строка 1403 |

Канонические slug используются 3–6 другими страницами docs/ — это и есть истина. Не-программист, кликнув по этим ссылкам, попадёт в никуда (404). Тот же кластер slug-drift, что задокументирован на соседних страницах (state-persistence, emergency-flatten). Информация не выдумана — страницы существуют под другими именами — но ссылки сломаны.

**NB:** `[[09-глоссарий/oco-emulation]]` и `[[09-глоссарий/fail-closed]]` (строки 269–270) — **НЕ флагать**: это соглашение «запланированный глоссарий» (папки `docs/09-глоссарий/` ещё нет; 69 таких ссылок по всему docs/).

**Фикс:** заменить 4 slug на канонические.

---

## WARN

### W1. Систематический off-by-one в цитатах строк coordinator.py

Писатель последовательно цитировал строку *перед* `def` (пустую строку / начало docstring). Диапазон всё равно содержит нужный код, поэтому не вводит в заблуждение, но строго неточно:

| Утверждение | Цитата в доке | Реальная строка |
|---|---|---|
| `start_bracket()` | 335–398 | def на 336 |
| `on_order_event()` | 399–460 | def на 400 |
| `_arm_oco_after_entry_fill()` | 461–518 | def на 462 |
| `current_state()` | 149–171 | def на 150 |
| RLock | 138–139 | на 139 (138 = `_bootstrap_done`) |
| `parts[-2]` | «строка 938» | литерал `return parts[-2]` на 939 (938 = `parts = link_id.split("-")`) |

**Точные цитаты (НЕ дефект):** bracket_id uuid «351» ✓; 110001-успех «928» ✓; `arm_oco` «612–685» ✓; `_cancel_sibling` «913–931» ✓; `reconcile_arming_ttl` «877–901» ✓; config «177» ✓; enum состояний «12–28» ✓; `apply`/`IllegalTransitionError` «195–200» ✓; `TRANSITIONS` «71–192» ✓; bracket «116–133» ✓.

### W2. Кросс-ссылка «65+ переходов» занижена (строка 265)

Дока в описании ссылки на FSM-страницу пишет «65+ переходов». Реально в `TRANSITIONS` — **76** (подтверждено `len(TRANSITIONS)` и соседней страницей `execution-state-machine.md:37`, которая пишет «76»). «65+» формально истинно (76 ≥ 65), но фраза устарела и расходится с братской страницей. Привести к «76».

### W3. Pitfall 4 чрезмерно обобщает 110072-как-успех (строки 249–250)

Дока: «Каждый логически новый ордер имеет уникальный `orderLinkId`. Если ... один и тот же запрос дошёл до биржи дважды — второй вернёт код `110072` ... Мы считаем это успехом».

В коде трактовка `110072 = успех` реализована **только для flatten/residual Market Sell** (coordinator.py:586, 812). Вход (`start_bracket`) и плечи арминга (`arm_oco`) НЕ ловят 110072 как успех — исключение в `arm_oco` просто логируется, FSM остаётся в `OCO_ARMING` (строки 670–685). Формулировка «каждый логически новый ордер» — мягкое преувеличение; механизм (детерминированный orderLinkId → дедуп Bybit → успех) реален, но область применения уже. Упрощение, не вводящее грубо в заблуждение → WARN.

---

## Проверено и ВЕРНО (анти-re-flag)

**Канонические числа.**
- 16 состояний (`len(ExecutionState)` = 16) — строки 36, 51, 265 ✓
- 30 событий (дока не заявляет число — ОК)
- 76 переходов (`len(TRANSITIONS)`), 0 SHORT-переходов → «нет шорт-переходов / бот только в лонг» (строки 255–256) ✓
- TTL = 60: config.py:177 `oco_arming_ttl_seconds: int = 60`; manager.py:177 передаёт `ttl_seconds=settings.oco_arming_ttl_seconds`; `reconcile_arming_ttl` default = 60 (строка 877). Строки 189, 226–227 ✓

**Формула `compute_oco_qty` (строки 127–134).** Псевдокод совпадает с bracket.py:130–133 (опущен guard `if net<=0: return 0` — допустимое упрощение). Пересчёт Scenario A: `floor((0.01−0.00001)/0.001)·0.001 = floor(9.99)·0.001 = 0.009` — **Bash-точно** через `compute_oco_qty(...)`.

**Тонкая нумерация попыток.** Scenario A: вход `oco-a1b2c3d4-entry-1` (attempt=1, start_bracket coord:359), TP `oco-a1b2c3d4-tp-2` (arm_oco `attempt = last_attempt_num + 1`, coord:644). Писатель верно поставил `tp-2` (а не `tp-1`).

**Код дубликата 110072 (НЕ 10006).** Дока Pitfall 4 использует `110072` = errors.py:45 `REJECT_DUPLICATE_ORDER`. Устаревший docstring `arm_oco` (coord:622) ошибочно пишет «10006», но 10006 = `RATE_LIMIT_HIT` (errors.py:31). Дока НЕ повторила эту ошибку кода. Это плюс доке.

**FSM-цепочки всех сценариев (симуляция через `apply()`):**
- Scenario A: `FLAT → ENTRY_PENDING → LONG_OPEN → OCO_ARMING → OCO_ARMED → EXIT_SIBLING_CANCELLING → FLAT` ✓ (строки 214–220)
- Scenario B: `OCO_ARMING → HALTED` (BRACKET_TIMEOUT; age 63 > 60) ✓ (строки 226–227)
- Scenario C: `OCO_ARMED → EXIT_SIBLING_CANCELLING → FLAT` (SL_TRIGGERED, затем SIBLING_CANCELLED) ✓ (строки 231–234)
- Ветка отказа отмены: `EXIT_SIBLING_CANCELLING → EXIT_SIBLING_CANCEL_FAILED` ✓ (строка 172; state_machine.py:116)

**Прочие поведенческие утверждения:**
- 110001 = успех в `_cancel_sibling` (coord:928 `res.cancelled or reason is REJECT_ORDER_ALREADY_TERMINAL`) ✓; 0мс Triggered→Filled gap ✓ (строка 170)
- Терминальный дроп: FLAT/HALTED/KILLED/ERROR молча отбрасываются с warning (coord:421–430) ✓ (строка 89)
- Роутинг-таблица (строки 93–98): `entry+Filled`→арминг, `sl+Triggered`→отмена TP, `tp+Filled`→отмена SL, `sl+PartiallyFilled`→спецобработка — все совпадают (coord:432–450) ✓
- Механизм `arm_oco` (строки 153–161): отмена-старых-первой (640–643), bump attempt (644), TP→`OCO_ARMING` (TP_PLACED), SL→`OCO_ARMED` (SL_PLACED), TP-один→остаётся `OCO_ARMING` ✓
- Fail-closed при отсутствии цен/нулевом qty → HALT_OCO_ARM_TIMEOUT (coord:477–489, 500–513) ✓ (строки 111, 243–244)
- `current_state` S55 ARCH-03 TOCTOU-нарратив совпадает с docstring (coord:150–168) ✓ (строки 180–183); RLock реентрантный (139) ✓; ARCH-02 off-lock REST (coord:180–192, 266–284) ✓ (~15.5с округлено до ~15с — ОК)
- `arming_started_at` пишется ДО первой постановки (arm_oco upsert 650–656 перед try-place 657) — Pitfall 7 ✓ (строки 258–259)
- start_bracket пишет state=ENTRY_PENDING + bracket_tp/sl_price (coord:373–396) ✓ (строки 70–72)
- IllegalTransitionError логируется, не роняет воркер (coord:451–460) ✓ (строки 100, 252–253)

**Выдуманных сущностей НЕТ.** Все упомянутые методы/функции/состояния/события/reason-коды существуют: `start_bracket`, `on_order_event`, `_arm_oco_after_entry_fill`, `arm_oco`, `_cancel_sibling`, `current_state`, `reconcile_arming_ttl`, `build_bracket`, `compute_oco_qty`, `make_order_link_id`, `IllegalTransitionError`, `EXIT_SIBLING_CANCEL_FAILED`, `BRACKET_TIMEOUT`, `HALT_OCO_ARM_TIMEOUT`, `oco_qty`, `bracket_id`, RLock.

**ADR-футер (строки 272–273):** ADR 0020 (sub-decisions 2–11), 0021, 0022 — все существуют; ADR 0020 имеет sub-decisions 1–11+. NB: ADR 0020:170 говорит «21 состояние» (дрейф ADR↔код), но дока пишет «16» (совпадает с кодом) — дока права, не её проблема.

**Страница НЕ повторяет ошибку halt-gate** («request_halt отменяет ордера») — этого утверждения на странице нет. Чисто.

---

## Рекомендации (приоритет)

1. **[BLOCKER]** Исправить 4 slug в «Связанных документах»: `state-machine`→`execution-state-machine`, `bracket-legs`→`oco-bracket-emulation`, `bybit-adapter`→`bybit-order-adapter`, `reconciler`→`reconcile-as-truth`.
2. **[WARN]** Поправить «65+ переходов» → «76 переходов» (строка 265).
3. **[WARN]** (опц.) Сдвинуть 6 цитат строк на +1 к фактическому `def` — косметика, низкий приоритет.
4. **[WARN]** (опц.) Уточнить Pitfall 4: трактовка 110072-как-успех относится к flatten/residual-путям, не к входу/армингу.
