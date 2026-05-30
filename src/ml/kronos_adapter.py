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
from typing import Protocol, runtime_checkable

import pandas as pd

_ML_EXTRA_HINT = "Kronos requires the [ml] extra: pip install -e '.[ml]'"


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
    """

    def __init__(
        self,
        model_id: str,
        tokenizer_id: str,
        device: str = "mps",
        max_context: int = 2048,
        *,
        temperature: float = 1.0,
        top_p: float = 0.9,
        sample_count: int = 1,
    ) -> None:
        """Load the Kronos model + tokenizer (lazy torch import).

        Args:
            model_id: HuggingFace id of the Kronos model (e.g. Kronos-mini).
            tokenizer_id: HuggingFace id of the matching Kronos tokenizer.
            device: torch device string (default ``"mps"`` for operator M4).
            max_context: Max context length; input is sliced to the last
                ``max_context`` rows before prediction.
            temperature: Sampling temperature ``T`` passed to ``predict``.
            top_p: Nucleus sampling cutoff passed to ``predict``.
            sample_count: Number of samples drawn per prediction.

        Raises:
            ImportError: If torch / Kronos are not installed.
        """
        try:
            from kronos import (  # type: ignore[import-not-found]
                Kronos,
                KronosPredictor,
                KronosTokenizer,
            )
        except ImportError as exc:  # torch/Kronos absent in this env by design
            raise ImportError(_ML_EXTRA_HINT) from exc

        self._device = device
        self._max_context = max_context
        self._temperature = temperature
        self._top_p = top_p
        self._sample_count = sample_count

        model = Kronos.from_pretrained(model_id)
        tokenizer = KronosTokenizer.from_pretrained(tokenizer_id)
        self._predictor = KronosPredictor(model, tokenizer, device=device, max_context=max_context)

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
