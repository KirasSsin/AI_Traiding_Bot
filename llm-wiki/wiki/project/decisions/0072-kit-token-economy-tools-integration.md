---
title: "0072. Интеграция token-economy инструментов — ponytail принят, headroom отложен, mem0/memanto отклонены"
type: decision
tags: [decision, adr, kit, tooling, token-economy, ponytail, headroom, mem0, memanto]
created: 2026-07-01
updated: 2026-07-01
status: accepted
sources:
  - .claude/skills/ponytail/SKILL.md
  - .claude/skills/ponytail-audit/SKILL.md
  - https://github.com/DietrichGebert/ponytail
  - https://github.com/headroomlabs-ai/headroom
  - https://github.com/mem0ai/mem0
  - https://github.com/moorcheh-ai/memanto
---

# 0072. Интеграция token-economy инструментов (ponytail / headroom / mem0 / memanto)

**Status:** accepted
**Date:** 2026-07-01

## Контекст

Оценивались 4 внешних репозитория, закрывающих 3 «течи токенов»:

- **OUTPUT** (лишний код / повторённая логика) — ponytail
- **INPUT** (портянки логов / JSON / RAG-чанков) — headroom
- **CROSS-SESSION** (каждая новая сессия = чистый лист) — mem0, memanto

Цель: внедрить так, чтобы инструменты **не конфликтовали** с текущим китом.

**Ключевой вывод — кит уже закрывает 2 из 3 течей:**

| Течь | Уже в ките | Кандидат |
|------|-----------|----------|
| OUTPUT | `caveman` (сжатие вывода, hooks+skill) + CLAUDE.md YAGNI/KISS | ponytail |
| CROSS-SESSION | `claude-mem` (MCP: observations/smart_search/timeline) + file-memory `~/.claude/.../memory/*.md` | mem0 / memanto |
| INPUT | `context-budget-warn.sh` — **только предупреждает** (60%/80% транскрипта), не сжимает | headroom ← единственный реально пустой слот |

Метаданные репо (verified через GitHub API, 2026-07-01):

| Repo | Stars | License | Зрелость |
|------|-------|---------|----------|
| DietrichGebert/ponytail | 70 128 | MIT | v4.8.4, prod |
| headroomlabs-ai/headroom (moved от chopratejas) | 55 089 | Apache-2.0 | v0.28, Py+Rust |
| mem0ai/mem0 | 59 863 | Apache-2.0 | YC S24, prod |
| moorcheh-ai/memanto | 1 520 | MIT | v0.2.4 **Alpha**, 185 issues |

## Опции и вердикты

### ponytail → ПРИНЯТ (skill-port, НЕ plugin)

Механизм: 7-ступенчатая «лестница решений» перед генерацией кода (нужно ли → уже в коде → stdlib → native → installed dep → 1 строка → минимум) + команды `/ponytail-review` (diff) / `/ponytail-audit` (repo) по 5 тегам `delete/stdlib/native/yagni/shrink`.

Реализация:
- `.claude/skills/ponytail/SKILL.md` — лестница (verbatim из repo), триггер PHASE 4 (написание кода).
- `.claude/skills/ponytail-audit/SKILL.md` — over-engineering scan, триггер PHASE 5/6 (verify/review).

Почему skill-port, а не официальный plugin:
- Plugin вешает 3 хука: `SessionStart` + `SubagentStart` + `UserPromptSubmit`. Первый и третий **коллизят** с `caveman-activate.js` / `caveman-mode-tracker.js` (сосуществуют, но добавляют always-on инжект ~250 токенов на каждую сессию).
- Ruleset ~60% дублирует существующий раздел CLAUDE.md «Минимальность изменений» / YAGNI.
- Net-new = **позитивный упорядоченный алгоритм** лестницы + `ponytail:` маркировка упрощений + команды audit/review (ось over-engineering, ортогональная нашему correctness-focused `code-review`).
- Skills = управляемый вызов вместо автовпрыска. Кит философски предпочитает skills (см. 5 workflow-скиллов).

### headroom → ОТЛОЖЕН (routing-proxy несовместим с подпиской)

Установлено глубокой проверкой (6 тестов, изолированно через `uvx`):

