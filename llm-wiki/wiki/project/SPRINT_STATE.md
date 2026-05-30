---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-05-30  # S52 SHIPPED v0.1.0-alpha.52 → between-sprints.
sprint: 52
phase: between-sprints
branch: main
tag: v0.1.0-alpha.52
---

## Текущий статус

**S52 SHIPPED** — `a188347` (PR #63) tag `v0.1.0-alpha.52`. Kronos ML strategy (первая ML-стратегия проекта, NeoQuasar/Kronos-mini, offline predict→cache→replay). reason_codes 65→67, pytest 1494, mypy 0/96. Backtest = exploratory `RAW_PRETRAIN_LEAKAGE_SUSPECTED` (non-gating, GATE 0: BTC/USDT в pretrain corpus). Детали → `sprints/sprint-52-kronos.md` + log.md.

**OPERATOR M4 FOLLOW-UP (post-merge):** real inference = только Mac M4 Pro MPS. Запустить `pip install -e ".[ml]"` → set `KRONOS_REVISION=<verified sha>` (security ACE) → `RUN_ML=1 .venv/bin/python scripts/run_kronos_s52.py` → собрать prediction-cache + manifest (11 combos) → exploratory backtest в dashboard. Forward paper-trade gate → formal hypothesis #11 (отдельный будущий ADR).

**S51 SHIPPED** — `75644e2` tag v0.1.0-alpha.51 (6 debts).

## S52+ backlog (carries)

- **atr_breakout ATR-index offset** (D4 follow-up, HIGH) — live 9 vs research 28 entries; own ADR + WFA re-run ДО live-капитала. ADR 0064.
- **D5 forfeit-N policy** (operator escalation) — accept forfeit-N OR conservative pooled-sigma proxy.
- **free-form reason strings** (atr_breakout) — verify canonical enum.
- Permanently deferred: 12mo MAINNET ADR / live trade feed widget / M4 __repr__ redaction.

**S53 carries (S52 PHASE 6 review):**
- **current-state.md split** (54KB > 50KB порог) — indexed parts per universal split pattern.
- **backtest_runner.py 1500 LoC split** (god-object, 1636 LoC) — extract `_kronos_dispatch.py` при следующем touch (HARD-GATE @1500).
- prediction-cache `put()` atomicity (tmp+os.replace) — нужно если cache станет concurrent (сейчас single-thread safe).
- property test `median_ensemble` length invariant (Hypothesis).
- integration test horizon=3 variant (operator M4, RUN_ML).

---

## Phase tracking

| Phase | Status | Notes |
|---|---|---|
| 1 Orient | done | session resume orient |
| 2 Brainstorm | done | C1-C7 + V1-V5 + ESC-1=A → pre-s52-backlog.md |
| 3 Plan | done | 2026-05-30-sprint-52-kronos.md (T0-T10) |
| 4 Execute | done | T0-T10 complete |
| 5 Verify | done | pytest 1494 / mypy 0/96 / reason_codes 67 / Vitest 43 / tsc+build clean / torch-absent CI-isolated |
| 6 Review | done | 9 reviewers → remediation R1-R4 (0d2ef1f/0d3b417/716c0c5/5d46c50), all re-verified GREEN |
| 7 Sync | done | wiki synced (ADR 0068 + manifest docs + index/README) |
| 8 Ship | done | PR #63 squash-merge a188347, tag v0.1.0-alpha.52 |
| 9 Close | done | SPRINT_STATE between-sprints + log ship entry |

---

## История спринтов (где искать)

- **`wiki/project/sprints/sprint-NN-<slug>.md`** — canonical per-sprint
- **`wiki/log.md`** — chronological ship journal
- **`wiki/project/architecture/current-state.md`** — sprint history + canonical counts
- **Pre-trim archive (S46):** [[archive/SPRINT_STATE-archive-part-1]] + [[archive/SPRINT_STATE-archive-part-2]]. Source git `cbf3328`.

---

## Правила файла

**BUDGET ≤ 6 KB BINDING.** History → `log.md` + `sprint-NN.md`. Инструкции → repo CLAUDE.md.
