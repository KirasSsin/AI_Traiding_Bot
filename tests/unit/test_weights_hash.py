"""S55 TQ-05 — src/ml/weights_hash.py unit tests (C4 cache-integrity defense).

The ``weights_hash`` is folded into the prediction CacheKey so stale/foreign
weights are never reused (contract in src/ml/prediction_cache.py:8-13).  This
module SHA-256s the actual HF weight files; when none are on disk it falls back
to a revision-pinned seed.

Coverage:
  1. file-hash path: two distinct fake weight files -> stable 64-hex digest that
     CHANGES when any byte changes.
  2. fallback path (no files on disk) -> stable 64-hex digest.
  3. REGRESSION (the TQ-05 bug guard): two variants with DIFFERENT pinned
     revisions but absent weights MUST produce DIFFERENT hashes.  The original
     fallback hashed only ``"model_id|tokenizer_id"`` (revision-independent) ->
     cross-revision cache-key collision -> stale predictions replayed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from src.ml.weights_hash import compute_weights_hash

_HEX64 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class _FakeVariant:
    """Structural stand-in for KronosVariant (model_id/tokenizer_id + revisions)."""

    model_id: str
    tokenizer_id: str
    model_revision: str
    tokenizer_revision: str


def _make_variant(
    *,
    model_rev: str = "a" * 40,
    tokenizer_rev: str = "b" * 40,
) -> _FakeVariant:
    return _FakeVariant(
        model_id="NeoQuasar/Kronos-base",
        tokenizer_id="NeoQuasar/Kronos-Tokenizer-base",
        model_revision=model_rev,
        tokenizer_revision=tokenizer_rev,
    )


def _write_weight_file(hf_cache: Path, repo_id: str, filename: str, data: bytes) -> Path:
    """Create a fake HF-cache weight file under the expected repo dir layout."""
    repo_dir = hf_cache / ("models--" + repo_id.replace("/", "--")) / "snapshots" / "rev"
    repo_dir.mkdir(parents=True, exist_ok=True)
    path = repo_dir / filename
    path.write_bytes(data)
    return path


# ---------------------------------------------------------------------------
# 1. file-hash path: stable 64-hex AND byte-sensitive
# ---------------------------------------------------------------------------


def test_compute_weights_hash_files_stable_and_byte_sensitive(tmp_path: Path) -> None:
    """Two distinct weight files -> deterministic 64-hex digest; a 1-byte change flips it."""
    variant = _make_variant()
    hf_cache = tmp_path / "hub"

    model_file = _write_weight_file(
        hf_cache, variant.model_id, "model.safetensors", b"MODEL-WEIGHTS-AAAA"
    )
    _write_weight_file(
        hf_cache, variant.tokenizer_id, "pytorch_model.bin", b"TOKENIZER-WEIGHTS-BBBB"
    )

    digest1 = compute_weights_hash(variant, hf_cache=hf_cache)
    assert _HEX64.match(digest1), f"expected 64-hex digest, got {digest1!r}"

    # Stable: recomputing over the same files yields the identical digest.
    digest2 = compute_weights_hash(variant, hf_cache=hf_cache)
    assert digest1 == digest2, "digest must be deterministic for identical files"

    # Byte-sensitive: flip one byte in the model weights -> digest must change.
    model_file.write_bytes(b"MODEL-WEIGHTS-AAAB")  # last byte A -> B
    digest3 = compute_weights_hash(variant, hf_cache=hf_cache)
    assert digest3 != digest1, "digest must change when a weight byte changes (C4)"
    assert _HEX64.match(digest3)


# ---------------------------------------------------------------------------
# 2. fallback path: no files on disk -> stable 64-hex
# ---------------------------------------------------------------------------


def test_compute_weights_hash_fallback_stable_hex(tmp_path: Path) -> None:
    """With no weight files on disk, the fallback returns a stable 64-hex digest."""
    variant = _make_variant()
    empty_cache = tmp_path / "empty_hub"  # never created -> no repos found

    digest1 = compute_weights_hash(variant, hf_cache=empty_cache)
    assert _HEX64.match(digest1), f"expected 64-hex fallback digest, got {digest1!r}"

    digest2 = compute_weights_hash(variant, hf_cache=empty_cache)
    assert digest1 == digest2, "fallback digest must be deterministic"


# ---------------------------------------------------------------------------
# 3. REGRESSION (TQ-05 bug guard): distinct revisions, absent weights -> distinct hashes
# ---------------------------------------------------------------------------


def test_compute_weights_hash_fallback_distinct_revisions_differ(tmp_path: Path) -> None:
    """Two variants differing ONLY in pinned revision must hash differently in fallback.

    The original fallback seed was ``f"{model_id}|{tokenizer_id}"`` — independent
    of model_revision/tokenizer_revision.  Two distinct pinned revisions whose
    weights are not yet downloaded therefore produced the SAME weights_hash ->
    the prediction CacheKey collided across revisions -> stale cross-revision
    predictions were replayed (violates the C4 contract on the revision
    dimension).  This guard fails on the old seed and passes once the revisions
    are folded into the seed.
    """
    empty_cache = tmp_path / "empty_hub"

    variant_rev1 = _make_variant(model_rev="1" * 40, tokenizer_rev="2" * 40)
    variant_rev2 = _make_variant(model_rev="3" * 40, tokenizer_rev="4" * 40)

    # Same model_id + tokenizer_id; only the pinned revisions differ.
    assert variant_rev1.model_id == variant_rev2.model_id
    assert variant_rev1.tokenizer_id == variant_rev2.tokenizer_id
    assert variant_rev1.model_revision != variant_rev2.model_revision

    digest1 = compute_weights_hash(variant_rev1, hf_cache=empty_cache)
    digest2 = compute_weights_hash(variant_rev2, hf_cache=empty_cache)

    assert digest1 != digest2, (
        "fallback weights_hash collides across revisions "
        f"({digest1} == {digest2}) — cross-revision cache-key collision (C4 bug)"
    )


def test_compute_weights_hash_fallback_model_revision_alone_differs(tmp_path: Path) -> None:
    """Changing ONLY model_revision (tokenizer pinned) must change the fallback hash."""
    empty_cache = tmp_path / "empty_hub"
    base = _make_variant(model_rev="a" * 40, tokenizer_rev="c" * 40)
    bumped_model = _make_variant(model_rev="b" * 40, tokenizer_rev="c" * 40)

    assert compute_weights_hash(base, hf_cache=empty_cache) != compute_weights_hash(
        bumped_model, hf_cache=empty_cache
    )


def test_compute_weights_hash_fallback_tokenizer_revision_alone_differs(
    tmp_path: Path,
) -> None:
    """Changing ONLY tokenizer_revision (model pinned) must change the fallback hash."""
    empty_cache = tmp_path / "empty_hub"
    base = _make_variant(model_rev="a" * 40, tokenizer_rev="c" * 40)
    bumped_tok = _make_variant(model_rev="a" * 40, tokenizer_rev="d" * 40)

    assert compute_weights_hash(base, hf_cache=empty_cache) != compute_weights_hash(
        bumped_tok, hf_cache=empty_cache
    )
