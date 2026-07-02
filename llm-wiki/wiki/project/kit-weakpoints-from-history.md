---
type: audit
title: Слабые места kit-процесса по данным экспорта сессий (апрель–июль 2026)
updated: 2026-07-02
sources: session-export-1782940628374/logs/ (main*.log, mcp*.log, claude.ai-web.log), b8009145-…b504d.jsonl (121MB, основная рабочая сессия 2026-04-19…2026-07-02, 618 turns), metadata.json
method: grep/JSON-stream, полные файлы не читались
---

# Слабые места kit-процесса — добыто из журналов сессий

Разбор экспорта журналов операторской машины: 44 454 события jsonl-транскрипта + 21MB логов harness. Все числа посчитаны скриптами, не оценки.

## TL;DR — топ-5 слабых мест

1. **Limit-остановки без авто-возобновления — главный убийца времени.** 27 событий `rate_limit` в основном транскрипте (24 «out of extra usage», 2 «session limit», 1 «weekly limit») + ~35 падений субагентов в батчах. Суммарный простой после 23 измеримых остановок ≈ **102 часа** (включая ночи — но именно потому, что никто не возобновлял работу в момент reset). Reset-время есть ТОЛЬКО в человекочитаемой строке — парсить можно (§«Данные для S58»).
2. **Батчи субагентов гибнут посреди прогона.** 2026-06-26: 21 писатель отработал, ~25 depth/domain-агентов упали на session limit. 2026-06-27: следующий батч добит weekly limit. 2026-07-01: link-агенты упали. Апрель: ревьюеры (trading-logic + python) падали парами. Частичный батч = ручной разбор «кто успел» — прямой вход для S58 auto-resume + чекпойнт батча.
3. **61 автокомпакция, каждая ≈ −92 % контекста и ~2,1 мин ожидания** (в сумме ~130 мин чистого ожидания). 53 из 61 — в апреле (23 шт. за один день 2026-04-23 — kitchen-sink-сессия до правил S31). 7 «Prompt is too long» (= `contextExceededCount: 7` из metadata.json) — все в апреле. После S31/S46 дисциплины — почти исчезло: класс проблемы закрыт, но телеметрии компакций в ките нет.
4. **Хук adr-agent-sync-check = 77 % всех блокировок (58 из 75)** — и почти все «лечатся» ритуальным `touch reviewer.md`. Барьер выродился в налог на push. Реальные ловли: wiki-broken-link ×10 (настоящие битые ссылки), phase-advance ×4, sprint-flow-check ×1.
5. **Read-фейлы больших файлов повторяются циклами.** 12 отказов «>25k tokens», из них 6 подряд по одному файлу (27 554 tok) за вечер 2026-04-22 — retry-петля; 3 отказа 2026-05-10/11 по 40–41k tok = инцидент SPRINT_STATE 86KB (S46). Плюс 49 «File does not exist» за период. Правила «don't-retry» и «≤6KB SPRINT_STATE» родились именно отсюда — теперь принуждать (S61 state v2).

## Сводная таблица: симптом → частота → пример → влияние → куда уходит фикс

