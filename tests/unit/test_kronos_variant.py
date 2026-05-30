from __future__ import annotations

import dataclasses

import pytest
from src.ml.kronos_variant import KRONOS_BASE, KRONOS_MINI, variant_by_name


def test_base_variant_fields() -> None:
    assert KRONOS_BASE.name == "base"
    assert KRONOS_BASE.model_id == "NeoQuasar/Kronos-base"
    assert KRONOS_BASE.tokenizer_id == "NeoQuasar/Kronos-Tokenizer-base"
    assert KRONOS_BASE.max_context == 512


def test_mini_variant_fields_correct_tokenizer() -> None:
    # mini MUST pair with the 2k tokenizer (S52 bug used -base)
    assert KRONOS_MINI.name == "mini"
    assert KRONOS_MINI.model_id == "NeoQuasar/Kronos-mini"
    assert KRONOS_MINI.tokenizer_id == "NeoQuasar/Kronos-Tokenizer-2k"
    assert KRONOS_MINI.max_context == 2048


def test_variant_is_frozen() -> None:
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        KRONOS_BASE.max_context = 999  # type: ignore[misc]


def test_variant_by_name_resolves() -> None:
    assert variant_by_name("base") is KRONOS_BASE
    assert variant_by_name("mini") is KRONOS_MINI


def test_variant_by_name_unknown_raises() -> None:
    with pytest.raises(ValueError, match="unknown Kronos variant"):
        variant_by_name("large")
