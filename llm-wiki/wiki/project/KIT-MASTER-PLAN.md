---
title: KIT-MASTER-PLAN — ультимативный план доработки кита (mega-run v2)
type: plan
updated: 2026-07-02
status: in-progress
sources: 8 AI-аудитов (валидированы, VERIFICATION-LEDGER), 14 docs-страниц кита (валидированы 2026-07-02), Фаза 0, решения оператора
---

# KIT-MASTER-PLAN — от него отталкиваемся, сделанное зачёркиваем

Цель: максимум КПД / минимум токенов; все фазы принуждаются механически; команда агентов участвует в каждом спринте (директива оператора 2026-07-02); документация самообновляется; состояние не теряется; работа возобновляется после лимитов автоматически.

## Статус прогона

- [x] ~~Фаза 0 — MERGE & VERIFY 8 аудитов~~ → UNIFIED-BACKLOG-S57 (21 CONFIRMED), VERIFICATION-LEDGER (24 проверки), OPERATOR-QUEUE
- [x] ~~Расследование нумерации: «S75» не существовал; S56 docs не закрыт (chore-ветка); следующий = S57~~
- [x] ~~A1 — валидация 14 docs-страниц кита~~ (2026-07-02: валидны; устаревания: модели агентов, хуки 6→7, токен удалён S57, state 5380Б)
- [x] ~~S57 «Ground Truth & Basis»~~ — SHIPPED v0.1.0-alpha.57: секрет out (+апрельский .bak убит), kit/ в git (30 файлов), hooks-selfcheck fail-CLOSED, kit-inventory AUTO+drift-guard, link-scanner. Ревью: arch APPROVE, security BLOCKER→fixed
- [x] ~~A2 — анализ session-export + транскрипта~~ → [[kit-weakpoints-from-history]]: 27 limit-остановок ≈ 102ч простоя (S58 окупается сразу); 61 автокомпакция −92% (S62 телеметрия готова в jsonl); 75 hook-блоков (58 = adr-sync touch-шум → S59 KIT-009); Read-фейлы 12 (S62 cascade-хук); сломанный хук в бою 1 раз (S57 selfcheck ✅)
- [ ] **S58 «Auto-Resume & Continuity» (приоритет оператора №1)** — детали ниже
- [ ] S59 «Gates» — KIT-002 branch-bypass, KIT-003 review-gate, KIT-009 ADR-sync по содержимому, KIT-013 per-task WARN
- [ ] S60 «Docs-Sync Gate» — шаг 0: мердж chore (закрытие S56, 128 стр docs) → staleness-хук + link-хук + manifest + скилл docs-update + починка всех битых ссылок + Фаза 7 = wiki+docs
- [ ] S61 «SPRINT_STATE v2» — PRE-PLAN гейт architecture-reviewer; state/CURRENT ≤2КБ + BACKLOG + .backup/ + integrity-hook + last_task_sha; миграция читателей
- [ ] S62 «Manifest & Telemetry» — skill-firing manifest в sprint-finish, kit-validation-checklist, cascade-хук (block full-read banned), budget-hook ревизия, ADR AUTOCOMPACT/MAX_THINKING
- [ ] S63 «Fable-5 Team» — матрица §4.1 (trader-expert+architecture→fable-5), ADR pin-policy v2, агенты kit-auditor/merge-analyst/release-manager, смоуки
- [ ] S64 «Plugins & Best Practices» — GitHub-ресерч по звёздам, строгая валидация совместимости, внедрение ≤2 с метрикой токены до/после (директива: внедрить, не только зафиксировать)
- [ ] Финал — kit-upgrade-report.md, мастер-план вычеркнут, один git push origin

## S58 Auto-Resume — дизайн (укрупнённо)

Проблема: сессия упирается в лимит (5h-окно/weekly) → спринт замирает до ручного вмешательства.
Механизм (детали финализируются после ресерча claude-code-guide + PRE-PLAN architecture-reviewer):
1. Детектор остановки по лимиту → маркер-файл `.claude/auto-resume/pending` (время сброса, sprint, next_action из SPRINT_STATE).
2. Внешний опросник: launchd-агент пользователя (macOS), интервал ~10 мин: маркер есть → пробуем `claude --continue` / `claude -p` c промптом «sprint-orient → продолжай next_action»; лимит не сброшен → попытка дёшево падает, ждём следующего тика; успех → маркер снят, лог-запись.
3. Опора на SPRINT_STATE.next_action (уже per-task протокол) — сессия знает, где встала; S61 v2 усилит.
4. Fail-safe: маркер старше 48ч → уведомление оператору вместо бесконечных попыток; никакого автозапуска без маркера.
Proof: симуляция маркера → resume-скрипт корректно продолжает; битый маркер → не зациклился.

## Обязательства каждого спринта (директива оператора)
Полный 9-фазный цикл; Workflow/панели агентов на design/brainstorm-шагах; Фаза 6 = минимум 2 профильных ревьюера параллельно (architecture + security для кит-правок; +doc-reviewer на доки); verification-before-completion с пруфами в спринт-странице.

## Внеспринтовое (по мере)
- [ ] OQ-1: ротация GitHub-токена (оператор)
- [ ] `docs/Без названия.md` — чужой файл, решает оператор
- [ ] DEFER-реестр: БД-state (ADR-черновик), docs-CI GitHub Actions, партиции памяти, worktrees для autoresearch
