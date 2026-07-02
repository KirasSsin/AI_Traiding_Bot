---
title: Sprint 58 — Auto-Resume & Continuity
type: summary
sprint: 58
created: 2026-07-02
updated: 2026-07-02
tag: v0.1.0-alpha.58
status: stable
---

# S58 — Auto-Resume (mega-run 2/8, приоритет оператора №1)

**TL;DR:** сессия упёрлась в usage-лимит → кит сам возобновляет работу после сброса. Хук `StopFailure` пишет маркер, launchd-опросник (600с) поднимает сессию headless-вызовом с проверкой реального прогресса. Историческая цена проблемы: 27 остановок ≈ 102 ч простоя. src/ не тронут.

## Сделано

| T | Что | Proof (в сессии) |
|---|---|---|
| T1 | `limit-marker.sh` + `lib/auto_resume_marker.py` — StopFailure→маркер (rate_limit/overloaded only, атомарный replace) | green: маркер с полями; red: billing/мусор → нет маркера; selfcheck покрывает (C-3 ✅) |
| T2 | `auto_resume_poll.py` — 4-значный outcome (C-1 ✅): PROGRESS(sha256 state+HEAD)/NO_PROGRESS(noprog→3→stale)/STILL_LIMITED/ESCALATE(48ч); cwd-guard(foreign), lock(mkdir, сирота>2ч), timeout 1800с; `--allowedTools` явный + `--disallowedTools WebFetch,WebSearch`, dangerously-skip ЗАПРЕЩЁН (C-2) | 7 мок-сценариев green + hardening: badsid/malformed → карантин |
| T3 | `com.kit.auto-resume.plist` (600с, без секретов — Keychain/OAuth only) + `install.sh` (install/uninstall/status, идемпотентен, same-FS atomic swap settings.json) | plutil OK; launchctl loaded; kickstart-тик чистый; повторный install idempotent |
| T4 | component page [[../components/auto-resume]] + index + CLAUDE.md continuity-note + OQ-4 + AUTO-блоки (hooks 7+2+2, files 10) | kit-drift clean |

## Ревью (Phase 6) — оба APPROVE

- **PRE-PLAN architecture-reviewer:** APPROVE_WITH_CONDITIONS → все 3 HIGH-условия закрыты в коде (проверено post-impl по тексту кода, не по коммит-месседжам).
- **security-auditor: APPROVE** (0 BLOCKER/HIGH). Plist без секретов — endorsed; маркер = не новая поверхность (subsumed); PreToolUse-гейты работают и в `-p` (пуш/мердж защищены даже headless). MEDIUM (unattended full-capability) принят с митигантами: cwd-guard + константный промпт + хуки активны. LOW×4 → 3 исправлены в спринте (sid-regex, same-FS mktemp+trap, malformed-карантин), №4 (0644 маркер) — не требует действий.
- **architecture-reviewer post-impl: APPROVE** (0 C/H/M). Lock корректен при StartInterval<timeout; ordering эскалации верен; noprog не сгорает на STILL_LIMITED. LOW#2: нет коммитнутого pytest для poller — норма kit/-тулинга (bash -n + интерактивный red/green), follow-up на будущий kit-maintenance.

## Боевой гейт: OQ-4 (оператор)

CLI залогинен в Console-аккаунт без кредитов → headless «Credit balance is too low». До `/login` в подписку механизм в безопасном холостом ходу (STILL_LIMITED→эскалация). Пост-логин: permission-probe A/B (OPERATOR-QUEUE) закрывает C-2 полностью. E2E на живом лимите — при первом реальном срабатывании.

## Ограничения (документированы в component page)

Mac asleep → launchd молчит (caffeinate для ночных прогонов); operator-race смягчён MIN_AGE+lock (без abort-канала); reset-время лимита не машиночитаемо → фиксированный опрос.

## Related

[[../plans/2026-07-02-sprint-58-auto-resume]] · [[../components/auto-resume]] · [[../kit-weakpoints-from-history]] · [[../KIT-MASTER-PLAN]]
