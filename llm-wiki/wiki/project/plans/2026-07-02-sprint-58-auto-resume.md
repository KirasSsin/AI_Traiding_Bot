---
title: Sprint 58 — Auto-Resume & Continuity (kit-maintenance, приоритет оператора)
type: plan
sprint: 58
updated: 2026-07-02
branch: feature/sprint-58-auto-resume
scope: кит-инфраструктура; src/ НЕ трогаем
source: KIT-MASTER-PLAN + ресерч claude-code-guide (verified v2.1.154 docs+CLI)
---

# План S58 — «Auto-Resume»: лимит кончился → работа продолжилась сама

## Проблема
Сессия спринта упирается в usage-лимит (5h-окно/weekly) → работа замирает до ручного «продолжай». Оператор хочет: опрос «лимит обновился?» → автоматическое возобновление.

## Верифицированные факты (ресерч 2026-07-02, CLI v2.1.154)
- Хук-событие `StopFailure` срабатывает при обрыве хода по API-ошибке; payload содержит `error: "rate_limit"` (+ `session_id`, `transcript_path`). Отличим лимит от нормального завершения.
- Встроенного auto-resume НЕТ (флагов/настроек не существует) → внешний опросник.
- Headless: `claude -p "<prompt>" --resume <session-id> --output-format json` возобновляет конкретную сессию (в т.ч. десктопную) из cwd проекта; JSON содержит `is_error`/`api_error_status`/`session_id`.
- Время сброса лимита machine-readable НЕ отдаётся → фиксированный интервал опроса.
- launchd: минимальный PATH (абсолютные пути), Keychain требует `UserInteractionAllowed: true`; логи через StandardOutPath/ErrorPath. Секреты в plist НЕ кладём (auth через существующий OAuth/Keychain).

## Дизайн (3 компонента, всё в kit/auto-resume/ + зеркало в живую систему)

### C1 — Детектор: `limit-marker.sh` (хук StopFailure)
Регистрируется в settings.json `hooks.StopFailure`. Скрипт читает payload; если `error` ∈ {rate_limit, overloaded} → пишет маркер `~/.claude/auto-resume/pending.json`: `{ts, session_id, cwd, error}` (+ append в `~/.claude/auto-resume/log`). Другие ошибки — игнор (billing/auth человеку, не машине). Fail-OPEN.

### C2 — Опросник: `auto-resume-poller.sh` + `com.kit.auto-resume.plist`
launchd LaunchAgent (интервал 600с). Логика:
1. Нет `pending.json` → exit 0 (тихо).
2. Маркер старше 48ч → переименовать в `stale-<ts>.json`, записать в лог «нужен оператор», exit 0 (не зацикливаемся).
3. Иначе: `cd <cwd из маркера>` → `claude -p "<resume-промпт>" --resume <session_id> --output-format json --allowedTools <рабочий набор>` (таймаут обёрткой).
4. Разбор JSON: `is_error == false` → маркер снят, лог «RESUMED»; `is_error == true` (лимит ещё) → маркер остаётся, ждём следующий тик.
5. Если во время возобновлённого хода лимит кончится снова — StopFailure напишет новый маркер → цикл сам поддерживает многодневный прогон.

Resume-промпт: «Ты продолжаешь автономный прогон. Прочитай llm-wiki/wiki/project/SPRINT_STATE.md → продолжай с next_action по фазам кита. Работай до завершения текущей задачи/фазы, обновляя SPRINT_STATE per-task.»

### C3 —管理: `kit/auto-resume/install.sh` + компонент-страница wiki
install: копирует скрипты, `launchctl bootstrap gui/$(id -u)` plist, статус-команда. Uninstall-режим. Регистрация хука в settings.json через jq (идемпотентно).

Опция (выключена по умолчанию): watchdog-режим `WATCHDOG=1` в `~/.claude/auto-resume/config` — если маркера нет, но SPRINT_STATE.phase ≠ between-sprints и mtime SPRINT_STATE старше 30 мин → мягкий continue (страховка от «ход тихо завершился, прогон не доделан»). Риск конфликта с живой интерактивной сессией → поэтому opt-in.

## Trace map

| Задача | Что | Proof |
|---|---|---|
| T1 | limit-marker.sh + регистрация StopFailure + kit-зеркало | Симуляция payload (echo JSON \| скрипт) → pending.json появился с корректными полями; не-лимит ошибка → маркера нет |
| T2 | auto-resume-poller.sh (без launchd) | red: маркер есть + мок-claude (лимит) → маркер остался; green: мок-claude success → маркер снят, лог RESUMED; stale-маркер 48ч → переименован |
| T3 | plist + install.sh | `plutil -lint` OK; `launchctl print gui/UID/com.kit.auto-resume` после bootstrap; bash -n; повторный install = idempotent |
| T4 | Sync: component-страница (+ документированные ограничения: Mac asleep = launchd молчит, mid-run operator race → running.lock) + kit-inventory + строка в CLAUDE.md | страница есть, счётчики позеленели |

## PRE-PLAN вердикт architecture-reviewer: APPROVE_WITH_CONDITIONS (BINDING, вписано)

| # | Условие | Где закрыто |
|---|---|---|
| C-1 | `is_error:false` недостаточно — прогресс проверять по diff(SPRINT_STATE hash + git HEAD) до/после; outcome 4-значный: RESUMED_PROGRESS / RESUMED_NO_PROGRESS (маркер остаётся, счётчик noprog, ≥3 → stale-эскалация) / STILL_LIMITED / STALE | T2 poller + red/green сценарий no-progress |
| C-2 | Явный `--allowedTools "Bash,Read,Edit,Write,Grep,Glob,Task"`; `--dangerously-skip-permissions` ЗАПРЕЩЁН; T2-тест: headless scratch-сессия без allowedTools НЕ может писать файлы (если наследует шире — CRITICAL, Ship-гейт: добавить явный `--permission-mode default`) | T2 permission-probe, Ship-гейт |
| C-3 | hooks-selfcheck.sh покрывает новый limit-marker.sh (glob *.sh) — проверить прогоном, не предполагать | T1 proof |

MEDIUM (принято): running.lock (pid+ts) от operator-race — документированное ограничение; 600с = баланс «жирный prompt-cache не нужен, попытка при лимите дешёвая, 10 мин ≪ 102ч исторического простоя»; sleep-ограничение launchd → component-страница (+ заметка про caffeinate).

## Фазы: 1 done → 2 done (ресерч+PRE-PLAN вердикт architecture-reviewer BINDING) → 3 этот файл → 4 T1-T4 → 5 симуляции red/green + bash -n + plutil → 6 architecture-reviewer + security-auditor (unattended-запуск, --allowedTools объём, отсутствие секретов в plist) → 7 wiki → 8 ship tag alpha.58 → 9 close → S59.

## Риски
- `-p --resume` на десктоп-сессии: подтверждено доками+тестом агента, но наш случай (121MB транскрипт) может грузиться долго → таймаут 30 мин на вызов, лог длительности.
- Все хуки глобальные (~/.claude) → limit-marker сработает и в чужих проектах: маркер пишет cwd, poller работает только если cwd == наш repo root (guard в скрипте).
- Двойной запуск (живая сессия + poller): poller перед resume проверяет lock-файл `pending.lock` + возраст маркера ≥ 5 мин (даём живой сессии шанс).
