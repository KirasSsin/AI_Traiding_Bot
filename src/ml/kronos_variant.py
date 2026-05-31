"""Kronos model variants (Sprint 53, ADR 0069 C10).

Each variant binds a (model_id, tokenizer_id, max_context) triple. The
tokenizer↔context coupling is encoded structurally so it cannot be set wrong:
mini REQUIRES the 2k tokenizer (ctx 2048); base/small REQUIRE the base
tokenizer (ctx 512). S52 paired mini with the base tokenizer — a bug.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KronosVariant:
    """Immutable Kronos model configuration.

    SECURITY: ``model_revision`` / ``tokenizer_revision`` pin the HuggingFace
    repos to verified commit SHAs (ACE defense — ``from_pretrained`` deserializes
    untrusted checkpoints). Model and tokenizer are SEPARATE repos with DIFFERENT
    SHAs, so each needs its own pin (a single shared ``revision`` cannot pin both).
    Pinned in-code (version-controlled) rather than via env var.
    """

    name: str
    model_id: str
    tokenizer_id: str
    max_context: int
    model_revision: str
    tokenizer_revision: str


KRONOS_BASE = KronosVariant(
    name="base",
    model_id="NeoQuasar/Kronos-base",
    tokenizer_id="NeoQuasar/Kronos-Tokenizer-base",
    max_context=512,
    model_revision="2b554741eca47781b64468546e77fef3e85130e6",
    tokenizer_revision="0e0117387f39004a9016484a186a908917e22426",
)

KRONOS_MINI = KronosVariant(
    name="mini",
    model_id="NeoQuasar/Kronos-mini",
    tokenizer_id="NeoQuasar/Kronos-Tokenizer-2k",
    max_context=2048,
    model_revision="f4e68697d9d5aed55cef5c96aabc3376bcad9f81",
    tokenizer_revision="26966d0035065a0cae0ebad7af8ece35bc1fb51c",
)

_BY_NAME: dict[str, KronosVariant] = {v.name: v for v in (KRONOS_BASE, KRONOS_MINI)}


def variant_by_name(name: str) -> KronosVariant:
    """Resolve a variant by its short name (``base`` | ``mini``)."""
    try:
        return _BY_NAME[name]
    except KeyError as exc:
        raise ValueError(f"unknown Kronos variant: {name!r}") from exc
