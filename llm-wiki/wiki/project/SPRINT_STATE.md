---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-05-29  # S50 PHASE 5+6 done → phase=8-ship. Verdict WFA_FAIL, merge+tag alpha.50 (operator).
sprint: 50
phase: 8-ship
branch: feature/sprint-50-supertrend
tag: v0.1.0-alpha.50
---

## Текущий статус

**S50 PHASE 4 COMPLETE (T1-T11) → PHASE 5/6.** Supertrend freqtrade adaptation, hypothesis #10. **Verdict WFA_FAIL** (honest, 10th conjoint fail). Trader ROUND 1+2 binding + operator decisions (Q1 pure Supertrend, Q3 1H not 4H, Q4 OVERRIDE fix autoresearch held-out split). Полная детализация → `sprints/sprint-50-supertrend.md`.

**T9 WFA_FAIL:** winner atr=21/mult=2.0 (boundary-winner snooping flag). Gates failed: t5_floor + n_eff (47<50) + dsr_threshold (0.0, Bailey penalty n_trials=10 sigma=35.41). MC p=0.0005 PASS. Held-out Sharpe 8.08 = bull-beta, не edge. Strategy NOT shipped — dashboard comparison only.

**PHASE 6 BLOCKER FIXED (2026-05-29, `48dac93`):** backtest same-bar fill look-ahead (flip@close[i] исполнялся на open[i] вместо open[i+1]). Fix 3 пути + 2 TDD fill-guard теста; streaming untouched, 4-way parity сохранён. Held-out 8.08→**−4.23** (inflation убрана, сигнал отрицательный OOS), verdict остаётся WFA_FAIL (n_eff 47→16). Детали → `sprints/sprint-50-supertrend.md`.

**Reusable infra (despite FAIL):** wilder_atr() shared (indicators.py); autoresearch held-out split (anti-champion-bias); supertrend_runner; SupertrendStrategy streaming. Methodology win: T5 cross-validation поймала windowed-ATR look-ahead bug → incremental ATR.

**Canonical post-S50:** 16 states / 30 events / 74 transitions / **65** reason_codes (+2 Supertrend) / 67 ADRs (0067) / **54** sprint pages / Vitest 43 / Playwright 7 / pytest **1414** (+2 backtest fill-guard) / mypy 0.

## Phase tracking (S50 — current sprint)

| Phase | Status | Notes |
|---|---|---|
| 1 Orient | done | post-S49 ship |
| 2 Brainstorm | done | trader ROUND 1+2 + operator Q1/Q4 → ADR 0067 |
| 3 Plan | done | writing-plans 11-task TDD plan `4ee1e6d` |
| 4 Execute | done | T1-T11 all committed (verdict WFA_FAIL) |
| 5 Verify | done | pytest 1414 / mypy 0/91 GREEN; CI green PR #61 |
| 6 Review | done | 5 reviewers: python APPROVE / quant APPROVE_WITH_CONCERNS / trading-logic BLOCKER→FIXED `48dac93` / test-engineer APPROVE_WITH_CONDITIONS / trader-expert Ship-OK. All addressed. |
| 7 Sync | done | T11 wiki sync (sprint-50 + index + log + current-state + ADR 0067 accepted) |
| 8 Ship | in_progress | operator: merge + tag v0.1.0-alpha.50 (infra-sprint, strategy WFA_FAIL) |
| 9 Close | pending | — |

## Следующее действие

**PHASE 6 BLOCKER (backtest fill look-ahead) closed `48dac93` → re-review → ship decision.** S50 = honest WFA_FAIL (no edge). Ship = merge branch (reusable infra: wilder_atr / held-out split / supertrend_runner) к main, NO production strategy tag. Open Q for operator: cross_trial_sharpes contamination (sigma_sr=35.41 from S44 multi-symbol mixed into Supertrend DSR).

## S51 ROADMAP

### S51 — operator TBD. Carry-overs:
- **atr_breakout windowed-ATR bug** (pre-existing LOCKED ADR 0060/0064 — same defect S50 fixed in Supertrend; investigate live/backtest parity, needs ADR note). `pre-s50-backlog.md` "Carry-overs discovered S50".
- **ADX-filter Supertrend = hypothesis #11** (deferred operator Q1 — only if pure passed; it FAILED → reconsider).
- **cross_trial_sharpes hygiene** — sprint tag bug (509 vs 50); contamination policy (mixing strategy families in DSR pool) — pending reviewer verdict.
- S49 carries: 110072 dup-order retCode, parquet manifest, block_bootstrap edge-null.

### Permanently deferred
- 12mo MAINNET-promotion ADR (нужен live data — irrelevant до passing strategy)
- Live trade feed widget (YAGNI — 0 live trades)
- M4 `__repr__` security redaction — defer к mainnet activation

---

## История спринтов (где искать)

**SPRINT_STATE — only current sprint.** History distributed:
- **`wiki/project/sprints/sprint-NN-<slug>.md`** — canonical per-sprint (primary lookup "что было в SN")
- **`wiki/log.md`** — chronological ship journal
- **`wiki/project/architecture/current-state.md`** — sprint history table + canonical counts evolution
- **Pre-trim archive (S46):** [[archive/SPRINT_STATE-archive-part-1]] + [[archive/SPRINT_STATE-archive-part-2]]. Source git `cbf3328`.

---

## Правила файла

**BUDGET ≤ 6 KB BINDING.** History → `log.md` + `sprint-NN.md`. Инструкции → repo CLAUDE.md.
