---
title: 0018. Sprint 4 risk decisions — R:R, reason codes mapping, Wilson lower bound, L0 naming, reason-codes count
type: decision
tags: [adr, risk, kelly, circuit-breakers, reason-codes, sprint-4, security]
created: 2026-04-23
updated: 2026-04-23
sources: [src/risk/manager.py, src/risk/kelly.py, src/risk/reason_codes.py, src/risk/override.py, src/platform/config.py, src/risk/equity_tracker.py, src/risk/resume_cb.py]
status: accepted
---

# 0018. Sprint 4 risk decisions

**Status:** accepted
**Date:** 2026-04-23
**Supersedes:** none
**Amends:** [[0012-4-phase-kelly-sizing]] (sub-decision 3 — Wilson lower bound contract); [[../../trading/concepts/reason-codes]] (sub-decision 5 — wiki count typo).

## Context

Sprint 4 имплементировал risk-модуль (Kelly + CB + RiskManager). По ходу разработки возникли 5 субдецизий, не покрытых ранее существующими ADR (0012, 0013, 0017). Они влияют на API контракт и аудит-инвариант, поэтому фиксируются явно.

## Sub-decision 1 — R:R = 2:1 default

**Question:** Какие SL/TP multiplier'ы по умолчанию?

**Decision:**
- `risk_sl_atr_multiplier = 1.5` (k для `compute_qty` И SL placement: `entry − 1.5·ATR`).
- `risk_tp_atr_multiplier = 3.0` (TP placement: `entry + 3.0·ATR`).
- Risk:Reward = 2:1 на каждый сетап.

**Rationale:** Walk-forward тесты Mimo bot (reference) показывали стабильный edge при R:R 2:1 на 1H BTCUSDT EMA-cross стратегии. Phase 1 (n<30 trades) — фиксированная 1% позиция; даже при 50% win-rate ожидаемый PnL положительный (`0.5·(+2R) − 0.5·(−1R) = +0.5R`).

**Configurable:** Оба значения в `Settings`, не в коде. ADR не меняется при тюнинге значений; меняется только при смене **формулы** (например, переход на ATR-on-entry vs trailing).

## Sub-decision 2 — REJECT_INVALID_SIGNAL и REJECT_ZERO_QTY НЕ распаковываются

**Question:** В prompt-spec было предложено добавить `REJECT_INVALID_SIGNAL` и `REJECT_ZERO_QTY` как отдельные коды. Делать?

**Decision:** Нет (для v0.1). Использовать существующие:
- "Invalid signal" → `REJECT_DUPLICATE_SIGNAL` (когда signal приходит повторно для одного бара) — это единственный realistic invalid case в S4. Strategy layer (S3) уже фильтрует out-of-order и not-closed bars; до Risk модуля невалидные signals не доходят.
- "Zero qty" после quantize → `REJECT_MIN_NOTIONAL` (семантически точнее: qty=0 значит позиция меньше минимального notional, который exchange примет).

**Rationale:** Reason codes immutable (см. правила в [[../../trading/concepts/reason-codes]] §3 — новые коды только через ADR). Перед добавлением кодов хотим увидеть реальные audit-log distributions из backtests S7. Если "zero qty" окажется частым отдельным класом (не от MIN_NOTIONAL, а от floating-point degenerate input) — добавим в S5/S7.

**Re-evaluate:** Sprint 5 (executor) — если venue filter rejects распадаются на distinct categories (FILTER_PRICE vs MIN_NOTIONAL vs LOT_SIZE), пересмотреть.

## Sub-decision 3 — Wilson 95% CI lower bound для Kelly phases 3/4

**Question:** В `RiskManager._compute_p_b` для phases 3/4 — использовать точечную оценку `wins/total` или Wilson lower bound?

**Decision:** **Wilson 95% CI lower bound** (`wilson_95_ci(wins, total)[0]`).

**Rationale:** Точечная оценка `p_hat = wins/total` системно переоценивает edge на малой выборке. Пример: 30 wins / 50 trades → `p_hat = 0.6`, но Wilson 95% lower = `0.45`. Если мы используем Half-Kelly формулу с завышенным `p`, получаем over-betting и blow-up при первой просадке. Lower bound — conservative estimate, потеря edge на upside, но защита от ruin на downside (Kelly criterion is symmetric in wrong direction — over-betting губительно).

