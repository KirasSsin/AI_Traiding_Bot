---
title: "Review — Sprint 69 (Гейты по-настоящему)"
type: review
sprint: 69
created: 2026-07-03
updated: 2026-07-03
status: approved
---

# Review S69 — Гейты по-настоящему

**Blockers: 0** (все найденные закрыты в ходе Фазы 6)

Reviewers: **security-auditor** (opus, gate-bypass-hunt, 2 прохода) · **python-reviewer** (sonnet, новые lib). Домен: kit/hooks (money-path enforcement логика гейтов); src/ денежного ядра НЕ тронут (заморожен).

## security-auditor — money-path gate-bypass-hunt (CRITICAL)

Задача: доказать, что правки НЕ ослабляют money-path enforcement (review-gate KIT-003 + phase-advance Phase-5). Итог: enforcement **same-or-stronger**. Найдено и ЗАКРЫТО 2 BLOCKER (оба — регресс относительно старого substring-floor):

1. **[BLOCKER — закрыт]** shlex-argv separator-bypass: `echo hi;git merge <branch>` (разделитель, приклеенный к слову) → op_detect=`allow` → оба гейта exit 0. Доказано end-to-end (scratch repo, Phase6 pending, `src/execution/oco.py` в диффе): `git merge` rc=2 vs `echo hi;git merge` rc=0. **Фикс:** полный редизайн op_detect на quote-strip skeleton (765ebc8) — устойчив ко ВСЕМУ классу разделителей.
2. **[BLOCKER — закрыт]** combined short-flag sh -c: `bash -lc "git merge X"` (также `-ec/-xc/-ic`) → raw re-scan не срабатывал → `allow`. **Фикс:** `-c\b` → `-[A-Za-z]*c\b` (fba270c), auditor-verified.

**Verified GATE (аргумент устойчивости):** сепараторы `; && | () newline { } backtick`; standard `eval`/`sh -c`; program-prefix `sudo/xargs/nice/time//usr/bin/git`; `git -c … merge`, env-prefix; `gh -R pr merge`; `gh api …/pulls/N/merge`. **False-fire wins HELD (allow):** `git commit -m "…git merge…"`, `grep -rn "git merge"`. **git-common-dir canon (T7):** не создаёт worktree/cwd-обхода, строго лучше pre-S69.

**Follow-ups (НЕ регресс S69 — старый floor тоже промахивался, backstop = diff-детект):** adjacent-quote concat (`g"i"t merge`), `git pull . <ref>`, inline-alias, `$CMD` var-expansion.

## python-reviewer — новые lib (op_detect.py, emit_context.py)

- **[BLOCKER — закрыт]** `gh -R/--repo pr merge` не ловился (глобалки gh не срезались) → редизайн срезает gh-глобалки в `_normalize`.
- **[BLOCKER — закрыт]** `/merge` substring ловил `/merges` (false-positive) → якорь `pulls/[^/\s]+/merge\b` (endswith).
- **Verified:** shlex ValueError-обработка (в редизайне — total regex, PARSE_ERROR не нужен); emit_context JSON-escaping + 10000-truncation + empty-guard; system-python3 совместимость.
- Type hints добавлены (H1/H2).

## Verify (Фаза 5, повторно после фикса)

- `test_phase_gate_canon.sh` — 70 кейсов GREEN (включая separator/eval/sh-c-combined/gh-flag/`/merges`).
- `test_state_integrity_security.py` — 32/32 PASS. 17/17 хуков `bash -n`. libs ruff+compile.

## Вердикт

**APPROVE.** Money-path enforcement усилен (закрыт separator + sh-c bypass-класс, `git -c`/gh-globals, self-skip forgery). Оба BLOCKER-прохода закрыты + доказаны харнессом. Готово к ship (alpha.69).
