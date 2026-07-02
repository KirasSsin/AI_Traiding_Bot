---
title: Review S63 — Fable-5 Team (Phase 6 artifact)
sprint: 63
updated: 2026-07-02
---
# Review S63 — 3 новых kit-агента + pin-policy

Reviewers (parallel, async, оба fable-5):

- **architecture-reviewer: APPROVE_WITH_CONDITIONS** — 2 HIGH + MEDIUM закрыты:
  - HIGH #1: kit-auditor не имел pin-audit измерения, хотя ADR 0075 BINDING назначает его именно kit-auditor → добавлено **измерение 8** (grep `^model:` пинов → diff против `kit/PINNED_VERSIONS.md`; UNREGISTERED → finding).
  - HIGH #2: `kit/PINNED_VERSIONS.md` мисклассифицировал 6 явных `claude-sonnet-5` пинов как «алиасы» → перенесены в таблицу пинов с причиной+датой (явный пин ≠ алиас).
  - MEDIUM #3: merge-analyst без dispatch-триггера → добавлен «Use proactively BEFORE PR-merge/branch-merge». MEDIUM #6: ownership-граница secret-scan (kit-auditor tripwire → эскалирует security-auditor). LOW #8: «хук главнее отчёта» → discipline-блок.
  - Verified clean: пины Matrix §4.1 применены+синхронизированы (18 агентов оба дерева); роли 3 агентов не пересекаются; advisory-граница заявлена; tool sets минимальны.
  - Follow-up (LOW/cosmetic): MEDIUM #5 kit-auditor description bloat (сжать ≤1200б) — принято на будущее.

- **security-auditor: APPROVE_WITH_CONDITIONS** — 1 HIGH + MEDIUM закрыты:
  - **HIGH #1 (закрыт):** secret-echo в транскрипт — kit-auditor `grep -nE`/plain `diff` над живым settings.json печатали ПОЛНЫЙ секрет в stdout (транскрипт+claude-mem). → `jq keys` структурно + presence `grep -cE` + evidence ТОЛЬКО префикс; binding «ни одна Bash-команда не печатает полный секрет».
  - MEDIUM #2: sibling-файлы (settings.bak/.local — S57-урок) → свип `settings*` + `.bak`/`~`. MEDIUM #4: `xargs -I{} sh -c` filename-инъекция → for-цикл с `"$f"`. MEDIUM #3: read-only-by-tools противоречие (harness инжектит Write) → discipline-блок «Write ТОЛЬКО под agent-memory/». LOW #6: pattern-drift `sk-` → анкерный паттерн (FP `sk-stat` из пути закрыт).
  - Verified clean: merge-analyst/release-manager execute-paths (propose-not-execute); PINNED_VERSIONS/ADR 0075 secret-free; skill-manifest write-free; mirror parity byte-identical.
  - Follow-up (LOW): release-manager pytest дертит tracked `data/cross_trial_sharpes.json` (известный S-carry) — принято.

## Доказательства
- frontmatter 3/3 OK после фиксов; kit-drift clean (18 агентов оба дерева); kit-auditor audit-блок bash -n OK.
- Smoke: kit-auditor логика прогнана вручную (live-dispatch теперь доступен — агенты в реестре) → нашла 3 реальных pre-ship issue (broken-link + ADR-orphan + FP sk-в-пути), все исправлены.

## Границы
- «Read-only» 3 агентов = дисциплина промпта, не sandbox (Bash может мутировать; harness инжектит Write) — задокументировано discipline-блоком + вынесено в wiki. Hard-fix (op-detect argv, per-agent enforcement) = KIT-OD-1 backlog.
- op-detect FP: benign-команда с литералом `gh pr merge` в тексте ложно триггерит phase-advance (наблюдалось при этом ревью) → усиливает [[../kit-op-detect-hardening-backlog]].

Blockers: 0
