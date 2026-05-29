"""S50 CC3 — N_trials runtime wiring requirement for the (future) supertrend_runner.

WHY THIS FILE EXISTS
====================
ADR 0067 CC3 (carry-over from ADR 0059 G5) flagged a concern: Supertrend is
hypothesis #10, so its DSR multiple-testing penalty must use n_trials=10, NOT
n_trials=1. Before T7 builds ``supertrend_runner.py`` we must establish exactly
what the runner has to do so the n_trials=10 value actually reaches
``compute_dsr_with_status``. This module documents that wiring requirement and
codifies the testable parts so a future regression cannot silently drop the
penalty.

FINDING (traced S50 T2)
=======================
The n_trials -> DSR data path is:

    <runner>.main()
        -> research_wfa.run_research_wfa(..., n_trials=<K>, sprint_tag=<tag>)
            -> CrossTrialLog.append_trial(...)             # ALWAYS appends this trial
            -> if sigma_sr valid (>= 3 cross-trial sharpes):
                   compute_dsr_with_status(n_trials=<K>, sigma_sr=...)   # K flows through
               else:  # < 3 entries -> sigma_sr None/NaN
                   compute_dsr_with_status(n_trials=1)     # FALLBACK, no penalty

Three facts established by tracing the code (S50 T2):

1. ``run_research_wfa`` is the single chokepoint. It accepts ``n_trials`` (default
   1, fail-safe — ``research_wfa.py`` ~line 115) and ALSO performs the
   ``CrossTrialLog.append_trial`` itself (``research_wfa.py`` ~line 262, added by
   the "S44 T9" retrofit). So any runner that calls ``run_research_wfa`` gets the
   cross-trial append "for free" and passes its ``n_trials`` straight through.

   - ``atr_breakout_runner.py`` ~line 497 calls ``run_research_wfa(n_trials=10)``
     => CORRECT wiring (atr_breakout family = 10 hypotheses). VERDICT: atr_breakout
     wires n_trials correctly.
   - ``volume_breakout_runner.py`` ~line 402 calls ``run_research_wfa(n_trials=1)``
     (single hypothesis — intentional). NOTE: the ADR 0059 G5 / ADR 0067 CC3 wording
     "volume_breakout bypasses append_trial" is now STALE — since the S44 T9 retrofit
     moved the append INTO ``run_research_wfa``, volume_breakout does NOT bypass it;
     it routes through ``run_research_wfa`` which appends. The residual concern is the
     n_trials VALUE (1 vs the correct count), not a missing append.
   - ``donchian_runner.py`` does NOT use ``run_research_wfa``; it has its own inline
     DSR block (``donchian_runner.py`` ~lines 190-213) using ``N_TRIALS_LOCKED`` and
     a direct ``CrossTrialLog``. A new runner must NOT copy that inline pattern — it
     should go through ``run_research_wfa`` (the atr_breakout pattern).

2. Passing ``n_trials=10`` is NECESSARY BUT NOT SUFFICIENT. ``run_research_wfa``
   only forwards ``n_trials`` to ``compute_dsr_with_status`` when ``sigma_sr`` is
   valid, and ``sigma_sr`` is valid only when the cross-trial log already holds
   >= 3 OOS Sharpe entries (ADR 0056 hierarchy: >=3 -> stdev; 1-2 -> NaN; 0 -> None).
   With fewer than 3 accumulated cross-trial sharpes the code DELIBERATELY falls
   back to ``compute_dsr_with_status(n_trials=1)`` (honest reporting — no penalty
   can be computed without a sigma_sr estimate). This is the real "gap": the
   multiple-testing penalty for hypothesis #10 only materializes once >= 3
   cross-trial sharpes have accumulated in ``data/cross_trial_sharpes.json``.

3. ``compute_dsr`` itself ENFORCES this: it RAISES ``ValueError`` if n_trials > 1
   without a (non-None, non-NaN, >= 0) sigma_sr (``dsr.py`` ~lines 117-135). So a
   runner cannot "just pass n_trials=10" and skip the cross-trial log — the
   n_trials=1 fallback inside ``run_research_wfa`` is what keeps the call legal when
   sigma_sr is unavailable.

REQUIREMENT FOR T7 (supertrend_runner)
======================================
1. supertrend_runner.main() MUST call ``research_wfa.run_research_wfa`` (the
   atr_breakout pattern), NOT an inline DSR block.
2. It MUST pass ``n_trials=10`` (Supertrend = hypothesis #10) and a distinct
   ``sprint_tag`` so its cross-trial entry is recorded under a unique
   (sprint, symbol) key.
3. It MUST rely on ``run_research_wfa`` for the ``CrossTrialLog.append_trial``
   call (do NOT also append directly — that would double-count / poison the log).
4. The n_trials=10 penalty only applies once the shared cross-trial log holds
   >= 3 OOS Sharpe entries; with < 3 the DSR honestly falls back to n_trials=1.
   This is expected behaviour, not a bug — the runner must not fabricate a
   sigma_sr to force a penalty (and could not anyway: compute_dsr raises without
   a valid one).

The tests below verify (a) that ``compute_dsr_with_status`` actually honours the
n_trials value when a valid sigma_sr is supplied (so passing n_trials=10 is
meaningful), (b) that ``CrossTrialLog`` accumulates cross-trial sharpes across
(sprint, symbol) keys as the runner relies upon, and (c) that n_trials > 1 without
sigma_sr is rejected (proving n_trials alone is insufficient). A skipped
placeholder pins the end-to-end runner requirement until T7 exists.
"""

from __future__ import annotations

import math
from pathlib import Path
from types import SimpleNamespace

import pytest
from src.analytics.cross_trial_log import CrossTrialLog
from src.analytics.dsr import compute_dsr_with_status

