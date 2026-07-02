# Depth review — docs/08-дашборд/caching-and-security.md

**Reviewer:** doc-reviewer-depth
**Date:** 2026-07-01
**Axis:** CORRECTNESS vs actual `src/`
**Verdict:** APPROVE_WITH_CONCERNS — 0 BLOCKER, 1 WARN, 1 DEEP
**Recomputed:** 3 numeric claims (max-age, collision prob 2⁻⁶⁴ vs 2⁻¹²⁸, SHA truncation bits)

Source files: `src/dashboard/app.py` (374L), `src/dashboard/backtest_runner.py` (1519L), `src/dashboard/_cache_io.py` (34L).

## Cite verification — ALL exact

| Doc cite | Claim | Code | Status |
|---|---|---|---|
| app.py:62 | `_SYMBOL_RE = re.compile(r"\A[A-Z0-9]{1,20}\Z")` | :62 verbatim | ✓ |
| app.py:80-92 | date `_validate_iso_date` field_validator | :80-92 verbatim | ✓ |
| app.py:89 | `date.fromisoformat(v)` | :89 | ✓ |
| app.py:105 | `fullmatch` symbol | :105 `_SYMBOL_RE.fullmatch(v)` | ✓ |
| app.py:220-254 | LOCKED dims enforcement (ADR 0059) | :220-254 (locked_symbol/interval/supported_combos) | ✓ |
| app.py:318-330 | `_CacheControlMiddleware` | :318 class, :324 assets branch, :327 else `no-cache,no-store,must-revalidate`, :330 add_middleware | ✓ |
| app.py:3-4 | header "Localhost-only ... NO auth, NO CORS (single-user dev tool)" | :3 verbatim | ✓ |
| backtest_runner.py:857-859 | `run_id()` SHA-256[:16] of `sid|sym|interval|start|end` | :857-859 verbatim | ✓ |
| backtest_runner.py:916-922 | cache-hit path (outside lock) | :916-922 verbatim | ✓ |
| backtest_runner.py:315 | `_lock = threading.Lock()` | :315 | ✓ |
| backtest_runner.py:931-934 | `with _lock: _run_backtest_locked(...)` | :931-934 | ✓ |
| backtest_runner.py:322 | `_RUN_ID_RE = re.compile(r"\A[a-f0-9]{16}\Z")` | :322 | ✓ |
| backtest_runner.py:1492-1500 / 1498-1499 | `get_run` + `_is_valid_run_id` guard | :1492-1500 exact | ✓ |
| _cache_io.py:17-33, :26 | `atomic_write_text` tmp+os.replace | :17-33 verbatim | ✓ |

**Behavioral facts confirmed:**
- `atomic_write_text` (aliased `_atomic_write_text`) is genuinely the cache writer — 4 call sites (:1025 vb, :1098 ab, :1179 st, :1456 default WFA). Шаг 5 accurate.
- `volume_breakout_iter10` preset really has `locked_symbol="BTCUSDT"`, `locked_interval="240"` (:152-153) — matches example `(BTCUSDT, 240)`. Exact.
- ADR 0059 confirmed = "Sprint 39 volume_breakout pre-registration LOCKED", tags include `anti-snooping`. Attribution correct.
- `max-age=31536000` = 365×24×3600 EXACT (Bash-verified).
- Cache-hit check (:919-922) is OUTSIDE the lock; only `_run_backtest_locked` under lock. Doc's Шаг3→Шаг4 ordering faithful.
- `variant="base"` is 6th BacktestRequest field (:855) NOT in run_id (:858). Doc CORRECTLY states variant excluded from hash + explains it (lines 62, 150, 184). Avoids the dashboard-overview DEEP trap — handled well here.

## WARN

**W1 — collision probability `~10⁻³⁸` is for full SHA-256, but the key is truncated to 64 bits.**
Line 148 (section "Формулы и расчёты"): "SHA-256 гарантирует, что любые два разных набора параметров дадут разный run_id (с вероятностью коллизии ~10⁻³⁸ — пренебрежимо мало)."
The code truncates to `[:16]` hex = **64 bits**. For two specific different param sets the collision probability is **2⁻⁶⁴ ≈ 5.4×10⁻²⁰**, not ~10⁻³⁸. The `~10⁻³⁸` figure corresponds to the FULL 256-bit digest (2⁻¹²⁸ ≈ 2.9×10⁻³⁹ birthday-bound). Off by ~18 orders of magnitude relative to the truncated hash the code actually uses. Still practically negligible (single-user, few runs), so not a BLOCKER — but it is a wrong number in a section that claims precision, and line 60 ("[:16] достаточно для практической уникальности") is the qualitative claim that IS correct. Fix: cite 2⁻⁶⁴ (~5×10⁻²⁰) or drop the specific figure. Bash-verified.

## DEEP

**D1 — single-flight does NOT dedupe two concurrent identical cache-misses; the 2nd request recomputes.**
Doc Шаг 4 + pitfall #3 correctly say the lock serializes ("встанут в очередь"). But note the subtle real behavior: two concurrent identical requests both miss the outside-lock cache check (:919), then serialize on `_lock`. The first computes+writes (:1456); the second re-enters `_run_backtest_locked` which does NOT re-check the cache inside the lock — it recomputes the full WFA and re-writes the same file. So "queue" is accurate but the second run is redundant work, not a cache-hit. Not misleading for a non-programmer and not a money/loss issue (single-user dev tool, atomic write means no corruption). Noted for completeness; no doc change required.

## Minor (not flagged as WARN)
- Шаг7 snippet writes `dispatch(self, request: Request, call_next) -> Response` while real signature is `call_next: Any`. Cosmetic type-hint simplification in an illustrative block; consistent with other pages' style. Not misleading.

## Code issues (real bugs / loss vectors)
None. The security gates (anchored `\A...\Z` + fullmatch on symbol AND run_id) are genuinely wired and effective; atomic write is correct; no money-path/look-ahead/PnL logic touched by this page. The double-compute race (D1) has zero financial impact and is acceptable for a single-user tool.
