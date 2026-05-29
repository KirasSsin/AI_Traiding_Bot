---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-05-29  # S50 PHASE 4 — T5 done (look-ahead cross-validation; T4 ATR windowing bug fixed)
sprint: 50
phase: 4-execution
branch: feature/sprint-50-supertrend
tag: v0.1.0-alpha.49
---

## Текущий статус

**S50 PHASE 4 execution.** Supertrend (freqtrade adaptation). Trader-expert ROUND 1+2 binding + operator decisions. ADR 0067 proposed. LOCKED: BTCUSDT 1H, hypothesis #10. Q1 pure Supertrend. Q3 1H (not 4H — T5 reachability). Q4 OPERATOR OVERRIDE: fix autoresearch held-out split → legitimate sweep (not literature defaults). 8-step execution order в pre-s50-backlog. Prereq CC2 (Wilder ATR extract) + CC3 (N_trials gap) + CC4 (held-out split).

**T1 (CC2 Wilder ATR extract) DONE** — `db66ca7`. Manual Wilder RMA recursion extracted → `wilder_atr()` в `src/signalgen/indicators.py` (distinct from talib `atr()`); `atr_breakout_strategy._wilder_atr` delegates. **volume_breakout untouched** (talib `atr()` LOCKED per ADR 0059 anti-snooping — 0 diff vs main). 3 parity tests (`tests/unit/test_wilder_atr.py`), mypy strict clean.

**T3 (CC4 held-out split) DONE** — `2fc2cb7`. `split_train_heldout()` + `eval_heldout_once()` + HELDOUT_START/END constants в `scripts/autoresearch_endless.py`; sweep now train-only (ts < 2025-06-01) anti-champion-bias. 5 new tests (`tests/unit/test_autoresearch_heldout.py`). pytest 1359.

**T4 (SupertrendStrategy streaming, Lazybear) DONE** — `0d10eac` (impl) + `9c8d2f1`/`8c1e3a0` (count guards). `src/signalgen/supertrend_strategy.py` + `SUPERTREND_LOCKED_PARAMS` (atr_period=10, mult=3.0). Reason codes 63→65 (ENTRY_LONG_SUPERTREND + EXIT_FLAT_SUPERTREND_FLIP, ADR 0067). Look-ahead-safe (is_closed + OOO/dedup guard + wilder_atr from T1; seed bar trend=BEAR no-entry). Латч verified: BULL line non-decreasing, BEAR non-increasing. 18 new tests (14 strategy + 4 reason codes) + 5 count-guard bumps. pytest 1383, mypy --strict clean. T5 next: vectorized Lazybear cross-validation.

**T7 (supertrend_runner WFA) DONE** — `eaa65a9`. `src/backtest/supertrend_runner.py` mirrors `_run_atr_breakout_wfa` pattern: vectorized Lazybear `_backtest_single` kernel, `run_research_wfa(n_trials=10)`, `CrossTrialLog.append_trial` via `run_research_wfa` (NOT bypassed, NOT inline DSR). BTCUSDT 1H / high-freq tier / sprint_tag="S50". 8 unit tests + 3 ntrials tests GREEN, mypy strict 0. Unskip of `test_supertrend_runner_ntrials.py` placeholder covered by `test_supertrend_runner_n_trials_10_wiring_verified`. pytest 1422 collected / 1397 passed / 25 skipped.

**T2 (CC3 N_trials wiring) DONE** — `6d8f7ad`. Investigation+doc: `atr_breakout_runner.py:497` пробрасывает `n_trials=10` через `run_research_wfa` КОРРЕКТНО (эталон для T7). `run_research_wfa` сам делает `append_trial` (retrofit S44 T9) → ADR 0059 G5 «volume_breakout bypasses append» УСТАРЕЛА. Реальный gap: penalty материализуется только при ≥3 cross-trial sharpes (иначе fallback n_trials=1; `compute_dsr` райзит при n_trials>1 без sigma_sr). T7 ОБЯЗАН: `run_research_wfa` + `n_trials=10` + уникальный `sprint_tag`, НЕ inline DSR (donchian), НЕ отдельный append. Тест-док: `tests/unit/test_supertrend_runner_ntrials.py` (3 active + 1 skip). Finding → ADR 0067 CC3.