| Симптом | Частота | Пример (timestamp) | Влияние | Фикс уходит в |
|---|---|---|---|---|
| Usage-limit стоп основного треда (`error:"rate_limit"`, 429) | 27 событий (пик: 21 шт. 19–27 апр; далее 21.05, 26–27.06, 01.07) | `2026-06-26T21:04Z` «You've hit your session limit · resets 2:30am (Europe/Moscow)» | Простой до возврата оператора: ср. ≈ 4,5 ч, max 17,5 ч (`2026-04-21T21:43Z`, reset через 2 суток); сумма ≈ 102 ч | **S58 auto-resume** |
| Падение субагентов в батче на лимите (tool_result / queue-operation failures) | ≥ 4 крупных батча | `2026-06-26T21:04Z`: 21 writer done, ~25 depth/domain failed; `2026-06-27T13:10Z` weekly limit добил следующий | Частичные батчи, ручной аудит «кто дописал», повторные диспатчи | **S58** (чекпойнт батча + re-dispatch список) |
| Server-side лимиты (не usage): 529 Overloaded ×5, «temporarily limiting requests» ×2, socket closed ×3 | 10 событий | `2026-06-20T10:57Z`: verify-агенты ARCH-01/ARCH-04 убиты «Server is temporarily limiting» | Ложные FAIL в verify-батче; reset-времени нет — нужен retry с backoff, не ожидание reset | **S58** (ветка retry-now vs wait-until) |
| Автокомпакция (compact_boundary) | 61 (57 auto / 4 manual); по датам: апрель 55, май 5, июнь 1 | `2026-04-23`: 23 компакции за день; avg preTokens 307k → postTokens 25k (−92 %), avg 128 сек | Потеря деталей середины спринта → повторные чтения; ~130 мин ожидания суммарно | **Закрыто** дисциплиной S31 (/clear, ≤250 строк CLAUDE.md) + S46 (≤6KB SPRINT_STATE); телеметрия компакций → **S62** |
| Context overflow «Prompt is too long» | 7 (= contextExceededCount) | `2026-04-22T16:30Z`, ×3 22–23.04, ×4 26.04 | Провал turn, потеря контекста субагента | **Закрыто** (S31/S46); регресс-метрика → **S62** |
| Read >25k tokens отказ | 12 | 6× один файл (27 554 tok) вечер `2026-04-22`; 40 085 tok ×2 `2026-05-11T03:11Z` (SPRINT_STATE 86KB) | Retry-петли = 3× токенов; блокировка orient при старте сессии | **Закрыто** частично (banned-list, ≤6KB budget); механический guard full-read → S61/P1-CASCADE |
| «File does not exist» (Read по несуществующему пути) | 49 | распределены по всему периоду | Токен-мусор, hallucination-пути (AI_Traiding_Tool и пр.) | **S61 state v2** (path-verify перед Read уже BINDING — нужен счётчик в **S62**) |
| Блокировки хуков (PreToolUse exit 2) | 75: adr-agent-sync **58**, wiki-broken-link 10, phase-advance 4, sprint-flow-check 1 | первая: `2026-04-22T17:13Z`; пик 19 шт. `2026-04-26` | adr-agent-sync — 77 % блоков, лечится `touch` = ритуал, не проверка; sprint-flow-check реально ловил 1 раз | Пересмотр adr-agent-sync (шум) → **S62 telemetry**; P0-BRANCH уже в **S58-плане** |
| Синтаксически сломанный хук в бою | 1 | `2026-04-25T09:10Z` wiki-broken-link-check.sh line 199 `syntax error near ')'` | Хук упал с exit 2 → случайно fail-CLOSED (заблокировал push вместо тихой дыры); повезло | **Закрыто** S57 hooks-selfcheck fail-CLOSED |
| Потеря ориентации (повторные sprint-orient) | явных повторов мало: 3 вызова `2026-04-25`, 2 `2026-05-10` | — | После компакций апреля orient дёргался чаще; после S31 — стабильно | **Закрыто**; счётчик orient/день → **S62** |
| MCP wiki-sa разрыв | 1 | `2026-06-25T13:38Z` «Server transport closed unexpectedly» | Единичный, перезапустился штатно | не требуется |
| Harness-шум в main*.log | 3461 «Failed to log event», 1035 sqlite3 spawn fail, 417 git exit 128, ~330 EventLogging 403 (Cloudflare) | весь период | Kit не затрагивает; раздувает логи, мешает grep-диагностике | не kit; игнор-лист для будущих аудитов |

## Данные для S58 auto-resume (формат limit-остановок)

### Где остановка видна (4 канала)

| Канал | Формат | Машиночитаемость |
|---|---|---|
| jsonl: assistant-запись | `"type":"assistant"` + `"error":"rate_limit"` + `"isApiErrorMessage":true` + `"apiErrorStatus":429`; текст в `message.content[0].text` | Поля error/status — да; **reset-время — только в тексте** |
| jsonl: tool_result диспатча Agent | `"is_error":true`, текст лимита в content + `agentId: …(use SendMessage …)` | agentId сохранён → возобновление именно этого агента возможно |
| jsonl: queue-operation | `<failures>[verify:ARCH-04#1] failed: <текст лимита>…</failures>` | Список погибших участников батча — парсится |
| main.log (CCD) | `[warn] [CCD CycleHealth] <id> api_error (success): <текст>` | Только текст; дублирует jsonl |

**Эпохи/`retryAfter`/`resets_at` в записи НЕТ.** Проверено на полной структуре записи: top-level keys = `apiErrorStatus, cwd, entrypoint, error, gitBranch, isApiErrorMessage, message, parentUuid, requestId, sessionId, slug, timestamp, type, userType, uuid, version` — ни одного поля с reset-временем. Парсер S58 обязан разбирать человеческую строку.

