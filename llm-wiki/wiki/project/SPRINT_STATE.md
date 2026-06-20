---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-06-20  # S55 B1 BYBIT-03/02/ARCH-02 + B2 DASH-01/04 (91f92ec) + DI-01 (4740f90) + DI-02 (5a15fad) + SEC-S55-01 (09f2e40) + QS-1 (919a55f, DSR units) + B3 TL-03 (ff9ed12)/TL-04 (146b8c0) + B3 ARCH-03 (c9277df)/BYBIT-04 (d53fcc3)/BYBIT-05 (40e47a5) + B3 DI-04 (b66b751)/DI-03 (facc581) + B3 QS-2 (4ae88b8) + B3 DASH-02 (b85350d)/DASH-03 (32183fa) DONE.
sprint: 55
phase: 4-execution
branch: feature/sprint-55-full-audit-refactor
tag: v0.1.0-alpha.54
---

## Текущий статус

**S55 Batch 1 — HIGH BYBIT-03 (`2afeb6f`) + BYBIT-02 (`b4c5375`) DONE (money-path).** BYBIT-03: `adapter.BybitAPIError` ← подкласс `rest.BybitAPIError`, `_call_rest` ре-оборачивает rest-исчерпание retry с mapped `.reason`, 170005/170222 → RATE_LIMIT_HIT. BYBIT-02: emergency-`flatten` tri-state — сеть после submit = UNKNOWN → HALT, не слепой attempt-2 (double-sell). **ARCH-02 (`81b0329`):** reconcile REST-I/O (~15.5s backoff sleep) вынесен ИЗ Coordinator RLock + Reconciler Lock — fetch snapshot off-lock → потом lock только для pure classify + verdict-переход. Раньше lock-hold блокировал WS SL-cancel (0ms Triggered→Filled gap) → orphan TP self-fill → phantom short. Verdict-семантика byte-identical; classify-чистота подтверждена. TDD +2 (`test_reconcile_lock_hoist.py`). S49 D1 + S50/S51 B1 + TL-01 GREEN. mypy 0, pytest GREEN.

**TL-01/TL-02** (`0d84d57`). Live runtime никогда не вооружал OCO-bracket и сбрасывал exit-сигналы (unbounded-loss на shipped execution-пути). Исправлено: entry-fill → `arm_oco` (TP Limit + SL Stop-Market, fee-aware qty G5; точка подключения — `Coordinator.on_order_event`, прицепные tp/sl-цены сохраняются в `start_bracket` через migration 0007); EXIT_FLAT-сигнал → `coordinator.flatten` когда позиция держится; `reconcile_arming_ttl` подключён в `_tick`. `arm_oco`/`flatten`/`reconcile_arming_ttl` теперь имеют production call-sites. TDD: `tests/integration/test_runtime_oco_wiring.py` (4 new) + обновлён on_order_event safety-тест. mypy 0, pytest GREEN (6 torch-absent Kronos pre-existing).

