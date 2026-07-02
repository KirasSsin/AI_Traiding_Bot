# Depth review — kronos-ml-strategy.md (correctness vs code)

Reviewer: doc-reviewer-depth | Date: 2026-06-26 | Axis: CORRECTNESS (facts vs src/)
Page: `docs/02-стратегии/kronos-ml-strategy.md`
Verdict: **APPROVE_WITH_CONCERNS**

BLOCKER: 0 | WARN: 3 | DEEP: 1 | recomputed: 9 numeric/derived facts

---

## Summary

Exceptionally accurate money_core page. Every behavioral claim, threshold, formula,
FSM rule, reason code, CacheKey field, and line citation was verified against `src/`
and confirmed correct. The two recurring strategy-doc traps (Wilder ATR warm-up
boundary; strict `>` vs `≥`) are BOTH handled correctly here. No hallucinated
entities. No wrong numbers. Findings are all minor (broken doc-pointer, illustrative
self-consistency slips, one phrasing nuance) — none mislead the reader about bot behavior.

---

## VERIFIED CORRECT (recomputed / code-checked — do NOT re-flag)

- **Threshold 0.006 / 0.60% derivation** (lines 22, 226-239): commission 0.10%/side +
  slippage 0.05%/side = 0.15%/side → 0.30% round-trip → ×2 = 0.60%. Recomputed exact.
  Matches `DEFAULT_THRESHOLD = Decimal("0.006")` (kronos_strategy.py:46) and runner
  constants `_COMMISSION_TAKER=0.001`, `_SLIPPAGE=0.0005` (kronos_runner.py:44-45).
- **Entry rule** (lines 123-135): `FLAT AND pred_close > current*(1+threshold)` + ATR-guard
  (`_last_atr is None or <=0 → None`). Matches kronos_strategy.py:151-159 exactly,
  including strict `>`.
- **Exit rule** (lines 137-145, 242-248): `LONG AND pred_close < current`, no threshold.
  Matches :161-165. Doc correctly states exit is asymmetric (no reverse threshold) —
  this is the CODE behavior (ADR 0068 calling it "symmetric" is the imprecise one).
- **Wilder ATR warm-up** (lines 263-277, Scenario Г 342-348): DEEP-trap handled CORRECTLY.
  Simulation (`_WilderATR(14)`): `current` is None for bars 1-13, becomes non-None at
  bar 14 (index 13) = SEED = mean(TR[0..13]); recursion `(ATR*13+TR)/14` first applies
  bar 15. Doc says seed at "бар с индексом period-1, то есть 14-й бар" (correct),
  recursion "после инициализации" (correct), "До 14-го бара last_atr=None" (correct),
  "первые 13 баров" not warmed (correct). Citation `atr_breakout_strategy.py:135-180`
  for `_WilderATR` is accurate.
- **median_ensemble lower-middle** (lines 281-290): even N=4 [10,20,30,40] → 20
  (index (4-1)//2=1). Verified. "нижний средний при чётном N" correct (prediction_cache.py:85).
- **Reason codes 66/67** (lines 165, 152): ENTRY_LONG_KRONOS=66, EXIT_FLAT_KRONOS=67,
  total ReasonCode=67. Verified via enum + reason_codes.py:151-152.
- **CacheKey 7 fields** (lines 171-183, 88-100): model_id, weights_hash, symbol,
  timeframe, bar_close_ts, params_hash, device. Matches prediction_cache.py:33-47.
  `bar_close_ts=int(bar.close_time.timestamp())` of CURRENT bar (anti-look-ahead). Correct.
- **weights_hash IS SHA-256** (line 44): confirmed `compute_weights_hash` returns 64-char
  SHA-256 of weight files (weights_hash.py:52,70,110). digest()=SHA-256 of 7 fields
  (line 187) confirmed prediction_cache.py:44-47.
- **SHA-pin ACE defense** (line 374, pitfall 8): correctly attributes ACE defense to
  `model_revision`/`tokenizer_revision` (kronos_adapter.py:57-60), NOT weights_hash.
  Separate model+tokenizer repos → separate pins (kronos_variant.py:18-23). Correct.
- **Two variants** (lines 296-303): base ctx 512 / Tokenizer-base; mini ctx 2048 /
  Tokenizer-2k. Matches kronos_variant.py:33-49. Time conversions: 512h≈3 weeks ✓,
  2048h=85d≈3 months (2.8, acceptable). S52 mini↔base-tokenizer bug + ADR 0069 fix:
  matches kronos_variant.py:1-7.
- **torch isolation** (line 32): `tests/unit/test_ml_optional_dep.py` Test B = "no
  top-level torch import outside src/ml/". Exact match. `scripts/run_kronos_s53.py` EXISTS.
- **Empty-list = miss** (line 370): `test_kronos_strategy.py:237-267` exact match
  (`put(key,[])` → `get`→`[]` → `if not prediction: return None`).
- **Worked scenarios A/В + Простыми словами**: 101200>100600 ✓; 100300 not>100600 &
  not<100000 ✓; 100500 not>100600 ✓. All recomputed correct.
- **Bar fields** (is_closed, symbol, high/low/close, close_time): all exist
  (marketdata/models.py:17-32). All line citations to kronos_strategy.py
  (66-106 init, 112-166 on_bar, 168-184 build, 105 atr, 110 fsm) accurate.
- **FSM** (lines 54, 109-110): {FLAT, LONG}, init FLAT, never SHORT, TL-06. Correct.

---

## Findings

### WARN-1 — Broken ADR reference (wrong filename) — line 387
Doc footer cites `llm-wiki/wiki/project/decisions/0069-sprint-53-kronos-variant-fix.md`.
**Actual file:** `0069-sprint-53-kronos-enablement.md`. No file matching `*variant-fix*`
exists. A reader following the pointer hits a missing file.
- Also `source_files` frontmatter is fine; only the footer slug is wrong.
- Fix: change to `0069-sprint-53-kronos-enablement.md`.
- Not BLOCKER: ADR 0069's subject genuinely covers the variant/import/atr fix (its tags
  include `variant`, `import-fix`, `atr-fix`), and this is a pointer, not a behavior claim.

