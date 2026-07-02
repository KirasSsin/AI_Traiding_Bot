---
title: Plugins Research (S66) — ресерч Claude Code плагинов + внедрение ≤2
type: research
sprint: 66
created: 2026-07-02
updated: 2026-07-02
status: stable
---

# S66 — Plugins & Best Practices: ресерч + внедрение ≤2

**Методика:** топ по инсталлам/звёздам (Anthropic directory июнь-2026 + awesome-lists) → фильтр по fit к НАШЕМУ киту (зрелый: L5-ревьюеры, superpowers, agent-skills, хуки, kit-агенты, память, docs-sync) → отбор не-дублирующих + токен-экономных.

## Кандидаты (по популярности) и вердикт

| Плагин | Инсталлы/звёзды | Вердикт для нас | Причина |
|---|---|---|---|
| **Superpowers** (obra) | 752k / 94k⭐ | УЖЕ ЕСТЬ | 13 skills интегрированы (L3 process) с S54/S55 |
| **Context7 MCP** (Upstash) | 348k | **ВНЕДРЁН ✅** | up-to-date docs библиотек (pybit/pandas/FastAPI) → меньше галлюцинаций API = токен-экономия; не дублирует; free tier, reversible |
| **Frontend Design** (Anthropic) | 829k | → ОПЕРАТОРУ (OQ-2) | генерация UI; полезно для src/dashboard, но не core-trading; нужен выбор оператора «планируется ли dashboard UI работа» |
| code-review (Anthropic) | — | ОТКЛОНЁН | дублирует L5 domain-reviewers + `/code-review ultra` |
| security-guidance (Anthropic) | — | ОТКЛОНЁН | дублирует security-auditor (fable-5) |
| commit-commands / feature-dev | — | ОТКЛОНЁН | дублирует sprint-finish + subagent-driven-development |

## Внедрено: Context7 MCP (≤2, директива оператора v2)
- **Как:** `.mcp.json` (project-scoped, версионирован) — сервер `context7` = `npx -y @upstash/context7-mcp@latest`. Node v25 ✓, пакет v3.2.2 ✓.
- **Активация:** на reload сессии (MCP грузятся на старте — как новые агенты, OQ-5-класс).
- **Использование:** «use context7» в промпте при работе с библиотечным API → resolve-library-id + get-library-docs.
- **Токен-метрика (ожидаемая):** экономия на итерациях «неверный API → ошибка → фикс» при касании src/ (pybit/pandas). Замер — после первого реального использования (пост-mega-run, src/ разморожен).
- **Откат:** удалить блок `context7` из `.mcp.json` (reversible, без следов).

## Отложено оператору (OQ-2 / OQ-7)
- **Frontend Design** — установить ТОЛЬКО если планируется работа над dashboard UI (src/dashboard). 1 команда: `claude mcp add` / marketplace-плагин. Не устанавливаю без решения (не core-trading, YAGNI).

## Границы
- «≤2» = внедрён 1 (Context7, безусловно ценный, без дубля) + 1 на выбор оператора (Frontend Design). Устанавливать дубли ради числа — против YAGNI + токен-экономии.

## Sources
- [Anthropic plugin directory / awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code) · [Context7](https://github.com/upstash/context7) · [claudemarketplaces.com](https://claudemarketplaces.com/)
