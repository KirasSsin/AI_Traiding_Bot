---
title: "Sprint 69 — Гейты по-настоящему (план)"
type: plan
sprint: 69
created: 2026-07-03
updated: 2026-07-03
status: active
sources: [~/.claude/hooks/phase-advance.sh, ~/.claude/hooks/review-gate.sh, ~/.claude/hooks/state-backup.sh, llm-wiki/wiki/project/kit-deep-research-2026-07-02.md]
---

# S69 — Гейты по-настоящему

## Цель
Принуждение гейтов на РЕАЛЬНОМ ship-пути (локальный `git merge --squash`, не только `gh pr merge`), слышимый WARN-канал, split-brain защита, permission-hardening. Security-критично (money-path enforcement) → каждая правка тестируется + security-auditor review.

## Фаза 2 (Brainstorm) — артефакт + grounding
PHASE 2 = 47 панельных вердиктов на диске + **обязательный per-hook grounding** (merge-analyst урок: перечитать хук, не доверять версии находки — хуки закалялись S59-S62 ПОСЛЕ снятия логов ресёрча). Проверено на живом коде:

| Находка | Grounding-вердикт |
|---|---|
| D1-01 review-gate git merge | **УЖЕ СДЕЛАНО** (S59-62): review-gate строки 48-58 ловит `git merge`/sha/renamed/gh api REST + M-4 sprint-binding + tamper. НЕ трогаем. |
| D1-01 phase-advance git merge | **РЕАЛЬНЫЙ GAP** (подтверждён): phase-advance:48-52 ловит ТОЛЬКО `gh pr merge` → локальный `git merge --squash` Phase-5-verify минует. **FIX.** |
| остальные (D7-01/D3-01/MEM-03/D2-03/D5-02/D1-03/SKW-04/D2-07/LOG9-02/KIT-OD-1) | требуют per-hook grounding перед fix (см. задачи) |

## Задачи (verified scope)

| # | Задача | Находки | Файлы | Делегат |
|---|---|---|---|---|
| T1 | **phase-advance git-merge детект** — портировать из review-gate (normalize + strip `-c/-C` + `git merge `/merge-base-exclude + gh api REST) + sprint-binding M-4 (Phase-5-строка от ЭТОГО спринта: merge-ref sprint vs state sprint) + markdown-tolerance статус-ячейки (`**done**`) | D1-01/D1-04 + design-hole | phase-advance.sh | controller + S61 harness test |
| T2 | **4 немых WARN-хука → additionalContext** — capability-probe; cascade-read/context-budget/docs-staleness/pertask-state stderr→`hookSpecificOutput.additionalContext` (БЕЗ permissionDecision авто-аппрув). Fallback PostToolUse. | D7-01 | 4 хука | controller (probe first) |
| T3 | **state-backup git-нормализация** — grounding + `commit -a/-am`/`git -c … commit` покрытие (tr+sed образец review-gate) | D3-01 | state-backup.sh | controller |
| T4 | **consolidate-memory в sprint-finish** N%5==0 ДО skill-manifest + log; НЕ жёсткая manifest-строка | MEM-03 | sprint-finish SKILL | controller |
| T5 | **release-manager+merge-analyst вшить** в sprint-finish Step 6d + точки диспатча | D2-03 | sprint-finish, sprint-flow-ru | controller |
| T6 | **skill-manifest апгрейд** — advisory Skill-fires; Phase-2 строка; Phase-7 анкер; 3b `^(src|kit)/`; wiki-update триггер += kit/**/.claude/skills/**; два режима в CLAUDE.md | D5-02/D1-05/D1-06/SKW-05 | skill-manifest.sh, wiki-update, CLAUDE.md | controller |
| T7 | **LOG9-02 split-brain** — git-common-dir check в гейтах (worktree/2-й клон → чужой SPRINT_STATE) | LOG9-02 | phase-advance/review-gate | controller |
| T8 | **self-skip свип 9 хуков** — zero-forgery bypass (grounding: review-gate/phase-advance уже без self-skip round-5; проверить остальные 7) | D1-03 | 9 хуков | controller |
| T9 | **KIT-OD-1 argv op-detect** — резолв argv вместо substring (словил false-fire на моём grep этой сессии) | KIT-OD-1 | op-detect хуки | controller |
| T10 | **permission-hardening** — standing `alwaysAllowedReasons` Write-allow для typo-пути AI_Traiding_Tool (carry S68 security-auditor) | LOG9-04-смежно | desktop config | controller + security-auditor |
| T11 | hook-test переписать (S61-харнесс primary) + Phase 6 review-s{NN} контракт + SYNC-BLOCK desktop-prompt | SKW-04/D2-07/D3-04 | hook-test, sprint-flow-ru | controller |

## Acceptance
- phase-advance блокирует `git merge --squash feature/sprint-N` при Phase 5 != done (S61 harness test_phase_gate_canon.sh + новые кейсы GREEN); false-fire на литерале в тексте — не блок.
- 4 WARN-хука: probe подтверждает additionalContext доходит до модели ИЛИ fallback.
- Все тронутые хуки `bash -n` OK; S61 харнесс 38+ кейсов GREEN.
- security-auditor gate-bypass-hunt APPROVE (money-path enforcement не ослаблен, только усилен).

## Риски / guards
- **Money-path enforcement — не ослабить.** Любая правка review-gate/phase-advance → S61 harness + security-auditor обязательны (S55: 2 BLOCKER прошли ручное ревью).
- **fail-OPEN на инфра / fail-CLOSED только при доказанном пропуске** — сохранить политику.
- **markdown-tolerance:** статус-ячейка `**done**` (bold) должна засчитываться (design-hole панелей).

## Фазы
Plan(3) → Execute(4, per-task + S61 harness TDD) → Verify(5, harness + bash -n) → Review(6, security-auditor gate-bypass-hunt — CRITICAL) → Sync(7) → Ship(8 tag alpha.69) → Close(9 → S70).

## Related
[[../kit-deep-research-2026-07-02]] · [[../architecture/phase-dispatch-ru]] · [[../sprints/sprint-68-boot-layer]]
