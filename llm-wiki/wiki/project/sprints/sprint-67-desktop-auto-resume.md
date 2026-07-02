---
title: Sprint 67 — Desktop Auto-Resume (авто-продолжение в desktop-приложении)
type: summary
sprint: 67
created: 2026-07-02
updated: 2026-07-02
tag: v0.1.0-alpha.67
status: stable
---

# S67 — Desktop Auto-Resume

**TL;DR:** авто-продолжение прогона после сброса usage-лимита для оператора, работающего ТОЛЬКО в Claude Code desktop (не CLI). Нативной фичи нет (open req #35744) → desktop-native путь: C1-маркер (`limit-marker.sh`, уже работает в desktop) + **gate-only** helper (`auto_resume_gate.py`, решение GO/WAIT/NONE/STALE/FOREIGN, без headless `claude`) + **Desktop Scheduled Task** (`kit-desktop-auto-resume`, cron `*/30` MSK) стартует свежую sidebar-сессию → продолжает `SPRINT_STATE.next_action`. Закрывает пересмотренный OQ-4. src/ не тронут.

## Сделано

| T | Что | Proof |
|---|---|---|
| T1 | `auto_resume_gate.py` — gate-only (guardы C2: age/foreign/stale/noprog/lock/malformed/badsid + `first_ts` wall-clock ceiling; O_NOFOLLOW sanitized log, atomic writes, gate.lock; НЕ вызывает claude) | py3.9-compat, ruff-clean |
| T2 | `test_auto_resume_gate.py` — 20 pytest (NONE/WAIT/FOREIGN/STALE/GO + first_ts ceiling + lock-scope + symlink guards) | **20/20 GREEN** (`.venv/bin/pytest`) |
| T3 | Consumer-контракт `kit/auto-resume/desktop-task-prompt.md` (промпт Scheduled Task в git, под ревью — закрывает C-C) | GO-only, не `--resume` sid, fresh session |
| T4 | Desktop Scheduled Task `kit-desktop-auto-resume` создан через `scheduled-tasks` MCP (cron `*/30 * * * *`, `notifyOnCompletion:false`, enabled) | `list_scheduled_tasks` ✓ |

## Дизайн (отличие от S58 C2)

S58-C2 (`auto_resume_poll.py`): launchd → headless `claude -p --resume` (headless-сессия, отдельная от desktop). S67: desktop сам стартует видимую сессию через Scheduled Task, поэтому нужен **gate-only** helper — те же guardы, но вывод-решение вместо резюма. Оба поверх одного C1-маркера. C2 остаётся опциональным headless-треком.

**Cross-tick no-progress:** маркер снимается возобновлённой сессией (не переживает GO), поэтому счётчик прогресса в sidecar `gate_state.json` {last_stamp, attempt, first_ts}. `first_ts` = wall-clock потолок кампании (C-B fix): thrashing-сессия, что бесконечно re-limit'ит (ts маркера обновляется, stamp сбрасывается от SPRINT_STATE touch) — иначе не ограничена; `first_ts` даёт абсолютный предел → STALE.

## Ревью (Phase 6, security-auditor fable-5)

**Вердикт: APPROVE — 0 blockers.** 3 concern'а закрыты:
- **C-A** (sid-optional vs C2) → контракт: consumer НЕ использует `marker.session_id`, стартует свежую сессию (задокументировано в docstring + `desktop-task-prompt.md`). sid валидируется-если-есть (defense-in-depth).
- **C-B** (soft no-progress bound) → `first_ts` wall-clock ceiling внедрён + тест (STALE даже при меняющемся stamp).
- **C-C** (consumer не под ревью) → промпт зеркалирован в git (`desktop-task-prompt.md`).
- LOW (NONE-path lock scope) → clear под gate.lock.

Verified ревьюером: foreign-cwd не резюмит чужой репо; no shell/injection (git list-form, constant AR_REPO); atomic+O_NOFOLLOW; log-санитайз; fail-safe (любой сбой → NONE, exit 0, никогда GO на плохом вводе).

## Verify (Phase 5)

`20 passed in 0.29s`; ruff clean; dry-run: no-marker→NONE / age>300→GO (gate_state written) / foreign→FOREIGN (quarantined) / age<300→WAIT.

## Ограничения
App должен быть открыт + Mac не спит («Keep computer awake»). Пропуск тика → один catch-up. Первый тик без маркера → NONE (мгновенный стоп, мутаций нет). Лимит plan-usage общий на все поверхности — routines его не обходят.

## Related
[[../components/auto-resume]] · [[../plans/2026-07-02-sprint-67-desktop-auto-resume]] · [[../OPERATOR-QUEUE]] (OQ-4) · [[../decisions/0076-model-pin-uniform-fable5]]
