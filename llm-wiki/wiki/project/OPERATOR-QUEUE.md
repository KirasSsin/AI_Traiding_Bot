---
title: Operator Queue — действия, требующие человека
type: queue
updated: 2026-07-02
---

# OPERATOR-QUEUE — единственный канал к оператору

Пункты НЕ блокируют прогон. Статус OPEN → оператор выполняет → CLOSED.

## OQ-1 [OPEN] Ротация GITHUB_TOKEN (KIT-001, BLOCKER-часть, только руки человека)

Токен `ghp_LkY…` лежал плейнтекстом в `~/.claude/settings.json` и виден в git-историях чатов. Считать скомпрометированным.

Пошагово (≈5 минут):
1. GitHub → Settings → Developer settings → Personal access tokens → найти токен с префиксом `ghp_LkY` → **Revoke**.
2. Сгенерировать новый fine-grained PAT: репозиторий `KirasSsin/AI_Traiding_Bot`, права `Contents: Read/Write`, `Pull requests: Read/Write`.
3. Положить в Keychain (терминал):
   `security add-generic-password -a "$USER" -s github-pat-ai-trading -w '<НОВЫЙ_ТОКЕН>' -U`
4. Ничего не вписывать обратно в settings.json — прогон S57 уже удалил ключ из файла; git push работает через Keychain gh auth (`gho_…`), он НЕ отозван — проверка: `unset GITHUB_TOKEN GH_TOKEN; gh auth status`.

Proof-of-done: `grep -c ghp_ ~/.claude/settings.json` → `0` (выполнено прогоном) + токен отозван в UI GitHub (только ты).

**Оператор (2026-07-02): сделаю позже.** Остаётся OPEN; `gh` Keychain-auth (`gho_…`) работает, прогон не блокирован. Напоминание при следующем kit-спринте.

## OQ-2 [CLOSED] Решение по плагинам — отчёт (fix: файл `plugins-research.md`, НЕ `-s63`)
Оператор: «файла нет» — ссылка `plugins-research-s63.md` была неверна. Правильный путь: **[[plugins-research]]** = `llm-wiki/wiki/project/plugins-research.md`. Итог отчёта: внедрён **Context7 MCP** (docs библиотек, токен-экономия); **Frontend Design** → OQ-7 (оператор: «устанавливай всё» → ставим); дубли (code-review / security-guidance / commit-commands) отклонены осознанно (кит зрелый: L5-ревьюеры + superpowers покрывают).

## OQ-4 [OPEN → S67] Auto-Resume для desktop (CLI-путь отклонён оператором)

Оператор: «не пользуюсь claude CLI, работаю только через Claude Code **desktop** on Mac. Нужна функция: лимит закончился → наступил новый период → работа продолжается автоматически».

**Verdict** (research claude-code-guide fable-5, источники code.claude.com/docs — детали [[components/auto-resume]] секция «Desktop Auto-Resume»):
- Нативного «та же desktop-сессия сама возобновляется при сбросе лимита» **НЕТ** — open feature request `anthropics/claude-code#35744`.
- НО хуки/skills/settings общие desktop↔CLI (`~/.claude/`) → наш `StopFailure` `limit-marker.sh` (C1) **уже работает в desktop**.
- Реалистичный desktop-native путь: C1-маркер + **Desktop local Scheduled Task** (Settings → Routines → Local) стартует свежую видимую sidebar-сессию по расписанию → читает `SPRINT_STATE.next_action` → продолжает. Всё в GUI, без CLI-логина.

**Старый CLI-`/login`-гейт СНЯТ** (не используешь CLI). launchd-C2 остаётся опциональным headless-треком (результаты в git, не в твоём окне).

**Следующий шаг:** kit-мини-спринт **S67 «Desktop Auto-Resume»** — реализовать Scheduled Task (UI ИЛИ через scheduled-tasks MCP) + условие «Keep computer awake». Recurring автономную задачу НЕ создаю без явного ОК. Скажи «делаем S67» — запущу по kit-циклу.

## OQ-5 [CLOSED] Перезапуск сессии для 3 новых агентов (S63)

Оператор: «норм». Подтверждено 2026-07-02: kit-auditor / merge-analyst / release-manager в живом `~/.claude/agents/` И **dispatchable в текущей сессии** (reload состоялся — видны в available agent types; git-sync-валидация уже отработала 4× kit-auditor на fable-5). Реестр загружен, смоук-путь открыт.

## OQ-6 [CLOSED] doc-writer → fable-5 (оператор: «все агенты на fable-5 умышленно»)

Оператор: «Пока все агенты на fable-5 умышленно — токенов много, нужна глубокая проработка». **Выполнено 2026-07-02:** `doc-writer` поднят `claude-sonnet-5` → `claude-fable-5` в обоих деревьях (`kit/agents/doc-writer.md` + живой `~/.claude/agents/doc-writer.md`) + `kit/PINNED_VERSIONS.md`. Применится на reload сессии.

**Оператор (2026-07-02): ВСЕ агенты на fable-5 max** (safety-fallback → opus-4.8 max приемлем). **Выполнено:** 18 агентов = `claude-fable-5` в обоих деревьях (`diff -rq` clean) + `PINNED_VERSIONS.md` переписан + **ADR 0076** (суперседит 0075 mixed-tier). 6 money-ревьюеров подняты sonnet→fable; 3 экс-алиаса (frontend-developer / python-reviewer / doc-reviewer) → fable. Применится на reload.

## OQ-7 [CLOSED] Frontend Design plugin + Context7 (оператор: «устанавливай всё»)

**Выполнено 2026-07-02:**
- `frontend-design@claude-plugins-official` установлен (`claude plugin install`, scope: user; в `enabledPlugins`). Для будущей работы над `src/dashboard` UI.
- **Context7 MCP активирован:** `enabledMcpjsonServers: ["context7"]` в `~/.claude/settings.json` (project `.mcp.json` требовал ручного approval — снято). Шаблон `kit/settings.example.json` синхронизирован (+frontend-design +context7).
- Активация обоих — на reload desktop-сессии. Использование Context7: «use context7» в промпте при работе с pybit/pandas/FastAPI.

## OQ-3 [CLOSED] Нумерация спринтов «был 75»
Расследовано: `git tag` max = `v0.1.0-alpha.55`; `sprints/` max = 55; grep `sprint 7[0-9]` по 121MB транскрипта сессии и логам session-export — 0 совпадений. S56 (docs-спринт) не закрыт — корпус на ветке `chore/kit-integrate-headroom-ponytail`. Вывод: 75 не существовало; нумерация прогона S57+ корректна. Если помнишь контекст «75» — скажи, проверю точечно.
