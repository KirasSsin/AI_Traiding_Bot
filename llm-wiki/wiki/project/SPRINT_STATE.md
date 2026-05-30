---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-05-30  # S52 PHASE 4 — T0-T8 done. Next: T9 CI mock + opt-in integration test.
sprint: 52
phase: 4-execution
branch: feature/sprint-52-kronos
tag: v0.1.0-alpha.51
---

## Текущий статус

**S52 PHASE 4 execution — Kronos ML strategy.** ESC-1 RESOLVED = (A) per operator: build full integration as tradeable dropdown strategy NOW, backtest=exploratory RAW label, formal hypothesis #11 DEFERRED to forward paper-trade. EXPANDED scope: all 11 (symbol,TF) parquet combos (BTC 5m/15m/1h/4h/1d + ETH/SOL 15m/1h/4h), не только BTCUSDT 1H. Plan `2026-05-30-sprint-52-kronos.md` (T0-T10). Brainstorm C1-C7 + V1-V5 → `pre-s52-backlog.md`.

**COMPUTE CONSTRAINT:** real Kronos inference = operator Mac M4 Pro MPS. Dev/CI = mocked adapter (C5). Infra built+mock-tested here; operator runs cache-build + exploratory backtest via `RUN_ML=1 scripts/run_kronos_s52.py` post-merge.

**Execution T0-T10 (sequential, subagent-driven):**
- T0 GATE 0 pretrain cutoff investigation (BLOCKING) → ADR 0068 leakage clause
- T1 [ml] dep group / T2 kronos_adapter (torch boundary) / T3 predict-cache+determinism / T4 KronosStrategy on_bar + 2 reason codes (65→67) / T5 RAW_PRETRAIN_LEAKAGE_SUSPECTED verdict / T6 kronos_runner exploratory / T7 run script (M4) / T8 dashboard 11 presets / T9 CI mock+opt-in / T10 ADR+wiki sync

**Не останавливаться до полного внедрения (operator directive).**

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

## Phase tracking

| Phase | Status | Notes |
|---|---|---|
| 1 Orient | done | session resume orient |
| 2 Brainstorm | done | C1-C7 + V1-V5 + ESC-1=A → pre-s52-backlog.md |
| 3 Plan | done | 2026-05-30-sprint-52-kronos.md (T0-T10) |
| 4 Execute | in_progress | T0-T8 done. Next: T9 CI mock + opt-in integration test |
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
