---
title: "Sprint 68 — Boot-слой: стоимость и правда (план)"
type: plan
sprint: 68
created: 2026-07-02
updated: 2026-07-02
status: active
sources: [llm-wiki/wiki/project/kit-deep-research-2026-07-02.md, llm-wiki/wiki/project/research-evidence/kit-deep-research/confirmed.json]
---

# S68 — Boot-слой: токен-кровотечение, мёртвые ритуалы, канон-дрейф

## Цель

Убрать постоянный налог на КАЖДУЮ сессию (мёртвый boot-контекст, дубли хуков, мёртвый observer) + починить ритуалы, гарантированно блокирующие пуш + остановить мёртвый launchd-краш-луп. Экономия ~20k токенов/сессию. Всё tiny/small, зависимостей между задачами нет. src/ денежного ядра заморожен (kit-maintenance).

## Фаза 2 (Brainstorm) — артефакт

PHASE 2 выполнена deep-research панелями: **47/47 вердиктов** (23 CONFIRM + 24 REVISE, 0 отклонённых) на диске `research-evidence/kit-deep-research/panels-new.json` + `confirmed.json`. Адверсариальная верификация каждой находки (file:line пруфы). Открытых scope-вопросов для S68 = 0. trader-expert не требуется (kit-maintenance, не trading-домен).

## Pre-done этой сессией (НЕ пере-платить — вычтено из scope)

| Находка | Статус | Пруф |
|---|---|---|
| D7-02 Desktop 43.8KB boot-tax | ✅ файл удалён, архив в git | `ls Desktop/CLAUDE.md` → нет |
| MEM-07 CLAUDE.md компрессия (репо→скилл) | ✅ 105→52KB always-on; скилл `kit-conventions` | git |
| D7-03 stale-prose в телах агентов | ✅ grep body model/effort = CLEAN | git |
| D2-08 effort-конвенция | ✅ **снято ADR 0077** (effort в frontmatter) | PINNED_VERSIONS |
| SKW-01 «Sprint 38»→указатель | ✅ current-state → SPRINT_STATE-single-source | git |

## Задачи (осталось после pre-done)

| # | Задача | Находки | Файлы | Size | Делегат |
|---|---|---|---|---|---|
| T1 | 🔴 **launchd-краш-луп** — plist `com.kit.auto-resume.plist` жив, TCC-краш на след. маркере. try/except + лог «нужен Full Disk Access» ИЛИ uninstall (S67 desktop-путь его заменил — решить: kill C2 vs починить) | LOG9-01 | `kit/auto-resume/lib/auto_resume_poll.py`, plist | small | security-auditor |
| T2 | caveman-дубли из live+example settings.json (8 упоминаний — дубли) + `enabledPlugins warp=false`; diff-assert выживших selfcheck/state-integrity | D8-01, D8-04 | `~/.claude/settings.json`, `kit/settings.example.json` | small | controller |
| T3 | claude-mem: OBSERVATIONS 50→5, SESSION_COUNT 10→3; диагностика мёртвого observer (с 2026-04-24); healthcheck-WARN; ADR-поправка 0043 (каскад STEP 2 on-demand) | D5-03, MEM-01 | settings, hooks-selfcheck, ADR 0043 | small | controller |
| T4 | touch-ритуал → content-check на 6 поверхностях (sprint-finish 6b, wiki-update, repo CLAUDE.md, tooling-inventory, adr-agent-sync-hook.md, память github-push-auth) | D1-02, SKW-02, MEM-06 | 6 файлов | tiny×6 | controller (batch Read→Edit) |
| T5 | kit-inventory AUTO-блоки на repo/llm-wiki CLAUDE.md + index.md (счётчик ADR, AUTO:agent-models); phase table += ponytail/ponytail-audit/docs-update; де-номеровать литеральные boot-счётчики | SKW-01 хвост, D7-04 | `kit/kit-inventory.sh`, CLAUDE.md ×2 | small | controller |
| T6 | global `~/.claude/CLAUDE.md` §9b/9c → универсальное ядро ~15 строк (канон деталей = скилл `kit-conventions`); scoped-исключение model-dispatch (НЕ замена — другие проекты) | MEM-07 хвост, D7-03 хвост, D2-09 | `~/.claude/CLAUDE.md`, `kit-team-agents.md` | small | controller |
| T7 | ancestor-scan WARN в hooks-selfcheck (защита от рецидива walk-up мусора типа Desktop-файла) | D7-02 хвост | `kit/hooks/hooks-selfcheck.sh` | tiny | controller |
| T8 | LOG9-03 галлюцинированное дерево `AI_Traiding_Tool` (существует — проверено): merge полезного→delete + WARN wrong-project writes | LOG9-03 | filesystem, hooks-selfcheck | small | controller |
| T9 | Tiny-батч LOW: класс-10 таксономии (параллельный-батч-1-фейл, ~92 события) + «мутирующие Bash соло»; D5-05 no-read-back; SKW-06/07 двойники; D1-07/D2-11 WARN-семантика; поправка мифа «151× parse-fail»→~2 | D1-07,D2-11,MEM-08,SKW-06/07,D5-05 | error-taxonomy.md, sprint-orient, docs-* | tiny×N | controller |