# Synthetic OOS trades. compute_dsr reads ``t.pnl_pct`` (an attribute, NOT a dict
# key), and compute_dsr_with_status returns NaN below 10 trades (ADR 0056
# INSUFFICIENT_TRADES threshold). So we supply >= 10 SimpleNamespace records with a
# small positive mean and nonzero std -> finite, non-degenerate Sharpe so the DSR
# penalty term (which scales with n_trials) is actually exercised.
_PNLS = [0.02, 0.04, -0.01, 0.03, 0.015, -0.005, 0.025, 0.012, 0.018, -0.008, 0.022, 0.01]
_TRADES = [SimpleNamespace(pnl_pct=p) for p in _PNLS]


def _dsr(result: object) -> float:
    """Extract the scalar DSR from compute_dsr_with_status (dict) result."""
    assert isinstance(result, dict), f"expected dict status result, got {type(result)}"
    value = result["dsr"]
    assert isinstance(value, float)
    return value


def test_n_trials_changes_dsr_when_sigma_sr_valid() -> None:
    """n_trials=10 vs n_trials=1 MUST produce different DSR (penalty applied).

    This is the core CC3 guarantee: when a valid sigma_sr is available, the
    n_trials value supplied by the runner flows into compute_dsr and increases
    the multiple-testing deflation. If this ever stops holding, passing
    n_trials=10 from supertrend_runner would be a silent no-op.
    """
    dsr_n1 = _dsr(compute_dsr_with_status(trades=_TRADES, n_trials=1, sigma_sr=0.5))
    dsr_n10 = _dsr(compute_dsr_with_status(trades=_TRADES, n_trials=10, sigma_sr=0.5))

    assert not math.isnan(dsr_n1)
    assert not math.isnan(dsr_n10)
    # More trials => larger expected-max-Sharpe benchmark => stricter (lower) DSR.
    assert dsr_n10 < dsr_n1, (
        "n_trials=10 must deflate DSR more than n_trials=1 when sigma_sr is valid; "
        f"got n1={dsr_n1!r} n10={dsr_n10!r}"
    )


def test_cross_trial_log_accumulates_sharpes_across_keys(tmp_path: Path) -> None:
    """CrossTrialLog must accumulate >= 3 OOS sharpes for sigma_sr to become valid.

    run_research_wfa derives sigma_sr from CrossTrialLog.get_oos_sharpes(); the
    n_trials penalty only engages once >= 3 entries exist (ADR 0056 hierarchy).
    This documents the precondition supertrend_runner depends on.
    """
    log = CrossTrialLog(path=tmp_path / "cross_trial_sharpes.json")
    assert log.get_oos_sharpes() == []
    assert log.sigma_sr() is None  # 0 entries -> EMPTY

    log.append_trial(sprint=50, symbol="BTCUSDT_supertrend_a", oos_sharpe=0.4)
    log.append_trial(sprint=50, symbol="BTCUSDT_supertrend_b", oos_sharpe=0.6)
    assert len(log.get_oos_sharpes()) == 2
    assert math.isnan(log.sigma_sr())  # 1-2 entries -> DEGENERATE (NaN)

    log.append_trial(sprint=50, symbol="BTCUSDT_supertrend_c", oos_sharpe=0.9)
    sharpes = log.get_oos_sharpes()
    assert len(sharpes) == 3
    sigma = log.sigma_sr()
    assert sigma is not None and not math.isnan(sigma) and sigma > 0  # >=3 -> valid


def test_dsr_requires_sigma_sr_when_n_trials_above_one() -> None:
    """n_trials > 1 WITHOUT sigma_sr MUST raise — proving n_trials alone is insufficient.

    This is why run_research_wfa's DEGENERATE/EMPTY branch falls back to
    compute_dsr_with_status(n_trials=1): with < 3 cross-trial sharpes there is no
    sigma_sr, and compute_dsr refuses to apply a multiple-testing penalty without
    one (it raises ValueError, dsr.py ~lines 117-135). So the penalty for
    hypothesis #10 only materializes once the shared log has accumulated >= 3
    entries. supertrend_runner must rely on this fallback rather than fabricating a
    sigma_sr.
    """
    # n_trials=1 needs no sigma_sr -> computes fine (>=10 trades).
    dsr_fallback = _dsr(compute_dsr_with_status(trades=_TRADES, n_trials=1))
    assert not math.isnan(dsr_fallback)

    # n_trials=10 without sigma_sr is rejected by compute_dsr (ADR 0025/0056 guard).
    with pytest.raises(ValueError, match="sigma_sr"):
        compute_dsr_with_status(trades=_TRADES, n_trials=10)


@pytest.mark.skip(
    reason=(
        "T7 supertrend_runner not yet built. WIRING REQUIREMENT (CC3): "
        "supertrend_runner.main() MUST call research_wfa.run_research_wfa with "
        "n_trials=10 and a distinct sprint_tag (the atr_breakout_runner.py:497 "
        "pattern), and MUST rely on run_research_wfa for the CrossTrialLog."
        "append_trial (do NOT append directly, do NOT use an inline DSR block like "
        "donchian_runner.py). The n_trials=10 penalty only materializes once the "
        "shared cross-trial log holds >= 3 OOS sharpes; with fewer it honestly "
        "falls back to n_trials=1 (compute_dsr raises if n_trials>1 without "
        "sigma_sr). Unskip and assert run_research_wfa is called with n_trials=10 "
        "once the runner exists."
    )
)
def test_supertrend_runner_passes_n_trials_10() -> None:  # pragma: no cover
    """Placeholder — codify once supertrend_runner exists (see skip reason)."""
    raise AssertionError("supertrend_runner not implemented yet")