1. **Нет `compress` CLI-подкоманды** (`Error: No such command 'compress'`). Задуманный «PostToolUse-хук пайпит вывод в headroom» — нереализуем.
2. MCP `headroom mcp serve` требует SDK `mcp` (`--with mcp`) и строит `create_ccr_mcp_server(proxy_url=...)` — тонкий клиент к proxy.
3. MCP-`headroom_compress` **без запущенного proxy висит** (нет ответа за 30-45с, без stderr — блокирующее подключение к :8787).
4. `headroom proxy` — **routing-proxy**: `/v1/messages → api.anthropic.com`. Сжимает **только транзит**, идущий через `ANTHROPIC_BASE_URL=http://127.0.0.1:8787`. При standalone MCP-вызове в логе proxy — ноль входящих запросов.
5. Гипотеза «локальный compression-демон без роутинга» (A') **опровергнута**: proxy жмёт лишь то, что через него роутится.
6. Требует extras `[proxy]` (fastapi) + `[code]` (было DISABLED) + `[ml]` (ModernBERT) + SDK `mcp`.

→ Единственный рабочий путь = `ANTHROPIC_BASE_URL`-роутинг всего трафика Claude Code. На текущем окружении **нет `ANTHROPIC_API_KEY`** (подписка/OAuth, токен в Keychain). headroom сам позиционирует MCP-CCR как путь «for subscription users who don't have API access» — proxy спроектирован под API-ключ.

**Risk-разбор роутинга для кит/спринт-разработки (почему отложен):**

1. **Single point of failure** — каждая сессия зависит от живого proxy на :8787; краш демона = Claude Code не работает в проекте (спринт встаёт).
2. **Auth (OAuth)** — proxy становится MITM на Bearer-токен; если Anthropic привязывает OAuth к атрибутам клиента → 401 даже с валидным токеном.
3. **ToS-серая зона** — подписочный трафик через сторонний proxy, переписывающий запросы.
4. **Лосси-сжатие бьёт по correctness-critical** — `Read → Edit` требует verbatim (exact `old_string`); сжатый Read ломает Edit или даёт чуть-неверную строку. Также pytest/diff/ADR/canonical-counts.
5. **Тяжёлая машинерия кита** — весь трафик субагентов/ревьюеров через proxy → больше лосси-искажений вида кода; sprint-хуки парсят точный bash-вывод, расходящийся с тем, что видит модель.
6. **Недетерминизм + TTL** — сжатие turn-зависимо; оригиналы живут proxy 5 мин / MCP 1 час → retrieve после TTL = контент пропал.
7. **Латентность** — +localhost-хоп +ModernBERT-инференс; первые вызовы грузят модели (медленно).

Уместен был бы при **API-ключе** (риск auth/ToS исчезает) и read-heavy, не edit-exact workflow. Для correctness-critical трейдинг-кита со strict TDD + exact-Edit — плохой фит.

### mem0 → ОТКЛОНЁН

`claude-mem` уже владеет cross-session (глубоко вшит: MCP + observations + SessionStart-инжект + smart_search + timeline). mem0 решает ту же задачу, но: LLM-extraction на КАЖДУЮ запись + vector store (Qdrant) → ощутимо дороже; официальный CC-плагин ставит 7 lifecycle-хуков → конфликт с sprint-хуками + может блокировать запись MEMORY.md. Единственный плюс — семантический поиск (у claude-mem keyword/TF-IDF), не критичен сейчас. При потребности в семантике — добавить mem0 self-hosted **MCP-only** (без авто-хуков) отдельным шагом.

### memanto → ОТКЛОНЁН

Дубль claude-mem + backend `moorcheh-sdk` **проприетарный** (vendor lock-in даже on-prem через Ollama) + **Alpha** (v0.2.4, 185 open issues) + lifecycle-хуки конфликтуют с `sprint-orient`.

## Решение

Внедрить **только ponytail** (2 skill'а). headroom отложить, mem0/memanto отклонить.

## Последствия

- **+2 skill'а** (`ponytail`, `ponytail-audit`), 0 новых хуков, 0 новых MCP, 0 изменений инфраструктуры → 0 риска для кита.
- `.venv` бота не затронут (headroom пробовался через изолированный `uvx`; `fastapi` в .venv — родная зависимость дашборда, не утечка).
- Кит не воюет сам с собой: OUTPUT (caveman+ponytail), CROSS-SESSION (claude-mem), INPUT (по-прежнему только warn — осознанный пробел).

## Runbook: включить headroom позже

Активировать, **только** если (а) появится `ANTHROPIC_API_KEY` ИЛИ (б) осознанно принят routing-риск. Перед routing — изоляционный auth-тест.

```bash
# 1. Изолированная установка (НЕ в .venv бота)
uv tool install "headroom-ai[proxy,code,ml]" --with mcp

# 2. MCP-сервер → .mcp.json (mcpServers):
#   "headroom": {"command":"headroom","args":["mcp","serve"]}

# 3. Демон (фон, держать живым — напр. SessionStart-хук):
headroom proxy --port 8787

# 4. Routing (project-level, next-launch) → .claude/settings.json "env":
#   "ANTHROPIC_BASE_URL": "http://127.0.0.1:8787"

# Rollback: убрать env ANTHROPIC_BASE_URL + kill proxy (lsof -ti:8787 | xargs kill)
```

## Related

- [[project/architecture/tooling-inventory-ru]] — каталог инструментов кита (добавить ponytail/ponytail-audit)
- Существующие: `caveman` (OUTPUT-сжатие), `claude-mem` (CROSS-SESSION), `context-budget-warn.sh` (INPUT-warn)
