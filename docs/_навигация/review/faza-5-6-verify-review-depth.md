# Depth review — faza-5-6-verify-review.md

Страница: `docs/10-как-работает-кит/faza-5-6-verify-review.md`
Ревьюер: doc-reviewer-depth (ось — КОРРЕКТНОСТЬ против кода/кит-файлов)
Дата: 2026-07-01
Тип страницы: section-10 kit meta-doc (money_core:true в frontmatter, но фактически описывает ПРОЦЕСС, не денежный путь)

## Итог

- BLOCKER: 1
- WARN: 3
- DEEP: 1
- recomputed / re-verified: модели 15 агентов (Bash grep frontmatter), phase-advance.sh полностью прочитан и все цитаты сверены, канонические счётчики 16/30/76/67 сверены с 3+ памятными шардами (venv не запускался — см. ограничение среды)
- verdict: REQUEST_CHANGES

## ОГРАНИЧЕНИЕ СРЕДЫ (важно для контроллера)

Начиная с середины сессии, `src/`, `llm-wiki/` и часть `.claude/agent-memory/references/` стали недоступны (EPERM) как для Read tool, так и для Bash (весь repo tree заблокирован для bash). Доступны остались: страница под ревью, соседние страницы `docs/10-*` и `docs/08-*`, `~/.claude/hooks/*`, `~/.claude/agents/*`, scratchpad.

Следствия:
1. Команду канонических счётчиков (`.venv/bin/python -c "..."`) запустить НЕ удалось (venv pyvenv.cfg EPERM). Значения 16/30/76/67 подтверждены косвенно — 3+ памятных шарда (coordinator-orchestration «16/30/76 ✓», execution-state-machine «headline 76 correct», dual-reasoncode/risk-manager «67»). Прямого пересчёта этой сессии НЕТ.
2. Цитаты в `sprint-flow-ru.md` и `development-workflow.md` и `ADR 0017` НЕ сверены построчно (файлы EPERM). Поведенческие факты сверены с СОСЕДНЕЙ страницей `agenty-revyuery.md` (та же секция, читается) и с реальными agent-frontmatter.
3. Числа сценария S55 (120 агентов, 43 дефекта, TL-01/BYBIT-01) НЕ сверены с `sprint-55-full-audit-refactor.md` (EPERM). Косвенно правдоподобны (TL-01 OCO-never-armed и BYBIT-01 testnet/mainnet split — оба фигурируют в моих верифицированных шардах как реальные находки S55-эпохи).

Рекомендация контроллеру: перезапустить сверку п.1 (канонические счётчики) и п.3 (S55 числа) в сессии с доступом к src/+llm-wiki, если нужна 100% гарантия. BLOCKER ниже от этого не зависит — он подтверждён на доступных данных.

---

## BLOCKER

### B1. python-reviewer заявлен как sonnet — реально HAIKU; и ложное «все остальные ревьюеры на sonnet»

