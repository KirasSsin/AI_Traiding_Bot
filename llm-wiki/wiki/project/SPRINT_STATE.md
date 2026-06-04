---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-06-04  # S54 PHASE 7 done — ADR 0070 + sprint-54 page + wiki sync complete. Next: PHASE 8 Ship.
sprint: 54
phase: 7-sync
branch: feature/sprint-54-kronos-ui
tag: v0.1.0-alpha.53
---

## Текущий статус

**S54 — Kronos UI: cached-coverage auto-fill + uncached-TF block.** Plan `2026-06-01-sprint-54-kronos-ui.md`. Operator asks: Kronos+1h/5m → авто-период из кэша + график/параметры; Kronos+15m → BLOCK; merge to main. Manifest v1→v2 (per-combo dates+params), coverage API, React autofill. T1 manifest v2+backfill / T2 dispatch+coverage API / T3 frontend / T4 review+ship.

**Kronos exploratory (S53 post-ship):** оба TF убыток даже с leakage-преимуществом — 1h 25 trades -5.61%, 5m 21 trades -10.24%. Long-only Spot edge нет. Speed: batch/fp16 = тупик на MPS, `--sample-count` единственный рычаг (~линейно).

**S53** — `eff3ae6` v0.1.0-alpha.53 (real-inference enablement). **S52** — `a188347` v0.1.0-alpha.52.

## Carry (post-S53)

- **atr_breakout ATR-index offset** (D4, HIGH) — own ADR+WFA до live. ADR 0064.
- **D5 forfeit-N policy** (operator escalation).
- **free-form reason strings** (atr_breakout) verify.
- Track B Kronos signal enrichment (predicted high/low SL/TP, multi-horizon) — DEFER до forward paper-trade.
- prediction-cache put() atomicity · median_ensemble property test.
- Forward paper-trade harness → S54+ (единственная валидная Kronos-валидация).
- Permanently deferred: 12mo MAINNET ADR / live trade feed widget / M4 __repr__ redaction.

---

## Phase tracking

| Phase | Status | Notes |
|---|---|---|
| 1 Orient | done | S54 kickoff (Kronos UI, operator-specified scope) |
| 2 Brainstorm | skipped (operator-specified scope, dashboard polish) | — |
| 3 Plan | done | 2026-06-01-sprint-54-kronos-ui.md (T1-T4) |
| 4 Execute | done | T1-T3 done (manifest v2 + coverage API + frontend autofill/block) |
| 5 Verify | done | mypy 0/98, pytest 1525 passed (+14), frontend 45 passed + build+lint clean. 6 "fails" = torch-installed-venv artifacts (torch-absent guards; CI torch-free → green) |
| 6 Review | done | dashboard APPROVE + python APPROVE + data-integrity APPROVE (3 parallel) |
| 7 Sync | done | ADR 0070 + sprint-54 page + current-state/index/log/prediction-cache updates |
| 8 Ship | pending | — |
| 9 Close | pending | — |

---

## История спринтов (где искать)

- **`wiki/project/sprints/sprint-NN-<slug>.md`** — canonical per-sprint
- **`wiki/log.md`** — chronological ship journal
- **`wiki/project/architecture/current-state.md`** — sprint history + canonical counts
- **Pre-trim archive (S46):** [[archive/SPRINT_STATE-archive-part-1]] + [[archive/SPRINT_STATE-archive-part-2]]. Source git `cbf3328`.

---

## Правила файла

**BUDGET ≤ 6 KB BINDING.** History → `log.md` + `sprint-NN.md`. Инструкции → repo CLAUDE.md.