**T5 (look-ahead property + vectorized cross-validation) DONE** — `287dd47`. `tests/property/test_supertrend_lookahead.py`: full-history Lazybear reference + streaming-vs-vectorized parity (4 seeds, 1e-9) + truncation-invariance + determinism. **Cross-validation поймала look-ahead баг в T4-fix:** streaming пересчитывал `wilder_atr` из bounded `deque` → re-seed Wilder RMA при насыщении → diff с full-history ATR (~0.18). **Fix:** incremental Wilder ATR recursion (`_update_atr`, O(1), full history) → bit-exact (0.0 diff). T4 unit (11) без регрессий (ATR source only). Suite **1405 passed/25 skip**, mypy 0. **Carry-over:** `atr_breakout_strategy.py` identical pattern (LOCKED shipped — defer) → `pre-s50-backlog.md`.

**S49 SHIPPED** — `571e4fa` tag v0.1.0-alpha.49 (full tech-audit, 1348 tests).

**Canonical counts (post-S49):** 16 states / 30 events / 74 transitions / **63** reason_codes (+7 H6) / 66 ADRs / **53** sprint pages / Vitest 43 / Playwright 7 / pytest 1350

## Phase tracking (S49 — current sprint)

| Phase | Status | Notes |
|---|---|---|
| 1 Orient | done | Session start post-S48 ship |
| 2 Brainstorm | done | Audit-only sprint — no brainstorm (tech-review scope) |
| 3 Plan | done | 9 reviewers → findings aggregated → audit plan |
| 4 Execute | done | All BLOCKER+HIGH+MEDIUM+LOW fixed TDD |
| 5 Verify | done | pytest 1350 / mypy 0 / Vitest 43 / Playwright 7 / lint+tsc+build clean |
| 6 Review | done | 6 re-review agents: ALL APPROVE, 0 regressions |
| 7 Sync | done | wiki sync: sprint-49 page + log + current-state + index + SPRINT_STATE |
| 8 Ship | done | PR #60 squash-merge `571e4fa`, tag v0.1.0-alpha.49 pushed |
| 9 Close | done | SPRINT_STATE between-sprints + log ship entry |

## Следующее действие

**S50 PHASE 4 — продолжить execution.** Done: T1, T2, T3 (CC4 held-out split, `2fc2cb7`), T4 (SupertrendStrategy streaming), **T5 (`287dd47` — look-ahead property + vectorized cross-validation; T4-fix incremental ATR recursion folded in)**, **T6 (`45fae7f` — `strat_supertrend` vectorized Lazybear + COMBOS sweep grid)**, **T7 (`eaa65a9` — `supertrend_runner.py` WFA runner, n_trials=10 wired, CrossTrialLog via run_research_wfa, 8 TDD tests, mypy strict clean)**. Next: T8 (held-out winner eval via `eval_heldout_once`). NOTE: T6 vectorized `strat_supertrend` должен совпадать с T5 reference `_vectorized_supertrend` — verify parity при T8.

## S49-S51 ROADMAP (operator decisions 2026-05-29)

### S49 — Full Tech-Review Audit (SHIPPED → PHASE 8 ship in_progress)

**Все дефекты устранены** — see `sprint-49-tech-review-audit.md` canonical summary. T3 RESOLVED (binding verdict). 63 reason_codes. pytest 1350.

### S50 — NEW STRATEGIES (Path B activation)

**TBD после S49 ships.** Brainstorm: strategy direction / symbol scope / timeframe / acceptance criteria.

### Permanently deferred (no clear sprint owner)

- 12mo MAINNET-promotion ADR (нужен δ live data accumulation — irrelevant до S48 strategy validates)
- Live trade feed widget (YAGNI — 0 live trades)
- Honest close code piece (preset `disabled: bool` + 422 reject) — DROPPED per operator pivot
- M4 `__repr__` security redaction — defer к когда mainnet activation real

---

## История спринтов (где искать)

**SPRINT_STATE — only current.** Historical sprint sections archived и распределены:

**Per-sprint canonical (preferred):**
- **`llm-wiki/wiki/project/sprints/sprint-NN-<slug>.md`** — canonical per-sprint summary pages (50 pages, S1-S46) — primary lookup для "что было в SN"

**Chronological:**
- **`llm-wiki/wiki/log.md`** — append-only journal с per-sprint ship entries (S1 → S46+) — для "когда что произошло"

**SPRINT_STATE pre-trim archive (S46 post-ship):** [[archive/SPRINT_STATE-archive-part-1]] + [[archive/SPRINT_STATE-archive-part-2]]. Source git `cbf3328`.

**Cross-cutting:**
- **`llm-wiki/wiki/project/architecture/current-state.md`** — sprint history table + canonical counts evolution

---

## Правила файла

**BUDGET ≤ 6 KB BINDING.** History → `log.md` + `sprint-NN.md`. Инструкции → repo CLAUDE.md.
