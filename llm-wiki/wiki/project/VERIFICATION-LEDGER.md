---
title: Verification Ledger — Фаза 0 kit mega-run (S57–S63)
type: ledger
updated: 2026-07-02
verified_by: Fable-5 orchestrator, live system (диск+git+settings.json)
---

# VERIFICATION-LEDGER — заявление → команда → вывод → вердикт

Правило: в спринты идут только CONFIRMED. STALE = уже исправлено. WRONG = не подтвердилось.

| # | Заявление [источники] | Команда | Вывод (свежий, 2026-07-02) | Вердикт |
|---|---|---|---|---|
| 1 | GITHUB_TOKEN открытым текстом в settings.json [CLAUDE P0-SECRET][GLM K-12][QWEN P-06][GEMINI DE-001] | `grep -c "ghp_\|gho_" ~/.claude/settings.json` | `1` (префикс `ghp_LkY…`) | **CONFIRMED** |
| 2 | Гейты обходятся именем ветки [CLAUDE P0-BRANCH][GLM K-01][MINIMAX 2.1.6] | `grep -n "feature/sprint" ~/.claude/hooks/{sprint-flow-check,phase-advance}.sh` | `sprint-flow-check.sh:69`, `phase-advance.sh:68` — оба `^feature/sprint-([0-9]+[a-z]?)-.+$` | **CONFIRMED** |
| 3 | Нет механического гейта Фазы 6 [CLAUDE P0-REVIEW][GLM K-06] | `ls ~/.claude/hooks/` | нет review-gate.* | **CONFIRMED** |
| 4 | docs/ не синхронизируется с src/ [все 8] | `find docs -name '*.md' \| wc -l` на main | **6** (только superpowers-спеки). Корпус S56 (155 файлов) не смержен — на `chore/kit-integrate-headroom-ponytail` (`30e60ed` «WIP — not for main, kit rework pending») | **CONFIRMED+** (хуже: docs на main пуст) |
| 5 | Кит вне git [CLAUDE P0-KITVCS] | `git ls-files kit/ \| wc -l` | `0`; хуки/агенты в `~/.claude/` | **CONFIRMED** |
| 6 | Count-drift: 11 агентов в доках vs 15 [CLAUDE][GLM K-07][QWEN P-01][MINIMAX] | `ls -1 ~/.claude/agents/*.md \| wc -l`; `grep -n "11 reviewer" kit-overview-ru.md` | диск=15; kit-overview-ru.md:216 «11 reviewer agents» | **CONFIRMED** |
| 7 | Скиллов 8 vs 5 в доках | `ls -1d .claude/skills/*/ \| wc -l` | `8` | **CONFIRMED** |
| 8 | superpowers 13 vs 14 | `ls -1d ~/.claude/plugins/cache/*/superpowers/*/skills/*/ \| wc -l` | `14` | **CONFIRMED** |
| 9 | «7 push-хуков vs 6» [QWEN P-02][GLM] | `jq '.hooks…' settings.json` | PreToolUse(Bash)=6 team, UPS=2, SS=1; на диске 8 .sh — все 8 подключены (6+context-budget-warn+caveman-statusline≠hook) | **CONFIRMED** (док-цифра «7» неверна) |
| 10 | SPRINT_STATE 6242 > лимита 6144 [GLM K-02] | `wc -c SPRINT_STATE.md` | `5380` ≤ 6144 | **STALE** (сейчас в лимите; риск монолита остаётся → S60) |
| 11 | Хуки синтаксически битые / fail-OPEN дыра [CLAUDE P1-BASHN] | `for h in ~/.claude/hooks/*.sh; do bash -n; done` | все 8 `OK`; selfcheck-хука нет | **PARTIAL** (сегодня OK, механизма нет → S57) |
| 12 | adr-agent-sync обходится `touch` [GLM K-03] | `grep -n "mtime" adr-agent-sync-check.sh` | строки 96–140: сравнение mtime | **CONFIRMED** |
| 13 | AUTOCOMPACT=50, MAX_THINKING=10000 без ADR [CLAUDE P1-TUNING][QWEN] | `jq '.env' settings.json` | оба присутствуют; ADR не найден | **CONFIRMED** |
| 14 | Канонические счётчики устарели | `.venv/bin/python -c "…"` | `states=16 events=30 transitions=76 reason_codes=67` — совпадает с log.md S55 | **WRONG** (счётчики актуальны) |
| 15 | ~22 битых wiki-ссылок в docs/ [CLAUDE §4.1] | comm links/pages на chore-ветке | [CLAUDE] смотрел Desktop-снапшот `AI_Traiding_Bot_docs/` (obzor-kita.md найден там); канон-корпус на chore-ветке; грубый comm даёт шум (пути vs basename) | **UNVERIFIABLE точно** → нормальный скан скриптом в S59 |
| 16 | claude-mem перегруз 50 наблюдений [GLM K-10] | стартовый блок сессии | «17 obs (6,341t read), 94% savings» | **WRONG/STALE** (сейчас 17, не 50) |
| 17 | agent-memory отсутствует у части агентов | `for d in .claude/agent-memory/*/…` | 13/15 HAS; NONE: doc-reviewer, trader-expert | **CONFIRMED** (low) |
| 18 | «Был спринт 75, сейчас 56» [оператор] | `git tag \| sort -V \| tail`; grep 7x в 121MB транскрипте и логах export | max `v0.1.0-alpha.55`; sprints/ max 55; `sprint 7[0-9]` — 0 совпадений везде | **WRONG** (реальность: S55 shipped, S56 docs не закрыт, следующий = S57) |
| 19 | context-budget-warn только предупреждает | `grep -n exit context-budget-warn.sh` | `exit 0 = always allow (advisory)`; WARN=800KB URGENT=1200KB | **CONFIRMED** |
| 20 | PostToolUse хуки нестабильны (CLI vs Desktop) [QWEN P-07] | — | у нас PostToolUse не используется; ссылки на чужие issues | **WRONG/N-A** |
| 21 | Токсичность параллельных агентов [QWEN P-08] | — | изоляция контекстов — осознанный дизайн кита | **WRONG/OPINION** |
| 22 | GEMINI DE-005/006/007 (CI/CD права, OTTL, автоскейл) | — | в ките нет CI/CD-агентов и хост-телеметрии | **WRONG/N-A** |
| 23 | S56 не закрыт (Phase 9 нет) | `git log main..chore… --oneline`; SPRINT_STATE | chore на +9 коммитов; SPRINT_STATE: `sprint: 55, between-sprints`; docs B1–B6 128/128 готовы | **CONFIRMED** (новая находка) |
| 24 | contextExceededCount источник потери контекста | `cat metadata.json` (session export) | `"contextExceededCount": 7`, 618 turns | **CONFIRMED** (подтверждает KIT-STATE v2) |

## Chore-ветка (канон S56 docs)
- `git rev-list --count main..chore/kit-integrate-headroom-ponytail` → 9; трогает: docs(163), llm-wiki(2).
- chore ⊃ feature/sprint-56-project-docs (branch --contains подтвердил; +3 коммита).
- Desktop `AI_Traiding_Bot_docs/` — внешний снапшот (623 md), НЕ канон; аудит [CLAUDE] проведён по нему.
