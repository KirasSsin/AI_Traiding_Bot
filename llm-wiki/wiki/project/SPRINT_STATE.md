---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-05-30  # S53 T5 done (extract _kronos_dispatch.py, backtest_runner 1682→1482 LoC, C11).
sprint: 53
phase: 3-planning
branch: feature/sprint-53-kronos-enablement
tag: v0.1.0-alpha.52
---

## Текущий статус

**S53 — Kronos real-inference enablement.** S52 внедрил инфру, но real-inference path сломан (3 бага). S53 чинит + оба variant + корректная adaptation. Backtest остаётся exploratory (operator принял leakage-дисциплину после глубокого объяснения). Brainstorm → `pre-s53-backlog.md`.

**3 бага S52 (S53 чинит):** (1) import `from kronos`→`from model` (real-inference broken by design); (2) mini↔tokenizer mismatch (нужен Kronos-Tokenizer-2k, не -base); (3) `atr_14=0` в KronosStrategy → broken bracket sizing (нельзя торговать).

**Brainstorm verdicts:** Q1 git submodule (arch binding) · Q2 KronosVariant dataclass (base+mini) · Q3 V3 locked + ATR fix (operator ESC-1) · Q4 оба exploratory no-cherry-pick · Q5 forward harness→S54+. Architecture C8-C13 binding.

**S52 SHIPPED** — `a188347` tag v0.1.0-alpha.52 (Kronos integration). **S51** — `75644e2` v0.1.0-alpha.51.

## S53 scope (locked, brainstorm → pre-s53-backlog.md)

- T0 import fix + mini tokenizer-2k (C8, CC1) · T1 git submodule third_party/kronos pinned + sys.path wiring + error msg (C9,C13) · T2 KronosVariant dataclass base+mini (C10) · T3 ATR fix KronosStrategy (Track A, CC2 BLOCKER) · T4 extract _kronos_dispatch.py (C11, god-object 1682>1500) · T5 variant dispatch 2×11 presets (Q2) · T6 script rename run_kronos_s53.py + variant selector + rebuild warning (CC4,CC5) · T7 CI submodule-existence test + predict() sig verify (C12,CC3) · T8 ADR 0069 + wiki sync + current-state.md split.

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
| 1 Orient | done | S53 kickoff (session continuation) |
| 2 Brainstorm | done | trader ROUND 1 + arch PRE-PLAN → pre-s53-backlog.md, ESC-1 V3-locked+ATR-fix |
| 3 Plan | done | 2026-05-30-sprint-53-kronos-enablement.md (T1-T8) |
| 4 Execute | in_progress | T1-T5 done. Next: T6 variant dispatch + presets |
| 5 Verify | pending | — |
| 6 Review | pending | — |
| 7 Sync | pending | — |
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
