"""T3 prediction-cache tests (Sprint 52 — C3 predict-CACHE + C4 key/checksum + V4 determinism).

Covers:
- put then get same key → identical list[Decimal] (exact values, all Decimal, no float).
- get with a key differing in ANY one of the 7 fields → MISS (None), parametrized.
- get on empty cache → None.
- checksum tamper: corrupt artifact after put → get treats as MISS (None) + warning.
- determinism: same key+value put/get twice → identical.
- median_ensemble: per-horizon-step median across samples, Decimal preserved,
  odd and even sample counts (even → lower-middle convention).
- hash_params: stable across dict key ordering.
- torch-free: module must not import torch.
"""

from decimal import Decimal
from pathlib import Path

import pytest
from src.ml.prediction_cache import (
    CacheKey,
    PredictionCache,
    hash_params,
    median_ensemble,
)


def _make_key(**overrides: object) -> CacheKey:
    """Build a baseline CacheKey, with selective field overrides."""
    base: dict[str, object] = {
        "model_id": "kronos-small",
        "weights_hash": "abc123",
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "bar_close_ts": 1735689600,
        "params_hash": hash_params({"T": 1.0, "top_p": 0.9, "sample_count": 20}),
        "device": "cpu",
    }
    base.update(overrides)
    return CacheKey(**base)  # type: ignore[arg-type]


def _prediction() -> list[Decimal]:
    return [Decimal("100.12345678"), Decimal("99.87654321"), Decimal("101.00000001")]


def test_put_then_get_same_key_returns_identical(tmp_path: Path) -> None:
    cache = PredictionCache(tmp_path)
    key = _make_key()
    pred = _prediction()
    cache.put(key, pred)

    out = cache.get(key)
    assert out is not None
    assert out == pred
    for value in out:
        assert isinstance(value, Decimal)
        assert not isinstance(value, float)


def test_get_empty_cache_returns_none(tmp_path: Path) -> None:
    cache = PredictionCache(tmp_path)
    assert cache.get(_make_key()) is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("model_id", "kronos-base"),
        ("weights_hash", "deadbeef"),
        ("symbol", "ETHUSDT"),
        ("timeframe", "4h"),
        ("bar_close_ts", 1735693200),
        ("params_hash", hash_params({"T": 2.0})),
        ("device", "cuda"),
    ],
)
def test_get_with_any_field_mismatch_is_miss(tmp_path: Path, field: str, value: object) -> None:
    cache = PredictionCache(tmp_path)
    key = _make_key()
    cache.put(key, _prediction())

    other = _make_key(**{field: value})
    assert cache.get(other) is None


def test_checksum_tamper_is_miss(tmp_path: Path) -> None:
    cache = PredictionCache(tmp_path)
    key = _make_key()
    cache.put(key, _prediction())

    # Corrupt the artifact (not the sidecar) so the recomputed digest mismatches.
    artifacts = [p for p in tmp_path.iterdir() if p.suffix == ".json"]
    assert len(artifacts) == 1
    artifacts[0].write_text('{"prediction": ["0"]}')

    with pytest.warns(UserWarning):
        assert cache.get(key) is None


def test_determinism_same_key_value(tmp_path: Path) -> None:
    cache = PredictionCache(tmp_path)
    key = _make_key()
    pred = _prediction()
    cache.put(key, pred)
    cache.put(key, pred)

    first = cache.get(key)
    second = cache.get(key)
    assert first == second == pred


def test_median_ensemble_odd_samples() -> None:
    samples = [
        [Decimal("100"), Decimal("200")],
        [Decimal("102"), Decimal("198")],
        [Decimal("101"), Decimal("199")],
    ]
    out = median_ensemble(samples)
    assert out == [Decimal("101"), Decimal("199")]
    for value in out:
        assert isinstance(value, Decimal)
        assert not isinstance(value, float)


def test_median_ensemble_even_samples_lower_middle() -> None:
    # Even sample count → lower-middle convention (no averaging, stays exact Decimal).
    samples = [
        [Decimal("100")],
        [Decimal("110")],
        [Decimal("120")],
        [Decimal("130")],
    ]
    out = median_ensemble(samples)
    # Sorted [100, 110, 120, 130]; lower-middle of two middles (110, 120) → 110.
    assert out == [Decimal("110")]
    assert isinstance(out[0], Decimal)


def test_median_ensemble_single_sample() -> None:
    samples = [[Decimal("42"), Decimal("43")]]
    assert median_ensemble(samples) == [Decimal("42"), Decimal("43")]


def test_hash_params_stable_across_ordering() -> None:
    a = hash_params({"a": 1, "b": 2, "c": 3})
    b = hash_params({"c": 3, "b": 2, "a": 1})
    assert a == b


def test_hash_params_differs_on_value_change() -> None:
    assert hash_params({"T": 1.0}) != hash_params({"T": 2.0})


