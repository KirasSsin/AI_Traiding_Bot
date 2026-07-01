---
title: hooks-selfcheck — «сторожа сторожей» (единственный fail-CLOSED хук)
type: component
tags: [kit, hook, enforcement, fail-closed]
created: 2026-07-02
updated: 2026-07-02
sources: [kit/hooks/hooks-selfcheck.sh, kit/install.sh]
status: stable
---

# hooks-selfcheck — guard-the-guards

**TL;DR:** битый bash-хук в Claude Code падает fail-OPEN (молча снимает барьер). Этот хук ловит синтаксически битые хуки и не даёт запушить, пока оборона дырявая. S57, из [CLAUDE P1-BASHN] / KIT-007.

## Механика

| Событие | Поведение | Код выхода |
|---|---|---|
| SessionStart | `bash -n` по всем `~/.claude/hooks/*.sh`; битые → баннер в контекст сессии | 0 (не блокирует — сессия нужна для фикса) |
| PreToolUse Bash, команда содержит `git push` | те же проверки; битые → **блок пуша** | **2 (fail-CLOSED)** |
| PreToolUse Bash, прочие команды | не наше событие | 0 |

Диспетчер режимов: наличие `tool_input.command` в stdin-JSON = PreToolUse; пустой/без command = SessionStart.

## Политика

**Единственный fail-CLOSED хук кита** — осознанно: сломанный сторож хуже отсутствующего (все остальные хуки при инфра-ошибке fail-OPEN). `kit/install.sh` прогоняет тот же `bash -n` при установке и абортится на битых хуках.

## Проверка (red/green, S57)

- RED: подложен `zz-test-broken.sh` с ошибкой → SessionStart-баннер (exit 0); push-режим exit 2; non-push exit 0.
- GREEN: без битых — везде exit 0, тишина.
- Прогон: `/hook-test` скилл (env -i sandbox).

## Related

- [[adr-agent-sync-hook]] / [[sprint-state-freshness-hook]] / [[wiki-broken-link-hook]] — соседние push-гейты, которые этот хук защищает от молчаливой смерти (sprint-flow-check / phase-advance — см. [[../architecture/sprint-flow-ru]])
- [[../architecture/kit-overview-ru]] — AUTO-блок инвентаря (генерируется kit/kit-inventory.sh)