**Amends ADR 0012:** Добавляет явный contract: phases 3/4 _compute_p_b возвращает `wilson_95_ci(...)[0]`, не `wins/total`. Code: `src/risk/manager.py:223`.

**Test coverage:** `tests/unit/test_risk_kelly.py::test_wilson_95_ci_*` + `tests/unit/test_risk_manager.py` (через mock trade history).

## Sub-decision 4 — `HaltState.L0` explicit naming (NOT null/None)

**Question:** "No halt active" представляется как `HaltState.L0` или `None`?

**Decision:** Explicit `HaltState.L0` enum value.

**Rationale:**
1. Pydantic v2 strict mode: `Optional[HaltState]` требует extra null-check на каждом сравнении.
2. State persistence: `state` table storing JSON, null vs string инконсистентно сериализуется (особенно при roundtrip через SQLite TEXT).
3. Severity ordering таблица (`_halt_severity`) — `L0=0` естественно работает, `None` сломал бы `if new > current`.
4. Audit-log queries: `SELECT * FROM events WHERE halt_state='L0'` чище чем `WHERE halt_state IS NULL OR halt_state='L0'`.

**Implementation:** `src/risk/models.py::HaltState` — `L0|L1|L2|L3|FLASH`. Default value of `current_halt` field — `HaltState.L0`.

## Sub-decision 5 — Reason codes count fix (28 → 29)

**Question:** Wiki header `Reason Codes (28)` и `6+7+8+7=28`, но при перечислении: exits=8 codes, halts=7. Какое истинное число?

**Decision:** **29** (`6 + 8 + 8 + 7`). Wiki header был неверен.

**Rationale:** `src/risk/reason_codes.py::ReasonCode` enum (immutable per concept page §2) всегда содержал 29 элементов. Wiki header arithmetic ошибочен в исходной странице (создана 2026-04-19) — section names "(7)" и "(6)" не соответствовали bullet-counts.

**Action taken:**
- `wiki/trading/concepts/reason-codes.md` обновлён: title, TL;DR, секция-headers, total → 29.
- `src/risk/reason_codes.py` docstring уже содержал correct note (см. lines 22-26).
- Никаких code изменений не требовалось (enum уже был 29).

**Forward-only:** ADR изменяет wiki header, не enum. Enum codes immutable per concept page §2 правило.

## Sub-decision 6 — Decimal hot path для Quarter/Half-Kelly

**Question:** В `phase_adjusted_fraction` для phases 3/4 — оригинал использовал `Decimal(str(f * 0.25))`. Float multiply ДО Decimal cast нарушает invariant "monetary fraction is Decimal" (ADR 0007).

**Decision:** Сначала перевести `f` (float) в Decimal через `Decimal(str(f))`, затем умножать на `Decimal("0.25")`/`Decimal("0.5")` в Decimal domain, и квантовать результат до 10dp (`Decimal("1e-10")`) — это убирает trailing IEEE-754 noise унаследованный от float `f`, оставаясь far above бизнес-precision (≤5 sig digits в практических kelly fractions).

**Rationale:** Quant-stats reviewer flag (commit 4aae547): `f * 0.25` для f=0.30000000000000004 даёт 0.07500000000000001, что приводит к `Decimal("0.07500000000000001")` → пропагирует в qty calc. Decimal multiply: `Decimal("0.30000000000000004") * Decimal("0.25") = Decimal("0.0750000000000000100")` — та же ошибка магнитуды, но bounded. Quantize до 1e-10 → `Decimal("0.0750000000")` ≡ `Decimal("0.075")`.

**Code ref:** `src/risk/kelly.py::phase_adjusted_fraction`, lines 119-127.
**Test:** `tests/unit/test_risk_kelly.py::test_phase{3,4}_decimal_no_float_contamination`.

## Sub-decision 7 — Atomic equity flush через `_no_commit` API

**Question:** Trading-logic reviewer (commit 4aae547) flag'нул: `EquityTracker.record` вызывает `self._conn.commit()` сразу после INSERT, затем `StateRepository.update_many` открывает отдельную `with self._conn:` транзакцию. Две независимые транзакции вместо одной — нарушение invariant #5 (risk-manager.md: "equity snapshot + state в одной транзакции"). Crash между ними оставляет equity persisted, halt level lagging.