### Каталог наблюдавшихся строк (все реальные варианты)

| Тип | Строка (шаблон) | Reset присутствует | Наблюдений |
|---|---|---|---|
| session | `You've hit your session limit · resets 11:30pm (Europe/Moscow)` | время 12h + IANA-таймзона | 2 (тред) + ~8 (батчи/CCD) |
| weekly | `You've hit your weekly limit · resets 5pm (Europe/Moscow)` | время 12h | 1 + батчи |
| extra usage, время | `You're out of extra usage · resets 2am (Asia/Tbilisi)`; вариант с минутами `12:10pm` | время 12h | 24 |
| extra usage, дата+время | `You're out of extra usage · resets May 23 at 5pm (Europe/Moscow)`; `resets Apr 24 at 5am (Asia/Tbilisi)` | **дата + время** (reset > 24 ч) | 5 |
| server-side | `API Error: Server is temporarily limiting requests (not your usage limit) · Rate limited` | **нет** | 2 |
| overloaded | `API Error: 529 Overloaded. …` | **нет** | 5 |

### Требования к парсеру/резюмеру (выводы из данных)

1. **Regex ядро:** `resets (?:(\w{3}) (\d{1,2}) at )?(\d{1,2})(?::(\d{2}))?(am|pm) \(([^)]+)\)` — покрывает все 29 наблюдавшихся строк с reset.
2. **Таймзона нестабильна:** в апреле `Asia/Tbilisi`, с мая `Europe/Moscow` (оператор переехал). Брать зону из строки, НЕ хардкодить.
3. **Разрешение неоднозначности «время без даты»:** если полученное время < текущего локального — это завтра (случай `2026-06-26 00:03 → resets 2:30am` = тот же день; `resets 12am` = следующая полночь). Дата в строке появляется только когда reset дальше суток.
4. **Три класса реакции:** (а) session/weekly/extra с reset-временем → сон до reset + 2–5 мин буфер → авто-`SendMessage`/`claude --continue`; (б) server-429/529 без reset → экспоненциальный retry (наблюдалось восстановление за 1–24 мин); (в) частичный батч → перед сном записать в SPRINT_STATE список упавших агентов из `<failures>` (имена в скобках парсятся: `[depth:wfa-va…] failed:`).
5. **Что терялось без этого:** ср. простой 4,5 ч/событие; худший случай — reset `2:30am`, возврат оператора `15:26` (+12,9 ч мёртвого времени после reset, 2026-06-27); 17,5 ч на «resets Apr 24 at 5am».
6. **Сигнал «лимит близко» отсутствует** — ни одного warning-события до 429 в логах нет; авто-резюмеру нужен только post-factum хэндлер.

## Детали по компакциям (профиль для S62-телеметрии)

- 61 boundary: по датам `04-20:4, 04-21:2, 04-22:4, 04-23:23, 04-24:16, 04-25:3, 04-26:2, 04-27:1, 05-08:1, 05-09:2, 05-10:1, 05-11:1, 06-20:1`.
- preTokens avg 307 854 (min 167 014, **max 1 001 024**), postTokens avg 25 218, длительность avg 128 сек.
- Вывод: компакция срабатывала на ~167k (порог окна), т.е. `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=50` в бою почти не проявился в этой сессии; аномалии 402k и 1M — большие окна ([1m]-модель). Для P1-TUNING A/B: метрика уже есть в jsonl (`compactMetadata.preTokens/postTokens/durationMs`) — S62 может собирать её grep-скриптом без новой инструментовки.

## Прочее (не вошло в топ)

- «Model not available» ×1 (`claude-fable-5` недоступна — mid-June): деградация модельного диспетча, разовая.
- `gh pr view timed out` ×29 — сетевые таймауты GitHub из harness; к kit-гейтам не относится, но объясняет часть «зависших» ship-шагов.
- claude.ai-web.log: 3208 CORS-ошибок event_logging + 1548 «app-unavailable-in-region» (VPN/регион) — фон, на процесс не влиял, кроме Cloudflare-челленджей телеметрии.
- ssh.log / coworkd.log: kit-релевантных событий не найдено.

## Связанные документы

- [[SPRINT_STATE]] — текущий прогон S57–S62
- `docs/10-как-работает-кит/probely-i-uluchsheniya.md` — статический аудит кита (этот файл — динамическое дополнение по журналам)
- ADR 0072, план S58 (auto-resume) — потребитель раздела «Данные для S58»
