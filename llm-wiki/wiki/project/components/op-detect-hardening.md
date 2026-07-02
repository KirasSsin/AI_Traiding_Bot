---
title: Op-detect hardening — argv-классификация операций в гейтах
type: component
tags: [kit, hooks, security, gates, op-detect]
created: 2026-07-03
updated: 2026-07-03
sources: [kit/hooks/lib/op_detect.py, kit/hooks/lib/emit_context.py, kit/hooks/phase-advance.sh, kit/hooks/review-gate.sh]
status: stable
---

# Op-detect hardening — argv-классификация операций в гейтах

**TL;DR:** Хуки-гейты определяют операцию (`git merge` / `gh pr merge` / `git push` / `git commit`) по **неквотированному скелету команды** (`lib/op_detect.py`: вырезать содержимое кавычек → применить substring-floor к остатку), а не по подстроке всей команды. Убирает false-fire на литерале в кавычках, закрывает `git -c x=y <op>` bypass И устойчиво ко всему классу разделителей (`;` `&&` `|` перевод строки `{ }` подоболочка бэктик). Немые WARN-хуки доходят до модели через `lib/emit_context.py` (additionalContext). Введено в S69 «Гейты по-настоящему».

## Проблема (до S69)

Гейты детектили операцию подстрокой: `case "$cmd" in *"git merge"*) ...`. Три класса дефектов:

1. **False-fire на литерале.** Любая команда, ТЕКСТ которой содержал `git merge` / `git push` / `gh pr merge` (сообщение коммита, grep-паттерн, `echo`, `python -c`), ложно классифицировалась как операция и блокировала/варнила. Доказано live в S69: `grep -rn "git push"` был заблокирован `adr-agent-sync-check`.
2. **`git -c` bypass.** `git -c http.version=2 merge feature/x` не содержит подстроки `git merge` (между `git` и `merge` вклинилась глобалка) → детект промахивался → гейт молча пропускал. Money-path дыра.
3. **Self-skip forgery.** Каждый гейт имел `*"<hook-name>"*) exit 0` (чтобы hook-test не триггерил соседей). Побочно: `git push … # <hook>.sh` разоружал гейт нулевой подделкой — достаточно упомянуть имя хука в команде.

## Решение

### `lib/op_detect.py` — классификатор по unquoted-скелету

Читает команду со stdin, печатает РОВНО одно слово: `GATE` / `skip` / `allow`. Алгоритм (S69 Phase-6 security-редизайн — quote-strip вместо shlex-argv):

1. `_strip_quoted` — вырезает СОДЕРЖИМОЕ кавычек (`'…'` / `"…"`), оставляя неквотированный текст. Литерал в кавычках (сообщение коммита, grep-паттерн) исчезает. Несбалансированная кавычка → возвращаем исходную команду (консервативно — не прячем возможную операцию за случайной кавычкой).
2. `_normalize` — свёртка пробелов (включая ПЕРЕВОДЫ СТРОК и табы) в один пробел + срез git-глобалок (`-c/-C/--git-dir/…`) и gh-глобалок (`-R/--repo`).
3. Regex по скелету: `\bgit merge\b(?!-)` | `\bgh pr merge\b` | `pulls/[^/\s]+/merge\b` → GATE; `git merge-(base|tree|file)` → skip (plumbing). Для push — `\bgit push\b`; commit — `\bgit commit\b(?!-)` (commit-tree исключён).
4. `eval "<op>"` / `sh -c "<op>"` исполняют КВОТИРОВАННЫЙ аргумент → если в скелете остались `eval`/`… -c`, повторный матч по СЫРОЙ команде.

**Почему не shlex-argv (S69 Phase-6 BLOCKER):** первая версия токенизировала через shlex, но `shlex.split` не режет `; & | ( )`, приклеенные к слову — `echo hi;git merge X` классифицировался `allow`, минуя ОБА денежных гейта (доказано security-ревьюером end-to-end). Прескрипция `punctuation_chars`-лексера всё равно промахивалась на переводе строки / `{ }` / бэктике (self-verify). Quote-strip + floor устойчив ко ВСЕМУ классу разделителей сразу — они не кавычки, значит операция после них остаётся в скелете и гейтится.