## Acceptance

- Desktop boot-tax не вернётся: ancestor-scan WARN срабатывает на подкинутый walk-up `CLAUDE.md` (T7 тест).
- `settings.json`: caveman-хуки НЕ задвоены (grep count = 1 набор); warp=false; selfcheck/state-integrity/context-budget выжили (diff-assert).
- launchd: plist либо чинён (try/except, `bash -n`/py-compile OK), либо выгружен (`launchctl list | grep auto-resume` пусто) — маркер больше не краш-лупит.
- touch-ритуал: 0 упоминаний `touch ~/.claude/agents` как ОБЯЗАТЕЛЬНОГО pre-push на 6 поверхностях (заменён content-check).
- kit-inventory: AUTO-блоки регенерят счётчики ADR/skills/agent-models в CLAUDE.md ×2 + index.md; ручных стейл-чисел boot-строк = 0.
- `AI_Traiding_Tool`: полезная память смёржена в канон, дерево удалено, WARN на wrong-project write.
- pytest/hooks-selfcheck/`bash -n` всех тронутых хуков GREEN.

## Doc-first (Фаза 3 техстраница)

S68 = kit-meta (не src/-компонент). Техстраница = обновления `tooling-inventory-ru` (phase table +3 скилла, счётчики AUTO) + `kit-overview-ru` (boot-строки) в Фазе 7 Sync; plan-файл + `kit-deep-research-2026-07-02.md` = каноничные Фаза-2/3 артефакты. Отдельная новая техстраница не нужна (YAGNI).

## Риски / guards
- **T1 решение kill-vs-fix:** C2 launchd-поллер vs S67 desktop-путь — не дублировать контур. Рекомендация: выгрузить C2 plist (desktop-путь S67 уже боевой), оставить gate-only helper. Финал — security-auditor вердикт.
- **T2 settings мутация:** live `~/.claude/settings.json` вне git — backup вне репо ДО правки, снимок в sprint-страницу для отката.
- **T6 global CLAUDE.md:** blast-radius = другие проекты. Только scoped-исключения + сжатие универсального ядра, НЕ удаление generic-полезного (edit-after-read универсален).
- **НЕ в S68:** ADR 0066(React) vs 0039(vanilla) конфликт — pre-check для S70 D2-05 (dashboard-reviewer/frontend-developer), не блокирует S68.

## Фазы
Plan(3) → Execute(4, per-task; T1 security-auditor, остальное controller batch) → Verify(5, hooks-selfcheck + bash -n + pytest) → Review(6, security-auditor на T1/T2 settings-мутацию + kit-auditor на drift) → Sync(7, tooling-inventory + kit-overview + current-state counts) → Ship(8, tag alpha.68) → Close(9).

## Related
[[../kit-deep-research-2026-07-02]] · [[../decisions/0077-model-pin-tiered-v3]] · [[../decisions/0043-llmwiki-claude-mem-cascade]] · `research-evidence/kit-deep-research/`
