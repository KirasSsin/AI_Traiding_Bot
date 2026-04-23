---
title: RiskManager (orchestrator)
type: component
tags: [risk, orchestrator, look-ahead, security, v0.1]
created: 2026-04-23
updated: 2026-04-23
status: stable
sources: [src/risk/manager.py, src/risk/override.py, src/platform/config.py, ADR 0012, ADR 0013, ADR 0018]
---

# RiskManager — risk module orchestrator

**TL;DR:** Точка входа Risk модуля. Композирует `EquityTracker`, `CircuitBreakerDetector`, `Kelly` (4-phase + Wilson lower bound), `compute_qty`, `OverrideStore`, `StateRepository`, `TradeHistoryRepository`. Возвращает `RiskAssessment` (frozen pydantic v2). Enforces look-ahead invariant (`assessed_at >= signal.generated_at`).

## Public API

`src/risk/manager.py`:

```python
class RiskManager:
    def __init__(self, *, conn: Connection, settings: Settings,
                 clock: Callable[[], datetime] = ...) -> None: ...

    # Lifecycle
    def load_state(self) -> None
    def persist_state(self) -> None  # via update_equity flush

    # Hot path
    def update_equity(self, *, realized: Decimal, unrealized: Decimal,
                      ts: datetime) -> None
    def on_bar_close(self, bar: object) -> None
    def assess(self, signal: Signal, *, mark_price: Decimal) -> RiskAssessment

    # Persistence
    def record_closed_trade(self, record: TradeRecord) -> int
```

`Signal` — `src/signalgen/models.py`. `RiskAssessment` — `src/risk/models.py` (frozen pydantic v2).

## Decision pipeline (assess)

```
                       ┌────────────────────────┐
signal + mark_price → │  1. clock() → assessed_at │
                       │  2. assert signal.side == LONG (v0.1 LONG-only)  ← FSM GATE
                       │  3. assert assessed_at >= signal.generated_at    ← LOOK-AHEAD GATE
                       │  4. override = OverrideStore.read_active(now, expected_config_hash)
                       │  5. if prev_close: check_flash → maybe escalate to FLASH
                       │  6. if current_halt != L0:
                       │        if override matches level → continue
                       │        else → reject(HALT_DRAWDOWN_L*|HALT_FLASH_CRASH)
                       │  7. n = trades.count(); phase = phase_from_trade_count(n)
                       │  8. p, b = _compute_p_b(phase)   ← Wilson lower bound for 3/4
                       │  9. f = phase_adjusted_fraction(phase, p, b, KellyCaps)
                       │ 10. qty = compute_qty(equity, f, atr, price, k=sl_mult)
                       │ 11. qty = quantize(8dp, ROUND_DOWN); if qty <= 0 → REJECT_MIN_NOTIONAL
                       │ 12. sl = price - sl_mult·ATR; tp = price + tp_mult·ATR  (LONG-only)
                       │ 13. return RiskAssessment(approved=True, qty, sl, tp, ...)
                       └────────────────────────┘
```

## Invariants (CRITICAL)

| # | Invariant | Enforcement |
|---|---|---|
| 1 | **Look-ahead:** `assessed_at >= signal.generated_at` | `ValueError` raised in `assess` step 2 |
| 2 | **Halt severity ordering:** L3 > L2 > L1 > L0; FLASH > L3 | `_halt_severity` table + `if new > current: escalate` |
| 3 | **Wilson lower bound for phases 3/4** | `_compute_p_b` returns `wilson_95_ci(...)[0]`, not `wins/total` |
| 4 | **Override match required:** override применяется ТОЛЬКО если `override.level == current_halt` | step 5 check |
| 5 | **Atomic equity flush:** equity snapshot + state update в одной транзакции | `update_equity` оборачивает `EquityTracker.record_no_commit` + `StateRepository.update_many_no_commit` в один `with conn:` блок (test: `test_update_equity_atomic_rollback_on_state_failure`) |
| 6 | **Decimal everywhere monetary:** `qty`, `sl`, `tp`, `equity`, `fraction` — Decimal; `p, b` — float (statistical) | type signatures + tests; `phase_adjusted_fraction` использует Decimal multiply (no float×float contamination, ADR 0007) |
| 7 | **LONG-only contract:** `assess()` принимает только `side==LONG`, иначе ValueError | v0.1 FSM (FLAT signals — exit semantics, обрабатываются вне Risk) |
| 8 | **qty step-floor:** quantize(8dp) с `ROUND_DOWN` — Bybit Spot BUY rounding direction | `Decimal.quantize(..., rounding=ROUND_DOWN)` |
| 9 | **Flash CB continuity across restart:** `_prev_close` персистится в `state` table (`risk:cb:prev_close`), восстанавливается в `load_state` | `on_bar_close` → `state.set`; `load_state` → restore |
| 10 | **Override HMAC envelope** (ADR 0018 sub-dec 9 / H2): override file = `{"payload":..,"sig":..}`; verify через `hmac.compare_digest` с `Settings.risk_override_hmac_key` (≥32 chars). Tampered/wrong-key/missing-sig → `read_active` returns `None` + WARNING | `OverrideStore.read_active` fail-closed; `test_read_with_tampered_*` |
| 11 | **Override single-use** (ADR 0018 sub-dec 9 / H3): после успешного матча `override.level == current_halt` → `consume()` **до** sizing. Файл → `cb_override.consumed.<ISO-ts>.json` | `RiskManager.assess` step 5; `test_override_is_consumed_after_bypass` |
| 12 | **Override file mode** (ADR 0018 sub-dec 9 / M1+M2): `0o600` для файла, `0o700` для parent dir; write atomic через `os.open(O_WRONLY\|O_CREAT\|O_TRUNC, 0o600)` + `fsync` + `os.replace` | `OverrideStore.write`; `test_write_file_mode_is_0o600`, `test_write_overwrite_is_atomic` |
| 13 | **`config_hash` allowlist** (ADR 0018 sub-dec 9 / H1): hash покрывает только 12 risk-threshold полей. Rotate API secret/HMAC key, поменять пути/log_level → hash invariant | `Settings._HASH_ALLOWLIST`; `test_config_hash_excludes_*` |
| 14 | **`peak_equity_24h` Decimal-strict** (ADR 0018 sub-dec 9 / I1): ranking через Python `max([Decimal(...)])`, не SQL `CAST AS REAL` (collapse в IEEE-754 для значений > 15 sig digits — wrong peak) | `EquityTracker.peak_equity_24h`; `test_peak_equity_24h_decimal_precision_beyond_double` |