### WARN-2 — Scenario А timestamp self-inconsistency — lines 312, 2
Doc: "`bar_close_ts = 1704384000` (UNIX-время 14:00)". Actual: 1704384000 =
2024-01-04 **16:00:00 UTC**, not 14:00. Purely illustrative number vs label mismatch;
no behavioral consequence, but a careful reader can catch the arithmetic slip.
- Fix: either change label to 16:00, or change the number to a 14:00 UTC epoch
  (e.g. 1704376800).

### WARN-3 — "SignalSide.SHORT не используется" understates — line 366
Doc: "Поле `SignalSide.SHORT` в системе вообще не используется в v0.1." Precisely,
`SignalSide` has only LONG, FLAT — there is **no SHORT member at all** (`hasattr=False`,
models.py:11-14). "Not used" reads as if it exists but is dormant; it is not defined.
Behavioral conclusion (never shorts) is correct. Cosmetic.

### DEEP-1 — "weights_hash = защита от подмены" phrasing nuance — line 44
The param table glosses `weights_hash` as "защита от подмены" (protection against
substitution). The code is deliberately precise that weights_hash is **provenance /
cache-integrity, NOT anti-tampering security**:
- `weights_hash.py:1,52`: "provenance hashing" / "provenance digest".
- `kronos_adapter.py:60`: "`weights_hash` is post-download provenance, **NOT ACE prevention**".
- Its real job (C4): folded into CacheKey so stale/foreign weights are never *reused*
  (weights_hash.py:9) — detection of accidental staleness, not defense against a
  malicious swap.
"Защита от подмены" can be misread as a security guarantee. The doc does NOT actually
conflate it with the ACE/SHA-pin defense (that is correctly separated at line 374 and
pitfall 8), and pitfall 2 (line 362) frames weights_hash correctly as cache-invalidation.
So the local table phrasing is the only soft spot.
- Suggested: "отпечаток весов для инвалидации кэша при смене модели" (matches code intent);
  keep the ACE/security story attached to the SHA pins, as the doc already does.

---

## Cross-file consistency
- Reason-code total (67), threshold (0.006/0.60%), CacheKey (7 fields), FSM (FLAT/LONG)
  all consistent with verified canonical facts (memory shards kronos-v3-facts,
  kronos-domain-facts) and ADR 0068.
- No contradiction with sibling Kronos pages observed in cited claims.

## No hallucinated entities
All named symbols exist: KronosStrategy, PredictionCache, CacheKey, median_ensemble,
hash_params, _WilderATR, KronosVariant, KRONOS_BASE, KRONOS_MINI, KronosModelAdapter,
KronosAdapter, compute_weights_hash, ReasonCode.ENTRY_LONG_KRONOS/EXIT_FLAT_KRONOS,
SignalSide.{LONG,FLAT}, Signal. ADR 0068 file exists.