**BYBIT-01** (`1130cb7`). REST и private-WS подключались к РАЗНЫМ Bybit-окружениям (WS `demo.bybit.com` MAINNET-demo vs REST `testnet` без demo-флага) → ордера через REST не давали fill/exec/wallet-эхо на WS → FSM не получал ENTRY_FILLED → OCO не вооружался. Исправлено: `demo: bool` в `Settings` — единый источник истины; REST+WS из ОДНОЙ пары явных флагов; startup-лог `bybit.env_resolved`. Каноник S35 demo = testnet-биржа (`testnet=True, demo=False`, ADR 0053 LOCKED #1). Конфликт с ADR 0027 Q6 в коммите для operator-review. TDD: `test_bybit_env_consistency.py` (7 new). Детали → git `1130cb7`.


**S54 SHIPPED** — `60ee7f3` (PR #69) tag `v0.1.0-alpha.54`. Kronos UI: manifest v1→v2 (per-combo dates+params), `GET /api/kronos/coverage`, frontend ConfigureBacktest auto-fill START/END из кэша + блок некэшированных TF (15m). 3 reviewers APPROVE. mypy 0/98, pytest 1525, frontend 45. Детали → `sprints/sprint-54-kronos-ui.md`.

**S55 B2 DASH-01+DASH-04** (`91f92ec`). Kronos `RAW_PRETRAIN_LEAKAGE_SUSPECTED` misrender'ился как failed WFA-gate — fix: shared `RESEARCH_VERDICTS` (`utils/verdicts.ts`) на dispatch-сайтах (MetricsTable/TradesTable/HistoryTab) → research-view + leakage-caveat. Frontend +4 (49 GREEN), lint/tsc/build GREEN.

**S55 B2 HIGH DI-02** (`5a15fad`). `BarSource.poll()` мог отдать формирующийся (не закрытый) бар как `is_closed=True` → live look-ahead. Fix: `poll()` дропает бары с `close_time > now` (инъектируемые часы `now_fn`), выбирает новейший settled; dedup+stall сохранены. TDD +3, pytest+mypy GREEN.

**S55 B2 HIGH SEC-S55-01** (`09f2e40`). Path traversal: attacker-`symbol` f-string'ился в parquet-путь `_load_ohlcv` (`__main__.py:500`), достижим из неаутентиф. `/api/backtest`. Fix defense-in-depth: anchored allowlist `\A[A-Z0-9]{1,20}\Z` (1) `BacktestPayload` field_validator → 422 на границе + (2) gate в `_load_ohlcv` (CLI-reachable). Anchored fullmatch (не substring) отбивает `BTCUSDT\n/evil`. TDD +18 traversal payloads. mypy 0, pytest GREEN.

**S55 B2 HIGH QS-1** (`919a55f`). DSR units mismatch: `compute_dsr` candidate Sharpe per-trade (un-annualized), но `sigma_sr` от callers = stdev аннуализированных fold-Sharpe → SR* раздут ~9× → DSR≈0 false-negative (ACTIVE atr_breakout). Fix (quant-stats option B): new `annualization_factor` де-аннуализирует sigma_sr к per-trade шкале внутри `compute_dsr` (Bailey eq.12 одна частота; Lo eq.13 denom не тронут). Wired research_wfa + wfa_reporter. S51 D5 scoping orthogonal (scope≠scale), сохранён. Note: `__main__.py` donchian-путь имеет тот же mismatch — у параллельного агента. TDD +5, mypy 0, pytest GREEN.

**S55 B3 MEDIUM TL-03 (`ff9ed12`) + TL-04 (`146b8c0`).** Streaming exit-priority был ОБРАТНЫМ WFA-runner: atr_breakout проверял reverse-breakdown до ATR-stop, volume_breakout — channel-exit до ATR-stop, тогда как runner'ы делают ATR-stop ПЕРВЫМ (`low[i]<=stop_price` до `elif`). На same-bar double-exit live давал EXIT_FLAT_ATR_REVERSE/VOLUME_CHANNEL вместо stop runner'а (расходящийся reason+fill, live≠backtest). Fix: реордер только streaming-проверок → ATR-stop первым. TDD: parity-тесты same-bar double-exit (atr +1, volume +2). Runner'ы не тронуты. mypy 0, pytest GREEN (6 torch-absent Kronos pre-existing).

**S55 B3 MEDIUM DI-04 (`b66b751`) + DI-03 (`facc581`).** DI-04: `Bar.open_time`/`close_time` → `AwareDatetime` (tz-naive отвергается на domain boundary, как trade_history `entry_ts`). Все src construction sites уже tz-aware (bar_builder real+synth-GAP, bybit rest, kronos). DI-03: `init_db` сортирует миграции по integer-version prefix (не lexicographic — `0006`<`001` ставил FK-миграцию перед referent); +assert non-decreasing order; applied-файлы НЕ переименованы. TDD +5. mypy 0, pytest GREEN.

**S55 B3 MEDIUM ARCH-03 (`c9277df`) + BYBIT-04 (`d53fcc3`) + BYBIT-05 (`40e47a5`).** ARCH-03: публичный `Coordinator.current_state()` (чтение row под RLock — устранён TOCTOU RuntimeManager `_repo.get` вне lock) + `adapter.step_size`/`min_order_qty` свойства (убран `_filters` leak). BYBIT-04: residual-flatten Sell теперь ВСЕГДА несёт детерминированный orderLinkId (при bracket_id=None → symbol-derived fallback, не None → дедуп сохранён). BYBIT-05: residual leavesQty step-floor + sub-min/floored-0 dust → RESIDUAL_FLATTENED (не sell-that-rejects → ложный HALT). current_state pure-read под RLock (no deadlock, no ARCH-02 I/O-под-lock regress). TDD +7. mypy 0 (execution+runtime strict), pytest GREEN.

**S55 B3 MEDIUM DASH-02 (`b85350d`) + DASH-03 (`32183fa`).** DASH-02: MonthlyHeatmap считал ячейку как разницу двух compounded cumulative `equity_pct` (`last-prevClose`) → завышение тем сильнее, чем дальше equity от 0% (~9× при +800%). Fix: истинная месячная доходность через отношение equity-множителей `(mult_close/mult_prev-1)*100`, baseline первого месяца = 1.0; ячейки теперь компаундятся (произведение), не суммируются. Vitest +1 (6 GREEN), tsc/build/lint clean. DASH-03: cache-writes стали atomic (`tmp`+`os.replace` через `_atomic_write_text`, зеркало storage.py) — устранён torn-file read в `get_run`; `with _lock:` поднят в wrapper `run_backtest`→`_run_backtest_locked` так что ВСЕ strategy-ветки (vb/atr/supertrend/kronos+default) single-flight per docstring (раньше research-ветки и cache-write default-пути были вне lock). TDD +3. mypy --strict dashboard 0, pytest GREEN (6 torch-absent Kronos pre-existing).

**Kronos exploratory вывод:** оба TF убыток даже с leakage-преимуществом — 1h 25 trades -5.61%, 5m 21 trades -10.24%. **Long-only Spot edge нет.** Если продолжать: futures-шорт (S55+, плечо/ликвидации) ИЛИ закрыть. Speed: batch/fp16 = тупик на MPS, `--sample-count` единственный рычаг.

**S53** — `eff3ae6` v0.1.0-alpha.53. **S52** — `a188347` v0.1.0-alpha.52.

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
| 8 Ship | done | PR #69 squash-merge 60ee7f3, tag v0.1.0-alpha.54 |
| 9 Close | done | SPRINT_STATE between-sprints + log ship entry + gitignore kronos logs |

---

## История спринтов (где искать)

- **`wiki/project/sprints/sprint-NN-<slug>.md`** — canonical per-sprint
- **`wiki/log.md`** — chronological ship journal
- **`wiki/project/architecture/current-state.md`** — sprint history + canonical counts
- **Pre-trim archive (S46):** [[archive/SPRINT_STATE-archive-part-1]] + [[archive/SPRINT_STATE-archive-part-2]]. Source git `cbf3328`.

---

## Правила файла

**BUDGET ≤ 6 KB BINDING.** History → `log.md` + `sprint-NN.md`. Инструкции → repo CLAUDE.md.
