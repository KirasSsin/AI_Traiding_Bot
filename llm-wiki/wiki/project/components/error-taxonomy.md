---
title: Error Taxonomy — token-waste ошибки прогона и превентивные паттерны (S65)
type: component
tags: [kit, errors, token-economy, anti-waste]
created: 2026-07-02
updated: 2026-07-02
sources: [CLAUDE.md, kit/hooks/, .claude/skills/]
status: stable
---

# Таксономия token-waste ошибок (S65)

Ошибки, повторявшиеся по ходу mega-run S57-S64 и жёгшие токены (failed tool-call → retry). Источник — прямой опыт прогона (ground truth) + grep логов. **Поправка S68 (log-validation по session-export):** первичный grep дал `151× Unexpected token`, но 149 из них = **region-block HTML-вместо-JSON** (сеть отдавала HTML на fetch → SyntaxError парсинга), а НЕ workflow parse-fail. Реальных workflow-парс-фейлов ~2. Класс 1 остаётся валидным паттерном (backtick/TS-аннотации рвут скрипт), но частота была завышена артефактом сети (→ класс 10 региональной блокировки, OQ-8).

| # | Класс | Сигнатура | Цена | Превентивный паттерн (место) |
|---|---|---|---|---|
| 1 | workflow TS-parse | `Invalid workflow script: Unexpected token` (реально ~2; 149 из grep'а = класс 10) | весь workflow-запуск | Named schema consts, plain JS, НЕ TS-аннотации (`: string[]`) / генерики / несовпадение скобок. **Под-случай (словлен live S65): вложенные backticks внутри template-строки `\`...\`` рвут литерал — строй многострочный текст через массив + `.join()`, а не template с backtick-инлайном.** → workflow-authoring гайд |
| 2 | Edit-до-Read | `File has not been read yet` | Edit fail + forced Read + retry (3×) | Read перед Edit ВСЕГДА, даже для «знакомого» файла. → CLAUDE.md anti-waste |
| 3 | File-modified-since-read | `has been modified since read` | re-Read + retry | После мутирующего tool (kit-inventory.sh AUTO-regen, ruff-format, hook) — re-Read перед Edit. → anti-waste |
| 4 | String-not-found | `String to replace not found` | несколько round-trips | Невидимые unicode (U+2028/NBSP) / whitespace mismatch. Regex/unicode строить через `python3` (chr/escape), НЕ Edit-paste. → anti-waste |
| 5 | hook false-fire | `phase-advance/review-gate FAILED` на безобидной команде | блок + разбор + workaround | op-detect substring матчит литерал `gh pr merge`/`git push` в тексте команды. → KIT-OD-1 (argv) + workaround «Edit, не Bash для текста с merge/push-литералом» |
| 6a | bash: python не найден | `command not found: python` | retry | ВСЕГДА `.venv/bin/python` (проект) или `python3` (stdlib). НЕ голый `python`. → anti-waste (уже есть, усилить) |
| 6b | zsh glob | `no matches found` | retry | Glob без совпадений в zsh = ошибка. Кавычки OR `2>/dev/null` OR `setopt`. → anti-waste |
| 6c | git checkout clobber | uncommitted затёрт | потеря работы + восстановление | НЕ `git checkout -- <file>` при незакоммиченных правках (затирает). Stash/commit сначала. → anti-waste |
| 7 | zsh bad-math | `bad math expression` | retry | `$N[:...` в zsh = array-math. Кавычки / `bash -c`. → anti-waste |
| 8 | control-chars | `command contains control characters` | reject + переделка | Zero-width в payload команды. Строить через `chr()`/файл, НЕ литералы. → anti-waste |
| 9 | agent-not-in-registry | `agent type 'X' not found` | workflow fail, 0 tokens | Свежесозданные агенты dispatchable ТОЛЬКО после reload реестра (session start). Frontmatter-validate + OQ. → workflow-authoring гайд |
| 10 | параллельный-батч 1-фейл (S68 log-val) | 1 failed tool-call в parallel-batch отменяет соседей (~92 события, из них git add ×39) | пере-выполнение отменённых соседей | **Мутирующие Bash-команды (git add/commit, mv, rm) — соло, НЕ в одном parallel-batch с рискующими вызовами.** Read/Grep/Glob — можно батчить. Region-block fetch (149 HTML) — сюда же (OQ-8 VPN + connectivity-check). → anti-waste + kit-conventions |
| 11 | read-back после своего Edit (S68 D5-05) | лишний Read файла, который сам только что записал | лишний Read (токены) | После собственного Write/Edit файл УЖЕ в контексте — НЕ Read его обратно «для проверки» (Edit/Write вернул бы ошибку при провале; harness трекает состояние). Re-Read только после ЧУЖОЙ мутации (скрипт/hook/ruff). → anti-waste |

## Философия
Механизировать нельзя всё (tool-call пре-валидацию контролирует harness). Но дисциплина + гайды в самых читаемых местах (CLAUDE.md anti-waste, workflow-гайд) снижают частоту. Цель — минимум токенов на прогон.

## Related
[[../plans/2026-07-02-sprint-65-error-harvest]] · [[kit-op-detect-hardening-backlog]] (KIT-OD-1 op-detect) · [[manifest-telemetry]]