## Reason code mapping

| Outcome | `RiskAssessment.reason_code` | `approved` |
|---|---|---|
| Entry approved | `ENTRY_LONG_TREND_FOLLOWING` | True |
| L1/L2/L3 active, no override | `HALT_DRAWDOWN_L1\|L2\|L3` | False |
| Flash detected, no override | `HALT_FLASH_CRASH` | False |
| `qty == 0` after quantize | `REJECT_MIN_NOTIONAL` | False |

См. [[../../trading/concepts/reason-codes]] (29 enum). v0.1 не маппит `REJECT_INVALID_SIGNAL` / `REJECT_ZERO_QTY` отдельно — см. ADR 0018 для rationale.

## State persistence schema

`migrations/002_risk.sql` + `003_trade_history_unique.sql`:

- `trade_history` — closed trades (UNIQUE INDEX on `entry_signal_id` для idempotent insert)
- `equity_snapshots` — каждый equity update (`realized`, `unrealized`, `source`)
- `state` (existing) — KV store, ключи:
  - `risk:cb:current_level` — `{"level": "L0|L1|L2|L3|FLASH", "triggered_at", "peak_equity", "dd_pct"}`
  - `risk:cb:prev_close` — `{"value": "<decimal_str>"}` — для flash continuity across restart

CB level + prev_close survive restart через `RiskManager.load_state()`.

## Settings (config_hash anti-replay + HMAC envelope)

**`Settings.config_hash()`** возвращает SHA-256 от **whitelisted** 12 risk-threshold полей (allowlist `_HASH_ALLOWLIST` в `src/platform/config.py`). Канонизация через `json.dumps(..., sort_keys=True, separators=(",",":"), default=str)`. `OverrideStore.read_active` отвергает override с `config_hash` не совпадающим с текущим — защита от подмены config при активном override.

**Allowlist (intentionally excludes):**
- API креды (`bybit_api_key`, `bybit_api_secret`) — rotate без invalidate overrides
- `risk_override_hmac_key` — separate trust anchor
- Paths, log_level, sentry_dsn — operational metadata, не risk decision

**`Settings.risk_override_hmac_key`** — required `Field(..., min_length=32)`, separate from API secret. Используется для HMAC-SHA256 envelope подписи override file (см. invariant #10).

См. ADR 0018 sub-decision 9 для полного rationale + threat model.

## Tests

- Unit: 8 файлов (`test_risk_*`) — каждый компонент изолированно
- Integration: `tests/integration/test_risk_flow.py` — 50-bar synthetic price series, 8 сценариев (normal entry → L1 escalation → L2 halt → manual resume → flash → recovery)

## Related

- [[../decisions/0012-4-phase-kelly-sizing]] — Kelly source of truth
- [[../decisions/0013-circuit-breakers-l1-l2-l3-flash]] — CB source of truth
- [[../decisions/0018-sprint-4-risk-decisions]] — Sprint 4 sub-decisions (R:R, reason codes mapping, Wilson lower bound contract, L0 naming, **sub-dec 9: post-merge security audit hardening — C1+H1+H2+H3+M1+M2+I1+L3**)
- [[kelly]] [[circuit-breakers]] [[sizing]] [[override]] — sub-components
- [[../../trading/concepts/look-ahead-bias]] — invariant context
