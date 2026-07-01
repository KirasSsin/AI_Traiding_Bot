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

## OQ-3 [CLOSED] Нумерация спринтов «был 75»
Расследовано: `git tag` max = `v0.1.0-alpha.55`; `sprints/` max = 55; grep `sprint 7[0-9]` по 121MB транскрипта сессии и логам session-export — 0 совпадений. S56 (docs-спринт) не закрыт — корпус на ветке `chore/kit-integrate-headroom-ponytail`. Вывод: 75 не существовало; нумерация прогона S57+ корректна. Если помнишь контекст «75» — скажи, проверю точечно.