def test_module_is_torch_free() -> None:
    """prediction_cache must have NO top-level torch import (env-independent AST gate).

    A runtime ``"torch" not in sys.modules`` check is fragile: torch may already
    be imported by an unrelated test or be installed locally (operator's ``.[ml]``
    env). The durable guard parses the source and asserts no module-body
    ``import torch`` / ``from torch ...`` — survives torch being installed,
    mirrors Test B in test_ml_optional_dep.py.
    """
    import ast
    import importlib.util

    spec = importlib.util.find_spec("src.ml.prediction_cache")
    assert spec is not None and spec.origin is not None
    with open(spec.origin, encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), filename=spec.origin)

    violations: list[str] = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "torch" or alias.name.startswith("torch."):
                    violations.append(f"import {alias.name}")
        elif (
            isinstance(node, ast.ImportFrom)
            and node.module
            and (node.module == "torch" or node.module.startswith("torch."))
        ):
            violations.append(f"from {node.module} import ...")

    assert violations == [], f"Top-level torch import in prediction_cache: {violations}"


# ---------------------------------------------------------------------------
# Edge-case: median_ensemble raises for invalid input (PHASE 6 R3)
# ---------------------------------------------------------------------------


def test_median_ensemble_raises_for_jagged_vectors() -> None:
    """Vectors of unequal length must raise ValueError with the documented message."""
    with pytest.raises(ValueError, match="all sample vectors must have equal length"):
        median_ensemble([[Decimal("1")], [Decimal("1"), Decimal("2")]])


def test_median_ensemble_raises_for_empty_input() -> None:
    """Empty samples list must raise ValueError (no samples to reduce)."""
    with pytest.raises(ValueError, match="samples must be non-empty"):
        median_ensemble([])


# ---------------------------------------------------------------------------
# Edge-case: put(key, []) → get returns [] (PHASE 6 R3)
# ---------------------------------------------------------------------------


def test_put_empty_prediction_get_returns_empty_list(tmp_path: Path) -> None:
    """put with an empty prediction vector persists it; get returns [] not None."""
    cache = PredictionCache(tmp_path)
    key = _make_key()
    cache.put(key, [])

    out = cache.get(key)
    # The artifact exists (non-None), but is an empty list.
    assert out is not None, "get after put([]) must return a list, not None"
    assert out == [], f"expected [] but got {out!r}"


# ---------------------------------------------------------------------------
# Atomicity: put() must stage to .tmp then os.replace (DI-06/SEC-S55-03/PY-5).
# Mirrors the canonical tmp+os.replace idiom in src/marketdata/storage.py so a
# crash mid-write never leaves a truncated artifact or a body without a matching
# sidecar.
# ---------------------------------------------------------------------------


def test_put_uses_tmp_then_os_replace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """put() must os.replace BOTH body and sidecar from a .tmp staging path.

    Spies on os.replace and asserts: (1) it is called for both final targets
    (.json + .json.sha256), (2) every source is a .tmp path (never written
    directly to the final name), and (3) the body (.json) is replaced LAST so a
    crash never exposes a body whose sidecar is not yet in place.
    """
    import os

    from src.ml import prediction_cache as pc_mod

    calls: list[tuple[str, str]] = []
    real_replace = os.replace

    def spy_replace(src: object, dst: object, *args: object, **kwargs: object) -> None:
        calls.append((str(src), str(dst)))
        real_replace(src, dst, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(pc_mod.os, "replace", spy_replace)

    cache = PredictionCache(tmp_path)
    cache.put(_make_key(), _prediction())

    dsts = [dst for _, dst in calls]
    body = next(d for d in dsts if d.endswith(".json"))
    sidecar = next(d for d in dsts if d.endswith(".json.sha256"))
    assert body in dsts and sidecar in dsts, f"missing replace target: {calls}"
    # Every staged source must be a .tmp file (never the final name written direct).
    for src, _ in calls:
        assert src.endswith(".tmp"), f"source not staged via .tmp: {src}"
    # Body replaced LAST → if final body exists, its sidecar is already in place.
    assert dsts.index(body) > dsts.index(
        sidecar
    ), f"body must be os.replace'd after sidecar, got order: {dsts}"


def test_put_crash_before_body_replace_leaves_no_partial(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A crash during put() must never leave a partial final body artifact.

    Inject a failure at the body os.replace step (the final commit). Afterwards
    NO final ``.json`` artifact may exist, no ``.tmp`` files may litter the dir,
    and get() returns MISS — the cache stays consistent.
    """
    import os

    from src.ml import prediction_cache as pc_mod

    cache = PredictionCache(tmp_path)
    key = _make_key()
    final_body = tmp_path / f"{key.digest()}.json"

    real_replace = os.replace

    def flaky_replace(src: object, dst: object, *args: object, **kwargs: object) -> None:
        if str(dst) == str(final_body):
            raise OSError("simulated crash before body commit")
        real_replace(src, dst, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(pc_mod.os, "replace", flaky_replace)

    with pytest.raises(OSError, match="simulated crash"):
        cache.put(key, _prediction())

    assert not final_body.exists(), "partial body artifact left after crash"
    leftovers = [p.name for p in tmp_path.iterdir() if p.name.endswith(".tmp")]
    assert leftovers == [], f"tmp files littered after crash: {leftovers}"
    assert cache.get(key) is None, "cache must report MISS after a failed put"