**Decision:**
1. Добавить `EquityTracker.record_no_commit(...)` — INSERT без commit, возвращает lastrowid.
2. Добавить `StateRepository.update_many_no_commit(...)` — multi-key UPSERT без `with self._conn:` обёртки.
3. `RiskManager.update_equity` оборачивает оба вызова в один `with self._conn:` блок. Любое исключение → rollback обоих.

**Test:** `tests/unit/test_risk_manager.py::test_update_equity_atomic_rollback_on_state_failure` — monkeypatches `update_many_no_commit` чтобы raise, verifies equity_snapshots row count не изменился.

**Code refs:** `src/risk/equity_tracker.py:39-61`, `src/risk/state_repo.py:60-77`, `src/risk/manager.py::update_equity`.

**Rationale:** Старые `record()` / `update_many()` сохранены для use-cases вне orchestrator (тесты, ad-hoc CLI, future repositories) — обратная совместимость не сломана.

## Sub-decision 8 — LONG-only `assess()` контракт + ROUND_DOWN qty + prev_close persistence

**Three small fixes batched** (one ADR amendment to avoid bloat):

**8a. LONG-only gate в `assess()`:** ранее SL/TP формулы (lines 184-185) и hardcoded `ENTRY_LONG_TREND_FOLLOWING` reason были silently LONG-only. Quant-stats reviewer flag: либо gate на `signal.side == LONG` с raise, либо branch SL/TP по side. Решено: explicit `ValueError` если `side != LONG`, поскольку v0.1 FSM = LONG+FLAT only, а FLAT — exit semantics handled outside Risk per Strategy contract. Code: `src/risk/manager.py::assess` (после look-ahead gate). Test: `test_assess_rejects_non_long_signal`.

**8b. ROUND_DOWN qty quantize:** ранее `qty.quantize(Decimal("0.00000001"))` использовал default `ROUND_HALF_EVEN`. Trading-logic reviewer flag: для Bybit Spot BUY правило rounding = step-floor (round-down), round-up рискует rejection (insufficient balance / oversize). Fix: `quantize(..., rounding=ROUND_DOWN)`. Code: `src/risk/manager.py:181`. Test: `test_qty_quantize_rounds_down` (mocks compute_qty=`0.123456789`, asserts result=`0.12345678` not `0.12345679`).

**8c. `_prev_close` persistence across restart:** ранее `load_state()` восстанавливал только `_current_halt`, не `_prev_close`. После restart первый bar пропускал flash detection silently. Fix: `on_bar_close` персистит `risk:cb:prev_close` в state table; `load_state` восстанавливает. Code: `src/risk/manager.py::on_bar_close` + `load_state`. Tests: `test_on_bar_close_persists_prev_close`, `test_load_state_restores_prev_close`.

**Rationale (общее):** все три fix'а — bounded, well-localized, без contract changes наружу (только дополнительные guarantees). LONG-only была implicit assumption — теперь explicit. ROUND_DOWN — venue compliance, не семантика. prev_close — operational continuity gap, не invariant violation.

## Sub-decision 9 — Sprint 4 security audit hardening (post-merge review)

**Context:** Перед merge'ом Sprint 4 PR прогнан full L4 review (Agent Skills `code-review-and-quality` + `security-and-hardening`) на полном diff. Аудиторы вернули **5 must-fix** (1 Critical + 3 High + 1 Important) + **3 Medium/Low** (M1, M2, L3). Все 8 вошли в один батч-патч поверх Sprint 4.

### 9a. C1 — Bybit creds: убрать committed defaults (CWE-798)

**Problem:** `Settings.bybit_api_key` и `bybit_api_secret` имели hardcoded defaults в `src/platform/config.py` ("changeme") — нарушает CWE-798 (use of hard-coded credentials), даже если "очевидно фейк".

**Decision:** Оба поля → `Field(..., min_length=8)` (required, no default). Любой запуск без явного env var падает с pydantic `ValidationError`. Test fixtures передают тестовые значения явно.

**Files:** `src/platform/config.py`, `tests/unit/test_config.py`, `tests/unit/test_risk_settings.py`, `tests/unit/test_risk_manager.py`, `tests/integration/test_resume_cb_cli.py`.

