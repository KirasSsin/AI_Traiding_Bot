---
name: hook-test
description: Test PreToolUse hook scripts (gate + WARN hooks) для AI Trading Bot v0.1 без false-positive triggering. Use ONLY when explicitly invoked via /hook-test (disable-model-invocation=true). Primary = S61 regression harness; manual payloads через env -i + python3-конкатенацию.
disable-model-invocation: true
---

# Hook Test — sandboxed PreToolUse hook invocation

## When to use

**Explicit invocation only** (disable-model-invocation: true — model не auto-trigger). User invokes via `/hook-test` ИЛИ "test the hook script".

Triggers:
- After editing `kit/hooks/<hook>.sh` (source) OR `~/.claude/hooks/<hook>.sh` (live) — verify changes.
- After adding a new PreToolUse hook.
- Debugging a hook false-positive OR false-negative.

## Тестовая пирамида (S69 SKW-04 — PRIMARY = харнесс)

1. **PRIMARY — регресс-харнесс (ВСЕГДА первым, покрывает 40+ кейсов):**
   ```bash
   bash kit/hooks/tests/test_phase_gate_canon.sh                    # canonical phase + op-detect argv + false-fire
   .venv/bin/python kit/hooks/tests/test_state_integrity_security.py  # STANDALONE скрипт (не pytest); 32/32 PASS = exit 0
   ```
   Харнесс реплицирует parse+detect хуков и покрывает: canonical phase (zero-width/мусор → BLOCK), op-detect argv (merge/push/commit), false-fire на литералах в кавычках, `git -c x=y` bypass, plumbing exclusion (`git merge-base`). **Все PASS — до любого manual-теста.**

2. **MANUAL — единичный сценарий** (когда харнесс не покрывает): env -i изоляция + payload через stdin (ниже).

## Почему self-skip больше нет (S69 T8)

Старые хуки имели self-skip (`*<hook-name>*) exit 0`), чтобы test-инвокация не ложно триггерила соседние хуки. **T8 его удалил** (zero-forgery: `git push … # <hook>.sh` разоружал гейт нулевой подделкой). Теперь детект операции — по РЕЗОЛВНУТОМУ argv (`lib/op_detect.py`, shlex): литерал `git push`/`git merge`/`git commit` внутри кавычек/echo/аргумента **инертен**, а голый `bash <hook>.sh` не классифицируется как операция. Значит test-инвокация проходит корректно БЕЗ self-skip.

## Manual invocation (env -i isolation + python3-конкатенация)

**Строй команду с op-литералом через python3-конкатенацию**, чтобы твоя ВНЕШНЯЯ Bash-команда не содержала `git push`/`git merge` как текст (иначе ЖИВОЙ хук сработает на ТВОЙ tool-call — op_detect его пропустит, но конкатенация надёжнее и не зависит от порядка синка):

```bash
env -i HOME="$HOME" PATH="/usr/bin:/bin:/usr/sbin:/sbin" bash -c '
  cd /Users/Apple/Desktop/Vibe_Code/Bot/AI_Traiding_Bot
  # "git push" собирается в python, не в тексте Bash-команды:
  payload="$(python3 -c '"'"'import json;print(json.dumps({"tool_input":{"command":"git "+"push origin main"}}))'"'"')"
  printf "%s" "$payload" | bash kit/hooks/<hook>.sh
  echo "EXIT: $?"
'
```

`env -i` срезает окружение → цепочка PreToolUse-хуков не re-триггерит на вложенном `bash`.

## Exit-code table по классам хуков

| Класс | Хуки | Block (exit 2) | Allow (exit 0) | Канал WARN |
|---|---|---|---|---|
| **Money/phase gate** | review-gate, phase-advance | Phase 5/6 != done ИЛИ money-diff без артефактов Фазы 6 | не merge / не активная фаза / артефакты на месте | stderr при блоке |
| **Push gate** | sprint-flow-check, adr-agent-sync, adr-index-sync, wiki-broken-link, docs-broken-link, sprint-state-freshness | нет plan / ADR не в index / битая ссылка / stale state | не push / нет нарушения | stderr при блоке |
| **WARN (advisory)** | docs-staleness, pertask-state-warn, cascade-read, context-budget | НИКОГДА (всегда exit 0) | всегда | stderr + `additionalContext` (S69 T2 — модель слышит) |
| **State/backup** | state-backup, state-integrity | integrity: exit 2 при доказанном повреждении | не commit / целостно | — |

Другой ненулевой код → fail-OPEN (Claude Code продолжает). Политика: fail-OPEN на инфра, fail-CLOSED только при доказанном нарушении.

## Verify

Positive (block) / negative (allow) / edge — сверь exit-код + stderr против таблицы. Отклонение → баг хука, investigate (не «подправь тест под результат»).

## Anti-patterns (НЕ делать)

- ❌ Тестировать хук через реальный `git push`/`git merge` (remote side-effects + триггерит соседей).
- ❌ Пропустить PRIMARY-харнесс, сразу manual (харнесс = регресс-сеть 40+ кейсов).
- ❌ Manual-payload с ЛИТЕРАЛОМ `git push`/`git merge` в тексте Bash-команды (строй через python3-конкатенацию).
- ❌ Полагаться на self-skip (удалён в T8 — его больше нет; детект по argv).
- ❌ Менять хук без прогона харнесса (silent regression risk).
- ❌ Auto-invoke (disable-model-invocation: true — только явно).

## Related kit references

- Регресс-харнесс: `kit/hooks/tests/test_phase_gate_canon.sh` (S61, расширен S69 op_detect) + `test_state_integrity_security.py`
- op-detect: `kit/hooks/lib/op_detect.py` (argv-классификация merge/push/commit; shlex + shell-operator split)
- WARN→additionalContext: `kit/hooks/lib/emit_context.py` (S69 T2 — немой WARN → слышимый модели)
- Hook scripts: `kit/hooks/*.sh` (source) → `~/.claude/hooks/*.sh` (live mirror via `kit/install.sh`)
- Claude Code hook protocol: stdin=JSON, exit 2=block, other non-zero=fail-open, `hookSpecificOutput.additionalContext`=model-visible (exit 0)
