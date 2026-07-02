---
title: Sprint 61 — SPRINT_STATE v2 (Вариант B): отказоустойчивость без разделения
type: summary
sprint: 61
created: 2026-07-02
updated: 2026-07-02
tag: v0.1.0-alpha.61
status: stable
---

# S61 — SPRINT_STATE v2 (mega-run 5/8)

**TL;DR:** SPRINT_STATE.md получил crash-durability без разделения монолита. Авто-бэкап перед каждым коммитом, валидация + авто-восстановление при повреждении (fail-OPEN, чтобы не дедлочить unattended auto-resume), `last_task_sha` как точка восстановления. Полное разделение (Вариант A) осознанно отложено: blast radius 17 читателей, боль ≤6КБ уже закрыта дисциплиной. src/ не тронут.

## Решение (PRE-PLAN → ADR [[../decisions/0073-sprint-state-v2-variant-b]])

architecture-reviewer BINDING: **Вариант B** (упрочнение), а не A (разделение на state/CURRENT.md + BACKLOG.md). Три sub-decision: авто-бэкап = хук (не скилл); integrity = fail-OPEN-с-восстановлением (не fail-CLOSED — второй fail-CLOSED сверх hooks-selfcheck дедлочил бы auto-resume); last_task_sha = HEAD code-commit. A остаётся живой опцией с триггерами пересмотра в ADR.

## Сделано

| T | KIT | Что | Proof |
|---|---|---|---|
| T1 | KIT-008 | `state-backup.sh` (PreToolUse `git commit`): staged SPRINT_STATE.md → `state/.backup/SPRINT_STATE.<ts>.md`, ротация keep-20. fail-OPEN | green: коммит со staged state → бэкап появился; ротация 20 |
| T2 | KIT-008 | `state-integrity-check.sh` + `lib/state_integrity.py` (SessionStart + push): валидный YAML (sprint/phase/branch), phase-regex, ≤6КБ; повреждён → авто-восстановление из новейшего .backup. fail-OPEN | red: нет frontmatter → восстановлен exact (sha совпал); green: валидный → тишина |
| T3 | KIT-008 | `last_task_sha:` во frontmatter — точка восстановления auto-resume; sprint-orient сверяет с HEAD; poller инжектит в resume-prompt | integrity clean с полем; poller/orient обновлены |
| T4 | — | ADR 0073 + component [[../components/state-integrity-hook]] + index + adr-index-sync; `.backup/` в .gitignore (runtime-эфемерно) | adr-index green; check-ignore verified |
| T5 | — | Подключение (13 PreToolUse + 2 UserPromptSubmit + 3 SessionStart), kit-зеркало sync | selfcheck OK; kit-drift clean; bash -n 16 хуков |
| T6 | sec | Закалка по 5 раундам adversarial-hunt (BLOCKER symlink-exfil/dest-symlink, HIGH parser-differential/dup-key/non-ASCII-ws, gate fail-open). Валидатор: symlink-guards, atomic_write, validate-before-install, raw-line+strict-ASCII поля, _DANGER+isspace+dup-key. Гейты: fail-CLOSED на неканоничной phase (sprint-flow/phase-advance/review-gate) | regression 32 python + 13 bash PASS; ruff/bash -n OK; review [[../reviews/review-s61]] |

## Ревью (Phase 6) — артефакт [[../reviews/review-s61]]

- **architecture-reviewer: APPROVE_WITH_CONDITIONS** — HIGH #1 [BINDING] staleness-blind restore → закрыт (`stale_restore()` git-ancestor + STALE-RESTORE WARN). MEDIUM #2/#3/#4 закрыты/задокументированы.
- **security-auditor: 1 BLOCKER + 2 HIGH + MEDIUM/LOW — ВСЕ закрыты в спринте, regression-tested 9/9:**
  - BLOCKER #1 symlink-follow exfil (PROVEN) → `safe_backups()` отсекает симлинки + dir-escape.
  - HIGH #2 blind restore подделанного бэкапа → validate-before-install + walk-older + no-write-on-total-fail.
  - HIGH #3 `last_task_sha` → shell-инъекция → full-match `^[0-9a-fA-F]{7,40}$`.
  - MEDIUM #4 sticky-poison → mtime-select. LOW #6 escape → sanitize. LOW #7 self-skip → сужен.
- Доказательства: exploit-regression 9/9 PASS; bash -n 16 + ruff + py_compile OK; adversarial bypass-hunt (4 lens + refutation).

## Принятые границы (документировано)

- **Forged-valid-backup** — integrity структурный, не семантический: бэкап с валидным frontmatter + предком-`last_task_sha` + подделанным телом phase-таблицы установится (validate не парсит таблицу). Baseline «local user compromised» + tamper-evidence (подпись/hash бэкапов) → S62.
- **Repairer, не gate** — state-integrity никогда не блокирует (fail-OPEN); money-гейты верят файлу, который хук авто-переписывает. Приемлемо только потому, что #1/#2 закрыли «что пишется». Инвариант «gate-input пишется только человеком» → S62 manifest.
- **Split (Вариант A) отложен** — решение, не долг: триггеры пересмотра явны (стабильно >5КБ / ≥3-я ось записи / удешевление миграции читателей).

## Related
[[../plans/2026-07-02-sprint-61-state-v2]] · [[../components/state-integrity-hook]] · [[../decisions/0073-sprint-state-v2-variant-b]] · [[../components/auto-resume]] · [[../KIT-MASTER-PLAN]]