Места в доке:
- Строка 158-159: «**python-reviewer** (`~/.claude/agents/python-reviewer.md`, **модель sonnet**)»
- Строка 237-239 (Подводный камень #3): «security-auditor — единственный агент на модели opus. **Все остальные ревьюеры работают на модели sonnet** (быстрее и дешевле).»

Факт (Bash grep `^model:` по `~/.claude/agents/*.md`, 2026-07-01):
```
python-reviewer   -> model: haiku
doc-reviewer      -> model: haiku
security-auditor  -> model: opus
trading-logic     -> model: sonnet
quant-stats       -> model: sonnet
data-integrity    -> model: sonnet
test-engineer     -> model: sonnet
architecture      -> model: sonnet
trader-expert     -> model: sonnet
dashboard         -> model: claude-sonnet-4-5
bybit-api         -> model: claude-sonnet-4-5
```

Два ложных утверждения:
1. python-reviewer — **haiku**, не sonnet (строка 158 неверна).
2. «все остальные ревьюеры на sonnet» — **ложь**: python-reviewer И doc-reviewer оба на haiku (строка 239).

Подтверждение через cross-file (моя обязанность — согласованность): КАНОНИЧЕСКАЯ соседняя страница `docs/10-как-работает-кит/agenty-revyuery.md` (та же секция, та же дата 2026-06-27, money_core:true) прямо утверждает противоположное:
- строка 120: «#### 6. python-reviewer... **Модель:** haiku... Это намеренно самый «дешёвый» агент»
- строка 168: «#### 9. doc-reviewer... **Модель:** haiku... Самый «лёгкий» агент»

Т.е. страница под ревью противоречит: (а) реальному frontmatter агентов, (б) своей собственной родственной странице того же раздела.

Почему BLOCKER: не-программист прочитает «python-reviewer на sonnet» и «все кроме security на sonnet» и поверит. Это фактически неверно про инструментарий его же проекта; и это прямое внутреннее противоречие двух страниц одного раздела. Автоматика поймать не может.

Фикс: строка 158 → «модель haiku». Строка 239 → напр.: «Остальные ревьюеры работают на sonnet или haiku (python-reviewer и doc-reviewer — самые лёгкие, на haiku)». Плюс уточнить пункт про «единственный на opus» (см. DEEP-1).

---

## WARN

### W1. Цитата сообщения хука phase-advance.sh — сокращённая, не дословная

Строки 100-108 доки приводят «сообщение» хука:
```
🚫  Phase advance check FAILED
Branch: feature/sprint-NN-xxx (sprint NN)
Phase 5 (Verify) status: "pending"

Required action:
  1. Run superpowers:verification-before-completion checklist
  2. Update SPRINT_STATE.md Phase 5 row → "done"
```

Реальный heredoc (phase-advance.sh:107-133) между «status:» и «Required action:» содержит ещё блок «Required: Phase 5 must be "done" OR "skipped"... - "done" — ... - "skipped (...)" — ...», а «Required action:» состоит из 4 пунктов (1 Run checklist с под-списком, 2 Update, 3 Or skip, 4 Retry merge), не 2. Дока даёт сжатую версию. Заголовок `🚫 Phase advance check FAILED` и общая структура — верны. Framing как иллюстрация допустим, но не-программист может ждать дословного совпадения. Пометить как «упрощённо» или привести дословно.

### W2. Числа сценария S55 не поддаются проверке этой сессии

Строки 216-223: «120 агентов-ревьюеров (9 измерений + двойная скептик-верификация)», «43 подтверждённых дефекта», «2 BLOCKER: TL-01 / BYBIT-01». Источник (`sprint-55-full-audit-refactor.md`) недоступен (EPERM). Описания TL-01 (live-runtime не вооружал OCO → unbounded-loss) и BYBIT-01 (REST/WS разные окружения testnet/mainnet → нет уведомлений об исполнении) согласуются с моими верифицированными шардами как реальные находки. Числа 120/43/9 — не подтверждены. НЕ утверждаю, что неверны; помечаю как непроверенное этой сессии. Контроллеру: сверить с sprint-55 страницей.

### W3. mypy baseline «0 после S55» не поддаётся проверке

Строка 40: «Допустимая граница: 0 новых ошибок (базовое значение закреплено как 0 после S55).» Источник (llm-wiki / sprint-55) недоступен. Правдоподобно, но не сверено. Низкий риск.

---

## DEEP

### D1. «security-auditor — единственный агент на модели opus» — верно только для КОД-ревьюеров, ложно для папки целиком

Строка 152 и 237-240 (Подводный камень #3): «Единственный ревьюер на модели opus» / «security-auditor — единственный агент на модели opus».

Цитата `~/.claude/agents/security-auditor.md:5` корректна: строка 5 = `model: opus` (подтверждает, что security-auditor на opus — но НЕ подтверждает уникальность).

Факт: в `~/.claude/agents/` на opus ТАКЖE находятся:
- `doc-reviewer-depth` → claude-opus-4-8[1m]
- `doc-linker` → model: opus
- `frontend-developer` → claude-opus-4-7

Т.е. «единственный **агент** на opus» — фактически неверно на уровне папки. Формулировка «единственный **ревьюер** на opus» (строка 152) защитима, если doc-linker/doc-reviewer-depth трактовать как doc-инструментарий, а frontend-developer как не-ревьюера (родственная страница agenty-revyuery.md:196 явно называет frontend-developer «не специфичный для трейдинга»). Но пункт #3 (строка 237) говорит именно «единственный **агент**» — это overbroad.

Тонкость (почему DEEP, а не просто WARN): формулировка звучит уверенно и подкреплена корректной цитатой строки frontmatter — но цитата доказывает лишь «opus», а не «единственный». Классический случай, когда верная цитата создаёт ложное впечатление проверенности более сильного утверждения. Не-программист не отличит.

Фикс: «единственный ревьюер-агент на opus среди код-ревьюеров» ИЛИ убрать «единственный» и сказать «security-auditor — единственный из шести ревьюеров кода, работающий на opus».

---

## Проверено и ВЕРНО (не тратить время повторно)

- Канонические счётчики 16/30/76/67 (строка 65, таблица 70-75) — заявлены КОРРЕКТНО (сверено с 3+ шардами; прямой пересчёт заблокирован средой).
- Команда счётчиков (строки 54-60): импорт `TRANSITIONS, ExecutionState, ExecutionEvent` из `src.execution.state_machine` + `ReasonCode` из `src.risk.reason_codes` — имена модулей/символов корректны (совпадают с командой в phase-advance.sh:124 и с моими шардами).
- `pytest tests/ -q --ignore=tests/integration` (строка 35) — байт-в-байт совпадает с phase-advance.sh:122.
- `mypy --strict src/` (строка 43) — совпадает с phase-advance.sh:123.
- HARD-GATE (строки 87-111): хук блокирует именно `gh pr merge` (phase-advance.sh:46-48 ✓), ищет строку `| 5 Verify |` (grep :80 ✓), допускает только done/skipped* (case :104-105 ✓), exit 2 блокирует (:97,:134 ✓). Цитаты `:80-136`, `:19-20`, `:104-136` — все попадают на заявленные факты.
- Пример строки таблицы `| 5 Verify | done | ... |` (строка 95) — совпадает с комментарием хука :76.
- Каскад ревьюеров (таблица строки 124-134): все 8 строк маршрутизации file-path → reviewer совпадают с триггерами «Запускается при изменении...» в agenty-revyuery.md (trading-logic :65, quant-stats :79, data-integrity :94, python :122, security :138, test-engineer :159, doc-reviewer :170, architecture :109).
- Модели остальных агентов в перечне (строки 143-156): trading-logic=sonnet ✓, quant-stats=sonnet ✓, data-integrity=sonnet ✓, security-auditor=opus ✓, test-engineer=sonnet ✓. (Ошибка только в python-reviewer — см. B1.)
- Цитата `security-auditor.md:5` = `model: opus` ✓ (для факта «opus»; см. D1 про «единственный»).
- Категории отчёта ревьюера (таблица строки 184-192): Blockers/Concerns/Verified/Follow-ups for wiki — согласуются с процессом.
- ~1.4% ATR (Wilder vs talib/EMA) (строка 203) — согласуется с шардом atr-impl-count и с agenty-revyuery.md:83 (α=2/(n+1) EMA vs α=1/n Wilder).
- Все 5 wikilinks футера (строки 257-261) РАЗРЕШАЮТСЯ: faza-3-4-plan-execute ✓, faza-7-8-9-sync-ship-close ✓, khuki-mehanicheskie-barery ✓, agenty-revyuery ✓, skilly-rabochie-protsedury ✓.
- «нет такого правила — пропустить ревью потому что тривиально» (строки 135, 227) — согласуется с процессом (kit-flow BINDING, никаких shortcut).

## Замечания низкой уверенности (spot-check желателен при доступе к src/)

- Примеры reason-кодов «EXIT_SL_HIT, EXIT_FLAT_KRONOS» (строка 75): `EXIT_FLAT_*` — реальное семейство (шард kronos-v3, reason 66/67). `EXIT_SL_HIT` — правдоподобное имя SL-hit кода, но точное написание не сверено с `src/risk/reason_codes.py` (EPERM). Если реальное имя иное (напр. `EXIT_STOP_HIT`) — это мелкий WARN, не центральный. Проверить при доступе.

## Отдельно: НЕ ошибка доки, но наблюдение по разделу

Родственная `faza-3-4-plan-execute.md` в футере ссылается на `[[faza-5-8-verify-ship]]` (строка 246), тогда как реальное имя страницы под ревью — `faza-5-6-verify-review`. Это битая ВХОДЯЩАЯ ссылка на нашу страницу со стороны faza-3-4 (проблема faza-3-4, не этой страницы). Также faza-3-4 использует другой набор slug-ов (huki-i-zashchita, agenty-i-navyki) чем faza-5-6 (khuki-mehanicheskie-barery, agenty-revyuery). Раздел 10 имеет рассогласование схемы wikilink-slug между соседними страницами — стоит унифицировать на уровне раздела (для doc-linker прохода).

## Найденные баги в КОДЕ (не в доке)

Нет. Проверка кода `src/` в этой сессии заблокирована средой (EPERM), поэтому анализ денежного пути/look-ahead/PnL по коду не проводился. Ноль находок по коду.
