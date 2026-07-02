---
title: Sprint 65 — Error-Harvest & Kit Hardening (план)
type: plan
sprint: 65
created: 2026-07-02
status: active
---

# S65 — Error-Harvest & Kit Hardening (mega-run)

**Цель:** искоренить token-waste ошибки, которые повторялись по ходу прогона (чтение файлов, bash-скрипты, hook false-fire, workflow-парс, unicode-Edit), внедрив превентивные паттерны в самые подходящие места кита. src/ не трогаем.

**Метод (директива оператора):** глубокий дизайн фиксов — через **Workflow, kit-агенты fable-5** (architecture-reviewer + kit-auditor; «Fable хорошо ловит баги»). Источник таксономии — прямой опыт прогона S57-S64 (ground truth) + узкий grep логов (`151× Unexpected token`).

## Задачи

| T | Что | Acceptance |
|---|---|---|
| T1 | Tech-страница [[../components/error-taxonomy]] — таксономия token-waste ошибок (класс → сигнатура → цена → фикс) | страница создана (doc-first) |
| T2 | Workflow fable-5: дизайн превентивного паттерна на КАЖДЫЙ класс + точное место в ките (CLAUDE.md anti-waste / workflow-гайд / hook / skill) | вердикт по каждому |
| T3 | Внедрить фиксы: anti-waste таблица CLAUDE.md (+ новые классы), workflow-authoring гайд (named schemas, no TS), unicode-safe Edit нота, bash-дисциплина (venv/glob/checkout) | правки в местах |
| T4 | Carry из S64: current-state→AUTO-блок (kit-inventory.sh), WARN-видимость red-тест 3 хуков (docs-staleness/pertask/cascade) | сделано/задокументировано |
| T5 | Verify + Review (arch, fable-5) + Sync + Ship alpha.65 + Close | manifest 7/7 |

## Таксономия (ground truth прогона)
1. **workflow TS-parse** (151×): TS-аннотации/несовпадение скобок в inline-схеме → «Unexpected token». Фикс: named schema consts, plain JS, гайд.
2. **Edit-до-Read** («File has not been read yet»): правка файла без Read в сессии (особ. linter-modified / freshly-created).
3. **File-modified-since-read**: kit-inventory AUTO-regen / ruff-format тронул файл → Edit fail. Фикс: re-Read после мутирующих tool.
4. **String-not-found в Edit**: невидимые unicode (_DANGER/_CTRL_RE) / whitespace. Фикс: regex/unicode строить через python, не Edit-paste.
5. **hook false-fire**: phase-advance/review-gate на безобидном bash с литералом `gh pr merge`/`git push` → op-detect substring. Фикс: KIT-OD-1 частично + workaround «Edit, не Bash для текста с merge-литералом».
6. **bash-ошибки**: `command not found: python` (→ .venv/bin/python), zsh `no matches found` (glob → quote/`2>/dev/null`), `git checkout` затирает uncommitted.
7. **zsh bad math** (`$N[:` = array-math): quoting в тест-скриптах.
8. **control-characters** (Bash reject zero-width): payload через chr()/файл, не литералы.
9. **agent-not-in-registry**: свежесозданные агенты dispatchable после reload.

## Границы
- src/ заморожен. Фиксы — только kit/process/docs. op-detect полный argv → KIT-OD-1 backlog (частично здесь).
