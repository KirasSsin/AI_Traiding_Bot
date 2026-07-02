---
title: "Sprint 67 — Desktop Auto-Resume (план)"
type: plan
sprint: 67
created: 2026-07-02
updated: 2026-07-02
status: active
sources: [kit/auto-resume/lib/auto_resume_poll.py, kit/hooks/limit-marker.sh, llm-wiki/wiki/project/components/auto-resume.md]
---

# S67 — Desktop Auto-Resume

## Цель

Авто-продолжение прогона после сброса usage-лимита для оператора, работающего **только в Claude Code desktop** (не CLI). Закрывает пересмотренный OQ-4.

## Контекст (verdict OQ-4)

Research (claude-code-guide, fable-5, code.claude.com/docs): нативного «та же desktop-сессия сама возобновляется» НЕТ (open req `anthropics/claude-code#35744`). Но:
- Хуки/settings общие desktop↔CLI (`~/.claude/`) → C1 `StopFailure` `limit-marker.sh` (S58) **уже пишет маркер в desktop**.
- `scheduled-tasks` MCP = Desktop local Scheduled Task: cron в local-time, стартует СВЕЖУЮ видимую sidebar-сессию с self-contained промптом, «runs while app open / on next launch».

S58-launchd (C2) остаётся опциональным headless-треком; S67 добавляет desktop-native путь поверх того же C1-маркера.

## Дизайн

**Поток:** лимит → C1 `limit-marker.sh` пишет `~/.claude/auto-resume/pending.json` → Scheduled Task (cron `*/30`) стартует desktop-сессию → промпт вызывает gate → GO → сессия снимает маркер, читает `SPRINT_STATE.next_action`, продолжает kit-цикл. Снова лимит → C1 новый маркер → следующий тик.

**Ключевое отличие от C2:** desktop сам стартует сессию (не headless `claude -p`). Значит нужен **gate-only** helper — те же guardы C2, но БЕЗ вызова `claude`, только решение + управление маркером.

### Задачи

| # | Задача | Файлы | Делегат |
|---|---|---|---|
| T1 | `auto_resume_gate.py` — gate-only (marker/age/foreign/stale/noprog/lock/malformed guards из C2, вывод `GO`/`WAIT`/`NONE`/`STALE`/`FOREIGN`; при GO — записать `last_stamp`+`attempt`++ в маркер; прогресс между тиками = `progress_stamp` diff → noprog++). НЕ вызывает claude. python3.9-совместим. | `kit/auto-resume/lib/auto_resume_gate.py` | fable-5 (TDD) |
| T2 | Тесты gate — сценарии: no-marker→NONE / age<MIN→WAIT / GO+stamp-записан / stale(age>MAX)→карантин / foreign-cwd→карантин / malformed→карантин / noprog≥MAX→STALE / badsid→карантин. Переиспользовать паттерн `test_state_integrity_security.py`. | `kit/auto-resume/tests/test_auto_resume_gate.py` | fable-5 (TDD) |
| T3 | Промпт Scheduled Task (self-contained, RU): (1) Bash gate → читает решение; (2) NONE/WAIT/STALE/FOREIGN → сразу стоп; (3) GO → снять маркер, прочитать SPRINT_STATE, продолжить next_action по kit-циклу per-task, `last_task_sha` = НЕДОВЕРЕННЫЙ (hex-валидация до shell). Не задавать вопросов → OPERATOR-QUEUE. | текст в plan + создание через MCP | controller |
| T4 | Создать Scheduled Task через `scheduled-tasks` MCP (`taskId: kit-desktop-auto-resume`, `cron */30 * * * *` MSK, `notifyOnCompletion:false`); задокументировать в `auto-resume.md` + управление (list/update/disable). Условие «Keep computer awake». | `auto-resume.md`, MCP | controller |

## Acceptance

- `auto_resume_gate.py` gate-режим: 8 red/green сценариев зелёные (`.venv/bin/pytest kit/auto-resume/tests/`).
- Dry-run: нет маркера → `NONE`; свежий маркер (age<300) → `WAIT`; валидный маркер age>300 → `GO` + `last_stamp` записан.
- Scheduled Task создан (`list_scheduled_tasks` показывает `kit-desktop-auto-resume`, enabled, nextRunAt).
- `hooks-selfcheck`/`bash -n` — gate helper python (не bash) → syntax OK через `.venv/bin/python -c`.
- Guardы: foreign-cwd маркер → карантин (не резюмит чужой проект); stale >48ч → карантин + лог оператору.
- auto-resume.md обновлён (S67 desktop-путь боевой), sprint-67 page, index, current-state (+ scheduled task в инвентарь).

## Риски / guards (autonomous loop)

- **Бесконечный цикл при активном лимите:** сессия стартует, мгновенно упирается (дёшево), C1 обновляет ts. noprog≥3 без прогресса → STALE-карантин → оператор. Защита от «стартует но не двигается».
- **Foreign cwd:** маркер другого проекта → gate FOREIGN-карантин (как C2).
- **Operator-race:** оператор в живой desktop-сессии + task fires → две сессии. Смягчение: MIN_AGE 300с + гейт снимает маркер ТОЛЬКО при реальном GO; полного abort нет (принято, как S58).
- **App закрыт/Mac спит:** task не тикает (Desktop-ограничение). Митигация: «Keep computer awake» (Settings→Desktop app→General). Пропуск → один catch-up на пробуждении.
- **Секреты:** gate не логирует маркер целиком; `_CTRL_RE`-санитайз лог-строк (переиспс. C2).

## Фазы
Plan(3, doc-first) → Execute(4, fable-5 TDD) → Verify(5) → Review(6 security-auditor fable-5: autonomous-resume surface) → Sync(7) → Ship(8 commit+tag alpha.67, push отложен per оператор) → Close(9).

## Related
[[../components/auto-resume]] · [[../decisions/0076-model-pin-uniform-fable5]] · [[../OPERATOR-QUEUE]] (OQ-4) · C2 `kit/auto-resume/lib/auto_resume_poll.py`
