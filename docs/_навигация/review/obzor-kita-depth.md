# Depth review — obzor-kita.md (раздел 10 «как работает кит»)

Страница: `docs/10-как-работает-кит/obzor-kita.md`
Дата ревью: 2026-07-01
Тип: meta-документация о ките разработки (не торговый код). Сверка против CLAUDE.md / llm-wiki / .claude/ / ~/.claude/hooks / ~/.claude/agents.
Verdict: **APPROVE_WITH_CONCERNS**

recomputed / verified: 18 проверяемых утверждений сверено с источниками.

---

## VERIFIED CORRECT (сверено с кодом/kit-файлами)

| # | Строка | Утверждение | Источник-подтверждение |
|---|--------|-------------|------------------------|
| 1 | L20 | ADR 0041 = process enforcement | `decisions/0041-sprint-28-process-enforcement.md` ✓ |
| 2 | L31 | `.claude/skills/` = sprint-orient, brainstorm-init, wiki-update, sprint-finish, hook-test, autoresearch-iterate, ponytail, ponytail-audit (8) | `ls .claude/skills/` — ровно эти 8 ✓ |
| 3 | L47 | «Superpowers (13 скиллов)» | kit-overview-ru:135 + sprint-flow-ru:655 «Superpowers skills (13)» ✓ |
| 4 | L69-79 | 9-фаз таблица: имена фаз + артефакты | sprint-flow-ru «Обзор фаз (9)» таблица — все совпадают (Orient=chapter, Brainstorm=pre-sN-backlog, Plan=plan file, Execute=commits, Verify=green, Review=blockers, Sync=components, Ship=tag+PR, Close=journal) ✓ |
| 5 | L107, L129 | `sprint-flow-check.sh` блокирует `git push` на feature/sprint-NN-* без plan file | Код хука подтверждает (`*"git push"*`, plans_dir check, pattern `<date>-sprint-N-<slug>.md`) ✓ |
| 6 | L129 | `phase-advance.sh` блокирует `gh pr merge` если Фаза 5 != done/skipped | Код хука подтверждает (`*"gh pr merge"*`, парсит `\| 5 Verify \|`, allow `done`/`skipped`) ✓ |
| 7 | L119 | S27 «пять исправлений формул» | log.md:1640 «S27 — Formula bug fixes (5 bugs)», :1654 «5 bug fixes (TDD, +18 tests, 745→762)» ✓ |
| 8 | L131 | S46: накопленная история 1239 строк (86 КБ) превысила лимит Read tool | CLAUDE.md:76 «86 KB / 1239 lines … exceeded 25k Read tool limit» ✓ |
| 9 | L131/90 | SPRINT_STATE ≤ 6 КБ | Текущий SPRINT_STATE.md = 6242 байт ≈ 6 КБ, frontmatter budget «≤6KB BINDING» ✓ |
| 10 | L133 | «36 скиллов» | sprint-flow-ru:621 «Total: 36 skills mapped» ✓ |
| 11 | L63 | «execute inline до начала Фазы 3», раздел «Autonomous mode overrides» | llm-wiki/CLAUDE.md:294 (заголовок) + :305 («EXPLICITLY says execute inline перед PHASE 3 — skip override only тот раз») ✓ |
| 12 | L89-91 | wiki-first 2-3КБ / ADR 8КБ / haiku-sonnet-opus до 50× | component-страницы реально ~1.9-2.6КБ, ADR 3-7КБ; иллюстративно корректно ✓ |
| 13 | L137-142 | 6 связанных wikilink | Все 6 целей существуют в `docs/10-как-работает-кит/`: devyat-faz-obzor, agenty-revyuery, skilly-rabochie-protsedury, khuki-mehanicheskie-barery, pamyat-i-nepreryvnost, ekonomiya-tokenov ✓ |
| 14 | L53 | L1 = claude-mem + ccd_session | llm-wiki/CLAUDE.md skills hierarchy ✓ |
| 15 | L51 | L2 = «читать СНАЧАЛА, не сырые ADR» | Cascade rule STEP 1 wiki-first ✓ |
| 16 | L125 | trader-expert выносит CONFIRM/REVISE/DEFER/EXPAND | sprint-flow-ru:105/153 + kit-overview:109 ✓ |
| 17 | L127 | «между спринтами» = завершён/не начат, хуки не блокируют | Согласуется с Phase 9 + hook logic (нет sprint branch → fail open) ✓ |
| 18 | L20/119 | drift S16-S27, S27 нарушения (прямой Agent dispatch, нет plan file, subagent-driven пропущен) | sprint-flow-ru:29-36 «Зачем мы это делаем» — verbatim ✓ |

