"""S52 T5 — RAW_PRETRAIN_LEAKAGE_SUSPECTED verdict class tests.

ADR 0068 / ESC-1=A, V5: Kronos pretrained model may have seen backtest period —
WFA OOS invalid. New verdict class honest-labels this as exploratory-only,
NON-gating (not promotable to live).

Mirrors RAW_FULL_PERIOD / verdict_raw pattern:
  - Module constant in research_runner_envelope.py
  - warning code "pretrain_leakage" with explanatory message
  - Glossary entry "verdict_pretrain_leakage" in glossary_data.py
  - Verdict union in types.ts (frontend parity check is separate)
"""

from __future__ import annotations

from src.backtest.research_runner_envelope import (
    VERDICT_RAW_PRETRAIN_LEAKAGE,
    build_research_runner_envelope,
)
from src.dashboard.glossary_data import GLOSSARY_ENTRIES as GLOSSARY

# ---------------------------------------------------------------------------
# Constant identity tests
# ---------------------------------------------------------------------------


def test_verdict_constant_value() -> None:
    """VERDICT_RAW_PRETRAIN_LEAKAGE must equal the literal string we use in the frontend."""
    assert VERDICT_RAW_PRETRAIN_LEAKAGE == "RAW_PRETRAIN_LEAKAGE_SUSPECTED"


def test_verdict_distinct_from_other_verdicts() -> None:
    """Must be distinct from all existing verdict strings."""
    other_verdicts = {"WFA_PASS", "WFA_FAIL", "WFA_FAIL_DATA", "RAW", "PASS", "FAIL"}
    assert VERDICT_RAW_PRETRAIN_LEAKAGE not in other_verdicts


# ---------------------------------------------------------------------------
# Envelope integration tests
# ---------------------------------------------------------------------------

_BASE_KWARGS = dict(
    runner_name="kronos_runner",
    symbol="BTCUSDT",
    interval="240",
    n_trades=10,
    sharpe=1.0,
    win_rate=0.5,
    total_pnl_pct=50.0,
    bars_per_year=2191,
    equity_curve=[0.0, 50.0],
    runner_label="Kronos (exploratory)",
)


def test_envelope_accepts_pretrain_leakage_verdict_override() -> None:
    """Envelope with verdict_override=RAW_PRETRAIN_LEAKAGE_SUSPECTED returns that verdict."""
    payload = build_research_runner_envelope(
        **_BASE_KWARGS,
        verdict_override=VERDICT_RAW_PRETRAIN_LEAKAGE,
    )
    assert payload["verdict"] == VERDICT_RAW_PRETRAIN_LEAKAGE


def test_envelope_pretrain_leakage_warning_present() -> None:
    """When verdict_override=RAW_PRETRAIN_LEAKAGE_SUSPECTED, 'pretrain_leakage' high-warning is added."""
    payload = build_research_runner_envelope(
        **_BASE_KWARGS,
        verdict_override=VERDICT_RAW_PRETRAIN_LEAKAGE,
    )
    high = [
        w for w in payload["warnings"] if w["level"] == "high" and w["code"] == "pretrain_leakage"
    ]
    assert len(high) == 1
    msg = high[0]["message"]
    # Honest explanation required per ADR 0068
    assert "pretrained" in msg.lower() or "pretrain" in msg.lower()
    assert "WFA" in msg
    assert "exploratory" in msg.lower()
    assert "NOT a gate" in msg or "not a gate" in msg.lower() or "NOT" in msg


def test_envelope_pretrain_leakage_is_non_gating() -> None:
    """Pretrain leakage verdict is non-gating — acceptance_gate must be None."""
    payload = build_research_runner_envelope(
        **_BASE_KWARGS,
        verdict_override=VERDICT_RAW_PRETRAIN_LEAKAGE,
    )
    assert payload["acceptance_gate"] is None


def test_envelope_pretrain_leakage_has_empty_failed_criteria() -> None:
    """Non-gating verdict must not inject failed_criteria (exploratory, no gate applied)."""
    payload = build_research_runner_envelope(
        **_BASE_KWARGS,
        verdict_override=VERDICT_RAW_PRETRAIN_LEAKAGE,
    )
    assert payload["failed_criteria"] == []


# ---------------------------------------------------------------------------
# Glossary tests
# ---------------------------------------------------------------------------


def test_glossary_contains_verdict_pretrain_leakage_entry() -> None:
    """Glossary must have verdict_pretrain_leakage entry in verdict_status section."""
    assert "verdict_pretrain_leakage" in GLOSSARY


def test_glossary_pretrain_leakage_section() -> None:
    """verdict_pretrain_leakage must be in verdict_status section (mirrors verdict_raw)."""
    entry = GLOSSARY["verdict_pretrain_leakage"]
    assert entry["section"] == "verdict_status"


def test_glossary_pretrain_leakage_description_honest() -> None:
    """Description must surface honest explanation per ADR 0068."""
    entry = GLOSSARY["verdict_pretrain_leakage"]
    desc = entry["description_ru"]
    # Must mention pretrained model + exploratory limitation
    assert "Kronos" in desc or "pretrain" in desc.lower()
    assert "exploratory" in desc.lower() or "исследовательск" in desc.lower()
    # Must not claim this is a gate-passing result
    assert "WFA" in desc