### 9b. H1 — `config_hash()` allowlist (CWE-532)

**Problem:** `config_hash()` хешировал весь `model_dump()`, включая API secret и пути логов. Это означало: rotate API secret → invalidate active risk overrides (operational footgun + потенциальный leak секрета через логи hash-mismatch).

**Decision:** Whitelist'нуть **12 risk-threshold полей** (`risk_max_position_pct_cap`, `risk_sl_atr_multiplier`, `risk_tp_atr_multiplier`, `risk_cb_l1_dd`, `risk_cb_l2_dd`, `risk_cb_l3_dd`, `risk_cb_flash_abs`, `risk_cb_flash_atr_mult`, `risk_kelly_phase1_cap..4_cap`). Канонизация: `json.dumps(..., sort_keys=True, separators=(",",":"), default=str)` → SHA-256.

**Invariant:** Rotate API secret/key, поменять `log_level`/`sentry_dsn`, поменять пути → hash **не меняется**. Изменить любой risk-threshold → hash меняется → active overrides invalidated.

**Files:** `src/platform/config.py` (`_HASH_ALLOWLIST` frozenset).

### 9c. H2 — Override file HMAC envelope (CWE-345 / CWE-306)

**Problem:** `cb_override.json` был plain JSON. Любой process с правами на directory мог подделать override — bypass Circuit Breaker. Нет authenticity check.

**Decision:** **HMAC-SHA256 envelope** `{"payload": <CbOverride>, "sig": <hex>}`. Подпись = `hmac.new(key, canonical_payload, sha256).hexdigest()`. Verify через `hmac.compare_digest` (constant-time).
- Новое required Settings-поле: `risk_override_hmac_key: str = Field(..., min_length=32)` (separate from API secret — позволяет rotate creds без invalidate overrides, см. 9b).
- `OverrideStore.__init__(path, *, hmac_key)` — keyword-only, валидирует `len >= 32`.
- `read_active` fail-closed: missing sig / wrong key / tampered payload / tampered sig → `None` + WARNING log "override HMAC mismatch — possible tampering".

**Files:** `src/risk/override.py`, `src/risk/resume_cb.py` (передаёт key в store), `src/risk/manager.py` (передаёт key в store).

### 9d. H3 — Single-use override semantics (CWE-672)

**Problem:** Override оставался активен до `expires_at` — можно было использовать один файл много раз. Если key утёк, атакующий получает persistent bypass окно.

**Decision:** `consume()` вызывается **сразу** после успешного матча override→halt level в `RiskManager.assess`, **до** sizing. Файл переименовывается в `cb_override.consumed.<ISO-ts>.json` (audit trail сохраняется). Любой повторный assess видит "no active override" → halt re-applies.

**Files:** `src/risk/manager.py::assess`. Test: `tests/unit/test_risk_manager.py::test_override_is_consumed_after_bypass`.

### 9e. M1 — File mode 0o600 + parent 0o700 (CWE-276)

**Decision:** `OverrideStore.write` → `os.open(tmp, O_WRONLY|O_CREAT|O_TRUNC, 0o600)` для файла; `mkdir(mode=0o700, parents=True)` для родителя. Только owner может читать секретный envelope.

### 9f. M2 — Atomic write через `os.replace` (CWE-367 TOCTOU)

**Decision:** Write в `<path>.tmp` → `fsync` → `os.replace(tmp, path)`. Concurrent reader никогда не видит partial file. На Posix `os.replace` — атомарный rename внутри того же FS.

### 9g. I1 — Decimal-strict ranking в `peak_equity_24h` (ADR 0007)

**Problem:** `EquityTracker.peak_equity_24h` использовал `ORDER BY CAST(total_equity AS REAL) DESC LIMIT 1`. CAST'ит Decimal-as-TEXT → IEEE-754 double для сортировки. Два значения, отличающиеся за 15-й значащей цифрой, collapsно в один float — SQL возвращает whoever first, **не** настоящий peak. Нарушает ADR 0007 ("monetary fraction is Decimal").

