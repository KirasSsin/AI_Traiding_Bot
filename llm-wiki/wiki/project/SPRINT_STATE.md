---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-07-02  # S67 SHIPPED (alpha.67) — Desktop Auto-Resume; push отложен (оператор)
sprint: 67
phase: between-sprints
branch: main
tag: v0.1.0-alpha.67  # последний shipped (S67)
last_task_sha: c1d2232  # squash S67 на main — точка восстановления auto-resume
---

## Текущий статус

**Mega-run v2 (S57–S66) ЗАВЕРШЁН** + пост-прогон **S67**. Все отгружены локально (теги alpha.57…alpha.67). **Push отложен** (оператор — накопить, один push позже; `unset GITHUB_TOKEN GH_TOKEN`).

**S67 SHIPPED** (main `c1d2232`, tag alpha.67): Desktop Auto-Resume — gate-only `auto_resume_gate.py` (GO/WAIT/NONE/STALE/FOREIGN, C2-guardы + first_ts ceiling) + Desktop Scheduled Task `kit-desktop-auto-resume` (cron `*/30` MSK). Закрыл пересмотренный OQ-4 (desktop, не CLI). security-auditor APPROVE 0 blockers, 20/20 tests. Детали → [[sprints/sprint-67-desktop-auto-resume]].

**Uniform fable-5** (ADR 0076, `857c6a3` на main): 18 агентов = claude-fable-5; frontend-design + Context7 активированы. OPERATOR-QUEUE: OQ-2/5/6/7 закрыты, OQ-1 отложен.

**Carry (после прогона / оператору):** KIT-OD-1 (op-detect argv-классификация, выделенный security-спринт), KIT-OD-2 (tamper review↔diff), current-state→AUTO-блок kit-inventory, docs/ бэкфилл S57-63 + repoint source_files→kit/, tuning A/B (ADR 0074). OQ: 1 (токен), 4 (CLI /login), 5 (reload агентов), 6 (doc-writer тир), 7 (Frontend Design).

**Важно при обрыве:** Auth `unset GITHUB_TOKEN GH_TOKEN` (Keychain gho_). Push origin — один, в конце прогона. src/ заморожен (kit-maintenance). SPRINT_STATE стейджить ОТДЕЛЬНО от commit (иначе state-backup не увидит staged).

## Carry (не трогаем в mega-run: src/ денежного ядра заморожен)

- **BYBIT-08** (MEDIUM) — adapter-level typed `AmbiguousOrderOutcome`, свой ADR/спринт.
- atr_breakout ATR-index offset (ADR 0064) — own ADR+WFA до live.
- D5 forfeit-N policy; Track B Kronos enrichment — DEFER; forward paper-trade harness.
- Test-hygiene: тесты пишут в tracked `data/cross_trial_sharpes.json`.

---

## Phase tracking (S67 — Desktop Auto-Resume)

| Phase | Status | Notes |
|---|---|---|
| 1 Orient | done | chapter S67 marked |
| 2 Brainstorm | skipped | директива ясна (OQ-4 verdict → desktop path) |
| 3 Plan | done | plan + техстраница auto-resume (doc-first); ветка feature/sprint-67 |
| 4 Execute | done | T1 gate helper + T2 20 tests (fable-5 TDD via Workflow), T3 consumer-контракт git, T4 Scheduled Task через MCP |
| 5 Verify | done | 20/20 pytest, ruff clean, dry-run NONE/GO/FOREIGN/WAIT |
| 6 Review | done | security-auditor (fable-5) APPROVE 0 blockers; C-A/C-B/C-C закрыты; review в sprint-67 |
| 7 Sync | done | auto-resume component + sprint-67 + index + current-state (sprint pages 69) |
| 8 Ship | done | squash main c1d2232 + tag v0.1.0-alpha.67 (push отложен) |
| 9 Close | done | между спринтами; auto-resume боевой (первый тик gate → NONE, мутаций нет) |

---

## История спринтов (где искать)

- `wiki/project/sprints/sprint-NN-<slug>.md` — canonical per-sprint; `wiki/log.md` — journal; `current-state.md` — counts.
- Pre-trim archive (S46): [[archive/SPRINT_STATE-archive-part-1]] / [[archive/SPRINT_STATE-archive-part-2]].

## Правила файла

**BUDGET ≤ 6 KB BINDING.** History → `log.md` + `sprint-NN.md`.
