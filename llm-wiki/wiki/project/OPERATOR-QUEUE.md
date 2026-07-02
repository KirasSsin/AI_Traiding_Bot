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

## OQ-2 [OPEN] Решение по S63-плагинам после прогона
По твоему ответу: «фиксируем варианты, в конце посмотрим». Отчёт будет в `llm-wiki/wiki/project/plugins-research-s63.md`. После прочтения выбери ≤2 кандидата — интеграция отдельным спринтом.

## OQ-4 [OPEN] Логин CLI в подписку — БЕЗ этого Auto-Resume (S58) не боеспособен

Headless-вызов `claude -p` (ядро авто-резюма) отвечает «Credit balance is too low» даже в чистом окружении: логин CLI указывает на Console-аккаунт без API-кредитов, а не на твою Max-подписку (десктоп-приложение логинится отдельно).

Шаги (~2 минуты):
1. Открой Terminal → `claude` (интерактивно) → команда `/login` → выбери вход по подписке (Claude account с Max), НЕ Console/API-key.
2. Проверка одной командой:
   `cd /tmp && claude -p "Say OK" --output-format json --model haiku | grep -o '"is_error":[a-z]*'`
   Ожидание: `"is_error":false`.
3. Пост-проверка прав (Ship-гейт C-2 из PRE-PLAN ревью S58) —两 команды:
   `cd /tmp/perm-probe && claude -p "Create probe1.txt with word OK using Write tool" --output-format json --model haiku; ls probe1.txt` → файла быть НЕ должно;
   `claude -p "Create probe2.txt with word OK using Write tool" --output-format json --model haiku --allowedTools Write; ls probe2.txt` → файл должен появиться.
   Оба результата скинь мне (или просто напиши «OQ-4 done, A=no file, B=file») — я закрою гейт в спринт-странице.

До OQ-4 механизм S58 установлен и протестирован на моках; боевой E2E ждёт логина. Безопасная деградация: при нерабочем биллинге поллер логирует STILL_LIMITED/NO_PROGRESS и эскалирует, ничего не ломая.

## OQ-5 [OPEN] Перезапуск сессии для 3 новых агентов (S63)

kit-auditor / merge-analyst / release-manager созданы в `~/.claude/agents/` (frontmatter валиден, model=fable-5). Реестр агентов грузится на старте сессии — **свежесозданные не dispatchable в текущей сессии**. После любого перезапуска CLI они станут доступны как subagent_type. Проверка: `claude` → спроси «list available agents» ИЛИ dispatch «kit-auditor: прогони аудит кита». Смоук в S63 сделан по логике вручную (нашёл 3 реальных pre-ship issue).

## OQ-6 [OPEN] doc-writer на sonnet-5 — намеренно?

ADR 0075 pin-policy: 5 из 6 fable-5-пинов judgment-heavy (обосновано). `doc-writer=claude-sonnet-5` — дешёвый тир для draft-генерации доков. Подтверди: намеренный тир ИЛИ gap миграции fable-5? Если намеренно — оставляю; иначе подниму до fable-5 в след. kit-спринте. (Записано в `kit/PINNED_VERSIONS.md`.)

## OQ-3 [CLOSED] Нумерация спринтов «был 75»
Расследовано: `git tag` max = `v0.1.0-alpha.55`; `sprints/` max = 55; grep `sprint 7[0-9]` по 121MB транскрипта сессии и логам session-export — 0 совпадений. S56 (docs-спринт) не закрыт — корпус на ветке `chore/kit-integrate-headroom-ponytail`. Вывод: 75 не существовало; нумерация прогона S57+ корректна. Если помнишь контекст «75» — скажи, проверю точечно.
