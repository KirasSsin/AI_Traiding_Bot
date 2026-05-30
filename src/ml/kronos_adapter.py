"""Kronos forecasting adapters (Sprint 52, ADR 0068).

Defines the adapter boundary (C2) between the Kronos ML model and the rest of
the trading system, and enforces the Decimal boundary (C6): every predicted
price leaving an adapter is a :class:`~decimal.Decimal`, never a float / numpy
scalar / tensor.

torch and the Kronos libraries are heavy optional dependencies. They are
imported LAZILY and ONLY inside :class:`KronosModelAdapter` (C1 isolation):
no module-level torch import lives anywhere outside ``src/ml/``. The
``MockKronosAdapter`` is torch-free and is what dev/CI tests run against.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Protocol, runtime_checkable

import pandas as pd

if TYPE_CHECKING:
    from src.ml.kronos_variant import KronosVariant


@runtime_checkable
class KronosAdapter(Protocol):
    """Boundary Protocol for Kronos-style close-price forecasters (C2).

    Implementations forecast the CLOSE price of the next ``horizon`` bars from
    an OHLCV history. All returned prices MUST be :class:`Decimal` (C6).
    """

    def predict(self, ohlcv_df: pd.DataFrame, lookback: int, horizon: int) -> list[Decimal]:
        """Forecast the next ``horizon`` close prices.

        Args:
            ohlcv_df: OHLCV history with a ``DatetimeIndex`` and at least a
                ``close`` column. Only the most recent ``lookback`` rows are
                used as model context.
            lookback: Number of trailing rows fed to the model as context.
            horizon: Number of future bars to forecast (>= 1).

        Returns:
            A list of length ``horizon`` of predicted close prices as Decimals.
        """
        ...


class KronosModelAdapter:
    """Concrete Kronos adapter backed by the real model (C2 + C6).

    This is the ONLY class allowed to import torch / Kronos, and it does so
    lazily inside its methods (C1). If those dependencies are absent, a clean
    :class:`ImportError` with an actionable message is raised.

    SECURITY: pin ``revision`` to a verified commit SHA before any RUN_ML=1 run —
    ``from_pretrained`` deserializes untrusted checkpoints (torch.load pickle = ACE).
    ``weights_hash`` is post-download provenance, NOT ACE prevention.
    """

    def __init__(
        self,
        variant: KronosVariant,
        device: str = "mps",
        *,
        temperature: float = 1.0,
        top_p: float = 0.9,
        sample_count: int = 1,
        revision: str | None = None,
    ) -> None:
        """Load the Kronos model + tokenizer for ``variant`` (lazy import).

        Args:
            variant: Kronos model configuration binding ``model_id``,
                ``tokenizer_id`` and ``max_context`` (see ``kronos_variant``).
            device: torch device string (default ``"mps"`` for operator M4).
            temperature: Sampling temperature ``T`` passed to ``predict``.
            top_p: Nucleus sampling cutoff passed to ``predict``.
            sample_count: Number of samples drawn per prediction.
            revision: HuggingFace revision (branch/tag/commit SHA) for
                ``from_pretrained``. Pin to a verified commit SHA before any
                RUN_ML=1 run (ACE defense — see class docstring).

        SECURITY: pin ``revision`` to a verified commit SHA before any RUN_ML=1
        run — ``from_pretrained`` deserializes untrusted checkpoints (torch.load
        pickle = ACE). ``weights_hash`` is post-download provenance, NOT ACE
        prevention. The submodule sha pins the model *code*.

        Raises:
            ImportError: if the Kronos submodule code or torch is absent.
        """
        import os
        import sys

        kronos_root = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "..", "third_party", "kronos")
        )
        try:
            if kronos_root not in sys.path:
                sys.path.insert(0, kronos_root)
            from model import (  # type: ignore[import-not-found]
                Kronos,
                KronosPredictor,
                KronosTokenizer,
            )
        except ImportError as exc:
            raise ImportError(
                "Kronos model code / torch unavailable. Two steps required: "
                "1) git submodule update --init third_party/kronos  "
                "2) pip install -e '.[ml]'"
            ) from exc

        self._device = device
        self._max_context = variant.max_context
        self._temperature = temperature
        self._top_p = top_p
        self._sample_count = sample_count

        model = Kronos.from_pretrained(variant.model_id, revision=revision)
        tokenizer = KronosTokenizer.from_pretrained(variant.tokenizer_id, revision=revision)
        self._predictor = KronosPredictor(
            model, tokenizer, device=device, max_context=variant.max_context
        )

    def predict(
        self,
        ohlcv_df: pd.DataFrame,
        lookback: int,  # noqa: ARG002 — part of the KronosAdapter contract
        horizon: int,
    ) -> list[Decimal]:
        """Forecast the next ``horizon`` close prices via the Kronos model.

        Slices input to the last ``max_context`` rows, builds the future
        timestamp index from the inferred bar interval, runs the predictor,
        and casts each predicted close to :class:`Decimal` (C6).
        """
        context = ohlcv_df.iloc[-self._max_context :]
        x_timestamp = context.index
        interval = x_timestamp[-1] - x_timestamp[-2]
        last_ts = x_timestamp[-1]
        y_timestamp = pd.DatetimeIndex([last_ts + interval * (i + 1) for i in range(horizon)])

        pred_df = self._predictor.predict(
            df=context,
            x_timestamp=x_timestamp,
            y_timestamp=y_timestamp,
            pred_len=horizon,
            T=self._temperature,
            top_p=self._top_p,
            sample_count=self._sample_count,
        )

        return [Decimal(str(value)) for value in pred_df["close"].tolist()]


class MockKronosAdapter:
    """Deterministic torch-free Kronos adapter for dev/CI (C6-compliant).

    Produces a reproducible forecast purely from the input: the last close is
    extrapolated by a fixed per-step multiplicative drift. Same ``df`` +
    ``horizon`` always yields the same output.
    """

    _DRIFT_PER_STEP: Decimal = Decimal("1.001")

    def predict(
        self,
        ohlcv_df: pd.DataFrame,
        lookback: int,  # noqa: ARG002 — part of the KronosAdapter contract
        horizon: int,
    ) -> list[Decimal]:
        """Return a deterministic list of ``horizon`` close-price Decimals."""
        last_close = Decimal(str(ohlcv_df["close"].iloc[-1]))
        forecast: list[Decimal] = []
        price = last_close
        for _ in range(horizon):
            price = price * self._DRIFT_PER_STEP
            forecast.append(price)
        return forecast
