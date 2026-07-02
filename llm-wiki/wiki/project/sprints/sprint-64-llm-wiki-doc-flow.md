---
title: Sprint 64 — LLM-Wiki Audit & Doc-Flow: правило «документация сначала»
type: summary
sprint: 64
created: 2026-07-02
updated: 2026-07-02
tag: v0.1.0-alpha.64
status: stable
---

# S64 — LLM-Wiki Audit & Doc-Flow (mega-run, вставка перед плагинами)

**TL;DR:** внедрено BINDING-правило потока документации (техстраница llm-wiki RU → код → пользовательские docs/ RU); аудит llm-wiki fable-5-командой закрыл HIGH-дрейф канонов; docs/-гейт понижен до WARN (решение оператора); session-restore усилен tech-doc priming. src/ не тронут.

## Метод
Аудит + дизайн правила — через **Workflow, kit-агенты fable-5** (kit-auditor + architecture-reviewer + doc-reviewer-depth). Директива оператора «команда через workflow, максимум fable-5».

## Сделано

| T | Что | Proof |
|---|---|---|
| T1 | kit-auditor аудит llm-wiki (362 стр): HIGH-дрейф current-state.md (agents 11→18, hooks 7→14, ADR 71→75, sprints 59→65, components 51→60) → синхронизирован + указатель на AUTO-блок; 1 битая ссылка (overview→minimum-backtest-length) снята; 252/362 не-RU = принятое наследие (incremental) | audit-отчёт; counts синк |
| T2 | Правило **doc-first** в repo `CLAUDE.md` (полный текст) + ссылки без дублирования: `sprint-flow-ru.md` (Phase 3/7), `sprint-orient` (шаг 4b priming), `skill-manifest.sh` (строка 3b advisory) | 4 места, текст в одном |
| T3 | docs-staleness-check.sh → **WARN** (exit 2→0, docs/=WARN per оператор); docs-broken-link остаётся БЛОК (гигиена) | red-check: WARN печатается |
| T4 | sprint-orient шаг 4b: восстановление от техдоков llm-wiki (components/README + ≤2 страницы, токен-бюджет) | skill обновлён |
| T5 | Вердикт по idea-документу «LLM Wiki»: ADOPT lint(=kit-auditor)/index/log (уже есть, 0 нового); REJECT qmd(=wiki-sa MCP)/Dataview/Marp (YAGNI) | зафиксировано |
| T6 | Пользовательская docs/ страница [[../../../docs/10-как-работает-кит/evolyutsiya-kita-s57-s64|эволюция кита S57-64]] (dogfood нового правила; source_files→kit/, не ~/.claude) | docs/ страница создана |

## Корневая причина (doc-reviewer-depth)
`docs/manifest.json` + frontmatter `source_files:` пользовательских страниц указывали на `~/.claude/...` (вне git), а не на версионированный `kit/` (S57) — поэтому docs-staleness не срабатывал на правки кита. Новая docs/-страница S64 задаёт правильный паттерн (`source_files: kit/...`). **Массовый repoint существующих docs/-страниц + бэкфилл S57-S63 контента → follow-up** (большая переводческо-писательская работа, отдельный docs-спринт).

## Аудит-остаток (принято/follow-up)
- Orphans (закрыты ссылкой отсюда): [[../state-v2-design]] (дизайн-док S61), [[../reviews/review-s60]] (гейт-артефакт).
- index.md недокаталогизирован (~110 стр) — частичный синк; полный → docs-спринт.
- `state/.backup/**` спотыкает сканеры → exclude-паттерн в wiki-сканеры (follow-up).
- 252/362 не-RU страниц — incremental-перевод по мере touch (policy).

## Ревью (Phase 6) — артефакт [[../reviews/review-s64]]

- **architecture-reviewer (fable-5): APPROVE_WITH_CONDITIONS** — 2 HIGH закрыты: #1 висячий указатель на HARD-GATE (добавлены Doc-first чеклисты Фаз 3/7 + честная формулировка advisory); #2 само-нарушение (docs-sync-gate.md + docs-update SKILL синхронизированы на WARN). Verified: money/security не ослаблены, 3b не в exit 1, счётчики точны, дупликации нет. MEDIUM #3 (WARN-видимость) + #5 (current-state→AUTO-блок) → S65 backlog.
- kit-auditor + doc-reviewer-depth (fable-5): аудит llm-wiki + ROOT CAUSE docs/ (source_files→~/.claude вместо kit/). Blockers: 0.

## Related
[[../plans/2026-07-02-sprint-64-llm-wiki-doc-flow]] · [[../../../docs/10-как-работает-кит/evolyutsiya-kita-s57-s64|user-docs эволюция]] · [[kit-overview-ru]] · [[../KIT-MASTER-PLAN]]
