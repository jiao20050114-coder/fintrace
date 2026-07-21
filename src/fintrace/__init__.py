"""FinTrace: auditable signal cards for financial research agents."""

from fintrace.schema import Evidence, Signal, SignalStatus, UpdateEvent, WatchItem

__all__ = [
    "Evidence",
    "Signal",
    "SignalStatus",
    "UpdateEvent",
    "WatchItem",
]

__version__ = "0.10.0"
