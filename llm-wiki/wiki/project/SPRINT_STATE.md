---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-05-30  # S51 SHIPPED v0.1.0-alpha.51. S52 = Kronos ML strategy brainstorm.
sprint: 52
phase: 2-brainstorming
branch: main
tag: v0.1.0-alpha.51
---

## Текущий статус

**S51 SHIPPED** — squash-merge `75644e2` (PR #62), tag `v0.1.0-alpha.51`. 6 carry-over debts closed (D1 Bybit 110072 / D2 parquet sidecar / D3 block_bootstrap guard / D4 atr_breakout ATR parity / D5 DSR two-level pool scoping / D6 supertrend parity). pytest 1449, mypy 0/91, reason codes 65. Детали → `sprints/sprint-51-debt-closing.md`.

**S52 = Kronos ML strategy (operator-scoped, PHASE 2 brainstorm).** Adapt Kronos foundation model (K-line forecasting transformer, NeoQuasar/Kronos-base 102M, MIT) как новую торговую стратегию. Major: новый heavy dep (torch + pretrained weights) + ML inference path (бот = pure streaming on_bar, нет ML). Kit MANDATORY + architecture-reviewer PRE-PLAN (S46 rule major stack change).

## S52 Kronos — scouted facts

- **Task:** decoder-only AR transformer, прогноз future OHLCV K-line. Input: DataFrame [open,high,low,close,(volume,amount)] + timestamps. Output: predicted OHLCV для pred_len баров.
- **Variants:** mini 4.1M/ctx2048 · small 24.7M/ctx512 · base 102.3M/ctx512 · large 499M (closed). Tokenizer = separate model (Kronos-Tokenizer-base).
- **API:** `KronosPredictor(model, tokenizer, device, max_context).predict(df, x_timestamp, y_timestamp, pred_len, T, top_p, sample_count)`.
- **Deps:** torch, HF transformers/tokenizers, pandas, Python 3.10+. MIT license.
- **Compute:** operator Mac M4 Pro → torch device **"mps"** (NOT cuda).

## S52 operator decisions (binding)

- **Validation:** trader-expert ROUND 1+2 в PHASE 2 (data-leakage: pretrained на истории incl. вероятно BTC backtest-период → WFA OOS невалиден; вероятно forward paper-trade на post-cutoff данных).
- **Compute:** Mac M4 Pro MPS.

## S52 brainstorm questions (trader-expert)

1. Validation под data-leakage: WFA невалиден? forward-only? held-out post-cutoff? как honestly под ADR 0014/anti-snooping.
2. Variant: base 102M (точнее) vs mini 4.1M (MPS-friendly ctx2048)? accuracy vs latency на M4.
3. Signal extraction: predicted OHLCV → entry/exit? (pred close > current×threshold = LONG? direction sign? vs ATR band?). Новый archetype.
4. Inference в streaming on_bar: predict() на rolling lookback каждый бар. Latency M4 MPS? cache? heavy ML без блокировки.
5. N_trials/hypothesis: Kronos = #11 (Bailey pool class "kronos"). sample_count/T/top_p/threshold = param surface → held-out discipline.
6. Symbol/timeframe lock: BTCUSDT 1H? ADR 0059 pre-registration.

## S52+ backlog (S51 carries)

- **atr_breakout ATR-index offset** (D4 follow-up, HIGH) — live 9 vs research 28 entries; own ADR + WFA re-run ДО live-капитала. ADR 0064.
- **D5 forfeit-N policy** (operator escalation) — accept forfeit-N OR conservative pooled-sigma proxy.
- **free-form reason strings** (atr_breakout) — verify canonical enum.
- Permanently deferred: 12mo MAINNET ADR / live trade feed widget / M4 __repr__ redaction.

---

## История спринтов (где искать)

- **`wiki/project/sprints/sprint-NN-<slug>.md`** — canonical per-sprint
- **`wiki/log.md`** — chronological ship journal
- **`wiki/project/architecture/current-state.md`** — sprint history + canonical counts
- **Pre-trim archive (S46):** [[archive/SPRINT_STATE-archive-part-1]] + [[archive/SPRINT_STATE-archive-part-2]]. Source git `cbf3328`.

---

## Правила файла

**BUDGET ≤ 6 KB BINDING.** History → `log.md` + `sprint-NN.md`. Инструкции → repo CLAUDE.md.
