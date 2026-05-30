"""ML adapters for the Kronos forecasting strategy (Sprint 52).

Public surface: the adapter Protocol plus concrete + mock implementations.
torch is imported lazily and ONLY inside ``KronosModelAdapter`` (C1 isolation).
"""

from src.ml.kronos_adapter import (
    KronosAdapter,
    KronosModelAdapter,
    MockKronosAdapter,
)

__all__ = ["KronosAdapter", "KronosModelAdapter", "MockKronosAdapter"]
