"""Torch-free SHA-256 provenance hashing of HuggingFace weight files (C4).

Extracted from ``scripts/run_kronos_s53.py`` so the cache-integrity defense is
unit-testable (the script is never imported by pytest, and importing it drags in
torch behind ``RUN_ML``).  This module is pure ``hashlib`` + ``pathlib`` — it
NEVER imports torch.

Integrity contract (C4, mirrors ``src/ml/prediction_cache.py``):
  The ``weights_hash`` is folded into the prediction CacheKey so that stale or
  foreign weights are never reused.  Two distinct pinned revisions MUST produce
  two distinct hashes even when the weight files are not yet on disk — otherwise
  the fallback path would collide cross-revision keys and replay stale
  predictions from the other revision.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Protocol

_log = logging.getLogger(__name__)

_WEIGHT_EXTENSIONS = {".bin", ".safetensors", ".ckpt", ".pt"}
_CHUNK_SIZE = 65536


class _VariantLike(Protocol):
    """Structural type for the fields ``compute_weights_hash`` reads.

    Mirrors :class:`~src.ml.kronos_variant.KronosVariant` without importing it,
    keeping this module dependency-free for the import-gate.  Declared as
    read-only properties so a frozen dataclass (read-only attrs) satisfies it.
    """

    @property
    def model_id(self) -> str: ...
    @property
    def tokenizer_id(self) -> str: ...
    @property
    def model_revision(self) -> str: ...
    @property
    def tokenizer_revision(self) -> str: ...


def compute_weights_hash(
    variant: _VariantLike,
    *,
    hf_cache: Path | None = None,
) -> str:
    """Compute a SHA-256 provenance digest for the variant's HF weight files.

    Searches the HuggingFace cache for files matching ``variant.model_id`` AND
    ``variant.tokenizer_id`` (model + tokenizer are separate Kronos repos).  All
    found weight files are sorted and hashed together for a combined digest (C4).

    When no weight files are found (e.g. models not yet downloaded), falls back
    to a SHA-256 over the *revision-pinned* repo identifiers so that two distinct
    pinned revisions never collide on the same cache key.

    Args:
        variant: A :class:`~src.ml.kronos_variant.KronosVariant` (or any object
            exposing ``model_id``, ``tokenizer_id``, ``model_revision``,
            ``tokenizer_revision``).
        hf_cache: HuggingFace ``hub`` cache directory.  Defaults to
            ``~/.cache/huggingface/hub``.  Injectable for tests.

    Returns:
        A 64-char lowercase hex SHA-256 digest.
    """
    if hf_cache is None:
        hf_cache = Path.home() / ".cache" / "huggingface" / "hub"

    weight_files: list[Path] = []
    for repo_id in (variant.model_id, variant.tokenizer_id):
        # Repo id "org/name" -> directory prefix "models--org--name".
        repo_dir_name = "models--" + repo_id.replace("/", "--")
        repo_dir = hf_cache / repo_dir_name
        if repo_dir.exists():
            for candidate in repo_dir.rglob("*"):
                if candidate.is_file() and candidate.suffix in _WEIGHT_EXTENSIONS:
                    weight_files.append(candidate)

    if not weight_files:
        # Revision-folded fallback: distinct pinned revisions must never collide,
        # even when weights are not yet on disk (C4 revision dimension).
        fallback_seed = (
            f"{variant.model_id}@{variant.model_revision}"
            f"|{variant.tokenizer_id}@{variant.tokenizer_revision}"
        )
        _log.warning(
            "No weight files found for %s@%s / %s@%s under %s; using "
            "revision-pinned ids as hash seed.",
            variant.model_id,
            variant.model_revision,
            variant.tokenizer_id,
            variant.tokenizer_revision,
            hf_cache,
        )
        return hashlib.sha256(fallback_seed.encode("utf-8")).hexdigest()

    weight_files.sort()
    h = hashlib.sha256()
    for wf in weight_files:
        _log.info("  hashing weights file: %s", wf)
        with wf.open("rb") as fh:
            while chunk := fh.read(_CHUNK_SIZE):
                h.update(chunk)
    digest = h.hexdigest()
    _log.info("weights_hash (%d files, model+tokenizer): %s", len(weight_files), digest)
    return digest
