---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-05-30  # S52 PHASE 2 brainstorm DONE → PAUSED at ESC-1 (operator продолжит в новой сессии).
sprint: 52
phase: 2-brainstorming-PAUSED-ESC1
branch: feature/sprint-52-kronos
tag: v0.1.0-alpha.51
---

## Текущий статус

**⏸ S52 PAUSED — ожидает operator ESC-1 решения (новая сессия).** PHASE 2 brainstorm DONE (architecture C1-C7 + trader V1-V5). Plan lock (PHASE 3) ЗАБЛОКИРОВАН до ESC-1. Полная детализация → `pre-s52-backlog.md`.

**RESUME ПРОТОКОЛ (новая сессия):**
1. Read `pre-s52-backlog.md` (architecture C1-C7 + trader V1-V5 + ESC-1 три опции A/B/C).
2. Operator выбирает ESC-1: (A) exploratory infra + forward paper-trade [trader+maintainer rec] / (B) forward-only gate exception / (C) permanent research track.
3. После ESC-1 → PHASE 3 writing-plans на `feature/sprint-52-kronos` (branch уже создан, brainstorm committed `212ce16`).

**ESC-1 суть (data-leakage):** Kronos pretrained на истории (cutoff НЕ опубликован, вероятно overlap с 2023-2026 BTC backtest). WFA "OOS" методологически невалиден = in-sample под видом OOS (look-ahead на уровне весов). Backtest = только pipeline smoke-test, НЕ gate. Forward paper-trade = единственный валидный метод. N_trials НЕ инкрементируется до forward gate.

**S51 SHIPPED** — `75644e2` tag v0.1.0-alpha.51 (6 debts). pytest 1449, mypy 0/91, reason codes 65.

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