**Floor money-path:** дизайн ошибается В СТОРОНУ GATE (over-gate безопасен; under-gate = дыра). Скелет = видимый неквотированный текст команды — не слабее старого substring-floor, минус квотированные спаны (там только данные, не команды; кроме eval/sh -c — обработаны отдельно). python3 отсутствует → хук откатывается на substring-`case`.

**Остаток (документирован, старый substring-floor тоже промахивался — НЕ регресс S69):** переменная-развёртка (`$CMD`), динамическая подстановка (`$(cat …)`), inline-alias git config → консервативно; денежный контур защищён diff-детектом review-gate.

### `lib/emit_context.py` — немой WARN → слышимый модели

Exit-0 хук, пишущий только в stderr, виден ОПЕРАТОРУ, но не МОДЕЛИ. `emit_context.py` оборачивает текст в `{"hookSpecificOutput":{"hookEventName":"<Event>","additionalContext":"…"}}` на stdout — Claude Code инжектит это в контекст модели (подтверждено probe: работает на exit-0 для UserPromptSubmit / PreToolUse / PostToolUse). Двухканальность: хук СОХРАНЯЕТ stderr (оператор) И добавляет additionalContext (модель). Без `permissionDecision` (остаётся advisory).

### git-common-dir split-brain защита

`phase-advance.sh` + `review-gate.sh` резолвят SPRINT_STATE из КАНОНИЧНОГО checkout (main worktree через `git rev-parse --git-common-dir` → родитель) — не из локального worktree-чекаута. Несколько checkout (worktrees + 2-й клон) = параллельные SPRINT_STATE; гейт обязан сверять фазу с каноничным. В обычном single-checkout `common-dir=.git` → `canon_root==repo_root` (0 изменений поведения). git diff/branch остаются на repo_root.

## Ключевые свойства

- **Потребители op_detect:** `phase-advance` (merge), `review-gate` (merge), `state-backup` (commit), `pertask-state-warn` (commit), `sprint-flow-check` / `adr-agent-sync-check` / `adr-index-sync-check` / `wiki-broken-link-check` / `docs-broken-link-check` / `sprint-state-freshness-check` (push).
- **Потребители emit_context:** `docs-staleness-check`, `pertask-state-warn`, `context-budget-warn`, `cascade-read-check` (через `cascade_check.py`).
- **Резолв пути lib:** `$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/…` — работает из `kit/hooks/` (source) и `~/.claude/hooks/` (live, зеркалится `install.sh`).
- **Регресс-сеть:** `kit/hooks/tests/test_phase_gate_canon.sh` (40+ кейсов: canonical phase + op-detect merge/push/commit + false-fire + `git -c` bypass + plumbing exclusion).

## Связано

- [[error-taxonomy]] — класс op-detect false-fire (S65)
- [[adr-agent-sync-hook]] · [[sprint-state-freshness-hook]] — потребители push-детекта
- [[auto-resume]] — контур непрерывности (limit-marker → gate)
- [[../architecture/sprint-flow-ru]] — Фаза 6 контракт review-sNN.md (механические потребители)

## Открытые вопросы

- Автоматическая WARN-сверка зеркало↔живая Scheduled Task в hooks-selfcheck (D3-04, deferred LOW).
- inline-alias резолв (KIT-OD-2, backlog) — требует чтения git config.

## Источники

- `kit/hooks/lib/op_detect.py`, `kit/hooks/lib/emit_context.py`
- `kit/hooks/phase-advance.sh`, `kit/hooks/review-gate.sh`
- `llm-wiki/wiki/project/kit-deep-research-2026-07-02.md` (находки D1-01/D7-01/LOG9-02/KIT-OD-1)