**Decision:** Тянуть все строки в окне через `WHERE ts >= ?` → строить `[Decimal(r[0]) for r in rows]` → возвращать Python `max(values)`. Decimal сравнение exact. Окно 24h ограничивает memory (≤24·3600 = 86 400 rows worst case при 1Hz).

**Files:** `src/risk/equity_tracker.py::peak_equity_24h`. Test: `test_peak_equity_24h_decimal_precision_beyond_double`.

### 9h. L3 — Drop override path from stdout (CWE-532)

**Decision:** `resume_cb.py` printит `level` + `expires_at`, но **не** абсолютный путь файла. Lateral movement не получает подсказку, где искать секреты.

### Invariants добавленные этой sub-decision

| # | Invariant | Test |
|---|-----------|------|
| H2 | Override file MUST be HMAC-SHA256 envelope; verify uses `hmac.compare_digest` | `test_read_with_tampered_signature_returns_none`, `test_read_with_wrong_hmac_key_returns_none`, `test_read_with_tampered_payload_returns_none` |
| H3 | Override is single-use (consumed before sizing) | `test_override_is_consumed_after_bypass` |
| M1 | Override file mode = 0o600, parent dir = 0o700 | `test_write_file_mode_is_0o600`, `test_write_parent_dir_mode_is_0o700` |
| M2 | Override write is atomic (no partial file readable, no .tmp residue on success) | `test_write_does_not_leave_tmp_file`, `test_write_overwrite_is_atomic` |
| H1 | `config_hash()` excludes credentials, paths, log/observability config | `test_config_hash_excludes_bybit_secret`, `test_config_hash_excludes_bybit_key`, `test_config_hash_excludes_hmac_key`, `test_config_hash_excludes_paths_and_observability` |
| C1 | Bybit creds + HMAC key — no committed defaults; min_length enforced | `test_missing_api_key_raises`, `test_missing_api_secret_raises`, `test_missing_hmac_key_raises`, `test_short_hmac_key_raises` |
| I1 | `peak_equity_24h` ranks by Python `max(Decimal)`, not SQL `CAST AS REAL` | `test_peak_equity_24h_decimal_precision_beyond_double` |

### Rationale (общее)

Аудит показал классический паттерн: код проходил unit tests, но pre-merge security review нашёл реальные attack surfaces (operator compromise, file tampering, credential rotation footgun, Decimal precision regression). Все 8 фиксов — bounded, well-tested, без contract changes наружу (только дополнительные guarantees). HMAC key как **отдельное** required поле решает chicken-and-egg "config_hash includes API secret → secret rotation invalidates active overrides".

## Consequences

**Positive:**
- Wilson lower bound защищает от over-betting на early Kelly phases.
- Explicit L0 упрощает persistence и severity ordering.
- Wiki ↔ code reconciliation устраняет DRY violation (29 в код, 28 в wiki).
- Reason code mapping (sub-decision 2) предотвращает enum bloat без data evidence.

**Negative:**
- Wilson lower bound теряет ~10-20% edge upside на phases 3/4 (intentional trade-off).
- `REJECT_MIN_NOTIONAL` сейчас несёт две семантики (true filter violation + zero-qty after quantize). Audit-log queries должны учитывать.
- `EquityTracker.record` (commit-each-call) и `record_no_commit` (caller owns tx) — два API. Документировано в docstrings.
- LONG-only `assess()` raise — если в S5+ появится SHORT, потребуется explicit ADR + branch.
- Sub-decision 9: deployment теперь требует **два** обязательных секрета (`BYBIT_API_SECRET` + `RISK_OVERRIDE_HMAC_KEY`), задокументировано в ops runbook (Sprint 9).
- Sub-decision 9: rotate HMAC key инвалидирует все active overrides (intentional — HMAC = trust anchor).

**Neutral:**
- R:R 2:1 — стартовый default; Sprint 7 (backtest) может предложить тюнинг.

## References

- [[0012-4-phase-kelly-sizing]] — Kelly base ADR, amended sub-decision 3.
- [[0013-circuit-breakers-l1-l2-l3-flash]] — CB base ADR, no changes.
- [[../components/risk-manager]] — implementation reference.
- [[../../trading/concepts/reason-codes]] — wiki page updated by sub-decision 5.
- `src/risk/manager.py`, `src/risk/kelly.py`, `src/risk/reason_codes.py`.