---

## WARN

### W1. «~65% сжатие caveman» — конфликт двух цифр в самих kit-доках (L93)
Страница: «Caveman-сжатие: вывод ИИ сокращается на ~65%».
- **Источник ЕСТЬ:** `development-workflow.md:54` («Caveman active (65% сжатие)», «65% меньше output») и :77 («сжатие вывода (65% экономия)») — это один из cited source_files страницы. Страница ВЕРНА своему источнику.
- **НО конфликт:** `llm-wiki/CLAUDE.md:278` и `~/.claude/CLAUDE.md:90` говорят caveman-compress = **~47%**.
- Разбор: 47% относится к one-time сжатию CLAUDE.md/agent-промптов при загрузке; 65% — к сжатию вывода/ответов в caveman-режиме. Это ДВЕ разные операции, поэтому обе цифры формально «правильны», но соседство создаёт риск путаницы.
- Вердикт: НЕ ошибка страницы (faithful к cited source + framing «вывод» совпадает с 65%-источником). Upstream-несогласованность. Downgrade с потенциального BLOCKER до WARN. Опционально: добавить «(сжатие вывода в caveman-режиме)» для дизамбигуации.

### W2. «11 агентов в ~/.claude/agents/» — расходится с реальным содержимым папки (L41)
Страница (L41 диаграмма L5): «Доменные рецензенты (11 агентов в ~/.claude/agents/)».
- Каноническая цифра **11** подтверждена: `current-state.md:49` = 11, `kit-overview-ru.md:105` = 11. Страница корректно наследует канон.
- **НО** реальный `ls ~/.claude/agents/` = **15 файлов**: architecture-reviewer, bybit-api-reviewer, dashboard-reviewer, data-integrity-reviewer, **doc-linker**, **doc-reviewer-depth**, doc-reviewer, **doc-writer**, **frontend-developer**, python-reviewer, quant-stats-reviewer, security-auditor, test-engineer, trader-expert, trading-logic-reviewer.
- «11» = только *рецензенты*; doc-writer/doc-reviewer-depth/doc-linker (созданы в S56 — см. SPRINT_STATE) и frontend-developer не входят в канонический reviewer-набор.
- Риск: не-программист, которому сказали «11 агентов в ~/.claude/agents/», запустив `ls`, увидит 15 → недоумение. Формулировка «11 агентов в папке X» смешивает семантическую категорию (рецензенты) с физическим расположением (папка со всеми агентами). Рекомендация: «11 доменных рецензентов» без привязки «в папке = 11», ИЛИ обновить канон после S56.

### W3. «прошёл через S56» — S56 in-progress, не завершён (L18)
Страница: «На момент написания этой документации бот прошёл через S56».
- SPRINT_STATE: `sprint: 56`, `phase: 4-execution` — S56 идёт ПРЯМО СЕЙЧАС (эта дока пишется В S56), не «пройден».
- Последний зашипленный = S55 (`tag: v0.1.0-alpha.55`). Точнее было бы «дошёл до S56» / «на S56». Мелкая неточность формулировки.

---

## DEEP

### D1. «5 команд» в подводных камнях смешивает skill и slash-команды (L133)
Страница: «Единственное, что важно знать оператору: 9 фаз, 5 команд (`sprint-orient`, `/clear`, `/btw`, `claude --continue`, `/compact`)».
- `sprint-orient` — это project **skill** (`.claude/skills/sprint-orient/`), а не команда. Остальные 4 — slash/CLI команды.
- kit-overview-ru «Top 10 commands» перечисляет 10 (`Skill: sprint-orient`, --continue, --resume, /clear, /btw, /rewind, /compact, /agents, /permissions, /statusline).
- Не фактическая ошибка (для не-программиста «команда» = «что набрать/вызвать»), но терминологически sprint-orient — skill. Педагогически допустимо; отмечено для полноты.

---

## Вывод
Страница фактически точна по всем механическим/процессным утверждениям (хуки, фазы, счётчики скиллов, ADR-ссылки, S27/S46 факты, wikilink-цели). Три WARN — не искажающие суть неточности формулировок (caveman-цифра faithful к источнику но конфликтует; «11 агентов в папке» vs 15 файлов; «прошёл через S56» vs in-progress). Блокеров нет. Денежного ядра страница не касается (money_core: false) — code_issues пусты.
