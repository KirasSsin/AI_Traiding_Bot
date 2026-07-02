---
title: Auto-Resume — авто-возобновление прогона после usage-лимита
type: component
tags: [kit, auto-resume, launchd, continuity, hooks]
created: 2026-07-02
updated: 2026-07-02
sources: [kit/auto-resume/, kit/hooks/limit-marker.sh, kit/hooks/lib/auto_resume_marker.py]
status: stable
---

# Auto-Resume (S58) — лимит кончился → работа продолжилась сама

**TL;DR:** сессия спринта упёрлась в usage-лимит → хук пишет маркер → launchd-опросник каждые 10 минут пробует `claude -p --resume <sid>` → при сбросе лимита прогон продолжается с `SPRINT_STATE.next_action`. Историческая цена проблемы: 27 остановок ≈ 102 ч простоя ([[../kit-weakpoints-from-history]]).

## Механика (3 компонента)

| Компонент | Файл (kit → live) | Роль |
|---|---|---|
| C1 детектор | `kit/hooks/limit-marker.sh` + `lib/auto_resume_marker.py` → `~/.claude/hooks/` | Хук `StopFailure`: `error ∈ {rate_limit, overloaded}` → атомарный маркер `~/.claude/auto-resume/pending.json` (ts, session_id, cwd). Прочие ошибки (billing/auth) — человеку. Fail-OPEN |
| C2 опросник | `kit/auto-resume/auto-resume-poller.sh` + `lib/auto_resume_poll.py` → `~/.claude/auto-resume/bin/` | launchd, 600с. Outcome 4-значный (условие PRE-PLAN C-1): RESUMED_PROGRESS (diff SPRINT_STATE hash+git HEAD → маркер снят) / RESUMED_NO_PROGRESS (noprog++, ≥3 → stale) / STILL_LIMITED (ждём) / STALE-ESCALATE (>48ч → оператор). Guard: чужой cwd → foreign-*, lock от параллельного запуска (сиротский >2ч переезжает) |
| C3 установка | `kit/auto-resume/install.sh` (install/uninstall/status) + `com.kit.auto-resume.plist` | Идемпотентно: скрипты → bin, StopFailure → settings.json (jq), plutil-lint → `launchctl bootstrap gui/UID`. Синтаксис-гейт перед установкой |

Headless-вызов: `claude -p "<resume-промпт>" --resume <sid> --output-format json --allowedTools "Bash,Read,Edit,Write,Grep,Glob,Task"` из cwd репозитория. `--dangerously-skip-permissions` ЗАПРЕЩЁН (PRE-PLAN C-2). Resume-промпт ведёт сессию в `SPRINT_STATE.md → next_action` (поэтому per-task протокол обновления state — опора всего механизма).

Цикл через многодневный прогон: возобновлённый ход снова упёрся в лимит → StopFailure пишет новый маркер → цикл продолжается без человека.

## Ограничения (документированные)

- **Mac спит / крышка закрыта → launchd не тикает.** Для ночных прогонов: `caffeinate -is` или Energy Settings «Prevent sleep». Это ограничение macOS, не бага.
- **Operator-race:** оператор вернулся в живую сессию во время headless-хода → два писателя. Смягчение: MIN_AGE 300с + lock; полного abort-канала нет (принятое ограничение, PRE-PLAN MEDIUM).
- **OQ-4 (пересмотрено — desktop-путь, 2026-07-02):** оператор работает ТОЛЬКО в Claude Code desktop (не CLI), поэтому CLI-`/login`-гейт снят с критического пути. Хуки/skills/settings общие для desktop и CLI (`~/.claude/`) → C1 (`StopFailure` `limit-marker.sh`) СРАБАТЫВАЕТ в desktop. Но launchd-C2 запускает headless-сессию, отдельную от desktop-списка. Boевой desktop-native путь → секция «Desktop Auto-Resume» ниже. launchd-C2 остаётся как опциональный background-трек (headless, результаты в git).
- Reset-время лимита не machine-readable (в тексте «resets 3pm (TZ)», таймзона плавала) → фиксированный опрос 600с вместо парсинга.

## Проверено (S58, red/green)

C1: rate_limit → маркер с полными полями; billing_error/мусор → нет маркера, fail-open. C2 (мок-claude): 7 сценариев — min-age тишина / STILL_LIMITED / RESUMED_PROGRESS (маркер снят) / NO_PROGRESS×3 → stale / foreign cwd / 48h stale / parallel lock. C3: plutil OK, bootstrap loaded, повторный install идемпотентен, kickstart-тик чистый. hooks-selfcheck покрывает limit-marker.sh (PRE-PLAN C-3 ✅).

## Управление

```bash
./kit/auto-resume/install.sh status     # состояние
./kit/auto-resume/install.sh uninstall  # снять launchd-агент (kill-switch)
tail -20 ~/.claude/auto-resume/log      # журнал решений
```

## Desktop Auto-Resume (OQ-4, verdict research 2026-07-02)

**Проблема:** оператор в desktop-приложении; launchd-опросник C2 запускает headless `claude -p` — отдельную от desktop сессию (docs: CLI и desktop делят конфиг/CLAUDE.md, но история сессий раздельная). Для чисто-desktop оператора headless-продолжение идёт «в фоне», не в его окне.

**Verdict** (claude-code-guide fable-5, источники code.claude.com/docs): нативного «та же сессия сама возобновляется при сбросе лимита» НЕТ — open feature request `anthropics/claude-code#35744` (смежные #36320/#26775/#18980/#47276 закрыты как duplicate, НЕ completed).

**Реалистичный desktop-native путь (рекомендуется):**
1. **C1 готов** — `StopFailure`-матчер `rate_limit` (`limit-marker.sh`) работает и в desktop (shared `~/.claude/settings.json`). Маркер пишется.
2. **Desktop local Scheduled Task** (Settings → Routines → Local, Desktop-фича): каждые 30–60 мин — «прочитай `~/.claude/auto-resume/pending.json`; если есть и время сброса прошло → прочитай SPRINT_STATE.md, продолжи `next_action`; иначе сразу стоп». По расписанию desktop стартует СВЕЖУЮ видимую sidebar-сессию, ре-ориентация через `sprint-orient` (опора — `SPRINT_STATE.next_action`, per-task протокол).
3. **Условия:** app открыт + Mac не спит (Settings → Desktop app → General → «Keep computer awake»). Пропущенный запуск = один catch-up на пробуждении. Запуск до сброса лимита ошибётся — следующий подхватит.

**Плюсы:** всё в GUI, без CLI-логина (снимает старый CLI-гейт OQ-4). Лимит plan-usage общий на все поверхности — routines/cloud его не обходят.

**Реализация:** отдельный kit-мини-спринт **S67 «Desktop Auto-Resume»** — заменить/дополнить launchd desktop-scheduled-task (создаётся в UI ИЛИ через scheduled-tasks MCP). Recurring-задачу не создаю без явного ОК (автономный процесс).

## Related

- [[hooks-selfcheck-hook]] — сторож синтаксиса, покрывает и limit-marker.sh
- [[state-integrity-hook]] — S61: `last_task_sha` даёт poller точную точку восстановления при обрыве между коммитом и обновлением state
- [[../kit-weakpoints-from-history]] — обоснование (102ч простоя)
- [[../plans/2026-07-02-sprint-58-auto-resume]] — план + PRE-PLAN вердикт
