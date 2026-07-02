---
title: Sprint 59 — Gates: принуждение вместо дисциплины
type: summary
sprint: 59
created: 2026-07-02
updated: 2026-07-02
tag: v0.1.0-alpha.59
status: stable
---

# S59 — Gates (mega-run 3/8)

**TL;DR:** четыре механических барьера вместо дисциплины: гейты привязаны к SPRINT_STATE.phase (не к имени ветки), денежное ядро не мержится без артефактов Фазы 6, ADR-sync требует содержательного упоминания (touch мёртв), per-task протокол напоминает о себе WARN'ом. src/ не тронут.

## Сделано

| T | KIT | Что | Proof |
|---|---|---|---|
| T1 | KIT-002 | branch-bypass guard в sprint-flow-check + phase-advance: не-sprint ветка + phase∈{2..8} → блок (закрыт прецедент S56 на chore/*). Фазы 1/9 вне гейта — осознанно (docs-only действия; Close-пуш финала прогона идёт при between-sprints) | red exit=2 оба; green: between-sprints/sprint-ветка |
| T2 | KIT-003 | review-gate.sh: money-diff (signalgen/execution/risk/backtest/override) требует `\| 6 Review \| done \|` (sprint-scoped) + `reviews/review-sNN.md` (Blockers: 0). Ref-резолв: sprint-ветка → любой git-ref (sha/rename) → текущая; не определили → громкий WARN; merge с main при активной фазе → блок | red: sha/rename/comment-dodge/stale-sprint-row все exit=2; green + docs-only exit=0 |
| T3 | KIT-009 | adr-agent-sync: содержательная проверка `ADR NNNN`-анкера в теле агента (голое число не катит — 108 случайных 4-цифр в агентах); deleted-ADR skip; touch-обход мёртв (A2: 58/75 блоков были touch-шумом) | red: bare-число/touch exit=2; green: «ADR 9999: ack» exit=0; deleted-ADR skip verified |
| T4 | KIT-013 | pertask-state-warn.sh: WARN (exit 0) при коммите src/ без SPRINT_STATE в staged. Эскалация до блока — по телеметрии S62 | WARN печатается/тишина корректно |
| T5 | — | Подключение (9 PreToolUse), kit-зеркало, 2 component-страницы + adr-sync-страница обновлена, index, AUTO-блоки | selfcheck OK; kit-drift clean |

## Ревью (Phase 6) — артефакт [[../reviews/review-s59]]

- **architecture-reviewer: APPROVE_WITH_CONDITIONS** — HIGH-1 (тихий обход `git merge <sha>`/rename) + M2..M5; ВСЕ закрыты в спринте, re-verified red/green.
- **security-auditor: APPROVE with Concerns** — M-1..M-4 (sha-ref, main-merge, self-skip подстрока, non-sprint-scoped row); ВСЕ закрыты в спринте. Инъекции в T1 verified safe; T4 verified no-block/no-leak.

## Принятые границы (документировано)

- **Same-session forgery** — сессия, пишущая review-sNN.md без запуска ревьюеров, обманет гейт по построению (хук в том же trust-домене). Tamper-evidence (файл commit-in-range + schema-check вердиктов) → S62 manifest.
- Self-skip narrowing применён к review-gate; kit-wide унификация остальных 8 хуков → S62.
- `main` как diff-база захардкожена (этот репозиторий).

## Механических гейтов теперь

Было (до прогона): 2 (и оба обходились именем ветки). Стало: **6 блокирующих** (sprint-flow×2 условия, phase-advance×2, review-gate, adr-sync-content, wiki-links, adr-index, freshness, selfcheck-fail-closed) + 2 WARN (budget, pertask) + auto-resume контур.

## Related
[[../plans/2026-07-02-sprint-59-kit-gates]] · [[../components/review-gate-hook]] · [[../components/pertask-state-warn-hook]] · [[../components/adr-agent-sync-hook]] · [[../KIT-MASTER-PLAN]]
