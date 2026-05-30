---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-05-30  # S53 SHIPPED v0.1.0-alpha.53 → between-sprints.
sprint: 53
phase: between-sprints
branch: main
tag: v0.1.0-alpha.53
---

## Текущий статус

**S53 SHIPPED** — `eff3ae6` (PR #64) tag `v0.1.0-alpha.53`. Kronos real-inference enablement: 3 S52 бага исправлены (import `from kronos`→`from model` via git submodule; mini→Kronos-Tokenizer-2k; atr_14=0→real Wilder ATR). Оба variant (base 102M/ctx512 + mini 4.1M/ctx2048) через `KronosVariant` dataclass. backtest_runner 1682→1489 (`_kronos_dispatch.py` extract). pytest 1517, mypy 0/98, reason codes 67. Backtest exploratory (RAW_PRETRAIN_LEAKAGE_SUSPECTED). Детали → `sprints/sprint-53-kronos-enablement.md`.

**OPERATOR M4 FOLLOW-UP:** `git submodule update --init third_party/kronos` → `pip install -e ".[ml]"` → `export KRONOS_REVISION=<verified sha>` (security hard-fail if unset) → `RUN_ML=1 .venv/bin/python scripts/run_kronos_s53.py --variant base` (+ `--variant mini`) → exploratory backtest оба variant в dashboard.

**S52** — `a188347` v0.1.0-alpha.52 (Kronos integration). **S51** — `75644e2` v0.1.0-alpha.51.

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
| 4 Execute | done | T1-T8 complete |
| 5 Verify | done | pytest 1513 / mypy 0/98 / reason_codes 67 / backtest_runner 1489<1500 / isolation order-independent / script skip-exit-0 |
| 6 Review | in_progress | 8 reviewers → R1 remediation (B1 CI-fix + 4 fixes), re-verified GREEN |
| 7 Sync | pending | — |
| 8 Ship | done | PR #64 squash-merge eff3ae6, tag v0.1.0-alpha.53 |
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
