---
title: Sprint State — живое состояние проекта
type: state
updated: 2026-06-20  # S55 Batch 0 — BLOCKER TL-01/TL-02 + BYBIT-01 DONE (оба закрыты).
sprint: 55
phase: 4-execution
branch: feature/sprint-55-full-audit-refactor
tag: v0.1.0-alpha.54
---

## Текущий статус

**S55 Batch 0 — BLOCKER TL-01/TL-02 + BYBIT-01 DONE (оба блока закрыты).**

**TL-01/TL-02** (`0d84d57`). Live runtime никогда не вооружал OCO-bracket и сбрасывал exit-сигналы (unbounded-loss на shipped execution-пути). Исправлено: entry-fill → `arm_oco` (TP Limit + SL Stop-Market, fee-aware qty G5; точка подключения — `Coordinator.on_order_event`, прицепные tp/sl-цены сохраняются в `start_bracket` через migration 0007); EXIT_FLAT-сигнал → `coordinator.flatten` когда позиция держится; `reconcile_arming_ttl` подключён в `_tick`. `arm_oco`/`flatten`/`reconcile_arming_ttl` теперь имеют production call-sites. TDD: `tests/integration/test_runtime_oco_wiring.py` (4 new) + обновлён on_order_event safety-тест. mypy 0, pytest GREEN (6 torch-absent Kronos pre-existing).

**BYBIT-01** (`1130cb7`). REST и private-WS подключались к РАЗНЫМ Bybit-окружениям: `_cmd_run` строил WS endpoint `"demo.bybit.com"` при `testnet=True` → pybit-флаги резолвились в MAINNET-demo (`stream-demo`), тогда как REST = `HTTP(testnet=True)` без demo-флага → testnet-биржа (`api-testnet`). testnet-биржа и demo — РАЗНЫЕ account-вселенные → ордера через REST никогда не давали fill/exec/wallet-эхо на WS → FSM не получал ENTRY_FILLED/Filled → OCO не вооружался по live-пути. Исправлено: `demo: bool` добавлен в `Settings` как единый источник истины (пара `testnet`+`demo`); `BybitRESTClient` и `BybitPrivateWSConsumer` строятся из ОДНОЙ пары явных флагов (не substring-эвристика endpoint); startup-лог `bybit.env_resolved` печатает resolved REST+WS хосты. Каноническое окружение S35 demo = testnet-биржа (`testnet=True, demo=False`) — соответствует ADR 0053 LOCKED pre-commit #1 («δ TESTNET ONLY, zero MAINNET») + config.py s35-валидатору. Конфликт с ADR 0027 Q6 (тот описывал Bybit demo-trading для WS, но demo = MAINNET-инфра → противоречит более позднему LOCKED #1) задокументирован в коммите для operator-review. TDD: `tests/unit/test_bybit_env_consistency.py` (7 new — параметризованная проверка REST-вселенная == WS-вселенная для всех 4 комбо + e2e `_cmd_run` no-split + explicit-flags-over-substring + legacy-fallback). mypy 0/98, pytest 1579 passed (6 torch-absent Kronos pre-existing).


**S54 SHIPPED** — `60ee7f3` (PR #69) tag `v0.1.0-alpha.54`. Kronos UI: manifest v1→v2 (per-combo dates+params), `GET /api/kronos/coverage`, frontend ConfigureBacktest auto-fill START/END из кэша + блок некэшированных TF (15m). 3 reviewers APPROVE. mypy 0/98, pytest 1525, frontend 45. Детали → `sprints/sprint-54-kronos-ui.md`.

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
