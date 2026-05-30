"""Prediction cache for the Kronos forecasting strategy (Sprint 52 — C3 + C4 + V4).

Kronos runs OFFLINE (T7 cache-build path). Predictions are precomputed as
deterministic ``Decimal`` values and persisted here; the strategy later REPLAYS
cached predictions through ``on_bar`` (T4). This module therefore NEVER imports
torch — it only stores and reloads already-deterministic Decimal predictions.

Integrity contract (C4):
  - The cache key includes ``(model_id, weights_hash, symbol, timeframe,
    bar_close_ts, params_hash, device)``. A mismatch on ANY field is a MISS;
    stale, foreign-device or foreign-weights predictions are never reused.
  - Each artifact is written with a SHA-256 sidecar (mirrors the S51 D2 parquet
    manifest pattern in ``src/marketdata/storage.py``). On read the digest is
    recomputed and compared; a mismatch is treated as a MISS and a ``UserWarning``
    is emitted (callers branch on ``None`` without exception handling).

Determinism contract (V4): the same key always maps to the same stored value.
Predictions are produced upstream with a fixed torch seed and reduced via
``median_ensemble`` (provided here as a pure function) AT CACHE-BUILD time, so a
single deterministic Decimal vector is stored per key.
"""

import hashlib
import json
import warnings
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path


@dataclass(frozen=True)
class CacheKey:
    """Immutable cache key. A mismatch on ANY field is a MISS (C4)."""

    model_id: str
    weights_hash: str
    symbol: str
    timeframe: str
    bar_close_ts: int
    params_hash: str
    device: str

    def digest(self) -> str:
        """Return a stable SHA-256 hex derivation of all key fields."""
        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def hash_params(params: dict[str, object]) -> str:
    """Return a stable SHA-256 hex digest of a sampling-params dict.

    Order-independent: ``{"a": 1, "b": 2}`` and ``{"b": 2, "a": 1}`` hash equal.
    Intended for the ``params_hash`` field of :class:`CacheKey` (T, top_p,
    sample_count, threshold, ...).
    """
    payload = json.dumps(params, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def median_ensemble(samples: list[list[Decimal]]) -> list[Decimal]:
    """Reduce per-sample horizon vectors to a single per-step median vector.

    For each horizon step, the median is taken across all samples. Decimal is
    preserved end-to-end (no float). For an EVEN number of samples the
    lower-middle element is returned (no averaging), keeping the result an exact
    stored Decimal value.

    Args:
        samples: list of equal-length horizon vectors, one per torch sample.

    Returns:
        A single horizon vector of medians; ``Decimal`` elements throughout.

    Raises:
        ValueError: if ``samples`` is empty or vectors have differing lengths.
    """
    if not samples:
        raise ValueError("samples must be non-empty")
    horizon = len(samples[0])
    if any(len(s) != horizon for s in samples):
        raise ValueError("all sample vectors must have equal length")

    n = len(samples)
    lower_mid = (n - 1) // 2  # lower-middle index for even n; exact middle for odd n
    result: list[Decimal] = []
    for step in range(horizon):
        column = sorted(s[step] for s in samples)
        result.append(column[lower_mid])
    return result


def _sha256(path: Path) -> str:
    """Return lowercase hex SHA-256 digest of a file's contents."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


class PredictionCache:
    """Directory-backed cache of deterministic Decimal predictions (C3).

    Artifacts are JSON files named ``<key-digest>.json`` with a sibling
    ``<key-digest>.json.sha256`` checksum sidecar. Predictions are serialized as
    lists of decimal strings to preserve exact Decimal values across reload.
    """

    def __init__(self, cache_dir: Path) -> None:
        """Create a cache rooted at ``cache_dir`` (created if absent)."""
        self._dir = cache_dir
        self._dir.mkdir(parents=True, exist_ok=True)

    def _artifact_path(self, key: CacheKey) -> Path:
        return self._dir / f"{key.digest()}.json"

    def put(self, key: CacheKey, prediction: list[Decimal]) -> None:
        """Write the prediction artifact plus its SHA-256 sidecar.

        Predictions are stored as decimal strings; reload via ``Decimal(str)``
        reproduces the exact values. Re-putting the same key+value is idempotent
        (V4 determinism: same key → same stored bytes).
        """
        path = self._artifact_path(key)
        body = json.dumps(
            {"prediction": [str(value) for value in prediction]},
            sort_keys=True,
            separators=(",", ":"),
        )
        path.write_text(body)
        sidecar = path.with_suffix(".json.sha256")
        sidecar.write_text(_sha256(path))

    def get(self, key: CacheKey) -> list[Decimal] | None:
        """Return the cached prediction on hit, ``None`` on miss.

        A miss occurs when the key (any of the 7 fields) is not found, the
        sidecar is missing, or the recomputed SHA-256 does not match the sidecar
        (tampered/corrupt artifact). On a checksum mismatch a ``UserWarning`` is
        emitted and ``None`` is returned (treated as a miss, never raises).
        """
        path = self._artifact_path(key)
        sidecar = path.with_suffix(".json.sha256")
        if not path.exists() or not sidecar.exists():
            return None

        expected = sidecar.read_text().strip()
        if _sha256(path) != expected:
            warnings.warn(
                f"Prediction cache checksum mismatch for {path.name}; treating as miss",
                UserWarning,
                stacklevel=2,
            )
            return None

        data = json.loads(path.read_text())
        return [Decimal(value) for value in data["prediction"]]
